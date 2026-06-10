from __future__ import annotations

from .cdx import Snapshot
from .http_client import get_text


def fetch_html(snap: Snapshot) -> str | None:
    body, status = get_text(snap.archive_url)
    if status != 200 or not body.strip():
        return None
    return body
