"""Experiment design: sample size, MDE and a switchback power simulation.

Why this file exists
--------------------
A simulation on historical data cannot prove the incentive works. Only a
randomised experiment can. In a two-sided marketplace the naive design
(randomise riders or drivers) is flawed, because treated and control users
compete for the SAME drivers: the effect leaks between groups ("interference",
a violation of SUTVA). Standard fixes are switchback tests (alternate
treatment on/off over time blocks per zone) or geo-cluster tests.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import stats

from . import config as C


def sample_size_two_proportions(p_control: float, p_treat: float, alpha: float = C.ALPHA, power: float = C.POWER) -> int:
    """Per-arm n to detect p_control -> p_treat (two-sided z-test, unpooled)."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    var = p_control * (1 - p_control) + p_treat * (1 - p_treat)
    return math.ceil((z_a + z_b) ** 2 * var / (p_control - p_treat) ** 2)


def sample_size_means(sd: float, delta: float, alpha: float = C.ALPHA, power: float = C.POWER) -> int:
    """Per-arm n to detect a mean difference `delta` given standard deviation `sd`."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    return math.ceil(2 * ((z_a + z_b) * sd / delta) ** 2)


def mde_proportion(p_control: float, n_per_arm: int, alpha: float = C.ALPHA, power: float = C.POWER) -> float:
    """Smallest ABSOLUTE drop in a proportion detectable with n_per_arm (approx.)."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return z * math.sqrt(2 * p_control * (1 - p_control) / n_per_arm)


def design_effect(cluster_size: float, icc: float) -> float:
    """Variance inflation when observations come in correlated clusters.

    DE = 1 + (m - 1) * rho.  Effective sample size = n / DE.
    Trips inside one zone-block are not independent, so 10,000 trips may be
    worth only a few hundred independent observations.
    """
    return 1 + (cluster_size - 1) * icc


def simulate_switchback_power(
    zone_baselines,
    n_blocks: int,
    rel_effect: float,
    block_sd: float = 0.03,
    n_sims: int = 2000,
    alpha: float = C.ALPHA,
    seed: int = C.RANDOM_SEED,
) -> float:
    """Monte-Carlo power of a switchback test (the unit is the ZONE).

    Each zone alternates treatment on/off across `n_blocks` time blocks (half
    treated, random order). Per zone we take (treated mean - control mean) of
    the long-wait share, then run a one-sample t-test on those differences
    across zones. Pairing each zone with itself removes zone-to-zone
    differences, which is the whole point of a switchback.

    Set rel_effect=0 to run an A/A test: the 'power' returned is then the
    false-positive rate and should be close to alpha. ALWAYS check this.
    """
    rng = np.random.default_rng(seed)
    base = np.asarray(zone_baselines, dtype=float)
    n_zones = len(base)
    half = n_blocks // 2
    hits = 0
    for _ in range(n_sims):
        # Random assignment: for every zone, which blocks are treated.
        order = np.argsort(rng.random((n_zones, n_blocks)), axis=1)
        treated = np.zeros((n_zones, n_blocks), dtype=bool)
        np.put_along_axis(treated, order[:, :half], True, axis=1)
        mean = base[:, None] * (1 - rel_effect * treated)
        y = np.clip(mean + rng.normal(0, block_sd, size=mean.shape), 0, 1)
        diff = (y * treated).sum(1) / half - (y * ~treated).sum(1) / (n_blocks - half)
        p = stats.ttest_1samp(diff, 0.0).pvalue
        hits += p < alpha
    return hits / n_sims
