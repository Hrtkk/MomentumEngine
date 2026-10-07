"""Compact daily holdings sheet for Drive (primary book)."""
import json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def run(t: str, run_date: str) -> Path:
    st = json.loads((ROOT / "ledgers" / "state.json").read_text())["books"]["c0.006"]
    c = pd.read_csv(ROOT / "data" / "candidates.csv"); c = c[c["date"] == t].set_index("symbol")
    ch = ROOT / "data" / "codex" / f"challenge_{t}.json"
    sev = {p["symbol"]: p["severity"] for p in json.loads(ch.read_text()).get("picks", [])} if ch.exists() else {}
    E = st["cash"] + sum(p["qty"] * p["last"] for p in st["positions"].values())
    rows = [{"run_date": run_date, "signal_date": t, "symbol": s, "sector": c.at[s, "industry"] if s in c.index else "",
             "weight_pct": round(p["qty"] * p["last"] / E * 100, 1), "qty": p["qty"], "entry": p["entry"],
             "last": p["last"], "pnl_pct": round((p["last"] / p["entry"] - 1) * 100, 2), "stop": round(p["stop"], 2),
             "score": round(c.at[s, "mqs"], 1) if s in c.index else "", "codex_risk": sev.get(s, "")}
            for s, p in st["positions"].items()]
    rows.append({"run_date": run_date, "signal_date": t, "symbol": "CASH", "weight_pct": round(st["cash"] / E * 100, 1),
                 "last": round(st["cash"], 2)})
    rows.append({"run_date": run_date, "signal_date": t, "symbol": "TOTAL", "weight_pct": 100, "last": round(E, 2)})
    out = ROOT / "reports" / f"{run_date}_holdings.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


if __name__ == "__main__":
    print(run(sys.argv[1], sys.argv[2]))
