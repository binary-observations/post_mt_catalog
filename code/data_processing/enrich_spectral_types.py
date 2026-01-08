#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
import time

# Project paths
proj_root = Path(__file__).resolve().parents[2]
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))
from paths import DATA_DIR

# Ensure local module path is available when running as a script
local_dir = Path(__file__).resolve().parent
if str(local_dir) not in sys.path:
    sys.path.insert(0, str(local_dir))
from simbad_enrichment import Cache, enrich_entry


def load_catalog(path: Path) -> list[dict]:
    data = json.load(open(path, "r"))
    assert isinstance(data, list)
    return data


def save_catalog(path: Path, entries: list[dict]) -> None:
    with open(path, "w") as f:
        f.write("[\n")
        for i, system in enumerate(entries):
            f.write(json.dumps(system, separators=(",", ":")))
            if i < len(entries) - 1:
                f.write(",\n")
            else:
                f.write("\n")
        f.write("]\n")


def _process_indices(entries: list[dict], indices: list[int], cache: Cache, workers: int) -> int:
    updated = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(enrich_entry, entries[i], cache): i for i in indices}
        for fut in as_completed(futs):
            try:
                if fut.result():
                    updated += 1
            except Exception:
                pass
    return updated


def main(max_queries: int = 200, workers: int = 8, chunk_size: int = 500) -> None:
    catalog_file = DATA_DIR / "post_mt_systems.json"
    cache_file = DATA_DIR / "simbad_cache.json"
    print(f"Loading catalog: {catalog_file}")
    entries = load_catalog(catalog_file)
    cache = Cache(cache_file)

    # Build a list of indices needing enrichment
    targets = [i for i, e in enumerate(entries) if e.get("obs_type_1") in (None, "", []) or e.get("obs_type_2") in (None, "", [])]
    total_needed = len(targets)
    if max_queries > 0:
        targets = targets[:max_queries]
    print(f"Entries needing enrichment: {total_needed} (processing {len(targets)} this run)")

    updated_total = 0
    start = time.time()
    # Chunk processing with periodic saves
    for start_idx in range(0, len(targets), chunk_size):
        batch = targets[start_idx:start_idx + chunk_size]
        if not batch:
            break
        batch_start = time.time()
        updated = _process_indices(entries, batch, cache, workers)
        updated_total += updated
        cache.save()
        # Save catalog after each chunk
        save_catalog(catalog_file, entries)
        elapsed_batch = time.time() - batch_start
        print(f"Chunk {start_idx//chunk_size + 1}: updated {updated} entries in {elapsed_batch:.1f}s (cumulative {updated_total}).")

    elapsed = time.time() - start
    print(f"SIMBAD enrichment updated {updated_total} entries in {elapsed:.1f}s using {workers} workers (chunk_size={chunk_size}).")
    print(f"Catalog saved to: {catalog_file}")
    print("Done.")


if __name__ == "__main__":
    # CLI args: max_queries, workers, chunk_size
    mq = 200
    wk = 8
    ch = 500
    if len(sys.argv) >= 2:
        try:
            mq = int(sys.argv[1])
        except Exception:
            pass
    if len(sys.argv) >= 3:
        try:
            wk = int(sys.argv[2])
        except Exception:
            pass
    if len(sys.argv) >= 4:
        try:
            ch = int(sys.argv[3])
        except Exception:
            pass
    main(max_queries=mq, workers=wk, chunk_size=ch)
