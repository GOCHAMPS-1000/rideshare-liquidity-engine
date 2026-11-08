# 01 · Concepts explained (basic → advanced)

Read this top to bottom once. Each item is written so you can say it out loud in an interview.

---
## A. The business idea (basic)

**Two-sided marketplace.** Riders (demand) and drivers (supply) both need to show up. If either side is thin, the product feels broken.

**Liquidity.** How easily a rider who wants a ride gets one, quickly. Practical measures: pickup wait time, share of requests that get a driver (*match rate* / *fulfilment rate*), cancellations.

**ETA / wait time.** Time between pressing "request" and the driver arriving. In this project: `eta_min = on_scene_datetime − request_datetime`. Note it is the *actual* arrival time, which is not identical to the ETA the app *promised*.

**Why wait time matters.** Long waits → riders cancel or switch apps → fewer trips → drivers earn less and leave → even fewer drivers. This is a *flywheel* that spins up or down.

**Supply–demand imbalance.** Often *local and temporary* (one zone, one 10-minute window). The company cannot simply "add drivers"; it must *move* them with incentives or pricing.

**Incentive vs surge pricing.** Surge raises prices to reduce demand and attract drivers; an incentive pays drivers to relocate without charging riders more. This project studies an incentive.

**Take rate.** Platform's cut: (rider fare − driver pay) / rider fare. It is the budget from which incentives must be paid.

---
## B. Metrics vocabulary (basic → intermediate)

| Term | Meaning | In this project |
|---|---|---|
| **North Star metric** | The one number that best captures the value delivered | Match rate in production; **long-wait share** with public data |
| **Input / driver metrics** | Levers that move the North Star | Idle drivers per zone, relocation acceptance |
| **Guardrail metric** | Must *not* get worse while you improve the target | Incentive cost per ride, driver cancellations, mean wait |
| **Proxy metric** | Measurable stand-in for something you can't measure | Long-wait share stands in for unfulfilled rate |
| **Funnel** | Ordered steps users pass through | search → request → match → pickup → trip |

**Why a proxy is needed here.** The TLC file has only *completed* trips. Requests that never got a driver are invisible. This is *survivorship bias*: you are looking only at the survivors of the funnel. Say this proactively; interviewers love candidates who spot it.

---
## C. Statistics you must be comfortable with (intermediate)

**Mean vs median vs percentile.** Wait times are right-skewed (a few very long waits). The mean is pulled up by them; the median ignores them; **p90** says "1 in 10 riders waits longer than this". Riders churn because of bad experiences, so tails matter.

**Long-wait share.** % of trips with wait > 8 min. Easy for non-technical stakeholders; maps directly to the PRD threshold.

**Ratio of sums vs mean of ratios.** Take rate over a group = total take ÷ total fare (ratio of sums). Averaging each trip's own ratio gives a different, noisier answer because cheap trips have extreme ratios. Test `test_take_rate_is_ratio_of_sums_not_mean_of_ratios` shows it with two trips.

**Small-sample noise.** A rate from 2 trips is 0 %, 50 % or 100 %: meaningless. So we set minimum counts (`MIN_TRIPS_ZONE`, `MIN_TRIPS_WINDOW`) before ranking or triggering.

**Why the v1 sample was a problem.** 50,000 rows out of ~19 million means a typical zone-hour has 0–2 trips. Use the full month with DuckDB/pandas.

**Spearman vs Pearson correlation.** Pearson measures *linear* relationship and is distorted by outliers; Spearman works on *ranks*, so it is robust for skewed data like trips-per-zone. Range −1…+1.

**Correlation ≠ causation.** A negative trips-vs-wait correlation does not prove "more demand causes faster pickups". It is consistent with the *density effect* (below), but also with busy zones simply being in dense Manhattan with many idle drivers nearby.

**Statistical vs practical significance.** With millions of rows, even a 0.01-minute difference is "significant". Always report *effect size* (minutes, percentage points), not just p-values.

**Simpson's paradox.** A trend in the whole data can reverse inside subgroups (e.g. overall wait looks flat but rises in every zone, because the mix of zones shifts by hour). Hence we slice by zone, hour and company.

---
## D. Marketplace-specific ideas (advanced)

**Thick vs thin markets / density effect.** When many riders and drivers are in one area, the nearest driver is closer. So busy zones tend to be *more* liquid; thin zones suffer. Practical consequence: the incentive is most valuable in *thin-but-active* zones and during demand surges, not everywhere.

**Network effects (local).** Liquidity in rideshare is *local* (per zone and time), unlike social networks. Therefore analysis and experiments must be at zone × time level.

**Interference / SUTVA violation.** Standard A/B tests assume one user's treatment doesn't affect another's outcome. In a marketplace, a treated driver who relocates *removes* supply from a control zone. Randomising riders or drivers individually therefore gives biased estimates.

**Switchback (time-based) experiment.** Randomly alternate treatment ON/OFF for a zone across time blocks (e.g. 2-hour blocks). Each zone is its own control. Cheap and avoids interference, but needs care with *carry-over* (bonus effects lingering into the next block) and *time trends*.

**Geo-cluster experiment.** Randomise whole zones/cities. Strong isolation, but few units → low power.

**Power, MDE, alpha.** *Alpha* = false-positive rate you tolerate (5 %). *Power* = chance to detect a real effect (80 %). *MDE* = smallest effect the test can reliably detect with your sample. Rule: decide the MDE you care about first, then compute the sample size.

**Design effect.** Trips in the same zone-block are correlated, so n trips ≠ n independent observations: effective n = n / (1 + (m−1)ρ). This is why the experiment's *unit* is the zone-block, not the trip.

**A/A test.** Run the test machinery with *no* treatment. It should reject the null about 5 % of the time. If it doesn't, the analysis is broken. `simulate_switchback_power(..., rel_effect=0)` does this.

**Incentive economics ("what you must believe").** If you pay a bonus on every ride in a live window, you also pay for rides that would have happened anyway. `breakeven_ride_lift_pct` tells you how many *extra* rides the policy must create to repay its cost from platform margin. A large number is the signal to pay only for *incremental* supply (drivers who relocated into the zone).

**Driver gaming / Goodhart's law.** When a measure becomes a target it stops being a good measure: drivers can go offline/online to trigger or farm bonuses. Hence the 15-minute online requirement in the PRD.

**Elasticity.** How strongly supply responds to a price/incentive change. Unknown here; it is the main thing the experiment must measure.
