"""Forward paper books (E4 forward validation) for the frozen E2 strategies M11, M10, M2.

Each evening the books are re-simulated from LIVE_START with frozen code on the latest point-in-time data
(deterministic), and only NEW dates are appended to the ledgers. Previously recorded days are re-checked:
any divergence (data revision, code change) is written to exceptions.csv instead of silently rewriting history.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EXP = HERE.parent / "experiments"
sys.path.insert(0, str(EXP))
import e2_strategies as E2  # noqa: E402
import pit_panels  # noqa: E402
import sim  # noqa: E402
from run_e1 import b2_series  # noqa: E402

LIVE_START = pd.Timestamp("2026-10-07")        # first signal close; first fills at the 2026-10-08 open
BOOKS = ["M11", "M10", "M2"]
CAPITAL, COST = 60_000.0, 0.006
LED = HERE / "ledgers"
FROZEN = ["e2_strategies.py", "sim.py", "panels.py", "pit_panels.py"]


def code_hash() -> dict:
    return {f: hashlib.sha256((EXP / f).read_bytes()).hexdigest()[:16] for f in FROZEN}


def signal_record(P, s: str, t, st, meta: dict) -> dict:
    """Objective pre-trade record (no subjective confidence)."""
    g = lambda panel: None if pd.isna(panel.at[t, s]) else round(float(panel.at[t, s]), 4)
    rec = {"close": g(P.C), "day_ret": g(P.ret1), "R3": g(P.R3), "R6": g(P.R6), "R12_1": g(P.R12_1),
           "vs_52w_high": round(float(P.C.at[t, s] / P.hi252.at[t, s]), 4) if pd.notna(P.hi252.at[t, s]) else None,
           "vol_x_median20": round(float(P.V.at[t, s] / P.medV20.at[t, s]), 2) if P.medV20.at[t, s] else None,
           "vs_sma20": round(float(P.C.at[t, s] / P.sma20.at[t, s] - 1), 4), "rsi14": g(P.rsi), "atr20": g(P.atr20),
           "rank": int(st.frozen_rank.get(s)) if len(getattr(st, "frozen_rank", [])) and s in st.frozen_rank else None,
           "industry": str(P.industry.get(s, "Unknown")),
           "nifty500_vs_200dma": round(float(P.n5.loc[t] / P.n5_sma200.loc[t] - 1), 4)}
    rec.update({k: (round(v, 2) if isinstance(v, float) else v) for k, v in meta.items()})
    return rec


def run(rebuild: bool = True, patch_note: str | None = None) -> dict:
    P = pit_panels.build(cache=not rebuild)
    pd.to_pickle(P, EXP / "data" / "pit_panels.pkl")
    dates = P.C.index
    if dates[-1] < LIVE_START:
        return {"status": "before live start"}
    i0 = int(np.searchsorted(dates, LIVE_START))
    LED.mkdir(parents=True, exist_ok=True)
    reg = LED / "registration.json"
    if not reg.exists():
        reg.write_text(json.dumps({"live_start": str(LIVE_START.date()), "books": BOOKS, "capital": CAPITAL,
                                   "cost_round_trip": COST, "integer_shares": True, "code_sha256": code_hash(),
                                   "spec": "experiments/SPEC_E2.md (frozen E2 selection)"}, indent=1))
    registered = json.loads(reg.read_text())
    exceptions = []
    if patch_note and registered["code_sha256"] != code_hash():       # deliberate, documented patch
        registered.setdefault("patches", []).append({"at": str(pd.Timestamp.now()), "note": patch_note,
                                                     "old_sha256": registered["code_sha256"], "new_sha256": code_hash()})
        registered["code_sha256"] = code_hash()
        reg.write_text(json.dumps(registered, indent=1))
    if registered["code_sha256"] != code_hash():
        exceptions.append({"type": "CODE_CHANGED", "detail": json.dumps(code_hash())})
    summary = {"last_session": str(dates[-1].date()), "books": {}}
    for k in BOOKS:
        st = E2.ladder(P)[k]()
        st.week_end.add(LIVE_START)              # initial refresh on the first live signal date
        st.month_end.add(LIVE_START)
        bk = sim.run(st, COST, i0, integer=True, capital=CAPITAL, live=True)
        d = LED / k
        d.mkdir(exist_ok=True)
        eq = pd.DataFrame(bk.equity, columns=["date", "equity", "cash"])
        eq["n_positions"] = np.nan
        eq.loc[eq.index[-1], "n_positions"] = len(bk.pos)
        ef = d / "equity.csv"
        if ef.exists():
            old = pd.read_csv(ef, parse_dates=["date"])
            both = old.merge(eq, on="date", suffixes=("_old", "_new"))
            bad = both[(both["equity_old"] - both["equity_new"]).abs() > 0.5]
            for r in bad.itertuples():
                exceptions.append({"type": "HISTORY_DIVERGENCE", "detail": f"{k} {r.date.date()} old {r.equity_old:.2f} new {r.equity_new:.2f}"})
            new = eq[eq["date"] > old["date"].max()]
            if len(new):
                new.to_csv(ef, mode="a", header=False, index=False)
        else:
            eq.to_csv(ef, index=False)
        tr = pd.DataFrame(bk.trades)
        if len(tr):
            tr["entry_date"] = [str(dates[i].date()) for i in tr["entry_i"]]
            tr["exit_date"] = [str(dates[i].date()) for i in tr["exit_i"]]
            tf = d / "trades.csv"
            known = pd.read_csv(tf) if tf.exists() else pd.DataFrame(columns=tr.columns)
            key = set(zip(known.get("sym", []), known.get("exit_date", [])))
            fresh = tr[[(s, e) not in key for s, e in zip(tr["sym"], tr["exit_date"])]]
            if len(fresh):
                fresh.to_csv(tf, mode="a", header=not tf.exists(), index=False)
        t = dates[-1]
        snap = {"signal_date": str(t.date()), "equity": round(bk.equity[-1][1], 2), "cash": round(bk.cash, 2),
                "positions": {s: {"qty": p["qty"], "entry": round(p["entry"], 2),
                                  "entry_date": str(dates[p["entry_i"]].date()), "stop": round(p["stop"], 2),
                                  "last": round(p["last"], 2), "industry": str(P.industry.get(s, "Unknown")),
                                  **({"t0low": round(p["meta"]["t0low"], 2)} if "t0low" in p["meta"] else {})}
                              for s, p in bk.pos.items()},
                "orders_next_open": [{**{kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in o.items() if kk != "meta"},
                                      **({"signal": signal_record(P, o["sym"], t, st, o.get("meta", {}))} if o["side"] == "buy" else {})}
                                     for o in bk.pending]}
        sf = d / f"snapshot_{t.date()}.json"
        if not sf.exists():                      # immutable once written
            sf.write_text(json.dumps(snap, indent=1, default=str))
        summary["books"][k] = {"equity": snap["equity"], "positions": len(snap["positions"]),
                               "buys_next_open": [o["sym"] for o in snap["orders_next_open"] if o["side"] == "buy"],
                               "sells_next_open": [o["sym"] for o in snap["orders_next_open"] if o["side"] == "sell"]}
    # benchmarks since live start
    b2g, b2n = b2_series(P, i0)
    bm = pd.DataFrame({"date": dates[i0:], "nifty500": P.n5.iloc[i0:].values, "b2net_cum": (1 + b2n).cumprod().values})
    bm.to_csv(LED / "benchmarks.csv", index=False)
    if exceptions:
        pd.DataFrame([{**e, "logged": str(pd.Timestamp.now())} for e in exceptions]).to_csv(
            LED / "exceptions.csv", mode="a", header=not (LED / "exceptions.csv").exists(), index=False)
    summary["exceptions"] = exceptions
    (LED / "last_run.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    note = sys.argv[sys.argv.index("--register-patch") + 1] if "--register-patch" in sys.argv else None
    print(json.dumps(run(patch_note=note), indent=1, default=str))
