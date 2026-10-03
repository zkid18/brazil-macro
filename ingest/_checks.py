"""_checks.py — internal-gap check for bronze series.

A gap is the distance between two CONSECUTIVE observations of one series (per entity).
Thresholds (weekends/holidays are fine for daily; leading/trailing edges are not gaps):
    daily > 30 days · weekly > 21 days · monthly > 2 months · quarterly > 6 months
    annual > 2 years · event: not checked

Adapters call check_gaps(df, metric_id, freq) after writing; it prints a [FAIL] line per
gap and returns False so main() can exit non-zero.

Run (scan every bronze file, exit 1 on any gap):
    .venv/bin/python ingest/_checks.py [warehouse/bronze/native ...]
"""
from __future__ import annotations
import sys, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
# freq -> (max allowed step, unit) ; months measured as calendar-month index difference
LIMITS = {"daily": (30, "days"), "weekly": (21, "days"), "monthly": (2, "months"),
          "quarterly": (6, "months"), "annual": (24, "months")}


def find_gaps(dates, freq: str) -> list[tuple[str, str, int]]:
    """Return [(prev_date, next_date, step)] for steps above the freq limit."""
    if freq not in LIMITS:
        return []
    lim, unit = LIMITS[freq]
    d = pd.Series(pd.to_datetime(pd.Series(dates).unique())).sort_values().reset_index(drop=True)
    if len(d) < 2:
        return []
    if unit == "days":
        step = d.diff().dt.days
    else:
        mi = d.dt.year * 12 + d.dt.month
        step = mi.diff()
    bad = step[step > lim].index
    return [(d[i - 1].strftime("%Y-%m-%d"), d[i].strftime("%Y-%m-%d"), int(step[i])) for i in bad]


def check_gaps(df: pd.DataFrame, metric_id: str, freq: str | None = None, quiet: bool = False) -> bool:
    """True if no internal gaps. Prints one [FAIL] line per gap."""
    freq = freq or df["freq"].iloc[0]
    groups = df.groupby("entity_id") if "entity_id" in df.columns else [(None, df)]
    ok = True
    for ent, g in groups:
        gaps = find_gaps(g["date"], freq)
        if gaps:
            ok = False
            unit = LIMITS[freq][1]
            for a, b, s in gaps:
                tag = f"{metric_id}[{ent}]" if ent is not None else metric_id
                print(f"[FAIL] gap {tag:<34} {freq:<9} {a} -> {b} ({s} {unit})")
    if ok and not quiet:
        print(f"[gap-ok] {metric_id}")
    return ok


def scan(dirs) -> int:
    nfail = nfiles = 0
    for d in dirs:
        for p in sorted(pathlib.Path(d).glob("*.csv")):
            df = pd.read_csv(p, dtype={"date": str})
            if df.empty or "freq" not in df.columns:
                continue
            nfiles += 1
            for freq, g in df.groupby("freq"):
                nfail += not check_gaps(g, p.stem, freq, quiet=True)
    print(f"[gap-scan] {nfiles} files, {nfail} with internal gaps")
    return nfail


if __name__ == "__main__":
    dirs = sys.argv[1:] or [ROOT / "warehouse" / "bronze" / "native"]
    sys.exit(1 if scan(dirs) else 0)
