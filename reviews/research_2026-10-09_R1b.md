# Research R1b — R1 follow-ups from the Codex review (2026-10-09, development data only)

**Question:** Do R1's findings about M11's 52-week-high breakouts survive the fixes Codex asked for: observed-only hit rates, correct count labels, exclusion of stale/unfillable returns, an entry-aligned benchmark, dependence-aware bootstrap blocks, and multiplicity-controlled bucket contrasts?
**Method:** Same signal set as R1 (`R1_m11_anatomy.signals`, reused unchanged; 8,722 breakouts, 6,722 M11 signals, signal dates 2013-01-01..2020-12-31, windows ending ≤ 2020-12-31). New: per-signal execution flags from `sim.fillable` (entry buy at open t+1, exit sell at close t+h), open-above-stop check, terminal-close-present check; "clean" = all four. Benchmark B2-net rebuilt from `run_e1.b2_series`'s arithmetic (replication asserted to 1e-12) with the day-t+1 overnight leg removed. Circular moving-block bootstrap over the 96 calendar months (L = 4 primary, L = 8 sensitivity, 4,000 draws, seed 20261009) plus a symbol-cluster bootstrap; 44 bucket contrasts tested as differences of means under joint block resampling, Holm-adjusted across all 44, BH q-values alongside. Code: `experiments/research/R1b_m11_followups.py`, output `experiments/research/out_R1b/`.
**Result:** The corrections are small and do not change the picture. M11 60d excess on the clean sample with the aligned benchmark is **+4.30% [+2.84, +5.70] (block L=4; L=8 and symbol-cluster intervals agree to ±0.2 pp)**, vs R1's +4.05%; median +0.63%, observed-only hit rate 51.4% on the clean/aligned sample. Correcting only R1's missing-as-loss error (R1 treatment, same sample) gives 50.7% at 60d, not 49%, and 51% for 2020, not 38%. Mean 60d excess after dropping the top 5% of signals: +0.32%. Only 50 of 6,460 M11 60d outcomes are excluded as unfillable/stale (mean raw excess of the excluded +11.2%); excluding them moves the 60d mean by −0.06 pp. Aligning the benchmark raises every horizon by ≈+0.3 pp (the dropped B2 overnight leg averages +0.296% for M11, +0.279% for rejected signals). Short horizons stay negative: 5d −0.60% [−0.87, −0.34], 10d −0.20% [−0.53, +0.13], 20d +0.52% [−0.15, +1.19]. **No bucket contrast survives multiplicity control:** smallest raw p = 0.027 (distance 3–5% vs 0–1% at 20d, +1.65 pp); Holm-adjusted p = 1.00 for all 44 tests, smallest BH q = 0.33. M11 vs volume-rejected breakouts at 60d: +1.20 pp [−0.87, +3.05], p = 0.31.
**Caveats:** Block bootstrap over 96 months with L=4 gives ≈24 effective blocks, so intervals are rough; 60-session overlap is inside a block only when both signals fall within the same 4-month block (L=8 sensitivity agrees). Same-name episodes (median 3 signals/date, 5,015 of 6,722 M11 signals are repeats within 63 sessions) inflate n; the symbol-cluster interval is the relevant check and is no wider. The signal-level analysis is not book-level attribution (no slots, sector cap, rank exits); no claim about which trades drove the E2 result is made, and R1's "samples this tail randomly" sentence is withdrawn. `pit_panels.build()` uses a through-2026 cache with retrospective symbol mapping and corporate-action factors; no truncated-source invariance check was run (not done, see below). Bucket edges (volume, distance, 63-session repeat window) are the same ad-hoc choices as R1. Fillability is judged by `sim.fillable` on a daily bar; it is not a market-impact model.
**Next:** R1 conclusions stand as hypotheses with the corrected numbers: M11's development-period excess is a ~3-month right-tail effect with a ~51% hit rate, not a high-hit-rate signal; none of the volume, distance or first/repeat cuts are distinguishable from noise after multiplicity control. R2 next (agreement between strategies).

## What changed vs R1, item by item (Codex review 2026-10-08)

| Codex issue | R1 | R1b | Effect |
|---|---|---|---|
| Hit rates counted missing as losses | 49% (60d), 38% (2020) | observed only, R1 treatment: 50.7% (60d), 51% (2020); clean/aligned: 51.4% | the "2020 low hit-rate" statement in R1 was wrong |
| Count labels | "773 names / 1,661 dates" was the breakout set | M11: 760 names, 1,571 dates | label only |
| Stale terminal closes | forward-filled, undisclosed count | 23 flagged at 60d (4/6/10 at 5/10/20d), excluded from clean | −0.06 pp on 60d mean |
| Unfillable next-open buys | counted | 13 flagged (`sim.fillable` buy); 0 opens at/below the ATR stop | included in the −0.06 pp |
| Unfillable exits | counted | 37 flagged at 60d (`sim.fillable` sell, includes stale) | included |
| Benchmark overnight leg on t+1 | included in B2, not in stock | removed from B2 | ≈+0.3 pp at every horizon, uniform across buckets |
| Independent month resampling | 90% CI, L=1 | circular block L=4 (primary), L=8, symbol cluster | 60d CI width unchanged within ±0.2 pp |
| Overlapping CIs read as "no difference" | descriptive | 44 joint-resampling contrasts, Holm + BH | nothing significant after adjustment |
| "Samples this tail randomly" | asserted | withdrawn | — |
| "No 2021–26 data is used" | absolute | softened: no 2021–26 *prices or outcomes* are used; cache, symbol map and CA factors are retrospective | invariance check not done |

## Tables (excess vs B2-net, %, net of 0.6% round trip; mean [90% block-bootstrap CI, L=4 months]; hit = share of observed outcomes > 0)

### Sample accounting (M11 signals)

| h | window in dev | entry unfillable | open ≤ stop | terminal close missing (stale) | exit unfillable (incl. stale) | clean | mean raw excess of excluded |
|---|---|---|---|---|---|---|---|
| 5 | 6691 | 13 | 0 | 4 | 36 | 6644 | −6.56% |
| 10 | 6680 | 13 | 0 | 6 | 33 | 6635 | −5.83% |
| 20 | 6609 | 13 | 0 | 10 | 25 | 6571 | +4.03% |
| 60 | 6460 | 13 | 0 | 23 | 37 | 6410 | +11.23% |

B2 overnight leg on day t+1 (dropped by the aligned benchmark): M11 +0.296%, rejected +0.279% (signals with 60d outcomes).

### M11 headline under each treatment

| h | treatment | n | mean% | CI block L=4 | CI block L=8 | CI symbol-cluster | median% | hit | mean ex top 5% |
|---|---|---|---|---|---|---|---|---|---|
| 5 | R1 raw (B2 incl. overnight) | 6691 | −0.95 | [−1.26,−0.65] | [−1.26,−0.65] | [−1.15,−0.74] | −1.59 | 39.2% | −1.98 |
| 5 | aligned B2 (all) | 6691 | −0.64 | [−0.92,−0.37] | [−0.92,−0.36] | [−0.85,−0.43] | −1.30 | 40.9% | −1.67 |
| 5 | aligned B2, clean | 6644 | −0.60 | [−0.87,−0.34] | [−0.87,−0.34] | [−0.81,−0.39] | −1.29 | 40.9% | −1.62 |
| 10 | R1 raw | 6680 | −0.54 | [−0.92,−0.17] | [−0.85,−0.25] | [−0.86,−0.21] | −1.74 | 41.5% | −1.97 |
| 10 | aligned B2 (all) | 6680 | −0.23 | [−0.60,+0.11] | [−0.53,+0.04] | [−0.56,+0.10] | −1.41 | 42.9% | −1.66 |
| 10 | aligned B2, clean | 6635 | −0.20 | [−0.53,+0.13] | [−0.48,+0.08] | [−0.51,+0.12] | −1.41 | 42.8% | −1.61 |
| 20 | R1 raw | 6609 | +0.24 | [−0.47,+0.95] | [−0.36,+0.87] | [−0.27,+0.74] | −1.65 | 44.0% | −1.89 |
| 20 | aligned B2 (all) | 6609 | +0.54 | [−0.15,+1.24] | [−0.03,+1.15] | [+0.04,+1.05] | −1.34 | 45.0% | −1.58 |
| 20 | aligned B2, clean | 6571 | +0.52 | [−0.15,+1.19] | [−0.04,+1.12] | [+0.04,+1.01] | −1.34 | 45.0% | −1.56 |
| 60 | R1 raw | 6460 | +4.05 | [+2.57,+5.46] | [+2.66,+5.34] | [+2.75,+5.39] | +0.36 | 50.7% | +0.00 |
| 60 | aligned B2 (all) | 6460 | +4.36 | [+2.87,+5.77] | [+2.96,+5.66] | [+3.07,+5.71] | +0.59 | 51.3% | +0.31 |
| 60 | aligned B2, clean | 6410 | +4.30 | [+2.84,+5.70] | [+2.88,+5.62] | [+3.03,+5.61] | +0.63 | 51.4% | +0.32 |

### Buckets — clean sample, aligned B2-net (full tables with 5/10/20/60d in `experiments/research/out_R1b/tables.md`)

Volume ratio (all breakouts; M11 = ≥1.5×), 60d: <1× +3.97 [+0.8,+7.6] (n 669); 1–1.25× +3.15 [+0.9,+5.2] (575); 1.25–1.5× +2.14 [+0.1,+4.1] (619); 1.5–2× +3.28 [+1.7,+5.0] (1,084); 2–3× +3.96 [+2.4,+5.5] (1,515); ≥3× +4.73 [+2.9,+6.5] (3,811). Not monotone; at 5d the <1.5× buckets are slightly less negative.

M11 vs rejected, 60d: M11 +4.30 [+2.8,+5.7] (6,410) vs rejected +3.11 [+1.0,+5.4] (1,863); difference +1.20 pp, p = 0.31.

Distance above the prior 52-week high (M11), 60d: 0–1% +3.57 [+2.1,+5.1] (1,848); 1–3% +4.42 [+2.8,+6.0] (2,364); 3–5% +6.04 [+4.0,+8.0] (1,101); >5% +3.56 [+1.1,+6.2] (1,097, hit 46%). The 3–5% bucket leads at every horizon (raw p 0.027–0.045) but not after adjustment.

First vs repeat (M11), 60d: A (prior M11 signal ≤63 sessions) first +3.44 [+2.4,+4.4] (1,637) vs repeat +4.60 [+2.8,+6.3] (4,773), p = 0.22; B (any close > hi252 ≤63 sessions) first +4.35 [+2.4,+6.3] (608) vs repeat +4.30 [+2.7,+5.9] (5,802), p = 0.97.

By year (M11, 60d, clean, aligned): 2013 +8.97 [+4.4,+11.1] hit 61%; 2014 +4.51 [−2.4,+7.8] 53%; 2015 +1.48 [−2.2,+4.1] 43%; 2016 +1.82 [−5.4,+4.9] 47%; 2017 +4.99 [−0.4,+8.0] 49%; 2018 +0.71 [−0.7,+2.2] 53%; 2019 +5.07 [+2.0,+7.3] 58%; 2020 +6.40 [+2.1,+10.1] 51%. All eight means are positive; only 2013, 2019 and 2020 have intervals excluding zero (8 more comparisons, not adjusted).

### Contrasts — 44 tests, difference of means, joint block resampling, Holm across all

| family | contrast | h | diff pp | 90% CI | p | p Holm | q BH | p (L=8) |
|---|---|---|---|---|---|---|---|---|
| distance | 3–5% − 0–1% | 20 | +1.65 | [+0.37,+2.85] | 0.027 | 1.000 | 0.332 | 0.025 |
| distance | 3–5% − 0–1% | 10 | +0.94 | [+0.17,+1.68] | 0.038 | 1.000 | 0.332 | 0.027 |
| repeat A | repeat − first | 10 | +0.54 | [+0.10,+0.97] | 0.042 | 1.000 | 0.332 | 0.028 |
| volume | 1.25–1.5× − ≥3× | 60 | −2.59 | [−4.61,−0.36] | 0.043 | 1.000 | 0.332 | 0.030 |
| distance | 3–5% − 0–1% | 5 | +0.49 | [+0.10,+0.90] | 0.044 | 1.000 | 0.332 | 0.035 |
| distance | 3–5% − 0–1% | 60 | +2.47 | [+0.46,+4.46] | 0.045 | 1.000 | 0.332 | 0.047 |
| M11 vs rejected | M11 − rejected | 60 | +1.20 | [−0.87,+3.05] | 0.311 | 1.000 | 0.646 | 0.316 |
| M11 vs rejected | M11 − rejected | 5 | −0.27 | [−0.66,+0.09] | 0.247 | 1.000 | 0.604 | 0.281 |

The remaining 36 contrasts have raw p ≥ 0.069; the full list is in `experiments/research/out_R1b/contrasts.csv`. With 44 tests, about 2 raw p < 0.05 are expected under the null; 6 were observed, 4 of them the same 3–5% distance bucket at four overlapping horizons (one effect counted four times).

## Reading (facts, not recommendations)
- **Robustness of R1's main number:** the 60d mean moves from +4.05% to +4.30% after the fixes; all three bootstrap schemes put the 90% interval at roughly +2.8 to +5.7. The mean without the top 5% of signals is +0.32%; the median is +0.63%. The right-tail description stands.
- **Hit rates:** M11 is a coin flip at 60d (51%) and below 50% at 5–20d; the R1 statement that 2020 had a 38% hit rate was an artefact of counting missing outcomes as losses.
- **Execution realism:** the 13 entries that `sim.fillable` would reject plus the 23 stale terminal marks (36 signals) carried a mean raw 60d excess of +9.92%; all 50 exclusions including unfillable exits average +11.23%. They are 0.8% of the sample and shift the mean by 0.06 pp. Excluding by terminal availability conditions on the future (see Codex review); the unconditional figures are the "aligned B2 (all)" rows.
- **Benchmark alignment:** the overnight leg was worth ≈0.3 pp against M11 at every horizon and did not differ materially between M11 and rejected signals (0.296% vs 0.279%).
- **Bucket cuts:** after Holm, no volume, distance or first/repeat difference is distinguishable from zero. The 3–5% distance bucket is the only cut that is consistently ahead across horizons; with four overlapping horizons and ad-hoc edges it is a candidate for a pre-registered check, not a finding.

## Not done / open
- Truncated-source invariance check (rebuild panels from data ending 2020-12-31 and confirm identical dev signals): not done; `pit_panels.build()` has no end-date parameter and the frozen file must not be modified. It would need a research-side copy of the loader.
- Issuer/episode-level clustering beyond symbol: not done (symbol cluster only).
- Book-level attribution: out of scope; needs sim trade logs.
- Volume bucket rows in `out_R1b/tables.md` are string-sorted ("<1" prints after "2-3"); cosmetic.
- No 2021–26 prices or outcomes are used.

## Codex review (2026-10-09, gpt-6-astra, read-only)

Codex confirmed the headline means, counts and the 44 Holm-adjusted tests from the saved CSVs, and that all outcome windows stop at 2020. **REVIEW ISSUES:**
- **2021–26 claim too strong:** `pit_panels.py` picks corporate-action factors using later prices (retrospective adjustment). Not shown to leak into scale-invariant signals, but "no 2021–26 prices used" needs the truncated-source invariance check, which was not run. *Left open (R-level follow-up: research-side loader with an end date).*
- **Future-conditioned clean sample:** excluding signals by terminal availability/fillability conditions on the future. Valid as a sensitivity analysis, not as an executable-return correction; failed exits need retention with an explicit valuation policy. *Accepted; the text now points to the unconditional "aligned B2 (all)" rows as the primary figures, and the clean rows as sensitivity. Effect size 0.06 pp.*
- **Repeat-A boundary:** the reused R1 builder starts its M11 memory empty in January 2013, so early-2013 signals are labelled "first" by construction. *Left open; affects the repeat-A split only (not the headline).*
- **Reporting errors:** the missing-only correction of R1's hit rate is 50.7%, not 51.4% (which also changes benchmark and sample); the entry-unfillable-or-stale subset is 36 signals at +9.92%, while 50 / +11.23% covers all exclusions. *Fixed in the text above (verified from `out_R1b/breakouts_dev_flags.csv`).*
- **Inference wording:** separate symbol and time bootstraps do not jointly handle both dependencies; Holm covers the 44 chosen reference contrasts, not every pairwise difference; non-rejection is not equivalence. *Accepted as stated; no sentence here claims equivalence.*

Final line from Codex: `REVIEW ISSUES: unverified retrospective-data invariance; future-conditioned clean sample; repeat-history truncation; reporting errors; inference overstatement.`
