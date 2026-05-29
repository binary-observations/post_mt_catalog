#!/usr/bin/env python3
"""Export the main JSON catalog to tabular formats.

This script reads the catalog JSON file (list of dict entries), expands triplet-valued
fields into three columns, and writes multiple output formats.

Triplet expansion rule:
- If a value is a list/tuple of length 3 and each element is numeric or null,
  it is interpreted as [err_minus, value, err_plus].
- The original column is replaced by the central value, and two companion columns
  are added:
    <column>_errm, <column>_errp

Outputs:
- CSV
- FITS
- ECSV
- JSONL
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
from astropy.table import Table

proj_root = Path(__file__).resolve().parents[2]
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import DATA_DIR, MAIN_CATALOG


# Data notes used for table metadata and sidecar documentation.
COLUMN_DESCRIPTIONS: dict[str, str] = {
    "System Name": "Primary system identifier used in the catalog.",
    "RA": "Right ascension in degrees.",
    "Dec": "Declination in degrees.",
    "Reference": "ADS bibcode reference for the measurement.",
    "Notes": "Free-text notes, provenance remarks, and caveats for the entry.",
    "Period": "Orbital period in days.",
    "Eccentricity": "Orbital eccentricity.",
    "M1": "Presumed accretor mass in solar masses.",
    "M2": "Presumed donor mass in solar masses.",
    "M1_sin3i": "Projected accretor mass term M1*sin(i)^3.",
    "M2_sin3i": "Projected donor mass term M2*sin(i)^3.",
    "Mass Function": "Binary mass function as reported or derived in the source.",
    "evol_type_1": "Assumed evolutionary stage of the accretor.",
    "evol_type_2": "Assumed evolutionary stage of the donor.",
    "obs_type_1": "Observed classification of the accretor (for example spectral type).",
    "obs_type_2": "Observed classification of the donor (for example spectral type).",
    "system_class": "Class of binary system.",
    "quality_flags": "Flags marking assumed values and/or minimum/maximum constraints.",
    "Simbad": "SIMBAD coordinate-query URL for the source position.",
}


COLUMN_UNITS: dict[str, str] = {
    "RA": "deg",
    "Dec": "deg",
    "Period": "d",
    "M1": "solMass",
    "M2": "solMass",
    "M1_sin3i": "solMass",
    "M2_sin3i": "solMass",
}


GLOBAL_NOTES: list[str] = [
    "RA and Dec are in degrees.",
    "Reference values are ADS bibcodes.",
    "Period is in days.",
    "M1 is the presumed accretor mass in solar masses.",
    "M2 is the presumed donor mass in solar masses.",
    "M1_sin3i is the projected mass term of the accretor (M1*sin(i)^3).",
    "M2_sin3i is the projected mass term of the donor (M2*sin(i)^3).",
    "evol_type_1 and evol_type_2 are assumed evolutionary stages for accretor and donor.",
    "obs_type_1 and obs_type_2 are observational types (for example spectral class) for accretor and donor.",
    "system_class is the broad class of binary system.",
    "quality_flags marks entries with assumed values or minimum/maximum constraints.",
]


def _is_number_or_none(value: Any) -> bool:
    return value is None or isinstance(value, (int, float))


def _is_triplet(value: Any) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return False
    return all(_is_number_or_none(v) for v in value)


def _normalize_nan(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _serialize_for_table(value: Any) -> Any:
    """Convert non-scalar objects to JSON text for flat table formats."""
    value = _normalize_nan(value)
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _to_ascii_text(value: Any) -> str:
    """Return an ASCII-safe representation for FITS text columns."""
    if value is None:
        return ""
    text = str(value).replace("\u2212", "-")
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def expand_triplets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand all triplet fields into value/errm/errp columns."""
    if not records:
        return []

    triplet_columns: set[str] = set()
    for rec in records:
        for key, value in rec.items():
            if _is_triplet(value):
                triplet_columns.add(key)

    expanded: list[dict[str, Any]] = []
    for rec in records:
        out: dict[str, Any] = {}
        for key, value in rec.items():
            if key in triplet_columns and _is_triplet(value):
                errm, central, errp = value
                out[f"{key}_errm"] = _normalize_nan(errm)
                out[key] = _normalize_nan(central)
                out[f"{key}_errp"] = _normalize_nan(errp)
            elif key in triplet_columns:
                # Keep schema consistent even if this row lacks a valid triplet.
                out[f"{key}_errm"] = None
                out[key] = _serialize_for_table(value)
                out[f"{key}_errp"] = None
            else:
                out[key] = _serialize_for_table(value)
        expanded.append(out)

    return expanded


def _apply_table_metadata(table: Table) -> None:
    """Attach column units/descriptions and global notes to Astropy table metadata."""
    descriptions = _build_column_descriptions(table.colnames)
    for col_name, desc in descriptions.items():
        if col_name in table.colnames:
            table[col_name].description = desc

    for col_name, unit in COLUMN_UNITS.items():
        if col_name in table.colnames:
            table[col_name].unit = unit

    table.meta["comments"] = GLOBAL_NOTES


def _default_column_description(col_name: str) -> str:
    """Return a generic description for columns not explicitly documented."""
    if col_name.endswith("_errm"):
        base = col_name[:-5]
        return f"Lower uncertainty for {base}."
    if col_name.endswith("_errp"):
        base = col_name[:-5]
        return f"Upper uncertainty for {base}."
    return f"Catalog field: {col_name}."


def _build_column_descriptions(columns: list[str] | Any) -> dict[str, str]:
    """Build descriptions for all columns, using defaults when needed."""
    out: dict[str, str] = {}
    for col in columns:
        out[col] = COLUMN_DESCRIPTIONS.get(col, _default_column_description(col))
    return out


def _write_notes_file(output_dir: Path, stem: str) -> Path:
    """Write a human-readable notes/data-dictionary sidecar file."""
    notes_path = output_dir / f"{stem}_notes.md"
    lines = [
        "# Catalog Notes",
        "",
        "## Global Notes",
    ]
    lines.extend([f"- {note}" for note in GLOBAL_NOTES])
    lines.extend(["", "## Column Definitions"])
    sample_csv = output_dir / f"{stem}.csv"
    if sample_csv.exists():
        columns = list(pd.read_csv(sample_csv, nrows=0).columns)
    else:
        columns = sorted(COLUMN_DESCRIPTIONS.keys())

    all_descriptions = _build_column_descriptions(columns)
    for key in sorted(all_descriptions.keys()):
        unit_suffix = ""
        if key in COLUMN_UNITS:
            unit_suffix = f" (unit: {COLUMN_UNITS[key]})"
        lines.append(f"- {key}: {all_descriptions[key]}{unit_suffix}")

    notes_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return notes_path


def write_outputs(df: pd.DataFrame, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{stem}.csv"
    fits_path = output_dir / f"{stem}.fits"
    ecsv_path = output_dir / f"{stem}.ecsv"
    jsonl_path = output_dir / f"{stem}.jsonl"
    notes_path = output_dir / f"{stem}_notes.md"

    df.to_csv(csv_path, index=False)

    # FITS columns do not support arbitrary mixed Python object dtypes.
    # Normalize object columns to strings while preserving nulls as empty text.
    fits_df = df.copy()
    for col in fits_df.columns:
        if fits_df[col].dtype == object:
            fits_df[col] = fits_df[col].map(_to_ascii_text)

    table = Table.from_pandas(fits_df)
    _apply_table_metadata(table)
    table.write(fits_path, format="fits", overwrite=True)
    table.write(ecsv_path, format="ascii.ecsv", overwrite=True)

    with jsonl_path.open("w", encoding="utf-8") as f:
        for rec in df.to_dict(orient="records"):
            f.write(json.dumps(rec, ensure_ascii=True, separators=(",", ":")) + "\n")

    _write_notes_file(output_dir, stem)

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {fits_path}")
    print(f"Wrote: {ecsv_path}")
    print(f"Wrote: {jsonl_path}")
    print(f"Wrote: {notes_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the post-mass-transfer JSON catalog to multiple tabular formats."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=MAIN_CATALOG,
        help="Input JSON catalog path (default: data/post_mt_systems.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DATA_DIR / "alternate_formats",
        help="Output directory for exported files (default: data/exports)",
    )
    parser.add_argument(
        "--stem",
        type=str,
        default="post_mt_systems_flat",
        help="Base filename stem for outputs.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    with args.input.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of catalog entries (objects).")

    records = [d for d in data if isinstance(d, dict)]
    expanded = expand_triplets(records)
    df = pd.DataFrame(expanded)

    write_outputs(df, args.output_dir, args.stem)
    print(f"Done. Exported {len(df)} rows with {len(df.columns)} columns.")


if __name__ == "__main__":
    main()
