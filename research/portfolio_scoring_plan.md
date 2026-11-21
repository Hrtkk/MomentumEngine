# Portfolio fundamentals scoring plan

Status: proposed methodology, 14 October 2026. No company score has been assigned by this plan.

## Existing evidence

`docs/inidividual-stocks-research.md` (Research scorecard section) provides an illustrative seven-component scorecard. Its 60/100 example uses placeholder 3/5 component ratings and is not a company rating. `schedules.md` also supplies illustrative opportunity weights, explicitly not real stock scores. The BSE dossier at `companies/BSE/2026-10-14/README.md` remains incomplete and has no accepted numerical score. Searches of research Markdown, JSON and JSONL found no completed fundamentals score for the current holdings.

## Owner policy

- Equity index funds, including sector index ETFs: Long term, 3–5 years.
- Gold: Long term; retain the separate Gold allocation bucket.
- Debt: Medium term; retain the separate Debt allocation bucket.
- Individual equity score 8–10: Long term; 6–<8: Medium term; 4–<6: Short term. Apply the highest qualifying band.
- Below 4: Review, with no automatic sale or promotion. Missing scores remain unavailable.
- Silver has no new owner rule; preserve its existing horizon pending a specific policy.
- Allocation targets remain Long term 30%, Medium term 30%, Short term 20%, Gold 10%, Debt 10%. The first three buckets exclude gold/debt to prevent double counting. A separate horizon view may include them.

## Proposed fundamentals score out of 10

Adapt the existing research scorecard into a business-fundamentals score. Keep valuation and technical timing separate so a price change does not relabel business quality. Proposed weights below require calibration and are not validated predictors:

| Component | Weight | Evidence |
|---|---:|---|
| Business quality and moat | 25% | Customer retention, competition, concentration, durable unit economics |
| Financial strength and earnings quality | 25% | Reconciled cash conversion, leverage, returns on capital, contingent obligations |
| Growth visibility and execution | 20% | Multi-period revenue/profit drivers, execution against guidance, per-share dilution |
| Management and governance | 20% | Auditor findings, related-party dealings, capital allocation, disclosure quality |
| Industry position and structural risk | 10% | Cyclicality, regulation, disruption, competitive position |

Rate each component 0–5 against a published sector-specific rubric. Total = 2 × SUM(component rating × component weight), yielding 0–10. Anchors: 0 severe evidenced weakness; 1 weak; 2 below the defined sector benchmark; 3 adequate; 4 strong; 5 exceptional with sustained evidence. Missing evidence is null, never a neutral 3. Do not redistribute weights across missing components. Assess unrounded scores at the 4/6/8 boundaries.

## Implementation sequence

1. Build an evidence record keyed by ISIN, reporting cutoff, publication date, source URL/page and method version. Prioritize the eight held equities: ZEEL, SURYAROSNI, EIDPARRY, LTF, BSE, LICHSGFIN, ICICIBANK and HFCL.
2. Publish sector rubrics before scoring. Banks/NBFCs/housing finance require capital adequacy, asset quality, funding and provisioning metrics; ordinary industrial cash-conversion ratios are not interchangeable. Exchanges require clearing/regulatory capital and restricted-cash treatment. Validate the issuer/sector mapping.
3. Gather current issuer/exchange filings and reconcile at least five annual periods and eight quarterly periods where available. Document exceptions and freshness limits. Expand the existing BSE dossier rather than duplicating it.
4. Record component ratings with evidence and counterevidence. Unresolved material governance/solvency issues, stale mandatory evidence or incomplete mandatory coverage block an accepted score regardless of the numerical result.
5. Store append-only score versions: component ratings, score, evidence status, as-of date, reviewer, method version and rationale. Never overwrite the original investment thesis to justify a revised horizon.
6. Publish only accepted scores into the sheet's Fundamentals score column; retain score source/date alongside the evidence registry. Existing equity horizons remain provisional while scores are absent.
7. Test 3.99/4/5.99/6/7.99/8/10, blanks, zero, invalid input, stale/blocked evidence, symbol sorting and Gold/Debt precedence. Check aggregate allocation equals portfolio value once, and changes follow ISIN rather than row position.
8. Review quarterly and on material filings. Measure stability and false promotions before automation. No alerts, scheduler or trading execution are enabled by this plan.

## Current sheet behavior

Strategy is the holding horizon. Asset class and Allocation bucket are separate fields. Existing manual equity horizons are preserved as provisional when scores are missing; Classification status makes this visible. Valid scores entered later apply the owner bands. Numeric score entry must be limited to accepted research results; the sheet does not independently verify research provenance.

Index-fund identity references checked for this update: [Nippon India ETF directory](https://etf.nipponindiaim.com/Home/faq), [ICICI Prudential Nifty FMCG ETF](https://digitalfactsheet.icicipruamc.com/passive/icici-prudential-nifty-fmcg-etf.php), and [Zerodha Nifty Smallcap 100 ETF](https://www.zerodhafundhouse.com/etfs/zerodha-smallcap-etf-ZESML). Applying the Long term label is the owner's policy, not a recommendation inferred from these sources.
