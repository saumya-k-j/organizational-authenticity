#!/usr/bin/env python3
"""Part 2 step 1 — collect DEF 14A proxy statements from SEC EDGAR.

  python scripts/p2_collect.py                 # all 50 companies
  python scripts/p2_collect.py AAPL JPM XOM    # a slice (collection sanity check)

Cached + idempotent: reruns make zero network calls. Writes raw/clean layers under
data/part2/ and the manifest at logs/part2_filings.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.disclosure.collect import collect  # noqa: E402


def main() -> None:
    tickers = sys.argv[1:] or None
    manifest = collect(tickers)
    sel = tickers or list(manifest.keys())
    n_ok = n_filings = 0
    for t in sel:
        e = manifest.get(t, {})
        ok = sum(1 for f in e.get("filings", []) if f["status"] == "ok")
        n_filings += len(e.get("filings", []))
        n_ok += ok
        print(f"{t:6s} cik={e.get('cik') or '-':>10}  filings_ok={ok:2d}"
              f"  collisions={e.get('collisions', 0)}  err={e.get('error') or '-'}")
    print("-" * 60)
    print(f"{len(sel)} companies, {n_ok}/{n_filings} filings cleaned OK")
    print("manifest -> logs/part2_filings.json")


if __name__ == "__main__":
    main()
