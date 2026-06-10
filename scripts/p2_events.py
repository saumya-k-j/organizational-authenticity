#!/usr/bin/env python3
"""Part 2 step 4 — event-coincidence analysis.

Tests whether proxy-language theme shifts line up in time with known 2016-2024 external
events (config/events.yaml). Reads the analysis output; writes
data/part2/output/part2_event_alignment.csv. Run after scripts/p2_analyze.py.

  python scripts/p2_events.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.disclosure.events import analyze_events  # noqa: E402


def main() -> None:
    df = analyze_events()
    cols = ["event", "theme", "reflect_year", "pre_mean", "post_mean", "change_pct",
            "biggest_jump_year", "verdict"]
    print(df[cols].to_string(index=False))
    print("-" * 70)
    print("wrote data/part2/output/part2_event_alignment.csv")


if __name__ == "__main__":
    main()
