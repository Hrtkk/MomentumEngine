# Research 2026-10-09 — do overbought-looking entries do worse? (development data, pre-registered)

**Question (owner, 2026-10-09):** the first M11/M2 fills (CUPID, IOLCP, TFCILTD …) show RSI14 > 70, the MACD line crossing below its signal, fading volume and expanding Bollinger bands. Does the rule buy names that are losing strength, and do such entries do worse?

**Method:** every entry the frozen rule took on the point-in-time universe, split by the reading on the signal day. Outcome = the trade's realised return (exit ÷ entry − 1, gross) plus the 20- and 60-session close after entry. A reading *matters* only if the 90% bootstrap interval of the mean difference excludes zero. Hypotheses H1–H5 and the method were written before the numbers were computed (`experiments/research/overbought_entries.py`). 14 strategies were tried in E2; this note tests 6 readings × 2 books, which is 12 more looks.

Indicators: RSI14 (Wilder), MACD 12/26/9 on closes, volume fading = mean(V, last 5) < mean(V, previous 20), Bollinger width = 4·σ20/SMA20 vs 5 sessions earlier, stretched = close > 1.10 × SMA20. All computed on corporate-action-adjusted closes.

## M11 — development 2013–2020 (279 entries)

| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |
|---|---|---|---|---|---|---|---|---|
| rsi_gt70 | 205 / 74 | +11.3% / +11.6% | -9.7% / -6.8% | 33% / 38% | -0.3% [-13.4%, +12.9%] | +0.7% / +1.8% | +5.3% / +4.6% | no difference |
| macd_below_signal | 21 / 258 | +12.1% / +11.3% | -7.4% / -9.5% | 43% / 33% | +0.8% [-13.6%, +16.1%] | +11.1% / +0.2% | +10.2% / +4.7% | no difference |
| macd_hist_falling | 2 / 277 | too few | | | | | | — |
| volume_fading | 43 / 236 | +51.5% / +4.1% | +2.0% / -9.7% | 51% / 31% | +47.5% [+14.3%, +91.9%] | +7.4% / -0.1% | +16.8% / +3.0% | **better** |
| bb_expanding | 210 / 69 | +11.6% / +10.5% | -9.6% / -6.8% | 32% / 39% | +1.1% [-9.7%, +13.3%] | -0.0% / +4.2% | +4.6% / +6.5% | no difference |
| stretched_10pct_above_sma20 | 196 / 83 | +12.7% / +8.1% | -10.6% / -7.5% | 35% / 31% | +4.6% [-7.6%, +17.3%] | +0.9% / +1.2% | +4.9% / +5.6% | no difference |
| all_four | 2 / 277 | too few | | | | | | — |

### M11 — holdout 2021 → 2026-10-07 (185 entries) — information only, spent data

| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |
|---|---|---|---|---|---|---|---|---|
| rsi_gt70 | 125 / 60 | +3.5% / +10.5% | -10.0% / -7.0% | 31% / 42% | -7.1% [-18.5%, +3.2%] | +0.4% / +4.2% | +5.9% / +8.5% | no difference |
| macd_below_signal | 17 / 168 | +34.1% / +2.9% | +14.6% / -9.1% | 59% / 32% | +31.2% [+5.3%, +64.2%] | +6.3% / +1.2% | +23.0% / +5.1% | **better** |
| macd_hist_falling | 1 / 184 | too few | | | | | | — |
| volume_fading | 27 / 158 | +0.8% / +6.6% | -9.9% / -8.2% | 30% / 35% | -5.8% [-14.4%, +2.7%] | +0.3% / +1.9% | -1.3% / +8.1% | no difference |
| bb_expanding | 142 / 43 | +5.1% / +7.9% | -8.2% / -9.9% | 35% / 35% | -2.8% [-17.0%, +8.4%] | +1.3% / +3.0% | +6.9% / +6.1% | no difference |
| stretched_10pct_above_sma20 | 134 / 51 | +3.6% / +11.6% | -10.9% / -4.2% | 32% / 41% | -8.0% [-20.9%, +2.7%] | +1.4% / +2.5% | +6.7% / +6.8% | no difference |
| all_four | 0 / 185 | too few | | | | | | — |

## M2 — development 2013–2020 (305 entries)

| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |
|---|---|---|---|---|---|---|---|---|
| rsi_gt70 | 84 / 221 | +23.1% / +10.6% | -12.2% / -11.0% | 31% / 36% | +12.6% [-13.1%, +48.9%] | +4.8% / +3.6% | +8.7% / +11.3% | no difference |
| macd_below_signal | 172 / 133 | +15.4% / +12.2% | -8.0% / -13.2% | 41% / 26% | +3.2% [-21.5%, +22.3%] | +6.4% / +0.8% | +15.1% / +4.6% | no difference |
| macd_hist_falling | 142 / 163 | +11.1% / +16.6% | -11.1% / -11.9% | 37% / 33% | -5.4% [-27.0%, +12.0%] | +3.1% / +4.7% | +12.4% / +9.0% | no difference |
| volume_fading | 164 / 141 | +12.0% / +16.5% | -10.2% / -13.2% | 39% / 29% | -4.5% [-29.1%, +13.9%] | +5.0% / +2.8% | +13.1% / +7.6% | no difference |
| bb_expanding | 150 / 155 | +15.3% / +12.8% | -11.4% / -11.5% | 31% / 37% | +2.4% [-15.6%, +24.2%] | +4.3% / +3.6% | +9.0% / +12.1% | no difference |
| stretched_10pct_above_sma20 | 94 / 211 | +21.9% / +10.5% | -13.9% / -10.5% | 30% / 36% | +11.4% [-12.6%, +45.4%] | +3.3% / +4.3% | +10.2% / +10.7% | no difference |
| all_four | 0 / 305 | too few | | | | | | — |

### M2 — holdout 2021 → 2026-10-07 (225 entries) — information only, spent data

| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |
|---|---|---|---|---|---|---|---|---|
| rsi_gt70 | 61 / 164 | +10.7% / +4.4% | -11.2% / -10.5% | 34% / 35% | +6.4% [-4.4%, +17.9%] | +4.5% / +3.4% | +10.4% / +6.6% | no difference |
| macd_below_signal | 123 / 102 | +4.3% / +8.3% | -5.4% / -12.7% | 37% / 32% | -4.0% [-13.8%, +5.0%] | +5.2% / +2.0% | +10.3% / +4.5% | no difference |
| macd_hist_falling | 102 / 123 | +6.0% / +6.2% | -11.2% / -10.7% | 34% / 35% | -0.2% [-8.9%, +8.7%] | +4.5% / +3.1% | +7.2% / +8.0% | no difference |
| volume_fading | 116 / 109 | +4.3% / +8.0% | -10.3% / -12.4% | 34% / 35% | -3.7% [-12.9%, +5.1%] | +3.8% / +3.7% | +6.9% / +8.4% | no difference |
| bb_expanding | 117 / 108 | +8.5% / +3.5% | -9.0% / -12.5% | 39% / 30% | +5.0% [-3.5%, +13.7%] | +3.7% / +3.8% | +7.0% / +8.3% | no difference |
| stretched_10pct_above_sma20 | 84 / 141 | +4.8% / +6.9% | -13.8% / -7.9% | 29% / 38% | -2.0% [-11.4%, +7.7%] | +2.7% / +4.3% | +5.0% / +9.2% | no difference |
| all_four | 1 / 224 | too few | | | | | | — |

## Reading the result

- A row marked **worse** means: on development data, entries with that reading earned less, and the interval excludes zero. That is a hypothesis for a *shadow* variant (an entry veto), not a change to the live rule.
- A row marked *no difference* means the reading carried no information about the trade's outcome, in this sample.
- Win rates near 35–40% are the rule's normal state; the return comes from a few large winners, so medians are negative even when means are positive.
- Context from E2: the tier-4 extension veto (M9: skip if day return > 5%, close > 1.10·SMA20 or RSI14 > 75, on the 3-month rule) failed development (2 of 4 blocks) and in the holdout earned +13.7% excess vs +20.9% without the veto (`results_e2/holdout_metrics.csv`).

Sources: `strategy/data/backtest_<ID>_trades.csv` (regenerated 2026-10-09 with the frozen E2 engine), `experiments/data/pit/`.