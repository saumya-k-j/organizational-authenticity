"""SEC EDGAR access layer — the entire "collection" half of Part 2.

Mirrors Part 1's polite-cached-HTTP pattern (User-Agent on every request, rate
limiting, exponential-backoff retry, on-disk cache keyed by sha256(url)). The only
intentional divergence from Part 1's http_client is the politeness profile: EDGAR
documents a ~10 req/s ceiling, so we pace at ~8 req/s instead of Wayback's gentle 2s
gap. Everything is cached, so a rerun touches the network zero times.

Three EDGAR endpoints, all free and key-less:
  1. https://www.sec.gov/files/company_tickers.json   ticker -> CIK
  2. https://data.sec.gov/submissions/CIK##########.json   full filing history
     (+ the older-filing shards it references in filings.files)
  3. https://www.sec.gov/Archives/edgar/data/<cik>/<accession>/<doc>   the filing itself
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import CACHE_DIR, load_settings

_S = load_settings()
_UA = _S["user_agent"]
_TIMEOUT = _S["request_timeout_seconds"]
_MAX_RETRIES = _S["max_retries"]
_MIN_INTERVAL = _S["sec_min_interval_seconds"]
_Y0, _Y1 = _S["year_start"], _S["year_end"]
_Q4 = _S["meeting_year_q4_cutover"]
_FORMS = set(_S["form_types"])
_CIK_OVERRIDES = {k.upper(): v for k, v in (_S.get("cik_overrides") or {}).items()}

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS = "https://data.sec.gov/submissions/{cik}.json"
_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"

_session = requests.Session()
_session.headers.update({"User-Agent": _UA, "Accept-Encoding": "gzip, deflate"})

_last_request_at = 0.0
_throttle_lock = threading.Lock()


class HTTPError(Exception):
    """Non-2xx that survived retries."""


def _throttle() -> None:
    global _last_request_at
    with _throttle_lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _cache_path(url: str, suffix: str) -> Path:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"sec_{h}{suffix}"   # sec_ prefix keeps Part 2 cache distinct


@retry(
    retry=retry_if_exception_type((requests.RequestException, HTTPError)),
    stop=stop_after_attempt(_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)
def _raw_get(url: str) -> requests.Response:
    _throttle()
    resp = _session.get(url, timeout=_TIMEOUT, allow_redirects=True)
    # 429 (rate limited) and 5xx are transient -> retry. 404 is a real "absent" answer.
    if resp.status_code == 429 or resp.status_code >= 500:
        raise HTTPError(f"{resp.status_code} for {url}")
    return resp


def get(url: str, suffix: str, use_cache: bool = True) -> tuple[str, int]:
    """GET a URL, returning (text, status). Caches the body on a 200 keyed by url hash."""
    cache = _cache_path(url, suffix)
    if use_cache and cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace"), 200
    resp = _raw_get(url)
    if resp.status_code == 200:
        cache.write_text(resp.text, encoding="utf-8")
    return resp.text, resp.status_code


# --- 1. ticker -> CIK -------------------------------------------------------

@lru_cache(maxsize=1)
def _ticker_cik_map() -> dict[str, str]:
    """{TICKER -> zero-padded 10-digit CIK} from EDGAR's master ticker file (cached)."""
    body, status = get(_TICKERS_URL, ".json")
    if status != 200:
        raise HTTPError(f"company_tickers.json -> {status}")
    raw = json.loads(body)
    out: dict[str, str] = {}
    for row in raw.values():
        out[row["ticker"].upper()] = f"{int(row['cik_str']):010d}"
    return out


def cik_for_ticker(ticker: str) -> str | None:
    """Resolve a ticker to a 10-digit CIK. EDGAR uses '-' where some sources use '.'
    (BRK.B -> BRK-B), so we try the dotted form, the dashed form, and the base symbol."""
    m = _ticker_cik_map()
    t = ticker.upper()
    for cand in (t, t.replace(".", "-"), t.split(".")[0]):
        if cand in m:
            return m[cand]
    return None


def ciks_for_ticker(ticker: str) -> list[str]:
    """All CIKs to scan for a ticker: an explicit override list (continuing entity +
    predecessor, for mid-window reincorporations) when configured, else the single
    current-registrant CIK from the ticker map."""
    if ticker.upper() in _CIK_OVERRIDES:
        return list(_CIK_OVERRIDES[ticker.upper()])
    c = cik_for_ticker(ticker)
    return [c] if c else []


# --- 2. submissions -> DEF 14A filings --------------------------------------

@dataclass(frozen=True)
class Filing:
    cik: str            # 10-digit
    accession: str      # dashed form, e.g. 0001308179-24-000010
    form: str
    filing_date: str    # YYYY-MM-DD
    primary_doc: str    # e.g. laapl2024_def14a.htm ("" -> fall back to full .txt)
    meeting_year: int   # filing year, +1 when filed in Q4 (see settings)

    @property
    def acc_nodashes(self) -> str:
        return self.accession.replace("-", "")

    @property
    def doc_url(self) -> str:
        doc = self.primary_doc or f"{self.accession}.txt"  # full-submission fallback
        return _ARCHIVE.format(cik=int(self.cik), acc=self.acc_nodashes, doc=doc)


def _meeting_year(filing_date: str) -> int:
    y, m, _ = (int(x) for x in filing_date.split("-"))
    return y + 1 if m >= _Q4 else y


def _iter_submission_blocks(cik: str):
    """Yield each filings block: the inline 'recent' set plus any older shards that
    EDGAR splits out in filings.files (active filers exceed the 1000-row inline cap,
    which for our window matters — the 1000 most-recent rows may not reach 2016)."""
    url = _SUBMISSIONS.format(cik=f"CIK{cik}")
    body, status = get(url, ".json")
    if status != 200:
        raise HTTPError(f"submissions {cik} -> {status}")
    doc = json.loads(body)
    yield doc["filings"]["recent"]
    for f in doc["filings"].get("files", []):
        b, s = get(f"https://data.sec.gov/submissions/{f['name']}", ".json")
        if s == 200:
            yield json.loads(b)


def def14a_filings(cik: str) -> list[Filing]:
    """ALL in-window annual-proxy filings for a CIK (no dedup), oldest first.

    We intentionally do NOT collapse to one-per-year here: in a contested year the
    subject company's EDGAR feed carries both management's DEFC14A and the dissident's
    DEFC14A (e.g. ExxonMobil 2021). Picking the right one needs the cleaned text length,
    which lives in the collection step, so selection happens there — this function just
    returns every candidate."""
    rows: list[Filing] = []
    for blk in _iter_submission_blocks(cik):
        forms = blk["form"]
        for i, form in enumerate(forms):
            if form not in _FORMS:
                continue
            fdate = blk["filingDate"][i]
            my = _meeting_year(fdate)
            if my < _Y0 or my > _Y1:
                continue
            rows.append(Filing(
                cik=cik,
                accession=blk["accessionNumber"][i],
                form=form,
                filing_date=fdate,
                primary_doc=blk["primaryDocument"][i],
                meeting_year=my,
            ))
    rows.sort(key=lambda f: f.filing_date)
    return rows


# Form preference when several candidates share a meeting-year: the plain annual proxy
# outranks the contested-election variant.
FORM_RANK = {"DEF 14A": 0, "DEFC14A": 1}


# --- 3. download the filing document ----------------------------------------

def download_filing(f: Filing, raw_dir: Path, ticker: str) -> tuple[str, str]:
    """Fetch the filing's primary document HTML. Returns (html, doc_url). Caches via
    the URL-hash cache AND writes an explicit raw-layer copy at raw/<TICKER>_<year>.html
    so the raw/clean/structured layering matches Part 1."""
    url = f.doc_url
    body, status = get(url, ".html")
    if status != 200:
        raise HTTPError(f"filing {ticker} {f.meeting_year} -> {status} ({url})")
    raw_path = raw_dir / f"{ticker.replace('.', '_')}_{f.meeting_year}.html"
    raw_path.write_text(body, encoding="utf-8")
    return body, url
