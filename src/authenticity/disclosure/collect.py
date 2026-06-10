"""Collection orchestration: tickers -> CIK -> DEF 14A list -> download -> clean ->
raw/interim layers + a manifest. Mirrors Part 1's pipeline style and shares the cache
and a run-log (logs/part2_run.jsonl). Reruns are free: every fetch is cache-backed.

State is persisted to logs/part2_filings.json (the Part-2 analogue of Part 1's
discovery_results.json) so coverage and analysis read from disk, not the network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from collections import defaultdict

from .clean_filing import clean_filing
from .config import INTERIM_DIR, LOG_DIR, RAW_DIR, load_companies
from .edgar import FORM_RANK, ciks_for_ticker, def14a_filings, download_filing

_MANIFEST = LOG_DIR / "part2_filings.json"
_RUNLOG = LOG_DIR / "part2_run.jsonl"


def _log(rec: dict) -> None:
    rec["t"] = datetime.now(timezone.utc).isoformat()
    with _RUNLOG.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _interim_path(ticker: str, year: int):
    return INTERIM_DIR / f"{ticker.replace('.', '_')}_{year}.txt"


def _load_manifest() -> dict:
    return json.loads(_MANIFEST.read_text()) if _MANIFEST.exists() else {}


def collect(tickers: list[str] | None = None) -> dict:
    """Collect DEF 14A filings for the selected companies (default: all 50).

    Per company: resolve CIK, enumerate in-window DEF 14A filings, download + clean
    each, write the clean text to the interim layer, and record an entry per filing.
    Merges into any existing manifest so partial/slice runs accumulate.
    """
    companies = load_companies()
    if tickers:
        want = {t.upper() for t in tickers}
        companies = [c for c in companies if c.ticker.upper() in want]

    manifest = _load_manifest()
    for c in companies:
        ciks = ciks_for_ticker(c.ticker)  # >1 when a predecessor CIK is merged in
        entry = {"cik": ciks[0] if ciks else None, "ciks_scanned": ciks,
                 "name": c.name, "sector": c.sector, "filings": [], "error": None}
        if not ciks:
            entry["error"] = "no_cik"
            _log({"event": "collect", "ticker": c.ticker, "status": "no_cik"})
            manifest[c.ticker] = entry
            continue

        try:
            filings = []
            for cik in ciks:  # merge filings across continuing + predecessor CIKs
                filings.extend(def14a_filings(cik))
        except Exception as e:  # network/parse failure for the whole company
            entry["error"] = f"submissions_error: {e!r}"
            _log({"event": "collect", "ticker": c.ticker, "status": "submissions_error", "error": repr(e)})
            manifest[c.ticker] = entry
            continue

        # Group candidates by meeting-year. Most years have exactly one; a contested
        # year has several (management's proxy + dissident solicitations, all under the
        # subject CIK). Download+clean each candidate, then keep the management annual
        # proxy: lowest form rank (DEF 14A > DEFC14A), then longest text (the full
        # statement dwarfs a dissident's card). Alternates are recorded, not discarded.
        cands_by_year: dict[int, list] = defaultdict(list)
        for f in filings:
            cands_by_year[f.meeting_year].append(f)

        collisions = 0
        for year in sorted(cands_by_year):
            cands = cands_by_year[year]
            if len(cands) > 1:
                collisions += 1
            scored = []
            for f in cands:
                try:
                    html, _ = download_filing(f, RAW_DIR, c.ticker)
                    text = clean_filing(html)
                    scored.append((f, text, len(text or "")))
                except Exception as e:
                    scored.append((f, None, -1))
                    _log({"event": "filing_cand_error", "ticker": c.ticker,
                          "year": year, "accession": f.accession, "error": repr(e)})
            # selection key: prefer real annual proxy form, then most text
            scored.sort(key=lambda s: (FORM_RANK.get(s[0].form, 9), -s[2]))
            f, text, n = scored[0]
            rec = {"meeting_year": year, "accession": f.accession, "form": f.form,
                   "filing_date": f.filing_date, "doc_url": f.doc_url,
                   "n_chars": max(n, 0), "status": "ok",
                   "n_candidates": len(cands),
                   "alternates": [s[0].accession for s in scored[1:]]}
            if not text:
                rec["status"] = "empty_text"
            else:
                _interim_path(c.ticker, year).write_text(text, encoding="utf-8")
            entry["filings"].append(rec)
            _log({"event": "filing", "ticker": c.ticker, "year": year, "form": f.form,
                  "status": rec["status"], "n_chars": rec["n_chars"],
                  "n_candidates": len(cands)})

        entry["collisions"] = collisions
        manifest[c.ticker] = entry
        _log({"event": "collect", "ticker": c.ticker, "status": "done",
              "n_filings": len(cands_by_year), "collisions": collisions})

    _MANIFEST.write_text(json.dumps(manifest, indent=2))
    return manifest
