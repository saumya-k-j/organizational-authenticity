# Organizational Authenticity — Part 2: Lived Values (Disclosure Analysis)

Where Part 1 captured what 50 large U.S. companies **said they valued** on their public
"About/values" pages, Part 2 measures what those same companies **put in their binding,
regulated disclosure** — the annual proxy statement (SEC form **DEF 14A**) — for every
meeting year 2016–2024. The proxy is the "lived" channel: it's mandatory, lawyer-reviewed,
and aimed at the people who can fire the board. Comparing the two channels is the point —
do the values a company markets show up where it answers to its owners?

This README is the structured overview; `PART2_SCHEMA.md` is the column-by-column data
dictionary. Part 2 reuses Part 1's repo layout, on-disk cache, run-log style, and the
**frozen 13-theme taxonomy**, so the two halves are directly comparable.

> **Status: full 50-company run complete — 100% coverage (450/450 company-years).**
> `PART2_FINDINGS.md` is the non-technical summary; `PART2_SLICE_FINDINGS.md` is the
> earlier 3-company sanity-check record (superseded). The pipeline was validated on a
> sector-spanning slice first, then scaled unchanged.

---

## What it does (end to end)

```
ticker → CIK → submissions → pick DEF 14A per meeting-year → download → clean
        → classical stats + tf-idf similarity + LLM tag → structured dataset
```

1. **Map** each ticker to its SEC CIK via `company_tickers.json` (handles BRK.B→BRK-B, and
   merges predecessor CIKs for two mid-window reincorporations — see Assumptions).
2. **List** the company's filing history from the EDGAR submissions API, following the
   older-filing shards so the window reaches back to 2016, and keep the annual proxies.
3. **Bucket** each proxy by **meeting year**, not filing-date year (see Assumptions), and
   **select** one filing per year — management's full annual proxy, even in a contested
   year where dissident solicitations share the company's feed.
4. **Download** the primary document and **clean** it to text (BeautifulSoup; proxies are
   100+ pages of mostly tables, which Part 1's article-tuned trafilatura would discard).
5. **Coverage grid** — companies × years with reason-coded gaps, exactly like Part 1.
6. **Analyze** (the real work): classical NLP on the full text + selective LLM tagging on
   a values excerpt → a documented structured dataset and aggregate trend tables.
7. **Event coincidence** — test whether the proxy-language theme shifts line up in time
   with known 2016–2024 external events (config/events.yaml); report alignments *and*
   misses.

**Outputs** (`data/part2/output/`): `part2_disclosure_metrics.csv` (one row per
company-year), `part2_coverage_grid.csv`, three aggregate tables (`..._theme_trends_by_year`,
`..._theme_by_sector`, `..._distinctive_terms`), and `part2_event_alignment.csv`. Full
schema in `PART2_SCHEMA.md`.

---

## Why these choices

- **Proxy statements as the "lived/disclosed" channel.** Among free EDGAR sources, the
  DEF 14A is the one document that is (a) annual, (b) mandatory for every public company,
  (c) values-bearing (governance, human capital, sustainability, pay philosophy), and
  (d) aimed at owners, not customers. That makes it the cleanest counterweight to Part 1's
  marketing-page "stated" values.
- **Meeting-year bucketing, not filing-date year.** A proxy is filed weeks before its
  annual meeting; off-cycle filers (Apple files in December some years) otherwise produce
  a phantom gap in one calendar year and a double in the next. Bucketing by meeting year
  (`filing_month ≥ 10 → year+1`) gives one clean row per annual cycle. In the slice this
  turned Apple's apparent 2017-double / 2018-gap into a clean 2016–2024 with zero
  collisions.
- **Include DEFC14A, exclude DEFA14A / DEFM14A.** The definitive *contested* proxy
  (DEFC14A) is the same annual document filed under a different code during a board fight
  — excluding it would blank out exactly the most interesting years (ExxonMobil 2021,
  Engine No. 1). Additional soliciting material (DEFA14A) and merger/special-meeting
  proxies (DEFM14A) are *not* the annual values document and are excluded.
- **Robust filing selection on contested years.** In a proxy fight the subject company's
  EDGAR feed also carries the dissident's DEFC14A. We pick management's by ranking
  candidates (real annual form first, then longest cleaned text — the full statement
  dwarfs a dissident card) and record the alternates. The `collisions` column flags every
  such year so the choice is auditable.
- **Classical first, LLM for the residual judgment.** Dictionary counts / tf-idf run on
  every word of all 450 filings — transparent, free, deterministic. The LLM is spent only
  on what counts can't do: semantic theme presence and shareholder-vs-stakeholder framing,
  on a bounded values excerpt, cached by content hash. (Full justification in the schema.)
- **Politeness + caching, reused from Part 1.** Every request carries a descriptive
  User-Agent (SEC requires it), is rate-limited under EDGAR's ~10 req/s ceiling (~8 req/s),
  retries with backoff, and is cached by `sha256(url)`. Reruns make **zero** network calls.

---

## Assumptions

- **One proxy per meeting year = the company's stated values in the governance channel
  for that cycle.** A company files exactly one annual proxy per meeting; we take it whole.
- **Meeting year ≈ filing year, +1 if filed in Q4.** Defensible for spring-meeting large
  caps; a minority of June-fiscal-year firms (Nov/Dec meetings) could shift by one — a
  mis-shift would show up as a doubled year next to a missing one, but all 50 companies
  resolved to a clean 9/9 with no missing years, so none occurred. (The 9 `collisions`
  flagged in the full run are all *contested-proxy* years — management's filing competing
  with a dissident's in the same feed — not bucketing artifacts; each was audited and
  resolved to management's full proxy.)
- **Primary document = the proxy.** We read the filing's `primaryDocument`; if absent we
  fall back to the full-submission text. For 2016–2024 every filing has an HTML primary doc.
- **Predecessor-CIK merges for two reincorporations.** `company_tickers.json` maps a ticker
  to its *current* registrant CIK, which misses in-window proxies when a company reorganized
  mid-window. Two needed an explicit CIK list (continuing + predecessor), merged by
  meeting-year: **BLK** (2024 holdco reorg → proxies under the operating company CIK
  1364742) and **AVGO** (Broadcom Ltd redomiciled to the US in 2018 → 2016–2018 under CIK
  1649338). Both verified against EDGAR; this is what lifts coverage from 97.3% to 100%.
- **Cleaned full text is the analysis surface.** We keep the whole proxy (including the
  cover boilerplate, which is near-identical across filings and so non-distinctive under
  tf-idf `min_df`) rather than trying to segment sections — simpler and reproducible.

---

## What I'd do differently with more time

- **Section-aware extraction.** Split the proxy into its standard sections (governance,
  human capital, sustainability, compensation D&A) and analyze the values-bearing sections
  separately from the mechanical ones — this would de-saturate the governance-dominated
  `dominant_theme` and sharpen the distinctive-terms table.
- **A real Loughran-McDonald dictionary.** The tone lexicon here is a compact curated
  subset; swapping in the full LM word lists (and a finance stop-word list) would make tone
  comparable to the accounting/finance literature.
- **Proxy-baseline tf-idf for distinctive terms.** Weight each sector against a
  proxy-corpus baseline so governance boilerplate stops dominating the "distinctive" view.
- **Direct Part-1↔Part-2 join + gap score.** The natural payoff: per company-year, set the
  proxy's theme/stakeholder profile against Part 1's stated-values profile and compute a
  "say-do" divergence — the seed of the authenticity index (Parts 3–4).
- **A few more contested/edge forms audited** (10-K "Human Capital" item, post-2020) as a
  second disclosure channel.

---

## Known limitations

- **`leadership_governance` dominant-theme saturation (known limitation; Part 2.1 fix
  planned).** Because a proxy's literal, mandated purpose is electing directors and
  approving executive pay, governance vocabulary (board, director, committee, oversight)
  and shareholder-return vocabulary saturate every filing. As a result `dominant_theme_classical`
  is `leadership_governance` for essentially **all** company-years, and even the
  excerpt-based `llm_dominant_theme` skews governance — the raw "dominant theme" is
  therefore **not** an informative discriminator across companies or years. Current
  mitigations: (a) `dominant_theme_distinctive`, the argmax after removing the two
  structural themes (`leadership_governance`, `profitable_growth`), which *is* informative
  and is what the findings rely on; (b) the `llm_stakeholder_orientation` judgment; and
  (c) the per-theme frequency **trends**, which are unaffected since each theme is tracked
  in its own right. **Planned Part 2.1 refinement — section-aware extraction:** split each
  proxy into its standard sections (proxy summary, corporate governance, human capital /
  ESG, compensation discussion & analysis) and compute theme metrics on the
  values-bearing sections separately from the mechanical governance/compensation
  sections. That removes the structural baseline at the source, de-saturating the
  dominant-theme metric and sharpening the distinctive-terms table, rather than working
  around it downstream.
- **Approximate readability.** Flesch uses an approximate syllable counter; treat the
  *trend* (proxies getting denser) as the signal, not the absolute grade.
- **Distinctive-terms table is boilerplate-heavy** until the proxy-baseline weighting above.
- **Slice ≠ population.** Findings in `PART2_SLICE_FINDINGS.md` are from 3 companies chosen
  to span sectors and stress-test collection (Apple's off-cycle filing, Exxon's proxy
  fight). They are directional, not the 50-company result.

---

## How to run

```bash
./.venv/bin/python -m pip install -r requirements.txt   # adds bs4, lxml, scikit-learn, numpy
# .env already holds ANTHROPIC_API_KEY (needed only for the LLM tagging step)
```

```bash
# slice (what was run for the sanity check)
./.venv/bin/python scripts/p2_collect.py  AAPL JPM XOM
./.venv/bin/python scripts/p2_coverage.py AAPL JPM XOM
./.venv/bin/python scripts/p2_analyze.py  AAPL JPM XOM      # add --no-llm to skip the API

# full population (after sanity check) — same scripts, no args
./.venv/bin/python scripts/p2_collect.py
./.venv/bin/python scripts/p2_coverage.py
./.venv/bin/python scripts/p2_analyze.py
./.venv/bin/python scripts/p2_events.py        # event-coincidence analysis (reads the above)
```

Everything is cached (`.cache/`, `sec_`-prefixed) and logged to `logs/part2_run.jsonl`
and the manifest `logs/part2_filings.json`. Reruns are free and deterministic.
