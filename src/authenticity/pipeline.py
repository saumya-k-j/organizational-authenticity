"""Part 1 orchestration over the persisted discovery state.

  resolve_breakdown   discovery -> coverage -> 4-way tiering (+ gentle timeout retry)
  build_coverage_grid the companies x years grid with reason codes
  extract_and_tag     fetch + clean + change-detect + theme-tag every filled cell

Each is driven by its own script in scripts/; they share the cache and the
logs/run.jsonl decision log.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from . import change as change_mod
from .clean import clean_html
from .config import INTERIM_DIR, LOG_DIR, OUTPUT_DIR, load_companies, load_settings
from .discovery import (
    DiscoveryResult, _resolve_one, coverage_status, load_results, resolve_all,
    write_misses, write_results,
)
from .fetch import fetch_html
from .tagging import classify

_S = load_settings()
_Y0, _Y1 = _S["year_start"], _S["year_end"]
_MIN_YEARS = _S["discovery"]["min_years_covered"]


def _log(rec: dict) -> None:
    rec["t"] = datetime.now(timezone.utc).isoformat()
    with (LOG_DIR / "run.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _interim_path(ticker: str, year: int):
    safe = ticker.replace(".", "_")
    return INTERIM_DIR / f"{safe}_{year}.txt"


def _confirm_coverage(r: DiscoveryResult) -> None:
    """Gentle serial coverage check for one result; resolves the 3-way category.

      - request failed       -> timeout
      - responded, >=1 year  -> stays override/prefix_filter (resolved)
      - responded, 0 captures-> genuine_miss (URL has no in-window snapshots)
    """
    if r.resolved_by not in ("override", "prefix_filter") or not r.chosen_url:
        return
    snaps, responded = coverage_status(r.chosen_url)
    r.years_covered = len(snaps)
    r.covered_years = sorted(snaps.keys())
    if not responded:
        r.resolved_by = "timeout"
    elif len(snaps) >= _MIN_YEARS:
        pass                       # stays resolved (override / prefix_filter)
    elif snaps:
        r.resolved_by = "low_coverage"   # has a URL, but < min_years of 9
    else:
        r.resolved_by = "genuine_miss"   # URL responded with 0 in-window captures


def _missing_reason(resolved_by: str) -> str:
    """Deterministic reason code for a missing company-year cell.

    redirect / broken_snapshot are NOT assignable deterministically here (they need
    per-snapshot inspection) — the Step-E agent assigns those as it investigates.
    """
    return {
        "timeout": "timeout",            # archive did not respond for this company
        "genuine_miss": "host_wrong",    # www host had no values page at all
        "low_coverage": "no_capture",    # URL exists, that year not captured
        "override": "no_capture",
        "prefix_filter": "no_capture",
        "agent": "no_capture",           # agent found a URL; that year still not captured
    }.get(resolved_by, "not_yet_checked")


def build_coverage_grid(tickers: list[str] | None = None) -> pd.DataFrame:
    """Write data/coverage_grid.csv from the PERSISTED discovery state — no archive
    calls. One row per company, a column per year; each cell is 'filled' or a reason
    code (no_capture / host_wrong / timeout / not_yet_checked). Run discovery first
    (scripts/discover.py) so logs/discovery_results.json exists.
    """
    state = load_results()
    companies = load_companies()
    if tickers:
        wanted = {t.upper() for t in tickers}
        companies = [c for c in companies if c.ticker.upper() in wanted]

    # Cells found to have no extractable text during extraction -> broken_snapshot.
    broken = set()
    bpath = LOG_DIR / "broken_snapshots.json"
    if bpath.exists():
        broken = {(t, int(y)) for t, y in json.loads(bpath.read_text())}

    years = list(range(_Y0, _Y1 + 1))
    rows = []
    for c in companies:
        r = state.get(c.ticker, {})
        tier = r.get("resolved_by", "not_yet_checked")
        covered = set(r.get("covered_years", []))
        row = {
            "ticker": c.ticker, "name": c.name, "sector": c.sector,
            "tier": tier, "chosen_url": r.get("chosen_url") or "",
            "years_covered": len(covered),
            "is_canonical": r.get("is_canonical", True),
            "non_canonical_note": r.get("non_canonical_note", ""),
        }
        for y in years:
            if (c.ticker, y) in broken:
                row[str(y)] = "broken_snapshot"
            else:
                row[str(y)] = "filled" if y in covered else _missing_reason(tier)
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR.parent / "coverage_grid.csv", index=False)
    return df


def extract_and_tag(tickers: list[str] | None = None, do_tagging: bool = True) -> pd.DataFrame:
    """Part 1 deliverable: fetch + clean every FILLED grid cell, detect change, tag.

    Reads the final persisted discovery state (per-year URL map), so each year is
    fetched from the URL that actually has it. Change is the deterministic
    digest/difflib signal; the LLM is called only on the first year and on detected
    changes (identical text reuses the prior tag). Output columns:
    [ticker, company, sector, year, page_text_clean, changed_from_prior,
     theme_categories, analyst_notes] -> data/output/part1_stated_values.csv.
    """
    from .discovery import coverage, load_results
    state = load_results()
    companies = {c.ticker: c for c in load_companies()}
    sel = ([t.upper() for t in tickers] if tickers
           else [t for t, r in state.items() if r.get("years_covered", 0) > 0])

    cov_cache: dict[str, dict] = {}

    def cov(url: str) -> dict:
        if url not in cov_cache:
            cov_cache[url] = coverage(url)   # {year: Snapshot}, cached
        return cov_cache[url]

    rows: list[dict] = []
    broken: list[list] = []   # [[ticker, year], ...] snapshot exists but no extractable text
    for tk in sel:
        r = state.get(tk)
        c = companies.get(tk)
        if not r or not c:
            continue
        pyu = r.get("per_year_url") or {}
        chosen = r.get("chosen_url")
        prev_text = prev_digest = prev_themes = None
        prev_year = None
        for year in sorted(r.get("covered_years", [])):
            url = pyu.get(str(year)) or chosen
            snap = cov(url).get(year) if url else None
            if snap is None:
                continue
            html = fetch_html(snap)
            text = clean_html(html) if html else None
            if text:
                _interim_path(tk, year).write_text(text, encoding="utf-8")

            changed = change_mod.changed_from_prev(prev_digest, snap.digest, prev_text, text)
            themes = analyst_notes = None
            if not text:
                # snapshot exists but cleans to nothing -> broken_snapshot (not real content)
                broken.append([tk, year])
                analyst_notes = "broken_snapshot: archived snapshot has no extractable text"
            elif do_tagging and text:
                if prev_themes is None or changed:        # first year or a real change
                    try:
                        tag = classify(text)
                        themes = "|".join(tag.present_theme_keys)
                        analyst_notes = tag.summary
                    except Exception as e:
                        _log({"event": "tag_error", "ticker": tk, "year": year, "error": repr(e)})
                else:                                       # identical text -> reuse, no LLM call
                    themes = prev_themes
                    analyst_notes = f"unchanged from {prev_year}"

            rows.append({
                "ticker": tk, "company": c.name, "sector": c.sector, "year": year,
                "page_text_clean": text or "",
                "changed_from_prior": changed,
                "theme_categories": themes or "",
                "analyst_notes": analyst_notes or "",
            })
            _log({"event": "extract", "ticker": tk, "year": year,
                  "n_chars": len(text) if text else 0, "changed": changed, "tagged": bool(themes)})
            prev_text, prev_digest = text, snap.digest
            if themes:
                prev_themes = themes
            prev_year = year

    # Record broken_snapshot cells so the grid can reclassify them (snapshot exists
    # but yields no content -> not real content coverage).
    if broken:
        existing = []
        bpath = LOG_DIR / "broken_snapshots.json"
        if bpath.exists():
            existing = json.loads(bpath.read_text())
        merged = {tuple(x) for x in existing} | {tuple(x) for x in broken}
        bpath.write_text(json.dumps(sorted(merged), indent=2))

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "part1_stated_values.csv", index=False)
    _log({"event": "extract_done", "rows": len(df), "companies": len(sel),
          "tagged": do_tagging, "broken": len(broken)})
    return df


def resolve_breakdown(tickers: list[str] | None = None,
                      retry_timeouts: bool = True) -> tuple[list[DiscoveryResult], dict]:
    """Discovery (gentle, one host query each) -> serial coverage -> optional retry.

    Four-way outcome: resolved (override/prefix_filter, >=min_years), low_coverage
    (URL but <min_years), genuine_miss (archive responded, no page), timeout (archive
    did not respond). With retry_timeouts, timeouts get ONE gentle retry pass — they
    are NEVER the discovery agent's job.
    """
    from collections import Counter
    companies = load_companies()
    if tickers:
        wanted = {t.upper() for t in tickers}
        companies = [c for c in companies if c.ticker.upper() in wanted]
    by_ticker = {c.ticker: c for c in companies}

    resolved = resolve_all(companies)            # concurrent (cap 2) host queries
    results = [resolved[c.ticker] for c in companies]
    for r in results:                            # serial, throttled coverage
        _confirm_coverage(r)

    if retry_timeouts:                           # ONE gentle retry pass for timeouts only
        for r in results:
            if r.resolved_by != "timeout":
                continue
            nr = _resolve_one(by_ticker[r.ticker])
            r.resolved_by, r.chosen_url = nr.resolved_by, nr.chosen_url
            r.n_candidate_paths, r.candidates = nr.n_candidate_paths, nr.candidates
            _confirm_coverage(r)

    write_misses(results)
    write_results(results)
    return results, dict(Counter(r.resolved_by for r in results))
