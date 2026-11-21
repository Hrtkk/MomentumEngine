# Routine 2 — Watchlist builder

Status: implementation plan, not an installed job. Plan version: 1.1, 2026-10-10. Amended following the supplied architecture review; deployment gates remain open.

## Purpose and ownership

Maintain an evidence-backed research watchlist, progressing companies from discovery through investigation while retaining rejected cases. This is a separate research list; do not change the human watchlist in `../InvestmentStrategy/ops/` or paper-book selection rules.

| Work | Accountable owner | Reviewer |
| --- | --- | --- |
| Research triage, company dossiers and thesis statements | Claude | Codex challenges evidence and missing alternatives |
| Screening calculations, state machine and storage | Codex | Claude checks economic meaning |
| Proposed promotion/rejection with explicit reasons | Claude | Codex validates gate evidence |
| Apply accepted transitions and publish snapshot | Codex | Claude checks final deltas |
| Resolve research gaps | Claude | Codex owns technical/source blockers |

Follow the [shared run contract](01_market_movers_plan.md#shared-run-contract--applies-to-all-five-routines), repository boundaries and governing rules in Routine 1. Output opinions concern research readiness; `QUALIFIED` is not a buy recommendation or authorization to alter a paper book.

## Inputs and daily startup

Read the previous successful R2 snapshot and unresolved tasks first, then the latest committed R3 change proposals, current batch R1 signals, sealed R4 events and independently scheduled fundamental-screen results. Neither an R1 anomaly nor a news event is required for fundamental intake. Upstream IDs must be pinned. R3 proposals from the current batch are applied on the next R2 run, preventing a circular dependency. R5 can still report the immediate thesis risk today.

Use `research/research.md` for fundamental coverage, `strategy/` for frozen paper-rule context, and `live/ledgers/` as read-only context for which names are already in paper books. Access to the owner's actual holdings is not assumed; unknown real exposure must be labeled unknown.

Point-in-time fundamentals remain gated by ROADMAP R7 source feasibility. Missing filing/publication dates or unverified financial data block affected fundamental gates, not the whole discovery list. Do not backfill historical decisions with figures learned later. Financial-sector metrics must use sector-specific templates rather than industrial debt thresholds.

First run seeds only documented candidates from enabled R1/R4/fundamental lanes or an explicit owner-provided research seed. Record seed provenance and `bootstrap=true`. Do not convert all paper holdings into qualified fundamental theses.

## What to build

1. **Codex: persistent company registry.** One stable security ID per effective identity, retaining aliases and symbol dates. Separate membership state, thesis status, signal history and paper exposure.
2. **Claude: research templates.** For each company cover business/segments, growth quality, cash conversion, leverage, capital allocation, governance, competitive position, valuation assumptions, technical context, catalysts and disconfirmation. Separate verified facts, interpretations and unanswered questions. Scenario calculations are research assumptions, not published price targets.
3. **Codex: deterministic gates.** Implement versioned eligibility, freshness, required dossier fields and evidence completeness. Missing values do not pass a gate. Serious unresolved governance/accounting evidence cannot be offset by a high momentum score.
4. **Claude: strategy-specific assessment.** Tag hypotheses such as quality, earnings acceleration, turnaround, cyclical recovery and momentum without collapsing them into one opaque conviction score. Different families need different evidence. A momentum-only candidate must say so.
5. **Codex: deterministic work ordering.** Apply the information-value ordering below within the shared resource budgets. The FAST pass performs intake, expiry and already-reviewed transitions only; it does not start deep dossiers. OVERNIGHT permits at most five changed dossiers; the weekly full-review pass permits at most ten unique updates instead of that night’s ordinary allocation. Preserve overflow with due dates and expose queue age.

## State transitions and review gates

| Transition | Required evidence / action |
| --- | --- |
| New → DISCOVERY | Verified signal, filing or seed with stable identity and intake reason |
| DISCOVERY → RESEARCH | Investability checks recorded; at least two distinct supporting evidence types, or a documented material-event exception reviewed by Codex; assigned research question |
| RESEARCH → QUALIFIED | Complete dated dossier, sector-appropriate financial checks, valuation context, risks, falsifiable thesis, objective review triggers, data freshness and Codex PASS |
| Any active state → REJECTED | Documented failing gate or invalidated thesis with source and reviewer; retain original thesis |
| Any active state → ARCHIVED | No active research case, with reason and revisit trigger; no deletion |
| QUALIFIED → RESEARCH | Material contradiction, expired critical evidence or unresolved monitor proposal; preserve qualification history |
| REJECTED / ARCHIVED → DISCOVERY | New evidence addressing the prior reason; link previous episode and start a new research episode |

Data absence alone is not evidence that the company is bad. Keep the record with `review_blocked=true`, stale fields and an open task; demote stale QUALIFIED cases to RESEARCH with reason DATA_EXPIRED when a predeclared freshness policy requires it. No mass rejection because a provider failed.

Each transition stores `transition_id`, security and episode ID, from/to state, prior version, proposed_by, reviewed_by, review status, reason code, evidence IDs, timestamp and applied run ID. Codex is the single state writer. Claude submits proposals; R3 never directly rewrites membership. Apply once using transition ID and expected prior version. Reviewer unavailability blocks qualification; lower-risk intake can be committed with review pending. Disagreement creates an open challenge task and retains the last accepted state.

## Per-run procedure

1. **Codex** validates all manifests, unions unresolved tasks with new intake and deduplicates by security/event/episode.
2. **Codex** applies accepted prior R3 proposals using expected-version checks. Conflicts return to Claude with both evidence versions; never silently prefer the newest file.
3. **Claude** triages the queue; **Codex** computes verified screening metrics. In FAST, defer deep work to OVERNIGHT; continue from the last accepted dossiers. Proposed screen defaults in `research.md` must be versioned and sector-adjusted before being enabled.
4. **Claude** updates only changed sections of a dossier, preserving the previous version and thesis predictions. Each material claim references source IDs; counterevidence gets equal visibility.
5. **Codex** challenges state-changing claims, dates, arithmetic, source quality and thesis falsifiability. A disagreement is preserved beside the proposal.
6. **Codex** commits accepted transitions and the full snapshot; **Claude** writes the concise changes report. Hand off active records and review triggers to R3 and transitions to R5.

Daily FAST intake runs against pinned available R1/R4/fundamental snapshots; unavailable inputs are labeled and do not block risk monitoring. Deep dossier steps run OVERNIGHT under the canonical R1 scheduling contract. A full reconciliation on the last confirmed trading session of the week checks every active record's freshness, overdue tasks, duplicate identities and archived revisit triggers. Deep research follows the capacity queue; “full review” does not falsely imply every dossier was re-researched. News-only runs may process material filings using labeled last-known technical data.

## Produced artifacts

Within `research/runs/<batch_id>/routine_02/<run_id>/`:

- `report.md`: run health; state-count changes; additions/promotions/demotions/rejections; strongest counterevidence; blocked/deferred research; next-run queue.
- `watchlist.jsonl`: complete current snapshot, including retained rejected/archived records or immutable archive references.
- `transitions.jsonl`: proposals and accepted transitions, linked to prior state versions.
- `dossiers/<security_id>/<version>.md`: changed dossiers only; unchanged records link to immutable prior versions.
- `handoff.json` and `manifest.json`: shared envelope and committed artifact index.

Required watchlist record: `security_id`, `symbol`, `episode_id`, `record_version`, `research_state`, `strategy_tags`, `intake_reason`, `first_seen_at`, `last_reviewed_at`, `dossier_ref`, `thesis_version`, `thesis_statement`, `baseline_metrics` with dates/units/evidence, `risk_flags`, `next_catalyst`, `invalidation_conditions`, `next_review_at`, `review_triggers`, `review_blocked`, `open_task_ids`, and `paper_exposure_refs`.

Triggers are executable where possible: metric, operator, threshold, units, applicable period, source and missing-data behavior. Subjective triggers require named Claude review, not an invented numerical threshold. Dossiers record expected observation dates and alternate explanations so later runs can test what was actually predicted.

## Carry-forward and acceptance

Next R2 reads the last accepted snapshot plus every unresolved proposal/task since it, including partial runs; it does not reconstruct truth from the prose digest. R3 consumes the exact current snapshot and its thesis versions. R5 gets deltas plus explicit deferred counts. R4 consumes company/sector/alias relevance mappings from the previous committed R2 snapshot so its ingestion does not depend on this run finishing.

Acceptance checks: duplicate signals produce one episode; missing financial evidence prevents qualification; a rejection survives subsequent runs; reopened cases link prior failure; concurrent/stale transition versions are rejected; Codex outage records review unavailable without auto-approval; R3's contradiction appears immediately in R5 and is applied once by next R2. A two-run fixture must prove that unfinished dossier work resumes without losing its original hypothesis.

Implementation order: registry/schema and state transitions (Codex) → dossier rubric (Claude) → gates and challenge interface (Codex) → seeded dry run (Claude) → restart/replay validation (Codex). Routine is ready when every active record has an owner, next trigger and evidence trail, and downstream consumers can reproduce its state.


## Independent fundamental discovery and strategy lanes

Claude owns screening hypotheses/templates; Codex implements deterministic shared screener code, source adapters and versioned configs under proposed `research/config/screens/`. Trigger a changed-company screen after verified results ingestion and a full eligible-universe screen during the weekly overnight review, even with no price anomaly or news alert. Run only after the applicable Phase 0/R7 gate passes. Until then record FUNDAMENTALS_BLOCKED rather than simulate discovery with model-supplied figures.

Every config defines `lane_id`, `version`, universe, allowed sectors, required fields/periods, publication-date cutoff, formulas, thresholds, exclusions, null handling, ranking, benchmark, cadence and validation reference. Freeze a config before emitting prospective candidates. The following are initial research-only hypotheses for non-financials; sector-specific financial-company templates remain DISABLED until separately specified and reviewed. Missing inputs produce UNAVAILABLE, not FAIL/PASS.

| Lane | Proposed executable screen | Evidence required / limitation |
| --- | --- | --- |
| Quality compounder | 3Y revenue CAGR ≥12%; ROCE ≥15% in each of latest 3 FYs; CFO positive in ≥3 of latest 5 FYs; debt/equity ≤0.5 | Consistent annual statements; no price-spike requirement |
| Earnings acceleration | Revenue YoY growth ≥15% and recurring diluted EPS YoY growth ≥20% in each of last 2 quarters; latest EPS growth exceeds prior quarter’s YoY growth | Comparable positive EPS bases; separate one-offs; normalization unavailable means blocked |
| Turnaround | Latest 2 quarters operating profit positive after a loss in either preceding 2 quarters; trailing-year net debt does not rise | Cash-flow and restructuring review before qualification; negative-base CAGR not used |
| Value | Positive trailing EPS; P/E below both own 5Y point-in-time median and current comparable-sector median; positive latest FY FCF | Valid historical prices/filings and ≥5 comparable peers; low P/E alone is not a thesis |
| Cyclical recovery | Latest 2 quarterly operating margins improve sequentially; latest revenue YoY >0%; net debt/EBITDA declines YoY with positive denominators | Full-cycle context and normalized earnings required before qualification |
| Momentum | Any enabled R1 trend/relative-strength lane passes | Retain scan evidence; no implied fundamental qualification |

Record exact ROCE, debt, recurring EPS and cash-flow definitions in config before activation; denominator ≤0 or unavailable comparables yields UNAVAILABLE. These proposed thresholds are not evidence of attractive returns. Claude challenges economic validity; Codex verifies arithmetic on dated fixtures. Screen activation is research-only and does not register a new live strategy.

`fundamental_candidates.jsonl` and `screen_coverage.json` are additional R2 artifacts. Each candidate has `candidate_id`, security ID, `lane_id/version`, `screen_run_id`, `asof`, `available_at`, passed/failed/unavailable predicates, metric values with units/evidence, rank, eligibility and `next_research_question`. Coverage includes every attempted eligible security, including failures and missing cases. Retain all screened names and thresholds for later false-negative/evaluation analysis.

A company record contains `lane_assessments[]`: separate evidence, hypothesis, state-of-assessment and counterevidence for each lane. One company dossier can share verified facts; one lane failing must not erase another lane's rationale. R1, R4 and fundamental intake share the stable candidate interface: origin, source run, security ID, event/scan version, evidence IDs, cutoff and hypothesis. The R2 watchlist is their union, deduplicated by identity and research episode—not their intersection.

## Prioritize expected information value

After critical exposure/integrity tasks and mandatory expiry work, sort research tasks by: (1) fresh evidence capable of changing an explicit state/assumption, (2) a named decision-blocking gap that available evidence can resolve, (3) independent evidence convergence, (4) overdue age, (5) smaller bounded effort, (6) stable task ID. Store the observed basis for each dimension; do not ask an LLM to invent a probability or monetary value of information.

Use effort classes SMALL (one source/recalculation), MEDIUM (up to three sources plus comparison), LARGE (full dossier). Admit work only if its estimated calls/tokens/time fit remaining budget; checkpoint and revise estimates from actual usage. Unchanged complete dossiers get no new model call. More than seven calendar days overdue creates a backlog incident and forces explicit re-triage rather than silent starvation. A risk task cannot be displaced by a cheaper interesting candidate.

Added acceptance: a slowly appreciating company passing quality/earnings criteria enters discovery with no R1/R4 signal; multi-lane evidence survives one lane’s failure; missing publication dates prevent a pass; an unchanged dossier consumes no model call; budget exhaustion defers work without delaying R3/R5. Record this lane coverage in each R2 report and carry its cursor/config/task IDs into the next run.
