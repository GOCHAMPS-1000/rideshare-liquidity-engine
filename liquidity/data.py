"""Loading and feature-engineering the raw TLC trip records."""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

from . import config as C

TRIP_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_{ym}.parquet"
ZONE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"


def download(url: str, dest: Path) -> Path:
    """Download `url` to `dest` unless it already exists (idempotent)."""
    dest = Path(dest)
    if dest.exists():
        print(f"[data] already have {dest}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[data] downloading {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)
    return dest


def load_trips(path: str | Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Read only the needed columns from a parquet file.

    Parquet is *columnar*: reading 16 of ~25 columns really does read less
    from disk. That is the main reason a full month fits in a laptop's RAM.
    """
    return pd.read_parquet(path, columns=columns or C.TRIP_COLUMNS)


def load_zones(path: str | Path | None) -> pd.DataFrame | None:
    """Zone lookup: LocationID -> Borough, Zone. Returns None if not available."""
    if path is None or not Path(path).exists():
        return None
    z = pd.read_csv(path)
    return z.rename(columns={"LocationID": "PULocationID"})


def prepare_trips(df: pd.DataFrame, days: int | None = None) -> pd.DataFrame:
    """Add analysis columns. Mutates and returns `df` (saves memory on big data).

    New columns
    -----------
    company          Uber / Lyft / ... from the license code.
    eta_min          minutes from request to driver ARRIVING (needs on_scene).
    rider_wait_min   minutes from request to pickup (available for ALL firms,
                     includes the time the rider takes to board).
    hour, dow        hour of day (0-23) and day of week (0=Mon).
    is_weekend, is_rush   rush = commute hours on weekdays only.
    window_start     request time floored to the PRD's 10-minute window.
    platform_take    base_passenger_fare - driver_pay (see docs for caveats).
    """
    if days is not None:
        start = df["request_datetime"].min().normalize()
        df = df[df["request_datetime"] < start + pd.Timedelta(days=days)].copy()

    df["company"] = (
        df["hvfhs_license_num"].map(C.LICENSE_MAP).fillna("Other").astype("category")
    )
    req = df["request_datetime"]
    df["eta_min"] = (df["on_scene_datetime"] - req).dt.total_seconds() / 60.0
    df["rider_wait_min"] = (df["pickup_datetime"] - req).dt.total_seconds() / 60.0

    df["hour"] = req.dt.hour.astype("int8")
    df["dow"] = req.dt.dayofweek.astype("int8")
    df["is_weekend"] = df["dow"] >= 5
    df["is_rush"] = df["hour"].isin(C.RUSH_HOURS) & ~df["is_weekend"]
    df["window_start"] = req.dt.floor(f"{C.WINDOW_MINUTES}min")
    df["platform_take"] = df["base_passenger_fare"] - df["driver_pay"]
    return df
