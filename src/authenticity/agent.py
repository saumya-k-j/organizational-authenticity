"""Step-E discovery agent — scoped to MISSING-YEAR RECOVERY.

The one justified agent in the pipeline. For a company whose grid shows missing
years, it investigates whether a DIFFERENT url/host has those years, using two
deterministic tools, then submits a finding. The harness then RE-VERIFIES the
submitted URL with a real coverage query before accepting anything — so the agent
can only ever fill a cell from a real archived snapshot, never invent one.

Tools given to the model:
  - cdx_host_candidates(host): ranked values-page paths archived on that host
  - url_coverage(url): which of 2016-2024 that URL actually has snapshots for
  - submit_finding(best_url, covered_years, reason_for_gaps, reasoning): finish

Gentle: tools go through the throttled, cached HTTP layer. Bounded: a hard
per-company iteration cap. Auditable: every finding + the model's reasoning is
logged to logs/agent_reasoning.jsonl.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import re

from .config import LOG_DIR, load_settings
from .discovery import _excluded, _host_query_paths, _rank_paths, coverage_status

# A URL may fill cells only if it is plausibly an About/values page. Broader than
# discovery's path-only rule (the agent legitimately finds about.google,
# aboutamazon.com, /our-firm), but still blocks junk via the exclusion list
# (/b/ product browse, facebook.com profiles, jobs, file types).
_HOST_SIGNAL = re.compile(r"(^|\.)(about|values|whoweare|ourpurpose|purpose)")
_SEG_KW = ["about", "who-we-are", "values", "mission", "purpose",
           "company", "firm", "story", "overview", "identity"]
_SEG_SIGNAL = re.compile(r"^(?:our-|the-)?(" + "|".join(_SEG_KW) + r")(?:[-./]|$)")


def _acceptable(url: str) -> bool:
    if _excluded(url):
        return False
    host, _, rest = url.partition("/")
    if _HOST_SIGNAL.search(host.lower()):
        return True
    return any(_SEG_SIGNAL.match(s) for s in rest.lower().split("/") if s)

_S = load_settings()
_Y0, _Y1 = _S["year_start"], _S["year_end"]
_YEARS = list(range(_Y0, _Y1 + 1))
_MODEL = _S["llm"]["agent_model"]
_MAX_ITERS = _S["llm"]["agent_max_iters"]


def tool_cdx_host_candidates(host: str) -> dict:
    paths, responded = _host_query_paths(host)
    return {"responded": responded, "candidates": _rank_paths(paths)[:10]}


def tool_url_coverage(url: str) -> dict:
    snaps, responded = coverage_status(url)
    return {"responded": responded, "years": sorted(snaps.keys()),
            "looks_like_values_page": _acceptable(url)}


_TOOLS = [
    {
        "name": "cdx_host_candidates",
        "description": "List the ranked About/values-page paths the web archive has for a "
                       "given host (e.g. 'corporate.chevron.com', 'about.salesforce.com', "
                       "'chevron.com'). Use to discover alternate hosts/paths for a company.",
        "input_schema": {
            "type": "object",
            "properties": {"host": {"type": "string", "description": "Host, no scheme."}},
            "required": ["host"],
        },
    },
    {
        "name": "url_coverage",
        "description": "Return which years (2016-2024) the archive actually has snapshots "
                       "for a specific URL. This is how you CONFIRM a URL fills missing years.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Host+path, no scheme."}},
            "required": ["url"],
        },
    },
    {
        "name": "submit_finding",
        "description": "Submit your conclusion once you've investigated. List ALL the URLs you "
                       "verified with url_coverage that together cover the missing years — "
                       "different years may live at different paths (e.g. an old /who-we-are "
                       "plus a newer /about/who-we-are). The harness unions their real coverage. "
                       "Submit only URLs a url_coverage call actually returned years for.",
        "input_schema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Confirmed URLs (host+path, no scheme) covering missing years. "
                                   "Empty if nothing beats the current URL.",
                },
                "is_canonical": {
                    "type": "boolean",
                    "description": "True if the primary page is a main corporate About/values "
                                   "page; False if it's a sub-brand/regional/section page chosen "
                                   "only because the canonical hosts are absent from the archive.",
                },
                "non_canonical_note": {
                    "type": "string",
                    "description": "If is_canonical is False, briefly why (e.g. 'sub-brand "
                                   "/aviation page; corporate.* empty in archive'). Else ''.",
                },
                "reason_for_gaps": {
                    "type": "string",
                    "description": "no_capture | broken_snapshot | redirect | host_wrong | other",
                },
                "reasoning": {"type": "string", "description": "What you tried and concluded."},
            },
            "required": ["urls", "is_canonical", "non_canonical_note",
                         "reason_for_gaps", "reasoning"],
        },
    },
]

_DISPATCH = {"cdx_host_candidates": tool_cdx_host_candidates, "url_coverage": tool_url_coverage}


def _prompt(name: str, domain: str, current_url: str | None, covered: list[int]) -> str:
    missing = [y for y in _YEARS if y not in covered]
    return (
        f"Company: {name} (domain {domain}).\n"
        f"Current best values URL: {current_url or '(none found)'}\n"
        f"Years already covered: {covered or 'none'}\n"
        f"MISSING years to recover: {missing}\n\n"
        "Find whether a different host or path for THIS company has the missing years' "
        "About/values page. Try plausible corporate hosts (corporate.<domain>, "
        "about.<domain>, the bare <domain>, regional variants) with cdx_host_candidates, "
        "and confirm candidates with url_coverage. Different missing years may live at "
        "different paths — collect EVERY url that covers some missing year (the harness unions "
        "them). Prefer canonical corporate About/values pages; if only a sub-brand/regional "
        "page exists in the archive, you may use it but set is_canonical=False with a note. "
        "Then call submit_finding with all confirmed urls. Only include urls a url_coverage "
        "call actually returned years for. If nothing beats the current URL, submit empty urls "
        "and explain the gap with a reason code."
    )


def _log(rec: dict) -> None:
    rec["t"] = datetime.now(timezone.utc).isoformat()
    with (LOG_DIR / "agent_reasoning.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")


def recover_company(client, name: str, ticker: str, domain: str,
                    current_url: str | None, covered: list[int]) -> dict:
    """Run the agent for one company; RE-VERIFY its pick; return the accepted result.

    Returns {ticker, best_url, covered_years (verified), reason_for_gaps, reasoning,
             source: 'agent'|'kept_current'}.
    """
    messages = [{"role": "user", "content": _prompt(name, domain, current_url, covered)}]
    finding = None
    rounds = 0
    urls_tried: list[str] = []
    for _ in range(_MAX_ITERS):
        rounds += 1
        resp = client.messages.create(
            model=_MODEL, max_tokens=4000, tools=_TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            break
        results = []
        for tu in tool_uses:
            if tu.name == "submit_finding":
                finding = tu.input
            elif tu.name == "url_coverage":
                urls_tried.append(tu.input.get("url", ""))
            elif tu.name == "cdx_host_candidates":
                urls_tried.append("host:" + tu.input.get("host", ""))
            fn = _DISPATCH.get(tu.name)
            out = fn(**tu.input) if fn else {"ok": True}
            results.append({"type": "tool_result", "tool_use_id": tu.id,
                            "content": json.dumps(out)})
        messages.append({"role": "user", "content": results})
        if finding is not None:
            break

    # If it never submitted (hit the iter cap or ended early), force a final submit.
    hit_cap = finding is None
    if finding is None:
        messages.append({"role": "user", "content":
                         "Stop investigating and call submit_finding now with the best "
                         "URLs you have confirmed (or empty urls if none beat the current)."})
        try:
            resp = client.messages.create(
                model=_MODEL, max_tokens=2000, tools=_TOOLS,
                tool_choice={"type": "tool", "name": "submit_finding"}, messages=messages,
            )
            for b in resp.content:
                if b.type == "tool_use" and b.name == "submit_finding":
                    finding = b.input
        except Exception:
            pass

    # Harness verification: re-run url_coverage on every candidate, KEEP ONLY URLs that
    # pass the values-page rules, and UNION their real coverage. A junk page (product
    # category, social profile, sub-brand with no About segment) can never fill a cell.
    finding = finding or {}
    candidates = list(dict.fromkeys(
        ([current_url] if current_url else []) + list(finding.get("urls", []))
    ))
    url_years: dict[str, list[int]] = {}
    for u in candidates:
        if not _acceptable(u):
            continue
        snaps, responded = coverage_status(u)
        if responded and snaps:
            url_years[u] = sorted(snaps.keys())

    per_year: dict[int, str] = {}
    for u in sorted(url_years, key=lambda u: (-len(url_years[u]), u)):
        for y in url_years[u]:
            per_year.setdefault(y, u)
    union = sorted(per_year)
    primary = max(url_years, key=lambda u: len(url_years[u])) if url_years else None

    result = {
        "ticker": ticker,
        "best_url": primary,
        "covered_years": union,
        "per_year_url": {str(y): u for y, u in sorted(per_year.items())},
        "is_canonical": bool(finding.get("is_canonical", True)),
        "non_canonical_note": finding.get("non_canonical_note", ""),
        "reason_for_gaps": finding.get("reason_for_gaps", "no_capture"),
        "reasoning": finding.get("reasoning", "agent did not submit a finding"),
        "rounds": rounds,
        "urls_tried": urls_tried,
        "hit_cap": hit_cap,
        "source": "agent" if url_years else "none",
    }
    _log({"event": "recover", **{k: result[k] for k in
          ("ticker", "best_url", "covered_years", "is_canonical", "non_canonical_note",
           "reason_for_gaps", "rounds", "urls_tried", "hit_cap", "source", "reasoning")}})
    return result
