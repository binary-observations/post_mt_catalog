import pandas as pd
import h5py
import json
from io import StringIO
import os, sys
import argparse

# Ensure project root is on sys.path so `import paths` finds the top-level paths.py
from pathlib import Path
proj_root = Path('/Users/liekevanson/Documents/Projects/post_mt_review').resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import RESULT_TABLES, DATA_DIR

# === CONFIGURATION ===
# Set up argument parser
parser = argparse.ArgumentParser(description="Combine post-mass-transfer system tables into a single JSON file.")
parser.add_argument("input_h5_path", type=str, nargs='?', help="Path to the directory containing .h5 files.", default=str(RESULT_TABLES))
parser.add_argument("output_json_path", type=str, nargs='?', help="Path to save the combined JSON output. (must include outp filename)",  default=str(DATA_DIR / "post_mt_systems.json"))
args = parser.parse_args()

# Use parsed arguments
input_h5_path = args.input_h5_path
output_json_path = args.output_json_path

triplet_cols = ["RA", "Dec", "Period", "Eccentricity", "M1", "M1_sin3i", "M2", "M2_sin3i", "q", "Mass Function"]


def class_from_table_path(table_path):
    """Determine object class based on the table file path or name."""
    p = Path(table_path)
    name = p.name.lower()
    full = str(p).lower()

    mapping = {
        'algols.h5': 'Algols',
        'be_sdob_table.h5': 'Hot subdwarfs (d)',
        'bh_table.h5': 'Black Holes (d)',
        'bss_data.h5': 'Blue Straggler Stars',
        'contact1.h5': 'contact binaries',
        'ns_table.h5': 'Neutron star (d)',
        'young_psr_table.h5': 'Neutron star (d)',
        'stripped_star_table.h5': 'Stripped stars (d)'
    }

    # WDMS subdirectory -> White Dwarf (d)
    if 'wdms' in full:
        return 'White Dwarf (d)'

    # Exact filename mapping
    if name in mapping:
        return mapping[name]

    # Any table name containing 'wr' -> Wolf-Rayet
    if 'wr' in name:
        return 'Wolf-Rayet (d)'

    return 'Unclassified'

# === COLLECT FILES ===
list_of_tables = []
for root, dirs, files in os.walk(input_h5_path):
    for file in files:
        if file.endswith(".h5") or file.endswith(".hdf5"):
            list_of_tables.append(os.path.join(root, file))

# === PROCESSING ===
all_systems = []

for n, table_path in enumerate(list_of_tables):
    print(f"Processing table {n+1}/{len(list_of_tables)}: {table_path}")

    try:
        with h5py.File(table_path, "r") as f:
            metadata_json = f["metadata_json"][()].decode("utf-8")
            metadata_df = pd.read_json(StringIO(metadata_json), orient="records")

            for idx in range(len(metadata_df)):
                entry = metadata_df.loc[idx].to_dict()

                for col in triplet_cols:
                    loerr = float(f[col][idx, 0])
                    val   = float(f[col][idx, 1])
                    uperr = float(f[col][idx, 2])
                    # Pre-format the list as a compact string
                    entry[col] = [round(loerr, 5), round(val, 5), round(uperr, 5)]

                # Remove example placeholder systems
                sys_name = entry.get('System Name', '')
                if isinstance(sys_name, str) and 'example' in sys_name.lower():
                    # skip this placeholder/example entry
                    continue

                # Add class information based on the table filename / path
                try:
                    entry['class'] = class_from_table_path(table_path)
                except Exception:
                    entry['class'] = 'Unclassified'

                all_systems.append(entry)

    except Exception as e:
        print(f"Error processing {table_path}: {e}")
        continue

# === OPTIONAL: run duplicate-detection + resolution from check_duplicates.py
try:
    import importlib.util
    cd_path = Path(proj_root) / 'code' / 'data_processing' / 'check_duplicates.py'
    if cd_path.exists():
        spec = importlib.util.spec_from_file_location('check_duplicates', str(cd_path))
        cd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cd)

        # build names and coordinate lists compatible with check_duplicates functions
        names = [entry.get('System Name', f'System_{i}') for i, entry in enumerate(all_systems)]
        ra_vals = cd.extract_column(all_systems, 'RA')
        dec_vals = cd.extract_column(all_systems, 'Dec')

        coords = []
        valid_names = []
        for name, ra, dec in zip(names, ra_vals, dec_vals):
            try:
                if not (np.isnan(ra) or np.isnan(dec)):
                    coords.append(cd.SkyCoord(ra=ra * cd.u.deg, dec=dec * cd.u.deg, frame='icrs'))
                    valid_names.append(name)
            except Exception:
                continue

        overlapping_pairs = []
        if len(coords) > 1:
            all_coords = cd.SkyCoord([c for c in coords])
            sep_matrix = all_coords[:, None].separation(all_coords[None, :]).to(cd.u.arcsec).value
            i_idx, j_idx = np.triu_indices_from(sep_matrix, k=1)
            close_pairs = np.where(sep_matrix[i_idx, j_idx] < cd.threshold.to(cd.u.arcsec).value)[0]
            for idx in close_pairs:
                overlapping_pairs.append((i_idx[idx], j_idx[idx]))

        if overlapping_pairs:
            print(f"Found {len(overlapping_pairs)} overlapping coordinate pairs — resolving duplicates programmatically...")
            try:
                cleaned_catalog, duplicates = cd.resolve_duplicates(all_systems, overlapping_pairs, names, valid_names)
                all_systems = cleaned_catalog
                # optionally write duplicates file
                try:
                    with (Path(output_json_path).parent / 'duplicates.json').open('w') as fdup:
                        json.dump(duplicates, fdup, indent=2)
                    print(f"Wrote {len(duplicates)} duplicates to {Path(output_json_path).parent / 'duplicates.json'}")
                except Exception:
                    pass
            except Exception as e:
                print(f"Error while resolving duplicates: {e}")
    else:
        print('check_duplicates.py not found; skipping duplicate resolution')
except Exception as e:
    print(f"Failed to run duplicate-resolution: {e}")


# === OUTPUT ===
# Dump with indent but ensure compact lists by avoiding advanced encoders
with open(output_json_path, "w") as f_out:
    for system in all_systems:
        # Use json.dumps to serialize each system with compact lists
        json_str = json.dumps(system, separators=(",", ": "), ensure_ascii=False, allow_nan=True)
        f_out.write(json_str + ",\n")  # comma + newline per entry

# Write full file with proper wrapping
with open(output_json_path, "w") as f_out:
    f_out.write("[\n")
    for i, system in enumerate(all_systems):
        json_str = json.dumps(system, separators=(",", ": "), ensure_ascii=False, allow_nan=True)
        f_out.write("  " + json_str)
        if i < len(all_systems) - 1:
            f_out.write(",\n")
        else:
            f_out.write("\n")
    f_out.write("]\n")




print(f"\n All systems written to: {output_json_path}")
