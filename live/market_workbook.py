"""Daily market-stats workbook: reports/market_stats.xlsx. Reads data and ledgers only; never changes book state.

Run by evening_batch.py after the books (best-effort), or by hand:  python live/market_workbook.py [--sessions N]
The workbook is rebuilt from the point-in-time data on every run, so each evening it gains the new session.
Sheets: Daily (one row per session) · Leaders (latest session) · Sectors (latest session) · Books · About.
Descriptive statistics only — no signals, no advice.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ME = HERE.parent
LED = HERE / "ledgers"
PIT = ME / "experiments" / "data" / "pit"
OUT = ME / "reports" / "market_stats.xlsx"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
BOOKS = ["M11", "M10", "M2"]
CR = 1e7                                       # ₹ crore


# ---------------------------------------------------------------- data
def load_panels():
    sys.path.insert(0, str(ME / "experiments"))
    import pit_panels
    return pit_panels.build(cache=True)       # the pickle live_books.run() rebuilt this evening


def load_raw(years: list[int]) -> pd.DataFrame:
    """Unadjusted whole-market bhavcopy rows: EQ series only, ETFs / MF units (ISIN INF…) dropped."""
    fs = [PIT / f"bhav_{y}.parquet" for y in years if (PIT / f"bhav_{y}.parquet").exists()]
    if not fs:
        return pd.DataFrame(columns=["date", "symbol", "close", "prev_close", "value", "trades"])
    b = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    b = b[(b["series"].astype(str).str.strip() == "EQ") & ~b["isin"].astype(str).str.startswith("INF")].copy()
    b["date"] = pd.to_datetime(b["date"])
    for c in ("close", "prev_close", "value", "trades"):
        b[c] = pd.to_numeric(b[c], errors="coerce")
    return b


def ca_exdates() -> set[tuple[str, pd.Timestamp]]:
    """(symbol, ex-date) pairs: on these days PREV_CLOSE is not adjusted, so the raw day change is not a price move."""
    f = PIT / "ca.parquet"
    if not f.exists():
        return set()
    ca = pd.read_parquet(f, columns=["symbol", "exDate"])
    ex = pd.to_datetime(ca["exDate"], format="%d-%b-%Y", errors="coerce")
    return {(s, d.normalize()) for s, d in zip(ca["symbol"], ex) if pd.notna(d)}


def whole_market(raw: pd.DataFrame, exd: set) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    r = raw.copy()
    r["skip"] = [(s, d) in exd for s, d in zip(r["symbol"], r["date"])]
    ch = (r["close"] / r["prev_close"] - 1).where(~r["skip"] & (r["prev_close"] > 0))
    r["adv"], r["dec"], r["unch"] = ch > 0, ch < 0, ch == 0
    g = r.groupby("date")
    out = pd.DataFrame({"eq_traded": g.size(), "eq_adv": g["adv"].sum(), "eq_dec": g["dec"].sum(), "eq_unch": g["unch"].sum(),
                        "eq_turnover_cr": g["value"].sum() / CR, "eq_trades_lakh": g["trades"].sum() / 1e5,
                        "eq_exdate_skipped": g["skip"].sum()})
    out["eq_ad_ratio"] = out["eq_adv"] / out["eq_dec"].replace(0, np.nan)
    return out


def liquid500(P) -> pd.DataFrame:
    """Liquid-500 (point-in-time, CA-adjusted) breadth. Membership = P.universe on each date."""
    u = P.universe.fillna(False).astype(bool) & P.C.notna()
    r1 = P.ret1.where(u)
    lo252 = P.L.shift(1).rolling(252).min()
    n = u.sum(axis=1).replace(0, np.nan)
    pct = lambda m: (m & u).sum(axis=1) / n
    return pd.DataFrame({
        "l500_members": u.sum(axis=1),
        "l500_adv": (r1 > 0).sum(axis=1), "l500_dec": (r1 < 0).sum(axis=1),
        "l500_median_day": r1.median(axis=1), "l500_mean_day": r1.mean(axis=1),
        "l500_above_sma50": pct(P.C > P.sma50), "l500_above_sma200": pct(P.C > P.sma200),
        "l500_new_52w_high": ((P.C > P.hi252) & u).sum(axis=1), "l500_new_52w_low": ((P.C < lo252) & u).sum(axis=1),
        "l500_up_5pct": (r1 >= 0.05).sum(axis=1), "l500_down_5pct": (r1 <= -0.05).sum(axis=1),
    })


def book_equity() -> pd.DataFrame:
    cols = {}
    for k in BOOKS:
        f = LED / k / "equity.csv"
        if f.exists():
            cols[f"{k}_equity"] = pd.read_csv(f, parse_dates=["date"]).set_index("date")["equity"]
    f = ME / "ledgers" / "equity.csv"
    if f.exists():
        c0 = pd.read_csv(f)
        c0 = c0[c0["book"] == "c0.006"]
        cols["C0_equity"] = pd.Series(c0["equity"].values, index=pd.to_datetime(c0["date"]))
    return pd.DataFrame(cols)


def daily_table(P, wm: pd.DataFrame, n_sessions: int) -> pd.DataFrame:
    dates = P.C.index[-n_sessions:]
    d = pd.DataFrame(index=dates)
    d["nifty500"] = P.n5.reindex(dates)
    d["nifty500_day"] = P.n5.pct_change().reindex(dates)
    d["nifty500_vs_200dma"] = (P.n5 / P.n5.rolling(200).mean() - 1).reindex(dates)
    d = d.join(wm.reindex(dates)).join(liquid500(P).reindex(dates))
    bm = LED / "benchmarks.csv"
    if bm.exists():
        b = pd.read_csv(bm, parse_dates=["date"]).set_index("date")["b2net_cum"]
        d["b2net_day"] = b.pct_change().reindex(dates)
    d = d.join(book_equity().reindex(dates))
    d.index.name = "date"
    return d.reset_index()


def leaders(P, raw: pd.DataFrame, n: int = 15) -> dict[str, pd.DataFrame]:
    t = P.C.index[-1]
    u = P.universe.loc[t].fillna(False).astype(bool) & P.C.loc[t].notna()
    syms = u[u].index
    df = pd.DataFrame({"symbol": syms, "industry": [str(P.industry.get(s, "Unknown")) for s in syms],
                       "close": P.nominal.loc[t, syms].values, "day": P.ret1.loc[t, syms].values,
                       "1m": P.R21.loc[t, syms].values, "6m": P.R6.loc[t, syms].values,
                       "vol_x_median20": (P.V.loc[t, syms] / P.medV20.loc[t, syms]).values,
                       "data_alert": P.bad.loc[t, syms].values})
    val = raw[raw["date"] == t].set_index("symbol")["value"] / CR if len(raw) else pd.Series(dtype=float)
    df["turnover_cr"] = df["symbol"].map(val)
    clean = df[~df["data_alert"]]
    return {"gainers": clean.nlargest(n, "day"), "losers": clean.nsmallest(n, "day"),
            "turnover": df.nlargest(n, "turnover_cr"), "date": t}


def sectors(P) -> pd.DataFrame:
    t = P.C.index[-1]
    u = P.universe.loc[t].fillna(False).astype(bool) & P.C.loc[t].notna()
    s = u[u].index
    df = pd.DataFrame({"industry": [str(P.industry.get(x, "Unknown")) for x in s], "day": P.ret1.loc[t, s].values,
                       "1m": P.R21.loc[t, s].values, "6m": P.R6.loc[t, s].values,
                       "above200": (P.C.loc[t, s] > P.sma200.loc[t, s]).values})
    g = df.groupby("industry")
    out = pd.DataFrame({"stocks": g.size(), "median_day": g["day"].median(), "median_1m": g["1m"].median(),
                        "median_6m": g["6m"].median(), "pct_above_sma200": g["above200"].mean()})
    return out.sort_values("median_day", ascending=False).reset_index()


def holdings() -> pd.DataFrame:
    last = json.loads((LED / "last_run.json").read_text()) if (LED / "last_run.json").exists() else {}
    t = last.get("last_session")
    rows = []
    for k in BOOKS:
        f = LED / k / f"snapshot_{t}.json"
        if not t or not f.exists():
            continue
        s = json.loads(f.read_text())
        for sym, p in s["positions"].items():
            rows.append({"book": k, "symbol": sym, "industry": p["industry"], "qty": p["qty"], "entry_date": p["entry_date"],
                         "entry": p["entry"], "last": p["last"], "pnl": p["last"] / p["entry"] - 1, "stop": p["stop"],
                         "weight": p["qty"] * p["last"] / s["equity"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- excel
DAILY_COLS = [  # (column, header, number format)
    ("date", "Date", "yyyy-mm-dd"),
    ("nifty500", "Nifty 500", "#,##0.00"), ("nifty500_day", "Nifty 500 day", "+0.00%;-0.00%;0.00%"),
    ("nifty500_vs_200dma", "Nifty 500 vs 200-DMA", "+0.0%;-0.0%;0.0%"),
    ("eq_traded", "All EQ: traded", "#,##0"), ("eq_adv", "All EQ: advances", "#,##0"), ("eq_dec", "All EQ: declines", "#,##0"),
    ("eq_unch", "All EQ: unchanged", "#,##0"), ("eq_ad_ratio", "All EQ: A/D ratio", "0.00"),
    ("eq_turnover_cr", "All EQ: turnover ₹ cr", "#,##0"), ("eq_trades_lakh", "All EQ: trades (lakh)", "#,##0.0"),
    ("eq_exdate_skipped", "All EQ: ex-date rows skipped", "0"),
    ("l500_members", "Liquid-500: members", "0"), ("l500_adv", "L500: advances", "0"), ("l500_dec", "L500: declines", "0"),
    ("l500_median_day", "L500: median day", "+0.00%;-0.00%;0.00%"), ("l500_mean_day", "L500: mean day", "+0.00%;-0.00%;0.00%"),
    ("l500_above_sma50", "L500: % > 50-DMA", "0%"), ("l500_above_sma200", "L500: % > 200-DMA", "0%"),
    ("l500_new_52w_high", "L500: new 52w highs", "0"), ("l500_new_52w_low", "L500: new 52w lows", "0"),
    ("l500_up_5pct", "L500: up ≥ 5%", "0"), ("l500_down_5pct", "L500: down ≥ 5%", "0"),
    ("b2net_day", "B2-net day", "+0.00%;-0.00%;0.00%"),
    ("M11_equity", "M11 equity ₹", "#,##0"), ("M10_equity", "M10 equity ₹", "#,##0"), ("M2_equity", "M2 equity ₹", "#,##0"),
    ("C0_equity", "C0 equity ₹", "#,##0"),
]
PCT = "+0.0%;-0.0%;0.0%"


def write_xlsx(daily: pd.DataFrame, lead: dict, sec: pd.DataFrame, hold: pd.DataFrame, path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference
    from openpyxl.formatting.rule import ColorScaleRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    HEAD = PatternFill("solid", fgColor="1F3A5F")
    HFONT = Font(bold=True, color="FFFFFF")
    TITLE = Font(bold=True, size=13)
    wb = Workbook()

    def table(ws, df: pd.DataFrame, spec: list[tuple[str, str, str]], r0: int = 1, c0: int = 1, widths=True):
        for j, (_, h, _) in enumerate(spec):
            c = ws.cell(r0, c0 + j, h)
            c.fill, c.font = HEAD, HFONT
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        for i, rec in enumerate(df.to_dict("records"), start=1):
            for j, (col, _, fmt) in enumerate(spec):
                v = rec.get(col)
                if isinstance(v, (float, np.floating)) and not np.isfinite(v):
                    v = None
                elif isinstance(v, pd.Timestamp):
                    v = v.to_pydatetime()
                elif isinstance(v, np.generic):
                    v = v.item()
                c = ws.cell(r0 + i, c0 + j, v)
                c.number_format = fmt
        if widths:
            for j, (_, h, _) in enumerate(spec):
                ws.column_dimensions[get_column_letter(c0 + j)].width = max(10, min(18, len(h) * 0.7 + 4))
        return r0 + len(df)

    # Daily — newest session on top
    ws = wb.active
    ws.title = "Daily"
    d = daily.sort_values("date", ascending=False)
    spec = [s for s in DAILY_COLS if s[0] in d.columns]
    last = table(ws, d, spec)
    ws.row_dimensions[1].height = 45
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(spec))}{last}"
    for col, *_ in spec:
        if col in ("nifty500_day", "l500_median_day", "b2net_day", "nifty500_vs_200dma"):
            L = get_column_letter([s[0] for s in spec].index(col) + 1)
            ws.conditional_formatting.add(f"{L}2:{L}{last}", ColorScaleRule(
                start_type="num", start_value=-0.02, start_color="F4A6A0", mid_type="num", mid_value=0,
                mid_color="FFFFFF", end_type="num", end_value=0.02, end_color="9FD8B5"))

    # Trend sheet: oldest → newest with charts
    tr = wb.create_sheet("Trend")
    a = daily.sort_values("date")
    tspec = [("date", "Date", "yyyy-mm-dd"), ("nifty500", "Nifty 500", "#,##0"),
             ("l500_above_sma200", "L500 % > 200-DMA", "0%"), ("l500_above_sma50", "L500 % > 50-DMA", "0%"),
             ("l500_new_52w_high", "New 52w highs", "0"), ("l500_new_52w_low", "New 52w lows", "0")]
    tspec = [s for s in tspec if s[0] in a.columns]
    n = table(tr, a, tspec)
    cats = Reference(tr, min_col=1, min_row=2, max_row=n)
    for k, (cols, title, anchor) in enumerate([([2], "Nifty 500", "H2"), ([3, 4], "Liquid-500 breadth: % above moving averages", "H20"),
                                               ([5, 6], "Liquid-500: new 52-week highs vs lows", "H38")]):
        if max(cols) > len(tspec):
            continue
        ch = LineChart()
        ch.title, ch.height, ch.width = title, 8, 22
        ch.x_axis.number_format, ch.x_axis.majorTimeUnit = "dd-mmm-yy", "months"
        for c in cols:
            ch.add_data(Reference(tr, min_col=c, min_row=1, max_row=n), titles_from_data=True)
        ch.set_categories(cats)
        for s in ch.series:
            s.smooth, s.marker.symbol = False, "none"
        tr.add_chart(ch, anchor)

    # Leaders
    lw = wb.create_sheet("Leaders")
    t = lead["date"]
    lw.cell(1, 1, f"Liquid-500 leaders — session {pd.Timestamp(t):%d %b %Y} (CA-adjusted returns; rows with a data alert excluded from gainers/losers)").font = TITLE
    lspec = [("symbol", "Symbol", "@"), ("industry", "Industry", "@"), ("close", "Close ₹", "#,##0.00"), ("day", "Day", PCT),
             ("1m", "1 month", PCT), ("6m", "6 months", PCT), ("vol_x_median20", "Vol × 20d median", "0.0"),
             ("turnover_cr", "Turnover ₹ cr", "#,##0.0")]
    r = 3
    for key, title in (("gainers", "Top gainers"), ("losers", "Top losers"), ("turnover", "Highest turnover")):
        lw.cell(r, 1, title).font = Font(bold=True)
        r = table(lw, lead[key], lspec, r0=r + 1, widths=False) + 2
    for j, w in enumerate([14, 34, 11, 9, 9, 10, 11, 12], start=1):
        lw.column_dimensions[get_column_letter(j)].width = w

    # Sectors
    sw = wb.create_sheet("Sectors")
    sw.cell(1, 1, f"Liquid-500 by industry — session {pd.Timestamp(t):%d %b %Y} (medians across members)").font = TITLE
    sspec = [("industry", "Industry", "@"), ("stocks", "Stocks", "0"), ("median_day", "Median day", PCT),
             ("median_1m", "Median 1 month", PCT), ("median_6m", "Median 6 months", PCT), ("pct_above_sma200", "% > 200-DMA", "0%")]
    n = table(sw, sec, sspec, r0=3, widths=False)
    sw.column_dimensions["A"].width = 40
    for L in "BCDEF":
        sw.column_dimensions[L].width = 13
    if n > 3:
        sw.conditional_formatting.add(f"C4:C{n}", ColorScaleRule(start_type="num", start_value=-0.02, start_color="F4A6A0",
                                                                  mid_type="num", mid_value=0, mid_color="FFFFFF",
                                                                  end_type="num", end_value=0.02, end_color="9FD8B5"))

    # Books
    bw = wb.create_sheet("Books")
    bw.cell(1, 1, "Paper-book holdings at the latest signal close (simulation of frozen rules — not recommendations)").font = TITLE
    hspec = [("book", "Book", "@"), ("symbol", "Symbol", "@"), ("industry", "Industry", "@"), ("qty", "Qty", "0"),
             ("entry_date", "Entry date", "@"), ("entry", "Entry ₹", "#,##0.00"), ("last", "Last ₹", "#,##0.00"),
             ("pnl", "P&L", PCT), ("stop", "Stop ₹", "#,##0.00"), ("weight", "Weight", "0.0%")]
    if len(hold):
        table(bw, hold, hspec, r0=3, widths=False)
    else:
        bw.cell(3, 1, "No holdings snapshot found.")
    for j, w in enumerate([7, 14, 34, 7, 12, 11, 11, 9, 11, 9], start=1):
        bw.column_dimensions[get_column_letter(j)].width = w

    # About
    ab = wb.create_sheet("About")
    lines = [
        ("Market stats workbook", TITLE),
        (f"Built {dt.datetime.now(IST):%Y-%m-%d %H:%M} IST by live/market_workbook.py; rebuilt every evening after the batch.", None),
        ("Descriptive statistics only. Nothing here is a buy/sell/hold call.", None),
        ("", None),
        ("Sources", Font(bold=True)),
        ("All EQ columns: NSE CM bhavcopy (experiments/data/pit/bhav_<year>.parquet), EQ series, ETFs/MF units (ISIN INF…) excluded.", None),
        ("  Advances/declines use CLOSE vs PREV_CLOSE. PREV_CLOSE is not adjusted on corporate-action ex-dates, so rows with an", None),
        ("  ex-date in the NSE corporate-actions file are skipped (count shown). Turnover = sum of traded value.", None),
        ("Liquid-500 columns: point-in-time Liquid-500 universe and CA-adjusted prices from experiments/pit_panels.py (SPEC_E2 §1).", None),
        ("  New 52w high = close above the prior 252-session high; new 52w low = close below the prior 252-session low.", None),
        ("Nifty 500: Yahoo ^CRSLDX (experiments/data/nifty500_index.parquet). B2-net: live/ledgers/benchmarks.csv.", None),
        ("Book equity: live/ledgers/<book>/equity.csv and ledgers/equity.csv (C0); blank before each book's start.", None),
        ("Industry: latest NSE Nifty 500 membership file — not point-in-time.", None),
        ("Blank cell = value not available for that session.", None),
    ]
    for i, (txt, f) in enumerate(lines, start=1):
        c = ab.cell(i, 1, txt)
        if f:
            c.font = f
    ab.column_dimensions["A"].width = 130

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.xlsx")
    wb.save(tmp)
    tmp.replace(path)                       # atomic: a half-written workbook never replaces a good one


def build(P=None, n_sessions: int = 260, path: Path = OUT) -> dict:
    P = P if P is not None else load_panels()
    dates = P.C.index[-n_sessions:]
    raw = load_raw(sorted({d.year for d in dates}))
    raw = raw[raw["date"].isin(dates)]
    daily = daily_table(P, whole_market(raw, ca_exdates()), n_sessions)
    write_xlsx(daily, leaders(P, raw), sectors(P), holdings(), path)
    return {"path": str(path.relative_to(ME)) if path.is_relative_to(ME) else str(path),
            "sessions": len(daily), "last_session": str(P.C.index[-1].date())}


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--sessions") + 1]) if "--sessions" in sys.argv else 260
    print(json.dumps(build(n_sessions=n), indent=1))
