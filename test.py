
# import pandas as pd
# df = pd.read_csv('outputs/polymarket_closing_prices.csv')
# missing = df[df['found'] == False]
# print(missing[['week', 'date', 'away_team', 'home_team', 'slug']])

# # Test these slugs manually
# test_slugs = [
#     'nfl-car-tb-2026-01-04',    # day after
#     'nfl-car-tb-2026-01-02',    # day before
#     'nfl-sea-sf-2026-01-04',
#     'nfl-sea-sf-2026-01-02',
# ]

# import requests
# BASE_GAMMA = "https://gamma-api.polymarket.com"
# for slug in test_slugs:
#     r = requests.get(f"{BASE_GAMMA}/events", params={"slug": slug}, timeout=10)
#     data = r.json()
#     print(f"{slug}: {'FOUND' if data else 'not found'}")


# import pandas as pd, requests, json

# BASE_GAMMA = "https://gamma-api.polymarket.com"

# fixes = [
#     ('Carolina Panthers',  'Tampa Bay Buccaneers', 'nfl-car-tb-2026-01-04'),
#     ('Seattle Seahawks',   'San Francisco 49ers',  'nfl-sea-sf-2026-01-04'),
# ]

# df = pd.read_csv('outputs/polymarket_closing_prices.csv')

# for away, home, slug in fixes:
#     r = requests.get(f"{BASE_GAMMA}/events", params={"slug": slug}, timeout=10)
#     event = r.json()[0]
#     prices = json.loads(event['markets'][0]['outcomePrices'])
#     mask = (df['away_team'] == away) & (df['home_team'] == home)
#     df.loc[mask, 'slug']                  = slug
#     df.loc[mask, 'found']                 = True
#     df.loc[mask, 'polymarket_away_close'] = float(prices[0])
#     df.loc[mask, 'polymarket_home_close'] = float(prices[1])
#     df.loc[mask, 'volume_total']          = float(event.get('volume', 0))
#     print(f"Fixed: {away} @ {home} → {slug}  prices={prices}")

# df.to_csv('outputs/polymarket_closing_prices.csv', index=False)
# print("Saved.")


import pandas as pd, requests, json, os

BASE_GAMMA = "https://gamma-api.polymarket.com"
BASE_CLOB  = "https://clob.polymarket.com"

fixes = [
    ('Seattle Seahawks',  'Carolina Panthers',    'Tampa Bay Buccaneers', 'nfl-car-tb-2026-01-04', '18', '2026-01-03'),
    ('Seattle Seahawks',  'Seattle Seahawks',     'San Francisco 49ers',  'nfl-sea-sf-2026-01-04', '18', '2026-01-03'),
]

# Correct structure
fixes = [
    {'away': 'Carolina Panthers',  'home': 'Tampa Bay Buccaneers', 'slug': 'nfl-car-tb-2026-01-04', 'week': 18, 'date': '2026-01-03'},
    {'away': 'Seattle Seahawks',   'home': 'San Francisco 49ers',  'slug': 'nfl-sea-sf-2026-01-04', 'week': 18, 'date': '2026-01-03'},
]

def fetch_price_history(token_id):
    r = requests.get(f"{BASE_CLOB}/prices-history",
                     params={"market": token_id, "interval": "max", "fidelity": 720}, timeout=10)
    return r.json().get("history", [])

def history_to_rows(history, team, side, away, home, week, date):
    rows = []
    for h in history:
        rows.append({
            "timestamp":  h["t"],
            "datetime":   pd.to_datetime(h["t"], unit="s"),
            "team":       team,
            "side":       side,
            "probability":h["p"],
            "week":       week,
            "date":       date,
            "away_team":  away,
            "home_team":  home,
        })
    return rows

all_6h     = []
all_spreads = []
all_totals  = []

for fix in fixes:
    away, home, slug, week, date = fix['away'], fix['home'], fix['slug'], fix['week'], fix['date']
    print(f"\nFetching {slug}...")

    r = requests.get(f"{BASE_GAMMA}/events", params={"slug": slug}, timeout=10)
    event = r.json()[0]
    markets = event.get("markets", [])

    for market in markets:
        q = market.get("question", "").lower()
        raw_tokens = market.get("clobTokenIds", "[]")
        tokens = json.loads(raw_tokens)
        if len(tokens) < 2:
            continue

        # ── Moneyline 6H ────────────────────────────────────────────────
        if "vs." in q and "spread" not in q and "o/u" not in q and "over" not in q and "under" not in q:
            for idx, (side, team) in enumerate([ ("away", away), ("home", home) ]):
                hist = fetch_price_history(tokens[idx])
                all_6h.extend(history_to_rows(hist, team, side, away, home, week, date))
            print(f"  ✓ Moneyline 6H")

        # ── Spreads ─────────────────────────────────────────────────────
        elif "spread" in q and "1h" not in q:
            import re
            m = re.search(r'[\(\+\-]?(\d+\.?\d*)\)?$', market.get("question","").strip())
            line = float(m.group(1)) if m else None
            for idx, (side, team) in enumerate([ ("away", away), ("home", home) ]):
                hist = fetch_price_history(tokens[idx])
                for h in hist:
                    all_spreads.append({
                        "timestamp": h["t"], "datetime": pd.to_datetime(h["t"], unit="s"),
                        "team": team, "side": side, "probability": h["p"],
                        "market_type": "spread", "line": line,
                        "question": market.get("question",""),
                        "week": week, "date": date, "away_team": away, "home_team": home,
                    })
            print(f"  ✓ Spread {line}")

        # ── Totals ──────────────────────────────────────────────────────
        elif "vs." in q and "o/u" in q and "1h" not in q:
            import re
            m = re.search(r'[\(\+\-]?(\d+\.?\d*)\)?$', market.get("question","").strip())
            line = float(m.group(1)) if m else None
            for idx, side in enumerate(["over", "under"]):
                hist = fetch_price_history(tokens[idx])
                for h in hist:
                    all_totals.append({
                        "timestamp": h["t"], "datetime": pd.to_datetime(h["t"], unit="s"),
                        "team": f"{side} {line}", "side": side, "probability": h["p"],
                        "market_type": "total", "line": line,
                        "question": market.get("question",""),
                        "away_team": away, "home_team": home, "week": week, "date": date,
                    })
            print(f"  ✓ Total {line}")

# ── Append to existing CSVs ──────────────────────────────────────────────────
def append_to_csv(new_rows, path):
    if not new_rows:
        print(f"  No new rows for {path}")
        return
    new_df = pd.DataFrame(new_rows)
    if os.path.exists(path):
        existing = pd.read_csv(path)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(path, index=False)
    print(f"  Saved {len(new_df)} new rows → {path}")

append_to_csv(all_6h,      'outputs/polymarket_all_6h.csv')
append_to_csv(all_spreads, 'outputs/polymarket_all_spreads.csv')
append_to_csv(all_totals,  'outputs/polymarket_all_totals.csv')

# ── Save individual 6H files ─────────────────────────────────────────────────
for fix in fixes:
    rows = [r for r in all_6h if r['away_team'] == fix['away'] and r['home_team'] == fix['home']]
    if rows:
        pd.DataFrame(rows).to_csv(f"outputs/6h_histories/{fix['slug']}.csv", index=False)
        print(f"  Saved outputs/6h_histories/{fix['slug']}.csv")

print("\nDone. All files patched.")