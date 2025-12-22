"""
creates weekly panel for synthetic control
output: data/panel_weekly.parquet
"""

import geopandas as gpd
import pandas as pd
import duckdb


# -- PARAMETERS --
TREATMENT_DATE = "2022-11-21"


# -- LOAD DATA --
conn = duckdb.connect("data/strava/strava.duckdb")
hex_gdf = gpd.read_parquet("data/berlin_hexagons.parquet")
osm_features = pd.read_csv("data/hex_osm_features.csv")

hex_gdf = hex_gdf.to_crs("EPSG:3857")

# IMPORTANT: filter edge counts by date range here to speed up query
edge_counts = conn.execute("""
    SELECT
        edge_uid,
        DATE_TRUNC('day', STRPTIME(hour, '%Y-%m-%dT%H')) as date,
        SUM(total_trip_count) as daily_count
    FROM data
    WHERE STRPTIME(hour, '%Y-%m-%dT%H') >= '2021-11-21'
      AND STRPTIME(hour, '%Y-%m-%dT%H') < '2024-11-21'
    GROUP BY edge_uid, date
""").df()
conn.close()


# -- HEX-EDGE MAPPING --
gdf = gpd.read_file("data/strava/strava_map.shp")
if gdf.crs is None:
    gdf = gdf.set_crs("EPSG:4326")
gdf = gdf.to_crs("EPSG:3857")
gdf["centroid"] = gdf.geometry.centroid

centroids_gdf = gpd.GeoDataFrame(gdf[["edgeUID"]], geometry=gdf["centroid"], crs=gdf.crs)
hex_joined = gpd.sjoin(hex_gdf, centroids_gdf, how="left", predicate="contains")
hex_edge_map = hex_joined[["edgeUID"]].reset_index()
hex_edge_map.columns = ["hex_id", "edge_uid"]


# -- BUILD DAILY PANEL --
hex_time = edge_counts.merge(hex_edge_map, on="edge_uid", how="inner")
daily = hex_time.groupby(["hex_id", "date"])["daily_count"].sum().reset_index()
daily["date"] = pd.to_datetime(daily["date"])
daily = daily.rename(columns={"daily_count": "trips"})


# -- AGGREGATE TO WEEKS (centered on treatment) --
treatment_dt = pd.Timestamp(TREATMENT_DATE)
daily["days_from_treatment"] = (daily["date"] - treatment_dt).dt.days
daily["time"] = daily["days_from_treatment"] // 7

panel = (
    daily.groupby(["hex_id", "time"])
    .agg(
        trips=("trips", "sum"),
    )
    .reset_index()
)


# -- COMPLETE PANEL --
all_hexes = panel["hex_id"].unique()
all_times = range(panel["time"].min(), panel["time"].max() + 1)

full_index = pd.MultiIndex.from_product([all_hexes, all_times], names=["hex_id", "time"])
panel = (
    panel.set_index(["hex_id", "time"]).reindex(full_index, fill_value=0).reset_index()
)


# -- MERGE UNIT TYPE FROM HEXAGONS --
hex_info = gpd.read_parquet("data/berlin_hexagons.parquet")[["hex_id", "unit_type"]]
panel = panel.merge(hex_info, on="hex_id", how="left")


# -- SAVE PANEL --
panel.to_parquet("data/panel_weekly.parquet", index=False)
