"""Exploratory study (no ledger writes): does the gainer universe / MQS predict short-horizon returns?

For each signal date with enough history, score the day exactly as the engine does, then measure
forward returns O(t+1) -> C(t+h) for several cohorts. Prints a summary and writes reviews/study_<asof>.csv.
In-sample, today's Nifty 500 membership (survivorship-biased), tiny sample — diagnosis only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as E  # noqa: E402

HORIZONS = (1, 3, 5)


def main(n_dates: int = 30) -> None:
    b, idx, hist = E.load_bhav(), E.load_index(), E.load_history()
    hist_by = {s: g.sort_values("date") for s, g in hist.groupby("symbol")}
    days = sorted(b["date"].unique())
    memb = set(E.load_membership(days[-1])["symbol"])
    o = b.pivot_table(index="date", columns="symbol", values="o")
    c = b.pivot_table(index="date", columns="symbol", values="c")
    usable = [d for i, d in enumerate(days) if i >= 21 and i + 1 < len(days)][-n_dates:]
    rows, ics = [], []
    for t in usable:
        i = days.index(t)
        f, disc = E.score_day(t, b, idx, hist_by, [])
        el = f[f["eligible"] & f["in_window"]].copy()
        # broad universe: all Nifty 500 names with 63-session history on t
        n500 = []
        for s in memb:
            h = hist_by.get(s)
            if h is None:
                continue
            h = h[h["date"] <= t]
            if len(h) > 64 and h["date"].iloc[-1] == t:
                n500.append((s, h["yc"].iloc[-1] / h["yc"].iloc[-64] - 1))
        n5 = pd.Series(dict(n500))
        coh = {
            "N500_ALL": list(n5.index),
            "N500_MOM63_10": list(n5.sort_values(ascending=False).head(10).index),
            "DISCOVERY_100": disc["symbol"].tolist(),
            "ELIGIBLE": list(el.index),
            "MQS10": list(el.sort_values("mqs", ascending=False).head(10).index),
            "MQS_BOTTOM10": list(el.sort_values("mqs").head(10).index),
            "RAW10": list(el[el.index.isin(disc["symbol"])].sort_values("day_ret", ascending=False).head(10).index),
            "PERSIST10": list(el.sort_values(["persist_n", "day_ret"], ascending=False).head(10).index),
            "MOM63_10_GAINERS": list(el.sort_values("ret63", ascending=False).head(10).index),
        }
        for h in HORIZONS:
            if i + h >= len(days):
                continue
            entry, exitp = o.loc[days[i + 1]], c.loc[days[i + h]]
            r = (exitp / entry - 1).replace([np.inf, -np.inf], np.nan)
            r = r.where(r.abs() < 0.4)                                   # drop corporate-action artefacts
            for k, mem in coh.items():
                v = r.reindex(mem).dropna()
                rows.append({"date": t.date(), "h": h, "cohort": k, "n": len(v), "ret": v.mean()})
            if h == 5 and len(el) > 10:
                rr = r.reindex(el.index)
                ok = rr.notna()
                d = {"date": t.date(), "MQS": el.loc[ok, "mqs"].corr(rr[ok], method="spearman")}
                for fac in ["p_rs", "p_trend", "p_volume", "p_breakout", "p_persist", "p_sector", "p_vol", "eqs",
                            "day_ret", "close_quality"]:
                    d[fac] = el.loc[ok, fac].corr(rr[ok], method="spearman")
                ics.append(d)
    R = pd.DataFrame(rows)
    out = Path(__file__).resolve().parents[1] / "reviews"
    out.mkdir(exist_ok=True)
    R.to_csv(out / f"study_{days[-1].date()}.csv", index=False)
    print(f"signal dates: {usable[0].date()} .. {usable[-1].date()}  ({len(usable)})")
    piv = R.pivot_table(index="cohort", columns="h", values="ret", aggfunc="mean") * 100
    base = R[R.cohort == "N500_ALL"].set_index(["date", "h"])["ret"]
    ex = R.set_index(["date", "h"]).join(base.rename("b"))
    ex["x"] = ex["ret"] - ex["b"]
    hit = ex.groupby(["cohort", ex.index.get_level_values("h")])["x"].apply(lambda s: (s > 0).mean() * 100).unstack()
    ndates = R.groupby(["cohort", "h"])["date"].nunique().unstack()
    print("\nMean forward return % (open t+1 -> close t+h), equal-weight:")
    print(piv.round(2).to_string())
    print("\n% of dates beating the whole Nifty 500 (same dates):")
    print(hit.round(0).to_string())
    print("\nn dates per horizon:", ndates.iloc[0].to_dict())
    I = pd.DataFrame(ics).set_index("date")
    print(f"\nDaily rank IC vs 5-session forward return, eligible candidates (n dates={len(I)}):")
    print(pd.DataFrame({"mean_IC": I.mean(), "share_positive_%": (I > 0).mean() * 100}).round(3).to_string())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
