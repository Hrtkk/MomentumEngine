"""Seal available factual evidence and unfinished owner tasks; no paid calls or fetches."""
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'research'
TZ = ZoneInfo('Asia/Kolkata')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def write(p, value):
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def atomic(p, value):
    tmp = p.with_name(p.name + '.tmp')
    write(tmp, value)
    os.replace(tmp, p)


def rows(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def validate(p):
    m = read(p / 'manifest.json')
    assert m['committed']
    for a in m['artifacts']:
        assert sha(p / a['path']) == a['sha256'], str(p / a['path'])
    return {'run_dir': str(p.relative_to(ROOT)), 'manifest_sha256': sha(p / 'manifest.json')}


def registry(p, seen=None):
    seen = set() if seen is None else seen
    assert p not in seen, 'Registry reference cycle'
    seen.add(p)
    validate(p)
    if (p / 'event_registry.jsonl').exists():
        return p, rows(p / 'event_registry.jsonl')
    ref = read(p / 'registry_ref.json')['immutable_registry_run']
    parent = ROOT / ref.get('path', ref.get('run_dir'))
    assert sha(parent / 'manifest.json') == ref['manifest_sha256']
    base, records = registry(parent, seen)
    delta = rows(p / 'events.jsonl') if (p / 'events.jsonl').exists() else []
    merged = {r['event_id']: r for r in records}
    merged.update({r['event_id']: r for r in delta})
    return base, list(merged.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    parser.add_argument('--auth-evidence', help='Fresh read-only normal-context authentication observation')
    args = parser.parse_args()
    date = datetime.fromisoformat(args.date).date().isoformat()
    slot = date + 'T21:00:00+05:30'
    deadline = date + 'T21:30:00+05:30'
    batch = date + '_evening_snapshot_v01'
    state = R / 'state/orchestrator'
    started = datetime.now(TZ).isoformat()
    with (state / 'writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        completed = read(state / 'completed_slots.json')
        if slot in completed:
            for name in completed[slot]['runs']:
                validate(ROOT / name)
            print(json.dumps({'reused': True, 'batch_id': completed[slot]['batch_id']}))
            return
        source = ROOT / read(R / 'state/stock_report/latest.json')['report_dir']
        stock_ref = validate(source)
        stocks = rows(source / 'stocks.jsonl')
        stock_h = read(source / 'handoff.json')
        assert stock_h['compiled_at'] <= slot
        assert stock_h['cutoff_at'] <= slot
        stats = read(source / 'stats.json')
        upstream, tasks, prior = [], {}, {}
        for n in range(1, 6):
            p = ROOT / read(R / f'state/routine_0{n}/latest.json')['run_dir']
            ref = validate(p)
            upstream.append(ref)
            prior[n] = p
            for t in read(p / 'handoff.json').get('open_tasks', []):
                if t['status'] not in ['DONE', 'CANCELLED']:
                    tasks[t['task_id']] = t
        base_registry, events = registry(prior[4])
        news_updates = rows(source / 'news_updates.jsonl')
        pinned = {}
        for p in [ROOT / 'CLAUDE.md', ROOT / 'ROADMAP.md', R / 'operating_schedule.md',
                  *sorted(R.glob('0*_plan.md')), ROOT / 'live/ledgers/registration.json']:
            pinned[str(p.relative_to(ROOT))] = sha(p)
        checks = []
        reg = read(ROOT / 'live/ledgers/registration.json')
        for name, expected in reg['code_sha256'].items():
            p = ROOT / 'experiments' / name
            pinned[str(p.relative_to(ROOT))] = sha(p)
            checks.append({'path': str(p.relative_to(ROOT)), 'matches': sha(p).startswith(expected)})
        assert all(c['matches'] for c in checks), 'Registered source mismatch requires an integrity incident'
        positions = []
        for book in ['M11', 'M10', 'M2']:
            candidates = [(read(p).get('signal_date', ''), p) for p in (ROOT / 'live/ledgers' / book).glob('snapshot_*.json')]
            asof, p = max(candidates)
            pinned[str(p.relative_to(ROOT))] = sha(p)
            positions.extend({'portfolio': book, 'symbol': s, 'asof': asof, 'exposure_scope': 'PAPER',
                              'thesis_status': 'THESIS_NOT_DOCUMENTED', 'evaluation_status': 'NOT_EVALUATED',
                              'comparison_available': False} for s in read(p)['positions'])
        c0 = ROOT / 'ledgers/state.json'
        pinned[str(c0.relative_to(ROOT))] = sha(c0)
        try:
            probe = subprocess.run(['/opt/homebrew/bin/claude', 'auth', 'status'], capture_output=True, text=True, timeout=10)
            auth = json.loads(probe.stdout)
        except (subprocess.TimeoutExpired, ValueError):
            auth = {}
        auth_state = {'status': 'AUTHENTICATED' if auth.get('loggedIn') else 'AUTH_CONTEXT_UNAVAILABLE',
                      'logged_in_in_current_context': auth.get('loggedIn'), 'checked_at': datetime.now(TZ).isoformat(),
                      'inference': 'No claim of human logout; normal context access previously verified'}
        if args.auth_evidence:
            auth_path = ROOT / args.auth_evidence
            observation = read(auth_path)
            age = datetime.now(TZ) - datetime.fromisoformat(observation['checked_at'])
            assert timedelta(0) <= age < timedelta(minutes=15), 'Normal-context auth observation expired'
            auth_state = {**observation, 'sandbox_context_status': auth_state['status']}
            pinned[str(auth_path.relative_to(ROOT))] = sha(auth_path)
        for row in stocks:
            if row.get('new_to_report'):
                tid = 'verify-cutoff-2026-10-13-' + row['symbol']
                tasks.setdefault(tid, {'task_id': tid, 'owner': 'Codex', 'security_id': row.get('security_id'),
                    'description': row['next_check'], 'priority': 'P2', 'status': 'OPEN',
                    'created_run_id': batch, 'due_at': None, 'trigger': 'next eligible source verification pass',
                    'blocking_reason': 'Dated primary context/identity controls require verification',
                    'evidence_refs': [str(source.relative_to(ROOT) / 'stocks.jsonl')]})
        task_rows = sorted(tasks.values(), key=lambda t: (t['priority'], t['task_id']))
        readiness = {'scheduled_slot': slot, 'deadline_at': deadline, 'claude': auth_state,
            'budget_accounting_available': False, 'phase0_certified': False, 'calendar_certified': False,
            'current_eod_batch_present': (ROOT / f'live/ledgers/evening_{date}.json').exists(),
            'current_raw_bhavcopy_present': (ROOT / f'data/raw/bhav/{date}.csv').exists(),
            'available_official_observation_session': stock_h['market_asof'],
            'stock_evidence_cutoff': stock_h['cutoff_at'], 'stock_report_ref': stock_ref,
            'full_registry_ref': validate(base_registry), 'full_registry_records': len(events),
            'additional_news_records': len(news_updates), 'new_fetches': 0, 'paid_cli_calls': 0,
            'registration_checks': checks, 'paper_positions_inventoried': len(positions),
            'latest_paper_session': max(p['asof'] for p in positions), 'c0_asof': read(c0).get('last_t'),
            'c0_evaluation_status': 'NOT_EVALUATED', 'actual_exposure_known': False}
        market_asof = stock_h['market_asof']
        market_gap = market_asof != date or not readiness['current_eod_batch_present']
        stages = {1: ('PARTIAL', f'Existing {market_asof} diagnostic reused; {date} production scan NOT_EVALUATED'),
                  2: ('PARTIAL', f'{len(stocks)} factual leads carried into a deferred queue; no qualified transitions or fundamental screen'),
                  3: ('BLOCKED', 'Paper inventory/hash checks only; thesis comparisons NOT_EVALUATED'),
                  4: ('PARTIAL', 'Full prior registry and cutoff updates pinned; no fresh ingestion or Claude significance pass'),
                  5: ('PARTIAL', 'Codex factual assembly; Claude editorial drafting remains BLOCKED')}
        runs = []
        for n in range(1, 6):
            run_id = f'routine_0{n}_a01'
            target = R / 'runs' / batch / f'routine_0{n}' / run_id
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.exists(), 'Existing unpublished revision requires reconciliation'
            tmp = Path(tempfile.mkdtemp(prefix='.pending_', dir=target.parent))
            write(tmp / 'readiness.json', readiness)
            (tmp / 'open_tasks.jsonl').write_text(''.join(json.dumps(t) + '\n' for t in task_rows))
            write(tmp / 'stock_report_ref.json', stock_ref)
            if n == 1:
                write(tmp / 'diagnostic_ref.json', {**stock_ref, 'metrics': 'metrics.jsonl', 'signals': 'signals.jsonl',
                    'evaluated': stats['technical_evaluated'], 'quarantined': stats['quarantined'], 'fresh_scan_executed': False})
                (tmp / 'signals.jsonl').write_text('')
            if n == 2:
                write(tmp / 'intake_queue.json', {'report_ref': stock_ref, 'leads': stocks,
                    'admitted_candidates': [], 'deferred_count': len(stocks), 'qualification_executed': False,
                    'claude_owned_work_status': 'BLOCKED', 'reason': 'identity/readiness/budget/review gates absent'})
                (tmp / 'transitions.jsonl').write_text('')
            if n == 3:
                (tmp / 'monitor_state.jsonl').write_text(''.join(json.dumps(p) + '\n' for p in positions))
                (tmp / 'changes.jsonl').write_text('')
                (tmp / 'transition_proposals.jsonl').write_text('')
            if n == 4:
                write(tmp / 'registry_ref.json', {'immutable_registry_run': validate(prior[4]),
                    'record_count': len(events), 'new_event_count': 0, 'newness_evaluated': False,
                    'additional_cutoff_packet': {**stock_ref, 'payload': 'news_updates.jsonl', 'records': len(news_updates)}})
                (tmp / 'events.jsonl').write_text('')
                write(tmp / 'source_health.json', {'fresh_sources_evaluated': 0, 'source_cursors_advanced': False,
                    'claude_significance_status': 'BLOCKED', 'reason': 'budget/source adapters unavailable'})
            if n == 5:
                write(tmp / 'digest.json', {'status': 'PARTIAL', 'report_ref': stock_ref, 'items': stocks,
                    'stock_count': len(stocks), 'evidence_changed_since_last_compilation': False,
                    'editorial_executed': False, 'claude_owned_work_status': 'BLOCKED',
                    'executor': 'Codex deterministic factual assembly'})
                (tmp / 'decision_queue.jsonl').write_text(''.join(json.dumps(t) + '\n' for t in task_rows))
                write(tmp / 'notification_state.json', {'external_delivery': 'NOT_SENT',
                    'duplicate_stock_report_suppressed': True, 'unchanged_blockers_suppressed': True})
            body = [f'# Evening research assembly — {date} — {stages[n][0]}', '',
                f'Scheduled: {slot}; started: {started}; deadline: {deadline}. Routine R{n}.', '',
                'Codex compiled factual evidence only. Claude significance, dossiers, thesis interpretation and editorial work remain BLOCKED; no Claude review is claimed.', '',
                f'[{len(stocks)} named stock leads]({source / "report.md"}) retain the **{stock_h["cutoff_at"]} evidence cutoff** and **{market_asof} closing observations**. The source report documents retrieval after its cutoff; this is retrospective evidence. This assembly adds no fresh market/news observation.', '',
                f'Current {date} required EOD batch present: {readiness["current_eod_batch_present"]}; required raw bhavcopy present: {readiness["current_raw_bhavcopy_present"]}. Current-session evaluation gap: {market_gap}; current-session production price checks remain NOT_EVALUATED. A missing file is not proof of an exchange holiday.', '',
                f'| Stock | Close ₹ ({market_asof}) | Nominal daily change | Selection reason and next check |',
                '| --- | --- | --- | --- |']
            by_symbol = {s['symbol']: s for s in stocks}
            for symbol in ['HCLTECH', 'RBLBANK', 'LT']:
                row = by_symbol[symbol]
                metric = row['current_stats']
                event = row['new_events'][0]
                body.append(f'| {symbol} | {metric["close_inr"]:.2f} | {metric["nominal_daily_return_pct"]:+.2f}% | {event["published_at"]}: {event["fact"]} Verification: {event["verification_status"]}. Next: {row["next_check"]} Owner: Codex verification; Claude subsequent interpretation. |')
            body += ['', 'These items were already included in the 8 PM report. Prices are nominal and not entitlement-adjusted; no price move proves a causal thesis. All 35 records remain unqualified research leads.', '',
                f'Diagnostic coverage: {stats["technical_evaluated"]}/{stats["diagnostic_universe"]} evaluated; {stats["quarantined"]} quarantined. No fresh technical evaluation in this assembly. Full legacy registry: {len(events)} events plus {len(news_updates)} separately pinned cutoff updates; no source cursor advanced.', '',
                '| Routine | Status | Evaluated scope |', '| --- | --- | --- |']
            body += [f'| R{k} | {v[0]} | {v[1]} |' for k, v in stages.items()]
            body += ['', f'Paper inventory: {len(positions)} position records, dated {readiness["latest_paper_session"]}; zero thesis triggers evaluated. C0 remains NOT_EVALUATED. Frozen registered source hashes match: {all(c["matches"] for c in checks)}.', '',
                f'Unresolved tasks carried: {len(task_rows)}. Exact upstream manifests and input versions are in handoff.json. Claude auth in this context: {auth_state["status"]}; shared metered-call accounting is absent. No paid call or external fetch occurred.', '',
                f'Next slot: {date} 23:00 IST. Resume pinned evidence and owner queues; do not repeat the stock list as fresh news, substitute Claude work, or promote candidates before applicable gates pass.']
            (tmp / 'report.md').write_text('\n'.join(body) + '\n')
            artifacts = [{'path': p.name, 'sha256': sha(p)} for p in sorted(tmp.iterdir())]
            handoff = {'schema_version': '1.1', 'routine_id': f'routine_0{n}', 'batch_id': batch, 'run_id': run_id,
                'session_date': stock_h['market_asof'], 'started_at': started, 'completed_at': datetime.now(TZ).isoformat(),
                'scheduled_slot': slot, 'cutoff_at': slot, 'evidence_cutoff_at': stock_h['cutoff_at'], 'deadline_at': deadline,
                'deadline_missed': datetime.now(TZ) > datetime.fromisoformat(deadline), 'timezone': 'Asia/Kolkata',
                'status': stages[n][0], 'result': 'NOT_EVALUATED', 'execution_lane': 'FAST', 'production_eligible': False,
                'readiness_ref': 'readiness.json', 'budget_ref': None, 'budget_usage': {'paid_cli_calls': 0, 'external_requests': 0},
                'deferred_counts': {'research_leads': len(stocks), 'paper_thesis_checks': len(positions)},
                'owner': 'Claude' if n in [2, 4, 5] else 'Codex', 'executor': 'Codex factual assembly and continuation',
                'reviewer': 'Codex' if n in [2, 4, 5] else 'Claude', 'review_status': 'UNAVAILABLE',
                'previous_success_run_id': None, 'previous_committed_run': validate(prior[n]),
                'supersedes_run_id': None, 'bootstrap': False, 'upstream_runs': upstream + [stock_ref],
                'input_versions': pinned, 'config_version': 'evening-factual-snapshot-1',
                'code_revision': {'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                                  'script_sha256': sha(Path(__file__))},
                'coverage': {'factual_leads': len(stocks), 'thesis_evaluated': 0, 'fresh_news_evaluated': False},
                'freshness': {'market_asof': stock_h['market_asof'], 'paper_asof': readiness['latest_paper_session']},
                'limitations': [stages[n][1], 'No fresh ingestion; budget/readiness controls absent'],
                'artifacts': artifacts, 'source_cursors': {}, 'processed_event_ids': [], 'open_tasks': task_rows,
                'resolved_task_ids': [], 'next_run': {'slot': date + 'T23:00:00+05:30',
                    'instructions': 'Resume evidence refs, full registry and unresolved owners without duplicate notices.'}}
            write(tmp / 'handoff.json', handoff)
            write(tmp / 'manifest.json', {'schema_version': '1.1', 'committed': True, 'batch_id': batch,
                'run_id': run_id, 'artifacts': artifacts + [{'path': 'handoff.json', 'sha256': sha(tmp / 'handoff.json')}]})
            os.rename(tmp, target)
            validate(target)
            runs.append(str(target.relative_to(ROOT)))
        for n, name in enumerate(runs, 1):
            atomic(R / f'state/routine_0{n}/latest.json', {'run_dir': name, 'status': stages[n][0], 'production_eligible': False})
        completed[slot] = {'batch_id': batch, 'runs': runs}
        atomic(state / 'completed_slots.json', completed)
        atomic(state / f'batch_evening_{date}.json', {'batch_id': batch, 'scheduled_slot': slot,
            'runs': runs, 'stock_report_ref': stock_ref, 'status': 'PARTIAL'})
        print(json.dumps({'batch_id': batch, 'report': str(ROOT / runs[-1] / 'report.md'),
            'stocks': len(stocks), 'open_tasks': len(task_rows), 'new_observations': 0,
            'unchanged_stock_report_notification_suppressed': True, 'paid_calls': 0}))


if __name__ == '__main__':
    main()
