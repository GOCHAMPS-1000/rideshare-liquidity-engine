"""Tests with tiny hand-made data so every expected value can be checked by eye."""

import math

import numpy as np
import pandas as pd
import pytest

from liquidity import config as C
from liquidity import data, experiment, metrics, quality, simulate, synthetic


def make_trips(rows):
    """rows: (license, request, on_scene_or_None, pickup, zone, fare, pay)"""
    df = pd.DataFrame(
        rows,
        columns=["hvfhs_license_num", "request_datetime", "on_scene_datetime", "pickup_datetime", "PULocationID", "base_passenger_fare", "driver_pay"],
    )
    for c in ["request_datetime", "on_scene_datetime", "pickup_datetime"]:
        df[c] = pd.to_datetime(df[c])
    df["wav_request_flag"] = "N"
    df["wav_match_flag"] = "N"
    df["shared_request_flag"] = "N"
    df["shared_match_flag"] = "N"
    return data.prepare_trips(df)


# ---------------------------------------------------------------- features
def test_eta_and_rider_wait_minutes():
    df = make_trips([("HV0003", "2024-01-01 08:00:00", "2024-01-01 08:04:30", "2024-01-01 08:06:00", 1, 20.0, 15.0)])
    assert df.loc[0, "eta_min"] == pytest.approx(4.5)
    assert df.loc[0, "rider_wait_min"] == pytest.approx(6.0)
    assert df.loc[0, "company"] == "Uber"
    assert df.loc[0, "platform_take"] == pytest.approx(5.0)


def test_rush_is_weekday_only():
    # 2024-01-01 is a Monday, 2024-01-06 a Saturday; both at 08:00
    df = make_trips(
        [
            ("HV0003", "2024-01-01 08:00:00", "2024-01-01 08:03:00", "2024-01-01 08:04:00", 1, 10, 8),
            ("HV0003", "2024-01-06 08:00:00", "2024-01-06 08:03:00", "2024-01-06 08:04:00", 1, 10, 8),
        ]
    )
    assert df["is_rush"].tolist() == [True, False]


def test_window_start_floors_to_10_minutes():
    df = make_trips([("HV0003", "2024-01-01 08:17:59", "2024-01-01 08:20:00", "2024-01-01 08:21:00", 1, 10, 8)])
    assert df.loc[0, "window_start"] == pd.Timestamp("2024-01-01 08:10:00")


# ----------------------------------------------------------------- quality
def test_audit_flags_missing_on_scene_for_lyft():
    df = make_trips(
        [
            ("HV0003", "2024-01-01 08:00:00", "2024-01-01 08:03:00", "2024-01-01 08:04:00", 1, 10, 8),
            ("HV0005", "2024-01-01 08:00:00", None, "2024-01-01 08:04:00", 1, 10, 8),
            ("HV0005", "2024-01-01 09:00:00", None, "2024-01-01 09:04:00", 1, 10, 12),  # negative margin
        ]
    )
    a = quality.audit(df)
    assert a.loc["Lyft", "null_on_scene_pct"] == 100.0
    assert a.loc["Uber", "usable_eta_pct"] == 100.0
    assert a.loc["Lyft", "negative_margin_pct"] == 50.0


# ----------------------------------------------------------------- metrics
def test_eta_summary_percentiles_and_long_share():
    # ETAs 1..10 minutes for one company
    rows = [("HV0003", "2024-01-01 08:00:00", f"2024-01-01 08:{m:02d}:00", f"2024-01-01 08:{m+1:02d}:00", 1, 10, 8) for m in range(1, 11)]
    df = make_trips(rows)
    s = metrics.eta_summary(df, "company").loc["Uber"]
    assert s["trips"] == 10
    assert s["mean"] == pytest.approx(5.5)
    assert s["p50"] == pytest.approx(5.5)
    assert s["long_wait_share"] == pytest.approx(0.2)  # 9 and 10 exceed 8


def test_take_rate_is_ratio_of_sums_not_mean_of_ratios():
    df = make_trips(
        [
            ("HV0003", "2024-01-01 08:00:00", "2024-01-01 08:03:00", "2024-01-01 08:04:00", 1, 100.0, 80.0),  # 20 %
            ("HV0003", "2024-01-01 09:00:00", "2024-01-01 09:03:00", "2024-01-01 09:04:00", 1, 10.0, 5.0),    # 50 %
        ]
    )
    e = metrics.unit_economics(df).loc["Uber"]
    assert e["take_rate_pct"] == pytest.approx(100 * 25 / 110, abs=0.01)  # 22.727
    assert e["mean_of_ratios_pct"] == pytest.approx(35.0)


def test_zone_bottlenecks_ranks_by_volume_times_severity():
    # zone 1: 4 trips at 10 min (excess 4 each = 16); zone 2: 1 trip at 20 min (excess 14)
    rows = [("HV0003", "2024-01-01 08:00:00", "2024-01-01 08:10:00", "2024-01-01 08:11:00", 1, 10, 8)] * 4
    rows += [("HV0003", "2024-01-01 08:00:00", "2024-01-01 08:20:00", "2024-01-01 08:21:00", 2, 10, 8)]
    b = metrics.zone_bottlenecks(make_trips(rows), min_trips=1, target=6.0)
    assert b["PULocationID"].tolist() == [1, 2]  # zone 1 has more total excess although zone 2 is slower per trip
    assert b.loc[0, "excess_min"] == pytest.approx(16.0)
    assert b["cum_share_of_excess"].iloc[-1] == pytest.approx(1.0)
    assert metrics.zones_for_share(b, 0.5) == 1


def test_wav_unmet():
    df = make_trips([("HV0003", "2024-01-01 08:00:00", "2024-01-01 08:03:00", "2024-01-01 08:04:00", 1, 10, 8)] * 4)
    df["wav_request_flag"] = "Y"
    df["wav_match_flag"] = ["Y", "N", "N", "N"]
    w = metrics.wav_unmet(df, by="company", min_requests=1)
    assert w.loc["Uber", "unmet_share"] == pytest.approx(0.75)


# ---------------------------------------------------------------- simulate
def _windows():
    t0 = pd.Timestamp("2024-01-01 08:00:00")
    step = pd.Timedelta(minutes=10)
    # zone 1: stress 0.10, 0.50 (trigger), 0.10, 0.10, 0.10, 0.10, ... 10 trips each
    stresses = [0.10, 0.50, 0.10, 0.10, 0.10, 0.10]
    return pd.DataFrame(
        {
            "PULocationID": 1,
            "window_start": [t0 + i * step for i in range(len(stresses))],
            "trips": 10,
            "stress": stresses,
        }
    )


def test_simulate_policy_exact_numbers():
    p = simulate.PolicyParams(threshold=0.20, base_bonus=2.0, rate_multiplier=5.0, active_windows=3)
    r = simulate.simulate_policy(_windows(), p, margin_per_ride=6.0)
    # trigger at window 1 (stress .5) -> bonus = 2 + .5*5 = 4.5, live for windows 2,3,4 => 3 x 10 rides
    assert r["trigger_rate"] == pytest.approx(1 / 6, abs=1e-3)  # output is rounded to 4 dp
    assert r["covered_ride_share"] == pytest.approx(30 / 60)
    assert r["total_cost"] == pytest.approx(4.5 * 30)
    assert r["cost_per_covered_ride"] == pytest.approx(4.5)
    assert r["blended_cost_per_ride"] == pytest.approx(135 / 60)  # 2.25 < 2.50 cap
    assert r["within_budget"] is True
    assert r["breakeven_ride_lift_pct"] == pytest.approx(100 * 135 / (6.0 * 30))


def test_policy_min_bonus_exceeds_cap_per_covered_ride():
    """The PRD's own formula gives >= $3.00 per bonus ride, above its $2.50 cap:
    the cap only makes sense as a BLENDED per-ride number."""
    p = simulate.PolicyParams()
    assert simulate.bonus_amount(p.threshold, p) >= 3.0 > p.budget_cap


def test_no_trigger_means_no_cost():
    w = _windows().assign(stress=0.05)
    r = simulate.simulate_policy(w, simulate.PolicyParams(), 6.0)
    assert r["total_cost"] == 0 and r["trigger_rate"] == 0


def test_higher_threshold_never_costs_more():
    df = make_trips_big()
    w = simulate.build_windows(df, min_trips=3)
    sweep = simulate.sweep_thresholds(w, [0.1, 0.2, 0.3, 0.4], simulate.PolicyParams(), 6.0)
    assert sweep["total_cost"].is_monotonic_decreasing
    assert sweep["trigger_rate"].is_monotonic_decreasing


def make_trips_big():
    return data.prepare_trips(synthetic.make_synthetic_trips(n=60_000, days=3, n_zones=20, seed=1))


# -------------------------------------------------------------- experiment
def test_sample_size_matches_textbook_value():
    # 10 % -> 12 %, alpha .05, power .80: about 3,800-3,850 per arm
    n = experiment.sample_size_two_proportions(0.10, 0.12)
    assert 3800 <= n <= 3900


def test_mde_is_consistent_with_sample_size():
    n = experiment.sample_size_two_proportions(0.10, 0.12)
    assert experiment.mde_proportion(0.10, n) == pytest.approx(0.02, abs=0.003)


def test_design_effect():
    assert experiment.design_effect(1, 0.5) == 1
    assert experiment.design_effect(101, 0.01) == pytest.approx(2.0)


def test_switchback_aa_test_has_nominal_false_positive_rate():
    base = np.full(30, 0.15)
    fpr = experiment.simulate_switchback_power(base, 14, 0.0, n_sims=1500, seed=3)
    assert 0.02 <= fpr <= 0.09


def test_switchback_power_increases_with_effect_and_blocks():
    base = np.full(30, 0.15)
    small = experiment.simulate_switchback_power(base, 14, 0.05, n_sims=500, seed=3)
    big = experiment.simulate_switchback_power(base, 14, 0.30, n_sims=500, seed=3)
    assert big > small
    assert big > 0.8


# ---------------------------------------------------------------- pipeline
def test_demo_pipeline_end_to_end(tmp_path):
    from liquidity import run

    run.main(["--demo", "--out", str(tmp_path)])
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "figures" / "fig3_pareto.png").exists()
    assert "SYNTHETIC" in (tmp_path / "summary.md").read_text()
