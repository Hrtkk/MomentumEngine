# Momentum Research Engine — Strategy v0.1

> Status: **v0.1 agreed 2026-10-07 (§14). Amended to v0.2 pre-live the same day after a dry run — see `strategy_ledger.md` (stop, sizing for ₹30k, cooldown, 10:00 schedule). Where this file and the v0.2 ledger entry differ, the ledger wins.**
> Mode: **paper only.** No real-money orders. Every output is the result of a pre-registered rule, not a recommendation. The owner makes every real call (repo `CLAUDE.md`: "report, don't advise").
> Started 2026-10-07 · Draft: Claude (Opus 5.5) · Review: Codex CLI 0.154.0

---

## 0. Summary

Each NSE trading day, a script takes the **top 100 gainers within the Nifty 500**, stores them permanently, and scores every eligible name over a rolling 7-session discovery window on a fully specified, reproducible **Momentum Quality Score (MQS)**. Two things are produced from that:

1. **Research cohorts** — the *measurement* layer. Equal-weight groups (MQS top-10, raw top-10 gainers, persistence top-10, random-10, …) whose 10-session forward returns tell us whether the scoring predicts anything. This is where learning comes from.
2. **The 10-slot watchlist + paper portfolio** — the owner's *operating* view. Challengers compete with the weakest incumbent; adds and removals are mirrored into a simple paper portfolio.

Every decision and rejection is logged with its reason **before** outcomes are known. Rules change only through versioned, pre-registered tests with explicit statistical thresholds. The question being answered: **"Does anything in this process predict forward returns better than naive baselines, and under what regime?"** — not "were our picks right?"

---

## 1. Hypotheses (pre-registered)

The owner's proposal treats gainers as a **discovery universe**, not as the strategy itself. The engine tests whether that universe contains a usable signal:

| # | Hypothesis | Primary test (§8) | Note |
|---|---|---|---|
| H1 | The discovery cohort (all 100) beats Nifty 500 over **C(t+1)→C(t+10)**, close-to-close, price returns on both legs (§8.2) | Benchmark excess panel | Short-horizon returns tend to **reverse** in the literature — Jegadeesh (1990), *J. Finance* 45(3); Lehmann (1990), *QJE* 105(1). This is the strongest case against the project. |
| H2 | MQS top-10 beats Random-10 drawn from the same eligible candidates | Paired daily spread | Core question: does the scoring add anything? |
| H3 | MQS top-10 beats persistence top-10 ("most appearances") | Paired daily spread | Does the score beat counting appearances? |
| H4 | Adding an entry-timing filter (EQS ≥ 60) improves MQS top-10 | Paired spread, MQS∧EQS vs MQS | Separates stock quality from entry timing |
| H5 | Any edge depends on regime (breadth) | H2 spread split by regime | Regime is **logged only** in v0.1 |
| H6 | MQS beats a plain 63-session-return ranking | Paired spread | Is our multi-factor score better than simple medium-term momentum? |

Medium-horizon (3–12 month) momentum is the well-documented effect — Jegadeesh & Titman (1993), *J. Finance* 48(1). H6 checks whether our score adds anything beyond it.

**Primary endpoint:** 10-session return, **open of t+1 → close of t+10**. Horizons of 1, 3, 5 and 20 sessions are recorded but are **exploratory** (picking the best horizon after the fact would be model selection).

---

## 2. Data

Reachability checked 2026-10-07 ~20:40 IST.

| Need | Source | Status |
|---|---|---|
| End-of-day OHLC, volume, turnover, **delivery %**, all NSE equities | NSE `sec_bhavdata_full_DDMMYYYY.csv`, `https://nsearchives.nseindia.com/products/content/` | ✅ 06-Oct and 07-Oct files returned HTTP 200 (07-Oct was up by 20:40 IST; publish time otherwise unverified) |
| Index closes (Nifty 50, Nifty 500, sector indices) | NSE `ind_close_all_DDMMYYYY.csv`, `…/content/indices/` | ✅ |
| Nifty 500 membership + industry | `ind_nifty500list.csv` (nsearchives / niftyindices) | ✅ |
| Symbol master, listing dates | `EQUITY_L.csv` | ✅ |
| ≥ 252-session history; split/bonus adjustment factors | `yfinance` 0.2.66 in the project `.venv` (both raw and adjusted series) | ✅ |
| Catalysts / news (annotation only) | Claude WebSearch / WebFetch; NSE announcements | ✅ |
| Kite MCP (broker) | — | ❌ failed to connect; not needed for paper mode |

**Rules for data handling:**
- Reconcile **like with like**: compare Yahoo's *unadjusted* close with the bhavcopy close. Store adjustment factors separately. Factors are computed on adjusted series. Paper share quantities are adjusted explicitly on corporate-action dates.
- Every downloaded file is stored unmodified, together with its retrieval timestamp and SHA-256 hash.
- **Missing or stale essential input → no new watchlist adds or paper orders that day**, plus a logged exception. Yesterday's values are never silently reused.
- The Economic Times reports in `reference/` are **exploratory context only**. Their timestamps are mixed (intraday vs close), they cover one day each, and they validate nothing.

---

## 3. Universe

1. **Membership snapshot:** download the Nifty 500 list every day and store it dated. Membership is always taken as of day *t*.
2. **Discovery set (day t):** EQ-series rows of day-*t* Nifty 500 members with a positive return `close/prev_close − 1`. Rank by return and take the **top 100**; ties are broken alphabetically by symbol. All NSE EQ rows are also archived separately.
3. **Eligibility** (evaluated *after* discovery; failures stay in the discovery cohort with a reason code and are never dropped):
   - close ≥ ₹50
   - median daily turnover over the **previous 20 sessions (excluding today)** ≥ ₹10 cr
   - ≥ **252 valid sessions *preceding* t**; otherwise `INELIGIBLE_HISTORY`
   - no essential factor missing (§4)
4. **Candidate set (day t):** eligible names that appeared in the discovery set on any of the last **7 sessions** (including today), rescored with day-*t* data. **Open watchlist names are always rescored**, even after they drop out of the window.
5. **Retention:** discovery, candidate and outcome rows are permanent. Later suspensions, delistings, index removals and unresolved outcomes are retained and flagged, never silently removed.
6. **Flags (not rejections in v0.1):** upper-circuit heuristic (`high == close` and return ≥ 9.9% on ≥ 2 of the last 5 sessions), delivery % < 25, ASM/GSM membership if available. Flags become rejection rules only after evidence (§9).

---

## 4. Momentum Quality Score (MQS) — fully specified

**Reference population** = day-*t* **eligible candidates only** (§3.4). Holdings outside the window are never added to it.

**Percentile** of a candidate's raw factor value: `100 × (average_rank − 1) / (n − 1)`, ranked ascending so that higher = better. If n = 1, the percentile is 50. Ties get the average rank.

**Percentile of a non-candidate holding** (an incumbent outside the window): linearly interpolate its raw value against the sorted candidate raw values and their percentiles, clipping to 0 below the minimum and 100 above the maximum.

**Indicator definitions** (all on split/bonus-adjusted OHLC; *t* = signal date):
- SMA*n* = simple mean of the last *n* closes, including *t*.
- TR = max(H − L, |H − C₋₁|, |L − C₋₁|).
- ATR20 = Wilder smoothing with period 20, seeded with the simple mean of the first 20 TRs in the stored history: `ATR_t = (19 × ATR_{t−1} + TR_t) / 20`.
- RSI(14) uses Wilder smoothing, seeded the same way.
- "Preceding *k* sessions" means *t−k … t−1*, excluding *t*.

| Factor | Raw value | Weight | Essential? |
|---|---|---:|---|
| Relative strength | 0.5 × (21-session return − Nifty 500 21-session return) + 0.5 × (63-session return − Nifty 500 63-session return), close-to-close | 25 | yes |
| Trend structure | count of {C > SMA20, C > SMA50, C > SMA200, SMA20 > SMA50, SMA50 > SMA200} → 0–5 | 15 | yes |
| Volume confirmation | mean of the percentiles of (volume ÷ median volume over the previous 20 sessions) and (delivery % ÷ median delivery % over the previous 20 sessions) | 15 | yes |
| Breakout | mean of the percentiles of (C ÷ max high of the preceding 55 sessions) and (C ÷ max high of the preceding 252 sessions) | 15 | yes |
| Persistence | number of appearances in the **discovery** set over the last 7 sessions, capped at 4 | 10 | yes |
| Sector strength | sector index 21-session return − Nifty 500 21-session return (industry → sector-index map in `config/sector_map.csv`) | 10 | **no** — unmapped → percentile 50, flagged |
| Volatility quality | −(ATR20 ÷ C) | 10 | yes |

For **Volume confirmation** and **Breakout**, the factor's percentile **is** the mean of its two sub-percentiles, used directly with no second ranking.

`MQS_raw = Σ weight × factor_percentile / 100`

**Penalties** are stored as positive deduction points and logged individually:

| Code | Rule | Deduction |
|---|---|---:|
| `SPIKE` | day-*t* return > 10% **and** persistence = 1 | 15 |
| `EXTENDED` | C > 1.15 × SMA20 | 10 |
| `DOWNTREND_BOUNCE` | C < SMA200 **and** C < 0.65 × max high of the preceding 252 sessions | 15 |

`MQS = clip(MQS_raw − Σ deductions, 0, 100)`

**Exploratory factor (logged, weight 0):** close quality = `(C − L) / (H − L)`; if H = L, the value is 0.5.

**Changes from the owner's proposal:**
- The market-relative factor is merged into relative strength; it was double-counted.
- Catalyst quality and "operator-like" judgements are now **annotations**, because they aren't reproducible yet.
- Close-in-range is **recorded as an exploratory factor, not weighted**. It was suggested by a single day of data.
- Gap, illiquidity and circuit penalties are covered by the eligibility rules and flags.

---

## 5. Entry Quality Score (EQS) — specified, logged, not gating

Each input is mapped linearly to 0–100 between its "good" and "bad" bounds, clipped. EQS is the equal-weight mean.

| Input | 100 at | 0 at |
|---|---|---|
| C ÷ SMA20 − 1 | ≤ 6% | ≥ 12% |
| C ÷ (55-session breakout level) − 1 | ≤ 5% | ≥ 10% |
| RSI(14), Wilder | ≤ 70 | ≥ 78 |
| Consecutive up closes | ≤ 3 | ≥ 5 |

In v0.1, EQS **does not block watchlist adds or paper orders**. It feeds cohort H4 only. If H4 is supported, gating with EQS becomes a candidate change (§9).

---

## 6. The 10-slot watchlist (owner's operating view)

All rules are mechanical and evaluated after the close of day *t*:

**Ordering everywhere:** sort by MQS descending; the final tie-break is symbol ascending.

**Add-eligible** means all of the following: an eligible candidate, not currently held, MQS ≥ 70, and a valid stop under §7 (`S < C`, distance ≤ 8%).

1. Rank all candidates, and all current holdings rescored per §4, by MQS.
2. **Remove** an incumbent if its MQS < 50, it becomes ineligible, or its stop was hit (§7).
3. **Pending exits:** a slot whose exit has not yet filled (locked or suspended) stays **reserved**. It counts as occupied, and its replacement is deferred until the exit fills.
4. **Add:** fill free, unreserved slots with add-eligible names in order.
5. **Replace:** compare the best remaining add-eligible name with the weakest incumbent that is unreserved and has been held ≥ 3 sessions. If the challenger's MQS minus the incumbent's MQS ≥ 10, swap them. Repeat against the updated roster, at most **2 swaps per day**.
6. Fewer than 10 names is normal. **Cash is a valid outcome.**

Each day produces a **Keep / Add / Replace / Remove** list with rule codes. Names ranked 11–25 are logged as "Watch" with their rejection reason (e.g. `BELOW_THRESHOLD`, `NO_SLOT`, `CHURN_GUARD`). This feeds the false-negative review.

### 6.1 Thesis record (auto-generated before the fill; Claude adds sourced notes)

```
symbol, signal_date, strategy_version, run_id
MQS, EQS, factor percentiles, penalties, flags
why: top-3 contributing factors (auto)
expected: continuation over the 10-session primary horizon
stop: §7 price; size: §7
notes (Claude, ≤3 lines, with links): catalyst / adverse news — no effect on rules
```

---

## 7. Paper portfolio (mirrors the watchlist)

- **Notional capital:** ₹10,00,000, with **no borrowing** (cash-constrained). Each watchlist name targets **equal weight, 10% of equity**: `qty = floor(0.10 × equity_at_close_t ÷ C_t)`. Quantities are **frozen before the next session**.
- **Execution order at the open of t+1:**
  1. All exits fill first; the cash they release is available immediately.
  2. Buys then fill in watchlist order (§6). If cash, after costs, cannot cover the frozen quantity at the open price, the quantity is reduced to the largest affordable integer and logged as `PARTIAL_CASH`. A quantity of 0 means the buy is skipped (`NO_CASH`) and the slot stays free.
- **Entry:** market order simulated at the **open of t+1**. There is no gap guard in v0.1; the size of opening gaps is measured instead. If the open of t+1 is ≤ S, the entry is **cancelled** (`GAP_BELOW_STOP`).
- **Stop *S*:** fixed at signal time using day-*t* data: `S = max(C − 2 × ATR20, breakout_level − 0.5 × ATR20)`, where breakout_level = max high of the preceding 55 sessions.
  - If S ≥ C, or S is more than 8% below C, the name is not add-eligible (`STOP_INVALID` / `STOP_TOO_WIDE`). The stop is never moved to make it fit.
  - The stop is active from t+1 and never loosens.
  - **Fill rule on each active session:** if the open ≤ S, fill at the open; otherwise, if the low ≤ S, fill at S.
  - If the stock is locked at its circuit or suspended, the exit stays unfilled and is logged, and the slot stays reserved (§6). The exit is retried at each next open.
- **Exits:** stop, or watchlist removal/replacement, which is filled at the next open. **v0.1 deliberately has no** trailing stops, partial reductions or confidence tiers. They are deferred hypotheses.
- **Regime:** logged daily but **not used to gate trades in v0.1**. Order of evaluation: Risk-off if breadth < 30% or Nifty 500 < SMA200; else Risk-on if breadth ≥ 50% and Nifty 500 > SMA50; else Neutral. Breadth is our own count of Nifty 500 stocks above their SMA50. (ET showed about 24% on 06/07-Oct; that figure is context only, not our measurement.)
- **Costs:** results are reported under three round-trip cost scenarios: **0.30% / 0.60% / 1.00%**, charged proportionally on each fill. These are assumptions. No "after-cost edge" claim may rest on the 0.30% case alone. Real costs will be checked against a broker contract note.

The portfolio exists to make the watchlist concrete and to measure execution effects. **It is not the main evidence for or against the strategy** (that's §8). It is too sparse for that.

---

## 8. Measurement

### 8.1 Research cohorts (primary evidence)

Each signal date *t* produces equal-weight cohorts with a **fixed 10-session holding period: open of t+1 to close of t+10, no stops**. The cohorts overlap and are research measurements, not separately funded portfolios.

| Cohort | Members |
|---|---|
| `DISCOVERY` | all 100 discovery names (including ineligible) |
| `ELIGIBLE` | all eligible candidates |
| `MQS10` | top 10 candidates by MQS |
| `MQS10_EQS` | MQS10 restricted to EQS ≥ 60 |
| `PERSIST10` | top 10 by persistence, ties broken by day-*t* return |
| `RAW10` | 10 largest day-*t* gainers among eligible names |
| `MOM63_10` | top 10 eligible names by 63-session return |
| `RANDOM10` | **1,000** draws of 10 eligible names, sampled **without replacement within each draw** → report the median and the 5th–95th percentile range |

**Cohort conventions:**
- Every comparator except DISCOVERY is drawn from the **same eligible candidate set** for date *t*.
- Size is `min(10, n)`. An empty cohort's return is `UNAVAILABLE`.
- Ties: the cohort's primary key (descending), then symbol ascending.
- Membership and equal weights are **frozen at formation** and never renormalised over the names that have outcomes.
- A cohort's return stays `UNRESOLVED` while any member lacks its endpoint price. Registered terminal-value rule: if a member has no trade for 5 sessions after its endpoint (suspended or delisted), its last traded close is used and the row is flagged `TERMINAL_LAST_CLOSE`.
- **RANDOM10 reproducibility:** NumPy `default_rng` (PCG64) with seed = integer `YYYYMMDD` of date *t*. The eligible list is sorted by symbol before sampling. `rng.choice(n, size=min(10,n), replace=False)` is called 1,000 times in sequence.

### 8.2 Statistics

- **Cohort spread:** for example, MQS10 − RANDOM10 median, calculated daily. Both legs share the same timestamps, so the benchmark-timing problem cancels.
- **Benchmark excess panel** (H1 only): a separate panel of **close of t+1 → close of t+10** stock returns minus Nifty 500 returns over the same window, so that both legs use closes.
  - **Both legs are price returns.** The Nifty 500 price index from `ind_close_all` is matched against stock closes adjusted for splits, bonuses and rights only; **dividends are excluded on both sides**.
  - A demerger is treated as a corporate-action adjustment using Yahoo's factor. If no factor is available, the row is flagged `CA_UNRESOLVED` and left out of the panel; that exclusion is logged and counted.
- **Daily cross-sectional rank IC** (Spearman) of MQS and each factor against 10-session forward returns. Subtracting a benchmark doesn't change the IC, so IC is reported once, not as several separate confirmations.
- **Primary change metric:** the **mean paired daily improvement**, i.e. the mean over signal dates of (variant cohort 10-session return − v0.1 cohort return for the same date).
- **Uncertainty:** a **moving-block bootstrap** over signal dates.
  - Block length is 20 dates, with each day's whole cross-section kept together.
  - 10,000 replicates, using NumPy PCG64 with seed `20261007`.
  - The **95% percentile interval** is reported. The observations are **not independent**: stocks repeat, sectors co-move and holding windows overlap. The effective sample is much smaller than the row count.
- Selection outcomes (fixed-horizon cohort labels) are reported separately from realised paper-trade P&L.

### 8.3 Decision review (qualitative)

At t+10, each watchlist add and each Watch-level rejection gets a label: TP, FP, TN, FN or neutral, using ±3% excess vs Nifty 500. For losers, an error type is added: selection, timing or exit. Short prose is written **only for material cases**: the 3 biggest misses and the 3 biggest failures each week. This is diagnosis, not grounds for changing rules.

---

## 9. Rule-change governance

| Milestone | What it allows |
|---|---|
| **Backfill** (§11, ~1 year of history using today's Nifty 500 list) | Exploratory reading of H1–H6. It is **survivorship-biased by an unknown amount**. It may be used to *register* hypotheses, never to *authorise* changes |
| **Session 30** | Operational review: data quality, bugs, report usefulness. **No model changes** except patch fixes |
| **≥ 120 fully matured signal dates** | Consider **one** pre-registered model change |
| Change accepted | Two stages, both required. **Development:** the primary metric's 95% block-bootstrap interval is above zero. **Prospective:** over the next **60 untouched signal dates** (plus 10 sessions for labels to mature), the prospective improvement's **own** 95% interval is also above zero. Otherwise the result is "inconclusive", which is a valid outcome, and v0.1 stays |

- **Shadow variants:** any proposed change (for example "use EQS as a gate", or "reject on the circuit flag") runs **in parallel as a shadow version from the day it is proposed**. It accumulates prospective evidence without touching v0.1. This is how we stay patient without standing still.
- Training labels whose windows cross a validation start date are purged. Holdout dates are never used for development.
- **Patch versions** (v0.1.x) are only for demonstrable data or logic bugs. History is re-scored into a *new column*; the original decision record is never overwritten.
- Every version is written to `strategy_ledger.md` with: the change, the reason, the evidence (window, n, statistic, interval) and the expected effect.

**Stop / pivot:** after 60 sessions, the owner may stop the experiment for practical reasons. After 120 matured dates, if the MQS10 − RANDOM10 spread interval includes zero **and** H1 shows no positive excess, the finding is "no evidence the score adds value". The likely pivot is to use gainers as an alert feed into a longer-horizon momentum model. A null result is not proof that gainers carry no signal.

---

## 10. Daily operation and division of labour

**One evening batch**, run after the bhavcopy is published (target 19:30 IST):

| Step | Owner of step | Output |
|---|---|---|
| 1. Download, hash and validate files; snapshot membership | Script | `data/raw/`, exceptions |
| 2. Score, run cohorts, mature earlier outcomes, update watchlist and paper portfolio | Script | `data/*.csv`, `ledgers/*.csv` |
| 3. Build daily report (regime, watchlist changes, exceptions, cohort scoreboard) | Script | `reports/YYYY-MM-DD.html` + CSV |
| 4. Sourced notes on **≤ 5 names**: watchlist adds/removes plus material events | **Claude** | notes appended to report |
| 5. Publish report + CSV to Drive; daily off-device backup of `data/` and `ledgers/` | **Claude** | Drive `Momentum Engine/YYYY-MM/` |
| Weekly (Fri) | **Codex**: independently recomputes a sample of scores and outcomes, audits data integrity, reviews code. **Claude**: weekly scoreboard (`reviews/YYYY-Www.md`) | audit notes |
| Exceptions | **Codex** investigates data/logic exceptions when flagged | patch proposal |

- **Code:** Codex implements the deterministic scripts and tests (once authorised); Claude reviews them.
- **Neither agent's presence or narrative blocks the mechanical run.** If the agents disagree, the rule output stands and the disagreement is logged. Neither agent overrides rules or gives the owner a buy/sell call.
- **Owner reading time: ≤ 5 minutes normally, ≤ 10 on exception days.** The top of the report shows the regime, watchlist Keep/Add/Replace/Remove, exceptions and the cohort scoreboard.

---

## 11. Storage

**Local canonical, one-way publishing to Drive, daily off-device backup.**

- **Canonical:** this project folder (moved on 2026-10-07 from `InvestmentStrategy/momentum-engine/` to its own repository, `StartupIdea/MomentumEngine/`). Codex CLI is local-only and has no Drive access, so the source of truth must be local. Git commits are part of the daily run, because git does not protect uncommitted data.
- **Drive:** the owner's `Momentum Engine/` folder. It receives daily reports, CSVs (converted to Sheets) and a zip backup. Drive is **never read back** into decisions. Claude's Drive connector can create folders, upload CSV→Sheets and read Sheets (verified 2026-10-07). Whether HTML previews properly in Drive still needs testing. If it doesn't, publish the reports as a Claude artifact or PDF instead.
- An unattended option for later is `gspread` with a service account (the libraries are already in `requirements.txt`). That needs the owner to create the credentials.

```
momentum-engine/
  STRATEGY.md               current rules (this file)
  strategy_ledger.md        append-only version history
  config/                   sector_map.csv, parameters.yaml (versioned)
  reference/                ET reports 06/07-Oct, original proposal summary
  data/
    raw/YYYY-MM-DD/         unmodified source files + manifest (timestamp, hash)
    membership/             daily Nifty 500 snapshots
    history/                adjusted + unadjusted OHLCV (parquet), adjustment factors
    discovery.csv           every day's top-100, eligibility, reason codes
    candidates.csv          every candidate-day: factors, percentiles, MQS, EQS, penalties, flags
  ledgers/
    watchlist.csv           every Keep/Add/Replace/Remove/Watch with rule codes
    portfolio.csv           paper positions, fills, cash, by cost scenario
    cohorts.csv             cohort members + 1/3/5/10/20 forward returns
    exceptions.csv          data/run exceptions
  reports/  reviews/  src/  tests/
```

The owner's five permanent datasets map as follows: Daily Scanner → `discovery.csv`; Candidate History → `candidates.csv`; Watchlist Ledger → `watchlist.csv` + `portfolio.csv`; Outcome Ledger → `cohorts.csv` (+ portfolio fills); Strategy Ledger → `strategy_ledger.md`.

`ops/watchlist.md` and `watchlist.txt` remain the owner's **human** watchlist. Nothing from the engine is promoted into them automatically; promotion happens only through the owner, for example via `/triage`.

---

## 12. Build order (pending owner authorisation — see §13)

1. Backfill ~1 year of history for today's Nifty 500 list and reconstruct daily discovery sets from bhavcopies. This produces an exploratory H1–H6 read, labelled survivorship-biased.
2. Run-1 pipeline: download, validate, score, cohorts, watchlist, paper portfolio, with tests. Codex writes it; Claude reviews.
3. Daily report + Drive publish + backup.
4. Paper go-live = session 1.

The repo is in "desk, not build" mode (`CLAUDE.md`, since 2026-08-11). This engine is a separate folder and does not touch the paused `src/`. **Building it needs the owner's explicit go-ahead** (§13 Q1).

---

## 13. Open questions for the owner

1. **Go-ahead to build** steps 1–4 of §12 (a Python pipeline in `momentum-engine/src/`)? This is an exception to "desk, not build" mode.
2. Universe: Nifty 500 only (default), or should a wider liquid universe be added later?
3. Notional ₹10 lakh and equal 10% weights — OK?
4. Drive folder name and location (default: `Momentum Engine/` at My Drive root)?
5. Should the daily run be triggered as a scheduled task, or manually by asking `/scan`?
6. Reconnect Kite MCP? (Optional.)

---

## Appendix A — Implementation conventions (binding; these override the main text where more specific)

**A1. Scoring edge cases (§4)**
- If the eligible candidate set is empty (n = 0), MQS is `UNAVAILABLE` that day. All MQS-driven removals, adds and replacements are suspended. Eligibility exits and stops still apply.
- RSI(14): average gain and average loss are each Wilder-smoothed, seeded with the simple means of the first 14 close-to-close changes. Edge cases: positive gain with zero loss → 100; zero gain with positive loss → 0; both zero → 50.

**A2. Cohort conventions (§8.1)**
- DISCOVERY and ELIGIBLE keep **all** their members. `min(10, n)` applies only to the top-10 selections.
- MQS10_EQS is MQS10 filtered to EQS ≥ 60, **without replacing** the names filtered out.
- PERSIST10 is ordered by (persistence desc, day-*t* return desc, symbol asc). RAW10 by (day-*t* return desc, symbol asc). MOM63_10 by (63-session return desc, symbol asc). MQS10 by (MQS desc, symbol asc).

**A3. Replacement lifecycle (§§6–7)**
- Each swap is a **linked exit/entry pair** for the next open. The entry executes **only if that exit fills at that same open**; otherwise the entry is cancelled and the slot reserved.
- Once a delayed exit fills, the slot is filled by a **fresh selection at that day's close**, executed at the following open. Stale challenger orders are never carried forward.
- Tenure counts the entry session as session 1. "Held ≥ 3 sessions" means the incumbent's entry was at least 3 sessions ago, counting the entry session.

**A4. Fillability and costs (§7)**
- **Fillability**, based on the bhavcopy of the fill session:
  - No trades (`NO_OF_TRADES = 0` or volume = 0) → nothing fills.
  - If H = L and C > previous close (locked at upper band) → **buys unfillable**, sells fillable.
  - If H = L and C < previous close (locked at lower band) → **sells unfillable**, buys fillable.
  - Otherwise both sides are fillable.
  - If the bhavcopy row is missing, nothing fills and an exception is logged.
- **Costs:** for round-trip rate *c*, charge `fill_notional × c/2` on each buy and each sell.
- **Each cost scenario (0.30 / 0.60 / 1.00%) is a fully independent paper portfolio**, with its own cash, quantities, equity and holdings.
- The frozen quantity is the §7 target quantity, reduced only by the affordability rule.

**A5. Return and corporate-action scope (all research returns, cohorts, IC panels and paper valuation)**
- All returns are **price returns that exclude dividends**, using prices adjusted only for splits and bonuses. Entry and endpoint prices are adjusted to the same basis.
- **Paper portfolio adjustments:**
  - Split or bonus with factor *f*: `qty × f`, `stop ÷ f`, cash unchanged.
  - Cash dividends: ignored (price-return convention).
  - Rights issues, demergers, mergers and any action not listed here: the position's valuation becomes `UNRESOLVED`, flagged for a logged manual resolution, and is never valued silently at the raw price.

**A6. Missing outcomes (§8)**
- A missing entry price (no fill at the open of t+1) makes that member, and therefore the cohort, `UNRESOLVED`.
- Missing endpoint: use the **first traded close within the 5 sessions after the endpoint**. If there is none, use the **last traded close on or before the endpoint** and flag `TERMINAL_LAST_CLOSE`.
- Formation weights are kept in **every** panel, including H1. `CA_UNRESOLVED` makes the aggregate unresolved rather than dropping and reweighting the member. (This supersedes the "left out of the panel" wording in §8.2.)

**A7. Bootstrap (§8.2)**
- Input: the chronological series of N signal dates. A block is valid only if **all 20 consecutive signal dates in it have complete paired outcomes**; dates are never filtered out before blocks are built. If no valid block exists, or N < 20, the result is "inference unavailable" and no interval is reported. Starts are drawn only from valid block start indices.
- For N ≥ 20, each replicate does the following:
  1. Draw `ceil(N/20)` start indices uniformly, with replacement, from `0 … N−20`.
  2. Concatenate the 20-date blocks and truncate to N.
  3. Compute the mean.
- 10,000 replicates are drawn from a single PCG64 generator with seed `20261007`. The interval is the 2.5th–97.5th percentile, linearly interpolated.

---

## 14. Review log

| Date | Reviewer | Summary | Resolution |
|---|---|---|---|
| 2026-10-07 | Codex (round 1) | Architecture sound, but v0.1 was under-specified and over-built. MUST items: universe = top 100 *within* Nifty 500; 252-session history; like-for-like reconciliation; fully specified formulas and percentiles; annotations have zero rule effect; regime log-only; frozen next-open orders, no gap guard; fixed stop with reject-if > 8%; primary endpoint O(t+1)→C(t+10); fixed-horizon cohorts; matched benchmark timing; ≥120 matured dates + bootstrap CI + 60 prospective dates before changes. SHOULD items: 1,000 random paths, MOM63 comparator, 3 cost scenarios, flag-not-reject circuits, separate selection labels from P&L. Also cut EQS gating, tiers, reductions, trailing stops and the top-25 narratives. | MUST and SHOULD items adopted in the revision (round 2 found 5 of them incompletely specified, fixed below). One disagreement resolved by compromise: Codex proposed removing challenger replacement and the 10-slot structure from v0.1. Claude kept them (the owner explicitly asked for them) as **mechanical, logged outputs**, while the **research cohorts (§8), not the portfolio, carry the evidence**. EQS is kept as logged-only, testing H4. Shadow variants added (Claude) so proposed changes gather evidence without breaking the freeze. |
| 2026-10-07 | Codex (round 2) | **Accepts the watchlist/portfolio compromise.** "AGREE WITH CHANGES": ATR/RSI not defined; double-percentile ambiguity; penalty sign; 252 *preceding* sessions; close-quality formula; stop fill rule, S ≥ C and entry gap below the stop; H1 timing and dividend treatment; prospective-interval requirement; incumbent percentile mapping; ties, replacement sequencing and empty cohorts; cash funding and pending exits; unresolved cohort outcomes; PRNG and bootstrap spec; premature "agreed" status | All fixed in §§1, 3, 4, 6, 7, 8.2, 9 (Claude). Choices made: cash-constrained (no borrowing), partial-fill-to-affordable; cancel entry if the open ≤ S; moving-block bootstrap. |
| 2026-10-07 | Codex (round 3) | Round-2 items resolved or partly resolved. 7 blocking edge cases: empty reference set and RSI edges; cohort size and tie conflicts; replacement lifecycle; fillability and per-scenario costs; corporate-action scope; missing outcomes; bootstrap construction | All adopted as **Appendix A** (Claude). Fillability predicate is derived from bhavcopy H/L/C/prev-close and trade counts. |
| 2026-10-07 | Codex (round 4) | Items A1–A6 resolved; A7 partly resolved (incomplete dates could be filtered out before blocks were built). No design-level blockers. Convergence rule accepted. **"AGREE: v0.1 is ready for owner sign-off"** | A7 fixed immediately (valid-block rule). Convergence rule recorded in `strategy_ledger.md`. |
