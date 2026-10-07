"""Run experiment E1 (SPEC.md): all strategies x 3 cost levels on identical data; metrics + report."""
from __future__ import annotations

import html
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panels as PN  # noqa: E402
import sim  # noqa: E402

OUT = Path(__file__).resolve().parent / "results"
COSTS = (0.003, 0.006, 0.010)
_P = None
ALERTS: dict = {}


def b2_series(P, start_i: int, cost: float = 0.006):
    """A3: EW of names eligible at close t, executed at open t+1; old book earns the overnight gap."""
    E = P.eligible.fillna(False).astype(float)
    W = E.div(E.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)          # target at close t
    g = (P.O / P.C.shift(1) - 1).fillna(0.0)                                   # overnight into d
    j = (P.C / P.O - 1).fillna(0.0)                                            # intraday d
    w_on, w_id = W.shift(2).fillna(0.0), W.shift(1).fillna(0.0)
    on = (w_on * g).sum(axis=1)
    gross = (1 + on) * (1 + (w_id * j).sum(axis=1)) - 1
    drift = (w_on * (1 + g)).div((1 + on).replace(0, np.nan), axis=0).fillna(0.0)
    turn = (w_id - drift).abs().sum(axis=1)
    net = gross - cost / 2 * turn
    gross, net = gross.iloc[start_i:].copy(), net.iloc[start_i:].copy()
    gross.iloc[0] = net.iloc[0] = 0.0
    return gross, net


def make(P, key):
    return {
        "S0": lambda: sim.S0E1(P),
        "S1": lambda: sim.RankStrategy(P, P.R3, "S1 3M momentum"),
        "S2": lambda: sim.RankStrategy(P, P.R6, "S2 6M momentum"),
        "S3": lambda: sim.RankStrategy(P, P.R12_1, "S3 12-1 momentum (monthly)", monthly=True),
        "S4": lambda: sim.RankStrategy(P, P.blend, "S4 blended momentum"),
        "S5": lambda: sim.S5Patient(P),
        "S7": lambda: sim.S7Confirm(P),
    }[key]()


def _init():
    global _P
    _P = PN.load()


def _job(args):
    key, cost, start_i = args
    st = make(_P, key)
    t0 = time.time()
    bk = sim.run(st, cost, start_i)
    eq = pd.DataFrame(bk.equity, columns=["date", "equity", "cash"]).set_index("date")
    tr = pd.DataFrame(bk.trades)
    alerts = [x for x in bk.log if x[2] == "ALERT_GT40"]
    unresolved = sum(1 for x in bk.log if x[2] == "UNRESOLVED_NO_DATA")
    return key, st.name, cost, eq, tr, time.time() - t0, alerts, unresolved


def metrics(eq: pd.Series, cash: pd.Series, tr: pd.DataFrame, P, b2r: pd.Series, n5: pd.Series, cost: float) -> dict:
    r = eq.pct_change().fillna(eq.iloc[0] / sim.CAPITAL - 1)
    yrs = len(eq) / 252
    cagr = (eq.iloc[-1] / sim.CAPITAL) ** (1 / yrs) - 1
    b2 = (1 + b2r.reindex(eq.index).fillna(0)).cumprod()
    b2cagr = b2.iloc[-1] ** (1 / yrs) - 1
    n5e = n5.reindex(eq.index)
    n5cagr = (n5e.iloc[-1] / n5e.iloc[0]) ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    down = r[r < 0]
    m = {"total_ret": eq.iloc[-1] / sim.CAPITAL - 1, "CAGR": cagr, "xs_CAGR_vs_B1": cagr - n5cagr,
         "xs_CAGR_vs_B2": cagr - b2cagr, "vol": r.std() * np.sqrt(252),
         "Sharpe": r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan,
         "Sortino": r.mean() / down.std() * np.sqrt(252) if len(down) > 1 else np.nan, "maxDD": dd,
         "exposure": float((1 - cash / eq).mean())}
    if len(tr):
        tr = tr.copy()
        tr["ret"] = tr["exit"] / tr["entry"] - 1
        tr["hold"] = tr["exit_i"] - tr["entry_i"]
        notional = (tr["qty"] * tr["entry"]).sum() + (tr["qty"] * tr["exit"]).sum()
        m.update(trades=len(tr), win_rate=(tr["ret"] > 0).mean(), avg_win=tr.loc[tr.ret > 0, "ret"].mean(),
                 avg_loss=tr.loc[tr.ret <= 0, "ret"].mean(), avg_hold=tr["hold"].mean(),
                 turnover_pa=notional / 2 / eq.mean() / yrs, costs=notional * cost / 2,
                 stop_share=(tr["reason"] == "STOP").mean())
        # entry quality: forward excess vs B2 from entry open
        C, O, idx = P.C, P.O, P.C.index
        fx = {5: [], 10: [], 20: []}
        for _, t in tr.iterrows():
            i0, s = int(t["entry_i"]), t["sym"]
            for h in fx:
                j = i0 + h - 1
                if j < len(idx):
                    sr = C.iat[j, C.columns.get_loc(s)] / O.iat[i0, O.columns.get_loc(s)] - 1
                    br = (1 + b2r.iloc[i0:j + 1]).prod() - 1
                    if pd.notna(sr):
                        fx[h].append(sr - br)
        m.update({f"entry_xs_{h}d": np.mean(v) if v else np.nan for h, v in fx.items()})
    # regimes (Nifty 500 vs its 200-DMA on previous close)
    bull = (n5 > P.n5_sma200).shift(1).reindex(eq.index).fillna(False)
    x = r - b2r.reindex(eq.index).fillna(0)
    for name, msk in (("bull", bull), ("bear", ~bull)):
        m[f"{name}_ann"] = (1 + r[msk]).prod() ** (252 / max(msk.sum(), 1)) - 1
        m[f"{name}_xs_ann"] = x[msk].mean() * 252
        m[f"{name}_days"] = int(msk.sum())
    half = len(r) // 2
    def cg(z):
        return (1 + z).prod() ** (252 / max(len(z), 1)) - 1
    b2a = b2r.reindex(eq.index).fillna(0)
    m["xs_half1"] = cg(r.iloc[:half]) - cg(b2a.iloc[:half])
    m["xs_half2"] = cg(r.iloc[half:]) - cg(b2a.iloc[half:])
    m["years"] = {str(y): float((1 + g).prod() - 1) for y, g in r.groupby(r.index.year)}
    return m


def main():
    P = PN.load()
    dates = P.C.index
    ok = P.eligible.sum(axis=1)
    start_i = int(np.argmax((ok >= 300).values))
    print(f"panel {dates[0].date()}..{dates[-1].date()} | test start {dates[start_i].date()} | symbols {P.C.shape[1]}"
          f" | delivery {'yes' if P.deliv is not None else 'no'}", flush=True)
    b2g, b2n = b2_series(P, start_i)
    b2r = b2n                                          # A3: economic hurdle = B2-net (0.6%)
    keys = ["S0", "S1", "S2", "S3", "S4", "S5", "S7"]
    jobs = [(k, c, start_i) for k in keys for c in COSTS]
    res = {}
    with ProcessPoolExecutor(max_workers=6, initializer=_init) as ex:
        for key, name, cost, eq, tr, sec, alerts, unres in ex.map(_job, jobs):
            res[(key, cost)] = (name, eq, tr)
            ALERTS[(key, cost)] = (alerts, unres)
            print(f"done {key} {cost} in {sec:.0f}s  end={eq['equity'].iloc[-1]:,.0f}", flush=True)
    OUT.mkdir(exist_ok=True)
    rows, curves = [], {}
    n5 = P.n5
    for (key, cost), (name, eq, tr) in res.items():
        m = metrics(eq["equity"], eq["cash"], tr, P, b2r, n5, cost)
        rows.append({"id": key, "name": name, "cost": cost, **{k: v for k, v in m.items() if k != "years"},
                     "years": json.dumps(m["years"])})
        if cost == 0.006:
            curves[key] = eq["equity"] / sim.CAPITAL
        tr.to_csv(OUT / f"trades_{key}_{cost}.csv", index=False)
    M = pd.DataFrame(rows).sort_values(["cost", "id"])
    M.to_csv(OUT / "metrics.csv", index=False)
    b2c = (1 + b2n).cumprod()
    n5c = n5.iloc[start_i:] / n5.iloc[start_i]
    curves["B1 Nifty 500"], curves["B2-net EW"], curves["B2-gross EW"] = n5c, b2c, (1 + b2g).cumprod()
    yrs = len(b2c) / 252
    print(f"B2-net CAGR {b2c.iloc[-1] ** (1 / yrs) - 1:.3%} | B2-gross CAGR {(1 + b2g).prod() ** (1 / yrs) - 1:.3%} | "
          f"B1 CAGR {n5c.iloc[-1] ** (1 / yrs) - 1:.3%}", flush=True)
    al = pd.DataFrame([{"id": k, "cost": c, "alerts": len(a), "alert_pnl": sum(x[4] for x in a), "unresolved_days": u}
                       for (k, c), (a, u) in ALERTS.items()])
    al.to_csv(OUT / "alerts.csv", index=False)
    pd.DataFrame([(k, c, *x) for (k, c), (a, u) in ALERTS.items() for x in a],
                 columns=["id", "cost", "date", "sym", "flag", "ret", "pnl"]).to_csv(OUT / "alerts_detail.csv", index=False)
    pd.DataFrame(curves).to_csv(OUT / "curves_0.006.csv")
    # B2 metrics for the decision rule
    b2dd = (b2c / b2c.cummax() - 1).min()
    report(M, pd.DataFrame(curves), b2dd, dates[start_i], dates[-1], al)
    print(M[M.cost == 0.006][["id", "CAGR", "xs_CAGR_vs_B2", "Sharpe", "maxDD", "turnover_pa", "trades", "win_rate",
                              "bull_xs_ann", "bear_xs_ann", "xs_half1", "xs_half2"]].round(3).to_string(index=False))


def report(M, curves, b2dd, d0, d1, al):
    m6 = M[M.cost == 0.006].set_index("id")
    verdict = {}
    for k, r in m6.iterrows():
        why = []
        if not r["xs_CAGR_vs_B2"] > 0:
            why.append("excess vs B2-net ≤ 0")
        if not (r["xs_half1"] > 0 and r["xs_half2"] > 0):
            why.append("not positive in both halves")
        if (-r["maxDD"]) - (-b2dd) > 0.10:
            why.append("MDD > B2-net + 10pp")
        verdict[k] = ("NOT ADVANCED: " + "; ".join(why)) if why else "ADVANCE → paper shadow book"
    # chart
    c = curves.dropna(how="all").ffill()
    W, H, L, R, T = 900, 320, 60, 150, 16
    lo, hi = np.log(c.min().min()) - 0.02, np.log(c.max().max()) + 0.02
    xs = np.linspace(L, W - R, len(c))
    y = lambda v: T + (hi - np.log(v)) / (hi - lo) * H
    pal = ["#2e5aac", "#c2410c", "#0f766e", "#7c3aed", "#b45309", "#be123c", "#15803d", "#6b7280", "#111827"]
    lines, labels = "", ""
    for j, col in enumerate(c.columns):
        pts = " ".join(f"{xs[i]:.1f},{y(v):.1f}" for i, v in enumerate(c[col].values) if i % 3 == 0 or i == len(c) - 1)
        dash = ' stroke-dasharray="5 4"' if col.startswith("B") else ""
        w = 2.4 if col in ("S0",) else 1.6
        lines += f'<polyline points="{pts}" fill="none" stroke="{pal[j % len(pal)]}" stroke-width="{w}"{dash}/>'
        labels += (f'<text x="{W - R + 6}" y="{y(c[col].iloc[-1]) + 4:.1f}" font-size="11" fill="{pal[j % len(pal)]}">'
                   f'{html.escape(col)} {c[col].iloc[-1]:.2f}×</text>')
    grid = ""
    for v in (0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8):
        if lo <= np.log(v) <= hi:
            grid += (f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="var(--line)"/>'
                     f'<text x="{L - 6}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end" fill="var(--mut)">{v}×</text>')
    years = sorted({int(d.year) for d in c.index})
    xt = "".join(f'<text x="{xs[c.index.get_indexer([c.index[c.index.year == yy][0]])[0]]:.1f}" y="{T + H + 16}" '
                 f'font-size="11" text-anchor="middle" fill="var(--mut)">{yy}</text>' for yy in years)
    svg = f'<svg viewBox="0 0 {W} {T + H + 24}" style="width:100%;height:auto">{grid}{lines}{labels}{xt}</svg>'
    f = lambda v, p=1: "—" if pd.isna(v) else f"{v * 100:+.{p}f}%"
    rows = "".join(
        f"<tr><td class=l><b>{k}</b> {html.escape(r['name'])}</td><td>{f(r['CAGR'])}</td><td>{f(r['xs_CAGR_vs_B2'])}</td>"
        f"<td>{f(r['xs_CAGR_vs_B1'])}</td><td>{r['Sharpe']:.2f}</td><td>{f(r['maxDD'])}</td><td>{r['turnover_pa']:.1f}×</td>"
        f"<td>{int(r['trades'])}</td><td>{f(r['win_rate'], 0)}</td><td>{r['avg_hold']:.0f}</td><td>{f(r['exposure'], 0)}</td>"
        f"<td>{f(r['bull_xs_ann'])}</td><td>{f(r['bear_xs_ann'])}</td><td>{f(r['xs_half1'])} / {f(r['xs_half2'])}</td>"
        f"<td class=l>{html.escape(verdict[k])}</td></tr>" for k, r in m6.iterrows())
    costrows = "".join(
        f"<tr><td class=l>{k}</td>" + "".join(f"<td>{f(M[(M.id == k) & (M.cost == cc)]['xs_CAGR_vs_B2'].iloc[0])}</td>" for cc in COSTS)
        + "</tr>" for k in m6.index)
    yrs = sorted(json.loads(m6.iloc[0]["years"]).keys())
    yrows = "".join(f"<tr><td class=l>{k}</td>" + "".join(f"<td>{f(json.loads(r['years']).get(yy))}</td>" for yy in yrs) + "</tr>"
                    for k, r in m6.iterrows())
    page = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Experiment E1</title>
<style>:root{{--bg:#f6f6f3;--card:#fff;--ink:#141413;--mut:#5f5e5a;--line:#e3e2dc}}@media (prefers-color-scheme:dark){{:root{{--bg:#121211;--card:#1b1b1a;--ink:#f3f2ee;--mut:#b9b8b0;--line:#33332f}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,sans-serif}}.w{{max-width:1150px;margin:auto;padding:20px 16px}}
.card,.tw{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}.tw{{overflow-x:auto;padding:0}}table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}th{{color:var(--mut);font-weight:600}}.l{{text-align:left}}h2{{font-size:15px;margin:24px 0 8px}}.mut{{color:var(--mut)}}</style></head>
<body><div class=w><h1 style="font-size:20px;margin:0">Experiment E1 — strategy comparison</h1>
<div class=mut>{d0.date()} → {d1.date()} · ₹60,000 notional · fractional shares · next-open fills · 0.6% round-trip cost (primary) · pre-registered in experiments/SPEC.md · no parameter tuning</div>
<p class=mut><b>Read with care:</b> today's Nifty 500 list is used for all history (survivorship bias favours momentum). Compare strategies to each other and to B2 (equal-weight of the same universe), not on absolute return. S6 (quality) not run — no point-in-time fundamentals.</p>
<h2>Growth of ₹1 (log scale, 0.6% costs)</h2><div class=card>{svg}</div>
<h2>Summary (0.6% costs) and SPEC §5 verdict</h2><div class=tw><table><thead><tr><th class=l>Strategy</th><th>CAGR</th><th>xs vs B2</th><th>xs vs Nifty500</th><th>Sharpe</th><th>Max DD</th><th>Turnover/yr</th><th>Trades</th><th>Win</th><th>Hold (d)</th><th>Exposure</th><th>Bull xs</th><th>Bear xs</th><th>xs half1 / half2</th><th class=l>Verdict</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class=mut>B2-net max drawdown: {b2dd * 100:.1f}%. "xs" = excess CAGR vs B2-net (equal-weight of the same eligible universe, next-open execution, 0.6% costs). Sharpe uses 0% risk-free. E1 is exploratory package screening conditional on today's surviving universe — "not advanced" ≠ disproved; no component-level causal claims (SPEC §7).</p>
<h2>Data alerts (>40% single-day moves touching holdings, unvalidated — SPEC A1)</h2><div class=tw><table><thead><tr><th class=l>Strategy</th><th>Alerts</th><th>P&amp;L on alert days (₹)</th><th>Unresolved no-data days</th></tr></thead><tbody>{''.join(f"<tr><td class=l>{r.id}</td><td>{r.alerts}</td><td>{r.alert_pnl:,.0f}</td><td>{r.unresolved_days}</td></tr>" for r in al[al.cost == 0.006].itertuples())}</tbody></table></div>
<h2>Cost sensitivity — excess CAGR vs B2</h2><div class=tw><table><thead><tr><th class=l>Strategy</th><th>0.3%</th><th>0.6%</th><th>1.0%</th></tr></thead><tbody>{costrows}</tbody></table></div>
<h2>Calendar-year returns (0.6%)</h2><div class=tw><table><thead><tr><th class=l>Strategy</th>{''.join(f'<th>{y}</th>' for y in yrs)}</tr></thead><tbody>{yrows}</tbody></table></div>
</div></body></html>"""
    (OUT / "E1_report.html").write_text(page)
    print("report", OUT / "E1_report.html")


if __name__ == "__main__":
    main()
