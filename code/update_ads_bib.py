#!/usr/bin/env python3
# Update main.bib from a public ADS library (works with ads==0.12.x; no ads.Library needed)
from __future__ import annotations
import os, sys
from datetime import datetime

# Ensure project root is on sys.path so `import paths` finds the top-level paths.py
from pathlib import Path
proj_root = Path('/Users/liekevanson/Documents/Projects/post_mt_review').resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import WRITING_DIR      # keep your way

import requests

LIB_ID  = "Zm5P-O4cQPChveuI79eCzA"       # your public library ID
OUTFILE = WRITING_DIR / "main.bib"      # write exactly here
API     = "https://api.adsabs.harvard.edu/v1"

def fail(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)

def get_session() -> requests.Session:
    token = os.getenv("ADS_DEV_KEY")
    if not token:
        fail("ERROR: ADS_DEV_KEY env var is not set.")
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    return s

def fetch_library_bibcodes(s: requests.Session, lib_id: str) -> list[str]:
    # Ask for a huge number of rows to avoid pagination.
    url = f"{API}/biblib/libraries/{lib_id}"
    r = s.get(url, params={"rows": 20_000_000})
    if r.status_code == 404:
        fail(f"Library {lib_id} not found or not public.")
    r.raise_for_status()
    j = r.json()
    return j.get("documents", [])


def export_bibtex(s: requests.Session, bibcodes: list[str]) -> str:
    # sort="no sort" preserves the input order returned by biblib.
    r = s.post(f"{API}/export/bibtex", json={"bibcode": bibcodes, "sort": "no sort"})
    r.raise_for_status()
    j = r.json()
    return j.get("export", "")

def main():
    s = get_session()

    bibcodes = fetch_library_bibcodes(s, LIB_ID)
    if not bibcodes:
        fail(f"No bibcodes found in library {LIB_ID}.")

    bib = export_bibtex(s, bibcodes)
    text = bib if bib.endswith("\n") else bib + "\n"

    # Do not mkdir WRITING_DIR (per your request). Just write atomically.
    if OUTFILE.exists() and OUTFILE.read_text(encoding="utf-8") == text:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] no changes in {OUTFILE}")
        return

    tmp = OUTFILE.with_suffix(OUTFILE.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(OUTFILE)
    print(f"[{datetime.now().isoformat(timespec='seconds')}] wrote {OUTFILE}")

if __name__ == "__main__":
    main()


