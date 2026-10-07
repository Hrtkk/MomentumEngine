"""Momentum Research Engine v0.1 — end-of-day batch for one signal date t.

Order of work for signal date t (STRATEGY.md §§3–8, Appendix A):
  1. Fill pending orders (made at t-1) at the open of t; apply stops on t; mark to close t.
  2. Discovery, eligibility, factors, MQS, EQS for t.
  3. Watchlist Keep/Add/Replace/Remove; frozen orders for the open of t+1.
  4. Research cohorts for t.
State lives in ledgers/; every run appends, nothing is rewritten.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA, LED = ROOT / "data", ROOT / "ledgers"
P = yaml.safe_load((ROOT / "config" / "parameters.yaml").read_text())
SECTOR_MAP = pd.read_csv(ROOT / "config" / "sector_map.csv").set_index("industry")["sector_index"].to_dict()
WEIGHTS = {"rs": 25, "trend": 15, "volume": 15, "breakout": 15, "persist": 10, "sector": 10, "vol": 10}
FACTOR_LABEL = {"rs": "relative strength", "trend": "trend structure", "volume": "volume/delivery surge",
                "breakout": "near breakout/52W high", "persist": "repeat gainer", "sector": "strong sector",
                "vol": "smooth (low ATR)"}


# ---------------------------------------------------------------- loading
def load_bhav() -> pd.DataFrame:
    frames = []
    for f in sorted((DATA / "raw" / "bhav").glob("*.csv")):
        df = pd.read_csv(f, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
        df = df[df["SERIES"].str.strip() == "EQ"].copy()
        df["date"] = pd.Timestamp(f.stem)
        frames.append(df)
    b = pd.concat(frames, ignore_index=True)
    b["symbol"] = b["SYMBOL"].str.strip()
    num = ["PREV_CLOSE", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "TTL_TRD_QNTY",
           "TURNOVER_LACS", "NO_OF_TRADES", "DELIV_PER"]
    for c in num:
        b[c] = pd.to_numeric(b[c].astype(str).str.strip().replace({"-": None}), errors="coerce")
    b = b.rename(columns={"PREV_CLOSE": "pc", "OPEN_PRICE": "o", "HIGH_PRICE": "h", "LOW_PRICE": "l",
                          "CLOSE_PRICE": "c", "TTL_TRD_QNTY": "vol", "TURNOVER_LACS": "turn_lacs",
                          "NO_OF_TRADES": "trades", "DELIV_PER": "deliv"})
    return b[["date", "symbol", "pc", "o", "h", "l", "c", "vol", "turn_lacs", "trades", "deliv"]]


def load_index() -> pd.DataFrame:
    frames = []
    for f in sorted((DATA / "raw" / "index").glob("*.csv")):
        df = pd.read_csv(f)
        df["date"] = pd.Timestamp(f.stem)
        frames.append(df[["date", "Index Name", "Closing Index Value"]])
    i = pd.concat(frames, ignore_index=True)
    i.columns = ["date", "index", "close"]
    i["close"] = pd.to_numeric(i["close"], errors="coerce")
    return i.pivot_table(index="date", columns="index", values="close").sort_index()


def load_history() -> pd.DataFrame:
    f = sorted((DATA / "history").glob("yahoo_*.parquet"))[-1]
    h = pd.read_parquet(f)
    return h.rename(columns={"open": "yo", "high": "yh", "low": "yl", "close": "yc", "volume": "yv"})


def load_membership(t: pd.Timestamp) -> pd.DataFrame:
    files = sorted((DATA / "membership").glob("*_nifty500.csv"))
    on_or_before = [f for f in files if f.name[:10] <= t.date().isoformat()]
    f = on_or_before[-1] if on_or_before else files[0]  # backfill uses earliest snapshot (survivorship caveat)
    m = pd.read_csv(f)
    return m.rename(columns={"Symbol": "symbol", "Industry": "industry", "Company Name": "name"})[
        ["symbol", "name", "industry"]]


# ---------------------------------------------------------------- indicators
def wilder(x: pd.Series, n: int) -> pd.Series:
    out = pd.Series(np.nan, index=x.index)
    vals = x.to_numpy()
    if len(vals) < n:
        return out
    prev = np.nanmean(vals[:n])
    out.iloc[n - 1] = prev
    for i in range(n, len(vals)):
        prev = (prev * (n - 1) + vals[i]) / n
        out.iloc[i] = prev
    return out


def rsi14(c: pd.Series) -> float:
    d = c.diff().dropna()
    if len(d) < 15:
        return np.nan
    g, l = wilder(d.clip(lower=0), 14).iloc[-1], wilder((-d).clip(lower=0), 14).iloc[-1]
    if l == 0 and g == 0:
        return 50.0
    if l == 0:
        return 100.0
    if g == 0:
        return 0.0
    return 100 - 100 / (1 + g / l)


def pct_rank(s: pd.Series) -> pd.Series:
    """100*(avg_rank-1)/(n-1), ascending: higher raw = higher percentile."""
    n = s.notna().sum()
    if n == 0:
        return s * np.nan
    if n == 1:
        return s.where(s.isna(), 50.0)
    return 100 * (s.rank(method="average") - 1) / (n - 1)


def interp_pct(x: float, ref: pd.Series) -> float:
    ref = ref.dropna()
    if ref.empty or pd.isna(x):
        return np.nan
    pr = pct_rank(ref)
    pts = pd.DataFrame({"v": ref, "p": pr}).groupby("v")["p"].mean().sort_index()
    return float(np.interp(x, pts.index.to_numpy(), pts.to_numpy(), left=0.0, right=100.0))


def lin(x: float, good: float, bad: float) -> float:
    if pd.isna(x):
        return np.nan
    return float(np.clip(100 * (bad - x) / (bad - good), 0, 100))


# ---------------------------------------------------------------- scoring
def discovery(b: pd.DataFrame, memb: set[str], t: pd.Timestamp) -> pd.DataFrame:
    d = b[(b["date"] == t) & b["symbol"].isin(memb)].copy()
    d["ret"] = d["c"] / d["pc"] - 1
    d = d[d["ret"] > 0].sort_values(["ret", "symbol"], ascending=[False, True]).head(P["discovery_top_n"])
    d["disc_rank"] = range(1, len(d) + 1)
    return d


def factors_for(sym: str, t: pd.Timestamp, b: pd.DataFrame, hist_by: dict, idx: pd.DataFrame,
                industry: str, persist: int) -> dict:
    r: dict = {"symbol": sym, "persist_n": persist, "industry": industry, "reasons": []}
    bt = b[(b["symbol"] == sym) & (b["date"] <= t)].sort_values("date")
    today = bt[bt["date"] == t]
    if today.empty:
        r["reasons"].append("NO_TRADE_T")
        return r
    row = today.iloc[0]
    r.update(close=row["c"], day_ret=row["c"] / row["pc"] - 1, h=row["h"], l=row["l"])
    prev20 = bt[bt["date"] < t].tail(20)
    r["med_turn_cr"] = prev20["turn_lacs"].median() / 100 if len(prev20) == 20 else np.nan
    h = hist_by.get(sym)
    if h is None:
        r["reasons"].append("NO_HISTORY")
        return r
    h = h[h["date"] <= t]
    if h.empty or h["date"].iloc[-1] != t:
        r["reasons"].append("NO_HISTORY_T")
        return r
    r["n_prev"] = int((h["date"] < t).sum())
    c, hi, lo = h["yc"].reset_index(drop=True), h["yh"].reset_index(drop=True), h["yl"].reset_index(drop=True)
    C = c.iloc[-1]
    r["yahoo_vs_bhav"] = C / row["c"] - 1
    tr = pd.concat([hi - lo, (hi - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    atr = wilder(tr.iloc[1:].reset_index(drop=True), 20).iloc[-1]
    sma = {n: c.tail(n).mean() if len(c) >= n else np.nan for n in (20, 50, 200)}
    n5 = idx["Nifty 500"].loc[:t].dropna()

    def ret(series: pd.Series, k: int) -> float:
        return series.iloc[-1] / series.iloc[-1 - k] - 1 if len(series) > k else np.nan

    r["ret21"], r["ret63"] = ret(c, 21), ret(c, 63)
    r["rs_raw"] = 0.5 * (r["ret21"] - ret(n5, 21)) + 0.5 * (r["ret63"] - ret(n5, 63))
    r["trend_raw"] = sum([C > sma[20], C > sma[50], C > sma[200], sma[20] > sma[50], sma[50] > sma[200]])
    vol_t, del_t = row["vol"], row["deliv"]
    r["vol_ratio"] = vol_t / prev20["vol"].median() if len(prev20) == 20 else np.nan
    r["deliv_ratio"] = del_t / prev20["deliv"].median() if len(prev20) == 20 and prev20["deliv"].median() else np.nan
    r["deliv_pct"] = del_t
    prev_hi = hi.iloc[:-1]
    r["bo55_level"] = prev_hi.tail(55).max()
    r["hi252"] = prev_hi.tail(252).max()
    r["bo55_raw"], r["bo252_raw"] = C / r["bo55_level"], C / r["hi252"]
    sec = SECTOR_MAP.get(industry)
    if sec and sec in idx.columns:
        si = idx[sec].loc[:t].dropna()
        r["sector_index"], r["sector_raw"] = sec, ret(si, 21) - ret(n5, 21)
    else:
        r["sector_index"], r["sector_raw"] = None, np.nan
    r["atr20"], r["vol_raw"] = atr, -atr / C
    r.update(sma20=sma[20], sma50=sma[50], sma200=sma[200], rsi=rsi14(c.tail(300)))
    r["close_quality"] = 0.5 if row["h"] == row["l"] else (row["c"] - row["l"]) / (row["h"] - row["l"])
    up = 0
    for x in c.diff().iloc[::-1]:
        if x > 0:
            up += 1
        else:
            break
    r["up_days"] = up
    # penalties (positive deductions)
    pen = {}
    if r["day_ret"] > 0.10 and persist == 1:
        pen["SPIKE"] = 15
    if C > 1.15 * sma[20]:
        pen["EXTENDED"] = 10
    if C < sma[200] and C < 0.65 * r["hi252"]:
        pen["DOWNTREND_BOUNCE"] = 15
    r["penalties"] = pen
    # EQS
    r["eqs"] = np.nanmean([lin(C / sma[20] - 1, 0.06, 0.12), lin(C / r["bo55_level"] - 1, 0.05, 0.10),
                           lin(r["rsi"], 70, 78), lin(up, 3, 5)])
    # stop (signal-time, fixed)
    S = C - 2 * atr  # v0.2 F1: volatility stop only
    r["stop"] = S
    r["stop_dist"] = 1 - S / C
    return r


ESSENTIAL = ["rs_raw", "trend_raw", "vol_ratio", "deliv_ratio", "bo55_raw", "bo252_raw", "vol_raw"]


def score_day(t: pd.Timestamp, b: pd.DataFrame, idx: pd.DataFrame, hist_by: dict,
              holdings: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    memb = load_membership(t)
    msyms = set(memb["symbol"])
    ind = memb.set_index("symbol")["industry"].to_dict()
    names = memb.set_index("symbol")["name"].to_dict()
    days = sorted(b["date"].unique())
    win = [d for d in days if d <= t][-P["window_sessions"]:]
    disc_by_day = {d: discovery(b, msyms, d) for d in win}
    disc_t = disc_by_day[t]
    persist = pd.Series(dtype=float)
    for d in win:
        persist = persist.add(pd.Series(1, index=disc_by_day[d]["symbol"]), fill_value=0)
    persist = persist.clip(upper=4).astype(int)
    universe = sorted(set(persist.index) | set(holdings))
    rows = [factors_for(s, t, b, hist_by, idx, ind.get(s, ""), int(persist.get(s, 0))) for s in universe]
    f = pd.DataFrame(rows).set_index("symbol")
    f["name"] = [names.get(s, s) for s in f.index]
    f["in_window"] = f.index.isin(persist.index)
    f["held"] = f.index.isin(holdings)
    # eligibility
    def elig(r) -> list[str]:
        why = list(r["reasons"])
        if why:
            return why
        if r["close"] < P["min_price"]:
            why.append("PRICE_LT_50")
        if not (r["med_turn_cr"] >= P["min_median_turnover_cr"]):
            why.append("LOW_TURNOVER")
        if not (r.get("n_prev", 0) >= P["min_history_sessions"]):
            why.append("INELIGIBLE_HISTORY")
        if any(pd.isna(r.get(k)) for k in ESSENTIAL):
            why.append("MISSING_FACTOR")
        return why
    f["inelig"] = f.apply(elig, axis=1)
    f["eligible"] = f["inelig"].str.len() == 0
    cand = f[f["eligible"] & f["in_window"]]
    ref = {
        "rs": cand["rs_raw"], "trend": cand["trend_raw"], "vol_r": cand["vol_ratio"], "del_r": cand["deliv_ratio"],
        "bo55": cand["bo55_raw"], "bo252": cand["bo252_raw"], "persist": cand["persist_n"].astype(float),
        "sector": cand["sector_raw"], "vol": cand["vol_raw"],
    }
    pct = {k: pct_rank(v) for k, v in ref.items()}
    raw_col = {"rs": "rs_raw", "trend": "trend_raw", "vol_r": "vol_ratio", "del_r": "deliv_ratio", "bo55": "bo55_raw",
               "bo252": "bo252_raw", "persist": "persist_n", "sector": "sector_raw", "vol": "vol_raw"}

    def p_of(sym: str, k: str) -> float:
        if sym in cand.index:
            return pct[k].get(sym, np.nan)
        return interp_pct(f.at[sym, raw_col[k]], ref[k])  # incumbents outside window (A1/§4)

    out = []
    for s in f.index:
        if not f.at[s, "eligible"] or len(cand) == 0:
            out.append({"symbol": s, "mqs": np.nan})
            continue
        fp = {"rs": p_of(s, "rs"), "trend": p_of(s, "trend"),
              "volume": np.nanmean([p_of(s, "vol_r"), p_of(s, "del_r")]),
              "breakout": np.nanmean([p_of(s, "bo55"), p_of(s, "bo252")]),
              "persist": p_of(s, "persist") if f.at[s, "in_window"] else 0.0,
              "sector": p_of(s, "sector"), "vol": p_of(s, "vol")}
        flags = []
        if pd.isna(fp["sector"]):
            fp["sector"] = 50.0
            flags.append("SECTOR_UNMAPPED")
        raw = sum(WEIGHTS[k] * fp[k] / 100 for k in WEIGHTS)
        ded = sum(f.at[s, "penalties"].values())
        top3 = sorted(WEIGHTS, key=lambda k: WEIGHTS[k] * fp[k], reverse=True)[:3]
        out.append({"symbol": s, "mqs_raw": raw, "deductions": ded, "mqs": float(np.clip(raw - ded, 0, 100)),
                    "flags": flags, "top3": [FACTOR_LABEL[k] for k in top3],
                    **{f"p_{k}": v for k, v in fp.items()}})
    sc = pd.DataFrame(out).set_index("symbol")
    f = f.join(sc)
    if f["flags"].isna().any():
        f["flags"] = f["flags"].apply(lambda x: x if isinstance(x, list) else [])
    for s in f.index:
        if f.at[s, "deliv_pct"] is not None and pd.notna(f.at[s, "deliv_pct"]) and f.at[s, "deliv_pct"] < 25:
            f.at[s, "flags"] = f.at[s, "flags"] + ["LOW_DELIVERY"]
        if pd.notna(f.at[s, "yahoo_vs_bhav"]) and abs(f.at[s, "yahoo_vs_bhav"]) > 0.01:
            f.at[s, "flags"] = f.at[s, "flags"] + ["YAHOO_BHAV_MISMATCH"]
    # circuit heuristic flag over last 5 sessions
    last5 = [d for d in days if d <= t][-5:]
    b5 = b[b["date"].isin(last5)].copy()
    b5["uc"] = (b5["h"] == b5["c"]) & (b5["c"] / b5["pc"] - 1 >= 0.099)
    ucs = b5.groupby("symbol")["uc"].sum()
    for s in f.index:
        if ucs.get(s, 0) >= 2:
            f.at[s, "flags"] = f.at[s, "flags"] + ["CIRCUIT_PATTERN"]
    f["date"] = t
    disc_t = disc_t.assign(name=disc_t["symbol"].map(names))
    return f, disc_t


# ---------------------------------------------------------------- portfolio (v0.2: one independent book per scenario)
PRIMARY = "c0.006"
BOOKS = {f"c{c:.3f}": {"cost": c, "fractional": False} for c in P["cost_scenarios"]}
BOOKS["frac0.006"] = {"cost": 0.006, "fractional": True}   # fractional-share shadow (rounding-noise check)


def fillable(row, side: str) -> bool:
    if row is None or pd.isna(row.get("o")) or not (row.get("trades", 0) > 0) or not (row.get("vol", 0) > 0):
        return False
    if row["h"] == row["l"]:
        if row["c"] > row["pc"] and side == "buy":
            return False
        if row["c"] < row["pc"] and side == "sell":
            return False
    return True


def load_state() -> dict:
    f = LED / "state.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"version": P["version"], "last_t": None, "books": {
        k: {**v, "cash": float(P["paper_capital"]), "positions": {}, "roster": {}, "pending": [], "cooldown": {}}
        for k, v in BOOKS.items()}}


def equity(bk: dict) -> float:
    return bk["cash"] + sum(p["qty"] * p["last"] for p in bk["positions"].values())


def execute(bk: dict, bt: pd.DataFrame, t: pd.Timestamp, fills: list, notes: list, key: str) -> None:
    """Official fills at the open of t (exits first, then buys in order), then stops on t, then mark to close."""
    c, d = bk["cost"], t.date().isoformat()
    get = lambda s: bt.loc[s] if s in bt.index else None
    say = (lambda m: notes.append(m)) if key == PRIMARY else (lambda m: None)
    keep_pending, failed_links = [], set()

    def fill(sym, side, qty, px, reason, entry):
        fills.append({"date": d, "book": key, "symbol": sym, "side": side, "qty": qty, "price": round(px, 4),
                      "reason": reason, "entry": entry})

    for o in [o for o in bk["pending"] if o["side"] == "sell"]:
        pos = bk["positions"].get(o["symbol"])
        if not pos:
            bk["roster"].pop(o["symbol"], None)
            continue
        row = get(o["symbol"])
        if fillable(row, "sell"):
            px = float(row["o"])
            bk["cash"] += pos["qty"] * px * (1 - c / 2)
            fill(o["symbol"], "sell", pos["qty"], px, o["reason"], pos["entry"])
            del bk["positions"][o["symbol"]]
            bk["roster"].pop(o["symbol"], None)
            if o["reason"] == "STOP":
                bk["cooldown"][o["symbol"]] = d
        else:
            failed_links.add(o.get("link"))
            keep_pending.append(o)                      # retry next open; slot stays reserved
            say(f"{o['symbol']}: exit not fillable at open — retried next session")
    for o in [o for o in bk["pending"] if o["side"] == "buy"]:
        s, row = o["symbol"], get(o["symbol"])
        why = None
        if o.get("link") and o["link"] in failed_links:
            why = "LINKED_EXIT_FAILED"
        elif not fillable(row, "buy"):
            why = "NOT_FILLABLE"
        elif float(row["o"]) <= o["stop"]:
            why = "GAP_BELOW_STOP"
        if why is None:
            px = float(row["o"])
            afford = bk["cash"] / (px * (1 + c / 2))
            cap = 0.20 * o["equity_t"] / px
            q = min(o["qty"], afford, cap)
            q = q if bk["fractional"] else math.floor(q)
            if q <= 0:
                why = "NO_CASH"
            else:
                bk["cash"] -= q * px * (1 + c / 2)
                bk["positions"][s] = {"qty": q, "entry": px, "entry_date": d, "stop": o["stop"], "last": px,
                                      "mqs_entry": o["mqs"]}
                fill(s, "buy", q, px, o["reason"] + ("" if q == o["qty"] else " PARTIAL"), px)
        if why:
            bk["roster"].pop(s, None)                    # zero fill releases the slot
            say(f"{s}: entry not filled ({why})")
    for s, pos in list(bk["positions"].items()):
        if any(o["symbol"] == s for o in keep_pending):
            continue
        row = get(s)
        if row is None:
            continue
        S = pos["stop"]
        hit = row["o"] <= S or row["l"] <= S
        if not hit:
            continue
        if not fillable(row, "sell"):
            keep_pending.append({"symbol": s, "side": "sell", "reason": "STOP"})
            say(f"{s}: stop triggered but locked — exit retried next open")
            continue
        px = float(row["o"]) if row["o"] <= S else S
        bk["cash"] += pos["qty"] * px * (1 - c / 2)
        fill(s, "sell", pos["qty"], px, "STOP", pos["entry"])
        del bk["positions"][s]
        bk["roster"].pop(s, None)
        bk["cooldown"][s] = d
        say(f"{s}: stop hit at ₹{px:,.2f}")
    for s, pos in bk["positions"].items():
        row = get(s)
        if row is not None and pd.notna(row["c"]):
            pos["last"] = float(row["c"])
    bk["pending"] = keep_pending


def decide(bk: dict, f: pd.DataFrame, t: pd.Timestamp, days: list, regime: str = "") -> tuple[list[dict], list[dict]]:
    """§6 + A3 + v0.2 F2/F3. Orders are frozen here for the next open."""
    roster, decisions, orders = bk["roster"], [], list(bk["pending"])  # carry retried exits
    E = equity(bk)
    di = {pd.Timestamp(x): i for i, x in enumerate(days)}
    for s in roster:
        if not roster[s].get("exiting"):
            roster[s]["sessions"] = roster[s].get("sessions", 0) + 1
    if f["mqs"].notna().sum() == 0:
        return [{"symbol": s, "action": "KEEP", "code": "MQS_UNAVAILABLE"} for s in roster], orders

    def mq(s):
        return f.at[s, "mqs"] if s in f.index else np.nan

    for s in list(roster):
        if roster[s].get("exiting"):
            continue
        code = "INELIGIBLE" if (s not in f.index or not f.at[s, "eligible"]) else ("MQS_LT_50" if mq(s) < P["remove_mqs"] else None)
        if code:
            decisions.append({"symbol": s, "action": "REMOVE", "code": code, "mqs": mq(s)})
            orders.append({"symbol": s, "side": "sell", "reason": code})
            roster[s]["exiting"] = True

    def add_block(s) -> str | None:
        r = f.loc[s]
        if not r["eligible"]:
            return "INELIGIBLE"
        if not r["in_window"]:
            return "NOT_IN_WINDOW"
        if r["mqs"] < P["add_mqs"]:
            return "BELOW_THRESHOLD"
        if not (r["atr20"] > 0) or not (0 < r["stop_dist"] <= P["max_stop_distance"]):
            return "STOP_TOO_WIDE" if r["stop_dist"] > P["max_stop_distance"] else "STOP_INVALID"
        if s in bk["cooldown"] and di.get(t, 0) - di.get(pd.Timestamp(bk["cooldown"][s]), -99) <= 4:
            return "COOLDOWN"
        if r["close"] > 0.20 * E:
            return "NOT_AFFORDABLE"
        return None

    ranked = sorted([s for s in f.index if pd.notna(f.at[s, "mqs"])], key=lambda s: (-f.at[s, "mqs"], s))
    rejected, adds = {}, []
    for s in ranked:
        if s in roster:
            continue
        why = add_block(s)
        (rejected.__setitem__(s, why) if why else adds.append(s))
    if P.get("pause_entries_risk_off") and regime == "Risk-off":       # shadow-variant switch (default off)
        for s in adds:
            rejected[s] = "RISK_OFF_PAUSE"
        adds = []
    cap = P.get("max_per_sector")                                         # shadow-variant switch (default off)

    def sector_ok(s, leaving=None) -> bool:
        if not cap:
            return True
        ind = f.at[s, "industry"]
        n = sum(1 for x in roster if not roster[x].get("exiting") and x != leaving and x in f.index
                and f.at[x, "industry"] == ind)
        return n < cap

    new = []
    free = P["max_positions"] - len(roster)
    while free > 0 and adds:
        s = adds.pop(0)
        if not sector_ok(s):
            rejected[s] = "SECTOR_CAP"
            continue
        roster[s] = {"since": t.date().isoformat(), "sessions": 0}
        decisions.append({"symbol": s, "action": "ADD", "code": "FREE_SLOT", "mqs": mq(s)})
        new.append((s, "ADD", None))
        free -= 1
    swaps = 0
    while adds and swaps < P["max_swaps_per_day"]:
        inc = [s for s in roster if not roster[s].get("exiting") and roster[s]["sessions"] >= P["min_tenure_sessions"]
               and s in f.index and s not in [n[0] for n in new]]
        if not inc:
            break
        weakest = min(inc, key=lambda s: (mq(s), s))
        ch = adds[0]
        if not sector_ok(ch, leaving=weakest):
            rejected[ch] = "SECTOR_CAP"
            adds.pop(0)
            continue
        if mq(ch) - mq(weakest) < P["replace_margin"]:
            break
        link = f"{t.date()}:{weakest}->{ch}"
        decisions.append({"symbol": weakest, "action": "REPLACED", "code": f"BY_{ch}", "mqs": mq(weakest)})
        decisions.append({"symbol": ch, "action": "ADD", "code": f"REPLACES_{weakest}", "mqs": mq(ch)})
        orders.append({"symbol": weakest, "side": "sell", "reason": f"REPLACED_BY_{ch}", "link": link})
        roster[weakest]["exiting"], roster[weakest]["link"] = True, link
        roster[ch] = {"since": t.date().isoformat(), "sessions": 0}
        new.append((ch, "REPLACE", link))
        adds.pop(0)
        swaps += 1
    N = sum(1 for s in roster if not roster[s].get("exiting"))
    w = 1 / max(P["min_positions_target"], N)
    for s, reason, link in new:
        C = f.at[s, "close"]
        q = w * E / C
        q = q if bk["fractional"] else (math.floor(q) or (1 if C <= 0.20 * E else 0))
        orders.append({"symbol": s, "side": "buy", "reason": reason, "link": link, "stop": float(f.at[s, "stop"]),
                       "qty": q, "ref_close": float(C), "equity_t": E, "target_w": w, "mqs": float(mq(s))})
    for s in roster:
        if not roster[s].get("exiting") and not any(d["symbol"] == s for d in decisions):
            decisions.append({"symbol": s, "action": "KEEP", "code": "", "mqs": mq(s)})
    for s in adds:
        rejected[s] = "NO_SLOT" if swaps == 0 else "CHURN_GUARD"
    for s in [s for s in ranked if s not in roster][:15]:
        decisions.append({"symbol": s, "action": "WATCH", "code": rejected.get(s, ""), "mqs": mq(s)})
    return decisions, orders


def cohorts(f: pd.DataFrame, disc: pd.DataFrame, t: pd.Timestamp) -> list[dict]:
    el = f[f["eligible"] & f["in_window"]].copy()
    el["sym"] = el.index

    def top(by: list[str], asc: list[bool], frame=el) -> list[str]:
        return frame.sort_values(by + ["sym"], ascending=asc + [True]).head(10).index.tolist()

    mqs10 = top(["mqs"], [False])
    out = {
        "DISCOVERY": disc["symbol"].tolist(), "ELIGIBLE": sorted(el.index),
        "MQS10": mqs10, "MQS10_EQS": [s for s in mqs10 if el.at[s, "eqs"] >= 60],
        "PERSIST10": top(["persist_n", "day_ret"], [False, False]),
        "RAW10": top(["day_ret"], [False], el[el.index.isin(disc["symbol"])]),
        "MOM63_10": top(["ret63"], [False]),
    }
    return [{"date": t.date(), "cohort": k, "n": len(v), "members": " ".join(v),
             "random_seed": int(t.strftime("%Y%m%d")) if k == "ELIGIBLE" else ""} for k, v in out.items()]




# ---------------------------------------------------------------- main
def append(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, mode="a", header=not path.exists(), index=False)


def run(t: pd.Timestamp) -> dict:
    LED.mkdir(exist_ok=True)
    b, idx, hist = load_bhav(), load_index(), load_history()
    if t not in set(b["date"]):
        raise SystemExit(f"no bhavcopy for {t.date()}")
    hist_by = {s: g.sort_values("date") for s, g in hist.groupby("symbol")}
    days = sorted(b["date"].unique())
    state = load_state()
    if state["last_t"] and pd.Timestamp(state["last_t"]) >= t:
        raise SystemExit(f"already ran for {state['last_t']}; refusing to re-run {t.date()}")
    bt = b[b["date"] == t].set_index("symbol")
    fills, notes = [], []
    for k, bk in state["books"].items():
        execute(bk, bt, t, fills, notes, k)
    holdings = sorted({s for bk in state["books"].values() for s in bk["roster"]})
    f, disc = score_day(t, b, idx, hist_by, holdings)
    # regime (logged only)
    above = total = 0
    for s in load_membership(t)["symbol"]:
        h = hist_by.get(s)
        if h is None:
            continue
        h = h[h["date"] <= t]
        if len(h) >= 50:
            total += 1
            above += int(h["yc"].iloc[-1] > h["yc"].tail(50).mean())
    breadth = above / total if total else np.nan
    n5 = idx["Nifty 500"].loc[:t].dropna()
    below200 = len(n5) >= 200 and n5.iloc[-1] < n5.tail(200).mean()   # needs >=200 index files; else breadth-only
    if breadth < 0.30 or below200:
        regime = "Risk-off"
    elif breadth >= 0.50 and n5.iloc[-1] > n5.tail(50).mean():
        regime = "Risk-on"
    else:
        regime = "Neutral"
    all_dec = {}
    for k, bk in state["books"].items():
        dec, orders = decide(bk, f, t, days, regime)
        bk["pending"] = orders
        all_dec[k] = dec
    state["last_t"] = t.date().isoformat()
    # ---- append-only ledgers
    keep = ["date", "name", "industry", "close", "day_ret", "persist_n", "in_window", "held", "eligible", "inelig",
            "mqs", "mqs_raw", "deductions", "penalties", "flags", "eqs", "rsi", "sma20", "sma50", "sma200",
            "atr20", "stop", "stop_dist", "bo55_level", "hi252", "ret21", "ret63", "rs_raw", "trend_raw",
            "vol_ratio", "deliv_ratio", "deliv_pct", "sector_index", "sector_raw", "close_quality", "up_days",
            "med_turn_cr", "yahoo_vs_bhav", "top3", "p_rs", "p_trend", "p_volume", "p_breakout", "p_persist",
            "p_sector", "p_vol"]
    append(f[keep].reset_index(), DATA / "candidates.csv")
    append(disc[["date", "disc_rank", "symbol", "name", "c", "ret", "vol", "deliv"]], DATA / "discovery.csv")
    append(pd.DataFrame([{**d, "date": t.date(), "book": k} for k, dec in all_dec.items() for d in dec]),
           LED / "watchlist.csv")
    if fills:
        append(pd.DataFrame(fills), LED / "fills.csv")
    append(pd.DataFrame(cohorts(f, disc, t)), LED / "cohorts.csv")
    eq = {k: equity(bk) for k, bk in state["books"].items()}
    append(pd.DataFrame([{"date": t.date(), "book": k, "equity": v, "cash": state["books"][k]["cash"],
                          "n_positions": len(state["books"][k]["positions"]), "nifty500": n5.iloc[-1],
                          "breadth": breadth, "regime": regime} for k, v in eq.items()]), LED / "equity.csv")
    (LED / "state.json").write_text(json.dumps(state, indent=1, default=str))
    summary = {"t": t.date().isoformat(), "version": P["version"], "regime": regime, "breadth": breadth,
               "nifty500": float(n5.iloc[-1]), "equity": eq, "exec_notes": notes, "n_disc": len(disc),
               "n_cand": int((f["eligible"] & f["in_window"]).sum()), "primary": PRIMARY,
               "orders": state["books"][PRIMARY]["pending"], "decisions": all_dec[PRIMARY],
               "fills_today": [x for x in fills if x["book"] == PRIMARY]}
    (LED / f"run_{t.date()}.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--signal", required=True)
    s = run(pd.Timestamp(ap.parse_args().signal))
    print(json.dumps({k: s[k] for k in ("t", "regime", "breadth", "equity", "n_disc", "n_cand", "exec_notes")},
                     default=str, indent=1))
    for d in s["decisions"]:
        if d["action"] != "WATCH":
            print(d["action"], d["symbol"], d["code"], round(d["mqs"], 1) if d.get("mqs") == d.get("mqs") and d.get("mqs") is not None else "")
    for o in s["orders"]:
        print("ORDER", o["side"], o["symbol"], o.get("qty"), o.get("reason"), round(o.get("stop", 0), 2))
