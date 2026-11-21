# Routine 4 — News intelligence

Status: implementation plan, not an installed job. Plan version: 1.1, 2026-10-10. Amended following the supplied architecture review; deployment gates remain open.

## Purpose and ownership

Turn disclosures and relevant news into dated, source-backed events tied to companies and research assumptions. Separate what a source says, what can be verified, and the inferred financial mechanism. Repeated articles about one event must not create repeated “new” opportunities.

| Work | Accountable owner | Reviewer |
| --- | --- | --- |
| Source hierarchy, event taxonomy and financial interpretation | Claude | Codex challenges unsupported claims |
| Fetch adapters, identity matching, timestamps, hashes and dedupe | Codex | Claude checks missed/incorrect matches |
| Company/sector relevance and thesis implications | Claude | Codex checks evidence references and calculations |
| Durable cursors, source health and correction history | Codex | Claude summarizes coverage limitations |

Use the [shared run contract](01_market_movers_plan.md#shared-run-contract--applies-to-all-five-routines). Source access, entitlement and publication timing must be verified during implementation; the architectural suggestions in `schedules.md` do not prove an API is available or licensed.

## Inputs and source policy

Load previous R4 event registry, source cursors, correction links, unresolved verification tasks and the previous committed R2 company/sector/alias map. Add available R1 discovery identities and paper-held securities for relevance. R4 ingestion is independent of R1 availability; the FAST lane seals a bounded snapshot before intake/monitoring cutoffs, avoiding a dependency cycle. Bootstrap can operate with R1 + paper identities while dossiers are absent.

Priority order:

1. Original NSE/BSE company filings and notices for exchange-reported facts.
2. Company investor-relations reports, presentations and official earnings transcripts, clearly labeled management claims.
3. Relevant regulator/government documents and original industry data.
4. Credible financial reporting with a direct source and publication time; seek primary confirmation for material claims.

Use available `live/notes/` and `data/claude/` notes as leads only, retaining provenance and re-verifying material claims. ROADMAP R7 governs feasibility of point-in-time financial data. Do not assume news summaries replace the financial ingestion work.

Each enabled source needs owner (Codex for adapter, Claude for editorial quality), access method, retrieval cadence, timestamp convention, dedupe key, allowed retention, parser version, freshness expectation and fallback. If a source is inaccessible, retain its prior cursor and mark coverage incomplete. Do not silently substitute an aggregator for an exchange filing.

## What to classify

Use a versioned taxonomy: RESULTS, GUIDANCE, ORDER_OR_CONTRACT, CAPEX, DEBT_OR_FINANCING, OWNERSHIP_OR_PLEDGE, GOVERNANCE_OR_AUDITOR, REGULATORY_OR_LEGAL, CORPORATE_ACTION, MANAGEMENT_CHANGE, SECTOR_POLICY, and CORRECTION. Add a type only with schema compatibility documented.

For every event answer:

- What happened, to which legal entity/security, and when was it first publicly available?
- Is it incremental, a repeat, a correction or an update to an existing event?
- What is the potential financial mechanism: revenue, margin, cash flow, balance-sheet risk, dilution, execution or valuation assumptions?
- Which exact dossier assumption is confirmed/contradicted, or is there no documented thesis yet?
- What evidence is missing before drawing a stronger conclusion?

An order amount alone is insufficient: Claude checks execution period, incremental versus previously disclosed scope, disclosed margins, counterparty, cancellations and revenue/order-book context. Codex calculates any ratio only with compatible dated denominators. Undisclosed profitability remains unknown.

## Per-run procedure

1. **Codex: resume safely.** Query from each successful cursor with a configurable overlap (initially 48 hours) to catch late indexing; run weekly reconciliation over the preceding seven calendar days. Deduplicate the overlap. Older corrections are processed whenever discovered; these windows cannot guarantee complete archives and coverage must say so.
2. **Codex: preserve raw evidence.** Save permitted source copies or locators/hashes, publication/retrieval timestamps, document identity and parser version. Do not store credentials. Unknown publication times remain unknown and cannot support historical point-in-time eligibility.
3. **Codex: resolve identity.** Match exchange code/ISIN and effective symbol aliases; avoid fuzzy-name-only assignment. Put ambiguous group/subsidiary relationships in a verification queue. Sector events can map to multiple companies with an explicit exposure rationale, not an assertion of equal impact.
4. **Codex: normalize and deduplicate.** Group by original disclosure ID or economic-event identity. Attach secondary coverage to the existing event; distinguish genuine updates from headline paraphrases. A correction appends a new version with `supersedes_event_version`; retain the original.
5. **Claude: extract facts and interpretation separately.** Cite exact document sections. Separate management projections from realized results. Assign impact class and urgency with a written basis; avoid ungrounded sentiment/conviction scores.
6. **Codex: challenge high-impact cases.** Check amounts, units (rupees/lakh/crore), dates, company identity, duplicates and source support for P0/P1 or qualification-related claims. Review absence means PENDING/UNAVAILABLE. Severe unverified allegations are routed as verification work with uncertainty; they are not silently suppressed or asserted as facts.
7. **Claude: hand off.** Route new candidate evidence to R2, thesis changes to R3 and report-worthy items to R5. Other events stay in the registry. **Codex** seals artifacts and advances only successfully persisted source cursors.

## Produced artifacts

Within `research/runs/<batch_id>/routine_04/<run_id>/`:

- `report.md`: source coverage and cutoff; new material events; thesis implications; corrections; duplicates suppressed; unresolved verification and next-source checks.
- `events.jsonl`: new events and event-version updates, including common evidence/finding fields.
- `event_registry.jsonl`: complete dedupe index or a manifest-pinned prior registry plus replayable changes.
- `source_health.json`: per-source watermark, attempted window, result counts, failures and retry state.
- `handoff.json`, `manifest.json`: shared envelope and atomic publication.

Required event fields: `event_id`, `event_version`, `original_disclosure_id`, `security_ids`, `sector_ids`, `event_type`, `published_at`, `first_seen_at`, `effective_at`, `source_refs`, `raw_document_hash`, `facts`, `numeric_facts` with units/evidence, `interpretation`, `financial_mechanism`, `thesis_refs`, `impact_class`, `priority`, `verification_status`, `duplicate_of`, `supersedes_event_version`, `routed_to`, and `open_task_ids`.

Verification status is PRIMARY_VERIFIED, SECONDARY_ONLY, CONFLICTING or UNVERIFIED. Two articles citing one original claim are one evidence lineage, not independent corroboration. A sector item with no company mapping remains a sector finding and must not disappear.

Human event table: **Company/sector | Event and publication time | Verified fact | Why it may matter | Thesis link | Source | Next check/owner**. “No new material events” is permitted only with a stated source scope and completed window. A failed feed yields incomplete coverage even if other feeds are quiet.

## Cadence, recovery and acceptance

Daily EOD relevance enrichment uses available validated R1 inputs; source collection does not wait for prices. FAST processes material exposure/governance/integrity events first and defers full context research to OVERNIGHT under the shared budget. Additional event-triggered passes can run on non-trading days using a new batch/cutoff. Intraday or immediate alerts are future operational configuration, not created by this document. An event after a sealed batch cutoff enters the next revision/run rather than retroactively changing the prior report.

Next R4 consumes its durable registry/cursors and open tasks. R2/R3 consume only manifest-pinned event versions, including corrections. If a correction invalidates a prior report item, create an explicit correction finding for R5 and reopen affected research tasks. Do not rewrite old reports.

Acceptance: same filing across three sources creates one event; revised filing creates a linked version; company-name collision is quarantined; delayed publication is captured by overlap/reconciliation; provider outage leaves cursor unchanged; unrelated currency/period ratios are rejected; secondary-only claims stay labeled; a correction propagates to both thesis review and next digest. Claude verifies that the report distinguishes facts from interpretation.

Implementation order: source registry/access spike (Codex) → event rubric and sample annotations (Claude) → adapters/dedupe/versioning (Codex) → manual comparison against a small disclosure set (Claude) → replay/recovery validation (Codex). Readiness requires a measured coverage sample, not a claim to have read “all market news”.


## Economic significance and research backlog

Claude records the mechanism and affected assumption, not just positive/negative sentiment. Codex calculates ratios from dated compatible quantities and stores numerator, denominator, units, periods and evidence. Scale alone never establishes profitability. Add `significance_context`, `assumptions_affected`, `effect_known`, `context_missing`, `context_task_id` and `estimated_work` to each event.

| Event | Required economic context before a strong interpretation |
| --- | --- |
| Contract | Incremental value / latest annual revenue; value / existing backlog; execution duration, cancellation and margin disclosure |
| Capacity expansion | Capex, funding, current/planned utilization, commissioning schedule; incremental ROIC only if supported inputs exist |
| Promoter purchase | Transaction size, pre/post ownership and denominator, disclosed rationale; no inference of intent from purchase alone |
| Debt issuance | Gross and net leverage, maturity profile, refinancing versus new funding, intended use and rate where disclosed |
| Regulatory change | Effective date, applicable business segments and documented revenue/profit exposure |
| Results/surprise | Recurring versus one-off contributions, base effects, dilution; “surprise” requires a timestamped prior forecast |
| Management departure | Role criticality, successor, transition timing and disclosed circumstances; avoid speculation |

If missing context could change an apparent conclusion, classify impact UNCERTAIN and queue the specific fact check. A potential severe risk can still receive a verification notice with uncertainty; do not wait for a complete dossier to expose it.

Use the shared source/model/storage caps. Scan source metadata before paying to retrieve full text; cache by document hash, collapse repeated economic events and prioritize observed exposures, governance/corrections, near-term catalysts, then new discovery. The bounded full-document queue stores first_seen, source publication time, reason, priority, attempts, estimated cost and next eligible time. Keep P0 verification in the reserved capacity; P1 context delayed over one day and P2 over seven days triggers a backlog-quality incident and explicit re-triage. Do not advance a full-content cursor merely because metadata was enumerated: preserve separate metadata and content-processing watermarks.

## Source quality and cost audits

Codex produces `feed_quality.json` daily; Claude samples interpretation/identity quality weekly. Report per source: successful fetches / attempted fetches, detected records, publication-to-detection mean/median/p95 lag for known timestamps, unknown-timestamp count, oldest unprocessed event, paid requests, actual cost, cost per unique verified event and parser/identity errors. Never interpret a quiet feed as 100% coverage.

Weekly, compare a deterministic sample of up to 20 official filings across dates/sectors against the source listing, including a small random seeded sample outside watched names. Count missed disclosures / audited disclosures, incorrect company mappings / audited mappings and correction-detection failures; retain the sampled IDs, seed and adjudication. Where no independent listing is available, mark audit coverage UNKNOWN. Audits consume the same budgets; inability to audit is visible deferred work, not a passing audit.

Proposed operational triggers: any wrong company mapping on P0/P1 quarantines the affected adapter's matching path; ≥1 missed material filing in a sample opens a source incident; availability <95% over the last seven days or p95 lag >24 hours opens an adapter review. These are initial service targets, not measured performance. Codex fixes adapters and backfills impacted windows; Claude rechecks affected conclusions, and R5 publishes necessary corrections. Preserve the original publication/first-seen times after backfill.
