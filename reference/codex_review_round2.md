1. **Round-1 MUST items**, in original order:

| # | MUST | Assessment |
|---|---|---|
| 1 | Discovery universe | **Adopted correctly.** |
| 2 | History, membership, retention, survivorship | **Adopted correctly.** |
| 3 | Reconciliation and stale inputs | **Adopted correctly.** |
| 4 | Fully specified formulas | **Adopted incorrectly.** §4 leaves ATR smoothing/initialisation undefined; volume and breakout may receive a second percentile transformation; negative penalty values are then subtracted. Specify ATR calculation, use the composite percentiles directly, and store penalties as positive deductions. Require 252 **preceding** sessions for the breakout reference. |
| 5 | Percentiles and missing-factor conventions | **Adopted incorrectly.** Percentiles, clipping and essential-factor exclusion are present; exploratory close-quality formula and `H=L → 0.5` are missing. Add `(C−L)/(H−L)`, with that fallback. |
| 6 | Annotation neutrality | **Adopted correctly.** |
| 7 | Regime logged only | **Adopted correctly.** |
| 8 | Frozen quantities and next-open execution | **Adopted correctly.** Funding remains a separate blocker below. |
| 9 | Fixed stops | **Adopted incorrectly.** Distance rejection and locked-exit handling are present, but ordinary intraday stop fills are unspecified. State: `O≤S → fill O; otherwise L≤S → fill S`, subject to tradability. Reject `S≥C`; define entry-gap handling when the opening fill is already below the stop. |
| 10 | Primary endpoint and fixed cohorts | **Adopted correctly.** Cohort construction still needs the conventions below. |
| 11 | Matched benchmark | **Adopted incorrectly.** §8.2 fixes timestamps, but H1 still claims open-to-close benchmark excess. Dividend treatment remains unspecified. Rewrite H1 to the close-to-close panel and use matching price-return or total-return series, with explicit corporate-action treatment. |
| 12 | Review and validation schedule | **Adopted correctly.** |
| 13 | Uncertainty and prospective acceptance | **Adopted incorrectly.** “60…dates…confirming it” does not explicitly require the **prospective improvement’s own 95% interval above zero**. Require that before promotion; otherwise inconclusive. |

2. **Yes, I accept the compromise.** Keeping the watchlist, challenger replacement and paper portfolio is acceptable when §8 carries the evidence and the operating rules are deterministic. This acceptance is conditional on resolving the blockers.

3. **Additional blocking issues introduced or exposed by the revision:**

- **§§3–4: incumbent scoring.** Out-of-window holdings have no defined percentile mapping against candidates. **Fix:** compute reference percentiles on eligible candidates only; specify interpolation and endpoint clipping for incumbent raw values. Never add incumbents to the reference population implicitly.

- **§§6–8: selection and replacement rules.** MQS ties, final persistence ties, replacement eligibility, second-swap sequencing and undersized/empty cohorts are undefined. **Fix:** use symbol ascending as the final tie-break everywhere; require replacements to satisfy all add rules; repeat the replacement procedure sequentially against the updated roster. Define every comparator over the same eligible candidate set, use `min(10,n)`, and mark empty-cohort returns unavailable.

- **§7: funding and failed exits.** Ten quantities sized from yesterday’s closes can exceed available cash after opening gaps and costs. A locked incumbent can also remain held while its replacement is bought. **Fix:** explicitly permit and account for simulated borrowing, or specify cash-constrained execution with frozen quantities and deterministic priority. Reserve a slot until its exit fills; defer its replacement.

- **§§2, 8: unresolved outcomes.** Retaining a flagged row does not specify its contribution to cohort averages. **Fix:** freeze membership and weights at formation; never renormalise over available outcomes. Mark an aggregate unresolved while a constituent lacks its required endpoint, unless a registered terminal-value rule applies.

- **§§8–9: reproducible statistics.** “Seed = date” and “20-session blocks” do not uniquely define calculations. **Fix:** register the PRNG, date encoding, sampling without replacement within each draw, bootstrap variant, replicate count, seed and interval method. Define the primary change metric as the mean paired daily improvement.

- **Header/§14: premature agreement.** **Fix:** replace “agreed” and “all…adopted” with pending/partial status until these corrections are reviewed.

AGREE WITH CHANGES: complete formulas and stop rules; align H1 and dividend treatment; require prospective CI acceptance; specify incumbent scoring, selection, funding, unresolved outcomes and resampling; correct agreement status