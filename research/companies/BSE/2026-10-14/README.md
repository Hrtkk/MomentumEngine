# BSE Ltd — first research case

Research cutoff: 14 October 2026, Asia/Kolkata. NSE symbol BSE; ISIN INE118H01025. Provisional horizon: 3–5 years, assumed rather than specified by the owner. This is a dated initial research pack, not a completed investment due-diligence certification or a trading recommendation.

## Initial assessment

**The research case is about the durability of derivatives earnings and the valuation paid for that durability.** BSE's recent growth warrants further investigation. The present evidence does not establish a differentiated investment thesis or a sufficiently reconciled cash-flow valuation.

The working hypothesis is that deeper participation and recurring platform revenue can sustain earnings even when industry trading activity slows. The strongest opposing hypothesis is that recent profitability depends on a favourable mix of trading activity, competitive conditions and regulatory settings that may not persist. These are research hypotheses, not reported facts.

## What the latest results establish

Consolidated figures, INR crore except EPS. Source: S2, PDF page 5; FY25 comparison from S1, printed page 153. Figures below are extracted from company-authored documents retrieved through a third-party mirror; they have not been independently matched to an issuer-hosted copy.

| Metric | FY25 | FY26 | Q1 FY26 | Q4 FY26 | Q1 FY27 |
|---|---:|---:|---:|---:|---:|
| Revenue from operations | 2,957.34 | 4,833.95 | 957.95 | 1,563.51 | 1,566.02 |
| Profit attributable to parent shareholders | 1,325.89 | 2,496.98 | 539.41 | 797.33 | 874.02 |
| Reported EPS, INR | 32.18 | 60.61 | 13.09 | 19.35 | 21.22 |

Q1 FY27 operating revenue increased **63.5% year on year but only 0.16% sequentially**. Parent profit increased 62.0% year on year and 9.6% sequentially. Investment income rose from INR61.69 crore to INR135.18 crore sequentially. Consequently, the latest profit increase should not be described as equivalent growth in the core transaction business. These calculations are reproducible in `model.py`.

Profit definitions matter: Q1 FY27 total group profit is INR872.66 crore, while parent-attributable profit is INR874.02 crore, because non-controlling interests incurred losses. Per-share valuation uses the parent basis.

## How the business should be modelled

Use separate drivers for transaction fees, listing services, clearing-fund treasury income, and other operating services. Keep investment income and associate earnings separate. The company reports one accounting segment; product disclosures are not audited segment-profit accounts. [S2 PDF6; S3 PDF25–26]

The presentation reports Q1 FY27 derivatives premium ADTV of INR29,615.4 crore and derivatives revenue of INR1,155.0 crore. Premium turnover is a more relevant starting point for options fee analysis than headline notional turnover. Build the bridge from chargeable turnover, trading days and realised fee yield, then reconcile it to revenue; confirm one-sided versus two-sided charging conventions before computing yield. [S3 PDF13]

A useful operating model is:

`industry premium activity × BSE share × effective fee yield − variable clearing/regulatory costs − fixed operating costs`

Then add the other businesses, depreciation, investment income, associate earnings, tax and non-controlling interests. A simple assumption that all revenue growth drops into profit would be inappropriate.

## Cash and disclosure checks

FY26 continuing CFO was INR3,103.68 crore versus INR410.15 crore in FY25; cash capex was INR515.16 crore versus INR153.23 crore. CFO/continuing group profit was 1.25x and 0.31x respectively; combined conversion was 0.93x. Other-liability movements contributed INR727.67 crore to FY26 CFO. [S1 printed154]

**Research implication:** investigate the liability bridge before extrapolating conversion. CFO less capex is a diagnostic, not automatically cash distributable to shareholders.

Owned bank balances identified in notes11–12 total INR3,001.11 crore excluding accrued interest; earmarked balances are separate. No excess-cash adjustment is made. Regulatory capital and operating requirements remain unresolved. Contingent claims and guarantees total INR330.16 crore; this is exposure disclosed, not an expected loss. [S1 printed189–191,216]

The presentation lists 406,129,077 shares; the annual report records 407,884,077 paid-up shares and 411,979,077 for EPS including abeyance entitlements. Use published EPS pending current capital reconciliation. [S1 printed14,153; S3 PDF31]

## Valuation: what expectations need testing?

Indicative reference price: **INR3,375.40**, Upstox timestamp **13 October 2026, 15:59 IST**, corroborated by Kotak Neo. This is a secondary-source quote, not a verified NSE official close or a live 14 October price. The official NSE archive download failed twice.

Derived reported trailing EPS through June 2026 = FY26 EPS − Q1 FY26 EPS + Q1 FY27 EPS = **INR68.74**. At the indicative price:

| Earnings basis | Indicative P/E |
|---|---:|
| Reported FY26 | 55.7x |
| Trailing through June 2026 | 49.1x |
| Q1 FY27 EPS multiplied by four | 39.8x |

The last row is an annualisation sensitivity, **not a forecast**. Its lower multiple assumes that the latest quarter's earnings repeat. The trailing series also contains the prior discontinued-operation contribution; a fully normalised series remains to be built.

For an illustrative **12% annual price return over five years**, excluding dividends, required EPS growth would be:

| Assumed terminal P/E | Required annual EPS growth |
|---|---:|
| 25x | 28.2% |
| 35x | 19.8% |
| 45x | 14.0% |

These are algebraic sensitivities, not fair multiples, probabilities or return forecasts. Formula: `required growth = (current P/E × (1 + return hurdle)^years / terminal P/E)^(1/years) − 1`. The assumed hurdle is not the user's stated requirement. Dividends would reduce the earnings hurdle for the same total return, all else equal.

**Interpretation:** sustained earnings growth and the future valuation multiple both matter. Business growth alone does not settle the investment case. No target price, DCF or enterprise-value multiple is published because distributable cash and a normalised earnings baseline are not sufficiently reconciled.

## Counterarguments and next tests

| Hypothesis | Evidence that would strengthen it | Evidence that would weaken it |
|---|---|---|
| Derivatives franchise is becoming durable | Premium activity, participation and non-expiry activity broaden at stable fee yield | Growth concentrates in a narrow contract/expiry window; share or yield falls |
| Scale supports profitability | Operating earnings grow after regulatory, clearing and technology costs | Volume grows but costs absorb the gain |
| Other platforms diversify earnings | Repeat fee income grows with measurable contribution to operating profit | New products generate announcements but negligible revenue |
| Earnings become cash available to owners | Reconciled multi-period conversion after required investments | Liability reversals, restricted balances or investment needs absorb cash |
| Valuation assumptions are achievable | Operating evidence supports sustained per-share growth across scenarios | Earnings plateau while a high valuation still requires rapid growth |

The August call identifies a prior-quarter debtor provision and discusses uncertainty around regulatory effects. Management also describes a future change in international data distribution. Treat explanations and future plans as management statements, not independent proof of recovery or future profit. [S4 printed7,5,13–14]

Peer work should start with NSE for competitive economics and MCX for exchange operating leverage, then use CDSL/CAMS/KFin only as business-model contrasts. A common sector label does not justify the same multiple. No peer valuation ranking or analyst consensus has been validated here.

## Coverage and acceptance status

- **Completed:** initial business hypothesis, recent consolidated financial comparison, cash-flow diagnostics, indicative reverse expectations, opposing thesis, evidence register and monitoring checklist.
- **Still open:** issuer-hosted document matching; official closing price; full multi-year/quarterly normalisation; July–September operational data; latest ownership filings; current regulatory texts and effective dates; fee schedules; detailed capital/earmarked-cash bridge; peer and institutional forecast comparison; audit/governance history beyond the inspected sections.
- The latest financial period inspected is June 2026. This is not a claim that all subsequent disclosures were reviewed. Technical indicators and order-book analysis are not part of this first pass.
- Readiness remains **RESEARCH — incomplete evidence**, with no promotion into the operational research registry or changes to paper books. The most valuable next work is the post-June volume/fee bridge and the cash restrictions reconciliation.

## Files and sources

- `model.py` and `model-output.json`: sourced inputs, reproducible calculations and explicitly assumed scenarios.
- `evidence.jsonl`: material findings, provenance and verification limitations.
- `monitoring.md`: review conditions and next research tasks; no scheduler installed.
- `sources.json` and `sources/`: source URLs, publication dates, local originals and SHA-256 hashes. S1 annual report; S2 results filing; S3 presentation; S4 earnings-call transcript.
- Price sources: [Upstox](https://upstox.com/stocks/bse-limited-share-price/), [Kotak Neo](https://www.kotakneo.com/stocks/bse-share-price/).
- Regulatory follow-up: [SEBI August 2026 study announcement](https://www.sebi.gov.in/media-and-notifications/press-releases/aug-2026/sebi-studies-indicate-key-trends-in-retail-participation-trading-behaviour-and-profitability-in-the-equity-derivatives_103838.html). The announcement was located; the underlying studies and current rules have not been fully analysed. No new rule is inferred from a study announcement.
