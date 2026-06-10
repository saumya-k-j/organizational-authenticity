# Organizational Authenticity

This is my submission for the Wharton-TAU research assistant recruitment task on
organizational authenticity. The project measures the gap between what 50 of the largest U.S.
companies **say** they value (their public websites) and what they emphasize in their
**formal filings** (annual proxy statements, SEC form DEF 14A), for every year from 2016 to
2024. It builds up to a single per-company-year "authenticity index" for that gap, then
explores where the gap comes from.

## Headline findings

- **Say moved more than substance.** On their websites, companies shifted from shareholder
  language to stakeholder language over the decade (profit/shareholder talk fell from 48% to
  26% of pages). In their proxies, they mostly **added** stakeholder language on top without
  dropping shareholder primacy (profit/shareholder emphasis stayed flat and remained the
  single most prominent theme every year).
- **The authenticity index.** Comparing the two sides per company-year, energy firms
  over-claim the most (ConocoPhillips, Marathon, Phillips 66 top the table), while
  Citigroup, Home Depot, and Bank of America track closest between what they market and what
  they file.
- **What drives over-claiming (Part 4, exploratory).** Companies over-claim more on the
  values their industry is expected to hold, but the sharper driver is cheap-vs-costly: they
  back up the expected values that are costly or regulated (an energy firm genuinely engages
  the environment, which is material and litigated for it) and inflate the soft image values
  (heritage, innovation).

## The four parts

| Part | What it does | Docs |
|---|---|---|
| **Part 1: Stated Values** | Recover each company's public "About/values" page per year from the Wayback Machine and tag it against a frozen 13-theme taxonomy. | [README](PART1_README.md) · [summary](PART1_SUMMARY.md) · [design log](PART1.md) |
| **Part 2: Lived Values** | Collect every annual proxy (DEF 14A) from SEC EDGAR and analyze how value language shifts, with classical NLP plus selective LLM tagging. | [README](PART2_README.md) · [summary](PART2_SUMMARY.md) · [schema](PART2_SCHEMA.md) |
| **Part 3: Authenticity Index** | Score the emphasis-weighted over-claiming between the website and the proxy, per company-year, with a widening/closing trajectory. | [README](PART3_README.md) · [summary](PART3_SUMMARY.md) |
| **Part 4: Exploration** | Test whether over-claiming concentrates on industry-expected values, and refine that into the cheap-vs-costly pattern. | [README](PART4_README.md) · [summary](PART4_SUMMARY.md) |

Each part's README is the technical write-up. Each summary is a 1-2 page non-technical read.

## Repo structure

```
authenticity-index/
├── src/authenticity/      the Python package
│   ├── *.py               Part 1: discover, fetch, clean, change-detect, tag (Wayback + LLM)
│   ├── disclosure/        Part 2: SEC EDGAR collection + proxy text analysis
│   └── index3/            Part 3 + Part 4: the index, validity checks, sector exploration
├── scripts/               runnable entry points (one per pipeline step, per part)
├── config/                YAML inputs: companies, taxonomy, value lexicon, settings, events
├── data/                  outputs (Part 1 in data/output, Part 2 in data/part2, Part 3+4 in data/part3)
└── logs/                  run logs and persisted state (jsonl decision logs, filing manifests)
```

## How to run

```bash
python3 -m venv .venv && ./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY
```

Each part has its own run commands in its README (the scripts are named by part: `discover.py`
and friends for Part 1, `p2_*.py` for Part 2, `p3_*.py` for Part 3, `p4_explore.py` for Part
4). The API key is only needed for the steps that call a model: Part 1 theme tagging and the
recovery agent, and Part 2 LLM tagging. The Part 3 index and all of Part 4 are pure
computation over the existing outputs and need no API.

## Data and coverage

Coverage is partial and documented, never silently filled. Part 1 reaches about 72% of
possible company-years (some values pages were never archived or never existed). Part 2 is
complete (100%), because filing a proxy is mandatory. Part 3 scores only the intersection
where both sources exist (301 company-years, 243 of them on website pages long enough to
trust). Every missing cell carries a reason code. The coverage grids live at
[data/coverage_grid.csv](data/coverage_grid.csv) (Part 1) and
[data/part2/output/part2_coverage_grid.csv](data/part2/output/part2_coverage_grid.csv) (Part 2).

A note on scope: the index compares two registers of corporate **speech** (a marketing
website and an accountable filing), not words against real behavior. Read each part's
limitations section for what the numbers do and don't support.
