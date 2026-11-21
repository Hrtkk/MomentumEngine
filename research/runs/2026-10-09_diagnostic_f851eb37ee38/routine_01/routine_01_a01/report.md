# Routine 1 diagnostic — 2026-10-09

**Status: PARTIAL · production eligible: NO**

Owner: Codex. Reviewer: Claude — UNAVAILABLE (budget accounting absent). Run at 2026-10-11T22:26:19.623298+05:30.

Universe: 500 diagnostic Liquid-500 names at 2026-09-30; evaluated 63; quarantined 437. Observed securities with events: 18; event records: 19. Counts derive from [metrics](metrics.jsonl), [quarantine](quarantine.jsonl) and [signals](signals.jsonl).

## Noteworthy diagnostic observations

| Symbol | Events | Daily return | Volume / prior 20-session median |
| --- | --- | --- | --- |
| SKYGOLD | ABOVE_PRIOR_20_SESSION_HIGH, ABOVE_PRIOR_252_SESSION_HIGH | 4.13% | 3.01× |
| PNGJL | CROSSED_ABOVE_SMA200 | 2.33% | 7.04× |
| GMRAIRPORT | PRICE_VOLUME_ANOMALY | 5.17% | 5.57× |
| NTPCGREEN | VOLATILITY_EXPANSION_CONDITION | 1.98% | 1.80× |
| AMBER | DRAWDOWN_10PCT_CROSSING | -1.68% | 1.45× |
| SBC | VOLATILITY_EXPANSION_CONDITION | -1.23% | 1.36× |
| POONAWALLA | CROSSED_ABOVE_SMA200 | 2.15% | 1.32× |
| NYKAA | CROSSED_ABOVE_SMA50 | 3.22% | 1.29× |
| IFCI | CROSSED_ABOVE_SMA200 | 1.38% | 1.11× |
| CARTRADE | CROSSED_ABOVE_SMA50 | 3.99% | 1.03× |

All table metrics are as of 2026-10-09; [raw/evidence references](evidence.jsonl); [formula configuration](config.json). They are research observations, not validated opportunities.

## Coverage and limitations

- Phase 0 calendar, historical identity and corporate-action completeness are not certified.
- Universe reproduction is diagnostic, not an approved membership snapshot.
- Broad/sector relative strength and sector breadth are NOT_EVALUATED: benchmark readiness absent.
- No previous committed R1 baseline: bootstrap, not claims of newly discovered signals.
- Claude review NOT performed: shared metered-call budget accounting is not implemented.
- Available data are dated 2026-10-09, not a live/current-session scan.

## Next run

Codex: certify calendar, effective identities, membership and corporate-action input completeness before promoting this lane. Add verified sector benchmarks and budget accounting. Claude: review signal interpretation when budget controls permit. Next R1 must load this diagnostic handoff and retain unresolved tasks; R2 may use these records as quarantined leads only, never qualification evidence.
