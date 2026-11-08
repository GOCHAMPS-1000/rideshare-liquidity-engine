# 05 · Experiment design: how we would prove the incentive works

## Why not a normal A/B test?
If half of the *riders* (or drivers) get the incentive, treated and control users still compete for the **same pool of drivers**. A treated driver who moves into Zone A leaves Zone B, so the control group is affected by the treatment. This is **interference** (SUTVA violation) and biases the estimate, usually *exaggerating* the effect.

## Chosen design: switchback by zone
- **Unit of randomisation:** (zone, time block), e.g. 2-hour blocks.
- **Assignment:** within each zone, randomly mark half of the blocks treatment (rule ON) and half control (rule OFF).
- **Why it works:** each zone is compared with *itself*, so permanent differences between zones (Manhattan vs Bronx) cancel out.
- **Block length trade-off:** the bonus lasts 30 min and drivers' behaviour carries over. Too short → carry-over contaminates the next block. Too long → few blocks, low power. 2 hours with the first 30 min of each block dropped as *washout* is a reasonable start.
- **Alternatives:** geo-cluster test (randomise whole zones: clean but low power); synthetic control (when only one city can be treated).

## Metrics
| | Metric |
|---|---|
| Primary | Long-wait share (> 8 min) per zone-block |
| Secondary | p90 wait, trips completed per block (liquidity ↑ should also raise volume) |
| Guardrails | Blended $/ride ≤ $2.50, mean wait < 6 min, driver cancellations < 4 %, **neighbour-zone** wait (displacement) |

## Analysis plan (write it *before* running; this is "pre-registration")
1. For each zone: mean(primary | treated blocks) − mean(primary | control blocks).
2. One-sample t-test across zones (the zone is the independent unit), or a regression with **zone and time-of-day fixed effects** and standard errors clustered by zone.
3. Report effect size with a 95 % CI, not only a p-value.
4. Check pre-treatment balance and run an **A/A** period first.
5. Multiple secondary metrics → correct for multiplicity (Bonferroni/Holm) or label them exploratory.

## Power: what the code computes
`reports/tables/11_sample_size.csv` gives trips per arm *if trips were independent*. That is optimistic. Trips in the same zone-block are correlated:

`effective n = n / DE`, `DE = 1 + (m − 1)·ρ`

Example (illustrative): a zone-block holds m = 200 trips and ρ = 0.02 → DE ≈ 4.98, so 10,000 trips behave like ~2,000. This is why the Monte-Carlo in `simulate_switchback_power` treats the **zone** as the unit and reports power for 14/28/56 blocks per zone (`12_switchback_power.csv`).

How to read it: pick the row where power ≥ 0.8 at your smallest *worthwhile* effect (e.g. a 15 % relative drop). The A/A column must sit near 0.05; if not, the analysis method is flawed.

*Important:* the simulation assumes a block-to-block noise level (`block_sd=0.03`) that I chose. With real data, estimate it from the pilot's A/A period and re-run.

## Threats to validity and responses
| Threat | Response |
|---|---|
| Carry-over between blocks | Washout period; compare first vs last hour of treated blocks |
| Time trends (weather, events) | Randomised order, time-of-day fixed effects |
| Novelty effect (drivers excited at first) | Run ≥ 2–4 weeks; check effect over time |
| Displacement to neighbours | Neighbour-zone guardrail; cluster-level analysis |
| Winner's curse / peeking | Fixed duration; no early stopping on p-values |
| Treatment compliance (drivers never see the alert) | Track alert delivery/acceptance; consider CACE/"treatment on treated" analysis |

## Decision rule (example)
Ship if the 95 % CI for the relative drop in long-wait share excludes 0, the point estimate ≥ the MDE, **and** all guardrails are inside limits. Otherwise iterate on the bonus formula and re-test.
