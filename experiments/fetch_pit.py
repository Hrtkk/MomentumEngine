"""Point-in-time NSE equity history (all EQ securities incl. later-delisted) + corporate actions.

  bhav : cm{DD}{MON}{YYYY}bhav.csv.zip (2012 .. mid-2024) and UDiFF BhavCopy_NSE_CM_..._F_0000.csv.zip (Jul-2024 ..)
  ca   : NSE corporate actions API, month by month
  symchg: NSE symbol-change list
Output: experiments/data/pit/bhav_<year>.parquet, ca.parquet, symbolchange.csv. Every file's date is verified.
"""
from __future__ import annotations

import datetime as dt
import io
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent / "data" / "pit"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "Accept-Language": "en-US"}
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
COLS = ["date", "symbol", "series", "isin", "open", "high", "low", "close", "prev_close", "volume", "value", "trades"]


def _get(url: str) -> bytes | None:
    for k in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=40)
            if r.status_code == 200 and len(r.content) > 1000:
                return r.content
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(1 + 2 * k)
    return None


def one_day(d: dt.date) -> pd.DataFrame | None:
    if d < dt.date(2024, 7, 8):
        url = f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{d.year}/{MON[d.month - 1]}/cm{d:%d}{MON[d.month - 1]}{d.year}bhav.csv.zip"
        b = _get(url)
        if b is None:
            return None
        z = zipfile.ZipFile(io.BytesIO(b))
        df = pd.read_csv(z.open(z.namelist()[0]))
        df.columns = [c.strip().upper() for c in df.columns]
        ts = str(df["TIMESTAMP"].iloc[0]).strip()
        try:
            fd = dt.datetime.strptime(ts, "%d-%b-%Y").date()
        except ValueError:
            fd = dt.datetime.strptime(ts, "%d-%b-%y").date()       # some 2020 files use 2-digit years
        if fd != d:
            return None
        out = pd.DataFrame({"date": pd.Timestamp(d), "symbol": df["SYMBOL"], "series": df["SERIES"], "isin": df.get("ISIN"),
                            "open": df["OPEN"], "high": df["HIGH"], "low": df["LOW"], "close": df["CLOSE"],
                            "prev_close": df["PREVCLOSE"], "volume": df["TOTTRDQTY"], "value": df["TOTTRDVAL"],
                            "trades": df.get("TOTALTRADES")})
    else:
        url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
        b = _get(url)
        if b is None:
            return None
        z = zipfile.ZipFile(io.BytesIO(b))
        df = pd.read_csv(z.open(z.namelist()[0]))
        if pd.to_datetime(str(df["TradDt"].iloc[0])).date() != d:
            return None
        out = pd.DataFrame({"date": pd.Timestamp(d), "symbol": df["TckrSymb"], "series": df["SctySrs"], "isin": df["ISIN"],
                            "open": df["OpnPric"], "high": df["HghPric"], "low": df["LwPric"], "close": df["ClsPric"],
                            "prev_close": df["PrvsClsgPric"], "volume": df["TtlTradgVol"], "value": df["TtlTrfVal"],
                            "trades": df["TtlNbOfTxsExctd"]})
    out["series"] = out["series"].astype(str).str.strip()
    out = out[out["series"].isin(["EQ", "BE", "BZ", "SM", "ST"])]   # keep main + trade-to-trade; filtered later
    out["symbol"] = out["symbol"].astype(str).str.strip()
    return out[COLS]


def bhav(start: str, end: str) -> None:
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    days = [d0 + dt.timedelta(n) for n in range((d1 - d0).days + 1)]
    days = [d for d in days if d.weekday() < 5]
    by_year: dict[int, list[dt.date]] = {}
    for d in days:
        by_year.setdefault(d.year, []).append(d)
    for y, ds in sorted(by_year.items()):
        f = OUT / f"bhav_{y}.parquet"
        if f.exists() and y < d1.year:
            continue
        with ThreadPoolExecutor(4) as ex:
            frames = [x for x in ex.map(one_day, ds) if x is not None]
        if frames:
            pd.concat(frames, ignore_index=True).to_parquet(f, index=False)
        print(f"bhav {y}: {len(frames)} sessions", flush=True)


def ca(start: str, end: str) -> None:
    s = requests.Session()
    rows = []
    m = pd.Period(start, "M")
    while m <= pd.Period(end, "M"):
        a, b = m.start_time.date(), m.end_time.date()
        url = f"https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date={a:%d-%m-%Y}&to_date={b:%d-%m-%Y}"
        for k in range(3):
            try:
                r = s.get(url, headers={**UA, "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-actions"}, timeout=40)
                if r.status_code == 200:
                    rows += r.json()
                    break
            except Exception:
                pass
            time.sleep(2 + 3 * k)
        else:
            print("CA FAILED", m, flush=True)
        m += 1
        time.sleep(0.4)
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "ca.parquet", index=False)
    print("ca rows", len(df), flush=True)


def symchg() -> None:
    b = _get("https://nsearchives.nseindia.com/content/equities/symbolchange.csv")
    (OUT / "symbolchange.csv").write_bytes(b or b"")
    print("symbolchange bytes", len(b or b""), flush=True)


def update(asof: str | None = None) -> dict:
    """Incremental daily update: missing bhav days of the current year, last 2 months of CA (merged), Nifty 500 index."""
    end = dt.date.fromisoformat(asof) if asof else dt.date.today()
    f = OUT / f"bhav_{end.year}.parquet"
    have = pd.read_parquet(f) if f.exists() else pd.DataFrame(columns=COLS)
    got = set(pd.to_datetime(have["date"]).dt.date) if len(have) else set()
    start = max(got) + dt.timedelta(days=1) if got else dt.date(end.year, 1, 1)
    days = [start + dt.timedelta(n) for n in range((end - start).days + 1)]
    new = [x for x in (one_day(d) for d in days if d.weekday() < 5) if x is not None]
    if new:
        have = pd.concat([have] + new, ignore_index=True)
        have.to_parquet(f, index=False)
    # corporate actions: refresh last two months and merge
    s = requests.Session()
    a = (pd.Timestamp(end) - pd.DateOffset(months=2)).date()
    url = f"https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date={a:%d-%m-%Y}&to_date={end:%d-%m-%Y}"
    ca_new = 0
    try:
        r = s.get(url, headers={**UA, "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-actions"}, timeout=40)
        if r.status_code == 200:
            old = pd.read_parquet(OUT / "ca.parquet")
            add = pd.DataFrame(r.json())
            merged = pd.concat([old, add], ignore_index=True).drop_duplicates(["symbol", "exDate", "subject"])
            ca_new = len(merged) - len(old.drop_duplicates(["symbol", "exDate", "subject"]))
            merged.to_parquet(OUT / "ca.parquet", index=False)
    except Exception as e:
        print("CA refresh failed:", e)
    # Nifty 500 index (Yahoo ^CRSLDX)
    try:
        import yfinance as yf
        ix = yf.download("^CRSLDX", period="max", interval="1d", auto_adjust=False, progress=False)
        ix.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in ix.columns]
        ix = ix.reset_index().rename(columns={"Date": "date"})
        ix["date"] = pd.to_datetime(ix["date"]).dt.tz_localize(None).dt.normalize()
        ix.to_parquet(OUT.parent / "nifty500_index.parquet", index=False)
    except Exception as e:
        print("index refresh failed:", e)
    last = pd.to_datetime(have["date"]).max().date() if len(have) else None
    return {"new_sessions": [str(x["date"].iloc[0].date()) for x in new], "last_session": str(last), "ca_new_rows": ca_new}


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "bhav":
        bhav(sys.argv[2], sys.argv[3])
    elif what == "ca":
        ca(sys.argv[2], sys.argv[3])
    elif what == "update":
        print(update(sys.argv[2] if len(sys.argv) > 2 else None))
    else:
        symchg()
