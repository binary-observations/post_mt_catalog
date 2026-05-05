"""
P_e_Figures.py — Generate Period-Eccentricity diagrams for the post-main-sequence catalog.

Available figures:
    - plot_p_e_by_system_class(): General P-e diagram colored by system class
    - plot_p_e_2massbins_median(): P-e diagram colored by total mass, with low/high mass bins
    - plot_p_e_by_category_median(): P-e diagram per overarching category with median/percentile tracks

Usage:
    python P_e_Figures.py                    # Generate all figures
    
Or import and call directly:
    from P_e_Figures import plot_p_e_by_system_class, plot_p_e_2massbins_median, plot_p_e_by_category_median
    catalog_df = load_catalog(MAIN_CATALOG)
    fig1, ax1 = plot_p_e_by_system_class(catalog_df, save=True)
    fig2, ax2 = plot_p_e_2massbins_median(catalog_df, save=True)
    fig3, ax3 = plot_p_e_by_category_median(catalog_df, save=True)
"""

import json
import numpy as np
import pandas as pd
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ============================================================================
# Setup: Add project root to path and import custom modules
# ============================================================================
proj_root = Path(__file__).parent.parent.parent.resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import MAIN_CATALOG, PLOTS_DIR, LATEX_PLOT_DIR, DATA_ANALYSIS_DIR

# Add data_analysis to path so Category_dict can be imported
if str(DATA_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_ANALYSIS_DIR))

import importlib
import Category_dict as category_dict
importlib.reload(category_dict)

# Pull the shared plotting dictionaries into module scope so notebook and script
# figures stay visually synchronized.
SYSTEM_CLASS_MAP = category_dict.SYSTEM_CLASS_MAP
STYLE_MAP = category_dict.STYLE_MAP
COLORMAP = category_dict.COLORMAP
SYMBOLMAP = category_dict.SYMBOLMAP
PLOTLY_TO_MPL_MARKER = category_dict.PLOTLY_TO_MPL_MARKER
PAPER_PLOT_RCPARAMS = category_dict.PAPER_PLOT_RCPARAMS
LOW_MASS_CATEGORIES = category_dict.LOW_MASS_CATEGORIES
HIGH_MASS_CATEGORIES = category_dict.HIGH_MASS_CATEGORIES
LOW_MASS_CMAP = category_dict.LOW_MASS_CMAP
HIGH_MASS_CMAP = category_dict.HIGH_MASS_CMAP
darken_color = category_dict.darken_color

# ============================================================================
# Utility Functions
# ============================================================================

def read_json_file(file_path):
    """Load JSON catalog from file."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def extract_triplet_array(data, key):
    """Return an (N,3) float array for the given triplet key, robust to None/NaN."""
    rows = []
    for entry in data:
        val = entry.get(key, None)
        if isinstance(val, (list, tuple, np.ndarray)) and len(val) == 3:
            try:
                # The catalog stores measurements as [err-, value, err+].
                rows.append([
                    np.nan if val[0] is None else float(val[0]),
                    np.nan if val[1] is None else float(val[1]),
                    np.nan if val[2] is None else float(val[2])
                ])
            except (TypeError, ValueError):
                rows.append([np.nan, np.nan, np.nan])
        elif isinstance(val, (int, float)):
            rows.append([np.nan, float(val), np.nan])
        else:
            rows.append([np.nan, np.nan, np.nan])
    return np.array(rows, dtype=float)


def load_catalog(file_path):
    """
    Load the binary catalog and return a pandas DataFrame with key parameters.
    
    Returns:
        pd.DataFrame with columns: System Name, Period, Eccentricity, M1, M2, 
                                   system_class, evol_type_1, evol_type_2, etc.
    """
    data = read_json_file(str(file_path))
    if data is None:
        print("No data loaded. Exiting.")
        return None

    # Only unpack the columns needed by the exported figures.
    period_arr = extract_triplet_array(data, 'Period')
    ecc_arr = extract_triplet_array(data, 'Eccentricity')
    m1_arr = extract_triplet_array(data, 'M1')
    m2_arr = extract_triplet_array(data, 'M2')

    # Build DataFrame with central values and errors
    catalog_df = pd.DataFrame({
        'System Name': [entry.get('System Name', '') for entry in data],
        'Period': period_arr[:, 1],
        'Period_err_minus': period_arr[:, 0],
        'Period_err_plus': period_arr[:, 2],
        'Eccentricity': ecc_arr[:, 1],
        'Eccentricity_err_minus': ecc_arr[:, 0],
        'Eccentricity_err_plus': ecc_arr[:, 2],
        'M1': m1_arr[:, 1],
        'M2': m2_arr[:, 1],
        'system_class': [entry.get('system_class', 'None') for entry in data],
        'evol_type_1': [entry.get('evol_type_1', '') for entry in data],
        'evol_type_2': [entry.get('evol_type_2', '') for entry in data],
    })
    return catalog_df


# ============================================================================
# Figure Generation Functions
# ============================================================================

def plot_p_e_by_system_class(catalog_df=None, save=True):
    """
    Create Period-Eccentricity diagram colored by system class.
    
    Parameters:
    -----------
    catalog_df : pd.DataFrame, optional
        Catalog DataFrame. If None, loads from MAIN_CATALOG.
    save : bool, default=True
        Whether to save the figure to LATEX_PLOT_DIR and PLOTS_DIR.
    
    Returns:
    --------
    fig, ax : matplotlib Figure and Axes objects
    """
    
    if catalog_df is None:
        catalog_df = load_catalog(MAIN_CATALOG)
        if catalog_df is None:
            return None, None
    
    # Set matplotlib style
    plt.rcParams.update(PAPER_PLOT_RCPARAMS)

    fig, ax = plt.subplots(figsize=(12.5, 7))

    plot_df = catalog_df.copy()

    # Keep only rows with valid central values; log-x also requires Period > 0.
    plot_df = plot_df.dropna(subset=['Period', 'Eccentricity']).copy()
    plot_df = plot_df[plot_df['Period'] > 0].copy()

    # Propagate Period errors into log10 space: d(log P) = dP / (P ln 10)
    plot_df['period_err_minus_log'] = plot_df['Period_err_minus'] / (plot_df['Period'] * np.log(10))
    plot_df['period_err_plus_log'] = plot_df['Period_err_plus'] / (plot_df['Period'] * np.log(10))

    # Keep eccentricity errors physical: e - err >= 0 and e + err <= 1
    mask_min = plot_df['Eccentricity'] - plot_df['Eccentricity_err_minus'] < 0
    plot_df.loc[mask_min, 'Eccentricity_err_minus'] = plot_df.loc[mask_min, 'Eccentricity']
    mask_plus = plot_df['Eccentricity'] + plot_df['Eccentricity_err_plus'] > 1
    plot_df.loc[mask_plus, 'Eccentricity_err_plus'] = 1 - plot_df.loc[mask_plus, 'Eccentricity']

    # Missing uncertainties are treated as zero-length error bars
    plot_df['period_err_minus_log'] = plot_df['period_err_minus_log'].fillna(0)
    plot_df['period_err_plus_log'] = plot_df['period_err_plus_log'].fillna(0)
    plot_df['Eccentricity_err_minus'] = plot_df['Eccentricity_err_minus'].fillna(0)
    plot_df['Eccentricity_err_plus'] = plot_df['Eccentricity_err_plus'].fillna(0)

    # Keep error bars physical: no negative period, and eccentricity bounded [0,1].
    mask_pmin = plot_df['Period'] - plot_df['Period_err_minus'] < 0
    plot_df.loc[mask_pmin, 'Period_err_minus'] = plot_df.loc[mask_pmin, 'Period']

    mask_emin = plot_df['Eccentricity'] - plot_df['Eccentricity_err_minus'] < 0
    plot_df.loc[mask_emin, 'Eccentricity_err_minus'] = plot_df.loc[mask_emin, 'Eccentricity']

    mask_eplus = plot_df['Eccentricity'] + plot_df['Eccentricity_err_plus'] > 1
    plot_df.loc[mask_eplus, 'Eccentricity_err_plus'] = 1 - plot_df.loc[mask_eplus, 'Eccentricity']

    # Plot each system class separately so style/legend are per class.
    for system_class in STYLE_MAP.keys():
        sub = plot_df[plot_df['system_class'] == system_class]
        if sub.empty:
            continue
        # Draw WD-containing systems behind the rest so sparse high-mass systems
        # remain visible on top.
        Zord = 3 if 'WD' not in system_class else 0

        color = COLORMAP.get(system_class, '#666666')
        marker_plotly = SYMBOLMAP.get(system_class, 'circle')
        marker_mpl = PLOTLY_TO_MPL_MARKER.get(marker_plotly, 'o')

        ax.errorbar(np.log10(sub['Period']), sub['Eccentricity'],
            xerr=[sub['period_err_minus_log'], sub['period_err_plus_log']],
            yerr=[sub['Eccentricity_err_minus'], sub['Eccentricity_err_plus']],
            fmt=marker_mpl, ms=7 if marker_mpl in ['+', 'x'] else 6,
            color=color, ecolor=color,
            elinewidth=1, capsize=0,
            alpha=0.9 if marker_mpl in ['+', 'x'] else 0.8,
            linestyle='none', zorder=Zord,
            label=f"{system_class} ({len(sub)})"
        )

    # Write x ticks not in log space but in days
    xticks = [0.01, 0.1, 1, 10, 100, 1000, 10000]
    xtick_labels = ['0.01', '0.1', '1', '10', '100', '1000', '$10^4$']
    plt.xticks(np.log10(xticks), xtick_labels, fontsize=20)

    ax.set_xlim(-2, 4.5)
    ax.set_ylim(-0.05, 1)
    ax.tick_params(axis='both', labelsize=16)
    ax.set_xlabel('$\mathrm{Orbital\,Period\,(days)}$', fontsize=24)
    ax.set_ylabel('$\mathrm{Eccentricity}$', fontsize=24)
    ax.legend(bbox_to_anchor=(1, 1.05), loc='upper left', fontsize=15, framealpha=0., ncol=1)
    plt.tight_layout()

    if save:
        plt.savefig(LATEX_PLOT_DIR / 'P_e_by_system_class.pdf')
        plt.savefig(PLOTS_DIR / 'P_e_by_system_class.pdf')
        print(f"Saved to {LATEX_PLOT_DIR / 'P_e_by_system_class.pdf'}")
        print(f"Saved to {PLOTS_DIR / 'P_e_by_system_class.pdf'}")

    return fig, ax

def plot_p_e_2massbins_median(catalog_df=None, save=True):
    """
    Create Period-Eccentricity diagram colored by total mass, with low/high mass bins.
    
    Shows P-e distribution split into low-mass and high-mass donor systems,
    with separate colormaps for each bin and median trends overlaid.
    
    Parameters:
    -----------
    catalog_df : pd.DataFrame, optional
        Catalog DataFrame. If None, loads from MAIN_CATALOG.
    save : bool, default=True
        Whether to save the figure to LATEX_PLOT_DIR and PLOTS_DIR.
    
    Returns:
    --------
    fig, ax : matplotlib Figure and Axes objects
    """
    
    if catalog_df is None:
        catalog_df = load_catalog(MAIN_CATALOG)
        if catalog_df is None:
            return None, None
    
    # Set matplotlib style
    plt.rcParams.update(PAPER_PLOT_RCPARAMS)

    fig, ax = plt.subplots(figsize=(10, 6.8))

    plot_df = catalog_df.copy()
    plot_df = plot_df[plot_df['Period'] > 0].copy()
    plot_df['log_Period'] = np.log10(plot_df['Period'])
    plot_df['Mtot'] = plot_df['M1'] + plot_df['M2']

    # Prepare uncertainty columns for error bars
    plot_df['period_err_minus_log'] = plot_df['Period_err_minus'] / (plot_df['Period'] * np.log(10))
    plot_df['period_err_plus_log'] = plot_df['Period_err_plus'] / (plot_df['Period'] * np.log(10))

    # Keep eccentricity errors physical
    mask_min = plot_df['Eccentricity'] - plot_df['Eccentricity_err_minus'] < 0
    plot_df.loc[mask_min, 'Eccentricity_err_minus'] = plot_df.loc[mask_min, 'Eccentricity']
    mask_plus = plot_df['Eccentricity'] + plot_df['Eccentricity_err_plus'] > 1
    plot_df.loc[mask_plus, 'Eccentricity_err_plus'] = 1 - plot_df.loc[mask_plus, 'Eccentricity']

    plot_df['period_err_minus_log'] = plot_df['period_err_minus_log'].fillna(0)
    plot_df['period_err_plus_log'] = plot_df['period_err_plus_log'].fillna(0)
    plot_df['Eccentricity_err_minus'] = plot_df['Eccentricity_err_minus'].fillna(0)
    plot_df['Eccentricity_err_plus'] = plot_df['Eccentricity_err_plus'].fillna(0)

    # Use the top-level science categories as a proxy for low- vs high-mass donor populations.
    low_mass_classes = set()
    for cat in LOW_MASS_CATEGORIES:
        if cat in SYSTEM_CLASS_MAP:
            low_mass_classes |= set(SYSTEM_CLASS_MAP[cat].keys())

    high_mass_classes = set()
    for cat in HIGH_MASS_CATEGORIES:
        if cat in SYSTEM_CLASS_MAP:
            high_mass_classes |= set(SYSTEM_CLASS_MAP[cat].keys())

    # Assign mass bins
    plot_df = plot_df.dropna(subset=['log_Period', 'Eccentricity']).copy()
    plot_df['mass_bin'] = np.where(
        plot_df['system_class'].isin(low_mass_classes),
        'Low-mass systems',
        np.where(plot_df['system_class'].isin(high_mass_classes), 'High-mass systems', 'Unclassified')
    )
    plot_df = plot_df[plot_df['mass_bin'] != 'Unclassified'].copy()

    # Build separate colormaps
    low_mass_cmap = LOW_MASS_CMAP
    high_mass_cmap = HIGH_MASS_CMAP

    # Unknown total masses are kept as separate marker styles so they still contribute
    # to the morphology without being assigned an arbitrary color on the mass scale.
    low_known = plot_df[(plot_df['mass_bin'] == 'Low-mass systems') & plot_df['Mtot'].notna()].copy()
    low_unknown = plot_df[(plot_df['mass_bin'] == 'Low-mass systems') & plot_df['Mtot'].isna()].copy()
    high_known = plot_df[(plot_df['mass_bin'] == 'High-mass systems') & plot_df['Mtot'].notna()].copy()
    high_unknown = plot_df[(plot_df['mass_bin'] == 'High-mass systems') & plot_df['Mtot'].isna()].copy()

    # Fix the colorbar ranges so regenerated figures remain comparable across catalog updates.
    from matplotlib.colors import Normalize
    low_norm = Normalize(vmin=0.3, vmax=5.0)
    high_norm = Normalize(vmin=1.3, vmax=20.0)

    # Plot known-mass points colored by Mtot
    first_low_label = True
    for _, row in low_known.iterrows():
        color = low_mass_cmap(low_norm(row['Mtot']))
        ax.errorbar(
            row['log_Period'], row['Eccentricity'],
            xerr=[[row['period_err_minus_log']], [row['period_err_plus_log']]],
            yerr=[[row['Eccentricity_err_minus']], [row['Eccentricity_err_plus']]],
            fmt='o', ms=5, color=color, ecolor=color, elinewidth=1, capsize=0,
            alpha=0.9, zorder=3,
            label='Low-mass systems' if first_low_label else None
        )
        first_low_label = False

    for _, row in low_unknown.iterrows():
        ax.errorbar(
            row['log_Period'], row['Eccentricity'],
            xerr=[[row['period_err_minus_log']], [row['period_err_plus_log']]],
            yerr=[[row['Eccentricity_err_minus']], [row['Eccentricity_err_plus']]],
            fmt='x', ms=5, color='#829ebc', ecolor='#829ebc', elinewidth=1, capsize=0,
            alpha=0.9, zorder=3
        )

    first_high_label = True
    for _, row in high_known.iterrows():
        color = high_mass_cmap(high_norm(row['Mtot']))
        ax.errorbar(
            row['log_Period'], row['Eccentricity'],
            xerr=[[row['period_err_minus_log']], [row['period_err_plus_log']]],
            yerr=[[row['Eccentricity_err_minus']], [row['Eccentricity_err_plus']]],
            fmt='o', ms=5, color=color, ecolor=color, elinewidth=1, capsize=0,
            alpha=0.9, zorder=3,
            label='High-mass systems' if first_high_label else None
        )
        first_high_label = False

    for _, row in high_unknown.iterrows():
        ax.errorbar(
            row['log_Period'], row['Eccentricity'],
            xerr=[[row['period_err_minus_log']], [row['period_err_plus_log']]],
            yerr=[[row['Eccentricity_err_minus']], [row['Eccentricity_err_plus']]],
            fmt='x', ms=5, color='#dbccbc', ecolor='#dbccbc', elinewidth=1, capsize=0,
            alpha=0.9, zorder=3
        )

    # Summarize each mass bin with a median track and a broad central envelope.
    median_styles = {
        'Low-mass systems': {'color': '#1f4e79', 'label': 'Low-mass median'},
        'High-mass systems': {'color': '#e37601', 'label': 'High-mass median'},
    }
    P_bins = np.linspace(-1, 4, 7)
    x_stats = P_bins[:-1] + 0.5 * np.diff(P_bins)
    N_in_class = []

    for mass_bin, style in median_styles.items():
        subset = plot_df[plot_df['mass_bin'] == mass_bin].copy()
        subset['P_bin'] = pd.cut(subset['log_Period'], bins=P_bins)
        
        counts_by_bin = subset['P_bin'].value_counts(sort=False, dropna=False)
        N_in_class.append(sum(counts_by_bin))

        stats = subset.groupby('P_bin', observed=False)['Eccentricity'].quantile([0.05, 0.5, 0.95]).unstack()
        stats.columns = ['p05', 'median', 'p95']

        ax.plot(x_stats, stats['median'].values, lw=2.5, c=style['color'], label=style['label'], zorder=4)
        ax.plot(x_stats, stats['p05'].values, lw=2, ls='--', c=style['color'], zorder=4)
        ax.plot(x_stats, stats['p95'].values, lw=2, ls='--', c=style['color'], zorder=4)

    # Add colorbars
    fig.subplots_adjust(right=0.78)
    cax_low = fig.add_axes([0.81, 0.14, 0.015, 0.72])
    cax_high = fig.add_axes([0.92, 0.14, 0.015, 0.72])

    sm_low = plt.cm.ScalarMappable(cmap=low_mass_cmap, norm=low_norm)
    sm_low.set_array([])
    cbar_low = fig.colorbar(sm_low, cax=cax_low)
    cbar_low.set_label('total mass, low-M donor (M$_\\odot$)', fontsize=16)

    sm_high = plt.cm.ScalarMappable(cmap=high_mass_cmap, norm=high_norm)
    sm_high.set_array([])
    cbar_high = fig.colorbar(sm_high, cax=cax_high)
    cbar_high.set_label('total mass, high-M donor (M$_\\odot$)', fontsize=16)

    # Format axes
    xticks = [0.01, 0.1, 1, 10, 100, 1000, 10000]
    xtick_labels = ['0.01', '0.1', '1', '10', '100', '1000', '$10^4$']
    ax.set_xticks(np.log10(xticks))
    ax.set_xticklabels(xtick_labels, fontsize=20)

    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([0], [0], marker='o', linestyle='None', color='#4c78a8', markersize=6,
               label=f"Low-M donor ({N_in_class[0]}): \nWD binary, \nLow-M stripped\n"),
        Line2D([0], [0], marker='o', linestyle='None', color='#e37601', markersize=6,
               label=f"High-M donor ({N_in_class[1]}): \nOngoing RLOF, \nHigh-M stripped, \nCO binary"),
    ]
    legend = ax.legend(handles=legend_handles, fontsize=16, loc='upper left', 
                      bbox_to_anchor=(0.0, 1), framealpha=0.1)
    legend.get_texts()[0].set_color('#4c78a8')
    legend.get_texts()[1].set_color('#e37601')

    ax.set_xlim(-2, 4.5)
    ax.set_ylim(-0.05, 1)
    ax.tick_params(axis='x', labelsize=20)
    ax.set_xlabel('$\mathrm{Orbital \, Period \ (days)}$', fontsize=28)
    ax.set_ylabel('$\\mathrm{Eccentricity}$', fontsize=28)

    if save:
        plt.savefig(LATEX_PLOT_DIR / 'P_e_diagram_2massbins_median.pdf', bbox_inches='tight')
        plt.savefig(PLOTS_DIR / 'P_e_diagram_2massbins_median.pdf', bbox_inches='tight')
        print(f"Saved to {LATEX_PLOT_DIR / 'P_e_diagram_2massbins_median.pdf'}")
        print(f"Saved to {PLOTS_DIR / 'P_e_diagram_2massbins_median.pdf'}")

    return fig, ax


def plot_p_e_by_category_median(catalog_df=None, save=True):
    """
    Create Period-Eccentricity diagram per overarching category with median and
    5–95 percentile tracks overlaid.

    Categories plotted: WD binary, Ongoing RLOF, Low-M stripped stars,
    High-M stripped stars, CO binary.

    Parameters:
    -----------
    catalog_df : pd.DataFrame, optional
        Catalog DataFrame. If None, loads from MAIN_CATALOG.
    save : bool, default=True
        Whether to save the figure to LATEX_PLOT_DIR and PLOTS_DIR.

    Returns:
    --------
    fig, ax : matplotlib Figure and Axes objects
    """

    if catalog_df is None:
        catalog_df = load_catalog(MAIN_CATALOG)
        if catalog_df is None:
            return None, None

    plt.rcParams.update(PAPER_PLOT_RCPARAMS)

    fig, ax = plt.subplots(figsize=(9, 7))

    plot_df = catalog_df.copy()
    plot_df['log_Period'] = np.log10(plot_df['Period'])

    # Propagate errors for logP: d(log P) = 1/ln(10) * dP / P
    plot_df['period_err_minus_log'] = plot_df['Period_err_minus'] / (plot_df['Period'] * np.log(10))
    plot_df['period_err_plus_log'] = plot_df['Period_err_plus'] / (plot_df['Period'] * np.log(10))

    # Keep eccentricity errors physical
    mask_min = plot_df['Eccentricity'] - plot_df['Eccentricity_err_minus'] < 0
    plot_df.loc[mask_min, 'Eccentricity_err_minus'] = plot_df.loc[mask_min, 'Eccentricity']
    mask_plus = plot_df['Eccentricity'] + plot_df['Eccentricity_err_plus'] > 1
    plot_df.loc[mask_plus, 'Eccentricity_err_plus'] = 1 - plot_df.loc[mask_plus, 'Eccentricity']

    plot_df['period_err_minus_log'] = plot_df['period_err_minus_log'].fillna(0)
    plot_df['period_err_plus_log'] = plot_df['period_err_plus_log'].fillna(0)
    plot_df['Eccentricity_err_minus'] = plot_df['Eccentricity_err_minus'].fillna(0)
    plot_df['Eccentricity_err_plus'] = plot_df['Eccentricity_err_plus'].fillna(0)

    # Map display category names to one or more source categories in SYSTEM_CLASS_MAP
    plot_category_map = {
        'WD binary': ['WD binary'],
        'Ongoing RLOF': ['Ongoing RLOF'],
        'Low-M stripped stars': ['Low-M stripped'],
        'High-M stripped stars': ['High-M stripped'],
        'CO binary': ['CO binary'],
    }

    P_bins = np.linspace(-1, 4, 7)
    x_stats = P_bins[:-1] + 0.5 * np.diff(P_bins)

    for category, source_categories in plot_category_map.items():
        zorder = 1

        system_classes_in_category = []
        for src_category in source_categories:
            system_classes_in_category.extend(list(SYSTEM_CLASS_MAP[src_category].keys()))

        if source_categories[0] == 'Ongoing RLOF':
            zorder += 1

        subset = plot_df[plot_df['system_class'].isin(system_classes_in_category)].copy()

        # Use first color of the first source category as the representative color
        first_source = source_categories[0]
        first_system_color = list(SYSTEM_CLASS_MAP[first_source].values())[0]['color']
        if category == 'WD binary':
            first_system_color = list(SYSTEM_CLASS_MAP['WD binary'].values())[-1]['color']

        ax.errorbar(
            subset['log_Period'], subset['Eccentricity'],
            xerr=[subset['period_err_minus_log'], subset['period_err_plus_log']],
            yerr=[subset['Eccentricity_err_minus'].fillna(0), subset['Eccentricity_err_plus'].fillna(0)],
            fmt='o', c=first_system_color, alpha=0.6, zorder=1,
            label=f"{category} ({subset.shape[0]})"
        )

        subset['P_bin'] = pd.cut(subset['log_Period'], bins=P_bins)
        stats = subset.groupby('P_bin', observed=False)['Eccentricity'].quantile([0.05, 0.5, 0.95]).unstack()
        stats.columns = ['p05', 'median', 'p95']

        ax.plot(x_stats, stats['median'].values,
                lw=3, c=darken_color(first_system_color, factor=0.8), zorder=2 + zorder)
        ax.fill_between(x_stats, stats['p05'].values, stats['p95'].values,
                        color=darken_color(first_system_color, factor=0.8), alpha=0.1,
                        step='mid', zorder=-1)

    xticks = [0.01, 0.1, 1, 10, 100, 1000, 10000]
    xtick_labels = ['0.01', '0.1', '1', '10', '100', '1000', '$10^4$']
    ax.set_xticks(np.log10(xticks))
    ax.set_xticklabels(xtick_labels, fontsize=20)

    ax.set_xlim(-2, 4.5)
    ax.set_ylim(-0.05, 1)
    ax.tick_params(axis='both', labelsize=20)
    ax.set_xlabel('$\mathrm{Orbital\,Period \ (days)}$', fontsize=25)
    ax.set_ylabel('$\mathrm{Eccentricity}$', fontsize=25)
    ax.legend(loc='upper left', fontsize=18, framealpha=0.5)
    plt.tight_layout()

    if save:
        plt.savefig(LATEX_PLOT_DIR / 'P_e_by_category_median.pdf')
        plt.savefig(PLOTS_DIR / 'P_e_by_category_median.pdf')
        print(f"Saved to {LATEX_PLOT_DIR / 'P_e_by_category_median.pdf'}")
        print(f"Saved to {PLOTS_DIR / 'P_e_by_category_median.pdf'}")

    return fig, ax


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    print(f"Loading catalog from {MAIN_CATALOG}")
    catalog_df = load_catalog(MAIN_CATALOG)
    
    if catalog_df is not None:
        print(f"Loaded {len(catalog_df)} systems")
        
        print("\nGenerating P-e diagram by system class...")
        fig1, ax1 = plot_p_e_by_system_class(catalog_df, save=True)
        
        print("\nGenerating P-e diagram with 2 mass bins and medians...")
        fig2, ax2 = plot_p_e_2massbins_median(catalog_df, save=True)
        
        print("\nGenerating P-e diagram by category with medians...")
        fig3, ax3 = plot_p_e_by_category_median(catalog_df, save=True)
        
        plt.show()
    else:
        print("Failed to load catalog.")
