# Evidence, calculations and integrity appendix

Cutoff14 October2026. This extension preserves the original README, model.py, model-output.json, evidence.jsonl, monitoring.md and sources.json. No operational registry, portfolio ledger or scheduler is changed.

## Classification convention

- **VERIFIED:** transcribed and checked against a retrieved source document; host provenance is stated separately. This does not authenticate a mirror as an issuer-hosted copy or independently audit a company claim.
- **CALCULATED:** reproducible arithmetic using referenced inputs. Narrative interpretation remains conditional and is not a separate factual claim.
- **MANAGEMENT CLAIM:** explanation, intention or forward statement made by management.
- **THIRD-PARTY ESTIMATE:** an outside analyst's forecast. No validated consensus is available in this edition.
- **SCENARIO ASSUMPTION:** an explicitly chosen input, including industry growth, relative share changes, fees, taxes, capital needs, dilution and multiples.
- **UNRESOLVED:** unavailable, conflicting, stale, incompletely reconciled or unverified against a direct source.

The quoted market reference is a secondary observation, not an analyst forecast; direct verification remains UNRESOLVED. No confidence percentage or probability is invented.

## Source register

| ID | Document | Publication / coverage | Retrieval and status |
|---|---|---|---|
| S1 | BSE FY26 annual report |23July2026; FY26 and FY25 accounts | Original pack sources/bse_fy26.pdf; company-authored PDF via FinancialFilings mirror; SHA-256 in original sources.json |
| S2 | BSE quarterly results |4August2026; June2026 quarter with comparatives | sources/bse_results.pdf; PDF5 P&L, PDF6 notes; mirror-hosted, key table visually checked |
| S3 | BSE Q1 FY27 presentation |4August2026 | sources/bse_q1fy27.pdf; PDF13 operating activity,25–26 P&L,29 history,30 capital allocation,31 ownership |
| S4 | BSE earnings-call transcript |Call4August2026, filed10August2026 | sources/bse_transcript.pdf; management statements kept separate |
| S5–S6 | Upstox / Kotak Neo quote pages |13October2026 quote; retrieved14October | Original source URLs preserved; underlying feed independence unknown; no official-close match |
| P1 | MCX FY26 presentation |11May2026; FY26/FY25 consolidated | Local sources/mcx_fy26.pdf; company-authored mirror PDF; detailed P&L PDF13 |
| P2 | NSE FY26 results release |5May2026; FY26/FY25 | Issuer release reproduced on NoticeBlue; direct NSE PDF retrieval failed; numerical comparison remains provisional |
| P3 | NSE official financials directory |Accessed14October2026 | Confirms document availability; not used as a source of unseen numerical statements |
| P4 | MCX official investor-relations directory |Accessed14October2026 | Official results link located; PDF text not extractable by web tool; local download403 |

P1: [public company-presentation mirror](https://stockinsights-ai.s3.amazonaws.com/in/announcements/159926e7-8f51-49ed-b2e4-91a396ce779c.pdf).

P2: [reproduced NSE release](https://noticeblue.com/circulars/88a10820-7907-4c81-8133-1af19b9d807e); [original NSE link, retrieval failed](https://nsearchives.nseindia.com/web/pressrelease/2026-05/PR_cc_05052026_20260505191148.pdf).

P3: [NSE financials](https://www.nseindia.com/static/investor-relations/financials). P4: [MCX investor relations](https://www.mcxindia.com/investor-relations/).

All local additions have provenance in sources.json; the original source register is unchanged. PDF page means one-based physical page, while printed page means the document's own page number.

## Financial bridges and conventions

1. **Q1 P&L:** 1,566.02 +135.18 +5.52 −536.69 −25.91 +19.54 −291.00 =872.66 group PAT; subtract−1.36 minority loss =874.02 parent PAT. SourceS2 PDF5.
2. **Trailing EPS:** 60.61 −13.09 +21.22 =68.74, rounded published total-operation EPS. Period endsJune2026. TTM parent PAT2,831.59cr is separately calculated; do not switch to a different share denominator without reconciliation.
3. **Price/earnings:** 3,375.40/68.74 =49.10x. Quote13October, not live14October. Original reverse-expectation formulas remain in ../model.py.
4. **Annual cash:** FY26 continuing CFO3,103.68 / continuing GROUP PAT2,475.30 =1.254x. FY25 410.15/1,317.06 =0.311x. Two-year ratio uses sum of cash divided by sum of profit =0.927x.
5. **Receivable days:** ending net receivables / annual operating revenue ×365. Average balances and credit-only sales are not available; label as diagnostic.
6. **ROE / ROA:** parent PAT/average parent equity; group total PAT/average total assets. Separate profit and balance bases prevent a minority-interest mismatch.
7. **MCX operating margin:** headline EBITDA1,773.63 less other income127.05, divided by operating income2,302.00. Includes fund/regulatory expense. BSE analogous FY26 operating EBITDA3,078.69/4,833.95. Do not compare headline73% with operating63.7% directly.
8. **Peer median:** arithmetic median of NSE and MCX only, excluding BSE. Missing either comparable observation means no median. No sector percentile. Profit/total-income row is a uniform arithmetic ratio, not the issuers' own net-margin definition.
9. **Scenario price:** modelled diluted EPS × assumed P/E. Do not add associate value or cash again when their earnings are already capitalised. Scenario dividends are accumulated without reinvestment; terminal wealth CAGR is not IRR.
10. **Units:** original BSE statements in lakhs divide by100 for crore; presentation millions divide by10. Shares expressed in crore in scenario.py-equivalent calculate.py, so PATcrore/sharescrore gives INR/share.

## Historical and presentation discrepancies

- S3 lists a smaller outstanding-share count than S1's paid-up shares; published EPS includes abeyance entitlements. Original E07 remains open.
- S3 PDF29 labels profit/EPS as continuing/adjusted but its FY25 EPS32.18 matches total-operation S2, not continuing32.06. Do not use the chart as a uniform adjusted-EPS series.
- S3 displays FY26 continuing profit24,755million while S1 gives247,530lakh; these differ byINR0.20cr beyond a straightforward one-decimal crore reading. The detailed statement takes priority; source discrepancy is retained.
- Earlier headline FY24 profit includes a strategic investment-sale gain. No unadjusted EPS CAGR is calculated across that break.
- Six years of total income are available, but five-year cash, return-ratio, ownership, price-return and valuation histories are incomplete. Availability of a historical chart is not evidence of a complete point-in-time dataset.

## Scenario assumptions and reference baseline

All forward values are SCENARIO ASSUMPTION/CALCULATED. Base revenue capacity6,264.08cr is four times the Q1 operating-revenue line. Derivatives4,620cr is four times presentation derivatives revenue1,155cr; residual other operating revenue1,644.08cr is calculated. Rounded cash operating expenses2,080cr use four times management's520cr quarter figure and its54% variable-cost description. Minor baseline differences from exact statement EBITDA are rounding, not adjustments to reported accounts.

Depreciation170.4cr, investment income540.72cr, other income22.08cr and after-tax associate earnings78.16cr annualise S2 lines. Eligible share denominator41.1979077crore uses S1's EPS basis. It is not asserted to be a current tradable share count. No minority loss is forecast; no additional debt financing is assumed. The model's base tax method differs deliberately from the historical effective-rate denominator by taxing before associate earnings.

The expense split, future relative share, investment returns, required capital and dividends are not management guidance or third-party consensus. No probability-weighted expected price is supplied. Required capital is a placeholder assumption and not a regulatory calculation; a full integrated cash/balance model remains open.

## Evidence expansion and checks

`evidence-extension.jsonl` adds history, peer inputs, definition conflicts and scenario assumptions without changing the old ledger. `glossary.json` provides structured definitions, values, history, comparisons and assessments. `calculate.py` regenerates calculations.json, scenario tables and charts. `build_glossary.py` regenerates the glossary.

Arithmetic checks cover P&L reconciliation, minority attribution, original CFO bridge, share/EPS consistency within scenarios, dividend cash caps, scenario cost bridges, peer normalisation, five-year growth intervals, and preservation of original-source hashes. A successful calculation is not verification of a forecast assumption.

## Research still needed

Direct-host authentication; official quote; latest capital reconciliation; post-June operational/financial data; fee schedules and exact premium-yield convention; applicable regulation; required-capital and earmarked-cash bridge; older audited financials; matched peer cash and valuation; guidance-delivery record; full governance and ownership history. These gaps limit the investment conclusion, but do not prevent transparent conditional analysis.
