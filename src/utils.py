"""
utils.py — Core probability and EV functions for NFL 2025 analytics.
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Moneyline helpers
# ---------------------------------------------------------------------------

def ml_to_implied_prob(ml) -> float:
    """Convert American moneyline to raw implied probability (includes vig)."""
    try:
        ml = float(ml)
    except (ValueError, TypeError):
        return None
    if ml == 100 or ml == -100:
        return 0.5
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return abs(ml) / (abs(ml) + 100)


def normalize_probs(p_away, p_home):
    """
    Basic normalization: remove vig by dividing each implied prob by their sum.
    Returns (true_away_prob, true_home_prob).
    """
    total = p_away + p_home
    return p_away / total, p_home / total


def shin_probs(p_away, p_home):
    """
    Shin (1993) method: iteratively solve for true probabilities assuming
    a proportion z of bets come from insiders.
    Returns (true_away_prob, true_home_prob).
    """
    q_i = np.array([p_away, p_home])
    total_q = q_i.sum()
    z = 0.0
    for _ in range(1000):
        denom = 2 * (1 - z)
        if abs(denom) < 1e-12:
            break
        numerator = np.sqrt(z**2 + 4 * (1 - z) * (q_i**2 / total_q))
        p_i = (numerator - z) / denom
        z_denom = total_q - 2 * np.sum(p_i**2 / total_q)
        if abs(z_denom) < 1e-12:
            break
        z_new = (total_q - 1) / z_denom
        if abs(z_new - z) < 1e-10:
            break
        z = z_new
    with np.errstate(invalid="ignore", divide="ignore"):
        numerator = np.sqrt(z**2 + 4 * (1 - z) * (q_i**2 / total_q))
        p_i = (numerator - z) / (2 * (1 - z))
    if np.any(np.isnan(p_i)):
        return float(q_i[0] / total_q), float(q_i[1] / total_q)
    return float(p_i[0]), float(p_i[1])


# ---------------------------------------------------------------------------
# EV calculation
# ---------------------------------------------------------------------------

def calc_ev(true_prob, ml):
    """
    Expected Value of a $100 bet.
    EV = (true_prob * profit_if_win) - ((1 - true_prob) * 100)
    """
    try:
        ml = float(ml)
    except (ValueError, TypeError):
        return None
    profit = ml if ml > 0 else (100 / abs(ml)) * 100
    return (true_prob * profit) - ((1 - true_prob) * 100)


# ---------------------------------------------------------------------------
# Data loading & preprocessing
# ---------------------------------------------------------------------------

BOOKS = ["bet365", "si", "betway", "betmgm", "fanduel", "caesars", "draftkings"]


def load_data(path):
    df = pd.read_excel(path)
    ml_cols = [c for c in df.columns if c.endswith("_away_ml") or c.endswith("_home_ml")]
    for col in ml_cols:
        df[col] = df[col].replace("EVEN", "100")
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def compute_book_probs(df, book, method="normalize"):
    """
    Convert moneylines to vig-free probabilities for a given book and method.
    Adds: {book}_true_away_{method}, {book}_true_home_{method}
    """
    fn = normalize_probs if method == "normalize" else shin_probs
    rows = []
    for _, row in df.iterrows():
        p_a = ml_to_implied_prob(row.get(f"{book}_away_ml"))
        p_h = ml_to_implied_prob(row.get(f"{book}_home_ml"))
        if p_a is not None and p_h is not None:
            ta, th = fn(p_a, p_h)
        else:
            ta, th = None, None
        rows.append((ta, th))
    new_cols = pd.DataFrame(rows, columns=[f"{book}_true_away_{method}", f"{book}_true_home_{method}"], index=df.index)
    return pd.concat([df, new_cols], axis=1)


def compute_consensus_prob(df, method="normalize"):
    """Average true probabilities across all books."""
    away_cols = [f"{b}_true_away_{method}" for b in BOOKS if f"{b}_true_away_{method}" in df.columns]
    home_cols = [f"{b}_true_home_{method}" for b in BOOKS if f"{b}_true_home_{method}" in df.columns]
    new_cols = pd.DataFrame({
        f"consensus_away_{method}": df[away_cols].mean(axis=1),
        f"consensus_home_{method}": df[home_cols].mean(axis=1),
    }, index=df.index)
    return pd.concat([df, new_cols], axis=1)
