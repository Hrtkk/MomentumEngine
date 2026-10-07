"""Long history for the experiment framework (no effect on the live engine).

  yahoo : 7y daily OHLCV (split-adjusted, dividends NOT adjusted) for today's Nifty 500 + ^CRSLDX (Nifty 500 index)
  deliv : NSE sec_bhavdata_full delivery % (EQ series) back to --since, compacted to one parquet
"""
import datetime as dt
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "data"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def yahoo():
    import yfinance as yf
    memb = sorted((ROOT / "data" / "membership").glob("*_nifty500.csv"))[-1]
    syms = pd.read_csv(memb)["Symbol"].tolist()
    frames = []
    for i in range(0, len(syms), 100):
        chunk = [f"{s}.NS" for s in syms[i:i + 100]]
        df = yf.download(chunk, period="7y", interval="1d", auto_adjust=False, group_by="ticker", threads=True, progress=False)
        for t in chunk:
            if t in df.columns.get_level_values(0):
                sub = df[t].dropna(how="all").reset_index()
                if not sub.empty:
                    sub["symbol"] = t[:-3]
                    frames.append(sub)
    h = pd.concat(frames, ignore_index=True)
    h.columns = [str(c).lower().replace(" ", "_") for c in h.columns]
    h["date"] = pd.to_datetime(h["date"]).dt.tz_localize(None).dt.normalize()
    h.to_parquet(OUT / "yahoo_7y.parquet", index=False)
    ix = yf.download("^CRSLDX", period="max", interval="1d", auto_adjust=False, progress=False)
    ix.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in ix.columns]
    ix = ix.reset_index().rename(columns={"Date": "date"})
    ix["date"] = pd.to_datetime(ix["date"]).dt.tz_localize(None).dt.normalize()
    ix.to_parquet(OUT / "nifty500_index.parquet", index=False)
    print("yahoo", h["symbol"].nunique(), "symbols", h["date"].min().date(), h["date"].max().date(), "| index rows", len(ix))


def deliv(since: str):
    out = OUT / "delivery.parquet"
    have = pd.read_parquet(out) if out.exists() else pd.DataFrame(columns=["date", "symbol", "deliv", "turn_lacs", "trades"])
    done = set(pd.to_datetime(have["date"]).dt.date) if len(have) else set()
    d, end, frames, n = dt.date.fromisoformat(since), dt.date.today() - dt.timedelta(days=1), [], 0
    s = requests.Session()
    while d <= end:
        if d.weekday() < 5 and d not in done:
            url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d:%d%m%Y}.csv"
            try:
                r = s.get(url, headers=UA, timeout=30)
                if r.status_code == 200 and len(r.content) > 500:
                    df = pd.read_csv(io.BytesIO(r.content), skipinitialspace=True)
                    df.columns = [c.strip() for c in df.columns]
                    if pd.to_datetime(str(df["DATE1"].iloc[0]).strip(), format="%d-%b-%Y").date() == d:  # holiday duplicates
                        df = df[df["SERIES"].str.strip() == "EQ"]
                        frames.append(pd.DataFrame({"date": pd.Timestamp(d), "symbol": df["SYMBOL"].str.strip(),
                                                    "deliv": pd.to_numeric(df["DELIV_PER"].astype(str).str.strip(), errors="coerce"),
                                                    "turn_lacs": pd.to_numeric(df["TURNOVER_LACS"], errors="coerce"),
                                                    "trades": pd.to_numeric(df["NO_OF_TRADES"], errors="coerce")}))
                        n += 1
            except Exception as e:
                print("err", d, e)
            time.sleep(0.15)
            if n and n % 100 == 0 and frames:
                have = pd.concat([have] + frames, ignore_index=True); frames = []
                have.to_parquet(out, index=False); print("saved", n, d, flush=True)
        d += dt.timedelta(days=1)
    have = pd.concat([have] + frames, ignore_index=True)
    have.to_parquet(out, index=False)
    print("delivery sessions", have["date"].nunique(), have["date"].min(), have["date"].max())


if __name__ == "__main__":
    {"yahoo": yahoo, "deliv": lambda: deliv(sys.argv[2] if len(sys.argv) > 2 else "2020-09-01")}[sys.argv[1]]()
