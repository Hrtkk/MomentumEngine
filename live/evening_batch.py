"""Schedule 1 — evening batch (20:30 IST, Mon–Fri). Deterministic; no judgement calls.

  1. C0 (current live rules, src/engine.py): fetch NSE files, run the EOD batch for every unprocessed session.
  2. E2 books (M11, M10, M2): incremental point-in-time update, rebuild panels, re-simulate from LIVE_START, append ledgers.
  3. Codex challenge of every new buy order across books (best-effort; never changes rule outputs).
  4. Market-stats workbook reports/market_stats.xlsx (best-effort; reads data only).
  5. git commit in this project repo (never pushed).
Writes live/ledgers/evening_<date>.json and prints it. Exit code 1 on a hard failure.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ME = HERE.parent
REPO = ME                                   # project root = its own git repo
PY = str(REPO / ".venv" / "bin" / "python")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def sh(args, cwd, timeout=1800, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r.stdout


def c0_batch(today: dt.date) -> dict:
    sh([PY, "src/fetch.py", "--asof", today.isoformat(), "--history"], ME)
    st = ME / "ledgers" / "state.json"
    last_t = json.loads(st.read_text())["last_t"] if st.exists() else None
    sessions = sorted(p.stem for p in (ME / "data" / "raw" / "bhav").glob("*.csv"))
    todo = [s for s in sessions if last_t is None or s > last_t]
    for t in todo:
        sh([PY, "src/engine.py", "--signal", t], ME)
    return {"c0_processed": todo, "c0_last": todo[-1] if todo else last_t}


def codex_challenge(sig: str, summary: dict) -> str:
    buys = {k: v["buys_next_open"][:10] for k, v in summary["books"].items() if v["buys_next_open"]}
    if not buys:
        return "no new buys"
    out = ME / "live" / "codex" / f"challenge_{sig}.json"
    out.parent.mkdir(exist_ok=True)
    prompt = (ME / "live" / "codex_prompt.md").read_text().replace("{T}", sig).replace("{BUYS}", json.dumps(buys))
    try:
        r = subprocess.run(["codex", "exec", "-s", "workspace-write", "-c", "sandbox_workspace_write.network_access=true",
                            "--skip-git-repo-check", "-C", str(REPO), prompt], cwd=REPO, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=1200)
        tail = (r.stdout + r.stderr)[-400:]
        return "ok" if out.exists() else f"no output ({'usage limit' if 'usage limit' in tail else 'rc=' + str(r.returncode)})"
    except Exception as e:
        return f"skipped: {e}"


def main() -> int:
    today = dt.datetime.now(IST).date()
    rep = {"run_at": dt.datetime.now(IST).isoformat(timespec="seconds"), "date": today.isoformat(), "steps": {}}
    ok = True
    try:
        rep["steps"]["c0"] = c0_batch(today)
    except Exception as e:
        rep["steps"]["c0"] = {"error": str(e)[-1500:]}
        ok = False
    try:
        sys.path.insert(0, str(ME / "experiments"))
        import fetch_pit
        rep["steps"]["pit_update"] = fetch_pit.update(today.isoformat())
        sys.path.insert(0, str(HERE))
        import live_books
        s = live_books.run(rebuild=True)
        rep["steps"]["books"] = s
        sig = s.get("last_session")
        rep["steps"]["codex"] = codex_challenge(sig, s) if s.get("books") else "skipped"
    except Exception as e:
        rep["steps"]["books"] = {"error": str(e)[-1500:]}
        ok = False
    try:                                         # descriptive stats only; a failure here never fails the batch
        import market_workbook
        rep["steps"]["workbook"] = market_workbook.build()
    except Exception as e:
        rep["steps"]["workbook"] = f"skipped: {str(e)[-500:]}"
    rep["ok"] = ok
    (HERE / "ledgers").mkdir(exist_ok=True)
    (HERE / "ledgers" / f"evening_{today}.json").write_text(json.dumps(rep, indent=1, default=str))
    try:                                         # commit last, so the run log itself is versioned
        sh(["git", "add", "-A"], REPO)
        out = sh(["git", "commit", "-m", f"evening batch {today}"], REPO, check=False)
        rep["steps"]["git"] = "nothing to commit" if "nothing to commit" in out else "committed"
    except Exception as e:
        rep["steps"]["git"] = f"error: {e}"
    print(json.dumps(rep, indent=1, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
