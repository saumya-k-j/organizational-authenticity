"""Two validity checks for the index (both required by the brief).

(1) contested-proxy cluster — do the company-years where activists publicly contested the
    proxy (XOM 2021 / Engine No. 1, MCD 2022 / Icahn, SBUX 2024) sit high in the
    over-claiming distribution? A soft external anchor: those are years where the gap
    between a company's self-image and outside scrutiny was openly in dispute.

(2) diversity hard-facts — the only place we can put a NUMBER behind a value. We
    LLM-extract the actual board composition (women / racially-ethnically diverse
    directors) disclosed in each proxy, then ask: does a company's stated diversity
    emphasis (website) track its REAL board diversity? If diversity talk is authentic,
    more talk should go with more diverse boards (positive correlation); if it's cheap,
    it won't. This is the one check that reaches past speech to a disclosed fact.

Extraction is cached by content hash, same as Parts 1-2.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ..disclosure.config import INTERIM_DIR
from .config import CACHE_DIR, DISCRETIONARY_THEME_KEYS, OUTPUT_DIR
from .emphasis import proxy_emphasis, website_emphasis

# Known publicly-contested annual proxies in the Part 2 window (see PART2 findings).
CONTESTED = [("XOM", 2021), ("MCD", 2022), ("SBUX", 2024)]

_DISC_COLS = [f"theme_{k}" for k in DISCRETIONARY_THEME_KEYS]
_DIV_COL = "theme_diversity_inclusion"


def contested_cluster(index_df: pd.DataFrame) -> pd.DataFrame:
    """Percentile of each contested company-year within the HIGH-EVIDENCE over-claiming
    distribution (so a thin page can't distort the percentile)."""
    hi = index_df[~index_df["low_evidence"]] if "low_evidence" in index_df else index_df
    s = hi["over_claim_index"]
    rows = []
    for tk, yr in CONTESTED:
        cell = index_df[(index_df.ticker == tk) & (index_df.year == yr)]
        if cell.empty:
            rows.append({"ticker": tk, "year": yr, "over_claim_index": None,
                         "percentile": None, "note": "not scored (no Part 1 website cell)"})
            continue
        v = float(cell["over_claim_index"].iloc[0])
        low = bool(cell["low_evidence"].iloc[0]) if "low_evidence" in cell else False
        pct = round(float((s < v).mean()) * 100, 1)
        rows.append({"ticker": tk, "year": yr, "over_claim_index": round(v, 4),
                     "percentile": pct, "note": "low_evidence" if low else ""})
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_DIR / "part3_validity_contested.csv", index=False)
    return out


# --- diversity hard-facts -----------------------------------------------------

class BoardDiversity(BaseModel):
    n_directors: int = Field(description="Total number of director nominees on the board, as disclosed. 0 if not found.")
    n_women: int = Field(description="Number of those directors who are women. 0 if not found.")
    n_racially_ethnically_diverse: int = Field(description="Number who are racially or ethnically diverse. 0 if not disclosed.")
    disclosed: bool = Field(description="True only if the proxy explicitly discloses board gender/ethnic composition.")


_BOARD_CUE = re.compile(
    r"\b(board|director|nominee|women|woman|gender|ethnic|raciall|diverse|diversity)",
    re.IGNORECASE)


def _board_excerpt(text: str, max_chars: int = 12000) -> str:
    """Paragraphs about board composition (where the diversity matrix / director table lives)."""
    paras = [p for p in re.split(r"\n\s*\n", text) if len(p) > 60]
    scored = sorted(((len(_BOARD_CUE.findall(p)) / len(p), i, p) for i, p in enumerate(paras)
                     if _BOARD_CUE.search(p)), reverse=True)
    chosen, total = [], 0
    for _, i, p in scored:
        if total + len(p) > max_chars:
            continue
        chosen.append((i, p)); total += len(p)
    chosen.sort()
    return "\n\n".join(p for _, p in chosen)


@lru_cache(maxsize=1)
def _client():
    from dotenv import load_dotenv
    from anthropic import Anthropic
    load_dotenv()
    return Anthropic()


def _interim(tk: str, year: int):
    return INTERIM_DIR / f"{tk.replace('.', '_')}_{year}.txt"


def extract_board_diversity(tk: str, year: int) -> BoardDiversity | None:
    p = _interim(tk, year)
    if not p.exists():
        return None
    excerpt = _board_excerpt(p.read_text(encoding="utf-8"))
    system = ("Extract the board-of-directors composition disclosed in this proxy excerpt. "
              "Count director NOMINEES for the upcoming year. Only set disclosed=true if the "
              "proxy explicitly states gender/ethnic composition. Do not guess counts.")
    h = hashlib.sha256(f"boarddiv\n{system}\n{excerpt}".encode()).hexdigest()[:24]
    cache = CACHE_DIR / f"p3board_{h}.json"
    if cache.exists():
        return BoardDiversity(**json.loads(cache.read_text()))
    resp = _client().messages.parse(
        model="claude-haiku-4-5", max_tokens=400, system=system,
        messages=[{"role": "user", "content": excerpt}], output_format=BoardDiversity)
    res: BoardDiversity = resp.parsed_output
    cache.write_text(res.model_dump_json())
    return res


def diversity_hard_facts(tickers: list[str] | None = None) -> pd.DataFrame:
    """Per company-year: website D&I emphasis vs actual disclosed board diversity, then the
    correlation between them (the hard-facts validity test)."""
    web = website_emphasis(tickers).set_index(["ticker", "year"])[_DIV_COL]
    pxy = proxy_emphasis(tickers).set_index(["ticker", "year"])[_DIV_COL]
    rows = []
    for (tk, year) in web.index:
        if (tk, year) not in pxy.index:
            continue
        bd = extract_board_diversity(tk, year)
        if bd is None or not bd.disclosed or bd.n_directors == 0:
            pct_w = pct_d = np.nan
        else:
            pct_w = bd.n_women / bd.n_directors
            pct_d = bd.n_racially_ethnically_diverse / bd.n_directors
        rows.append({"ticker": tk, "year": year,
                     "web_div_emphasis": round(float(web.loc[(tk, year)]), 3),
                     "proxy_div_emphasis": round(float(pxy.loc[(tk, year)]), 3),
                     "board_pct_women": round(pct_w, 3) if pct_w == pct_w else np.nan,
                     "board_pct_diverse": round(pct_d, 3) if pct_d == pct_d else np.nan})
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_DIR / "part3_validity_diversity.csv", index=False)
    return out


def diversity_correlations(df: pd.DataFrame) -> dict:
    """Spearman correlation of stated (website) diversity emphasis vs real board diversity.
    Positive => stated commitment tracks actual diversity (authentic); ~0/neg => cheap talk."""
    d = df.dropna(subset=["board_pct_women"])  # pandas Spearman; no scipy dependency
    out = {"n": int(len(d))}
    if len(d) >= 4:
        out["corr_web_emphasis_vs_pct_women"] = round(
            float(d["web_div_emphasis"].corr(d["board_pct_women"], method="spearman")), 3)
        dd = df.dropna(subset=["board_pct_diverse"])
        out["corr_web_emphasis_vs_pct_diverse"] = round(
            float(dd["web_div_emphasis"].corr(dd["board_pct_diverse"], method="spearman")), 3)
    else:
        out["note"] = "too few disclosed board-diversity cells for a stable correlation"
    return out
