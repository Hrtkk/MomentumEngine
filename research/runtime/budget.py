"""Durable overlay-only resource reservations. Unknown outcomes keep their reservation."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Kolkata')
DEFAULT_DB = Path(__file__).resolve().parents[1] / 'state/budget.sqlite3'


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, dispatched_at TEXT, day TEXT, month TEXT,
                batch TEXT, lane TEXT, kind TEXT, source TEXT, input_tokens INTEGER,
                output_tokens INTEGER, usd REAL, storage_bytes INTEGER,
                state TEXT, actual_json TEXT)''')
            c.execute('CREATE TABLE IF NOT EXISTS admitted_records (day TEXT, kind TEXT, record_id TEXT, PRIMARY KEY(day,kind,record_id))')

    @contextmanager
    def transaction(self):
        c = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        c.row_factory = sqlite3.Row
        try:
            c.execute('PRAGMA synchronous=FULL')
            c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def reserve(self, key, batch, lane, kind, source, input_tokens=0, output_tokens=0,
                usd=0., storage_bytes=0, now=None, critical=False):
        now = now or datetime.now(TZ)
        assert now.tzinfo and lane in ['FAST', 'OVERNIGHT', 'EVENT', 'EVALUATION']
        assert kind in ['MODEL', 'SOURCE']
        assert min(input_tokens, output_tokens, usd, storage_bytes) >= 0
        if input_tokens > 20000 or output_tokens > 4000:
            raise BudgetExceeded('Per-call token ceiling')
        day, month = now.astimezone(TZ).date().isoformat(), now.astimezone(TZ).strftime('%Y-%m')
        with self.transaction() as c:
            if c.execute('SELECT 1 FROM requests WHERE id=?', (key,)).fetchone():
                raise BudgetExceeded('Request ID already reserved/dispatched; reconcile, never replay blindly')
            all_rows = [dict(r) for r in c.execute('SELECT * FROM requests')]
            daily = [r for r in all_rows if r['day'] == day]
            monthly = [r for r in all_rows if r['month'] == month]
            models = [r for r in daily if r['kind'] == 'MODEL']
            sources = [r for r in daily if r['kind'] == 'SOURCE']
            if kind == 'MODEL':
                if any(r['kind'] == 'MODEL' and r['state'] in ['RESERVED', 'UNKNOWN'] for r in all_rows):
                    raise BudgetExceeded('One model request at a time; unknown usage needs reconciliation')
                ceiling = {'FAST': 8, 'OVERNIGHT': 24, 'EVENT': 8, 'EVALUATION': 24}[lane]
                counted_lane = 'OVERNIGHT' if lane == 'EVALUATION' else lane
                lane_rows = [r for r in models if ('OVERNIGHT' if r['lane'] == 'EVALUATION' else r['lane']) == counted_lane]
                if len(models) >= 40 or len(lane_rows) >= ceiling:
                    raise BudgetExceeded('Daily/lane model-request ceiling')
                if sum(r['input_tokens'] for r in models) + input_tokens > (300000 if critical else 240000):
                    raise BudgetExceeded('Input tokens/reserve exhausted')
                if sum(r['output_tokens'] for r in models) + output_tokens > (40000 if critical else 32000):
                    raise BudgetExceeded('Output tokens/reserve exhausted')
                # A batch cannot obtain another lane allowance by crossing midnight.
                if sum(r['kind'] == 'MODEL' and r['batch'] == batch for r in all_rows) >= ceiling:
                    raise BudgetExceeded('Per-batch model ceiling')
            else:
                if len(sources) >= (1000 if critical else 800):
                    raise BudgetExceeded('Daily source request/critical reserve ceiling')
                if sum(r['source'] == source for r in sources) >= 300:
                    raise BudgetExceeded('Per-source ceiling')
                if sum(r['kind'] == 'SOURCE' and r['state'] == 'RESERVED' for r in all_rows) >= 2:
                    raise BudgetExceeded('At most two fetches in flight')
            if sum(r['usd'] for r in daily) + usd > (5 if critical else 4):
                raise BudgetExceeded('Daily spend/critical reserve ceiling')
            if sum(r['usd'] for r in monthly) + usd > (100 if critical else 80):
                raise BudgetExceeded('Monthly spend/critical reserve ceiling')
            if sum(r['storage_bytes'] for r in daily) + storage_bytes > (250 if critical else 200) * 1024**2:
                raise BudgetExceeded('Daily storage/critical reserve ceiling')
            c.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (key, now.isoformat(), day, month, batch, lane, kind, source,
                       input_tokens, output_tokens, usd, storage_bytes, 'RESERVED', None))
        return key

    def reconcile(self, key, *, usd=None, input_tokens=None, output_tokens=None, storage_bytes=None, details=None):
        with self.transaction() as c:
            row = c.execute('SELECT * FROM requests WHERE id=?', (key,)).fetchone()
            if not row or row['state'] == 'RECONCILED':
                raise ValueError('Missing or already reconciled request')
            values = {k: row[k] if v is None else v for k, v in dict(usd=usd, input_tokens=input_tokens,
                output_tokens=output_tokens, storage_bytes=storage_bytes).items()}
            if any(values[k] < 0 or values[k] > row[k] for k in values):
                c.execute('UPDATE requests SET state=?,actual_json=? WHERE id=?',
                          ('UNKNOWN', json.dumps(details or values), key))
                # Commit the incident before raising outside this transaction.
                violation = True
            else:
                c.execute('UPDATE requests SET usd=?,input_tokens=?,output_tokens=?,storage_bytes=?,state=?,actual_json=? WHERE id=?',
                          (values['usd'], values['input_tokens'], values['output_tokens'], values['storage_bytes'],
                           'RECONCILED', json.dumps(details or {}), key))
                violation = False
        if violation:
            raise BudgetExceeded('Observed usage exceeded reservation: retained UNKNOWN, stop and reconcile')

    def unknown(self, key, reason):
        with self.transaction() as c:
            c.execute('UPDATE requests SET state=?,actual_json=? WHERE id=? AND state!=?',
                      ('UNKNOWN', json.dumps({'reason': reason}), key, 'RECONCILED'))

    def snapshot(self):
        with self.transaction() as c:
            return [dict(r) for r in c.execute('SELECT * FROM requests ORDER BY dispatched_at,id')]

    def admit_records(self, kind, record_ids, limit, now=None):
        """Unique record ceilings survive overlapping windows, retries and restarts."""
        day = (now or datetime.now(TZ)).astimezone(TZ).date().isoformat()
        admitted, deferred = [], []
        with self.transaction() as c:
            seen = {r[0] for r in c.execute('SELECT record_id FROM admitted_records WHERE day=? AND kind=?', (day, kind))}
            for record_id in dict.fromkeys(record_ids):
                if record_id in seen:
                    admitted.append(record_id)
                elif len(seen) < limit:
                    c.execute('INSERT INTO admitted_records VALUES (?,?,?)', (day, kind, record_id))
                    seen.add(record_id); admitted.append(record_id)
                else:
                    deferred.append(record_id)
        return admitted, deferred

    def reconcile_observed_incident(self, key, *, usd, input_tokens, output_tokens, evidence):
        """Explicit operator reconciliation from a complete provider receipt; retain breach evidence."""
        assert evidence and usd >= 0 and input_tokens >= 0 and output_tokens >= 0
        with self.transaction() as c:
            row = c.execute('SELECT * FROM requests WHERE id=?', (key,)).fetchone()
            assert row and row['state'] == 'UNKNOWN'
            # Known usage replaces uncertain estimates; it never erases the incident.
            detail = {'incident': 'RESERVATION_OVERRUN', 'original_reservation': dict(row),
                      'provider_receipt': evidence, 'resolution': 'Observed usage charged; output rejected; worker corrected before new dispatch'}
            c.execute('UPDATE requests SET usd=?,input_tokens=?,output_tokens=?,state=?,actual_json=? WHERE id=?',
                      (usd, input_tokens, output_tokens, 'RECONCILED_WITH_INCIDENT', json.dumps(detail), key))
