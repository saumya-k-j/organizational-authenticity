#!/usr/bin/env python3
"""Part 2 step 3 — analyze collected proxies into the structured dataset + trend tables.

  python scripts/p2_analyze.py                  # all collected, with LLM tagging
  python scripts/p2_analyze.py AAPL JPM XOM     # a slice
  python scripts/p2_analyze.py --no-llm AAPL    # classical only (no API key needed)

Outputs land in data/part2/output/. LLM tagging needs ANTHROPIC_API_KEY in .env.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.disclosure.analyze import analyze  # noqa: E402


def main() -> None:
    argv = sys.argv[1:]
    do_llm = "--no-llm" not in argv
    tickers = [a for a in argv if not a.startswith("--")] or None

    df = analyze(tickers, do_llm=do_llm)
    cols = ["ticker", "meeting_year", "n_words", "net_tone", "flesch_reading_ease",
            "sim_to_prev", "dominant_theme_classical"]
    if do_llm:
        cols += ["llm_dominant_theme", "llm_stakeholder_orientation"]
    print(df[cols].to_string(index=False))
    print("-" * 70)
    print(f"{len(df)} company-years -> data/part2/output/part2_disclosure_metrics.csv")
    print("aggregates: part2_theme_trends_by_year.csv, part2_theme_by_sector.csv, "
          "part2_distinctive_terms.csv")


if __name__ == "__main__":
    main()
