# Part 4 — Exploratory: Do companies over-claim more on the values their sector expects?

**My hypothesis (stated up front).** I think companies over-claim *more* on the values their
**sector is expected** to hold. The mechanism I have in mind: sector norms pressure a company
to *say* a value — an energy firm almost has to profess environmental concern, its absence
would be conspicuous — but nothing compels it to *back that up* in its filings. So
sector-expected themes should carry a bigger say-vs-do gap than themes the sector isn't
expected to care about. I expected this to hold. It partly did, and partly surprised me — both
reported below.

This builds entirely on Parts 1–3 (no new collection): the same 11 discretionary themes, the
same max-normalized per-theme over-claiming from Part 3, the same `low_evidence` exclusion.

> **Status: full run — all 5 sectors, 40 scored companies.** (Built and reviewed as a 2-sector
> slice first; scaling changed the headline — see Finding 1.) Still a *preliminary* exploration
> per the brief: the reasoning and the honest confounder accounting matter as much as the point
> estimates.

---

# Part A — The analysis and what I found

**Setup.** A theme is **sector-expected** if a clear majority of the sector's companies
profess it: a company counts as professing theme `t` if `t` appears in ≥ half its Part 1
website-years, and a theme is sector-expected if ≥ **60%** of the sector's companies profess
it. (60% is the "clear majority" cut and falls in a natural gap between each sector's core
fingerprint and its tail.) Then, for each company, I split its Part 3 per-theme over-claiming
into its sector's **expected** themes vs the **non-expected** ones, comparing the **mean
over-claim per theme** in each group (mean, not sum, so unequal group sizes don't bias it).
Positive gap = over-claims more on expected themes = my hypothesis.

Expected themes per sector (≥60% of the sector's companies profess it):

| sector | expected themes |
|---|---|
| Technology | customer_client_focus, human_progress_wellbeing, innovation_science |
| Healthcare | customer_client_focus, human_progress_wellbeing, innovation_science, integrity_responsibility, people_talent |
| Energy | heritage_longevity, innovation_science, operational_excellence |
| Consumer Discretionary | community_social_good, customer_client_focus, operational_excellence |
| Financials | customer_client_focus |

### Finding 1 — The hypothesis holds: 4 of 5 sectors over-claim more on expected themes

| sector | n | mean over-claim, expected | non-expected | **gap** |
|---|---|---|---|---|
| Technology | 5 | 0.246 | 0.036 | **+0.210** |
| Healthcare | 9 | 0.193 | 0.076 | **+0.117** |
| Energy | 10 | 0.217 | 0.122 | **+0.095** |
| Consumer Discretionary | 8 | 0.130 | 0.094 | **+0.036** |
| Financials | 8 | 0.017 | 0.106 | **−0.089** |

Across all **40 companies the mean gap is +0.066 and 68% are positive.** This is a real
positive effect — and it *strengthened* on scaling. My slice (Energy + Financials only) had
read as "washes out at +0.014" purely because it paired the strongest sector with the one
**reversal**: Financials over-claims *less* on its single expected theme (customer focus). So
the honest sequence is: the slice under-sold the effect, the full run confirms my prior holds
broadly, and Financials remains the lone documented exception.

### Finding 2 (centerpiece) — The energy/environment case study surprised me

I expected environmental stewardship to be energy's **biggest** over-claim. It is nearly its
**smallest**. Ranked by mean over-claim across the 10 energy firms:

| rank | theme | mean over-claim |
|---|---|---|
| 1 | heritage_longevity | 0.325 |
| 2 | innovation_science | 0.287 |
| 3 | human_progress_wellbeing | 0.221 |
| … | … | … |
| **8** | **environmental_stewardship** | **0.054** |
| 11 | operational_excellence | 0.024 |

Environment is **#8 of 11**. And the reason is clean and checkable: in energy **proxies**,
environmental stewardship ranks **#4 of 11** discretionary themes (3.24 per 1k words) — energy
filings *genuinely engage* climate (it's material, regulated, and litigated for them; recall
the Engine No. 1 fight). Meanwhile **heritage_longevity ranks dead last in energy proxies**
(0.15 per 1k) yet is the **#1 over-claim**. So the cheap talk isn't environment at all — it's
the soft, unfalsifiable image themes (heritage, innovation, human progress) the proxy has no
reason to detail. Energy says environment *and largely backs it up*; it says heritage and
doesn't. My prior had the specific theme exactly backwards — which pointed me at a sharper
question (Finding 3).

### Finding 3 — The refined "cheap-vs-costly expected value" pattern generalizes (and energy isn't special)

The energy case suggested a rule: a company **backs up** expected values that are
costly/material/enforced (environment — regulated, litigated) but **over-claims** expected
values that are soft/image (heritage). To test it across sectors I need an observable for
"costly/enforced," and I use **how much the proxy engages the theme** (its mean per-1k
frequency) — a value the filing details heavily is one the company is in practice compelled to
address. For every theme that is sector-expected *somewhere*, over-claim-where-expected vs
proxy frequency:

| theme | over-claim where expected | proxy frequency | reading |
|---|---|---|---|
| human_progress_wellbeing | 0.377 | 1.02 | soft / over-claimed |
| heritage_longevity | 0.325 | 0.20 | soft / over-claimed |
| innovation_science | 0.310 | 1.56 | soft / over-claimed |
| community_social_good | 0.213 | 0.64 | soft-ish |
| integrity_responsibility | 0.160 | 2.87 | mid (semi-enforced) |
| customer_client_focus | 0.068 | 4.66 | material / backed up |
| people_talent | 0.034 | 4.20 | material (human-capital disclosure) / backed up |
| operational_excellence | 0.026 | 5.93 | material / backed up |

The pattern is strong and monotone: **Spearman(over-claim-where-expected, proxy frequency) =
−0.86.** Soft, unenforced expected values (heritage, human progress, innovation) are
over-claimed most; material, filing-detailed ones (operations, human capital, customer/business)
are over-claimed least. **Energy/environment is one instance of this general rule, not a
special case** — in fact environment never even clears the 60% "expected" bar (it tops out at
50% of energy firms), yet it behaves exactly as the rule predicts: heavily engaged in proxies,
barely over-claimed. So the refined thesis holds across all five sectors.

**But the −0.86 is also the catch, and I won't hide it** (see confounders): "soft vs costly" and
"rare-vs-frequent in the proxy" are here almost the *same variable*, so I can describe the
pattern cleanly but cannot fully attribute it to conformity-driven cheap talk over the
mechanical max-norm effect.

### Confounders (the part I most want to be honest about)

- **Trendiness vs sector-conformity — I can't fully separate them.** A theme being "expected"
  and being "over-claimed" might both just track how visible/fashionable the theme is
  generally, not sector-conformity specifically. The partial control (per theme, over-claim
  where it's expected vs where it isn't) now has enough sectors to read: human_progress
  (+0.26), heritage (+0.16) and innovation (+0.15) are over-claimed clearly *more* where
  expected (consistent with conformity), people_talent (+0.01) and operational (+0.02) are
  flat, and customer_client_focus is *negative* (−0.05). So conformity shows up for the soft
  themes but not the material ones — which is suggestive, not clean, because it overlaps the
  frequency story below.
- **Frequency confounder — and it nearly *is* the refined thesis.** Over-claiming is
  mechanically smaller for a theme the proxy discusses a lot (max-normalization: a frequent
  theme is near the proxy's top, so `p[t]` is high and `over[t]` small). Across all 2,673
  theme-cells the Spearman of over-claim vs proxy frequency is **−0.25**; restricted to the
  expected themes that drive Finding 3 it is **−0.86**. That second number is the one to worry
  about: my "costly/material" stand-in *is* proxy frequency, so the substantive story (soft,
  unenforced values get over-claimed) and the mechanical one (rare-in-proxy themes score higher
  by construction) are the same measurement read two ways. I think they genuinely coincide —
  the proxy detailing a value at length *is* what "being compelled to back it up" looks like —
  but I can describe the pattern, not prove the mechanism over the artifact. That's the honest
  ceiling on Finding 3.
- **"Soft vs costly" labels are mine.** The proxy-frequency ordering is objective, but calling
  heritage "soft" and operations "material" is my post-hoc reading; the data orders the themes,
  I interpret them.
- **`low_evidence` excluded**, consistent with Part 3 (thin website pages can't carry a
  reliable profile).

---

# Part B — Why this question grabbed me (first-person)

<!-- TODO (Ssaumya): rewrite this whole section in my own voice before final submission, same as Part 3 Part B. Reasoning is mine, phrasing is drafted. Kill the em-dashes, cut the 'what grabbed me' / 'my gut' narration, plainer sentences. -->

What grabbed me about this was a specific intuition: that the most *expected* virtues are the
cheapest to fake. If you're an energy company, everyone expects you to care about the
environment — so you almost have to say it, whether or not you do anything about it. Whereas a
value nobody expects from your sector, you'd only claim if you actually meant it. So my prior
was that over-claiming should concentrate on the sector-expected themes: the social pressure
is to *say* the value, and there's nothing forcing you to back it up where it counts, in the
filings. I genuinely expected this to hold, and I expected energy + environment to be the
poster child.

So I set it up the simplest honest way: mark each sector's expected themes from what its
companies actually profess on their websites, then split each company's over-claiming into the
expected themes versus the rest, and see if the expected side is bigger. I reused everything
from Part 3 so I wasn't quietly changing the measure mid-stream.

The first result, on a two-sector slice, almost talked me out of it. Energy did what I
expected, but Financials did the opposite and the effect washed out — so I nearly concluded
"sector expects it → over-claims it" was at most a weak tendency. I'm glad I scaled before
believing that, because it was a sampling artifact: my slice had paired the strongest sector
with the single reversal. Across all five sectors the prior holds plainly — four of five
positive, two-thirds of companies positive. The lesson I'll keep is that a clean two-point
story is exactly the kind I should distrust until the rest of the data is in.

Then the energy case study turned my prior on its head, in the most useful way. I was sure
environment would be energy's biggest over-claim. It's almost its smallest — eighth of eleven.
When I looked at why, it made complete sense and taught me something: energy proxies actually
talk about the environment a lot, because for an oil company climate is a material, regulated,
litigated risk they're forced to address in the filing. So environment isn't cheap talk for
them — it's the one expected value they're genuinely compelled to back up. The cheap talk is
somewhere quieter: heritage, innovation, human progress — soft image themes the proxy has no
reason to detail. I'd had the mechanism right (expected values are easy to say) but applied it
to exactly the wrong theme, because I forgot that some expected values are *also* the ones
outside forces make you act on.

That mistake was actually the most useful thing that happened, because it gave me a sharper
question than I started with: maybe the gap isn't about "expected" at all, but about whether an
expected value is *soft* (heritage, image) or *costly* (regulated, material). When I tested
that across sectors — using how much the proxy engages a theme as the stand-in for
costly/enforced — it lined up almost perfectly: the soft expected values are over-claimed most,
the material ones least, correlation around −0.86. Energy wasn't special; it was just the first
place I noticed a rule that holds everywhere.

But that −0.86 is also where I have to stop myself, because it's *too* clean. My measure of
"costly" is proxy frequency, and the measure mechanically hands a small over-claim to any theme
the proxy discusses a lot — so the substantive story and the mechanical artifact are basically
the same number here. I believe they genuinely coincide (a filing detailing a value at length
really is what backing it up looks like), but I can only honestly say I've *described* the
pattern, not proven the mechanism. And the other confounder still stands: "expected" and
"over-claimed" might both just track what's generally fashionable; the control points toward
real conformity for the soft themes but it leans on the same frequency overlap, so I won't
oversell it.

What I'd explore next is the consequences question below — whether any of this over-claiming
actually costs companies anything.

---

## Consequences extension — do over-claimers face real consequences? (reasoned, not built)

Part 3 already dropped a hint here. Its contested-proxy validity check found that the
company-years where activists openly fought the board — **XOM 2021 (Engine No. 1, 77th
percentile) and SBUX 2024 (89th)** — sit high in over-claiming, while a single-issue fight
(MCD/Icahn) doesn't. That's the seed of the natural next question: **do over-claimers actually
get punished for the gap** — by activists, regulators, the press, employees, or the market?

How I'd test it, without overreaching: take the per-company-year over-claiming level and
trajectory as the predictor, and line up *independent* outcome signals that don't reuse the
same text — shareholder-proposal counts and contested elections (already in EDGAR, where Part
2 lives), ESG-litigation or regulatory actions, Glassdoor-style sentiment, or abnormal stock
returns around proxy season. Then ask whether high or *widening* over-claiming predicts more
of those, controlling for size and sector. The honest framing is that this stays
*speech-vs-consequence*, not proof of causation — an over-claimer drawing a fight could be
cause (the gap invites scrutiny) or effect (a company under attack puffs up its website). I'd
treat it as the same kind of soft external anchor Part 3 used, just with more outcomes. I'm
explicitly **not** building it here — it's the reasoned extension, not Part 4's deliverable.

---

## Caveats / limitations

- **Preliminary and small-n.** All five sectors but only 40 companies, unevenly split
  (Technology n=5, Energy n=10). The per-sector gaps are directional, not significance-tested,
  and themes expected in few sectors thin out the conformity control.
- **Two unresolved confounders** (trendiness; frequency, which is nearly collinear with the
  refined thesis at −0.86) — see Part A; neither is fully separable from the effect I'm after.
- **"Expected" is defined from website claims (Part 1),** so it inherits Part 1's coverage
  gaps, and is itself a *speech* signal — "the sector says it," not "the sector is objectively
  about it."
- **Everything inherits Part 3's framing:** speech-vs-speech, not words-vs-behavior.

---

## How to run

```bash
./.venv/bin/python scripts/p4_explore.py Energy Financials   # the slice
./.venv/bin/python scripts/p4_explore.py                     # all five sectors
```

Pure computation over Parts 1–3 outputs — no network, no API. Writes
`data/part3/output/part4_{by_sector,per_company,theme_controls,energy_case}.csv`.
