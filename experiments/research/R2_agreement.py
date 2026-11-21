"""R2 — Does agreement between strategies help? Analysis only, development data
(signal dates 2013-01-01..2020-12-31; forward windows must end by 2020-12-31). No rule change.

"Selected by strategy X on date t" is book-independent (empty book, no slots/sector cap/hysteresis):
  M2  : R6 rank <= 50 among eligible names, ranked at the latest ISO-week-end refresh <= t (frozen between refreshes).
  M8  : same, but ranked only among names passing the dual-momentum mask (R6 > 0 and R6 > Nifty 500 R6).
  M5  : m5 score rank <= 50, ranked at the latest month-end <= t (frozen until the next month-end).
  M10 : the frozen E2 EventConfirm state machine (e2_strategies.EventConfirm, unchanged) run with an empty book;
        a confirmation (buy order) on t counts as selected on t.
  M11 : Breakout52 candidate on t: frozen R6 top-100, C > hi252, V >= 1.5 x medV20, eligible, ATR stop valid.
Count = number of the five that select (sym, t). Sampled two ways:
  weekly (primary): week-end refresh dates; M10/M11 count if they fired on any session of that ISO week.
  daily (sensitivity): every session; M2/M5/M8 by frozen list, M10/M11 only on the exact day.
Forward excess: enter open t+1, exit close t+h (h = 5, 20, 60), 0.6% round trip, minus B2-net aligned to the
entry (R1b: day t+1 intraday leg + turnover cost, full B2-net thereafter). Missing open or terminal close -> missing.
Inference: R1b circular moving-block bootstrap over the 96 dev months (L = 4 primary, 8 sensitivity), joint
resampling across count groups; contrasts vs count 1, Holm-adjusted.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))
sys.path.insert(0, str(HERE))
import pit_panels  # noqa: E402
import sim  # noqa: E402
import e2_strategies as e2  # noqa: E402
import R1b_m11_followups as r1b  # noqa: E402

START, DEV_END, COST = r1b.START, r1b.DEV_END, r1b.COST
H = [5, 20, 60]
STRATS = ["M2", "M5", "M8", "M10", "M11"]
OUT = HERE / "out_R2"


def membership(P):
    dates = P.C.index
    si = int(np.searchsorted(dates, START))
    ei = int(np.searchsorted(dates, DEV_END, side="right")) - 1
    base = sim.Strategy(P)
    lowvol_unused = None  # noqa: F841  (M6 mask not needed)
    dual = (P.R6 > 0) & P.R6.gt((P.n5 / P.n5.shift(126) - 1), axis=0)
    m2 = e2.Ranked(P, P.R6, "M2")
    m8 = e2.Ranked(P, P.R6, "M8", mask=dual)
    m5 = e2.Ranked(P, P.m5, "M5", monthly=True)
    m10 = e2.EventConfirm(P)
    bk = sim.Book(cost=COST)                      # stays empty: book-independent signals
    L2 = L8 = L5 = set()
    top100 = pd.Index([])
    rows = []
    for i in range(si - 70, ei + 1):              # warm-up so frozen lists / M10 state exist on 2013-01-01
        t = dates[i]
        if t in base.week_end:
            r = m2.rank_now(t); L2 = set(r[r <= 50].index)
            r = m8.rank_now(t); L8 = set(r[r <= 50].index)
            r = P.rank_of(P.R6, t); top100 = r[r <= 100].index
        if t in base.month_end:
            r = m5.rank_now(t); L5 = set(r[r <= 50].index)
        _, buys = m10.decide(bk, i, t)
        S10 = {s for s, _, _ in buys}
        brk = (P.C.loc[t, top100] > P.hi252.loc[t, top100]) & (P.V.loc[t, top100] >= 1.5 * P.medV20.loc[t, top100])
        S11 = {s for s in brk[brk].index if P.eligible.at[t, s] and base.ok_atr(s, t)}
        if i < si:
            continue
        for s in L2 | L5 | L8 | S10 | S11:
            rows.append((i, t, s, s in L2, s in L5, s in L8, s in S10, s in S11, t in base.week_end))
    df = pd.DataFrame(rows, columns=["i", "date", "sym"] + STRATS + ["weekend"])
    return df, si, ei


def weekly(df, P, si, ei):
    """Week-end rows; M10/M11 = fired on any session of the ISO week ending t."""
    dates = P.C.index
    wk = pd.Series(dates.to_period("W-SUN"), index=dates)
    d = df.copy()
    d["wk"] = wk.loc[d.date].values
    ev = d.groupby(["wk", "sym"])[["M10", "M11"]].any()
    we = d[d.weekend].set_index(["wk", "sym"])
    st = we[["M2", "M5", "M8"]]
    # names that fired M10/M11 during the week but are in no list at the week-end still need a row
    idx = st.index.union(ev[ev.any(axis=1)].index)
    out = pd.DataFrame(index=idx)
    out[["M2", "M5", "M8"]] = st.reindex(idx).fillna(False).astype(bool)
    out[["M10", "M11"]] = ev.reindex(idx).fillna(False).astype(bool)
    wend = pd.Series(dates, index=dates).groupby(wk.values).max()
    wend = wend[wend.isin(df.loc[df.weekend, "date"].unique())]
    out = out.reset_index()
    out = out[out.wk.isin(wend.index)]
    out["date"] = wend.loc[out.wk].values
    pos = pd.Series(np.arange(len(dates)), index=dates)
    out["i"] = pos.loc[out.date].values
    return out.drop(columns="wk")


def forward(P, d, ei):
    on, net, first = r1b.b2_components(P)
    lnet = np.log1p(net).cumsum().values
    lfirst = np.log1p(first).values
    C, O = P.C.values, P.O.values
    col = P.C.columns.get_indexer(d.sym)
    i = d.i.values
    o = np.where(i + 1 <= ei, O[np.minimum(i + 1, len(O) - 1), col], np.nan)
    for h in H:
        j = i + h
        ok = (j <= ei) & np.isfinite(o) & (o > 0)
        jj = np.minimum(j, len(C) - 1)
        c = C[jj, col]
        r = c / o * (1 - COST / 2) / (1 + COST / 2) - 1
        b = np.expm1(lfirst[np.minimum(i + 1, len(C) - 1)] + lnet[jj] - lnet[np.minimum(i + 1, len(C) - 1)])
        x = np.where(ok & np.isfinite(c), r - b, np.nan)
        d[f"a{h}"] = x
        d[f"miss{h}"] = ok & ~np.isfinite(c)         # window inside dev but terminal close missing (no ffill)
    return d


def ref_universe(P, si, ei, week_only=True):
    """Mean aligned excess of all eligible names (count 0 + selected) per date: reference row."""
    pass


def cnt_label(n):
    return "4+" if n >= 4 else str(int(n))


def table(d, L=4, tag=""):
    rows, cons = [], []
    for h in H:
        col = f"a{h}"
        S, N = r1b.agg(d, col, d.grp.values)
        bm = r1b.boot(S, N, L=L)
        means = {}
        for k in ["0", "1", "2", "3", "4+"]:
            if k not in S.columns:
                continue
            v = d.loc[d.grp == k, col].dropna()
            lo, hi = r1b.ci(bm, k)
            means[k] = v.mean()
            rows.append({"h": h, "count": k, "n": len(v), "names": d.loc[(d.grp == k) & d[col].notna(), "sym"].nunique(),
                         "mean%": r1b.pct(v.mean()), "90% CI": f"[{100*lo:+.2f},{100*hi:+.2f}]",
                         "median%": r1b.pct(v.median()), "hit": f"{100*(v > 0).mean():.1f}%"})
        ks = [k for k in ["1", "2", "3", "4+"] if k in S.columns]
        mono = float(np.mean(np.all(np.diff(bm[ks].values, axis=1) > 0, axis=1)))
        for k in ks[1:]:
            hat = means[k] - means["1"]
            lo, hi, p = r1b.contrast(bm, k, "1", hat)
            cons.append({"sample": tag, "h": h, "contrast": f"{k} − 1", "diff%": 100 * hat, "lo": 100 * lo, "hi": 100 * hi,
                         "p": p, "P(monotone 1<2<3<4+)": mono})
    return pd.DataFrame(rows), pd.DataFrame(cons)


def main():
    OUT.mkdir(exist_ok=True)
    P = pit_panels.build()
    df, si, ei = membership(P)
    df["n"] = df[STRATS].sum(axis=1)
    wk = weekly(df, P, si, ei)
    wk["n"] = wk[STRATS].sum(axis=1)
    lines = []

    # reference: all eligible names on week-end dates (count 0 = eligible, not selected by any)
    dates = P.C.index
    wdates = sorted(wk.date.unique())
    E = P.eligible.loc[wdates]
    ref = E.stack()
    ref = ref[ref].reset_index()
    ref.columns = ["date", "sym", "_"]
    ref = ref.drop(columns="_").merge(wk[["date", "sym", "n"] + STRATS], on=["date", "sym"], how="left")
    ref["n"] = ref.n.fillna(0).astype(int)
    for s in STRATS:
        ref[s] = ref[s].fillna(False).astype(bool)
    pos = pd.Series(np.arange(len(dates)), index=dates)
    ref["i"] = pos.loc[ref.date].values
    # selected names that are not eligible at the week-end (event earlier in the week) are kept from wk
    extra = wk.merge(ref[["date", "sym"]], on=["date", "sym"], how="left", indicator=True)
    extra = extra[extra._merge == "left_only"].drop(columns="_merge")
    W = pd.concat([ref, extra[ref.columns]], ignore_index=True)
    W = forward(P, W, ei)
    W["grp"] = W.n.map(cnt_label)
    D = forward(P, df.copy(), ei)
    D["grp"] = D.n.map(cnt_label)
    W.to_csv(OUT / "weekly_rows.csv.gz", index=False)

    # composition
    lines.append("### Sample and composition\n")
    lines.append(f"Weekly: {len(wdates)} week-end dates, {len(W)} eligible stock-weeks "
                 f"({(W.n > 0).sum()} with count ≥ 1, {W.sym[W.n > 0].nunique()} names) plus {len(extra)} selected rows "
                 f"not eligible at the week-end. Daily: {len(D)} selected stock-days, {D.sym.nunique()} names, "
                 f"{D.date.nunique()} dates.\n")
    sel = W[W.n > 0]
    comp = sel.groupby(STRATS).size().sort_values(ascending=False).head(15).reset_index(name="stock-weeks")
    comp["combo"] = comp[STRATS].apply(lambda r: "+".join(s for s in STRATS if r[s]), axis=1)
    comp["count"] = comp[STRATS].sum(axis=1)
    comp["share%"] = (100 * comp["stock-weeks"] / len(sel)).round(1)
    lines.append("Most frequent combinations (weekly, count ≥ 1):\n")
    lines.append(r1b.md(comp[["combo", "count", "stock-weeks", "share%"]]) + "\n")
    cnts = sel.groupby("grp").size()
    lines.append("Stock-weeks by count: " + ", ".join(f"{k}: {v}" for k, v in cnts.items()) + "\n")
    jac = pd.DataFrame(index=STRATS, columns=STRATS, dtype=float)
    for a in STRATS:
        for b in STRATS:
            jac.loc[a, b] = (sel[a] & sel[b]).sum() / max(1, (sel[a] | sel[b]).sum())
    lines.append("Pairwise Jaccard overlap of selections (weekly):\n")
    jt = jac.round(2).reset_index().rename(columns={"index": "strategy"})
    lines.append(r1b.md(jt) + "\n")
    share = sel.groupby("grp")[STRATS].mean().mul(100).round(0)
    lines.append("Share of rows in each count group selected by each strategy (%, weekly):\n")
    lines.append(r1b.md(share.reset_index()) + "\n")
    r6r = []
    for g, x in W[W.n > 0].groupby("grp"):
        rk = [P.rank_of(P.R6, t).get(s, np.nan) for t, s in zip(x.date.values[:3000], x.sym.values[:3000])] if False else None
    # R6 rank by count (confound check) — rank recomputed per week-end
    rk = {}
    for t in wdates:
        rk[t] = P.rank_of(P.R6, t)
    W["r6rank"] = [rk[t].get(s, np.nan) for t, s in zip(W.date, W.sym)]
    rr = W[W.n > 0].groupby("grp").r6rank.agg(["median", "mean"]).round(0)
    lines.append("R6 rank (among eligible, week-end) by count — agreement is largely a proxy for 6-month strength:\n")
    lines.append(r1b.md(rr.reset_index()) + "\n")

    # main tables
    allc = []
    for tag, d, L in [("weekly", W, 4), ("weekly L=8", W, 8), ("daily", D, 4)]:
        t, c = table(d, L=L, tag=tag)
        lines.append(f"### Forward excess vs entry-aligned B2-net by count — {tag} (block bootstrap L={L} months)\n")
        lines.append(r1b.md(t) + "\n")
        allc.append(c)
    # within M2's own list: does extra agreement add anything given M2 selected it?
    m2 = W[W.M2].copy()
    m2["grp"] = m2.n.map(cnt_label)
    t, c = table(m2, tag="weekly, within M2 top-50")
    lines.append("### Within M2 top-50 only (weekly) — does agreement add anything beyond M2?\n")
    lines.append(r1b.md(t) + "\n")
    allc.append(c)
    # within R6 rank bands (weekly, count >= 1)
    band = pd.cut(W.r6rank, [0, 10, 25, 50, np.inf], labels=["1-10", "11-25", "26-50", ">50"]).astype(str)
    bt = []
    for b in ["1-10", "11-25", "26-50", ">50"]:
        x = W[(band == b) & (W.n > 0)]
        for g, y in x.groupby("grp"):
            v = y.a60.dropna()
            bt.append({"R6 rank band": b, "count": g, "n60": len(v), "mean60%": r1b.pct(v.mean()), "hit60": f"{100*(v>0).mean():.0f}%"})
    lines.append("### 60d excess by count within R6 rank bands (weekly, point estimates only)\n")
    lines.append(r1b.md(pd.DataFrame(bt)) + "\n")
    # by block
    yb = []
    for blk, (a, b) in {"D1 2013-14": (2013, 2014), "D2 2015-16": (2015, 2016), "D3 2017-18": (2017, 2018), "D4 2019-20": (2019, 2020)}.items():
        x = W[W.date.dt.year.between(a, b)]
        rec = {"block": blk}
        for g in ["0", "1", "2", "3", "4+"]:
            rec[g] = r1b.pct(x.loc[x.grp == g, "a60"].mean())
        yb.append(rec)
    lines.append("### 60d mean excess by count and dev block (weekly)\n")
    lines.append(r1b.md(pd.DataFrame(yb)) + "\n")

    c = pd.concat(allc, ignore_index=True)
    prim = c["sample"] == "weekly"
    c["p_holm(primary)"] = np.nan
    c.loc[prim, "p_holm(primary)"] = r1b.holm(c.loc[prim, "p"].values)
    fmt = c.copy()
    for k in ["diff%", "lo", "hi"]:
        fmt[k] = fmt[k].map(lambda x: f"{x:+.2f}")
    for k in ["p", "P(monotone 1<2<3<4+)", "p_holm(primary)"]:
        fmt[k] = fmt[k].map(lambda x: "—" if pd.isna(x) else f"{x:.3f}")
    lines.append("### Contrasts vs count 1 (difference of means, joint block resampling); Holm over the 9 primary tests\n")
    lines.append(r1b.md(fmt) + "\n")
    miss = {h: int(W[f"miss{h}"].sum()) for h in H}
    lines.append(f"Terminal close missing inside dev (excluded, weekly rows): {miss}\n")
    c.to_csv(OUT / "contrasts.csv", index=False)
    text = "\n".join(lines)
    (OUT / "tables.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
