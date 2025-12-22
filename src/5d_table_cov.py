"""
create latex table showing characteristics treated and top donors
outputs: output/tables/donor_characteristics.tex
"""

import pandas as pd
from pathlib import Path


# -- PARAMETERS --
SAVE = True


# -- SETUP --
input_dir = Path("models")
output_dir = Path("output/tables")

# Load ASCM weights
weights = pd.read_csv(input_dir / "ascm_weights.csv")

# Get top 5 donors by absolute weight
top_donors = weights.nlargest(5, "weight")

# Load hexagons to get treated unit
hexagons = pd.read_parquet("data/berlin_hexagons.parquet")
treated_hex = hexagons[hexagons["unit_type"] == "treated"]["hex_id"].iloc[0]

# Load features
features = pd.read_csv("data/hex_osm_features.csv")

# Define covariates to include in the table (with nice labels)
covariates = {
    "dist_alexanderplatz_m": "Dist. to Center (m)",
    "road_length_m": "Road Length (m)",
    "bike_track_m": "Bike Track (m)",
    "bike_lane_m": "Bike Lane (m)",
    "n_ubahn_stops": "U-Bahn Stops",
    "n_sbahn_stops": "S-Bahn Stops",
    "n_restaurants": "Restaurants",
    "n_shops": "Shops",
}

# Get values for treated unit
treated_values = features[features["hex_id"] == treated_hex][
    list(covariates.keys())
].iloc[0]

# Get values for each top donor
donor_data = []
for _, donor_row in top_donors.iterrows():
    hex_id = donor_row["hex_id"]
    weight = donor_row["weight"]
    values = features[features["hex_id"] == hex_id][list(covariates.keys())].iloc[0]
    donor_data.append({"hex_id": hex_id, "weight": weight, **values.to_dict()})

donor_df = pd.DataFrame(donor_data)

# Calculate weighted average for donors
weighted_avg = {}
for cov_key in covariates.keys():
    weighted_avg[cov_key] = (
        sum(donor_df[cov_key] * donor_df["weight"]) / donor_df["weight"].sum()
    )

# Create LaTeX table
latex_lines = []
latex_lines.append(r"\begin{table}[htbp]")
latex_lines.append(r"\centering")
latex_lines.append(r"\caption{Treated Unit vs. Top 5 Donors}")
latex_lines.append(r"\label{tab:donor_characteristics}")
latex_lines.append(r"\begin{tabular}{lccccccc}")
latex_lines.append(r"\toprule")

# Header row
header = "Covariate & Treated"
for i in range(5):
    header += f" & Donor {i + 1}"
header += " & Avg"
header += r" \\"
latex_lines.append(header)

# Add weights row
weights_row = "Weight & ---"
for _, row in donor_df.iterrows():
    weights_row += f" & {row['weight']:.3f}"
weights_row += " & ---"
weights_row += r" \\"
latex_lines.append(r"\midrule")
latex_lines.append(weights_row)
latex_lines.append(r"\midrule")

# Add covariate rows
for cov_key, cov_label in covariates.items():
    row = f"{cov_label} & {treated_values[cov_key]:.0f}"
    for _, donor_row in donor_df.iterrows():
        row += f" & {donor_row[cov_key]:.0f}"
    row += f" & {weighted_avg[cov_key]:.0f}"
    row += r" \\"
    latex_lines.append(row)

latex_lines.append(r"\bottomrule")
latex_lines.append(r"\end{tabular}")
latex_lines.append(r"\end{table}")

latex_table = "\n".join(latex_lines)

if SAVE:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "donor_characteristics.tex"
    with open(output_path, "w") as f:
        f.write(latex_table)
