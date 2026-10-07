# Experiment E2 — strategy ladder on a point-in-time universe (pre-registered 2026-10-07)

**Goal (owner, 2026-10-07):** try many strategies from simple to advanced and find **4–5 reliable ones**, with reliable data first.
**Protection against luck:** about 15 strategies are tested. All of them are selected on the **development period only**. The **holdout period is evaluated once**, after the selection has been logged. Parameters are fixed here; nothing is tuned.

Conventions carry over from E1 (`SPEC.md` §2 and amendments A1–A8) unless changed below.

## 1. Data: point-in-time, including stocks that were later delisted

- **Prices:**
  - NSE daily bhavcopy for all EQ securities, 2011-06 → 2026-10-07.
  - Old `cm…bhav.csv.zip` format up to 2024-07-05, then the UDiFF format.
  - Every file's internal date is verified.
- **Corporate actions:** from the NSE corporate-actions API.
  - Bonus `a:b` → factor `(a+b)/b`.
  - Face-value split `X → Y` → factor `X/Y`.
  - On the ex-date, the return uses `prev_close / factor`. The history before the ex-date is divided by the cumulative factor.
  - Rights issues, demergers and schemes are **not adjusted**. They are listed as A1 alerts.
  - An overnight gap of ≤ −40% or ≥ +60% with no recorded action is also an A1 alert.
- **Symbol changes:** NSE `symbolchange.csv` stitches old symbols into new ones.
- **Trade-to-trade series:** a stock moved to the BE/BZ series stays priced from those rows, for valuation and exits only, and is **ineligible** for entry.
- **Universe — "Liquid-500", rebuilt each month-end:**
  - EQ series, ≥ 252 prior sessions, nominal close ≥ ₹50.
  - Ranked by median traded value over the previous 63 sessions; the top 500 are in.
  - Membership is fixed until the next month-end.
  - No index-membership data is used, so **there is no survivorship or inclusion bias**.
- **Sector:** today's Nifty 500 industry label where one exists, otherwise "Unknown". The 3-per-sector cap applies to known sectors only.
- **Benchmarks:**
  - **B1:** Nifty 500 price index (Yahoo `^CRSLDX`).
  - **B2-net:** equal weight of Liquid-500, executed at the next open, with 0.6% costs on turnover. **B2-net is the hurdle.**

## 2. Periods

| Period | Dates | Use |
|---|---|---|
| Warm-up | 2011-06 → 2012-12 | Indicators only |
| **Development** | 2013-01-01 → 2020-12-31 (8 years) | Blocks D1 2013-14, D2 2015-16, D3 2017-18, D4 2019-20 |
| **Holdout** | 2021-01-01 → 2026-10-07 (5.8 years) | Blocks H1 2021-22, H2 2023-24, H3 2025-26. **Not examined until the selection is logged in §5** |

Each strategy runs as one continuous book from 2013-01-01. Period metrics are computed on that book's returns within each period.

## 3. Common portfolio rules (all except controls C0 and C1)

- **Size:** 10 slots, 10% of equity at entry each, no weight rebalancing, max 3 per known sector, cash allowed.
- **Execution:** decide at close t, trade at open t+1. Costs are 0.3 / 0.6 / 1.0% round trip; **0.6% is primary**.
- **Catastrophic stop:** `C − 3·ATR20`, fixed at entry.
- **Hysteresis (ranked strategies):** enter at rank ≤ 50, stay while rank ≤ 125. Ranks are recomputed at each refresh; there are no swaps between refreshes.
- **Ineligibility (fixes the E1 flicker):** a holding exits when it falls out of Liquid-500 **at a monthly reconstitution**, or has no EQ or BE trade for 5 consecutive sessions. A single day of ineligibility no longer forces an exit.
- **Refresh:** the last session of the ISO week (W) or of the month (M).

## 4. The ladder (fixed now)

| Tier | ID | Strategy | Score / rule | Refresh |
|---|---|---|---|---|
| 1 Simple momentum | **M1** | 3-month momentum | R3 = 63-session return | W |
| | **M2** | 6-month momentum | R6 | W |
| | **M3** | 12-1 momentum | `C[t−21]/C[t−252] − 1` | M |
| | **M4** | 52-week-high proximity (George & Hwang 2004) | `C / max(H, 252 sessions)` | W |
| 2 Risk-adjusted | **M5** | Volatility-adjusted momentum (NSE Mom-30 style) | mean of pct(R6/σ126) and pct(R12/σ252) | M |
| | **M6** | Low-volatility momentum | R6 rank among names with σ126 ≤ the universe median | W |
| 3 Regime / absolute | **M7** | M1 + market filter | If Nifty 500 < its 200-DMA at a refresh: exit all, no entries. Re-enter at the next refresh above it | W |
| | **M8** | Dual momentum | M2, but only names with R6 > 0 and R6 > Nifty 500 R6; empty slots stay cash | W |
| 4 Entry timing | **M9** | M1 + extension veto | Skip a buy if day return > 5%, C > 1.10·SMA20 or RSI14 > 75; retry at the next refresh. No extra exits | W |
| 5 Events | **M10** | Gainer event + confirmation | E1 S7 with A6 state machine; candidates = frozen M5 top 50 | W (events daily) |
| | **M11** | 52-week-high breakout | Close > prior 252-session high **and** volume ≥ 1.5× median20, among the R6 top 100; entries on any day | W |
| Controls | **C0** | Current live rules (S0-E1) | v0.2.1 per E1 A4. Delivery data only from 2020; volume-only before that | daily |
| | **C1** | Short-term winners | Top 10 by 5-session return, equal weight, rebuilt weekly | W |
| 6 Ensemble | **EN** | Equal-capital sleeves of the **dev-selected strategies** (max 4) | Each sleeve gets 1/k of the capital and runs its own rules. Composition is set mechanically by §5 | — |

That is 13 tested strategies plus 1 ensemble. **The number of trials is 14, and it is disclosed with every result.**

## 5. Selection on development only (mechanical)

A strategy (not C0 or C1) **passes dev** only if all of these hold:
1. Excess CAGR vs B2-net is > 0 over the whole development period.
2. Excess is > 0 in **at least 3 of the 4** dev blocks.
3. `MDD − MDD_B2net ≤ 10 pp`.
4. Excess vs B2-net is > 0 at **1.0%** cost too.

Passers are ranked by dev Sharpe. The **top 5 are selected, with at most 2 from the same tier**. The EN ensemble is made of the top 4 selected, equal capital.

The selection is written to `results_e2/selection.json` **before** any holdout metric is computed. The runner enforces this order.

## 6. Holdout verdict (run once)

A selected strategy is **"reliable (E2)"** if, in the holdout:
1. its excess CAGR vs B2-net is > 0;
2. it is positive in at least 2 of the 3 holdout blocks;
3. `MDD − MDD_B2net ≤ 10 pp`.

Also reported: a moving-block bootstrap 90% interval of the daily excess (block of 20 sessions, 5,000 replicates, seed 20261007), results at all three cost levels, and results split into bull and bear regimes.

"Reliable (E2)" still means a **paper shadow book next**. Nothing goes to real money from a backtest.

## 7. Known limits

- Industry labels are as of today, and delisted names have none.
- Corporate actions are only partly adjustable: rights issues and demergers are alerts.
- Liquid-500 is a proxy for the Nifty 500, not the official index.
- Fourteen trials in total. Holdout passes are judged knowing that.

---

## 8. Data amendments, made before any E2 strategy result was examined (2026-10-07)

- **A9 Corporate actions.**
  - **Adjustable events:** equity bonus `a:b` and face-value split `X→Y`. Where both happen on the same ex-date, the factors are multiplied. The factor applied is the candidate that the **ex-day close ratio confirms within ±30%**.
  - **Not share bonuses:** bonus preference shares and bonus debentures are not adjusted as share bonuses.
  - **Value-neutral treatment:** any day with a corporate-action record (demerger, scheme, special dividend, or an unconfirmed split or bonus) and an **ex-day close ratio of ≤ 0.70 or ≥ 1/0.70** is made value-neutral and logged as `CA_NEUTRALISED`. There were 77 such days.
  - **Manual override:** one, PHILIPCARB on 2018-04-19 (ratio 0.21, no NSE record), listed in `data/pit/manual_ca.csv`.
  - **What remains:** > 40% daily moves left inside Liquid-500 are genuine events, such as DHFL, Jet Airways, 63 Moons, Infibeam, PC Jeweller, PNB and IndusInd.
- **A10 ETFs and mutual-fund units** (ISIN starting `INF`) are excluded from the universe.
- **A11 2-digit years** in some 2020 bhavcopy timestamps are parsed correctly. Every file's date is still verified.
