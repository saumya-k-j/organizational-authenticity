# Part 2: Data Dictionary

Documents every output file under `data/part2/output/` and justifies every column.
The unit of analysis is a **company-year** keyed by *meeting year* (the year of the
annual meeting the proxy serves; see README for why this, not filing-date year).

---

## `part2_disclosure_metrics.csv`: the main dataset (one row per company-year)

### Identity & provenance
| column | type | why it's here |
|---|---|---|
| `ticker` | str | Company key; joins to Part 1 and to `companies.yaml`. |
| `company` | str | Human-readable name. |
| `sector` | str | One of the 5 S&P sectors; the cross-sector comparison axis. |
| `meeting_year` | int | 2016–2024; the time axis. Bucketed by annual-meeting year. |
| `form` | str | `DEF 14A` or `DEFC14A` (contested years). Records which genre variant was used. |
| `filing_date` | str | Actual SEC filing date (YYYY-MM-DD). Provenance, and lets a reader recover the meeting-year mapping. |
| `accession` | str | SEC accession number: the exact filing this row was computed from (full reproducibility). |

### Size (classical): proxies have ballooned; length is itself a finding
| column | type | why it's here |
|---|---|---|
| `n_words` | int | Word count of cleaned text. Tracks the multi-year growth in proxy length. |
| `n_sentences` | int | Sentence count; denominator for readability. |

### Value-theme frequencies (classical): `theme_<key>`, one per Part-1 taxonomy theme
| column | type | why it's here |
|---|---|---|
| `theme_integrity_responsibility` … `theme_safety` (13 cols) | float | Per-1,000-word frequency of each value theme's keyword lexicon. Per-1k normalization makes long and short proxies comparable. **Keyed to Part 1's frozen 13-theme taxonomy so the "stated" (web) and "disclosed" (proxy) channels line up.** |
| `dominant_theme_classical` | str | Argmax of the 13 theme frequencies. Note: a proxy's structural purpose (governance + pay) saturates this at `leadership_governance` on nearly every filing. Kept for transparency. |
| `dominant_theme_distinctive` | str | Argmax **excluding** the two structural themes (`leadership_governance`, `profitable_growth`). The *discretionary* values emphasis: what this proxy foregrounds beyond its mandatory content. |

### Tone (classical): LM-style, per 1,000 words
| column | type | why it's here |
|---|---|---|
| `tone_positive` | float | Positive-sentiment term frequency. Proxies are promotional, so level and drift are signals. |
| `tone_negative` | float | Negative/adverse term frequency (litigation, loss, decline). |
| `tone_uncertainty` | float | Hedging/uncertainty terms (may, risk, could). Rises with risk-disclosure caution. |
| `net_tone` | float | (pos − neg) / (pos + neg), in [−1, 1]. One-number tonal positivity. |

### Readability / complexity (classical)
| column | type | why it's here |
|---|---|---|
| `avg_sentence_len` | float | Mean words/sentence. Proxy density proxy. |
| `flesch_reading_ease` | float | Standard readability (higher = easier). Tracks the drift toward denser legalese. Syllables are approximated (documented limitation). |

### Language change (classical, corpus-level)
| column | type | why it's here |
|---|---|---|
| `sim_to_prev` | float / null | tf-idf cosine similarity to the **same company's** prior-year proxy. High = boilerplate carried forward; dips flag genuine rewrites. Null in a company's first covered year. |

### Semantic tags (LLM, on a values-relevant excerpt)
| column | type | why it's here |
|---|---|---|
| `llm_themes` | str | Pipe-joined taxonomy keys the proxy clearly expresses. Semantic, so it catches themes stated without their dictionary keywords. |
| `llm_dominant_theme` | str | The single most-emphasized theme (LLM judgment). |
| `llm_stakeholder_orientation` | enum | `shareholder_primacy` / `balanced` / `stakeholder_oriented`. **The proxy-side test of Part 1's headline shareholder→stakeholder shift**, a judgment classical keyword counts can't make. |
| `llm_summary` | str | One-sentence plain-language gloss of the proxy's foregrounded values. |

---

## Aggregate tables

### `part2_theme_trends_by_year.csv`
Mean `theme_<key>` across companies for each meeting-year. The decade time-series.
Shows which value themes rose or fell in proxy language (compare to Part 1's trend).

### `part2_theme_by_sector.csv`
Mean `theme_<key>` by sector. The proxy-language "values fingerprint" per sector
(compare to Part 1's sector fingerprints).

### `part2_distinctive_terms.csv`
Top tf-idf terms per sector (sector centroid of the tf-idf matrix). A transparent,
no-LLM view of how each sector's proxy language sounds. (Boilerplate governance terms
dominate; documented as a limitation. A richer version would weight against a
proxy-corpus baseline.)

### `part2_event_alignment.csv`
One row per (external event × hypothesized theme). Tests whether proxy-language shifts
coincide in *time* with known 2016–2024 events (config/events.yaml). Columns: `event`,
`event_date`, `theme`, `hypothesis` (`up` / `down_or_plateau`), `reflect_year` (first
meeting-year the language could reflect the event, given proxy lag), `pre_mean` /
`post_mean` (all-company theme frequency in the 2-year windows before/after), `change_pct`,
`biggest_jump_year` (the theme's own largest year-over-year rise, data-driven),
`biggest_jump`, and `verdict` (`aligned` / `partial` / `weak` / `no`). This is descriptive
timing coincidence, **not** causal inference. Misses are reported, not hidden.

### `part2_coverage_grid.csv`
Companies × meeting-years; each cell `filled` or a reason code
(`no_filing` / `empty_text` / `fetch_error` / `no_cik`). Plus `cik`, `years_covered`,
and `collisions` (>0 flags a year where multiple candidate filings competed, e.g. a
contested proxy, so the auto-selection is auditable).

---

## Why classical vs LLM (the split, justified)

- **Classical (full corpus, every filing):** theme frequencies, tone, readability,
  sizes, tf-idf similarity. Transparent, free, deterministic, and identical on every
  rerun. The right tool for a 450-filing time series and for anything a keyword or
  vector can capture.
- **LLM (bounded excerpt, selective):** semantic theme presence and
  shareholder-vs-stakeholder framing. These judgments need reading comprehension, not
  word counts. Bounded to a values-relevant excerpt (proxies are mostly compensation
  tables) and cached by content hash, so cost and nondeterminism are contained.
