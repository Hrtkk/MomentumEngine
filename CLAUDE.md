# CLAUDE.md — MomentumEngine

A paper-trading **research** platform for NSE equities. It was split out of `../InvestmentStrategy/` on 2026-10-07; the owner's human watchlist and daily desk (`ops/`) stay there.

## Read first
1. [ROADMAP.md](ROADMAP.md) — the governing rules, the daily schedules and the research backlog.
2. [experiments/SPEC_E2.md](experiments/SPEC_E2.md) — the frozen E2 strategies and the point-in-time data rules.
3. [strategy_ledger.md](strategy_ledger.md) — the append-only version history.

## Non-negotiable rules
- **Report, don't advise.** Never issue buy/sell/hold calls or price targets, even when asked; give the evidence instead. These are paper books of pre-registered rules, and the owner makes every real-money decision.
- **Sources and dates on every number.** Where something can't be verified, write `—` and say so.
- **Trades → observations → evidence → hypotheses.** Only validated hypotheses change strategies.
  - The daily books run frozen code; `live/ledgers/registration.json` holds the code hashes, and any change is flagged.
  - Changes go through shadow versions and the promotion gate described in ROADMAP.
- **Data periods:**
  - 2013–2020 is development data.
  - 2021 to 2026-10-07 is spent for the momentum family and is used for information only.
  - From 2026-10-08 is the forward test.
- **Ledgers are append-only.** Never rewrite history; add follow-ups underneath.
- **Codex is the challenger** on specifications, picks and results. Run it with `codex exec … < /dev/null` (it hangs on stdin otherwise). It has a usage quota.

## Layout
| Path | What |
|---|---|
| `live/` | Forward paper books M11, M10 and M2: `live_books.py`, `evening_batch.py`, `morning_report.py`, plus ledgers |
| `src/`, `config/`, `ledgers/` | C0, the original top-gainer engine, kept as a control book |
| `experiments/` | E1 and E2 backtests, the point-in-time data pipeline (`fetch_pit.py`, `pit_panels.py`) and `research/` |
| `strategy/` | Strategy register: one file per strategy (rule, why, entry/exit/stop, evidence, review log); `build_reports.py` → `reports/` (charts), `backtest.py` → `data/` |
| `reviews/` | Diagnosis and nightly research write-ups |
| `reports/` | Daily HTML reports and holdings CSVs |
| `live/market_sheet.py` | Rewrites the "MomentumEngine — Market Stats" Google Sheet after each evening batch (setup: `config/google_sheet.json`) |

## Environment
- `.venv/` (Python 3.11), built from `requirements.txt`.
- Run scripts from their own folder with `../.venv/bin/python`, or from the root with `.venv/bin/python`.

## Commands
```bash
.venv/bin/python live/evening_batch.py     # data -> books -> Codex challenge -> git commit
.venv/bin/python live/morning_report.py    # report (add --no-provisional outside market hours)
```

## Data gotchas (each one caused a real bug on 2026-10-07)

**NSE bhavcopy files**
- On holidays NSE re-serves the previous session's bhavcopy under the holiday's date. Always check the date inside the file (`DATE1` / `TIMESTAMP` / `TradDt`).
- `PREV_CLOSE` is **not** adjusted for corporate actions on the ex-date. Example: RELIANCE 1:1 bonus on 28-Oct-2024.
- Three formats:
  - `sec_bhavdata_full`, which has delivery %, from about 2020;
  - `cm…bhav.csv.zip` for 2011 to 2024-07;
  - UDiFF `BhavCopy_NSE_CM_…` from 2024-07.
- Some 2020 files use two-digit years.
- ISINs starting `INF` are ETFs or mutual-fund units, not equities.

**NSE corporate-actions API**
- Subjects come abbreviated ("Fv Splt Frm Rs 10 To Re 1") or combined ("Bonus 1:1 / Face Value Split").
- Bonus debentures and bonus preference shares are not share bonuses.
- A bonus and a split on the same ex-date may arrive as separate rows.
- Every factor is validated against the ex-day price ratio.
- Demergers and special dividends are handled as value-neutral (`experiments/SPEC_E2.md` §8).

**Survivorship**
- Yahoo history for today's Nifty 500 list is survivorship-biased and strongly inflates momentum backtests. Use the point-in-time Liquid-500 universe (`experiments/pit_panels.py`).
