"""
fetch_polymarket.py
Run from the repo root: python scripts/fetch_polymarket.py
"""

import sys
import os
import time
import pandas as pd

sys.path.insert(0, os.path.abspath('.'))
from src.utils import load_data
from src.polymarket import (
    build_slug, fetch_event, extract_closing_price,
    extract_opening_price, extract_6h_history,
    extract_spread_history, extract_total_history, 
    get_event_volume, TEAM_SLUG
)

os.makedirs('outputs', exist_ok=True)
os.makedirs('outputs/6h_histories', exist_ok=True)

# ── Load game data ───────────────────────────────────────────────────────────
df = load_data('data/nfl2025_complete.xlsx')
df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

# ── Config ───────────────────────────────────────────────────────────────────
TEST_ONE_GAME       = False    # set False to run all 285
TEST_GAME_ROW_INDEX = 284
RUN_6H_HISTORY      = True
DEBUG_MARKETS       = False    # set False once token detection is confirmed working

df_to_process = df

if TEST_ONE_GAME:
    df_reset = df.reset_index(drop=True)
    df_to_process = df_reset.iloc[TEST_GAME_ROW_INDEX:TEST_GAME_ROW_INDEX + 1]
    sel = df_to_process.iloc[0]
    print(f"Test mode: {sel['away_team']} @ {sel['home_team']} ({sel['date_str']})\n")

print(f"Fetching data for {len(df_to_process)} games...\n")

records = []
all_6h  = []
all_spreads = []
all_totals  = []

for i, row in df_to_process.iterrows():
    try:
        slug = build_slug(row['away_team'], row['home_team'], row['date_str'])
    except ValueError as e:
        print(f"  ✗ Slug error: {e}")
        continue

    print(f"  [{i+1:3d}/{len(df_to_process)}] {slug}", end=" ... ", flush=True)
    event = fetch_event(slug)

    if event is None:
        print("not found")
        records.append({
            'week': row['week'], 'date': row['date_str'],
            'away_team': row['away_team'], 'home_team': row['home_team'],
            'slug': slug, 'found': False,
            'polymarket_away_close': None, 'polymarket_home_close': None,
            'polymarket_away_open':  None, 'polymarket_home_open':  None,
            'volume_total': None, 'volume_moneyline': None,
            'volume_spread': None, 'volume_totals': None,
        })
    else:
        # ── Debug: print all market questions so we can see exact wording ──
        if DEBUG_MARKETS:
            print()
            print(f"    Markets in event ({len(event.get('markets', []))}):")
            for m in event.get('markets', []):
                q      = m.get('question', '')
                vol    = float(m.get('volume') or 0)
                tokens = m.get('tokens', [])
                tids   = [t.get('token_id','')[:12]+'...' for t in tokens]
                print(f"      Q: {q}")
                print(f"         vol=${vol/1e6:.2f}M  tokens={tids}")
            print()

        away_close = extract_closing_price(event, 'away')
        home_close = extract_closing_price(event, 'home')
        away_open  = extract_opening_price(event, 'away')
        home_open  = extract_opening_price(event, 'home')
        vols       = get_event_volume(event)

        print(f"  close: away={away_close}  home={home_close}  "
              f"vol=${vols['total']/1e6:.2f}M", end="")

        # ── 6H history ───────────────────────────────────────────────────────
        if RUN_6H_HISTORY:
            hist_df = extract_6h_history(event, row['away_team'], row['home_team'])
            if not hist_df.empty:
                hist_df['week']      = row['week']
                hist_df['date']      = row['date_str']
                hist_df['away_team'] = row['away_team']
                hist_df['home_team'] = row['home_team']
                all_6h.append(hist_df)
                safe_slug = slug.replace('/', '_')
                hist_df.to_csv(f"outputs/6h_histories/{safe_slug}.csv", index=False)
                print(f"  6H: {len(hist_df)} rows", end="")
            else:
                print(f"  6H: no data", end="")

        # ── Spread history ───────────────────────────────────────────────
        spread_df = extract_spread_history(event, row['away_team'], row['home_team'])
        if not spread_df.empty:
            spread_df['week']      = row['week']
            spread_df['date']      = row['date_str']
            spread_df['away_team'] = row['away_team']
            spread_df['home_team'] = row['home_team']
            all_spreads.append(spread_df)

        # ── Total history ────────────────────────────────────────────────
        total_df = extract_total_history(event, row['away_team'], row['home_team'])
        if not total_df.empty:
            total_df['week'] = row['week']
            total_df['date'] = row['date_str']
            all_totals.append(total_df)
        
        print()

        records.append({
            'week': row['week'], 'date': row['date_str'],
            'away_team': row['away_team'], 'home_team': row['home_team'],
            'slug': slug, 'found': True,
            'polymarket_away_close': away_close,
            'polymarket_home_close': home_close,
            'polymarket_away_open':  away_open,
            'polymarket_home_open':  home_open,
            'volume_total':     vols['total'],
            'volume_moneyline': vols['moneyline'],
            'volume_spread':    vols['spread'],
            'volume_totals':    vols['totals'],
        })

    time.sleep(0.5)

# ── Save closing prices ───────────────────────────────────────────────────────
results = pd.DataFrame(records)
results.to_csv('outputs/polymarket_closing_prices.csv', index=False)
found = results['found'].sum()
print(f"\nClosing prices: {found}/{len(df_to_process)} games found")
print(f"Saved → outputs/polymarket_closing_prices.csv")

# ── Save combined 6H ─────────────────────────────────────────────────────────
if RUN_6H_HISTORY and all_6h:
    combined = pd.concat(all_6h, ignore_index=True)
    combined.to_csv('outputs/polymarket_all_6h.csv', index=False)
    print(f"Saved → outputs/polymarket_all_6h.csv  ({len(combined):,} rows, {len(all_6h)} games)")
elif RUN_6H_HISTORY:
    print("No 6H data returned — check DEBUG_MARKETS output above for market question wording.")
# ── Save spreads ──────────────────────────────────────────────────────────
if all_spreads:
    pd.concat(all_spreads, ignore_index=True).to_csv(
        'outputs/polymarket_all_spreads.csv', index=False)
    print(f"Saved → outputs/polymarket_all_spreads.csv  ({len(all_spreads)} games)")
else:
    print("No spread data returned.")

# ── Save totals ───────────────────────────────────────────────────────────
if all_totals:
    pd.concat(all_totals, ignore_index=True).to_csv(
        'outputs/polymarket_all_totals.csv', index=False)
    print(f"Saved → outputs/polymarket_all_totals.csv  ({len(all_totals)} games)")
else:
    print("No totals data returned.")
