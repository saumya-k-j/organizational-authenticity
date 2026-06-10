"""Part 3 config + paths. Reuses Parts 1/2 conventions (shared cache, logs, taxonomy)
and adds a data/part3/ output layer. No new settings file — Part 3 is pure computation
over the two existing datasets.
"""
from __future__ import annotations

from ..config import CACHE_DIR, DATA_DIR, LOG_DIR, load_taxonomy  # noqa: F401

P3_DIR = DATA_DIR / "part3"
OUTPUT_DIR = P3_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PART1_CSV = DATA_DIR / "output" / "part1_stated_values.csv"
PART2_CSV = DATA_DIR / "part2" / "output" / "part2_disclosure_metrics.csv"

ALL_THEME_KEYS = [t["key"] for t in load_taxonomy()["themes"]]

# Two themes OBSERVABLY dominate every proxy: in the Part 2 data governance runs at 26-31
# mentions/1k words (3.5-5.6x the top discretionary theme in every sector) and profit is the
# next-largest. Some of that is genuine emphasis and some is SEC-mandated board/pay
# disclosure; the lexicon can't cleanly separate the two. Either way, leaving them in
# mechanically dominates the over-claiming math (including all 13 nearly doubles the mean and
# reorders companies, rank corr ~0.67). So the index SCORES only the 11 discretionary themes.
# Both remain tagged/stored in part2_disclosure_metrics.csv — only the scoring skips them.
STRUCTURAL_THEMES = {"leadership_governance", "profitable_growth"}
DISCRETIONARY_THEME_KEYS = [k for k in ALL_THEME_KEYS if k not in STRUCTURAL_THEMES]
