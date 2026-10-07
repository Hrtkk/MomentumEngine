"""Daily report (concise HTML) for one signal date. Reads ledgers only; never changes state.

Usage: python report.py --signal 2026-10-07 [--run-date 2026-10-08] [--provisional data/provisional_YYYY-MM-DD.json]
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import html
import json
import math
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
LED, DATA = ROOT / "ledgers", ROOT / "data"
PRIMARY = "c0.006"
CODE_TEXT = {
    "FREE_SLOT": "new entry — score ≥ 70, slot free", "MQS_LT_50": "score fell below 50",
    "INELIGIBLE": "failed liquidity/data checks", "STOP": "stop-loss hit", "BELOW_THRESHOLD": "score < 70",
    "NO_SLOT": "portfolio full; not ≥10 pts better than weakest", "COOLDOWN": "stopped out < 5 sessions ago",
    "NOT_AFFORDABLE": "one share > 20% of capital", "STOP_TOO_WIDE": "stop would be > 8% away",
    "NOT_IN_WINDOW": "not a gainer in last 7 sessions", "": "—",
}


def brief(x: str, n: int = 2, cap: int = 320) -> str:
    """First n sentences, capped — keeps the report short."""
    parts = str(x).replace("; ", ". ").split(". ")
    out = ". ".join(parts[:n]).strip()
    out = out if out.endswith(".") else out + "."
    return out if len(out) <= cap else out[:cap].rsplit(" ", 1)[0] + "…"


def esc(x) -> str:
    return html.escape(str(x))


def inr(x: float, d: int = 0) -> str:
    return f"₹{x:,.{d}f}"


def pct(x: float, d: int = 2, sign: bool = True) -> str:
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def cls(x: float) -> str:
    return "pos" if x > 0 else "neg" if x < 0 else ""


def load_challenge(t: str) -> dict:
    f = DATA / "codex" / f"challenge_{t}.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except json.JSONDecodeError:
        return {}


def pnl_chart(eqp: pd.DataFrame, fills: pd.DataFrame, start: float, window: int) -> str:
    """Inline SVG: cumulative return (book vs Nifty 500) + daily P&L bars, last `window` sessions; plus a table."""
    d = eqp.sort_values("date").reset_index(drop=True)
    d["pnl"] = d["equity"].diff().fillna(d["equity"] - start)
    d["ret_cum"] = d["equity"] / start - 1
    d["n5_cum"] = d["nifty500"] / d["nifty500"].iloc[0] - 1
    d["n5_day"] = d["nifty500"].pct_change().fillna(0)
    d = d.tail(window + 1).reset_index(drop=True) if len(d) > window + 1 else d
    n = len(d)
    if n < 2:
        return '<p class="muted">Chart starts after the second session.</p>'
    W, H1, H2, L, R, T = 760, 170, 110, 58, 26, 14
    xs = [L + i * (W - L - R) / (n - 1) for i in range(n)]
    lo = min(d["ret_cum"].min(), d["n5_cum"].min(), 0)
    hi = max(d["ret_cum"].max(), d["n5_cum"].max(), 0)
    pad = (hi - lo) * 0.12 or 0.005
    lo, hi = lo - pad, hi + pad
    y1 = lambda v: T + (hi - v) / (hi - lo) * H1
    def path(col):
        return " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f},{y1(v):.1f}" for i, v in enumerate(d[col]))
    step = next(x for x in (0.0025, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2) if (hi - lo) / x <= 6)
    lo, hi = math.floor(lo / step) * step, math.ceil(hi / step) * step
    grid = ""
    for k in range(int(round((hi - lo) / step)) + 1):
        v = lo + k * step
        grid += (f'<line x1="{L}" x2="{W - R}" y1="{y1(v):.1f}" y2="{y1(v):.1f}" class="g"/>'
                 f'<text x="{L - 6}" y="{y1(v) + 4:.1f}" class="ax" text-anchor="end">{v * 100:+.1f}%</text>')
    zero = f'<line x1="{L}" x2="{W - R}" y1="{y1(0):.1f}" y2="{y1(0):.1f}" class="z"/>'
    dots = "".join(f'<circle cx="{xs[i]:.1f}" cy="{y1(v):.1f}" r="2.6" class="bk"><title>{d["date"][i]}: {v * 100:+.2f}% (₹{d["equity"][i]:,.0f})</title></circle>'
                   for i, v in enumerate(d["ret_cum"]))
    top = 2 * T + H1
    pm = max(d["pnl"].abs().max(), 1)
    y2 = lambda v: top + H2 / 2 - v / pm * (H2 / 2 - 4)
    bw = max(4, (W - L - R) / n * 0.55)
    bars = "".join(
        f'<rect x="{xs[i] - bw / 2:.1f}" y="{min(y2(v), y2(0)):.1f}" width="{bw:.1f}" height="{abs(y2(v) - y2(0)):.1f}" '
        f'class="{"bp" if v >= 0 else "bn"}"><title>{d["date"][i]}: {"+" if v >= 0 else "−"}₹{abs(v):,.0f}</title></rect>'
        for i, v in enumerate(d["pnl"]) if i > 0 or len(eqp) <= window + 1)
    xl = "".join(f'<text x="{xs[i]:.1f}" y="{top + H2 + 16}" class="ax" text-anchor="middle">{pd.Timestamp(d["date"][i]).strftime("%d %b")}</text>'
                 for i in range(n) if n <= 14 or i % 2 == 0)
    svg = f"""<svg viewBox="0 0 {W} {top + H2 + 24}" role="img" aria-label="Cumulative return and daily P&L">
<style>.g{{stroke:var(--line);stroke-width:1}}.z{{stroke:var(--mut);stroke-width:1;stroke-dasharray:3 3}}.ax{{fill:var(--mut);font-size:11px}}
.lb{{fill:none;stroke:var(--acc);stroke-width:2.2}}.ln{{fill:none;stroke:var(--mut);stroke-width:1.6;stroke-dasharray:5 4}}.bk{{fill:var(--acc)}}
.bp{{fill:var(--pos)}}.bn{{fill:var(--neg)}}</style>
{grid}{zero}<path d="{path('n5_cum')}" class="ln"/><path d="{path('ret_cum')}" class="lb"/>{dots}
<line x1="{L}" x2="{W - R}" y1="{y2(0):.1f}" y2="{y2(0):.1f}" class="z"/>
<text x="{L - 6}" y="{y2(pm) + 4:.1f}" class="ax" text-anchor="end">+₹{pm:,.0f}</text><text x="{L - 6}" y="{y2(-pm) + 4:.1f}" class="ax" text-anchor="end">−₹{pm:,.0f}</text>
{bars}{xl}</svg>"""
    trades = fills.groupby("date").size().to_dict() if not fills.empty else {}
    rows = "".join(
        f'<tr><td class="l">{pd.Timestamp(r["date"]).strftime("%a %d %b")}</td><td class="{cls(r["pnl"])}">{"+" if r["pnl"] >= 0 else "−"}₹{abs(r["pnl"]):,.0f}</td>'
        f'<td class="{cls(r["pnl"])}">{r["pnl"] / (r["equity"] - r["pnl"]) * 100:+.2f}%</td><td class="{cls(r["n5_day"])}">{r["n5_day"] * 100:+.2f}%</td>'
        f'<td>₹{r["equity"]:,.0f}</td><td class="{cls(r["ret_cum"])}">{r["ret_cum"] * 100:+.2f}%</td><td class="{cls(r["n5_cum"])}">{r["n5_cum"] * 100:+.2f}%</td>'
        f'<td>{int(r["n_positions"])}</td><td>{trades.get(r["date"], 0)}</td></tr>'
        for _, r in d.iloc[::-1].iterrows())
    legend = ('<div class="legend"><span><i class="sw" style="background:var(--acc)"></i>Paper book (cumulative)</span>'
              '<span><i class="sw dash"></i>Nifty 500 (cumulative)</span><span><i class="sw" style="background:var(--pos)"></i>/<i class="sw" style="background:var(--neg)"></i> Daily P&amp;L (₹)</span></div>')
    table = ('<div class="tw" style="margin-top:10px"><table><thead><tr><th class="l">Session</th><th>P&amp;L</th><th>P&amp;L %</th><th>Nifty 500</th>'
             '<th>Value</th><th>Cum.</th><th>Nifty cum.</th><th>Stocks</th><th>Trades</th></tr></thead><tbody>' + rows + "</tbody></table></div>")
    return f'<div class="card">{legend}{svg}</div>{table}'


def build(t: str, run_date: str | None, provisional: dict | None) -> Path:
    run = json.loads((LED / f"run_{t}.json").read_text())
    state = json.loads((LED / "state.json").read_text())
    bk = state["books"][PRIMARY]
    eq = pd.read_csv(LED / "equity.csv")
    eqp = eq[eq["book"] == PRIMARY].sort_values("date")
    cand = pd.read_csv(DATA / "candidates.csv")
    c_t = cand[cand["date"] == t].set_index("symbol")
    wl = pd.read_csv(LED / "watchlist.csv")
    wl = wl[wl["book"] == PRIMARY]
    dates = sorted(wl["date"].unique())
    prev_t = dates[dates.index(t) - 1] if dates.index(t) > 0 else None
    fills = pd.read_csv(LED / "fills.csv") if (LED / "fills.csv").exists() else pd.DataFrame()
    fills = fills[fills["book"] == PRIMARY] if not fills.empty else fills
    ch = load_challenge(t)
    chp = {p["symbol"]: p for p in ch.get("picks", [])}

    E = eqp[eqp["date"] == t]["equity"].iloc[0]
    start = float(yaml.safe_load((ROOT / "config" / "parameters.yaml").read_text())["paper_capital"])
    prevE = eqp[eqp["date"] < t]["equity"].iloc[-1] if (eqp["date"] < t).any() else start
    n5 = eqp.set_index("date")["nifty500"]
    n5_day = n5[t] / n5[prev_t] - 1 if prev_t else 0.0
    first = eqp["date"].iloc[0]
    n5_total = n5[t] / n5[first] - 1
    cash = bk["cash"]

    # ---- holdings table
    rows = []
    for s, p in sorted(bk["positions"].items(), key=lambda kv: -kv[1]["qty"] * kv[1]["last"]):
        r = c_t.loc[s] if s in c_t.index else None
        val = p["qty"] * p["last"]
        top3 = ", ".join(ast.literal_eval(r["top3"])) if r is not None and isinstance(r["top3"], str) else ""
        cp = chp.get(s, {})
        sev = cp.get("severity", "")
        rows.append(f"""<tr><td class="l"><b>{esc(s)}</b><div class="sub">{esc(r['name'] if r is not None else '')}</div></td>
<td class="l sub">{esc(r['industry'] if r is not None else '')}</td>
<td><b>{val / E * 100:.1f}%</b></td><td>{p['qty']:g}</td><td>{inr(val)}</td>
<td>{inr(p['entry'], 2)}</td><td>{inr(p['last'], 2)}</td><td class="{cls(p['last'] / p['entry'] - 1)}">{pct(p['last'] / p['entry'] - 1)}</td>
<td>{inr(p['stop'], 2)}<div class="sub">{pct(p['stop'] / p['last'] - 1, 1)}</div></td>
<td><b>{r['mqs']:.0f}</b></td>
<td class="l why">{esc(top3)}{f'<div class="ch sev-{esc(sev)}"><span>Codex · {esc(sev)}</span> {esc(cp.get("bear_case", ""))}</div>' if cp else ''}</td></tr>""")
    hold_html = "\n".join(rows) or '<tr><td colspan="11" class="l">No positions — all cash.</td></tr>'

    # ---- what changed
    today = wl[wl["date"] == t]
    adds = today[today["action"] == "ADD"]
    rem = today[today["action"].isin(["REMOVE", "REPLACED"])]
    keeps = today[today["action"] == "KEEP"]
    stops = fills[(fills["date"] == t) & (fills["reason"] == "STOP")] if not fills.empty else pd.DataFrame()
    prev_mqs = {}
    if prev_t:
        pv = cand[cand["date"] == prev_t].set_index("symbol")["mqs"]
        prev_mqs = pv.to_dict()
    chg = []
    buys = fills[(fills["date"] == t) & (fills["side"] == "buy")] if not fills.empty else pd.DataFrame()
    for _, r in adds.iterrows():
        cr = c_t.loc[r["symbol"]]
        chg.append(f'<li><span class="tag add">ADDED</span> <b>{esc(r["symbol"])}</b> — score {r["mqs"]:.0f}. '
                   f'{esc(CODE_TEXT.get(r["code"], r["code"]))}. Strengths: {esc(", ".join(ast.literal_eval(cr["top3"])))}.</li>')
    for _, r in rem.iterrows():
        chg.append(f'<li><span class="tag rem">{"REPLACED" if r["action"] == "REPLACED" else "REMOVED"}</span> '
                   f'<b>{esc(r["symbol"])}</b> — {esc(CODE_TEXT.get(r["code"], r["code"]))} (score {r["mqs"]:.0f}). Sells at next open.</li>')
    for _, r in stops.iterrows():
        chg.append(f'<li><span class="tag rem">STOPPED</span> <b>{esc(r["symbol"])}</b> — stop hit at {inr(r["price"], 2)} '
                   f'({pct(r["price"] / r["entry"] - 1)} from entry). 5-session cooldown.</li>')
    moves = []
    for _, r in keeps.iterrows():
        s = r["symbol"]
        if s in prev_mqs and pd.notna(prev_mqs[s]):
            moves.append((r["mqs"] - prev_mqs[s], s, prev_mqs[s], r["mqs"]))
    moves.sort()
    kept_line = ""
    if len(keeps):
        mv = ", ".join(f"{s} {a:.0f}→{b:.0f}" for d, s, a, b in (moves[:2] + moves[-2:] if len(moves) > 4 else moves))
        kept_line = (f'<li><span class="tag keep">KEPT</span> {len(keeps)} names held — none fell below 50 and no challenger '
                     f'beat the weakest by ≥10 pts.{(" Biggest score moves: " + esc(mv) + ".") if mv else ""}</li>')
    if len(buys):
        chg.insert(0, '<li><span class="tag add">BOUGHT</span> at today\'s open (from the previous session\'s signals): '
                   + ", ".join(f'<b>{esc(r["symbol"])}</b> {r["qty"]:g}@{inr(r["price"], 2)}' for _, r in buys.iterrows()) + "</li>")
    chg.append(kept_line)
    if not adds.empty or not rem.empty or not stops.empty:
        headline = f"{len(adds)} added · {len(rem)} removed · {len(stops)} stopped out · {len(keeps)} kept"
    else:
        headline = "No changes — every holding kept"
    if len(buys):
        headline = f"{len(buys)} bought at open · " + headline[0].lower() + headline[1:]
    if prev_t is None:
        headline = "First day — portfolio built from scratch"

    # ---- orders for the open
    orders = run["orders"]
    if orders:
        orows = []
        for o in orders:
            prov = (provisional or {}).get(o["symbol"])
            orows.append(f'<tr><td class="l"><b>{esc(o["side"].upper())}</b></td><td class="l">{esc(o["symbol"])}</td>'
                         f'<td>{o.get("qty", "all")}</td><td>{inr(o.get("ref_close", 0), 2) if o.get("ref_close") else "—"}</td>'
                         f'<td>{(pct(o["target_w"], 1, False)) if o.get("target_w") else "—"}</td>'
                         f'<td>{inr(o["stop"], 2) if o.get("stop") else "—"}</td>'
                         f'<td>{(inr(prov, 2) + " <span class=sub>provisional</span>") if prov else "pending open"}</td></tr>')
        order_html = ('<table><thead><tr><th class="l">Side</th><th class="l">Stock</th><th>Qty</th><th>Ref close</th>'
                      '<th>Target wt</th><th>Stop</th><th>Fill</th></tr></thead><tbody>' + "".join(orows) + "</tbody></table>")
    else:
        order_html = '<p class="muted">No trades at today\'s open.</p>'

    # ---- next in line
    nm = today[today["action"] == "WATCH"].head(5)
    nmc = {x["symbol"]: x.get("comment", "") for x in ch.get("near_miss", [])}
    nm_html = "".join(
        f'<li><b>{esc(r["symbol"])}</b> {r["mqs"]:.0f} — {esc(CODE_TEXT.get(r["code"] if isinstance(r["code"], str) else "", r["code"]))}'
        f'{(" · <span class=sub>Codex: " + esc(nmc[r["symbol"]]) + "</span>") if nmc.get(r["symbol"]) else ""}</li>'
        for _, r in nm.iterrows())

    # ---- other books
    others = eq[(eq["date"] == t)].set_index("book")["equity"]
    books_line = " · ".join(f"{k}: {inr(v)} ({pct(v / start - 1)})" for k, v in others.items())

    port = ch.get("portfolio", {})
    notes = [esc(n) for n in run.get("exec_notes", [])]
    risk_html = ""
    if port:
        risk_html += f'<p><b>Concentration.</b> {esc(brief(port.get("concentration", "")))}</p>'
        risk_html += f'<p><b>Regime.</b> {esc(brief(port.get("regime", ""), 1))}</p>'
        if port.get("shadow_variant_proposal"):
            risk_html += f'<p><b>Proposed shadow test.</b> {esc(brief(port["shadow_variant_proposal"], 2))}</p>'
    if ch.get("overall"):
        risk_html += f'<p><b>Codex overall.</b> {esc(brief(ch["overall"], 2))}</p>'
    if notes:
        risk_html += "<p><b>Execution notes.</b> " + "; ".join(notes) + "</p>"

    nf = DATA / "claude" / f"notes_{t}.json"
    cnotes = json.loads(nf.read_text()) if nf.exists() else []
    notes_html = "".join(
        f'<li><b>{esc(n["symbol"])}</b> — {esc(n["note"])} '
        f'{"".join(f"<a href={chr(34)}{esc(u)}{chr(34)} target=_blank rel=noopener>[src]</a> " for u in n.get("sources", []))}</li>'
        for n in cnotes)
    window = int(yaml.safe_load((ROOT / "config" / "parameters.yaml").read_text()).get("chart_sessions", 13))
    chart_html = pnl_chart(eqp[eqp["date"] <= t], fills[fills["date"] <= t] if not fills.empty else fills, start, window)
    rd = run_date or t
    rd_label = dt.date.fromisoformat(rd).strftime("%a %d %b %Y")
    t_label = dt.date.fromisoformat(t).strftime("%a %d %b")
    invested = E - cash
    day_pnl = E - prevE
    tot_pnl = E - start
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Momentum Desk {esc(rd)}</title>
<style>
:root{{--bg:#f6f6f3;--card:#fff;--ink:#141413;--mut:#5f5e5a;--line:#e3e2dc;--pos:#1f7a4d;--neg:#b42318;--acc:#2e5aac;--abg:#e8eefb;--gbg:#e3f3ea;--rbg:#fde8e6;--ybg:#fbf1d9;--ytx:#8a5a00}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#121211;--card:#1b1b1a;--ink:#f3f2ee;--mut:#b9b8b0;--line:#33332f;--pos:#5fd39a;--neg:#ff8a80;--acc:#8fb0f0;--abg:#1b2640;--gbg:#173326;--rbg:#3b1a17;--ybg:#3a2e12;--ytx:#e8b44a}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:20px 16px 40px}}h1{{font-size:20px;margin:0}}h2{{font-size:15px;margin:26px 0 8px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}}
.muted,.sub{{color:var(--mut)}}.sub{{font-size:12px}}.pos{{color:var(--pos)}}.neg{{color:var(--neg)}}
.banner{{background:var(--ybg);color:var(--ytx);border-radius:8px;padding:8px 12px;font-size:13px;margin:10px 0}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}}.k{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}}.k b{{display:block;font-size:20px}}.k span{{font-size:12px;color:var(--mut)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}}
.tw{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap;vertical-align:top}}th{{font-weight:600;color:var(--mut);font-size:12px}}.l{{text-align:left}}
td.why{{white-space:normal;min-width:240px;font-size:12px}}.ch{{margin-top:4px;padding:4px 6px;border-radius:6px;background:var(--abg)}}.ch span{{font-weight:600}}
.sev-high{{background:var(--rbg)}}.sev-medium{{background:var(--ybg)}}
ul.chg{{list-style:none;padding:0;margin:0}}ul.chg li{{padding:6px 0;border-bottom:1px solid var(--line)}}ul.chg li:last-child{{border:0}}
.tag{{display:inline-block;font-size:11px;font-weight:700;border-radius:99px;padding:1px 8px;margin-right:4px}}.add{{background:var(--gbg);color:var(--pos)}}.rem{{background:var(--rbg);color:var(--neg)}}.keep{{background:var(--abg);color:var(--acc)}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--mut);margin-bottom:4px}}.sw{{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:5px}}.sw.dash{{border-top:2px dashed var(--mut);height:0}}
svg{{width:100%;height:auto;display:block}}
footer{{margin-top:28px;font-size:12px;color:var(--mut)}}
</style></head><body><div class="wrap">
<h1>Momentum Desk — {esc(rd_label)}</h1>
<div class="sub">Signals from {esc(t_label)} close · Strategy v{esc(run['version'])} · paper book {inr(start)} · cost assumption 0.6% round-trip</div>
<div class="banner">Paper simulation of pre-registered rules. The rule output is not a recommendation; real-money decisions are yours.{' <b>DRY RUN.</b>' if provisional is None and run_date and run_date != t else ''}</div>

<div class="kpis">
<div class="k"><span>Portfolio value</span><b>{inr(E)}</b><span>{pct(invested / E, 0, False)} invested · {inr(cash)} cash</span></div>
<div class="k"><span>Today's P&amp;L</span><b class="{cls(day_pnl)}">{'+' if day_pnl >= 0 else '−'}{inr(abs(day_pnl))}</b><span class="{cls(day_pnl)}">{pct(day_pnl / prevE)}</span> <span>· Nifty 500 {pct(n5_day)}</span></div>
<div class="k"><span>Since start ({esc(first)})</span><b class="{cls(tot_pnl)}">{'+' if tot_pnl >= 0 else '−'}{inr(abs(tot_pnl))}</b><span class="{cls(tot_pnl)}">{pct(tot_pnl / start)}</span> <span>· Nifty 500 {pct(n5_total)}</span></div>
<div class="k"><span>Market regime</span><b>{esc(run['regime'])}</b><span>{pct(run['breadth'], 0, False)} of Nifty 500 above 50-DMA</span></div>
</div>

<h2>P&amp;L — last {min(len(eqp) - 1, window)} sessions</h2>
{chart_html}

<h2>1 · What changed — {esc(headline)}</h2>
<div class="card"><ul class="chg">{''.join(chg)}</ul></div>

<h2>2 · Today's portfolio ({len(bk['positions'])} stocks)</h2>
<div class="tw"><table><thead><tr><th class="l">Stock</th><th class="l">Sector</th><th>Weight</th><th>Qty</th><th>Value</th><th>Entry</th><th>Last</th><th>P&amp;L</th><th>Stop</th><th>Score</th><th class="l">Why it's held · challenger's bear case</th></tr></thead>
<tbody>{hold_html}</tbody></table></div>

<h2>3 · Orders for today's open</h2>
{order_html}

<h2>4 · Risks flagged</h2>
<div class="card">{risk_html or '<p class="muted">No challenger review available.</p>'}</div>

<h2>5 · News check (Claude, sourced · no effect on rules)</h2>
<div class="card"><ul class="chg">{notes_html or '<li class="muted">No notes today.</li>'}</ul></div>

<h2>6 · Next in line</h2>
<div class="card"><ul class="chg">{nm_html or '<li class="muted">—</li>'}</ul></div>

<footer>
<p><b>How to read.</b> Score (0–100) ranks today's eligible gainers on relative strength, trend, volume/delivery, breakout, repeat appearances, sector and smoothness. Add ≥ 70 · remove &lt; 50 · replace only if ≥ 10 pts better · stop = 2× ATR below signal close · weights ≈ 1/N (max 20%).</p>
<p><b>Other books.</b> {esc(books_line)}. <b>Research cohorts:</b> first 10-session results mature after 10 more sessions; they, not this paper book, decide whether the strategy works.</p>
<p>Sources: NSE bhavcopy &amp; index closes ({esc(t)}), Yahoo history, Codex cross-check via Economic Times. Run {esc(run['n_disc'])} discovered · {esc(run['n_cand'])} candidates.</p>
</footer></div></body></html>"""
    out = ROOT / "reports" / f"{rd}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--signal", required=True)
    ap.add_argument("--run-date")
    ap.add_argument("--provisional")
    a = ap.parse_args()
    prov = json.loads(Path(a.provisional).read_text()) if a.provisional else None
    print(build(a.signal, a.run_date, prov))
