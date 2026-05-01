# Brief script to call the plotting functions for all paper figures.
import sys
from pathlib import Path
import matplotlib.pyplot as plt


# Make the project root importable when this file is run directly.
proj_root = Path(__file__).parent.parent.parent.resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import DATA_ANALYSIS_DIR, MAIN_CATALOG

if str(DATA_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_ANALYSIS_DIR))

# Reuse the most complete catalog loader so all figures work off the same dataframe.
from P_e_Figures import load_catalog as load_pe_catalog, plot_p_e_by_system_class, plot_p_e_2massbins_median
from P_dist_Figure import load_catalog as load_period_catalog, plot_period_distribution_by_category
from mass_ratio_Figure import load_catalog as load_mass_catalog, plot_m1_m2_log_by_category


if __name__ == "__main__":
    pe_catalog_df = load_pe_catalog(MAIN_CATALOG)
    period_catalog_df = load_period_catalog(MAIN_CATALOG)
    mass_catalog_df = load_mass_catalog(MAIN_CATALOG)

    if pe_catalog_df is None or period_catalog_df is None or mass_catalog_df is None:
        raise SystemExit("Failed to load one or more plotting catalogs.")

    print(f"Loaded {len(pe_catalog_df)} systems")

    print("Generating P-e diagram by system class...")
    plot_p_e_by_system_class(pe_catalog_df, save=True)

    print("Generating P-e diagram with two mass bins...")
    plot_p_e_2massbins_median(pe_catalog_df, save=True)

    print("Generating period distribution by category...")
    plot_period_distribution_by_category(period_catalog_df, save=True)

    print("Generating log-scale M1 vs M2 diagram...")
    plot_m1_m2_log_by_category(mass_catalog_df, save=True)

    plt.show()
