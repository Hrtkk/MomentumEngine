"""E2 report: curves (log, dev/holdout shaded), dev + holdout tables, verdicts. Reads results_e2 only."""
import html, json, pickle
from pathlib import Path
import numpy as np, pandas as pd

R = Path(__file__).resolve().parent / "results_e2"
B = pickle.load(open(R / "books.pkl", "rb"))
sel = json.loads((R / "selection.json").read_text())
dev = pd.read_csv(R / "dev_metrics.csv"); dev = dev[dev.cost == 0.006].set_index("id")
hold = pd.read_csv(R / "holdout_metrics.csv").set_index("id")
curves = {k: v["eq"]["equity"] / 60000 for (k, c), v in B["res"].items() if c == 0.006}
idx = next(iter(curves.values())).index
curves["EN"] = pd.concat([curves[k] for k in sel["ensemble"]], axis=1).mean(axis=1)
curves["B2-net"] = (1 + B["b2n"]).cumprod().reindex(idx).ffill()
n5 = B["n5"].reindex(idx).ffill(); curves["Nifty 500"] = n5 / n5.iloc[0]
show = ["M2", "M5", "M8", "M10", "M11", "EN", "M1", "C0", "B2-net", "Nifty 500"]
pal = {"M2": "#2e5aac", "M5": "#7c3aed", "M8": "#0f766e", "M10": "#c2410c", "M11": "#15803d", "EN": "#111827",
       "M1": "#a3a3a3", "C0": "#be123c", "B2-net": "#6b7280", "Nifty 500": "#9ca3af"}
c = pd.DataFrame({k: curves[k] for k in show}).ffill()
W, H, L, Rr, T = 940, 340, 56, 150, 14
lo, hi = np.log(c.min().min()) - .05, np.log(c.max().max()) + .05
xs = np.linspace(L, W - Rr, len(c)); y = lambda v: T + (hi - np.log(v)) / (hi - lo) * H
hx = xs[c.index.get_indexer([pd.Timestamp("2021-01-01")], method="bfill")[0]]
svg = [f'<rect x="{hx:.0f}" y="{T}" width="{W - Rr - hx:.0f}" height="{H}" fill="var(--hold)"/>',
       f'<text x="{hx + 6:.0f}" y="{T + 14}" font-size="11" fill="var(--mut)">HOLDOUT (tested once)</text>',
       f'<text x="{L + 6}" y="{T + 14}" font-size="11" fill="var(--mut)">DEVELOPMENT (selection)</text>']
for v in (0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 32, 64):
    if lo <= np.log(v) <= hi:
        svg.append(f'<line x1="{L}" x2="{W - Rr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="var(--line)"/><text x="{L - 6}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end" fill="var(--mut)">{v}×</text>')
for k in show:
    pts = " ".join(f"{xs[i]:.1f},{y(v):.1f}" for i, v in enumerate(c[k].values) if i % 4 == 0 or i == len(c) - 1)
    dash = ' stroke-dasharray="5 4"' if k in ("B2-net", "Nifty 500", "M1") else ""
    svg.append(f'<polyline points="{pts}" fill="none" stroke="{pal[k]}" stroke-width="{2.4 if k == "EN" else 1.6}"{dash}/>')
lab = sorted(show, key=lambda k: -c[k].iloc[-1]); last = -99
for k in lab:
    yy = max(y(c[k].iloc[-1]) + 4, last + 12); last = yy
    svg.append(f'<text x="{W - Rr + 6}" y="{yy:.1f}" font-size="11" fill="{pal[k]}">{k} {c[k].iloc[-1]:.1f}×</text>')
for yr in range(2013, 2027):
    j = c.index.get_indexer([pd.Timestamp(f"{yr}-01-01")], method="bfill")[0]
    if j >= 0: svg.append(f'<text x="{xs[j]:.0f}" y="{T + H + 16}" font-size="10" text-anchor="middle" fill="var(--mut)">{yr}</text>')
f = lambda v, p=1: "—" if pd.isna(v) else f"{v * 100:+.{p}f}%"
g = lambda v: "—" if pd.isna(v) else f"{v * 100:.0f}%"
names = {k: dev.loc[k, "name"] for k in dev.index}; names["EN"] = "EN ensemble (M10+M2+M8+M11)"
rows = ""
for k in ["M10", "M2", "M8", "M11", "M5", "EN", "M3", "M1", "M9", "M7", "M6", "M4", "C0", "C1"]:
    d = dev.loc[k] if k in dev.index else None
    h = hold.loc[k]
    vd = "selected" if k in sel["selected"] or k == "EN" else (sel["verdict_dev"].get(k, "") or "")
    vh = h["verdict"]
    cls = "ok" if vh.startswith("RELIABLE") else ("warn" if k in sel["selected"] or k == "EN" else "")
    rows += (f'<tr class="{cls}"><td class=l><b>{k}</b> {html.escape(names[k].split(" ", 1)[1] if " " in names[k] else names[k])}</td>'
             + (f'<td>{f(d["dev_xs"])}</td><td>{g(d["dev_MDD"])}</td><td>{d["dev_Sharpe"]:.2f}</td>' if d is not None else "<td>—</td><td>—</td><td>—</td>")
             + f'<td class=l>{html.escape(vd)}</td><td>{f(h["h_CAGR"])}</td><td><b>{f(h["h_xs"])}</b></td><td>{g(h["h_MDD"])}</td><td>{h["h_Sharpe"]:.2f}</td>'
             f'<td>{f(h["H1"])} / {f(h["H2"])} / {f(h["H3"])}</td><td>{h["xs_ann_CI90"]}</td><td class=l>{html.escape(vh)}</td></tr>')
b2d, b2h = B["b2n"], B["b2n"]
page = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Experiment E2</title>
<style>:root{{--bg:#f6f6f3;--card:#fff;--ink:#141413;--mut:#5f5e5a;--line:#e3e2dc;--hold:#eef3fb;--ok:#e3f3ea;--warn:#fbf1d9}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121211;--card:#1b1b1a;--ink:#f3f2ee;--mut:#b9b8b0;--line:#33332f;--hold:#18202e;--ok:#173326;--warn:#3a2e12}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,sans-serif}}.w{{max-width:1200px;margin:auto;padding:20px 16px}}
.card,.tw{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}.tw{{overflow-x:auto;padding:0}}table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}th{{color:var(--mut);font-weight:600}}.l{{text-align:left}}tr.ok td{{background:var(--ok)}}tr.warn td{{background:var(--warn)}}
h2{{font-size:15px;margin:24px 0 8px}}.mut{{color:var(--mut)}}</style></head><body><div class=w>
<h1 style="font-size:20px;margin:0">Experiment E2 — strategy ladder on a point-in-time universe</h1>
<div class=mut>NSE bhavcopy 2011-06 → 2026-10-07 · Liquid-500 rebuilt monthly (incl. later-delisted stocks) · ₹60,000 · next-open fills · 0.6% costs · 14 trials · selection on 2013–2020 logged before the 2021–2026 holdout was evaluated once</div>
<h2>Growth of ₹1 (log scale)</h2><div class=card><svg viewBox="0 0 {W} {T + H + 24}" style="width:100%;height:auto">{''.join(svg)}</svg></div>
<h2>Results — excess = CAGR minus B2-net (equal-weight Liquid-500, same execution & costs)</h2>
<div class=tw><table><thead><tr><th class=l>Strategy</th><th>Dev xs</th><th>Dev MDD</th><th>Dev Sharpe</th><th class=l>Dev verdict</th><th>Holdout CAGR</th><th>Holdout xs</th><th>Holdout MDD</th><th>Sharpe</th><th>xs 21-22 / 23-24 / 25-26</th><th>xs 90% CI</th><th class=l>Holdout verdict</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class=mut>B2-net: dev CAGR 12.1%, MDD 57.9% · holdout CAGR 21.2%, MDD 24.5%. Reliability rule (fixed in advance): holdout excess &gt; 0, ≥2 of 3 holdout blocks positive, MDD ≤ B2-net + 10 pp. Green = passes all; amber = selected, beats the benchmark, fails the drawdown rule.</p>
</div></body></html>"""
(R / "E2_report.html").write_text(page); print(R / "E2_report.html")
