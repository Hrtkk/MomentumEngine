"""Experiment E2 runner (SPEC_E2). Two phases, enforced order:

  python run_e2.py dev      -> runs all books (continuous from 2013-01-01), writes DEV metrics + selection.json only
  python run_e2.py holdout  -> requires selection.json; computes holdout verdicts + ensemble; writes final report
"""
from __future__ import annotations

import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_strategies as E2  # noqa: E402
import pit_panels  # noqa: E402
import sim  # noqa: E402
from run_e1 import b2_series  # noqa: E402

OUT = Path(__file__).resolve().parent / "results_e2"
COSTS = (0.003, 0.006, 0.010)
START, DEV_END, HOLD_START = pd.Timestamp("2013-01-01"), pd.Timestamp("2020-12-31"), pd.Timestamp("2021-01-01")
DEV_BLOCKS = [("D1", "2013-01-01", "2014-12-31"), ("D2", "2015-01-01", "2016-12-31"),
              ("D3", "2017-01-01", "2018-12-31"), ("D4", "2019-01-01", "2020-12-31")]
HOLD_BLOCKS = [("H1", "2021-01-01", "2022-12-31"), ("H2", "2023-01-01", "2024-12-31"), ("H3", "2025-01-01", "2026-12-31")]
_P = None


def _init():
    global _P
    _P = pit_panels.build()


def _job(args):
    key, cost, start_i = args
    st = E2.ladder(_P)[key]()
    bk = sim.run(st, cost, start_i)
    eq = pd.DataFrame(bk.equity, columns=["date", "equity", "cash"]).set_index("date")
    return key, st.name, cost, eq, pd.DataFrame(bk.trades), [x for x in bk.log if x[2] == "ALERT_GT40"]


def seg(r: pd.Series, a, b) -> pd.Series:
    return r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]


def cagr(r: pd.Series) -> float:
    return (1 + r).prod() ** (252 / max(len(r), 1)) - 1


def mdd(r: pd.Series) -> float:
    e = (1 + r).cumprod()
    return float(-(e / e.cummax() - 1).min())          # positive magnitude (A8)


def period_metrics(r, b2, a, b, tr=None, dates=None) -> dict:
    rs, bs = seg(r, a, b), seg(b2, a, b)
    m = {"CAGR": cagr(rs), "xs": cagr(rs) - cagr(bs), "MDD": mdd(rs), "MDD_B2": mdd(bs),
         "Sharpe": rs.mean() / rs.std() * np.sqrt(252) if rs.std() > 0 else np.nan, "days": len(rs)}
    if tr is not None and len(tr):
        ent = dates[tr["entry_i"].values]
        t = tr[(ent >= pd.Timestamp(a)) & (ent <= pd.Timestamp(b))]
        m["trades"] = len(t)
        m["win"] = float((t["exit"] > t["entry"]).mean()) if len(t) else np.nan
        m["hold"] = float((t["exit_i"] - t["entry_i"]).mean()) if len(t) else np.nan
    return m


def run_all():
    P = pit_panels.build()
    dates = P.C.index
    start_i = int(np.searchsorted(dates, START))
    b2g, b2n = b2_series(P, start_i)
    keys = list(E2.ladder(P).keys())
    jobs = [(k, c, start_i) for k in keys for c in COSTS]
    res = {}
    with ProcessPoolExecutor(max_workers=6, initializer=_init) as ex:
        for key, name, cost, eq, tr, al in ex.map(_job, jobs):
            res[(key, cost)] = {"name": name, "eq": eq, "trades": tr, "alerts": al}
            print(f"ran {key} {cost}", flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "books.pkl", "wb") as f:
        pickle.dump({"res": res, "b2n": b2n, "b2g": b2g, "n5": P.n5, "dates": dates,
                     "alerts_panel": P.alerts}, f)
    return res, b2n, dates


def returns(eq: pd.DataFrame) -> pd.Series:
    e = eq["equity"]
    r = e.pct_change()
    r.iloc[0] = e.iloc[0] / sim.CAPITAL - 1
    return r


def dev():
    res, b2n, dates = run_all()
    rows, sel_pool = [], []
    for (k, c), v in res.items():
        r = returns(v["eq"])
        m = period_metrics(r, b2n, START, DEV_END, v["trades"], dates)
        blocks = {n: period_metrics(r, b2n, a, b)["xs"] for n, a, b in DEV_BLOCKS}
        rows.append({"id": k, "name": v["name"], "cost": c, **{f"dev_{x}": y for x, y in m.items()}, **blocks,
                     "alerts": len(v["alerts"])})
    M = pd.DataFrame(rows)
    M.to_csv(OUT / "dev_metrics.csv", index=False)
    m6 = M[M.cost == 0.006].set_index("id")
    m10 = M[M.cost == 0.010].set_index("id")
    verdict = {}
    for k, r in m6.iterrows():
        if k.startswith("C"):
            verdict[k] = "control"
            continue
        why = []
        if not r["dev_xs"] > 0:
            why.append("dev excess ≤ 0")
        if sum(r[n] > 0 for n, _, _ in DEV_BLOCKS) < 3:
            why.append("<3 of 4 dev blocks positive")
        if r["dev_MDD"] - r["dev_MDD_B2"] > 0.10:
            why.append("MDD > B2 + 10pp")
        if not m10.loc[k, "dev_xs"] > 0:
            why.append("excess ≤ 0 at 1.0% cost")
        verdict[k] = "PASS" if not why else "FAIL: " + "; ".join(why)
        if not why:
            sel_pool.append((r["dev_Sharpe"], k))
    chosen, per_tier = [], {}
    for sh, k in sorted(sel_pool, reverse=True):
        t = E2.TIER[k]
        if per_tier.get(t, 0) >= 2:
            continue
        chosen.append(k)
        per_tier[t] = per_tier.get(t, 0) + 1
        if len(chosen) == 5:
            break
    sel = {"selected": chosen, "ensemble": chosen[:4], "verdict_dev": verdict, "n_trials": 14,
           "written_before_holdout": True, "spec": "SPEC_E2.md"}
    (OUT / "selection.json").write_text(json.dumps(sel, indent=1))
    show = m6[["name", "dev_CAGR", "dev_xs", "dev_MDD", "dev_MDD_B2", "dev_Sharpe", "dev_trades", "dev_win", "dev_hold",
               "D1", "D2", "D3", "D4"]].copy()
    show["xs@1.0%"] = m10["dev_xs"]
    show["verdict"] = pd.Series(verdict)
    pd.set_option("display.width", 250)
    print(f"\nB2-net dev CAGR {cagr(seg(b2n, START, DEV_END)):.2%}  MDD {mdd(seg(b2n, START, DEV_END)):.1%}")
    print(show.round(3).to_string())
    print("\nSELECTED (logged before holdout):", chosen, "| ensemble:", chosen[:4])


def holdout():
    sel = json.loads((OUT / "selection.json").read_text())
    with open(OUT / "books.pkl", "rb") as f:
        B = pickle.load(f)
    res, b2n, dates = B["res"], B["b2n"], B["dates"]
    end = dates[-1]
    rows = []
    rets = {k: returns(res[(k, 0.006)]["eq"]) for k, c in res if c == 0.006}
    if sel["ensemble"]:
        eqs = pd.concat([res[(k, 0.006)]["eq"]["equity"] for k in sel["ensemble"]], axis=1).mean(axis=1)
        rr = eqs.pct_change()
        rr.iloc[0] = eqs.iloc[0] / sim.CAPITAL - 1
        rets["EN"] = rr
    rng = np.random.default_rng(20261007)
    for k, r in rets.items():
        m = period_metrics(r, b2n, HOLD_START, end, res[(k, 0.006)]["trades"] if k != "EN" else None, dates)
        blocks = {n: period_metrics(r, b2n, a, b)["xs"] for n, a, b in HOLD_BLOCKS}
        x = (seg(r, HOLD_START, end) - seg(b2n, HOLD_START, end)).values
        n, L = len(x), 20
        boots = []
        for _ in range(5000):
            st = rng.integers(0, n - L + 1, size=int(np.ceil(n / L)))
            s = np.concatenate([x[j:j + L] for j in st])[:n]
            boots.append(s.mean() * 252)
        lo, hi = np.percentile(boots, [5, 95])
        xs_costs = {f"xs@{c}": period_metrics(returns(res[(k, c)]["eq"]), b2n, HOLD_START, end)["xs"]
                    for c in COSTS} if k != "EN" else {}
        is_sel = k in sel["selected"] or k == "EN"
        why = []
        if not m["xs"] > 0:
            why.append("holdout excess ≤ 0")
        if sum(blocks[b] > 0 for b in blocks) < 2:
            why.append("<2 of 3 holdout blocks positive")
        if m["MDD"] - m["MDD_B2"] > 0.10:
            why.append("MDD > B2 + 10pp")
        verdict = ("RELIABLE (E2)" if not why else "NOT RELIABLE: " + "; ".join(why)) if is_sel else "not selected (info only)"
        rows.append({"id": k, "selected": is_sel, **{f"h_{a}": b for a, b in m.items()}, **blocks,
                     "xs_ann_CI90": f"[{lo:+.1%}, {hi:+.1%}]", **xs_costs, "verdict": verdict})
    H = pd.DataFrame(rows).set_index("id")
    H.to_csv(OUT / "holdout_metrics.csv")
    pd.set_option("display.width", 250)
    print(f"B2-net holdout CAGR {cagr(seg(b2n, HOLD_START, end)):.2%}  MDD {mdd(seg(b2n, HOLD_START, end)):.1%}")
    print(H.round(3).to_string())


if __name__ == "__main__":
    {"dev": dev, "holdout": holdout}[sys.argv[1]]()
