# Part 3: What We Built and What It Says (plain-language summary)

## The finding, in one breath

A company's website and its formal investor filings often **do not emphasize the same
values**. The website is the company's marketing voice. The annual proxy filing is its
accountable, lawyer-reviewed voice to shareholders. We built a single score, an **authenticity
index**, that measures how much a company's website plays up values that its filings don't back
up, for each company each year. A higher score means a bigger gap between the two voices.

## What the score actually does

For each company and year we compared which values the website stresses against which values
the proxy filing stresses, then added up the cases where the website leans on something the
filing doesn't. We only score a company-year when we have **both** documents. A missing
website is recorded as a gap, never counted as a zero. We also flag and set aside cases where
the website page was too thin (a tagline of a few dozen words) to read reliably, so a
near-empty page can't pass as a perfectly honest one.

We covered **44 companies across 2016–2024** (about 300 company-years, ~240 after dropping
thin pages). Scores range from near-zero to about 3.6, with a typical company around 1.2. That
spread is wide enough that the score genuinely separates companies rather than rating everyone
the same.

## Who over-claims, who doesn't: the part a reader can act on

- **Over-claim the most: energy companies.** Three of the four highest scorers are energy:
  ConocoPhillips, Marathon Petroleum and Phillips 66. Their websites market sustainability,
  community and similar values well beyond what their filings emphasize. (Morgan Stanley is the
  notable non-energy name near the top, and Eli Lilly and Tesla also rank high.)
- **Track closest, the most aligned: Citigroup, Home Depot, and Bank of America.** Their
  website emphasis lines up with their filings. What they market is roughly what they tell
  shareholders.
- **Direction of travel matters as much as the level.** We also measured whether each company's
  gap is widening or closing over the decade. More companies are *closing* the gap than widening
  it, so their two voices are converging over time. A meaningful minority are drifting apart.

## A sanity check that it's measuring something real

The years when activist investors publicly fought a company's board are exactly the years you'd
expect self-presentation to be under strain. Two of the three such cases in our data,
**ExxonMobil's 2021 climate proxy fight and Starbucks' 2024 contest**, score among the
highest-over-claiming years in the whole dataset (top ~10–20%). The third (a single-issue fight
at McDonald's) sits mid-pack, which also makes sense. The score points the right way without
being told the answer.

## The limitation:

This index compares **two kinds of corporate speech, not words against real behavior.** A proxy
filing is more accountable and costlier to lie in than a homepage, but it is still the company
describing itself, not a measure of what it actually did. So a high score means "the company's
marketing leans on values its formal disclosures don't echo." That's a flag worth investigating,
not a verdict that the company is dishonest. Plenty of innocent reasons (different audiences,
different document purposes) can drive the gap. Treat the score as a question, not a conclusion.

## Bottom line

The website and the filing are two portraits a company paints of itself, and they frequently
don't match. The authenticity index turns that mismatch into one comparable number per company
per year. That's useful for spotting which companies' marketing runs ahead of their formal
disclosures (energy firms most of all), which keep the two in step (Citigroup, Home Depot, Bank
of America), and whether each is closing the gap or letting it grow.
