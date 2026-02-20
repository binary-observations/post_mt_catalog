import json
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import paths` finds the top-level paths.py
proj_root = Path('/Users/liekevanson/Documents/Projects/post_mt_review').resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import MAIN_CATALOG, PLOTS_DIR, DOCS_DIR, WRITING_DIR

file_path = MAIN_CATALOG


def read_json_file_topd(file_path, as_dataframe=True):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        # If JSON is a dict of systems → convert to list
        if isinstance(data, dict):
            data = list(data.values())

        if as_dataframe:
            return pd.DataFrame(data)

        return data

    except Exception as e:
        print(f"Error reading file: {e}")
        return None


# Read data
pd_catalog_data = read_json_file_topd(MAIN_CATALOG)

# Print the keys
print(pd_catalog_data.keys())


###########################
# Count systems by class with nice formatting
print(f"Total systems in catalog: {len(pd_catalog_data)}")
print("\n" + "="*60)
print(f"{'System Class':<35} {'Count':>10}")
print("="*60)

# Get counts and sort by frequency (descending)
class_counts = [(cls, sum(pd_catalog_data['system_class'] == cls)) 
                for cls in np.unique(pd_catalog_data['system_class'])]
class_counts.sort(key=lambda x: x[1], reverse=True)

for sys_class, count in class_counts:
    print(f"{sys_class:<35} {count:>10,}")

print("="*60)
print(f"{'TOTAL':<35} {len(pd_catalog_data):>10,}")
print("="*60)


###########################
# Save as LaTeX macros
macros_file = WRITING_DIR / 'system_class_counts_macros.tex'
with open(macros_file, 'w') as f:
    f.write("% Auto-generated system class counts\n")
    f.write(f"\\newcommand{{\\TotalSystems}}{{{len(pd_catalog_data):,}}}\n\n")
    
    for sys_class, count in class_counts:
        # Create macro names like \AstrometricWDMS for "Astrometric WD + MS"
        macro_name = sys_class.replace(' ', '').replace('+', '').replace('-', '')
        f.write(f"\\newcommand{{\\{macro_name}Count}}{{{count:,}}}\n")
    
    all_WD_MS_count = sum(count for sys_class, count in class_counts if 'WD + MS' in sys_class)
    f.write(f"\\newcommand{{\\allWDMS}}{{{all_WD_MS_count:,}}}\n")

print(f"Saved LaTeX macros to: {macros_file}")