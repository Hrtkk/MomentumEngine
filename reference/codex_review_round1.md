**Verdict: sound research architecture, but not yet an executable or statistically defensible v0.1.** Start with signal measurement; defer most portfolio machinery. Reviewed all five requested files locally. No files changed.

**1. Methodological flaws**

- **Universe mismatch (§§1, 3, 9.3):** “Top 100 across all NSE, then intersect Nifty 500” differs from the reports’ “top 100 within Nifty 500.” It can produce far fewer candidates. Raw top-10 results do not directly test H1 about top-100 results.
- **Survivorship (§14):** Calling current-membership backfill bias “mild” is unsupported. Prospective results also become biased if later membership changes or missing/delisted securities silently remove old observations.
- **Corporate actions (§2):** Comparing unadjusted bhavcopy levels against adjusted historical closes with a 1% tolerance is invalid. Adjusted OHLC, volume, dividends, symbol changes and portfolio share quantities need consistent treatment. Sixty accumulated bhavcopies cannot replace missing 200/252-session history.
- **Undefined model (§5):** EQS has no weights or interpolation; MQS blends, breakout definition, percentile ties, missing data and zero-range days are unspecified. Listed for 120 sessions does not provide a 200-DMA. “Reproducible” currently overstates the specification.
- **Hidden discretion (§§5.4, 7, 8):** “Experimental” annotations change sizing; adverse annotations trigger exits. They therefore affect performance despite being described as annotation-only.
- **Overfitting (§§1, 5, 8):** Eight factors, six penalties, five timing inputs, numerous exits and regime thresholds are excessive for this sample. Close quality was selected after inspecting one day. Choosing the best of five horizons is another model-selection step.
- **False sample size (§9.1):** Three thousand candidate-days are not 3,000 independent observations. Stocks repeat, sectors co-move, and forward windows overlap. Candidate counts also contradict the estimated 250–400-name rolling universe.
- **Weak governance (§9.5):** Under independent symmetric block signs, a specified positive sign wins ≥2 of 3 blocks with probability 50%. The IC magnitude condition adds no calibrated uncertainty test. Twenty penalty observations are likewise insufficient. Ten-session blocks have overlapping forward outcomes; at session 30, recent 10/20-session labels are immature.
- **Holdout leakage (§9.5):** “Sessions 1–N” cannot include the latest ten sessions used as holdout. Repeatedly consulting that holdout turns it into development data.
- **IC interpretation (§9):** Subtracting the same Nifty return from every stock does not change cross-sectional Spearman IC. Neither does subtracting the candidate mean. Those are not separate confirmations of predictive power.
- **Baselines (§9.3):** One Random-10 path is noisy. “Same exits” potentially imports MQS into supposedly naive baselines. Rebalance schedule, exposure, sizing and replacement treatment are undefined. Nifty buy-and-hold versus a mostly-cash strategy confounds selection with exposure. H4 needs an explicit MQS-only comparator.
- **Execution (§§6–8):** Observing tomorrow’s open to decide eligibility and quantity, then filling at that same open, requires an explicit order model. Stop-at-price fills are not necessarily pessimistic during circuits or illiquidity. EOD trailing-stop updates cannot apply retrospectively to that day’s low.
- **Regime (§4):** Risk-on and risk-off can both apply when the index is above its 50-DMA but below its 200-DMA. Existing-position reductions after an exposure-cap change are undefined. ET breadth does not establish the engine’s starting regime.
- **Outcome interpretation (§§9.4–9.6):** Fixed-horizon selection outcomes and realised trade outcomes are different. TP/FP labels blur them. Sixty sessions can justify stopping an experiment, but cannot establish that gainers lack predictive value; the kill rule also omits persistence and depends on one random path.

**2. Departures from the original proposal**

- The owner explicitly called gainers a **discovery universe**, not the strategy. §1 incorrectly attributes an assumption of continuation to the proposal.
- A **10-slot watchlist** becomes a **10-position portfolio**. Those are different requirements; preserve separate research ranks and positions.
- The original rolling window retained raw discoveries; §3 uses eligible discoveries. Filter failures therefore disappear from candidate learning.
- Confidence allocations of 10–12%, 7–10%, 3–5% become risk multipliers that need not produce those allocations. This is a redesign, not a direct mapping.
- Nifty 50 disappears; false-negative review narrows to Watch-level rejections.
- Moving catalysts/operator judgements to annotations and removing duplicate market-relative scoring are sensible departures. The draft should state them consistently.

**3. Practicality and cuts**

Buildable, but **not as a dependable three-agent-pass daily routine within the existing desk constraint**. Data reconciliation and execution rules are the hard parts; report styling is secondary.

For v0.1 retain: deterministic scan, frozen MQS, immutable snapshots, forward-return cohorts, simple comparators, one short daily report.

Cut initially: EQS execution gate, confidence tiers, partial reductions, challenger replacement, trailing stops, annotation-driven exits and four stateful shadow portfolios. Keep their hypotheses for later. Research only proposed entries and material holding events—**maximum five names/day**, rather than top-25 narratives.

One evening batch can ingest data, mature earlier outcomes and produce the report. A separate morning review adds little without new inputs. Reading should take **≤5 minutes normally, ≤10 on exceptions**.

§12’s assertion of prior build authorization cannot be established from the supplied proposal summary. This review authorizes no implementation.

**4. Labour and storage**

Agree with **local canonical storage and one-way Drive publishing**.

- **Script:** owns universe, scores, paper decisions, outcomes and report generation.
- **Claude:** sourced event annotations, brief commentary, Drive publishing.
- **Codex:** deterministic implementation when authorized, independent calculation checks, weekly audit; daily attention only for exceptions.
- Neither agent’s attendance or narrative should block the mechanical run.

Keep complete downloaded source files, retrieval timestamps, hashes, membership snapshots and strategy/code versions. Git does not automatically preserve uncommitted data, and a local repository alone is not a backup. Publish a dated report/CSV plus run ID; back up canonical data off-device daily. Test Drive HTML preview before relying on it.

**5. Specific changes**

These numbers are proposed operating conventions, not empirically validated optimums.

| Priority | Sections | Exact change |
|---|---|---|
| **MUST** | 1, 3 | Define primary discovery as **top 100 positive-return EQ securities within that day’s Nifty 500 membership**, before price/liquidity/history filters. Tie-break by symbol. Archive all NSE EQ rows separately. |
| **MUST** | 2, 3, 14 | Require **252 valid sessions** for the full factor model; otherwise mark history-ineligible. Snapshot membership daily; retain subsequent suspensions, removals and unresolved outcomes. Label current-membership backfill **exploratory, survivorship-biased; magnitude unknown**. |
| **MUST** | 2, 10 | Compare like-for-like unadjusted closes for provider reconciliation. Store adjustment factors separately. Missing/stale essential input → **no new orders**, explicit exception; never silently reuse yesterday’s values. |
| **MUST** | 5 | Specify every formula before implementation. Suggested defaults: RS = **0.5×21-session excess return + 0.5×63-session excess return**; volume factor = mean percentile of volume ratio and delivery-% ratio, each against **previous 20 sessions excluding today**; breakout reference = **maximum high over preceding 55 sessions**. |
| **MUST** | 5 | Percentile = **100×(average rank−1)/(n−1)**; n=1 → 50; H=L → close-quality raw value 0.5; essential missing factor → ineligible, no weight redistribution. Clip final MQS to **[0,100]**. Disable EQS-dependent orders until fully specified. |
| **MUST** | 5.4, 7, 8 | Annotations have **zero effect on eligibility, sizing or exits** in v0.1. Any later event rule needs a timestamped, structured input and explicit rule version. |
| **MUST** | 4 | For v0.1, **log regime only**. If retaining exposure gates: evaluate risk-off first, then risk-on, otherwise neutral; specify deterministic next-open reductions when caps fall. |
| **MUST** | 6–8 | Freeze orders and integer quantities before the next session. Simplest initial convention: **next-open market simulation without the 3% gap guard**. If the guard stays, specify an opening-limit simulation and label fill uncertainty. |
| **MUST** | 8 | If stops remain: compute a fixed stop using signal-close inputs; if the intended stop exceeds **8% distance, reject**, rather than silently move invalidation. EOD stop updates activate **next session only**; stops never loosen. Locked/suspended exits remain unfilled and logged. |
| **MUST** | 9.2–9.3 | Primary signal endpoint: **10-session return, O(t+1) to C(t+10)**; other horizons exploratory. Use daily equal-weight cohorts with fixed 10-session exits for full discovery, MQS top-10, persistence top-10 and raw gainers top-10. They are overlapping research cohorts, not independently funded portfolios. |
| **MUST** | 9.2 | Match benchmark timestamps and dividend treatment. With index closes only, use a separate **C(t+1)→C(t+10)** stock/index excess-return panel; do not subtract close-to-close index returns from open-to-close stock returns and call it matched alpha. |
| **MUST** | 9.5–9.6 | Replace automatic 30/60-session inference with **30 sessions for operational review; ≥120 fully matured signal dates before considering one registered model change**, followed by **60 untouched prospective signal dates plus label maturation**. Neither date count alone proves an edge. |
| **MUST** | 9.5 | Replace “2/3 blocks and IC≥0.03 / 20 observations” with daily cross-sectional IC and paired comparator spreads, uncertainty from **20-session date-block resampling**, retaining whole cross-sections. Purge training labels crossing validation start. A changed version needs positive prospective improvement with its **95% interval above zero** on the registered primary metric; otherwise inconclusive. |
| **SHOULD** | 9.3 | Use **1,000 reproducible Random-10 paths**, reporting median and 5th–95th percentiles. Add a simple **63-session-return ranking** comparator. Portfolio comparisons must match exposure and execution conventions. |
| **SHOULD** | 7 | Until costs are verified, report **0.30%, 0.60%, 1.00% round-trip** scenarios, charged proportionally on every fill, including reductions. Call them assumptions; no “after-cost edge” claim resting solely on 0.30%. |
| **SHOULD** | 3, 6 | Replace circuit heuristic **rejection with flagging** until authoritative band data exist. Rescore open holdings after they leave discovery, using the same daily reference distribution as challengers. |
| **SHOULD** | 9.4 | Separate fixed T+10 selection labels from realised execution P&L. Retain every rejection’s rule code; generate prose only for material cases. |
| **COULD** | 10–11 | Add Drive Sheets, polished HTML and automated publishing after the local batch is stable. |

**6. Agree as-is**

Paper-only scope; cash as a valid result; next-session execution as the basic timing principle; retaining discoveries and rejections; separating candidate research from sparse actual trades; sourced pre-entry records; append-only original decisions; versioned rules and separately stored rescoring; official EOD data over mixed ET snapshots; local canonical storage; and no automatic promotion into the owner’s human watchlist.

The two ET reports are useful **exploratory references only**. Their mixed timestamps and one-day comparisons provide no validation of the proposed weights, close-quality factor or regime thresholds.