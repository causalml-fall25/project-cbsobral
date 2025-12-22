# The Effect of Infrastructure Removal on Cycling Activity

This repository contains code and data for estimating the causal effect of removing cycling infrastructure on cycling activity in Berlin.

## Prerequisites

- Python: Version ≥ 3.10
- R: Version ≥ 4.0
- uv: [Package manager](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`)
- Make: `winget install GnuWin32.Make` (Windows) 

## Quick Start

```bash
make setup  # Install dependencies
make run    # Run analysis
make all    # setup + run
make clean  # Remove generated files and environments
```

## Pipeline
The analysis runs:
1. SCM/ASCM models (`src/4_ascm.R`)
2. All visualization and table scripts (`src/5_*.py`)

## Project Structure

```
├── data/              # Input data
├── src/               # Analysis scripts
├── pyproject.toml     # Python dependencies
├── Makefile           # Pipeline commands
├── README.md
├── renv.R             # R setup script
├── renv.lock          # R lock file
└── uv.lock            # Python lock file
└── writeup.pdf           
```

## Notes
- Pre-processed data files are provided in `data/`; raw Strava Metro data cannot be redistributed due to licensing restrictions
- By default, `TEST = TRUE` in `src/4_ascm.R` for fast testing (10 donors, 2 placebos); set `TEST = FALSE` for full analysis with all donors and 50 placebos 
