import json
import numpy as np
from pathlib import Path
from paths import MAIN_CATALOG, DATA_DIR, PLOTS_DIR # central paths
from astropy.coordinates import SkyCoord
import astropy.units as u
import matplotlib.pyplot as plt

################################################################################
# === USER INPUT Constants ===
threshold = 0.1 * u.arcsec


################################################################################
# === Helper Functions ===
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


def plot_catalog_on_sky(catalog=None, coords_list=None, names=None, annotate=False, save_path=None, figsize=(8, 6)):
    """Plot catalog sources on the sky.

    Provide either `catalog` (list of dicts with RA/Dec triplets) or `coords_list` (list of astropy.coordinates.SkyCoord).
    - names: optional list of labels to annotate points (used when coords_list supplied)
    - annotate: boolean, whether to draw text labels next to points
    - save_path: optional path to save the figure; if None the figure is shown
    """
    # Build coords and names from catalog if needed
    if coords_list is None:
        if catalog is None:
            raise ValueError('Either catalog or coords_list must be provided')
        ra_vals = extract_column(catalog, 'RA')
        dec_vals = extract_column(catalog, 'Dec')
        coords = []
        names = [] if names is None else list(names)
        for entry, ra, dec in zip(catalog, ra_vals, dec_vals):
            if ra is None or dec is None:
                continue
            try:
                if np.isnan(ra) or np.isnan(dec):
                    continue
            except Exception:
                pass
            coords.append(SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame='icrs'))
            if names is not None:
                names.append(entry.get('System Name', ''))
    else:
        coords = list(coords_list)

    if len(coords) == 0:
        print('No valid coordinates to plot.')
        return

    ras = np.array([c.ra.deg for c in coords])
    decs = np.array([c.dec.deg for c in coords])

    fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(ras, decs, s=3, alpha=0.8, marker ='o',facecolors='none', edgecolors='blue', linewidth=0.5)
    ax.set_xlabel('RA (deg)')
    ax.set_ylabel('Dec (deg)')
    ax.set_title('Catalog sources (RA / Dec)')
    # In astronomy plots RA is often shown increasing to the left
    ax.invert_xaxis()

    if annotate and names:
        for x, y, txt in zip(ras, decs, names):
            ax.text(x, y, str(txt), fontsize=6, alpha=0.9)

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(save_path), dpi=500, bbox_inches='tight')
        print(f'Saved sky plot to {save_path}')
    else:
        plt.show()

    plt.close(fig)


# Function to resolve duplicate entries in the catalog
def resolve_duplicates(data, overlapping_pairs, names, valid_names):
    """ Resolve the duplicates
    If user has confirmed a system as duplicate we will merge them:
    System Name should become a list of both names
    first preference goes to 'best mass measured entry'
    move the losing entry to a duplicates json file. 
    
    Args:
        data (list): list of dictionaries, each representing a system
        overlapping_pairs (list): list of tuples, each containing the indices of the overlapping systems
        names (list): list of system names
        valid_names (list): list of valid system names

    Returns:
        cleaned_catalog (list): list of dictionaries, each representing a system
        duplicates (list): list of dictionaries, each representing a duplicate system
    """
    # Track which indices have already been merged
    merged_indices = set()
    cleaned_catalog = data.copy()
    duplicates = []

    for i, j in overlapping_pairs:
        idx1, idx2 = names.index(valid_names[i]), names.index(valid_names[j])
        if idx1 in merged_indices or idx2 in merged_indices:
            continue  # Already merged in a previous step
        entry1, entry2 = data[idx1], data[idx2]

        # Helper to compute mass precision (smaller error = more precise)
        def mass_precision(entry):
            m1 = entry.get("M1", [np.nan, np.nan, np.nan])
            m2 = entry.get("M2", [np.nan, np.nan, np.nan])
            m1_err = m1[2] if isinstance(m1, list) and len(m1) == 3 else np.nan
            m2_err = m2[2] if isinstance(m2, list) and len(m2) == 3 else np.nan
            return np.nansum([m1_err, m2_err])

        # Prefer entry with smaller total mass error
        if mass_precision(entry1) <= mass_precision(entry2):
            keep, drop = entry1, entry2
            keep_idx, drop_idx = idx1, idx2
        else:
            keep, drop = entry2, entry1
            keep_idx, drop_idx = idx2, idx1

        # Merge names as a list
        merged_names = list({
            *(keep["System Name"] if isinstance(keep["System Name"], list) else [keep["System Name"]]),
            *(drop["System Name"] if isinstance(drop["System Name"], list) else [drop["System Name"]])
        })
        keep["System Name"] = merged_names

        # Update the catalog and mark as merged
        cleaned_catalog[keep_idx] = keep
        merged_indices.add(drop_idx)
        duplicates.append(drop)

    # Remove dropped entries from cleaned_catalog
    cleaned_catalog = [entry for idx, entry in enumerate(cleaned_catalog) if idx not in merged_indices]
    return cleaned_catalog, duplicates


def resolve_duplicate_pair(entry1, entry2):
    def mass_precision(entry):
        m1 = entry.get("M1", [np.nan, np.nan, np.nan])
        m2 = entry.get("M2", [np.nan, np.nan, np.nan])
        m1_err = m1[2] if isinstance(m1, list) and len(m1) == 3 else np.nan
        m2_err = m2[2] if isinstance(m2, list) and len(m2) == 3 else np.nan
        return np.nansum([m1_err, m2_err])
    if mass_precision(entry1) <= mass_precision(entry2):
        keep, drop = entry1, entry2
    else:
        keep, drop = entry2, entry1
    merged_names = list({
        *(keep["System Name"] if isinstance(keep["System Name"], list) else [keep["System Name"]]),
        *(drop["System Name"] if isinstance(drop["System Name"], list) else [drop["System Name"]])
    })
    keep["System Name"] = merged_names
    return keep, drop

################################################################################
# === Main ===

# === STEP 1: load and prep data ===
# open the json file with main catalog
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

# === STEP 2: use astropy to find overlapping locations ===
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


# === STEP 3: compare P, M1, and M2 for overlapping systems ===
duplicates = []
cleaned_catalog = data.copy() # work on a copy of the data
merged_names_set = set()

if overlapping_pairs:
    print("\nComparing Period, M1, and M2 for overlapping systems:")
    for pair_num, (i, j) in enumerate(overlapping_pairs):
        name1, name2 = valid_names[i], valid_names[j]
        idx1, idx2 = names.index(name1), names.index(name2)
        # Skip if already merged
        if name1 in merged_names_set or name2 in merged_names_set:
            continue
        entry1, entry2 = cleaned_catalog[idx1], cleaned_catalog[idx2]
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

        print(f"\n {pair_num} out of {len(overlapping_pairs)} {name1} vs {name2}:")
        print(f"  Period: {period1} vs {period2} (diff: {percent_diff(period1, period2)})")
        print(f"  M1: {m1_1} vs {m1_2} (diff: {percent_diff(m1_1, m1_2)})")
        print(f"  M2: {m2_1} vs {m2_2} (diff: {percent_diff(m2_1, m2_2)})")
        
        # Ask user to confirm duplicate pair, and merge if so
        user_input = input("Merge these as duplicates? (y/n): ").strip().lower()
        if user_input == "y":
            keep, drop = resolve_duplicate_pair(entry1, entry2)
            cleaned_catalog[idx1] = keep
            cleaned_catalog[idx2] = None  # Mark for removal
            duplicates.append(drop)
            merged_names_set.update(keep["System Name"] if isinstance(keep["System Name"], list) else [keep["System Name"]])
            merged_names_set.update(drop["System Name"] if isinstance(drop["System Name"], list) else [drop["System Name"]])

    # Remove None entries
    cleaned_catalog = [entry for entry in cleaned_catalog if entry is not None]
    # Write duplicates to a new JSON file
    with (DATA_DIR / 'duplicates.json').open('w') as f:
        json.dump(duplicates, f, indent=2)
    print(f"\nResolved duplicates. {len(duplicates)} entries written to {DATA_DIR / 'duplicates.json'}.")
    with (DATA_DIR / 'cleaned_catalog.json').open('w') as f:
        json.dump(cleaned_catalog, f, indent=2)
    print(f"Updated catalog written to {DATA_DIR}/ 'cleaned_catalog.json'.")


# === STEP 4: Optional plot the systems on the sky ===
p = Path('data') / 'post_mt_systems.json'
print(f"Reading catalog: {p.resolve()}")
data = read_json_file(p)

plot_catalog_on_sky(catalog=data, save_path=Path('plots') / 'sky_locations.pdf', annotate=False)
print(f"Saved plot to {Path('plots') / 'sky_locations.pdf'}")



################################################################################
# === Main ===
if __name__ == "__main__":
    main()









