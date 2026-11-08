# Results summary (real)

Generated automatically by `liquidity.run`; every number below comes from the tables in `tables/`.

## 1. Data quality (per company)
| company | trips | null_on_scene_pct | negative_eta_pct | eta_above_cutoff_pct | usable_eta_pct | negative_margin_pct |
|---|---|---|---|---|---|---|
| Uber | 14432755 | 0.0 | 0.89 | 0.01 | 99.09 | 10.37 |
| Lyft | 5231175 | 99.76 | 0.12 | 0.0 | 0.12 | 6.39 |

## 2. Wait time, request to arrival (`eta_min`)
| company | trips | mean | p50 | p90 | p95 | long_wait_share |
|---|---|---|---|---|---|---|
| Lyft | 6123 | 5.703 | 4.95 | 10.847 | 13.582 | 0.229 |
| Uber | 14301565 | 3.154 | 2.583 | 6.117 | 7.767 | 0.045 |

Rider wait, request to pickup (`rider_wait_min`, available for every company):
| company | trips | mean | p50 | p90 | p95 | long_wait_share |
|---|---|---|---|---|---|---|
| Lyft | 5133455 | 4.63 | 3.95 | 8.017 | 9.967 | 0.1 |
| Uber | 14333910 | 4.147 | 3.6 | 7.067 | 8.717 | 0.067 |

Rush hour (weekday commute hours) vs other times:
| is_rush | trips | mean | p50 | p90 | p95 | long_wait_share |
|---|---|---|---|---|---|---|
| False | 10244868 | 3.139 | 2.567 | 6.1 | 7.767 | 0.045 |
| True | 4062820 | 3.193 | 2.617 | 6.2 | 7.8 | 0.045 |

## 3. Where the excess waiting is
**41 of 250 zones** account for 50% of all excess wait above the 6-minute target.

Top 10 zones by excess wait:
| PULocationID | trips | mean_eta | p90_eta | long_wait_share | excess_min | cum_share_of_excess | Borough | Zone |
|---|---|---|---|---|---|---|---|---|
| 132 | 282639 | 5.681 | 10.9 | 0.231 | 412056.233 | 0.111 | Queens | JFK Airport |
| 138 | 247810 | 4.765 | 8.917 | 0.142 | 196431.583 | 0.164 | Queens | LaGuardia Airport |
| 230 | 189751 | 2.862 | 6.5 | 0.059 | 65628.833 | 0.181 | Manhattan | Times Sq/Theatre District |
| 61 | 183824 | 3.514 | 6.65 | 0.056 | 57814.983 | 0.197 | Brooklyn | Crown Heights North |
| 161 | 193750 | 2.783 | 6.2 | 0.05 | 54877.767 | 0.212 | Manhattan | Midtown Center |
| 148 | 143273 | 3.157 | 6.783 | 0.064 | 50837.583 | 0.225 | Manhattan | Lower East Side |
| 246 | 164559 | 2.923 | 6.117 | 0.047 | 47495.883 | 0.238 | Manhattan | West Chelsea/Hudson Yards |
| 79 | 197151 | 2.759 | 5.867 | 0.042 | 45756.567 | 0.25 | Manhattan | East Village |
| 37 | 149935 | 3.328 | 6.483 | 0.055 | 45345.4 | 0.263 | Brooklyn | Bushwick South |
| 76 | 145683 | 3.495 | 6.367 | 0.048 | 38940.85 | 0.273 | Brooklyn | East New York |

## 4. Does density help?
Spearman correlation, trips vs mean wait: zone level = **-0.539** (250 zones); zone-hour level = **-0.314** (171377 cells). Negative = busier is faster.

## 5. Unit economics
| company | trips | avg_fare | avg_driver_pay | avg_take | negative_margin_share | take_rate_pct | mean_of_ratios_pct |
|---|---|---|---|---|---|---|---|
| Lyft | 5224094 | 22.942 | 17.551 | 5.391 | 0.063 | 23.499 | 24.257 |
| Uber | 14432502 | 24.34 | 18.53 | 5.81 | 0.104 | 23.87 | 23.429 |

Average platform take per trip: **$5.69**

## 6. Incentive rule replay (PRD defaults: threshold 20%, base $2.0, x$5.0)
| threshold | windows | trigger_rate | covered_ride_share | total_cost | cost_per_covered_ride | blended_cost_per_ride | within_budget | breakeven_ride_lift_pct |
|---|---|---|---|---|---|---|---|---|
| 0.2 | 731295 | 0.038 | 0.0816 | 4322150.8 | 3.885 | 0.317 | True | 68.3 |

Threshold sweep:
| threshold | windows | trigger_rate | covered_ride_share | total_cost | cost_per_covered_ride | blended_cost_per_ride | within_budget | breakeven_ride_lift_pct |
|---|---|---|---|---|---|---|---|---|
| 0.1 | 731295 | 0.1185 | 0.2032 | 8821350.2 | 3.184 | 0.647 | True | 56.0 |
| 0.15 | 731295 | 0.0716 | 0.1248 | 6019832.99 | 3.539 | 0.442 | True | 62.2 |
| 0.2 | 731295 | 0.038 | 0.0816 | 4322150.8 | 3.885 | 0.317 | True | 68.3 |
| 0.25 | 731295 | 0.0282 | 0.0627 | 3510560.46 | 4.108 | 0.258 | True | 72.2 |
| 0.3 | 731295 | 0.0217 | 0.0492 | 2888447.6 | 4.304 | 0.212 | True | 75.6 |
| 0.35 | 731295 | 0.0162 | 0.0381 | 2337571.23 | 4.501 | 0.171 | True | 79.1 |
| 0.4 | 731295 | 0.0109 | 0.0287 | 1840314.84 | 4.699 | 0.135 | True | 82.6 |
| 0.45 | 731295 | 0.0081 | 0.0218 | 1450072.59 | 4.878 | 0.108 | True | 85.7 |
| 0.5 | 731295 | 0.0052 | 0.0153 | 1061223.84 | 5.083 | 0.08 | True | 89.3 |

## 7. Experiment design
Sample size per arm (trips) to detect a relative drop in long-wait share.
*Naive: assumes every trip is independent. Trips inside one zone-block are correlated, so the real requirement is larger by the design effect (see `docs/05_EXPERIMENT_DESIGN.md`).*
| relative_reduction | baseline_long_wait | target | n_per_arm_trips |
|---|---|---|---|
| 10% | 0.0453 | 0.0408 | 31511 |
| 15% | 0.0453 | 0.0385 | 13650 |
| 20% | 0.0453 | 0.0362 | 7478 |

Switchback power simulation (unit = zone):
| blocks_per_zone | A/A false-positive rate | power @15% relative drop |
|---|---|---|
| 14 | 0.052 | 0.849 |
| 28 | 0.057 | 0.972 |
| 56 | 0.049 | 1.0 |
