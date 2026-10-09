"""Strategy performance reports (read-only). Reads live ledgers (+ optional backtest curves) and writes strategy/reports/.

  .venv/bin/python strategy/build_reports.py            # overview.html + one page per book + CSVs

Charts are inline SVG with a hover read-out and a table view; no plotting library is needed.
"""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LED = ROOT / "live" / "ledgers"
OUT = ROOT / "strategy" / "reports"
BT = ROOT / "strategy" / "data"
CAP = 60_000.0
BOOKS = {"M11": "52-week-high breakout", "M10": "Gainer event + confirmation", "M2": "6-month momentum",
         "C0": "Legacy control (v0.2.1)"}
# categorical slots, validated (dataviz skill, light + dark); benchmarks are neutral dashed lines, not series colours
COL = {"M2": ("#2a78d6", "#3987e5"), "M10": ("#eb6834", "#d95926"), "M11": ("#1baf7a", "#199e70"), "C0": ("#4a3aa7", "#9085e9")}
E = html.escape


# ---------------------------------------------------------------- data
def load_book(k: str) -> dict:
    """equity (Series), daily pnl, drawdown, trades (DataFrame), positions (dict), start date."""
    if k == "C0":
        e = pd.read_csv(ROOT / "ledgers" / "equity.csv", parse_dates=["date"])
        eq = e[e["book"] == "c0.006"].set_index("date")["equity"].sort_index()
        f = pd.read_csv(ROOT / "ledgers" / "fills.csv", parse_dates=["date"])
        f = f[f["book"] == "c0.006"]
        sells = f[f["side"] == "sell"].copy()
        tr = pd.DataFrame({"sym": sells["symbol"], "entry": sells["entry"], "exit": sells["price"], "qty": sells["qty"],
                           "exit_date": sells["date"].dt.date.astype(str), "reason": sells["reason"]})
        tr["entry_date"] = ""
        st = json.loads((ROOT / "ledgers" / "state.json").read_text())["books"]["c0.006"]
        pos = {s: {"qty": p["qty"], "entry": p["entry"], "last": p["last"], "stop": p["stop"], "entry_date": p["entry_date"],
                   "industry": ""} for s, p in st["positions"].items()}
    else:
        eq = pd.read_csv(LED / k / "equity.csv", parse_dates=["date"]).set_index("date")["equity"].sort_index()
        tf = LED / k / "trades.csv"
        tr = pd.read_csv(tf) if tf.exists() else pd.DataFrame(columns=["sym", "entry", "exit", "qty", "reason", "entry_date", "exit_date"])
        snaps = sorted((LED / k).glob("snapshot_*.json"))
        pos = json.loads(snaps[-1].read_text())["positions"] if snaps else {}
    if len(tr):
        tr["ret_pct"] = (tr["exit"] / tr["entry"] - 1) * 100
        tr["pnl"] = (tr["exit"] - tr["entry"]) * tr["qty"]
    base = eq.iloc[0]
    cum = eq / base - 1
    dd = eq / eq.cummax() - 1
    pnl = eq.diff().fillna(0.0)
    return {"eq": eq, "cum": cum, "dd": dd, "pnl": pnl, "trades": tr, "pos": pos, "base": base}


def benchmarks() -> pd.DataFrame:
    bm = pd.read_csv(LED / "benchmarks.csv", parse_dates=["date"]).set_index("date")
    return pd.DataFrame({"Nifty 500": bm["nifty500"] / bm["nifty500"].iloc[0] - 1,
                         "B2-net": bm["b2net_cum"] / bm["b2net_cum"].iloc[0] - 1})


def backtest(k: str) -> pd.DataFrame | None:
    f = BT / f"backtest_{k}.csv"
    return pd.read_csv(f, parse_dates=["date"]).set_index("date") if f.exists() else None


# ---------------------------------------------------------------- stats
def stats(b: dict) -> dict:
    eq, pnl, tr = b["eq"], b["pnl"], b["trades"]
    r = eq.pct_change().dropna()
    n = len(r)
    out = {"Start": str(eq.index[0].date()), "Last": str(eq.index[-1].date()), "Sessions": n,
           "Value": eq.iloc[-1], "Return": eq.iloc[-1] / b["base"] - 1, "Max drawdown": b["dd"].min(),
           "Best day": pnl.max(), "Worst day": pnl.min(),
           "Sharpe (ann., since start)": (r.mean() / r.std() * np.sqrt(252)) if n > 1 and r.std() > 0 else np.nan,
           "Closed trades": len(tr), "Win rate": (tr["ret_pct"] > 0).mean() if len(tr) else np.nan,
           "Avg win %": tr.loc[tr["ret_pct"] > 0, "ret_pct"].mean() if len(tr) else np.nan,
           "Avg loss %": tr.loc[tr["ret_pct"] <= 0, "ret_pct"].mean() if len(tr) else np.nan,
           "Open positions": len(b["pos"])}
    return out


# ---------------------------------------------------------------- svg charts
def _axis_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    if hi == lo:
        hi = lo + 1e-9
    step = (hi - lo) / (n - 1)
    mag = 10 ** np.floor(np.log10(abs(step))) if step else 1
    nice = min([1, 2, 2.5, 5, 10], key=lambda m: abs(m * mag - step)) * mag
    a = np.floor(lo / nice) * nice
    return list(np.arange(a, hi + nice * 0.5, nice))


def line_chart(df: pd.DataFrame, colours: dict, fmt: str = "pct", title: str = "", cid: str = "c", fill_below_zero: bool = False, log: bool = False) -> str:
    """df: index=dates, columns=series. Benchmarks ('Nifty 500', 'B2-net') drawn dashed in muted ink.
    log=True: df holds cumulative returns; the axis shows multiples of the start (1x, 2x, 4x ...) on a log scale."""
    df = df.dropna(how="all").ffill()
    if log:
        df = np.log(1 + df)
    if len(df) < 2:
        return f'<div class=card><h3>{E(title)}</h3><p class=muted>Needs at least two sessions.</p></div>'
    W, H, L, R, T, B = 880, 260, 60, 130, 16, 28
    vals = df.values.astype(float)
    lo, hi = np.nanmin(vals), np.nanmax(vals)
    lo, hi = min(lo, 0), max(hi, 0)
    pad = (hi - lo) * 0.08 or 0.01
    lo, hi = lo - pad, hi + pad
    xs = np.linspace(L, W - R, len(df))
    y = lambda v: T + (hi - v) / (hi - lo) * H
    f = (lambda v: f"{np.exp(v):.1f}×") if log else (lambda v: f"{v * 100:+.1f}%") if fmt == "pct" else (lambda v: f"₹{v:,.0f}")
    ticks = [np.log(m) for m in (0.5, 1, 2, 4, 8, 16, 32, 64, 128) if lo <= np.log(m) <= hi] if log else _axis_ticks(lo, hi)
    p = [f'<rect x="{L}" y="{T}" width="{W - L - R}" height="{H}" fill="var(--surface)"/>']
    for tv in ticks:
        if lo <= tv <= hi:
            p.append(f'<line x1="{L}" x2="{W - R}" y1="{y(tv):.1f}" y2="{y(tv):.1f}" stroke="var(--line)"/>'
                     f'<text x="{L - 8}" y="{y(tv) + 4:.1f}" font-size="11" text-anchor="end" fill="var(--mut)">{f(tv)}</text>')
    p.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="var(--mut)" stroke-width="1"/>')
    step = max(1, len(df) // 8)
    for i in range(0, len(df), step):
        p.append(f'<text x="{xs[i]:.0f}" y="{T + H + 16}" font-size="10" text-anchor="middle" fill="var(--mut)">{df.index[i].strftime("%d %b %y")}</text>')
    labels = []
    for col in df.columns:
        v = df[col].values
        pts = " ".join(f"{xs[i]:.1f},{y(x):.1f}" for i, x in enumerate(v) if pd.notna(x))
        bench = col in ("Nifty 500", "B2-net")
        stroke = "var(--mut)" if bench else f"var(--s-{col})"
        dash = ' stroke-dasharray="5 4"' if bench else ""
        if fill_below_zero and not bench:
            area = f"{xs[0]:.1f},{y(0):.1f} " + pts + f" {xs[-1]:.1f},{y(0):.1f}"
            p.append(f'<polygon points="{area}" fill="{stroke}" opacity="0.12"/>')
        p.append(f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linejoin="round"{dash}/>')
        labels.append((float(v[-1]), col, stroke))
    last = -99
    for val, col, stroke in sorted(labels, key=lambda t: -t[0]):
        yy = max(y(val) + 4, last + 13)
        last = yy
        p.append(f'<text x="{W - R + 8}" y="{yy:.1f}" font-size="11" fill="var(--ink)"><tspan fill="{stroke}">●</tspan> {E(col)} {f(val)}</text>')
    # hover layer
    p.append(f'<line id="{cid}-x" x1="0" x2="0" y1="{T}" y2="{T + H}" stroke="var(--ink)" stroke-width="1" opacity="0" pointer-events="none"/>')
    p.append(f'<rect x="{L}" y="{T}" width="{W - L - R}" height="{H}" fill="transparent" class="hit" data-chart="{cid}"/>')
    data = {"dates": [d.strftime("%d %b %Y") for d in df.index], "xs": [round(x, 1) for x in xs],
            "series": {c: [None if pd.isna(x) else round(float(np.exp(x) if log else x), 5) for x in df[c].values] for c in df.columns}, "fmt": "mult" if log else fmt}
    legend = " ".join(f'<span class=lg><i style="background:{"var(--mut)" if c in ("Nifty 500", "B2-net") else f"var(--s-{c})"}"></i>{E(c)}</span>' for c in df.columns)
    table = "<table class=tv><thead><tr><th class=l>Date</th>" + "".join(f"<th>{E(c)}</th>" for c in df.columns) + "</tr></thead><tbody>"
    for d, row in df.iterrows():
        table += f"<tr><td class=l>{d.date()}</td>" + "".join(f"<td>{f(x) if pd.notna(x) else '—'}</td>" for x in row.values) + "</tr>"
    table += "</tbody></table>"
    return (f'<div class=card><h3>{E(title)}</h3><div class=legend>{legend}</div>'
            f'<svg viewBox="0 0 {W} {T + H + B}" style="width:100%;height:auto" id="{cid}">{"".join(p)}</svg>'
            f'<div class=tip id="{cid}-tip"></div><script type="application/json" id="{cid}-data">{json.dumps(data)}</script>'
            f'<details><summary>Table view</summary><div class=tw>{table}</div></details></div>')


def bar_chart(s: pd.Series, colour: str, title: str, cid: str) -> str:
    s = s.dropna()
    if len(s) < 2:
        return f'<div class=card><h3>{E(title)}</h3><p class=muted>Needs at least two sessions.</p></div>'
    W, H, L, R, T, B = 880, 200, 60, 20, 16, 28
    lo, hi = min(float(s.min()), 0), max(float(s.max()), 0)
    pad = (hi - lo) * 0.1 or 1
    lo, hi = lo - pad, hi + pad
    y = lambda v: T + (hi - v) / (hi - lo) * H
    n = len(s)
    bw = max(2.0, (W - L - R) / n - 2)
    p = [f'<rect x="{L}" y="{T}" width="{W - L - R}" height="{H}" fill="var(--surface)"/>']
    for tv in _axis_ticks(lo, hi):
        if lo <= tv <= hi:
            p.append(f'<line x1="{L}" x2="{W - R}" y1="{y(tv):.1f}" y2="{y(tv):.1f}" stroke="var(--line)"/>'
                     f'<text x="{L - 8}" y="{y(tv) + 4:.1f}" font-size="11" text-anchor="end" fill="var(--mut)">₹{tv:,.0f}</text>')
    p.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="var(--mut)"/>')
    rows = ""
    for i, (d, v) in enumerate(s.items()):
        x = L + (W - L - R) * (i + 0.5) / n - bw / 2
        top, h = (y(v), y(0) - y(v)) if v >= 0 else (y(0), y(v) - y(0))
        p.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(h, 0.5):.1f}" rx="2" fill="{colour}" opacity="{1 if v >= 0 else 0.55}">'
                 f'<title>{d.strftime("%d %b %Y")}: ₹{v:+,.0f}</title></rect>')
        if n <= 40 or i % max(1, n // 10) == 0:
            p.append(f'<text x="{x + bw / 2:.1f}" y="{T + H + 16}" font-size="10" text-anchor="middle" fill="var(--mut)">{d.strftime("%d %b")}</text>')
        rows += f"<tr><td class=l>{d.date()}</td><td>₹{v:+,.0f}</td></tr>"
    return (f'<div class=card><h3>{E(title)}</h3><svg viewBox="0 0 {W} {T + H + B}" style="width:100%;height:auto">{"".join(p)}</svg>'
            f'<details><summary>Table view</summary><div class=tw><table class=tv><thead><tr><th class=l>Date</th><th>Day P&amp;L</th></tr></thead><tbody>{rows}</tbody></table></div></details></div>')


# ---------------------------------------------------------------- pages
CSS = """:root{--bg:#f6f6f3;--card:#fff;--surface:#fcfcfb;--ink:#141413;--mut:#5f5e5a;--line:#e3e2dc;--pos:#1f7a4d;--neg:#b42318;--ybg:#fbf1d9;
--s-M2:#2a78d6;--s-M10:#eb6834;--s-M11:#1baf7a;--s-C0:#4a3aa7}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#121211;--card:#1b1b1a;--surface:#1a1a19;--ink:#f3f2ee;--mut:#b9b8b0;--line:#33332f;--pos:#5fd39a;--neg:#ff8a80;--ybg:#3a2e12;
--s-M2:#3987e5;--s-M10:#d95926;--s-M11:#199e70;--s-C0:#9085e9}}
:root[data-theme=dark]{--bg:#121211;--card:#1b1b1a;--surface:#1a1a19;--ink:#f3f2ee;--mut:#b9b8b0;--line:#33332f;--pos:#5fd39a;--neg:#ff8a80;--ybg:#3a2e12;--s-M2:#3987e5;--s-M10:#d95926;--s-M11:#199e70;--s-C0:#9085e9}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}.w{max-width:1100px;margin:auto;padding:20px 16px 48px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:26px 0 8px}h3{font-size:13px;margin:0 0 6px;color:var(--mut);font-weight:600}
.muted,.sub{color:var(--mut)}.sub{font-size:12px}.pos{color:var(--pos)}.neg{color:var(--neg)}
.card,.tw{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin:10px 0}.tw{overflow-x:auto;padding:0}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{color:var(--mut);font-weight:600;font-size:12px}.l{text-align:left}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0}.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.tile .k{font-size:11px;color:var(--mut)}.tile .v{font-size:20px;font-weight:600}
.legend{font-size:12px;color:var(--mut);margin-bottom:4px}.lg{margin-right:12px}.lg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:middle}
.tip{font-size:12px;color:var(--mut);min-height:18px}.banner{background:var(--ybg);border-radius:8px;padding:8px 12px;font-size:13px;margin:10px 0}
details summary{cursor:pointer;font-size:12px;color:var(--mut)}nav a{margin-right:14px}a{color:inherit}"""

JS = """document.querySelectorAll('rect.hit').forEach(function(r){var id=r.dataset.chart,d=JSON.parse(document.getElementById(id+'-data').textContent),
svg=document.getElementById(id),xl=document.getElementById(id+'-x'),tip=document.getElementById(id+'-tip');
function f(v){return v==null?'—':d.fmt==='mult'?v.toFixed(2)+'×':(d.fmt==='pct'?(v*100>=0?'+':'')+(v*100).toFixed(2)+'%':'₹'+Math.round(v).toLocaleString('en-IN'))}
r.addEventListener('mousemove',function(e){var pt=svg.createSVGPoint();pt.x=e.clientX;pt.y=e.clientY;var p=pt.matrixTransform(svg.getScreenCTM().inverse());
var best=0,bd=1e9;d.xs.forEach(function(x,i){var dd=Math.abs(x-p.x);if(dd<bd){bd=dd;best=i}});xl.setAttribute('x1',d.xs[best]);xl.setAttribute('x2',d.xs[best]);xl.setAttribute('opacity','0.5');
tip.textContent=d.dates[best]+' · '+Object.keys(d.series).map(function(k){return k+' '+f(d.series[k][best])}).join(' · ')});
r.addEventListener('mouseleave',function(){xl.setAttribute('opacity','0');tip.textContent=''})});"""


def pc(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.{d}f}%"


def cl(x):
    return "" if x is None or pd.isna(x) else ("pos" if x > 0 else "neg" if x < 0 else "")


def page(title: str, body: str, sub: str = "") -> str:
    return (f'<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'
            f'<title>{E(title)}</title><style>{CSS}</style></head><body><div class=w>'
            f'<nav class=sub><a href="overview.html">Overview</a>' + "".join(f'<a href="{k}.html">{k}</a>' for k in BOOKS) + '</nav>'
            f'<h1>{E(title)}</h1><div class=sub>{sub}</div>'
            f'<div class=banner>Paper books of pre-registered rules. Report, not advice. Numbers come from the ledgers named on each page; nothing here changes a book.</div>'
            f'{body}</div><script>{JS}</script></body></html>')


def tiles(st: dict) -> str:
    def v(k, x):
        if k in ("Return", "Max drawdown", "Win rate"):
            return f'<span class="{cl(x) if k != "Max drawdown" else "neg"}">{pc(x)}</span>'
        if k in ("Value", "Best day", "Worst day"):
            return f"₹{x:,.0f}"
        if isinstance(x, float):
            return "—" if pd.isna(x) else f"{x:.2f}"
        return E(str(x))
    return '<div class=tiles>' + "".join(f'<div class=tile><div class=k>{E(k)}</div><div class=v>{v(k, x)}</div></div>' for k, x in st.items()) + '</div>'


def trades_table(tr: pd.DataFrame) -> str:
    if not len(tr):
        return '<p class=muted>No closed trades yet.</p>'
    rows = "".join(f'<tr><td class=l><b>{E(str(r.sym))}</b></td><td>{E(str(r.entry_date))}</td><td>{E(str(r.exit_date))}</td><td>{r.qty:g}</td>'
                   f'<td>₹{r.entry:,.2f}</td><td>₹{r.exit:,.2f}</td><td class="{cl(r.ret_pct)}">{r.ret_pct:+.2f}%</td><td class="{cl(r.pnl)}">₹{r.pnl:+,.0f}</td><td class=l>{E(str(r.reason))}</td></tr>'
                   for r in tr.sort_values("exit_date", ascending=False).itertuples())
    return f'<div class=tw><table><thead><tr><th class=l>Stock</th><th>Entry date</th><th>Exit date</th><th>Qty</th><th>Entry</th><th>Exit</th><th>Return</th><th>P&amp;L</th><th class=l>Reason</th></tr></thead><tbody>{rows}</tbody></table></div>'


def positions_table(pos: dict) -> str:
    if not pos:
        return '<p class=muted>No open positions.</p>'
    rows = ""
    for s, p in sorted(pos.items(), key=lambda kv: -kv[1]["qty"] * kv[1]["last"]):
        r = p["last"] / p["entry"] - 1
        rows += (f'<tr><td class=l><b>{E(s)}</b> <span class=sub>{E(str(p.get("industry", "")))}</span></td><td>{E(str(p["entry_date"]))}</td><td>{p["qty"]:g}</td>'
                 f'<td>₹{p["entry"]:,.2f}</td><td>₹{p["last"]:,.2f}</td><td class="{cl(r)}">{pc(r)}</td><td>₹{p["stop"]:,.2f}</td><td class=neg>{pc(p["stop"] / p["last"] - 1, 1)}</td></tr>')
    return f'<div class=tw><table><thead><tr><th class=l>Stock</th><th>Since</th><th>Qty</th><th>Entry</th><th>Last</th><th>P&amp;L</th><th>Stop</th><th>Stop vs last</th></tr></thead><tbody>{rows}</tbody></table></div>'


def book_page(k: str, b: dict, bm: pd.DataFrame) -> str:
    st = stats(b)
    cum = pd.DataFrame({k: b["cum"]}).join(bm, how="left")
    body = tiles(st)
    body += f'<p class=sub>Rules, reasons and evidence: <a href="../{k}.md">strategy/{k}.md</a>. Ledger: <code>{"ledgers/" if k == "C0" else "live/ledgers/" + k + "/"}</code>.</p>'
    body += line_chart(cum, COL, "pct", f"{k} — cumulative return since {st['Start']} (Nifty 500 and B2-net dashed)", f"{k}-cum")
    body += line_chart(pd.DataFrame({k: b["dd"]}), COL, "pct", f"{k} — drawdown from peak", f"{k}-dd", fill_below_zero=True)
    body += bar_chart(b["pnl"], f"var(--s-{k})", f"{k} — daily P&L (₹)", f"{k}-pnl")
    body += f"<h2>Open positions ({len(b['pos'])})</h2>" + positions_table(b["pos"])
    body += f"<h2>Closed trades ({len(b['trades'])})</h2>" + trades_table(b["trades"])
    bt = backtest(k)
    if bt is not None:
        c = pd.DataFrame({f"{k} backtest": bt["equity"] / bt["equity"].iloc[0] - 1})
        for col in ("B2-net", "Nifty 500"):
            if col in bt.columns:
                c[col] = bt[col] / bt[col].iloc[0] - 1
        c = c.rename(columns={f"{k} backtest": k})
        ddb = bt["equity"] / bt["equity"].cummax() - 1
        body += f"<h2>Backtest 2013 → {bt.index[-1].date()} (development 2013–2020, holdout 2021 → 2026-10-07; 0.6% costs; fractional shares as in E2)</h2>"
        body += '<p class=sub>Development data selected the rule; the holdout was examined once. Both are history, not a forecast. The growth chart is on a log scale so each doubling takes the same height.</p>'
        body += line_chart(c.iloc[::5], COL, "pct", f"{k} — backtest growth of ₹1, log scale (every 5th session)", f"{k}-bt", log=True)
        body += line_chart(pd.DataFrame({k: ddb}).iloc[::5], COL, "pct", f"{k} — backtest drawdown", f"{k}-btdd", fill_below_zero=True)
        yr = bt["equity"].resample("YE").last().pct_change()
        yr.iloc[0] = bt["equity"].resample("YE").last().iloc[0] / bt["equity"].iloc[0] - 1
        rows = "".join(f'<tr><td class=l>{d.year}</td><td class="{cl(v)}">{pc(v, 1)}</td></tr>' for d, v in yr.items())
        body += f'<div class=tw><table><thead><tr><th class=l>Year</th><th>{k} return</th></tr></thead><tbody>{rows}</tbody></table></div>'
    else:
        body += f'<h2>Backtest</h2><p class=muted>No backtest curve yet. Run <code>.venv/bin/python strategy/backtest.py {k}</code> (needs the 2011→ point-in-time data).</p>'
    return page(f"{k} · {BOOKS[k]}", body, f"Generated {dt.date.today()} · ₹60,000 paper · 0.6% round-trip costs")


def overview(books: dict, bm: pd.DataFrame) -> str:
    rows = ""
    for k, b in books.items():
        s = stats(b)
        rows += (f'<tr><td class=l><b><a href="{k}.html">{k}</a></b> <span class=sub>{E(BOOKS[k])}</span></td><td>{s["Start"]}</td><td>₹{s["Value"]:,.0f}</td>'
                 f'<td class="{cl(s["Return"])}">{pc(s["Return"])}</td><td class=neg>{pc(s["Max drawdown"])}</td><td>{s["Sessions"]}</td><td>{s["Closed trades"]}</td>'
                 f'<td>{pc(s["Win rate"], 0) if not pd.isna(s["Win rate"]) else "—"}</td><td>{s["Open positions"]}</td></tr>')
    body = ('<h2>Scoreboard</h2><div class=tw><table><thead><tr><th class=l>Book</th><th>Start</th><th>Value</th><th>Return</th><th>Max DD</th><th>Sessions</th>'
            f'<th>Closed</th><th>Win</th><th>Open</th></tr></thead><tbody>{rows}</tbody></table></div>')
    live = pd.DataFrame({k: b["cum"] for k, b in books.items() if k != "C0"})
    c0 = books["C0"]["eq"]
    c0 = c0[c0.index >= live.index[0]]
    if len(c0):
        live["C0"] = c0 / c0.iloc[0] - 1
    cum = live.join(bm, how="left")
    body += line_chart(cum, COL, "pct", "Cumulative return since the forward-test start (08-Oct-2026)", "ov-cum")
    body += line_chart(pd.DataFrame({k: (b["eq"][b["eq"].index >= live.index[0]] / b["eq"][b["eq"].index >= live.index[0]].cummax() - 1) for k, b in books.items()}),
                       COL, "pct", "Drawdown from peak, same window", "ov-dd", fill_below_zero=True)
    for k, b in books.items():
        body += bar_chart(b["pnl"][b["pnl"].index >= live.index[0]], f"var(--s-{k})", f"{k} — daily P&L (₹)", f"ov-{k}")
    body += '<h2>Reading these pages</h2><p class=sub>Each book page carries its rule, why each stock was picked, entry/exit/stop, the development and holdout evidence and an append-only review log (strategy/&lt;ID&gt;.md). Win rates near 35–40% are normal for these rules: the return comes from a few large winners.</p>'
    return page("Strategy overview", body, f"Generated {dt.date.today()} · forward paper test since 08-Oct-2026 · C0 since 17-Sep-2026")


def main() -> None:
    global LED, OUT
    import sys
    if "--ledgers" in sys.argv:                  # test against a scratch ledger copy; output goes next to it
        LED = Path(sys.argv[sys.argv.index("--ledgers") + 1]).resolve()
        OUT = LED.parent / "reports"
    OUT.mkdir(parents=True, exist_ok=True)
    bm = benchmarks()
    books = {k: load_book(k) for k in BOOKS}
    for k, b in books.items():
        (OUT / f"{k}.html").write_text(book_page(k, b, bm))
        pd.DataFrame({"equity": b["eq"], "cum_return": b["cum"], "drawdown": b["dd"], "day_pnl": b["pnl"]}).to_csv(OUT / f"{k}_equity.csv")
        b["trades"].to_csv(OUT / f"{k}_trades.csv", index=False)
        print(OUT / f"{k}.html")
    (OUT / "overview.html").write_text(overview(books, bm))
    print(OUT / "overview.html")


if __name__ == "__main__":
    main()
