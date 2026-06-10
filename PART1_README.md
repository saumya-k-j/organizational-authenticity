# Organizational Authenticity: Part 1: Stated Values

Recover what 50 large U.S. companies (10 by market cap in each of 5 S&P 500 sectors)
**publicly said they valued**, year by year, 2016–2024, from the Wayback Machine, and
tag each page against a fixed set of value themes. The output is a tidy
company-year dataset of stated values and how they changed.

`PART1.md` is the detailed design log. This README is the structured overview.

---

## What it does (end to end)

```
discover  →  fetch  →  clean  →  change-detect  →  agent-recover  →  tag
```

1. **Discover** the right "About/values" URL per company. One Wayback **CDX host query**
   per company returns the archived About-ish paths. They're ranked locally and the best
   is kept. Companies the query can't resolve are split into `genuine_miss` (archive
   answered, no page) vs `timeout` (archive didn't answer).
2. **Fetch** one archived snapshot per year (nearest a fixed anchor date) as raw HTML.
3. **Clean** to main-content text (trafilatura), with charset-correct decoding plus `ftfy`
   so the text is free of mojibake.
4. **Change-detect** year over year from the CDX content digest (identical bytes means no
   change, for free), backed by a difflib similarity check.
5. **Agent-recover** the residual gaps: a tool-using LLM agent looks for a *different*
   archived URL/host that has the missing years, but only for companies deterministic
   discovery couldn't fully resolve.
6. **Tag** every page against a **frozen 13-theme taxonomy** with Claude structured
   outputs. The LLM is called only on the first year and on detected changes. Identical
   text reuses the prior tag.

**Outputs:** `data/output/part1_stated_values.csv` (one row per company-year) and
`data/coverage_grid.csv` (the companies × years grid with a reason code on every gap).

---

## Why these choices

- **Host CDX query, not exact-path guessing or a domain scan.** Exact guessing only finds
  paths you think of and needs ~40 calls/company. `matchType=domain` scans the entire
  domain index and *times out* on heavily-archived sites (microsoft.com never returned).
  A `matchType=host` query with a keyword filter and a small `limit` returns the canonical
  paths in one cheap call.
- **Deterministic first, agent only for the residual.** ~84% of companies resolve with no
  LLM at all. The agent is non-deterministic and the only step that costs API credits, so it runs
  only where deterministic methods fell short. Timeouts are excluded from it entirely:
  a non-response says nothing about whether a page exists, so those get gentle retries instead.
- **Confirm-don't-invent harness.** Whatever URL the agent proposes, the harness re-runs a
  real archive query itself and accepts only years a query actually returns. The model
  cannot fill a cell from thin air, and its URL picks are constrained to real values pages
  (product-category and social-profile pages are rejected by rule).
- **Frozen taxonomy.** The 13 themes are bootstrapped once from a 5-sector sample, frozen,
  and justified. They're never re-derived per page, which would make labels incomparable.
- **`broken_snapshot` reclassification.** A snapshot can exist yet clean to empty text
  (JS-rendered/stub pages). Those cells are reclassified out of "covered" so coverage
  reflects real *content*, not just the presence of a capture.
- **Politeness plus caching.** Every request sends a `User-Agent`, is rate-limited, and is
  cached by content hash, so reruns are free and deterministic and the archive isn't
  hammered. (Over-aggressive early runs got us soft-throttled, hence the gentle defaults.)

---

## Assumptions

- **One snapshot per year**, the capture nearest July 1. This is a fixed, defensible rule rather
  than cherry-picking.
- **"Values page" means a real About/mission/values page.** Not a homepage (Apple has no
  dedicated values page, so it's left a documented gap rather than tagging the homepage),
  not a product/category page, not a social-media profile.
- **Snapshot status 200 plus `text/html`** only. Redirects/404s are dropped (and logged).
- **Human-pinned URLs are trusted** (e.g. `about.google`, `berkshirehathaway.com`) and
  exempt from the automated acceptance rule.

---

## What I'd do differently with more time

- **Parallelize discovery earlier and budget rate limits up front.** The throttling that
  forced the gentle, partly-serial approach was self-inflicted by bursty early runs.
- **Follow multi-hop redirects** at the snapshot level to rescue some `no_capture` /
  `broken_snapshot` years that exist behind a 301/302.
- **A headless-render fallback** for JS-rendered About pages (the `broken_snapshot` cells),
  instead of accepting empty text.
- **Per-year URL provenance in the main CSV** (it's tracked internally) so a reader can see
  exactly which archived URL each cell came from.

---

## Known limitations

- **72% content coverage** (326 / 450 cells). Remaining: `no_capture` 70 (archive lacks the
  year), `timeout` 36 (4 heavy sites that never responded: AAPL, F, INTC, ORCL), `host_wrong`
  9 (no values page found, e.g. AXP), `broken_snapshot` 9 (snapshot exists, no text).
- **A few non-canonical fills**, flagged `is_canonical=false` in the grid: XOM's only
  archived About content is under an `/aviation/` sub-brand, and AMZN's 2016–17 came from the
  jobs site. The years are real; the page is second-best.
- **Watch-item: `human_progress_wellbeing`.** This is a broad theme. The full run shows it at 44%
  (mid-pack, not a runaway catch-all), but it's worth re-checking if the taxonomy is revised.
- **Discovery is gentle but slow**, by necessity given archive throttling.

---

## How to run

```bash
python3 -m venv .venv && ./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY (needed only for the agent + tagging)
```

Pipeline (each step has a script; all reuse the cache + logs):

```bash
./.venv/bin/python scripts/discover.py            # deterministic discovery -> tiers
./.venv/bin/python scripts/run_agent.py           # agent missing-year recovery (needs key)
./.venv/bin/python scripts/enforce_acceptable.py  # scrub any non-values URLs (free)
./.venv/bin/python scripts/retry_timeouts.py      # one gentle retry of timeouts (free)
./.venv/bin/python scripts/bootstrap_taxonomy.py  # propose taxonomy from cleaned sample
./.venv/bin/python scripts/extract_part1.py       # fetch+clean+change+tag -> the CSV
./.venv/bin/python scripts/build_grid.py          # (re)build the coverage grid
```

`ANTHROPIC_API_KEY` lives in `.env` (gitignored); never commit it.
