.PHONY: all setup run clean

# -- DEFAULT --
all: setup run

# -- ENVIRONMENT SETUP --
setup:
	uv sync
	Rscript renv.R

# -- ANALYSIS --
run:
	Rscript src/4_ascm.R
	uv run python src/5a_plot_results.py
	uv run python src/5b_plot_placebo.py
	uv run python src/5c_plot_donor_map.py
	uv run python src/5d_table_cov.py
	@echo "Analysis complete."

# -- CLEANUP --
clean:
	@if [ -d ".venv" ]; then rm -rf .venv; fi
	@if [ -d "renv" ]; then rm -rf renv; fi
	@if [ -f ".Rprofile" ]; then rm -f .Rprofile; fi
	@if [ -d "output" ]; then rm -rf output; fi
	@if [ -d "models" ]; then rm -rf models; fi
	@if [ -d "__pycache__" ]; then rm -rf __pycache__; fi
	@if [ -d "src/__pycache__" ]; then rm -rf src/__pycache__; fi
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "__pycache__" -delete 2>/dev/null || true
