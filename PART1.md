# Part 1: Stated Values

**Goal.** For each of the 50 companies, recover the public "About/values" page text
for each year 2016–2024, detect how it changed over time, and tag which value
themes it expresses, producing one tidy row per company-year.

## Pipeline (what / why / code vs LLM)

| Stage | Approach | Why |
|------|----------|-----|
| Resolve the values page | **deterministic, concurrent** host queries (`discovery.py`): per company, a few `matchType=host` CDX queries (one per common corporate host) with a server-side keyword filter return candidate paths; rank locally; confirm the top candidates' year-coverage with fast exact queries; unresolved → `logs/discovery_misses.json` | See "Discovery design" below. A `values_url` override in `companies.yaml` pins a known-good page and skips discovery. |
| List snapshots | **code**: Wayback CDX API (`cdx.py`) | One call returns a JSON array-of-arrays of snapshot metadata (not page text). |
| Pick one per year | **code**: snapshot nearest a fixed anchor (Jul 1) | Deterministic, defensible, reproducible. |
| Fetch archived HTML | **code**: `web/<ts>id_/<url>` raw flag (`fetch.py`) | `id_` returns original HTML without Wayback's injected toolbar. |
| Clean text | **library**: `trafilatura` (`clean.py`) | Strips nav/footer/boilerplate; no LLM needed. |
| Change vs prior year | **code**: CDX `digest` equality, then `difflib` ratio (`change.py`) | Identical digest = byte-identical = unchanged, for free. LLM only worth spending to *characterize* a flagged change. |
| Clean text | **library**: `trafilatura` + **`ftfy`** | trafilatura extracts main content; the fetch layer decodes with the *detected* charset (not requests' ISO-8859-1 default, which mojibakes UTF-8 archived HTML) and `ftfy` repairs any residual artifacts, so `page_text_clean` is pristine. |
| Theme tagging | **structured LLM**: Claude `messages.parse()` vs the **frozen** taxonomy (`tagging.py`) | Same frozen prompt+schema for every page ⇒ the ~335 classifications are reproducible and comparable. Bulk on Haiku 4.5. |


## Discovery design 

The first version guessed ~40 exact `{subdomain}×{path}` URLs per company, serially.
It worked but was slow and could only find paths we thought to guess. We rebuilt it
against the live archive. The redesign is shaped by what CDX actually does:

- **Why not `matchType=domain`?** It is comprehensive (covers subdomains) but scans
  the entire domain index server-side. On heavily-archived sites it ran for *minutes*
  (microsoft.com never returned). Unusable at 50×.
- **Why `matchType=host` + keyword filter?** A host query with a server-side `urlkey`
  keyword filter returns just the About/values-ish paths for that host. We enumerate
  the handful of common corporate hosts (`www.`, bare, `corporate.`, `about.`) so we
  still catch subdomain values pages (e.g. `corporate.exxonmobil.com`).
- **Why `collapse=urlkey` + a SMALL `limit` (400)?** `collapse=urlkey` returns one row
  per path. A *large* limit forces the server to scan deep to fill it and times out on
  huge sites (nike.com, target.com timed out at 60s with limit 2500). A small limit is
  fast because the canonical paths (`/about`, `/values`, …) sort early in urlkey order.
- **Why a separate coverage-confirm step?** `collapse=urlkey` loses year coverage, so we
  confirm the top-ranked candidates with one fast **exact** query each (exact queries are
  indexed and quick) and pick the first covering ≥ `min_years_covered` years.
- **Why concurrency, not serial?** Discovery is I/O-bound on CDX. A bounded thread pool
  (cap = `concurrency`, default 6) overlaps requests; politeness comes from the cap rather
  than a per-request delay. The content-hash cache keeps reruns free and deterministic.
- **Keyword filter: simple on the server, precise locally.** A token-boundary regex sent
  to CDX is rejected (returns nothing), so the server-side `urlkey` filter stays permissive
  (`about|mission|…`) and Python does the precise filtering: a keyword counts only as a real
  path *token* (delimited by `/ _ -` or ends), so `com-MISSION` / `MISSION-ary` /
  `commission` no longer masquerade as values pages.
- **Ranking** keeps only token-matching, non-excluded paths (drops `news`, `press`,
  `investor`, query-string `?_amp`/`?callback` variants, …) and orders by **path depth first**
  (a shallow `/about-jnj` beats a deep `/caring/.../people-and-values` that merely contains
  "values"), then keyword priority (`values > mission > about > company`), then shortest path.
  Misses carry their candidate list into `discovery_misses.json` for the Step-2 agent. No
  silent failures.
- **Upstream reality + the gentle re-run.** CDX latency is highly variable and the archive
  soft-throttles bursty clients. An early version (several hosts/company × high concurrency ×
  a per-candidate confirm pass × repeated runs) got us rate-limited so hard that even MSFT's
  known-good URL returned 0 captures, a pure throttling artifact rather than a real miss. The fix is
  to be *lean and gentle*, and to stop conflating "no answer" with "no page":
  - **One host query per company** (the single best corporate host, `www.`), not several.
    Subdomain-hosted values pages (`corporate.*`) are handled by **overrides in `companies.yaml`**
    instead of extra speculative queries.
  - **Concurrency 2** with a **2s inter-request delay** and **exponential-backoff retries**
    (`max_retries: 3`) on timeout/429. Politeness now comes from both the small pool and the delay.
  - **Cache-first**: any URL already fetched is never re-called (only HTTP 200 bodies are cached,
    so a real failure is retried, not memoised).
  - **Three outcomes, not two.** Every query carries a `responded` flag, so we distinguish:
    `resolved` (override/prefix_filter, coverage confirmed) · `genuine_miss` (archive **responded**,
    no values page found → `discovery_misses.json`, Step-2 agent) · `timeout` (archive did **not**
    respond → `discovery_timeouts.json`, gets a **retry pass**, never the agent). Folding timeouts
    into "miss" is what made the earlier breakdown meaningless.
  - At 500× this matters more, not less: keep the small pool + delay, add jitter, and prefer an
    off-peak window over a burst. Overrides-as-data scale linearly and sidestep discovery entirely.

## The coverage grid

A first clean sweep "resolved" 34/50, but that label was too generous: it included
1–3-year picks and two junk URLs where a keyword matched mid-slug (`/gaming-company`,
`/…-mission-road`). Two rule changes fix the *rule*, not the symptoms:

- **Segment-anchored keywords.** A keyword now only counts when it *begins* a path
  segment (optionally after `our-`/`the-`): `/about-us`, `/our-values`, `/company-info`
  qualify; `/gaming-company`, `/valeros-…-mission-road`, `/see-what-were-all-about`
  (keyword buried mid/end-slug) do not. False gaps are safer than false picks.
- **File-type exclusions.** `.json/.svg/.jpg/.png/.gif/.ico/.css/.js/.xml/.pdf` can never
  be chosen as a "page" (an asset is not a values page).
- **`min_years_covered: 4` enforced.** A pick covering <4 of the 9 years is no longer
  "resolved"; it becomes its own **`low_coverage`** tier (it has a plausible URL, just
  sparse archival). So the four outcomes are now: `resolved` (≥4y), `low_coverage` (1–3y),
  `genuine_miss` (0 captures / no page), `timeout` (archive didn't answer). The threshold
  is 4 because a values-trajectory needs several points to be meaningful; sparser companies
  go to the agent for missing-year recovery rather than being silently counted as done.

### Coverage grid (`data/coverage_grid.csv`): the source of truth for gaps
One row per company, one column per year 2016–2024; each cell is `filled` or a reason
code: `no_capture` (URL responded, that year absent) · `host_wrong` (no values page on the
www host) · `timeout` (archive didn't answer) · `not_yet_checked`. Two richer codes,
`redirect` and `broken_snapshot`, are **not** deterministically assignable here (they need
per-snapshot inspection), so the Step-E agent assigns those as it investigates. The grid is
updated in place by later steps (pins, retries, agent fills), so at any moment it shows
exactly what is missing and why. Every blank for a big company must end up justified by
a reason code, never left as an unexplained default.

## Step-E agent: scoped to missing-year RECOVERY

The agent is the expensive, non-deterministic tier, so it runs ONLY where deterministic
methods genuinely fell short, and its job is narrow: for a given company-year that the grid
shows missing, decide whether the archive truly lacks it or whether a **different url/host**
for that company has it, and if so fill those cells. It may only fill a cell from a **real
archived snapshot it located**, never invent one. If it can't, the cell stays a confirmed
gap *with a reason code* (`no_capture`/`broken_snapshot`/`redirect`), justified by evidence it
actually tried alternates. Every decision is logged per company-year for audit.

- **Agent targets**: every company with <9 years that is not a timeout, namely `genuine_miss`,
  `low_coverage`, and resolved-but-incomplete (40 companies). Timeouts and the 9/9-complete
  companies are excluded.
- **Timeouts are NOT agent targets.** A non-response tells us nothing about whether a page
  exists, so routing it to the agent would have it chase a question the archive simply didn't
  answer. Timeouts get gentle **retries** until the archive responds, then they fall into one
  of the real buckets.
- **Multi-URL union.** Coverage of a company's About page often splits across paths over time
  (e.g. SLB's old `/who-we-are` 2019–22 + new `/about/who-we-are` 2022–24). The agent submits
  *all* confirmed URLs and the harness unions their real per-year coverage (storing a per-year
  URL map), so a year is filled whenever *any* confirmed URL has it, leaving a cell blank only
  when no URL covers it. 
- **Canonical flag.** When only a sub-brand/regional page exists in the archive (e.g. XOM's
  `/aviation/about-us`, because `corporate.exxonmobil.com` is empty in the archive), the agent fills
  from it but marks `is_canonical=false` with a note, so non-corporate picks are reviewable in
  the grid rather than silently trusted.
- **Forced submit + harness re-verification.** If the model hits its iteration cap without
  concluding, a forced `submit_finding` captures its best answer; either way the harness
  re-runs `url_coverage` on every submitted URL and accepts only years a real query returns.
  The model cannot fill a cell from thin air, and a non-submission degrades to "keep current",
  never to data loss.
- **URL acceptance rule (learned the hard way).** Maximizing coverage alone let the agent grab
  non-values pages (a Target `/b/mission/-/n-…` product category, a `facebook.com` profile, an
  ExxonMobil `/aviation` sub-brand page). So a cell can be filled only from an *acceptable* URL:
  the **host** signals about (`about.google`, `aboutamazon.com`) **or** a path segment is an
  about-keyword (`/about-us`, `/our-firm`, `/who-we-are`), **and** it isn't excluded
  (product-browse `/b/`, social domains, `jobs`, file types). Human **pins are exempt** (e.g.
  `berkshirehathaway.com`). `scripts/enforce_acceptable.py` applies this rule deterministically
  (free archive queries, no LLM): it restores any pin the agent overwrote and drops junk-filled
  years, so the grid is always 100% from real values pages even between agent runs.
- **Auditable instrumentation.** Each recovery logs `rounds` (tool-call rounds used),
  `urls_tried` (every host/URL queried), and `hit_cap` (whether it exhausted the round budget),
  alongside the fills and confirmed gaps, so a struggling company (e.g. one that hit 12 rounds)
  is visible.

### Recovery stopped at 75% verified: diminishing returns
After the credit-enabled recovery pass, **recovery was deliberately stopped**. The companies still
short of 9/9 are the ones whose agent hit the 12-round cap (`AXP, TGT, SCHW, TMO, XOM, IBM`): they
hit the cap precisely because the archive genuinely lacks an acceptable About/values page for those
years, so more rounds won't conjure data. The acceptance rule was also tightened once more: topic/
learning/earnings paths (`/learn/`, `/topic/`, `earnings`) are excluded, so a segment merely
*starting with* "company" (e.g. Schwab's `/learn/topic/company-earnings`) can no longer whitelist a
non-values page; SCHW's affected years reverted to a confirmed gap. **75% verified, all from real
values pages, with every remaining blank carrying a reason code, is the accepted baseline.** No
further discovery refinement loops.

## Frozen value-theme taxonomy (v1)

The taxonomy is **bootstrapped once, frozen, and justified**, not re-derived per page (which
would give 335 inconsistent label sets). Procedure:
1. Scrape-cleaned a **5-sector sample**: MSFT (Tech), CVX (Energy), JPM (Financials),
   JNJ (Healthcare), MCD (Consumer), 41 pages spanning 2016–2024.
2. `scripts/bootstrap_taxonomy.py` showed that sample to a strong model and asked for a compact,
   mutually-distinct taxonomy. It proposed **12 themes** (integrity, operational excellence,
   innovation/science, people/talent, diversity & inclusion, customer/client focus, community,
   environmental stewardship, leadership/governance, human progress & well-being, profitable
   growth, heritage/longevity).
3. **One justified addition, `safety`.** The universe is energy + healthcare + industrial-heavy
   (10 Energy + 10 Healthcare firms, plus Ford/Boeing-like operations), where physical/operational
   safety is a primary *stated* value; a single energy company (CVX) under-weighted it in the
   sample, so it was added rather than folded into "operational excellence".
4. Frozen as **v1 (13 themes)** in `config/taxonomy.yaml`. Every snapshot is classified against
   this fixed list via Claude structured output (`tagging.py`), so labels are comparable across
   companies and years. Changing the taxonomy later means a re-tag, by design.

## Reproducibility

- **Content-hash caching** (`.cache/`): every HTTP body keyed by `sha256(url)`,
  every LLM response keyed by `sha256(model+prompt+text)`. Reruns are free and
  deterministic.
- **Decision log** (`logs/run.jsonl`): one record per discovery / row / missing
  year / error. This log is the raw material for the writeup and limitations.

## Key assumptions / judgment calls (graded)

1. **One snapshot per year, nearest July 1.** 
2. **Frozen taxonomy.** Bootstrapped from a sample (`bootstrap_taxonomy.py`), then
   frozen and justified, not re-derived per page (which would give inconsistent labels).
3. **`status:200` + `text/html` only.** Redirects/404s are dropped (and logged);
   how to treat them is itself a documented choice.
4. **`favor_recall` cleaning.** Values pages are short, so keep more text rather
   than risk trafilatura dropping the substance.

## Known limitations / what I'd do with more time

- **Discovery is a serial candidate sweep**, correct but slow at 50× scale.
  Faster: a single CDX prefix query per host, or parallelize; or batch-resolve via
  the LLM discovery agent. Misses (e.g. companies whose values live on a
  non-standard path) currently drop out until the agent stage is built.
- **Locale bias.** The `/en-us/` path assumption suits US pages; a multinational's
  non-US values page could differ.
- **No semantic dedup of themes yet** across companies. The taxonomy is fixed but
  not validated for inter-rater agreement; a second-model adjudication pass would
  strengthen it.
- **Tagging cost** not yet batched. The `Message Batches` API (50% cheaper, async)
  is the right tool for the full 50-company fan-out.
