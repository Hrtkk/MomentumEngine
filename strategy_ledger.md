# Strategy ledger (append-only)

Never rewrite entries. Add follow-ups underneath.

---

## v0.1 — 2026-10-07 — design agreed (Claude + Codex), awaiting owner sign-off

- Rules: `STRATEGY.md` as of 2026-10-07, including Appendix A.
- Reviews: `reference/codex_review_round1.md` … `round3.md`. Round 4 result: "AGREE: v0.1 is ready for owner sign-off".
- **Convergence rule (agreed with Codex, round 4):** edge cases found during implementation are logged here as **v0.1.x patch conventions before the first live paper session**. They do not block sign-off of the design. Changes to hypotheses, selection rules or acceptance thresholds are **not** patches and remain governed by `STRATEGY.md` §9.
- Live paper session 1: — (not started)

---

## v0.2 — 2026-10-07 — pre-live amendment after dry run (owner-directed; Codex-challenged)

**Owner instructions (2026-10-07):**
- Paper capital ₹30,000.
- 5–10 stocks with a percentage split.
- Daily run at 10:00 IST, Mon–Fri.
- Codex acts as challenger.

**Dry-run findings (signals 06-Oct and 07-Oct; development observations only, no improvement claimed):**
- **P1:** the stop `max(C−2ATR, bo55−0.5ATR)` sat within noise after breakouts. Kotak's stop was ₹431.30 against a ₹431.90 close; 3 of 7 entries were stopped out on their entry day and re-added that evening.
- **P2:** with 10% slots on ₹30k, any stock priced above ₹3,000 was unbuyable.
- **P3:** there was no cooldown after a stop.

**Changes (reviewed: `reference/` Codex fix challenge, "AGREE WITH CHANGES" — all adopted):**
- **F1 — Stop.** `S = C_t − 2×ATR20_t`. Requires finite positive ATR and `0 < (C−S)/C ≤ 8%`. Frozen at entry. `GAP_BELOW_STOP` retained. This also changes selection, since names previously rejected as `STOP_INVALID` can now qualify.
- **F2 — Entry allocation target.** `w = 1/max(5, N)`, where N = roster size after removals, cooldown and affordability checks; each linked replacement counts once; max 10 names. Per book, `q = floor(w×E_t/C_t)`. One share is allowed when q = 0 and `C_t ≤ 20% E_t`; otherwise `NOT_AFFORDABLE`.
  - Execution: exits first, then buys in decision order. Quantity is reduced to available cash including costs, with `q×open ≤ 20% E_t`.
  - A zero fill releases the slot. There is no daily rebalancing. Fewer than 5 names leaves the remainder in cash.
- **F3 — Cooldown.** After a STOP exit in session e, entries are blocked in sessions e+1…e+5. Applied per book.
- **F4 — 10:00 run.**
  1. Finalise the previous session from official bhavcopy data.
  2. Generate signals from that close.
  3. Simulate today's open as **PROVISIONAL** (Yahoo, display only). Tomorrow's official batch is the record.
- **Bug fixes:**
  - Each cost scenario is now an independent book (own roster, cash and pending orders).
  - Failed exits are retried and keep their slot reserved.
  - A zero fill no longer shows as KEEP.
- **Shadow book:** `frac0.006` added (fractional shares) to measure integer-rounding noise.
- **Unchanged:** §8 research cohorts — same candidates, fractional equal weights, fixed horizons, no stops, cooldown or capital filters.
- **§9 exception:** this is a one-time, pre-live baseline amendment. v0.2 is frozen from the first scheduled live run, after which §9 governs all changes.
- **Owner sign-off of v0.2:** pending (requested 2026-10-07).

**Proposed shadow variant (Codex, 2026-10-07), not yet registered:**
- `SECTOR_CAP3` is the MQS10 cohort with at most 3 names per Nifty 500 industry, scanned in MQS order, with unfilled slots held as cash.
- Trigger: on 07-Oct, 5 of 10 holdings (47.7% of holdings value) were in Healthcare.
- It would run in parallel with no effect on the live rules. Owner decision needed to register it.

---

## v0.2.1 — 2026-10-07 — owner parameter change + 13-session historical replay

**Owner instructions (2026-10-07):**
- Paper capital ₹60,000 (was ₹30,000).
- Portfolio size "10 ±3": max 13 names; target weight `w = 1/max(7, N)`. The 20% per-name cap and the one-share rule are unchanged.
- P&L chart window: 13 sessions.

**Data fix (patch, pre-live):**
- On holidays NSE re-serves the previous session's bhavcopy under the holiday's date. 2026-09-14 and 2026-10-02 were duplicate files and created fake sessions.
- `fetch.py` now verifies `DATE1` (bhavcopy) and `Index Date` (index file) against the requested date, and stores nothing on a mismatch.
- The run affected by this bug is archived in `ledgers/_archive/replay_with_holiday_bug/`. The earlier ₹30k dry run is in `ledgers/_archive/dryrun_30k_2026-10-07/`.

**Replay (signals 17-Sep → 07-Oct, 13 P&L sessions, primary book at 0.6% costs)** — in-sample and exploratory. It uses today's Nifty 500 membership (survivorship bias) and split-adjusted Yahoo history fetched on 07-Oct. It is not evidence for or against the strategy.

| Measure | Result |
|---|---|
| Primary book | ₹60,000 → ₹58,183 (**−3.03%**) |
| Nifty 500 (same closes) | **−2.63%** |
| Other books | 0.3% cost −2.52% · 1.0% cost −3.61% · fractional −4.01% |
| Closed trades | 20, of which 3 winners; mean −2.72% |
| Stop-outs | 6 |
| Traded notional | ≈ ₹2.03 lakh (3.4× capital in 13 sessions); costs ≈ ₹610 |
| End-state holdings | 13, of which **8 Healthcare** |

**Observations to test as shadow variants (not live changes, per §9):**
- Replacement churn: 2 swaps/day across 13 slots.
- Sector concentration: see `SECTOR_CAP3` above.
- Whether to enter at all in Risk-off.

**Go-live:** the replay end state becomes the starting state for the scheduled 10:00 runs from 2026-10-08, unless the owner asks for a reset.
