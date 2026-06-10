"""Wayback Machine CDX API client.

One CDX call returns a JSON *array of arrays* (row 0 is the header) describing
every archived snapshot of a URL — metadata only, not the page text. We filter
to HTTP 200 HTML captures in the year window and select one snapshot per year
nearest a fixed anchor date (deterministic + defensible).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode

from .config import load_settings
from .http_client import get_text

_S = load_settings()
_Y0, _Y1 = _S["year_start"], _S["year_end"]
_ANCHOR_MMDD = (_S["anchor_month"], _S["anchor_day"])

CDX_BASE = "https://web.archive.org/cdx/search/cdx"


@dataclass(frozen=True)
class Snapshot:
    timestamp: str  # YYYYMMDDhhmmss
    original: str   # the original (live) URL that was captured
    statuscode: str
    digest: str     # content fingerprint; identical digest == identical bytes

    @property
    def year(self) -> int:
        return int(self.timestamp[:4])

    @property
    def archive_url(self) -> str:
        """Raw archived HTML (the `id_` flag strips Wayback's injected toolbar)."""
        return f"https://web.archive.org/web/{self.timestamp}id_/{self.original}"


def list_snapshots_status(url: str, collapse: str = "timestamp:6",
                          throttle: bool = True) -> tuple[list[Snapshot], bool]:
    """Like `list_snapshots`, but also returns whether the archive RESPONDED.

    Returns (snapshots, responded). `responded` is False ONLY when the request
    itself failed (timeout / connection error / 429-5xx after backoff) — i.e. the
    archive did not answer. A genuine 200-with-no-captures (or a 404) is
    responded=True with an empty list. This lets discovery tell a `timeout` apart
    from a `genuine_miss`.
    """
    query = urlencode(
        {
            "url": url,
            "from": f"{_Y0}",
            "to": f"{_Y1}",
            "filter": "statuscode:200",
            "collapse": collapse,
            "output": "json",
            "fl": "timestamp,original,statuscode,digest",
        }
    )
    # mimetype filter is a second `filter=` param (urlencode can't repeat keys cleanly)
    full = f"{CDX_BASE}?{query}&filter=mimetype:text/html"
    try:
        body, status = get_text(full, throttle=throttle)
    except Exception:
        return [], False  # archive did not respond -> caller marks this a timeout
    if status != 200 or not body.strip():
        return [], True   # responded, but no usable data
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return [], True
    if not rows or len(rows) < 2:
        return [], True
    idx = {name: i for i, name in enumerate(rows[0])}
    out = [
        Snapshot(
            timestamp=r[idx["timestamp"]],
            original=r[idx["original"]],
            statuscode=r[idx["statuscode"]],
            digest=r[idx["digest"]],
        )
        for r in rows[1:]
    ]
    return out, True


def list_snapshots(url: str, collapse: str = "timestamp:6",
                   throttle: bool = True) -> list[Snapshot]:
    """All HTTP-200 HTML snapshots of `url` within the year window (one per ~month)."""
    return list_snapshots_status(url, collapse, throttle)[0]


def _anchor_distance(ts: str) -> int:
    """Days-ish distance from the anchor date within that snapshot's year."""
    month, day = int(ts[4:6]), int(ts[6:8])
    am, ad = _ANCHOR_MMDD
    return abs((month - am) * 31 + (day - ad))


def one_per_year(snaps: list[Snapshot]) -> dict[int, Snapshot]:
    """Pick, for each year, the snapshot closest to the anchor date."""
    by_year: dict[int, Snapshot] = {}
    for s in snaps:
        if not (_Y0 <= s.year <= _Y1):
            continue
        cur = by_year.get(s.year)
        if cur is None or _anchor_distance(s.timestamp) < _anchor_distance(cur.timestamp):
            by_year[s.year] = s
    return by_year
