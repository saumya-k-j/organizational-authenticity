#!/usr/bin/env python3
"""Part 2 step 2 — build the coverage grid from the persisted manifest (no network).

  python scripts/p2_coverage.py                # all collected companies
  python scripts/p2_coverage.py AAPL JPM XOM   # a slice

Writes data/part2/output/part2_coverage_grid.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.disclosure.coverage import build_coverage_grid, coverage_summary  # noqa: E402


def main() -> None:
    tickers = sys.argv[1:] or None
    df = build_coverage_grid(tickers)
    years = [c for c in df.columns if c.isdigit()]
    print(df[["ticker", "sector", "cik", "years_covered", "collisions"] + years].to_string(index=False))
    print("-" * 70)
    s = coverage_summary(df)
    print(f"coverage: {s['filled']}/{s['cells']} cells ({s['pct']}%)  "
          f"gaps={s['gap_reasons']}  collisions_flagged={s['collisions']}")
    print("wrote data/part2/output/part2_coverage_grid.csv")


if __name__ == "__main__":
    main()
