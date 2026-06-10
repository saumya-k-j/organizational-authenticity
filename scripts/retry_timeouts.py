#!/usr/bin/env python3
"""(b) One gentle, free archive retry of the timeout companies.

Timeouts are NOT agent targets (a non-response says nothing about whether a page
exists). This does a single polite pass (throttled + backoff, no credits) on the
companies still marked `timeout`, updating only those rows in the persisted state.
Whatever still times out stays a documented timeout gap — no further retries.

  python scripts/retry_timeouts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.config import LOG_DIR, load_companies, load_settings  # noqa: E402
from authenticity.discovery import _resolve_one, coverage_status, load_results  # noqa: E402
from authenticity.pipeline import build_coverage_grid  # noqa: E402

_MIN = load_settings()["discovery"]["min_years_covered"]


def main() -> None:
    state = load_results()
    companies = {c.ticker: c for c in load_companies()}
    timeouts = sorted(t for t, r in state.items() if r["resolved_by"] == "timeout")
    print(f"Retrying {len(timeouts)} timeouts: {timeouts}\n")

    for tk in timeouts:
        res = _resolve_one(companies[tk])          # one gentle host query
        rd, url, yrs = res.resolved_by, res.chosen_url, []
        if rd in ("prefix_filter", "override") and url:
            snaps, responded = coverage_status(url)
            yrs = sorted(snaps)
            if not responded:
                rd, url = "timeout", None
            elif len(yrs) >= _MIN:
                pass                                # resolved
            elif yrs:
                rd = "low_coverage"
            else:
                rd, url = "genuine_miss", None
        elif rd == "timeout":
            url = None

        state[tk].update(
            resolved_by=rd, chosen_url=url, covered_years=yrs, years_covered=len(yrs),
            per_year_url={str(y): url for y in yrs} if url else {},
        )
        verdict = "STILL TIMEOUT (documented gap)" if rd == "timeout" else f"{rd} {len(yrs)}y {url}"
        print(f"  {tk:6s} -> {verdict}")

    (LOG_DIR / "discovery_results.json").write_text(json.dumps(list(state.values()), indent=2))
    df = build_coverage_grid()
    years = [c for c in df.columns if c.isdigit()]
    filled = int((df[years] == "filled").sum().sum())
    print(f"\nGrid now {filled}/{len(df)*len(years)} cells filled.")


if __name__ == "__main__":
    main()
