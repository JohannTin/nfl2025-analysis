"""
calibration.py — Model calibration metrics for NFL 2025 analytics.
"""

import numpy as np
import pandas as pd


def brier_score(probs: pd.Series, outcomes: pd.Series) -> float:
    """Mean squared error between predicted probabilities and binary outcomes."""
    return float(((probs - outcomes) ** 2).mean())


def brier_skill_score(bs_model: float, bs_reference: float) -> float:
    """
    BSS = 1 - (BS_model / BS_reference).
    Positive = better than reference. 0 = same. Negative = worse.
    """
    return 1 - (bs_model / bs_reference)


def reliability_diagram_data(probs: pd.Series, outcomes: pd.Series, n_bins: int = 10) -> pd.DataFrame:
    """
    Bin predicted probabilities and compute mean predicted vs. mean actual outcome per bin.
    Returns DataFrame with: bin_center, mean_pred, mean_actual, n, bin_label.
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_labels = pd.cut(probs, bins=bins, include_lowest=True)
    df = pd.DataFrame({"prob": probs, "outcome": outcomes, "bin": bin_labels})
    agg = (
        df.groupby("bin", observed=False)
        .agg(mean_pred=("prob", "mean"), mean_actual=("outcome", "mean"), n=("outcome", "count"))
        .reset_index()
    )
    agg["bin_center"] = bins[:-1] + (bins[1] - bins[0]) / 2
    agg["bin_label"] = agg["bin"].astype(str)
    return agg.dropna(subset=["mean_pred"])


def decompose_brier(probs: pd.Series, outcomes: pd.Series, n_bins: int = 10) -> dict:
    """
    Murphy (1973) decomposition: BS = Reliability - Resolution + Uncertainty.
    - Reliability: how far bins deviate from perfect calibration (lower = better)
    - Resolution:  how spread out bin means are from base rate (higher = better)
    - Uncertainty: irreducible noise from base rate
    """
    base_rate = outcomes.mean()
    rel_data = reliability_diagram_data(probs, outcomes, n_bins)
    n_total = len(outcomes)

    reliability = (rel_data["n"] / n_total * (rel_data["mean_pred"] - rel_data["mean_actual"]) ** 2).sum()
    resolution = (rel_data["n"] / n_total * (rel_data["mean_actual"] - base_rate) ** 2).sum()
    uncertainty = base_rate * (1 - base_rate)

    return {
        "brier_score": brier_score(probs, outcomes),
        "reliability": float(reliability),
        "resolution": float(resolution),
        "uncertainty": float(uncertainty),
        "base_rate": float(base_rate),
    }


def log_loss(probs: pd.Series, outcomes: pd.Series, eps: float = 1e-7) -> float:
    """Binary cross-entropy loss. Lower = better."""
    p = probs.clip(eps, 1 - eps)
    return float(-(outcomes * np.log(p) + (1 - outcomes) * np.log(1 - p)).mean())
