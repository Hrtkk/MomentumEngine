"""Persist a blocked overnight backlog without substituting research ownership."""
import argparse
import fcntl
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from seal_evening_snapshot import ROOT, R, TZ, read, write, atomic, rows, sha, validate, registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    parser.add_argument('--auth-evidence', required=True)
    args = parser.parse_args()
    date = datetime.fromisoformat(args.date).date()
    slot = f'{date}T23:00:00+05:30'
    deadline = f'{date + timedelta(days=1)}T01:00:00+05:30'
    next_slot = f'{date + timedelta(days=1)}T10:00:00+05:30'
    batch = f'{date}_overnight_checkpoint_v01'
    started = datetime.now(TZ).isoformat()
    state = R / 'state/orchestrator'
    with (state / 'writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        completed = read(state / 'completed_slots.json')
        if slot in completed:
            for name in completed[slot]['runs']:
                validate(ROOT / name)
            print(json.dumps({'reused': True, 'batch_id': completed[slot]['batch_id']}))
            return
        auth_path = ROOT / args.auth_evidence
        auth = read(auth_path)
        assert timedelta(0) <= datetime.now(TZ) - datetime.fromisoformat(auth['checked_at']) < timedelta(minutes=15)
        upstream, prior, tasks = [], {}, {}
        for n in range(1, 6):
            prior[n] = ROOT / read(R / f'state/routine_0{n}/latest.json')['run_dir']
            upstream.append(validate(prior[n]))
            for task in read(prior[n] / 'handoff.json')['open_tasks']:
                if task['status'] not in ['DONE', 'CANCELLED']:
                    tasks[task['task_id']] = task
        source = ROOT / read(R / 'state/stock_report/latest.json')['report_dir']
        stock_ref = validate(source)
        stocks = rows(source / 'stocks.jsonl')
        stock_h = read(source / 'handoff.json')
        assert stock_h['compiled_at'] <= slot and stock_h['cutoff_at'] <= slot
        full_registry, events = registry(prior[4])
        updates = rows(source / 'news_updates.jsonl')
        previous_readiness = read(prior[5] / 'readiness.json')
        input_versions = dict(read(prior[5] / 'handoff.json')['input_versions'])
        for p in [ROOT / 'CLAUDE.md', ROOT / 'ROADMAP.md', R / 'operating_schedule.md', *sorted(R.glob('0*_plan.md'))]:
            input_versions[str(p.relative_to(ROOT))] = sha(p)
        input_versions[str(auth_path.relative_to(ROOT))] = sha(auth_path)
        checks = []
        for name, expected in read(ROOT / 'live/ledgers/registration.json')['code_sha256'].items():
            p = ROOT / 'experiments' / name
            checks.append({'path': str(p.relative_to(ROOT)), 'matches': sha(p).startswith(expected)})
            input_versions[str(p.relative_to(ROOT))] = sha(p)
        assert all(c['matches'] for c in checks), 'Registered source mismatch; incident required'
        queue = []
        for row in stocks:
            queue.append({'queue_id': 'research-' + row['symbol'], 'symbol': row['symbol'],
                'status': 'BLOCKED', 'dossier_owner': 'Claude', 'verification_owner': 'Codex',
                'reason': 'Budget accounting, certified inputs and dossier adapters unavailable',
                'question': row.get('next_check'), 'evidence_ref': stock_ref,
                'record': row, 'qualified': False, 'dispatch_reserved': False})
        task_rows = sorted(tasks.values(), key=lambda t: (t['priority'], t['task_id']))
        readiness = {**previous_readiness, 'scheduled_slot': slot, 'deadline_at': deadline,
            'claude': auth, 'registration_checks': checks, 'budget_accounting_available': False,
            'fundamental_screen_enabled': False, 'fundamental_screen_result': 'NOT_EVALUATED',
            'dossiers_completed': 0, 'new_fetches': 0, 'paid_cli_calls': 0,
            'weekly_reconciliation_due': date.weekday() == 4,
            'next_morning_slot': next_slot, 'authentication_evidence_sha256': sha(auth_path)}
        stages = {1: ('SKIPPED', 'Not due in OVERNIGHT; prior diagnostic reference retained'),
                  2: ('BLOCKED', 'Fundamental discovery/dossiers NOT_EVALUATED; 35-lead queue preserved'),
                  3: ('SKIPPED', 'No changed accepted thesis; morning triggers remain gated, not NO_CHANGE'),
                  4: ('BLOCKED', 'Changed context backlog preserved; no ingestion or Claude significance executed'),
                  5: ('SKIPPED', 'Morning assembly not yet due; prior factual report reference retained')}
        batch_parent = R / 'runs' / batch
        assert not batch_parent.exists(), 'Existing unregistered batch requires recovery'
        batch_parent.parent.mkdir(parents=True, exist_ok=True)
        pending = Path(tempfile.mkdtemp(prefix='.pending_overnight_', dir=batch_parent.parent))
        runs = []
        for n in range(1, 6):
            run_id = f'routine_0{n}_a01'
            target = pending / f'routine_0{n}' / run_id
            target.mkdir(parents=True)
            write(target / 'readiness.json', readiness)
            write(target / 'stock_report_ref.json', stock_ref)
            (target / 'open_tasks.jsonl').write_text(''.join(json.dumps(t) + '\n' for t in task_rows))
            if n == 2:
                (target / 'research_backlog.jsonl').write_text(''.join(json.dumps(q) + '\n' for q in queue))
                write(target / 'fundamental_screen.json', {'status': 'BLOCKED', 'result': 'NOT_EVALUATED',
                    'screened_universe': None, 'selected_count': None, 'reason': 'Source/readiness/runtime not certified',
                    'independent_discovery_executed': False, 'existing_leads_are_not_screen_output': True})
                (target / 'transitions.jsonl').write_text('')
            if n == 4:
                write(target / 'registry_ref.json', {'immutable_registry_run': validate(prior[4]),
                    'record_count': len(events), 'new_event_count': 0, 'newness_evaluated': False,
                    'additional_cutoff_packet': {**stock_ref, 'payload': 'news_updates.jsonl', 'records': len(updates)}})
                (target / 'events.jsonl').write_text('')
                write(target / 'source_health.json', {'fresh_sources_evaluated': 0, 'source_cursors_advanced': False,
                    'registry_resolved': True, 'legacy_events': len(events), 'cutoff_updates': len(updates)})
            if n == 5:
                write(target / 'digest.json', {'status': 'SKIPPED', 'result': 'NOT_EVALUATED',
                    'prior_digest_ref': validate(prior[5]), 'stock_report_ref': stock_ref,
                    'editorial_executed': False, 'evidence_changed': False})
                write(target / 'notification_state.json', {'external_delivery': 'NOT_SENT',
                    'unchanged_blockers_suppressed': True, 'unchanged_stock_list_suppressed': True})
                (target / 'decision_queue.jsonl').write_text(''.join(json.dumps(t) + '\n' for t in task_rows))
            body = [f'# Overnight checkpoint — {date} — {stages[n][0]}', '',
                f'Slot: {slot}. Started: {started}. Hard deadline: {deadline}. Routine R{n}.', '',
                'Claude normal-context authentication was freshly verified (Claude.ai, Max). Shared budget reservation/accounting and applicable source/runtime gates remain absent; no model call was dispatched. Claude assignments remain BLOCKED and are not replaced by Codex.', '',
                f'[{len(stocks)} named leads and dated next checks]({source / "report.md"}) remain available at the existing {stock_h["cutoff_at"]} evidence cutoff. Market observations are dated {stock_h["market_asof"]}. No new stock report, price scan, filing verification, fundamental screen or dossier was produced in this pass.', '',
                f'The full legacy registry resolves through continuation references to {len(events)} events; {len(updates)} cutoff updates remain separately pinned. Empty deltas do not erase the known registry. No source watermark advanced.', '',
                '| Routine | Status | Scope |', '| --- | --- | --- |']
            body.extend(f'| R{k} | {v[0]} | {v[1]} |' for k, v in stages.items())
            body += ['', f'{len(task_rows)} unresolved tasks retained with their original owners and stable IDs; {len(queue)} per-stock questions checkpointed for R2. No qualification transitions. Registered frozen hashes match. Paper context retains its prior date; no updated book/exposure claims are made.', '',
                f'Next: {next_slot}; assemble available sealed evidence by 10:15 IST, run only eligible changed-thesis/expiry checks, preserve the factual stock report and suppress unchanged notices. For Claude dispatch, first establish verified pricing, durable reservations/reconciliation and applicable source readiness. Friday reconciliation is not due for this Tuesday slot.']
            (target / 'report.md').write_text('\n'.join(body) + '\n')
            artifacts = [{'path': p.name, 'sha256': sha(p)} for p in sorted(target.iterdir())]
            hand = {'schema_version': '1.1', 'routine_id': f'routine_0{n}', 'batch_id': batch, 'run_id': run_id,
                'session_date': stock_h['market_asof'], 'scheduled_slot': slot, 'started_at': started,
                'completed_at': datetime.now(TZ).isoformat(), 'cutoff_at': slot, 'evidence_cutoff_at': stock_h['cutoff_at'],
                'deadline_at': deadline, 'deadline_missed': datetime.now(TZ) > datetime.fromisoformat(deadline),
                'timezone': 'Asia/Kolkata', 'status': stages[n][0], 'result': 'NOT_EVALUATED',
                'execution_lane': 'OVERNIGHT', 'production_eligible': False, 'readiness_ref': 'readiness.json',
                'budget_ref': None, 'budget_usage': {'paid_cli_calls': 0, 'external_requests': 0},
                'deferred_counts': {'research_leads': len(queue), 'open_tasks': len(task_rows)},
                'owner': 'Claude' if n in [2, 4, 5] else 'Codex', 'executor': 'Codex checkpoint/manifest validation only',
                'reviewer': 'Codex' if n in [2, 4, 5] else 'Claude', 'review_status': 'UNAVAILABLE',
                'previous_success_run_id': None, 'previous_committed_run': validate(prior[n]),
                'supersedes_run_id': None, 'bootstrap': False, 'upstream_runs': upstream + [stock_ref, validate(full_registry)],
                'input_versions': input_versions, 'config_version': 'overnight-checkpoint-1',
                'code_revision': {'script_sha256': sha(Path(__file__))},
                'coverage': {'fundamental_universe_evaluated': 0, 'dossiers_completed': 0, 'fresh_news_evaluated': False},
                'freshness': {'market_asof': stock_h['market_asof'], 'evidence_cutoff_at': stock_h['cutoff_at']},
                'limitations': [stages[n][1], 'Budget/source/runtime prerequisites absent'], 'artifacts': artifacts,
                'source_cursors': {}, 'processed_event_ids': [], 'open_tasks': task_rows, 'resolved_task_ids': [],
                'next_run': {'slot': next_slot, 'instructions': 'Consume sealed references and unresolved owner queues; do not duplicate historical observations.'}}
            write(target / 'handoff.json', hand)
            write(target / 'manifest.json', {'committed': True, 'schema_version': '1.1', 'batch_id': batch,
                'run_id': run_id, 'artifacts': artifacts + [{'path': 'handoff.json', 'sha256': sha(target / 'handoff.json')}]})
            validate(target)
            runs.append(str((batch_parent / f'routine_0{n}' / run_id).relative_to(ROOT)))
        os.rename(pending, batch_parent)
        for n, name in enumerate(runs, 1):
            atomic(R / f'state/routine_0{n}/latest.json', {'run_dir': name, 'status': stages[n][0], 'production_eligible': False})
        completed[slot] = {'batch_id': batch, 'runs': runs}
        atomic(state / 'completed_slots.json', completed)
        atomic(state / f'batch_overnight_{date}.json', {'batch_id': batch, 'scheduled_slot': slot,
            'deadline_at': deadline, 'runs': runs, 'status': 'BLOCKED', 'notification_required': False,
            'reason': 'Previously reported blockers unchanged; no new evidence', 'stock_report_ref': stock_ref})
        print(json.dumps({'batch_id': batch, 'status': 'BLOCKED', 'open_tasks': len(task_rows),
            'research_leads': len(queue), 'paid_calls': 0, 'notification_required': False}))


if __name__ == '__main__':
    main()
