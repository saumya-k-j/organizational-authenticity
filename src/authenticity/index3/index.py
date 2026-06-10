"""The Organizational Authenticity Index: emphasis-weighted, asymmetric over-claiming
between the website (Part 1) and the proxy (Part 2), per company-year, plus trajectory.

See PART3_README.md for the precise definition and the reasoning. In brief, per
company-year scored only where BOTH channels have data:

  1. Take each channel's per-theme emphasis over the 11 DISCRETIONARY themes.
  2. MAX-normalize each side within itself (divide by that side's top theme). This makes
     the comparison about RELATIVE emphasis, immune to the channels' very different
     absolute volumes (short dense website vs long dilute proxy).
  3. Per theme, over[t] = max(0, web_rel[t] - proxy_rel[t]); under[t] = the reverse.
  4. over_claim_index = sum_t over[t]  (HIGHER = more over-claiming = LESS aligned).
     under_claim_index = sum_t under[t], recorded separately and NOT penalized.

LEVEL (per-year index) is kept separate from CHANGE (year-over-year delta), so a company
that repeats itself reads as steady, not shifting. Trajectory is the slope of the level
across 2016-2024.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DISCRETIONARY_THEME_KEYS, OUTPUT_DIR
from .emphasis import proxy_emphasis, website_emphasis

_DISC_COLS = [f"theme_{k}" for k in DISCRETIONARY_THEME_KEYS]
# A year is called widening/closing only past this |slope| (index-units per year); inside
# it the trajectory is "flat". Modest by design — we don't over-read small drifts.
_TRAJ_EPS = 0.03

# Minimum evidence for a TRUSTWORTHY score. The website is the binding side (proxies are
# never short — min ~20k words). Below ~120 website words the max-normalized 11-theme
# emphasis profile is degenerate: in the Part 1 data, pages under 120 words register a
# median of only 1-3 of the 11 themes (44-68% hit <=2 themes), so the profile is near
# one-hot and the over/under split is dominated by which single theme happened to appear.
# At >=120 words essentially no page registers <=2 themes — a real profile exists. So 120
# is where an emphasis comparison becomes meaningful, not an arbitrary cutoff.
MIN_WEB_WORDS = 120
# Defensive floor for the proxy side; it never triggers in this dataset (min ~19,780) but
# documents the symmetric intent — either side being too thin flags the cell.
MIN_PROXY_WORDS = 5000


def _max_norm(vec: np.ndarray) -> np.ndarray | None:
    """Scale a non-negative emphasis vector by its max (top theme -> 1.0). None if the
    document has no discretionary value terms at all (emphasis undefined)."""
    m = vec.max()
    return vec / m if m > 0 else None


def compute_index(tickers: list[str] | None = None) -> pd.DataFrame:
    """Per-company-year index table. Scores ONLY company-years present in BOTH channels;
    everything else is simply absent (a documented gap, never a zero row)."""
    web = website_emphasis(tickers)
    pxy = proxy_emphasis(tickers)

    merged = web.merge(pxy, on=["ticker", "year"], suffixes=("_web", "_pxy"))
    rows = []
    for r in merged.itertuples(index=False):
        d = r._asdict()
        w = _max_norm(np.array([d[f"{c}_web"] for c in _DISC_COLS], dtype=float))
        p = _max_norm(np.array([d[f"{c}_pxy"] for c in _DISC_COLS], dtype=float))
        if w is None or p is None:
            continue  # degenerate doc with zero value terms -> unscoreable, skip (not 0)
        over = np.maximum(0.0, w - p)
        under = np.maximum(0.0, p - w)
        web_words, proxy_words = int(d["web_words"]), int(d["proxy_words"])
        rows.append({
            "ticker": d["ticker"], "sector": d["sector_web"], "year": d["year"],
            "over_claim_index": round(float(over.sum()), 4),
            "under_claim_index": round(float(under.sum()), 4),
            # the single theme the website over-claims most — for interpretation
            "top_over_theme": DISCRETIONARY_THEME_KEYS[int(over.argmax())] if over.max() > 0 else "",
            "top_under_theme": DISCRETIONARY_THEME_KEYS[int(under.argmax())] if under.max() > 0 else "",
            # evidence size + low-evidence flag (kept in the data; excluded from rankings/stats)
            "web_words": web_words, "web_chars": int(d["web_chars"]), "proxy_words": proxy_words,
            "low_evidence": bool(web_words < MIN_WEB_WORDS or proxy_words < MIN_PROXY_WORDS),
        })

    df = pd.DataFrame(rows).sort_values(["ticker", "year"]).reset_index(drop=True)
    # CHANGE is the year-over-year delta of the LEVEL, within a company, between
    # consecutively-scored years only (gap-aware: a skipped year breaks the chain).
    df["prev_year"] = df.groupby("ticker")["year"].shift(1)
    df["prev_level"] = df.groupby("ticker")["over_claim_index"].shift(1)
    consecutive = df["year"] - df["prev_year"] == 1
    df["yoy_change"] = np.where(consecutive, df["over_claim_index"] - df["prev_level"], np.nan)
    df = df.drop(columns=["prev_year", "prev_level"])
    df.to_csv(OUTPUT_DIR / "part3_authenticity_index.csv", index=False)
    return df


def compute_trajectory(index_df: pd.DataFrame, exclude_low_evidence: bool = True) -> pd.DataFrame:
    """Per company: is over-claiming WIDENING or CLOSING across its scored years? OLS slope
    of the level on year. Low-evidence years are dropped by default so a thin page can't tilt
    a slope. Requires >=2 trustworthy years; fewer -> 'insufficient_data'."""
    rows = []
    for tk, g_all in index_df.groupby("ticker"):
        g = g_all[~g_all["low_evidence"]] if exclude_low_evidence else g_all
        g = g.sort_values("year")
        n_excluded = len(g_all) - len(g)
        yrs = g["year"].to_numpy(float)
        lvl = g["over_claim_index"].to_numpy(float)
        n = len(g)
        if n < 2:
            slope, direction = np.nan, "insufficient_data"
        else:
            slope = float(np.polyfit(yrs, lvl, 1)[0])
            direction = ("widening" if slope > _TRAJ_EPS
                         else "closing" if slope < -_TRAJ_EPS else "flat")
        rows.append({
            "ticker": tk, "sector": g_all["sector"].iloc[0], "n_years": n,
            "n_low_evidence_excluded": n_excluded,
            "first_year": int(yrs[0]) if n else None, "last_year": int(yrs[-1]) if n else None,
            "first_level": round(float(lvl[0]), 4) if n else np.nan,
            "last_level": round(float(lvl[-1]), 4) if n else np.nan,
            "slope_per_year": round(slope, 4) if n >= 2 else np.nan,
            "trajectory": direction,
        })
    out = pd.DataFrame(rows).sort_values("slope_per_year", ascending=False)
    out.to_csv(OUTPUT_DIR / "part3_trajectory.csv", index=False)
    return out
