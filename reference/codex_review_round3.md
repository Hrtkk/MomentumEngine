Round-2 items, in original order:

| Item | Resolved? |
|---|---|
| 1. Discovery universe | Yes. |
| 2. History, membership, retention, survivorship | Yes. |
| 3. Reconciliation and stale inputs | Yes. |
| 4. Formulas | Yes for the requested corrections; remaining indicator edge cases below. |
| 5. Percentiles and close quality | Yes. |
| 6. Annotation neutrality | Yes. |
| 7. Regime logged only | Yes. |
| 8. Frozen quantities and next-open execution | Yes, with an explicit cash-affordability reduction. |
| 9. Fixed stops | Yes: intraday fills, invalid stops and entry-gap cancellation are specified. |
| 10. Primary endpoint and fixed cohorts | Yes; cohort conventions still need corrections below. |
| 11. Matched benchmark | Partial: H1 is aligned; return and corporate-action conventions remain incomplete elsewhere. |
| 12. Review and validation schedule | Yes. |
| 13. Prospective acceptance | Yes: the prospective improvement’s own interval must exceed zero. |
| Watchlist/portfolio compromise | Acceptance stands. |
| Additional: incumbent scoring | Partial: empty reference populations remain undefined. |
| Additional: selection and replacement | Partial: cohort conventions conflict; replacement timing remains ambiguous. |
| Additional: funding and failed exits | Partial: cash constraints and reserved slots exist, but execution lifecycle needs completion. |
| Additional: unresolved outcomes | Partial: weights are frozen, but missing-price cases and panel exclusions remain ambiguous. |
| Additional: reproducible statistics | Partial: random cohorts are specified; bootstrap construction is incomplete. |
| Additional: premature agreement | Yes: header correctly says confirmation and sign-off are pending. |

Remaining **BLOCKING** ambiguities, with exact fixes:

1. **Scoring edge cases — [§4](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/STRATEGY.md:78).** No incumbent percentile exists when the candidate set is empty; RSI’s zero-gain/zero-loss cases are unspecified. **Fix:** when `n=0`, mark MQS unavailable, suspend score-driven removals/replacements, and retain eligibility exits and stops. Specify RSI using separately Wilder-smoothed gains/losses seeded from the first 14 close changes; return 100 for positive gain/zero loss, 0 for zero gain/positive loss, and 50 when both are zero.

2. **Conflicting cohort rules — [§8.1](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/STRATEGY.md:198).** Universal `min(10,n)` contradicts the two “all” cohorts; the universal tie rule omits PERSIST10’s return tie-break. **Fix:** DISCOVERY and ELIGIBLE retain all members; apply `min(10,n)` only to top-10 selections; MQS10_EQS filters MQS10 without replenishment. Specify PERSIST10 ordering as `(persistence descending, day-t return descending, symbol ascending)`.

3. **Replacement lifecycle — [§§6–7](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/STRATEGY.md:150).** “Deferred until the exit fills” permits either a stale challenger order or fresh selection, potentially at different opens. **Fix:** make each swap a linked exit/entry pair for the next open. Execute the entry only if that exit fills at that open; otherwise cancel the entry and reserve the slot. After a delayed exit fills, select afresh at that day’s close for the following open. Define three-session tenure as counting the entry session.

4. **Execution and cost conventions — [§7](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/STRATEGY.md:172).** Tradability is undefined, and cost scenarios can produce different quantities and rosters. **Fix:** register a precise, data-backed fillability predicate for both buys and sells; absent required trading-status data, record no fill. For round-trip rate `c`, charge `fill_notional × c/2` on each side. Run cash, quantities, equity and resulting holdings independently per scenario; define frozen quantity as the maximum order quantity subject only to the stated affordability reduction.

5. **Return and corporate-action scope — [§§2, 7, 8.2](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/STRATEGY.md:218).** Price-return treatment is explicit only for H1; primary cohorts and paper corporate-action handling can diverge. **Fix:** extend the dividend-excluding, corporate-action-adjusted convention to every research return, adjusting both entry and endpoint prices consistently. Define paper adjustments to quantities, stops and cash for each supported action; unsupported actions must make valuation unresolved rather than silently use raw prices.

6. **Missing outcomes — [§8.1–8.2](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/STRATEGY.md:212).** Missing entry prices, trading resuming within the five-session grace period, and demerger exclusions lack a consistent aggregation rule. **Fix:** missing entry prices remain unresolved. For a missing endpoint, explicitly use the first subsequent traded close within five sessions; otherwise use the last close on or before the endpoint. Preserve formation weights in H1 too: `CA_UNRESOLVED` makes the aggregate unresolved, rather than dropping and reweighting the member.

7. **Bootstrap construction — [§8.2](/Users/khritik/workspace/StartupIdea/InvestmentStrategy/momentum-engine/STRATEGY.md:223).** Block length, seed and replicate count do not specify block draws or incomplete data handling. **Fix:** use chronological, consecutive signal-date windows with complete paired outcomes; otherwise mark inference unavailable. For `N≥20`, sample `ceil(N/20)` starts uniformly with replacement from `0…N−20`, concatenate their 20-date blocks, truncate to `N`, and compute the mean. Repeat 10,000 times from one seeded generator; take linear-interpolated 2.5th/97.5th percentiles. For `N<20`, report no interval.

Non-blocking nits: none.

AGREE WITH CHANGES: scoring edge cases; cohort conventions; replacement lifecycle; execution and costs; corporate-action scope; missing outcomes; bootstrap construction