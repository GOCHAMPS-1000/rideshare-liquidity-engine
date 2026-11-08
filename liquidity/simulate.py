"""Replay the PRD's incentive rule on historical data.

THE BIG LIMITATION (say this first in any interview)
----------------------------------------------------
The TLC data contains only COMPLETED trips. We cannot see unfulfilled searches,
so the PRD's "unfulfilled rate" is not directly measurable. We use a proxy:

    stress rate of a zone-window = share of its trips whose wait exceeded
                                   LONG_WAIT_MIN (8 min)

This simulation therefore answers COST questions ("how often would the rule
fire, and what would it cost?") using real data. It does NOT claim the bonus
fixes waits: that needs an experiment (see experiment.py).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C
from .metrics import valid


@dataclass(frozen=True)
class PolicyParams:
    threshold: float = C.TRIGGER_THRESHOLD
    base_bonus: float = C.BASE_BONUS
    rate_multiplier: float = C.RATE_MULTIPLIER
    active_windows: int = C.ACTIVE_WINDOWS
    # Share of rides in a live-bonus window that actually receive the bonus.
    # 1.0 = pay everyone (upper bound on cost). Paying only drivers who
    # relocated INTO the zone would be a much smaller number.
    eligible_share: float = 1.0
    budget_cap: float = C.BUDGET_CAP_PER_RIDE


def bonus_amount(stress, p: PolicyParams):
    """PRD formula: base + stress_rate x multiplier (stress capped to [0, 1])."""
    return p.base_bonus + np.clip(stress, 0, 1) * p.rate_multiplier


def build_windows(
    df: pd.DataFrame,
    col: str = "eta_min",
    long_wait_min: float = C.LONG_WAIT_MIN,
    min_trips: int = C.MIN_TRIPS_WINDOW,
) -> pd.DataFrame:
    """One row per (pickup zone, 10-minute window) with its stress rate.

    Windows with fewer than `min_trips` trips are dropped: with 1 or 2 trips
    the 'rate' would jump between 0 % and 100 % purely by chance and the rule
    would fire randomly (small-sample noise).
    """
    d = valid(df, col)[["PULocationID", "window_start", col]].copy()
    d["_long"] = d[col] > long_wait_min
    w = (
        d.groupby(["PULocationID", "window_start"])["_long"]
        .agg(trips="size", stress="mean")
        .reset_index()
    )
    return w[w["trips"] >= min_trips].reset_index(drop=True)


def simulate_policy(windows: pd.DataFrame, p: PolicyParams, margin_per_ride: float) -> dict:
    """Apply the rule and total up the cost.

    Mechanics
    ---------
    1. A window TRIGGERS if stress > threshold.
    2. A trigger at time t makes a bonus live for the next `active_windows`
       windows of that zone (t+10, t+20, t+30 min). If several triggers
       overlap, the largest bonus is offered.
    3. Cost upper bound: every ride in a live window earns the bonus
       (scaled by `eligible_share`).
    """
    w = windows.copy()
    w["trigger"] = w["stress"] > p.threshold
    w["bonus"] = np.where(w["trigger"], bonus_amount(w["stress"], p), 0.0)

    trig = w.loc[w["trigger"], ["PULocationID", "window_start", "bonus"]]
    if len(trig):
        live = pd.concat(
            [
                trig.assign(window_start=trig["window_start"] + pd.Timedelta(minutes=C.WINDOW_MINUTES * k))
                for k in range(1, p.active_windows + 1)
            ]
        )
        live = (
            live.groupby(["PULocationID", "window_start"], as_index=False)["bonus"]
            .max()
            .rename(columns={"bonus": "offered_bonus"})
        )
        w = w.merge(live, on=["PULocationID", "window_start"], how="left")
        w["offered_bonus"] = w["offered_bonus"].fillna(0.0)
    else:
        w["offered_bonus"] = 0.0

    w["covered"] = w["offered_bonus"] > 0
    w["cost"] = w["offered_bonus"] * w["trips"] * p.eligible_share

    total_rides = int(w["trips"].sum())
    covered_rides = int(w.loc[w["covered"], "trips"].sum())
    total_cost = float(w["cost"].sum())

    triggered_zones = w.loc[w["trigger"], "PULocationID"].unique()
    rides_in_triggered_zones = int(w.loc[w["PULocationID"].isin(triggered_zones), "trips"].sum())

    blended_zone = total_cost / rides_in_triggered_zones if rides_in_triggered_zones else 0.0
    return {
        "threshold": p.threshold,
        "windows": len(w),
        "trigger_rate": round(float(w["trigger"].mean()), 4) if len(w) else 0.0,
        "covered_ride_share": round(covered_rides / total_rides, 4) if total_rides else 0.0,
        "total_cost": round(total_cost, 2),
        "cost_per_covered_ride": round(total_cost / covered_rides, 3) if covered_rides else 0.0,
        "blended_cost_per_ride": round(blended_zone, 3),
        "within_budget": bool(blended_zone <= p.budget_cap),
        # To pay for itself, covered windows must gain this many % more rides:
        "breakeven_ride_lift_pct": round(100 * total_cost / (margin_per_ride * covered_rides), 1)
        if covered_rides and margin_per_ride > 0
        else float("nan"),
    }


def sweep_thresholds(windows: pd.DataFrame, thresholds, p: PolicyParams, margin_per_ride: float) -> pd.DataFrame:
    """Re-run the simulation across trigger thresholds (sensitivity analysis)."""
    rows = [simulate_policy(windows, PolicyParams(**{**p.__dict__, "threshold": round(float(t), 4)}), margin_per_ride) for t in thresholds]
    return pd.DataFrame(rows)
