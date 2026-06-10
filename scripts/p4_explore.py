#!/usr/bin/env python3
"""Part 4 (exploratory) — do companies over-claim more on sector-EXPECTED values?

  python scripts/p4_explore.py                      # all sectors
  python scripts/p4_explore.py Energy Financials     # a slice of sectors

Pure computation over Parts 1-3 outputs. Writes data/part3/output/part4_*.csv.
(Sector filtering is applied after computing sector-expected themes from the full Part 1.)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from authenticity.index3.sector_conformity import (  # noqa: E402
    energy_case_study, expected_vs_nonexpected, frequency_confounder,
    refined_thesis, sector_expected_themes,
)


def main() -> None:
    sectors = sys.argv[1:] or None
    # Sector-expected themes are always computed from ALL companies; we only restrict the
    # REPORTING (and the over-claim tables) to the requested sectors via their tickers.
    expected = sector_expected_themes()
    tickers = None
    if sectors:
        p1 = pd.read_csv("data/output/part1_stated_values.csv")
        tickers = sorted(p1[p1.sector.isin(sectors)].ticker.unique().tolist())

    print("=== sector-expected themes (>=60% of a sector's companies profess it) ===")
    for s in (sectors or sorted(expected)):
        print(f"  {s:24s}: {', '.join(sorted(expected.get(s, set()))) or '(none)'}")

    per_company, by_sector, controls = expected_vs_nonexpected(tickers)
    print("\n=== over-claiming: EXPECTED vs NON-EXPECTED themes, by sector ===")
    print("(per-theme mean over-claim; gap>0 => over-claims more on expected themes)")
    print(by_sector[["sector", "n_companies", "mean_over_expected",
                     "mean_over_nonexpected", "mean_gap"]].to_string(index=False))
    overall = per_company["gap"].mean()
    pos = (per_company["gap"] > 0).mean()
    print(f"\n  ACROSS COMPANIES: mean gap = {overall:+.4f}  |  "
          f"{pos*100:.0f}% of companies have gap>0 (n={len(per_company)})")

    print("\n=== ENERGY case study: themes ranked by mean over-claim ===")
    rank = energy_case_study(tickers)
    if not rank.empty:
        print(rank[["rank", "theme", "mean_over_claim"]].to_string(index=False))
        env = rank[rank.theme == "environmental_stewardship"]
        if not env.empty:
            print(f"  -> environmental_stewardship ranks #{int(env['rank'].iloc[0])} of {len(rank)} "
                  f"over-claimed themes for Energy")

    print("\n=== CONTROL: trendiness vs sector-conformity (per theme) ===")
    print("(over-claim where theme is sector-expected vs where it isn't; positive = conformity)")
    print(controls.to_string(index=False))

    print("\n=== REFINED THESIS: soft/image vs costly/material expected themes ===")
    print("(proxy frequency = stand-in for material/enforced; over-claim-where-expected)")
    tbl, sp = refined_thesis(tickers)
    print(tbl.to_string(index=False))
    print(f"  Spearman(over_where_expected, proxy_freq) = {sp}  "
          f"(strong negative => soft/rare themes over-claimed most; also the entanglement caveat)")

    print("\n=== CONTROL: frequency confounder ===")
    print(" ", frequency_confounder(tickers))
    print("\nwrote part4_*.csv (by_sector, per_company, theme_controls, energy_case, refined_thesis)")


if __name__ == "__main__":
    main()
