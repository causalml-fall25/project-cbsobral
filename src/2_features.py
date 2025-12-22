"""
downloads features from OHSOME API
output: data/hex_osm_features.csv
"""

import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


# -- PARAMETERS --
TIMESTAMP = "2021-09-01"  # date for OHSOME API queries


# -- LOAD HEXAGONS --
hexagons = gpd.read_parquet("data/berlin_hexagons.parquet")
hex_geoms = hexagons[["hex_id", "geometry"]].copy()

if hex_geoms.crs != "EPSG:4326":
    hex_geoms = hex_geoms.to_crs("EPSG:4326")


# -- KEY LOCATIONS --
hauptbahnhof = Point(13.369545, 52.525589)
alexanderplatz = Point(13.413244, 52.521918)  # City center

# Calculate distances (in meters)
hex_geoms_meters = hex_geoms.to_crs("EPSG:3857")
hauptbahnhof_meters = (
    gpd.GeoSeries([hauptbahnhof], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]
)
alexanderplatz_meters = (
    gpd.GeoSeries([alexanderplatz], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]
)

hex_geoms["dist_hauptbahnhof_m"] = hex_geoms_meters.geometry.centroid.distance(
    hauptbahnhof_meters
)
hex_geoms["dist_alexanderplatz_m"] = hex_geoms_meters.geometry.centroid.distance(
    alexanderplatz_meters
)


# -- FORMAT BPOLYS --
def format_bpolys(gdf):
    polys = []
    for idx, row in gdf.iterrows():
        coords = list(row.geometry.exterior.coords)
        coord_str = ",".join([f"{lon},{lat}" for lon, lat in coords])
        polys.append(f"{row['hex_id']}:{coord_str}")
    return "|".join(polys)


bpolys_str = format_bpolys(hex_geoms)


# -- ALL QUERIES --
queries = {
    # Cycling infrastructure (CycleOSM comprehensive filter)
    # Separated tracks
    "bike_track_m": {
        "endpoint": "length",
        "filter": "(highway=cycleway or cycleway=track or cycleway:both=track or cycleway:left=track or cycleway:right=track) and type:way",
    },
    # Painted lanes
    "bike_lane_m": {
        "endpoint": "length",
        "filter": "(cycleway=lane or cycleway:both=lane or cycleway:left=lane or cycleway:right=lane) and type:way",
    },
    # Cycle streets / bicycle roads
    "cyclestreet_m": {
        "endpoint": "length",
        "filter": "(bicycle_road=yes or cyclestreet=yes or bicycle=designated) and type:way",
    },
    # Roads
    "road_length_m": {
        "endpoint": "length",
        "filter": "highway=* and highway!=footway and highway!=path and highway!=steps and type:way",
    },
    # Transit stops
    "n_ubahn_stops": {
        "endpoint": "count",
        "filter": "public_transport=stop_position and subway=yes and type:node",
    },
    "n_sbahn_stops": {
        "endpoint": "count",
        "filter": "public_transport=stop_position and train=yes and type:node",
    },
    "n_tram_stops": {
        "endpoint": "count",
        "filter": "public_transport=stop_position and tram=yes and type:node",
    },
    "n_bus_stops": {
        "endpoint": "count",
        "filter": "public_transport=stop_position and bus=yes and type:node",
    },
    # Bike amenities
    "n_bike_shops": {"endpoint": "count", "filter": "shop=bicycle and type:node"},
    "n_bike_repair": {
        "endpoint": "count",
        "filter": "amenity=bicycle_repair_station and type:node",
    },
    "n_bike_parking": {
        "endpoint": "count",
        "filter": "amenity=bicycle_parking and type:node",
    },
    "n_bike_rental": {
        "endpoint": "count",
        "filter": "amenity=bicycle_rental and type:node",
    },
    # Traffic control
    "n_traffic_signals": {
        "endpoint": "count",
        "filter": "highway=traffic_signals and type:node",
    },
    # POIs - Retail/Services
    "n_restaurants": {"endpoint": "count", "filter": "amenity=restaurant and type:node"},
    "n_cafes": {"endpoint": "count", "filter": "amenity=cafe and type:node"},
    "n_shops": {"endpoint": "count", "filter": "shop=* and type:node"},
    "n_supermarkets": {"endpoint": "count", "filter": "shop=supermarket and type:node"},
    # POIs - Offices/Jobs
    "n_offices": {"endpoint": "count", "filter": "office=* and type:node"},
    # POIs - Education/Recreation
    "n_schools": {"endpoint": "count", "filter": "amenity=school and type:node"},
    "n_universities": {"endpoint": "count", "filter": "amenity=university and type:node"},
    "n_parks": {"endpoint": "count", "filter": "leisure=park and type:node"},
}


# -- EXECUTE QUERIES --
all_results = []

for name, config in queries.items():
    url = f"https://api.ohsome.org/v1/elements/{config['endpoint']}/groupBy/boundary"

    response = requests.post(
        url, data={"bpolys": bpolys_str, "time": TIMESTAMP, "filter": config["filter"]}
    )

    if response.status_code == 200:
        data = response.json()["groupByResult"]
        feature_dict = {
            int(item["groupByObject"]): item["result"][0]["value"] for item in data
        }
        all_results.append(pd.Series(feature_dict, name=name))
        print(f"  Got data for {len(feature_dict)} hexagons")
    else:
        print(f"  ERROR: {response.status_code}")
        print(f"  {response.text[:300]}")


# -- BUILD DATAFRAME --
features_df = pd.concat(all_results, axis=1)
features_df.index.name = "hex_id"
features_df.reset_index(inplace=True)

# Merge with distances
features_df = features_df.merge(
    hex_geoms[["hex_id", "dist_hauptbahnhof_m", "dist_alexanderplatz_m"]],
    on="hex_id",
    how="left",
)

# Add binary flags for transit presence
features_df["has_ubahn"] = (features_df["n_ubahn_stops"] > 0).astype(int)
features_df["has_sbahn"] = (features_df["n_sbahn_stops"] > 0).astype(int)
features_df["has_tram"] = (features_df["n_tram_stops"] > 0).astype(int)
features_df["has_bus"] = (features_df["n_bus_stops"] > 0).astype(int)


# -- SAVE --
features_df.to_csv("data/hex_osm_features.csv", index=False)
