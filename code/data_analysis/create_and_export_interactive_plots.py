import json
import numpy as np
import pandas as pd
import plotly.express as px
import matplotlib.colors as mcolors

# Ensure project root is on sys.path so `import paths` finds the top-level paths.py
import os, sys
from pathlib import Path
proj_root = Path('/Users/liekevanson/Documents/Projects/post_mt_review').resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import MAIN_CATALOG, DOCS_DIR, PLOTS_DIR
file_path = MAIN_CATALOG


def read_json_file(file_path):
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
                rows.append([float(val[0]), float(val[1]), float(val[2])])
            except Exception:
                rows.append([np.nan, np.nan, np.nan])
        elif isinstance(val, (int, float)):
            # Scalar provided → treat as central value with unknown errors
            rows.append([np.nan, float(val), np.nan])
        else:
            rows.append([np.nan, np.nan, np.nan])
    return np.array(rows, dtype=float)


# Read data
data = read_json_file(str(file_path))
if data is None:
    print("No data loaded. Exiting.")
    exit(1)

# Extract triplet columns once for efficiency/consistency
period_arr = extract_triplet_array(data, 'Period')
ecc_arr = extract_triplet_array(data, 'Eccentricity')
m1_arr = extract_triplet_array(data, 'M1')
m2_arr = extract_triplet_array(data, 'M2')

# Build a single DataFrame with central values and errors
df = pd.DataFrame({
    'Period': period_arr[:, 1],
    'Period_err_minus': period_arr[:, 0],
    'Period_err_plus': period_arr[:, 2],
    'Eccentricity': ecc_arr[:, 1],
    'Eccentricity_err_minus': ecc_arr[:, 0],
    'Eccentricity_err_plus': ecc_arr[:, 2],
    'M1': m1_arr[:, 1],
    'M1_err_minus': m1_arr[:, 0],
    'M1_err_plus': m1_arr[:, 2],
    'M2': m2_arr[:, 1],
    'M2_err_minus': m2_arr[:, 0],
    'M2_err_plus': m2_arr[:, 2],
    'System Name': [entry.get('System Name', '') for entry in data],
    'obs_type_1': [entry.get('obs_type_1', '') for entry in data],
    'obs_type_2': [entry.get('obs_type_2', '') for entry in data],
    'evol_type_1': [entry.get('evol_type_1', '') for entry in data],
    'evol_type_2': [entry.get('evol_type_2', '') for entry in data],
    'system_class': [entry.get('system_class', 'None') for entry in data],
    'Simbad': [entry.get('Simbad', None) for entry in data]
})

# # Hand-picked colors and symbols for each class (hex strings). Adjust as you like.
# # Combined color and symbol map for each system class
# STYLE_MAP = {
#     # Binaries w. non-degenerate components
#     'Contact binary': {'color': '#f49856', 'symbol': 'circle'},           # orange
#     'Algol': {'color': '#6d2c14', 'symbol': 'diamond'},                   # maroon
#     'Hot subdwarf': {'color': '#37a8a8', 'symbol': 'square'},             # UV purple
#     'Stripped star': {'color': '#3a8ea3', 'symbol': 'x'},  # muted green
#     'WR binary': {'color': '#52b4e5', 'symbol': 'triangle-up'},       # blue
#     'post AGB': {'color': '#ea4d4d', 'symbol': 'cross'},           # coral/red
    
#     # Binaries containing white dwarfs
#     'EL CVn': {'color': '#8864ba', 'symbol': 'star'},         # orange
#     'Blue straggler binary': {'color': '#6a65b2', 'symbol': 'hourglass'}, # yellow
#     'Chemically peculiar star': {'color': '#af52a6', 'symbol': 'pentagon'}, # gray #FF6692 gumball
#     'Astrometric WD + MS': {'color': '#e6cfd9', 'symbol': 'circle'},                  # light purple
#     'Spectroscopic WD + MS': {'color': '#e6cfd9', 'symbol': 'cross-dot'},                  # light purple
    
#     # Binaries containing neutron stars or black holes
#     'Pulsar binary': {'color': '#9bd24e', 'symbol': 'diamond'},           # lime green
#     'X-ray binary': {'color': '#1abc9c', 'symbol': 'square'},             # muted green
#     'Spectroscopic compact object': {'color': '#cbd24f', 'symbol': 'x'},  # yellow green
#     'Astrometric compact object': {'color': '#408c63', 'symbol': 'triangle-up'}  # muted green
# }

# Hand-picked colors and symbols for each class (hex strings). Adjust as you like.
# Create discrete color map between 
WD_cmap = mcolors.LinearSegmentedColormap.from_list('custom_gradient', ['#e6cfd9', '#a5678e'])
WDcolors = [mcolors.rgb2hex(WD_cmap(i)) for i in np.linspace(0, 1, 7)]

stripped_star_cmap = mcolors.LinearSegmentedColormap.from_list('custom_gradient', ['#82c9ed', '#366de2']) #BDDEF4 #1b478e
strippedstar_colors = [mcolors.rgb2hex(stripped_star_cmap(i)) for i in np.linspace(0, 1, 4)]

compact_object_cmap = mcolors.LinearSegmentedColormap.from_list('custom_gradient', ['#bde256', '#0c9e27'])
compact_obj_colors = [mcolors.rgb2hex(compact_object_cmap(i)) for i in np.linspace(0, 1, 4)]

# Combined color and symbol map for each system class
STYLE_MAP = {
    # Binaries containing white dwarfs
    'Astrometric WD + MS': {'color': WDcolors[0], 'symbol': 'circle'},                  # light purple
    'Spectroscopic WD + MS': {'color': WDcolors[1], 'symbol': 'cross-dot'},                  # light purple
    'WD + MS': {'color': WDcolors[2], 'symbol': 'pentagon'},                  # left over ones (come from Krukow paper 2021ApJ...920...86K)
    'Blue straggler binary': {'color': WDcolors[3], 'symbol': 'hourglass'}, # yellow
    'Chemically Peculiar': {'color': WDcolors[4], 'symbol': 'square'}, # gray  

    # Binaries w. non-degenerate components
    'Contact binary': {'color': '#eda45c', 'symbol': 'triangle-up'},           # orange
    'Algol': {'color': '#d65906', 'symbol': 'diamond'},                   # maroon

    'Hot subdwarf': {'color': strippedstar_colors[0], 'symbol': 'pentagon-open'},             # UV purple
    'Stripped star': {'color': strippedstar_colors[1], 'symbol': 'x'},  # muted green
    'WR binary': {'color': strippedstar_colors[2], 'symbol': 'triangle-up'},       # blue
    
    'EL CVn': {'color': '#FF6692', 'symbol': 'star'},         # orange
    'post AGB': {'color': '#ea4d4d', 'symbol': 'cross'},           # coral/red
    
    # Binaries containing neutron stars or black holes
    'pulsar binary': {'color': compact_obj_colors[0], 'symbol': 'diamond-tall'},           # lime green
    'high-mass XRB': {'color': compact_obj_colors[1], 'symbol': 'square'},             # muted green
    'Spectroscopic compact object': {'color': compact_obj_colors[2], 'symbol': 'x'},  # yellow green
    'Astrometric compact object': {'color': compact_obj_colors[3], 'symbol': 'circle-open'},  # muted green
}

# Extract color and symbol maps for backward compatibility
COLORMAP = {k: v['color'] for k, v in STYLE_MAP.items()}
SYMBOLMAP = {k: v['symbol'] for k, v in STYLE_MAP.items()}

def make_scatter(df, x, y, out_pdf, out_html=None, x_log=False, y_log=False, x_title=None, y_title=None,
                export_legend_to_pdf=True, export_width=700, export_height=450, export_scale=2, 
                 tick_size = 15,label_size = 45,xlim=None, ylim=None):

    # Data preprocessing
    # -------------------- 
    # Drop any rows where either x or y is NaN
    sub = df.dropna(subset=[x, y]).copy()

    # Set  error bars and Fill missing error columns with zero
    sub[f"{x}_err_plus"] = sub[f"{x}_err_plus"].fillna(0)
    sub[f"{x}_err_minus"] = sub[f"{x}_err_minus"].fillna(0)
    sub[f"{y}_err_plus"] = sub[f"{y}_err_plus"].fillna(0)
    sub[f"{y}_err_minus"] = sub[f"{y}_err_minus"].fillna(0)

    # Check that errors don't drop below zero
    for param in [x, y]:
        # wherever the value minus the minus error is <0, set the minus error to the value itself
        # I.e, limit the error bar to not go below zero
        mask_min = sub[param] - sub[f"{param}_err_minus"] < 0
        sub.loc[mask_min, f"{param}_err_minus"] = sub.loc[mask_min, param] 
        print(f"Corrected {mask_min.sum()} negative {param} minus errors.")
        # Also ensure that Eccentricities do not exceed 1
        if param == 'Eccentricity': 
            mask_plus = sub[param] + sub[f"{param}_err_plus"] > 1
            sub.loc[mask_plus, f"{param}_err_plus"] = 1 - sub.loc[mask_plus, param]
            print(f"Corrected {mask_plus.sum()} eccentricity plus errors exceeding 1.")

    print(df[['Eccentricity','Eccentricity_err_plus']][df['System Name']== 'EXO 1722-363'])

    # Replace obs and evol_ type 'None' with 'Unknown' (for hover info)
    sub['obs_type_1'] = sub['obs_type_1'].fillna('Unknown')
    sub['obs_type_2'] = sub['obs_type_2'].fillna('Unknown')
    sub['evol_type_1'] = sub['evol_type_1'].fillna('Unknown')
    sub['evol_type_2'] = sub['evol_type_2'].fillna('Unknown')

    
    # Do the actual plotting
    # -------------------- 
    fig = px.scatter(sub,x=x,y=y,
        error_x=f"{x}_err_plus", error_x_minus=f"{x}_err_minus", error_y=f"{y}_err_plus", error_y_minus=f"{y}_err_minus",
        color='system_class',color_discrete_map=COLORMAP,
        symbol='system_class',symbol_map=SYMBOLMAP,
        hover_name='System Name',
        hover_data=[
            'obs_type_1', 'obs_type_2', 'evol_type_1', 'evol_type_2',
            f'{x}_err_plus', f'{x}_err_minus', 
            f'{y}_err_plus', f'{y}_err_minus'
        ],
        template='plotly_white',
        category_orders={'system_class': list(STYLE_MAP.keys())}  # set order of things in legend
    )

    # Plot values
    # -------------------- 
    fig.update_layout(
        legend_title_text='System Class',
        legend=dict(itemclick='toggle', itemdoubleclick='toggleothers'),
        legend_title=dict(font=dict(size=15)),
        legend_font=dict(size=14)
    )
    fig.update_traces(marker=dict(size=8))


    # Set the axis titles and their label sizes
    x_kwargs = dict(title_text=x_title, tickfont=dict(size=tick_size), title_font=dict(size=label_size))
    y_kwargs = dict(title_text=y_title, tickfont=dict(size=tick_size), title_font=dict(size=label_size))
    if x_log:
        x_kwargs['type'] = 'log'
    if y_log:
        y_kwargs['type'] = 'log'
    if xlim is not None:  
        x_kwargs['range'] = xlim  
    if ylim is not None:  
        y_kwargs['range'] = ylim 
    fig.update_xaxes(**x_kwargs)
    fig.update_yaxes(**y_kwargs)

    # -------------------- 
    # Save the PDF and HTML
    if out_html is not None:
        out_html = Path(out_html)
        out_html.parent.mkdir(parents=True, exist_ok=True)
        fig.update_layout(font=dict(size=14))
        # Write the interactive HTML with the legend intact
        fig.write_html(str(out_html), include_plotlyjs='cdn', include_mathjax='cdn')

    if out_pdf is not None:
        out_pdf = Path(out_pdf)
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        # For static exports (PDF/PNG) we may want to hide the legend
        try:
            orig_showlegend = True
            if hasattr(fig.layout, 'showlegend') and fig.layout.showlegend is not None:
                orig_showlegend = bool(fig.layout.showlegend)
            fig.update_layout(showlegend=export_legend_to_pdf,
            margin=dict(l=40, r=0, t=0, b=60),  # left, right, top, bottom (in pixels)
            font=dict(size=label_size, family="Arial"))

            # Pass width/height/scale to write_image to control PDF resolution.
            fig.write_image(str(out_pdf), width=export_width, height=export_height, scale=export_scale)
            print(f'Wrote PDF: {out_pdf} (w={export_width}, h={export_height}, scale={export_scale})')
        except Exception as e:
            print(f'Could not write PDF for {out_pdf}:', e)

# Create the three plots

## Period vs eccentricity 
make_scatter(
    df,
    x='Period', y='Eccentricity',
    out_html=DOCS_DIR / 'interactive_period_vs_eccentricity.html',
    out_pdf=PLOTS_DIR / 'interactive_period_vs_eccentricity.pdf',
    x_log=True, y_log=False,
    x_title='P (days)', #'$P \, \mathrm{(days)}$', 
    y_title= 'Eccentricity', #'$\mathrm{Eccentricity}$',
    export_legend_to_pdf=True, 
    export_height=550,
    export_width=900,
    export_scale=1,
    label_size = 23,
)

## Period vs donor mass 
make_scatter(
    df,
    x='Period', y='M2',
    out_html=DOCS_DIR / 'interactive_period_vs_m2.html',
    out_pdf=PLOTS_DIR / 'interactive_period_vs_m2.pdf',
    x_log=True, y_log=True,
    x_title='P (days)', #'$P \, \mathrm{(days)}$', 
    y_title='donor mass (Msun)', #'$M_{\mathrm{donor}} \mathrm{(M_{\odot})}$',
    export_legend_to_pdf=False,
    export_height=500,
    export_width=550,
    export_scale=2,
    label_size = 23,
)

## donor (2) vs accretor (1) mass
make_scatter(
    df,
    x='M1', y='M2',
    out_html=DOCS_DIR / 'interactive_m2_vs_m1.html',
    out_pdf=PLOTS_DIR / 'interactive_m2_vs_m1.pdf',
    x_log=True, y_log=True,
    x_title= 'accretor mass (Msun)' , #'$M_{\mathrm{accretor}} \mathrm{(M_{\odot})}$', 
    y_title= 'donor mass (Msun)' , # '$M_{\mathrm{donor}} \mathrm{(M_{\odot})}$',
    export_legend_to_pdf=False,
    export_height=550,
    export_width=550,
    export_scale=2,
    label_size = 23,
    xlim=(-0.5, 1.9), ylim=(-0.5, 1.9)
)