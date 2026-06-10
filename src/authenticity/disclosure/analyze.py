"""Analysis orchestration: persisted filings -> one structured dataset + trend tables.

Combines the two halves:
  - classical (textstats): theme freqs, tone, readability, sizes — on full text.
  - corpus-level classical: tf-idf year-over-year similarity per company, and per-sector
    distinctive terms.
  - LLM (llmtag): semantic theme tags + stakeholder orientation on a values excerpt.

Outputs (data/part2/output/):
  part2_disclosure_metrics.csv     one row per company-year (the main deliverable)
  part2_theme_trends_by_year.csv   mean theme freq per meeting-year (the time trend)
  part2_theme_by_sector.csv        mean theme freq per sector (the sector fingerprint)
  part2_distinctive_terms.csv      top tf-idf terms per sector
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import INTERIM_DIR, LOG_DIR, OUTPUT_DIR, load_settings, load_taxonomy
from .textstats import text_stats

_S = load_settings()
_MANIFEST = LOG_DIR / "part2_filings.json"
_RUNLOG = LOG_DIR / "part2_run.jsonl"
_THEME_KEYS = [t["key"] for t in load_taxonomy()["themes"]]


def _log(rec: dict) -> None:
    rec["t"] = datetime.now(timezone.utc).isoformat()
    with _RUNLOG.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _interim_path(ticker: str, year: int):
    return INTERIM_DIR / f"{ticker.replace('.', '_')}_{year}.txt"


def _filled_units(tickers: list[str] | None):
    """Yield (ticker, name, sector, year, accession, form, filing_date, text) for every
    successfully-cleaned company-year in the manifest."""
    manifest = json.loads(_MANIFEST.read_text())
    want = {t.upper() for t in tickers} if tickers else None
    for tk, e in manifest.items():
        if want and tk.upper() not in want:
            continue
        for f in e.get("filings", []):
            if f["status"] != "ok":
                continue
            p = _interim_path(tk, f["meeting_year"])
            if not p.exists():
                continue
            yield (tk, e["name"], e["sector"], f["meeting_year"],
                   f["accession"], f.get("form", ""), f["filing_date"],
                   p.read_text(encoding="utf-8"))


def _tfidf_features(texts: list[str]):
    vec = TfidfVectorizer(
        max_features=_S["analysis"]["tfidf_max_features"],
        min_df=_S["analysis"]["tfidf_min_df"],
        stop_words="english",
        token_pattern=r"[A-Za-z][A-Za-z]+",
    )
    return vec, vec.fit_transform(texts)


def analyze(tickers: list[str] | None = None, do_llm: bool = True) -> pd.DataFrame:
    units = list(_filled_units(tickers))
    if not units:
        raise SystemExit("No collected filings found — run scripts/p2_collect.py first.")

    texts = [u[7] for u in units]
    vec, X = _tfidf_features(texts)   # corpus-level tf-idf for sim + distinctive terms

    # index rows by (ticker, year) so we can look up the prior-year vector per company
    idx_by_unit = {(u[0], u[3]): i for i, u in enumerate(units)}

    rows = []
    for i, u in enumerate(units):
        tk, name, sector, year, acc, form, fdate, text = u
        row = {"ticker": tk, "company": name, "sector": sector, "meeting_year": year,
               "form": form, "filing_date": fdate, "accession": acc}
        row.update(text_stats(text))

        # year-over-year tf-idf cosine similarity within the same company
        prev = idx_by_unit.get((tk, year - 1))
        row["sim_to_prev"] = (
            round(float(cosine_similarity(X[i], X[prev])[0, 0]), 4)
            if prev is not None else None
        )

        if do_llm:
            try:
                from .llmtag import classify_proxy
                tag = classify_proxy(text)
                row["llm_themes"] = "|".join(tag.present_theme_keys)
                row["llm_dominant_theme"] = tag.dominant_theme_key
                row["llm_stakeholder_orientation"] = tag.stakeholder_orientation
                row["llm_summary"] = tag.summary
            except Exception as e:
                _log({"event": "llm_error", "ticker": tk, "year": year, "error": repr(e)})
                row["llm_themes"] = row["llm_dominant_theme"] = ""
                row["llm_stakeholder_orientation"] = row["llm_summary"] = ""
        rows.append(row)
        _log({"event": "analyze", "ticker": tk, "year": year, "n_words": row["n_words"],
              "sim_to_prev": row["sim_to_prev"], "llm": do_llm})

    df = pd.DataFrame(rows).sort_values(["sector", "ticker", "meeting_year"])
    df.to_csv(OUTPUT_DIR / "part2_disclosure_metrics.csv", index=False)

    _write_aggregates(df)
    _write_distinctive_terms(vec, X, units)
    _log({"event": "analyze_done", "rows": len(df), "llm": do_llm})
    return df


def _write_aggregates(df: pd.DataFrame) -> None:
    theme_cols = [f"theme_{k}" for k in _THEME_KEYS]
    df.groupby("meeting_year")[theme_cols].mean().round(3).to_csv(
        OUTPUT_DIR / "part2_theme_trends_by_year.csv")
    df.groupby("sector")[theme_cols].mean().round(3).to_csv(
        OUTPUT_DIR / "part2_theme_by_sector.csv")


def _write_distinctive_terms(vec, X, units, top_n: int = 20) -> None:
    """Per-sector top tf-idf terms: mean tf-idf vector per sector, highest-weighted terms.
    A cheap, transparent 'what does this sector's proxy language sound like' view."""
    terms = np.array(vec.get_feature_names_out())
    sectors = sorted({u[2] for u in units})
    out = []
    for s in sectors:
        idx = [i for i, u in enumerate(units) if u[2] == s]
        centroid = np.asarray(X[idx].mean(axis=0)).ravel()
        top = centroid.argsort()[::-1][:top_n]
        out.append({"sector": s, "top_terms": ", ".join(terms[top])})
    pd.DataFrame(out).to_csv(OUTPUT_DIR / "part2_distinctive_terms.csv", index=False)
