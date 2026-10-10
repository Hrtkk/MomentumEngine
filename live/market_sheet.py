"""Daily market-stats Google Sheet. Reads data and ledgers only; never changes book state.

Run by evening_batch.py after the books (best-effort), or by hand:  python live/market_sheet.py [--sessions N]
Every run rewrites the tabs from the point-in-time data, so each evening the sheet gains the new session.
Tabs: Daily (one row per session) · Trend (charts) · Leaders · Sectors (latest session) · Books · About.
Descriptive statistics only — no signals, no advice.

Setup (once): config/google_sheet.json names the spreadsheet and a Google service-account key file kept OUTSIDE
the repo; share the spreadsheet with the service account's e-mail as Editor. See config/google_sheet.json.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ME = HERE.parent
LED = HERE / "ledgers"
PIT = ME / "experiments" / "data" / "pit"
CFG = ME / "config" / "google_sheet.json"
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




# ---------------------------------------------------------------- layout
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
GRADIENT_COLS = ("nifty500_day", "nifty500_vs_200dma", "l500_median_day", "b2net_day")
EPOCH = pd.Timestamp("1899-12-30")            # Sheets date serial 0


def cell(v):
    """Python/pandas value -> Sheets RAW value. Dates become serial numbers (formatted as dates), NaN becomes blank."""
    if v is None or v is pd.NaT:
        return ""
    if isinstance(v, (pd.Timestamp, dt.datetime, dt.date)):
        return int((pd.Timestamp(v).normalize() - EPOCH).days)
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and not np.isfinite(v):
        return ""
    return v


class Tab:
    """A tab's values plus the formatting that goes with them (0-based row/column indices)."""

    def __init__(self, name: str, widths: list[int] | None = None, freeze: int = 0):
        self.name, self.widths, self.freeze = name, widths or [], freeze
        self.rows: list[list] = []
        self.titles: list[int] = []
        self.heads: list[tuple[int, int]] = []                      # (row, n_cols)
        self.fmts: list[tuple[int, int, int, str]] = []             # (row0, row1 excl, col, pattern)
        self.gradients: list[tuple[int, int, int]] = []             # (row0, row1 excl, col)
        self.charts: list[dict] = []

    def title(self, text: str, bold: bool = True) -> None:
        if bold:
            self.titles.append(len(self.rows))
        self.rows.append([text])

    def blank(self) -> None:
        self.rows.append([])

    def table(self, df: pd.DataFrame, spec: list[tuple[str, str, str]], gradient: tuple = ()) -> tuple[int, int]:
        r0 = len(self.rows)
        self.heads.append((r0, len(spec)))
        self.rows.append([h for _, h, _ in spec])
        for rec in df.to_dict("records"):
            self.rows.append([cell(rec.get(c)) for c, _, _ in spec])
        r1 = len(self.rows)
        for j, (c, _, f) in enumerate(spec):
            self.fmts.append((r0 + 1, r1, j, f))
            if c in gradient:
                self.gradients.append((r0 + 1, r1, j))
        return r0, r1


def layout(daily: pd.DataFrame, lead: dict, sec: pd.DataFrame, hold: pd.DataFrame) -> list[Tab]:
    tabs = []
    # Daily — newest session on top
    t = Tab("Daily", widths=[95] + [105] * (len(DAILY_COLS) - 1), freeze=1)
    t.table(daily.sort_values("date", ascending=False), [s for s in DAILY_COLS if s[0] in daily.columns], GRADIENT_COLS)
    tabs.append(t)
    # Trend — oldest first, with charts
    t = Tab("Trend", widths=[95, 95, 120, 120, 110, 110], freeze=1)
    tspec = [("date", "Date", "yyyy-mm-dd"), ("nifty500", "Nifty 500", "#,##0"),
             ("l500_above_sma200", "L500 % > 200-DMA", "0%"), ("l500_above_sma50", "L500 % > 50-DMA", "0%"),
             ("l500_new_52w_high", "New 52w highs", "0"), ("l500_new_52w_low", "New 52w lows", "0")]
    _, r1 = t.table(daily.sort_values("date"), tspec)
    for cols, title, row in (([1], "Nifty 500", 0), ([2, 3], "Liquid-500 breadth: % above moving averages", 20),
                             ([4, 5], "Liquid-500: new 52-week highs vs lows", 40)):
        t.charts.append({"title": title, "series": cols, "rows": r1, "anchor": (row, 7)})
    tabs.append(t)
    # Leaders
    day = pd.Timestamp(lead["date"])
    t = Tab("Leaders", widths=[110, 260, 90, 75, 75, 80, 110, 100])
    t.title(f"Liquid-500 leaders — session {day:%d %b %Y} (CA-adjusted returns; rows with a data alert excluded from gainers/losers)")
    lspec = [("symbol", "Symbol", "@"), ("industry", "Industry", "@"), ("close", "Close ₹", "#,##0.00"), ("day", "Day", PCT),
             ("1m", "1 month", PCT), ("6m", "6 months", PCT), ("vol_x_median20", "Vol × 20d median", "0.0"),
             ("turnover_cr", "Turnover ₹ cr", "#,##0.0")]
    for key, title in (("gainers", "Top gainers"), ("losers", "Top losers"), ("turnover", "Highest turnover")):
        t.blank()
        t.title(title)
        t.table(lead[key], lspec)
    tabs.append(t)
    # Sectors
    t = Tab("Sectors", widths=[300, 70, 100, 110, 115, 100])
    t.title(f"Liquid-500 by industry — session {day:%d %b %Y} (medians across members)")
    t.blank()
    t.table(sec, [("industry", "Industry", "@"), ("stocks", "Stocks", "0"), ("median_day", "Median day", PCT),
                  ("median_1m", "Median 1 month", PCT), ("median_6m", "Median 6 months", PCT),
                  ("pct_above_sma200", "% > 200-DMA", "0%")], gradient=("median_day",))
    tabs.append(t)
    # Books
    t = Tab("Books", widths=[60, 110, 260, 60, 95, 90, 90, 75, 90, 75])
    t.title("Paper-book holdings at the latest signal close (simulation of frozen rules — not recommendations)")
    t.blank()
    if len(hold):
        t.table(hold, [("book", "Book", "@"), ("symbol", "Symbol", "@"), ("industry", "Industry", "@"), ("qty", "Qty", "0"),
                       ("entry_date", "Entry date", "@"), ("entry", "Entry ₹", "#,##0.00"), ("last", "Last ₹", "#,##0.00"),
                       ("pnl", "P&L", PCT), ("stop", "Stop ₹", "#,##0.00"), ("weight", "Weight", "0.0%")])
    else:
        t.title("No holdings snapshot found.", bold=False)
    tabs.append(t)
    # About
    t = Tab("About", widths=[1000])
    t.title("Market stats")
    for line in [
        f"Updated {dt.datetime.now(IST):%Y-%m-%d %H:%M} IST by live/market_sheet.py; every tab is rewritten after each evening batch.",
        "Descriptive statistics only. Nothing here is a buy/sell/hold call.",
        "",
        "SOURCES",
        "All EQ columns: NSE CM bhavcopy (experiments/data/pit/bhav_<year>.parquet), EQ series, ETFs/MF units (ISIN INF…) excluded.",
        "  Advances/declines use CLOSE vs PREV_CLOSE. PREV_CLOSE is not adjusted on corporate-action ex-dates, so rows with an",
        "  ex-date in the NSE corporate-actions file are skipped (count shown). Turnover = sum of traded value.",
        "Liquid-500 columns: point-in-time Liquid-500 universe and CA-adjusted prices from experiments/pit_panels.py (SPEC_E2 §1).",
        "  New 52w high = close above the prior 252-session high; new 52w low = close below the prior 252-session low.",
        "Nifty 500: Yahoo ^CRSLDX (experiments/data/nifty500_index.parquet). B2-net: live/ledgers/benchmarks.csv.",
        "Book equity: live/ledgers/<book>/equity.csv and ledgers/equity.csv (C0); blank before each book's start.",
        "Industry: latest NSE Nifty 500 membership file — not point-in-time.",
        "Blank cell = value not available for that session.",
        "Edits made by hand in these tabs are overwritten on the next run; add your own tabs for notes.",
    ]:
        t.title(line, bold=False)
    tabs.append(t)
    return tabs


# ---------------------------------------------------------------- google sheets
HEAD_BG = {"red": 0.12, "green": 0.23, "blue": 0.37}
RED, WHITE, GREEN = {"red": 0.96, "green": 0.65, "blue": 0.63}, {"red": 1, "green": 1, "blue": 1}, {"red": 0.62, "green": 0.85, "blue": 0.71}


def _grid(sid: int, r0: int, r1: int, c0: int, c1: int) -> dict:
    return {"sheetId": sid, "startRowIndex": r0, "endRowIndex": r1, "startColumnIndex": c0, "endColumnIndex": c1}


def _numfmt(pattern: str) -> dict:
    kind = "TEXT" if pattern == "@" else "DATE" if "yy" in pattern else "NUMBER"
    return {"type": kind, "pattern": pattern}


def clear_requests(sid: int, meta: dict) -> list[dict]:
    """Wipe values, formats, our conditional formats and charts so every run starts from a blank tab (same tab id/link)."""
    req = [{"updateCells": {"range": {"sheetId": sid}, "fields": "userEnteredValue,userEnteredFormat"}}]
    req += [{"deleteConditionalFormatRule": {"sheetId": sid, "index": i}} for i in reversed(range(len(meta.get("conditionalFormats", []))))]
    req += [{"deleteEmbeddedObject": {"objectId": c["chartId"]}} for c in meta.get("charts", [])]
    return req


def format_requests(sid: int, tab: Tab) -> list[dict]:
    req = [{"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": tab.freeze}},
                                      "fields": "gridProperties.frozenRowCount"}}]
    for j, w in enumerate(tab.widths):
        req.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": j, "endIndex": j + 1},
                                                  "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    for r in tab.titles:
        req.append({"repeatCell": {"range": _grid(sid, r, r + 1, 0, 1),
                                   "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                                   "fields": "userEnteredFormat.textFormat.bold"}})
    for r, n in tab.heads:
        req.append({"repeatCell": {"range": _grid(sid, r, r + 1, 0, n),
                                   "cell": {"userEnteredFormat": {"backgroundColor": HEAD_BG, "wrapStrategy": "WRAP",
                                                                  "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
                                                                  "textFormat": {"bold": True, "foregroundColor": WHITE}}},
                                   "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.wrapStrategy,"
                                             "userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,"
                                             "userEnteredFormat.textFormat.bold,userEnteredFormat.textFormat.foregroundColor"}})
    for r0, r1, c, pat in tab.fmts:
        if r1 > r0:
            req.append({"repeatCell": {"range": _grid(sid, r0, r1, c, c + 1),
                                       "cell": {"userEnteredFormat": {"numberFormat": _numfmt(pat)}},
                                       "fields": "userEnteredFormat.numberFormat"}})
    for r0, r1, c in tab.gradients:
        if r1 > r0:
            req.append({"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [_grid(sid, r0, r1, c, c + 1)], "gradientRule": {
                "minpoint": {"color": RED, "type": "NUMBER", "value": "-0.02"},
                "midpoint": {"color": WHITE, "type": "NUMBER", "value": "0"},
                "maxpoint": {"color": GREEN, "type": "NUMBER", "value": "0.02"}}}}})
    for ch in tab.charts:
        src = lambda c: {"sourceRange": {"sources": [_grid(sid, 0, ch["rows"], c, c + 1)]}}
        req.append({"addChart": {"chart": {
            "spec": {"title": ch["title"], "basicChart": {
                "chartType": "LINE", "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
                "axis": [{"position": "BOTTOM_AXIS"}, {"position": "LEFT_AXIS"}],
                "domains": [{"domain": src(0)}],
                "series": [{"series": src(c), "targetAxis": "LEFT_AXIS"} for c in ch["series"]]}},
            "position": {"overlayPosition": {"anchorCell": {"sheetId": sid, "rowIndex": ch["anchor"][0], "columnIndex": ch["anchor"][1]},
                                             "widthPixels": 720, "heightPixels": 380}}}}})
    return req


def config() -> tuple[str, str]:
    cfg = json.loads(CFG.read_text())
    key = os.path.expanduser(os.environ.get("MOMENTUM_GSHEET_CREDENTIALS", cfg["credentials"]))
    if not Path(key).exists():
        raise FileNotFoundError(f"service-account key not found at {key} (see config/google_sheet.json)")
    return cfg["spreadsheet_id"], key


def push(tabs: list[Tab]) -> str:
    import gspread
    sheet_id, key = config()
    sh = gspread.service_account(filename=key).open_by_key(sheet_id)
    meta = {s["properties"]["title"]: s for s in sh.fetch_sheet_metadata(
        {"fields": "sheets.properties,sheets.charts.chartId,sheets.conditionalFormats"})["sheets"]}
    clear, fmt, wss = [], [], []
    for tab in tabs:
        rows, cols = max(len(tab.rows) + 20, 100), max(26, max(len(r) for r in tab.rows) + 2)
        if tab.name in meta:
            ws = sh.worksheet(tab.name)
            ws.resize(rows=rows, cols=cols)
        else:
            ws = sh.add_worksheet(tab.name, rows=rows, cols=cols)
        clear += clear_requests(ws.id, meta.get(tab.name, {}))
        fmt += format_requests(ws.id, tab)
        wss.append((ws, tab))
    sh.batch_update({"requests": clear})
    sh.values_batch_update({"valueInputOption": "RAW",                # RAW: symbols and labels are never re-parsed
                            "data": [{"range": f"'{ws.title}'!A1", "values": tab.rows} for ws, tab in wss]})
    sh.batch_update({"requests": fmt})
    first = [ws for ws, tab in wss if tab.name == "Daily"]
    if first and first[0].index != 0:
        sh.batch_update({"requests": [{"updateSheetProperties": {"properties": {"sheetId": first[0].id, "index": 0}, "fields": "index"}}]})
    blank = [s for s in sh.worksheets() if s.title == "Sheet1"]
    for s in blank:                                                    # the empty default tab of a new spreadsheet
        if not any(any(v for v in r) for r in s.get_all_values()):
            sh.del_worksheet(s)
    return sh.url


def build(P=None, n_sessions: int = 260, upload: bool = True) -> dict:
    P = P if P is not None else load_panels()
    dates = P.C.index[-n_sessions:]
    raw = load_raw(sorted({d.year for d in dates}))
    raw = raw[raw["date"].isin(dates)]
    daily = daily_table(P, whole_market(raw, ca_exdates()), n_sessions)
    tabs = layout(daily, leaders(P, raw), sectors(P), holdings())
    out = {"sessions": len(daily), "last_session": str(P.C.index[-1].date())}
    if upload:
        out["url"] = push(tabs)
    else:
        out["tabs"] = tabs
    return out


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--sessions") + 1]) if "--sessions" in sys.argv else 260
    print(json.dumps(build(n_sessions=n), indent=1))
