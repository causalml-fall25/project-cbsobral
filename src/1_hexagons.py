"""
creates hexagonal grid centered on friedrichstr.
output: data/berlin_hexagons.parquet
"""

import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np


# -- PARAMETERS --
HEX_RADIUS = 500

# -- CONFIG --
friedrichstr_coords = [
    (13.3875142, 52.5150097),
    (13.3908383, 52.5151272),
    (13.3913958, 52.5103902),
    (13.3882648, 52.5102075),
    (13.3875142, 52.5150097),
]


# -- FRIEDRICHSTRASSE CENTER --
friedrichstr_polygon = Polygon(friedrichstr_coords)
friedrichstr_gdf = gpd.GeoDataFrame(
    geometry=[friedrichstr_polygon], crs="EPSG:4326"
).to_crs("EPSG:3857")
friedrichstr_center = friedrichstr_gdf.geometry.iloc[0].centroid
center_x = friedrichstr_center.x
center_y = friedrichstr_center.y


# -- LOAD NETWORK BOUNDS --
gdf = gpd.read_file("data/strava/strava_map.shp")
gdf = gdf.to_crs("EPSG:3857")

minx, miny, maxx, maxy = gdf.total_bounds


# -- CREATE HEXAGONAL GRID --
dx = HEX_RADIUS * 1.5
dy = HEX_RADIUS * np.sqrt(3)

col_range = int((max(abs(center_x - minx), abs(maxx - center_x)) / dx) + 2)
row_range = int((max(abs(center_y - miny), abs(maxy - center_y)) / dy) + 2)

hexagons = []

for col in range(-col_range, col_range):
    y_offset = dy / 2 if col % 2 == 1 else 0

    for row in range(-row_range, row_range):
        cx = center_x + col * dx
        cy = center_y + row * dy + y_offset

        angles = np.linspace(0, 2 * np.pi, 7)
        x = cx + HEX_RADIUS * np.cos(angles)
        y = cy + HEX_RADIUS * np.sin(angles)
        hex_poly = Polygon(zip(x, y))

        if (
            cx >= minx - HEX_RADIUS
            and cx <= maxx + HEX_RADIUS
            and cy >= miny - HEX_RADIUS
            and cy <= maxy + HEX_RADIUS
        ):
            hexagons.append(hex_poly)

hex_gdf = gpd.GeoDataFrame({"geometry": hexagons}, crs="EPSG:3857")
hex_gdf["hex_id"] = range(len(hex_gdf))


# -- IDENTIFY TREATED HEX AND ASSIGN UNIT TYPES --
treated_hex_gdf = hex_gdf[hex_gdf.geometry.contains(friedrichstr_center)]

# Default assignment
hex_gdf["unit_type"] = "donor"


# -- EXCLUDE KANTSTRASSE AREA --
bbox_kant = (13.307318, 52.504083, 13.3315946, 52.5073198)  # minx, miny, maxx, maxy
kant_polygon = Polygon(
    [
        (bbox_kant[0], bbox_kant[1]),
        (bbox_kant[2], bbox_kant[1]),
        (bbox_kant[2], bbox_kant[3]),
        (bbox_kant[0], bbox_kant[3]),
        (bbox_kant[0], bbox_kant[1]),
    ]
)

kant_geom = gpd.GeoSeries([kant_polygon], crs="EPSG:4326").to_crs(hex_gdf.crs).iloc[0]
hex_gdf.loc[hex_gdf.geometry.intersects(kant_geom), "unit_type"] = "excluded"

treated_id = treated_hex_gdf["hex_id"].iloc[0]
treated_geom = treated_hex_gdf.geometry.iloc[0]

# Exclude adjacent hexes (queen contiguity)
hex_gdf.loc[hex_gdf.geometry.touches(treated_geom), "unit_type"] = "excluded"

# Mark treated last
hex_gdf.loc[hex_gdf["hex_id"] == treated_id, "unit_type"] = "treated"


# -- SAVE --
hex_gdf.to_crs("EPSG:4326").to_parquet("data/berlin_hexagons.parquet")
