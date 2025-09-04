import json
import numpy as np
import pandas as pd
import plotly.express as px
from pathlib import Path
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

# Remove entries with missing values for each plot
plot1_df = pd.DataFrame({
    'Period': periods,
    'Eccentricity': eccentricities
}).dropna()

plot2_df = pd.DataFrame({
    'Period': periods,
    'M2': M2s
}).dropna()

# Create and save interactive plots
fig1 = px.scatter(plot1_df, x='Period', y='Eccentricity', title='Period vs Eccentricity')
out1 = DOCS_DIR / 'interactive_period_vs_eccentricity.html'
fig1.write_html(str(out1), include_plotlyjs='cdn')

fig2 = px.scatter(plot2_df, x='Period', y='M2', title='Period vs M2')
out2 = DOCS_DIR / 'interactive_period_vs_m2.html'
fig2.write_html(str(out2), include_plotlyjs='cdn')