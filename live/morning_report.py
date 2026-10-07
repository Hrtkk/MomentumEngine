"""Schedule 3 — morning report (≈10:35 IST, Mon–Fri). Reads ledgers only; never changes book state.

Usage: python morning_report.py [--no-provisional]
Writes reports/desk_<today>.html and reports/desk_<today>_holdings.csv; prints both paths.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ME = HERE.parent
LED = HERE / "ledgers"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
BOOKS = {"M11": "52-week-high breakout", "M10": "Gainer event + confirmation", "M2": "6-month momentum"}
CAP = 60_000.0
E = html.escape


def inr(x, d=0):
    return "—" if x is None or pd.isna(x) else f"₹{x:,.{d}f}"


def pc(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.{d}f}%"


def cl(x):
    return "" if x is None or pd.isna(x) else ("pos" if x > 0 else "neg" if x < 0 else "")


def provisional_opens(symbols: list[str], today: dt.date) -> dict:
    if not symbols:
        return {}
    try:
        import yfinance as yf
        df = yf.download([f"{s}.NS" for s in symbols], period="5d", interval="1d", auto_adjust=False,
                         group_by="ticker", progress=False)
        out = {}
        for s in symbols:
            try:
                sub = df[f"{s}.NS"].dropna(how="all")
                sub.index = pd.to_datetime(sub.index).tz_localize(None).normalize()
                if pd.Timestamp(today) in sub.index:
                    out[s] = float(sub.loc[pd.Timestamp(today), "Open"])
            except Exception:
                pass
        return out
    except Exception:
        return {}


def expected_fills(snap: dict) -> list[dict]:
    """Mirror the execution layer: sells first, then buys in order while slots (10) and industry cap (3, known) allow."""
    pos = dict(snap["positions"])
    for o in snap["orders_next_open"]:
        if o["side"] == "sell":
            pos.pop(o["sym"], None)
    out, inds, skipped = [], {}, []
    for p in pos.values():
        inds[p["industry"]] = inds.get(p["industry"], 0) + 1
    n = len(pos)
    for o in snap["orders_next_open"]:
        if o["side"] != "buy":
            continue
        ind = o.get("signal", {}).get("industry", "Unknown")
        if n >= 10:
            break
        if ind != "Unknown" and inds.get(ind, 0) >= 3:
            continue
        if o["qty"] < 1:                                   # whole shares: slot too small for one share
            skipped.append(o)
            continue
        out.append(o)
        inds[ind] = inds.get(ind, 0) + 1
        n += 1
    return out, skipped


def svg_chart(curves: pd.DataFrame) -> str:
    c = curves.dropna(how="all").ffill()
    if len(c) < 2:
        return '<p class="muted">The chart starts after the second live session. Day 1 is the first fill at the 08-Oct open.</p>'
    W, H, L, R, T = 760, 220, 52, 120, 12
    lo, hi = min(c.min().min(), 0), max(c.max().max(), 0)
    pad = (hi - lo) * 0.15 or 0.01
    lo, hi = lo - pad, hi + pad
    xs = np.linspace(L, W - R, len(c))
    y = lambda v: T + (hi - v) / (hi - lo) * H
    pal = {"M11": "#15803d", "M10": "#c2410c", "M2": "#2e5aac", "C0 (legacy)": "#be123c", "Nifty 500": "#9ca3af", "B2-net": "#6b7280"}
    parts = [f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="var(--mut)" stroke-dasharray="3 3"/>']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        parts.append(f'<text x="{L - 6}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end" fill="var(--mut)">{v * 100:+.1f}%</text>')
    for col in c.columns:
        pts = " ".join(f"{xs[i]:.1f},{y(v):.1f}" for i, v in enumerate(c[col].values))
        dash = ' stroke-dasharray="5 4"' if col in ("Nifty 500", "B2-net") else ""
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{pal.get(col, "#111")}" stroke-width="2"{dash}/>')
        parts.append(f'<text x="{W - R + 6}" y="{y(c[col].iloc[-1]) + 4:.1f}" font-size="11" fill="{pal.get(col, "#111")}">{E(col)} {c[col].iloc[-1] * 100:+.1f}%</text>')
    for i in range(len(c)):
        if len(c) <= 15 or i % 3 == 0:
            parts.append(f'<text x="{xs[i]:.0f}" y="{T + H + 14}" font-size="10" text-anchor="middle" fill="var(--mut)">{pd.Timestamp(c.index[i]).strftime("%d %b")}</text>')
    return f'<svg viewBox="0 0 {W} {T + H + 22}" style="width:100%;height:auto">{"".join(parts)}</svg>'


def main(provisional: bool = True) -> None:
    today = dt.datetime.now(IST).date()
    last = json.loads((LED / "last_run.json").read_text())
    t = last["last_session"]
    snaps = {k: json.loads((LED / k / f"snapshot_{t}.json").read_text()) for k in BOOKS if (LED / k / f"snapshot_{t}.json").exists()}
    bm = pd.read_csv(LED / "benchmarks.csv", parse_dates=["date"]).set_index("date")
    curves = pd.DataFrame(index=bm.index)
    rows = []
    for k in BOOKS:
        eq = pd.read_csv(LED / k / "equity.csv", parse_dates=["date"]).set_index("date")["equity"]
        curves[k] = eq / CAP - 1
        day = eq.iloc[-1] - eq.iloc[-2] if len(eq) > 1 else 0.0
        rows.append((k, BOOKS[k], eq.iloc[-1], day, eq.iloc[-1] / CAP - 1, len(snaps.get(k, {}).get("positions", {}))))
    # C0 legacy book (src/engine.py) — its own start; shown since live start for comparability
    c0 = pd.read_csv(ME / "ledgers" / "equity.csv")
    c0 = c0[c0["book"] == "c0.006"].assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")["equity"]
    c0s = c0[c0.index >= bm.index[0]]
    if len(c0s):
        base = c0s.iloc[0]
        curves["C0 (legacy)"] = c0s / base - 1
        st0 = json.loads((ME / "ledgers" / "state.json").read_text())["books"]["c0.006"]
        rows.append(("C0", "Current live rules (legacy control)", c0s.iloc[-1], c0s.iloc[-1] - c0s.iloc[-2] if len(c0s) > 1 else 0.0,
                     c0s.iloc[-1] / base - 1, len(st0["positions"])))
    curves["Nifty 500"] = bm["nifty500"] / bm["nifty500"].iloc[0] - 1
    curves["B2-net"] = bm["b2net_cum"] / bm["b2net_cum"].iloc[0] - 1
    n5d = bm["nifty500"].iloc[-1] / bm["nifty500"].iloc[-2] - 1 if len(bm) > 1 else 0.0
    # orders + provisional opens
    exp, unaff = {}, {}
    for k, s in snaps.items():
        exp[k], unaff[k] = expected_fills(s)
    sells = {k: [o for o in s["orders_next_open"] if o["side"] == "sell"] for k, s in snaps.items()}
    syms = sorted({o["sym"] for k in exp for o in exp[k]} | {o["sym"] for k in sells for o in sells[k]})
    prov = provisional_opens(syms, today) if provisional else {}
    ch = {}
    chf = HERE / "codex" / f"challenge_{t}.json"
    if chf.exists():
        try:
            ch = json.loads(chf.read_text())
        except json.JSONDecodeError:
            ch = {}
    chp = {(p.get("book"), p.get("symbol")): p for p in ch.get("picks", [])}
    # ---- html
    kpi = "".join(f'<tr><td class=l><b>{E(k)}</b> <span class=sub>{E(n)}</span></td><td>{inr(v)}</td>'
                  f'<td class="{cl(d)}">{"+" if d >= 0 else "−"}{inr(abs(d))}</td><td class="{cl(s)}">{pc(s)}</td><td>{p}</td></tr>'
                  for k, n, v, d, s, p in rows)
    kpi += (f'<tr class=bm><td class=l>Nifty 500</td><td>—</td><td class="{cl(n5d)}">{pc(n5d)}</td>'
            f'<td class="{cl(curves["Nifty 500"].iloc[-1])}">{pc(curves["Nifty 500"].iloc[-1])}</td><td>—</td></tr>'
            f'<tr class=bm><td class=l>B2-net (equal-weight Liquid-500)</td><td>—</td><td>—</td>'
            f'<td class="{cl(curves["B2-net"].iloc[-1])}">{pc(curves["B2-net"].iloc[-1])}</td><td>—</td></tr>')
    sections = ""
    hold_rows = []
    for k, s in snaps.items():
        ords = ""
        for o in sells[k]:
            ords += f'<tr><td class=l><span class="tag rem">SELL</span> <b>{E(o["sym"])}</b></td><td colspan=6 class=l>{E(o.get("reason", ""))}</td><td>{inr(prov.get(o["sym"]), 2)}</td></tr>'
        for o in exp[k]:
            sg, cp = o.get("signal", {}), chp.get((k, o["sym"]), {})
            ords += (f'<tr><td class=l><span class="tag add">BUY</span> <b>{E(o["sym"])}</b><div class=sub>{E(sg.get("industry", ""))}</div></td>'
                     f'<td>{int(o["qty"])}</td><td>{inr(sg.get("close"), 2)}</td><td>{inr(o["stop"], 2)}</td>'
                     f'<td>{sg.get("rank", "—")}</td><td>{pc(sg.get("R6"), 0)}</td>'
                     f'<td class=l sub>{sg.get("vol_x_median20", "—")}× vol · {pc(sg.get("vs_sma20"), 1)} vs SMA20 · RSI {round(sg["rsi14"]) if sg.get("rsi14") is not None else "—"}'
                     f'{("<div class=ch>Codex · " + E(cp.get("severity", "")) + ": " + E(cp.get("bear_case", "")) + "</div>") if cp else ""}</td>'
                     f'<td>{inr(prov.get(o["sym"]), 2)}</td></tr>')
        if unaff[k]:
            ords += (f'<tr><td class="l sub" colspan=8>Not affordable with a ₹6,000 slot (one share costs more): '
                     f'{E(", ".join(o["sym"] + " ₹" + format(o.get("signal", {}).get("close", 0), ",.0f") for o in unaff[k]))}</td></tr>')
        ords = ords or '<tr><td class="l muted" colspan=8>No orders at today\'s open.</td></tr>'
        E_ = s["equity"]
        hrows = ""
        for sym, p in sorted(s["positions"].items(), key=lambda kv: -kv[1]["qty"] * kv[1]["last"]):
            v = p["qty"] * p["last"]
            hold_rows.append({"date": str(today), "signal_date": t, "book": k, "symbol": sym, "industry": p["industry"],
                              "qty": p["qty"], "entry": p["entry"], "last": p["last"], "weight_pct": round(v / E_ * 100, 1),
                              "pnl_pct": round((p["last"] / p["entry"] - 1) * 100, 2), "stop": p["stop"]})
            hrows += (f'<tr><td class=l><b>{E(sym)}</b> <span class=sub>{E(p["industry"])}</span></td><td>{v / E_ * 100:.1f}%</td><td>{p["qty"]:g}</td>'
                      f'<td>{inr(p["entry"], 2)}</td><td>{inr(p["last"], 2)}</td><td class="{cl(p["last"] / p["entry"] - 1)}">{pc(p["last"] / p["entry"] - 1)}</td>'
                      f'<td>{inr(p["stop"], 2)}</td><td>{E(p["entry_date"])}</td></tr>')
        hrows = hrows or '<tr><td class="l muted" colspan=8>No holdings yet.</td></tr>'
        bk_note = ch.get("books", {}).get(k, "")
        sections += f"""<h2>{E(k)} · {E(BOOKS[k])}</h2>
<div class=tw><table><thead><tr><th class=l>Order at today's open</th><th>Qty</th><th>Signal close</th><th>Stop</th><th>Rank</th><th>6M ret</th><th class=l>Signal record · challenger</th><th>Open (prov.)</th></tr></thead><tbody>{ords}</tbody></table></div>
<div class=tw style="margin-top:8px"><table><thead><tr><th class=l>Holding</th><th>Weight</th><th>Qty</th><th>Entry</th><th>Last</th><th>P&amp;L</th><th>Stop</th><th>Since</th></tr></thead><tbody>{hrows}</tbody></table></div>
{('<p class=sub><b>Codex on this book:</b> ' + E(bk_note) + '</p>') if bk_note else ''}"""
    # notes, research, exceptions
    nf = HERE / "notes" / f"notes_{t}.json"
    notes = json.loads(nf.read_text()) if nf.exists() else []
    notes_html = "".join(f'<li><b>{E(n["symbol"])}</b> — {E(n["note"])} ' + " ".join(f'<a href="{E(u)}" target=_blank rel=noopener>[src]</a>' for u in n.get("sources", [])) + "</li>" for n in notes) or '<li class=muted>No news check yet.</li>'
    rs = sorted((ME / "reviews").glob("research_*.md"))
    research = ""
    if rs:
        txt = rs[-1].read_text().strip().splitlines()
        research = f'<p><b>{E(rs[-1].name)}</b></p><pre>{E(chr(10).join(txt[:18]))}</pre>'
    exc = []
    ev = LED / f"evening_{t}.json"
    for f in sorted(LED.glob("evening_*.json"))[-1:]:
        r = json.loads(f.read_text())
        if not r.get("ok"):
            exc.append(f"Evening batch {f.stem}: errors — see {f.name}")
        if r.get("steps", {}).get("codex", "ok") != "ok":
            exc.append(f"Codex challenge: {r['steps']['codex']}")
    if (LED / "exceptions.csv").exists():
        ex = pd.read_csv(LED / "exceptions.csv").tail(5)
        exc += [f"{r.type}: {r.detail}" for r in ex.itertuples()]
    exc_html = "".join(f"<li>{E(x)}</li>" for x in exc) or "<li class=muted>None.</li>"
    prov_note = f"Provisional opens from Yahoo for {len(prov)}/{len(syms)} symbols" if provisional else "No provisional opens"
    page = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Momentum Desk {today}</title>
<style>:root{{--bg:#f6f6f3;--card:#fff;--ink:#141413;--mut:#5f5e5a;--line:#e3e2dc;--pos:#1f7a4d;--neg:#b42318;--abg:#e8eefb;--gbg:#e3f3ea;--rbg:#fde8e6;--ybg:#fbf1d9}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#121211;--card:#1b1b1a;--ink:#f3f2ee;--mut:#b9b8b0;--line:#33332f;--pos:#5fd39a;--neg:#ff8a80;--abg:#1b2640;--gbg:#173326;--rbg:#3b1a17;--ybg:#3a2e12}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}.w{{max-width:1100px;margin:auto;padding:20px 16px 40px}}
h1{{font-size:20px;margin:0}}h2{{font-size:15px;margin:24px 0 8px}}.muted,.sub{{color:var(--mut)}}.sub{{font-size:12px}}.pos{{color:var(--pos)}}.neg{{color:var(--neg)}}
.card,.tw{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}.tw{{overflow-x:auto;padding:0}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap;vertical-align:top}}th{{color:var(--mut);font-weight:600;font-size:12px}}.l{{text-align:left}}td.l.sub{{white-space:normal;min-width:220px}}
tr.bm td{{color:var(--mut)}}.tag{{font-size:11px;font-weight:700;border-radius:99px;padding:1px 7px}}.add{{background:var(--gbg);color:var(--pos)}}.rem{{background:var(--rbg);color:var(--neg)}}
.ch{{margin-top:3px;padding:3px 6px;border-radius:6px;background:var(--ybg);font-size:12px}}.banner{{background:var(--ybg);border-radius:8px;padding:8px 12px;font-size:13px;margin:10px 0}}pre{{white-space:pre-wrap;font-size:12px;margin:0}}
ul{{margin:0;padding-left:18px}}li{{margin:3px 0}}</style></head><body><div class=w>
<h1>Momentum Desk — {E(today.strftime('%a %d %b %Y'))}</h1>
<div class=sub>Signals from the {E(t)} close · forward paper test since 08-Oct-2026 · ₹60,000 per book · 0.6% round-trip costs · selection rules frozen (E2) · {E(prov_note)}</div>
<div class=banner>Paper simulation of pre-registered rules. This is not a recommendation; real-money decisions are yours. Today's fills are <b>provisional</b> until tonight's official NSE file.</div>
<h2>Scoreboard</h2><div class=tw><table><thead><tr><th class=l>Book</th><th>Value</th><th>Day P&amp;L</th><th>Since start</th><th>Stocks</th></tr></thead><tbody>{kpi}</tbody></table></div>
<h2>Since the live start</h2><div class=card>{svg_chart(curves)}</div>
{sections}
<h2>News check (Claude, sourced · no effect on rules)</h2><div class=card><ul>{notes_html}</ul></div>
<h2>Challenger overall (Codex)</h2><div class=card><p>{E(ch.get('overall', 'No challenge available.'))}</p>{('<p class=sub>Overlap: ' + E(ch['overlap']) + '</p>') if ch.get('overlap') else ''}</div>
<h2>Research step (nightly, development data only)</h2><div class=card>{research or '<p class=muted>No research step yet.</p>'}</div>
<h2>Data &amp; run exceptions</h2><div class=card><ul>{exc_html}</ul></div>
<p class=sub>Rules: M11 buys a close above the prior 252-session high on ≥1.5× volume among the 6-month-momentum top 100. M10 buys a ≥5% up-day on ≥2× volume after 3–7 sessions of confirmation. M2 buys the 6-month-momentum top 50 and holds while in the top 125. Max 10 stocks per book, 3 per known sector, 3×ATR catastrophic stop. C0 = the original gainer rules, kept as a control. Backtest context (E2 holdout 2021–26, excess vs B2-net): M11 +14.2%, M10 +17.1%, M2 +15.1%; C0 −21.4%.</p>
</div></body></html>"""
    out = ME / "reports" / f"desk_{today}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    hp = ME / "reports" / f"desk_{today}_holdings.csv"
    pd.DataFrame(hold_rows).to_csv(hp, index=False)
    print(out)
    print(hp)


if __name__ == "__main__":
    main(provisional="--no-provisional" not in sys.argv)
