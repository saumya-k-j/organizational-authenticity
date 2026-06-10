"""Event-coincidence analysis: do the proxy-language shifts line up in TIME with known
external events (Business Roundtable 2019, COVID/Floyd 2020, Engine No. 1 2021, the
anti-ESG backlash 2022-23, etc.)?

This is deliberately descriptive, not causal. For each (event, theme) hypothesis we:
  - take the all-company mean theme frequency per meeting-year,
  - compare a PRE window (2 years before the event's expected first reflection) to a POST
    window (the reflection year + the next), and
  - independently find the theme's own biggest year-over-year jump (data-driven), then
    check whether that breakpoint falls in the event's window.
A hypothesis is 'aligned' only if BOTH the direction matches and the data's own breakpoint
sits near the event. Direction-right-but-timing-off is 'partial'; wrong direction is 'no'.
We report misses honestly — the point is to test the hypotheses, not to confirm them.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from .config import CONFIG_DIR, OUTPUT_DIR, load_settings, load_taxonomy

_S = load_settings()
_Y0, _Y1 = _S["year_start"], _S["year_end"]
_THEME_KEYS = {t["key"] for t in load_taxonomy()["themes"]}

# Relative-change thresholds for calling a move (on per-1k-word theme frequencies).
_UP_REL = 0.15        # >=15% rise counts as a real increase
_FLAT_REL = 0.10      # within +/-10% counts as "flat" for plateau hypotheses


def _load_events() -> list[dict]:
    with (CONFIG_DIR / "events.yaml").open() as f:
        return yaml.safe_load(f)["events"]


def theme_year_means(metrics_csv: Path | None = None) -> pd.DataFrame:
    """All-company mean of each theme_<key> per meeting-year (index = year)."""
    path = metrics_csv or (OUTPUT_DIR / "part2_disclosure_metrics.csv")
    df = pd.read_csv(path)
    theme_cols = [c for c in df.columns if c.startswith("theme_")]
    return df.groupby("meeting_year")[theme_cols].mean()


def _biggest_jump_year(series: pd.Series) -> tuple[int, float]:
    """Year with the largest year-over-year increase, and that increase."""
    diffs = series.diff().dropna()
    if diffs.empty:
        return (int(series.index[0]), 0.0)
    y = int(diffs.idxmax())
    return y, round(float(diffs.loc[y]), 3)


def analyze_events(metrics_csv: Path | None = None) -> pd.DataFrame:
    means = theme_year_means(metrics_csv)
    rows = []
    for ev in _load_events():
        ry = ev["reflect_year"]
        pre_years = [y for y in (ry - 2, ry - 1) if _Y0 <= y <= _Y1]
        post_years = [y for y in (ry, ry + 1) if _Y0 <= y <= _Y1]
        for theme in ev["themes"]:
            col = f"theme_{theme}"
            if theme not in _THEME_KEYS or col not in means.columns:
                continue
            s = means[col]
            pre = float(s.loc[pre_years].mean()) if pre_years else float("nan")
            post = float(s.loc[post_years].mean()) if post_years else float("nan")
            rel = (post - pre) / pre if pre else 0.0
            jump_year, jump_val = _biggest_jump_year(s)
            near = ry - 1 <= jump_year <= ry + 1   # data breakpoint near the event?

            if ev["hypothesis"] == "up":
                if rel >= _UP_REL and near:
                    verdict = "aligned"
                elif rel >= _UP_REL:
                    verdict = "partial (rose, but biggest jump off-timing)"
                elif rel > 0:
                    verdict = "weak (small rise)"
                else:
                    verdict = "no (did not rise)"
            else:  # down_or_plateau
                if rel <= _FLAT_REL:
                    verdict = "aligned (flat/declined as hypothesized)"
                else:
                    verdict = f"no (kept rising +{rel*100:.0f}%)"

            rows.append({
                "event": ev["name"], "event_date": ev["date"], "theme": theme,
                "hypothesis": ev["hypothesis"], "reflect_year": ry,
                "pre_mean": round(pre, 3), "post_mean": round(post, 3),
                "change_pct": round(rel * 100, 1),
                "biggest_jump_year": jump_year, "biggest_jump": jump_val,
                "verdict": verdict,
            })
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_DIR / "part2_event_alignment.csv", index=False)
    return out
