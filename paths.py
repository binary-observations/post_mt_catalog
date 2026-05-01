# paths.py
from pathlib import Path
import os

# Get the absolute path to the project root (where this file lives)
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))

# Define key directories
CODE_DIR = PROJECT_ROOT / "code"
DATA_DIR = PROJECT_ROOT / "data"
WRITING_DIR = PROJECT_ROOT / "writing"
LATEX_PLOT_DIR = WRITING_DIR / "figures"
DOCS_DIR = PROJECT_ROOT / "docs"
PLOTS_DIR = PROJECT_ROOT / "plots"

# result tables (h5 files etc.)
RESULT_TABLES = DATA_DIR / "result_tables"
LEGACY_H5_DIR = RESULT_TABLES / "legacy_h5"
RAW_JSON_DIR  = RESULT_TABLES / "raw_json"

# Example: frequently used files
MAIN_CATALOG = DATA_DIR / "post_mt_systems.json"
DUMMY_CATALOG = DATA_DIR / "dummy.json"

# Example: output files
PERIOD_ECC_PLOT = DOCS_DIR / "interactive_period_vs_eccentricity.html"
PERIOD_M2_PLOT = DOCS_DIR / "interactive_period_vs_m2.html"

# Module paths
DATA_ANALYSIS_DIR = CODE_DIR / "data_analysis"
# Ensure data_analysis modules are importable
import sys
if str(DATA_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_ANALYSIS_DIR))

CATEGORY_DICT_PATH = DATA_ANALYSIS_DIR / "Category_dict.py"