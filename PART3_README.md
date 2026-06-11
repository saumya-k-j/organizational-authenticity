# Part 3: The Organizational Authenticity Index

A single number, per company-year, for **emphasis-weighted over-claiming**: how much *more*
a company's public website emphasizes each value than its proxy filings back up. It grades by
degree, is asymmetric (over-claiming is penalized, modesty is not), and scores only where both
sides exist. A **trajectory** shows whether the gap is widening or closing over 2016–2024.

This index does **not** measure words versus behavior. A proxy statement is not behavior. It is a legal document, more accountable and costlier to lie in than a homepage, but still the company describing itself. So the index compares two
*registers of corporate speech*: **unconstrained self-presentation** (the website, Part 1)
versus **accountable self-presentation** (the proxy, Part 2). 

> **Status: full run, 301 scored company-years across 44 companies; 243 high-evidence
> (58 flagged `low_evidence`).** A company-year is scored only where both a Part 1 website
> page and a Part 2 proxy exist; the bound is Part 1's 72% web coverage (5 companies, incl.
> Apple, have no scorable website and drop out entirely). Distribution and rankings below use
> the 243 high-evidence cells (see step 10 / methodology note).

---

# Part A: Precise definition

For each company `c` and year `y`:

**1. Inputs.** The Part 1 website cleaned text and the Part 2 proxy per-theme emphasis.

**2. Themes (11 of 13).** We score the frozen 13-theme taxonomy *minus* the two themes that
**observably dominate every proxy**: `leadership_governance` and `profitable_growth`. In the
Part 2 data governance runs at 26–31 mentions per 1,000 words, 3.5–5.6× the top discretionary
theme in every sector, and is the single most-emphasized topic for nearly every company-year.
Leaving them in mechanically dominates the over-claiming math (quantified in "Implementation
decisions"). Both themes remain fully tagged and stored in `part2_disclosure_metrics.csv`;
only the index *scoring* skips them. The remaining **11 discretionary themes** are the index's
scope.

**3. Emphasis vectors.** For each side, a per-theme emphasis over the 11 themes:
- **Website `W[t]`**: per-1,000-word frequency of theme `t`'s lexicon, **recomputed from
  Part 1's stored page text using Part 2's exact lexicon** (`disclosure.textstats`). Part 1
  itself stored only *binary* theme tags, so to grade by degree on a scale comparable to the
  proxy, the website emphasis must be re-measured the identical way.
- **Proxy `P[t]`**: Part 2's `theme_<t>` per-1,000-word frequency (already computed with
  that lexicon).

**4. Within-document max-normalization.** Divide each side by its own largest theme:

```
w[t] = W[t] / max_s W[s]        p[t] = P[t] / max_s P[s]
```

so each side's top discretionary theme = 1.0 and every theme is expressed *relative to that
side's strongest emphasis*. This makes the comparison about **relative emphasis profile**,
immune to the two channels' very different absolute volumes (a short, dense values page vs a
long, dilute proxy). If either side has no discretionary value terms at all (`max = 0`), the
company-year is **unscoreable** and excluded as a gap, never scored 0.

**5. Per-theme over- and under-claiming (asymmetric).**

```
over[t]  = max(0, w[t] − p[t])      # website emphasizes t more than the proxy does
under[t] = max(0, p[t] − w[t])      # the reverse
```

**6. Aggregate (the LEVEL), per company-year.**

```
OverClaimIndex(c,y)  = Σ_t over[t]      ← THE INDEX
UnderClaimIndex(c,y) = Σ_t under[t]      ← recorded separately, NOT penalized
```

**Direction convention: higher `OverClaimIndex` = more over-claiming = less aligned.**
`UnderClaimIndex` (discloses more than it advertises, i.e. modesty) is reported alongside but is
never added into the index and never penalized.

**7. Scoring domain.** A company-year is scored **only if both** a Part 1 (non-empty website)
and a Part 2 cell exist. Every other company-year is simply **absent** from the output, a
documented gap, never a zero row. (In Part 1, 5 companies and many individual years have no
website text; those cannot be scored.)

**8. LEVEL vs CHANGE.** The level is step 6. The change is the
year-over-year delta of the level, **only between consecutively-scored years**:

```
yoy_change(c,y) = OverClaimIndex(c,y) − OverClaimIndex(c,y−1)   if y−1 is also scored, else undefined
```

A company that repeats its wording gets the same level two years running and therefore a
change of 0: steadiness, not a shift. A one-year gap breaks the chain (no spurious change
across it).

**9. TRAJECTORY (required output).** Per company, the OLS slope of `OverClaimIndex` on `year`
across its trustworthy scored years (≥2): `slope > +0.03 → widening`, `slope < −0.03 →
closing`, else `flat`. Widening = the over-claiming gap is growing over 2016–2024.

**10. EVIDENCE FLAG (`low_evidence`).** Each scored cell records its evidence size
(`web_words`, `web_chars`, `proxy_words`) and a boolean `low_evidence`, true when the
website has **< 120 words** (or, defensively, the proxy < 5,000 words; never triggers here,
proxies run ~20k+). 120 words is not arbitrary: in the Part 1 data, pages below it register a
median of only 1–3 of the 11 themes (44–68% hit ≤ 2 themes), so the max-normalized emphasis
profile is near one-hot and the over/under split is dominated by whichever single theme
happened to appear. A thin "values" stub then scores as near-perfect alignment (e.g. AVGO
2016 at 114 words, TMO 2019 at 28 words both scored ~0.00 and topped the "most-aligned"
list). At ≥ 120 words essentially no page registers ≤ 2 themes, so a real profile exists.
`low_evidence` cells are **kept in the data but excluded by default** from the distribution,
the rankings, and the trajectory slopes: documented, not hidden, never silently zeroed.

Outputs: `data/part3/output/part3_authenticity_index.csv` (per company-year: level,
under-claim, yoy-change, top over/under theme, `web_words`/`proxy_words`/`low_evidence`) and
`part3_trajectory.csv` (per company; `n_years` counts trustworthy years,
`n_low_evidence_excluded` records the rest).

---

# Part B: My reasoning

When I first looked at this, the obvious move seemed simple: for each company, each year,
compare how much what they said on their website matched what they disclosed in their
filings, and average it out. That felt too naive almost immediately. Real life has too
many things going on for a flat average to mean much.

The first problem was **missing data**. If a company has no website text for a
year and I score that as zero, I'm saying "perfectly misaligned", but that's a lie; I just
don't have the data. So a missing year has to be a documented gap, never a zero. I can only
score a company-year where I actually have both sides.

Then I worried about the opposite: what if a company says the exact same thing two years
running? My method might read that as a "change" when nothing changed. So I had to keep the
**level** of alignment in a year separate from the **change** between years. Identical wording
just means the company held steady. 

The next issue was **time**. A single per-year score is just a
snapshot. A company might be badly aligned one year and improve a lot the next, and that
trajectory matters more than any single year. A company steadily closing the gap between its
words and its substance is telling a more honest story than one drifting apart. So the index
needs a trajectory (is the gap widening or closing across 2016–2024) and not just a snapshot.

Once the structure felt right, I had to decide what **"alignment" actually means**. The
simplest options were checking whether the same themes appear on both sides (overlap), or
whether the company ranks themes in the same order in both places (rank agreement). I rejected
both as too simplistic. Overlap treats a meaningful match and a throwaway match the same, and
rank agreement is mechanical, neither captures what authenticity actually is.

What it came down to: **authenticity is about not claiming what you don't back up.** A
company that loudly advertises sustainability on its website but barely mentions it in its
filings is over-claiming. That's the inauthentic move. The reverse, disclosing more than you
advertise, isn't dishonest, it's modest, so I don't penalize it, though I record it as its
own signal. So I built the core around over-claiming: saying more than you back up.

And I didn't want it binary. There's a real difference between making sustainability your
number-one website message but your twentieth filing topic, versus fifth on the site and
eighth in the filing. Both technically "match," but the first over-claims far more. So I made
it **emphasis-weighted**: how much more a company emphasizes a value than its filings
support, not just whether the theme appears.

Then I asked whether I could actually validate the proxy side.
I'd been loosely calling the website "say" and the proxy "do", but a proxy statement isn't
behavior. It's a legal document, more accountable and costlier to lie in than a homepage, but
still the company describing itself. So what I'm really measuring isn't words versus deeds;
it's **two registers of corporate speech**: unconstrained self-presentation (website) versus
accountable self-presentation (filing). I'd rather state that honestly than overclaim what my
measure does.

That same honesty is why I left some things out of the math. I kept wondering about
**confounders**: what if a company couldn't do what it said because the market turned bad
that year? But that doesn't belong inside the index. The moment I start correcting for the
market, I'm mixing a text comparison with an economic model and can't defend either cleanly.
So confounders like market conditions go into the limitations and interpretation, not the
formula.

For the same reason I kept the core index **theme-neutral**. I had an idea about weighting
themes by how costly or sector-expected they are (whether a value everyone in an industry
claims is just box-ticking), but that introduces a judgment I'd have to defend and would muddy
a measure I want clean. So I deferred that whole question to Part 4, where exploration is the
point.

The last thing was **evidence**. When I looked at which companies came out
"most aligned," the top of the list was a near-empty page scoring almost zero: a website with
barely twenty or thirty words on it. That wasn't alignment; it was nothing to measure. So I
went back and checked how much text a page actually needs before the emphasis profile means
anything, by counting how many of the value themes register as the page gets longer. Below
roughly 120 words the themes collapse. A page that short usually names one or two values, not
a profile, so whichever single theme happened to appear runs the whole score. Above that a
real spread of themes shows up. So I added a low-evidence floor: cells under that threshold
stay in the data, flagged, but I keep them out of the rankings and the distribution by default,
so a tagline can't masquerade as the most honest company in the dataset.

In the end the index does one thing: per company-year, it measures emphasis-weighted
over-claiming (how much a company says beyond what it backs up), scored only where I have
both sides, kept honest about being speech-vs-speech, with a trajectory on top to capture
whether companies are closing or widening that gap over time.

---

## Implementation decisions beyond that reasoning 

Three mechanical choices the reasoning above did not settle, surfaced here:

1. **Website emphasis is recomputed, not reused.** Part 1 stored only binary present/absent
   theme tags. Grading by degree requires a frequency, measured the *same* way as the proxy,
   so the website emphasis is recomputed from Part 1's saved page text with Part 2's lexicon.
   The alternative (binary website tags vs graded proxy) would not be comparable.
2. **Excluding `leadership_governance` and `profitable_growth` from the scoring.** Looking at
   the proxy data, these two themes dominate every sector. Governance runs at roughly 26–31
   per thousand words, four to six times larger than any other theme, and it's the single
   most-emphasized topic for nearly every company in every year. Some of that is genuine and
   some reflects SEC-mandated disclosure of board and compensation matters, and my tagging
   can't cleanly separate the two. But regardless of cause, leaving these themes in
   mechanically dominates the over-claiming computation and drowns out the discretionary
   values the index is meant to capture. Including all thirteen themes nearly doubles the
   mean (1.24 → 2.29) and reorders companies (rank correlation only 0.67). So I scored only
   the eleven discretionary themes. This is a deliberate trade: it removes the structural
   distortion at the cost of any genuine governance/profit signal, which I flag as a
   limitation. (Both themes stay tagged and stored in the Part 2 data; only the index math
   skips them.)
3. **Max-normalization, not share-normalization.** Normalizing each side to sum to 1 (a
   proper distribution) would force total over-claiming to equal total under-claiming by
   construction (it becomes total-variation distance), which would make the asymmetry vacuous
   and penalize a modest under-claimer as much as an over-claimer. Max-normalization (anchor
   to each side's top theme) keeps over- and under-claiming genuinely separable, which is what
   the asymmetry requires.

---

## Validity checks

**(1) Contested-proxy cluster.** Do the company-years where activists openly contested the
proxy sit high in the over-claiming distribution (percentiles taken within the high-evidence
cells)? On the full run, **two of the three land high**: **XOM 2021 (Engine No. 1) at the
77th percentile** and **SBUX 2024 at the 89th**, both elevated, as the hypothesis predicts.
**MCD 2022 (Icahn) is mid-pack (47th)**, the honest partial exception (Icahn's fight was over
a single supply-chain issue, not the company's whole self-presentation, so it needn't move
the aggregate). A soft external anchor, not proof, but it points the right way. Output:
`part3_validity_contested.csv`.

**(2) Diversity hard-facts, the only check that reaches past speech.** We LLM-extract the
actual board composition disclosed in each proxy (women / racially-ethnically diverse director
nominees) and test whether a company's stated diversity emphasis (website) tracks its real
board diversity: authentic commitment should correlate positively; cheap talk should not.


---

## Distributional properties (high-evidence: 243 of 301 scored company-years)

`OverClaimIndex`: range **[0.07, 3.57]**, mean **1.30**, median **1.20**, std **0.78**
(quartiles 0.63 / 1.66). The right-skew and the 3.5-point spread show the measure
discriminates rather than collapsing everyone to one value. Most-over-claiming companies
cluster in **Energy** (COP, MPC, PSX top the table; websites that market
sustainability/community/safety well beyond their proxies' emphasis) plus a few
Healthcare/Consumer names (LLY, TSLA, NKE); the genuinely **least**-over-claiming are
**Citigroup, Home Depot, Bank of America**, large pages whose website emphasis tracks their
proxies closely. `UnderClaimIndex` runs higher on average: proxies disclose a broader value
set than websites advertise, the modest direction, which the index correctly declines to
penalize.

**The evidence flag mattered.** Before flagging, the "most-aligned" list was topped by
artifacts: AVGO 2016 (114-word page) and TMO 2019 (28 words) scored ~0.00 not because they
were aligned but because there was almost nothing to compare; the former max (GOOGL 2022 at
4.39) was likewise a thin-page artifact. Excluding the 58 `low_evidence` cells removes all
four no-evidence companies (AVGO, META, TGT, TMO drop to `insufficient_data`) and leaves the
real low-over-claimers (C, HD, BAC) standing. The numbers above are post-exclusion.

---

## Limitations

- **Speech vs speech, not words vs behavior.** Both sides are the company describing itself.
  The proxy is the more accountable register, but it is not conduct. The index measures
  alignment between two self-presentations.
- **Coverage gaps.** Only company-years with both a website page and a proxy are scored
  (301 of 450 possible, bounded by Part 1's 72% web coverage). Five companies (incl. Apple)
  have no scorable website and drop out entirely. Gaps are documented, never zeroed.
- **Thin website pages (`low_evidence`).** 58 of 301 scored cells rest on a website page under
  120 words, too thin for a reliable 11-theme emphasis profile (step 10). They stay in the
  data, flagged, but are excluded from the distribution, rankings, and trajectories by
  default; four companies (AVGO, META, TGT, TMO) have *no* high-evidence year and so carry no
  trustworthy index at all. This is a real coverage limitation of the website side, not the
  measure: Part 1's values pages are sometimes just a tagline.
- **Two themes excluded from scoring.** Removing `leadership_governance` and
  `profitable_growth` strips the structural distortion they cause (above) but also discards
  any *genuine* governance/profit over-claiming a company might do, a deliberate trade, noted
  so it isn't mistaken for a claim that those values don't matter.
- **Asymmetric document lengths / genres.** A values page is short and dense; a proxy is long
  and dilute. Max-normalization controls the *level* of this, but short website pages (median
  ~1,500 characters) make the website emphasis vector coarse and noisier than the proxy's.
- **Confounders are deliberately outside the formula.** Market conditions, sector norms, and
  the cost/expectedness of a given value all shape language independently of authenticity. By
  design they live here in interpretation, not in the index (see Part B). High over-claiming
  is a flag to investigate.

---

## How to run

```bash
./.venv/bin/python scripts/p3_index.py    MSFT JPM XOM MCD   # slice (or no args for all)
./.venv/bin/python scripts/p3_validate.py MSFT JPM XOM MCD   # (2) needs ANTHROPIC_API_KEY
```

Pure computation over the existing Part 1 + Part 2 datasets, no network. Outputs land in
`data/part3/output/`.
