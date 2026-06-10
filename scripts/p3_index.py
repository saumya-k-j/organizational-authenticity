#!/usr/bin/env python3
"""Part 3 step 1 — compute the Organizational Authenticity Index.

  python scripts/p3_index.py                    # all companies
  python scripts/p3_index.py MSFT JPM XOM MCD   # a slice

Writes data/part3/output/part3_authenticity_index.csv (per company-year) and
part3_trajectory.csv (per company widening/closing). Pure computation over the existing
Part 1 + Part 2 datasets — no network, no API.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.index3.index import compute_index, compute_trajectory  # noqa: E402


def main() -> None:
    tickers = sys.argv[1:] or None
    idx = compute_index(tickers)
    traj = compute_trajectory(idx)

    # Distribution + rankings are reported on TRUSTWORTHY cells only; low-evidence cells stay
    # in the CSV (flagged) but are excluded by default so a near-empty page can't present as
    # "most aligned". (Part 1's confirm-don't-invent / documented-not-hidden discipline.)
    hi = idx[~idx["low_evidence"]]
    n_low = int(idx["low_evidence"].sum())
    s = hi["over_claim_index"]
    print(f"=== distribution of over_claim_index (high-evidence cells only) ===")
    print(f"  scored cells: {len(idx)}  |  low_evidence excluded: {n_low}  |  used: {len(s)}")
    print(f"  range=[{s.min():.3f}, {s.max():.3f}]  mean={s.mean():.3f}"
          f"  median={s.median():.3f}  std={s.std():.3f}")

    print("\n=== most over-claiming (company means, high-evidence) ===")
    cm = (hi.groupby(["ticker", "sector"])["over_claim_index"].agg(["mean", "size"])
          .sort_values("mean", ascending=False).round(3))
    print(cm.head(8).to_string())
    print("\n=== least over-claiming (high-evidence) ===")
    print(cm.tail(8).to_string())

    print("\n=== trajectory (widening = over-claiming gap growing; low-evidence years dropped) ===")
    print(traj[["ticker", "n_years", "n_low_evidence_excluded", "first_level",
                "last_level", "slope_per_year", "trajectory"]].to_string(index=False))
    print("\nwrote data/part3/output/part3_authenticity_index.csv, part3_trajectory.csv")


if __name__ == "__main__":
    main()
