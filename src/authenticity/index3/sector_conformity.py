"""Part 4 (exploratory): do companies over-claim MORE on the values their SECTOR EXPECTS?

Hypothesis (mine, stated in PART4_README): sector norms pressure a company to SAY a value
(an energy firm almost has to profess environmental concern), but nothing compels it to back
that up in its proxy. So sector-expected themes should carry a bigger say-vs-do gap.

This reuses Part 3 wholesale: the same 11 discretionary themes, the same max-normalized
emphasis, the same per-theme over-claiming, the same low_evidence exclusion. The only new
ingredients are (a) a per-sector definition of "expected" themes from Part 1 prevalence, and
(b) splitting each company's over-claiming into expected vs non-expected themes.

PRELIMINARY by design — the point is the reasoning and the honest confounder accounting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DISCRETIONARY_THEME_KEYS, OUTPUT_DIR, PART1_CSV
from .emphasis import proxy_emphasis, website_emphasis
from .index import MIN_WEB_WORDS, _max_norm

_DISC = DISCRETIONARY_THEME_KEYS
_DISC_COLS = [f"theme_{k}" for k in _DISC]

# A theme is "sector-expected" if a CLEAR MAJORITY of the sector's companies profess it. Two
# thresholds, both chosen to mean "most": a company counts as professing theme t if t appears
# in >= HALF its website-years (consistent, not a one-off mention); a theme is sector-expected
# if >= 60% of the sector's companies profess it. 60% is the "clear majority" cut and, in this
# data, sits in a natural gap between each sector's core fingerprint and its long tail.
COMPANY_CLAIM_YEAR_FRAC = 0.5
SECTOR_EXPECTED_FRAC = 0.60


def sector_expected_themes() -> dict[str, set[str]]:
    """{sector -> set of expected discretionary themes} from Part 1 website tags."""
    p1 = pd.read_csv(PART1_CSV)
    p1 = p1[p1["theme_categories"].fillna("").str.len() > 0]
    # company-level: does the company profess theme t in >= half its website-years?
    claims: dict[str, dict] = {}
    for (sec, tk), g in p1.groupby(["sector", "ticker"]):
        yearsets = [set(str(c).split("|")) for c in g["theme_categories"]]
        professed = {t for t in _DISC
                     if sum(t in ys for ys in yearsets) / len(yearsets) >= COMPANY_CLAIM_YEAR_FRAC}
        claims.setdefault(sec, {})[tk] = professed
    expected = {}
    for sec, comp in claims.items():
        n = len(comp)
        expected[sec] = {t for t in _DISC
                         if sum(t in p for p in comp.values()) / n >= SECTOR_EXPECTED_FRAC}
    return expected


def per_theme_overclaim(tickers: list[str] | None = None) -> pd.DataFrame:
    """Long table [ticker, sector, year, theme, over, proxy_freq] for HIGH-EVIDENCE cells —
    the per-theme decomposition Part 3 summed away. `proxy_freq` (raw per-1k) is kept for the
    frequency-confounder check."""
    web = website_emphasis(tickers)
    pxy = proxy_emphasis(tickers)
    m = web.merge(pxy, on=["ticker", "year"], suffixes=("_web", "_pxy"))
    m = m[m["web_words"] >= MIN_WEB_WORDS]  # low_evidence excluded, same as Part 3
    rows = []
    for r in m.itertuples(index=False):
        d = r._asdict()
        w = _max_norm(np.array([d[f"{c}_web"] for c in _DISC_COLS], float))
        p = _max_norm(np.array([d[f"{c}_pxy"] for c in _DISC_COLS], float))
        if w is None or p is None:
            continue
        over = np.maximum(0.0, w - p)
        for i, t in enumerate(_DISC):
            rows.append({"ticker": d["ticker"], "sector": d["sector_web"], "year": d["year"],
                         "theme": t, "over": round(float(over[i]), 4),
                         "proxy_freq": d[f"theme_{t}_pxy"]})
    return pd.DataFrame(rows)


def expected_vs_nonexpected(tickers: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Core comparison. Returns (per_company, by_sector, controls).

    For each company we average over-claiming PER THEME within its sector's expected set vs
    its non-expected set (mean-per-theme, so the unequal group sizes don't bias the sum), then
    take the gap. Positive gap => over-claims more on expected themes (the hypothesis)."""
    expected = sector_expected_themes()
    long = per_theme_overclaim(tickers)
    long["is_expected"] = [t in expected.get(s, set()) for s, t in zip(long["sector"], long["theme"])]

    # per company: mean over-claim on expected vs non-expected themes (avg across its years)
    per_company = (long.groupby(["sector", "ticker", "is_expected"])["over"].mean()
                   .unstack("is_expected").rename(columns={True: "over_expected", False: "over_nonexpected"}))
    per_company["gap"] = per_company["over_expected"] - per_company["over_nonexpected"]
    per_company = per_company.reset_index().dropna(subset=["gap"])

    by_sector = (per_company.groupby("sector")
                 .agg(n_companies=("ticker", "size"),
                      mean_over_expected=("over_expected", "mean"),
                      mean_over_nonexpected=("over_nonexpected", "mean"),
                      mean_gap=("gap", "mean"))
                 .round(4).reset_index())
    by_sector["expected_themes"] = by_sector["sector"].map(
        lambda s: ", ".join(sorted(expected.get(s, set()))) or "(none)")

    # CONTROL — trendiness vs sector-conformity: for each theme, is over-claiming higher in
    # sectors where it's expected than where it isn't? If the gap is theme-wide (same
    # everywhere) it's "trendy theme"; if it's bigger where expected it's sector-conformity.
    th = long.groupby(["theme", "is_expected"])["over"].mean().unstack("is_expected")
    th.columns = ["over_where_not_expected", "over_where_expected"]
    th["conformity_gap"] = th["over_where_expected"] - th["over_where_not_expected"]
    controls = th.round(4).reset_index().sort_values("conformity_gap", ascending=False)

    per_company.round(4).to_csv(OUTPUT_DIR / "part4_per_company.csv", index=False)
    by_sector.to_csv(OUTPUT_DIR / "part4_by_sector.csv", index=False)
    controls.to_csv(OUTPUT_DIR / "part4_theme_controls.csv", index=False)
    return per_company.round(4), by_sector, controls


def refined_thesis(tickers: list[str] | None = None) -> tuple[pd.DataFrame, float]:
    """Test the slice's refined idea across sectors: companies BACK UP expected values that
    are costly/material/enforced but OVER-CLAIM expected values that are soft/image. We have
    no direct 'enforcement' variable, so we use **proxy engagement** (mean per-1k frequency in
    the filing) as its observable stand-in — a value the proxy details heavily is one the
    company is in practice compelled to address. For every theme that is sector-expected
    somewhere, we line up its over-claim-where-expected against that proxy frequency.

    Returns (table, spearman). A strongly NEGATIVE spearman = soft (low-proxy-frequency)
    expected themes are over-claimed most, material (high-frequency) ones least — the refined
    pattern. The same number is the honest caveat: it shows the thesis is nearly collinear with
    the max-norm frequency effect, so 'soft' and 'rare-in-proxy' can't be separated here."""
    long = per_theme_overclaim(tickers)
    expected = sector_expected_themes()
    long["is_expected"] = [t in expected.get(s, set()) for s, t in zip(long["sector"], long["theme"])]
    oe = long[long["is_expected"]].groupby("theme")["over"].mean()
    pf = long.groupby("theme")["proxy_freq"].mean()
    tbl = (pd.DataFrame({"over_where_expected": oe, "proxy_freq_overall": pf})
           .dropna(subset=["over_where_expected"])
           .sort_values("over_where_expected", ascending=False).round(3).reset_index())
    spearman = float(tbl["over_where_expected"].corr(tbl["proxy_freq_overall"], method="spearman"))
    tbl.to_csv(OUTPUT_DIR / "part4_refined_thesis.csv", index=False)
    return tbl, round(spearman, 3)


def energy_case_study(tickers: list[str] | None = None) -> pd.DataFrame:
    """Rank the 11 themes by mean over-claiming among ENERGY firms — is environmental
    stewardship their biggest over-claim, given energy loudly SAYS environment (Part 1/2)?"""
    long = per_theme_overclaim(tickers)
    en = long[long["sector"] == "Energy"]
    if en.empty:
        return pd.DataFrame()
    rank = (en.groupby("theme")["over"].mean().sort_values(ascending=False)
            .round(4).reset_index().rename(columns={"over": "mean_over_claim"}))
    rank["rank"] = range(1, len(rank) + 1)
    rank.to_csv(OUTPUT_DIR / "part4_energy_case.csv", index=False)
    return rank


def frequency_confounder(tickers: list[str] | None = None) -> dict:
    """Flag the mechanical frequency effect: a theme frequent in the proxy is its likely top,
    so max-norm gives it a high p[t] and a small over[t]. Report the correlation so the reader
    can judge how much 'low over-claim' just means 'proxy talks about it a lot'."""
    long = per_theme_overclaim(tickers)
    corr = long["over"].corr(long["proxy_freq"], method="spearman")
    return {"spearman_over_vs_proxy_freq": round(float(corr), 3),
            "n": int(len(long))}
