# Routine 3 — Watchlist monitor

Status: implementation plan, not an installed job. Plan version: 1.1, 2026-10-10. Amended following the supplied architecture review; deployment gates remain open.

## Purpose and ownership

Answer: **What materially changed since the last assessment, and which research assumption needs review?** Evaluate active research cases and every security in the available paper books, even if not in the research watchlist. A paper position without a dossier is labeled THESIS_NOT_DOCUMENTED and gets a research task; do not invent its rationale beyond the frozen strategy rule.

| Work | Accountable owner | Reviewer |
| --- | --- | --- |
| Baseline comparison, trigger evaluation, freshness and coverage | Codex | Claude checks interpretation |
| Interpret confirmations/contradictions against the recorded thesis | Claude | Codex challenges sources and unsupported inference |
| Prioritize research risk and propose state changes | Claude | Codex checks objective priority conditions |
| Delta history, task persistence and replay-safe publication | Codex | Claude checks readable report |

Use the [shared run contract](01_market_movers_plan.md#shared-run-contract--applies-to-all-five-routines). This worker neither changes book orders nor writes watchlist membership. R2 is the sole watchlist-state writer.

## Inputs and comparison baseline

- Current committed R2 intake snapshot/dossier references (or last accepted snapshot explicitly dated when current intake is unavailable), R1 calculations, sealed R4 events, prior successful R3 handoff and unresolved monitor tasks from later partial attempts.
- Read-only latest paper snapshots under `live/ledgers/M11/`, `M10/`, `M2/` and C0 `ledgers/`; verify session/as-of dates rather than choosing filenames lexically without validation.
- Registered strategy rules and risk levels are context from `strategy/`, `live/ledgers/registration.json` and the underlying immutable snapshot. Distinguish observed frozen-rule conditions from discretionary research interpretations.
- Preserve two baselines: the immutable original thesis forecast, and the last verified observation for each metric. A new dossier version cannot erase a previously failed forecast.
- Current-session prices require current-session coverage; financials require the latest verified available filing under the source freshness policy. Unknown freshness is a visible gap, not evidence of stability.

First run establishes observed baselines and sets `comparison_available=false`; it may report current verified risks, but cannot assert a change from an unobserved past. Newly qualified records within a batch also need this treatment.

## What to monitor

| Area | Comparison | Materiality rule |
| --- | --- | --- |
| Thesis fundamentals | Results/segments/margins/cash flow versus explicit assumptions | Dossier's versioned threshold and period |
| Leverage/governance | Financing, pledges, auditor/regulatory events | Verified new material event; Claude reviews economic effect |
| Catalysts | Promised milestone versus actual disclosure/date | Recorded delay, cancellation or completion trigger |
| Valuation context | Updated inputs versus previous research assumptions | Predeclared valuation-review threshold; no price target or trade call |
| Technical conditions | Level crossing, relative strength and volatility | R1's versioned event rule or dossier trigger |
| Paper-book exposure | Verified holdings, weights and concentration | Registered constraints or separately labeled research-observation threshold |
| Data/engine integrity | Missing source, stale quote, registration mismatch | Explicit incident; never relabel as company deterioration |

Do not create arbitrary thresholds on each run. Claude proposes a trigger in the dossier; Codex freezes its deterministic representation before evaluating it. Qualitative changes carry an evidence-backed rationale and reviewer status.

## Per-run procedure

1. **Codex: resolve coverage.** Union active R2 records and paper-held securities. Record counts for evaluated, unchanged, changed, missing and partially evaluated. Archived cases are processed only on a revisit trigger; still-held securities are never excluded because research state is archived.
2. **Codex: compare facts.** For each trigger, record old value/date, new value/date, source and formula. Corporate actions and identity changes require verified normalization before comparison. Missing current data leaves the trigger NOT_EVALUATED.
3. **Claude: assess thesis impact.** Classify CONFIRMS, CONTRADICTS, NEUTRAL or UNCERTAIN against a named thesis version and assumption. A price fall alone does not disprove a business hypothesis. Positive price action does not resolve a governance risk.
4. **Codex: assign objective severity.** P0 = verified material risk to an observed position or severe data/thesis integrity failure; P1 = a documented research condition requiring timely review; P2 = noteworthy research change; P3 = routine/duplicate information. Identify paper exposure explicitly; real holdings are unknown unless supplied. Potential severe but unverified news gets urgent VERIFICATION_REQUIRED with uncertainty, not a confirmed-event claim.
5. **Claude: propose follow-up.** Each material change gets a named owner, due time/event, evidence request and proposed R2 state transition if needed. No buy/sell/hold calls. `INVALIDATED` means a documented research thesis condition failed, not an instruction to exit.
6. **Codex: persist and deduplicate.** New finding, continuing unresolved incident, worsened incident and resolved incident are different lifecycle events. Send a new alert only for a new incident, meaningful escalation, resolution or predeclared overdue reminder. Keep ongoing risks visible in the record.
7. **Claude: summarize; Codex: commit.** Publish findings to R5 and proposals for the next R2 run. R2's membership can remain QUALIFIED while a new contradiction is pending; the digest must prominently show that qualification is under review.

## Produced artifacts

Within `research/runs/<batch_id>/routine_03/<run_id>/`:

- `report.md`: health and coverage; material changes ordered by priority; thesis impact; unresolved risks; quiet coverage; next-run actions.
- `changes.jsonl`: all evaluated material changes with common finding fields plus `thesis_version`, `assumption_id`, `baseline_ref`, `old_value`, `new_value`, `absolute_delta`, `relative_delta` where meaningful, `trigger_rule`, `thesis_impact`, `incident_id`, `incident_status` and `task_ids`.
- `monitor_state.jsonl`: per-security last verified observations, open incidents, next review trigger, last evaluation and per-trigger result.
- `transition_proposals.jsonl`: proposed R2 changes with expected prior record version, reason/evidence and review status; no direct mutation.
- `handoff.json`, `manifest.json`: shared contract, exact coverage and durable continuation state.

Incident status is OPEN, ESCALATED, RESOLVED or UNVERIFIED. A resolution requires evidence; disappearance from today's news is insufficient. Preserve original incident ID across updates and separate immutable finding IDs for each observation.

Human change table: **Security | What changed | Prior assumption | Evidence/date | Impact | Priority | Owner/next check**. Do not repeat a complete dossier. If all covered records are unchanged, return `NO_CHANGE` with the evaluated denominator. With gaps, return PARTIAL and list NOT_EVALUATED records; never say “no material changes across the watchlist” when part was unavailable.

## Cadence, recovery and next-run consumption

Run the FAST risk pass after the bounded intake cutoff, consuming available sealed R2/R4 snapshots; neither deep research nor a failed intake source may block it. Re-evaluate only affected theses at morning assembly after overnight updates. R4 event-triggered updates may run an incremental monitor pass against the most recent committed R2 snapshot with its as-of timestamp. Pin event cutoff, carry known technical staleness, and use a new batch revision. No recursive immediate R2↔R3 loop.

Next R3 reads monitor state and open incidents before fetching new data, evaluates overdue triggers first, and resumes failed partitions. Recovered data creates a dated follow-up, not a backdated replacement of the earlier gap. R2 consumes unprocessed proposals at its next run; R5 consumes current incidents today. A P0 artifact can be handed to R5 immediately; actual external delivery requires an already configured, authorized channel.

Acceptance: unchanged case yields one quiet record; missing quote yields NOT_EVALUATED; one event repeated across days yields one incident; worsening creates escalation; explicit resolving evidence closes it; a revised dossier retains the original forecast; held-but-unlisted securities stay covered; a crash/retry duplicates neither incident nor proposal. Claude checks that every stated contradiction cites the assumption it contradicts.

Implementation order: comparison/state layer (Codex) → thesis-impact rubric (Claude) → severity/dedupe and proposals (Codex) → three-session dry run including missing data (joint sequential review). Ready means another run can recover every pending risk without reading old chat messages.


## Monitoring tiers, exposure context and expiry

Codex schedules triggers and computes exposure; Claude owns thesis/evidence review. Every record has `monitoring_tier`, `tier_reason`, `next_due_at`, `last_evaluated_at` and `exposure_scope` (PAPER, ACTUAL_SUPPLIED, UNKNOWN). Actual exposure requires an owner-supplied, timestamped holdings record; no inference from a watchlist. Stale supplied holdings retain their date and cannot be asserted current. Aggregate concentration only within one explicitly identified portfolio and valuation snapshot; do not combine paper books as though they were one real account.

| Tier | Cadence | Coverage |
| --- | --- | --- |
| A — critical exposure/active setup | Every FAST session + material event; daily expiry check | All observed paper holdings, supplied actual holdings, open critical incidents and active objective setups |
| B — fundamental thesis | Results/material events + weekly heartbeat | Other RESEARCH/QUALIFIED cases; heartbeat checks missed events, due dates and expiry |
| C — lower-priority discovery | Weekly screen/queue check + monthly research review | DISCOVERY cases; any material incident escalates to A/B |
| D — inactive | Explicit revisit trigger + monthly registry reconciliation | REJECTED/ARCHIVED unless still held, in which case A overrides |

A cheap daily expiry/incident check covers every active record independent of its deep-review tier. For a record not due today, report NOT_DUE with last evaluation date, not NO_CHANGE. `NO_CHANGE` applies only to evaluated triggers. Coverage denominators distinguish active total, due today, evaluated, not due and unavailable.

Initial research-expiry defaults: technical snapshot valid for its market session only; valuation review expires after 30 calendar days or a new material filing; latest-quarter financial review after 120 calendar days or the issuer's recorded next-results due date plus seven days, whichever is earlier; competitive-position review after 180 calendar days; annual governance/cash-flow review after 400 calendar days or a new annual filing. A newly published material filing requires immediate reassessment of affected assumptions. These are operational review defaults, not regulatory deadlines; issuer/sector overrides must be versioned before use.

Persist `evidence_expires_at`, `expiry_rule_version`, `qualification_valid_until` (earliest critical expiry), `needs_reassessment` and affected assumption IDs. At expiry the effective displayed qualification is EXPIRED/UNDER_REVIEW immediately, even if R2 has not yet applied the queued QUALIFIED → RESEARCH transition. Provider outage adds a data incident and review block; it does not prove thesis failure. Expiry cannot be postponed merely by opening an old document again.

Append `assumption_evidence_history.jsonl`: thesis/assumption ID, previous/new evidence state, SUPPORTS/WEAKENS/CONTRADICTS/INCONCLUSIVE, source IDs, alternative explanation, timestamp and reviewer. No AI confidence percentage or subjective pre-trade signal is introduced. A fresh stronger source may resolve uncertainty, but never rewrites the original forecast.

Portfolio-aware alerts state which portfolio is affected, observed position/weight date, known constraint and measured breach. Unknown real exposure yields a request to verify exposure, not “your portfolio is at risk”. Apply the [canonical alert policy](05_report_generator_plan.md#operational-alert-policy) for immediacy, quiet hours, acknowledgement and escalation.

Added acceptance: held archived name remains tier A; tier C not-due records are not claimed unchanged; expired qualification displays under review before R2 catches up; stale real holdings are labeled; multiple paper books remain distinct; strengthening/weakening evidence is recoverable across thesis versions without an invented confidence score.
