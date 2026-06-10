#!/usr/bin/env python3
"""Step E — run the discovery agent on missing-year-recovery targets.

Targets = companies with <9 years that are NOT timeouts (genuine_miss +
low_coverage + resolved-but-incomplete). Timeouts and 9/9-complete companies are
excluded. Needs ANTHROPIC_API_KEY in .env.

  python scripts/run_agent.py                 # all targets
  python scripts/run_agent.py --tickers CVX,SLB,XOM   # a subset (test first!)
  python scripts/run_agent.py --limit 3       # only the first N targets
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.config import LOG_DIR, load_companies, load_settings  # noqa: E402
from authenticity.discovery import load_results  # noqa: E402
from authenticity.pipeline import build_coverage_grid  # noqa: E402

_MIN_YEARS = load_settings()["discovery"]["min_years_covered"]
_COMPLETE = (load_settings()["year_end"] - load_settings()["year_start"] + 1)


def _tier(n: int) -> str:
    return "agent" if n >= _MIN_YEARS else ("low_coverage" if n >= 1 else "genuine_miss")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="Comma-separated subset of targets")
    ap.add_argument("--limit", type=int, help="Process only the first N targets")
    ap.add_argument("--replace", action="store_true",
                    help="Overwrite state with the agent's verdict even if coverage drops "
                         "(used to CORRECT junk picks; default only updates on improvement)")
    args = ap.parse_args()

    import os
    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to .env, then re-run.")
        sys.exit(1)

    state = load_results()
    if not state:
        print("No logs/discovery_results.json — run scripts/discover.py first.")
        sys.exit(1)
    companies = {c.ticker: c for c in load_companies()}

    if args.tickers:
        # Explicit selection overrides the <9y auto-filter (lets us re-run a company
        # that is at 9y but on a junk URL we want corrected).
        want = {t.strip().upper() for t in args.tickers.split(",")}
        targets = [t for t in state if t.upper() in want]
    else:
        targets = [t for t, r in state.items()
                   if r["resolved_by"] != "timeout" and r.get("years_covered", 0) < _COMPLETE]
    targets.sort()
    if args.limit:
        targets = targets[: args.limit]

    print(f"Agent targets: {len(targets)} companies\n")

    from anthropic import Anthropic
    from authenticity.agent import recover_company
    client = Anthropic()

    for tk in targets:
        c, r = companies[tk], state[tk]
        before = len(r.get("covered_years", []))
        res = recover_company(client, c.name, tk, c.domain,
                              r.get("chosen_url"), r.get("covered_years", []))
        n = len(res["covered_years"])
        # --replace: take the agent's (rules-constrained) verdict even if it drops
        # coverage (corrects junk). Otherwise only adopt genuine improvements.
        applied = args.replace or n > before
        if applied:
            r["chosen_url"] = res["best_url"]
            r["covered_years"] = res["covered_years"]
            r["years_covered"] = n
            r["per_year_url"] = res["per_year_url"]
            r["is_canonical"] = res["is_canonical"]
            r["non_canonical_note"] = res["non_canonical_note"]
            r["resolved_by"] = _tier(n)
        final = r["years_covered"]                      # true state value, not the per-run find
        cap = " [HIT-CAP]" if res.get("hit_cap") else ""
        canon = "" if res.get("is_canonical", True) or not applied else " [non-canonical]"
        kept = "" if applied else f" (agent found {n}y, kept {final})"
        print(f"  {tk:6s} {before}y -> {final}y ({final-before:+d})  rounds={res.get('rounds','?')}"
              f"{cap}{canon}{kept}  {r['chosen_url'] or '(none)'}", flush=True)
        # Persist after EVERY company so a mid-run failure (e.g. credits) loses nothing.
        (LOG_DIR / "discovery_results.json").write_text(
            json.dumps(list(state.values()), indent=2)
        )

    # rebuild grid from the final state
    df = build_coverage_grid()
    years = [c for c in df.columns if c.isdigit()]
    filled = int((df[years] == "filled").sum().sum())
    print(f"\nGrid now {filled}/{len(df)*len(years)} cells filled. "
          f"Reasoning -> logs/agent_reasoning.jsonl")


if __name__ == "__main__":
    main()
