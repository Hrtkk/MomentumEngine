"""Download raw inputs: NSE bhavcopies, NSE index closes, Nifty 500 list, Yahoo history.

Every file is stored unmodified with a manifest row (retrieved_at IST, sha256, url).
Usage: python fetch.py [--sessions 30] [--index-sessions 70] [--history] [--asof YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
HIST = ROOT / "data" / "history"
MEMB = ROOT / "data" / "membership"
MANIFEST = RAW / "manifest.csv"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

BHAV_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d}.csv"
INDEX_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{d}.csv"
N500_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"


def now_ist() -> str:
    return dt.datetime.now(IST).isoformat(timespec="seconds")


def _record(kind: str, date: str, url: str, path: Path, content: bytes) -> None:
    row = pd.DataFrame([{
        "kind": kind, "date": date, "url": url, "path": str(path.relative_to(ROOT)),
        "retrieved_at": now_ist(), "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
    }])
    row.to_csv(MANIFEST, mode="a", header=not MANIFEST.exists(), index=False)


def _get(url: str) -> bytes | None:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 200 and len(r.content) > 500:
                return r.content
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(1 + attempt)
    return None


def fetch_bhav(day: dt.date) -> Path | None:
    out = RAW / "bhav" / f"{day.isoformat()}.csv"
    if out.exists():
        return out
    url = BHAV_URL.format(d=day.strftime("%d%m%Y"))
    content = _get(url)
    if content is None:
        return None
    # NSE re-serves the previous session's file on holidays: verify the date inside the file
    first = pd.read_csv(io.BytesIO(content), skipinitialspace=True, nrows=1)
    first.columns = [c.strip() for c in first.columns]
    if pd.to_datetime(str(first["DATE1"].iloc[0]).strip(), format="%d-%b-%Y").date() != day:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content)
    _record("bhav", day.isoformat(), url, out, content)
    return out


def fetch_index(day: dt.date) -> Path | None:
    out = RAW / "index" / f"{day.isoformat()}.csv"
    if out.exists():
        return out
    url = INDEX_URL.format(d=day.strftime("%d%m%Y"))
    content = _get(url)
    if content is None:
        return None
    first = pd.read_csv(io.BytesIO(content), nrows=1)
    if pd.to_datetime(str(first["Index Date"].iloc[0]).strip(), format="%d-%m-%Y").date() != day:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content)
    _record("index", day.isoformat(), url, out, content)
    return out


def trading_days_back(asof: dt.date, n: int, fetcher) -> list[dt.date]:
    """Walk back from asof, keeping days for which the NSE file exists (= trading days)."""
    days, d, misses = [], asof, 0
    while len(days) < n and misses < 30:
        if d.weekday() < 5 and fetcher(d) is not None:
            days.append(d)
            misses = 0
        else:
            misses += 1
        d -= dt.timedelta(days=1)
    return sorted(days)


def fetch_membership(asof: dt.date) -> Path:
    out = MEMB / f"{asof.isoformat()}_nifty500.csv"
    if out.exists():
        return out
    content = _get(N500_URL)
    if content is None:
        raise RuntimeError("Nifty 500 list unavailable")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content)
    _record("membership", asof.isoformat(), N500_URL, out, content)
    return out


def fetch_history(symbols: list[str], asof: dt.date) -> Path:
    """Yahoo daily OHLCV, auto_adjust=False -> split/bonus-adjusted prices, dividends NOT adjusted."""
    import yfinance as yf

    out = HIST / f"yahoo_{asof.isoformat()}.parquet"
    if out.exists():
        return out
    tickers = [f"{s}.NS" for s in symbols]
    frames = []
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i + 100]
        df = yf.download(chunk, period="2y", interval="1d", auto_adjust=False, actions=True,
                         group_by="ticker", threads=True, progress=False)
        for t in chunk:
            if t not in df.columns.get_level_values(0):
                continue
            sub = df[t].dropna(how="all").reset_index()
            if sub.empty:
                continue
            sub["symbol"] = t[:-3]
            frames.append(sub)
    hist = pd.concat(frames, ignore_index=True)
    hist.columns = [str(c).lower().replace(" ", "_") for c in hist.columns]
    hist["date"] = pd.to_datetime(hist["date"]).dt.tz_localize(None).dt.normalize()
    hist = hist[hist["date"] <= pd.Timestamp(asof)]
    out.parent.mkdir(parents=True, exist_ok=True)
    hist.to_parquet(out, index=False)
    for old in sorted(out.parent.glob("yahoo_*.parquet"))[:-3]:   # keep the 3 most recent snapshots
        old.unlink()
    _record("yahoo_history", asof.isoformat(), "yfinance period=2y auto_adjust=False", out, out.read_bytes())
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=dt.datetime.now(IST).date().isoformat())
    ap.add_argument("--sessions", type=int, default=30)
    ap.add_argument("--index-sessions", type=int, default=70)
    ap.add_argument("--history", action="store_true")
    a = ap.parse_args()
    asof = dt.date.fromisoformat(a.asof)
    bdays = trading_days_back(asof, a.sessions, fetch_bhav)
    idays = trading_days_back(asof, a.index_sessions, fetch_index)
    memb = fetch_membership(asof)
    print(f"bhav {len(bdays)} sessions {bdays[0]}..{bdays[-1]}; index {len(idays)} sessions; membership {memb.name}")
    if a.history:
        syms = pd.read_csv(memb)["Symbol"].tolist()
        p = fetch_history(syms, asof)
        h = pd.read_parquet(p)
        print(f"history {p.name}: {h['symbol'].nunique()} symbols, {len(h)} rows, last {h['date'].max().date()}")


if __name__ == "__main__":
    main()
