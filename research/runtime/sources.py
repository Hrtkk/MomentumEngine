"""Allowlisted, bounded public-source collection. Never invokes the live batch."""
import hashlib
import json
import urllib.request
import urllib.error
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from budget import Budget, TZ

ALLOWED = {'www.nseindia.com', 'nsearchives.nseindia.com', 'archives.nseindia.com',
           'www.hcltech.com', 'www.rbl.bank.in', 'www.pib.gov.in'}
MAX_BYTES = 4 * 1024**2


def fetch(url, target, *, batch, lane, budget, max_bytes=MAX_BYTES):
    target = Path(target)
    meta = target.with_name(target.name + '.source.json')
    if target.exists() and meta.exists():
        record = json.loads(meta.read_text())
        assert record['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
        assert record['url'] == url
        return record
    assert urlparse(url).scheme == 'https' and urlparse(url).hostname in ALLOWED
    research = Path(__file__).resolve().parents[1]
    retained = sum(p.stat().st_size for p in research.rglob('*') if p.is_file())
    if retained + max_bytes > 10 * 1024**3:
        raise RuntimeError('Active research storage ceiling reached; no provenance deletion allowed')
    # One initial request; transient failures remain retryable on the next pass.
    key = 'source-' + uuid.uuid4().hex
    budget.reserve(key, batch, lane, 'SOURCE', urlparse(url).hostname, storage_bytes=max_bytes)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
        with urllib.request.urlopen(req, timeout=20) as response:
            assert urlparse(response.url).hostname in ALLOWED, 'Unapproved redirect'
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ValueError('Source exceeds reserved byte ceiling')
            content_type = response.headers.get('Content-Type', '')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        record = {'url': url, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body),
            'retrieved_at': datetime.now(TZ).isoformat(), 'publication_at': None,
            'content_type': content_type, 'budget_request_id': key}
        meta.write_text(json.dumps(record, indent=2) + '\n')
        budget.reconcile(key, storage_bytes=len(body), details=record)
        return record
    except Exception as e:
        # Count the request and keep worst-case storage if completion is uncertain.
        budget.unknown(key, type(e).__name__ + ': ' + str(e)[:200])
        raise


def validate_bhav(path, expected):
    import pandas as pd
    frame = pd.read_csv(path)
    frame.columns = frame.columns.str.strip()
    frame['SYMBOL'] = frame['SYMBOL'].str.strip()
    frame['SERIES'] = frame['SERIES'].str.strip()
    dates = pd.to_datetime(frame.DATE1.str.strip(), format='%d-%b-%Y').dt.strftime('%Y-%m-%d')
    if frame.empty or not dates.eq(expected).all():
        raise ValueError('Internal session date mismatch; holiday re-serves are not accepted')
    if frame.duplicated(['SYMBOL', 'SERIES']).any():
        raise ValueError('Duplicate symbol/series')
    return frame
