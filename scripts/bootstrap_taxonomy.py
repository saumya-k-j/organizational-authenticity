#!/usr/bin/env python3
"""Propose a value-theme taxonomy from a SAMPLE of real cleaned pages.

Run this AFTER a scraping-only pass has populated data/interim/ with cleaned
text. It shows a strong model (Opus) a sample of real pages and asks it to
propose a compact, mutually-distinct taxonomy. You then review its proposal,
edit config/taxonomy.yaml by hand, bump `version`, and FREEZE it — every
snapshot is classified against that frozen list.

  python scripts/bootstrap_taxonomy.py --sample 25
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authenticity.config import INTERIM_DIR, load_settings  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=25, help="How many pages to sample")
    args = ap.parse_args()

    files = sorted(INTERIM_DIR.glob("*.txt"))
    if not files:
        print("No cleaned pages in data/interim/. Run run_part1.py --no-tagging first.")
        return
    # Deterministic, spread-out sample (every k-th file).
    step = max(1, len(files) // args.sample)
    sample = files[::step][: args.sample]
    corpus = "\n\n=====\n\n".join(
        f"[{f.stem}]\n{f.read_text(encoding='utf-8')[:2500]}" for f in sample
    )

    from dotenv import load_dotenv
    from anthropic import Anthropic
    load_dotenv()
    model = load_settings()["llm"]["reason_model"]

    prompt = (
        "Below are excerpts from the public 'About/values' pages of several large "
        "companies. Propose a COMPACT taxonomy of value themes (aim for 8-12) that "
        "is mutually distinct and collectively covers what these pages express. "
        "For each theme give: a short snake_case key, a label, and a one-line "
        "definition. Output as YAML matching this shape:\n"
        "themes:\n  - key: ...\n    label: ...\n    desc: ...\n\n"
        f"PAGES:\n{corpus[:60000]}"
    )
    resp = Anthropic().messages.create(
        model=model,
        max_tokens=2000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    print("# Proposed taxonomy (review, edit config/taxonomy.yaml, then freeze):\n")
    print(text)


if __name__ == "__main__":
    main()
