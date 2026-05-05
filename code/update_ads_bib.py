#!/usr/bin/env python3
# Update main.bib from a public ADS library (works with ads==0.12.x; no ads.Library needed)
from __future__ import annotations
import os, sys
import time
import re
from datetime import datetime

# Ensure project root is on sys.path so `import paths` finds the top-level paths.py
from pathlib import Path
proj_root = Path('/Users/liekevanson/Documents/Projects/post_mt_review').resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import WRITING_DIR      

import requests

LIB_ID  = "Zm5P-O4cQPChveuI79eCzA"       # your public library ID
OUTFILE = WRITING_DIR / "main.bib"      # write output here
API     = "https://api.adsabs.harvard.edu/v1"
PAGE_ROWS = 2000
MAX_RETRIES = 4

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
    })
    return s


def _request_json_with_retry(
    s: requests.Session,
    method: str,
    url: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    """Make an ADS API request with basic retry/backoff for transient failures."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = s.request(method, url, params=params, json=json, timeout=30)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                fail(f"Request failed after {MAX_RETRIES} attempts: {e}")
            time.sleep(2 ** (attempt - 1))
            continue

        # Retry transient server-side/rate-limit errors.
        if r.status_code in {429, 500, 502, 503, 504} and attempt < MAX_RETRIES:
            retry_after = r.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(int(retry_after))
            else:
                time.sleep(2 ** (attempt - 1))
            continue

        if r.status_code == 404:
            fail(f"Library {LIB_ID} not found or not public.")

        if not r.ok:
            body = r.text.strip()
            snippet = body[:500] + ("..." if len(body) > 500 else "")
            fail(
                f"ADS API error {r.status_code} for {method.upper()} {r.url}\n"
                f"Response: {snippet or '<empty>'}"
            )

        try:
            return r.json()
        except ValueError:
            fail(f"ADS API returned non-JSON response for {method.upper()} {r.url}")

    fail("Unexpected retry loop exit.")

def fetch_library_bibcodes(s: requests.Session, lib_id: str) -> list[str]:
    url = f"{API}/biblib/libraries/{lib_id}"
    all_docs: list[str] = []
    start = 0

    while True:
        j = _request_json_with_retry(
            s,
            "get",
            url,
            params={"rows": PAGE_ROWS, "start": start},
        )
        docs = j.get("documents", [])
        if not docs:
            break

        all_docs.extend(docs)
        if len(docs) < PAGE_ROWS:
            break
        start += PAGE_ROWS

    # Preserve order while removing accidental duplicates.
    return list(dict.fromkeys(all_docs))


def export_bibtex(s: requests.Session, bibcodes: list[str]) -> str:
    # sort="no sort" preserves the input order returned by biblib.
    j = _request_json_with_retry(
        s,
        "post",
        f"{API}/export/bibtex",
        json={"bibcode": bibcodes, "sort": "no sort"},
    )
    return j.get("export", "")


def sanitize_bibtex_for_pdflatex(bib: str) -> str:
    """
    Replace accent macros that can fail under default OT1 pdflatex settings.

    ADS sometimes emits names such as St{\k{e}}pie{\'n}. The ogonek accent
    command (\k) is unavailable in OT1 and causes hard LaTeX errors.
    """
    # Replace \k{...} with the bare letter to keep compilation robust.
    # Example: St{\k{e}}pie{\'n} -> St{e}pie{\'n}
    return re.sub(r"\\k\{([^{}])\}", r"\1", bib)

def main():
    s = get_session()

    bibcodes = fetch_library_bibcodes(s, LIB_ID)
    if not bibcodes:
        fail(f"No bibcodes found in library {LIB_ID}.")

    bib = export_bibtex(s, bibcodes)
    bib = sanitize_bibtex_for_pdflatex(bib)
    text = bib if bib.endswith("\n") else bib + "\n"

    if OUTFILE.exists() and OUTFILE.read_text(encoding="utf-8") == text:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] no changes in {OUTFILE}")
        return

    tmp = OUTFILE.with_suffix(OUTFILE.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(OUTFILE)
    print(f"[{datetime.now().isoformat(timespec='seconds')}] wrote {OUTFILE}")

if __name__ == "__main__":
    main()


