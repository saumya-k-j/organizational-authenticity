"""Proxy-statement HTML -> clean text.

Part 1 used trafilatura because it targets short article-like *web pages*; a DEF 14A
is a 100+ page legal document that is mostly tables (compensation, beneficial
ownership, audit fees). trafilatura's boilerplate-stripping throws away the bulk of a
proxy, so here we extract the full visible text with BeautifulSoup instead and let the
downstream analysis decide what matters. Same ftfy mojibake-repair pass as Part 1.
"""
from __future__ import annotations

import re
import warnings

import ftfy
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# A few proxies are served as XHTML; parsing them with the HTML parser is fine for
# text extraction, so silence bs4's (correct but irrelevant-here) XML notice.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_WS = re.compile(r"[ \t ]+")
_NL = re.compile(r"\n{3,}")


def clean_filing(html: str) -> str | None:
    """Return cleaned visible text of a proxy filing, or None if nothing extractable."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "head", "title"]):
        tag.decompose()
    # Tables hold real content (comp tables, ownership) but render as run-on text; a
    # newline separator keeps rows legible without trying to reconstruct layout.
    text = soup.get_text(separator="\n")
    text = ftfy.fix_text(text)
    # Collapse the ragged whitespace SEC HTML is full of, but preserve paragraph breaks
    # (the excerpt selector and readability metric both work on paragraphs/sentences).
    text = _WS.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _NL.sub("\n\n", text).strip()
    return text or None
