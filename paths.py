# paths.py
import os

# Get the absolute path to the project root (where this file lives)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Define key directories
CODE_DIR = os.path.join(PROJECT_ROOT, "code")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
WRITING_DIR = os.path.join(PROJECT_ROOT, "writing")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
PLOTS_DIR = os.path.join(PROJECT_ROOT, "plots")

# Example: frequently used files
MAIN_CATALOG = os.path.join(DATA_DIR, "post_mt_systems.json")
DUMMY_CATALOG = os.path.join(DATA_DIR, "dummy.json")

# Example: output files
PERIOD_ECC_PLOT = os.path.join(DOCS_DIR, "interactive_period_vs_eccentricity.html")
PERIOD_M2_PLOT = os.path.join(DOCS_DIR, "interactive_period_vs_m2.html")

