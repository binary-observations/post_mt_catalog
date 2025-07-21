# paths.py
from pathlib import Path
import os

# Get the absolute path to the project root (where this file lives)
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))

# Define key directories
CODE_DIR = PROJECT_ROOT / "code"
DATA_DIR = PROJECT_ROOT / "data"
WRITING_DIR = PROJECT_ROOT / "writing"
DOCS_DIR = PROJECT_ROOT / "docs"
PLOTS_DIR = PROJECT_ROOT / "plots"

# Example: frequently used files
MAIN_CATALOG = DATA_DIR / "post_mt_systems.json"
DUMMY_CATALOG = DATA_DIR / "dummy.json"

# Example: output files
PERIOD_ECC_PLOT = DOCS_DIR / "interactive_period_vs_eccentricity.html"
PERIOD_M2_PLOT = DOCS_DIR / "interactive_period_vs_m2.html"

