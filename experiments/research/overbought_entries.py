"""Research step 2026-10-09 — do "overbought-looking" entries of M11 / M2 do worse? Development data only (2013–2020).

Pre-registered before looking (owner question of 2026-10-09, after seeing RSI > 70, MACD cross-down, fading volume and
expanding Bollinger bands on CUPID, IOLCP, TFCILTD):

  H1  Entries whose signal-day RSI14 > 70 earn a lower realised trade return than entries with RSI14 <= 70.
  H2  Entries where the MACD line is below its signal line (12/26/9 EMA) on the signal day earn less.
  H3  Entries where volume is fading (mean of the last 5 sessions < mean of the 20 before) earn less.
  H4  Entries where the Bollinger band width (20, 2 sigma) is wider than 5 sessions earlier earn less.
  H5  Entries with all four readings together earn less.

Unit of analysis: every trade the frozen rule actually took in 2013–2020 (strategy/data/backtest_<ID>_trades.csv), i.e. the
rule's own entries, not hypothetical ones. Outcome: realised trade return (exit/entry − 1, before costs) and the 20- and
60-session close after the entry open. A difference "counts" if its 90% bootstrap interval excludes zero (5,000 resamples,
seed 20261009). Holdout (2021 → 2026-10-07) is printed for information only — it is spent data.

  .venv/bin/python experiments/research/overbought_entries.py   ->  reviews/research_2026-10-09_overbought_entries.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
import pit_panels  # noqa: E402

DEV = (pd.Timestamp("2013-01-01"), pd.Timestamp("2020-12-31"))
HOLD = (pd.Timestamp("2021-01-01"), pd.Timestamp("2026-10-07"))
RNG = np.random.default_rng(20261009)


def indicators(P):
    C, V = P.C, P.V
    e12, e26 = C.ewm(span=12, adjust=False).mean(), C.ewm(span=26, adjust=False).mean()
    macd = e12 - e26
    sig = macd.ewm(span=9, adjust=False).mean()
    hist = macd - sig
    sma20, sd20 = C.rolling(20).mean(), C.rolling(20).std()
    bw = (4 * sd20) / sma20
    v5, v20 = V.rolling(5).mean(), V.shift(5).rolling(20).mean()
    return {"rsi_gt70": P.rsi > 70, "macd_below_signal": macd < sig, "macd_hist_falling": hist < hist.shift(1),
            "volume_fading": v5 < v20, "bb_expanding": bw > bw.shift(5), "stretched_10pct_above_sma20": C / sma20 - 1 > 0.10}


def ci(a: np.ndarray, b: np.ndarray, n: int = 5000) -> tuple[float, float]:
    d = [RNG.choice(a, len(a)).mean() - RNG.choice(b, len(b)).mean() for _ in range(n)]
    return float(np.percentile(d, 5)), float(np.percentile(d, 95))


def study(P, k: str, lo, hi, ind: dict) -> tuple[pd.DataFrame, int]:
    tr = pd.read_csv(ROOT / "strategy" / "data" / f"backtest_{k}_trades.csv")
    tr["signal"] = pd.to_datetime(tr["signal_date"])
    tr = tr[(tr["signal"] >= lo) & (tr["signal"] <= hi)].copy()
    dates = P.C.index
    tr["ret"] = tr["exit"] / tr["entry"] - 1
    for h in (20, 60):
        out = []
        for r in tr.itertuples():
            j = min(r.entry_i + h, len(dates) - 1)
            c = P.C.at[dates[j], r.sym]
            out.append(c / r.entry - 1 if pd.notna(c) else np.nan)
        tr[f"fwd{h}"] = out
    for name, panel in ind.items():
        tr[name] = [bool(panel.at[d, s]) if pd.notna(panel.at[d, s]) else False for d, s in zip(tr["signal"], tr["sym"])]
    tr["all_four"] = tr["rsi_gt70"] & tr["macd_below_signal"] & tr["volume_fading"] & tr["bb_expanding"]
    rows = []
    for name in list(ind) + ["all_four"]:
        a, b = tr[tr[name]], tr[~tr[name]]
        if len(a) < 10 or len(b) < 10:
            rows.append({"flag": name, "n_flag": len(a), "n_other": len(b)})
            continue
        lo90, hi90 = ci(a["ret"].values, b["ret"].values)
        rows.append({"flag": name, "n_flag": len(a), "n_other": len(b),
                     "mean_ret_flag": a["ret"].mean(), "mean_ret_other": b["ret"].mean(),
                     "median_flag": a["ret"].median(), "median_other": b["ret"].median(),
                     "win_flag": (a["ret"] > 0).mean(), "win_other": (b["ret"] > 0).mean(),
                     "diff_mean": a["ret"].mean() - b["ret"].mean(), "ci90_lo": lo90, "ci90_hi": hi90,
                     "fwd20_flag": a["fwd20"].mean(), "fwd20_other": b["fwd20"].mean(),
                     "fwd60_flag": a["fwd60"].mean(), "fwd60_other": b["fwd60"].mean()})
    return pd.DataFrame(rows), len(tr)


def md_table(df: pd.DataFrame) -> str:
    f = lambda v: "—" if pd.isna(v) else f"{v * 100:+.1f}%"
    g = lambda v: "—" if pd.isna(v) else f"{v * 100:.0f}%"
    out = ["| Reading on the signal day | n with / without | Mean trade return with / without | Median | Win rate | Difference (90% CI) | 20-session fwd | 60-session fwd | Verdict |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        if pd.isna(getattr(r, "diff_mean", np.nan)):
            out.append(f"| {r.flag} | {r.n_flag} / {r.n_other} | too few | | | | | | — |")
            continue
        verdict = ("**worse**" if r.ci90_hi < 0 else "**better**" if r.ci90_lo > 0 else "no difference")
        out.append(f"| {r.flag} | {r.n_flag} / {r.n_other} | {f(r.mean_ret_flag)} / {f(r.mean_ret_other)} | {f(r.median_flag)} / {f(r.median_other)} | "
                   f"{g(r.win_flag)} / {g(r.win_other)} | {f(r.diff_mean)} [{f(r.ci90_lo)}, {f(r.ci90_hi)}] | {f(r.fwd20_flag)} / {f(r.fwd20_other)} | "
                   f"{f(r.fwd60_flag)} / {f(r.fwd60_other)} | {verdict} |")
    return "\n".join(out)


def main() -> None:
    P = pit_panels.build(cache=True)
    ind = indicators(P)
    parts = ["# Research 2026-10-09 — do overbought-looking entries do worse? (development data, pre-registered)", "",
             "**Question (owner, 2026-10-09):** the first M11/M2 fills (CUPID, IOLCP, TFCILTD …) show RSI14 > 70, the MACD line crossing "
             "below its signal, fading volume and expanding Bollinger bands. Does the rule buy names that are losing strength, and do such entries do worse?", "",
             "**Method:** every entry the frozen rule took on the point-in-time universe, split by the reading on the signal day. Outcome = the trade's "
             "realised return (exit ÷ entry − 1, gross) plus the 20- and 60-session close after entry. A reading *matters* only if the 90% bootstrap "
             "interval of the mean difference excludes zero. Hypotheses H1–H5 and the method were written before the numbers were computed "
             "(`experiments/research/overbought_entries.py`). 14 strategies were tried in E2; this note tests 6 readings × 2 books, which is 12 more looks.", "",
             "Indicators: RSI14 (Wilder), MACD 12/26/9 on closes, volume fading = mean(V, last 5) < mean(V, previous 20), Bollinger width = 4·σ20/SMA20 vs 5 sessions earlier, "
             "stretched = close > 1.10 × SMA20. All computed on corporate-action-adjusted closes.", ""]
    for k in ("M11", "M2"):
        if not (ROOT / "strategy" / "data" / f"backtest_{k}_trades.csv").exists():
            parts.append(f"## {k}\n\n— backtest trades not available (run `strategy/backtest.py {k}`).\n")
            continue
        d, n = study(P, k, *DEV, ind)
        parts += [f"## {k} — development 2013–2020 ({n} entries)", "", md_table(d), ""]
        h, nh = study(P, k, *HOLD, ind)
        parts += [f"### {k} — holdout 2021 → 2026-10-07 ({nh} entries) — information only, spent data", "", md_table(h), ""]
    parts += ["## Reading the result", "",
              "- A row marked **worse** means: on development data, entries with that reading earned less, and the interval excludes zero. "
              "That is a hypothesis for a *shadow* variant (an entry veto), not a change to the live rule.",
              "- A row marked *no difference* means the reading carried no information about the trade's outcome, in this sample.",
              "- Win rates near 35–40% are the rule's normal state; the return comes from a few large winners, so medians are negative even when means are positive.",
              "- Context from E2: the tier-4 extension veto (M9: skip if day return > 5%, close > 1.10·SMA20 or RSI14 > 75, on the 3-month rule) "
              "failed development (2 of 4 blocks) and in the holdout earned +13.7% excess vs +20.9% without the veto (`results_e2/holdout_metrics.csv`).", "",
              "Sources: `strategy/data/backtest_<ID>_trades.csv` (regenerated 2026-10-09 with the frozen E2 engine), `experiments/data/pit/`."]
    out = ROOT / "reviews" / "research_2026-10-09_overbought_entries.md"
    out.write_text("\n".join(parts))
    print(out)


if __name__ == "__main__":
    main()
