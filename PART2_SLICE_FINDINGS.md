# Part 2 — Slice Findings (Apple, JPMorgan, ExxonMobil)

> **Superseded by `PART2_FINDINGS.md` (full 50-company run).** This file is kept as the
> record of the 3-company sanity-check slice that was reviewed before scaling. Its
> directional findings — ESG language rising while shareholder language holds, Exxon's 2021
> environmental pivot — all held up and strengthened on the full sample.

*A non-technical read of the 3-company sanity-check slice. These results are directional
— chosen to span sectors (Tech / Financials / Energy) and to stress-test collection — not
the final 50-company picture. The method and code are unchanged for the full run.*

---

## The one-paragraph version

For three of America's largest companies, we recovered **every** annual proxy statement
(SEC DEF 14A) for 2016–2024 and measured how their values language moved. The headline:
the same "rise of ESG/stakeholder language" that Part 1 found on company *websites* is
also visible in their *regulated disclosure* — environmental language in these proxies
**tripled** over the decade. But there's a twist Part 1 didn't show: in the proxy, the old
**shareholder-return language did not retreat to make room for it** — it stayed just as
prominent. On their marketing pages companies *swapped* shareholder talk for stakeholder
talk; in their proxies they simply *added* the new language on top of the old.

---

## What we found

**1. Disclosure is the dependable channel — coverage was 100%.**
All 27 company-years (3 companies × 9 years) were recovered and cleaned. This is the
expected contrast with Part 1: filing a proxy is mandatory, so there are no archive gaps.
Notably, **Apple** — which Part 1 could not recover a public "values page" for at all — has
a complete, machine-readable values record here. Where a company is silent in marketing, it
is still on the record in governance.

**2. The ESG/stakeholder language rose here too — sharply.**
Comparing the early window (2016–2018) to the recent one (2022–2024), averaged across the
three companies:

| Value theme (proxy language) | 2016–18 | 2022–24 | change |
|---|---|---|---|
| Environmental stewardship | 1.72 | 5.21 | **+202%** |
| Safety | 0.27 | 0.55 | +104% |
| Community & social responsibility | 0.51 | 0.97 | +90% |
| Diversity & inclusion | 2.77 | 3.95 | +43% |
| **Profit & shareholder value** | **8.46** | **7.99** | **−5%** |

(Figures are mentions per 1,000 words, so longer proxies aren't counted as "more.")

**3. The cross-channel twist: companies *added*, they didn't *swap*.**
Part 1 found shareholder/profit language on websites falling steeply (48% → 26% of pages).
In the proxy it barely moved (−5%) and remained the **most prominent** value theme
throughout. The plausible reading: a proxy's core audience is shareholders, so firms keep
the returns language front-and-center and *layer* sustainability, safety and inclusion on
top. The marketing channel reframes; the governance channel accretes.

**4. Each company's discretionary emphasis shifted in a recognizable direction.**
Setting aside the boilerplate every proxy shares (governance and pay), the leading
*discretionary* value theme tracks each company's public story:
- **ExxonMobil** → flips to **environmental stewardship** from 2021 — the year activist
  investor Engine No. 1 won board seats on a climate platform. (That contested 2021 proxy
  was correctly captured; our pipeline picked management's filing over the dissident's.)
- **Apple** → moves to **diversity & inclusion** from 2022.
- **JPMorgan** → steadily **customer/client focus**, as you'd expect from a bank.

An independent LLM read of each proxy's shareholder-vs-stakeholder framing agrees: Exxon
leans "shareholder-primacy" most often (4 of 9 years) but shifts to "balanced" from 2021
onward; Apple and JPMorgan read as "balanced" in most years.

**5. Proxies are getting longer and harder to read.**
JPMorgan's proxy grew **+42%** in words over the decade and ExxonMobil's **+34%**; reading
ease fell across the board (Apple 34.7 → 24.6 on the Flesch scale — solidly "difficult").
Companies are disclosing *more* about values, but in *denser* language.

---

## Why this matters for the project

Part 2's job is the "lived/disclosed" counterweight to Part 1's "stated" values. The slice
shows the two channels **rhyme but don't match** — the same ESG rise, but a different
relationship to shareholder language — which is exactly the kind of gap an authenticity
index (Parts 3–4) is meant to quantify. The natural next step after the full 50-company run
is to join the two datasets per company-year and score the divergence.

## What to check before we scale

- **Governance saturation** of the raw dominant-theme metric (handled with a
  "discretionary" version and the stakeholder-orientation tag; fully fixed by section-aware
  extraction — see README "what I'd do differently").
- **Sample is 3 companies**, picked partly *because* they're tricky (Apple's December
  filings, Exxon's proxy fight). The full run will tell us whether the "add, don't swap"
  pattern holds across all 50.
