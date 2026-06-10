"""Extract the meaningful page text from archived HTML.

trafilatura strips nav/header/footer/boilerplate and returns the main content.
This is a deterministic library call — no LLM. (A small LLM cleanup pass could
be added later for the handful of pages trafilatura mangles.)
"""
from __future__ import annotations

import ftfy
import trafilatura


def clean_html(html: str) -> str | None:
    """Return cleaned main-content text, or None if nothing extractable.

    Runs ftfy to repair any residual encoding mojibake (the fetch layer already
    decodes with the detected charset; ftfy is the belt-and-suspenders pass)."""
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_recall=True,  # values pages are short; keep more rather than less
    )
    if not text:
        return None
    return ftfy.fix_text(text).strip()
