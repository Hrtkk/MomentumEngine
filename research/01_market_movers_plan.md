# Routine 1 — Market movers

Status: implementation plan, not an installed job. Plan version: 1.1, 2026-10-10. Amended following the supplied architecture review; deployment gates remain open.

Companion plans: [R2 watchlist builder](02_watchlist_builder_plan.md), [R3 monitor](03_watchlist_monitor_plan.md), [R4 news](04_news_intelligence_plan.md), [R5 reports, alerts and amendment tracker](05_report_generator_plan.md).

## Purpose and boundaries

Find unusual, verifiable price, volume and relative-strength events and pass evidence to the watchlist builder. A signal means “investigate”, not a trade instruction. Read [schedules.md](schedules.md) for the original proposal and [research.md](research.md) for research coverage.

These five routines share one verified data layer and multiple discovery paths: **R1 technical scans + R4 news + an independent fundamental screener owned by R2 → R2 watchlist → R3 monitoring → R5 reporting**. Fundamental screening and outcome evaluation are shared capabilities, not additional routines. The fast lane uses bounded R2 intake and the last accepted dossiers; deep research runs overnight. Every consumer pins the available upstream snapshot and cutoff, so missing discovery inputs cannot block critical monitoring. Routine numbers identify responsibilities, not execution order. They are distinct from ROADMAP backlog IDs R0–R8; use `routine_01` etc. in all artifacts.

[ROADMAP.md](../ROADMAP.md), [CLAUDE.md](../CLAUDE.md), [SPEC_E2.md](../experiments/SPEC_E2.md) and subsequent append-only ledger amendments govern repository behavior. In conflicts, retain the latest governing amendment and disclose the conflict. E2 results currently carry an audit failure; do not claim validated performance. Development is 2013–2020; 2021 through 2026-10-07 is spent momentum data; forward evidence starts 2026-10-08.

This is an isolated research overlay. Never edit frozen strategies, registrations, paper ledgers or the owner's human watchlist in `../InvestmentStrategy/ops/`. All proposed runtime outputs below live under `research/`; none exist merely because this plan names them.

## Ownership

| Work | Accountable owner | Reviewer / handoff |
| --- | --- | --- |
| Data adapters, session/identity checks, indicator calculations | Codex | Claude reviews coverage and interpretation |
| Signal definitions and research rationale | Claude | Codex checks implementability and ambiguity |
| Scanner, schemas, immutable persistence, replay checks | Codex | Claude checks report readability and exclusions |
| Explain unusual events and triage unknowns | Claude | Codex challenges unsupported numeric claims |
| Run recovery and data-quality incident closure | Codex | Claude receives limitations for downstream reporting |

Codex remains the independent challenger for Claude's hypotheses. Codex-authored code receives Claude review; an author cannot label their own work independently reviewed. Reviewer absence is recorded, never invented.

## Inputs and prerequisites

- Inspect `src/fetch.py`, `experiments/fetch_pit.py`, `experiments/pit_panels.py`, `data/raw/manifest.csv` and `experiments/data/pit/` as possible read-only inputs. Existing code is a reference, not automatically a certified data source: ROADMAP R0 lists known calendar, identity and corporate-action defects.
- Pin official session calendar version, effective-dated security identities, membership snapshot, raw file hashes and corporate-action treatment. Validate the internal bhavcopy date, not just its filename.
- MVP universe: an explicitly versioned Liquid-500 snapshot, admitted only after the Phase 0 readiness gate below. Until then, use synthetic or explicitly diagnostic runs with `production_eligible=false`. If membership validity cannot be established, quarantine affected coverage. Nifty Total Market / 750-name expansion from `schedules.md` is a later option requiring verified membership and coverage; never silently substitute one universe for another.
- Builder/monitor get any available verified results but cannot promote candidates using quarantined values. Unknown identity/action factors make affected indicators unavailable.
- Load previous committed R1 handoff, last successful per-source cursor, signal registry and unfinished tasks. First run declares `bootstrap=true` and has no prior comparison.

## How to execute

1. **Codex: establish the batch.** Assign market session, timezone `Asia/Kolkata`, observation cutoff, input versions and immutable batch ID. A calendar-confirmed non-session is skipped; an unavailable file is not proof of a holiday.
2. **Codex: validate coverage.** Record expected, received, valid and quarantined security counts. Check duplicates, nonpositive prices, inconsistent OHLC, missing volume, series restrictions, identity ambiguity and unexplained corporate actions. Exclude ETF/fund identities from the equity scan. Preserve a reason per exclusion.
3. **Codex: compute deterministic indicators.** Freeze formulas in a research configuration version before operating. Proposed MVP: adjusted close-to-close return; current volume / median of prior 20 valid sessions; current close exceeding prior 20/252-session high; SMA50/200 crossings; 21/63-session stock return minus aligned benchmark return; ATR14 and gap versus action-adjusted prior close. Windows exclude current observations where used as a comparison baseline. Document adjustment method, ATR initialization and required warm-up. Missing history yields null, never zero. “All-time high” is unavailable without full lifetime history.
4. **Claude: specify event meanings; Codex: implement.** Run the independent technical scans defined below. The >5% gain / >2× volume rule is one anomaly channel, not the discovery admission gate. Sector comparisons are unavailable without a valid sector benchmark. These research defaults do not alter M11/M10/M2/C0.
5. **Codex: compare to the previous successful session.** Distinguish new crossing, continuing condition, resolved condition and unobservable condition. A missing observation cannot resolve a signal. Preserve all findings; suppress repeat notifications, not source records.
6. **Claude: triage.** Produce a small queue with factual reason, evidence references and missing checks. Do not infer business quality from price movement. Send suspected corporate-action artifacts back to Codex rather than calling them opportunities.
7. **Codex: publish transactionally.** Validate artifacts against the contract below, seal a manifest, then advance the routine pointer. R4 and R2 consume manifest-pinned artifacts.

## Shared run contract — applies to all five routines

This section is the canonical contract; the other four plans link here. Start with local JSON/JSONL + Markdown. A future database must preserve these IDs and semantics. No cloud provider, source entitlement or notification channel is assumed configured.

Proposed layout:

```text
research/runs/<batch_id>/routine_01/<run_id>/
  report.md          # human-readable result
  handoff.json       # machine-readable envelope + carry-forward state
  manifest.json      # artifact hashes, committed flag, schema version
  signals.jsonl      # routine-specific records
research/state/routine_01/latest.json  # atomic pointer, not history
research/config/                     # versioned research rules and source registry
```

Use the same layout with `routine_02` … `routine_05`; payload names are defined in their plans. `batch_id` includes session and revision (e.g. `2026-10-12_eod_v01`); `run_id` includes routine and attempt (e.g. `routine_01_a01`). IDs here are examples, not real outputs. Corrections/retries create new runs and set `supersedes_run_id`; never overwrite a sealed run. Batch manifests pin exact upstream runs, not mutable `latest` files. A single orchestrator owns pointer updates; use a lock and compare-and-swap on the expected prior pointer to prevent concurrent writers.

Required `handoff.json` envelope (proposed schema `1.1`; consumers explicitly negotiate required fields, even within a compatible major version):

| Field | Contract |
| --- | --- |
| `schema_version`, `routine_id`, `batch_id`, `run_id` | Required strings; start implementation at `1.1`; reject unsupported major versions |
| `session_date`, `started_at`, `completed_at`, `cutoff_at`, `timezone` | ISO date / timezone-aware timestamps; timezone is Asia/Kolkata |
| `status`, `result` | Status: SUCCESS, PARTIAL, BLOCKED, FAILED, SKIPPED. Result: CHANGED, NO_CHANGE, NOT_EVALUATED |
| `execution_lane`, `production_eligible`, `readiness_ref`, `budget_ref`, `budget_usage`, `deferred_counts` | FAST, OVERNIGHT, EVENT or EVALUATION; readiness evidence; actual/reserved cost and resource use; backlog by reason |
| `owner`, `reviewer`, `review_status` | Claude/Codex identities; review status PASS, ISSUES, PENDING, UNAVAILABLE, NOT_REQUIRED; link review evidence |
| `previous_success_run_id`, `supersedes_run_id`, `bootstrap` | Nullable references plus explicit boolean |
| `upstream_runs`, `input_versions`, `config_version`, `code_revision` | Exact run references, source hashes, configuration and code identity (include dirty-file hashes where needed) |
| `coverage`, `freshness`, `limitations` | Expected/processed/quarantined counts; per-source timestamps, cutoff and missing reason |
| `artifacts` | Relative path, record count and SHA-256 per payload; resolve from run directory |
| `source_cursors`, `processed_event_ids` | Per-source last durably processed watermark and event IDs; do not advance failed sources |
| `open_tasks`, `resolved_task_ids`, `next_run` | Durable task queue, resolution references and explicit resume instructions |

Every task has `task_id`, `owner`, `security_id` if applicable, `description`, `priority`, `status`, `created_run_id`, `due_at` or event trigger, `blocking_reason`, and `evidence_refs`. Use OPEN, BLOCKED, DONE, CANCELLED; never silently drop a task. Carry unresolved tasks into the next run, append resolutions, and sort overdue/critical work first.

Every evidence record has `evidence_id`, source URL or local path, source document hash, source type, publication timestamp (or explicit unknown), retrieval timestamp, effective period/session, page/section locator, and verification status. Every reported numeric metric references evidence and calculation version, unit/currency and as-of date. Machine unknowns are `null` plus reason; display them as `—`. Store published financial period separately from when it became available.

Every finding has stable `finding_id`, effective-dated `security_id` (ISIN where valid), symbol-at-event, event type, observation time, previous/current values, units, evidence IDs, materiality rule, priority and lifecycle. Deduplicate on security + event type + original event/source identity + effective date; record versions when facts change. Content hashes catch repeated documents, but source IDs and economic-event identity catch differently worded duplicates.

Local commit protocol: write into a temporary run directory → validate JSON, paths, hashes, counts and upstream compatibility → atomically rename and mark manifest committed → update pointer. A committed PARTIAL run remains inspectable; `latest_success` advances only for SUCCESS. Resume cursors may advance only for verified, durably stored partitions, with unresolved gaps retained. Identical inputs/config/cutoff reuse the logical result; retries must not duplicate events, tasks, transitions or deliveries. Success with no findings is distinct from failure with no data. `NO_CHANGE` is allowed only over explicitly evaluated coverage; uncovered records remain NOT_EVALUATED.

## Produced report and handoff

`report.md` uses: **Run identity and health → Changes since previous run → Signal table → Coverage/exclusions → Open tasks → Next-run instructions**. Signal table columns: security, event, previous/current value, session, source/calculation link, priority, recipient. Keep top findings readable and link the full payload.

`signals.jsonl` contains the common finding fields plus universe version, return, relative volume, prior high/MA values, benchmark/sector returns where verified, eligibility, and quarantine reason. `handoff.json` tells R2 exactly which new/resolved signals to consume and tells next R1 which observations/cursors to resume. Empty results require explicit counts and coverage, not an empty report.

## Cadence, recovery and acceptance

The governing existing batch is 20:30 IST in ROADMAP, not the illustrative 16:15 start in `schedules.md`. Proposed integration starts current-session market calculations only after the evening batch’s required data artifacts are verified; a timed-out batch still produces the degraded health/news pass below. Do not invoke `live/evening_batch.py` as a read-only fetch: it mutates paper books and stages/commits repository files. Snapshot its outputs instead. Leave the 22:00 backlog and 10:35 morning report schedules unchanged. A separate earlier run requires an approved operational schedule and ready data.

Codex implements at most three attempts total per transient request (initial plus two retries, backoff 30 then 120 seconds, honoring longer Retry-After only within the lane deadline). Every attempt consumes the shared budget. The FAST lane alone has a 30-minute deadline; deep research uses the separate overnight SLA below. Non-session news runs can continue independently; price scans are SKIPPED. Calendar gaps remain visible.

Acceptance: date-mismatch/holiday fixture rejected; corporate-action ambiguity quarantined; indicator windows reproduced independently; repeat input creates no duplicate signal; interrupted publication leaves no usable half-run; a two-session replay carries unresolved tasks and detects crossings correctly. Claude checks that no numeric assertion lacks provenance. Completion means a committed report and handoff, validated payload, recorded review status and reproducible restart—not merely a generated paragraph.


## Independent technical scans

These are proposed research-screen configurations, not calibrated performance claims. Claude owns hypothesis definitions; Codex owns formulas, configuration hashes and replay. Each channel emits its own `scan_id`, `scan_version`, pass/fail/unavailable status and evidence; a company can pass more than one without duplicating its identity.

| Daily scan | Initial executable definition | Required context |
| --- | --- | --- |
| Price/volume anomaly | Return >5% AND volume / prior-20-session median >2 | Corporate-action-safe return and valid volume |
| Persistent relative strength | Positive 21- AND 63-session excess return against broad benchmark AND mapped sector benchmark | Separate effective-dated sector benchmark series; aligned sessions |
| Breakout/trend | Close exceeds prior 20/252-session high OR crosses above SMA50/200 | Previous side of MA, sufficient history; no anomaly prerequisite |
| Volatility/drawdown | ATR14/close exceeds 1.5× its prior-63-session median OR 20-session peak-to-close drawdown crosses −10% | Label as risk/dislocation, never infer fundamental quality |
| Sector breadth | Share of eligible sector constituents above SMA50 crosses 60% upward or 40% downward | At least 10 constituents and ≥90% valid price coverage; actual numerator/denominator |

Unavailable sector data yields UNAVAILABLE for sector-relative strength/breadth, with broad-market results separately labeled. A +4% stock move versus +6% in its sector is −2 percentage points relative performance, not sector leadership. Preserve each sector series, methodology, membership vintage and total-return/price-return convention. Never compare price returns to total returns without explicitly harmonizing the basis. After-results and weekly fundamental acceleration belongs to the independent R2 screener.

## Phase 0 — data readiness is a production gate

Codex owns `research/readiness/<version>/readiness.json` and an evidence report; Claude challenges economic interpretation. Record each source, universe vintage, affected scope, audit findings, corrected dataset version, reproducible checks and PASS/BLOCKED. These are proposed artifacts, not completed repairs.

Required gates: authoritative calendar including special sessions and download-failure distinction; effective-dated identities/rename/merger/delisting treatment; entitlement-derived corporate actions and proceeds; next-open-effective membership; reconciled benchmark accounting for evaluation; publication-dated fundamentals for fundamental lanes. Map each to ROADMAP R0/R7 and the E2 audit rather than silently reusing a failed component. Verify complete declared-universe identity/membership and report every excluded/quarantined record. Use independent source reconciliation plus rename, merger, split/bonus, special-session and interrupted-fetch fixtures. Record the full defect inventory and scope of every pass; checking a few examples does not certify all historical data.

Unresolved defects block production of the affected lane and any dependent claim. Synthetic/replay scaffolding can proceed. Price-only diagnostic results cannot certify fundamental discovery or historical performance. The first production vertical slice requires all its applicable gates to pass; later lanes add their own readiness gates. No new work in these plans changes existing frozen books or marks ROADMAP R0/R7 complete.

## Canonical scheduling and service objectives

Times are proposed operational objectives in Asia/Kolkata, not exchange-data guarantees or installed automations. Codex owns orchestration/recovery; Claude owns research queue and editorial completion.

| Lane | Trigger and deadline | Permitted work and output |
| --- | --- | --- |
| FAST evening | Verified EOD artifacts after existing 20:30 batch; begin by 21:00, seal by min(start +30 minutes, 21:30) | R1 scans + bounded R4 intake → bounded R2 intake → R3 risk checks → R5 internal evening brief; use previously accepted dossiers |
| Missing-EOD fallback | No valid EOD snapshot by 21:00 | Start degraded health/news/known-incident pass; seal by 21:30 with market NOT_EVALUATED; late EOD enters a new revision |
| OVERNIGHT research | 23:00, after existing 22:00–22:45 ROADMAP backlog; stop at 01:00 | Fundamental screens, queued R4 context, up to budgeted dossiers/challenges; checkpoint incomplete work |
| Morning assembly | 10:00 cutoff; internal R5 artifact by 10:15 | Incorporate sealed overnight updates and run R3 against changed theses; label prior-session prices; provide artifact to existing 10:35 report for its usual ~11:00 delivery |
| EVENT critical | Verified incident detected; local notice target within 10 minutes | R3/R5 minimal evidence-backed notice independent of dossier completion; delivery per R5 policy |
| EVALUATION | Weekly, next available 60-minute window after overnight work, within budgets | Mature outcome updates and operational/reader-feedback metrics; never block daily risk output |

The FAST deadline includes a reserved final five minutes for R3/R5 deterministic fallback output. Pending model work is checkpointed, not awaited. Independent R4 ingestion and fundamental screener outputs may be reused only with their explicit cutoff/freshness. Missing upstreams produce partial results; optional overnight research deferred by capacity is a queue outcome, not automatically a failed FAST scan. Production reporting readiness is separate from whether a dossier was completed.

At 10:15, R5 seals from whatever valid artifacts exist; no overnight run may delay the morning report. Existing schedules and senders remain unchanged until an integration is implemented. `execution_lane`, scheduled/actual times, deadline misses and deferred reasons enter every handoff.

## Hard resource budgets and backpressure

Initial proposed ceilings for the entire new research overlay, aggregated across all routines, retries, lanes and model providers per IST calendar day. They are spending limits, not provider price estimates; record actual unit prices before enabling paid calls. Existing paper-book jobs have a separate budget and are never starved by this overlay.

| Resource | Hard ceiling | Reservation / overflow behavior |
| --- | --- | --- |
| LLM requests | 40/day; at most 8 FAST, 24 OVERNIGHT, 8 EVENT | Morning assembly shares FAST allocation; EVALUATION interpretation shares OVERNIGHT allocation; no automatic borrowing |
| LLM tokens | 300,000 input + 40,000 output/day; each request ≤20,000 input and ≤4,000 output | Reserve 60,000 input +8,000 output for critical verification/reporting; retries included |
| External source requests | 1,000/day including retries; per source ≤300 or stricter provider limit | 200 requests reserved for critical verification; cached evidence first |
| News ingestion/AI triage | 2,000 metadata records +100 new full documents/day; at most 20 AI-interpreted events | Reserve 20 documents and 5 event interpretations for critical cases; persist overflow and age |
| Concurrency | One state writer, one active LLM request, at most two fetch requests | Queue additional work; critical work preempts at safe checkpoint |
| Dossier work | At most 5 changed dossiers/night, at most 10 unique dossiers in a weekly full-review pass | The weekly pass replaces that night's ordinary allocation; model/spend ceilings still bind |
| Variable spend | US$5/day and US$100/calendar month for models + metered sources | Reserve US$1/day and US$20/month within those totals for critical work |
| Cloud/storage fixed commitment | At most US$50/month for hosting/storage/source subscriptions combined | Verify projected commitment before deployment; if exceeded, local-only remains the fallback |
| Storage | 250 MiB new retained source material/day and 10 GiB active artifacts | Reserve 50 MiB/day and 1 GiB for incident/evidence manifests; stop optional ingestion before cap |

A run spanning midnight is charged by request dispatch date; reservations persist across rollover, and per-run call/time ceilings do not reset. Deterministic evaluation and morning fallback need no model call. Also persist a per-batch ceiling matching its lane allocation to prevent retries or midnight rollover from doubling its allowance.

Codex maintains a durable budget ledger: reserve worst-case request cost/tokens before dispatch, reconcile actual usage after response, and conservatively retain reservation after unknown outcomes. Stop paid requests if pricing is unknown. At the critical reserve's exhaustion, publish a deterministic budget-exhausted incident from existing verified facts; hard ceilings are never silently exceeded. Monthly counters survive daily resets and retries. Time and cost limits both apply; count limits do not promise all allowed work will fit.

Store license-permitted raw documents, immutable evidence hashes/locators and derived records; never delete provenance to meet the quota. At 80% storage utilization create a capacity task; at the cap stop optional payload ingestion and retain small incident manifests in reserved space. Propose a versioned retention/archive policy before enabling automatic deletion. Admission failures carry `deferred_reason` (BUDGET, DEADLINE, SOURCE_LIMIT, STORAGE, REVIEW_UNAVAILABLE), priority, age and next eligible run. Codex publishes actual/remaining budgets; Claude must select work inside them.

## Cloud persistence and recovery design

Proposed production deployment: one Cloud Scheduler-triggered Cloud Run job, Google Cloud Storage for immutable artifacts, Cloud SQL PostgreSQL for coordination/state, and Secret Manager for credentials. This is a design choice, not a provisioned service or assertion of current pricing. Phase 5 must verify availability, access controls and cost fit; if the stack cannot fit the fixed cap, remain local until a revised deployment is agreed. Local replay keeps JSON/JSONL files and filesystem locks.

Codex owns deployment, credentials plumbing, database migrations and incident recovery; Claude owns report/dossier reconciliation after recovery. Use a least-privilege service identity, never secrets in repository/artifacts or logs. Actual project, bucket, database, source credentials and delivery recipient identifiers are deployment configuration, not invented values.

In cloud mode, PostgreSQL is the single authority for batch leases, run pointers, queues, budgets, source watermarks and notification outbox. One orchestrator holds a 120-second renewable lease (renew every 30 seconds) with a monotonically increasing fencing token; all writes validate that token and expected prior version. A stale worker cannot publish after lease expiry. Unique constraints enforce logical run, event, transition and delivery keys. Workers submit proposals; only the leased orchestrator commits state.

Upload immutable artifacts to unique object keys and verify hashes first; then transactionally commit their manifest references, cursors, budget reconciliation and outbox rows in PostgreSQL. Object storage has no assumed atomic directory rename. Failed uploads never advance cursors. Uploaded-but-uncommitted objects are orphans, ignored by consumers and reconciled later. Consumers read committed database manifests only; they never discover state by bucket listing. PostgreSQL state updates and outbox creation share a transaction, while external delivery uses R5's receipt/UNKNOWN protocol.

After worker failure, a new leased orchestrator resumes checkpoints, validates object hashes and fences off old writes. After a database outage, stop publication/delivery and retain already uploaded evidence; never reconstruct authority from an unverified local pointer. Daily database backups plus point-in-time recovery and object versioning are required before unattended use. Target recovery point ≤15 minutes and recovery time ≤4 hours; these are unproven until a restore drill reproduces manifests, budget reservations, queues and delivery receipt state. Reconcile provider receipts before resending after a restore. Report any unrecoverable interval explicitly.
