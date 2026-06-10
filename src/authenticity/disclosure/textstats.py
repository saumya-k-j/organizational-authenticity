"""Classical (no-LLM) text statistics for a proxy statement.

This is the deterministic, reproducible, full-corpus half of the analysis. It runs on
EVERY filing's complete text (proxies are 200-400k chars; an LLM pass over all of that
for 450 filings would be slow, costly and non-deterministic). It produces:

  - theme frequencies: per-1k-word counts of each Part-1 value theme via the frozen
    keyword lexicon -> directly comparable to Part 1's "stated values" channel.
  - tone: positive / negative / uncertainty per 1k words (LM-style), plus net_tone.
  - readability: Flesch reading ease + mean sentence length (proxy complexity/legalese).
  - sizes: word and sentence counts (proxies have ballooned over the decade — a finding
    in itself).

Why classical here and LLM elsewhere (see llmtag.py): dictionary counts are transparent,
free, and identical on every rerun, which is what you want for a 450-filing time series.
The LLM is reserved for the semantic judgment classical methods do badly — mapping prose
onto themes it doesn't lexically name, and rating shareholder-vs-stakeholder framing.
"""
from __future__ import annotations

import re
from functools import lru_cache

from .config import load_lexicon

_WORD = re.compile(r"[A-Za-z']+")
_SENT = re.compile(r"[.!?]+")
_VOWEL_GROUP = re.compile(r"[aeiouy]+")


@lru_cache(maxsize=1)
def _compiled_lexicon():
    """Compile each lexicon list to one regex. Stems match on a LEFT word boundary only
    (so 'innovat' catches innovation/innovative) — multi-word cues keep their spaces."""
    lex = load_lexicon()
    def compile_terms(terms):
        # longest-first so multi-word phrases match before their constituent stems
        parts = sorted((re.escape(t) for t in terms), key=len, reverse=True)
        return re.compile(r"\b(?:" + "|".join(parts) + r")", re.IGNORECASE)
    themes = {k: compile_terms(v) for k, v in lex["theme_terms"].items()}
    tone = {k: compile_terms(lex[f"tone_{k}"]) for k in ("positive", "negative", "uncertainty")}
    return themes, tone


def _syllables(word: str) -> int:
    # Approximate: count vowel groups, drop a silent trailing 'e', floor at 1.
    w = word.lower()
    n = len(_VOWEL_GROUP.findall(w))
    if w.endswith("e") and n > 1:
        n -= 1
    return max(n, 1)


def text_stats(text: str) -> dict:
    """All classical metrics for one filing as a flat dict (theme_* / tone_* / etc.)."""
    words = _WORD.findall(text)
    n_words = len(words)
    n_sents = max(len(_SENT.findall(text)), 1)
    themes, tone = _compiled_lexicon()
    per_k = (1000.0 / n_words) if n_words else 0.0

    out: dict[str, float | int | str] = {"n_words": n_words, "n_sentences": n_sents}

    theme_freqs = {}
    for key, rx in themes.items():
        freq = len(rx.findall(text)) * per_k
        theme_freqs[key] = round(freq, 3)
        out[f"theme_{key}"] = theme_freqs[key]
    out["dominant_theme_classical"] = max(theme_freqs, key=theme_freqs.get) if theme_freqs else ""
    # A proxy's literal purpose is electing directors and approving pay, so governance and
    # shareholder-return language is STRUCTURAL — it saturates dominant_theme on every
    # filing. The discretionary values emphasis is the leading theme once those two
    # genre-baseline themes are set aside; that's the more informative comparison signal.
    discretionary = {k: v for k, v in theme_freqs.items()
                     if k not in ("leadership_governance", "profitable_growth")}
    out["dominant_theme_distinctive"] = max(discretionary, key=discretionary.get) if discretionary else ""

    pos = len(tone["positive"].findall(text)) * per_k
    neg = len(tone["negative"].findall(text)) * per_k
    unc = len(tone["uncertainty"].findall(text)) * per_k
    out["tone_positive"] = round(pos, 3)
    out["tone_negative"] = round(neg, 3)
    out["tone_uncertainty"] = round(unc, 3)
    out["net_tone"] = round((pos - neg) / (pos + neg), 3) if (pos + neg) else 0.0

    syl = sum(_syllables(w) for w in words) if n_words else 0
    out["avg_sentence_len"] = round(n_words / n_sents, 2)
    # Flesch reading ease (higher = easier). Approximate syllables; documented limitation.
    out["flesch_reading_ease"] = round(
        206.835 - 1.015 * (n_words / n_sents) - 84.6 * (syl / n_words), 1
    ) if n_words else 0.0
    return out
