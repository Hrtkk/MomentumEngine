# Experiment E1 — Strategy comparison S0–S7 (pre-registered 2026-10-07)

**Purpose:** reject strategies, not tune them. Every parameter below is fixed **before** the first run. Any change after the first comparison report becomes E2 with a new spec; E1 results are never overwritten.
Owner brief: the pasted "PMPE" plan (2026-10-07). The live engine (`src/engine.py`, v0.2.1) is untouched and is represented here as S0.

## 1. Data and known biases

| Item | Choice | Bias / limitation |
|---|---|---|
| Universe | Today's Nifty 500 list (2026-10-07). 499 symbols have Yahoo data (DUMMYHEG has none) | **Survivorship bias, strongly favourable to momentum.** No point-in-time constituents are available. Compare strategies **with each other and with B2**, never on absolute return |
| Prices | Yahoo daily OHLCV, `auto_adjust=False`: split/bonus-adjusted, dividends not adjusted → price returns | Yahoo errors are possible. Daily returns with abs > 40% on a stock are treated as data errors: that day is excluded from signals and the stock is not traded that day |
| Index | Nifty 500 price index (Yahoo `^CRSLDX`) | Price index; dividends excluded on both sides |
| Delivery % | NSE `sec_bhavdata_full` since 2020-09 (S0 only) | Where missing, S0's volume factor uses only the volume ratio |
| Sector | Industry from today's Nifty 500 list | Industry labels as of today. No sector-index history, so S0's sector factor is neutral (50) |
| Fundamentals | **Not available point-in-time** | **S6 (Momentum + Quality) is not run.** Using today's ROE/debt figures for past dates would be look-ahead bias |

**Test window:** the first signal date is the first session with ≥ 252 prior sessions for at least 300 symbols (≈ Oct-2020). The last is 2026-10-07. That is about 6 years, covering both bull and bear phases.

## 2. Common rules (all strategies unless stated otherwise)

- **Eligible on day t:** ≥ 252 prior sessions; close ≥ ₹50; median of (close × volume) over the previous 20 sessions ≥ ₹10 cr; valid data on t.
- **Timing:** decide on the close of t and trade at the open of t+1. Intraday stop: if the open ≤ S, fill at the open; otherwise, if the low ≤ S, fill at S. A row with H = L counts as locked: no buy if it closed up, no sell if it closed down.
- **Costs:** 0.30 / 0.60 / 1.00% round trip, half charged on each side. **0.60% is primary.**
- **Capital:** ₹60,000 notional, fractional shares (scale-free returns).
- **Portfolio (S1–S7):** 10 slots, entry target 10% of equity each, no weight rebalancing, max 3 names per industry, cash allowed.
- **Catastrophic stop (S1–S7):** `S = C_t − 3×ATR20_t`, fixed at signal time and never moved. Wilder ATR as in the engine.
- **Momentum definitions** (closes, in sessions): R3 = 63, R6 = 126, R12 = 252, `R12_1 = C[t−21]/C[t−252] − 1`. `VOL126` = std of daily log returns × √252. `VAM6 = R6/VOL126`. Percentiles are taken within eligible names on t, on a 0–100 scale. Ranking by return relative to Nifty 500 is identical to ranking by raw return, so raw is used.
- **Hysteresis (S1–S5, S7):** a name may **enter only if its rank ≤ 50**. A holding **stays while its rank ≤ 125**. If its rank is > 125 at a rebalance, it is exited at the next open. No rank-based swaps between rebalances.
- **Rebalance day:** the last session of each ISO week (S1, S2, S4, S5, S7) or of each calendar month (S3). Entries for S1–S4 happen only on rebalance days. S5 and S7 may enter on any day, but only from the latest candidate set.

## 3. Strategies

| ID | Selection | Entry | Exit (in addition to catastrophic stop) |
|---|---|---|---|
| **S0** | v0.2.1 as-is: top-100 Nifty 500 gainers, 7-session window, MQS (sector factor = 50), daily decisions, add ≥ 70, remove < 50, replace margin 10, max 2 swaps/day, tenure 3, 13 slots, weight `1/max(7,N)`, stop `C−2ATR` (reject if > 8%), 5-session cooldown, no sector cap | Next open | v0.2.1 rules (its own stop replaces the 3×ATR stop) |
| **S1** | Rank by R3, weekly | Immediate (next open after the rebalance) | Rank > 125 at a rebalance |
| **S2** | Rank by R6, weekly | Immediate | Rank > 125 |
| **S3** | Rank by R12_1, monthly | Immediate | Rank > 125 at a monthly rebalance |
| **S4** | Blend: `0.35·pct(R3) + 0.30·pct(R6) + 0.20·pct(R12_1) + 0.15·pct(VAM6)`, weekly | Immediate | Rank > 125 |
| **S5** | S4 rank ≤ 40 **and** trend filter (C > SMA50 and SMA50 > SMA200) → WATCH | **Patient entry**, checked daily. **Not extended:** day return < 5%, C/SMA20 − 1 ≤ 7%, RSI14 ≤ 70. **Reset seen:** max close of the last 10 sessions ≥ 1.03 × C, *or* (5-session high − low) ≤ 1.5 × ATR20. **Turning up:** C > C₋₁ | Rank > 125 at a rebalance; **trend break:** C < SMA50 → exit next open |
| **S6** | Momentum + quality | — | **Not run** (no point-in-time fundamentals) |
| **S7** | **Event T0:** eligible name with day return ≥ 5% and volume ≥ 2 × 20-session median. **Confirmation on day k, 3 ≤ k ≤ 7 after T0:** every close since T0 ≥ T0 midpoint (H+L)/2; C_k ≥ T0 high and C_k > max high of T0+1 … k−1; mean volume over T0+1 … k−1 < T0 volume. Ties ranked by S4 blend | Next open after confirmation | Close < T0 low → exit next open; S4 rank > 125 at a weekly rebalance |

**Benchmarks:**
- **B1:** Nifty 500 price index.
- **B2:** equal weight of all eligible names, rebalanced daily, no costs. B2 shares the survivorship bias, so it is the fair comparison.

## 4. Metrics (all on the 0.60% book unless stated)

- **Returns:** total return, CAGR, excess CAGR vs B1 and vs B2.
- **Risk:** annualised volatility, Sharpe (risk-free rate 0, stated), Sortino, maximum drawdown.
- **Trading:** turnover per year, total costs, number of trades, win rate, average win and average loss, average holding period (sessions), average exposure, average largest-industry weight.
- **By regime:** daily returns split into **Bull** (Nifty 500 > its 200-DMA on the previous close) and **Bear**, with annualised return and excess vs B2 in each. Also returns by calendar year.
- **Entry quality:** mean forward excess vs B2 over 5, 10 and 20 sessions from each entry fill.
- **Robustness:** results at all 3 cost levels, plus the first half vs the second half of the window.

## 5. Decision rule for E1 (fixed now)

- A strategy is **rejected** if, at 0.60% cost, its excess CAGR vs B2 is ≤ 0, **or** its maximum drawdown is worse than B2's by more than 10 percentage points, **or** its sign of excess vs B2 differs between the two halves of the window.
- Survivors move to a **paper shadow book**. Nothing goes live from a backtest alone, and no parameter is changed in E1.

## 6. Roles

- **Claude** builds `experiments/` and runs E1.
- **Codex** challenges this spec before the run (look-ahead, ambiguity) and audits the code and results after the run (independent recomputation of a sample).
- **Owner** decides what moves to a shadow book.

---

## 7. Pre-run amendments — Codex spec review (all 8 blocking items adopted; `codex_spec_review.md`)

**Status:** E1 is **exploratory package screening, conditional on today's surviving universe.**
- "Reject" means *not advanced under this policy*, not *disproved*.
- No component-level causal claims: S0 vs S4 changes many things at once.
- 2026-09-04 … 2026-10-07 was already inspected in the diagnosis. It is labelled **development data**.

**A1. Data flags.** A single-day return with abs > 40% is a data-validation **alert**:
- It never cancels or reprices fills, and it never drops a held position's return.
- It removes the name from **signals only**, from the flagged close onwards, for 253 sessions.
- Every flagged event that touches a held position is listed in the report with its P&L, as "unvalidated".

**A2. Prices and corporate actions.**
- Indicators and execution both use Yahoo split-adjusted prices. Stops and quantities are in the same units, so no quantity adjustment is needed.
- The ₹50 threshold uses the **nominal** close: `adjusted close × Π(split ratios after t)`, from Yahoo split history (`fetch_splits.py`).
- Liquidity uses close × volume, which is unchanged by splits.
- Yahoo does not adjust demergers or rights issues. They appear as price moves and are caught by the A1 alert list.

**A3. Benchmarks.**
- **B2-gross:** equal weight of names eligible at close t, executed at open t+1. The portfolio held from the previous open earns the overnight gap.
- **B2-net:** the same, charged per side on daily |Δw| turnover.
- **The rejection hurdle is B2-net.** B2-gross is reported as a stricter, frictionless reference.
- Differential survivorship bias between strategies is **unknown**.

**A4. S0-E1** (not "as-is"). The overrides are:
- fractional quantities, with the one-share affordability rejection removed;
- sector percentile fixed at 50;
- delivery optional: when the delivery ratio is unavailable, the volume factor uses the volume ratio alone, and eligibility does not require delivery.

All other v0.2.1 rules are kept. As a check, S0-E1 adds over 2026-09-17 … 10-07 are compared with the live ledger.

**A5. Lifecycle (S1–S5, S7).**
- **Sizing:** `qty = 0.10 × equity_close_t / C_t`, frozen at signal time. At the open, exits fill first, then buys in ranked order. Each buy is reduced to the available cash after fees; no borrowing.
- **Buys at the open** are skipped, and need a fresh signal later, if:
  - the open ≤ stop;
  - the stop is ≤ 0;
  - 10 positions are already held, counting unfilled exits as occupied;
  - the industry already has 3 positions, counting unfilled exits.
- **Stops** are active from the entry session.
- **Unfilled exits** are retried at each open.
- **Holdings that become ineligible** (data present, eligibility false) exit at the next open. If the data is missing, the position is held and logged as unresolved.
- No cooldown. Fresh signals are evaluated only after that session's execution.

**A6. State machines.**
- **Ranks:** S4 ranks and S5 WATCH membership are **frozen at each weekly refresh** until the next one.
- **S5 daily checks:** eligibility, the trend filter and the entry conditions are rechecked every day.
- **S7 candidates:** the frozen S4 top 50. A T0 counts only if the name is in that set on T0. One active event per name; newer events are ignored while one is active.
- **S7 day count:** k counts exchange sessions.
- **S7 invalidation:** the event is cancelled the first time any of these fails:
  - every close since T0, **including T0**, stays ≥ the T0 midpoint;
  - the name stays in the candidate set;
  - k ≤ 7.
- **S7 entry:** only the first confirmation counts, and the event is consumed after one opening-order attempt. The T0 low is kept for the exit rule.
- **Simultaneous entries:** allocated by frozen S4 score, highest first, then symbol ascending.

**A7. Numerics and calendar.**
- `Rk = C_t/C_{t−k} − 1`.
- VOL126 uses exactly 126 log returns ending t, with ddof = 1. Zero volatility makes VAM unavailable.
- RSI uses Wilder recursion over the full available history: `ewm(alpha=1/14, adjust=False)`. This is documented as differing from the engine's 300-close window.
- Ties: the engine percentile formula, with symbol ascending as the final tie-break.
- S5 windows include t. The 5-session range is `max(H) − min(L)`.
- The S7 volume median covers t−20 … t−1.
- **Rebalance days** are true period ends: the period containing the last data date (07-Oct-2026, mid-week) is not a rebalance.
- **Books:** all start together in cash and are valued at the final close. Orders left unexecuted stay unfilled.

**A8. §5 decision rule, replacing §5.** A strategy is advanced to a paper shadow book only if, at 0.60% cost, all three hold:
1. its excess CAGR vs **B2-net** is > 0 in the full window **and** in each half. The halves are the first `floor(N/2)` daily returns and the rest, from one continuous book.
2. `MDD_strategy − MDD_B2net ≤ 0.10`, with drawdowns measured as positive magnitudes.
3. Its results are reported at all three cost levels.

Inferential claims are reserved for a separately registered prospective evaluation.
