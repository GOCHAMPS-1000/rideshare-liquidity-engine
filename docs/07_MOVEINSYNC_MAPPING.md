# 07 · Connecting this project to a Product Analyst role at MoveInSync

**Read this first:** I could not retrieve the actual job description (the job pages wouldn't load for me). What follows is based on my general understanding that MoveInSync builds software for corporate / employee commute and mobility. **Paste the JD to me** and I will tighten this page and your resume bullets against its exact wording.

## Same ideas, different context
| This project (ride-hailing) | Likely analogue in employee-commute software |
|---|---|
| Rider wait / ETA | Cab arrival delay, on-time pickup |
| Supply (drivers) vs demand (riders) imbalance by zone and time | Vehicles/seats vs employee roster demand by shift, route, time |
| Match / fulfilment rate | % of requested rides or seats fulfilled |
| Long-wait share, p90 | Delay tail: % of trips beyond an SLA |
| Incentive to rebalance supply | Allocation, routing or vendor/fleet incentives |
| Take rate, margin guardrail | Cost per trip / utilisation vs contract |
| Switchback experiment | Pilots by site, shift or time block (employees share vehicles → interference again) |
| Thin vs thick markets | Low-volume sites/routes vs large campuses |

## Skills this project demonstrates (typical for product-analyst roles)
- **SQL** (CTEs, windows, percentiles, `HAVING`), **Python/pandas**, data-quality auditing.
- **Metric design**: North Star, input and guardrail metrics, proxies.
- **Experimentation**: interference, switchback, power, A/A, pre-registration.
- **Product thinking**: PRD with edge cases, rollout plan, trade-offs.
- **Communication**: auto-generated summary, one-idea-per-chart.

## How to answer "Why MoveInSync?" from this project
Frame it around *reliability of mobility*: "In my project the hard part was a tail problem: averages looked fine while 1 in 10 riders waited too long. Employee commute has the same shape: an SLA is broken by the tail, not the mean."

## What I will do when you send the resume
1. Rewrite the project section into 3–4 quantified bullets using **your real run numbers**.
2. Mirror the JD's keywords honestly (only skills you can defend from this project).
3. Fit it into one page, ordered for a data/product-analyst reader.
