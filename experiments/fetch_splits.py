"""Split/bonus history per symbol (Yahoo) -> nominal price reconstruction for the ₹50 threshold (SPEC §1)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
syms = pd.read_csv(sorted((ROOT / "data" / "membership").glob("*_nifty500.csv"))[-1])["Symbol"].tolist()


def one(s):
    try:
        sp = yf.Ticker(f"{s}.NS").splits
        return [(s, pd.Timestamp(d).tz_localize(None).normalize(), float(r)) for d, r in sp.items() if r and r != 1]
    except Exception:
        return []


with ThreadPoolExecutor(8) as ex:
    rows = [r for lst in ex.map(one, syms) for r in lst]
df = pd.DataFrame(rows, columns=["symbol", "date", "ratio"])
df.to_parquet(ROOT / "experiments" / "data" / "splits.parquet", index=False)
print(len(df), "split events;", df["symbol"].nunique(), "symbols;", (df["date"] >= "2019-10-01").sum(), "since 2019-10")
