# Momentum Engine — Roadmap and operating rules

## Governing rules

1. **Trades generate observations. Observations update evidence. Evidence creates hypotheses. Only validated hypotheses change strategies.**
2. **Diversify hypotheses, not just securities.**
3. **The learning loop is slower than the trading loop.**
   - The daily books run frozen code. A frozen-code hash is recorded in `live/ledgers/registration.json`, and any change is flagged.
   - A proposed change runs as a *shadow* version. It replaces the current version only after a promotion gate:

     hypothesis → development test (2013–2020) → historical check → shadow paper book → enough new observations → owner approval
4. **Data periods:**
   - **2013–2020** is development data, used for all research.
   - **2021-01 to 2026-10-07** was the validation period. It is **spent** for the momentum family and is used only for information.
   - **From 2026-10-08** is the true forward test. Its ledgers are append-only.
5. **Generations:**
   - **E2** — signal discovery. Frozen: M11, M10, M2, plus C0 as a control.
   - **E3** — portfolio and risk construction only. Selection stays frozen.
   - **E4** — new strategy families.
   - **E5** — ensemble/orchestration, built only on forward evidence.
6. Every pre-trade record holds **objective signal values**, never subjective confidence. History is never rewritten; follow-ups are appended.
7. Report, don't advise. These are paper books; the owner makes every real-money decision.

## Daily schedules (Mon–Fri, IST)

| # | Time | Job | Output |
|---|---|---|---|
| 1 | 20:30 | `live/evening_batch.py`: NSE data → C0 engine → point-in-time update → M11, M10 and M2 books → Codex challenge → git commit | `live/ledgers/evening_<date>.json` |
| 2 | 22:00 | Research step: the next unchecked item below. Time-boxed to 45 minutes; development data only; Codex reviews it | `reviews/research_<date>_<id>.md` |
| 3 | 10:35 | Morning report: provisional opens, news check, `live/morning_report.py`, Drive upload, message to owner (~11:00) | `reports/desk_<date>.html` |

Reserved: a fundamentals-fetch schedule, once the data source is confirmed (R7).

## Research backlog (the nightly job takes the first unchecked item)

- [ ] **R0 — E2.1 corrected re-run.** Approved by the owner on 2026-10-08. **Scheduled for Sat 2026-10-10 10:00 IST** as the one-time task `momentum-e21-corrected-rerun`. It works in a new `experiments/e21/` package, so the live v1.1 code stays frozen. **The nightly job skips this item.** Codex audit 2026-10-08 (`reviews/codex/E2_audit_2026-10-08.md`) returned **AUDIT FAIL**.
  - **What passed:** the arithmetic reproduces exactly (all 447 M11 trades).
  - **What doesn't:** the E2 verdicts cannot be certified. Until R0 is done, E2 is **exploratory screening only**. The live books keep running as the forward test, which is the real validation anyway.
  - **Already fixed in v1.1** (2026-10-08, before the first fill): B5 sector cap for unknown labels; B8 M10 T0 midpoint; part of B1 (CA de-duplication).
  - **Remaining fixes:**
    - **B1:** use corporate-action factors from entitlements (not ex-day closes), plus an entitlement ledger for demergers, special dividends and rights.
    - **B2:** make B2-net a self-financing book on the common fill rules.
    - **B3:** effective-dated security identity (ISIN/rename history, e.g. PHILIPCARB→PCBL), plus delisting and merger proceeds (e.g. GSKCONS→HUL 4.39:1). Today, stale positions stay alive indefinitely.
    - **B4:** an authoritative exchange calendar that includes special sessions (e.g. 2024-01-20, 2024-05-18, Muhurat). Separate holidays from download failures, and backfill the gaps.
    - **B6:** withdraw the "untouched holdout" claim; seal dev selection before any continuation.
    - **B7:** apply month-end membership at the next open.
  - Then re-run dev selection and report sensitivity. These are bug fixes, not strategy changes, but they **may change which strategies pass**.

Each item runs on 2013–2020 unless stated otherwise. It must not touch `live/`, `src/`, the frozen experiment files, or the books. If an item needs an owner decision, it stops at **AWAITING OWNER** and the next night moves to the next item.

- [x] **R1b — R1 follow-ups from the Codex review.** *Result (dev): all fixes applied; M11 60d excess +4.30% [+2.8,+5.7] on the clean sample with the entry-aligned B2 (R1: +4.05%), observed-only hit rate 50.7% (R1's 49%/38%-in-2020 were artefacts), 50 of 6,460 outcomes stale/unfillable (−0.06 pp), no bucket contrast survives Holm across 44 tests. `reviews/research_2026-10-09_R1b.md` (Codex: REVIEW ISSUES — invariance check not run, clean sample is future-conditioned, repeat-A boundary, two reporting errors fixed in text).*
  - Count missing returns as missing, not as losses, in hit rates.
  - Correct the count labels and the treatment of stale or unfillable returns.
  - Align the benchmark's entry timing.
  - Use dependence-aware bootstrap blocks and bucket contrast tests with multiplicity control.
  - Drop the book-attribution claim.
- [x] **R1 — Why does M11 work?** *Result (dev): M11 signals +4.05% 60d excess vs B2-net but median +0.36% and ≈0 without the top 5% (right-tail driven); <1.5× volume breakouts +2.84% (CIs overlap), no monotone volume or first/repeat effect. `reviews/research_2026-10-07_R1.md` (Codex review pending).* Group its signals by volume ratio (1–1.25, 1.25–1.5, 1.5–2, 2–3, >3×), by how far the close is above the prior 52-week high (0–1, 1–3, 3–5, >5%), and by first versus repeat breakout. Measure the forward 5, 10, 20 and 60-session return in excess of B2. Analysis only; no rule change.
- [ ] **R2 — Does agreement between strategies help?** For each stock-day, count how many of M2, M5, M8, M10 and M11 select it, then compare forward returns by count (1, 2, 3, 4+). Report whether the relationship rises steadily, with bootstrap intervals.
- [ ] **R3 — Risk metrics for the E2 books (development period).** Average drawdown, drawdown duration, time to recovery, worst rolling 1- and 3-month returns, downside deviation, CVaR 95%, share of positive months, rolling 12-month excess, and pairwise correlation between the books.
- [ ] **R4 — Draft the E3 specification.** One change at a time on frozen M11, M10 and M2:
  - E3.1 sizing: equal, inverse-volatility, or ATR-risk;
  - E3.2 breadth: 10, 15, 20 or 30 stocks;
  - E3.3 sector cap: none, 30% or 20%;
  - E3.4 portfolio volatility targeting.

  Pre-register the metrics from R3. Codex challenges the draft. **AWAITING OWNER** before running.
- [ ] **R5 — Run E3.1 (sizing)** on development data, if R4 is approved. The 2021–26 result is shown for information only.
- [ ] **R6 — Specify and run a mean-reversion family on development data.** The hypothesis is short-term oversold within an intact uptrend, motivated by C1 losing 43% a year. Report its correlation with the momentum books.
- [ ] **R7 — Feasibility of point-in-time fundamentals.** Can NSE filings provide quarterly financial results with their **filing dates**? Check coverage, history depth and parsing effort. Output: a go/no-go for the quality, value and earnings families, and a design for schedule 4.
- [ ] **R8 — Sector rotation family.** Sector relative strength from Liquid-500 constituents, with a specification and a development-period test.

## Status

- E1 — done; superseded (survivorship bias). `experiments/results/`
- E2 — done, but **exploratory**: Codex audit 2026-10-08 = AUDIT FAIL on data and benchmark issues (see R0). Selection was logged in `selection.json` before the holdout table, but the holdout was not untouched (E1 had already examined 2022–26).
- Forward paper books — live from the 2026-10-08 open, code v1.1 (`live/ledgers/registration.json` lists patches). `live/ledgers/`
