#!/usr/bin/env python3
"""Step B — build data/coverage_grid.csv (companies x years 2016-2024).

Each cell is 'filled' or a reason code (no_capture / host_wrong / timeout /
not_yet_checked). redirect / broken_snapshot are assigned later by the Step-E
agent as it inspects individual snapshots. Reuses cached discovery/coverage
queries — gentle.

  python scripts/build_grid.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.pipeline import build_coverage_grid  # noqa: E402


def main() -> None:
    df = build_coverage_grid()
    years = [c for c in df.columns if c.isdigit()]
    total = len(df) * len(years)
    filled = int((df[years] == "filled").sum().sum())
    from collections import Counter
    reasons = Counter(
        v for y in years for v in df[y] if v != "filled"
    )
    print(df[["ticker", "tier", "years_covered", "chosen_url"]].to_string(index=False))
    print("\n" + "-" * 60)
    print(f"grid cells: {filled}/{total} filled  ({100*filled/total:.0f}%)")
    print(f"missing-cell reasons: {dict(reasons)}")
    print("wrote data/coverage_grid.csv")


if __name__ == "__main__":
    main()
