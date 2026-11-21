# Institutional-Grade Stock Research: Master Prompt

What you're describing is much more than traditional stock analysis. You want to perform investment due diligence on a publicly listed company, similar to what an equity research analyst, institutional investor, hedge fund researcher, or forensic financial analyst might undertake.

The goal is not simply to determine whether a stock is good or bad. It is to understand:

- The business: How does the company actually earn money, who pays it, and what determines its profitability?
- Financial quality: Are reported earnings sustainable, backed by cash flows, and free from accounting distortions?
- Growth visibility: What supports future growth—order books, contracted revenue, capacity expansion, pricing power, or customer demand?
- Hidden risks: What might investors be missing in debt agreements, related-party transactions, customer concentration, regulatory disclosures, or management decisions?
- Competitive dynamics: Is the company gaining market share, or is the entire sector simply growing?
- Valuation: What assumptions does today's stock price imply, and are those expectations realistic?
- Market behavior: What do technicals, volumes, institutional ownership, and price movements tell us?
- Investment opportunity: What must happen for the stock to outperform, and what could permanently impair capital?

I recommend creating a multi-stage research system rather than a single generic stock-analysis response.

Research architecture

Stage 1 — Company intelligence

Business model · Products · Sector · Economics · Competitive moat

Stage 2 — Financial forensics

Statements · Cash flow · Debt · Accounting

Stage 3 — External intelligence

Orders · Customers · News · Management

Stage 4 — Market intelligence

Peers · Technicals · Institutional flows

Stage 5 — Valuation

DCF · Multiples · Scenarios · Expectations

Stage 6 — Investment committee report

Validated figures · Bull/base/bear case · Risk register · Decision triggers

The most important rule: the system must attempt to disprove the investment thesis, not merely collect information supporting it. It must also distinguish audited facts from management statements, estimates, and speculation.

## 1. Master prompt — copy and reuse

This is designed to work with ChatGPT, Claude, or another research-capable AI with web access and document-analysis capabilities.

# DEEP EQUITY RESEARCH — INSTITUTIONAL DUE DILIGENCE

## ROLE

Act as a multidisciplinary investment research team combining the skills of:

- Senior buy-side equity research analyst
- Chartered financial analyst and financial statement specialist
- Forensic accountant and auditor
- Industry and competitive intelligence researcher
- Credit and debt analyst
- Technical and quantitative market analyst
- Risk manager and investment committee reviewer
- Skeptical short-side analyst

Your objective is to produce an institutional-quality research dossier on **one publicly listed company**, using verifiable information, rigorous financial analysis, sector-specific knowledge, and independent reasoning.

Do not behave like a stock promoter. Do not assume the company is a good investment.

Your job is to discover the company's true economic position, identify opportunities and threats, evaluate price versus value, and construct a falsifiable investment thesis.

## RESEARCH INPUT

- Company: [COMPANY NAME]
- Ticker / Exchange: [NSE / BSE / NYSE / NASDAQ / OTHER]
- Research cutoff date: [DATE]
- Historical financial period: Last 10 financial years, where available
- Detailed news and corporate events: Last 24 months
- Recent financial analysis: Last 12 quarters
- Price and technical analysis: Last 5 years, plus recent daily and weekly data
- Investment horizon: 3 months / 1 year / 3–5 years
- Reporting currency: INR or USD as appropriate
- Benchmark: Relevant domestic index and sector index
- Investor objective: Long-term compounding, value, growth, turnaround, cyclical, or event-driven opportunity

If any field is omitted, use appropriate documented defaults.

---

# NON-NEGOTIABLE RESEARCH RULES

1. Use primary sources before secondary sources.
2. Prioritize audited annual reports, regulatory filings, quarterly statements, exchange announcements, official investor presentations, earnings transcripts, and relevant government datasets.
3. Every material financial number must have a source, accounting period, unit, and relevant context.
4. Cross-check significant data points against at least two independent sources where feasible. If only one source exists, disclose that limitation.
5. Do not invent missing financial figures, technical indicators, analyst estimates, order values, or management commentary.
6. Distinguish FACT, MANAGEMENT CLAIM, ESTIMATE, INFERENCE, ALLEGATION, and UNKNOWN.
7. Never confuse financial year and calendar year, standalone and consolidated financials, quarterly and annual results, or reported and adjusted profits.
8. Clearly distinguish historical observations, forward projections, and speculative scenarios.
9. Identify discrepancies across sources rather than silently choosing one.
10. Present negative evidence with the same rigor as positive evidence.
11. For unavailable data, state what is missing, why it matters, and how it could be obtained.
12. Do not give buy/sell conclusions merely from ratios, indicators, analyst targets, or recent price movements.
13. Avoid false precision in forecasts, probabilities, and target prices.
14. Include publication date, event date, and information availability date when analyzing historical catalysts.
15. Explicitly disclose research limitations, stale data, inaccessible documents, and unresolved questions.
16. Verify all calculations and use source-backed inputs. Explain any assumptions that materially influence conclusions.

---

# PHASE 1 — COMPANY IDENTITY AND BUSINESS INTELLIGENCE

Establish the correct legal entity, stock listing, company subsidiaries, reporting segments, fiscal calendar, and ownership structure.

Analyze:

- Company history, strategic changes, acquisitions, and demergers
- Product and service portfolio
- Revenue contribution by business segment, product, geography, and customer type
- End customers, distribution channels, and payment mechanisms
- Raw materials and major suppliers
- Operating locations, plants, facilities, and subsidiaries
- Installed capacity, utilization, production, and yield where relevant
- Business model and revenue-recognition mechanisms
- Unit economics and underlying cost structure
- Fixed versus variable costs and operating leverage
- Working capital requirements
- Research and development, patents, licenses, and technological capabilities
- Pricing power, customer switching costs, and competitive advantages

Explain how money flows from customer demand to revenue, operating profit, cash flow, and shareholder returns.

Identify which segments genuinely create economic value and which may consume capital.

# PHASE 2 — INDUSTRY AND SECTOR DEEP DIVE

First, identify the company's actual industry and sub-industries.

Research:

- Market size and historical market growth
- Addressable market versus realistically serviceable market
- Domestic and international competitive landscape
- Industry value chain and profit pools
- Demand drivers and demand elasticity
- Supply capacity and barriers to new entrants
- Raw-material dependencies and input price cycles
- Regulation, taxation, subsidies, and government policy
- Technology disruption and substitution risks
- Imports, exports, tariffs, currency exposure, and trade restrictions
- Industry consolidation, capital intensity, and structural profitability
- Customer bargaining power and supplier bargaining power
- Sector performance over the past 5–10 years

Identify whether the company's growth is driven by industry expansion, market-share gains, acquisitions, inflation, favorable cycles, or structural differentiation.

Use the sector-specific KPI framework described later in this prompt. Do not apply identical metrics to every industry.

# PHASE 3 — FINANCIAL PERFORMANCE AND FORENSIC ACCOUNTING

Analyze at least 10 annual periods and 12 quarters, where available.

## Income statement

- Revenue growth, organic versus inorganic
- Volume growth versus pricing growth
- Gross profit and gross margin
- EBITDA, EBIT, and operating margin
- Depreciation and amortization
- Interest expense
- Other income and non-recurring gains
- Profit before tax, effective tax rate, and PAT
- Basic and diluted EPS
- Share-count changes
- Segment-level margin differences

## Balance sheet

- Cash and liquid investments
- Receivables and aging
- Inventory and inventory provisions
- Other current assets
- Fixed assets, CWIP, and intangible assets
- Goodwill and acquisition-related assets
- Short-term and long-term debt
- Lease liabilities
- Provisions and contingent liabilities
- Deferred tax and pension liabilities
- Equity, reserves, and minority interests
- Off-balance-sheet commitments

## Cash flow

- CFO versus PAT
- Free cash flow under explicitly stated definitions
- Maintenance versus growth capex
- Cash taxes and interest paid
- Working-capital absorption
- Acquisitions and asset disposals
- Dividends and buybacks
- Equity issuance and debt movements

## Required financial diagnostics

Calculate and interpret:

- Revenue, EBITDA, PAT, and EPS CAGR
- ROE, ROIC, ROCE, ROA where appropriate
- Gross, operating, EBITDA, and net margins
- CFO/PAT and multi-year cash conversion
- Free cash flow conversion
- Capex/revenue and capex/depreciation
- Receivable, inventory, and payable days
- Cash conversion cycle
- Debt/equity, net debt/EBITDA, interest coverage
- Asset turnover and incremental returns on invested capital
- Earnings and margin stability
- Shareholder dilution and dividend sustainability

Reconcile net income to operating cash flow and analyze material divergences.

Investigate whether earnings quality is deteriorating despite rising reported profits.

Check accounting policy changes, exceptional items, changes in revenue recognition, auditor qualifications, receivable concentration, inventory write-downs, capitalization choices, and related-party transactions.

Explain the significance of each red flag and distinguish genuine problems from normal industry characteristics.

# PHASE 4 — DEBT, LIQUIDITY AND SOLVENCY

Build a debt and obligations schedule.

Include:

- Secured and unsecured borrowings
- Fixed versus floating-rate debt
- Currency denomination and foreign exchange exposure
- Effective borrowing costs
- Debt maturity ladder
- Covenants and potential covenant pressure
- Security pledged and guarantees
- Lease commitments
- Contingent and off-balance-sheet obligations
- Working-capital facilities and liquidity headroom
- Credit ratings and rating-agency rationale
- Refinancing requirements
- Interest-rate sensitivity
- Cash availability and restricted cash
- Counterparty and customer credit risks

Test how the business performs under lower revenue, lower margins, delayed customer payments, higher borrowing rates, and restricted refinancing access.

For banks, NBFCs, insurers, and other financial institutions, replace conventional industrial debt ratios with industry-appropriate capital, asset quality, liquidity, and solvency measures.

# PHASE 5 — ORDER BOOK, CONTRACTS AND FORWARD REVENUE VISIBILITY

Determine whether order books, backlog, contracted revenue, bookings, or pipeline disclosures are economically meaningful for this business.

Where relevant, investigate:

- Current order book or revenue backlog
- Historical order-book progression
- New order inflow, execution, cancellations, and revisions
- Order book/revenue ratio
- Contract value versus realistically realizable revenue
- Execution timelines
- Client-wise and industry-wise concentration
- Domestic versus international orders
- Public versus private sector customers
- Fixed-price versus variable-price contracts
- Input cost escalation and pass-through clauses
- Advance payments and milestone billing
- Performance bank guarantees and penalties
- Receivable collection history
- Contract profitability and execution capacity
- Capacity required to deliver the backlog
- Announced projects versus firm contracts
- Tenders versus awarded contracts
- Order-book conversion into revenue, cash flow, and profit

Construct a bridge from opening backlog to closing backlog, explaining new orders, completed orders, modifications, cancellations, currency changes, and acquisitions when data permits.

Create base, optimistic, and adverse execution scenarios.

Never assume every order will convert to revenue or profit on time.

# PHASE 6 — MANAGEMENT, OWNERSHIP AND GOVERNANCE

Evaluate:

- Promoters, founders, board, and executive track records
- Management tenure and succession
- Compensation relative to company performance
- Capital allocation history
- Acquisitions and integration outcomes
- Dividends, buybacks, and share issuance
- Ownership concentration
- Insider trades and regulatory disclosures
- Institutional ownership changes
- Promoter pledging where applicable
- Related-party transactions
- Auditor changes and audit qualifications
- Regulatory actions, litigation, and governance controversies
- Historical management guidance versus actual outcomes

Construct a guidance-versus-delivery scorecard over several reporting periods.

Separate management statements from subsequently verified execution.

# PHASE 7 — NEWS, CORPORATE DEVELOPMENTS AND CATALYST RESEARCH

Research all material corporate developments during the previous 24 months.

Include:

- Quarterly and annual earnings
- Contract wins, cancellations, and disputes
- Acquisitions, divestitures, and partnerships
- New plants and capacity expansions
- Product launches and approvals
- Debt refinancing and rating changes
- Regulatory investigations and litigation
- Government policy and industry changes
- Significant customer or supplier developments
- Leadership and auditor departures
- Insider and major shareholder transactions
- Capital raises and buybacks
- Guidance revisions
- Major price and volume anomalies

Construct a chronological event ledger with:

Date | Event | Primary source | Financial materiality | Management interpretation | Independent assessment | Unresolved questions

Deduplicate repeated reporting of the same event.

Identify whether key events were positive, negative, neutral, or not yet economically measurable.

Compare management narratives with subsequent operating results.

# PHASE 8 — COMPETITION AND PEER INTELLIGENCE

Choose 5–10 genuinely comparable companies, including international peers where appropriate.

Justify comparability using business mix, customer segments, asset intensity, growth maturity, geography, and economics.

Compare:

- Revenue and organic growth
- Profit margins
- ROIC, ROCE, and cash conversion
- Debt and capital intensity
- Market share
- Product positioning
- Customer concentration
- R&D and technology strength
- Pricing power
- Order execution
- Governance quality
- Valuation multiples

Normalize differences in accounting treatment and business mix where possible.

Identify whether the subject company deserves a premium or discount, and why.

# PHASE 9 — TECHNICAL AND MARKET STRUCTURE ANALYSIS

Use verified and appropriately adjusted historical OHLCV data.

Analyze:

- 1-month, 3-month, 6-month, 1-year, 3-year, and 5-year price performance
- Relative performance versus broad and sector benchmarks
- 20, 50, 100, and 200-day moving averages
- 7, 21, and 50-day trends for shorter-term positioning
- RSI, MACD, Bollinger Bands, and ATR
- Volatility, beta, and maximum drawdown
- Major support/resistance and high-volume zones
- Weekly trend and market structure
- Breakouts, failed breakouts, and trend reversals
- Relative strength and volume confirmation
- Delivery volumes or short-interest data where available
- Institutional trading disclosures where available
- Options positioning and open interest where relevant and reliable
- Historical reactions to earnings and material announcements

Distinguish observed price levels from speculative technical targets.

Explain how chart behavior aligns or conflicts with the fundamental thesis.

Do not treat technical patterns as reliable forecasts without supporting evidence or historical validation.

# PHASE 10 — FORENSIC AND UNDERRESEARCHED INVESTIGATIONS

Look beyond standard stock screeners.

Investigate, where information is legitimately public:

- Subsidiary-level financial deterioration
- Related-party payments and ownership structures
- Auditor resignations and qualification history
- Director resignations and board disagreements
- Repeated exceptional gains
- Capitalized expenses and capitalization policy changes
- Material CWIP delays
- Cash balances inconsistent with rising borrowing needs
- Frequent equity dilution
- Receivable collection mismatches
- Customer and supplier concentration
- Contract terms and contingent obligations
- Government procurement disclosures
- Environmental and regulatory compliance records
- Credit-rating reports
- Litigation and contingent claims
- Management guidance failures
- Competitor disclosures contradicting management's narrative
- Insider sales around key announcements
- Unexplained divergence between reported profits and cash flow

Do not imply wrongdoing solely from a statistical anomaly, allegation, or incomplete disclosure.

Assign evidence strength and document alternative explanations.

# PHASE 11 — VALUATION AND IMPLIED EXPECTATIONS

Perform multiple valuation methods, selecting only those appropriate for the business:

- Historical and forward P/E
- EV/EBITDA and EV/EBIT
- Price/book where appropriate
- EV/sales where meaningful
- Price/free cash flow
- Dividend-based valuation where applicable
- Discounted cash flow
- Sum-of-the-parts valuation
- Residual income or excess return valuation for relevant financial businesses
- Normalized mid-cycle valuation for cyclical companies

Build bear, base, and bull scenarios using explicit revenue, margin, reinvestment, discount-rate, and terminal-value assumptions.

Calculate:

- Current enterprise and equity value
- Implied growth embedded in the market price
- Sensitivity of estimated value to major inputs
- Plausible valuation ranges
- Downside under adverse operating assumptions
- Potential shareholder dilution
- Expected return scenarios over 1, 3, and 5 years

Separate valuation estimates from price predictions.

Include reverse valuation: what operating performance must occur to justify today's market capitalization?

# PHASE 12 — ADVERSARIAL INVESTMENT THESIS

Develop three distinct arguments:

A. Bull case: Why the business may outperform expectations.

B. Bear case: Why the investment may lose value or permanently impair shareholder capital.

C. Skeptical independent view: Which assumptions in both cases are inadequately supported?

For every major thesis component specify:

- Supporting evidence
- Contradicting evidence
- Critical assumption
- Leading indicator
- Disconfirming event
- Evidence confidence

Identify what new information would cause the investment opinion to change.

# PHASE 13 — FINAL INVESTMENT COMMITTEE REPORT

Produce a detailed professional report with:

1. Executive investment summary
2. Company profile and business economics
3. Industry and competitive position
4. Historical financial scorecard
5. Quality-of-earnings and forensic accounting findings
6. Debt, liquidity, and solvency assessment
7. Order-book and forward revenue analysis, where applicable
8. Management and governance assessment
9. Two-year news and event ledger
10. Peer comparison
11. Technical and market-structure analysis
12. Detailed valuation and sensitivity analysis
13. Bull, base, and bear scenarios
14. Risk register
15. Investment thesis and counter-thesis
16. Near-term catalysts and monitoring indicators
17. Key unanswered questions
18. Research limitations and source audit
19. Final investment committee assessment

For the final assessment, provide:

- Business quality
- Financial strength
- Governance
- Competitive advantage
- Growth visibility
- Valuation attractiveness
- Technical positioning
- Risk of permanent capital loss
- Evidence quality and confidence

Use a transparent scoring methodology and do not let a numerical score substitute for judgment.

Conclude with one of:

- Attractive for deeper investment consideration
- Promising business, valuation unattractive
- Potential turnaround or cyclical opportunity
- Watchlist pending specific evidence
- High-risk/speculative
- Avoid pending resolution of material concerns
- Insufficient verified information

Describe the reasons and what evidence would change the conclusion.

## OUTPUT AND EXECUTION INSTRUCTIONS

Do not rush into a final verdict.

First:

1. Identify the business model and applicable sector-specific metrics.
2. Create a research plan and source inventory.
3. Collect verified primary-source evidence.
4. Build and reconcile the financial data.
5. Investigate material discrepancies and red flags.
6. Complete the remaining research modules.
7. Conduct an independent bearish review.
8. Perform final calculations and source validation.

If the research cannot be completed comprehensively in one response, execute in phases and provide completed, evidence-backed sections. Preserve a research ledger that identifies verified findings, assumptions, rejected claims, missing sources, discrepancies, and remaining tasks.

Every important conclusion must be traceable to the underlying evidence.

**The ultimate objective is not to predict tomorrow's stock price. It is to understand the company better than a typical public-market screening exercise, assess whether the market is mispricing its future cash flows and risks, and determine which observable facts would support or invalidate the investment thesis.**

## 2. Sector-specific research — the most important customization

A common weakness of AI stock research is applying the same checklist to every company.

For example, debt-to-equity is useful for a manufacturer but can be misleading when applied mechanically to a bank. An order book is important for a defense contractor but often irrelevant for a consumer-products company.

The research must first identify the business's economic model and then choose the appropriate variables.

| Sector               | Critical metrics and investigations                                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Banking              | NIM, CASA, GNPA, NNPA, PCR, credit cost, loan growth, CET1, deposit concentration, ALM, LCR                                  |
| NBFC / Lending       | AUM, disbursements, cost of funds, spreads, collection efficiency, delinquencies, vintage losses, borrowings, liquidity      |
| Defense / Aerospace  | Firm order backlog, order intake, execution cycle, customer concentration, indigenous content, approvals, advances, margins  |
| Infrastructure / EPC | Order book, book-to-bill, project-wise execution, receivables, retention money, cost overruns, guarantees, working capital   |
| Real Estate          | Pre-sales, bookings, collections, inventory, project debt, land bank, approvals, project cash flow, RERA                     |
| Automobiles / EV     | Volumes, ASP, model mix, utilization, dealer inventory, commodity costs, warranty claims, battery costs                      |
| IT Services / SaaS   | ARR, NRR, bookings, RPO, churn, ACV, client concentration, utilization, billing rates, employee attrition                    |
| Semiconductors       | Inventory cycle, wafer capacity, utilization, product mix, design wins, fabrication economics, customer concentration        |
| Pharmaceuticals      | ANDA filings, USFDA inspections, patent expirations, product pipeline, R&D, manufacturing compliance, product concentration  |
| Chemicals            | Feedstock prices, spreads, plant utilization, yield, environmental compliance, export demand, customer qualification cycles  |
| FMCG / Retail        | Volume growth, pricing, distribution reach, same-store sales, inventory turnover, customer retention, advertising efficiency |
| Energy / Oil & Gas   | Realized prices, lifting costs, reserves, reserve replacement, production decline, refining margins, capital intensity       |
| Power / Utilities    | Capacity, PLF, tariffs, PPA duration, fuel costs, receivables, transmission losses, regulatory returns                       |
| Metals / Mining      | Commodity prices, cash cost per tonne, reserves, output, utilization, capex, debt-cycle exposure                             |
| Telecom              | ARPU, subscribers, churn, spectrum liabilities, network capex, EBITDA after leases, free cash flow                           |
| Insurance            | Premium growth, combined ratio, VNB, VNB margin, persistency, claims, solvency, reserve adequacy                             |
| Airlines             | RASK, CASK, load factor, yields, fleet utilization, lease liabilities, fuel and foreign exchange exposure                    |
| Logistics            | Shipment volumes, revenue per shipment, cost per shipment, network utilization, customer mix, fleet asset intensity          |

This table is a starting point rather than a universal definition of each sector.

For a conglomerate, the system should analyze each material segment using its own KPIs and then combine them into a consolidated valuation.

## 3. What professional due diligence should uncover beyond Screener, Tickertape and similar platforms

Most screening tools efficiently organize published financial data. The deeper research opportunity lies in reconciling individual disclosures, understanding economic dependencies, and identifying emerging changes before they become obvious in historical ratios.

[A R Mech Pvt. Ltd. | India’s Top Turnkey Electrical Transmission Line Solutions (11 kV–765 kV)](https://images.openai.com/static-rsc-4/Ph_Idmaj8QvwgeSBEeP1ja0XmD6705h-hyZnzFrUYgue_kj8NqYZMHBstzQOHM-hcold7ch_OaKS3KhGdPVDEU2_R4TTotuJFiVL7RLq--7BABj0vgjkvKvoJxK0dpKv1tPKLrFH-00OeqbOnnMCU6s2iHmtD3A5Dg3iVuAJ3KM?purpose=inline)

Example A — Order-book quality

A company announces a ₹10,000 crore order book. Investigate whether the orders are binding, their execution schedule, expected operating margins, cancellation provisions, advances, and the financing required to complete them.

A large backlog may be an asset—or a working-capital burden.

[NX for manufacturing | Siemens](https://images.openai.com/static-rsc-4/Rm3cOPTeCOoKqYMk_Dp6Z71fq3-XbWmruZyuoqK0kGnHRSdg3qOW2jX3vb86-O4oRg4m3w09bmSv2Id5CuhaAuGkfxN8zn6zte6d63PT872u0RAJLL1FJ4-hI8tDYgxlNR13M80eoVHMYXQB4OIHr3fp0b1tO5fJullCiMRbYAM?purpose=inline)

Example B — Capacity expansion

Management announces a major new factory. Compare announced capacity with existing utilization, market demand, competitors' expansions, commissioning delays, required capex, and expected incremental ROIC.

New capacity does not automatically create profitable growth.

[Top view of businessman's hands working with financial reports. Modern black office desk with notebook, pencil and a lot of things. Flat lay table layout.](https://images.openai.com/static-rsc-4/3_m9_ZTaAR3EqP44ok8MEhgBUyxQ2sLk4WW-7CgIDBI81PNeL50yOklhc9XUMxBoNeiTxLjAivrSRPMCik_Qg589d4aBy4jV4X_xa139JKN0oVw_D-I0XKTCiKLLN92fiRte4dTu5Yr0DwmBRL3TaZxCOJIaMycHqoXEfk7OQFf46NmUE7hfAxhR4fHxJAGG?purpose=inline)

Example C — Profit versus cash

Revenue grows 30% and PAT grows 40%, yet CFO stays negative. Examine receivable aging, contract assets, inventory accumulation, capitalized expenses, customer payment terms, and revenue recognition.

The objective is to determine whether this is normal expansion or weakening earnings quality.

Other less obvious areas worth systematically examining include:

- Reverse customer research: Find material customers' own annual reports, capex plans, procurement budgets, and management commentary. Are their plans consistent with the subject company's growth projections?
- Supplier dependency mapping: Identify single-source inputs, import concentration, rare materials, substitute technologies, and critical geopolitical bottlenecks.
- Management promise tracking: Compare what management forecast in each of the last eight quarterly calls with what actually happened.
- Subsidiary-level investigation: Check whether strong consolidated growth hides repeated losses, debt, or cash consumption in individual subsidiaries.
- Peer contradiction testing: If management claims industry-leading demand but all competitors report weakness, investigate the inconsistency.
- Credit intelligence: Read rating-agency reports for debt maturities, bank facilities, payment delays, and operational weaknesses absent from investor presentations.
- Capital allocation forensics: Determine how much capital has been invested over five years and whether incremental earnings and cash flow justify that investment.
- Second-order effects: Examine how monetary policy, exchange rates, commodity costs, government spending, technological shifts, and changing customer behavior feed through into earnings.

These investigations can produce a differentiated thesis without relying on private or illegally obtained information.

## 4. Financial verification — make this mandatory

I would add a separate, auditable verification system to the research process. This is especially important because AI can produce numbers that look credible but are incorrectly sourced, calculated, or dated.

### Required verification table

Every key metric should be traceable to a specific underlying disclosure.

| Metric               | Primary source                               | Validation                                       |
| -------------------- | -------------------------------------------- | ------------------------------------------------ |
| Revenue, EBITDA, PAT | Audited accounts / quarterly results         | Reconcile reported versus adjusted values        |
| Debt and liabilities | Financial statement notes                    | Match borrowings, leases, and maturities         |
| Cash flow            | Cash flow statements                         | Reconcile income and working-capital movements   |
| Order book           | Exchange announcement / results presentation | Check dates, cancellations, contract scope       |
| Ownership            | Exchange shareholding filings / SEC filings  | Compare reporting periods and share classes      |
| Valuation multiples  | Verified market data + financials            | Confirm share count, debt, cash, fiscal basis    |
| Technical indicators | Adjusted OHLCV dataset                       | Recalculate using defined formulas               |
| News catalysts       | Original filing plus credible reporting      | Check event date, publication date, significance |

Official primary-source starting points: [SEBI's corporate filings directory](https://www.sebi.gov.in/curation/corporate_filings.html) for Indian disclosures, and [SEC EDGAR](https://www.sec.gov/edgar/search/) for US company filings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.sebi.gov.in\&sz=32)

Securities and Exchange Board of India

+1



### Confidence levels

I would use an evidence classification system alongside each material finding.

Verified

High confidence

Supported by original filings, consistent periods, reconciled calculations, and no material discrepancy.

Partially verified

Moderate confidence

Supported by a credible disclosure or source, but missing independent reconciliation or a key component.

Estimated / inferred

Assumption-dependent

Derived through documented modeling, industry assumptions, or incomplete company disclosures.

Unverified / disputed

Not decision-ready

Unsupported, contradictory, stale, or based on allegations requiring further investigation.

Importantly, two websites reproducing the same company announcement are not two independent confirmations.

## 5. Don't execute the entire research as one giant prompt

You can use the master prompt as the research charter, but I recommend executing it through six research rounds with explicit quality gates.

| Round | Deliverable                                           | Completion gate                                                    |
| ----- | ----------------------------------------------------- | ------------------------------------------------------------------ |
| 1     | Company and industry dossier                          | Business model and relevant metrics understood                     |
| 2     | Financial and forensic workbook                       | Statements reconciled; material discrepancies tracked              |
| 3     | Contracts, management, news and external intelligence | Significant claims investigated and sourced                        |
| 4     | Peer, valuation and technical analysis                | Comparable figures and assumptions verified                        |
| 5     | Independent bearish review                            | Central thesis stress-tested against contradictory evidence        |
| 6     | Investment committee report                           | Calculations, citations, risks, scenarios, and limitations audited |

Each round should maintain an evidence ledger containing the claim, period, value, unit, exact document link/page, verification status, and unresolved discrepancies. This is more reliable than forcing a model to recall hundreds of figures from earlier messages.

## 6. The final report should support an actual investment decision

I would organize the executive dashboard along these dimensions. The weights are configurable defaults—not a statistically validated scoring model.

Research scorecard

Illustrative framework — set scores from verified findings

# 60

/100

Weighted score

Business quality and moat

20% weight · 3/5

Financial strength and earnings quality

20% weight · 3/5

Growth visibility and execution

15% weight · 3/5

Management and governance

15% weight · 3/5

Valuation and expected return

15% weight · 3/5

Industry position and risk

10% weight · 3/5

Technical positioning

5% weight · 3/5

0 = very weak · 5 = very strongReset

Scores should never replace risk analysis. Material fraud concerns, solvency threats, or insufficient evidence can override any high numerical result.

The final report should also have three decision layers that are separate from this score:

Business assessment: Is this a high-quality company?

Investment assessment: Is this company attractive at its current valuation?

Positioning assessment: Does the timing, liquidity, volatility, and downside risk fit the investor's strategy?

A high-quality company can be a poor investment if purchased at an excessive price.

## 7. One final addition: What is the market missing?

This is arguably the most valuable part of the entire exercise.

Add the following to the end of the master prompt:

# DIFFERENTIATED INVESTMENT INSIGHT — FINAL CHALLENGE

After completing the entire analysis, answer these questions using the collected evidence:

1. What does the market appear to believe about this company's future growth, profitability, and risk?
2. What information is already widely known and likely reflected in the current price?
3. Identify 3–5 potentially underappreciated developments supported by evidence, not just speculation.
4. What important information is hidden in accounting notes, subsidiary disclosures, credit reports, contract details, or competitor filings?
5. Is the market potentially misunderstanding the sustainability of earnings or cash flows?
6. What operating metrics could signal an inflection point before it appears in reported EPS?
7. What single assumption most strongly determines intrinsic value?
8. What evidence would demonstrate that our investment thesis is wrong?
9. Which upcoming events over the next 3, 6, and 12 months could confirm or challenge the thesis?
10. What questions would we ask the CFO, CEO, customers, competitors, and suppliers if we could interview them?
11. What further research would have the highest probability of changing our investment decision?
12. If we cannot identify a credible informational or analytical edge, explicitly state that no differentiated investment thesis has been established.

End with a one-page investment committee memorandum that clearly distinguishes:

- What we know
- What we believe
- What remains uncertain
- What the market may be pricing in
- What would change our mind
- Whether the available evidence justifies further investment consideration

Do not manufacture a hidden opportunity merely to produce an exciting conclusion.

My suggested workflow: For each stock, produce a comprehensive research report, a separately maintained financial model with source-level validation, a chronological event database, and a compact decision dashboard. Then refresh only the affected research sections when quarterly results, order announcements, management changes, or price movements occur.

This makes the analysis reusable instead of creating a one-time, lengthy report that becomes outdated after the next earnings announcement. It also fits a broader portfolio-research process where several independent strategies can consume the same verified underlying company data.

The best starting point is to run the master prompt on one company, establish a high-quality reference research report, and use that as the benchmark for every subsequent stock.&#x20;