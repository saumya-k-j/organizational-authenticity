#!/usr/bin/env python3
"""Deterministically scrub non-values-page URLs from the discovery state.

No LLM (no API credits): coverage checks hit the free archive. For each company:
  - if its primary URL is a human PIN that the agent overwrote with a junk URL,
    restore the pin and re-confirm its coverage;
  - drop any year whose per-year URL fails the values-page rules (product/category
    pages, social profiles, sub-brand pages, file types);
  - re-tier by the surviving acceptable coverage.

Companies left with real missing years remain agent targets for a later
(credit-enabled) constrained re-run. Rebuilds data/coverage_grid.csv.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.agent import _acceptable  # noqa: E402
from authenticity.config import LOG_DIR, load_companies, load_settings  # noqa: E402
from authenticity.discovery import coverage_status, load_results  # noqa: E402
from authenticity.pipeline import build_coverage_grid  # noqa: E402

_MIN = load_settings()["discovery"]["min_years_covered"]


def _tier(n: int, override: bool) -> str:
    if override:
        return "override" if n >= 1 else "genuine_miss"
    return "agent" if n >= _MIN else ("low_coverage" if n >= 1 else "genuine_miss")


def main() -> None:
    state = load_results()
    pins = {c.ticker: c.values_url for c in load_companies() if c.values_url}
    changed = []

    for t, r in state.items():
        before = r.get("years_covered", 0)
        url = r.get("chosen_url")
        pyu = {int(y): u for y, u in (r.get("per_year_url") or {}).items()}

        # 1. Primary URL is junk but a human pin exists -> restore the pin.
        if url and not _acceptable(url) and t in pins:
            pin = pins[t]
            snaps, _ = coverage_status(pin)
            yrs = sorted(snaps)
            r.update(chosen_url=pin, covered_years=yrs, years_covered=len(yrs),
                     per_year_url={str(y): pin for y in yrs},
                     is_canonical=True, non_canonical_note="",
                     resolved_by=_tier(len(yrs), override=True))
            if len(yrs) != before:
                changed.append((t, before, len(yrs), pin))
            continue

        # 2. Drop years whose per-year URL is unacceptable (junk fills).
        if pyu:
            good = {y: u for y, u in pyu.items() if _acceptable(u)}
            if len(good) != len(pyu):
                yrs = sorted(good)
                # primary = the acceptable url covering the most years (or None)
                from collections import Counter
                primary = Counter(good.values()).most_common(1)[0][0] if good else None
                r.update(chosen_url=primary, covered_years=yrs, years_covered=len(yrs),
                         per_year_url={str(y): u for y, u in good.items()},
                         resolved_by=_tier(len(yrs), override=t in pins))
                changed.append((t, before, len(yrs), primary or "(none)"))
        # 3. Primary junk, no pin, no per-year map -> can't keep it.
        elif url and not _acceptable(url):
            r.update(chosen_url=None, covered_years=[], years_covered=0,
                     per_year_url={}, resolved_by="genuine_miss")
            changed.append((t, before, 0, "(stripped)"))

    (LOG_DIR / "discovery_results.json").write_text(json.dumps(list(state.values()), indent=2))
    df = build_coverage_grid()
    years = [c for c in df.columns if c.isdigit()]
    filled = int((df[years] == "filled").sum().sum())

    print("Scrubbed companies (junk -> trustworthy):")
    for t, b, a, u in sorted(changed):
        print(f"  {t:6s} {b}y -> {a}y   {u}")
    print(f"\nGrid now {filled}/{len(df)*len(years)} cells filled (all from acceptable URLs).")


if __name__ == "__main__":
    main()
