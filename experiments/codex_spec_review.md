**E1 needs changes before execution.** §5 is defensible as a conservative screening policy, but not as evidence that a strategy lacks an edge. No files were edited.

1. **BLOCKING — the >40% filter can introduce look-ahead and hide losses.**  
   [SPEC §1](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/experiments/SPEC.md:11) prohibits trading on a day identified using that day’s closing return. That information is unavailable for an opening order. Excluding such days also leaves held-position valuation and subsequent indicators undefined; genuine crashes or corporate actions could disappear.

   **Exact fix:** “The >40% flag is a data-validation alert, never a retrospective order-cancellation rule. Validate flagged observations before the run against an independent source and corporate-action records; retain genuine moves and log corrections. An unresolved observation affecting execution or valuation makes the affected comparison unresolved; do not drop the return or renormalise weights. Signal exclusions identified at close t affect only orders from t+1.”

2. **BLOCKING — today’s split-adjusted prices leak future corporate actions into the ₹50 threshold.**  
   [Eligibility](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/experiments/SPEC.md:21) uses an absolute price threshold against retrospectively adjusted history. A split occurring after historical date t can change whether a stock qualified on t. Return ratios are generally invariant to that rescaling; ₹50 is not. S0 also mixes Yahoo indicators with bhavcopy execution prices, making consistent units essential.

   **Exact fix:** use contemporaneous nominal close for ₹50 eligibility and contemporaneous traded turnover for liquidity. Compute indicators on a consistently adjusted series, converting stops into execution-date units. Specify split/bonus adjustments to quantities and stops, and explicit treatment of mergers, rights and demergers. Unresolved actions must block the affected comparison rather than silently erase holdings or returns.

3. **BLOCKING — B2 is neither operationally defined nor a bias-neutral comparator.**  
   [B2](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/experiments/SPEC.md:46) does not specify formation versus return timing. Averaging today’s returns over today’s eligible names would select using information from those same returns. Free daily rebalancing also gives B2 an economic advantage over costed strategies. Sharing current constituents does **not** make survivorship bias cancel: strategies have different exposures to the selected survivors.

   **Exact fix:** form B2 targets from eligibility at close t; execute at open t+1; retain the old portfolio’s overnight return; value through the common endpoint. Apply the same missing-price and execution conventions. Report both **B2-gross** and an independently funded **B2-net**, charged the same per-side costs; use B2-net for the economic comparison. Replace “fair comparison” with “conditional comparison within today’s surviving universe; differential survivorship bias remains unknown.” If B2-gross remains the rejection hurdle, explicitly call it an intentionally stricter, frictionless hurdle.

4. **BLOCKING — “S0 as-is” conflicts with the specified adaptation.**  
   The engine’s [essential factors](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/src/engine.py:219) include `deliv_ratio`; missing delivery therefore fails eligibility before the volume-only fallback can help. Its [affordability rule](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/src/engine.py:463) rejects a stock priced above 20% of equity even in the fractional book, contradicting “scale-free returns.” The implementation also depends on external parameters and data adapters.

   **Exact fix:** freeze hashes of `engine.py`, `parameters.yaml`, input data and the adapter. Name the comparison version **S0-E1**, listing every override: fractional quantities, sector percentile 50, delivery optional for eligibility with volume-only scoring when its ratio is unavailable, and removal of the one-share affordability rejection. Preserve and enumerate the remaining execution rules. Compare an adapter replay with the original engine on an overlapping period and explain every difference. Do not label the adapted version “as-is.”

5. **BLOCKING — the common portfolio lifecycle is under-specified.**  
   [Common rules](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/experiments/SPEC.md:25) leave independent implementations free to choose signal-close versus opening quantities, borrowing, replacement funding, failed-order retries, same-day stop activation, ineligible-held-name treatment and re-entry after stops.

   **Exact fix:** register the following explicitly for S1–S5/S7:
   - Freeze `qty = 0.10 × equity_close_t / C_t`; execute exits before ranked buys, reduce buys to available cash including fees, and prohibit borrowing.
   - Cancel buys if `open ≤ stop`; reject nonpositive stops; activate stops on the entry session.
   - Retry unfilled exits each open and reserve their slots and industry capacity. Cancel unfilled buys; require a fresh signal.
   - State whether scheduled exits permit linked replacements at the same open; permit those buys only after their linked exit fills.
   - Exit names failing observable eligibility at the next open; distinguish genuine ineligibility from unresolved data.
   - Use no cooldown for these strategies unless explicitly added; evaluate fresh signals only after that session’s execution.

6. **BLOCKING — S5/S7 candidate and event state is not reproducible.**  
   [Weekly candidate sets](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/experiments/SPEC.md:29) conflict with daily event detection and leave “rank ≤50” undefined between rebalances. S7 does not say what happens with overlapping events, repeated confirmations or events spanning weekly refreshes.

   **Exact fix:** adopt a concrete state machine:
   - Freeze weekly S4 ranks and candidate membership through the next scheduled refresh. S5 WATCH consists of rank ≤40 names satisfying its trend filter at refresh; recheck eligibility, trend and entry conditions daily.
   - S7 candidates are the frozen S4 top 50. Accept T0 only while a name belongs to that set; allow one active event per name, ignoring newer events while one is active.
   - Count k in exchange sessions; include T0 in the midpoint-close condition; invalidate on its first failure or loss of candidate membership; expire after k=7.
   - Use only the first confirmation, consume the event after its one opening-order attempt, and retain that event’s low for the position’s exit rule.
   - Allocate simultaneous entries by frozen S4 score descending, then symbol ascending.

7. **BLOCKING — numerical conventions and evaluation boundaries can change the result.**  
   [Indicator definitions](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/experiments/SPEC.md:27) omit volatility’s exact window and standard-deviation convention, ties, zero volatility and missing-session handling. RSI can differ materially: the engine explicitly uses its [last 300 closes](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/src/engine.py:191). The final signal date has no in-window next-open fill, and a truncated dataset can falsely make October 7 a weekly/monthly rebalance.

   **Exact fix:** freeze an exchange calendar and data-history start; index lookbacks by exchange sessions without compressing missing rows. Define Rk=`C_t/C_(t−k)−1`; VOL126 from exactly 126 log returns ending t, `ddof=1`; zero volatility makes VAM unavailable. Use the engine percentile formula and symbol-ascending final rank ties. Specify RSI’s 300-close convention, S5 windows inclusive of t, five-session range=`max(H)−min(L)`, and S7 volume median over t−20…t−1. Use actual scheduled period ends, not dataset-group endpoints. Start all books together from cash; value at the final close and leave unexecuted orders unfilled.

8. **BLOCKING — §5 overstates what this comparison can reject and does not isolate the proposed causes.**  
   [S0 versus alternatives](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/experiments/SPEC.md:35) changes slots, sizing, stops, industry limits, turnover and selection simultaneously. That is valid for comparing complete packages, but cannot establish that momentum selection or patient entry caused improvement. S5 additionally changes selection breadth and trend exits relative to S4.

   [§5](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/experiments/SPEC.md:59) can reject on an arbitrarily small negative estimate or half-window sign flip. Neither constitutes statistical evidence of inferiority. The diagnosis already inspected part of this window, so pre-registration now does not make it untouched validation.

   **Exact fix:** describe E1 as **exploratory package screening conditional on the available universe**, with failure meaning “not advanced under this policy,” not “strategy disproved.” Explicitly prohibit causal attribution to individual components; such claims require matched ablations. Define halves as the first `floor(N/2)` and remaining daily return observations from one continuous book, without resetting positions. Require strictly positive excess CAGR in **each** half rather than an ambiguous sign comparison. Define drawdown as positive loss magnitude and reject when `MDD_strategy − MDD_B2 > 0.10`. Label the previously examined dates as development data. Reserve inferential conclusions for a separately registered prospective evaluation; historical uncertainty estimates cannot repair survivorship or prior selection.

AGREE WITH CHANGES: causal data filtering; contemporaneous price thresholds and corporate actions; executable B2; frozen S0 adaptation; portfolio lifecycle; S5/S7 state machines; numerical and calendar conventions; exploratory-only rejection rule.