"""Compile a dated factual stock queue from committed evidence; no paid calls."""
import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'research'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def load_source(filename):
    candidates = []
    for manifest_path in (R / 'runs').glob('*/*/*/manifest.json'):
        manifest = json.loads(manifest_path.read_text())
        if not manifest.get('committed') or not any(a['path'] == filename for a in manifest['artifacts']):
            continue
        directory = manifest_path.parent
        for artifact in manifest['artifacts']:
            assert sha(directory / artifact['path']) == artifact['sha256'], str(directory)
        handoff = json.loads((directory / 'handoff.json').read_text())
        candidates.append((handoff['completed_at'], directory))
    if not candidates:
        return None, []
    directory = max(candidates, key=lambda item: item[0])[1]
    return directory, [json.loads(line) for line in (directory / filename).read_text().splitlines()]


def main():
    state = R / 'state/stock_report'
    state.mkdir(parents=True, exist_ok=True)
    with (R / 'state/orchestrator/writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pointer = state / 'latest.json'
        if pointer.exists():
            current = ROOT / json.loads(pointer.read_text())['report_dir']
            hand = json.loads((current / 'handoff.json').read_text())
            if hand.get('runtime_version') == 'pipeline-1':
                manifest = json.loads((current / 'manifest.json').read_text())
                assert manifest['committed']
                for item in manifest['artifacts']:
                    assert sha(current / item['path']) == item['sha256']
                print(json.dumps({'reused': True, 'runtime': 'pipeline-1', 'stocks': hand['stock_count'],
                    'market_asof': hand['market_asof'], 'report': str(current / 'report.md')}))
                return
        technical_dir, metrics = load_source('metrics.jsonl')
        news_dir, events = load_source('event_registry.jsonl')
        if not metrics and not events:
            raise RuntimeError('No committed evidence payloads available')
        stocks = {}
        for metric in metrics:
            if not metric['events']:
                continue
            stocks[metric['symbol']] = {
                'symbol': metric['symbol'], 'security_id': metric['security_id'],
                'record_kind': 'RESEARCH_LEAD', 'qualified': False,
                'technical': {key: metric[key] for key in ['session', 'close_inr', 'return_pct', 'relative_volume', 'events']},
                'technical_source': str(technical_dir / 'metrics.jsonl'),
                'technical_verification': 'DIAGNOSTIC_ONLY', 'company_events': [],
                'next_check': 'Refresh prices and verify actions/identity before evaluating persistence; investigate the business separately.',
                'owner': 'Codex verification; Claude subsequent research',
            }
        # Explicit issuer mapping; counterparties/sector-only stories do not imply stock beneficiaries.
        mappings = {'news-kec1030': 'KEC', 'news-kec1014': 'KEC', 'news-ncc': 'NCC',
                    'news-sepc': 'SEPC', 'news-ashoka': 'ASHOKA', 'news-ircon': 'IRCON',
                    'news-bajel': 'BAJEL', 'news-tcs': 'TCS', 'news-dmart': 'DMART',
                    'news-anandrathi': 'ANANDRATHI'}
        for event in events:
            symbol = mappings.get(event['event_id'])
            if symbol is None:
                continue
            row = stocks.setdefault(symbol, {'symbol': symbol, 'security_id': None,
                'record_kind': 'RESEARCH_LEAD', 'qualified': False, 'technical': None,
                'company_events': [], 'owner': 'Codex verification; Claude subsequent research'})
            row['company_events'].append({key: event[key] for key in ['event_id', 'published_date', 'event_type', 'verification_status', 'facts', 'research_question']})
            row['company_events'][-1]['source_record'] = str(news_dir / 'events.jsonl')
            row['next_check'] = event['research_question']
        ordered = [stocks[symbol] for symbol in sorted(stocks)]
        lineage = [{'run_dir': str(p.relative_to(ROOT)), 'manifest_sha256': sha(p / 'manifest.json')}
                   for p in [technical_dir, news_dir] if p is not None]
        # A manual cutoff refresh may have newer official observations than the
        # scheduled source workers. Preserve it when its parent used the same
        # committed source lineage; never replace fresh prices with old metrics.
        pointer_path = state / 'latest.json'
        if pointer_path.exists():
            current = ROOT / json.loads(pointer_path.read_text())['report_dir']
            current_handoff = json.loads((current / 'handoff.json').read_text())
            source_asof = max((item['session'] for item in metrics), default='')
            if current_handoff.get('market_asof', '') > source_asof:
                for parent_ref in current_handoff.get('upstream_runs', []):
                    parent_path = ROOT / parent_ref['run_dir']
                    parent_handoff = json.loads((parent_path / 'handoff.json').read_text())
                    if parent_handoff.get('upstream_runs') == lineage:
                        assert sha(parent_path / 'manifest.json') == parent_ref['manifest_sha256']
                        manifest = json.loads((current / 'manifest.json').read_text())
                        for artifact in manifest['artifacts']:
                            assert sha(current / artifact['path']) == artifact['sha256']
                        print(json.dumps({'reused': True, 'preserved_newer_snapshot': True,
                            'stocks': current_handoff['stock_count'], 'report': str(current / 'report.md')}))
                        return
        signature = hashlib.sha256(json.dumps({'lineage': lineage, 'compiler': sha(Path(__file__))}, sort_keys=True).encode()).hexdigest()[:12]
        target = R / 'stock_reports' / ('evidence_' + signature)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            manifest = json.loads((target / 'manifest.json').read_text())
            for artifact in manifest['artifacts']:
                assert sha(target / artifact['path']) == artifact['sha256']
            print(json.dumps({'reused': True, 'stocks': len(ordered), 'report': str(target / 'report.md')}))
            return
        temp = Path(tempfile.mkdtemp(prefix='.pending_', dir=target.parent))
        now = datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
        (temp / 'stocks.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in ordered))
        lines = ['# Stock research queue — concrete evidence list', '',
            f'Compiled {now}. **{len(ordered)} named research leads; no qualified investments.**', '',
            'Market observations are dated **9 October 2026**; company news covers **5–11 October**. These are historical observations, not current prices or freshly detected signals. The compiler copies facts and existing questions from committed records. Claude interpretation/review is pending; no Claude assessment is claimed.', '',
            '## Company disclosures: orders and earnings', '',
            '| Stock | Evidence date | Concrete selection reason | Verification | Next research check |',
            '| --- | --- | --- | --- | --- |']
        for row in ordered:
            for event in row['company_events']:
                facts = ' '.join(event['facts']).replace('|', '/')
                lines.append(f"| {row['symbol']} | {event['published_date']} | {facts} | {event['verification_status']} | {event['research_question']} |")
        lines += ['', f'Company-event source: [committed events]({news_dir / "events.jsonl"}). Original URLs and provenance: [evidence]({news_dir / "evidence.jsonl"}).', '',
            '## Technical research leads', '',
            'All values below are from 9 October. Relative volume = session volume / median of the preceding 20 sessions. All comparisons remain diagnostic because Phase 0 is uncertified.', '',
            '| Stock | Close ₹ | Daily return | Relative volume | Concrete signal |',
            '| --- | --- | --- | --- | --- |']
        for row in ordered:
            metric = row['technical']
            if metric:
                lines.append(f"| {row['symbol']} | {metric['close_inr']:.2f} | {metric['return_pct']:+.2f}% | {metric['relative_volume']:.2f}× | {', '.join(metric['events'])} |")
        lines += ['', f'Source: [metrics]({technical_dir / "metrics.jsonl"}); [formulas]({technical_dir / "config.json"}); [quarantined coverage]({technical_dir / "quarantine.jsonl"}).', '',
            'A moving-average crossing or higher volatility alone does not establish business quality. Drawdown events (AMBER, JYOTICNC, IKS) are risk-review cases. Volatility-only names are observation cases, not automatically opportunities.', '',
            '## Government-linked research', '',
            'The government stories remain sector leads until a listed recipient or supplier is evidenced. The BrahMos award is to a private company; BigEndian financing and the SME fund do not establish awards for any listed company. Chennai project inaugurations cannot be treated as new contract awards without package details. These stories remain in the news report and are not used to invent stock beneficiaries.', '',
            '## Follow-up ownership and limits', '',
            '- Codex: refresh current prices; validate original filings, issuer identity, contract scope, and dated financial denominators. Keep publication dates and standalone/consolidated bases distinct.',
            '- Claude: evaluate business quality, order economics, earnings quality and thesis implications when authenticated execution and budget controls are ready.',
            '- KEC announcements require date/overlap reconciliation before summation; SEPC signing may formalize a previously announced LOA; ANANDRATHI numeric details remain withheld.',
            '- No buy/sell/hold calls, price targets, live-book changes or R2 state promotions are generated. Named leads remain visible even while qualification is blocked.', '',
            'Next compiler run resolves the latest committed metrics/registry, deduplicates by symbol, keeps unchanged source dates, and reuses the same result for identical inputs. Analytical workers consume stocks.jsonl as a research queue, not proof of qualification.']
        (temp / 'report.md').write_text('\n'.join(lines) + '\n')
        save(temp / 'handoff.json', {'schema_version': '1.1', 'artifact_kind': 'FACTUAL_STOCK_QUEUE',
            'status': 'PARTIAL', 'production_eligible': False, 'compiled_at': now,
            'executor': 'Codex deterministic compiler', 'claude_interpretation_executed': False,
            'stock_count': len(ordered), 'technical_count': sum(row['technical'] is not None for row in ordered),
            'company_event_stock_count': sum(bool(row['company_events']) for row in ordered),
            'market_asof': '2026-10-09', 'news_window': ['2026-10-05', '2026-10-11'],
            'upstream_runs': lineage, 'metered_calls': 0,
            'next_run': 'Use latest committed evidence; retain source dates, verification gaps and owner queue. Never promote these leads automatically.'})
        artifacts = [{'path': path.name, 'sha256': sha(path)} for path in sorted(temp.iterdir())]
        save(temp / 'manifest.json', {'committed': True, 'signature': signature, 'artifacts': artifacts})
        assert len({row['symbol'] for row in ordered}) == len(ordered)
        assert all(not row['qualified'] for row in ordered)
        os.rename(temp, target)
        pointer = state / 'latest.tmp'
        save(pointer, {'report_dir': str(target.relative_to(ROOT)), 'status': 'PARTIAL', 'stock_count': len(ordered)})
        os.replace(pointer, state / 'latest.json')
        print(json.dumps({'report': str(target / 'report.md'), 'stocks': len(ordered), 'market_asof': '2026-10-09', 'metered_calls': 0}))


if __name__ == '__main__':
    main()
