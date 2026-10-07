# Diagnosis — why the v0.2.1 replay lost (2026-10-07)

Exploratory and in-sample. Uses today's Nifty 500 list (survivorship bias) and a falling market. The sample is small: 17–21 signal dates for the universe study and a single 13-session path for the replays. Treat everything here as hypotheses for shadow books, not as evidence.

## A. Universe study (`src/study_universe.py`, signals 2026-09-04 … 2026-10-06; raw data in `study_2026-10-07.csv`)

Mean forward return, from the open of t+1 to the close of t+5, with equal weights:

| Cohort | 5-day return | Dates beating the whole Nifty 500 |
|---|---:|---:|
| Whole Nifty 500 | −1.27% | — |
| Top-100 gainers (discovery) | −1.73% | 12% |
| Eligible candidates | −1.32% | 29% |
| **MQS top 10 (our pick)** | **−2.24%** | 35% |
| MQS bottom 10 | −1.76% | 29% |
| Raw top-10 gainers | −2.44% | 18% |
| 63-day momentum top 10 within gainers | −0.47% | 76% |
| **63-day momentum top 10 across all Nifty 500** | **−0.68%** | **76%** |

Daily rank IC against the 5-day return, across eligible candidates (17 dates):

| Factor | Mean IC |
|---|---:|
| MQS | +0.006 (≈ 0) |
| Day-*t* return | **−0.056** |
| EQS | **+0.055** |
| Sector | −0.035 |
| Persistence | −0.026 |

**Reading:**
- Yesterday's gainers *reversed*. The bigger the jump, the worse the next five days. This matches short-horizon reversal (Jegadeesh 1990, *J. Finance* 45(3)).
- MQS had no ranking power. Its top 10 did worse than its bottom 10.
- Medium-term momentum (63-day return) was the only selection that beat the market, on about three-quarters of dates.
- "Not over-extended" (EQS) was the most useful timing signal.

## B. Counterfactual replays (same 13 sessions, ₹60k, 0.6% cost; base reproduces the live ledger exactly)

| Variant | Return | Trades | Turnover | Costs | Stops | Max drawdown |
|---|---:|---:|---:|---:|---:|---:|
| v0.2.1 (live) | −3.03% | 53 | 3.4× | ₹610 | 6 | −5.2% |
| No score-based swaps | **−1.19%** | 25 | 1.7× | ₹309 | 6 | −3.8% |
| Sector cap 3 | −1.32% | 43 | 2.9× | ₹529 | 5 | −4.7% |
| No buys in Risk-off | −3.34% | 30 | 2.1× | ₹376 | 8 | −4.2% |
| All three combined | −2.66% | 22 | 1.5× | ₹268 | 8 | −3.0% |

Nifty 500 over the same window: −2.63%.

## Answer

- **Main cause — the entry trigger.** Buying names right after a big up-day sets the portfolio up for short-term reversal, and the score could not separate winners from losers inside that universe.
- **Amplifier — over-trading.** Daily swaps rotated the book into fresh spikes. Turning swaps off removed about 1.8 percentage points of the loss, in this sample.
- **Amplifier — crowding.** 8 of 13 names were Healthcare.
- **Not the fix — pausing in Risk-off.** It sat in cash during the fall but still took the stops.
- **Narrow or broad?** The issue is less breadth than *which* signal is used. Ranking the whole Nifty 500 by 63-day momentum did better than ranking the gainers.

## Proposed v0.3 candidate (shadow book first, Codex challenge before adoption)

1. **Selection:** rank all Nifty 500 names by volatility-adjusted 6/3-month momentum, in the style of the Nifty200 Momentum 30 index. Daily gainers become an alert feed, not the entry list.
2. **Entry timing:** buy only when the stock is not stretched: EQS ≥ 60 and day return < 5%. Otherwise wait.
3. **Turnover:** rebalance weekly, with no daily score swaps. Stops and removals still apply daily.
4. **Concentration:** at most 3 names per sector.
5. **Validation:** backtest on the ~2 years of Yahoo history already downloaded (~400 sessions, not 13), then run as a shadow book next to v0.2.1 on the same P&L chart.
