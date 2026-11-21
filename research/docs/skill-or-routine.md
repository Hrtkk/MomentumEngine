I recommend building it as a reusable research Skill, then using scheduled routines to keep the research updated.

These solve different problems:

- Skill = How to research a stock. Defines methodology, financial formulas, sector-specific metrics, data validation, forensic checks, valuation, and report structure.
- Routine = When and what to research. Runs recurring checks for financial results, regulatory announcements, order wins, news, peer developments, and changes to the investment thesis.

For your goal of institutional-grade stock research, a Skill should be the foundation, and daily routines should operate on top of it.

## Recommended architecture

Equity Research Skill

Research methodology · Sector playbooks · Validation rules · Scoring · Report templates

Deep Research

Run on demand for any stock

Daily Routines

Monitor existing coverage

Persistent Research Repository

Company dossiers · Verified financials · Source ledger · Event history · Open questions

Investment Intelligence Dashboard

Investment thesis · Changes · Risks · Watchlist · Actionable research questions

## How I would divide the work

| Component                            | Frequency                              | Output                                     |
| ------------------------------------ | -------------------------------------- | ------------------------------------------ |
| Full fundamental research            | Once per stock; major refresh annually | 30–60+ page dossier if evidence warrants   |
| Financial statement update           | Quarterly                              | Updated financial model and ratios         |
| Order book and contract intelligence | Daily event check                      | New orders, cancellations, execution risks |
| Corporate news and filings           | Daily                                  | Material developments and source links     |
| Technical and price-volume analysis  | Daily after market close               | Trend, volatility, key levels              |
| Sector and peer research             | Weekly                                 | Competitive changes and sector outlook     |
| Valuation refresh                    | Quarterly or material event            | Revised scenarios and assumptions          |
| Investment thesis audit              | Monthly or material event              | What changed, what was disproved           |

Don't run full deep research every day. It is expensive in research effort, creates duplicated information, and increases the risk of contradictory reports.

Instead, daily routines should perform incremental research: detect new information, validate it, assess its significance, and update only what has changed.

## My recommended implementation

Create a Skill named `deep-equity-research` with this structure:

```
deep-equity-research/
├── SKILL.md
├── references/
│   ├── research-methodology.md
│   ├── india-sources.md
│   ├── us-sources.md
│   ├── sector-playbooks/
│   │   ├── banking.md
│   │   ├── defense-epc.md
│   │   ├── manufacturing.md
│   │   ├── technology.md
│   │   └── other-sectors.md
│   ├── financial-forensics.md
│   ├── orderbook-analysis.md
│   ├── valuation.md
│   └── technical-analysis.md
├── templates/
│   ├── research-report.md
│   ├── evidence-ledger.csv
│   ├── investment-thesis.md
│   └── daily-change-report.md
└── scripts/
    ├── validate_financials.py
    ├── calculate_ratios.py
    └── technical_indicators.py
```

The Skill describes and standardizes research. The scripts handle repeatable calculations. A persistent repository or database maintains the research history. Scheduled tasks invoke the appropriate research instructions.

### Start with just three routines

Daily — Company Intelligence Monitor

Check new announcements, news, orders, governance developments, sector changes, and price-volume movements. Report only material changes.

Weekly — Thesis and Peer Review

Examine whether new evidence strengthens or weakens the investment thesis, compare peers, and identify emerging risks.

Quarterly — Fundamental Research Refresh

Reconcile reported results, update financial models and forecasts, evaluate management guidance, and recalculate valuation scenarios.

For standalone ChatGPT scheduled tasks, keep the routine reasonably focused. A task prompt alone does not guarantee that arbitrary Skill files, scripts, or a persistent database will be accessible at execution time. For a fully automated pipeline with durable data and calculations, a repository-backed scheduler is the stronger implementation.

My choice for you: Build the Skill first, validate it against two very different companies (for example, one bank and one industrial company), and only then automate daily monitoring. This prevents an imperfect research methodology from being repeated automatically across your watchlist.

Once established, the same Skill can support Indian and US equities, long-term investing, and event-driven stock research.