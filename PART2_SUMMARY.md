# Part 2: Findings: What 50 Major Companies *Disclosed* They Valued, 2016–2024

*A non-technical summary of the full 50-company run. Source: every company's annual proxy
statement (SEC form DEF 14A) for each meeting year 2016–2024, so 450 filings, 100% recovered.
This is the "lived/disclosed" counterpart to Part 1's "stated" values from company websites.*

---

## Summary

Across all 50 of America's largest companies, the language of social and environmental
responsibility surged in proxy statements over the decade. Environmental wording **more
than tripled**, and health/well-being, safety, community and diversity language all rose
sharply. But the money language never left: talk of **profit and shareholder returns stayed
flat and remained the single most prominent value theme throughout**. In their regulated
disclosure, companies *added* the new stakeholder vocabulary on top of the old shareholder
vocabulary rather than trading one for the other. That is a meaningfully different picture from
their marketing pages (Part 1), where shareholder language visibly retreated. And the timing
of the biggest shifts lines up with real-world events: the 2020 pandemic and racial-justice
reckoning, and the 2021 ExxonMobil climate proxy fight. Not every event left a mark, though.

---

## Coverage

All **450 company-years (50 × 9) were recovered, cleaned, and analyzed: 100%.** Filing a
proxy is mandatory, so unlike Part 1 (72% web coverage) there are no real gaps. Two
companies needed care because they reincorporated mid-decade and the SEC's ticker file only
points to their *current* legal entity: **BlackRock** (a 2024 reorganization) and
**Broadcom** (a 2018 move from Singapore to the US). We followed each company's predecessor
filings so the time series stays continuous. Nine companies had a "collision," meaning more than
one candidate filing in a year. This was almost always a shareholder-activist contest where the
dissident's materials sit alongside management's in the same SEC feed. In every case we
verified we kept management's full annual proxy (details in the coverage report).

## Finding 1: Stakeholder/ESG language rose sharply

Average mentions per 1,000 words, early decade (2016–18) vs recent (2022–24), across all 50:

| Value theme (proxy language) | 2016–18 | 2022–24 | change |
|---|---|---|---|
| Environmental stewardship | 0.87 | 2.85 | **+226%** |
| Safety | 0.20 | 0.46 | +129% |
| Human progress & well-being | 0.60 | 1.21 | +102% |
| Community & social responsibility | 0.46 | 0.76 | +63% |
| Diversity & inclusion | 2.30 | 3.35 | +46% |
| People & talent | 3.46 | 4.57 | +32% |
| **Profit & shareholder value** | **7.91** | **7.89** | **−0%** |

## Finding 2: The headline: companies *added*, they didn't *swap* (vs Part 1)

Part 1 found that on company **websites**, profit/shareholder language fell steeply
(48% → 26% of pages) as ESG language rose, a *substitution*. In the **proxy** it didn't
budge (−0%) and stayed the **most prominent** theme every single year. The likely reason
is audience: a proxy's readers are the shareholders who vote, so firms keep returns language
front-and-center and *layer* sustainability, safety and inclusion on top. The marketing
channel re-brands; the governance channel accretes.

The *framing* did shift even where the word-counts didn't. An independent
LLM read of each proxy's overall orientation shows the share of companies framing themselves
around **shareholder primacy falling from 37% (2016) to 8% (2024)**, with "balanced"
framing rising from 63% to ~89%. So firms increasingly *present* themselves as
stakeholder-balanced while never actually dialing down how much they talk about returns.

## Finding 3: The big shifts coincide with real external events (mostly)

We tested whether the timing of language shifts lines up with known 2016–2024 events,
accounting for the lag between an event and the next proxy season. **What aligned:**

- **COVID-19 (2020) → safety (+58%) and well-being (+51%).** Both jump in the 2021 proxies.
- **George Floyd / racial-justice reckoning (2020) → diversity & inclusion (+23%).** Jumps
  in 2021.
- **Engine No. 1's ExxonMobil board win (2021) → environmental stewardship (+73%).** Jumps
  in 2022, the season after activists won climate-platform board seats.
- **Business Roundtable stakeholder statement (2019) → community language (+46%).** Rises
  into 2021.

**What didn't (reported, not buried):**

- **The Paris Agreement (2016) did *not* move proxy climate language in 2017.** Environmental
  wording was flat until it surged in 2021–22. The climate-in-governance story is a
  proxy-fight-era phenomenon, not a Paris-era one.
- **Human-capital ("people & talent") language was already climbing before COVID and before
  the 2020 SEC human-capital disclosure rule.** Its biggest jump is in 2018. Those events
  rode a trend that predated them rather than starting it.
- **The 2022–23 anti-ESG backlash** coincides with diversity language going *flat*, which is consistent
  with backlash. But environmental language **kept rising** (+24%), so the backlash story
  only half-holds in the data.

## Finding 4: Proxies got longer and denser

The average proxy grew from ~43,500 to ~56,500 words (**+30%**) over the decade, and reading
ease fell (Flesch 32 → 27.5, solidly "difficult"). Companies are disclosing *more* about
values, in *harder* language. Tone stayed steadily promotional throughout.

## Finding 5: Beyond the boilerplate, sectors foreground predictable values

Every proxy is saturated with governance and pay language (its legal purpose), so the
informative signal is the leading *discretionary* value once that's set aside. Across all
filings that's most often **operational excellence** and **customer/client focus**, with
energy companies increasingly foregrounding **environmental stewardship** and several
consumer/tech firms shifting toward **diversity & inclusion** in the 2020s. These are the same
sector fingerprints Part 1 saw, now visible in regulated disclosure.

---

## Why this matters

Part 2 gives the "lived/disclosed" baseline to set against Part 1's "stated" values. The two
channels **rhyme but don't match**: the same ESG rise, but a different relationship to
shareholder language (substitution on the website, accretion in the proxy). That gap, what a
company emphasizes to customers vs to owners, is exactly what an authenticity index (Parts
3–4) is built to quantify. The natural next step is a per-company-year join of the two
datasets and a "say-do" divergence score.

## Limitations (full list in PART2_README)

- **Governance saturation** makes the raw "dominant theme" uninformative; we rely on the
  discretionary-theme metric, the stakeholder-orientation tag, and per-theme trends instead.
  The planned **Part 2.1** fix is section-aware extraction.
- **Keyword frequency ≠ sincerity.** Rising environmental wording measures emphasis, not
  action, and measuring the gap to action is the whole point of the later parts.
- **Event coincidence is timing, not causation.** We report alignment of dates, and we report
  the misses; we do not claim any event *caused* a language change.
- **Tone uses a compact curated lexicon** (not the full Loughran-McDonald dictionary).
