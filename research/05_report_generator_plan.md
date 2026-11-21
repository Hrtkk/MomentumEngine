# Routine 5 — Report generator

Status: implementation plan, not an installed job. Plan version: 1.1, 2026-10-10. Amended following the supplied architecture review; deployment gates remain open.

## Purpose and ownership

Produce one concise daily research brief from committed routine outputs. This is an editor and evidence gate, not a sixth research engine. Readers should understand what changed, why it needs attention, what remains uncertain and who owns the next step within five minutes.

| Work | Accountable owner | Reviewer |
| --- | --- | --- |
| Narrative, prioritization rationale and final readable brief | Claude | Codex challenges source support and omissions |
| Dependency validation, arithmetic, dedupe and rendering | Codex | Claude checks comprehension |
| Durable decision queue, delivery idempotency and run lineage | Codex | Claude checks actionable research tasks |
| Corrections and explicit uncertainty | Claude | Codex verifies affected versions and links |

Follow the [shared run contract](01_market_movers_plan.md#shared-run-contract--applies-to-all-five-routines). Report evidence and paper-book observations without buy/sell/hold recommendations or price targets. Missing real-portfolio data means exposure unknown, not zero.

## Inputs and dependency gate

Read the selected batch manifest with exact R1–R4 run IDs, artifacts and hashes, then prior R5 digest/notification state and unresolved decision tasks. R1 supplies coverage/signals; R4 supplies original events and corrections; R2 supplies membership/dossiers/transitions and independent fundamental-screen coverage; R3 supplies current thesis incidents and pending transition proposals.

Check common session, compatible schema/config versions, source cutoffs and commit status. News-only revisions may legitimately use earlier market data, but every affected section must show its market as-of date. Never imply that old prices are current. Check report counts against payloads instead of counting prose mentions.

R3 can identify deterioration after R2 qualified a candidate in the same batch. Show both: “research qualification under review; new contradiction pending”. Do not resolve the disagreement by discarding one record. Codex owns reconciliation of provenance; Claude owns clear wording.

No new browsing or independent company research during report generation. Missing evidence creates a task for R1–R4; the editorial layer cannot fill gaps from model memory. Validate the locally saved source/evidence references and route inaccessible or contradictory sources for re-verification.

## Per-run procedure

1. **Codex: validate completeness.** Build a stage-health table, missing-section list, expected/actual coverage and reviewer status. If some upstreams fail, make a degraded brief from safe committed artifacts. If none are usable, produce a BLOCKED health notice with NOT_EVALUATED result, not a “quiet market” message.
2. **Codex: consolidate events.** Use economic-event ID, security ID and incident ID across R1/R2/R3/R4. Keep one main item with all evidence links and separate technical/news contributions. Preserve meaningful contradictions. A repeated event may still have a new escalation or correction.
3. **Claude: select the attention queue.** P0 critical incidents first, then P1 predefined review conditions, then P2 discoveries. Within priority use exposure relevance, due time, first-observed time and stable ID. P3 and overflow remain accessible in detailed payloads. Do not let a positive discovery outrank an unresolved severe risk.
4. **Claude: draft.** Each main item states what changed, why it matters to a named assumption, the evidence/cutoff, uncertainty and a concrete research task with Claude/Codex/owner responsibility.
5. **Codex: challenge.** Verify every numeric claim, data date, priority condition, count, source link and quoted research state. Remove unsupported precision. Review author is recorded; an unavailable challenge does not become PASS. A factual P0 health/risk notice can still be published with review unavailability disclosed; unreviewed research conclusions cannot be presented as approved.
6. **Codex: reconcile task continuity.** Merge task IDs with prior open tasks; append resolutions only with evidence. The report is not evidence that a person acted. Owner decisions remain pending until an explicit decision record exists.
7. **Claude: finalize; Codex: commit.** Seal report, machine-readable digest and delivery candidate. External delivery is a separate authorized adapter and must not be inferred from merely generating a report.

## Human report template

```markdown
# Daily Research Brief — <session date> — <COMPLETE/PARTIAL/BLOCKED>
As of: <IST timestamp> | Market data: <session> | Review: <status>
Coverage: <valid/expected> securities; <evaluated/expected> monitored;
news sources: <complete/expected>. Full run: <manifest link>.

## Needs attention (maximum three main items; P0 may exceed)
1. <Security/sector — priority — concise change>
   Evidence: <dated primary record + calculation/dossier link>.
   Why it matters: <specific hypothesis or integrity concern>.
   Next: <research action>; owner <Claude/Codex/human>; due <time/trigger>.
   Uncertainty: <specific gap, or none identified within checked scope>.

## Research pipeline changes
<New discovery/research/qualified/rejected counts; link transitions.>

## Ongoing risks and coverage gaps
<Unresolved material incidents, deferred items and stale/missing inputs.>

## No action required within evaluated coverage
<Brief quiet-status line, or omit if not supported.>

## Next run
<Pending task IDs, expected catalyst/check, and prior digest link.>
```

Each item must answer “What changed?”, “Why should I care?” and “What exactly must happen next?”. Allowed next actions include research a candidate, re-evaluate a named valuation assumption, verify conflicting figures, review a documented concentration/downside condition, or no action required within checked coverage. “Monitor closely” is invalid without a measurable trigger and review date.

Normal target: 400–600 words and at most three main items. Quiet days can be a short coverage/status paragraph. P0 conditions override the word/item limit. Never hide incomplete data to fit the attention budget. Detailed dossiers and machine artifacts hold the rest.

## Produced artifacts and continuity

Within `research/runs/<batch_id>/routine_05/<run_id>/`:

- `report.md`: final human brief, using the template above.
- `digest.json`: item IDs, evidence refs, related upstream findings, priority, first/last seen, status, coverage and displayed numeric values with units/as-of/calculation refs.
- `decision_queue.jsonl`: all open/resolved tasks and owner-decision requests, including items not displayed in the top three.
- `notification_state.json`: dedupe keys and delivery states; generation alone sets NOT_SENT.
- `handoff.json`, `manifest.json`: shared contract and full lineage.

Each digest item includes `item_id`, `economic_event_id` or `incident_id`, `security_ids`, `upstream_finding_ids`, `headline`, `what_changed`, `why_it_matters`, `uncertainty`, `priority`, `evidence_refs`, `task_ids`, `review_status` and `display_state`. Display state is NEW, UPDATED, ONGOING, RESOLVED or CORRECTED. Stable item IDs support follow-up without duplicating work.

Next R5 reads prior digest + notification state + decision queue before assembling new items. “Already reported” is separate from “resolved”. Unanswered human decisions remain visible when material; no automatic approval. R1–R4 receive routed tasks by their owner/routine, with processed task IDs so a retry cannot reopen the same work twice.

Delivery key is channel + recipient reference + logical digest/incident version. States: NOT_SENT, PENDING, SENT, FAILED, UNKNOWN. Commit before enqueueing delivery; store external receipt IDs if available. If sending times out after possible delivery, check receipt/idempotency support before retrying; use UNKNOWN when confirmation is unavailable. A retry cannot assume no message was sent. No channel or recipient is configured by these plans.

## Schedule and operational integration

Use the canonical two-lane schedule, resource ceilings and persistence design in Routine 1. FAST combines available R1/R4 inputs with bounded R2 intake, then R3 and an internal R5 brief. Independent fundamental screening and deep R2/R4 work run OVERNIGHT; morning assembly consumes their sealed outputs without waiting for unfinished dossiers. Local replay tests the same logical protocol before cloud deployment.

Honor ROADMAP’s existing 20:30 EOD batch, 22:00 research backlog and 10:35 morning report. FAST seals by 21:30 (including degraded-data fallback); OVERNIGHT runs 23:00–01:00; morning cutoff is 10:00 and the internal digest is ready by 10:15 for the existing ~11:00 delivery. Until an integration exists, save the artifact locally; do not create a competing sender. Exact channel/account binding is a deployment gate under the policy below.

Critical event path: R4 verified event or R3 integrity incident → minimal R5 notice with available evidence/coverage → optional already-authorized delivery adapter. It need not wait for unrelated dossier work. The later daily digest references the same incident and avoids a second “new” alert. On a quiet non-session, skip the market digest unless material news or an operational issue warrants one.

## Implementation phases and acceptance

Do not build five independent workers in parallel before establishing their shared contracts. Codex owns implementation/infrastructure; Claude owns research rubrics and editorial validation, with independent review as assigned in each routine.

| Phase | Build | Completion gate |
| --- | --- | --- |
| 0 | Source audit, data readiness, schema 1.1 and R1/R2 candidate interface | Applicable calendar/identity/corporate-action/membership/source defects resolved and evidenced; replayable artifacts; unresolved scope blocked |
| 1 | R1 + minimal R5 vertical slice | Verified real price event produces source-linked brief; missing data produces degraded result; frozen books unchanged |
| 2 | R4 | Original disclosures matched, deduplicated and corrections propagated; source quality sample recorded |
| 3 | R2 + independent fundamental discovery | Slowly appreciating company can enter without R1/news trigger; lane configs, dated inputs, persistent dossiers and expiry fields validated |
| 4 | R3 | Tiered coverage, expiry, incident escalation and recovery pass replay checks |
| 5 | Cloud orchestration + alerts | Cost envelope verified, durable leases/restore tested, authorized recipient bound, delivery timeout/acknowledgement scenarios tested |
| 6 | Evaluation and controlled improvement | Mature cohorts measured with missingness/benchmark rules; no tuning from forward outcomes outside promotion process |

Capture evaluation cohort records from the first prospective discovery; Phase 6 builds analysis, not retroactive cohort selection. Within Phase 1, unimplemented R2–R4 have status SKIPPED and reason NOT_ENABLED rather than fabricated empty successes; such a slice cannot claim complete watchlist coverage. Later phases enable their declared readiness checks.

Acceptance across phases: every displayed fact resolves to an immutable artifact; one economic event yields one main item; P0 survives the top-three cap; a source failure cannot become NO_CHANGE; retries cannot duplicate tasks/deliveries; corrections link old briefs; unresolved work survives next run; all known data limitations are visible. Deployment readiness requires measured source coverage, actual cost/runtime, recorded reviewer availability and a successful recovery drill.

## Operational alert policy

This specifies intended behavior, not permission to send messages now. Codex owns routing, dedupe, acknowledgement storage and escalation timers; Claude owns evidence-backed wording and re-triage. Human recipient is the project owner only. Do not assume a real-money position from paper exposure.

Proposed routes: `OWNER_DIGEST` = the existing morning-report message channel; `OWNER_CRITICAL` = one owner-designated push-capable channel, with an optional owner-designated fallback. Bind exact provider/account/recipient IDs, verify consent and a test receipt, and store a configuration hash before Phase 5 passes. Until then, output local NOT_SENT artifacts and a CHANNEL_UNCONFIGURED incident. No addresses, third-party recipients or subscriptions are inferred.

| Priority / condition | Route and timing | Quiet-hours behavior |
| --- | --- | --- |
| P0: verified material exposure risk or pipeline integrity failure affecting current conclusions | Immediate OWNER_CRITICAL notice, target within 10 minutes of detection; include evidence and exposure scope | Quiet hours 22:00–08:00 IST; bypass only if delay past 08:00 would miss a documented deadline or allow compromised automated reporting/publication to continue |
| Suspected severe event lacking verification | Internal urgent verification task; if unresolved after 30 minutes, one uncertainty-labeled request to verify on OWNER_CRITICAL | Same bypass test; never assert allegation as fact |
| P1: concrete review condition due before next digest | Targeted owner notice if waiting would miss that recorded due time; otherwise next digest | Queue to 08:00 unless it satisfies the P0 bypass criteria |
| P2: new discovery, moderate evidence change | Next morning digest, within top-three attention budget | No separate notification |
| P3: repeats/routine/unchanged | Internal registry only | No notification |

The immediate path is immediate after detection, not a promise of continuous market coverage. Initial production feed polls: every 30 minutes 08:00–22:00, every two hours during quiet hours, bounded by source quotas and provider restrictions. Store scheduled/actual polling coverage; budgets or outages can degrade detection and must be reported. A source webhook may later improve latency only after verified support and configuration.

Suppress identical incident/version notifications for six hours except the bounded acknowledgement reminders below. Allow one consolidated noncritical targeted message per hour and at most three per day. Distinct P0 incidents bypass noncritical caps but are coalesced into one notice per five-minute window where safe; materially worsening verified facts can bypass incident suppression. These notification limits are separate from and subordinate to hard infrastructure/model spending caps. Critical deterministic notices must work without an LLM call.

Acknowledgement is an explicit owner response/button, stored as `acknowledged_at`, `acknowledged_by` and incident version. Delivery receipt/read status is not acknowledgement; acknowledgement is not resolution. For an eligible immediate P0, send one reminder after 30 minutes without acknowledgement, then one fallback/escalation after 60 minutes to the same owner only if that fallback was configured. Otherwise record DELIVERY_ESCALATION_UNAVAILABLE. Maximum three attempts/notices per unchanged P0 version per six hours, including initial, reminder and escalation. Quiet-held notices start acknowledgement timers on actual delivery, not original detection.

An acknowledged unresolved P0 stays in the next digest; Claude/Codex re-evaluate its evidence at the next event or within 24 hours, with a due task. Do not repeatedly page unchanged acknowledged facts. A new version reopens acknowledgement only for a material escalation/correction. Delivery failure creates an operational incident; UNKNOWN delivery uses receipt reconciliation before retry. Global provider outage is consolidated, not one alert per security. Actual channel binding and test delivery remain open implementation gates.

## Discovery evaluation capability

Codex owns deterministic cohort/return calculations; Claude reviews attribution, counterexamples and conclusions. This shared capability runs in the EVALUATION lane, not as another research agent or a source of daily selection changes. Store immutable proposed artifacts under `research/evaluation/<evaluation_run_id>/`: `cohorts.jsonl`, `outcomes.jsonl`, `metrics.json`, `report.md` and a manifest; R5 links only committed evaluated results.

Freeze a protocol before first eligible observation: candidate/episode ID, security identity, origin lane and config version, first-public/first-observed times, screening cutoff, decision state, evidence snapshot, benchmark version and cost assumptions. Retain screened failures, rejected/archived candidates and unobserved/missing outcomes. Cohorts start on actual prospective capture date; do not backdate this new system's forward test to the existing books' 2026-10-08 start.

Proposed outcome convention: signal observed by session close becomes eligible at next valid session open; after-hours disclosures use the next open after publication and observation. Record both times and conservative availability. Evaluate 20/60/120/252 trading-session horizons from that reference open to the horizon session’s close, counting the entry session as session 1. Use verified entitlement-aware total return including distributions/merger proceeds/delisting outcomes; unfillable entry is explicitly UNFILLABLE, never a fabricated fill. Record interim maximum drawdown from that reference path. Stale prices are not a delisting outcome.

Compare each stock with a broad-market total-return benchmark and the appropriate sector total-return benchmark using identical entry/exit timestamps where available. If compatible open/close benchmark values are unavailable, mark relative return unavailable or use a separately predeclared common-time comparison series—never silently use a close-to-open timing mismatch. B2 comparisons require their Phase 0 benchmark-accounting gate. Report gross research returns; any net hypothetical return must cite a predeclared cost model and remain separate from actual paper-book performance.

Report cohort count, matured count, unavailable/unfillable count, mean/median return, broad/sector excess, positive-excess rate, drawdown distribution and results by lane/config, entry vintage and sector. Predefine “positive discovery” for the initial diagnostic as positive broad-benchmark excess at 120 sessions; the false-discovery share (selected names that did not meet that outcome) is nonpositive excess / observed mature selected outcomes, with missing cases shown separately and no claim that this alone measures investment quality. Report false-positive count separately. A statistical false-positive rate uses false positives / all actual negative outcomes across the eligible universe, not merely selected names. Estimate that rate and recall only if the complete eligible universe has comparable outcomes; otherwise mark recall unavailable. Add development-only sensitivity across horizons instead of picking the best result after observation.

Multi-lane companies count once in overall unique-company cohorts and once per lane in explicitly overlapping lane analyses; repeated episode handling and cooldown are frozen before measuring. Use dependence-aware uncertainty intervals and multiplicity disclosure; small/immature samples are INSUFFICIENT_EVIDENCE. Outcome attribution separates earnings changes, multiple changes, dividends and sector effects only when input data support it; otherwise remain unattributed. Screening outcomes are not executable portfolio returns.

No daily threshold tuning against these forward results. Findings create hypotheses; controlled changes follow ROADMAP development → historical informational check → shadow version → new evidence → owner approval. Existing frozen rules and spent holdout designations remain intact. Added tests cover future publication leakage, missing returns not counted as losses, delisted companies retained, benchmark timing mismatch, overlapping lanes and immature cohorts.

## Reader feedback and attention-budget evaluation

Add optional feedback per item: USEFUL, DUPLICATE, TOO_LATE, NOT_RELEVANT, NEEDS_MORE_EVIDENCE; capture timestamp, reason and linked task/decision. No response means UNKNOWN, not useless or approved. Record optional self-reported reading time; do not infer it from message-delivery time or claim behavioral tracking exists.

Weekly `feedback_metrics.json` reports rated-item denominator, useful/rated, duplicate/rated, late/rated, total/unrated items, task completion/age, items omitted by attention budget, P0 exclusions (must be zero), and self-reported reading-time median/sample size. Compare feedback by routine/lane and priority without equating profitable stock outcomes with good alerts. Over-budget briefs or recurring missing-evidence feedback create editorial tasks; prospectively version display/routing changes and retain old metrics. Separate these product metrics from investment-discovery outcome metrics above.

## Architecture amendment tracker

“Specified” below means incorporated in these plans, not implemented, repaired, configured or validated. All production evidence gates remain open until recorded artifacts prove completion.

| ID | Review amendment | Plan location / accountable owner | Implementation evidence required |
| --- | --- | --- | --- |
| A01 | Source quality and historical identities | R1 Phase 0 — Codex; Claude review | Readiness report maps and closes applicable R0/R7 defects |
| A02 | Independent fundamental discovery | R2 discovery lanes — Claude hypotheses, Codex screener | No-price-spike fixture + verified filing coverage |
| A03 | Evening versus overnight SLAs | R1 canonical schedule — Codex | Deadline/backlog replay and morning fallback |
| A04 | Cloud storage, scheduling and recovery | R1 cloud design — Codex | Lease fencing, restore drill, source/credential configuration |
| A05 | Cost/resource budgets | R1 shared ceilings — Codex | Metered ledger, reservations, exhaustion/retry tests |
| A06 | Channels and critical-alert rules | R5 alert policy — Codex; owner supplies binding | Exact authorized recipient/channel, receipt/quiet/ack tests; binding remains OPEN |
| A07 | Discovery effectiveness | R5 evaluation — Codex; Claude interpretation | Prospective cohort protocol and mature outcome checks |
| A08 | Strategy-specific templates | R2 executable lane configs — Claude/Codex | Dated config, arithmetic review, sector exclusions |
| A09 | Monitoring tiers and expiry | R3 tiers — Codex; Claude evidence review | Expiry/NOT_DUE/exposure fixtures |
| A10 | Source coverage audits | R4 source quality — Codex/Claude | Independent sampled audit with missed/mismatch rates |
| A11 | News economic significance | R4 context matrix — Claude; Codex calculations | Context/unknown-effect examples with provenance |
| A12 | Daily feedback and alert quality | R5 feedback — Claude; Codex metrics | Explicit feedback records, denominators and missing-response treatment |

All twelve amendments are specified at the design level; none is claimed deployed. Begin with Phase 0 and the R1/R2 interfaces, then one end-to-end slice. Keep routine-specific next-run artifacts and the common contract together through implementation; do not recreate five disconnected prompt schedules.
