"""10:00 IST weekday runner (STRATEGY.md v0.2 F4).

1. Fetch inputs up to the latest published session (yesterday's bhavcopy).
2. Run the official EOD batch for every unprocessed session in order (finalises fills/stops/equity, then signals).
3. Codex challenge of the resulting picks (best-effort; the rule output never depends on it).
4. PROVISIONAL simulation of the frozen orders at today's open (Yahoo), display only — replaced by the
   official bhavcopy open in tomorrow's batch.
5. Build the report.
Prints the report path on the last line.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
sys.path.insert(0, str(ROOT / "src"))


def sh(args: list[str], timeout: int = 900, check: bool = True) -> str:
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise SystemExit(f"FAILED {' '.join(args)}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def provisional_open(symbols: list[str], today: dt.date) -> dict:
    import yfinance as yf
    out = {}
    if not symbols:
        return out
    df = yf.download([f"{s}.NS" for s in symbols], period="5d", interval="1d", auto_adjust=False,
                     group_by="ticker", progress=False)
    for s in symbols:
        try:
            sub = df[f"{s}.NS"].dropna(how="all")
            sub.index = pd.to_datetime(sub.index).tz_localize(None).normalize()
            if pd.Timestamp(today) in sub.index:
                out[s] = float(sub.loc[pd.Timestamp(today), "Open"])
        except Exception:
            pass
    return out


def codex_challenge(t: str) -> None:
    sh([PY, "-c", f"import sys; sys.path.insert(0,'src'); import export_picks; export_picks.run('{t}')"])
    prompt = (ROOT / "config" / "codex_challenge_prompt.md").read_text().replace("{T}", t)
    try:
        subprocess.run(["codex", "exec", "-s", "workspace-write", "-c", "sandbox_workspace_write.network_access=true",
                        "--skip-git-repo-check", "-C", str(ROOT.parent), prompt],
                       cwd=ROOT.parent, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
    except Exception as e:  # never block the run
        print(f"codex challenge skipped: {e}")


def main() -> None:
    today = dt.datetime.now(IST).date()
    if today.weekday() >= 5:
        print("weekend — nothing to do")
        return
    print(sh([PY, "src/fetch.py", "--asof", today.isoformat(), "--history"]))
    state_f = ROOT / "ledgers" / "state.json"
    last_t = json.loads(state_f.read_text())["last_t"] if state_f.exists() else None
    sessions = sorted(p.stem for p in (ROOT / "data" / "raw" / "bhav").glob("*.csv") if p.stem < today.isoformat())
    todo = [s for s in sessions if last_t is None or s > last_t]
    if last_t is None:
        todo = todo[-1:]                                  # fresh start: begin at the latest session only
    for t in todo:
        print(sh([PY, "src/engine.py", "--signal", t]))
    t = todo[-1] if todo else last_t
    if todo:
        codex_challenge(t)
    run = json.loads((ROOT / "ledgers" / f"run_{t}.json").read_text())
    syms = sorted({o["symbol"] for o in run["orders"]})
    prov = provisional_open(syms, today)
    pf = ROOT / "data" / f"provisional_{today}.json"
    pf.write_text(json.dumps(prov, indent=1))
    if syms and not prov:
        print("no opening prices for today — market holiday or data not yet available")
    print(sh([PY, "src/summary_csv.py", t, today.isoformat()]).strip())
    print(sh([PY, "src/report.py", "--signal", t, "--run-date", today.isoformat(), "--provisional", str(pf)]).strip())


if __name__ == "__main__":
    main()
