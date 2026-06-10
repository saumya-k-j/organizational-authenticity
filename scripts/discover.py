#!/usr/bin/env python3
"""Step 1 — run deterministic discovery only, and print the resolved_by breakdown.

  python scripts/discover.py                # all 50
  python scripts/discover.py --tickers MSFT,JNJ,XOM

Prints per-company resolution and a summary, and writes logs/discovery_misses.json.
No scraping, no LLM.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.pipeline import resolve_breakdown  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="Comma-separated tickers (default: all 50)")
    ap.add_argument("--no-retry", action="store_true",
                    help="Skip the gentle timeout-retry pass (avoids re-hitting heavy sites)")
    args = ap.parse_args()
    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else None

    t0 = time.monotonic()
    results, counts = resolve_breakdown(tickers, retry_timeouts=not args.no_retry)
    dt = time.monotonic() - t0

    groups = {
        "resolved": [r for r in results if r.resolved_by in ("override", "prefix_filter")],
        "low_coverage": [r for r in results if r.resolved_by == "low_coverage"],
        "genuine_miss": [r for r in results if r.resolved_by == "genuine_miss"],
        "timeout": [r for r in results if r.resolved_by == "timeout"],
    }
    for name, rs in groups.items():
        print(f"\n=== {name.upper()} ({len(rs)}) ===")
        for r in sorted(rs, key=lambda r: r.ticker):
            extra = f"{r.years_covered}y  {r.chosen_url}" if r.chosen_url else "(no page found)"
            tag = f"[{r.resolved_by}]" if name in ("resolved", "low_coverage") else ""
            print(f"  {r.ticker:6s} {extra} {tag}")

    print("\n" + "-" * 70)
    print("BREAKDOWN  " + "  ".join(f"{k}={len(v)}" for k, v in groups.items()))
    print(f"{len(results)} companies in {dt:.1f}s")
    print("genuine_miss + low_coverage -> logs/discovery_misses.json (Step-E agent targets)")
    print("timeout                     -> logs/discovery_timeouts.json (retry, NOT the agent)")


if __name__ == "__main__":
    main()
