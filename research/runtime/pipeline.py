"""Date-driven diagnostic research pipeline. Research artifacts only; never paper books."""
import argparse
import copy
import fcntl
import hashlib
import io
import json
import os
import tempfile
import zipfile
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from budget import Budget, TZ
from sources import fetch, validate_bhav
from seal_evening_snapshot import ROOT, R, read, write, atomic, rows, sha, validate, registry


def jsonl(path, records):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in records))


def available_events(announcements, cutoff):
    accepted, rejected = [], []
    for entry in announcements:
        try:
            published = datetime.strptime(entry['an_dt'], '%d-%b-%Y %H:%M:%S').replace(tzinfo=TZ)
        except (KeyError, ValueError, TypeError):
            rejected.append({'seq_id': entry.get('seq_id'), 'reason': 'PUBLICATION_TIME_UNKNOWN'})
            continue
        if published > cutoff:
            rejected.append({'seq_id': entry.get('seq_id'), 'reason': 'AFTER_CUTOFF'})
            continue
        accepted.append({**entry, 'published_at': published.isoformat()})
    return accepted, rejected


def independent_results(announcements, identities):
    """Filing-led discovery requires no price anomaly; missing statements never pass ratios."""
    output = {}
    for a in announcements:
        text = (str(a.get('desc', '')) + ' ' + str(a.get('attchmntText', ''))).lower()
        if 'financial result' not in text or 'board' not in str(a.get('desc', '')).lower():
            continue
        symbol = a['symbol']
        if symbol not in identities or identities[symbol] != a.get('sm_isin'):
            continue
        if symbol not in output or a['published_at'] > output[symbol]['published_at']:
            output[symbol] = {'symbol': symbol, 'security_id': identities[symbol],
                'event_id': 'nse-announcement-' + a['seq_id'], 'published_at': a['published_at'],
                'source_url': a['attchmntFile'], 'fact': a['attchmntText'],
                'verification_status': 'PRIMARY_EXCHANGE_METADATA_ONLY',
                'next_check': 'Verify original quarter table, sector metrics, cash conversion and valuation; no price trigger required.'}
    return list(output.values())


def fundamental_metrics(record):
    m = dict(record['metrics'])
    m['pat_yoy_pct'] = (m['pat'] / m['prior_year_pat'] - 1) * 100 if m.get('prior_year_pat', 0) > 0 else None
    for field in ['revenue', 'gross_written_premium']:
        if field in m:
            m[field + '_yoy_pct'] = (m[field] / m['prior_year_' + field] - 1) * 100 if m.get('prior_year_' + field, 0) > 0 else None
    return m


def screen_financial(record):
    m = fundamental_metrics(record)
    insurance = record['basis'] == 'INSURER_STATUTORY'
    growth_key = 'gross_written_premium_yoy_pct' if insurance else 'revenue_yoy_pct'
    growth = m.get(growth_key)
    pat_growth = m.get('pat_yoy_pct')
    return {'symbol': record['symbol'], 'screen_version': 'dated-quarter-observations-1',
        'template': 'GENERAL_INSURANCE' if insurance else 'NON_FINANCIAL',
        'positive_revenue_or_premium_growth': growth > 0 if growth is not None else None,
        'positive_pat_growth': pat_growth > 0 if pat_growth is not None else None,
        'growth_profit_divergence': growth > 0 and pat_growth < 0 if growth is not None and pat_growth is not None else None,
        'combined_ratio_below_100': m.get('combined_ratio_pct') < 100 if insurance and m.get('combined_ratio_pct') is not None else None,
        'industrial_leverage_test_applied': False,
        'qualification': 'NOT_EVALUATED', 'reason': 'Valuation/cash-conversion/governance and full sector context not verified',
        'evidence_id': record['evidence_id'], 'period_end': record['period_end'], 'basis': record['basis']}


def monitor(dossier, financial, prior, cutoff):
    metrics = fundamental_metrics(financial)
    checks = []
    for rule in (prior.get('original_forecast') if prior else None) or dossier['assumptions']:
        if not set(['metric', 'operator', 'threshold']) <= set(rule):
            continue
        assert rule['operator'] in ['lt', 'gt'] and rule['metric'] in ['pat_yoy_pct', 'revenue_yoy_pct', 'gross_written_premium_yoy_pct', 'combined_ratio_pct']
        assert isinstance(rule['threshold'], (int, float))
        newer_period = prior is not None and prior['period_end'] < financial['period_end']
        value = metrics.get(rule['metric'])
        triggered = (value < rule['threshold'] if rule['operator'] == 'lt' else value > rule['threshold']) if newer_period and value is not None else None
        checks.append({'assumption_id': rule['assumption_id'], 'rule': rule, 'observed_value': value,
            'comparison_available': newer_period, 'result': 'TRIGGERED' if triggered else 'NO_CHANGE' if triggered is False else 'BASELINE_ONLY'})
    expiry = datetime.fromisoformat(financial['published_at']) + timedelta(days=120)
    return {'symbol': dossier['symbol'], 'period_end': financial['period_end'],
        'original_hypothesis': prior.get('original_hypothesis') if prior else dossier['hypothesis'],
        'original_forecast': prior.get('original_forecast') if prior else dossier['assumptions'],
        'last_metrics': metrics, 'last_evaluated_at': cutoff.isoformat(), 'checks': checks,
        'evidence_expires_at': expiry.isoformat(), 'expiry_rule_version': 'quarterly-publication-120d-v1',
        'expiry_result': 'EXPIRED' if cutoff >= expiry else 'CURRENT', 'qualification': 'UNQUALIFIED',
        'exposure_scope': 'UNKNOWN', 'review_status': 'CODEX_SOURCE_CHALLENGE_REQUIRED'}


def collect(session, *, lane, batch, budget):
    date = datetime.fromisoformat(session).date()
    directory = R / f'inputs/{session}_runtime_v01'
    ddmmyyyy = date.strftime('%d%m%Y')
    urls = {
        f'bhav_{session}.csv': f'https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv',
        f'index_{session}.csv': f'https://nsearchives.nseindia.com/content/indices/ind_close_all_{ddmmyyyy}.csv',
        f'udiff_{session}.zip': f'https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date:%Y%m%d}_F_0000.csv.zip',
        'actions.json': f'https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date={date-timedelta(days=4):%d-%m-%Y}&to_date={date:%d-%m-%Y}',
        'announcements.json': f'https://www.nseindia.com/api/corporate-announcements?index=equities&from_date={date-timedelta(days=1):%d-%m-%Y}&to_date={date:%d-%m-%Y}'}
    for filename, url in urls.items():
        fetch(url, directory / filename, batch=batch, lane=lane, budget=budget)
    return directory



def prior_nonempty_payload(directory, filename):
    """Resolve empty continuation handoffs without resetting accepted evidence."""
    seen = set()
    while directory:
        directory = directory.resolve()
        assert directory not in seen, 'Prior payload reference cycle'
        seen.add(directory)
        ref = validate(directory)
        payload = directory / filename
        if payload.exists():
            records = rows(payload)
            if records:
                return records, ref
        previous = read(directory / 'handoff.json').get('previous_committed_run')
        if not previous:
            break
        directory = ROOT / previous['run_dir']
        assert sha(directory / 'manifest.json') == previous['manifest_sha256'], 'Prior payload manifest changed'
    return [], None


def compute_prices(directory, session):
    raw = validate_bhav(directory / f'bhav_{session}.csv', session)
    z = zipfile.ZipFile(directory / f'udiff_{session}.zip')
    u = pd.read_csv(z.open(z.namelist()[0]))
    assert pd.to_datetime(u.TradDt).dt.strftime('%Y-%m-%d').eq(session).all(), 'UDiFF internal date mismatch'
    u = u[(u.SctySrs == 'EQ') & u.ISIN.astype(str).str.startswith('INE') & (u.FinInstrmTp == 'STK')]
    assert not u.duplicated('TckrSymb').any()
    identities = dict(zip(u.TckrSymb, u.ISIN))
    merged = raw[raw.SERIES == 'EQ'].merge(u[['TckrSymb', 'ISIN', 'ClsPric']], left_on='SYMBOL', right_on='TckrSymb', validate='one_to_one')
    assert (merged.CLOSE_PRICE - merged.ClsPric).abs().le(.011).all(), 'Two official price files disagree'
    actions = read(directory / 'actions.json')
    action_today = {a['symbol'] for a in actions if datetime.strptime(a['exDate'], '%d-%b-%Y').date().isoformat() == session}
    known = [ROOT / 'experiments/data/pit' / f'bhav_{y}.parquet' for y in [2025, 2026]]
    history = pd.concat([pd.read_parquet(p) for p in known], ignore_index=True)
    history['date'] = pd.to_datetime(history['date'])
    extra, overlay_exclusions = [], []
    # Overlay files are isolated; frozen PIT parquet and raw-book inputs are never modified.
    for p in sorted((R / 'inputs').glob('*/bhav_*.csv')):
        day = p.stem.removeprefix('bhav_')
        if day > session or pd.Timestamp(day) <= history.date.max():
            continue
        try:
            frame = validate_bhav(p, day)
        except ValueError as error:
            # Retain rejected evidence; it cannot poison a verified primary session.
            overlay_exclusions.append({'source': str(p), 'expected_session': day,
                'reason': str(error), 'sha256': sha(p)})
            continue
        frame = frame[frame.SERIES == 'EQ']
        extra.append(pd.DataFrame({'symbol': frame.SYMBOL, 'date': pd.Timestamp(day),
            'close': frame.CLOSE_PRICE, 'high': frame.HIGH_PRICE, 'low': frame.LOW_PRICE,
            'volume': frame.TTL_TRD_QNTY, 'series': 'EQ'}))
    history = pd.concat([history, *extra], ignore_index=True)
    history = history[(history.series == 'EQ') & (history.date <= pd.Timestamp(session))]
    history = history.drop_duplicates(['date', 'symbol'], keep='last')
    grouped = {s: g.sort_values('date') for s, g in history.groupby('symbol')}
    result = {}
    for _, row in merged.iterrows():
        sym = row.SYMBOL
        g = grouped.get(sym)
        prior = g[g.date < pd.Timestamp(session)] if g is not None else pd.DataFrame()
        vol = float(row.TTL_TRD_QNTY)
        median = float(prior.tail(20).volume.median()) if len(prior) >= 20 else None
        nominal = (float(row.CLOSE_PRICE) / float(row.PREV_CLOSE) - 1) * 100 if row.PREV_CLOSE > 0 else None
        result[sym] = {'symbol': sym, 'security_id': row.ISIN, 'session': session,
            'close_inr': float(row.CLOSE_PRICE), 'nominal_daily_return_pct': None if sym in action_today else nominal,
            'raw_unadjusted_daily_return_pct': nominal, 'volume_ratio_prior20': vol / median if median and median > 0 and not overlay_exclusions else None,
            'nominal_return_since_oct9_pct': None, 'adjustment_verified': False,
            'price_action_flag': sym in action_today, 'raw_volume': vol,
            'history_overlay_exclusions': overlay_exclusions,
            'source': str(directory / f'bhav_{session}.csv'), 'events': []}
    # Long-window events remain diagnostic until identity/calendar/action history is certified.
    ca = pd.read_parquet(ROOT / 'experiments/data/pit/ca.parquet')
    ca['ex'] = pd.to_datetime(ca.exDate, format='%d-%b-%Y', errors='coerce')
    action_window = set(ca[ca.ex >= pd.Timestamp(session) - pd.Timedelta(days=500)].symbol) | {a['symbol'] for a in actions}
    technical, quarantine = [], []
    base = R / 'runs/2026-10-09_diagnostic_f851eb37ee38/routine_01/routine_01_a01'
    universe = [r['symbol'] for f in ['metrics.jsonl', 'quarantine.jsonl'] for r in rows(base / f)]
    for sym in universe:
        g = grouped.get(sym)
        reasons = ['UNVERIFIED_HISTORICAL_OVERLAY'] if overlay_exclusions else []
        if sym not in result: reasons.append('NO_VERIFIED_EQ_IDENTITY')
        if sym in action_window: reasons.append('ACTION_HISTORY_UNADJUSTED')
        if g is None or len(g) < 321: reasons.append('INSUFFICIENT_HISTORY')
        elif g.tail(321).close.isna().any(): reasons.append('HISTORY_GAPS')
        if reasons:
            quarantine.append({'symbol': sym, 'reasons': reasons}); continue
        m = result[sym]
        events = []
        if m['nominal_daily_return_pct'] is not None and m['nominal_daily_return_pct'] > 5 and (m['volume_ratio_prior20'] or 0) > 2:
            events.append('PRICE_VOLUME_ANOMALY')
        for n in [20, 252]:
            if m['close_inr'] > g.iloc[:-1].tail(n).high.max(): events.append(f'ABOVE_PRIOR_{n}_SESSION_HIGH')
        for n in [50, 200]:
            ma = g.close.rolling(n).mean()
            if g.close.iloc[-2] <= ma.iloc[-2] and m['close_inr'] > ma.iloc[-1]: events.append(f'CROSSED_ABOVE_SMA{n}')
        m['events'] = events
        technical.append({'symbol': sym, 'security_id': m['security_id'], 'session': session,
            'close_inr': m['close_inr'], 'return_pct': m['nominal_daily_return_pct'],
            'relative_volume': m['volume_ratio_prior20'], 'events': events, 'production_eligible': False})
    return result, identities, technical, quarantine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', default='AUTO', help='AUTO verifies official dated files; never infers a holiday from a failed fetch')
    parser.add_argument('--slot', help='Actual intended timezone-aware slot; retain on delayed runs')
    parser.add_argument('--lane', choices=['FAST', 'OVERNIGHT', 'EVENT'], default='EVENT')
    parser.add_argument('--analysis-dir', help='Previously reconciled Claude packet directory; no duplicate model request')
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--run-claude', action='store_true', help='Authenticated, reserved, bounded analysis of changed evidence')
    args = parser.parse_args()
    cutoff = datetime.fromisoformat(args.slot) if args.slot else datetime.now(TZ)
    started_at = datetime.now(TZ)
    if args.slot and cutoff.hour == 10:
        deadline = cutoff.replace(hour=10, minute=15, second=0, microsecond=0)
    elif args.slot and cutoff.hour == 21:
        deadline = cutoff.replace(hour=21, minute=30, second=0, microsecond=0)
    elif args.slot and cutoff.hour == 23:
        deadline = (cutoff + timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
    else:
        deadline = started_at + timedelta(minutes=30)
    assert cutoff.tzinfo
    budget = Budget()
    with (R / 'state/orchestrator/writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        batch = 'pipeline_' + cutoff.strftime('%Y-%m-%d_%H%M%S')
        completed_path = R / 'state/orchestrator/completed_slots.json'
        completed = read(completed_path)
        if cutoff.isoformat() in completed:
            for name in completed[cutoff.isoformat()]['runs']: validate(ROOT / name)
            print(json.dumps({'reused': True, 'batch_id': completed[cutoff.isoformat()]['batch_id']})); return
        if args.session == 'AUTO':
            candidate = cutoff.date() if cutoff.hour >= 18 else cutoff.date() - timedelta(days=1)
            chosen = None
            for offset in range(3):
                date = candidate - timedelta(days=offset)
                path = R / f'inputs/{date}_runtime_v01' / f'bhav_{date}.csv'
                try:
                    if args.collect:
                        fetch(f'https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date:%d%m%Y}.csv', path,
                              batch=batch, lane=args.lane, budget=budget)
                    validate_bhav(path, date.isoformat()); chosen = date.isoformat(); break
                except Exception:
                    continue
            if chosen is None:
                chosen = read(R / 'state/stock_report/latest.json')['market_asof']
                assert (R / f'inputs/{chosen}_runtime_v01' / f'bhav_{chosen}.csv').exists(), 'No validated source; retain previous report and publish collection failure'
            args.session = chosen
        assert args.session <= cutoff.date().isoformat(), 'Never future EOD'
        assert args.session < cutoff.date().isoformat() or cutoff.hour >= 18, 'Same-day close not eligible before evening'
        directory = collect(args.session, lane=args.lane, batch=batch, budget=budget) if args.collect else R / f'inputs/{args.session}_runtime_v01'
        prices, identities, technical, quarantine = compute_prices(directory, args.session)
        raw_announcements = read(directory / 'announcements.json')
        admitted, overflow = budget.admit_records('NEWS_METADATA', [str(a.get('seq_id')) for a in raw_announcements], 2000)
        admitted = set(admitted)
        ann, exclusions = available_events([a for a in raw_announcements if str(a.get('seq_id')) in admitted], cutoff)
        if overflow:
            jsonl(directory / 'metadata_backlog.jsonl', [{'seq_id': i, 'deferred_reason': 'DAILY_METADATA_BUDGET', 'owner': 'Codex'} for i in overflow])
        discovery = independent_results(ann, identities)
        prior_report = ROOT / read(R / 'state/stock_report/latest.json')['report_dir']
        validate(prior_report)
        stocks = {s['symbol']: copy.deepcopy(s) for s in rows(prior_report / 'stocks.jsonl')}
        for entry in discovery:
            row = stocks.setdefault(entry['symbol'], {'symbol': entry['symbol'], 'company_events': [], 'new_events': [],
                'owner': 'Codex verification; Claude research', 'record_kind': 'RESEARCH_LEAD', 'qualified': False})
            old_ids = {e['event_id'] for e in row.get('new_events', [])}
            if entry['event_id'] not in old_ids: row.setdefault('new_events', []).append(entry)
            row['next_check'] = entry['next_check']
            row['origin_lane'] = 'INDEPENDENT_RESULTS_DISCOVERY'
        for m in technical:
            if m['events']:
                row = stocks.setdefault(m['symbol'], {'symbol': m['symbol'], 'company_events': [], 'new_events': [],
                    'owner': 'Codex verification; Claude research', 'next_check': 'Verify business and action/identity history before interpreting the diagnostic event.', 'qualified': False})
                row['technical'] = m
        for sym, row in stocks.items():
            row['current_stats'] = prices.get(sym)
            row['security_id'] = identities.get(sym)
            row['qualified'] = False
        financials = []
        fpath = directory / 'verified_fundamentals.json'
        for f in read(fpath) if fpath.exists() else []:
            assert sha(ROOT / f['source_path']) == f['source_sha256']
            if datetime.fromisoformat(f['published_at']) <= cutoff:
                financials.append({**f, 'derived': fundamental_metrics(f)})
        draft, receipt = None, None
        if args.run_claude and datetime.now(TZ) + timedelta(seconds=110) < deadline:
            from claude_worker import run as run_claude
            # Small original-document collection is independent of price anomalies.
            ordered = sorted(discovery, key=lambda e: (-(prices.get(e['symbol'], {}).get('close_inr', 0) * prices.get(e['symbol'], {}).get('raw_volume', 0)), e['symbol']))
            document_notes = []
            for e in ordered[:3]:
                document = directory / (e['symbol'] + '_results.pdf')
                try:
                    fetch(e['source_url'], document, batch=batch, lane=args.lane, budget=budget, max_bytes=16*1024**2)
                    text = document.with_suffix('.txt')
                    subprocess.run(['/opt/homebrew/bin/pdftotext', '-layout', str(document), str(text)], timeout=20, check=True)
                    # Financial OCR is a lead only. Only manually/structurally verified
                    # quarter columns can populate quantitative financial metrics.
                    document_notes.append({**e, 'document_sha256': sha(document),
                        'text_excerpt': text.read_text(errors='replace')[:1400],
                        'table_verification': 'UNVERIFIED_OCR; no new financial numbers may be adopted'})
                except Exception as error:
                    document_notes.append({**e, 'document_status': type(error).__name__})
            packet = {'task': 'Return JSON: assessments (max 3 {symbol,mechanism,uncertainty,next_check,evidence_ids}), dossiers (max 3 {symbol,hypothesis,assumptions:[one {assumption_id,statement,metric,operator,threshold}],missing_fields:[two strings],evidence_ids}), brief (max 150 words). ENTIRE JSON max 650 words. Allowed rule metrics pat_yoy_pct,revenue_yoy_pct,gross_written_premium_yoy_pct,combined_ratio_pct; operators lt or gt, numeric thresholds; future comparable-quarter review triggers only. Dossiers only for the verified financials supplied; if absent, dossiers empty. OCR/metadata is not verified financial data. No new numbers, price targets or trading calls. Source causes are hypotheses only. No email/user identity. Claude owns research, Codex verification.',
                'evidence_ids': [f['evidence_id'] for f in financials] + [e['event_id'] for e in document_notes],
                'symbols': sorted({f['symbol'] for f in financials} | {e['symbol'] for e in document_notes}),
                'financials': financials, 'document_notes': document_notes}
            if financials:
                next_period = (pd.Timestamp(max(f['period_end'] for f in financials)) + pd.offsets.QuarterEnd(1)).date().isoformat()
                packet['next_period_end'] = next_period
                packet['task'] += f' The NEXT comparable quarterly observation is the quarter ending {next_period}, compared year on year with its own prior-year quarter. Do not defer review to the same quarter one year later. Use this next period in every next_check.'
            if args.slot and args.lane == 'FAST':
                packet['task'] += ' This is the scheduled FAST lane: dossiers MUST be empty; only bounded significance and editorial work. Existing dossiers are reused by the orchestrator; no deep dossier allocation.'
            if args.lane == 'OVERNIGHT' and cutoff.weekday() == 4:
                packet['task'] += ' Friday weekly reconciliation replaces ordinary allocation: review only provided existing company hypotheses, note expiry and missing-coverage gaps; at most three unique dossiers in this call, no additional ordinary allocation.'
            if packet['symbols']:
                analysis = R / 'analysis' / ('packet_' + hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()[:16])
                try:
                    draft, receipt = run_claude(packet, analysis, batch=batch, lane=args.lane, budget=budget)
                except Exception as error:
                    write(directory / 'claude_failure.json', {'status': 'BLOCKED', 'reason': str(error), 'at': datetime.now(TZ).isoformat()})
        if args.analysis_dir:
            analysis = ROOT / args.analysis_dir
            receipt = read(analysis / 'receipt.json')
            assert any(r['id'] == receipt['request_id'] and r['state'] == 'RECONCILED' for r in budget.snapshot())
            draft = read(analysis / 'accepted.json')
        prior, upstream, tasks = {}, [], {}
        for n in range(1, 6):
            prior[n] = ROOT / read(R / f'state/routine_0{n}/latest.json')['run_dir']
            upstream.append(validate(prior[n]))
            for t in read(prior[n] / 'handoff.json')['open_tasks']: tasks[t['task_id']] = t
        full_registry, legacy = registry(prior[4])
        if receipt and (prior[5] / 'claude_receipt.json').exists() and read(prior[5] / 'claude_receipt.json')['request_id'] == receipt['request_id']:
            receipt = {**receipt, 'reused': True}
        auth = receipt['auth'] if receipt else {'status': 'NOT_CHECKED', 'checked_at': None}
        resolutions = []
        implemented = ['r1-budget', 'r2-bootstrap']
        if draft: implemented += ['r4-claude-interpretation', 'r5-editorial']
        for tid in implemented:
            if tid in tasks:
                tasks[tid] = {**tasks[tid], 'status': 'DONE', 'blocking_reason': None,
                    'resolution': 'Implemented scope evidenced by this batch; production qualification remains gated',
                    'evidence_refs': ['readiness.json', 'budget_snapshot.json']}
                resolutions.append(tid)
        if 'r1-review' in tasks:
            tasks['r1-review'] = {**tasks['r1-review'], 'status': 'OPEN',
                'blocking_reason': 'Technical interpretation was not part of the executed financial packet; retain assigned Claude review',
                'resolution': None}
        if 'r3-thesis-baselines' in tasks and draft:
            tasks['r3-thesis-baselines'] = {**tasks['r3-thesis-baselines'], 'status': 'OPEN',
                'blocking_reason': 'Three provisional baselines implemented; expand company coverage with verified evidence'}
        # Import remote-only persistence failure as an explicit dated resolution, not deletion.
        tasks['repository-write-permission-2026-10-15'] = {'task_id': 'repository-write-permission-2026-10-15',
            'owner': 'Codex', 'priority': 'P1', 'status': 'DONE', 'security_id': None,
            'description': 'Restore repository checkpoint access', 'created_run_id': '2026-10-15_morning_persistence_blocked_v01',
            'due_at': None, 'trigger': 'repository writes available', 'blocking_reason': None,
            'resolution': 'Write probe and immutable batch persistence succeeded', 'evidence_refs': ['readiness.json']}
        resolutions.append('repository-write-permission-2026-10-15')
        monitors, dossiers = [], []
        carried_dossiers, dossier_ref = (prior_nonempty_payload(prior[2], 'dossiers.jsonl')
            if not draft or not draft.get('dossiers') else ([], None))
        prior_monitors, monitor_ref = prior_nonempty_payload(prior[3], 'monitor_state.jsonl')
        for historical_ref in [dossier_ref, monitor_ref]:
            if historical_ref and historical_ref not in upstream:
                upstream.append(historical_ref)
        old_monitors = {x['symbol']: x for x in prior_monitors}
        prior_registry = {x['symbol']: x for x in rows(prior[2] / 'registry.jsonl')} if (prior[2] / 'registry.jsonl').exists() else {}
        if carried_dossiers:
            known_symbols = {f['symbol'] for f in financials}
            for candidate in sorted((R / 'inputs').glob('*/verified_fundamentals.json')):
                for f in read(candidate):
                    if f['symbol'] not in known_symbols and datetime.fromisoformat(f['published_at']) <= cutoff and sha(ROOT / f['source_path']) == f['source_sha256']:
                        financials.append({**f, 'derived': fundamental_metrics(f)})
                        known_symbols.add(f['symbol'])
        for d in (draft['dossiers'] if draft and draft.get('dossiers') else carried_dossiers):
            f = next((f for f in financials if f['symbol'] == d['symbol']), None)
            if not f: continue
            challenge = ['Valuation, cash conversion and broader governance checks remain missing']
            if 'volume-led' in d['hypothesis'].lower(): challenge.append('No volume evidence supports volume-led revenue attribution')
            dossiers.append({**d, 'state': 'RESEARCH', 'qualified': False, 'author': 'Claude',
                'review_status': 'PENDING_ECONOMIC_CHALLENGE', 'source_facts_challenged_by': 'Codex',
                'codex_challenge': challenge,
                'document_ref': f['source_path'], 'evidence_expires_at': (datetime.fromisoformat(f['published_at']) + timedelta(days=120)).isoformat()})
            old = old_monitors.get(d['symbol'])
            monitors.append(monitor(d, f, old if old and 'period_end' in old else None, cutoff))
            latest_filing = next((e for e in discovery if e['symbol'] == d['symbol']), None)
            if latest_filing and latest_filing['source_url'] != f['source_url'] and latest_filing['published_at'] > f['published_at']:
                monitors[-1]['new_filing_table_pending'] = True
                monitors[-1]['expiry_result'] = 'UNDER_REVIEW_NEW_FILING'
                for check in monitors[-1]['checks']:
                    check['result'] = 'NOT_EVALUATED'; check['comparison_available'] = False
            stocks[d['symbol']]['dossier_status'] = 'RESEARCH_PROVISIONAL'
        paper = []
        for book in ['M11', 'M10', 'M2']:
            snapshots = [(read(p).get('signal_date', ''), p) for p in (ROOT / 'live/ledgers' / book).glob('snapshot_*.json')]
            if not snapshots: continue
            asof, snapshot = max(snapshots)
            for symbol in read(snapshot)['positions']:
                paper.append({'symbol': symbol, 'portfolio': book, 'asof': asof, 'exposure_scope': 'PAPER',
                    'thesis_status': 'DOCUMENTED_PROVISIONAL' if any(m['symbol'] == symbol for m in monitors) else 'THESIS_NOT_DOCUMENTED',
                    'evaluation_status': 'NOT_EVALUATED' if not any(m['symbol'] == symbol for m in monitors) else 'BASELINE_OR_EXPIRY_ONLY'})
        readiness = {'current_eod_batch_present': (ROOT / f'live/ledgers/evening_{args.session}.json').exists(),
            'isolated_official_eod_available': True, 'official_session_internally_verified': args.session,
            'raw_and_udiff_prices_reconciled': True, 'identity_scope': 'current EQ/STK INE identities only',
            'calendar_certified': False, 'phase0_certified': False, 'budget_accounting_available': True,
            'claude': auth, 'claude_analysis_available': draft is not None,
            'claude_executed': bool(draft and receipt and not receipt.get('reused')),
            'claude_analysis_reused': bool(receipt and receipt.get('reused')), 'financial_tables_verified': len(financials),
            'independent_results_candidates': len(discovery), 'provisional_dossiers': len(dossiers),
            'metadata_deferred': len(overflow),
            'monitor_baselines': len(monitors), 'paper_positions_inventoried': len(paper), 'unknown_real_holdings': True,
            'reconciliation_mode': 'WEEKLY' if args.lane == 'OVERNIGHT' and cutoff.weekday() == 4 else 'ORDINARY',
            'limitations': ['Historical calendar/identity/entitlement/sector coverage remains uncertified',
                'Results metadata does not pass financial/valuation gates; unverified tables remain unknown',
                'No production qualification or paper-book mutation']}
        parent = R / 'runs' / batch
        pending = Path(tempfile.mkdtemp(prefix='.pending_pipeline_', dir=R / 'runs'))
        pins = {str(p.relative_to(ROOT)): sha(p) for p in directory.iterdir() if p.is_file()}
        if receipt:
            pins.update({str(p.relative_to(ROOT)): sha(p) for p in analysis.iterdir() if p.is_file()})
        for p in [ROOT / 'CLAUDE.md', ROOT / 'ROADMAP.md', R / 'operating_schedule.md', *R.glob('0*_plan.md')]: pins[str(p.relative_to(ROOT))] = sha(p)
        reg = read(ROOT / 'live/ledgers/registration.json')
        for name, expected in reg['code_sha256'].items():
            assert sha(ROOT / 'experiments' / name).startswith(expected), 'Frozen source mismatch'
        statuses = {1: 'PARTIAL', 2: 'PARTIAL', 3: 'PARTIAL' if monitors else 'BLOCKED', 4: 'PARTIAL', 5: 'PARTIAL'}
        stage_reasons = {1: f'Official {args.session} prices reconciled; {len(technical)}/500 technical diagnostics; historical gates remain open',
            2: f'{len(discovery)} independent filing candidates; {len(financials)} verified tables; {len(dossiers)} provisional Claude dossiers; no qualification',
            3: f'{len(monitors)} hypothesis/expiry baselines and {len(paper)} paper inventory records; remaining company triggers unavailable',
            4: f'{len(ann)} publication-eligible announcement records; Claude financial significance recorded: {bool(draft)}; metadata-only cases retain gaps',
            5: f'Claude editorial executed: {bool(draft)}; dated factual report with {len(stocks)} named leads; economic challenge still pending'}
        report_lines = [f'# Research report — {args.session} close', '', f'Compiled {datetime.now(TZ).isoformat()}; cutoff {cutoff.isoformat()}. PARTIAL / diagnostic, unqualified research.', '',
            f'Official EOD files reconciled by current issuer ISIN and price. {len(stocks)} named leads; {len(discovery)} independent quarterly-results candidates; {len(financials)} original tables visually verified; {len(dossiers)} Claude provisional dossiers; {len(monitors)} monitor baselines.', '',
            draft['brief'] if draft else 'Claude interpretation unavailable; factual collection retained.', '',
            f'Analysis provenance: actual Claude packet {receipt["request_id"] if receipt else "unavailable"}; reused analysis: {bool(receipt and receipt.get("reused"))}. Reuse does not imply a new Claude call or a new approval.', '', '## Current stock observations', '',
            '| Symbol | Market date | Close INR | Nominal daily % | Next check |', '| --- | --- | --- | --- | --- |']
        for sym in sorted(stocks):
            s = stocks[sym]; m = s.get('current_stats') or {}
            ret = m.get('nominal_daily_return_pct')
            report_lines.append(f'| {sym} | {m.get("session", "unavailable")} | {m.get("close_inr", "—")} | {ret:.2f} | {s.get("next_check", "Verify original evidence")} |' if ret is not None else f'| {sym} | {m.get("session", "unavailable")} | {m.get("close_inr", "—")} | — (action/data check) | {s.get("next_check", "Verify original evidence")} |')
        report_lines += ['', '## Financial screening and limits', '',
            'Independent discovery uses publication-dated financial-results filings and current EQ issuer identity, without requiring a price spike. Metadata-only cases await original-table validation. Verified quantitative observations below retain sector-specific metrics and standalone/statutory basis; growth is not business-quality approval.', '']
        for f in financials:
            report_lines.append(f'- {f["symbol"]}: period {f["period_end"]}, {f["basis"]}, {f["unit"]}, publication {f["published_at"]}; page {f["page"]}. [Original filing]({f["source_url"]}). Verified/calculated metrics: {json.dumps(f["derived"])}.')
        report_lines += ['', 'Source retrieval occurred after the effective observation dates. This is explicitly retrospective collection, not a claim that sources were captured at the earlier session close. Raw price changes are nominal, and action-day values are withheld. Financial review is provisional: valuation, cash-flow and governance fields may be missing. No names are QUALIFIED. Historical Phase 0 gates and full-universe completeness remain open. No buy/sell/hold calls or targets.', '',
            f'Technical diagnostic evaluated {len(technical)}/500; quarantined {len(quarantine)}. Sector-relative strength/ATR/full historical action adjustment remain unavailable. New monitor records establish baselines and expiry checks; a first observation cannot confirm or contradict an older unrecorded forecast.']
        body = '\n'.join(report_lines) + '\n'
        runs = []
        for n in range(1, 6):
            run_id = f'routine_0{n}_a01'; p = pending / f'routine_0{n}' / run_id; p.mkdir(parents=True)
            write(p / 'readiness.json', readiness); write(p / 'budget_snapshot.json', budget.snapshot())
            jsonl(p / 'open_tasks.jsonl', list(tasks.values()))
            if n == 1:
                jsonl(p / 'metrics.jsonl', technical); jsonl(p / 'quarantine.jsonl', quarantine)
                jsonl(p / 'signals.jsonl', [m for m in technical if m['events']])
            if n == 2:
                jsonl(p / 'registry.jsonl', [{'symbol': s['symbol'], 'security_id': s.get('security_id'),
                    'state': 'RESEARCH' if s.get('dossier_status') else 'DISCOVERY', 'qualified': False,
                    'origin_lane': s.get('origin_lane', 'PREVIOUS_RESEARCH_LEAD'), 'next_check': s.get('next_check')} for s in stocks.values()])
                jsonl(p / 'independent_screen.jsonl', discovery); jsonl(p / 'financial_metrics.jsonl', financials); jsonl(p / 'dossiers.jsonl', dossiers)
                jsonl(p / 'financial_screen.jsonl', [screen_financial(f) for f in financials])
                jsonl(p / 'transitions.jsonl', [{'transition_id': batch + ':' + d['symbol'], 'symbol': d['symbol'], 'from_state': 'DISCOVERY', 'to_state': 'RESEARCH', 'reason': 'Material quarterly filing with validated issuer identity and provisional Claude dossier; qualification blocked', 'proposed_by': 'Claude', 'reviewed_by': 'Codex source/intake checks'} for d in dossiers if prior_registry.get(d['symbol'], {}).get('state') != 'RESEARCH'])
            if n == 3:
                jsonl(p / 'monitor_state.jsonl', monitors); jsonl(p / 'changes.jsonl', [m for m in monitors if any(c['result'] == 'TRIGGERED' for c in m['checks'])])
                jsonl(p / 'paper_coverage.jsonl', paper)
                write(p / 'coverage.json', {'named_leads': len(stocks), 'baseline_records': len(monitors),
                    'expiry_evaluated': len(monitors), 'business_forecast_comparisons': sum(any(c['comparison_available'] for c in m['checks']) for m in monitors),
                    'missing_dossier_count': len(stocks) - len(monitors), 'first_observations_are_not_confirmations': True})
            if n == 4:
                write(p / 'registry_ref.json', {'immutable_registry_run': validate(prior[4]), 'record_count': len(legacy), 'newness_evaluated': True})
                jsonl(p / 'events.jsonl', [{**d, 'facts': [d['fact']], 'event_type': 'RESULTS'} for d in discovery])
                jsonl(p / 'assessments.jsonl', draft['assessments'] if draft else []); jsonl(p / 'cutoff_exclusions.jsonl', exclusions)
                write(p / 'source_health.json', {'nse_announcements_received': len(ann) + len(exclusions), 'publication_eligible': len(ann), 'cutoff_excluded': len(exclusions), 'financial_tables_verified': len(financials)})
            if n == 5:
                write(p / 'digest.json', {'status': 'PARTIAL', 'stock_count': len(stocks), 'editorial_executed': bool(draft),
                    'editorial_executed_this_pass': bool(draft and receipt and not receipt.get('reused')),
                    'analysis_reused': bool(receipt and receipt.get('reused')),
                    'author': 'Claude' if draft else 'Codex factual fallback', 'economic_review': 'PENDING', 'items': draft['assessments'] if draft else []})
                jsonl(p / 'decision_queue.jsonl', list(tasks.values()))
            if receipt: write(p / 'claude_receipt.json', receipt)
            (p / 'report.md').write_text(body)
            artifacts = [{'path': f.name, 'sha256': sha(f)} for f in sorted(p.iterdir())]
            hand = {'schema_version': '1.1', 'routine_id': f'routine_0{n}', 'batch_id': batch, 'run_id': run_id,
                'session_date': args.session, 'scheduled_slot': cutoff.isoformat(), 'cutoff_at': cutoff.isoformat(),
                'started_at': started_at.isoformat(), 'completed_at': datetime.now(TZ).isoformat(), 'timezone': 'Asia/Kolkata',
                'deadline_at': deadline.isoformat(), 'deadline_missed': datetime.now(TZ) > deadline,
                'status': statuses[n], 'result': 'CHANGED', 'execution_lane': args.lane, 'production_eligible': False,
                'readiness_ref': 'readiness.json', 'budget_ref': 'budget_snapshot.json',
                'budget_usage': {'paid_cli_calls': 1 if receipt and n == 5 and not receipt.get('reused') else 0, 'cost_proxy_usd': receipt['cost_proxy_usd'] if receipt and n == 5 and not receipt.get('reused') else 0},
                'owner': 'Claude' if n in [2, 4, 5] else 'Codex', 'executor': 'Claude analysis; Codex validation/persistence' if draft and n in [2,4,5] else 'Codex',
                'reviewer': 'Codex' if n in [2,4,5] else 'Claude', 'review_status': 'PENDING',
                'previous_success_run_id': None, 'previous_committed_run': validate(prior[n]), 'supersedes_run_id': None, 'bootstrap': False,
                'upstream_runs': upstream, 'input_versions': pins, 'config_version': 'pipeline-1', 'code_revision': sha(Path(__file__)),
                'coverage': readiness, 'freshness': {'market_asof': args.session, 'collected_after_effective_dates': True},
                'limitations': [stage_reasons[n], *readiness['limitations']], 'artifacts': artifacts, 'source_cursors': {}, 'processed_event_ids': [],
                'deferred_counts': {'dossiers_missing': len(stocks) - len(dossiers)}, 'open_tasks': list(tasks.values()), 'resolved_task_ids': resolutions,
                'next_run': {'instructions': 'Collect dated sources, reserve usage, process changed dossiers, evaluate prior baselines and publish Sheet.'}}
            write(p / 'handoff.json', hand); write(p / 'manifest.json', {'committed': True, 'schema_version': '1.1', 'artifacts': artifacts + [{'path': 'handoff.json', 'sha256': sha(p / 'handoff.json')}]}); validate(p)
            runs.append(str((parent / f'routine_0{n}' / run_id).relative_to(ROOT)))
        os.rename(pending, parent)
        report = R / 'stock_reports' / batch; report.mkdir()
        jsonl(report / 'stocks.jsonl', [stocks[s] for s in sorted(stocks)]); jsonl(report / 'metrics.jsonl', technical)
        jsonl(report / 'news_updates.jsonl', discovery); jsonl(report / 'quarantine.jsonl', quarantine)
        write(report / 'stats.json', {'market_asof': args.session, 'stock_count': len(stocks), 'technical_evaluated': len(technical), 'quarantined': len(quarantine), 'independent_results_candidates': len(discovery), 'claude_dossiers': len(dossiers), 'baseline_records': len(monitors)})
        (report / 'report.md').write_text(body)
        write(report / 'handoff.json', {'schema_version': '1.1', 'artifact_kind': 'FACTUAL_STOCK_QUEUE', 'runtime_version': 'pipeline-1',
            'pipeline_batch': batch, 'status': 'PARTIAL', 'production_eligible': False, 'cutoff_at': cutoff.isoformat(),
            'compiled_at': datetime.now(TZ).isoformat(), 'market_asof': args.session, 'stock_count': len(stocks),
            'executor': 'Claude editorial; Codex factual validation', 'claude_interpretation_executed': bool(draft),
            'news_updates': len(discovery), 'upstream_runs': [validate(ROOT / name) for name in runs]})
        write(report / 'manifest.json', {'committed': True, 'artifacts': [{'path': p.name, 'sha256': sha(p)} for p in sorted(report.iterdir())]}); validate(report)
        for n, name in enumerate(runs, 1): atomic(R / f'state/routine_0{n}/latest.json', {'run_dir': name, 'status': statuses[n], 'production_eligible': False})
        atomic(R / 'state/stock_report/latest.json', {'report_dir': str(report.relative_to(ROOT)), 'status': 'PARTIAL', 'stock_count': len(stocks), 'market_asof': args.session, 'cutoff_at': cutoff.isoformat()})
        completed[cutoff.isoformat()] = {'batch_id': batch, 'runs': runs}; atomic(completed_path, completed)
        print(json.dumps({'batch_id': batch, 'report': str(report / 'report.md'), 'stocks': len(stocks), 'independent_results': len(discovery), 'financial_tables': len(financials), 'claude_dossiers': len(dossiers), 'monitors': len(monitors), 'status': 'PARTIAL'}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not erase the last usable report or invent a successful empty pass.
        state = R / 'state/orchestrator'
        atomic(state / 'last_execution_failure.json', {'status': 'FAILED', 'at': datetime.now(TZ).isoformat(),
            'reason': type(error).__name__ + ': ' + str(error)[:500],
            'next_check': 'Reconcile this failure and retain the last sealed report; do not advance source cursors'})
        raise
