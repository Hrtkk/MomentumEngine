Yes. You can automate all five routines without keeping your laptop awake, your browser open, or Excel running.

But I would make one important architectural change:

Do not create five independent AI routines that each research stocks and produce reports. Create one coordinated research pipeline with five specialized workers, a shared database, and a single daily decision brief.

The workers should produce structured findings, not long reports. You should receive only important changes, actionable opportunities and exceptional risks.

# 1. Proposed architecture

Stock Research Database

Prices · Fundamentals · Watchlist · News · Decision history

1\. Market Movers

Identify unusual price, volume, and volatility

2\. Watchlist Builder

Score and rank new candidates

3\. Watchlist Monitor

Track thesis and technical changes

4\. News Intelligence

Connect relevant events to companies

Signal Aggregator

Deduplication · Evidence validation · Risk checks · Ranking

5\. Daily Decision Brief

Five-minute summary · Only material signals · Links to full research

&#x20;Critical alerts

&#x20;Daily digest

&#x20;Dashboard

The key is a persistent research state. Each run should compare fresh information against what was already known instead of independently analyzing thousands of stocks from scratch.

That reduces cost, repetition, noise and the chance of contradictory conclusions.

## 2. Responsibilities of the five routines

| Routine                  | Frequency                              | Output                               | AI needed?       |
| ------------------------ | -------------------------------------- | ------------------------------------ | ---------------- |
| 1. Market movers         | Daily, after close                     | Structured abnormal-movement signals | Mostly no        |
| 2. Watchlist preparation | Daily incremental + weekly full review | Ranked additions/removals            | Yes, selectively |
| 3. Watchlist monitoring  | Daily                                  | Changes in existing research theses  | Selectively      |
| 4. News intelligence     | Daily + event-triggered                | Material news and its implications   | Yes              |
| 5. Final report          | Daily                                  | One 5-minute brief                   | Yes              |

### Routine 1: Market movers

Scan the Nifty Total Market universe initially, then expand as your data infrastructure matures.

Identify more than top gainers:

- Daily change above 5% with relative volume above 2×.
- New 20-day, 52-week, and all-time highs.
- Price crossing important moving averages.
- Stocks outperforming their sector for multiple weeks.
- Sudden volatility expansion, gap-ups and abnormal volume.
- Unusual drawdowns in otherwise fundamentally strong businesses.

Output: A structured list of noteworthy events, not 50 stock analyses.

### Routine 2: Watchlist builder

Consume candidates from routine 1, plus periodic fundamental screens.

Maintain four categories:

| State               | Meaning                                | Action                   |
| ------------------- | -------------------------------------- | ------------------------ |
| Discovery           | Interesting movement or new data       | Quick screening          |
| Research            | Multiple supporting signals            | Deeper research          |
| Qualified           | Research complete, conditions defined  | Monitor for entry        |
| Rejected / Archived | Thesis failed or evidence insufficient | Retain historical reason |

A watchlist entry should include the reason for selection, baseline metrics, risks, next catalyst, invalidation condition and last review date.

Do not remove historical failures from the dataset. They are essential for learning whether your strategy works.

### Routine 3: Watchlist monitor

This worker should ask a single question:

What has materially changed since the last assessment?

For example, it can identify that earnings estimates deteriorated, debt increased, price broke an important level, a planned capacity expansion was delayed, or a valuation became more attractive.

If nothing meaningful changes, it should produce `NO_CHANGE` rather than another detailed write-up.

### Routine 4: News intelligence

Read exchange disclosures first, then reliable financial news, earnings transcripts and relevant sector developments.

Each event should contain:

- Affected companies and sector.
- Event type and original source.
- What actually happened.
- Why it could matter financially.
- Whether it confirms or contradicts the existing thesis.
- Whether the information is new or already reflected in a prior alert.

For example, a ₹2,000 crore order announcement should not automatically be treated as positive. The system must consider execution period, existing order book, contract profitability and whether the announcement is genuinely incremental.

### Routine 5: Report generator

This routine should be an editor, not another independent researcher.

It combines the findings, validates sources, removes duplicates and presents only the highest-value decisions.

That design keeps the daily report short even when the underlying research volume grows.

## 3. What your daily five-minute report should look like

ILLUSTRATIVE REPORT · NOT LIVE SIGNALS

## Daily Market Intelligence

Example layout · 4-minute reading time

Scanned

## 750

New candidates

## 4

Action items

## 2

1\. What needs your attention

Watchlist Company A

Review

Quarterly operating margin fell below the assumption in the original thesis. Reassess forward earnings and valuation.

Why now: thesis deterioration · Action: review position risk

Candidate Company B

Research

Relative strength and earnings acceleration both passed predefined screening thresholds.

Why now: two independent signals · Action: investigate

2\. New opportunities

3 companies entered discovery; 1 advanced to fundamental research. None automatically qualifies as an investment.

3\. Events that matter

One hypothetical sector-policy change may affect industrial order flows. Two repeated news items were suppressed.

4\. No action required

Remaining monitored candidates have no material thesis changes. Scheduled reviews continue.

Your decisions today

Review Company A's risk. Consider researching Company B. No automatic trade recommended.

Every real alert should link to a dated evidence record, calculation snapshot and full company research dossier.

### Notification policy

I would enforce a strict attention budget.

| Priority           | Condition                                                            | Delivery                      |
| ------------------ | -------------------------------------------------------------------- | ----------------------------- |
| P0 — Critical      | Material risk to an existing position, severe data or thesis problem | Immediate alert when detected |
| P1 — Actionable    | Qualified opportunity approaching a predefined condition             | Next digest or targeted alert |
| P2 — Interesting   | New candidate, sector development, moderate signal                   | Daily brief                   |
| P3 — Informational | Routine movements, repeated news, unchanged stocks                   | Database only                 |

Set a maximum of three main items per daily report and roughly 400–600 words overall. Critical alerts can override the limit.

The ideal outcome on a quiet trading day is a 30-second message saying that no material decisions are required—not a five-page document.

## 4. Running everything without your laptop

You have three practical options.

Option A — ChatGPT scheduled tasks

Simplest

Run recurring research prompts from ChatGPT's cloud infrastructure. Your computer does not need to stay awake. Suitable for broad daily scans, news summaries and a concise report.

Limitation: five independent scheduled prompts do not inherently form a reliable shared-state pipeline. They need compatible data access, and automatic cross-routine handoffs are not guaranteed.

Option B — GitHub Actions + database

Run Python screening jobs on hosted runners, keep stock data in a hosted database, use an LLM API for selected analysis, and send one final message.

Useful for an inexpensive MVP. Scheduled workflows may be delayed, so it's less suitable for time-critical intraday signals.

Option C — Cloud Run + PostgreSQL + scheduler

A durable pipeline runs jobs, maintains watchlist state, handles retries and builds one daily brief. This gives you much more control over dependencies and data validation.

Best long-term choice if you want extensive backtesting, quantitative screening, independent strategies and historical analysis.

Google Cloud supports scheduled Cloud Run jobs, including a monthly free allocation. Its Cloud Scheduler also offers three free scheduled jobs per billing account, with low per-job charges beyond that; compute, database, model calls and market-data licensing are separate costs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cloud.google.com\&sz=32)

Google Cloud

+2



### An interesting data source: NSE's MCP interface

NSE now documents an AI-oriented market-data interface with tools for historical OHLCV, market breadth, top gainers, 52-week ranges and volume analysis, among others. Its website describes access to five years of historical data. [Explore NSE MCP](https://www.nse.in/nse-mcp).

This could be useful for the screening component, but API entitlement, automated-use restrictions, pricing and corporate-action adjustments need verification before committing to it. NSE also has a formal market-data usage policy and paid historical-data products.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.nseindia.com\&sz=32)

NSE India

+2



I would not build a reliable automated system around unlicensed scraping or unstable third-party endpoints.

## 5. Recommended daily execution schedule

Use one orchestrator with five stages rather than five unrelated timers.

Example schedule, Indian Standard Time; weekdays and confirmed NSE trading sessions only. Times are operational targets, not exchange publication guarantees.

| Time    | Stage                                          |
| ------- | ---------------------------------------------- |
| 4:15 PM | Ingest and validate complete end-of-day prices |
| 4:25 PM | Market mover scans and technical indicators    |
| 4:35 PM | Watchlist update and existing-position checks  |
| 4:45 PM | Corporate filings and news analysis            |
| 5:00 PM | Aggregate signals, deduplicate and rank        |
| 5:15 PM | Deliver daily brief if data is complete        |

In production, the next stage should begin when the previous stage completes successfully, not merely because its scheduled clock time has arrived.

If an input is late, the orchestrator should retry and mark the affected sections incomplete. It must never substitute yesterday's prices without labeling them.

### Data pipeline

```
Data collected
    ↓
Validation / freshness checks
    ↓
Technical screening (deterministic)
    ↓
Fundamental screening (deterministic)
    ↓
New candidates + existing watchlist
    ↓
Research only changed/high-priority cases
    ↓
News and exchange-filing evidence
    ↓
Signal scoring + deduplication
    ↓
Daily digest + conditional alerts
```

One rule I would enforce: AI should explain and evaluate verified numeric signals; it should not invent financial metrics or be the source of truth for computed indicators.

## 6. What makes the system intelligent rather than noisy?

The biggest improvement is change detection coupled with evidence-based prioritization.

Every candidate should have a persistent record such as:

```
{
  "symbol": "EXAMPLE",
  "research_state": "QUALIFIED",
  "strategy": ["earnings_acceleration", "momentum"],
  "last_reviewed": "2026-10-09",
  "thesis_status": "INTACT",
  "new_signals": ["VOLUME_BREAKOUT"],
  "risk_flags": [],
  "next_review_trigger": "Q2_RESULTS",
  "notification_priority": "P2"
}
```

The engine should avoid sending repeated reports merely because a stock remains above its 50-day moving average.

Instead, notify when it crosses an important level, its classification changes, fresh evidence contradicts an assumption, or multiple previously independent signals converge.

### Scoring opportunities

I would begin with transparent rules, not an LLM-generated conviction score.

Example opportunity scoring weights

Customize the relative importance of signals. This does not calculate any real stock score.

Fundamental quality

25

Growth acceleration

25

Valuation attractiveness

20

Technical strength

15

Risk and governance

15

Combined weight

100/100

Copy scoring weights

For different strategies, maintain different models. A turnaround stock should not automatically score poorly just because its historical profit CAGR is negative.

And some conditions should be hard exclusions, not weighted away: serious accounting uncertainty, unsupported data, prohibited trading conditions or unacceptable liquidity risk.

## 7. Keep daily costs and effort under control

The easiest way to control costs is to avoid full AI analysis of every stock.

| Activity                             | Approximate workload                |
| ------------------------------------ | ----------------------------------- |
| Daily prices/indicator updates       | 750 stocks                          |
| Rule-based screening                 | 750 stocks, inexpensive computation |
| New or materially changed candidates | Perhaps 10–30 on a typical day      |
| AI research                          | Only highest-priority candidates    |
| Deep fundamental dossiers            | Few per week                        |
| Report delivered                     | One per trading day                 |

The candidate numbers are design targets, not observed market statistics.

Use caching, precomputed indicators, source-document hashes and a research refresh date to prevent repeated work. Keep immutable snapshots of calculations and conclusions, especially if you plan to backtest the discovery system later.

You should also track alert precision: how often a notification led to a useful review, versus how often it was irrelevant or repeated.

## 8. Implementation roadmap

Phase 1 — Minimal daily intelligence

One scheduled cloud job, one database, end-of-day scanning, a manually seeded watchlist and a daily digest. No automated buying or selling.

Phase 2 — Intelligent watchlist

Incremental fundamental updates, material-news classification, event deduplication, analyst-style research dossiers and thesis monitoring.

Phase 3 — Strategy research

Historical multibagger analysis, multiple independent strategies, point-in-time backtesting, opportunity ranking and paper-portfolio tracking.

Phase 4 — Self-evaluation

Compare original investment hypotheses with outcomes, calibrate alert quality and strategy performance, and test proposed rule changes on held-out data before adopting them.

### Final architecture recommendation

For your case, I would choose:

Cloud Run + Python + PostgreSQL + an LLM API + a lightweight dashboard + one daily notification.

Start with 750 stocks, keep full research dossiers in storage, and avoid using Excel as the underlying data-processing engine. Excel can remain an optional analysis and visualization interface.

Most importantly, separate automated discovery and research from investment authorization. The system may suggest that a stock deserves investigation or that an existing thesis has deteriorated; it should not autonomously execute trades based on AI conclusions.

Your intended daily experience should be simple: open one notification, read the top three findings, decide whether anything needs attention, and close it. The rest of the system continues to collect evidence and maintain its research history independently of your laptop.