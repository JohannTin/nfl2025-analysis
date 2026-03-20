# NFL 2025 Analysis

> **[📊 View the Interactive Dashboard](https://JohannTin.github.io/nfl2025-analysis)**

End-to-end quantitative analysis of the 2025 NFL season — covering probability model accuracy, sportsbook pricing efficiency, Polymarket prediction markets, team ATS performance, and sharp money signals across all 285 regular season and playoff games.

---

## Dashboard

The full interactive dashboard is hosted on GitHub Pages. It includes all charts, findings, a game-by-game explorer with filters, and final analysis — no setup required, open in any browser.

**[→ Open Dashboard](https://JohannTin.github.io/nfl2025-analysis)**

---

## Notebooks

| # | Notebook | Topic | Key Finding |
|---|----------|-------|-------------|
| 1 | [ESPN Win Probability vs. Sportsbooks](notebooks/1-%20ESPN's%20Win%20Probability%20vs.%20Sportsbook%20Analysis.ipynb) | Expected Value Analysis | ESPN EV signal is inverted — high suggested EV bets won only 22.2% of the time |
| 2 | [Model Calibration](notebooks/2-%20Model%20Calibration:%20Brier%20Score%20%26%20Reliability%20Diagram.ipynb) | Brier Score & Reliability | 7-book consensus (BS 0.2101) is 1.57× more skill-efficient than ESPN (BS 0.2216) |
| 3 | [Sportsbook Consensus & Best Line Finder](notebooks/3-%20Sportsbook%20Consensus%20%26%20Best%20Line%20Finder.ipynb) | Line Shopping Analysis | $32,785 in season value from always choosing the best available line per $100 bet |
| 4 | [Polymarket vs. ESPN & Sportsbooks](notebooks/4-%20Polymarket%20vs.%20ESPN%20%26%20Sportsbooks.ipynb) | Prediction Market Analysis | $1.14B in trading volume yet Polymarket (BS 0.2224) performs no better than ESPN |
| 5 | [ATS & Over/Under Performance](notebooks/5-%20ATS%20%26%20Over-Under%20Performance%20by%20Team.ipynb) | Team Cover Rate Analysis | Seattle Seahawks covered 80% of games (p=0.012) — only statistically significant result |
| 6 | [Sharp Money & Line Movement](notebooks/6-%20Sharp%20Money%20%26%20Line%20Movement.ipynb) | Market Microstructure | When sportsbook and Polymarket signals disagreed, away team covered 87.5% of the time |

---

## Key Findings

- **Sportsbooks beat everyone.** The 7-book consensus is the most accurate probability model in the dataset — more accurate than ESPN, Polymarket, and any individual book.
- **ESPN overrates underdogs.** High ESPN Expected Value bets won only 22.2% of the time. The correlation between suggested EV and actual outcomes is −0.358 (p < 0.0001).
- **Line shopping is worth $32,785 a season.** The gap between best and worst available odds, compounded across every game at $100/bet, shows how much value loyal single-book bettors sacrifice.
- **$1.1 billion does not buy accuracy.** Despite massive trading volume, Polymarket's prediction accuracy is indistinguishable from ESPN's — professional bookmakers remain the gold standard.
- **Sharp money works.** Spread movements of 1–3 points correctly predicted cover direction 60–65% of the time. Reverse line movement produced 63.9% cover rates vs. a 47.3% baseline.
- **Playoffs: home teams swept the spread.** Away teams covered 0 of 6 games across the Divisional and Conference Championship rounds.

---

## Dataset

`data/nfl2025_complete.xlsx` — 285 games, 88 columns, Weeks 1–18 plus playoffs.

Includes moneylines, spreads, and totals from 8 sources: ESPN, Opener, Bet365, SI, Betway, BetMGM, FanDuel, Caesars, DraftKings.

---

## Project Structure

```
nfl2025-analysis/
├── docs/
│   └── index.html              # Interactive dashboard (GitHub Pages)
├── data/
│   └── nfl2025_complete.xlsx   # Full season dataset
├── notebooks/
│   ├── 1- ESPN's Win Probability vs. Sportsbook Analysis.ipynb
│   ├── 2- Model Calibration: Brier Score & Reliability Diagram.ipynb
│   ├── 3- Sportsbook Consensus & Best Line Finder.ipynb
│   ├── 4- Polymarket vs. ESPN & Sportsbooks.ipynb
│   ├── 5- ATS & Over-Under Performance by Team.ipynb
│   └── 6- Sharp Money & Line Movement.ipynb
├── outputs/                    # CSVs exported by each notebook
├── src/
│   ├── utils.py                # Probability conversion, EV calculation, data loading
│   ├── calibration.py          # Brier score, Murphy decomposition, log loss
│   └── polymarket.py           # Polymarket API client
├── scripts/
│   └── fetch_polymarket.py     # Pull Polymarket data for all season games
└── requirements.txt
```

---

## Setup

```bash
git clone https://github.com/JohannTin/nfl2025-analysis.git
cd nfl2025-analysis
pip install -r requirements.txt
jupyter notebook
```

Run notebooks in order (1 → 6). Each reads from `data/` and writes CSVs to `outputs/` for use by later notebooks.

---

## Methods

**Probability conversion:** Two vig-removal methods — simple normalisation and the Shin (1993) insider-adjusted method. Results reported for both.

**Brier Score:** Mean squared error of probability forecasts. Lower is better. 0.25 is the score for always predicting 50/50.

**Sharp money proxy:** Opener-to-close spread movement used as a proxy for professional betting activity. Reverse line movement identified using opening spread direction as a proxy for the public side.

**Polymarket data:** Opening prices, closing prices, and 6-hour pre-game histories sourced from the Polymarket Gamma and CLOB APIs. All 285 games had Polymarket coverage.

---

## Tools

Python 3.10+ · pandas · numpy · matplotlib · seaborn · scipy · requests · Chart.js (dashboard)
