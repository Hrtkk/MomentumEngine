"""Wide (date x symbol) indicator panels for experiment E1. Pure functions of past data at each row."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "experiments" / "data"


def wilder(x: pd.DataFrame, n: int) -> pd.DataFrame:
    # recursive Wilder smoothing; ewm(alpha=1/n, adjust=False) seeded at first value (seed effect fades within ~5n rows)
    return x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def pct_rank(x: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    """Row-wise 100*(avg_rank-1)/(n-1) among masked cells, higher raw = higher pct; n==1 -> 50."""
    v = x.where(mask)
    r = v.rank(axis=1, method="average")
    n = v.notna().sum(axis=1)
    out = 100 * (r.sub(1)).div((n - 1).replace(0, np.nan), axis=0)
    return out.where(~((n == 1).values[:, None] & v.notna().values), 50.0)


@dataclass
class Panels:
    O: pd.DataFrame
    H: pd.DataFrame
    L: pd.DataFrame
    C: pd.DataFrame
    V: pd.DataFrame
    n5: pd.Series
    industry: pd.Series
    deliv: pd.DataFrame | None = None
    nominal: pd.DataFrame | None = None

    def __post_init__(self):
        C, H, L, V = self.C, self.H, self.L, self.V
        self.ret1 = C / C.shift(1) - 1
        self.bad = self.ret1.abs() > 0.40                       # A1: data alert — affects signals only, from close t
        self.sma10, self.sma20 = C.rolling(10).mean(), C.rolling(20).mean()
        self.sma50, self.sma200 = C.rolling(50).mean(), C.rolling(200).mean()
        pc = C.shift(1)
        tr = np.fmax(np.fmax(H - L, (H - pc).abs()), (L - pc).abs())
        self.atr20 = wilder(tr, 20)
        d = C.diff()
        g, l = wilder(d.clip(lower=0), 14), wilder((-d).clip(lower=0), 14)
        rs = g / l
        self.rsi = (100 - 100 / (1 + rs)).where(l > 0, 100.0).where(~((g == 0) & (l == 0)), 50.0)
        self.R3, self.R6, self.R12 = C / C.shift(63) - 1, C / C.shift(126) - 1, C / C.shift(252) - 1
        self.R12_1 = C.shift(21) / C.shift(252) - 1
        self.R21 = C / C.shift(21) - 1
        lr_all = np.log(C / C.shift(1))
        self.vol126 = lr_all.rolling(126, min_periods=126).std() * np.sqrt(252)      # A7: exactly 126, ddof=1
        self.VAM6 = (self.R6 / self.vol126).where(self.vol126 > 0)
        self.medV20 = V.rolling(20).median().shift(1)
        self.medVal20 = (C * V).rolling(20).median().shift(1)
        self.n_prior = C.notna().cumsum().shift(1).fillna(0)
        self.hi55 = H.shift(1).rolling(55).max()
        self.hi252 = H.shift(1).rolling(252).max()
        badwin = self.bad.astype(float).rolling(253, min_periods=1).max().fillna(0).astype(bool)   # no signals through a bad print in lookback
        nom = self.nominal if self.nominal is not None else C
        self.eligible = ((self.n_prior >= 252) & (nom >= 50) & (self.medVal20 >= 1e8) & C.notna() & ~badwin)
        el = self.eligible
        self.blend = (0.35 * pct_rank(self.R3, el) + 0.30 * pct_rank(self.R6, el)
                      + 0.20 * pct_rank(self.R12_1, el) + 0.15 * pct_rank(self.VAM6, el)).where(el)
        self.n5_sma200 = self.n5.rolling(200).mean()

    def rank_of(self, score: pd.DataFrame, t) -> pd.Series:
        """Rank 1 = best among eligible on t; ties by symbol."""
        s = score.loc[t].where(self.eligible.loc[t]).dropna()
        s = s.sort_index()
        return s.rank(ascending=False, method="first").astype(int)


def load() -> Panels:
    h = pd.read_parquet(D / "yahoo_7y.parquet")
    def wide(col):
        return h.pivot_table(index="date", columns="symbol", values=col)
    O, H, L, C, V = (wide(c) for c in ("open", "high", "low", "close", "volume"))
    keep = C.notna().sum(axis=1) > 100                           # drop sparse/holiday rows
    O, H, L, C, V = (x.loc[keep] for x in (O, H, L, C, V))
    ix = pd.read_parquet(D / "nifty500_index.parquet").set_index("date")["close"]
    n5 = ix.reindex(C.index).ffill()
    memb = pd.read_csv(sorted((ROOT / "data" / "membership").glob("*_nifty500.csv"))[-1])
    industry = memb.set_index("Symbol")["Industry"]
    deliv = None
    dp = D / "delivery.parquet"
    if dp.exists():
        dl = pd.read_parquet(dp)
        deliv = dl.pivot_table(index="date", columns="symbol", values="deliv").reindex(index=C.index, columns=C.columns)
    nominal = C.copy()
    sp = D / "splits.parquet"
    if sp.exists():                                              # A2: nominal = adjusted x prod(split ratios after t)
        spl = pd.read_parquet(sp)
        for s, g in spl.groupby("symbol"):
            if s not in nominal.columns:
                continue
            f = pd.Series(1.0, index=C.index)
            for d, r in zip(g["date"], g["ratio"]):
                f[C.index < d] *= r
            nominal[s] = C[s] * f
    return Panels(O, H, L, C, V, n5, industry, deliv, nominal)
