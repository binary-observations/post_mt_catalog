"""
mass_ratio_Figure.py — Generate M1 vs M2 figures for the post-main-sequence catalog.

Available figures:
	- plot_m1_m2_log_by_category(): log-scale M1 vs M2 plot with class points and category medians

Usage:
	python mass_ratio_Figure.py

Or import and call directly:
	from mass_ratio_Figure import load_catalog, plot_m1_m2_log_by_category
	catalog_df = load_catalog(MAIN_CATALOG)
	fig, ax = plot_m1_m2_log_by_category(catalog_df, save=True)
"""

import json
import sys
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde


# Ensure project root is importable regardless of the working directory.
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
STYLE_MAP = category_dict.STYLE_MAP
COLORMAP = category_dict.COLORMAP
SYMBOLMAP = category_dict.SYMBOLMAP
PLOTLY_TO_MPL_MARKER = category_dict.PLOTLY_TO_MPL_MARKER
PAPER_PLOT_RCPARAMS = category_dict.PAPER_PLOT_RCPARAMS
darken_color = category_dict.darken_color


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
	"""Load the subset of catalog columns needed for the exported figure."""
	data = read_json_file(str(file_path))
	if data is None:
		return None

	m1_arr = extract_triplet_array(data, "M1")
	m2_arr = extract_triplet_array(data, "M2")

	return pd.DataFrame(
		{
			"System Name": [entry.get("System Name", "") for entry in data],
			"M1": m1_arr[:, 1],
			"M1_err_minus": m1_arr[:, 0],
			"M1_err_plus": m1_arr[:, 2],
			"M2": m2_arr[:, 1],
			"M2_err_minus": m2_arr[:, 0],
			"M2_err_plus": m2_arr[:, 2],
			"system_class": [entry.get("system_class", "None") for entry in data],
		}
	)

def plot_m1_m2_log_by_category(catalog_df=None, save=True):
	"""Plot log10(M1) vs log10(M2) with per-class points and per-category median tracks."""
	if catalog_df is None:
		catalog_df = load_catalog(MAIN_CATALOG)
		if catalog_df is None:
			return None, None

	plt.rcParams.update(PAPER_PLOT_RCPARAMS)

	fig, ax = plt.subplots(figsize=(10, 6.5))

	plot_df = catalog_df.copy()

	# Log scaling requires strictly positive masses.
	plot_df = plot_df[(plot_df["M1"] > 0) & (plot_df["M2"] > 0)].copy()
	plot_df["log_M1"] = np.log10(plot_df["M1"])
	plot_df["log_M2"] = np.log10(plot_df["M2"])

	# Propagate asymmetric mass uncertainties into log space.
	plot_df["M1_err_minus_log"] = (plot_df["M1_err_minus"] / (plot_df["M1"] * np.log(10))).fillna(0)
	plot_df["M1_err_plus_log"] = (plot_df["M1_err_plus"] / (plot_df["M1"] * np.log(10))).fillna(0)
	plot_df["M2_err_minus_log"] = (plot_df["M2_err_minus"] / (plot_df["M2"] * np.log(10))).fillna(0)
	plot_df["M2_err_plus_log"] = (plot_df["M2_err_plus"] / (plot_df["M2"] * np.log(10))).fillna(0)

	class_handles = []
	fit_handles = []

	def draw_combined_kde(group_classes, legend_label, levels=None, color=None, zorder=0, lin_levels=False):
		"""Draw a grouped 2D KDE in log(M1)-log(M2) space for related subclasses."""
		sub = plot_df[plot_df["system_class"].isin(group_classes)].copy()
		if len(sub) < 2:
			print(f"Not enough data points for KDE of {legend_label} (only {len(sub)}). Skipping KDE.")
			return

		kde_input = np.vstack([sub["log_M1"], sub["log_M2"]])
		scipystats_kde = gaussian_kde(kde_input)
		x_grid = np.linspace(-2, 1.9, 100)
		y_grid = np.linspace(-2, 1.9, 100)
		X, Y = np.meshgrid(x_grid, y_grid)
		Z = scipystats_kde([X.ravel(), Y.ravel()]).reshape(X.shape)

		base_rgb = mcolors.to_rgb(color)
		alpha_ramp = [(*base_rgb, a) for a in np.linspace(0.0, 0.85, 256)]
		group_cmap = mcolors.LinearSegmentedColormap.from_list(
			f"{legend_label}_combined_cmap",
			alpha_ramp,
		)

		if levels is None:
			z_low = np.percentile(Z, 80)
			z_high = np.max(Z)
			if lin_levels:
				levels = np.linspace(z_low, z_high, 5)
			else:
				z_low = max(z_low, 1e-10)
				levels = np.logspace(np.log10(z_low), np.log10(z_high), 5)

		ax.contourf(X, Y, Z, levels=levels, cmap=group_cmap, zorder=zorder, extend="max")
		contour_set = ax.contour(X, Y, Z, levels=levels, colors=color, linewidths=1.2, alpha=0.9, zorder=zorder + 1)
		ax.clabel(contour_set, fmt="%.2f", fontsize=9, inline=True)

		class_handles.append(ax.scatter([], [], c=color, marker="s", label=f"{legend_label} ({len(sub)})"))

	# Compile all WD+MS-like classes into one KDE (matches both "WD + MS" and "WD+MS").
	wd_ms_classes = [cls for cls in STYLE_MAP.keys() if "WD + MS" in cls]
	print(f"WD+MS classes included in KDE: {wd_ms_classes}")
	draw_combined_kde(wd_ms_classes, "WD + MS", color="#EE799A", levels=[0.01, 0.1, 1, 10], zorder=1)

	# Compile all WUMa-like classes into one KDE.
	wuma_classes = [cls for cls in STYLE_MAP.keys() if "WUMa" in cls]
	draw_combined_kde(wuma_classes, "WUMa", color="#e2be61", levels=[0.02, 0.2, 2, 20], zorder=0, lin_levels=True)

	kde_classes = set(wd_ms_classes + wuma_classes)

	for system_class in STYLE_MAP.keys():
		if system_class in kde_classes:
			continue

		sub = plot_df[plot_df["system_class"] == system_class].copy()
		if sub.empty:
			continue

		color = COLORMAP.get(system_class, "#666666")
		marker_plotly = SYMBOLMAP.get(system_class, "circle")
		marker_mpl = PLOTLY_TO_MPL_MARKER.get(marker_plotly, "o")
		zorder = 0 if system_class in SYSTEM_CLASS_MAP["WD binary"] else 2

		class_plot = ax.errorbar(
			sub["log_M1"],
			sub["log_M2"],
			xerr=[sub["M1_err_minus_log"], sub["M1_err_plus_log"]],
			yerr=[sub["M2_err_minus_log"], sub["M2_err_plus_log"]],
			fmt=marker_mpl,
			ms=5,
			c=color,
			ecolor=color,
			elinewidth=1,
			capsize=0,
			alpha=0.65,
			zorder=zorder,
			label=f"{system_class} ({len(sub)})",
		)
		class_handles.append(class_plot)

	# Overlay one median track per top-level category to summarize the point cloud.
	for category, systems in SYSTEM_CLASS_MAP.items():
		if "wd" in category.lower() or "CO binary" in category:
			continue

		system_classes_in_category = list(systems.keys())
		subset = plot_df[plot_df["system_class"].isin(system_classes_in_category)].copy()
		fit_df = subset.dropna(subset=["log_M1", "log_M2"])
		if len(fit_df) < 2:
			continue

		logm1_bins = np.linspace(-2, 1.9, 7)
		x_stats = logm1_bins[:-1] + 0.5 * np.diff(logm1_bins)
		subset["log_M1_bin"] = pd.cut(subset["log_M1"], bins=logm1_bins)
		stats = subset.groupby("log_M1_bin", observed=False)["log_M2"].quantile([0.05, 0.5, 0.95]).unstack()
		stats.columns = ["p05", "median", "p95"]

		first_system_color = list(systems.values())[0]["color"]
		fit_color = darken_color(first_system_color, factor=0.9)
		fit_line, = ax.plot(
			x_stats,
			stats["median"].values,
			color=fit_color,
			linewidth=3,
			zorder=10,
			label=f"{category}",
		)
		fit_handles.append(fit_line)

	# Mark commonly used donor-mass regimes for compact remnants.
	x, ymin, ymax = np.log10(15), np.log10(0.15), np.log10(0.55)
	ax.errorbar(
		x,
		0.5 * (ymin + ymax),
		yerr=[[0.5 * (ymin + ymax) - ymin], [ymax - 0.5 * (ymin + ymax)]],
		fmt="none",
		ecolor="grey",
		elinewidth=1,
		capsize=2,
		capthick=2,
	)
	ax.text(np.log10(17), np.log10(0.3), "$\\mathrm{He WD}$", color="grey", fontsize=14, ha="left", va="center", rotation=90)

	x, ymin, ymax = np.log10(25), np.log10(0.5), np.log10(1.15)
	ax.errorbar(
		x,
		0.5 * (ymin + ymax),
		yerr=[[0.5 * (ymin + ymax) - ymin], [ymax - 0.5 * (ymin + ymax)]],
		fmt="none",
		ecolor="grey",
		elinewidth=1,
		capsize=2,
		capthick=2,
	)
	ax.text(np.log10(28), np.log10(0.7), "$\\mathrm{CO\\, WD}$", color="grey", fontsize=14, ha="left", va="center", rotation=90)

	x, ymin, ymax = np.log10(55), np.log10(1.1), np.log10(2.5)
	ax.errorbar(
		x,
		0.5 * (ymin + ymax),
		yerr=[[0.5 * (ymin + ymax) - ymin], [ymax - 0.5 * (ymin + ymax)]],
		fmt="none",
		ecolor="grey",
		elinewidth=1,
		capsize=2,
		capthick=2,
	)
	ax.text(np.log10(60), np.log10(1.8), "$\\mathrm{NS}$", color="grey", fontsize=14, ha="left", va="center", rotation=90)

	# Reference lines of constant q = M2 / M1 appear as parallel diagonals in log-log space.
	x = 10 ** np.linspace(-2, 1.9, 150)
	ax.plot(np.log10(x), np.log10(10 * x), color="gray", linestyle=":", linewidth=1)
	ax.text(-1.7, -0.55, "$q = 10$", color="gray", fontsize=16, ha="center", va="center", rotation=33)

	ax.plot(np.log10(x), np.log10(x), color="gray", linestyle=":", linewidth=1)
	ax.text(-1.4, -1.2, "$q = M_2/M_1=1$", color="gray", fontsize=16, ha="center", va="center", rotation=33)

	ax.plot(np.log10(x), np.log10(0.4 * x), color="gray", linestyle=":", linewidth=1)
	ax.text(-1.0, -1.5, "$q = 0.4$", color="gray", fontsize=16, ha="center", va="center", rotation=33)

	ax.plot(np.log10(x), np.log10(0.1 * x), color="gray", linestyle=":", linewidth=1)
	ax.text(-0.5, -1.65, "$q = 0.1$", color="gray", fontsize=16, ha="center", va="center", rotation=33)

	tick_positions = [-2, -1, 0, np.log10(2), np.log10(5), 1, np.log10(20), np.log10(50)]
	tick_labels = ["0.01", "0.1", "1", "2", "5", "10", "20", "50"]
	ax.set_xticks(tick_positions)
	ax.set_xticklabels(tick_labels, fontsize=20)
	ax.set_yticks(tick_positions)
	ax.set_yticklabels(tick_labels, fontsize=20)

	legend_fits = ax.legend(
		handles=fit_handles,
		fontsize=12,
		loc="upper left",
		title="Category medians",
		framealpha=0.9,
	)
	legend_classes = ax.legend(
		handles=class_handles,
		fontsize=14,
		ncols=1,
		bbox_to_anchor=(0.9, 0.8),
		loc="upper left",
		bbox_transform=fig.transFigure,
		framealpha=0.0,
	)
	ax.add_artist(legend_fits)

	ax.set_xlim(-2, 1.9)
	ax.set_ylim(-2, 1.9)
	ax.set_xlabel("$\\mathrm{Accretor \\ mass} \\ M_1 \\mathrm{(M_{\\odot})}$", fontsize=26)
	ax.set_ylabel("$\\mathrm{Donor \\ mass} \\ M_2 \\mathrm{(M_{\\odot})}$", fontsize=26)

	if save:
		plt.savefig(LATEX_PLOT_DIR / "M1_M2_log.pdf", bbox_inches="tight")
		plt.savefig(PLOTS_DIR / "M1_M2_log.pdf", bbox_inches="tight")
		print(f"Saved to {LATEX_PLOT_DIR / 'M1_M2_log.pdf'}")
		print(f"Saved to {PLOTS_DIR / 'M1_M2_log.pdf'}")

	return fig, ax


if __name__ == "__main__":
	print(f"Loading catalog from {MAIN_CATALOG}")
	catalog_df = load_catalog(MAIN_CATALOG)

	if catalog_df is None:
		print("Failed to load catalog.")
	else:
		print(f"Loaded {len(catalog_df)} systems")
		print("\nGenerating log-scale M1 vs M2 figure...")
		fig, ax = plot_m1_m2_log_by_category(catalog_df, save=True)
		plt.show()
