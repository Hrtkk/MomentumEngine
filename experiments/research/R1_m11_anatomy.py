"""R1 — Why does M11 work? Analysis only, development data (signal dates 2013-01-01..2020-12-31,
forward windows must also end by 2020-12-31). No rule change.

Breakout set = M11 candidate condition WITHOUT the volume filter, so the volume buckets below 1.5x
(which M11 rejects) can be compared:
  frozen R6 rank <= 100 (rank from the latest ISO-week-end refresh <= t, as Breakout52 does),
  C_t > hi252_t (prior 252-session high of H), eligible_t, ATR stop valid (sim.Strategy.ok_atr).
M11 signal = breakout set & V_t >= 1.5 * medV20_t. Book-independent (ignores slots/positions).
Forward return: enter open t+1, exit close t+h (h = 5,10,20,60), 0.6% round trip;
excess = that minus B2-net compounded over sessions t+1..t+h (run_e1.b2_series).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pit_panels  # noqa: E402
import sim  # noqa: E402
from run_e1 import b2_series  # noqa: E402

START, DEV_END = pd.Timestamp("2013-01-01"), pd.Timestamp("2020-12-31")
H = [5, 10, 20, 60]
COST = 0.006
OUT = Path(__file__).resolve().parent / "out_R1"


def signals(P):
    dates = P.C.index
    start_i = int(np.searchsorted(dates, START))
    end_i = int(np.searchsorted(dates, DEV_END, side="right")) - 1
    st = sim.Strategy(P)
    rows, rank = [], None
    brk_any = (P.C > P.hi252)                                   # price-only breakout (any name)
    for i in range(start_i - 10, end_i + 1):
        t = dates[i]
        if t in st.week_end:
            rank = P.rank_of(P.R6, t)
        if rank is None or i < start_i:
            continue
        top = rank[rank <= 100].index
        b = brk_any.loc[t, top]
        for s in b[b.fillna(False)].index:
            if not bool(P.eligible.at[t, s]) or not st.ok_atr(s, t):
                continue
            rows.append((i, t, s, int(rank[s])))
    df = pd.DataFrame(rows, columns=["i", "date", "sym", "r6rank"])
    df["volr"] = [P.V.at[t, s] / P.medV20.at[t, s] for t, s in zip(df.date, df.sym)]
    df["dist"] = [P.C.at[t, s] / P.hi252.at[t, s] - 1 for t, s in zip(df.date, df.sym)]
    df["m11"] = df.volr >= 1.5
    # first vs repeat. A: prior M11 signal (full rule) in previous 63 sessions. B: any close > hi252 in previous 63 sessions
    last_m11, flagA = {}, []
    for i, s, m in zip(df.i, df.sym, df.m11):
        flagA.append(s in last_m11 and i - last_m11[s] <= 63)
        if m:
            last_m11[s] = i
    df["repeatA"] = flagA
    prior = brk_any.astype(float).shift(1).rolling(63, min_periods=1).max().fillna(0).astype(bool)
    df["repeatB"] = [bool(prior.at[t, s]) for t, s in zip(df.date, df.sym)]
    return df, start_i, end_i


def forward(P, df, start_i, end_i):
    _, b2n = b2_series(P, start_i)
    lb2 = np.log1p(b2n).cumsum()                                  # index aligned with dates[start_i:]
    C = P.C.ffill(limit=None)                                     # delisted/no-trade: hold last close (disclosed)
    O = P.O
    dates = P.C.index
    for h in H:
        ex = []
        for i, s in zip(df.i, df.sym):
            j = i + h
            if j > end_i or i + 1 > end_i:
                ex.append(np.nan)
                continue
            o = O.iat[i + 1, O.columns.get_loc(s)]
            if pd.isna(o) or o <= 0:
                ex.append(np.nan)
                continue
            c = C.iat[j, C.columns.get_loc(s)]
            r = c / o * (1 - COST / 2) / (1 + COST / 2) - 1
            b = np.expm1(lb2.iloc[j - start_i] - lb2.iloc[i - start_i])
            ex.append(r - b)
        df[f"x{h}"] = ex
    return df


def boot_ci(df, col, n=2000, seed=20261007):
    """Mean with a 90% CI resampling calendar months (clusters overlapping/same-day signals)."""
    d = df[["date", col]].dropna()
    if len(d) < 5:
        return np.nan, np.nan, np.nan
    g = d.groupby(d.date.dt.to_period("M"))[col].agg(["sum", "count"])
    rng = np.random.default_rng(seed)
    k = len(g)
    idx = rng.integers(0, k, size=(n, k))
    m = g["sum"].values[idx].sum(1) / g["count"].values[idx].sum(1)
    return d[col].mean(), *np.percentile(m, [5, 95])


def table(df, by, label):
    out = []
    for key, g in df.groupby(by, observed=True):
        row = {label: key, "n": len(g), "names": g.sym.nunique()}
        for h in H:
            m, lo, hi = boot_ci(g, f"x{h}")
            row[f"n{h}"] = int(g[f"x{h}"].notna().sum())
            row[f"x{h}%"] = f"{100*m:+.2f} [{100*lo:+.1f},{100*hi:+.1f}]"
            row[f"hit{h}"] = f"{100*(g[f'x{h}'] > 0).mean():.0f}%" if g[f"x{h}"].notna().any() else "—"
        row["med20%"] = f"{100*g['x20'].median():+.2f}"
        out.append(row)
    return pd.DataFrame(out)


def md(t):
    cols = list(t.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in t.itertuples(index=False)]
    return "\n".join(lines)


def main():
    OUT.mkdir(exist_ok=True)
    P = pit_panels.build()
    df, si, ei = signals(P)
    df = forward(P, df, si, ei)
    df.to_csv(OUT / "breakouts_dev.csv", index=False)
    vb = pd.cut(df.volr, [0, 1, 1.25, 1.5, 2, 3, np.inf], right=False,
                labels=["<1", "1-1.25", "1.25-1.5", "1.5-2", "2-3", ">=3"])
    m = df[df.m11].copy()
    db = pd.cut(m.dist, [0, .01, .03, .05, np.inf], right=False, labels=["0-1%", "1-3%", "3-5%", ">5%"])
    res = {
        "all_breakouts_by_volume (M11 = >=1.5x)": table(df.assign(vb=vb), "vb", "vol_ratio"),
        "m11_vs_rejected": table(df, "m11", "m11_signal"),
        "m11_by_distance": table(m.assign(db=db), "db", "dist_above_hi252"),
        "m11_first_vs_repeat_A (prior M11 signal <=63s)": table(m, "repeatA", "repeat"),
        "m11_first_vs_repeat_B (any close>hi252 <=63s)": table(m, "repeatB", "repeat"),
        "m11_by_year": table(m.assign(y=m.date.dt.year), "y", "year"),
    }
    with open(OUT / "tables.md", "w") as f:
        for k, v in res.items():
            f.write(f"\n### {k}\n\n{md(v)}\n")
    print(open(OUT / "tables.md").read())
    print("breakouts", len(df), "m11", int(df.m11.sum()), "dates", df.date.nunique(), "names", df.sym.nunique())


if __name__ == "__main__":
    main()
