"""
Category_dict.py — single source of truth for system-class colours and symbols.

Defines:
    SYSTEM_CLASS_MAP  – nested dict {category: {system_class: {color, symbol}}}
    STYLE_MAP         – flat dict   {system_class: {color, symbol}}  (derived)
    COLORMAP          – flat dict   {system_class: color}            (for plotly)
    SYMBOLMAP         – flat dict   {system_class: symbol}           (for plotly)

Import in notebooks / scripts with e.g.:
        from Category_dict import SYSTEM_CLASS_MAP, STYLE_MAP, COLORMAP, SYMBOLMAP
"""
import numpy as np
import matplotlib.colors as mcolors

# ---------------------------------------------------------------------------
# Colour gradients
# ---------------------------------------------------------------------------
# Create discrete color map between 
WD_cmap = mcolors.LinearSegmentedColormap.from_list('custom_gradient', ['#EE799A', '#a5678e', '#e6cfd9', ])
WDcolors = [mcolors.rgb2hex(WD_cmap(i)) for i in np.linspace(0, 1, 4)]

stripped_star_cmap = mcolors.LinearSegmentedColormap.from_list('custom_gradient', ['#82c9ed', '#366de2', '#8497E5']) #BDDEF4 #1b478e
strippedstar_colors = [mcolors.rgb2hex(stripped_star_cmap(i)) for i in np.linspace(0, 1, 6)]

compact_object_cmap = mcolors.LinearSegmentedColormap.from_list('custom_gradient', ['#bde256', '#0c9e27'])
compact_obj_colors = [mcolors.rgb2hex(compact_object_cmap(i)) for i in np.linspace(0, 1, 4)]

# ---------------------------------------------------------------------------
# SYSTEM_CLASS_MAP: canonical nested category → system-class colour / symbol map
# ---------------------------------------------------------------------------
SYSTEM_CLASS_MAP = {
    ## Binaries w. non-degenerate components ##
    # RLOF
    'Ongoing RLOF': {
    'Algol': {'color': '#eda45c', 'symbol': 'diamond'},                   # maroon
    'Contact binary': {'color': '#d65906', 'symbol': 'triangle-up'},           # orange
    },

    # Low-M stripped
    'Low-M stripped': {
    # Keep both old and new class labels to be robust across catalog versions.
    'Hot subdwarf binary': {'color': strippedstar_colors[0], 'symbol': 'pentagon-open'},             # UV purple
    'He giant': {'color': strippedstar_colors[0], 'symbol': 'cross'},           # coral/red
    'Post-AGB binary': {'color': strippedstar_colors[1], 'symbol': 'circle'},           # coral/red
    'EL CVn': {'color': strippedstar_colors[1], 'symbol': 'star'},         # orange
    },

    # Intermediate/high-M stripped
    'High-M stripped': {
    'Intermediate-M stripped star': {'color': strippedstar_colors[5], 'symbol': 'x'},
    'WR binary': {'color': strippedstar_colors[5], 'symbol': 'triangle-up'},
    },

    # Binaries containing white dwarfs
    'WD binary':{
    'Blue straggler binary': {'color': WDcolors[0], 'symbol': 'hourglass'}, # yellow
    'Chemically Peculiar': {'color': WDcolors[1], 'symbol': 'square'}, # gray  
    'Self-lensing WD + MS': {'color': WDcolors[2], 'symbol': 'diamond-open'},
    'Spectroscopic WD + MS': {'color': WDcolors[2], 'symbol': 'cross-dot'},                  # light purple
    'Astrometric WD + MS': {'color': WDcolors[3], 'symbol': 'circle'},                  # light purple
    'WD + MS': {'color': WDcolors[3], 'symbol': 'pentagon'},                  # left over ones (come from Krukow paper 2021ApJ...920...86K)
    },

    ## Binaries containing neutron stars or black holes ##
    'CO binary': {
    'pulsar binary': {'color': compact_obj_colors[0], 'symbol': 'diamond-tall'},           # lime green
    'high-mass XRB': {'color': compact_obj_colors[1], 'symbol': 'square'},
    'Symbiotic XRB': {'color': compact_obj_colors[1], 'symbol': 'triangle-down'},           # light green
    'Spectroscopic compact object': {'color': compact_obj_colors[2], 'symbol': '+'},  # yellow green
    'Astrometric compact object': {'color': compact_obj_colors[3], 'symbol': 'x'},  # muted green
    },
}

# ---------------------------------------------------------------------------
# Derived flat maps (for plotly's color_discrete_map / symbol_map and PDF plots)
# ---------------------------------------------------------------------------
# STYLE_MAP: flat dict {system_class: {color, symbol}} derived from SYSTEM_CLASS_MAP
STYLE_MAP = {
    cls: style
    for systems in SYSTEM_CLASS_MAP.values()
    for cls, style in systems.items()
}

# COLORMAP / SYMBOLMAP: convenience dicts for plotly
COLORMAP = {k: v['color']  for k, v in STYLE_MAP.items()}
SYMBOLMAP = {k: v['symbol'] for k, v in STYLE_MAP.items()}