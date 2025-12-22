"""
plot scm and ascm results
outputs: output/figs/scm_combined.png, acsm_combined.png
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from src._plot_style import PlotStyle
from scipy.interpolate import make_interp_spline
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# -- PARAMETERS --
SAVE = True
TREATMENT_TIME = 0

# -- SETUP --
input_dir = Path("models")
output_dir = Path("output/figs")


style = PlotStyle()
style.apply()


# -- PLOT BOTH MODELS --
for model_name in ["scm", "ascm"]:
    # Load data
    timeseries = pd.read_csv(input_dir / f"{model_name}_timeseries.csv")
    att = pd.read_csv(input_dir / f"{model_name}_att.csv")

    # Create figure with GridSpec (2 columns for 2 plots)
    fig = plt.figure(figsize=(12, 4))
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.25)

    # Plot 1: Observed vs Synthetic
    ax1 = fig.add_subplot(gs[0, 0])

    # Create smooth curves
    time_smooth = np.linspace(timeseries["time"].min(), timeseries["time"].max(), 300)
    spl_obs = make_interp_spline(timeseries["time"], timeseries["observed"], k=3)
    spl_syn = make_interp_spline(timeseries["time"], timeseries["synthetic"], k=3)

    ax1.plot(
        time_smooth,
        spl_obs(time_smooth),
        color=style.colors["orange_dark"],
        linewidth=1.2,
        alpha=0.8,
        label="Observed",
    )
    ax1.plot(
        time_smooth,
        spl_syn(time_smooth),
        color=style.colors["blue_dark"],
        linewidth=1.2,
        alpha=0.8,
        linestyle="--",
        label="Synthetic Control",
    )
    ax1.axvline(
        x=TREATMENT_TIME,
        color=style.colors["grey"],
        linestyle="--",
        linewidth=0.8,
        alpha=0.6,
    )
    ax1.set_xlabel("Time (Weeks)")
    ax1.set_ylabel("Trips Per Period")
    ax1.legend(loc="best", frameon=False)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}"))
    style.style_axes(ax1)

    # Add panel label A in top right
    ax1.text(
        0.98,
        0.98,
        "A",
        transform=ax1.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="right",
    )

    # Plot 2: Treatment Effect
    ax2 = fig.add_subplot(gs[0, 1])

    # Create smooth curve
    time_smooth_att = np.linspace(att["time"].min(), att["time"].max(), 300)
    spl_att = make_interp_spline(att["time"], att["att"], k=3)

    ax2.plot(
        time_smooth_att,
        spl_att(time_smooth_att),
        color=style.colors["teal"],
        linewidth=1.2,
        alpha=0.8,
    )
    ax2.axhline(
        y=0,
        color=style.colors["text"],
        linestyle=":",
        linewidth=0.8,
        alpha=0.4,
    )
    ax2.axvline(
        x=TREATMENT_TIME,
        color=style.colors["grey"],
        linestyle="--",
        linewidth=0.8,
        alpha=0.6,
    )
    ax2.set_xlabel("Time (Weeks)")
    ax2.set_ylabel("Gap (Trips/Period)")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}"))
    style.style_axes(ax2)

    # Add panel label B in top right
    ax2.text(
        0.98,
        0.98,
        "B",
        transform=ax2.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="right",
    )

    # Annotate largest drops in post-treatment period
    post_treatment = att[att["time"] > TREATMENT_TIME].copy()

    # Find the 2 largest negative values (biggest drops)
    largest_drops = post_treatment.nsmallest(2, "att")

    # Week 0 = November 2022, calculate dates
    base_date = datetime(2022, 11, 1)

    # Annotate the drops on the plot
    for idx, row in largest_drops.iterrows():
        week = int(row["time"])
        gap = row["att"]

        # Calculate approximate date
        date = base_date + timedelta(weeks=week)
        month = date.strftime("%b")
        year = date.strftime("%Y")
        label = f"{month}\n{year}"

        # Add point and annotation to the plot
        ax2.scatter(week, gap, color=style.colors["red_dark"], s=30, zorder=5, alpha=0.8)

        ax2.text(
            week + 3,
            gap,
            label,
            fontsize=style.base_font_size - 4,
            color=style.colors["red_dark"],
            ha="left",
            va="center",
        )

    plt.tight_layout()

    if SAVE:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{model_name}_combined.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
    else:
        plt.show()
