# Operating schedule — all five research routines

Configured date: 2026-10-11. Timezone: Asia/Kolkata (IST).
Automation ID: `momentumengine-five-research-routines`; app creation returned ACTIVE.

One local chat automation coordinates all five routines, with weekday wakes at
10:00, 21:00 and 23:00. These wakes initiate dependency-driven passes, not five
independent timers. A weekday is not proof of an exchange trading session.
Use the verified calendar and retain a non-session/missing-calendar reason.

## Ownership and recurring work

| Routine | Execution owner | Review / persistence owner | Scheduled work |
| --- | --- | --- | --- |
| R1 Market movers | Codex | Claude interpretation review when available; Codex persistence | 21:00 evening: validated price/volume, trend, relative-strength and risk scans |
| R2 Watchlist builder | Claude for research/dossiers; Codex for deterministic screening/intake | Codex challenge and sole state writer | Evening bounded intake; 23:00 independent fundamental discovery and dossiers; Friday weekly reconciliation |
| R3 Watchlist monitor | Codex for comparisons/trigger checks; Claude for thesis interpretation | Codex persistence; Claude checks economic interpretation | Evening risk pass; 10:00 changed-thesis/expiry checks using sealed overnight work |
| R4 News intelligence | Claude for significance and thesis relevance; Codex for collection/matching | Codex evidence challenge and persistence | Evening bounded news pass; 23:00 queued context research |
| R5 Report generator | Claude for editorial draft | Codex aggregation, numeric/source challenge and publication | Internal evening brief; 10:00 morning assembly, sealed by 10:15 |

The three lanes use the same state, budget ledger and immutable handoff contract
in [Routine 1](01_market_movers_plan.md). Use the other four plans for their exact
inputs, outputs, gates and acceptance criteria. No ownership label counts as an
executed review: retain author/reviewer identities and actual CLI results.

## Execution order and deadlines

At **21:00**, validate existing EOD artifacts from the governing 20:30 batch.
Run R1 and bounded R4 collection, then R2 intake, R3 risk monitoring and R5
internal brief. Seal by **21:30**, reserving the final five minutes for a
deterministic risk/health report. Reuse accepted dossiers; queue deep research.
If EOD is missing, produce a partial health/news report with price checks
NOT_EVALUATED. Never invoke `live/evening_batch.py` as a read-only fetch.

At **23:00**, after the existing 22:00 research backlog window, run the
independent fundamental-screen capability and priority R2/R4 research queue.
Stop/checkpoint by **01:00**. Friday performs the weekly reconciliation instead
of that night's ordinary allocation. Respect the shared daily, per-batch and
monthly budgets across midnight. This does not run or replace ROADMAP's nightly
development backlog.

At **10:00**, pin available committed overnight snapshots and the last verified
market session. Refresh only affected R3 assumptions plus expiry checks, then
produce R5 by **10:15**. An unfinished dossier cannot delay the report. Market
prices retain their prior-session label. The artifact is ready for future
integration with the existing 10:35 morning report; no new external sender is
enabled here. Monday morning may consume Friday's data and must label that date.

For delayed wakes, keep the intended slot and original cutoff/deadline. If that
slot is not exposed, use persisted completed-slot IDs to identify due work and
avoid duplicates. Missed deadlines get an explicit late/deferred result; do not
perform unlimited catch-up or claim timely execution.

## Claude execution and current readiness

Claude Code is installed at `/opt/homebrew/bin/claude`. On 2026-10-11, a
check outside the filesystem sandbox confirmed `loggedIn=true`,
`authMethod=claude.ai`, and an active Max subscription. A noninteractive,
tool-disabled request completed successfully and returned `CLAUDE_ACCESS_OK`.
The sandbox-only status check still reports unauthenticated because that context
cannot access the normal login/keychain. Recheck in the authorized execution
context on each pass. If normal login access is denied in an unattended run,
record AUTH_CONTEXT_UNAVAILABLE; do not treat that as proof the human logged out
or claim the run can bypass permissions. The live CLI test confirms access now,
not unattended execution readiness for every future run.

When authenticated, use noninteractive `claude --print` with bounded verified
evidence supplied via a file/stdin, a process timeout inside the lane deadline,
and budget reservation before dispatch. Leave model selection at the user's
configured default. Claude drafts findings; Codex challenges them and writes
accepted state. Do not bypass permissions, expose credentials, or allow Claude
to mutate paper books. If a call fails, retain its reservation until usage is
reconciled and record review availability accurately.

The runnable diagnostic overlay is now `research/runtime/pipeline.py` (installed
15 October 2026). Durable budget accounting, source adapters, results-led intake,
provisional dossiers and initial monitoring exist; production source certification
and complete company coverage remain unfinished. At each pass inspect actual artifacts. Missing applicable
implementation/readiness/budget controls produce BLOCKED or NOT_EVALUATED
records and durable tasks. Perform safe available read-only checks and persist
a human health report plus structured continuation state under `research/`.
No metered request is allowed without budget accounting. Never mark a plan
implemented or a data defect repaired because it has an active schedule.

## Persistence, scope and notifications

### Concrete stock output required

Owner correction on 2026-10-13: readiness notices alone do not satisfy the
research-report goal. At each morning/evening assembly, run
`.venv/bin/python research/runtime/build_stock_report.py` to compile the latest
committed market metrics and company-event registry into a named, factual stock
queue. This deterministic Codex compilation requires no model call and makes
no Claude interpretation or approval claim. Missing production gates block
qualification, not display of already sourced historical leads. Every item
must retain its source date, selection reason, verification class and next check.
When data are old, label them prominently rather than suggesting a fresh scan.
Read `research/state/stock_report/latest.json` for the current output. Reuse and
deduplicate unchanged reports; notify only when the source list materially
changes, a daily brief completes, or new user action is required. Health-only
output is appropriate only when no usable committed evidence exists. Do not
repeatedly send the same stock list as though its observations were new.

- Read governing repository docs and exact upstream manifests before every pass.
- Hold one single-writer lock; store immutable run IDs/reports, pinned upstream
  versions, unresolved tasks, completed slots and deduplicated blocker state.
- Keep frozen strategy code, registrations and paper ledgers intact. Do not
  stage, commit or push the repository from these passes.
- This schedule does not deploy cloud resources, poll continuously, or enable
  external messages. Google Sheet report publication is authorized below;
  publication access does not establish research-data readiness.
- Notify in this chat for a meaningful change, a completed daily brief, failure,
  material risk or required human action. Stay quiet on unchanged/non-actionable
  state; send one notice per persistent blocker until it changes.

This is a local schedule, not a cloud deployment. Keep the computer available
and the desktop app running for repository-based passes. Existing 20:30,
22:00 and 10:35 jobs are documented in ROADMAP; this setup has not verified or
modified their external schedulers. Initial schedule starts with the next due
weekday slot, **Monday 2026-10-12 at 10:00 IST**, subject to host availability.

## Google Sheet publication — authorized 14 October 2026

The reader-facing destination is the existing Zerodha Portfolio Ledger:
https://docs.google.com/spreadsheets/d/1uMgZd9anGrXOOleQlqwEHVT6zAXezsTBJxf9PnXTWK8/edit
Use the connected Google Drive Personal account specified in
`research/config/sheet_publication.json`. Only the five research tabs listed in
that configuration are writable. Preserve Strategy Allocation, Holdings,
Watchlist, sharing settings, workbook timezone and all other tabs.

After every sealed 10:00, 21:00 or 23:00 pass, publish the available final
factual report and stage statuses using the procedure in
`research/sheet_publication.md`. Morning/evening passes still run the factual
compiler first. The 23:00 pass publishes backlog/run status without implying
new stock evidence. Sheet publication is a deterministic Codex responsibility;
Claude retains research significance, dossiers, thesis interpretation and
editorial ownership. Do not claim Claude review unless it actually executed.

Research Dashboard, Research Stocks and Research Tasks are current views.
Routine Runs and Research Briefs retain deduplicated historical entries.
Verify remote readback before recording publication success. An unknown or
failed write remains UNKNOWN/FAILED; re-read remote IDs before retrying.
Never silently clear existing history or treat a failed publication as success.

The Sheet is the primary place for the owner to read final reports. Local
immutable evidence, manifests, owner tasks and checkpoints remain necessary
machine storage; they are not a competing report delivery channel. No new
user-facing local report is required solely because a Sheet was refreshed.

## Executable runner — repair of 15 October 2026

Run from the repository root:

`.venv/bin/python research/runtime/pipeline.py --session AUTO --slot <original-IST-slot> --lane <FAST-or-OVERNIGHT> --collect --run-claude`

Use FAST for 10:00/21:00 and OVERNIGHT for 23:00. Manual requested passes may
omit `--slot` and use EVENT. AUTO verifies dated official bhavcopy and UDiFF
files, rejecting mismatched dates; it never infers a holiday from an HTTP error.
It can reuse the last verified isolated session when current collection fails,
with that older date visible. This isolated research collector is authorized;
it does not invoke or replace the existing evening batch or change live books.

The runner owns the single-writer lock, original slot/deadline, immutable
five-stage handoffs, carried tasks, registry, named report and completed-slot
IDs. Repeating a completed slot validates and reuses it. Do not run the former
hard-coded health scripts as the main pipeline. Afterward run the stock compiler
(it preserves the new runtime snapshot) and the Sheet publication protocol.

Source requests and Claude dispatch reserve resources in
`research/state/budget.sqlite3` before execution. Unknown outcomes retain their
reservation; reconciliation requires usage evidence. API-equivalent costs are
accounting proxies, not Max subscription invoices. Pricing snapshot and expiry
are in `research/config/claude_pricing.json`; expired or unknown pricing blocks
only new metered dispatch until verified. Never clear budget state to retry.

Claude uses the configured default model with tools/hooks/connectors disabled,
one turn, short bounded output and a timeout. Reuse matching accepted evidence
packets without a new model call; record actual author, response/receipt hashes
and whether analysis was reused. Do not broaden budgets, change model or silently
replace Claude. A known failed output remains an incident, not accepted research.

Independent discovery scans publication-dated results filings without requiring
an R1 event. Verified tables feed sector-aware financial observations; unverified
OCR/metadata never supplies invented ratios. Up to three changed/provisional
dossiers per call remain below the plans' per-night ceilings. Morning/evening
passes reuse available dossiers; do not begin deep new dossiers in FAST. Friday
OVERNIGHT performs registry/expiry/missing-coverage reconciliation and uses its
review allocation instead of an additional ordinary dossier allocation.

Partial coverage yields PARTIAL reports with actual completed work. The following
remain separate production gates: historical calendar and identity/action
entitlements, sector benchmarks, broad financial-table parsing and company
valuation/cash-flow/governance reviews. No company is automatically QUALIFIED.
