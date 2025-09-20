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


def extract_central_value(entry, key):
    # Expects [err-, value, err+], returns value or np.nan
    val = entry.get(key, [np.nan, np.nan, np.nan])
    if isinstance(val, list) and len(val) == 3:
        return val[1]
    elif isinstance(val, (int, float)):
        return val
    else:
        return np.nan


def extract_error_minus(entry, key):
    # Returns the lower error (err-) from [err-, value, err+] or np.nan
    val = entry.get(key, None)
    if isinstance(val, list) and len(val) == 3:
        try:
            return float(val[0])
        except Exception:
            return np.nan
    return np.nan


def extract_error_plus(entry, key):
    # Returns the upper error (err+) from [err-, value, err+] or np.nan
    val = entry.get(key, None)
    if isinstance(val, list) and len(val) == 3:
        try:
            return float(val[2])
        except Exception:
            return np.nan
    return np.nan


def extract_column(data, key):
    return [extract_central_value(entry, key) for entry in data]


def extract_error_columns(data, key):
    """Return two lists: error_minus, error_plus for the given key across data."""
    errs_lo = [extract_error_minus(entry, key) for entry in data]
    errs_hi = [extract_error_plus(entry, key) for entry in data]
    return errs_lo, errs_hi


# Read data
data = read_json_file(str(file_path))
if data is None:
    print("No data loaded. Exiting.")
    exit(1)

# Build a single DataFrame with central values and errors
df = pd.DataFrame({
    'Period': extract_column(data, 'Period'),
    'Period_err_minus': extract_error_columns(data, 'Period')[0],
    'Period_err_plus': extract_error_columns(data, 'Period')[1],
    'Eccentricity': extract_column(data, 'Eccentricity'),
    'Ecc_err_minus': extract_error_columns(data, 'Eccentricity')[0],
    'Ecc_err_plus': extract_error_columns(data, 'Eccentricity')[1],
    'M1': extract_column(data, 'M1'),
    'M1_err_minus': extract_error_columns(data, 'M1')[0],
    'M1_err_plus': extract_error_columns(data, 'M1')[1],
    'M2': extract_column(data, 'M2'),
    'M2_err_minus': extract_error_columns(data, 'M2')[0],
    'M2_err_plus': extract_error_columns(data, 'M2')[1],
    'System Name': [entry.get('System Name', '') for entry in data],
    'Type1': [entry.get('Type1', '') for entry in data],
    'Type2': [entry.get('Type2', '') for entry in data],
    'class': [entry.get('class', 'Unclassified') for entry in data],
    'Simbad': [entry.get('Simbad', None) for entry in data]
})

# Hand-picked colors for each class (hex strings). Adjust as you like.
COLORMAP = {
    'Algols': '#6d2c14',            # maroon
    'Hot subdwarfs (d)': '#ea4d4d', # coral/red
    'Black Holes (d)': '#565656',   # orange
    'Blue Straggler Stars': '#f4d25a',
    'contact binaries': '#f49856',  # light olive
    'Neutron star (d)': '#9bd24e',   # lime green
    'Stripped stars (d)': '#408c63', # muted green
    'Wolf-Rayet (d)': '#52b4e5',     # blue 
    'White Dwarf (d)': '#e6cfd9',    # purple  #6d4aa0
    'Unclassified': '#cbd24f'
}

SYMBOLS = [
    'circle', 'diamond', 'square', 'x', 'triangle-up', 'cross', 'star', 'hourglass', 'pentagon'
]
SYMBOLMAP = {k: SYMBOLS[i % len(SYMBOLS)] for i, k in enumerate(COLORMAP.keys())}


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
        color='class',
        color_discrete_map=COLORMAP,
        symbol='class',
        symbol_map=SYMBOLMAP,
        hover_name='System Name',
        hover_data=['Type1', 'Type2'],
        template='plotly_white'
    )
    fig.update_traces(marker=dict(size=7, opacity=0.8))

    # attach error bars if columns available
    ex = f"{x}_err_plus"
    exm = f"{x}_err_minus"
    ey = f"{y}_err_plus"
    eym = f"{y}_err_minus"
    if ex in sub.columns and exm in sub.columns:
        fig.update_traces(error_x=dict(type='data', array=sub[ex].tolist(), arrayminus=sub[exm].tolist()))
    if ey in sub.columns and eym in sub.columns:
        fig.update_traces(error_y=dict(type='data', array=sub[ey].tolist(), arrayminus=sub[eym].tolist()))

    fig.update_layout(
        legend_title_text='Class',
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

    fig.update_layout(width=export_width, height=export_height, font=dict(size=14))

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

## Perios vs eccentricity 
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

## Perios vs donor mass 
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