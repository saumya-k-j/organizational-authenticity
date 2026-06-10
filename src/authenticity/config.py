"""Config loading and project paths."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]   # src/authenticity/config.py -> repo root
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
INTERIM_DIR = DATA_DIR / "interim"
OUTPUT_DIR = DATA_DIR / "output"
CACHE_DIR = ROOT / ".cache"
LOG_DIR = ROOT / "logs"

for _d in (INTERIM_DIR, OUTPUT_DIR, CACHE_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _load_yaml(path: Path) -> Any:
    with path.open() as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    sector: str
    domain: str
    values_url: str | None = None


def load_companies() -> list[Company]:
    raw = _load_yaml(CONFIG_DIR / "companies.yaml")["companies"]
    return [Company(**{**{"values_url": None}, **c}) for c in raw]


def load_settings() -> dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "settings.yaml")


def load_taxonomy() -> dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "taxonomy.yaml")
