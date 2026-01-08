#!/usr/bin/env python3
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any
import re
import requests
from urllib.parse import quote

# Lightweight SIMBAD ASCII parsing to avoid heavy TAP calls

_SPECTRAL_LINE_KEYS = ("SPTYPE", "SP_TYPE", "Spectral type:")
_SPECTRAL_TOKEN_RE = re.compile(r"\b([OBAFGKM][0-9](?:\.[0-9])?(?:[-–][0-9](?:\.[0-9])?)?(?:[IV]{1,3}|V)?e?)\b", re.IGNORECASE)


def _parse_simbad_ascii_for_sptype(text: str) -> str | None:
    if not text:
        return None
    for key in _SPECTRAL_LINE_KEYS:
        for line in text.splitlines():
            if key in line:
                val = line.split(key, 1)[-1]
                val = val.split("=", 1)[-1] if "=" in val else val
                val = val.split(":", 1)[-1] if ":" in val else val
                v = val.strip()
                # Strip trailing citation blocks like " C 1968ApJS..."
                v = v.split(" C ", 1)[0].strip()
                if v:
                    return v
    return None


def query_simbad_sptype_by_name(name: str, timeout: int = 15) -> str | None:
    if not name:
        return None
    try:
        url = ("https://simbad.cds.unistra.fr/simbad/sim-id?Ident=" + quote(name) + "&output.format=ASCII")
        resp = requests.get(url, timeout=timeout)
        if resp.ok:
            return _parse_simbad_ascii_for_sptype(resp.text)
    except Exception:
        return None
    return None


def query_simbad_sptype_by_coords(ra_deg: float | None, dec_deg: float | None, radius_arcsec: int = 5, timeout: int = 15) -> str | None:
    if ra_deg is None or dec_deg is None:
        return None
    try:
        coords = f"{float(ra_deg)} {float(dec_deg)}"
        url = (
            "https://simbad.cds.unistra.fr/simbad/sim-coo?Coord="
            + quote(coords)
            + f"&Radius={radius_arcsec}&Radius.unit=arcsec&output.format=ASCII"
        )
        resp = requests.get(url, timeout=timeout)
        if resp.ok:
            return _parse_simbad_ascii_for_sptype(resp.text)
    except Exception:
        return None
    return None


def spectral_tokens(sptype: str) -> list[str]:
    """Split a spectral type into up to two component-like tokens."""
    if not sptype:
        return []
    s = sptype.replace(":", " ").replace("::", " ")
    parts = re.split(r"[+/]", s)
    tokens: list[str] = []
    for part in parts:
        m = _SPECTRAL_TOKEN_RE.search(part.strip())
        if m:
            tokens.append(m.group(1))
    return tokens[:2]


def extract_central_value(entry: dict, key: str) -> float | None:
    val = entry.get(key)
    if isinstance(val, list) and len(val) == 3:
        return val[1] if isinstance(val[1], (int, float)) else None
    elif isinstance(val, (int, float)):
        return val
    else:
        return None


class Cache:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, Any] = {}
        if self.path.exists():
            try:
                self.data = json.load(open(self.path, "r"))
            except Exception:
                self.data = {}

    def get(self, key: str) -> Any:
        return self.data.get(key)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def save(self) -> None:
        try:
            json.dump(self.data, open(self.path, "w"), separators=(",", ":"))
        except Exception:
            pass


def enrich_entry(entry: dict, cache: Cache) -> bool:
    """Fill missing obs_type_1/obs_type_2 using SIMBAD. Returns True if updated."""
    o1_missing = entry.get("obs_type_1") in (None, "", [])
    o2_missing = entry.get("obs_type_2") in (None, "", [])
    if not (o1_missing or o2_missing):
        return False
    name = entry.get("System Name") or ""
    cache_key = None
    sptype = None
    if name:
        cache_key = f"name::{name}"
        sptype = cache.get(cache_key)
        if sptype is None:
            sptype = query_simbad_sptype_by_name(name)
            cache.set(cache_key, sptype)
    if not sptype:
        ra_val = extract_central_value(entry, "RA")
        dec_val = extract_central_value(entry, "Dec")
        cache_key = f"coo::{ra_val},{dec_val}"
        sptype = cache.get(cache_key)
        if sptype is None:
            sptype = query_simbad_sptype_by_coords(ra_val, dec_val)
            cache.set(cache_key, sptype)
    if not sptype:
        return False
    toks = spectral_tokens(sptype)
    changed = False
    if toks:
        if o1_missing and len(toks) >= 1:
            entry["obs_type_1"] = toks[0]
            changed = True
        if o2_missing and len(toks) >= 2:
            entry["obs_type_2"] = toks[1]
            changed = True
    return changed
