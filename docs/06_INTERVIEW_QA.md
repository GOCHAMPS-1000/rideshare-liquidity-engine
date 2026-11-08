# 06 · Interview Q&A (basic → advanced)

Answers are short on purpose: say them in your own words. Replace `[X]` with real numbers from your `reports/summary.md`. **Never quote a number you haven't seen in your own run.**

---
## LEVEL 1 · Basic (project and metrics)

**1. Describe the project in 30 seconds.**
I analysed ~19 M NYC Uber/Lyft trips to find where rideshare supply fails to meet demand, measured how bad and how concentrated it is, replayed a proposed driver-incentive rule on history to estimate its cost, and designed the experiment that would prove it works.

**2. Why this problem?**
In a marketplace, liquidity (fast pickups) drives retention on both sides. Shortages are local and short-lived, so targeted incentives are a classic product lever.

**3. What data did you use and what's in it?**
NYC TLC High-Volume FHV trip records, one month (Jan 2024): request/arrival/pickup times, pickup zone, fare, driver pay, WAV and shared flags. Completed trips only.

**4. What is "ETA" in your project?**
`on_scene − request`, in minutes: how long the rider waited until the driver arrived.

**5. Why use percentiles, not just the average?**
Waits are right-skewed; riders churn from bad experiences, which sit in the tail. Two zones can share a mean but differ hugely in p90.

**6. What is take rate and how did you calculate it?**
(fare − driver pay) ÷ fare, as total ÷ total (ratio of sums). Approximation: fare excludes tolls/taxes/fees and driver pay excludes tips.

**7. What was your North Star and why?**
Production: match rate. Not measurable in public data (only completed trips), so I used long-wait share (> 8 min) as a clearly-labelled proxy.

**8. What are guardrail metrics? Give yours.**
Metrics that must not degrade while improving the target: incentive cost per ride, mean wait, driver cancellations, margin.

---
## LEVEL 2 · Intermediate (data work and stats)

**9. How did you clean the data? What did you drop?**
Kept waits between 0 and 30 min. I audited drops per company first (`quality.audit`), because the missing values are not random: Lyft's arrival timestamp appears largely empty ([X] % null in my audit). I also ran a cutoff-sensitivity table to show conclusions don't depend on 30.

**10. How did you handle Lyft?**
ETA metrics rest on `on_scene`, which Lyft mostly lacks, so cross-company comparisons use `rider_wait_min` (request → pickup), which every company reports. I say plainly that ETA findings are effectively Uber's.

**11. How did you find priority zones?**
Excess wait = Σ max(wait − 6 min, 0) per zone. It weights severity by volume. The cumulative share (Pareto) shows how many zones cover 50 % of the pain: [X of Y].

**12. Why minimum trip counts?**
With few trips, rates are random (2 trips → 0/50/100 %). Guards: ≥ 500 trips per zone for ranking, ≥ 5 per 10-minute window for triggering.

**13. Correlation between demand and wait: what did you find?**
Spearman ρ = [X] at zone level. [If negative:] Busier zones are *faster*, consistent with the density effect. I note it's correlational.

**14. Why Spearman?**
Trips per zone are heavily skewed; ranks resist outliers and capture monotonic (not only linear) relationships.

**15. Ratio of sums vs mean of ratios?**
Aggregate take rate must be total take / total fare; averaging per-trip ratios over-weights cheap trips. Example in `test_core.py` gives 22.7 % vs 35 %.

**16. What did the full month change vs a 50 k sample?**
Samples that small leave 0–2 trips per zone-hour, so rankings and window triggers become noise. DuckDB/parquet column pruning makes the full month feasible on a laptop.

**17. SQL: write the share of trips with wait > 8 min per hour.**
```sql
SELECT hour(request_datetime) AS hr,
       AVG((date_diff('second', request_datetime, on_scene_datetime)/60.0 > 8)::INT) AS long_wait_share
FROM trips WHERE on_scene_datetime IS NOT NULL GROUP BY hr ORDER BY hr;
```
(Mention: add the 0–30 filter in a CTE.)

**18. What's the difference between `WHERE` and `HAVING`?**
`WHERE` filters rows before grouping; `HAVING` filters groups after aggregation (used for the ≥ 5 trips guard).

**19. When does LAG give a wrong answer here?**
LAG looks at the previous *row*, not the previous 10 minutes; if sparse windows were filtered out, "previous" can be 30 min earlier. In pandas I merge on exact shifted timestamps.

**20. Statistical vs practical significance?**
At millions of rows everything is "significant". I report effect sizes (minutes, percentage points) and confidence intervals.

---
## LEVEL 3 · Advanced (product, causality, experimentation)

**21. Can your simulation prove the incentive works?**
No. It replays the rule on history with behaviour held fixed: good for trigger frequency and cost, silent on causal effect. Proof needs an experiment.

**22. Why not a normal A/B test?**
Interference: treated and control share one pool of drivers, so effects leak (SUTVA violation) and bias the estimate. Use switchback by zone or geo-cluster.

**23. Explain your switchback design.**
Per zone, random half of time blocks ON, half OFF; compare each zone with itself, then test the differences across zones. Washout handles carry-over; randomised order handles time trends.

**24. How do you size it?**
Choose the smallest worthwhile effect (MDE), account for correlation (design effect 1 + (m−1)ρ), and run a Monte-Carlo with the zone as the unit. Also run an A/A to confirm ≈ 5 % false positives.

**25. What is an A/A test for?**
To validate the pipeline: with no treatment it should "find" an effect only α of the time. If not, randomisation or the analysis is broken.

**26. How can the bonus fail even if waits fall?**
Displacement (drivers leave neighbouring zones), gaming, cost > margin, anchoring driver expectations, novelty effect.

**27. Your PRD's cap is $2.50 but the bonus starts at $3.00. Explain.**
The cap is blended across all rides in affected zones, not per bonus ride. I made that explicit and tested it; it was an inconsistency in my first draft.

**28. How would you make the incentive cheaper?**
Pay only drivers who relocate into the zone (`eligible_share` < 1), raise the threshold, shorten the live window. The sweep chart shows cost vs trigger frequency.

**29. What is break-even ride lift?**
Total bonus cost ÷ (average platform margin × covered rides): the % extra rides the policy must create to repay itself. A big number means you are paying for rides that would have happened anyway.

**30. How would you measure *true* unfulfilled demand?**
Internal search/request logs: requests with no match. In public data the nearest signals are WAV requests not served by a WAV and shared requests not pooled; I report both.

**31. Survivorship bias?**
Data has only completed trips, so riders who gave up are invisible; true waits are *worse* than measured. My metrics are lower bounds on the problem.

**32. What would you do next with more time/data?**
Join weather and events; multi-month seasonality; model hourly demand to anticipate shortages rather than react; estimate supply elasticity from the pilot; build a live dashboard.

**33. What is CUPED?**
A variance-reduction method that adjusts the experiment metric using a pre-experiment covariate (e.g. last month's long-wait share of the same zone), shrinking the sample needed.

**34. What if two metrics conflict (waits fall, margin falls)?**
Decide by the pre-registered rule: guardrails are constraints, not trade-offs. If margin breaches, iterate on the formula and retest.

**35. How do you handle multiple comparisons?**
One pre-registered primary metric; secondary ones corrected (Holm/Bonferroni) or labelled exploratory.

---
## Hard "gotcha" questions: honest answers

**"Your numbers come from one month, in one city."** True: seasonality and city specifics limit generality; the *method* transfers, thresholds need recalibration.

**"The 72 % match rate?"** It was an illustrative baseline in my first draft. I now state it is not observable with public data and use a proxy.

**"Why did you rebuild?"** I audited v1, found my README overclaimed (see `03_AUDIT_OF_V1.md`), and fixed it. That's the habit I'd bring to the team.
