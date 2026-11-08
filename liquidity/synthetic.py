"""Synthetic trips with the REAL TLC schema.

Purpose: (1) unit tests, (2) a `--demo` mode you can run before downloading
the real 500 MB file.

!!  NEVER quote numbers produced from this data as findings.  !!
It is random data shaped like the real thing; its patterns are ones I put in.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic_trips(n: int = 200_000, days: int = 7, n_zones: int = 60, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2024-01-01")

    # Zipf-like zone popularity: a few very busy zones, a long thin tail.
    weights = 1 / np.arange(1, n_zones + 1) ** 1.1
    weights /= weights.sum()
    zone = rng.choice(np.arange(1, n_zones + 1), size=n, p=weights)

    # Time of day: morning and evening peaks.
    hour_w = np.array([2, 1, 1, 1, 1, 2, 4, 7, 8, 6, 5, 5, 5, 5, 5, 6, 8, 9, 9, 7, 6, 5, 4, 3], float)
    hour_w /= hour_w.sum()
    day = rng.integers(0, days, n)
    hour = rng.choice(24, size=n, p=hour_w)
    request = start + pd.to_timedelta(day, "D") + pd.to_timedelta(hour, "h") + pd.to_timedelta(rng.integers(0, 3600, n), "s")

    is_uber = rng.random(n) < 0.75
    thin = (zone > n_zones * 0.6).astype(float)  # thin markets wait longer
    rush = np.isin(hour, [7, 8, 9, 16, 17, 18, 19]).astype(float)
    mu = np.log(2.6) + 0.35 * thin + 0.10 * rush
    eta = rng.lognormal(mu, 0.65, n)  # minutes
    outlier = rng.random(n) < 0.002  # a few absurd waits, like real data
    eta[outlier] = rng.uniform(40, 90, outlier.sum())

    boarding = rng.uniform(0.3, 3.0, n)
    trip_min = rng.uniform(5, 40, n)
    fare = np.clip(rng.lognormal(np.log(20), 0.45, n), 6, 150)
    pay = fare * rng.normal(0.76, 0.10, n)

    def yn(p):
        return np.where(rng.random(n) < p, "Y", "N")

    wav_req = yn(0.015)
    shared_req = yn(0.03)
    df = pd.DataFrame(
        {
            "hvfhs_license_num": np.where(is_uber, "HV0003", "HV0005"),
            "request_datetime": request,
            # Lyft does not populate on_scene in the real data (check with quality.audit).
            "on_scene_datetime": pd.to_datetime(np.where(is_uber, request + pd.to_timedelta(eta, "m"), pd.NaT)),
            "pickup_datetime": request + pd.to_timedelta(eta + boarding, "m"),
            "PULocationID": zone.astype("int32"),
            "DOLocationID": rng.integers(1, n_zones + 1, n).astype("int32"),
            "trip_miles": rng.uniform(0.5, 15, n),
            "trip_time": (trip_min * 60).astype("int64"),
            "base_passenger_fare": fare.round(2),
            "tips": np.where(rng.random(n) < 0.2, rng.uniform(1, 8, n), 0.0).round(2),
            "driver_pay": pay.round(2),
            "shared_request_flag": shared_req,
            "shared_match_flag": np.where((shared_req == "Y") & (rng.random(n) < 0.4), "Y", "N"),
            "wav_request_flag": wav_req,
            "wav_match_flag": np.where((wav_req == "Y") & (rng.random(n) < 0.7), "Y", "N"),
        }
    )
    df["dropoff_datetime"] = df["pickup_datetime"] + pd.to_timedelta(trip_min, "m")
    return df


def make_zone_lookup(n_zones: int = 60) -> pd.DataFrame:
    boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx"]
    return pd.DataFrame(
        {
            "PULocationID": np.arange(1, n_zones + 1),
            "Borough": [boroughs[i % 4] for i in range(n_zones)],
            "Zone": [f"Demo Zone {i}" for i in range(1, n_zones + 1)],
        }
    )
