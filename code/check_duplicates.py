import json
import numpy as np
import sys
sys.path.append('/Users/lvanson/Documents/Projects/post_mt_review')
from paths import MAIN_CATALOG # is "../data/post_mt_systems.json"  # or dummy.json
from astropy.coordinates import SkyCoord
import astropy.units as u

# === Constants ===
threshold = 1.0 * u.arcsec

# === Functions ===
def read_json_file(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def extract_central_value(entry, key):
    # Expects [err-, value, err+], returns value or np.nan
    val = entry.get(key, [np.nan, np.nan, np.nan])
    if isinstance(val, list) and len(val) == 3:
        return val[1]
    elif isinstance(val, (int, float)):
        return val
    else:
        return np.nan
def extract_column(data, key):
    return [extract_central_value(entry, key) for entry in data]



################################################################################
# === Main ===
# def main():
# open the json file
data = read_json_file(MAIN_CATALOG)
if data is None:
    print("No data loaded. Exiting.")
    exit(1)


# Extract system names and coordinates
names = [entry.get("System Name", f"System_{i}") for i, entry in enumerate(data)]
ra_vals = extract_column(data, "RA")
dec_vals = extract_column(data, "Dec")

# Create SkyCoord objects (skip NaNs)
coords = []
valid_names = []
for name, ra, dec in zip(names, ra_vals, dec_vals):
    if not (np.isnan(ra) or np.isnan(dec)):
        coords.append(SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs'))
        valid_names.append(name)

# Find overlapping pairs and store them
overlapping_pairs = []
if len(coords) > 1:
    all_coords = SkyCoord([c for c in coords])
    sep_matrix = all_coords[:, None].separation(all_coords[None, :]).to(u.arcsec).value
    i_idx, j_idx = np.triu_indices_from(sep_matrix, k=1)
    close_pairs = np.where(sep_matrix[i_idx, j_idx] < threshold.to(u.arcsec).value)[0]

    print(f"\nPairs of systems within {threshold}:")
    for idx in close_pairs:
        i = i_idx[idx]
        j = j_idx[idx]
        print(f"  {valid_names[i]} <-> {valid_names[j]}: separation = {sep_matrix[i, j]:.3f} arcsec")
        overlapping_pairs.append((i, j))
else:
    print("Not enough valid coordinates to compare.")

# For each overlapping pair, compare Period, M1, and M2
if overlapping_pairs:
    print("\nComparing Period, M1, and M2 for overlapping systems:")
    for i, j in overlapping_pairs:
        name1, name2 = valid_names[i], valid_names[j]
        entry1, entry2 = data[names.index(name1)], data[names.index(name2)]
        period1, period2 = extract_central_value(entry1, "Period"), extract_central_value(entry2, "Period")
        m1_1, m1_2 = extract_central_value(entry1, "M1"), extract_central_value(entry2, "M1")
        m2_1, m2_2 = extract_central_value(entry1, "M2"), extract_central_value(entry2, "M2")

        def percent_diff(a, b):
            if np.isnan(a) or np.isnan(b):
                return 'NaN'
            if a == b == 0:
                return '0%'
            try:
                return f"{100 * abs(a - b) / np.mean([abs(a), abs(b)]):.2f}%"
            except ZeroDivisionError:
                return 'inf%'

        print(f"\n{name1} vs {name2}:")
        print(f"  Period: {period1} vs {period2} (diff: {percent_diff(period1, period2)})")
        print(f"  M1: {m1_1} vs {m1_2} (diff: {percent_diff(m1_1, m1_2)})")
        print(f"  M2: {m2_1} vs {m2_2} (diff: {percent_diff(m2_1, m2_2)})")


# Resolve the duplicates
# If user has defined this system as duplicate we will merge them:
# System Name should become a list of both names
# It think we care about the masses so first preference goes to 


################################################################################
# === Main ===
if __name__ == "__main__":
    main()









