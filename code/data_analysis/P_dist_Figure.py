"""
P_dist_Figure.py — Generate period-distribution figures for the post-main-sequence catalog.

Available figures:
	- plot_period_distribution_by_category(): normalized period distributions per major category

Usage:
	python P_dist_Figure.py

Or import and call directly:
	from P_dist_Figure import load_catalog, plot_period_distribution_by_category
	catalog_df = load_catalog(MAIN_CATALOG)
	fig, ax = plot_period_distribution_by_category(catalog_df, save=True)
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde


# Ensure project root is on sys.path so imports work regardless of cwd.
proj_root = Path(__file__).parent.parent.parent.resolve()
if str(proj_root) not in sys.path:
	sys.path.insert(0, str(proj_root))

from paths import DATA_ANALYSIS_DIR, LATEX_PLOT_DIR, MAIN_CATALOG, PLOTS_DIR

if str(DATA_ANALYSIS_DIR) not in sys.path:
	sys.path.insert(0, str(DATA_ANALYSIS_DIR))

import importlib
import Category_dict as category_dict

importlib.reload(category_dict)

SYSTEM_CLASS_MAP = category_dict.SYSTEM_CLASS_MAP
PAPER_PLOT_RCPARAMS = category_dict.PAPER_PLOT_RCPARAMS


def read_json_file(file_path):
	"""Load JSON catalog from file."""
	try:
		with open(file_path, "r") as handle:
			return json.load(handle)
	except Exception as exc:
		print(f"Error reading file: {exc}")
		return None


def extract_triplet_array(data, key):
	"""Return an (N, 3) float array for a triplet-valued key."""
	rows = []
	for entry in data:
		value = entry.get(key, None)
		if isinstance(value, (list, tuple, np.ndarray)) and len(value) == 3:
			try:
				rows.append([
					np.nan if value[0] is None else float(value[0]),
					np.nan if value[1] is None else float(value[1]),
					np.nan if value[2] is None else float(value[2]),
				])
			except (TypeError, ValueError):
				rows.append([np.nan, np.nan, np.nan])
		elif isinstance(value, (int, float)):
			rows.append([np.nan, float(value), np.nan])
		else:
			rows.append([np.nan, np.nan, np.nan])
	return np.array(rows, dtype=float)


def load_catalog(file_path=MAIN_CATALOG):
	"""Load the main catalog into a compact DataFrame for plotting."""
	data = read_json_file(str(file_path))
	if data is None:
		return None

	period_arr = extract_triplet_array(data, "Period")
	return pd.DataFrame(
		{
			"System Name": [entry.get("System Name", "") for entry in data],
			"Period": period_arr[:, 1],
			"system_class": [entry.get("system_class", "None") for entry in data],
		}
	)


def plot_period_distribution_by_category(catalog_df=None, save=True):
	"""Plot normalized log-period distributions for the top-level system categories."""
	if catalog_df is None:
		catalog_df = load_catalog(MAIN_CATALOG)
		if catalog_df is None:
			return None, None

	plt.rcParams.update(PAPER_PLOT_RCPARAMS)

	bins = np.linspace(-2, 4, 25)
	bin_width = bins[1] - bins[0]

	fig, ax = plt.subplots(figsize=(10, 9))

	for category, systems in SYSTEM_CLASS_MAP.items():
		system_classes = list(systems.keys())
		subset = catalog_df[catalog_df["system_class"].isin(system_classes)]
		log_periods = np.log10(subset["Period"].dropna())

		if len(log_periods) <= 1:
			continue

		counts, bin_edges = np.histogram(log_periods, bins=bins)
		if counts.sum() == 0:
			continue

		counts_normalized = counts / counts.sum()
		first_system_color = list(systems.values())[0]["color"]
		bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

		ax.bar(
			bin_centers,
			counts_normalized,
			width=bin_width,
			alpha=0.3,
			color=first_system_color,
			edgecolor="none",
		)

		kde = gaussian_kde(log_periods, bw_method=0.2)
		x_range = np.linspace(log_periods.min(), log_periods.max(), 200)
		kde_values = kde(x_range)
		kde_normalized = kde_values * bin_width

		ax.plot(
			x_range,
			kde_normalized,
			color=first_system_color,
			linewidth=2.5,
			label=f"{category} (n={len(log_periods)})",
			alpha=0.9,
		)

	xticks = [0.01, 0.1, 1, 10, 100, 1000, 10000]
	xtick_labels = ["0.01", "0.1", "1", "10", "100", "1000", "$10^4$"]
	ax.set_xticks(np.log10(xticks))
	ax.set_xticklabels(xtick_labels, fontsize=20)

	ax.set_xlim(-2, 4)
	ax.tick_params(axis="both", labelsize=20)
	ax.set_xlabel("$\\mathrm{Orbital\\,Period \\ (days)}$", fontsize=28)
	ax.set_ylabel("$\\mathrm{Normalized \\ Frequency}$", fontsize=28)
	ax.legend(loc="upper left", fontsize=18)
	plt.tight_layout()

	if save:
		plt.savefig(LATEX_PLOT_DIR / "period_distribution_by_category.pdf")
		plt.savefig(PLOTS_DIR / "period_distribution_by_category.pdf")
		print(f"Saved to {LATEX_PLOT_DIR / 'period_distribution_by_category.pdf'}")
		print(f"Saved to {PLOTS_DIR / 'period_distribution_by_category.pdf'}")

	return fig, ax


if __name__ == "__main__":
	print(f"Loading catalog from {MAIN_CATALOG}")
	catalog_df = load_catalog(MAIN_CATALOG)

	if catalog_df is None:
		print("Failed to load catalog.")
	else:
		print(f"Loaded {len(catalog_df)} systems")
		print("\nGenerating period distribution by category...")
		fig, ax = plot_period_distribution_by_category(catalog_df, save=True)
		plt.show()
