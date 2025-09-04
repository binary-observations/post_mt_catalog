import pandas as pd
import h5py
import json
from io import StringIO
import os
import argparse
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

                all_systems.append(entry)

    except Exception as e:
        print(f"Error processing {table_path}: {e}")
        continue

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
