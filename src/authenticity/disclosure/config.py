"""Part 2 config + paths. Mirrors Part 1's config.py conventions but keeps Part 1's
frozen config untouched. Reuses the same companies.yaml (same 50 firms) and the same
on-disk cache + logs directories, so the two parts share one reproducible substrate.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Reuse Part 1's project paths + Company model + companies/taxonomy loaders verbatim.
from ..config import (  # noqa: F401
    CACHE_DIR,
    CONFIG_DIR,
    DATA_DIR,
    LOG_DIR,
    Company,
    load_companies,
    load_taxonomy,
)

# Part 2 gets its own raw/clean/structured layers under data/part2/ so it never
# collides with Part 1's outputs.
P2_DIR = DATA_DIR / "part2"
RAW_DIR = P2_DIR / "raw"          # raw filing HTML, one file per company-year
INTERIM_DIR = P2_DIR / "interim"  # cleaned proxy text, one file per company-year
OUTPUT_DIR = P2_DIR / "output"    # structured datasets + coverage grid

for _d in (RAW_DIR, INTERIM_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict[str, Any]:
    with (CONFIG_DIR / "part2_settings.yaml").open() as f:
        return yaml.safe_load(f)


def load_lexicon() -> dict[str, Any]:
    with (CONFIG_DIR / "value_lexicon.yaml").open() as f:
        return yaml.safe_load(f)
