"""LLM-assisted tagging of a proxy statement — the selective, semantic half of analysis.

The classical pass (textstats.py) handles the full corpus deterministically. The LLM is
reserved for two judgments classical methods do poorly, on a bounded values-relevant
EXCERPT (not the whole 300k-char proxy — that would be slow, costly, and mostly
compensation tables):

  1. present/dominant value themes against Part 1's FROZEN 13-theme taxonomy — semantic,
     so it catches a theme expressed without its dictionary keywords. Same taxonomy as
     Part 1, so the "stated" (web) and "disclosed" (proxy) channels are comparable.
  2. stakeholder_orientation — does the proxy frame the company's purpose around
     shareholder primacy, a balance, or a broad stakeholder set? This is the proxy-side
     test of Part 1's headline shareholder->stakeholder shift.

Responses are cached by hash(model + system + excerpt), exactly like Part 1's tagging,
so reruns are free and a re-tag only re-hits genuinely new text.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field

from .config import CACHE_DIR, load_lexicon, load_settings, load_taxonomy

_S = load_settings()
_MODEL = _S["llm"]["classify_model"]
_MAX_TOKENS = _S["llm"]["max_tokens"]
_EXCERPT_MAX = _S["analysis"]["excerpt_max_chars"]


class ProxyTagging(BaseModel):
    """Structured result of tagging one proxy statement's values-relevant excerpt."""
    present_theme_keys: list[str] = Field(
        description="Taxonomy keys for every value theme the excerpt clearly expresses."
    )
    dominant_theme_key: str = Field(
        description="The single most-emphasized theme key (must be one of present_theme_keys)."
    )
    stakeholder_orientation: Literal[
        "shareholder_primacy", "balanced", "stakeholder_oriented"
    ] = Field(
        description=(
            "How the excerpt frames the company's purpose/governance: 'shareholder_primacy' "
            "if returns to shareholders dominate; 'stakeholder_oriented' if employees, "
            "communities, environment, customers are foregrounded as ends; 'balanced' if both."
        )
    )
    summary: str = Field(
        description="One plain-language sentence: what values this proxy foregrounds."
    )


@lru_cache(maxsize=1)
def _taxonomy_block() -> tuple[str, frozenset[str]]:
    tax = load_taxonomy()
    lines, keys = [], []
    for t in tax["themes"]:
        lines.append(f"- {t['key']}: {t['label']} — {t['desc']}")
        keys.append(t["key"])
    return "\n".join(lines), frozenset(keys)


@lru_cache(maxsize=1)
def _cue_regex():
    lex = load_lexicon()
    cues = list(lex["excerpt_cues"])
    for terms in lex["theme_terms"].values():
        cues.extend(terms)
    parts = sorted((re.escape(c) for c in set(cues)), key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(parts) + r")", re.IGNORECASE)


def values_excerpt(text: str, max_chars: int = _EXCERPT_MAX) -> str:
    """Concatenate the paragraphs richest in value-cue terms, up to max_chars.

    A proxy is mostly governance/compensation mechanics; value language is concentrated
    in a minority of paragraphs. We rank paragraphs by cue-term density and keep the top
    ones (restored to document order) so the LLM sees the values-relevant signal, not the
    audit-fee tables."""
    rx = _cue_regex()
    paras = [p for p in re.split(r"\n\s*\n", text) if len(p) > 120]
    scored = []
    for i, p in enumerate(paras):
        hits = len(rx.findall(p))
        if hits:
            scored.append((hits / len(p), i, p))   # density, not raw count (avoid long-para bias)
    scored.sort(reverse=True)
    chosen, total = [], 0
    for _, i, p in scored:
        if total + len(p) > max_chars:
            continue
        chosen.append((i, p))
        total += len(p)
        if total >= max_chars:
            break
    chosen.sort()  # restore document order for readability
    return "\n\n".join(p for _, p in chosen)


def _system_prompt() -> str:
    block, _ = _taxonomy_block()
    return (
        "You analyze excerpts from a U.S. public company's annual proxy statement "
        "(SEC form DEF 14A). Classify the company's expressed VALUES against this FIXED "
        "taxonomy. Use ONLY these theme keys:\n\n"
        f"{block}\n\n"
        "Rules: include a theme only if the excerpt clearly expresses it (not a passing "
        "mention). dominant_theme_key must be one of present_theme_keys. Judge "
        "stakeholder_orientation from how purpose/governance is framed. Keep the summary "
        "to one plain sentence. Do not invent keys."
    )


@lru_cache(maxsize=1)
def _client():
    from dotenv import load_dotenv
    from anthropic import Anthropic
    load_dotenv()
    return Anthropic()


def _cache_file(model: str, system: str, text: str):
    h = hashlib.sha256(f"{model}\n{system}\n{text}".encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"p2tag_{h}.json"


def classify_proxy(full_text: str, model: str | None = None) -> ProxyTagging:
    """Tag one proxy's values-relevant excerpt. Cached by (model, prompt, excerpt)."""
    model = model or _MODEL
    excerpt = values_excerpt(full_text)
    system = _system_prompt()
    cache = _cache_file(model, system, excerpt)
    if cache.exists():
        return ProxyTagging(**json.loads(cache.read_text()))

    resp = _client().messages.parse(
        model=model,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": f"Proxy excerpt:\n\n{excerpt}"}],
        output_format=ProxyTagging,
    )
    result: ProxyTagging = resp.parsed_output

    _, valid = _taxonomy_block()
    result.present_theme_keys = [k for k in result.present_theme_keys if k in valid]
    if result.dominant_theme_key not in valid and result.present_theme_keys:
        result.dominant_theme_key = result.present_theme_keys[0]

    cache.write_text(result.model_dump_json())
    return result
