import json
import numpy as np
import pandas as pd
import plotly.express as px

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
    'Ecc_err_minus': ecc_arr[:, 0],
    'Ecc_err_plus': ecc_arr[:, 2],
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

# Hand-picked colors for each class (hex strings). Adjust as you like.
COLORMAP = {
    'Algols': '#6d2c14',            # maroon
    'Hot subdwarfs': '#6d4aa0', # UV purple #6d4aa0
    'Post AGB stars': '#ea4d4d', # coral/red 
    'Black Holes': '#565656',   # orange
    'Blue Straggler Stars': '#f4d25a',
    'contact binaries': '#f49856',  # light olive
    'Neutron star': '#9bd24e',   # lime green
    'Stripped stars': '#408c63', # muted green
    'Wolf-Rayet': '#52b4e5',     # blue 
    'Barium stars': '#af52a6',    # purple  
    'White Dwarf': '#e6cfd9',    # purple 
    'Unclassified': '#cbd24f'
}

SYMBOLS = [
    'circle', 'diamond', 'square', 'x', 'triangle-up', 'cross', 'star', 'hourglass', 'pentagon'
]
SYMBOLMAP = {k: SYMBOLS[i % len(SYMBOLS)] for i, k in enumerate(COLORMAP.keys())}

# ...existing code...

# plotting function
def make_scatter(df, x, y, out_html, out_pdf, x_log=False, y_log=False, x_title=None, y_title=None,
 export_legend_to_pdf=True, export_width = 700, export_height = 450, export_scale = 2):
    """_summary_

    Args:
        df (_type_): _description_
        x (_type_): _description_
        y (_type_): _description_
        out_html (_type_): _description_
        out_pdf (_type_): _description_
        x_log (bool, optional): _description_. Defaults to False.
        y_log (bool, optional): _description_. Defaults to False.
        x_title (_type_, optional): _description_. Defaults to None.
        y_title (_type_, optional): _description_. Defaults to None.
        # export parameters
        export_legend_to_pdf (bool, optional): _description_. Defaults to True.
        export_width (int, optional): _description_. Defaults to 700.
        export_height (int, optional): _description_. Defaults to 450.
        export_scale (int, optional): _description_. Defaults to 2. Higher scale -> higher resolution (useful if rasterized).
    """
    sub = df.dropna(subset=[x, y]).copy()
    # ensure positive if log
    if x_log:
        sub = sub[pd.to_numeric(sub[x], errors='coerce') > 0]
    if y_log:
        sub = sub[pd.to_numeric(sub[y], errors='coerce') > 0]

    fig = px.scatter(
        sub,
        x=x,
        y=y,
        color='system_class',
        color_discrete_map=COLORMAP,
        symbol='system_class',
        symbol_map=SYMBOLMAP,
        hover_name='System Name',
        hover_data=['obs_type_1', 'obs_type_2', 'evol_type_1','evol_type_2'],
        template='plotly_white'
    )
    fig.update_traces(marker=dict(size=7, opacity=0.8))

    # Attach error bars PER TRACE
    ex = f"{x}_err_plus"
    exm = f"{x}_err_minus"
    ey = f"{y}_err_plus"
    eym = f"{y}_err_minus"
    
    has_x_err = ex in sub.columns and exm in sub.columns
    has_y_err = ey in sub.columns and eym in sub.columns
    
    if has_x_err or has_y_err:
        # Get unique system classes in the order they appear in the figure
        unique_classes = sub['system_class'].unique()
        
        for i, trace in enumerate(fig.data):
            # Get the system class for this trace
            system_class = unique_classes[i] if i < len(unique_classes) else None
            
            # Filter dataframe for this system class
            class_data = sub[sub['system_class'] == system_class]
            
            # Update this trace with its specific error bars
            update_dict = {}
            if has_x_err:
                update_dict['error_x'] = dict(
                    type='data',
                    array=class_data[ex].tolist(),
                    arrayminus=class_data[exm].tolist()
                )
            if has_y_err:
                update_dict['error_y'] = dict(
                    type='data',
                    array=class_data[ey].tolist(),
                    arrayminus=class_data[eym].tolist()
                )
            
            if update_dict:
                fig.update_traces(update_dict, selector=dict(name=trace.name))

    fig.update_layout(
        legend_title_text='System Class',
        legend=dict(itemclick='toggle', itemdoubleclick='toggleothers'),
        legend_title=dict(font=dict(size=15)),
        legend_font=dict(size=14)
    )
    tick_size = 15
    label_size = 50
    if x_log:
        fig.update_xaxes(type='log', title_text=x_title, tickfont=dict(size=tick_size), title_font=dict(size=label_size))
    else:
        fig.update_xaxes(title_text=x_title, tickfont=dict(size=tick_size), title_font=dict(size=label_size))
    if y_log:
        fig.update_yaxes(type='log', title_text=y_title, tickfont=dict(size=tick_size), title_font=dict(size=label_size))
    else:
        fig.update_yaxes(title_text=y_title, tickfont=dict(size=tick_size), title_font=dict(size=label_size))

    out_html = Path(out_html)
    out_pdf = Path(out_pdf)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    fig.update_layout(font=dict(size=14))

    # Write the interactive HTML with the legend intact
    fig.write_html(str(out_html), include_plotlyjs='cdn', include_mathjax='cdn')

    # For static exports (PDF/PNG) we may want to hide the legend
    # Temporarily store the current legend visibility, disable it, export,
    # and then restore the original state.
    try:
        orig_showlegend = True
        if hasattr(fig.layout, 'showlegend') and fig.layout.showlegend is not None:
            orig_showlegend = bool(fig.layout.showlegend)
        fig.update_layout(showlegend=export_legend_to_pdf)

        # Pass width/height/scale to write_image to control PDF resolution.
        fig.write_image(str(out_pdf), width=export_width, height=export_height, scale=export_scale)
        print(f'Wrote PDF: {out_pdf} (w={export_width}, h={export_height}, scale={export_scale})')
    except Exception as e:
        print(f'Could not write PDF for {out_pdf}:', e)
    finally:
        # restore legend visibility for any further interactive use
        try:
            fig.update_layout(showlegend=orig_showlegend)
        except Exception:
            pass


# Create the three plots via the helper

## Period vs eccentricity 
make_scatter(
    df,
    x='Period', y='Eccentricity',
    out_html=DOCS_DIR / 'interactive_period_vs_eccentricity.html',
    out_pdf=PLOTS_DIR / 'interactive_period_vs_eccentricity.pdf',
    x_log=True, y_log=False,
    x_title='$P \, \mathrm{(days)}$', 
    y_title='$\mathrm{Eccentricity}$',
    export_legend_to_pdf=False, 
    export_height=400,
    export_width=500,
    export_scale=3
)

## Period vs donor mass 
make_scatter(
    df,
    x='Period', y='M2',
    out_html=DOCS_DIR / 'interactive_period_vs_m2.html',
    out_pdf=PLOTS_DIR / 'interactive_period_vs_m2.pdf',
    x_log=True, y_log=True,
    x_title='$P\,\mathrm{(days)}$', 
    y_title='$M_{\mathrm{donor}} \mathrm{(M_{\odot})}$',
    export_legend_to_pdf=False,
    export_height=400,
    export_width=500,
    export_scale=2
)

## donor (2) vs accretor (1) mass
make_scatter(
    df,
    x='M1', y='M2',
    out_html=DOCS_DIR / 'interactive_m2_vs_m1.html',
    out_pdf=PLOTS_DIR / 'interactive_m2_vs_m1.pdf',
    x_log=True, y_log=True,
    x_title='$M_{\mathrm{accretor}} \mathrm{(M_{\odot})}$', 
    y_title='$M_{\mathrm{donor}} \mathrm{(M_{\odot})}$',
    export_legend_to_pdf=True,
    export_height=400,
    export_width=650,
    export_scale=2
)