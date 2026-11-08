# 03 · What was wrong with v1, and what v2 changes

I reviewed your original notebook, README and the two chart images. v1 is a good *idea* (real data, a PRD, a clear product question), but several statements in it would not survive a sharp interviewer. Finding them first, and fixing them, makes a stronger story than hiding them.

## Problems found

| # | Issue in v1 | Evidence | v2 fix |
|---|---|---|---|
| 1 | **README says rush-hour waits "spike"**; the chart does not show it | In `chart1_wait_times.png` the Uber line stays roughly flat (about 2.5–4 min); the high points are overnight Lyft values | Hourly **p50 and p90** chart; rush vs off-peak table with `n`; conclusions generated from tables |
| 2 | **README says demand and ETA have a "strong positive correlation"**; the scatter slopes *down* | `chart2…png`, panel 3: more trips → lower wait for most zones | Spearman correlation computed (`density_effect`) and explained as the **density effect** |
| 3 | **"Match rate 72 % → 85 %" is not measured anywhere**; "waits above 8 min" is also asserted | The notebook never computes a match rate; the data holds only completed trips | PRD now separates *production* metric (match rate, needs internal logs) from the *measurable proxy* (long-wait share) |
| 4 | **Lyft data is mostly missing, silently** | 50,000 sampled → 36,390 kept (≈27 % lost); Lyft line has gaps/spikes (a 3 AM value near 19 min); chart 1 shows only Uber for the top zones. The TLC dictionary labels `on_scene_datetime` "Accessible Vehicles only" | `quality.audit` shows null-rate per company; cross-company comparison uses `rider_wait_min`, which exists for everyone |
| 5 | **Lyft unit economics are impossible**: driver pay ($29.53) > rider fare ($15.02) | `chart2…png`, panel 1. Those Lyft rows survived a filter on `on_scene`, so they are a tiny, unrepresentative subset | Unit economics computed on **all** trips with fare/pay, not only those with ETA; negative-margin share reported |
| 6 | **Only a 50,000-row sample** (~0.3 % of a month) | Largest zone in the scatter has ~650 trips | Full month via parquet column pruning (+ `--days` option) |
| 7 | **Mean-only metrics** | Bar/line charts of averages | Percentiles, long-wait share, excess-minutes Pareto |
| 8 | **Boxplot hides outliers** (`showfliers=False`) and the Lyft rush box is very narrow, which suggests very few rows behind it | `chart2…png`, panel 2 | Report `n` beside every statistic |
| 9 | **PRD guardrail contradicts its own formula** | Bonus ≥ $2 + 0.2×$5 = **$3.00** > $2.50 cap | Cap defined as *blended* $ per ride; test documents the issue |
| 10 | "Rush hour" counted on weekends | `is_rush` used hour only | Weekday-only rush |
| 11 | Zone IDs instead of names | Charts show 79, 132 … | Zone lookup joined (`attach_zone_names`) |
| 12 | No tests, no SQL, no experiment design, no cost model | n/a | 18 tests, 3 SQL files, power analysis + switchback simulation, break-even lift |

**Honest caveat on #4–#5:** I could not run your notebook's data pull here (the data host is blocked in my environment), so the *reason* Lyft's rows look odd is inferred from your charts and the TLC dictionary. Step 1 of your real run, `summary.md` section 1, will show the exact null rates. Quote *those*, not my inference.

## How to tell this story in an interview
> "My first version was an exploratory notebook on a 50k sample. When I reviewed it critically I found the README overclaimed: for example the correlation direction was wrong and Lyft's wait times were mostly missing. So I rebuilt it: full month of data, a data-quality audit, percentile metrics, a cost simulation of the incentive rule, and an experiment design that handles marketplace interference."

That answer shows self-review, rigour and ownership: exactly what a Product Analyst is hired for.
