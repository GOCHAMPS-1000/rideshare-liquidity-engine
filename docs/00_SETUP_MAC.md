# 00 · Setup on your Mac (VS Code + GitHub), step by step

Everything below is run in the **VS Code terminal** (open it with `` Ctrl+` `` or Terminal → New Terminal). Lines starting with `$` are commands; do not type the `$`.

## Step 1 · Check Python
```
$ python3 --version
```
You need 3.10 or newer. If it is older or missing: install from https://www.python.org/downloads/ (or `brew install python` if you use Homebrew).

## Step 2 · Install two VS Code extensions
Extensions icon (left bar) → install **Python** and **Jupyter** (both by Microsoft).

## Step 3 · Open the project
Unzip the folder, then in VS Code: **File → Open Folder…** → choose `rideshare-liquidity-engine-v2`.

## Step 4 · Create an isolated environment and install packages
A *virtual environment* (venv) is a private copy of Python for this project, so its packages never clash with other projects.
```
$ python3 -m venv .venv
$ source .venv/bin/activate          # your prompt now starts with (.venv)
$ pip install --upgrade pip
$ pip install -r requirements.txt
```
Then tell VS Code to use it: `Cmd+Shift+P` → **Python: Select Interpreter** → pick the one inside `.venv`.

> Every time you open a new terminal, run `source .venv/bin/activate` again.

## Step 5 · Run the tests (proves the code works on your machine)
```
$ python -m pytest -q
```
Expected: `18 passed`.

## Step 6 · Try the demo (no download needed)
```
$ python -m liquidity.run --demo
```
It writes `reports/demo/summary.md`, 12 tables and 6 charts. **The demo uses made-up data. Never quote its numbers**; it only proves the pipeline runs.

## Step 7 · Download the real data (about 0.5 GB, once)
```
$ curl -L -o data/raw/fhvhv_tripdata_2024-01.parquet https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2024-01.parquet
$ curl -L -o data/raw/taxi_zone_lookup.csv https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```
(These are the same URLs your original notebook used. If the zone file's link has changed, get "Taxi Zone Lookup Table" from the TLC page: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page.)

The `.gitignore` already stops these big files from being committed.

## Step 8 · Run on the real data
```
$ python -m liquidity.run --data data/raw/fhvhv_tripdata_2024-01.parquet --zones data/raw/taxi_zone_lookup.csv
```
Output goes to `reports/`. Open `reports/summary.md` and `reports/figures/`.
If your Mac has 8 GB RAM and it struggles, add `--days 14` (uses the first 14 days, windows stay intact).

## Step 9 · Practice the SQL (DuckDB)
```
$ python -m liquidity.sql_runner sql/01_data_quality.sql
$ python -m liquidity.sql_runner sql/02_eta_by_hour.sql
$ python -m liquidity.sql_runner sql/03_zone_window_triggers.sql
```
These queries were written to match the pandas functions but **were not executed when this project was built** (the build environment had no DuckDB). Run them once, and if one errors, paste the error to me and I will fix it. Comparing their output with the pandas tables is also a good self-check.

## Step 10 · Put it on GitHub
1. On github.com click **New repository**, name it `rideshare-liquidity-engine`, leave "Add README" **unticked**, click Create.
2. In the terminal:
```
$ git init
$ git add .
$ git commit -m "Rideshare supply-liquidity engine v2"
$ git branch -M main
$ git remote add origin https://github.com/<your-username>/rideshare-liquidity-engine.git
$ git push -u origin main
```
GitHub no longer accepts your account password for `git push`. Easiest fix: `brew install gh` then `gh auth login` and follow the prompts (or use VS Code's built-in GitHub sign-in when it pops up).

**Good habit for the portfolio:** after the real run, commit `reports/` (tables + figures) so recruiters see results without running anything. Make several small commits (e.g. "add data-quality audit", "add policy simulation") instead of one giant one; a readable history is itself a signal.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `externally-managed-environment` when pip-installing | You skipped the venv. Do Step 4. |
| `ModuleNotFoundError: pyarrow` | `pip install pyarrow` inside the venv. |
| Killed / out-of-memory on the real run | Use `--days 14` (or `--days 7`). |
| `command not found: python` | Use `python3`, or activate the venv first. |
| SSL error on download inside Python | Use the `curl` commands above instead. |
