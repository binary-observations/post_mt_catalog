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

from paths import MAIN_CATALOG, DOCS_DIR
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

def extract_column(data, key):
    return [extract_central_value(entry, key) for entry in data]

data = read_json_file(str(file_path))
if data is None:
    print("No data loaded. Exiting.")
    exit(1)

# Extract columns for plotting
periods = extract_column(data, "Period")
eccentricities = extract_column(data, "Eccentricity")
M2s = extract_column(data, "M2")
M1s = extract_column(data, "M1")
names = [entry.get('System Name', '') for entry in data]
types1 = [entry.get('Type1', '') for entry in data]
types2 = [entry.get('Type2', '') for entry in data]
classes = [entry.get('class', 'Unclassified') for entry in data]

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

# Marker symbols to cycle through for classes. See Plotly marker symbol reference for names.
SYMBOLS = [
    'circle', 'diamond', 'square', 'x', 'triangle-up', 'cross', 'star', 'hourglass', 'pentagon'
]
# Build a symbol map aligned with COLORMAP keys (cycles if needed)
SYMBOLMAP = {k: SYMBOLS[i % len(SYMBOLS)] for i, k in enumerate(COLORMAP.keys())}

# Build DataFrames using the raw Period values and filter non-positive values
plot1_df = pd.DataFrame({
    'Period': periods,
    'Eccentricity': eccentricities,
    'System Name': names,
    'Type1': types1,
    'Type2': types2,
    'class': classes
}).dropna(subset=['Period', 'Eccentricity'])
# Keep only positive Periods because we'll plot on a log x-axis
plot1_df = plot1_df[pd.to_numeric(plot1_df['Period'], errors='coerce') > 0]

plot2_df = pd.DataFrame({
    'Period': periods,
    'M2': M2s,
    'System Name': names,
    'Type1': types1,
    'Type2': types2,
    'class': classes
}).dropna(subset=['Period', 'M2'])
plot2_df = plot2_df[pd.to_numeric(plot2_df['Period'], errors='coerce') > 0]

# --- Third plot: donor mass (M2) vs accretor mass (M1)
plot3_df = pd.DataFrame({
    'M1': M1s,
    'M2': M2s,
    'System Name': names,
    'Type1': types1,
    'Type2': types2,
    'class': classes
}).dropna(subset=['M1', 'M2'])


# Create and save plotly interactive plots


######### Period vs Eccentricity
fig1 = px.scatter(
    plot1_df,
    x='Period',
    y='Eccentricity',
    color='class',
    color_discrete_map=COLORMAP,
    symbol='class',
    symbol_map=SYMBOLMAP,
    hover_name='System Name',
    hover_data=['Type1', 'Type2'],
    title='Period vs Eccentricity',
    template='plotly_white'
)
fig1.update_traces(marker=dict(size=7, opacity=0.8))
fig1.update_layout(
    legend_title_text='Class',
    legend=dict(
        itemclick='toggle',           # click toggles visibility
        itemdoubleclick='toggleothers' # double-click isolates
    )
)
fig1.update_xaxes(type='log', title_text='$P\;\mathrm{(days)}$',title_font=dict(size=20))
fig1.update_yaxes(title_text='$\mathrm{Eccentricity}$', title_font=dict(size=20))
out1 = DOCS_DIR / 'interactive_period_vs_eccentricity.html'
fig1.write_html(str(out1), include_plotlyjs='cdn', include_mathjax='cdn')



######### Period vs donor mass (m2)
fig2 = px.scatter(
    plot2_df,
    x='Period',
    y='M2',
    color='class',
    color_discrete_map=COLORMAP,
    symbol='class',
    symbol_map=SYMBOLMAP,
    hover_name='System Name',
    hover_data=['Type1', 'Type2'],
    title='Period vs donor mass',
    template='plotly_white'
)
fig2.update_traces(marker=dict(size=7, opacity=0.8))
fig2.update_layout(
    legend_title_text='Class',
    legend=dict(
        itemclick='toggle',           # click toggles visibility
        itemdoubleclick='toggleothers' # double-click isolates
    )
)
fig2.update_xaxes(type='log', title_text='$P\;\mathrm{(days)}$', title_font=dict(size=20))
fig2.update_yaxes(type='log', title_text='$\mathrm{Donor \ mass, \,} M_2\; (M_\odot)$', title_font=dict(size=20) )
out2 = DOCS_DIR / 'interactive_period_vs_m2.html'
fig2.write_html(str(out2), include_plotlyjs='cdn', include_mathjax='cdn')



######### Donor vs accretor mass
fig3 = px.scatter(
    plot3_df,
    x='M1',
    y='M2',
    color='class',
    color_discrete_map=COLORMAP,
    symbol='class',
    symbol_map=SYMBOLMAP,
    hover_name='System Name',
    hover_data=['Type1', 'Type2'],
    title='Donor mass (M2) vs Accretor mass (M1)',
    template='plotly_white'
)
fig3.update_traces(marker=dict(size=7, opacity=0.8))
fig3.update_layout(
    legend_title_text='Class',
    legend=dict(
        itemclick='toggle',
        itemdoubleclick='toggleothers'
    )
)
fig3.update_xaxes(type='log',title_text='$\mathrm{Accretor \ mass, \,} M_1\; (M_\odot)$', title_font=dict(size=18))
fig3.update_yaxes(type='log',title_text='$\mathrm{Donor \ mass, \,} M_2\; (M_\odot)$', title_font=dict(size=18))
out3 = DOCS_DIR / 'interactive_m2_vs_m1.html'
fig3.write_html(str(out3), include_plotlyjs='cdn', include_mathjax='cdn')