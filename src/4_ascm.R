# runs SCM and ASCM models using augsynth
# outputs model results and placebo inference results to CSV files

library(augsynth)
library(dplyr)
library(arrow)
options(scipen = 999)


# -- PARAMETERS --
TREATMENT_TIME <- 0
TEST <- TRUE  # set to TRUE for fast testing (10 donors, 2 placebos)
N_PLACEBO <- 50
SEED <- 42
TARGET_PRE  <- -52
TARGET_POST <- 104


# -- SETUP AND DATA LOADING --
# Load panel
panel <- read_parquet("data/panel_weekly.parquet")

# Get treated hex ID from data
TREATED_HEX <- panel |>
  filter(unit_type == "treated") |>
  distinct(hex_id) |>
  pull(hex_id)

# Filter to treated and donor units only
analysis_df <- panel |>
  filter(unit_type %in% c("treated", "donor")) |>
  mutate(treat = as.integer(hex_id == TREATED_HEX & time >= TREATMENT_TIME)) |>
  filter(time >= TARGET_PRE & time <= TARGET_POST) %>%
  group_by(hex_id) |>
  ungroup() # |>  # restrict to donors that have trips in at least 60% of periods

# TEST MODE: Limit to 10 donors for fast testing
if (TEST) {
  set.seed(SEED)
  donor_sample <- analysis_df |>
    filter(unit_type == "donor") |>
    distinct(hex_id) |>
    slice_sample(n = 10) |>
    pull(hex_id)

  analysis_df <- analysis_df |>
    filter(unit_type == "treated" | hex_id %in% donor_sample)
}

length(unique(analysis_df$hex_id))

n_donors <- analysis_df |>
  filter(unit_type == "donor") |>
  distinct(hex_id) |>
  nrow()

stopifnot(sum(analysis_df$treat) > 0)


# -- SCM --
scm_fit <- augsynth(
  trips ~ treat,
  unit = hex_id,
  time = time,
  data = analysis_df,
  progfunc = "none",
  scm = TRUE
)

scm_sum <- summary(scm_fit, inf = FALSE)

  
# -- RIDGE ASCM --
ascm_fit <- augsynth(
  trips ~ treat,
  unit = hex_id,
  time = time,
  data = analysis_df,
  progfunc = "ridge",
  scm = TRUE
)

ascm_sum <- summary(ascm_fit, inf = FALSE)


# -- PRE-TREATMENT DIAGNOSTIC --
calc_pre_rmse <- function(model_obj, treated_id, treat_time, data) {
  synth_y <- as.numeric(predict(model_obj, att = FALSE))

  treated_data <- data |>
    filter(hex_id == treated_id) |>
    arrange(time)

  pre_mask <- treated_data$time < treat_time

  residuals <- treated_data$trips[pre_mask] - synth_y[pre_mask]
  sqrt(mean(residuals^2))
}

rmse_scm <- calc_pre_rmse(
  scm_fit, TREATED_HEX, TREATMENT_TIME, analysis_df
)

# -- EXPORT RESULTS FOR PLOTTING AND REPORTING --
# Create output directory
output_dir <- "models"
if (!dir.exists(output_dir)) dir.create(output_dir)

# Get treated unit data for exports
treated_data <- analysis_df |>
  filter(hex_id == TREATED_HEX) |>
  arrange(time)

# Calculate shared metrics
treated_pre_mean <- treated_data |>
  filter(time < TREATMENT_TIME) |>
  summarise(mean_trips = mean(trips, na.rm = TRUE)) |>
  pull(mean_trips)


# -- SCM OUTPUTS --
# 1. SCM timeseries
scm_timeseries <- treated_data |>
  mutate(synthetic = as.numeric(predict(scm_fit, att = FALSE))) |>
  select(time, observed = trips, synthetic)

write.csv(scm_timeseries, file.path(output_dir, "scm_timeseries.csv"), row.names = FALSE)

# 2. SCM ATT
scm_att <- as.data.frame(scm_sum$att)
colnames(scm_att) <- c("time", "att", "std_error")

write.csv(scm_att, file.path(output_dir, "scm_att.csv"), row.names = FALSE)

# 3. SCM weights
scm_weights_raw <- scm_fit$weights
scm_weights <- data.frame(
  hex_id = rownames(scm_weights_raw),
  weight = as.numeric(scm_weights_raw[, 1])
)

write.csv(scm_weights, file.path(output_dir, "scm_weights.csv"), row.names = FALSE)

# 4. SCM summary
scm_avg_att <- scm_sum$average_att$Estimate
scm_att_percent <- (scm_avg_att / treated_pre_mean) * 100

scm_summary <- data.frame(
  treated_hex = TREATED_HEX,
  n_donors = n_donors,
  n_pre_periods = sum(treated_data$time < TREATMENT_TIME),
  n_post_periods = sum(treated_data$time >= TREATMENT_TIME),
  pre_rmse = rmse_scm,
  treated_pre_mean = treated_pre_mean,
  avg_att = scm_avg_att,
  att_percent = scm_att_percent
)

write.csv(scm_summary, file.path(output_dir, "scm_summary.csv"), row.names = FALSE)



# -- ASCM OUTPUTS --
# 1. ASCM timeseries
ascm_timeseries <- treated_data |>
  mutate(synthetic = as.numeric(predict(ascm_fit, att = FALSE))) |>
  select(time, observed = trips, synthetic)

write.csv(ascm_timeseries, file.path(output_dir, "ascm_timeseries.csv"), row.names = FALSE)

# 2. ASCM ATT
ascm_att <- as.data.frame(ascm_sum$att)
colnames(ascm_att) <- c("time", "att", "std_error")

write.csv(ascm_att, file.path(output_dir, "ascm_att.csv"), row.names = FALSE)

# 3. ASCM weights
ascm_weights_raw <- ascm_fit$weights
ascm_weights <- data.frame(
  hex_id = rownames(ascm_weights_raw),
  weight = as.numeric(ascm_weights_raw[, 1])
)

write.csv(ascm_weights, file.path(output_dir, "ascm_weights.csv"), row.names = FALSE)

# 4. ASCM summary
rmse_ascm <- calc_pre_rmse(ascm_fit, TREATED_HEX, TREATMENT_TIME, analysis_df)
ascm_avg_att <- ascm_sum$average_att$Estimate
ascm_att_percent <- (ascm_avg_att / treated_pre_mean) * 100

ascm_summary <- data.frame(
  treated_hex = TREATED_HEX,
  n_donors = n_donors,
  n_pre_periods = sum(treated_data$time < TREATMENT_TIME),
  n_post_periods = sum(treated_data$time >= TREATMENT_TIME),
  pre_rmse = rmse_ascm,
  treated_pre_mean = treated_pre_mean,
  avg_att = ascm_avg_att,
  att_percent = ascm_att_percent
)

write.csv(ascm_summary, file.path(output_dir, "ascm_summary.csv"), row.names = FALSE)


# -- MODEL OBJECTS --
save(scm_fit, ascm_fit, scm_sum, ascm_sum,
     file = file.path(output_dir, "model_objects.rds"))


# -- PLACEBO INFERENCE --
set.seed(SEED)  # for reproducibility

# Get donor hex IDs
donor_ids <- analysis_df |>
  filter(unit_type == "donor") |>
  distinct(hex_id) |>
  pull(hex_id)

# Use all donors or sample (adjust for TEST mode)
n_placebo_to_run <- if (TEST) 2 else N_PLACEBO
placebo_units <- sample(donor_ids, min(n_placebo_to_run, length(donor_ids)))

# Storage for trajectories and summary stats
placebo_trajectories <- list()
placebo_stats <- list()

for (i in seq_along(placebo_units)) {
  placebo_id <- placebo_units[i]

  # Create placebo dataset
  placebo_df_temp <- analysis_df |>
    mutate(treat = as.integer(hex_id == placebo_id & time >= TREATMENT_TIME))

  # Run SCM for this placebo
  placebo_fit <- augsynth(
    trips ~ treat,
    unit = hex_id,
    time = time,
    data = placebo_df_temp,
    progfunc = "ridge",
    scm = TRUE
  )

  # Get observed values and synthetic predictions
  placebo_obs <- analysis_df |>
    filter(hex_id == placebo_id) |>
    arrange(time)

  placebo_synth <- as.numeric(predict(placebo_fit, att = FALSE))
  gaps <- placebo_obs$trips - placebo_synth

  # Calculate pre- and post-treatment RMSPE for this placebo
  pre_mask <- placebo_obs$time < TREATMENT_TIME
  post_mask <- placebo_obs$time >= TREATMENT_TIME

  pre_gaps <- gaps[pre_mask]
  post_gaps <- gaps[post_mask]

  pre_rmspe <- sqrt(mean(pre_gaps^2))
  post_rmspe <- sqrt(mean(post_gaps^2))

  # Store full trajectory
  placebo_trajectories[[i]] <- data.frame(
    unit = placebo_id,
    time = placebo_obs$time,
    gap = gaps,
    type = "placebo"
  )

  # Store summary stats (now including pre-RMSPE)
  placebo_stats[[i]] <- data.frame(
    unit = placebo_id,
    mean_gap = mean(post_gaps),
    mean_abs_gap = mean(abs(post_gaps)),
    rmspe = post_rmspe,
    pre_rmspe = pre_rmspe
  )

}

# Get treated unit trajectory
treated_obs <- analysis_df |>
  filter(hex_id == TREATED_HEX) |>
  arrange(time)

treated_synth <- as.numeric(predict(ascm_fit, att = FALSE))
treated_gaps <- treated_obs$trips - treated_synth

treated_trajectory <- data.frame(
  unit = TREATED_HEX,
  time = treated_obs$time,
  gap = treated_gaps,
  type = "treated"
)

# Treated unit stats
post_mask <- treated_obs$time >= TREATMENT_TIME
treated_post_gaps <- treated_gaps[post_mask]

treated_stats <- data.frame(
  unit = TREATED_HEX,
  mean_gap = mean(treated_post_gaps),
  mean_abs_gap = mean(abs(treated_post_gaps)),
  rmspe = sqrt(mean(treated_post_gaps^2))
)

# Combine all trajectories
all_trajectories <- rbind(
  do.call(rbind, placebo_trajectories),
  treated_trajectory
)

# Combine stats
placebo_stats_df <- bind_rows(placebo_stats)

# Calculate treated unit's pre-treatment RMSPE (needed for filtering)
pre_mask_treated <- treated_obs$time < TREATMENT_TIME
post_mask_treated <- treated_obs$time >= TREATMENT_TIME
treated_pre_rmse <- sqrt(mean(treated_gaps[pre_mask_treated]^2))
treated_post_rmse <- sqrt(mean(treated_gaps[post_mask_treated]^2))
treated_rmspe_ratio <- treated_post_rmse / treated_pre_rmse

# Filter placebos with poor pre-treatment fit (>5x treated unit's pre-RMSPE)
n_before_filter <- nrow(placebo_stats_df)
threshold <- 5 * treated_pre_rmse
placebo_stats_filtered <- placebo_stats_df[placebo_stats_df$rmspe <= threshold, ]

n_after_filter <- nrow(placebo_stats_filtered)
n_excluded <- n_before_filter - n_after_filter

# Filter trajectories to match
placebo_trajectories_filtered <- all_trajectories |>
  filter(type == "treated" | unit %in% placebo_stats_filtered$unit)

# Calculate p-values using filtered placebos
p_value_rmspe <- mean(placebo_stats_filtered$rmspe >= treated_stats$rmspe)
p_value_mean_abs <- mean(placebo_stats_filtered$mean_abs_gap >= treated_stats$mean_abs_gap)


# OUTPUTS
# Export filtered trajectories for spaghetti plot
write.csv(
  placebo_trajectories_filtered,
  file.path(output_dir, "ascm_placebo_trajectories.csv"),
  row.names = FALSE
)

# Calculate RMSPE ratio for treated vs filtered placebos
p_value_rmspe_ratio <- mean(placebo_stats_filtered$rmspe >= treated_post_rmse)

# Export placebo summary (using filtered placebos)
placebo_summary <- data.frame(
  treated_pre_rmse = treated_pre_rmse,
  treated_post_rmse = treated_post_rmse,
  treated_rmspe_ratio = treated_rmspe_ratio,
  mean_placebo_post_rmse = mean(placebo_stats_filtered$rmspe),
  p_value_post_rmse = p_value_rmspe,
  p_value_rmspe_ratio = p_value_rmspe_ratio,
  n_placebos = nrow(placebo_stats_filtered),
  n_placebos_excluded = n_excluded,
  pre_rmspe_threshold = 5 * treated_pre_rmse
)

write.csv(
  placebo_summary,
  file.path(output_dir, "ascm_placebo_summary.csv"),
  row.names = FALSE
)
