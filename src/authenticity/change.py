"""Year-over-year change detection, deterministic. The CDX digest gives an
identical-bytes check for free (no download, no LLM); difflib catches pages that
differ in bytes but not in substance. The LLM is only spent to characterize a
change once one is flagged."""
from __future__ import annotations

import difflib


def text_similarity(prev_text: str | None, cur_text: str | None) -> float | None:
    if not prev_text or not cur_text:
        return None
    return round(difflib.SequenceMatcher(None, prev_text, cur_text).ratio(), 4)


def changed_from_prev(
    prev_digest: str | None,
    cur_digest: str | None,
    prev_text: str | None,
    cur_text: str | None,
    sim_threshold: float = 0.95,
) -> bool | None:
    """True if the page meaningfully changed from the prior year, else False/None."""
    if prev_digest is None or prev_text is None:
        return None  # no prior year to compare against
    if cur_digest is not None and prev_digest == cur_digest:
        return False  # byte-identical
    sim = text_similarity(prev_text, cur_text)
    if sim is None:
        return None
    return sim < sim_threshold
