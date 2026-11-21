"""Build Sheets requests from sealed evidence and fresh remote readback. No network writes."""
import argparse
import json
from datetime import datetime
from seal_evening_snapshot import ROOT, R, TZ, read, rows, sha, validate, registry

CONFIG = R / 'config/sheet_publication.json'


def build(remote):
    config = read(CONFIG)
    assert set(config['tabs']) <= set(remote), 'Fresh complete readback required for all five managed tabs'
    source = ROOT / read(R / 'state/stock_report/latest.json')['report_dir']
    validate(source)
    hand = read(source / 'handoff.json')
    stocks = rows(source / 'stocks.jsonl')
    tasks, current, history = {}, [], []
    slots = read(R / 'state/orchestrator/completed_slots.json')
    for slot, batch in sorted(slots.items()):
        for name in batch['runs']:
            p = ROOT / name
            validate(p)
            h = read(p / 'handoff.json')
            key = h['batch_id'] + '/' + h['routine_id'] + '/' + h['run_id']
            history.append([key, h['scheduled_slot'], h['completed_at'], h['routine_id'], h['execution_lane'],
                h['owner'], h['executor'], h['status'], h['result'], h['review_status'], h['session_date'],
                h['deadline_missed'], h['budget_usage'].get('paid_cli_calls', 0), len(h['open_tasks']),
                '; '.join(h['limitations'])])
    for n in range(1, 6):
        p = ROOT / read(R / f'state/routine_0{n}/latest.json')['run_dir']
        validate(p)
        h = read(p / 'handoff.json')
        current.append([h['routine_id'], h['status'], h['owner'], h['completed_at'],
                        h['limitations'][0], h['review_status']])
        for task in h['open_tasks']:
            tasks[task['task_id']] = task
    stock_rows = []
    fresh_metrics = {m['symbol']: m for m in rows(source / 'metrics.jsonl')} if (source / 'metrics.jsonl').exists() else {}
    registry_dir, _ = registry(ROOT / read(R / 'state/routine_04/latest.json')['run_dir'])
    evidence_urls = {e['evidence_id']: e.get('original_url') or e.get('source_url')
                     for e in rows(registry_dir / 'evidence.jsonl')}
    for s in stocks:
        m = s.get('current_stats') or {}
        events = s.get('new_events', [])
        older = s.get('company_events', [])
        reason = [e.get('fact', '') for e in events] + [' '.join(e.get('facts', [])) for e in older]
        if s.get('technical'):
            reason += [', '.join(s['technical'].get('events', [])) + ' (technical source ' + s['technical'].get('session', '') + ')']
        if fresh_metrics.get(s['symbol'], {}).get('events') and (s.get('technical') or {}).get('session') != hand['market_asof']:
            reason += [', '.join(fresh_metrics[s['symbol']]['events']) + ' (diagnostic ' + hand['market_asof'] + ')']
        verification = sorted({e.get('verification_status', 'UNVERIFIED') for e in events + older})
        urls = sorted({e['source_url'] for e in events if e.get('source_url')})
        urls = sorted(set(urls) | {evidence_urls[e['event_id'].replace('news-', 'evidence-', 1)]
            for e in older if evidence_urls.get(e['event_id'].replace('news-', 'evidence-', 1))})
        dates = sorted({e.get('published_at', e.get('published_date', 'UNKNOWN')) for e in events + older})
        stock_rows.append([s['symbol'], m.get('session', hand['market_asof']), m.get('close_inr'),
            m.get('nominal_daily_return_pct'), m.get('nominal_return_since_oct9_pct'),
            m.get('volume_ratio_prior20'), '; '.join(reason) or 'Retained research lead; reverify prior evidence',
            '; '.join(dates), '; '.join(verification) or 'DIAGNOSTIC_ONLY',
            s.get('next_check', ''), s.get('owner', 'Codex verification; Claude research'), 'UNQUALIFIED',
            hand['cutoff_at'], '; '.join(urls), source.name,
            'Nominal prices; identity/action/calendar gates uncertified. ' + ('Claude provisional dossier recorded; valuation/cash-flow/economic challenge incomplete.' if s.get('dossier_status') else 'Claude company dossier pending.'),
            hand['compiled_at']])
    now = datetime.now(TZ).isoformat()
    dashboard = [['Item', 'Status / value', 'Owner', 'As of / last checked IST', 'Next check / limitation', 'Review'],
        ['Overall', 'PARTIAL', 'Codex persistence; Claude analysis', now, 'No new data implied by sheet publication', 'PENDING'],
        ['Stock leads', len(stocks), 'Codex', hand['compiled_at'], 'All unqualified research leads', 'PENDING'],
        ['Market observations', hand['market_asof'], 'Codex', hand['cutoff_at'], 'Historical snapshot; not live prices', 'DIAGNOSTIC'],
        ['Pending tasks', sum(t['status'] not in ['DONE','CANCELLED'] for t in tasks.values()), 'Assigned per task', now, 'See Research Tasks; resolved tasks remain dated records', ''], *current,
        ['READ FIRST', 'Research Stocks', '', '', 'Named stocks, facts, dates and next checks', ''],
        ['History', 'Routine Runs and Research Briefs', '', '', 'Append-only IDs; retries do not duplicate rows', ''],
        ['Ownership', 'Codex verifies/publishes; Claude interprets/drafts', '', '', 'Recorded authorship is required; never infer a review', ''],
        ['Time convention', 'ISO timestamps explicitly carry +05:30', '', '', 'Workbook timezone is unchanged; timestamps are stored as text', ''],
        ['Edit policy', 'Research tabs are automation-managed', '', '', 'Use existing Watchlist for your manual list; research tabs may be refreshed', ''],
        ['Storage', 'Sheet is the reader-facing report', '', '', 'Local sealed evidence/checkpoints remain for continuity and verification', '']]
    # Do not duplicate a stale authentication observation as a fresh check.
    readiness = read(ROOT / read(R / 'state/routine_05/latest.json')['run_dir'] / 'readiness.json')
    auth = readiness.get('claude', {})
    dashboard.insert(5, ['Claude access', auth.get('status', 'UNKNOWN'), 'Codex', auth.get('checked_at', ''),
        'Authentication alone does not enable research dispatch', ''])
    dashboard.insert(6, ['Budget controls', 'BLOCKED' if not readiness.get('budget_accounting_available') else 'AVAILABLE',
        'Codex', '', 'Durable reservation/reconciliation required before model calls', ''])
    tables = {
        'Research Dashboard': dashboard,
        'Research Stocks': [['Symbol', 'Market date', 'Close INR', 'Daily change %', 'Since 9 Oct %', 'Volume / prior20',
            'Selection / event facts', 'Publication date/time', 'Verification', 'Next check', 'Owner', 'Qualification',
            'Evidence cutoff IST', 'Source URLs', 'Snapshot ID', 'Verification gaps', 'Compiled at IST'], *stock_rows],
        'Routine Runs': [['Run ID', 'Scheduled slot IST', 'Completed at IST', 'Routine', 'Lane', 'Owner', 'Executor',
            'Status', 'Result', 'Review', 'Market date', 'Deadline missed', 'Model calls', 'Open tasks', 'Limitations'], *history],
        'Research Tasks': [['Task ID', 'Owner', 'Priority', 'Status', 'Security ID', 'Task / next check', 'Due / trigger',
            'Blocker', 'Evidence references', 'Created run'], *[[t['task_id'], t['owner'], t['priority'], t['status'],
            t.get('security_id'), t['description'], t.get('due_at') or t.get('trigger'), t.get('blocking_reason'),
            '; '.join(t.get('evidence_refs', [])), t['created_run_id']] for t in sorted(tasks.values(), key=lambda t: (t['priority'], t['task_id']))]],
        'Research Briefs': [['Report ID', 'Compiled at IST', 'Market date', 'Evidence cutoff IST', 'Status', 'Stock count',
            'Author', 'Claude review', 'Final report text'],
            [source.name, hand['compiled_at'], hand['market_asof'], hand.get('cutoff_at', ''), hand['status'], len(stocks),
             hand['executor'], 'NOT_EXECUTED' if not hand.get('claude_interpretation_executed') else 'SEE_HANDOFF',
             (source / 'report.md').read_text()]]}
    requests = []
    for title, values in tables.items():
        old = remote.get(title, [])
        if old:
            assert old[0] == values[0], f'{title}: headers changed; stop rather than overwrite'
        if title in ['Routine Runs', 'Research Briefs']:
            seen = {str(r[0]) for r in old[1:] if r}
            values = old + [r for r in values[1:] if str(r[0]) not in seen] if old else values
        width = len(values[0])
        length = max(len(values), len(old))
        padded = [r + [''] * (width - len(r)) for r in values] + [[''] * width for _ in range(length - len(values))]
        sheet_id = config['tabs'][title]
        if length > 1000:
            requests.append({'updateSheetProperties': {'properties': {'sheetId': sheet_id,
                'gridProperties': {'rowCount': length + 100}}, 'fields': 'gridProperties.rowCount'}})
        cells = []
        for row in padded:
            cells.append({'values': [{'userEnteredValue': {'boolValue': v} if isinstance(v, bool) else
                {'numberValue': v} if isinstance(v, (int, float)) else {'stringValue': '' if v is None else str(v)}} for v in row]})
        if title == 'Research Tasks':
            requests.append({'setDataValidation': {'range': {'sheetId': sheet_id, 'startRowIndex': 1,
                'endRowIndex': length, 'startColumnIndex': 3, 'endColumnIndex': 4},
                'rule': {'condition': {'type': 'ONE_OF_LIST', 'values': [{'userEnteredValue': s} for s in ['OPEN','BLOCKED','DONE','CANCELLED']]},
                         'strict': True, 'showCustomUi': True}}})
        requests.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': length,
            'startColumnIndex': 0, 'endColumnIndex': width}, 'rows': cells, 'fields': 'userEnteredValue'}})
        if title != 'Research Dashboard':
            requests.append({'setBasicFilter': {'filter': {'range': {'sheetId': sheet_id,
                'startRowIndex': 0, 'endRowIndex': len(values), 'startColumnIndex': 0, 'endColumnIndex': width}}}})
        requests.append({'repeatCell': {'range': {'sheetId': sheet_id, 'startRowIndex': 1,
            'endRowIndex': len(values), 'startColumnIndex': 0, 'endColumnIndex': width},
            'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP', 'verticalAlignment': 'TOP'}},
            'fields': 'userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment'}})
    return {'spreadsheet_id': config['spreadsheet_id'], 'link_id': config['link_id'],
            'requests': requests, 'table_counts': {k: len(v) - 1 for k, v in tables.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--remote-json', required=True, help='Fresh connector readback: tab title -> values; entire history required')
    args = parser.parse_args()
    print(json.dumps(build(read(ROOT / args.remote_json)), ensure_ascii=False, allow_nan=False))
