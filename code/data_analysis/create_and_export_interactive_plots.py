import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ensure project root is on sys.path so `import paths` finds the top-level paths.py
import os, sys
from pathlib import Path
proj_root = Path('/Users/liekevanson/Documents/Projects/post_mt_review').resolve()
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from paths import MAIN_CATALOG, DOCS_DIR, PLOTS_DIR, LATEX_PLOT_DIR

# System-class colours and symbols — imported from the shared module.
# Edit code/data_analysis/Category_dict.py to change colours/symbols everywhere.
from Category_dict import SYSTEM_CLASS_MAP, STYLE_MAP, COLORMAP, SYMBOLMAP

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
            # Convert each element independently so missing error bounds do not
            # erase a valid central value.
            row = []
            for item in val:
                try:
                    row.append(np.nan if item is None else float(item))
                except (TypeError, ValueError):
                    row.append(np.nan)
            rows.append(row)
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


def max_eccentricity(period_days):
    """ 
    Approximate max eccentricity following eq.3 from Moe & di Stefano 2017.
    e_max(P) = 1 - (P / 2 days)^(-2/3), valid for P > 2 days.
    """
    period_days = np.asarray(period_days, dtype=float)
    emax = np.full_like(period_days, np.nan, dtype=float)
    valid = period_days > 2.0
    emax[valid] = 1.0 - (period_days[valid] / 2.0) ** (-2.0 / 3.0)
    return np.clip(emax, 0.0, 1.0)

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

    # Add max eccentricity curve for Period vs Eccentricity plot
    # -------------------- 
    if x == 'Period' and y == 'Eccentricity':
        period_vals = np.logspace(np.log10(2.01), 4.5, 500)
        emax_vals = max_eccentricity(period_vals)
        fig.add_trace(
            go.Scatter(x=period_vals, y=emax_vals,
                       mode='lines',
                       name=r'$e_{\mathrm{max}}$ (Moe & di Stefano 2017)',
                       line=dict(color='grey', width=2.2, dash='dash'),
                       hovertemplate='<b>Max Eccentricity Envelope</b><br>Period: %{x:.2f} days<br>e_max: %{y:.3f}<extra></extra>',
                       showlegend=True)
        )

    # Plot values
    # -------------------- 
    fig.update_layout(
        legend_title_text='',
        legend=dict(itemclick='toggle', itemdoubleclick='toggleothers'),
        legend_title=dict(font=dict(size=20)),
        legend_font=dict(size=18)
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
    out_pdf= None, # PLOTS_DIR / 'interactive_period_vs_eccentricity.pdf',
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
    out_pdf=None, #PLOTS_DIR / 'interactive_period_vs_m2.pdf',
    x_log=True, y_log=True,
    x_title='P (days)', #'$P \, \mathrm{(days)}$', 
    y_title='donor mass (Msun)', #'$M_{\mathrm{donor}} \mathrm{(M_{\odot})}$',
    export_legend_to_pdf=True,
    export_height=500,
    export_width=900,
    export_scale=2,
    label_size = 23,
)

## Period vs donor mass 
make_scatter(
    df,
    x='Period', y='M2',
    out_html=DOCS_DIR / 'interactive_period_vs_m2.html',
    out_pdf=None, #PLOTS_DIR / 'interactive_period_vs_m2.pdf',
    x_log=True, y_log=True,
    x_title='P (days)', #'$P \, \mathrm{(days)}$', 
    y_title='donor mass (Msun)', #'$M_{\mathrm{donor}} \mathrm{(M_{\odot})}$',
    export_legend_to_pdf=True,
    export_height=500,
    export_width=900,
    export_scale=2,
    label_size = 23,
)


## donor (2) vs accretor (1) mass
make_scatter(
    df,
    x='M1', y='M2',
    out_html=DOCS_DIR / 'interactive_m2_vs_m1.html',
    out_pdf=None, #PLOTS_DIR / 'interactive_m2_vs_m1.pdf',
    x_log=True, y_log=True,
    x_title= 'accretor mass (Msun)' , #'$M_{\mathrm{accretor}} \mathrm{(M_{\odot})}$', 
    y_title= 'donor mass (Msun)' , # '$M_{\mathrm{donor}} \mathrm{(M_{\odot})}$',
    export_legend_to_pdf=True,
    export_height=550,
    export_width=900,
    export_scale=2,
    label_size = 23,
    xlim=(-0.5, 1.9), ylim=(-0.5, 1.9)
)