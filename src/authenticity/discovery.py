"""Deterministic values-page discovery, one CDX query per company.

Query shape was chosen empirically against the live archive: `matchType=domain`
scans the whole domain index and times out on heavily-archived sites (microsoft.com
never returned); `matchType=host` with a server-side urlkey keyword filter,
`collapse=urlkey`, and a *small* `limit` returns the canonical About/values paths
cheaply (a large limit makes the server scan deep and time out on sites like
nike.com). Paths are then ranked locally and the best is kept; coverage is confirmed
downstream in pipeline. No LLM here — that's reserved for the residual misses.

Concurrency is a bounded thread pool. 50 -> 500 is a config change, not a rewrite.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from urllib.parse import urlencode

from .cdx import Snapshot, list_snapshots_status, one_per_year
from .config import Company, LOG_DIR, load_settings

_S = load_settings()
_D = _S["discovery"]
_Y0, _Y1 = _S["year_start"], _S["year_end"]
_MIN_YEARS = _D["min_years_covered"]
_CONCURRENCY = _D["concurrency"]
_LIMIT = _D["query_limit"]
_KW_REGEX = _D["keyword_regex"]
_PRIORITY = _D["keywords_priority"]
_EXCLUDE = _D["exclude"]
_HOSTS = _D.get("hosts", ["www."])

CDX_BASE = "https://web.archive.org/cdx/search/cdx"


@dataclass
class DiscoveryResult:
    ticker: str
    resolved_by: str         # override|prefix_filter|low_coverage|genuine_miss|timeout|agent
    chosen_url: str | None
    years_covered: int
    n_candidate_paths: int
    candidates: list = field(default_factory=list)   # [[url, ...], ...] top-ranked paths
    covered_years: list = field(default_factory=list)  # which years have a snapshot (for grid)


def _normalize(original: str) -> str:
    """`http://www.x.com:80/About?q=1#f` -> `www.x.com/about` (host+path, query/frag dropped)."""
    no_scheme = original.split("://", 1)[-1].replace(":80", "").replace(":443", "")
    no_query = no_scheme.split("?", 1)[0].split("#", 1)[0].lower()
    return no_query.rstrip("/") or no_query


def _host_query_paths(host: str) -> tuple[set[str], bool]:
    """One host query -> (normalized candidate paths, responded).

    responded=False means the archive did not answer (timeout) — distinct from
    answering with no candidate paths (a genuine miss). Throttled (gentle).
    """
    from .http_client import get_text
    params = [
        ("url", host), ("matchType", "host"),
        ("from", str(_Y0)), ("to", str(_Y1)),
        ("filter", "statuscode:200"),
        ("filter", f"urlkey:.*({_KW_REGEX}).*"),
        ("collapse", "urlkey"),
        ("output", "json"),
        ("fl", "original"),
        ("limit", str(_LIMIT)),
    ]
    url = f"{CDX_BASE}?{urlencode(params)}"
    try:
        body, status = get_text(url)  # throttled by default (gentle)
    except Exception:
        return set(), False  # archive did not respond -> timeout
    if status != 200 or not body.strip():
        return set(), True
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        return set(), True
    return {_normalize(r[0]) for r in (rows[1:] if len(rows) > 1 else [])}, True


# A keyword qualifies only when it BEGINS a path segment (optionally after an
# `our-`/`the-` prefix), so `/about-us`, `/our-values`, `/company-info` win but
# `/gaming-company`, `/...-mission-road`, `/see-what-were-all-about` (keyword
# buried mid/end-slug) do NOT. Kills the HD/VLO-style junk picks at the rule level.
_KW_ALT = "|".join(re.escape(k) for k in _PRIORITY)
_SEG_RE = re.compile(rf"^(?:our-|the-)?({_KW_ALT})(?:[-.]|$)")


def _segments(path: str) -> list[str]:
    after_host = path.split("/", 1)[1] if "/" in path else ""
    return [s for s in after_host.lower().split("/") if s]


def _segment_priority(path: str) -> int | None:
    """Best (lowest) priority index among qualifying segments, or None if none qualify."""
    best: int | None = None
    for seg in _segments(path):
        m = _SEG_RE.match(seg)
        if m:
            idx = _PRIORITY.index(m.group(1))
            best = idx if best is None else min(best, idx)
    return best


def _is_token_match(path: str) -> bool:
    return _segment_priority(path) is not None


def _priority(path: str) -> int:
    p = _segment_priority(path)
    return p if p is not None else len(_PRIORITY)


def _excluded(path: str) -> bool:
    p = path.lower()
    return any(x in p for x in _EXCLUDE)


def _depth(path: str) -> int:
    """Number of non-empty path segments after the host (canonical pages are shallow)."""
    after_host = path.split("/", 1)[1] if "/" in path else ""
    return len([seg for seg in after_host.split("/") if seg])


def _rank_paths(paths: set[str]) -> list[str]:
    """Best-first candidate URLs.

    Depth FIRST: a shallow `/about` beats a deep `/caring/.../people-and-values`
    even though the latter contains the higher-priority keyword "values". Then
    keyword priority, then shortest. The coverage-confirm step falls through this
    ordering, so a sparse shallow page (e.g. a /about with one year) is skipped in
    favour of the next candidate.
    """
    cands = [p for p in paths if _is_token_match(p) and not _excluded(p)]
    cands.sort(key=lambda p: (_depth(p), _priority(p), len(p)))
    return cands


def _resolve_one(company: Company) -> DiscoveryResult:
    """Resolve the values URL from one host query. The outcome distinguishes a
    `timeout` (archive didn't answer) from a `genuine_miss` (answered, no values
    page) so the agent never chases a question the archive simply didn't answer.
    Coverage is measured later in the gentle serial pass, never here."""
    if company.values_url:                   # human pin: trust it, skip discovery
        return DiscoveryResult(company.ticker, "override", company.values_url,
                               0, 1, [company.values_url])

    paths: set[str] = set()
    responded = False
    for sub in _HOSTS:
        p, ok = _host_query_paths(f"{sub}{company.domain}")
        responded = responded or ok
        paths |= p

    if not responded:
        return DiscoveryResult(company.ticker, "timeout", None, 0, 0, [])

    ranked = _rank_paths(paths)
    if ranked:
        return DiscoveryResult(company.ticker, "prefix_filter", ranked[0],
                               0, len(ranked), ranked[:10])
    return DiscoveryResult(company.ticker, "genuine_miss", None, 0, 0, [])


def resolve_all(companies: list[Company]) -> dict[str, DiscoveryResult]:
    """Resolve every company's values URL with bounded (gentle) concurrency."""
    with ThreadPoolExecutor(max_workers=_CONCURRENCY) as pool:
        out = list(pool.map(_resolve_one, companies))
    return {c.ticker: r for c, r in zip(companies, out)}


def coverage_status(url: str) -> tuple[dict[int, Snapshot], bool]:
    """(per-year snapshot map, responded) — serial, throttled, cached."""
    snaps, responded = list_snapshots_status(url)
    return one_per_year(snaps), responded


def coverage(url: str) -> dict[int, Snapshot]:
    return coverage_status(url)[0]


def write_misses(results: list[DiscoveryResult]) -> None:
    """Agent targets (genuine_miss + low_coverage) -> misses file; timeout -> retry file."""
    targets = [asdict(r) for r in results
               if r.resolved_by in ("genuine_miss", "low_coverage")]
    timeouts = [asdict(r) for r in results if r.resolved_by == "timeout"]
    (LOG_DIR / "discovery_misses.json").write_text(json.dumps(targets, indent=2))
    (LOG_DIR / "discovery_timeouts.json").write_text(json.dumps(timeouts, indent=2))


def write_results(results: list[DiscoveryResult]) -> None:
    """Persist the FULL discovery state so downstream steps (grid, retries) reuse it
    without re-querying the archive."""
    (LOG_DIR / "discovery_results.json").write_text(
        json.dumps([asdict(r) for r in results], indent=2)
    )


def load_results() -> dict[str, dict]:
    path = LOG_DIR / "discovery_results.json"
    if not path.exists():
        return {}
    return {d["ticker"]: d for d in json.loads(path.read_text())}
