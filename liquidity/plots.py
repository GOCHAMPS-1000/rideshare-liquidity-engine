"""Charts. Matplotlib only (fewer dependencies, full control).

Design rules used throughout: one idea per chart, the title states the
takeaway's TOPIC, axes are labelled with units, one accent colour + grey.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files; no window needed
import matplotlib.pyplot as plt
import numpy as np

ACCENT = "#1f5fbf"
WARN = "#d9480f"
GREY = "#8a8f98"


def _style():
    plt.rcParams.update(
        {
            "figure.dpi": 130,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.titleweight": "bold",
            "axes.titlesize": 12,
            "font.size": 10,
        }
    )


def _save(fig, path: Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_hourly_eta(hourly, path, title="Wait time by hour of day: median vs p90"):
    """`hourly` = eta_summary(by='hour') output."""
    _style()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    h = hourly.index.get_level_values("hour")
    ax.fill_between(h, hourly["p50"], hourly["p90"], color=ACCENT, alpha=0.15, label="p50 to p90 range")
    ax.plot(h, hourly["p50"], color=ACCENT, marker="o", ms=3, label="median (p50)")
    ax.plot(h, hourly["p90"], color=WARN, marker="o", ms=3, label="p90 (1 in 10 waits is longer)")
    ax.set(xlabel="Hour of day (request time)", ylabel="Minutes from request to arrival", title=title)
    ax.set_xticks(range(0, 24, 2))
    ax.legend(frameon=False)
    return _save(fig, path)


def plot_heatmap(pivot, path, title="Share of waits longer than 8 min, by weekday and hour"):
    _style()
    fig, ax = plt.subplots(figsize=(9, 3.6))
    im = ax.imshow(pivot.values * 100, aspect="auto", cmap="YlOrRd")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][: len(pivot.index)])
    ax.set_xticks(range(0, len(pivot.columns), 2))
    ax.set_xticklabels(list(pivot.columns)[::2])
    ax.set(xlabel="Hour of day", title=title)
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="% of trips")
    return _save(fig, path)


def plot_pareto(bottlenecks, path, top=15, title="Where the excess waiting is concentrated"):
    _style()
    t = bottlenecks.head(top).iloc[::-1]
    label = t["Zone"].astype(str) if "Zone" in t else t["PULocationID"].astype(str)
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.barh(label, t["excess_min"] / 60, color=ACCENT)
    ax.set(xlabel="Excess wait above target (rider-hours)", title=title)
    ax2 = ax.twiny()
    ax2.plot(t["cum_share_of_excess"] * 100, label, color=WARN, marker="o", ms=3)
    ax2.set_xlabel("Cumulative % of all excess wait", color=WARN)
    ax2.set_xlim(0, 100)
    ax2.grid(False)
    return _save(fig, path)


def plot_density(zone_table, rho, path, title="Busier zones are NOT slower: density helps liquidity"):
    _style()
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.scatter(zone_table["trips"], zone_table["mean_eta"], s=22, color=ACCENT, alpha=0.7)
    ax.set_xscale("log")
    ax.set(xlabel="Trips in zone (log scale)", ylabel="Mean wait (min)", title=title)
    ax.text(0.97, 0.95, f"Spearman rho = {rho:+.2f}", transform=ax.transAxes, ha="right", va="top", color=GREY)
    return _save(fig, path)


def plot_take_distribution(df, path, title="Platform take per trip (fare minus driver pay)"):
    _style()
    s = df["platform_take"].dropna().clip(-20, 40)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(s, bins=80, color=ACCENT, alpha=0.85)
    ax.axvline(0, color=WARN, lw=1.2)
    ax.axvline(s.median(), color=GREY, ls="--", lw=1.2, label=f"median ${s.median():.2f}")
    ax.set(xlabel="$ per trip (clipped to -20..40)", ylabel="Trips", title=title)
    ax.legend(frameon=False)
    return _save(fig, path)


def plot_policy_sweep(sweep, cap, path, title="Incentive rule: how often it fires vs what it costs"):
    _style()
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.plot(sweep["threshold"] * 100, sweep["blended_cost_per_ride"], color=ACCENT, marker="o", label="blended $ per ride (triggered zones)")
    ax.axhline(cap, color=WARN, ls="--", label=f"budget cap ${cap:.2f}")
    ax.set(xlabel="Trigger threshold (% of trips with wait > 8 min)", ylabel="$ per ride", title=title)
    ax2 = ax.twinx()
    ax2.plot(sweep["threshold"] * 100, sweep["trigger_rate"] * 100, color=GREY, marker="s", ms=3, label="% of windows triggering")
    ax2.set_ylabel("% of zone-windows that trigger")
    ax2.grid(False)
    lines = ax.get_legend_handles_labels()
    lines2 = ax2.get_legend_handles_labels()
    ax.legend(lines[0] + lines2[0], lines[1] + lines2[1], frameon=False, loc="center right")
    return _save(fig, path)
