"""Experiment E1 simulator (SPEC.md incl. §7 amendments A1–A8).

One execution/portfolio layer; strategies differ only in decision rules.
Order of a session i:  fills at open (exits, then buys) -> intraday stops -> mark to close -> decisions on close.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from panels import Panels, pct_rank

CAPITAL = 60_000.0


@dataclass
class Book:
    cost: float
    slots: int = 10
    sector_cap: int | None = 3
    cash: float = CAPITAL
    pos: dict = field(default_factory=dict)        # sym -> {qty, entry, stop, entry_i, meta, last}
    pending: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    equity: list = field(default_factory=list)
    cooldown: dict = field(default_factory=dict)   # S0-E1 only
    log: list = field(default_factory=list)

    def value(self) -> float:
        return self.cash + sum(p["qty"] * p["last"] for p in self.pos.values())


def period_ends(dates: pd.DatetimeIndex, monthly: bool) -> set:
    """True period ends only (A7): drop the period that contains the last data date."""
    s = dates.to_series()
    key = s.dt.to_period("M") if monthly else s.dt.to_period("W-SUN")
    ends = s.groupby(key.values).max()
    return set(ends.iloc[:-1])


class Strategy:
    name, slots, sector_cap, uses_rank_exit = "base", 10, 3, True

    def __init__(self, P: Panels):
        self.P = P
        self.week_end = period_ends(P.C.index, False)
        self.month_end = period_ends(P.C.index, True)
        self.frozen_rank: pd.Series = pd.Series(dtype=int)
        self.frozen_score: pd.Series = pd.Series(dtype=float)

    def refresh(self, t) -> bool:
        return t in self.week_end

    def daily_exits(self, bk: Book, i: int, t) -> list[tuple[str, str]]:
        """A5: holdings that become ineligible (data present) exit next open."""
        P, out = self.P, []
        for s in bk.pos:
            if pd.isna(P.C.at[t, s]):
                bk.log.append((t, s, "UNRESOLVED_NO_DATA"))
            elif not P.eligible.at[t, s] and not P.bad.at[t, s]:
                out.append((s, "INELIGIBLE"))
        return out

    def decide(self, bk, i, t):
        return [], []

    def cat_stop(self, s, t) -> float:
        return float(self.P.C.at[t, s] - 3 * self.P.atr20.at[t, s])

    def ok_atr(self, s, t) -> bool:
        a = self.P.atr20.at[t, s]
        return pd.notna(a) and a > 0 and self.cat_stop(s, t) > 0


class RankStrategy(Strategy):
    """S1–S4: rank on refresh days; enter rank<=50 (immediate), stay while rank<=125."""

    def __init__(self, P, score, name, monthly=False):
        super().__init__(P)
        self.score, self.name, self.monthly = score, name, monthly

    def refresh(self, t):
        return t in (self.month_end if self.monthly else self.week_end)

    def rank_exits(self, bk, t):
        rk = self.P.rank_of(self.score, t)
        self.frozen_rank = rk
        self.frozen_score = self.score.loc[t].reindex(rk.index)
        return [(s, "RANK_GT_125") for s in bk.pos if rk.get(s, 10**6) > 125]

    def decide(self, bk, i, t):
        if not self.refresh(t):
            return [], []
        sells = self.rank_exits(bk, t)
        rk = self.frozen_rank
        buys = [(s, self.cat_stop(s, t), {}) for s in rk[rk <= 50].sort_values().index
                if s not in bk.pos and self.ok_atr(s, t)]
        return sells, buys                       # slot/sector limits enforced at the fill (A5)


class S5Patient(RankStrategy):
    def __init__(self, P):
        super().__init__(P, P.blend, "S5 blend + patient entry")
        self.watch: list[str] = []

    def decide(self, bk, i, t):
        P = self.P
        sells = []
        if self.refresh(t):
            sells = self.rank_exits(bk, t)
            rk = self.frozen_rank
            trend = (P.C.loc[t] > P.sma50.loc[t]) & (P.sma50.loc[t] > P.sma200.loc[t])
            self.watch = [s for s in rk[rk <= 40].sort_values().index if bool(trend.get(s, False))]
        buys = []
        for s in self.watch:                     # frozen order = frozen rank (score desc, symbol asc)
            if s in bk.pos or not P.eligible.at[t, s]:
                continue
            c = P.C.at[t, s]
            if not (c > P.sma50.at[t, s] and P.sma50.at[t, s] > P.sma200.at[t, s]):
                continue
            not_ext = P.ret1.at[t, s] < 0.05 and c / P.sma20.at[t, s] - 1 <= 0.07 and P.rsi.at[t, s] <= 70
            win = P.C[s].iloc[i - 9:i + 1]
            hl5 = P.H[s].iloc[i - 4:i + 1].max() - P.L[s].iloc[i - 4:i + 1].min()
            reset = win.max() >= 1.03 * c or hl5 <= 1.5 * P.atr20.at[t, s]
            up = c > P.C[s].iloc[i - 1]
            if not_ext and reset and up and self.ok_atr(s, t):
                buys.append((s, self.cat_stop(s, t), {}))
        return sells, buys

    def daily_exits(self, bk, i, t):
        P = self.P
        out = super().daily_exits(bk, i, t)
        out += [(s, "TREND_BREAK") for s in bk.pos
                if pd.notna(P.C.at[t, s]) and P.C.at[t, s] < P.sma50.at[t, s] and (s, "INELIGIBLE") not in out]
        return out


class S7Confirm(RankStrategy):
    """A6 state machine: events only for frozen S4 top-50; one active event per name; first confirmation only."""

    def __init__(self, P):
        super().__init__(P, P.blend, "S7 gainer event + confirmation")
        self.active: dict[str, dict] = {}       # sym -> {t0, mid, hi0, lo0, v0}
        self.is_event = P.eligible & (P.ret1 >= 0.05) & (P.V >= 2 * P.medV20)

    def decide(self, bk, i, t):
        P = self.P
        sells = []
        if self.refresh(t):
            sells = self.rank_exits(bk, t)
        top50 = set(self.frozen_rank[self.frozen_rank <= 50].index) if len(self.frozen_rank) else set()
        # 1) update / invalidate active events (k counted in sessions; T0 itself included in midpoint test)
        conf = []
        for s, e in list(self.active.items()):
            k = i - e["t0"]
            c = P.C.at[t, s]
            if s not in top50 or k > 7 or pd.isna(c) or c < e["mid"]:
                del self.active[s]
                continue
            if k >= 3:
                prior_hi = P.H[s].iloc[e["t0"] + 1:i].max()
                vol_ok = P.V[s].iloc[e["t0"] + 1:i].mean() < e["v0"]
                if c >= e["hi0"] and c > prior_hi and vol_ok:
                    conf.append(s)
        # 2) new events on t (only if in frozen top-50 and no active event)
        for s in top50:
            if s not in self.active and s not in bk.pos and bool(self.is_event.at[t, s]):
                h, l = P.H.at[t, s], P.L.at[t, s]
                self.active[s] = {"t0": i, "mid": (h + l) / 2, "hi0": h, "lo0": l, "v0": P.V.at[t, s]}
        # 3) confirmed -> one order attempt, event consumed
        buys = []
        order = sorted(conf, key=lambda s: (-self.frozen_score.get(s, -1), s))
        for s in order:
            e = self.active.pop(s)
            if s not in bk.pos and P.eligible.at[t, s] and self.ok_atr(s, t):
                buys.append((s, self.cat_stop(s, t), {"t0low": float(e["lo0"])}))
        return sells, buys

    def daily_exits(self, bk, i, t):
        out = super().daily_exits(bk, i, t)
        out += [(s, "BELOW_T0_LOW") for s, p in bk.pos.items()
                if "t0low" in p["meta"] and pd.notna(self.P.C.at[t, s]) and self.P.C.at[t, s] < p["meta"]["t0low"]]
        return out


class S0E1(Strategy):
    """v0.2.1 rules adapted per SPEC A4 (S0-E1): fractional, sector pct 50, delivery optional, no affordability gate."""
    name, slots, sector_cap = "S0-E1 v0.2.1 gainers", 13, None

    def __init__(self, P):
        super().__init__(P)
        el = P.eligible
        pos_ret = P.ret1.where(P.C.notna() & (P.ret1 > 0))
        disc = pos_ret.rank(axis=1, ascending=False, method="first") <= 100
        self.persist = disc.astype(int).rolling(7, min_periods=1).sum().clip(upper=4)
        self.cand = el & (self.persist > 0)
        trend = ((P.C > P.sma20).astype(int) + (P.C > P.sma50) + (P.C > P.sma200) + (P.sma20 > P.sma50)
                 + (P.sma50 > P.sma200)).astype(float)
        self.raw = {"rs": 0.5 * P.R21 + 0.5 * P.R3, "trend": trend, "volr": P.V / P.medV20,
                    "bo55": P.C / P.hi55, "bo252": P.C / P.hi252, "persist": self.persist.astype(float),
                    "vol": -P.atr20 / P.C}
        if P.deliv is not None:
            self.raw["delr"] = P.deliv / P.deliv.rolling(20, min_periods=20).median().shift(1)
        c = self.cand
        pct = {k: pct_rank(v, c) for k, v in self.raw.items()}
        if "delr" in pct:
            volume = (pct["volr"] + pct["delr"].fillna(pct["volr"])) / 2      # volume-only where delivery missing
        else:
            volume = pct["volr"]
        brk = (pct["bo55"] + pct["bo252"]) / 2
        self.ded = (15 * ((P.ret1 > 0.10) & (self.persist == 1)) + 10 * (P.C > 1.15 * P.sma20)
                    + 15 * ((P.C < P.sma200) & (P.C < 0.65 * P.hi252))).astype(float)
        mqs = (25 * pct["rs"] + 15 * pct["trend"] + 15 * volume + 15 * brk + 10 * pct["persist"] + 10 * 50
               + 10 * pct["vol"]) / 100
        self.mqs = (mqs - self.ded).clip(0, 100).where(c)

    def mqs_of(self, s, t) -> float:
        v = self.mqs.at[t, s]
        if pd.notna(v):
            return float(v)
        if not self.P.eligible.at[t, s]:
            return np.nan
        c = self.cand.loc[t]

        def ip(k):
            ref = self.raw[k].loc[t][c].dropna()
            x = self.raw[k].at[t, s]
            if ref.empty or pd.isna(x):
                return np.nan
            n = len(ref)
            pr = 100 * (ref.rank(method="average") - 1) / (n - 1) if n > 1 else ref * 0 + 50
            pts = pd.DataFrame({"v": ref, "p": pr}).groupby("v")["p"].mean().sort_index()
            return float(np.interp(x, pts.index, pts.values, left=0.0, right=100.0))

        vols = [ip("volr")] + ([ip("delr")] if "delr" in self.raw and pd.notna(self.raw["delr"].at[t, s]) else [])
        val = (25 * ip("rs") + 15 * ip("trend") + 15 * np.nanmean(vols) + 15 * np.nanmean([ip("bo55"), ip("bo252")])
               + 10 * 50 + 10 * ip("vol")) / 100 - self.ded.at[t, s]
        return float(np.clip(val, 0, 100)) if pd.notna(val) else np.nan

    def daily_exits(self, bk, i, t):
        return []                                  # S0 handles ineligibility inside decide (as v0.2.1)

    def decide(self, bk, i, t):
        P = self.P
        for s in bk.pos:
            bk.pos[s]["sessions"] = bk.pos[s].get("sessions", 0) + 1
        mq = {s: self.mqs_of(s, t) for s in bk.pos}
        sells = [(s, "INELIGIBLE" if pd.isna(v) else "MQS_LT_50") for s, v in mq.items() if pd.isna(v) or v < 50]
        leaving = {s for s, _ in sells}
        today = self.mqs.loc[t].dropna()
        ranked = sorted(today.index, key=lambda s: (-today[s], s))
        adds = []
        for s in ranked:
            if s in bk.pos or today[s] < 70:
                continue
            atr, c = P.atr20.at[t, s], P.C.at[t, s]
            if not (pd.notna(atr) and atr > 0):
                continue
            stop = c - 2 * atr
            if not (0 < 1 - stop / c <= 0.08):
                continue
            if s in bk.cooldown and i - bk.cooldown[s] <= 4:
                continue
            adds.append((s, stop))
        free = self.slots - (len(bk.pos) - len(leaving))
        buys = []
        while free > 0 and adds:
            s, stop = adds.pop(0)
            buys.append((s, stop, {}))
            free -= 1
        swaps = 0
        while adds and swaps < 2:
            inc = [s for s in bk.pos if s not in leaving and bk.pos[s].get("sessions", 0) >= 3 and pd.notna(mq.get(s))]
            if not inc:
                break
            weakest = min(inc, key=lambda s: (mq[s], s))
            s, stop = adds[0]
            if today[s] - mq[weakest] < 10:
                break
            sells.append((weakest, f"REPLACED_BY_{s}"))
            leaving.add(weakest)
            buys.append((s, stop, {"link": weakest}))
            adds.pop(0)
            swaps += 1
        w = 1 / max(7, len(bk.pos) - len(leaving) + len(buys))
        return sells, [(s, st, {**m, "w": w}) for s, st, m in buys]


# ---------------------------------------------------------------- execution
def fillable(P: Panels, i: int, s: str, side: str) -> bool:
    t = P.C.index[i]
    o, h, l, c = P.O.at[t, s], P.H.at[t, s], P.L.at[t, s], P.C.at[t, s]
    if any(pd.isna(x) for x in (o, h, l, c)) or not (P.V.at[t, s] > 0):
        return False
    if h == l:
        pc = P.C.iat[i - 1, P.C.columns.get_loc(s)]
        if c > pc and side == "buy":
            return False
        if c < pc and side == "sell":
            return False
    return True


def run(strategy: Strategy, cost: float, start_i: int, integer: bool = False, capital: float = CAPITAL,
        live: bool = False) -> Book:
    P = strategy.P
    bk = Book(cost=cost, slots=strategy.slots, sector_cap=strategy.sector_cap, cash=capital)
    dates = P.C.index
    ind = P.industry
    for i in range(start_i, len(dates)):
        t = dates[i]
        # 1) exits at open, then buys in order (A5)
        keep, failed = [], set()
        for o in [o for o in bk.pending if o["side"] == "sell"]:
            s = o["sym"]
            if s not in bk.pos:
                continue
            if fillable(P, i, s, "sell"):
                px = float(P.O.at[t, s])
                p = bk.pos.pop(s)
                bk.cash += p["qty"] * px * (1 - cost / 2)
                bk.trades.append({"sym": s, "entry_i": p["entry_i"], "exit_i": i, "entry": p["entry"], "exit": px,
                                  "qty": p["qty"], "reason": o["reason"]})
            else:
                keep.append(o)
                failed.add(s)
        for o in [o for o in bk.pending if o["side"] == "buy"]:
            s = o["sym"]
            if s in bk.pos or o["meta"].get("link") in failed:
                continue
            if len(bk.pos) >= bk.slots:
                continue
            if bk.sector_cap and sum(1 for x in bk.pos if ind.get(x, "?") == ind.get(s, "?")) >= bk.sector_cap:
                continue
            if not fillable(P, i, s, "buy"):
                continue
            px = float(P.O.at[t, s])
            if o["stop"] <= 0 or px <= o["stop"]:
                continue
            qty = min(o["qty"], bk.cash / (px * (1 + cost / 2)))
            if integer:
                qty = math.floor(qty)
            if qty <= 0:
                continue
            bk.cash -= qty * px * (1 + cost / 2)
            meta = {k: v for k, v in o["meta"].items() if k != "link"}
            bk.pos[s] = {"qty": qty, "entry": px, "stop": o["stop"], "entry_i": i, "meta": meta, "last": px}
        bk.pending = keep
        # 2) intraday stops (active from entry session)
        for s in list(bk.pos):
            p = bk.pos[s]
            if any(x["sym"] == s for x in bk.pending):
                continue
            o_, l_ = P.O.at[t, s], P.L.at[t, s]
            if pd.isna(o_) or pd.isna(l_) or not (o_ <= p["stop"] or l_ <= p["stop"]):
                continue
            if not fillable(P, i, s, "sell"):
                bk.pending.append({"side": "sell", "sym": s, "reason": "STOP"})
                continue
            px = float(o_) if o_ <= p["stop"] else p["stop"]
            bk.pos.pop(s)
            bk.cash += p["qty"] * px * (1 - cost / 2)
            bk.trades.append({"sym": s, "entry_i": p["entry_i"], "exit_i": i, "entry": p["entry"], "exit": px,
                              "qty": p["qty"], "reason": "STOP"})
            bk.cooldown[s] = i
        # 3) mark to close (A1: flagged prints are NOT dropped from valuation)
        for s, p in bk.pos.items():
            c = P.C.at[t, s]
            if pd.notna(c):
                if P.bad.at[t, s]:
                    bk.log.append((t, s, "ALERT_GT40", float(c / p["last"] - 1), float(p["qty"] * (c - p["last"]))))
                p["last"] = float(c)
        E = bk.value()
        bk.equity.append((t, E, bk.cash))
        if i == len(dates) - 1 and not live:
            break                                              # backtest: final close values only (A7); live: decide
        # 4) decisions on close t -> frozen orders for t+1
        exits = strategy.daily_exits(bk, i, t)
        sells, buys = strategy.decide(bk, i, t)
        names = {o["sym"] for o in bk.pending}
        for s, r in exits + sells:
            if s not in names and s in bk.pos:
                bk.pending.append({"side": "sell", "sym": s, "reason": r})
                names.add(s)
        for s, stop, meta in buys:
            w = meta.pop("w", 0.10)
            c = P.C.at[t, s]
            bk.pending.append({"side": "buy", "sym": s, "stop": stop, "qty": w * E / c, "meta": meta})
    return bk
