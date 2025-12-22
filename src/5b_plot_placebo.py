"""
plot placebo test results for scm
outputs: output/figs/ascm_placebo.png
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from src._plot_style import PlotStyle
from matplotlib.lines import Line2D
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# -- PARAMETERS --
SAVE = True
TREATMENT_TIME = 0


# -- LOAD DATA --
input_dir = Path("models")
output_dir = Path("output/figs")

trajectories = pd.read_csv(input_dir / "ascm_placebo_trajectories.csv")
summary = pd.read_csv(input_dir / "ascm_placebo_summary.csv")

treated = trajectories[trajectories["type"] == "treated"]
placebo = trajectories[trajectories["type"] == "placebo"]

placebo_units = placebo["unit"].unique()


# -- PLOT --
style = PlotStyle()
style.apply()

fig, ax = plt.subplots(figsize=style.figsize_from_pt(fraction=1, ratio=0.618))

# Placebo units in background
for unit in placebo_units:
    unit_data = placebo[placebo["unit"] == unit]
    ax.plot(
        unit_data["time"],
        unit_data["gap"],
        color=style.colors["grey"],
        linewidth=0.8,
        alpha=0.3,
    )

# Treated unit highlighted
ax.plot(
    treated["time"],
    treated["gap"],
    color=style.colors["orange_dark"],
    linewidth=1,
    label="Treated",
)

ax.axhline(
    y=0,
    color=style.colors["text"],
    linestyle=":",
    linewidth=0.8,
    alpha=0.4,
)
ax.axvline(
    x=TREATMENT_TIME,
    color=style.colors["grey"],
    linestyle="--",
    linewidth=0.8,
    alpha=0.6,
)

ax.set_xlabel("Time (Weeks)")
ax.set_ylabel("Gap (Observed - Synthetic)")

# Add p-value annotation
p_value = summary["p_value_rmspe_ratio"].iloc[0]
ax.text(
    0.98,
    0.98,
    f"p-value (RMSPE ratio): {p_value:.3f}",
    transform=ax.transAxes,
    ha="right",
    va="top",
    fontsize=style.base_font_size - 2,
    color=style.colors["text"],
)

# Create explicit legend handles: placebo (grey lines) and treated
placebo_handle = Line2D(
    [0], [0], color=style.colors["grey"], linewidth=0.8, alpha=0.3, label="Placebo Units"
)
treated_handle = Line2D(
    [0], [0], color=style.colors["orange_dark"], linewidth=1, label="Treated"
)
ax.legend(handles=[placebo_handle, treated_handle], loc="best", frameon=False)
style.style_axes(ax)

# Annotate the largest drops (same as ASCM)
post_treatment = treated[treated["time"] > TREATMENT_TIME].copy()
largest_drops = post_treatment.nsmallest(2, "gap")

# Week 0 = November 2022
base_date = datetime(2022, 11, 1)

for idx, row in largest_drops.iterrows():
    week = int(row["time"])
    gap = row["gap"]

    date = base_date + timedelta(weeks=week)
    month = date.strftime("%b")
    year = date.strftime("%Y")
    label = f"{month}\n{year}"

    ax.scatter(week, gap, color=style.colors["red_dark"], s=30, zorder=5, alpha=0.8)

    if week < 50:
        offset_x = 3
        ha = "left"
    else:
        offset_x = -3
        ha = "right"

    ax.text(
        week + offset_x,
        gap,
        label,
        fontsize=style.base_font_size - 4,
        color=style.colors["red_dark"],
        ha=ha,
        va="center",
    )


# -- SAVE OR SHOW --
plt.tight_layout()

if SAVE:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "ascm_placebo.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
else:
    plt.show()
