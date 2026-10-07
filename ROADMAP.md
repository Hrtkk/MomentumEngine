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

Each item runs on 2013–2020 unless stated otherwise. It must not touch `live/`, `src/`, the frozen experiment files, or the books. If an item needs an owner decision, it stops at **AWAITING OWNER** and the next night moves to the next item.

- [ ] **R1 — Why does M11 work?** Group its signals by volume ratio (1–1.25, 1.25–1.5, 1.5–2, 2–3, >3×), by how far the close is above the prior 52-week high (0–1, 1–3, 3–5, >5%), and by first versus repeat breakout. Measure the forward 5, 10, 20 and 60-session return in excess of B2. Analysis only; no rule change.
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
- E2 — done. `experiments/results_e2/`; selection logged in `selection.json` before the holdout.
- Forward paper books — live from the 2026-10-08 open. `live/ledgers/`
