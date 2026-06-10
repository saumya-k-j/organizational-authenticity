#!/usr/bin/env python3
"""(d) Part 1 deliverable — fetch + clean + change-detect + theme-tag filled cells.

  # scrape/clean only (free, no LLM) — used to bootstrap the taxonomy
  python scripts/extract_part1.py --tickers MSFT,CVX,JPM,JNJ,MCD --no-tagging

  # full slice incl. tagging (needs ANTHROPIC_API_KEY + a FROZEN taxonomy)
  python scripts/extract_part1.py --tickers MSFT,CVX,JPM

  # everything
  python scripts/extract_part1.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.pipeline import extract_and_tag  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="Comma-separated tickers (default: all filled)")
    ap.add_argument("--no-tagging", action="store_true", help="Scrape+clean only, no LLM")
    args = ap.parse_args()
    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else None

    df = extract_and_tag(tickers=tickers, do_tagging=not args.no_tagging)
    if df.empty:
        print("No rows produced.")
        return

    cols = ["ticker", "year", "changed_from_prior", "theme_categories"]
    show = df.copy()
    show["theme_categories"] = show["theme_categories"].str.slice(0, 50)
    print(show[cols].to_string(index=False))
    print(f"\n{len(df)} rows -> data/output/part1_stated_values.csv  "
          f"({df['theme_categories'].astype(bool).sum()} tagged)")


if __name__ == "__main__":
    main()
