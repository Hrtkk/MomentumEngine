"""Read-only readiness/continuation pass. Never executes frozen books or paid calls."""
import fcntl, hashlib, json, os, subprocess, tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'research'
TZ = ZoneInfo('Asia/Kolkata')

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, value):
    p.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + '\n')

def atomic_write(p, value):
    temp = p.with_name(p.name + '.tmp')
    write(temp, value)
    os.replace(temp, p)

def main():
    started = datetime.now(TZ)
    date = '2026-10-12'
    slot = date + 'T21:00:00+05:30'
    deadline = datetime.fromisoformat(date + 'T21:30:00+05:30')
    batch = date + '_evening_health_v01'
    state = R / 'state/orchestrator'
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        completed_path = state / 'completed_slots.json'
        completed = json.loads(completed_path.read_text()) if completed_path.exists() else {}
        if slot in completed:
            for path in completed[slot]['runs']:
                target = ROOT / path
                manifest = json.loads((target / 'manifest.json').read_text())
                for item in manifest['artifacts']:
                    assert digest(target / item['path']) == item['sha256']
            print(json.dumps({'reused': True, 'batch_id': batch}))
            return
        input_versions = {}
        upstream = []
        tasks = {}
        previous_runs = {}
        for n in range(1, 6):
            pointer = R / f'state/routine_0{n}/latest.json'
            if not pointer.exists():
                continue
            p = ROOT / json.loads(pointer.read_text())['run_dir']
            m = json.loads((p / 'manifest.json').read_text())
            assert m['committed']
            for artifact in m['artifacts']:
                assert digest(p / artifact['path']) == artifact['sha256']
            h = json.loads((p / 'handoff.json').read_text())
            ref = {'routine_id': f'routine_0{n}', 'path': str(p.relative_to(ROOT)),
                   'manifest_sha256': digest(p / 'manifest.json'), 'status': h['status'],
                   'production_eligible': h['production_eligible']}
            upstream.append(ref)
            previous_runs[n] = ref
            for task in h.get('open_tasks', []):
                if task['status'] not in ['DONE', 'CANCELLED']:
                    tasks[task['task_id']] = task
        for p in [ROOT/'CLAUDE.md', ROOT/'ROADMAP.md', R/'operating_schedule.md', *sorted(R.glob('0*_plan.md'))]:
            input_versions[str(p.relative_to(ROOT))] = digest(p)
        regpath = ROOT/'live/ledgers/registration.json'
        reg = json.loads(regpath.read_text())
        checks = []
        for name, expected in reg['code_sha256'].items():
            p = ROOT/'experiments'/name
            actual = digest(p)
            checks.append({'path': str(p.relative_to(ROOT)), 'expected_prefix': expected,
                           'actual_sha256': actual, 'matches': actual.startswith(expected)})
            input_versions[str(p.relative_to(ROOT))] = actual
        input_versions[str(regpath.relative_to(ROOT))] = digest(regpath)
        positions = []
        for book in ['M11', 'M10', 'M2']:
            candidates = []
            for p in (ROOT/'live/ledgers'/book).glob('snapshot_*.json'):
                obj = json.loads(p.read_text())
                candidates.append((obj.get('signal_date', ''), p, obj))
            asof, p, obj = max(candidates, key=lambda x: x[0])
            input_versions[str(p.relative_to(ROOT))] = digest(p)
            for symbol in obj['positions']:
                positions.append({'portfolio': book, 'symbol': symbol, 'asof': asof,
                                  'exposure_scope': 'PAPER', 'thesis_status': 'THESIS_NOT_DOCUMENTED',
                                  'evaluation_status': 'NOT_EVALUATED', 'comparison_available': False})
        c0_path = ROOT/'ledgers/state.json'
        c0 = json.loads(c0_path.read_text())
        input_versions[str(c0_path.relative_to(ROOT))] = digest(c0_path)
        c0_coverage = {'source': 'ledgers/state.json', 'asof': c0.get('last_t'),
                       'portfolio_names': list(c0.get('books', {})),
                       'status': 'NOT_EVALUATED', 'reason': 'No certified per-portfolio thesis/trigger layer; C0 exposure checks pending'}
        eod_exists = (ROOT/f'live/ledgers/evening_{date}.json').exists()
        raw_exists = (ROOT/f'data/raw/bhav/{date}.csv').exists()
        status_probe = subprocess.run(['claude', 'auth', 'status'], capture_output=True, text=True, timeout=10)
        try:
            auth = json.loads(status_probe.stdout)
        except (ValueError, TypeError):
            auth = {}
        auth_observation = {'logged_in_in_current_context': auth.get('loggedIn'),
                            'auth_method_in_current_context': auth.get('authMethod'),
                            'status': 'AUTH_CONTEXT_UNAVAILABLE' if not auth.get('loggedIn') else 'AUTHENTICATED',
                            'normal_login_previously_verified': True, 'inference': 'No claim of human logout'}
        if 4 in previous_runs:
            news_path = ROOT/previous_runs[4]['path']
            news_records = [json.loads(line) for line in (news_path/'event_registry.jsonl').read_text().splitlines()]
        else:
            news_records = []
        primary = sum(x['verification_status'] == 'PRIMARY_VERIFIED' for x in news_records)
        tid = 'eod-required-'+date
        tasks[tid] = {'task_id': tid, 'owner': 'Codex', 'security_id': None,
                      'description': 'Verify required dated EOD artifacts and session calendar before current-session scans',
                      'priority': 'P1', 'status': 'BLOCKED', 'created_run_id': batch,
                      'due_at': None, 'trigger': 'valid EOD inputs available',
                      'blocking_reason': 'No '+date+' EOD batch or raw bhavcopy in repository; calendar not certified',
                      'evidence_refs': ['readiness.json']}
        tasks['c0-monitor-coverage'] = {'task_id': 'c0-monitor-coverage', 'owner': 'Codex',
                      'security_id': None, 'description': 'Include C0 portfolio variants in a certified trigger/exposure layer',
                      'priority': 'P2', 'status': 'OPEN', 'created_run_id': batch, 'due_at': None,
                      'trigger': 'monitor implementation readiness', 'blocking_reason': c0_coverage['reason'],
                      'evidence_refs': ['ledgers/state.json']}
        readiness = {'scheduled_slot': slot, 'deadline_at': deadline.isoformat(),
                     'current_eod_batch_present': eod_exists, 'current_raw_bhavcopy_present': raw_exists,
                     'latest_paper_session': max(x['asof'] for x in positions),
                     'calendar_certified': False, 'phase0_certified': False,
                     'budget_accounting_available': False, 'claude': auth_observation,
                     'paper_position_records': len(positions), 'actual_exposure_known': False,
                     'prior_news_records': len(news_records), 'prior_primary_verified': primary,
                     'new_news_fetches': 0, 'paid_cli_calls': 0,
                     'c0_coverage': c0_coverage, 'registration_checks': checks}
        stages = {1: ('BLOCKED', 'Current-session EOD/readiness unavailable'),
                  2: ('BLOCKED', 'No accepted registry/dossiers; qualification and fresh fundamental screens unavailable'),
                  3: ('BLOCKED', 'Paper inventory/hash checks available; thesis/trigger evaluations unavailable'),
                  4: ('PARTIAL', 'Prior sealed evidence registry retained; no fresh collection or Claude significance pass'),
                  5: ('BLOCKED', 'Deterministic health fallback; Claude editorial work unavailable')}
        runs = []
        for n in range(1, 6):
            run_id = f'routine_0{n}_a01'
            target = R/f'runs/{batch}/routine_0{n}/{run_id}'
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = Path(tempfile.mkdtemp(prefix='.pending_', dir=target.parent))
            write(temp/'readiness.json', readiness)
            items = list(tasks.values())
            (temp/'open_tasks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in items))
            if n == 1:
                (temp/'signals.jsonl').write_text('')
            if n == 2:
                write(temp/'intake_queue.json', {'admitted_candidates': [], 'deferred_registry_refs': previous_runs.get(4),
                                                'deferred_records': len(news_records), 'reason': 'identity/registry gates unavailable'})
                (temp/'transitions.jsonl').write_text('')
            if n == 3:
                (temp/'monitor_state.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in positions))
                (temp/'changes.jsonl').write_text('')
                (temp/'transition_proposals.jsonl').write_text('')
            if n == 4:
                (temp/'events.jsonl').write_text('')
                write(temp/'registry_ref.json', {'immutable_registry_run': previous_runs.get(4), 'new_event_count': 0,
                                               'newness_evaluated': False, 'record_count': len(news_records)})
                write(temp/'source_health.json', {'fresh_sources_evaluated': 0, 'source_cursors_advanced': False,
                                                'reason': 'No eligible ingestion/budget implementation; prior source limitations retained'})
            if n == 5:
                write(temp/'digest.json', {'status': 'BLOCKED', 'result': 'NOT_EVALUATED', 'items': [],
                                          'editorial_executed': False, 'executor': 'Codex health fallback',
                                          'prior_news_registry_ref': previous_runs.get(4)})
                write(temp/'notification_state.json', {'external_delivery': 'NOT_SENT', 'new_incident': tid,
                                                      'repeated_blockers_suppressed': True})
            late = datetime.now(TZ) > deadline
            body = f'''# Evening research health — {date}

Status: {stages[n][0]}; result: NOT_EVALUATED. Scheduled slot: 21:00 IST.
Started: {started.isoformat()}. Deadline: 21:30 IST. Deadline missed: {late}.
Routine: {n}. Executor: Codex readiness/continuation checks only.

## Available evidence

No {date} evening-batch artifact or raw bhavcopy is present. Latest M11/M10/M2 snapshots are dated 9 October. Calendar/session completeness is not certified; this is not evidence of a holiday. Frozen registered source hashes match: {all(x['matches'] for x in checks)}. Detailed checks and input hashes are in readiness.json and handoff.json.

The prior sealed news registry contains {len(news_records)} leads for 5–11 October, including {primary} primary-body verified records. These are carried references, not newly detected news or a fresh/current-session scan. No source watermark advanced.

## Stage health

| Routine | Status | Reason |
| --- | --- | --- |
'''
            body += '\n'.join(f'| R{k} | {v[0]} | {v[1]} |' for k,v in stages.items())
            body += f'''

## Checks, limitations and next work

- R3 inventoried {len(positions)} paper positions across M11/M10/M2; no original thesis/accepted trigger baselines exist. Every thesis check is NOT_EVALUATED, not NO_CHANGE. C0 state dated {c0.get('last_t')} was inspected; its portfolio variants remain an explicit monitoring coverage gap.
- Claude login is unavailable in this unattended sandbox context. Normal login previously succeeded; no logout is inferred. No Claude-authored interpretation/review is claimed.
- Shared metered-call accounting, source-readiness and accepted R2 registry/dossiers remain absent. No paid CLI call, fresh news fetch, discretionary promotion or strategy/book change occurred.
- Existing unfinished tasks are retained by stable task ID. Codex owns input/readiness/budget and C0-coverage tasks; Claude retains dossier, significance, thesis and editorial work after prerequisites pass.
- The original slot/cutoff is preserved despite late completion. Next due slot is {date} 23:00 IST. Use exact pinned manifests and unresolved-task queue; do not replay already committed slots or treat this health report as a completed investment brief.
'''
            (temp/'report.md').write_text(body)
            artifacts = [{'path': p.name, 'sha256': digest(p), 'record_count': len(p.read_text().splitlines()) if p.suffix == '.jsonl' else None}
                         for p in sorted(temp.iterdir())]
            hand = {'schema_version': '1.1', 'routine_id': f'routine_0{n}', 'batch_id': batch, 'run_id': run_id,
                    'session_date': '2026-10-09', 'scheduled_slot': slot, 'started_at': started.isoformat(),
                    'completed_at': datetime.now(TZ).isoformat(), 'cutoff_at': slot, 'deadline_at': deadline.isoformat(),
                    'deadline_missed': late, 'timezone': 'Asia/Kolkata', 'status': stages[n][0],
                    'result': 'NOT_EVALUATED', 'execution_lane': 'FAST', 'production_eligible': False,
                    'readiness_ref': 'readiness.json', 'budget_ref': None,
                    'budget_usage': {'paid_cli_calls': 0, 'external_requests': 0},
                    'deferred_counts': {'news_leads': len(news_records), 'paper_thesis_checks': len(positions)},
                    'owner': 'Claude' if n in [2,4,5] else 'Codex', 'executor': 'Codex readiness/continuation only',
                    'reviewer': 'Codex' if n in [2,4,5] else 'Claude', 'review_status': 'UNAVAILABLE',
                    'previous_success_run_id': None, 'previous_committed_run': previous_runs.get(n),
                    'supersedes_run_id': None, 'bootstrap': n not in previous_runs,
                    'upstream_runs': upstream, 'input_versions': input_versions, 'config_version': 'evening-health-1',
                    'code_revision': {'git_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                                      'health_script_sha256': digest(Path(__file__))},
                    'coverage': {'thesis_evaluated': 0, 'paper_records_inventoried': len(positions),
                                 'c0_evaluation': 'NOT_EVALUATED', 'fresh_news_evaluated': False},
                    'freshness': {'latest_paper_session': '2026-10-09', 'prior_news_end': '2026-10-11', 'current_eod_present': eod_exists},
                    'limitations': [stages[n][1], 'Budget/readiness/auth-context blockers unchanged', 'No current-session conclusions'],
                    'artifacts': artifacts, 'source_cursors': {}, 'processed_event_ids': [],
                    'open_tasks': items, 'resolved_task_ids': [],
                    'next_run': {'slot': date+'T23:00:00+05:30', 'instructions': 'Resume unresolved tasks and pinned prior registry; recheck gates without repeating unchanged notifications.'}}
            write(temp/'handoff.json', hand)
            manifest = {'schema_version': '1.1', 'committed': True, 'batch_id': batch, 'run_id': run_id,
                        'artifacts': artifacts + [{'path':'handoff.json','sha256':digest(temp/'handoff.json'),'record_count':1}]}
            write(temp/'manifest.json', manifest)
            for item in manifest['artifacts']:
                assert digest(temp/item['path']) == item['sha256']
            os.rename(temp, target)
            rs = R/f'state/routine_0{n}'
            rs.mkdir(parents=True, exist_ok=True)
            atomic_write(rs/'latest.json', {'run_dir':str(target.relative_to(ROOT)), 'status':stages[n][0], 'production_eligible':False})
            runs.append(str(target.relative_to(ROOT)))
        atomic_write(state/'batch_evening_2026-10-12.json', {'batch_id':batch,'scheduled_slot':slot,'runs':runs,
                                                         'status':'BLOCKED','deadline_missed':datetime.now(TZ)>deadline})
        completed[slot] = {'batch_id':batch,'runs':runs}
        atomic_write(completed_path,completed)
        notify_path = state/'blocker_notifications.json'
        notices = json.loads(notify_path.read_text()) if notify_path.exists() else {}
        new = tid not in notices
        if new:
            notices[tid] = {'first_reported_at':datetime.now(TZ).isoformat(),'state':'OPEN','reason':'Required current-date EOD unavailable'}
        atomic_write(notify_path,notices)
        print(json.dumps({'report':str(ROOT/runs[-1]/'report.md'),'status':'BLOCKED','new_eod_notice':new,
                          'paid_calls':0,'prior_news_leads':len(news_records),'open_tasks':len(tasks),'deadline_missed':datetime.now(TZ)>deadline}))

if __name__ == '__main__':
    main()
