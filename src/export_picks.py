"""Export current primary-book holdings + pending buys + near-misses for the Codex challenger."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COLS = ["name", "industry", "close", "day_ret", "mqs", "eqs", "rsi", "sma20", "sma50", "sma200", "atr20", "stop",
        "stop_dist", "hi252", "ret21", "ret63", "vol_ratio", "deliv_pct", "persist_n", "penalties", "flags", "top3"]


def run(t: str) -> None:
    c = pd.read_csv(ROOT / "data" / "candidates.csv")
    c = c[c["date"] == t].set_index("symbol")
    st = json.loads((ROOT / "ledgers" / "state.json").read_text())["books"]["c0.006"]
    pos = list(st["positions"]) + [o["symbol"] for o in st["pending"] if o["side"] == "buy"]
    pos = [s for s in dict.fromkeys(pos) if s in c.index]
    out = c.loc[pos, COLS].round(3)
    out["status"] = ["held" if s in st["positions"] else "buy_at_next_open" for s in pos]
    d = ROOT / "data" / "codex"
    d.mkdir(parents=True, exist_ok=True)
    out.to_csv(d / f"picks_{t}.csv")
    w = c[c["eligible"] & c["in_window"] & ~c.index.isin(pos)].sort_values("mqs", ascending=False).head(10)[COLS].round(3)
    w.to_csv(d / f"nearmiss_{t}.csv")
