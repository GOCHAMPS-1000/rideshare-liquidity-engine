# 02 · Code walkthrough: every file, why it exists

Mental model of the whole project (one line each):

```
raw parquet ──► data.py ──► quality.py ──► metrics.py ──► simulate.py ──► experiment.py
 (trips)        load +       "can we       "what's the     "what would    "how would we
                features     trust it?"    problem?"       the rule cost?" prove it works?"
                                              │                │
                                              └──► plots.py ◄──┘      run.py = glue + summary.md
```

Design principles (be ready to say these):
1. **Separate calculation from presentation.** `metrics.py` returns tables; `plots.py` draws them. Each can be tested and reused alone.
2. **One config file.** Every threshold lives in `config.py`.
3. **Audit before analysis.** `quality.py` runs first so bad data can't silently shape conclusions.
4. **Test with tiny data you can verify by hand.** See `tests/test_core.py`.
5. **Honest about limits.** Proxies and assumptions are labelled in code and docs.

---
## `liquidity/config.py`
Constants only. Key ones and the reasoning:
- `ETA_MAX_VALID = 30`: a wait over 30 min is more likely a data glitch/edge case than a typical ride. Not sacred: `quality.cutoff_sensitivity()` shows how results change at 15/20/30/60/120.
- `LONG_WAIT_MIN = 8` and `ETA_TARGET_MIN = 6`: both from the PRD (8 = "bad experience", 6 = guardrail on average wait).
- `MIN_TRIPS_ZONE = 500`, `MIN_TRIPS_WINDOW = 5`: reliability guards against small-sample noise. Judgement calls, defensible, adjustable.
- `RUSH_HOURS`: 7–9 and 16–19, applied on **weekdays only**.

## `liquidity/data.py`
- `load_trips`: `pd.read_parquet(path, columns=[...])`. **Parquet is columnar**, so asking for 16 columns reads only those from disk: faster and less RAM.
- `prepare_trips`: adds the analysis columns.
  - `eta_min` = arrival − request, in minutes (`.dt.total_seconds()/60`).
  - `rider_wait_min` = pickup − request. Exists for **all** companies (including Lyft), so it is the fair cross-company measure; it includes boarding time.
  - `window_start = request.dt.floor("10min")`: assigns each trip to its 10-minute bucket, e.g. 08:17:59 → 08:10:00.
  - `platform_take = base_passenger_fare − driver_pay`.
  - It **mutates** the DataFrame (no copy) to save memory on 19 M rows.

## `liquidity/quality.py`
- `audit`: per company: trips, % null `on_scene`, % negative/over-cutoff ETA, % usable, % negative margin. This is where you discover **who** is missing: v1 never looked.
- `cutoff_sensitivity`: robustness check on the outlier cutoff.

## `liquidity/metrics.py`
| Function | Question it answers | Key idea |
|---|---|---|
| `valid` | which rows are usable? | `between(0, 30)` also drops NaN |
| `eta_summary` | what does the wait distribution look like for any grouping? | mean + p50 + p90 + p95 + long-wait share |
| `hourly_dow_heatmap` | when is it bad? | weekday × hour, sparse cells blanked |
| `zone_bottlenecks` | where should we act first? | **excess minutes = Σ max(wait − target, 0)**; cumulative share = Pareto |
| `density_effect` | does busier mean slower or faster? | Spearman at zone and zone-hour level |
| `unit_economics` | is there margin to fund incentives? | ratio-of-sums take rate; share of negative-margin trips |
| `wav_unmet` | any *real* unfulfilled-demand signal? | WAV requested but not served by a WAV |
| `shared_unmatched` | another mismatch signal | shared requested but not pooled |

**Why excess minutes instead of average wait?** It multiplies severity × volume. A zone with 50,000 slightly-slow trips can hurt more people than a zone with 200 terrible ones. The Pareto column lets you say "N zones hold 50 % of the pain".

## `liquidity/simulate.py`: the "engine"
1. `build_windows`: group trips into (zone, 10-min window); compute `trips` and `stress` (share of waits > 8 min). Drops windows with < 5 trips.
2. `bonus_amount`: PRD formula `base + stress × multiplier`, with `stress` capped to [0,1].
3. `simulate_policy`:
   - a window **triggers** if `stress > threshold`;
   - a trigger at *t* keeps a bonus live for the next 3 windows (30 min) in that zone (shifted by **exact timestamps** and merged: robust to missing windows);
   - overlapping bonuses take the max;
   - cost = bonus × rides in live windows × `eligible_share`.
   - Outputs: trigger rate, share of rides covered, total cost, cost per covered ride, **blended cost per ride** (compared with the $2.50 cap), and **break-even ride lift**.
4. `sweep_thresholds`: repeats the above for thresholds 10 %…50 % → sensitivity analysis and a chart.

**Important finding baked into the tests:** the PRD formula gives at least $2 + 0.20×$5 = **$3.00** per bonus ride, which is *above* the $2.50 guardrail. The cap only makes sense as a **blended** cost across all rides in affected zones. We define it that way explicitly (`test_policy_min_bonus_exceeds_cap_per_covered_ride`).

**What the simulation cannot do:** show that waits improve. It replays the *rule* on history; it holds behaviour fixed.

## `liquidity/experiment.py`
- `sample_size_two_proportions`: classic formula n = (z_α/2 + z_β)² · [p₁(1−p₁)+p₂(1−p₂)] / (p₁−p₂)².
- `mde_proportion`: the inverse: smallest detectable drop for a given n.
- `design_effect`: 1 + (m−1)ρ.
- `simulate_switchback_power`: Monte-Carlo. Each simulated experiment: for every zone, randomly mark half of its time blocks as treated; generate long-wait shares with noise; compute each zone's treated-minus-control difference; one-sample t-test across zones. Repeated 1,000–2,000×; power = fraction significant. With `rel_effect=0` it is an **A/A check** (should be ≈ 5 %).

## `liquidity/plots.py`
Six charts; one idea each. Title = topic, axes carry units, one accent colour.

## `liquidity/run.py`
Glue. `run()` does 7 steps, writes `tables/*.csv`, `figures/*.png` and an auto-generated `summary.md` where **every number comes from the tables**: so README claims can never drift from the code again.

## `liquidity/synthetic.py`
Random data with the real TLC columns. Used by tests and `--demo`. Contains patterns *I* put in (thin zones slower, Lyft's `on_scene` empty), so its numbers are never findings.

## `liquidity/sql_runner.py` and `sql/`
Same questions in SQL for DuckDB. SQL skills matter for a product-analyst role: windowing (`time_bucket`, `LAG`, rolling `AVG`), `GROUP BY … HAVING`, CTEs, percentile (`quantile_cont`).

## `tests/test_core.py`
18 tests. Pattern: build 2–10 rows by hand, compute the expected answer by hand, assert. Examples: exact policy cost (`4.5 × 30 = 135`), ratio-of-sums vs mean-of-ratios (22.73 % vs 35 %), A/A false-positive rate.

---
## Pandas ↔ SQL cheat-sheet (interview favourite)
| Pandas | SQL |
|---|---|
| `df.groupby("hour")["eta"].mean()` | `SELECT hour, AVG(eta) FROM t GROUP BY hour` |
| `.quantile(0.9)` | `quantile_cont(eta, 0.9)` (DuckDB) / `PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY eta)` |
| `df[df.n >= 5]` after groupby | `HAVING COUNT(*) >= 5` |
| `df.assign(_long = eta > 8)["_long"].mean()` | `AVG((eta > 8)::INT)` |
| `.shift(1)` within group | `LAG(x) OVER (PARTITION BY zone ORDER BY t)` |
| `.rolling(6).mean()` | `AVG(x) OVER (… ROWS BETWEEN 5 PRECEDING AND CURRENT ROW)` |
| `.dt.floor("10min")` | `time_bucket(INTERVAL '10 minutes', ts)` |
