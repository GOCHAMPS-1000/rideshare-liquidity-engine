"""Marketplace-liquidity metrics.

Every function takes the prepared trips DataFrame (see data.prepare_trips) and
returns a small, readable DataFrame. No plotting here: calculation and
presentation are kept separate so each can be tested and explained alone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import config as C


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def valid(df: pd.DataFrame, col: str = "eta_min") -> pd.DataFrame:
    """Rows whose `col` is a plausible wait time (NaN is excluded automatically)."""
    return df.loc[df[col].between(C.ETA_MIN_VALID, C.ETA_MAX_VALID)]


def _as_list(by) -> list[str]:
    return [by] if isinstance(by, str) else list(by)


# --------------------------------------------------------------------------
# 1. Wait-time distribution
# --------------------------------------------------------------------------
def eta_summary(df: pd.DataFrame, by, col: str = "eta_min", long_wait_min: float = C.LONG_WAIT_MIN) -> pd.DataFrame:
    """Mean, median, p90, p95 and the share of 'long waits' per group.

    Why not just the mean?  A rider experiences THEIR wait, not the average.
    Two zones can both average 4 min while one has a p90 of 6 and the other 12.
    Tail metrics (p90 / long_wait_share) are what drive cancellations.
    """
    by = _as_list(by)
    d = valid(df, col)[by + [col]].copy()
    d["_long"] = d[col] > long_wait_min
    g = d.groupby(by, observed=True)
    out = g[col].agg(trips="size", mean="mean", p50="median")
    out["p90"] = g[col].quantile(0.90)
    out["p95"] = g[col].quantile(0.95)
    out["long_wait_share"] = g["_long"].mean()
    return out.round(3)


def hourly_dow_heatmap(df: pd.DataFrame, col: str = "eta_min", min_trips: int = 50) -> pd.DataFrame:
    """Long-wait share for each (day-of-week x hour) cell; sparse cells -> NaN."""
    d = valid(df, col)[["dow", "hour", col]].copy()
    d["_long"] = d[col] > C.LONG_WAIT_MIN
    g = d.groupby(["dow", "hour"])["_long"].agg(["mean", "size"])
    g.loc[g["size"] < min_trips, "mean"] = np.nan
    return g["mean"].unstack("hour")


# --------------------------------------------------------------------------
# 2. Where are the bottlenecks? (prioritisation)
# --------------------------------------------------------------------------
def zone_bottlenecks(
    df: pd.DataFrame,
    col: str = "eta_min",
    target: float = C.ETA_TARGET_MIN,
    min_trips: int = C.MIN_TRIPS_ZONE,
) -> pd.DataFrame:
    """Rank pickup zones by *excess wait minutes* and add a Pareto column.

    excess wait of one trip = max(wait - target, 0)
    zone score            = sum over its trips

    This is better than "highest average wait" because it multiplies severity
    by volume: a mildly slow zone with 50,000 trips can hurt more riders than a
    terrible zone with 200 trips. The cumulative share tells a PM how many
    zones to focus on to address, say, 50 % of the pain.
    """
    d = valid(df, col)[["PULocationID", col]].copy()
    d["excess"] = (d[col] - target).clip(lower=0)
    d["_long"] = d[col] > C.LONG_WAIT_MIN
    g = d.groupby("PULocationID")
    out = g[col].agg(trips="size", mean_eta="mean")
    out["p90_eta"] = g[col].quantile(0.90)
    out["long_wait_share"] = g["_long"].mean()
    out["excess_min"] = g["excess"].sum()
    out = out[out["trips"] >= min_trips].sort_values("excess_min", ascending=False)
    total = out["excess_min"].sum()
    out["cum_share_of_excess"] = out["excess_min"].cumsum() / total if total > 0 else np.nan
    return out.round(3).reset_index()


def attach_zone_names(table: pd.DataFrame, zones: pd.DataFrame | None) -> pd.DataFrame:
    """Join Borough / Zone names so tables are readable. No-op without a lookup."""
    if zones is None:
        return table
    return table.merge(zones[["PULocationID", "Borough", "Zone"]], on="PULocationID", how="left")


def zones_for_share(bottlenecks: pd.DataFrame, share: float = 0.5) -> int:
    """How many top zones are needed to cover `share` of all excess wait?"""
    return int((bottlenecks["cum_share_of_excess"] < share).sum() + 1)


# --------------------------------------------------------------------------
# 3. Does density help? (the "thick market" effect)
# --------------------------------------------------------------------------
def density_effect(df: pd.DataFrame, col: str = "eta_min", min_trips: int = C.MIN_TRIPS_ZONE) -> dict:
    """Spearman correlation between demand volume and wait time.

    Spearman (rank) correlation is used because both variables are heavily
    right-skewed: a few huge zones would dominate a Pearson correlation.

    Returns a dict with a zone-level and an hourly-cell-level correlation.
    A NEGATIVE rho means: busier => faster pickups (thick markets are more
    liquid). That is the opposite of what v1's README claimed.
    """
    d = valid(df, col)[["PULocationID", "request_datetime", col]]
    zone = d.groupby("PULocationID")[col].agg(trips="size", mean_eta="mean")
    zone = zone[zone["trips"] >= min_trips]
    rho_z, _ = stats.spearmanr(zone["trips"], zone["mean_eta"])

    cell = (
        d.assign(_h=d["request_datetime"].dt.floor("h"))
        .groupby(["PULocationID", "_h"])[col]
        .agg(trips="size", mean_eta="mean")
    )
    cell = cell[cell["trips"] >= 5]
    rho_c, _ = stats.spearmanr(cell["trips"], cell["mean_eta"])
    return {
        "zone_level_rho": round(float(rho_z), 3),
        "zones": int(len(zone)),
        "zone_hour_level_rho": round(float(rho_c), 3),
        "zone_hour_cells": int(len(cell)),
    }


def zone_scatter_table(df: pd.DataFrame, col: str = "eta_min", min_trips: int = C.MIN_TRIPS_ZONE) -> pd.DataFrame:
    d = valid(df, col)
    z = d.groupby("PULocationID")[col].agg(trips="size", mean_eta="mean").reset_index()
    return z[z["trips"] >= min_trips]


# --------------------------------------------------------------------------
# 4. Unit economics
# --------------------------------------------------------------------------
def unit_economics(df: pd.DataFrame, by="company") -> pd.DataFrame:
    """Fare, driver pay and platform take per trip, by group.

    take_rate_pct is a RATIO OF SUMS  (total take / total fare).
    mean_of_ratios_pct averages each trip's own ratio. They differ because
    cheap trips have unstable ratios; the ratio-of-sums is the one finance
    would report. We show both so you can explain the difference.

    Caveat: base_passenger_fare excludes tolls/taxes/fees and driver_pay
    excludes tips (TLC data dictionary), so `take` is an approximation of
    platform revenue, not an audited number.
    """
    by = _as_list(by)
    d = df.dropna(subset=["base_passenger_fare", "driver_pay"])
    d = d[d["base_passenger_fare"] > 0][by + ["base_passenger_fare", "driver_pay", "platform_take"]].copy()
    d["_neg"] = d["platform_take"] < 0
    d["_ratio"] = d["platform_take"] / d["base_passenger_fare"]
    g = d.groupby(by, observed=True)
    out = g.agg(
        trips=("platform_take", "size"),
        avg_fare=("base_passenger_fare", "mean"),
        avg_driver_pay=("driver_pay", "mean"),
        avg_take=("platform_take", "mean"),
        negative_margin_share=("_neg", "mean"),
    )
    out["take_rate_pct"] = 100 * g["platform_take"].sum() / g["base_passenger_fare"].sum()
    out["mean_of_ratios_pct"] = 100 * g["_ratio"].mean()
    return out.round(3)


def avg_margin_per_ride(df: pd.DataFrame) -> float:
    """Average platform take per trip over all usable trips ($)."""
    d = df.dropna(subset=["base_passenger_fare", "driver_pay"])
    return float(d["platform_take"].mean())


# --------------------------------------------------------------------------
# 5. Real unmet-demand signals hidden in the data
# --------------------------------------------------------------------------
def wav_unmet(df: pd.DataFrame, by="PULocationID", min_requests: int = 20) -> pd.DataFrame:
    """Share of wheelchair-accessible-vehicle requests NOT served by a WAV.

    The dataset only contains completed trips, so a true 'unfulfilled request'
    never appears. But a rider who asked for a WAV and got a normal car is a
    genuine supply miss, so this is the closest real fulfilment metric.
    """
    by = _as_list(by)
    d = df.loc[df["wav_request_flag"] == "Y", by + ["wav_match_flag"]].copy()
    d["_unmet"] = d["wav_match_flag"] != "Y"
    g = d.groupby(by, observed=True)["_unmet"].agg(requests="size", unmet_share="mean")
    return g[g["requests"] >= min_requests].round(3).sort_values("unmet_share", ascending=False)


def shared_unmatched(df: pd.DataFrame, by="hour") -> pd.DataFrame:
    """Share of shared-ride requests that did not end up pooled with someone."""
    by = _as_list(by)
    d = df.loc[df["shared_request_flag"] == "Y", by + ["shared_match_flag"]].copy()
    d["_unmatched"] = d["shared_match_flag"] != "Y"
    return d.groupby(by, observed=True)["_unmatched"].agg(requests="size", unmatched_share="mean").round(3)
