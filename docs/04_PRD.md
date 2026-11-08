# 04 · PRD v2: Dynamic Supply Liquidity Incentive

**Owner:** Gonendra Verma · **Status:** analysis complete, experiment proposed · **Data:** NYC TLC HVFHV trips (completed trips only)

## 1. Problem
In some zones and 10-minute windows, rider requests outrun nearby idle drivers. Riders then wait long (or cancel), the platform loses rides, and drivers lose earnings. The shortage is **local and temporary**, so it can be fixed by *moving* supply, not by recruiting more drivers.

*Evidence to quote from your run* (copy the exact numbers from `reports/summary.md`): the long-wait share overall, the p90 wait, and "N of M zones hold 50 % of the excess waiting".

## 2. Goals and non-goals
**Goals**
1. Cut the share of long waits (> 8 min) in affected zone-windows.
2. Keep incentive spend inside budget.
3. Learn the supply *elasticity* (how many drivers move per $) with a clean experiment.

**Non-goals** (say these in interviews: scoping is a PM skill)
- Changing rider prices (surge) · long-term driver recruitment · airport/event special handling.

## 3. Metrics
| Role | Metric | Definition | Measurable with public data? |
|---|---|---|---|
| **North Star (production)** | Match rate | requests that end in a trip ÷ requests | ❌ needs internal search logs. The "72 % → 85 %" in v1 was an **illustrative assumption**, not an observation |
| **North Star (this analysis)** | Long-wait share | % of trips with request-to-arrival > 8 min | ✅ |
| Input metric | Idle drivers within the zone / relocation acceptance rate | | ❌ internal |
| Guardrail 1 | Blended incentive cost per ride | total bonus $ ÷ rides in affected zones; **≤ $2.50** | ✅ (simulated) |
| Guardrail 2 | Mean wait | stays < 6 min | ✅ |
| Guardrail 3 | Driver cancellation rate | < 4 % | ❌ internal |
| Guardrail 4 | Margin | platform take per ride after incentives stays positive | ✅ (approx.) |

**Why the cap is "blended".** The formula pays at least $3.00 on a bonus ride, which is above $2.50 by itself. The cap is therefore interpreted as *average spend across all rides in affected zones* (bonus rides + non-bonus rides).

## 4. Solution
**Trigger:** in a zone, if the stress rate over a 10-minute window exceeds **20 %** (stress = unfulfilled share in production; long-wait share as a proxy here) and the window has ≥ 5 requests.
**Offer:** to *idle drivers near the zone*, a relocation bonus
`bonus = $2.00 + stress × $5.00` (e.g. 30 % stress → $3.50), live for 30 minutes, paid when they complete a ride in the zone.
**Message:** "High demand in <Zone>! Complete 1 ride there in the next 30 minutes to earn +$3.50."

**Cost-control design choice (from the simulation).** Paying every ride in a live window also pays for rides that would have happened anyway. The simulation's `breakeven_ride_lift_pct` quantifies how many extra rides are needed for the bonus to pay for itself. If it is large, restrict the bonus to **drivers who relocated from outside the zone** (`eligible_share` < 1 in the code).

## 5. Edge cases and mitigations
| Scenario | Risk | Mitigation |
|---|---|---|
| Driver gaming (toggle online/offline to farm bonuses) | High | Must be online ≥ 15 min before qualifying; cap bonuses per driver per day |
| Phantom demand (fake requests inflate stress) | Medium | Count unique *authenticated* riders per window; require ≥ 5 requests |
| Gridlock (drivers can't reach the zone) | High | Extend bonus by 15 min when average speed < 10 mph |
| Small-sample noise fires the rule randomly | Medium | Minimum-request guard (`MIN_TRIPS_WINDOW`) |
| **Bonus chases supply out of neighbouring zones** (displacement) | Medium | Monitor neighbours as guardrail; cluster-level analysis in the experiment |
| Bonus anchors driver expectations ("I only work when there's a bonus") | Medium | Track organic supply in control blocks; cap frequency |
| Thin zones: rule almost never fires (few trips per window) | Medium | Use longer windows or a rolling average for low-volume zones |
| Weather/event spikes | Low | Pre-registered exclusion list, or treat as covariates |

## 6. Rollout
1. **Shadow mode** (log when the rule *would* fire, pay nothing) for 1–2 weeks → validates trigger rate vs this simulation.
2. **Switchback pilot** in ~20–40 zones (see `05_EXPERIMENT_DESIGN.md`).
3. Decision rule: ship if long-wait share falls by ≥ the pre-registered MDE **and** all guardrails hold.
4. Gradual ramp (25 % → 50 % → 100 % of eligible zones) with a hold-out group.

## 7. Open questions (honest list)
- True supply elasticity is unknown → that is what the pilot measures.
- Does the bonus shorten waits *or* just shift them to adjacent zones?
- Long-term effect on driver behaviour needs weeks of holdout data.
