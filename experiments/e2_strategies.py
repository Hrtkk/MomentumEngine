"""E2 ladder (SPEC_E2 §4). Built on the E1 execution layer (sim.run); only decision rules differ."""
from __future__ import annotations

import pandas as pd

import sim


class E2Mixin:
    """SPEC_E2 §3 ineligibility: exit at monthly reconstitution if out of Liquid-500, or after 5 sessions without a trade."""

    def daily_exits(self, bk, i, t):
        P, out = self.P, []
        recon = i > 0 and P.C.index[i - 1].month != t.month          # first session after a month-end
        for s, p in bk.pos.items():
            if pd.isna(P.C.at[t, s]):
                p["missing"] = p.get("missing", 0) + 1
                if p["missing"] >= 5:
                    out.append((s, "NO_TRADE_5"))
                continue
            p["missing"] = 0
            if recon and not bool(P.universe.at[t, s]):
                out.append((s, "LEFT_UNIVERSE"))
        return out + self.extra_exits(bk, i, t)

    def extra_exits(self, bk, i, t):
        return []


class Ranked(E2Mixin, sim.RankStrategy):
    def __init__(self, P, score, name, monthly=False, mask=None, market_filter=False, veto=False,
                 enter=50, stay=125, stop=True):
        sim.RankStrategy.__init__(self, P, score, name, monthly)
        self.mask, self.market_filter, self.veto = mask, market_filter, veto
        self.enter, self.stay, self.use_stop = enter, stay, stop

    def rank_now(self, t):
        sc = self.score.loc[t]
        if self.mask is not None:
            sc = sc.where(self.mask.loc[t].fillna(False).astype(bool))
        s = sc.where(self.P.eligible.loc[t]).dropna().sort_index()
        return s.rank(ascending=False, method="first").astype(int)

    def decide(self, bk, i, t):
        if not self.refresh(t):
            return [], []
        P = self.P
        if self.market_filter and P.n5.loc[t] < P.n5_sma200.loc[t]:
            return [(s, "MARKET_FILTER") for s in bk.pos], []
        rk = self.rank_now(t)
        self.frozen_rank, self.frozen_score = rk, self.score.loc[t].reindex(rk.index)
        sells = [(s, f"RANK_GT_{self.stay}") for s in bk.pos if rk.get(s, 10**6) > self.stay]
        buys = []
        for s in rk[rk <= self.enter].sort_values().index:
            if s in bk.pos or not self.ok_atr(s, t):
                continue
            if self.veto and (P.ret1.at[t, s] > 0.05 or P.C.at[t, s] > 1.10 * P.sma20.at[t, s] or P.rsi.at[t, s] > 75):
                continue
            buys.append((s, self.cat_stop(s, t) if self.use_stop else 1e-6, {}))
        return sells, buys


class EventConfirm(E2Mixin, sim.S7Confirm):
    """M10: E1 S7 state machine; candidates = frozen M5 top 50."""

    def __init__(self, P):
        sim.S7Confirm.__init__(self, P)
        self.score, self.name = P.m5, "M10 gainer event + confirm"

    def extra_exits(self, bk, i, t):
        return [(s, "BELOW_T0_LOW") for s, p in bk.pos.items()
                if "t0low" in p["meta"] and pd.notna(self.P.C.at[t, s]) and self.P.C.at[t, s] < p["meta"]["t0low"]]


class Breakout52(E2Mixin, sim.RankStrategy):
    """M11: new 252-session closing high with volume >= 1.5x median20, among frozen R6 top-100; entries any day."""

    def __init__(self, P):
        sim.RankStrategy.__init__(self, P, P.R6, "M11 52W-high breakout")

    def decide(self, bk, i, t):
        P, sells = self.P, []
        if self.refresh(t):
            sells = self.rank_exits(bk, t)
        if not len(self.frozen_rank):
            return sells, []
        top = self.frozen_rank[self.frozen_rank <= 100]
        brk = (P.C.loc[t] > P.hi252.loc[t]) & (P.V.loc[t] >= 1.5 * P.medV20.loc[t])
        cand = [s for s in top.sort_values().index if bool(brk.get(s, False)) and s not in bk.pos
                and P.eligible.at[t, s] and self.ok_atr(s, t)]
        return sells, [(s, self.cat_stop(s, t), {}) for s in cand]


class Controls:
    @staticmethod
    def c0(P):
        st = sim.S0E1(P)
        st.name = "C0 current live rules (S0-E1)"
        return st

    @staticmethod
    def c1(P):
        st = Ranked(P, P.R5, "C1 short-term winners (5-day)", enter=10, stay=10, stop=False)
        st.sector_cap = None
        return st


def ladder(P) -> dict:
    lowvol = P.vol126.le(P.vol126.where(P.eligible).median(axis=1), axis=0)
    dual = (P.R6 > 0) & P.R6.gt((P.n5 / P.n5.shift(126) - 1), axis=0)
    return {
        "M1": lambda: Ranked(P, P.R3, "M1 3-month momentum"),
        "M2": lambda: Ranked(P, P.R6, "M2 6-month momentum"),
        "M3": lambda: Ranked(P, P.R12_1, "M3 12-1 momentum", monthly=True),
        "M4": lambda: Ranked(P, P.C / P.hi252, "M4 52-week-high proximity"),
        "M5": lambda: Ranked(P, P.m5, "M5 vol-adjusted momentum (NSE-style)", monthly=True),
        "M6": lambda: Ranked(P, P.R6, "M6 low-volatility momentum", mask=lowvol),
        "M7": lambda: Ranked(P, P.R3, "M7 3M momentum + market filter", market_filter=True),
        "M8": lambda: Ranked(P, P.R6, "M8 dual momentum", mask=dual),
        "M9": lambda: Ranked(P, P.R3, "M9 3M momentum + extension veto", veto=True),
        "M10": lambda: EventConfirm(P),
        "M11": lambda: Breakout52(P),
        "C0": lambda: Controls.c0(P),
        "C1": lambda: Controls.c1(P),
    }


TIER = {"M1": 1, "M2": 1, "M3": 1, "M4": 1, "M5": 2, "M6": 2, "M7": 3, "M8": 3, "M9": 4, "M10": 5, "M11": 5,
        "C0": 0, "C1": 0}
