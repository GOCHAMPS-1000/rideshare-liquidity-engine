"""Data-quality audit. Always run this BEFORE trusting any metric.

The v1 notebook silently dropped ~27 % of rows (anything with a missing or
out-of-range wait time) and never looked at WHO was dropped. This module makes
that visible.
"""

from __future__ import annotations

import pandas as pd

from . import config as C


def audit(df: pd.DataFrame) -> pd.DataFrame:
    """Per-company data-quality table (all values in %, except `trips`)."""
    by = df["company"]
    eta = df["eta_min"]
    out = pd.DataFrame(
        {
            "trips": by.value_counts(),
            "null_on_scene_pct": df["on_scene_datetime"].isna().groupby(by, observed=True).mean() * 100,
            "negative_eta_pct": (eta < C.ETA_MIN_VALID).groupby(by, observed=True).mean() * 100,
            "eta_above_cutoff_pct": (eta > C.ETA_MAX_VALID).groupby(by, observed=True).mean() * 100,
            "usable_eta_pct": eta.between(C.ETA_MIN_VALID, C.ETA_MAX_VALID).groupby(by, observed=True).mean() * 100,
            "negative_margin_pct": (df["platform_take"] < 0).groupby(by, observed=True).mean() * 100,
        }
    )
    return out.sort_values("trips", ascending=False).round(2)


def cutoff_sensitivity(df: pd.DataFrame, cutoffs=(15, 20, 30, 60, 120), col="eta_min") -> pd.DataFrame:
    """Do the headline numbers change if the outlier cutoff changes?

    If mean / p90 barely move across cutoffs, the conclusion is robust.
    If they move a lot, say so out loud in the write-up.
    """
    rows = []
    for c in cutoffs:
        s = df.loc[df[col].between(C.ETA_MIN_VALID, c), col]
        rows.append(
            {
                "cutoff_min": c,
                "trips_kept": len(s),
                "mean": s.mean(),
                "p50": s.median(),
                "p90": s.quantile(0.9),
                "long_wait_share": (s > C.LONG_WAIT_MIN).mean(),
            }
        )
    return pd.DataFrame(rows).round(3)
