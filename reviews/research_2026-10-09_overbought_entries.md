# Research 2026-10-09 — do overbought-looking entries do worse? (development data, pre-registered)

**Question (owner, 2026-10-09):** the first M11/M2 fills (CUPID, IOLCP, TFCILTD …) show RSI14 > 70, the MACD line crossing below its signal, fading volume and expanding Bollinger bands. Does the rule buy names that are losing strength, and do such entries do worse?

**Method:** every entry the frozen rule took on the point-in-time universe, split by the reading on the signal day. Outcome = the trade's realised return (exit ÷ entry − 1, gross) plus the 20- and 60-session close after entry. A reading *matters* only if the 90% bootstrap interval of the mean difference excludes zero. Hypotheses H1–H5 and the method were written before the numbers were computed (`experiments/research/overbought_entries.py`). 14 strategies were tried in E2; this note tests 6 readings × 2 books, which is 12 more looks.

Indicators: RSI14 (Wilder), MACD 12/26/9 on closes, volume fading = mean(V, last 5) < mean(V, previous 20), Bollinger width = 4·σ20/SMA20 vs 5 sessions earlier, stretched = close > 1.10 × SMA20. All computed on corporate-action-adjusted closes.

## M11 — development 2013–2020 (273 entries)

| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |
|---|---|---|---|---|---|---|---|---|
| rsi_gt70 | 194 / 79 | +15.0% / +7.1% | -7.7% / -7.1% | 36% / 41% | +7.9% [-3.7%, +20.5%] | +0.0% / +1.9% | +7.1% / +4.9% | no difference |
| macd_below_signal | 24 / 249 | +4.5% / +13.5% | +0.8% / -7.7% | 54% / 36% | -9.0% [-18.8%, -0.0%] | +2.6% / +0.4% | +10.1% / +6.1% | **worse** |
| macd_hist_falling | 3 / 270 | too few | | | | | | — |
| volume_fading | 49 / 224 | +34.1% / +8.0% | +1.0% / -7.8% | 53% / 34% | +26.0% [-1.0%, +63.8%] | +2.7% / +0.1% | +11.0% / +5.4% | no difference |
| bb_expanding | 197 / 76 | +12.4% / +13.4% | -8.5% / +0.9% | 31% / 54% | -1.0% [-11.9%, +11.8%] | +0.2% / +1.4% | +6.0% / +7.7% | no difference |
| stretched_10pct_above_sma20 | 164 / 109 | +18.2% / +4.5% | -9.1% / -7.3% | 39% / 35% | +13.7% [+2.4%, +27.1%] | +1.0% / -0.1% | +7.7% / +4.5% | **better** |
| all_four | 1 / 272 | too few | | | | | | — |

### M11 — holdout 2021 → 2026-10-07 (176 entries) — information only, spent data

| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |
|---|---|---|---|---|---|---|---|---|
| rsi_gt70 | 114 / 62 | +5.4% / +12.0% | -8.7% / -5.0% | 32% / 44% | -6.6% [-18.6%, +3.8%] | +2.0% / +5.0% | +6.7% / +9.2% | no difference |
| macd_below_signal | 16 / 160 | +28.4% / +5.6% | +15.0% / -8.7% | 62% / 34% | +22.8% [-0.9%, +57.3%] | +6.9% / +2.7% | +20.3% / +6.3% | no difference |
| macd_hist_falling | 1 / 175 | too few | | | | | | — |
| volume_fading | 29 / 147 | -0.5% / +9.3% | -7.4% / -8.4% | 28% / 38% | -9.7% [-17.8%, -1.3%] | +1.8% / +3.3% | +1.1% / +8.8% | **worse** |
| bb_expanding | 122 / 54 | +8.4% / +6.2% | -7.6% / -9.3% | 38% / 33% | +2.2% [-9.9%, +12.9%] | +2.8% / +3.6% | +7.4% / +7.9% | no difference |
| stretched_10pct_above_sma20 | 118 / 58 | +7.5% / +8.0% | -10.4% / -6.7% | 36% / 36% | -0.5% [-12.3%, +9.4%] | +3.5% / +2.1% | +8.9% / +4.8% | no difference |
| all_four | 0 / 176 | too few | | | | | | — |

## M2 — development 2013–2020 (287 entries)

| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |
|---|---|---|---|---|---|---|---|---|
| rsi_gt70 | 64 / 223 | +41.0% / +10.1% | -8.7% / -8.5% | 39% / 39% | +30.9% [-2.9%, +80.4%] | +5.6% / +0.8% | +9.2% / +9.0% | no difference |
| macd_below_signal | 163 / 124 | +12.5% / +22.9% | -9.0% / -6.7% | 37% / 43% | -10.4% [-36.7%, +10.0%] | +0.8% / +3.2% | +8.6% / +9.7% | no difference |
| macd_hist_falling | 149 / 138 | +16.1% / +18.0% | -6.2% / -9.9% | 43% / 36% | -1.8% [-26.7%, +17.2%] | +2.8% / +0.9% | +12.2% / +5.7% | no difference |
| volume_fading | 171 / 116 | +13.5% / +22.2% | -7.9% / -9.4% | 40% / 38% | -8.7% [-36.8%, +12.2%] | +1.3% / +2.7% | +9.1% / +9.0% | no difference |
| bb_expanding | 145 / 142 | +25.6% / +8.3% | -6.7% / -9.9% | 47% / 32% | +17.3% [-1.7%, +39.8%] | +3.3% / +0.3% | +11.3% / +6.8% | no difference |
| stretched_10pct_above_sma20 | 67 / 220 | +40.9% / +9.8% | -9.7% / -8.3% | 46% / 37% | +31.1% [-1.2%, +77.1%] | +4.5% / +1.1% | +9.7% / +8.9% | no difference |
| all_four | 0 / 287 | too few | | | | | | — |

### M2 — holdout 2021 → 2026-10-07 (212 entries) — information only, spent data

| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |
|---|---|---|---|---|---|---|---|---|
| rsi_gt70 | 62 / 150 | +9.7% / +7.9% | -11.0% / -9.7% | 39% / 37% | +1.8% [-8.5%, +12.7%] | +3.0% / +2.9% | +8.1% / +8.5% | no difference |
| macd_below_signal | 108 / 104 | +4.3% / +12.7% | -11.1% / -9.0% | 36% / 39% | -8.3% [-18.5%, +1.3%] | +3.4% / +2.4% | +9.6% / +7.2% | no difference |
| macd_hist_falling | 91 / 121 | +13.1% / +4.9% | -8.1% / -11.9% | 44% / 33% | +8.2% [-1.8%, +18.3%] | +5.6% / +0.9% | +11.9% / +5.7% | no difference |
| volume_fading | 100 / 112 | +12.8% / +4.5% | -9.1% / -10.8% | 39% / 37% | +8.4% [-1.4%, +18.8%] | +3.7% / +2.2% | +9.2% / +7.7% | no difference |
| bb_expanding | 123 / 89 | +7.1% / +10.2% | -8.9% / -11.6% | 41% / 33% | -3.1% [-14.0%, +7.4%] | +3.1% / +2.6% | +8.3% / +8.5% | no difference |
| stretched_10pct_above_sma20 | 82 / 130 | +3.8% / +11.3% | -12.2% / -8.3% | 34% / 40% | -7.5% [-16.9%, +1.6%] | +1.5% / +3.8% | +3.4% / +11.5% | no difference |
| all_four | 0 / 212 | too few | | | | | | — |

## Reading the result

- A row marked **worse** means: on development data, entries with that reading earned less, and the interval excludes zero. That is a hypothesis for a *shadow* variant (an entry veto), not a change to the live rule.
- A row marked *no difference* means the reading carried no information about the trade's outcome, in this sample.
- Win rates near 35–40% are the rule's normal state; the return comes from a few large winners, so medians are negative even when means are positive.
- Context from E2: the tier-4 extension veto (M9: skip if day return > 5%, close > 1.10·SMA20 or RSI14 > 75, on the 3-month rule) failed development (2 of 4 blocks) and in the holdout earned +13.7% excess vs +20.9% without the veto (`results_e2/holdout_metrics.csv`).

Sources: `strategy/data/backtest_<ID>_trades.csv` (regenerated 2026-10-09 with the frozen E2 engine), `experiments/data/pit/`.