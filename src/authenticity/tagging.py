"""Theme tagging against the frozen taxonomy via Claude structured outputs.

Every page uses the same frozen prompt + schema, so labels are comparable across
companies and years. Responses are cached by hash(model+prompt+text), so reruns are
free and deterministic and a frozen-taxonomy re-tag only re-hits genuinely new text.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache

from pydantic import BaseModel, Field

from .config import CACHE_DIR, load_settings, load_taxonomy

_LLM = load_settings()["llm"]
_CLASSIFY_MODEL = _LLM["classify_model"]
_MAX_TOKENS = _LLM["max_tokens"]


class ThemeTagging(BaseModel):
    """Structured result of classifying one company-year values page."""
    present_theme_keys: list[str] = Field(
        description="Taxonomy keys for every value theme clearly expressed on the page."
    )
    dominant_theme_key: str = Field(
        description="The single theme the page emphasizes most."
    )
    summary: str = Field(
        description="One sentence: what values this page foregrounds, in plain language."
    )


@lru_cache(maxsize=1)
def _taxonomy_block() -> tuple[str, frozenset[str]]:
    tax = load_taxonomy()
    lines, keys = [], []
    for t in tax["themes"]:
        lines.append(f"- {t['key']}: {t['label']} — {t['desc']}")
        keys.append(t["key"])
    return "\n".join(lines), frozenset(keys)


def _system_prompt() -> str:
    block, _ = _taxonomy_block()
    return (
        "You classify a company's public 'About/values' page against a FIXED "
        "taxonomy of value themes. Use ONLY these theme keys:\n\n"
        f"{block}\n\n"
        "Rules: include a theme only if the page clearly expresses it (not just a "
        "passing word). dominant_theme_key must be one of the present keys. Keep the "
        "summary to one plain-language sentence. Do not invent new keys."
    )


@lru_cache(maxsize=1)
def _client():
    from dotenv import load_dotenv
    from anthropic import Anthropic
    load_dotenv()  # picks up ANTHROPIC_API_KEY from .env
    return Anthropic()


def _cache_file(model: str, system: str, text: str):
    h = hashlib.sha256(f"{model}\n{system}\n{text}".encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"tag_{h}.json"


def classify(text: str, model: str | None = None) -> ThemeTagging:
    """Classify one cleaned values page. Cached by (model, prompt, text)."""
    model = model or _CLASSIFY_MODEL
    system = _system_prompt()
    cache = _cache_file(model, system, text)
    if cache.exists():
        return ThemeTagging(**json.loads(cache.read_text()))

    resp = _client().messages.parse(
        model=model,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": f"Values page text:\n\n{text[:12000]}"}],
        output_format=ThemeTagging,
    )
    result: ThemeTagging = resp.parsed_output

    # Defensively drop any key the model invented despite instructions.
    _, valid_keys = _taxonomy_block()
    result.present_theme_keys = [k for k in result.present_theme_keys if k in valid_keys]
    if result.dominant_theme_key not in valid_keys and result.present_theme_keys:
        result.dominant_theme_key = result.present_theme_keys[0]

    cache.write_text(result.model_dump_json())
    return result
