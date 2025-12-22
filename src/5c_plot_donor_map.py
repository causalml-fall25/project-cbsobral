"""
plot study design map for scm and ascm
outputs: output/figs/scm_map.png, ascm_map.png
"""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import contextily as ctx
from pathlib import Path
from src._plot_style import PlotStyle
import warnings

warnings.filterwarnings("ignore", category=UserWarning)


# -- PARAMETERS --
SAVE = True


# -- SETUP --
output_dir = Path("output/figs")
input_dir = Path("models")

# Load base hexagons
hexagons = gpd.read_parquet("data/berlin_hexagons.parquet")
hexagons = hexagons.to_crs("EPSG:3857")

treated = hexagons[hexagons["unit_type"] == "treated"]
excluded = hexagons[hexagons["unit_type"] == "excluded"]
donors = hexagons[hexagons["unit_type"] == "donor"]

style = PlotStyle()
style.apply()


# -- PLOT BOTH MODELS --
for model_name in ["scm", "ascm"]:
    # Load weights
    weights = pd.read_csv(input_dir / f"{model_name}_weights.csv")

    # Merge with donors and split by weight
    donors_merged = donors.merge(weights[["hex_id", "weight"]], on="hex_id", how="left")
    donors_merged["weight"] = donors_merged["weight"].fillna(0)

    weighted_donors = donors_merged[donors_merged["weight"] > 0.01]
    unweighted_donors = donors_merged[donors_merged["weight"] <= 0.01]

    # Create figure
    fig, ax = plt.subplots(figsize=style.figsize_from_pt(fraction=1, ratio=1.0))

    # Unweighted donors (light background)
    if len(unweighted_donors) > 0:
        unweighted_donors.boundary.plot(
            ax=ax,
            color=style.colors["grey"],
            linewidth=0.1,
            alpha=0.2,
        )

    # Add hatching pattern for excluded donors
    if len(excluded) > 0:
        excluded.plot(
            ax=ax,
            color="none",  # Transparent fill
            hatch="///",  # Hatching pattern
            edgecolor=style.colors["grey"],
            linewidth=0.2,
            alpha=0.4,
        )

    # Weighted donors colored by weight
    if len(weighted_donors) > 0:
        # Plot weighted donors with a blue colormap (darker = more weight)
        from matplotlib.colors import LinearSegmentedColormap, Normalize

        blue_cmap = LinearSegmentedColormap.from_list(
            "blue_scale", ["#f7fbff", style.colors["blue_dark"]]
        )
        vmax = max(0.7, weighted_donors["weight"].max())
        norm = Normalize(vmin=0, vmax=vmax)

        weighted_donors.plot(
            ax=ax,
            column="weight",
            cmap=blue_cmap,
            norm=norm,
            alpha=0.9,
            edgecolor=style.colors["grey"],
            linewidth=0.3,
            legend=False,
        )

        # Add colorbar for donor weights
        sm = plt.cm.ScalarMappable(cmap=blue_cmap, norm=norm)
        sm.set_array([])
        from mpl_toolkits.axes_grid1.inset_locator import inset_axes

        cax = inset_axes(
            ax,
            width="20%",
            height="2.5%",
            loc="upper right",
            bbox_to_anchor=(0, -0.02, 1, 1),
            bbox_transform=ax.transAxes,
        )
        cbar = plt.colorbar(sm, cax=cax, orientation="horizontal")
        cbar.set_label(
            "Donor Weight", fontsize=style.base_font_size - 3, color=style.colors["text"]
        )
        cbar.ax.tick_params(
            labelsize=style.base_font_size - 2, colors=style.colors["text"]
        )
        ticks = [0, round(vmax / 2, 2), round(vmax, 2)]
        cbar.set_ticks(ticks)
        cbar.set_ticklabels([str(t) for t in ticks])
        cbar.outline.set_visible(False)
        cax.set_facecolor("white")
        cax.patch.set_alpha(0.85)

    # Treated unit
    treated.plot(
        ax=ax,
        color=style.colors["orange_dark"],
        alpha=0.8,
        edgecolor=style.colors["orange_dark"],
        linewidth=0.2,
    )

    # Crop the map to bounds of donors + treated (tighter cropping)
    all_units = pd.concat([donors, treated])
    minx, miny, maxx, maxy = all_units.total_bounds
    buffer = 1000
    ax.set_xlim(minx - buffer, maxx + buffer)
    ax.set_ylim(miny - buffer, maxy + buffer)

    # Basemap for geographic context
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=12)

    # Legend: hexagon-like markers using Line2D markers (avoids RegularPolygon init issues)
    from matplotlib.lines import Line2D

    marker_size = 10
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="h",
            color="w",
            markerfacecolor=style.colors["orange_dark"],
            markeredgecolor="none",
            markersize=marker_size,
            alpha=0.9,
            label="Treated",
        ),
        Line2D(
            [0],
            [0],
            marker="h",
            color="w",
            markerfacecolor=style.colors["blue_dark"],
            markeredgecolor="none",
            markersize=marker_size,
            alpha=0.75,
            label="Weighted Donors",
        ),
        Line2D(
            [0],
            [0],
            marker="h",
            color="w",
            markerfacecolor="white",
            markeredgecolor=style.colors["grey"],
            markersize=marker_size,
            alpha=0.85,
            label="Excluded Units",
            markeredgewidth=0.8,
        ),
    ]

    legend = ax.legend(
        handles=legend_handles,
        loc="upper left",
        frameon=True,
        facecolor="white",
        labelcolor=style.colors["text"],
        framealpha=0.6,
        edgecolor="none",
        fontsize=style.base_font_size - 2,
        handlelength=1,
        labelspacing=0.6,
    )

    ax.axis("off")

    # Save or show
    plt.tight_layout(pad=0.2)

    if SAVE:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{model_name}_map.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight", pad_inches=0.08)
        plt.close()
    else:
        plt.show()
