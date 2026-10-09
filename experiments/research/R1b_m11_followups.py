"""R1b — follow-ups to R1 from the Codex review (2026-10-08). Analysis only, development data
(signal dates 2013-01-01..2020-12-31; forward windows must end by 2020-12-31). No rule change.

Changes vs R1_m11_anatomy.py (whose signal builder is reused unchanged):
 1. Hit rates count only observed outcomes (missing is missing, not a loss).
 2. Counts (names/dates) are reported for the M11 subset itself, not for all breakouts.
 3. Execution flags per signal/horizon: entry fillable at open t+1 (sim.fillable, buy), open above the
    catastrophic stop (sim skips the buy otherwise), terminal close present (not carried forward), exit fillable
    at close t+h (sim.fillable, sell). "clean" = all four hold. Raw (R1) and clean figures are both shown.
 4. Benchmark aligned to the stock's entry: B2-net on day t+1 uses only the intraday leg (open->close) and the
    turnover cost; the overnight gap close t -> open t+1 is dropped. Days t+2..t+h use the full B2-net return.
 5. Inference: circular moving-block bootstrap over calendar months (block L=4 months primary, 8 months
    sensitivity) so 60-session overlap across adjacent months is inside a block; symbol-cluster bootstrap as a
    second sensitivity. Bucket contrasts are tested as differences of means under joint resampling of the same
    blocks; p-values are Holm-adjusted across all contrasts, with Benjamini-Hochberg q-values alongside.
 6. No book-level attribution claim is made.
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
from run_e1 import b2_series  # noqa: E402
import R1_m11_anatomy as r1  # noqa: E402

START, DEV_END, H, COST = r1.START, r1.DEV_END, r1.H, r1.COST
OUT = HERE / "out_R1b"
MONTHS = pd.period_range("2013-01", "2020-12", freq="M")
NBOOT, SEED = 4000, 20261009


def b2_components(P, cost=COST):
    """Same arithmetic as run_e1.b2_series, but returning the overnight and intraday legs separately."""
    E = P.eligible.fillna(False).astype(float)
    W = E.div(E.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    g = (P.O / P.C.shift(1) - 1).fillna(0.0)
    jr = (P.C / P.O - 1).fillna(0.0)
    w_on, w_id = W.shift(2).fillna(0.0), W.shift(1).fillna(0.0)
    on = (w_on * g).sum(axis=1)
    idr = (w_id * jr).sum(axis=1)
    gross = (1 + on) * (1 + idr) - 1
    drift = (w_on * (1 + g)).div((1 + on).replace(0, np.nan), axis=0).fillna(0.0)
    turn = (w_id - drift).abs().sum(axis=1)
    net = gross - cost / 2 * turn
    first = idr - cost / 2 * turn            # entry-aligned day t+1: no overnight leg, cost still charged
    return on, net, first


def forward_flags(P, df, start_i, end_i):
    on, net, first = b2_components(P)
    _, b2n = b2_series(P, start_i)           # cross-check against the frozen benchmark
    assert np.allclose(net.iloc[start_i + 1:].values, b2n.iloc[1:].values, atol=1e-12), "B2 replication differs"
    lnet = np.log1p(net).cumsum()
    lfirst = np.log1p(first)
    Cff, C, O = P.C.ffill(), P.C, P.O
    col = {s: C.columns.get_loc(s) for s in df.sym.unique()}
    stop = [float(C.at[t, s] - 3 * P.atr20.at[t, s]) for t, s in zip(df.date, df.sym)]
    df["ent_ok"] = [bool(sim.fillable(P, i + 1, s, "buy")) if i + 1 <= end_i else False for i, s in zip(df.i, df.sym)]
    df["stop_ok"] = [bool(O.iat[i + 1, col[s]] > k) if (i + 1 <= end_i and pd.notna(O.iat[i + 1, col[s]])) else False
                     for i, s, k in zip(df.i, df.sym, stop)]
    df["b2_on"] = [float(on.iloc[i + 1]) if i + 1 <= end_i else np.nan for i in df.i]   # overnight leg dropped
    for h in H:
        raw, al, term, exo = [], [], [], []
        for i, s in zip(df.i, df.sym):
            j = i + h
            if j > end_i:
                raw.append(np.nan); al.append(np.nan); term.append(False); exo.append(False)
                continue
            o = O.iat[i + 1, col[s]]
            if pd.isna(o) or o <= 0:
                raw.append(np.nan); al.append(np.nan); term.append(False); exo.append(False)
                continue
            c = Cff.iat[j, col[s]]
            r = c / o * (1 - COST / 2) / (1 + COST / 2) - 1
            b_raw = np.expm1(lnet.iloc[j] - lnet.iloc[i])
            b_al = np.expm1(lfirst.iloc[i + 1] + lnet.iloc[j] - lnet.iloc[i + 1])
            raw.append(r - b_raw); al.append(r - b_al)
            term.append(bool(pd.notna(C.iat[j, col[s]])))
            exo.append(bool(sim.fillable(P, j, s, "sell")))
        df[f"x{h}"], df[f"a{h}"] = raw, al                       # x = R1 benchmark, a = entry-aligned benchmark
        df[f"term{h}"], df[f"exit{h}"] = term, exo
        df[f"clean{h}"] = df.ent_ok & df.stop_ok & df[f"term{h}"] & df[f"exit{h}"]
    return df


# ---------------------------------------------------------------- bootstrap machinery
def agg(d, col, grp, by="month"):
    t = pd.DataFrame({"v": d[col].values, "g": np.asarray(grp), "k": (d.date.dt.to_period("M") if by == "month" else d.sym).values})
    t = t.dropna(subset=["v"])
    S = t.pivot_table(index="k", columns="g", values="v", aggfunc="sum")
    N = t.pivot_table(index="k", columns="g", values="v", aggfunc="count")
    if by == "month":
        S, N = S.reindex(MONTHS), N.reindex(MONTHS)
    return S.fillna(0.0), N.fillna(0.0)


def block_idx(rng, K, L, n):
    nb = int(np.ceil(K / L))
    starts = rng.integers(0, K, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(L)[None, None, :]) % K
    return idx.reshape(n, -1)[:, :K]


def boot(S, N, L=4, by="month", n=NBOOT, seed=SEED):
    """n x G matrix of resampled group means (joint resampling of the same blocks for every group)."""
    rng = np.random.default_rng(seed)
    K = len(S)
    idx = block_idx(rng, K, L, n) if by == "month" else rng.integers(0, K, size=(n, K))
    s, c = S.values[idx].sum(1), N.values[idx].sum(1)
    return pd.DataFrame(s / np.where(c > 0, c, np.nan), columns=S.columns)


def ci(bm, g):
    v = bm[g].dropna().values
    return np.percentile(v, [5, 95]) if len(v) else (np.nan, np.nan)


def contrast(bm, a, b, hat):
    d = (bm[a] - bm[b]).dropna().values
    lo, hi = np.percentile(d, [5, 95])
    p = float(np.mean(np.abs(d - hat) >= abs(hat)))
    return lo, hi, p


def holm(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p); adj = np.empty(m)
    run = 0.0
    for r, k in enumerate(o):
        run = max(run, (m - r) * p[k]); adj[k] = min(1.0, run)
    return adj


def bh(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)[::-1]; adj = np.empty(m); run = 1.0
    for r, k in enumerate(o):
        rank = m - r; run = min(run, m / rank * p[k]); adj[k] = min(1.0, run)
    return adj


def md(t):
    cols = list(t.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in t.itertuples(index=False)]
    return "\n".join(lines)


def pct(x):
    return "—" if pd.isna(x) else f"{100*x:+.2f}"


# ---------------------------------------------------------------- tables
def bucket_table(df, grp, label, col_prefix="a", clean=True, L=4):
    rows, contrasts = {}, []
    groups = pd.Series(np.asarray(grp), index=df.index)
    for h in H:
        col = f"{col_prefix}{h}"
        d = df[df[f"clean{h}"]] if clean else df
        g = groups.loc[d.index]
        S, N = agg(d, col, g)
        bm = boot(S, N, L=L)
        for k in S.columns:
            v = d.loc[g == k, col].dropna()
            lo, hi = ci(bm, k)
            rows.setdefault(k, {label: k, "n": int((groups == k).sum()), "names": int(df.loc[groups == k, "sym"].nunique())})
            rows[k][f"n{h}"] = len(v)
            rows[k][f"x{h}%"] = f"{pct(v.mean())} [{100*lo:+.1f},{100*hi:+.1f}]"
            rows[k][f"hit{h}"] = f"{100*(v > 0).mean():.0f}%" if len(v) else "—"
            if h == 20:
                rows[k]["med20%"] = pct(v.median())
        contrasts.append((h, S.columns.tolist(), bm, {k: d.loc[g == k, col].mean() for k in S.columns}))
    return pd.DataFrame(list(rows.values())), contrasts


def contrast_rows(family, contrasts, ref, pairs=None):
    out = []
    for h, keys, bm, means in contrasts:
        for k in keys:
            if k == ref:
                continue
            hat = means[k] - means[ref]
            lo, hi, p = contrast(bm, k, ref, hat)
            out.append({"family": family, "contrast": f"{k} − {ref}", "h": h, "diff%": 100 * hat, "lo": 100 * lo, "hi": 100 * hi, "p": p})
    return out


def main():
    OUT.mkdir(exist_ok=True)
    P = pit_panels.build()
    df, si, ei = r1.signals(P)
    df = forward_flags(P, df, si, ei)
    df.to_csv(OUT / "breakouts_dev_flags.csv", index=False)
    m = df[df.m11].copy()
    lines = []

    # 1. counts and execution accounting
    lines.append("### Sample accounting\n")
    lines.append(f"All breakouts: {len(df)} signals, {df.sym.nunique()} names, {df.date.nunique()} dates. "
                 f"M11 (≥1.5× volume): {len(m)} signals, {m.sym.nunique()} names, {m.date.nunique()} dates.\n")
    acc = []
    for h in H:
        meas = m[f"x{h}"].notna()
        acc.append({"h": h, "window_in_dev": int(meas.sum()), "entry_unfillable": int((meas & ~m.ent_ok).sum()),
                    "open_at_or_below_stop": int((meas & m.ent_ok & ~m.stop_ok).sum()),
                    "terminal_close_missing(stale)": int((meas & ~m[f"term{h}"]).sum()),
                    "exit_unfillable(incl. stale)": int((meas & ~m[f"exit{h}"]).sum()),
                    "clean": int(m[f"clean{h}"].sum()),
                    "mean_x_raw_excluded%": pct(m.loc[meas & ~m[f"clean{h}"], f"x{h}"].mean())})
    lines.append(md(pd.DataFrame(acc)) + "\n")
    on_m11 = m.loc[m.x60.notna(), "b2_on"].mean(); on_rej = df.loc[(~df.m11) & df.x60.notna(), "b2_on"].mean()
    lines.append(f"B2 overnight leg on day t+1 (dropped by the aligned benchmark): M11 {100*on_m11:+.3f}%, "
                 f"rejected {100*on_rej:+.3f}% (signals with 60d outcomes).\n")

    # 2. M11 headline under each treatment
    lines.append("### M11 headline, excess vs B2-net (%), mean [90% CI], hit = share of observed outcomes > 0\n")
    head = []
    for h in H:
        for name, d, col in [("R1 raw (all, B2 incl. overnight)", m, f"x{h}"), ("aligned B2 (all)", m, f"a{h}"),
                             ("aligned B2, clean sample", m[m[f"clean{h}"]], f"a{h}")]:
            v = d[col].dropna()
            S, N = agg(d, col, np.ones(len(d)))
            lo4, hi4 = ci(boot(S, N, L=4), 1.0); lo8, hi8 = ci(boot(S, N, L=8), 1.0)
            Ss, Ns = agg(d, col, np.ones(len(d)), by="sym"); los, his = ci(boot(Ss, Ns, by="sym"), 1.0)
            trim = v.sort_values().iloc[: int(np.floor(0.95 * len(v)))].mean() if len(v) else np.nan
            head.append({"h": h, "treatment": name, "n": len(v), "mean%": pct(v.mean()),
                         "CI block L=4": f"[{100*lo4:+.2f},{100*hi4:+.2f}]", "CI block L=8": f"[{100*lo8:+.2f},{100*hi8:+.2f}]",
                         "CI symbol-cluster": f"[{100*los:+.2f},{100*his:+.2f}]", "median%": pct(v.median()),
                         "hit": f"{100*(v > 0).mean():.1f}%", "mean ex top5%": pct(trim)})
    lines.append(md(pd.DataFrame(head)) + "\n")

    # 3. buckets on the clean sample with the aligned benchmark
    vb = pd.cut(df.volr, [0, 1, 1.25, 1.5, 2, 3, np.inf], right=False, labels=["<1", "1-1.25", "1.25-1.5", "1.5-2", "2-3", ">=3"]).astype(str)
    db = pd.cut(m.dist, [0, .01, .03, .05, np.inf], right=False, labels=["0-1%", "1-3%", "3-5%", ">5%"]).astype(str)
    allc = []
    specs = [("volume (all breakouts)", df, vb, "vol_ratio", ">=3"),
             ("M11 vs rejected", df, df.m11.map({True: "M11", False: "rejected"}), "group", "rejected"),
             ("distance above hi252 (M11)", m, db, "dist", "0-1%"),
             ("repeat A: prior M11 signal ≤63s (M11)", m, m.repeatA.map({True: "repeat", False: "first"}), "repeatA", "first"),
             ("repeat B: any close>hi252 ≤63s (M11)", m, m.repeatB.map({True: "repeat", False: "first"}), "repeatB", "first"),
             ("year (M11)", m, m.date.dt.year.astype(str), "year", None)]
    lines.append("### Buckets — clean sample, aligned B2-net, block bootstrap L=4 months\n")
    for fam, d, g, label, ref in specs:
        t, con = bucket_table(d, g, label)
        lines.append(f"#### {fam}\n\n{md(t)}\n")
        if ref is not None:
            allc += contrast_rows(fam, con, ref)
    # raw-sample repeat of the volume table for comparison with R1
    t_raw, _ = bucket_table(df, vb, "vol_ratio", col_prefix="x", clean=False)
    lines.append(f"#### volume, R1 treatment (all measured, B2 incl. overnight) — for comparison\n\n{md(t_raw)}\n")

    # 4. contrasts with multiplicity control
    c = pd.DataFrame(allc)
    c["p_holm"] = holm(c.p); c["q_bh"] = bh(c.p)
    c = c.sort_values("p").reset_index(drop=True)
    c8 = []
    for fam, d, g, label, ref in specs:
        if ref is None:
            continue
        _, con = bucket_table(d, g, label, L=8)
        c8 += contrast_rows(fam, con, ref)
    c8 = pd.DataFrame(c8).rename(columns={"p": "p_L8"})[["family", "contrast", "h", "p_L8"]]
    c = c.merge(c8, on=["family", "contrast", "h"])
    c["p_L8_holm"] = holm(c.p_L8)
    fmt = c.copy()
    for k in ["diff%", "lo", "hi"]:
        fmt[k] = fmt[k].map(lambda x: f"{x:+.2f}")
    for k in ["p", "p_holm", "q_bh", "p_L8", "p_L8_holm"]:
        fmt[k] = fmt[k].map(lambda x: f"{x:.3f}")
    lines.append(f"### Contrasts (difference of means, clean sample, aligned B2) — {len(c)} tests, Holm across all\n")
    lines.append(md(fmt) + "\n")
    c.to_csv(OUT / "contrasts.csv", index=False)
    text = "\n".join(lines)
    (OUT / "tables.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
