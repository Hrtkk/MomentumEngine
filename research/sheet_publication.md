# Google Sheet report structure and publication

Destination: https://docs.google.com/spreadsheets/d/1uMgZd9anGrXOOleQlqwEHVT6zAXezsTBJxf9PnXTWK8/edit

Authorized by the owner on 14 October 2026. Read `config/sheet_publication.json`
for the exact connector account and tab IDs. These five tabs are automation-managed;
human edits in them may be replaced by the next verified publication. Keep the
existing Watchlist for the owner's manual list. Never mutate the three original
portfolio tabs, sharing settings, or workbook timezone from this pipeline.

## Read order and columns

1. **Research Dashboard**: current status/value, owner, actual last-check timestamp,
   limitation/next check, review availability. Shows overall stage health,
   market/evidence dates, stock and task counts, Claude auth and budget controls.
2. **Research Stocks**: symbol; market date; close INR; daily nominal change %;
   since 9 October %; volume/prior20; selection/event facts; publication date/time;
   verification; next check; owner; qualification; evidence cutoff IST; source URLs;
   snapshot ID; verification gaps; compiled timestamp. The since-9-October baseline
   remains fixed and explicit until a versioned schema changes it. No buy/sell/hold
   recommendations or automatic watchlist qualification.
3. **Routine Runs**: unique run ID; intended slot and actual completion IST;
   routine; execution lane; accountable owner; actual executor; status; result;
   review; market date; deadline missed; model calls; open tasks; limitations.
4. **Research Tasks**: stable task ID; owner; priority; status; security ID;
   requested check; due/trigger; blocker; evidence references; creation run.
5. **Research Briefs**: immutable report ID; compilation IST; market date;
   evidence cutoff; status; stock count; author; actual Claude review availability;
   full final report text. The complete text is also readable in the formula bar.

Dates/timestamps are literal ISO strings with timezone offsets: the workbook's
existing America/Los_Angeles timezone is deliberately not altered. Numeric return
columns contain percentage points (8.42 means 8.42%, not 842%). Returns are nominal,
not entitlement-aware total returns. A publication time is not a source timestamp.

## Scheduled writer protocol — Codex

1. Seal the applicable local routine handoffs under the orchestrator lock. At
   morning/evening assembly run `build_stock_report.py`; retain old dates if it
   reuses the same evidence. No paid research is needed for factual publication.
2. Read fresh spreadsheet metadata through the configured Google Drive connector.
   Verify the five exact titles and IDs and current row counts. Stop on conflicts.
3. Read bounded cells/values from each managed tab through the connector; inspect
   headers and validation before writing. Start with the populated ranges, using
   full column widths A:F, A:Q, A:O, A:J and A:I respectively. For history tabs,
   page all populated rows in blocks of at most 1000; never pass a partial history
   as the whole table. Metadata grid bounds and blank sentinel rows help locate
   the end. Preserve all remote historical rows, including older report snapshots
   not selected by the current local pointer. No whole-workbook reads needed.
4. Save the complete remote values as a temporary JSON mapping of tab title to
   row arrays, with raw numbers/booleans from UNFORMATTED_VALUE. Empty tabs map to
   `[]`; absence of a history tab from the mapping is not permission to clear it.
5. Build the deterministic request payload:
   `.venv/bin/python research/runtime/build_sheet_publication.py --remote-json <temporary-path>`.
   Validate the payload's exact spreadsheet/account and managed sheet IDs. Use
   the connected `batch_update_spreadsheet` tool to apply its structured requests.
   Split into coherent per-tab batches if tool payload limits require it. Do not
   print secrets or invoke unrelated services. Keep one writer throughout remote
   read, preparation, write and receipt persistence; use bounded calls/deadlines.
6. Re-read the authored ranges, verify counts, IDs, evidence dates, stock rows,
   status/owner fields and report text. Retain gray headers, frozen first rows,
   wrapped text, readable widths and filters. Format only managed populated ranges.
7. Persist a local publication receipt containing spreadsheet ID, exact source
   manifest hashes, affected tabs, remote counts, verified timestamp and state.
   Success requires readback. A retry first reads remote history and IDs, so a
   completed-but-timed-out write cannot duplicate records. Do not mark an incomplete
   five-tab publication SENT; keep PARTIAL/UNKNOWN and retry missing partitions.

Routine-run key is batch/routine/run; final-report key is immutable snapshot ID.
Unchanged source reports do not create new brief entries. Each actual routine run
may add history while latest stock prices remain explicitly historical. A source
or Claude outage still publishes PARTIAL/BLOCKED facts and owner tasks. Sheet
publication failure does not change research qualification or erase local evidence.

The schedule stays weekday 10:00, 21:00 and 23:00 IST. This enables report publication,
not cloud hosting, external messages, changed paper books, or more model spending.
