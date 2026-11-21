# Runnable research overlay

Entry point: `pipeline.py --session AUTO --slot <ISO IST> --lane FAST|OVERNIGHT --collect --run-claude`.
Manual repair/research passes can omit slot and use EVENT. A completed slot is
idempotent. All files belong under research; frozen code, paper books and the
owner's separate watchlist are read-only.

Modules: budget.py reserves requests/tokens/cost/storage transactionally;
sources.py caches hash-pinned allowlisted public inputs; claude_worker.py checks
auth, reserves before dispatch, disables tools/customizations and records actual
usage; pipeline.py validates data, screens quarterly filings, maintains provisional
company/monitor records and seals five routine handoffs. build_stock_report.py
preserves the newest pipeline report; build_sheet_publication.py prepares exact
managed-tab requests from fresh remote readback. The connector performs and
verifies the actual Google Sheet write.

Run `.venv/bin/python -m unittest discover -s research/runtime -p test_runtime.py -v`.

The first real run verified 14 October EOD against two official files and current
ISINs, identified 23 results-led candidates, and produced three provisional
Claude dossiers from visually verified MRPL/CEAT/ICICI Lombard quarterly tables.
Numerical parsing across all companies is not claimed complete. Unverified OCR
and metadata are discovery evidence only; source and financial gates remain open.

Operational review: the initial Claude test produced 6903 aggregate output
tokens against a 4000 reservation. Its output was rejected and reported cost
reconciled with a retained incident. Shortened one-turn calls then returned
1640 and a second below-4000 output. Budget enforcement fails closed on unknown
usage or overrun; do not describe the failed output as compliant or approved.

Manual table verification is hash-bound in verified_fundamentals.json. A new PDF
does not inherit old verification. The generic collector stages new originals,
but their numerical table mapping needs independent validation before a financial
gate can pass. Historical identity/calendar/entitlement certification remains a
separate Phase 0 project. All present candidates are unqualified research.

Official references: [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing),
[CLI controls](https://code.claude.com/docs/en/cli-reference),
[NSE financial filings](https://www.nseindia.com/companies-listing/corporate-filings-financial-results).
