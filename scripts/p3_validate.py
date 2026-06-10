#!/usr/bin/env python3
"""Part 3 step 2 — validity checks.

  python scripts/p3_validate.py                    # all scored companies
  python scripts/p3_validate.py MSFT JPM XOM MCD   # a slice

(1) contested-proxy cluster (free); (2) diversity hard-facts (LLM board-diversity
extraction; needs ANTHROPIC_API_KEY). Run scripts/p3_index.py first.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.index3.index import compute_index  # noqa: E402
from authenticity.index3.validate import (  # noqa: E402
    contested_cluster, diversity_correlations, diversity_hard_facts,
)


def main() -> None:
    tickers = sys.argv[1:] or None
    idx = compute_index(tickers)

    print("=== (1) contested-proxy cluster: where do contested years rank? ===")
    print(contested_cluster(idx).to_string(index=False))

    print("\n=== (2) diversity hard-facts: website D&I emphasis vs real board diversity ===")
    try:
        div = diversity_hard_facts(tickers)
        print(div.to_string(index=False))
        print("\ncorrelations:", diversity_correlations(div))
    except Exception as e:
        print(f"[blocked] board-diversity extraction needs the Anthropic API and could not "
              f"run: {e!r}\nThe extractor is implemented + cache-backed; re-run this script "
              f"once API credits are available.")
    print("\nwrote part3_validity_contested.csv (+ part3_validity_diversity.csv if (2) ran)")


if __name__ == "__main__":
    main()
