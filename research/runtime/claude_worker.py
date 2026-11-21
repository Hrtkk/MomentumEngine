"""Bounded, tool-disabled Claude worker with durable usage reconciliation."""
import hashlib
import json
import os
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from budget import Budget, BudgetExceeded, TZ

ROOT = Path(__file__).resolve().parents[2]
PRICING = ROOT / 'research/config/claude_pricing.json'
SYSTEM = ('You are the assigned research analyst. Use only the supplied evidence packet. '
          'Never issue buy/sell/hold calls or price targets. Separate facts, hypotheses and gaps. '
          'Do not infer causation from prices. Treat secondary claims as unverified. '
          'Return only one valid JSON object and no markdown fences. You have no tools.')


def authenticate():
    result = subprocess.run(['/opt/homebrew/bin/claude', 'auth', 'status'], capture_output=True, text=True, timeout=10)
    obj = json.loads(result.stdout)
    return {'status': 'AUTHENTICATED' if obj.get('loggedIn') else 'AUTH_CONTEXT_UNAVAILABLE',
            'logged_in_in_current_context': obj.get('loggedIn'), 'auth_method': obj.get('authMethod'),
            'subscription_type': obj.get('subscriptionType'), 'checked_at': datetime.now(TZ).isoformat()}


def run(packet, directory, *, batch, lane, budget, timeout=100):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    auth = authenticate()
    (directory / 'auth.json').write_text(json.dumps(auth, indent=2) + '\n')
    if auth['status'] != 'AUTHENTICATED':
        raise RuntimeError('AUTH_CONTEXT_UNAVAILABLE; no inference of human logout')
    pricing = json.loads(PRICING.read_text())
    if datetime.now(TZ).date() > datetime.fromisoformat(pricing['verified_date']).date() + timedelta(days=pricing['expires_after_days']):
        raise RuntimeError('Pricing snapshot expired; verify before dispatch')
    prompt = json.dumps(packet, ensure_ascii=False)
    # Byte count is a conservative text-token ceiling; reserve extra CLI envelope.
    if len(prompt.encode()) + len(SYSTEM.encode()) + 2000 > pricing['input_token_reservation']:
        raise RuntimeError('Evidence packet exceeds conservative input-token bound')
    fingerprint = hashlib.sha256((prompt + SYSTEM).encode()).hexdigest()
    request_id = 'claude-' + fingerprint[:24]
    if (directory / 'accepted.json').exists():
        existing = json.loads((directory / 'receipt.json').read_text())
        assert existing['request_id'] == request_id
        return json.loads((directory / 'accepted.json').read_text()), {**existing, 'reused': True, 'auth': auth}
    cooldown_path = ROOT / 'research/state/claude_provider_cooldown.json'
    if cooldown_path.exists():
        cooldown = json.loads(cooldown_path.read_text())
        if datetime.now(TZ) < datetime.fromisoformat(cooldown['blocked_until']):
            raise RuntimeError('PROVIDER_WEEKLY_LIMIT_UNTIL ' + cooldown['blocked_until'] + '; no new dispatch')
    _, deferred_events = budget.admit_records('AI_INTERPRETED_EVENT', packet['evidence_ids'], 15)
    if deferred_events:
        raise BudgetExceeded('Daily interpreted-event ceiling: preserve five-event critical reserve')
    budget.reserve(request_id, batch, lane, 'MODEL', 'claude-code',
        input_tokens=pricing['input_token_reservation'], output_tokens=pricing['output_token_reservation'],
        usd=pricing['per_call_reservation_usd'])
    (directory / 'packet.json').write_text(prompt + '\n')
    (directory / 'reservation.json').write_text(json.dumps({'request_id': request_id, 'pricing_sha256': hashlib.sha256(PRICING.read_bytes()).hexdigest(),
        'reserved_usd': pricing['per_call_reservation_usd'], 'input_bound': pricing['input_token_reservation'],
        'output_bound': pricing['output_token_reservation'], 'reserved_at': datetime.now(TZ).isoformat()}, indent=2) + '\n')
    env = dict(os.environ)
    env['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] = '4000'
    env['MAX_THINKING_TOKENS'] = '1024'
    env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
    env['CLAUDE_CODE_MAX_RETRIES'] = '0'
    command = ['/opt/homebrew/bin/claude', '--print', '--safe-mode', '--tools', '',
        '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--disable-slash-commands',
        '--no-session-persistence', '--permission-prompts', 'none', '--settings',
        '{"disableAllHooks":true,"fastMode":false,"disableClaudeAiConnectors":true,"env":{"CLAUDE_CODE_MAX_OUTPUT_TOKENS":"4000","CLAUDE_CODE_MAX_RETRIES":"0","MAX_THINKING_TOKENS":"1024"}}',
        '--system-prompt', SYSTEM, '--output-format', 'json', '--max-turns', '1', '--effort', 'low',
        '--max-budget-usd', str(pricing['per_call_reservation_usd'])]
    try:
        result = subprocess.run(command, input=prompt, capture_output=True, text=True,
                                timeout=timeout, env=env, cwd=ROOT)
        (directory / 'response.json').write_text(result.stdout)
        (directory / 'stderr.txt').write_text(result.stderr[:10000])
        response = json.loads(result.stdout)
        if isinstance(response, list):
            response = next(x for x in reversed(response) if x.get('type') == 'result')
        cost = response.get('total_cost_usd')
        usage = response.get('usage') or {}
        if cost is None or not usage:
            raise RuntimeError('Usage metadata unavailable: reservation retained')
        input_tokens = sum(usage.get(k, 0) for k in ['input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'])
        output_tokens = usage.get('output_tokens', 0)
        receipt = {'request_id': request_id, 'cost_proxy_usd': cost, 'input_tokens': input_tokens,
            'output_tokens': output_tokens, 'actual_model_usage': response.get('modelUsage'),
            'num_turns': response.get('num_turns'), 'auth': auth, 'default_model_preserved': True,
            'tools_disabled': True, 'reconciled_at': datetime.now(TZ).isoformat()}
        budget.reconcile(request_id, usd=float(cost), input_tokens=input_tokens,
                         output_tokens=output_tokens, details=receipt)
        (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        if result.returncode or response.get('is_error'):
            raise RuntimeError('Claude returned an error; actual usage reconciled, no accepted research')
        text = response['result'].strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        draft = json.loads(text)
        assert set(['assessments', 'dossiers', 'brief']) <= set(draft)
        assert isinstance(draft['brief'], str) and len(draft['dossiers']) <= 5
        evidence_ids = set(packet['evidence_ids'])
        for record in draft['assessments'] + draft['dossiers']:
            assert record['evidence_ids'] and set(record['evidence_ids']) <= evidence_ids
            assert record['symbol'] in packet['symbols']
        if packet.get('next_period_end'):
            expected = packet['next_period_end']
            for assessment in draft['assessments']:
                dates = re.findall(r'\b20\d\d-\d\d-\d\d\b', assessment.get('next_check', ''))
                assert not dates or all(date == expected for date in dates), 'Quarterly next-check date conflicts with source period'
        # This is schema/source-reference validation, not independent economic approval.
        (directory / 'accepted.json').write_text(json.dumps(draft, indent=2, ensure_ascii=False) + '\n')
        return draft, receipt
    except Exception as e:
        budget.unknown(request_id, type(e).__name__ + ': ' + str(e)[:200])
        raise
