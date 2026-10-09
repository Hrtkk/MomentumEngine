"""Backtest curves for the strategy reports: one continuous book per strategy from 2013-01-01 on the point-in-time data.

  .venv/bin/python strategy/backtest.py M11 M2 M10      # writes strategy/data/backtest_<ID>.csv and backtest_<ID>_trades.csv

Same engine and settings as E2 (`experiments/run_e2.py`: 0.6% costs, fractional shares, start 2013-01-01). The curves are
history for the report pages; the selection and verdicts remain those in experiments/results_e2/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import e2_strategies as E2  # noqa: E402
import pit_panels  # noqa: E402
import sim  # noqa: E402
from run_e1 import b2_series  # noqa: E402

OUT = ROOT / "strategy" / "data"
START = pd.Timestamp("2013-01-01")


def main(keys: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    P = pit_panels.build(cache=False)
    dates = P.C.index
    i0 = int(np.searchsorted(dates, START))
    _, b2n = b2_series(P, i0)
    b2 = (1 + b2n).cumprod()
    for k in keys:
        st = E2.ladder(P)[k]()
        bk = sim.run(st, 0.006, i0)
        eq = pd.DataFrame(bk.equity, columns=["date", "equity", "cash"]).set_index("date")
        eq["B2-net"] = b2.reindex(eq.index).ffill().values
        eq["Nifty 500"] = P.n5.reindex(eq.index).ffill().values
        eq.to_csv(OUT / f"backtest_{k}.csv")
        tr = pd.DataFrame(bk.trades)
        if len(tr):
            tr["entry_date"] = [str(dates[i].date()) for i in tr["entry_i"]]
            tr["exit_date"] = [str(dates[i].date()) for i in tr["exit_i"]]
            tr["signal_date"] = [str(dates[i - 1].date()) for i in tr["entry_i"]]
        tr.to_csv(OUT / f"backtest_{k}_trades.csv", index=False)
        print(k, f"{eq.index[0].date()} → {eq.index[-1].date()}", f"final {eq['equity'].iloc[-1] / 60000:.1f}×", len(tr), "trades", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["M11", "M2", "M10"])
