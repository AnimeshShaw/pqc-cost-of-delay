"""
Reproduce every result, figure and table in this repository with one command.

    python scripts/reproduce.py              # full pipeline (about 2-4 minutes)
    python scripts/reproduce.py --quick      # tests and numerical validation only
    python scripts/reproduce.py --no-node    # skip the JavaScript parity check

Steps, in order:
  1. unit and property tests          (pytest)
  2. numerical validation             (Monte Carlo and quadrature cross-checks)
  3. statistical analysis             -> results/results.json, results/*.csv, results/summary.md
  4. parameter tables                 -> methodology/PARAMETERS_BY_ASSET.md
  5. case-study and worked tables     -> results/case_study_tables.md, results/worked_examples_report.txt
  6. figures                          -> paper/figures/*.pdf, paper/figures/*.png
  7. web-app data                     -> app/data.js, app/golden.json
  8. JavaScript parity check          (node app/test.js)

Everything is deterministic (fixed seeds). After a run, `git diff --stat results/`
should show no change, or last-digit differences if library versions differ.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(label: str, cmd: list[str], stdout_to: Path | None = None) -> bool:
    t0 = time.time()
    print(f"\n=== {label}")
    print("    $", " ".join(cmd))
    try:
        if stdout_to is not None:
            with open(stdout_to, "w", encoding="utf-8") as fh:
                proc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            err = proc.stderr
        else:
            proc = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8",
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out = proc.stdout.strip().splitlines()
            print("    " + "\n    ".join(out[-6:]))
            err = ""
        ok = proc.returncode == 0
    except FileNotFoundError as e:
        print(f"    SKIPPED ({e})")
        return True
    if not ok and err:
        print("    " + "\n    ".join(err.strip().splitlines()[-8:]))
    print(f"    {'ok' if ok else 'FAILED'}  ({time.time() - t0:.1f}s)")
    return ok


def main() -> int:
    quick = "--quick" in sys.argv
    use_node = "--no-node" not in sys.argv and shutil.which("node") is not None
    results = []

    results.append(("tests", run("1. tests", [PY, "-m", "pytest", "-q"])))
    results.append(("numerical validation", run("2. numerical validation", [PY, "-m", "costofdelay.validation"])))
    if not quick:
        results.append(("statistical analysis", run("3. statistical analysis", [PY, "scripts/make_results.py"])))
        results.append(("parameter tables", run("4. parameter tables", [PY, "scripts/make_parameter_tables.py"])))
        results.append(("case-study tables", run("5a. case-study tables", [PY, "scripts/make_tables.py"],
                                               stdout_to=ROOT / "results" / "case_study_tables.md")))
        results.append(("worked examples", run("5b. worked examples", [PY, "scripts/report_worked_examples.py"],
                                              stdout_to=ROOT / "results" / "worked_examples_report.txt")))
        results.append(("figures", run("6. figures", [PY, "scripts/make_figures.py"])))
        results.append(("app data", run("7. web-app data", [PY, "scripts/make_app_data.py"])))
        if use_node:
            results.append(("JS parity", run("8. JavaScript parity check", ["node", "app/test.js"])))
        else:
            print("\n=== 8. JavaScript parity check: skipped (node not found or --no-node)")

    print("\n" + "=" * 60)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL':5s} {name}")
    bad = [n for n, ok in results if not ok]
    print("=" * 60)
    if bad:
        print("FAILED:", ", ".join(bad))
        return 1
    print("All steps passed. Inspect `git diff --stat results/` for any change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
