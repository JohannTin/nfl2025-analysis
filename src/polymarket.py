"""
polymarket.py — Polymarket data extraction for NFL 2025 analytics.
"""

import json
import requests
import pandas as pd

BASE_GAMMA = "https://gamma-api.polymarket.com"
BASE_CLOB  = "https://clob.polymarket.com"

# ---------------------------------------------------------------------------
# Team name → Polymarket slug abbreviation
# ---------------------------------------------------------------------------

TEAM_SLUG = {
    "Arizona Cardinals":     "ari",
    "Atlanta Falcons":       "atl",
    "Baltimore Ravens":      "bal",
    "Buffalo Bills":         "buf",
    "Carolina Panthers":     "car",
    "Chicago Bears":         "chi",
    "Cincinnati Bengals":    "cin",
    "Cleveland Browns":      "cle",
    "Dallas Cowboys":        "dal",
    "Denver Broncos":        "den",
    "Detroit Lions":         "det",
    "Green Bay Packers":     "gb",
    "Houston Texans":        "hou",
    "Indianapolis Colts":    "ind",
    "Jacksonville Jaguars":  "jax",
    "Kansas City Chiefs":    "kc",
    "Las Vegas Raiders":     "lv",
    "Los Angeles Chargers":  "lac",
    "Los Angeles Rams":      "la",
    "Miami Dolphins":        "mia",
    "Minnesota Vikings":     "min",
    "New England Patriots":  "ne",
    "New Orleans Saints":    "no",
    "New York Giants":       "nyg",
    "New York Jets":         "nyj",
    "Philadelphia Eagles":   "phi",
    "Pittsburgh Steelers":   "pit",
    "San Francisco 49ers":   "sf",
    "Seattle Seahawks":      "sea",
    "Tampa Bay Buccaneers":  "tb",
    "Tennessee Titans":      "ten",
    "Washington Commanders": "was",
}


# ---------------------------------------------------------------------------
# Slug construction
# ---------------------------------------------------------------------------

def build_slug(away_team: str, home_team: str, date: str) -> str:
    """
    Build the Polymarket event slug.
    Example: build_slug('Dallas Cowboys', 'Philadelphia Eagles', '2025-09-04')
             -> 'nfl-dal-phi-2025-09-04'
    """
    away = TEAM_SLUG.get(away_team, "")
    home = TEAM_SLUG.get(home_team, "")
    if not away:
        raise ValueError(f"Unknown away team: '{away_team}'")
    if not home:
        raise ValueError(f"Unknown home team: '{home_team}'")
    return f"nfl-{away}-{home}-{date}"


# ---------------------------------------------------------------------------
# Token ID extraction
# Token IDs live in market["clobTokenIds"] as a JSON string:
#   "[\"token_away\", \"token_home\"]"
# index 0 = away / outcome[0], index 1 = home / outcome[1]
# ---------------------------------------------------------------------------

def _parse_clob_tokens(market: dict) -> list:
    """Parse clobTokenIds JSON string into a list of two token ID strings."""
    raw = market.get("clobTokenIds", "[]")
    try:
        tokens = json.loads(raw)
        return tokens if isinstance(tokens, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_outcome_prices(market: dict) -> list:
    """Parse outcomePrices JSON string into a list of floats."""
    raw = market.get("outcomePrices", "[]")
    try:
        prices = json.loads(raw)
        return [float(p) for p in prices]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def _is_moneyline(market: dict) -> bool:
    """
    Identify the moneyline market.
    Polymarket uses "TeamA vs. TeamB" format with no spread or O/U in the question.
    """
    q = market.get("question", "").lower()
    return (
        "vs." in q
        and "spread" not in q
        and "o/u" not in q
        and "total" not in q
        and "over" not in q
        and "under" not in q
    )


def _is_spread(market: dict) -> bool:
    q = market.get("question", "").lower()
    return "spread" in q and "1h" not in q


def _is_total(market: dict) -> bool:
    """
    Only match the game-level total (e.g. 'Seahawks vs. Patriots: O/U 46.5').
    Excludes player props, team totals, and 1st half totals.
    Game totals follow the pattern: 'TeamA vs. TeamB: O/U X'
    """
    q = market.get("question", "").lower()
    return "vs." in q and "o/u" in q and "1h" not in q


# ---------------------------------------------------------------------------
# Event fetching
# ---------------------------------------------------------------------------

def fetch_event(slug: str) -> dict | None:
    """Fetch event + all markets by slug. Returns event dict or None."""
    try:
        r = requests.get(
            f"{BASE_GAMMA}/events",
            params={"slug": slug},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        return data[0] if data else None
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Event fetch failed [{slug}]: {e}")
        return None


# ---------------------------------------------------------------------------
# Closing price  (directly from outcomePrices — no extra API call needed)
# ---------------------------------------------------------------------------

def extract_closing_price(event: dict, side: str = "away") -> float | None:
    """
    Get the closing moneyline probability from outcomePrices.
    outcomePrices = ["p_away", "p_home"] as a JSON string on the market.
    side: 'away' (index 0) or 'home' (index 1)
    """
    idx = 0 if side == "away" else 1
    for market in event.get("markets", []):
        if not _is_moneyline(market):
            continue
        prices = _parse_outcome_prices(market)
        if len(prices) > idx:
            return prices[idx]
    return None


def extract_opening_price(event: dict, side: str = "away") -> float | None:
    """First data point in the full price history = opening price."""
    idx = 0 if side == "away" else 1
    for market in event.get("markets", []):
        if not _is_moneyline(market):
            continue
        tokens = _parse_clob_tokens(market)
        if len(tokens) > idx:
            history = fetch_price_history(tokens[idx], interval="max", fidelity=720)
            if history:
                return float(history[0]["p"])
    return None


# ---------------------------------------------------------------------------
# Price history  (CLOB API)
# ---------------------------------------------------------------------------

def fetch_price_history(token_id: str, interval: str = "max", fidelity: int = 720) -> list:
    """
    Fetch price history for a token from the CLOB API.

    IMPORTANT: For resolved/closed markets (all NFL 2025 games are resolved),
    the API only returns data at fidelity >= 720 (12 hours in minutes).
    Requesting finer granularity returns empty history.

    interval: 'max' returns the full lifetime of the market
    fidelity: minutes per data point (720 = 12h, minimum for closed markets)
    Returns list of {"t": unix_timestamp, "p": probability}
    """
    try:
        r = requests.get(
            f"{BASE_CLOB}/prices-history",
            params={"market": token_id, "interval": interval, "fidelity": fidelity},
            timeout=10
        )
        r.raise_for_status()
        return r.json().get("history", [])
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Price history failed [token {token_id[:12]}...]: {e}")
        return []


def history_to_df(history: list, team: str, side: str) -> pd.DataFrame:
    """Convert raw history list to a clean DataFrame."""
    if not history:
        return pd.DataFrame()
    df = pd.DataFrame(history)
    df.rename(columns={"t": "timestamp", "p": "probability"}, inplace=True)
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
    df["team"] = team
    df["side"] = side
    return df[["timestamp", "datetime", "team", "side", "probability"]]


def extract_6h_history(event: dict, away_team: str, home_team: str) -> pd.DataFrame:
    """
    Get moneyline price trajectory for both teams across the full market lifetime.

    Note: For resolved markets the CLOB API only returns 12-hour granularity,
    so this returns the full lifetime trajectory at 12H intervals rather than
    a literal 6H pre-kickoff window. Label columns accordingly.
    """
    frames = []
    for market in event.get("markets", []):
        if not _is_moneyline(market):
            continue
        tokens = _parse_clob_tokens(market)
        if len(tokens) < 2:
            continue
        for idx, (side, team) in enumerate([("away", away_team), ("home", home_team)]):
            history = fetch_price_history(tokens[idx], interval="max", fidelity=720)
            df = history_to_df(history, team, side)
            if not df.empty:
                frames.append(df)
        break  # only process first moneyline market

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).sort_values("timestamp").reset_index(drop=True)

def extract_spread_history(event: dict, away_team: str, home_team: str) -> pd.DataFrame:
    """
    Get price history for all spread markets in the event.
    Each row includes the spread value so you can filter to a specific line.
    Returns combined DataFrame for all spread lines, both sides.
    """
    frames = []
    for market in event.get("markets", []):
        if not _is_spread(market):
            continue

        tokens = _parse_clob_tokens(market)
        if len(tokens) < 2:
            continue

        # Parse the spread value from the question
        # Format: "Spread: Eagles (-7.5)" or "Spread: Cowboys (+7.5)"
        q = market.get("question", "")
        spread_value = _parse_line_from_question(q)

        for idx, (side, team) in enumerate([("away", away_team), ("home", home_team)]):
            history = fetch_price_history(tokens[idx], interval="max", fidelity=720)
            df = history_to_df(history, team, side)
            if not df.empty:
                df["market_type"] = "spread"
                df["line"]        = spread_value
                df["question"]    = q
                frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).sort_values(["line", "timestamp"]).reset_index(drop=True)


def extract_total_history(event: dict, away_team: str, home_team: str) -> pd.DataFrame:
    """
    Get price history for all total (O/U) markets in the event.
    Each row includes the total line value.
    Returns combined DataFrame for all total lines, both over and under.
    """
    frames = []
    for market in event.get("markets", []):
        if not _is_total(market):
            continue

        tokens = _parse_clob_tokens(market)
        if len(tokens) < 2:
            continue

        # Format: "Cowboys vs. Eagles: O/U 47.5"
        q = market.get("question", "")
        total_value = _parse_line_from_question(q)

        # token[0] = over, token[1] = under
        for idx, side in enumerate(["over", "under"]):
            history = fetch_price_history(tokens[idx], interval="max", fidelity=720)
            df = history_to_df(history, f"{side} {total_value}", side)
            if not df.empty:
                df["market_type"] = "total"
                df["line"]        = total_value
                df["question"]    = q
                df["away_team"]   = away_team
                df["home_team"]   = home_team
                frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).sort_values(["line", "timestamp"]).reset_index(drop=True)


def _parse_line_from_question(question: str) -> float | None:
    """
    Extract the numeric line value from a market question.
    'Spread: Eagles (-7.5)'      → 7.5
    'Cowboys vs. Eagles: O/U 47.5' → 47.5
    'Spread: Cowboys (+7.5)'     → 7.5
    """
    import re
    match = re.search(r'[\(\+\-]?(\d+\.?\d*)\)?$', question.strip())
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None

# ---------------------------------------------------------------------------
# Volume breakdown
# ---------------------------------------------------------------------------

def get_event_volume(event: dict) -> dict:
    """Extract volume breakdown by market type."""
    moneyline_vol = spread_vol = total_vol = 0
    for market in event.get("markets", []):
        vol = float(market.get("volume") or 0)
        if _is_moneyline(market):
            moneyline_vol += vol
        elif _is_spread(market):
            spread_vol += vol
        elif _is_total(market):
            total_vol += vol
    return {
        "total":     float(event.get("volume") or 0),
        "moneyline": moneyline_vol,
        "spread":    spread_vol,
        "totals":    total_vol,
    }