"""Summarise tests/error_table.csv for the demo. Owner: Pair C.

Fill one row per measurement made in the app (set units to "decimal inches"):
    photo, target, true_in (tape), app_in (app reading), app_pm_in (the ± shown, inches), grade, notes
    python tools/error_summary.py
"""
import csv
from pathlib import Path
from statistics import median

rows = list(csv.DictReader(open(Path(__file__).resolve().parents[1] / "tests" / "error_table.csv")))
print(f"{'photo':<22}{'target':<22}{'tape':>8}{'app':>8}{'error':>9}{'err %':>7}  in ±?  grade")
errs = []
for r in rows:
    t, a = float(r["true_in"]), float(r["app_in"])
    e = a - t
    pm = float(r["app_pm_in"]) if r.get("app_pm_in") else None
    inside = "" if pm is None else ("yes" if abs(e) <= 2 * pm else "NO")
    errs.append(abs(e))
    print(f"{r['photo']:<22}{r['target']:<22}{t:8.3f}{a:8.3f}{e:+9.3f}{100 * e / t:+6.1f}%  {inside:<5}  {r['grade']}")
if errs:
    print(f"\n{len(errs)} measurements: median |error| {median(errs):.3f}\" "
          f"({median(errs) * 16:.1f}/16\"), worst {max(errs):.3f}\"")
