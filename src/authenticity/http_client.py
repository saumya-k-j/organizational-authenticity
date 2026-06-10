"""Polite, cached HTTP layer.

- Identifies itself with a User-Agent on every request.
- Rate-limits requests to a host (Wayback throttles aggressive clients).
- Retries transient failures with exponential backoff (tenacity).
- Caches every successful GET body on disk keyed by sha256(url), so reruns are
  free and deterministic. This directly supports the "transparency / reproducible
  process" requirement.
"""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import CACHE_DIR, load_settings

_SETTINGS = load_settings()
_UA = _SETTINGS["user_agent"]
_TIMEOUT = _SETTINGS["request_timeout_seconds"]
_MAX_RETRIES = _SETTINGS["max_retries"]
_MIN_INTERVAL = _SETTINGS["wayback_min_interval_seconds"]

_session = requests.Session()
_session.headers.update({"User-Agent": _UA})

_last_request_at = 0.0  # module-level throttle clock
_throttle_lock = threading.Lock()  # serialises the throttle clock across threads


def _cache_path(url: str, suffix: str) -> Path:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{h}{suffix}"


def _throttle() -> None:
    """Enforce a minimum inter-request gap. Used for SERIAL paths only; the
    concurrent discovery sweep instead bounds politeness via a thread-pool cap
    (throttle=False) so requests can overlap."""
    global _last_request_at
    with _throttle_lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


class HTTPError(Exception):
    """Raised on a non-2xx response that survived retries."""


@retry(
    retry=retry_if_exception_type((requests.RequestException, HTTPError)),
    stop=stop_after_attempt(_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _get(url: str, throttle: bool = True) -> requests.Response:
    if throttle:
        _throttle()
    resp = _session.get(url, timeout=_TIMEOUT, allow_redirects=True)
    # 404/410 are "real" answers (page genuinely absent) — don't retry those.
    if resp.status_code in (429,) or resp.status_code >= 500:
        raise HTTPError(f"{resp.status_code} for {url}")
    # When the server declares no charset, requests defaults to ISO-8859-1, which
    # mis-decodes UTF-8 archived HTML into mojibake. Use the detected encoding instead.
    if resp.status_code == 200 and (resp.encoding or "").lower() in ("", "iso-8859-1"):
        detected = resp.apparent_encoding
        if detected:
            resp.encoding = detected
    return resp


def get_text(url: str, use_cache: bool = True, throttle: bool = True) -> tuple[str, int]:
    """GET a URL, returning (body_text, status_code). Caches the body on success.

    Set throttle=False when the caller bounds concurrency itself (e.g. the
    discovery thread pool) — politeness then comes from the pool size cap.
    """
    cache = _cache_path(url, ".txt")
    if use_cache and cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace"), 200
    resp = _get(url, throttle=throttle)
    if resp.status_code == 200:
        cache.write_text(resp.text, encoding="utf-8")
    return resp.text, resp.status_code
