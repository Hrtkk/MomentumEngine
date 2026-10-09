"""Point-in-time panels for E2 (SPEC_E2 §1): stitched symbols, corporate-action adjusted prices, Liquid-500 universe."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

import panels as PN

D = Path(__file__).resolve().parent / "data"
PIT = D / "pit"


def symbol_map() -> dict[str, str]:
    m = {}
    for line in (PIT / "symbolchange.csv").read_text(errors="ignore").splitlines():
        parts = line.rsplit(",", 3)
        if len(parts) == 4:
            old, new = parts[1].strip(), parts[2].strip()
            if old and new and old != new:
                m[old] = new
    final = {}
    for o in m:                                   # follow chains old -> ... -> newest
        n, seen = m[o], {o}
        while n in m and n not in seen:
            seen.add(n)
            n = m[n]
        final[o] = n
    return final


def ca_factors() -> pd.DataFrame:
    """Equity bonus a:b -> (a+b)/b and face-value split X -> Y -> X/Y; both multiply when combined.
    Bonus preference shares / debentures and rights/demerger/schemes are NOT price adjustments here -> alerts."""
    ca = pd.read_parquet(PIT / "ca.parquet")
    ca = ca[ca["series"].isin(["EQ", "BE", "BZ"])]
    rows = []
    for r in ca.itertuples():
        sub = " ".join(str(r.subject).split())
        ex = pd.to_datetime(r.exDate, format="%d-%b-%Y", errors="coerce")
        if pd.isna(ex):
            continue
        f, kinds = 1.0, []
        for m in re.finditer(r"bonus(?!\s*(?:pref|deb|redeem|ncd|bond))[^0-9]{0,12}(\d+)\s*:\s*(\d+)", sub, re.I):
            a, b = int(m.group(1)), int(m.group(2))
            if b > 0:
                f *= (a + b) / b
                kinds.append("BONUS")
        m2 = re.search(r"(?:split|splt|sub-?division).*?(?:rs|re)\.?\s*([\d.]+).*?\bto\b\s*(?:rs|re)\.?\s*([\d.]+)", sub, re.I)
        if m2:
            x, y = float(m2.group(1)), float(m2.group(2))
            if y > 0 and x > y:
                f *= x / y
                kinds.append("SPLIT")
        if kinds:
            rows.append({"symbol": r.symbol, "ex": ex.normalize(), "factor": f, "kind": "+".join(kinds), "subject": sub})
        else:   # any other action (scheme, demerger, rights, special dividend, ...) -> price-checked in build()
            rows.append({"symbol": r.symbol, "ex": ex.normalize(), "factor": np.nan, "kind": "OTHER", "subject": sub})
    df = pd.DataFrame(rows)
    # one row per symbol/ex-date: candidate factors = each distinct factor and their product (bonus + split filed
    # as separate records); the price check in build() picks the candidate the market confirms
    out = []
    for (sym, ex), g in df.groupby(["symbol", "ex"]):
        # v1.1: de-duplicate by filing text, not by factor value (a 2x split + 2x bonus = 4x, not 2x)
        fs = sorted(g.dropna(subset=["factor"]).drop_duplicates("subject")["factor"].round(6).tolist())
        cands = fs + ([float(np.prod(fs))] if len(fs) > 1 else [])
        out.append({"symbol": sym, "ex": ex, "factor": cands[-1] if cands else np.nan, "cands": cands,
                    "kind": "+".join(sorted(set("+".join(g["kind"]).split("+")))), "subject": " || ".join(g["subject"])})
    return pd.DataFrame(out)


def load_bhav() -> pd.DataFrame:
    frames = [pd.read_parquet(f) for f in sorted(PIT.glob("bhav_*.parquet"))]
    b = pd.concat(frames, ignore_index=True)
    b = b[b["series"].isin(["EQ", "BE", "BZ"])].copy()
    b = b[~b["isin"].astype(str).str.startswith("INF")]          # ETFs / MF units are not equities
    sm = symbol_map()
    b["symbol"] = b["symbol"].map(lambda s: sm.get(s, s))
    for c in ["open", "high", "low", "close", "prev_close", "volume", "value", "trades"]:
        b[c] = pd.to_numeric(b[c], errors="coerce")
    b["is_eq"] = b["series"] == "EQ"
    # one row per symbol-day: prefer EQ
    b = b.sort_values(["date", "symbol", "is_eq"]).drop_duplicates(["date", "symbol"], keep="last")
    return b


class PitPanels(PN.Panels):
    """Same attributes as E1 Panels; eligibility = Liquid-500 membership & EQ-series on t & no recent data alert."""

    def __post_init__(self):
        super().__post_init__()
        self.eligible = self.universe & self.is_eq.fillna(False).astype(bool) & self.C.notna() & ~self.badwin_
        el = self.eligible
        self.blend = (0.35 * PN.pct_rank(self.R3, el) + 0.30 * PN.pct_rank(self.R6, el)
                      + 0.20 * PN.pct_rank(self.R12_1, el) + 0.15 * PN.pct_rank(self.VAM6, el)).where(el)
        lr = np.log(self.C / self.C.shift(1))
        self.vol252 = lr.rolling(252, min_periods=252).std() * np.sqrt(252)
        self.VAM12 = (self.R12 / self.vol252).where(self.vol252 > 0)
        self.m5 = ((PN.pct_rank(self.VAM6, el) + PN.pct_rank(self.VAM12, el)) / 2).where(el)
        self.R5 = self.C / self.C.shift(5) - 1


def build(cache: bool = True) -> PitPanels:
    f = D / "pit_panels.pkl"
    if cache and f.exists():
        return pd.read_pickle(f)
    b = load_bhav()
    piv = lambda col: b.pivot_table(index="date", columns="symbol", values=col, aggfunc="last")
    raw_c, prev = piv("close"), piv("prev_close")
    val, iseq = piv("value"), b.pivot_table(index="date", columns="symbol", values="is_eq", aggfunc="last")
    dates = raw_c.index
    # ---- Liquid-500 at each month-end (nominal close, raw traded value — no adjustment needed)
    n_prior = raw_c.notna().cumsum().shift(1).fillna(0)
    medval = val.rolling(63, min_periods=40).median()
    me = dates.to_series().groupby(dates.to_period("M")).max()
    uni = pd.DataFrame(False, index=dates, columns=raw_c.columns)
    members_any = set()
    for k, m in enumerate(me.values[:-1]):
        m = pd.Timestamp(m)
        ok = (iseq.loc[m] == True) & (n_prior.loc[m] >= 252) & (raw_c.loc[m] >= 50)  # noqa: E712
        top = medval.loc[m].where(ok).dropna().sort_values(ascending=False).head(500).index
        nxt = pd.Timestamp(me.values[k + 1])
        rows = (dates > m) & (dates <= nxt)
        uni.loc[rows, top] = True
        members_any |= set(top)
    keep = sorted(members_any)
    # ---- corporate-action adjustment
    cf = ca_factors()
    adj = pd.DataFrame(1.0, index=dates, columns=keep)
    alerts, pending = [], []
    for r in cf[cf["symbol"].isin(keep)].itertuples():
        on = dates[dates >= r.ex]
        if len(on) == 0:
            continue
        d0 = on[0]
        prev = raw_c[r.symbol].loc[:d0].iloc[:-1].dropna()
        cur = raw_c[r.symbol].get(d0, np.nan)
        q = cur / prev.iloc[-1] if len(prev) and pd.notna(cur) else np.nan
        best = None
        if pd.notna(q):
            for fct in r.cands:
                if fct > 1 and abs(q * fct - 1) <= 0.30 and (best is None or abs(q * fct - 1) < abs(q * best - 1)):
                    best = fct
        if best:
            adj.loc[dates < d0, r.symbol] *= best
            alerts.append({"symbol": r.symbol, "date": d0, "kind": r.kind, "factor": best, "subject": r.subject})
        else:
            if r.kind != "OTHER":
                alerts.append({"symbol": r.symbol, "date": d0, "kind": "CA_PENDING", "factor": np.nan,
                               "subject": f"{r.subject} | close ratio {q:.3f}"})
            pending.append((r.symbol, d0))
    sub = b[b["symbol"].isin(keep)]
    P5 = {c: sub.pivot_table(index="date", columns="symbol", values=c, aggfunc="last").reindex(index=dates, columns=keep)
          for c in ("open", "high", "low", "close", "volume")}
    man = PIT / "manual_ca.csv"
    if man.exists():
        for m in pd.read_csv(man).itertuples():
            if m.symbol in keep:
                pending.append((m.symbol, pd.Timestamp(m.date)))
    # demergers / schemes / rights / unconfirmed CA: value-neutral if the ex-day overnight gap is >= 30% (SPEC_E2 A9)
    for sym, d0 in pending:
        c_adj = P5["close"][sym] / adj[sym]
        prev = c_adj.loc[:d0].iloc[:-1].dropna()
        cur = c_adj.get(d0, np.nan)
        if not len(prev) or pd.isna(cur):
            continue
        q = cur / prev.iloc[-1]                     # close-to-close on the ex-day (A9)
        if q <= 0.70 or q >= 1 / 0.70:
            adj.loc[dates < d0, sym] *= 1 / q
            alerts.append({"symbol": sym, "date": d0, "kind": "CA_NEUTRALISED", "factor": float(1 / q),
                           "subject": "value-neutral: demerger/scheme/special dividend/unconfirmed split"})
    O, H, L, C = (P5[c] / adj for c in ("open", "high", "low", "close"))
    V = P5["volume"] * adj
    # unexplained overnight gaps (A1 alerts)
    gap = O / C.shift(1)
    g = ((gap <= 0.6) | (gap >= 1.6)) & gap.notna()
    for d, s in zip(*np.where(g.values)):
        alerts.append({"symbol": keep[s], "date": dates[d], "kind": "UNEXPLAINED_GAP", "factor": float(gap.iat[d, s]), "subject": ""})
    ix = pd.read_parquet(D / "nifty500_index.parquet").set_index("date")["close"].reindex(dates).ffill()
    memb = pd.read_csv(sorted((D.parents[1] / "data" / "membership").glob("*_nifty500.csv"))[-1])
    industry = memb.set_index("Symbol")["Industry"]
    P = PitPanels.__new__(PitPanels)
    P.universe = uni[keep]
    P.is_eq = iseq.reindex(index=dates, columns=keep)
    P.O, P.H, P.L, P.C, P.V, P.n5, P.industry, P.deliv, P.nominal = O, H, L, C, V, ix, industry, None, raw_c[keep]
    P.alerts = pd.DataFrame(alerts)
    # bad-print window for signals (A1): unexplained gaps and |ret|>40% that are not explained CA days
    r1 = C / C.shift(1) - 1
    bad = (r1.abs() > 0.40) | g
    P.badwin_ = bad.astype(float).rolling(253, min_periods=1).max().fillna(0).astype(bool)
    P.__post_init__()
    if cache:
        pd.to_pickle(P, f)
    return P
