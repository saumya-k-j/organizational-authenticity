"""Build the Part 2 coverage grid (companies x meeting-years 2016-2024) from the
persisted manifest — no network. Same idea and reason-coded shape as Part 1's grid,
so the two coverage tables read identically side by side.

Cell values:
  filled        DEF 14A found and cleaned to real text for that meeting-year
  no_filing     company resolved, but no DEF 14A in that meeting-year cycle
  empty_text    filing downloaded but cleaned to nothing (rare; analogue of Part 1's
                broken_snapshot)
  fetch_error   download/parse failed for that specific filing
  no_cik        ticker never resolved to a CIK (whole row)
Filing is mandatory for public companies, so we EXPECT near-total coverage; genuine
gaps (a company not yet public, a year run as a special/merger proxy) are documented,
not hidden. `collisions` flags any company where two filings fell in one meeting-year
bucket — a signal the Q4 cutover mis-shifted that firm.
"""
from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from .config import LOG_DIR, OUTPUT_DIR, load_companies, load_settings

_S = load_settings()
_Y0, _Y1 = _S["year_start"], _S["year_end"]
_MANIFEST = LOG_DIR / "part2_filings.json"


def build_coverage_grid(tickers: list[str] | None = None) -> pd.DataFrame:
    manifest = json.loads(_MANIFEST.read_text()) if _MANIFEST.exists() else {}
    companies = load_companies()
    if tickers:
        want = {t.upper() for t in tickers}
        companies = [c for c in companies if c.ticker.upper() in want]

    years = list(range(_Y0, _Y1 + 1))
    rows = []
    for c in companies:
        e = manifest.get(c.ticker, {})
        # status per meeting-year from the filing records
        status_by_year = {}
        for f in e.get("filings", []):
            st = f["status"]
            status_by_year[f["meeting_year"]] = (
                "filled" if st == "ok" and f.get("n_chars", 0) > 0
                else ("empty_text" if st == "empty_text" else "fetch_error")
            )
        row = {
            "ticker": c.ticker, "name": c.name, "sector": c.sector,
            "cik": e.get("cik") or "", "collisions": e.get("collisions", 0),
            "years_covered": sum(1 for v in status_by_year.values() if v == "filled"),
        }
        for y in years:
            if e.get("error") == "no_cik":
                row[str(y)] = "no_cik"
            else:
                row[str(y)] = status_by_year.get(y, "no_filing")
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "part2_coverage_grid.csv", index=False)
    return df


def coverage_summary(df: pd.DataFrame) -> dict:
    years = [c for c in df.columns if c.isdigit()]
    total = len(df) * len(years)
    filled = int((df[years] == "filled").sum().sum())
    reasons = Counter(v for y in years for v in df[y] if v != "filled")
    return {"cells": total, "filled": filled,
            "pct": round(100 * filled / total, 1) if total else 0.0,
            "gap_reasons": dict(reasons),
            "collisions": int(df["collisions"].sum())}
