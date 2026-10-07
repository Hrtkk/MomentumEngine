1. **Scoring edge cases — resolved:** A1 defines empty-population behavior and RSI boundaries.
2. **Cohort conventions — resolved:** A2 fixes sizes, filtering and tie-breaks.
3. **Replacement lifecycle — resolved:** A3 specifies linked orders, cancellation, fresh selection and tenure.
4. **Execution and costs — resolved:** A4 defines a paper fillability proxy, per-side costs and independent scenarios.
5. **Corporate-action scope — resolved:** A5 establishes consistent price returns and unresolved treatment for unsupported actions.
6. **Missing outcomes — resolved:** A6 specifies missing entries, endpoint fallback and preservation of formation weights.
7. **Bootstrap — partially resolved:** A7 still permits filtering out incomplete dates before constructing blocks. Register a pre-session patch requiring consecutive signal-date windows with complete paired outcomes; otherwise report inference unavailable.

**Design-level blockers:** None. Item 7 can reasonably be corrected as a pre-session implementation patch without changing the strategy’s hypotheses or acceptance thresholds.

**Convergence rule: Accept.** Log implementation conventions in `strategy_ledger.md` before the first live paper session. Changes to hypotheses, selection rules or acceptance thresholds remain governed by §9 rather than being classified as patches.

AGREE: v0.1 is ready for owner sign-off