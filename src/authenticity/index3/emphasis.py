"""Put both channels' value emphasis on ONE comparable scale.

The problem this solves: Part 2 computed graded per-theme frequencies for the proxies,
but Part 1 only stored BINARY theme tags (present/absent) for the websites. To grade
over-claiming by DEGREE we need graded emphasis on both sides, measured identically. So
we recompute the website's per-theme emphasis from Part 1's stored cleaned text with the
SAME lexicon Part 2 used (authenticity.disclosure.textstats) — the only way the two
channels are numerically comparable.

Returns, per channel, a tidy [ticker, year, <theme columns>] frame of raw per-theme
emphasis (per-1k-word frequencies). Normalization happens in index.py.
"""
from __future__ import annotations

import pandas as pd

from ..disclosure.textstats import text_stats
from .config import ALL_THEME_KEYS, PART1_CSV, PART2_CSV

_THEME_COLS = [f"theme_{k}" for k in ALL_THEME_KEYS]


def website_emphasis(tickers: list[str] | None = None) -> pd.DataFrame:
    """Per-theme website emphasis, RECOMPUTED from Part 1's page_text_clean with Part 2's
    lexicon (Part 1 itself stored only binary tags). One row per company-year with text."""
    df = pd.read_csv(PART1_CSV)
    df = df[df["page_text_clean"].fillna("").str.len() > 0].copy()
    if tickers:
        df = df[df["ticker"].isin(set(tickers))]
    rows = []
    for r in df.itertuples():
        stats = text_stats(r.page_text_clean)
        # evidence size of THIS side — the website is the binding constraint (proxies are
        # never thin), so a short page is what makes an emphasis profile unreliable.
        row = {"ticker": r.ticker, "sector": r.sector, "year": int(r.year),
               "web_chars": len(r.page_text_clean), "web_words": int(stats["n_words"])}
        row.update({c: stats[c] for c in _THEME_COLS})
        rows.append(row)
    return pd.DataFrame(rows)


def proxy_emphasis(tickers: list[str] | None = None) -> pd.DataFrame:
    """Per-theme proxy emphasis straight from Part 2's metrics (already computed with the
    same lexicon). meeting_year -> year so the two channels join."""
    df = pd.read_csv(PART2_CSV)
    if tickers:
        df = df[df["ticker"].isin(set(tickers))]
    keep = ["ticker", "sector", "meeting_year", "n_words"] + _THEME_COLS
    out = df[keep].rename(columns={"meeting_year": "year", "n_words": "proxy_words"}).copy()
    return out
