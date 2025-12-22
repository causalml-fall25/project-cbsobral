import matplotlib.pyplot as plt
import matplotlib as mpl
from dataclasses import dataclass, field
from typing import Dict
import matplotlib.font_manager as fm
import os

# Try to load Source Sans 3; fallback to Roboto, then Arial
font_paths = [
    r"C:\\Users\\carol\\AppData\\Local\\Microsoft\\Windows\\Fonts\\SourceSans3-Regular.ttf",
    r"C:\\Users\\carol\\AppData\\Local\\Microsoft\\Windows\\Fonts\\Roboto.ttf",
]

primary_font = "Arial"
for font_path in font_paths:
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        primary_font = (
            "Source Sans 3" if "SourceSans3" in font_path else "Source Sans Pro"
        )
        break


def latex_safe(text: str) -> str:
    return text.replace("%", r"\%")


@dataclass
class PlotStyle:
    base_font_size: int = 10

    colors: Dict[str, str] = field(
        default_factory=lambda: {
            # Primary blue-orange diverging palette
            "blue_dark": "#326da6",
            "blue_light": "#98accb",
            "neutral": "#f1f1f1",
            "orange_light": "#ebb4a1",
            "orange_dark": "#d87756",
            # Accent colors
            "grid": "#E6E6E6",
            "text": "#4D4D4D",
            "spines": "#CCCCCC",
            "teal": "#5a9e9e",
            "grey": "#6b7c8e",
            "red_dark": "#c44e52",
            "red_light": "#e8a0a4",
        }
    )

    @staticmethod
    def figsize_from_pt(width_pt=426.79135, fraction=1.0, ratio=0.618):
        inches_per_pt = 1 / 72.27
        width_in = width_pt * inches_per_pt * fraction
        height_in = width_in * ratio
        return (width_in, height_in)

    def apply(self, figsize=None):
        plt.style.use("seaborn-v0_8-white")

        mpl.rcParams.update(
            {
                # Rendering Fixes (prevents two-layers look)
                "pdf.fonttype": 42,
                "ps.fonttype": 42,
                "svg.fonttype": "none",
                "figure.dpi": 150,
                "savefig.dpi": 300,
                # Fonts
                "font.family": "sans-serif",
                "font.sans-serif": [
                    "Source Sans 3",
                    "Source Sans Pro",
                    primary_font,
                    "Arial",
                    "DejaVu Sans",
                    "sans-serif",
                ],
                "font.size": self.base_font_size,
                "font.weight": "light",
                # Colors & Sizes
                "axes.labelcolor": self.colors["text"],
                "xtick.color": self.colors["text"],
                "ytick.color": self.colors["text"],
                "axes.titlecolor": self.colors["text"],
                "axes.labelweight": "light",
                "axes.titleweight": "normal",
                "axes.labelsize": self.base_font_size - 1,
                "figure.titlesize": self.base_font_size + 1,
                "axes.titlesize": self.base_font_size,
                "legend.fontsize": self.base_font_size - 1,
                "xtick.labelsize": self.base_font_size - 2,
                "ytick.labelsize": self.base_font_size - 2,
            }
        )

        return self

    def style_axes(self, ax):
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(self.colors["spines"])
            spine.set_linewidth(0.5)

        ax.grid(True, color=self.colors["grid"], linestyle="-", linewidth=0.5)
        ax.set_axisbelow(True)
        ax.tick_params(
            colors=self.colors["spines"],
            labelcolor=self.colors["text"],
            length=2,
            width=0.5,
        )
        return ax
