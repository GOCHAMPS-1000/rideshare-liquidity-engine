"""End-to-end pipeline.

Real data :  python -m liquidity.run --data data/raw/fhvhv_tripdata_2024-01.parquet \
                                     --zones data/raw/taxi_zone_lookup.csv
Demo      :  python -m liquidity.run --demo        (synthetic data, for testing)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from . import data, experiment, metrics, plots, quality, simulate, synthetic


def _md(df: pd.DataFrame, index: bool = True) -> str:
    """Tiny DataFrame -> markdown table (avoids needing the `tabulate` package)."""
    d = df.reset_index() if index else df
    head = "| " + " | ".join(map(str, d.columns)) + " |"
    sep = "|" + "|".join("---" for _ in d.columns) + "|"
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in d.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def run(trips: pd.DataFrame, zones: pd.DataFrame | None, out: Path, label: str, days: int | None = None) -> Path:
    out = Path(out)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    def save(df, name, index=True):
        df.to_csv(out / "tables" / f"{name}.csv", index=index)

    print("[1/7] preparing features")
    df = data.prepare_trips(trips, days=days)

    print("[2/7] data-quality audit")
    audit = quality.audit(df)
    sens = quality.cutoff_sensitivity(df)
    save(audit, "01_quality_audit")
    save(sens, "02_cutoff_sensitivity", index=False)

    print("[3/7] wait-time metrics")
    by_company = metrics.eta_summary(df, "company")
    by_company_rw = metrics.eta_summary(df, "company", col="rider_wait_min")
    hourly = metrics.eta_summary(df, "hour")
    rush = metrics.eta_summary(df, "is_rush")
    heat = metrics.hourly_dow_heatmap(df)
    for name, t in [("03_eta_by_company", by_company), ("04_riderwait_by_company", by_company_rw), ("05_eta_by_hour", hourly), ("06_eta_rush_vs_offpeak", rush)]:
        save(t, name)
    plots.plot_hourly_eta(hourly, out / "figures" / "fig1_hourly_eta.png")
    plots.plot_heatmap(heat, out / "figures" / "fig2_heatmap.png")

    print("[4/7] bottleneck prioritisation + density effect")
    bott = metrics.attach_zone_names(metrics.zone_bottlenecks(df), zones)
    save(bott, "07_zone_bottlenecks", index=False)
    dens = metrics.density_effect(df)
    plots.plot_pareto(bott, out / "figures" / "fig3_pareto.png")
    plots.plot_density(metrics.zone_scatter_table(df), dens["zone_level_rho"], out / "figures" / "fig4_density.png")

    print("[5/7] unit economics + real unmet-demand signals")
    econ = metrics.unit_economics(df)
    save(econ, "08_unit_economics")
    margin = metrics.avg_margin_per_ride(df)
    wav = metrics.wav_unmet(df, by="company", min_requests=20)
    save(wav, "09_wav_unmet_by_company")
    plots.plot_take_distribution(df, out / "figures" / "fig5_take.png")

    print("[6/7] incentive simulation (rule replay)")
    windows = simulate.build_windows(df)
    p = simulate.PolicyParams()
    base_case = simulate.simulate_policy(windows, p, margin)
    sweep = simulate.sweep_thresholds(windows, np.arange(0.10, 0.55, 0.05), p, margin)
    save(sweep, "10_policy_sweep", index=False)
    plots.plot_policy_sweep(sweep, p.budget_cap, out / "figures" / "fig6_policy_sweep.png")

    print("[7/7] experiment design")
    overall = metrics.valid(df)["eta_min"].gt(C.LONG_WAIT_MIN).mean()
    rows = []
    for rel in (0.10, 0.15, 0.20):
        n = experiment.sample_size_two_proportions(overall, overall * (1 - rel))
        rows.append({"relative_reduction": f"{rel:.0%}", "baseline_long_wait": round(overall, 4), "target": round(overall * (1 - rel), 4), "n_per_arm_trips": n})
    ss = pd.DataFrame(rows)
    save(ss, "11_sample_size", index=False)

    zone_base = (
        metrics.valid(df).assign(_l=lambda d: d["eta_min"] > C.LONG_WAIT_MIN).groupby("PULocationID")["_l"].agg(["mean", "size"])
    )
    zone_base = zone_base[zone_base["size"] >= C.MIN_TRIPS_ZONE]["mean"].head(40).to_numpy()
    pw = []
    for blocks in (14, 28, 56):
        pw.append(
            {
                "blocks_per_zone": blocks,
                "A/A false-positive rate": experiment.simulate_switchback_power(zone_base, blocks, 0.0, n_sims=1000),
                "power @15% relative drop": experiment.simulate_switchback_power(zone_base, blocks, 0.15, n_sims=1000),
            }
        )
    pw = pd.DataFrame(pw)
    save(pw, "12_switchback_power", index=False)

    banner = (
        "> **DEMO RUN ON SYNTHETIC DATA. These numbers are NOT findings.**\n\n" if label == "demo" else ""
    )
    top = bott.head(10)
    summary = f"""# Results summary ({label})

{banner}Generated automatically by `liquidity.run`; every number below comes from the tables in `tables/`.

## 1. Data quality (per company)
{_md(audit)}

## 2. Wait time, request to arrival (`eta_min`)
{_md(by_company)}

Rider wait, request to pickup (`rider_wait_min`, available for every company):
{_md(by_company_rw)}

Rush hour (weekday commute hours) vs other times:
{_md(rush)}

## 3. Where the excess waiting is
{zones_line(bott)}

Top 10 zones by excess wait:
{_md(top, index=False)}

## 4. Does density help?
Spearman correlation, trips vs mean wait: zone level = **{dens['zone_level_rho']}** ({dens['zones']} zones); zone-hour level = **{dens['zone_hour_level_rho']}** ({dens['zone_hour_cells']} cells). Negative = busier is faster.

## 5. Unit economics
{_md(econ)}

Average platform take per trip: **${margin:.2f}**

## 6. Incentive rule replay (PRD defaults: threshold {p.threshold:.0%}, base ${p.base_bonus}, x${p.rate_multiplier})
{_md(pd.DataFrame([base_case]), index=False)}

Threshold sweep:
{_md(sweep, index=False)}

## 7. Experiment design
Sample size per arm (trips) to detect a relative drop in long-wait share.
*Naive: assumes every trip is independent. Trips inside one zone-block are correlated, so the real requirement is larger by the design effect (see `docs/05_EXPERIMENT_DESIGN.md`).*
{_md(ss, index=False)}

Switchback power simulation (unit = zone):
{_md(pw, index=False)}
"""
    (out / "summary.md").write_text(summary)
    print(f"[done] wrote {out/'summary.md'}")
    return out / "summary.md"


def zones_line(bott: pd.DataFrame) -> str:
    n50 = metrics.zones_for_share(bott, 0.5)
    return f"**{n50} of {len(bott)} zones** account for 50% of all excess wait above the {C.ETA_TARGET_MIN:g}-minute target."


def main(argv=None):
    ap = argparse.ArgumentParser(description="Rideshare supply-liquidity analysis")
    ap.add_argument("--data", help="path to fhvhv_tripdata_YYYY-MM.parquet")
    ap.add_argument("--zones", help="path to taxi_zone_lookup.csv", default=None)
    ap.add_argument("--out", default=None, help="output folder (default reports/ or reports/demo/)")
    ap.add_argument("--days", type=int, default=None, help="use only the first N days (saves memory, keeps windows intact)")
    ap.add_argument("--demo", action="store_true", help="run on synthetic data")
    a = ap.parse_args(argv)

    if a.demo:
        trips = synthetic.make_synthetic_trips()
        zones = synthetic.make_zone_lookup()
        run(trips, zones, Path(a.out or "reports/demo"), "demo", days=a.days)
    else:
        if not a.data:
            ap.error("--data is required unless --demo is given")
        trips = data.load_trips(a.data)
        zones = data.load_zones(a.zones)
        run(trips, zones, Path(a.out or "reports"), "real", days=a.days)


if __name__ == "__main__":
    main()
