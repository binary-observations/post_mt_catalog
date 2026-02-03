#!/usr/bin/env python3
import json
import math
import numpy as np
import h5py
from pathlib import Path
from typing import Any
from io import StringIO
import pandas as pd
from urllib.parse import quote
import time
import re
import requests

import sys
from pathlib import Path

proj_root = Path('/Users/liekevanson/Documents/Projects/post_mt_review').resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

# -------------------------------------------------
# Configuration
# -------------------------------------------------
from paths import RESULT_TABLES, RAW_JSON_DIR, LEGACY_H5_DIR, DATA_DIR

# Import astropy for coordinate-based deduplication
try:
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    ASTROPY_AVAILABLE = True
except ImportError:
    ASTROPY_AVAILABLE = False
    print("Warning: astropy not available; will use name-based deduplication only")

HDF5_DIR = LEGACY_H5_DIR
OUTPUT_JSON = DATA_DIR / "post_mt_systems.json"

# Import schema upgrader
import importlib.util
schema_path = Path(proj_root) / "code" / "data_processing" / "update_data_schema_v1_v2.py"
spec = importlib.util.spec_from_file_location("update_data_schema_v1_v2", str(schema_path))
schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schema)
upgrade_entry_schema = schema.upgrade_entry_schema

triplet_cols = ["RA", "Dec", "Period", "Eccentricity", "M1", "M1_sin3i", "M2", "M2_sin3i", "q", "Mass Function"]

# -------------------------------------------------
# Utility helpers
# -------------------------------------------------
def is_nan(x: Any) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except Exception:
        return False


def sanitize(obj: Any) -> Any:
    """Recursively replace NaN with None and strip whitespace."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, str):
        return obj.strip()
    if is_nan(obj):
        return None
    return obj


# -------------------------------------------------
# Legacy → new schema mapping
# -------------------------------------------------
def map_system_class(old_class: str | None, system_name: str | None):
    if not old_class:
        return "Spectroscopic binary"

    c = old_class.strip().lower()
    name = (system_name or "").strip()

    if "wolf" in c or "rayet" in c:
        return "WR binary"
    if "hot subdwarf" in c or "subdwarf" in c:
        return "Hot subdwarf"
    if "post agb" in c:
        return "post-AGB binary"
    if "barium" in c or "ch" in c:
        return "Chemically Peculiar"
    if "white dwarf" in c:
        return "Gaia WD + MS" if name.startswith("Gaia DR3") else "WD + non-degenerate"

    return "Spectroscopic binary"


def infer_evolution_type(obs_type: str | None):
    if not obs_type:
        return None
    o = obs_type.lower()
    if any(k in o for k in ["wd", "white dwarf", "subdwarf", "barium", "ch"]):
        return "post-mass transfer"
    if any(k in o for k in ["wolf", "rayet"]):
        return "stripped-envelope"
    return None


# -------------------------------------------------
# Duplicate handling
# -------------------------------------------------
def resolve_duplicate_pair(a: dict, b: dict) -> dict:
    """Prefer entry with more populated fields."""
    score_a = sum(v not in (None, "", []) for v in a.values())
    score_b = sum(v not in (None, "", []) for v in b.values())
    return a if score_a >= score_b else b


def extract_central_value(entry: dict, key: str) -> float | None:
    """Extract central value from triplet [err-, value, err+] or return value directly."""
    val = entry.get(key)
    if isinstance(val, list) and len(val) == 3:
        return val[1] if isinstance(val[1], (int, float)) else None
    elif isinstance(val, (int, float)):
        return val
    else:
        return None


def make_simbad_url_from_coords(ra_deg: float | None, dec_deg: float | None, radius_arcsec: int = 5) -> str | None:
    """Return a SIMBAD coordinate-search URL using decimal degrees and arcsec radius."""
    try:
        if ra_deg is None or dec_deg is None:
            return None
        coords = f"{float(ra_deg)} {float(dec_deg)}"
        return (
            "https://simbad.cds.unistra.fr/simbad/sim-coo?Coord="
            + quote(coords)
            + f"&Radius={radius_arcsec}&Radius.unit=arcsec&output.format=ASCII"
        )
    except Exception:
        return None


def add_simbad_links(systems: list[dict]) -> None:
    """Populate 'Simbad' field for entries that have central RA/Dec values."""
    for entry in systems:
        ra_val = extract_central_value(entry, "RA")
        dec_val = extract_central_value(entry, "Dec")
        entry["Simbad"] = make_simbad_url_from_coords(ra_val, dec_val) if (ra_val is not None and dec_val is not None) else None


def normalize_system_name(name: str | None) -> str:
    """Normalize system name for comparison: remove spaces, standardize case."""
    if not name:
        return ""
    # Remove spaces, convert to lowercase for matching
    return name.strip().replace(" ", "").lower()


def merge_duplicates_by_name(systems: list[dict]) -> list[dict]:
    """Merge by System Name only (with normalization for spacing/case)."""
    merged = {}
    name_map = {}  # Map normalized name → original name to keep
    
    for s in systems:
        key = s.get("System Name")
        if not key:
            continue
        normalized = normalize_system_name(key)
        
        # Store mapping from normalized to original name
        if normalized not in name_map:
            name_map[normalized] = key
        
        if normalized in merged:
            merged[normalized] = resolve_duplicate_pair(merged[normalized], s)
        else:
            merged[normalized] = s
    
    return list(merged.values())


def merge_duplicates_by_coords(systems: list[dict], threshold_arcsec: float = 0.1) -> list[dict]:
    """Merge duplicates using coordinate matching (RA/Dec) FIRST, then normalized names.
    
    Priority: coordinates > normalized names
    Falls back to name-based merging if astropy is unavailable or if coordinates are missing.
    """
    if not ASTROPY_AVAILABLE:
        print("Astropy unavailable; using name-based deduplication only")
        return merge_duplicates_by_name(systems)
    
    # Extract coordinates for all systems
    coords_list = []
    valid_indices = []
    
    for i, entry in enumerate(systems):
        ra = extract_central_value(entry, 'RA')
        dec = extract_central_value(entry, 'Dec')
        
        if ra is not None and dec is not None:
            try:
                if not (np.isnan(ra) or np.isnan(dec)):
                    coords_list.append(SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs'))
                    valid_indices.append(i)
            except Exception:
                pass
    
    print(f"Systems with valid coordinates: {len(coords_list)}")
    
    # Phase 1: Coordinate-based deduplication
    merged = {}
    used = set()
    coord_duplicates_found = 0
    
    if len(coords_list) >= 2:
        all_coords = SkyCoord(coords_list)
        sep_matrix = all_coords[:, None].separation(all_coords[None, :]).to(u.arcsec).value
        
        for i in range(len(coords_list)):
            if i in used:
                continue
            
            primary_idx = valid_indices[i]
            primary = systems[primary_idx]
            merged[primary_idx] = primary
            used.add(i)
            
            # Find duplicates of this system
            for j in range(i + 1, len(coords_list)):
                if j in used:
                    continue
                if sep_matrix[i, j] < threshold_arcsec:
                    dup_idx = valid_indices[j]
                    dup_entry = systems[dup_idx]
                    dup_name = dup_entry.get("System Name", "unknown")
                    primary_name = primary.get("System Name", "unknown")
                    print(f"  Found coordinate match: {primary_name} ({systems[primary_idx].get('source_file')}) ≈ {dup_name} ({dup_entry.get('source_file')}) @ {sep_matrix[i, j]:.4f} arcsec")
                    # Merge: keep entry with more populated fields
                    merged[primary_idx] = resolve_duplicate_pair(merged[primary_idx], dup_entry)
                    used.add(j)
                    coord_duplicates_found += 1
    
    print(f"Coordinate-based duplicates merged: {coord_duplicates_found}")
    
    # Add systems that had valid coordinates but were not matched
    for i in range(len(coords_list)):
        if i not in used:
            idx = valid_indices[i]
            if idx not in merged:
                merged[idx] = systems[idx]
    
    # Phase 2: Name-based deduplication (normalized) for remaining systems without coordinates
    # or for additional cleanup
    result_list = [merged[i] for i in sorted(merged.keys())]
    name_merged = merge_duplicates_by_name(result_list)
    
    print(f"After name-based dedup: {len(name_merged)} systems")
    
    return name_merged


def merge_duplicates(systems: list[dict]) -> list[dict]:
    """Merge duplicates using both name and coordinate matching."""
    return merge_duplicates_by_coords(systems)


# -------------------------------------------------
# SIMBAD spectral enrichment (lightweight ASCII endpoints)
# -------------------------------------------------

def _parse_simbad_ascii_for_sptype(text: str) -> str | None:
    """Extract a spectral type string from SIMBAD ASCII output."""
    if not text:
        return None
    for key in ("SPTYPE", "SP_TYPE", "Spectral type:"):
        for line in text.splitlines():
            if key in line:
                val = line.split(key, 1)[-1]
                val = val.split("=", 1)[-1] if "=" in val else val
                val = val.split(":", 1)[-1] if ":" in val else val
                v = val.strip()
                if v:
                    return v
    return None


def query_simbad_sptype_by_name(name: str) -> str | None:
    """Query SIMBAD by object name and parse spectral type from ASCII output."""
    if not name:
        return None
    try:
        url = (
            "https://simbad.cds.unistra.fr/simbad/sim-id?Ident="
            + quote(name)
            + "&output.format=ASCII"
        )
        resp = requests.get(url, timeout=15)
        if resp.ok:
            return _parse_simbad_ascii_for_sptype(resp.text)
    except Exception:
        return None
    return None


def query_simbad_sptype_by_coords(ra_deg: float | None, dec_deg: float | None, radius_arcsec: int = 5) -> str | None:
    """Query SIMBAD by coordinates and parse spectral type from ASCII output."""
    if ra_deg is None or dec_deg is None:
        return None
    try:
        coords = f"{float(ra_deg)} {float(dec_deg)}"
        url = (
            "https://simbad.cds.unistra.fr/simbad/sim-coo?Coord="
            + quote(coords)
            + f"&Radius={radius_arcsec}&Radius.unit=arcsec&output.format=ASCII"
        )
        resp = requests.get(url, timeout=15)
        if resp.ok:
            return _parse_simbad_ascii_for_sptype(resp.text)
    except Exception:
        return None
    return None


_SPECTRAL_TOKEN_RE = re.compile(r"\b([OBAFGKM][0-9](?:\.[0-9])?(?:[-–][0-9](?:\.[0-9])?)?(?:[IV]{1,3}|V)?e?)\b", re.IGNORECASE)


def parse_spectral_components(sptype: str) -> list[str]:
    """Split a spectral type into up to two component-like tokens.
    Handles separators '+', '/', and whitespace; normalizes repeated colons.
    """
    if not sptype:
        return []
    s = sptype.replace(":", " ").replace("::", " ")
    parts = re.split(r"[+/]", s)
    tokens: list[str] = []
    for part in parts:
        # find the best spectral token within this part
        m = _SPECTRAL_TOKEN_RE.search(part.strip())
        if m:
            tokens.append(m.group(1))
    # limit to two
    return tokens[:2]


def _set_if_missing(entry: dict, key: str, value: str | None) -> bool:
    """Set entry[key] to value only if it is missing/empty; return True if set."""
    if value is None or value == "":
        return False
    cur = entry.get(key)
    if cur in (None, "", []):
        entry[key] = value
        return True
    return False



# -------------------------------------------------
# Ingestion
# -------------------------------------------------

all_systems: list[dict] = []

# ---- HDF5 legacy tables ----
# Skip example files
skip_files = {"example_obs_df_full.h5", "example_obs_df.h5"}

for h5_path in sorted(HDF5_DIR.glob("*.h5")):
    if h5_path.name in skip_files:
        print(f"Skipping {h5_path.name}...")
        continue
    print(f"Processing {h5_path.name}...")
    try:
        with h5py.File(h5_path, "r") as f:
            metadata_json = f["metadata_json"][()].decode("utf-8")
            metadata_df = pd.read_json(StringIO(metadata_json), orient="records")

            for idx in range(len(metadata_df)):
                entry = metadata_df.loc[idx].to_dict()

                # Extract triplet columns (value, uncertainty triplets)
                for col in triplet_cols:
                    if col in f:
                        try:
                            loerr = float(f[col][idx, 0])
                            val   = float(f[col][idx, 1])
                            uperr = float(f[col][idx, 2])
                            entry[col] = [round(loerr, 5), round(val, 5), round(uperr, 5)]
                        except (IndexError, ValueError, TypeError):
                            pass

                entry["source_file"] = h5_path.name
                
                # Apply schema upgrade
                entry = upgrade_entry_schema(entry)
                all_systems.append(entry)
    except Exception as e:
        print(f"  Error processing {h5_path.name}: {e}")
        continue

# ---- HDF5 legacy tables in WDMS subdirectory ----
wdms_dir = HDF5_DIR / "WDMS"
if wdms_dir.exists():
    for h5_path in sorted(wdms_dir.glob("*.h5")):
        print(f"Processing {h5_path.name}...")
        try:
            with h5py.File(h5_path, "r") as f:
                metadata_json = f["metadata_json"][()].decode("utf-8")
                metadata_df = pd.read_json(StringIO(metadata_json), orient="records")

                for idx in range(len(metadata_df)):
                    entry = metadata_df.loc[idx].to_dict()

                    # Extract triplet columns (value, uncertainty triplets)
                    for col in triplet_cols:
                        if col in f:
                            try:
                                loerr = float(f[col][idx, 0])
                                val   = float(f[col][idx, 1])
                                uperr = float(f[col][idx, 2])
                                entry[col] = [round(loerr, 5), round(val, 5), round(uperr, 5)]
                            except (IndexError, ValueError, TypeError):
                                pass

                    entry["source_file"] = f"WDMS/{h5_path.name}"
                    
                    # Apply schema upgrade
                    entry = upgrade_entry_schema(entry)
                    all_systems.append(entry)
        except Exception as e:
            print(f"  Error processing {h5_path.name}: {e}")
            continue

print(f"Ingested {len(all_systems)} systems from HDF5 tables.")

# ---- RAW JSON tables (e.g. Malkov 2020) ----
raw_json_files = sorted(RAW_JSON_DIR.glob("*.json"))
print(f"Found {len(raw_json_files)} raw JSON tables.")

for jp in raw_json_files:
    print(f"Processing {jp.name}...")
    with open(jp, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        continue
    for entry in data:
        # Apply schema upgrade to JSON entries too
        entry = upgrade_entry_schema(entry)
        all_systems.append(entry)

print(f"Total systems after JSON ingestion: {len(all_systems)}")

# -------------------------------------------------
# Deduplication
# -------------------------------------------------

all_systems = merge_duplicates(all_systems)
print(f"Total systems after deduplication: {len(all_systems)}")


# -------------------------------------------------
# Final sanitization & output
# -------------------------------------------------
# Add SIMBAD links before sanitization/output
add_simbad_links(all_systems)

all_systems = sanitize(all_systems)

with open(OUTPUT_JSON, "w") as f:
    f.write("[\n")
    for i, system in enumerate(all_systems):
        f.write(json.dumps(system, separators=(",", ":")))
        if i < len(all_systems) - 1:
            f.write(",\n")
        else:
            f.write("\n")
    f.write("]\n")

print(f"Wrote {len(all_systems)} systems to {OUTPUT_JSON}")
# Final sanitization & output
# -------------------------------------------------

# Add SIMBAD links before sanitization/output
add_simbad_links(all_systems)

all_systems = sanitize(all_systems)

with open(OUTPUT_JSON, "w") as f:
    f.write("[\n")
    for i, system in enumerate(all_systems):
        f.write(json.dumps(system, separators=(",", ":")))
        if i < len(all_systems) - 1:
            f.write(",\n")
        else:
            f.write("\n")
    f.write("]\n")

print(f"Wrote {len(all_systems)} systems to {OUTPUT_JSON}")
