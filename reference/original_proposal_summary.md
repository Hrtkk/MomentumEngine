# Original proposal (owner, 2026-10-07) — summary

- Treat NSE top-100 daily gainers as a discovery universe, not the strategy itself.
- Three loops: discover → decide → learn. Rolling 7-day raw universe + permanent decision ledger.
- Momentum Quality Score with weights: RS 20, trend 15, volume 15, breakout 15, persistence 10, sector 10, market-relative 5, catalyst 5, risk/vol 5; penalties for spikes, illiquidity, gaps, operator-like behaviour, circuits, over-extension, weak volume, adverse news.
- States: Discover → Candidate → Watch → Entry-ready → Hold → Reduce → Exit → Rejected. Cash is valid.
- 10-slot watchlist where challengers compete with weakest incumbent.
- Separate Momentum Quality vs Entry Quality scores.
- Allocation by confidence × risk (exceptional 10–12%, strong 7–10%, experimental 3–5%); paper first.
- Pre-written thesis: why, expected behaviour, invalidation, exit.
- Classify TP/FP/TN/FN, timing/sizing/exit errors; learn from false negatives.
- Versioned strategy ledger; never silently change rules; ~10–20 observations before changing a core rule; freeze ~30 sessions.
- Benchmarks: Nifty 50/500, sector, candidate baseline; horizons 1/3/5/10/20D.
- Daily 3 passes: scan, deep analysis (top 20–30 → top 10 challengers → keep/add/replace/remove/wait), review.
- Five permanent datasets: daily scanner, candidate history, watchlist ledger, outcome ledger, strategy ledger.
- Owner wants Claude and Codex to share daily scanning/monitoring; data on Google Drive if possible, else local.
