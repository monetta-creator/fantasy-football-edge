"""Opponent ADP model: where will each player be taken, with variance.

Each player's pick is modelled as Normal(adp, sigma). sigma grows with ADP (late
picks are far noisier) and with disagreement between ADP sources.
"""
from __future__ import annotations

from math import erf, sqrt

import numpy as np


def sigma_for(adp: float, spread: float = 0.0) -> float:
    base = 1.0 + 0.16 * adp
    return float(min(35.0, sqrt(base * base + (0.5 * spread) ** 2)))


def _phi(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def p_taken_before(adp: float, sigma: float, pick_no: int) -> float:
    """P(player is drafted before overall pick `pick_no`), i.e. by pick_no-1."""
    return _phi((pick_no - 0.5 - adp) / sigma)


def p_gone_by(adp: float, sigma: float, now_pick: int, target_pick: int) -> float:
    """P(gone before target_pick | still available at now_pick)."""
    if target_pick <= now_pick:
        return 0.0
    p_now = p_taken_before(adp, sigma, now_pick)
    p_target = p_taken_before(adp, sigma, target_pick)
    denom = 1.0 - p_now
    if denom <= 1e-9:
        return 1.0
    return float(min(1.0, max(0.0, (p_target - p_now) / denom)))


def norm_cdf(x: np.ndarray) -> np.ndarray:
    # numpy-only normal CDF via erf approximation (Abramowitz-Stegun 7.1.26), abs err < 1.5e-7
    x = np.asarray(x, dtype=float)
    z = x / sqrt(2.0)
    s = np.sign(z)
    a = np.abs(z)
    t = 1.0 / (1.0 + 0.3275911 * a)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-a * a)
    return 0.5 * (1.0 + s * y)


def p_gone_by_array(adp: np.ndarray, sigma: np.ndarray, now_pick: int, target_pick: int) -> np.ndarray:
    p_now = norm_cdf((now_pick - 0.5 - adp) / sigma)
    p_target = norm_cdf((target_pick - 0.5 - adp) / sigma)
    denom = np.clip(1.0 - p_now, 1e-9, None)
    out = (p_target - p_now) / denom
    out = np.where(denom <= 1e-6, 1.0, out)
    return np.clip(out, 0.0, 1.0)
