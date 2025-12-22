# Install renv if needed
if (!require("renv", quietly = TRUE)) install.packages("renv")

# Initialize and install packages
renv::init(bare = TRUE)
renv::install(c("dplyr", "arrow"))

# Install augsynth from GitHub
renv::install("ebenmichael/augsynth")

renv::snapshot()
