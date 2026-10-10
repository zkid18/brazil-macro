# Pre-registration — Brazil political lean vs outcomes, 1985–2026

Written: 2026-10-05T19:57:23Z (UTC), before any term-level result, test, adjustment, event study or scenario was computed.
Only the plan's anchor table (section 0.9) was re-computed beforehand; all anchors reproduced (Ibovespa USD 2026 YTD 22.8 vs 22.7 in the plan — rounding).

Executor notes recorded before results:
- 2026 outcome: warehouse has no result (political_events ends with the 2026-10-04 first-round row; registry git log has nothing newer). External, user-supplied, not in warehouse: first round 2026-10-04 Flávio Bolsonaro (PL, right) 47.0%, Lula (PT, left) 44.9%; run-off 2026-10-25. Scenarios stay conditional; primary branches = Lula IV (left) and Flávio Bolsonaro (right); centre kept as secondary.
- Baseline contrast: Δ = mean(left terms) − mean(right terms) under coding A (centre-right → right); centre terms (Sarney, Itamar) excluded from Δ but kept in Q0 and composites.
- Operational choice fixed now: every metric is converted to an annual series (level metrics: annual value; change metrics: annual first difference or annual log change), years attributed by the 1 July rule; term statistic = mean over the term's years. Monthly series are aggregated to calendar-year (mean for rates/ratios, Dec value for stocks); 2026 (Jan–Aug/Sep) included as a partial Lula III year for monthly series and flagged. Exact-date monthly term means are also reported in term_table.csv for the anchors.
- Bootstrap CI: two-stage cluster bootstrap (resample terms with replacement within each lean group, then years within term), 5,000 draws, seed 0.
- Equal prominence: buckets E (labour/distribution) and F (health/education/safety) are reported with the same detail as C (fiscal) and D (markets) in the summary.

## 2. Pre-registration (write `preregistration.md` with a timestamp BEFORE any result is computed)

**Primary question Q0 (variance decomposition):** across presidential terms since 1985, how much of the between-term variance in each outcome is explained by lean vs by the terms-of-trade cycle? H0-primary: ΔToT explains at least as much as lean for A1, D1, D2, C2. This is the headline, because both partisan narratives implicitly assume lean dominates.

**Family 1 — four pre-specified composites (primary tests, Holm-corrected at α = 0.10):**
- COMP-G "Growth": z-mean of A1, A2, A3, A4 (higher = better).
- COMP-S "Stability": z-mean of −B1, −B2 (lower real rate = looser, sign-neutral: report both), C1, −C2, D6, D8 (orientation fixed: higher primary balance, lower debt growth, better CA, more reserves = "better" for the right-narrative; the left narrative accepts these as costs, so the composite is labelled "orthodox stability" not "good").
- COMP-D "Distribution": z-mean of −E1, −E5, −E6, E3, −E2 (higher = more equal / better jobs).
- COMP-M "Markets": z-mean of D1, −D2 (BRL appreciation), −D4, −D5.
z-scores are computed across terms within each metric (terms with data), then averaged; composites exist for terms 4–9 fully and 1–3 partially.

**Family 2 — the 26 primary metrics individually (Benjamini–Hochberg at q = 0.10).** Family 3 — secondary metrics (descriptive, no inference).

**Direction expectations from each narrative (recorded now, both must be reported regardless of outcome):**

| Metric | Left narrative expects under left govt | Right narrative expects under left govt |
|---|---|---|
| A1 growth | higher (demand-led, credit, min wage) | lower (crowding-out, uncertainty) |
| A3 investment | higher (public investment) | lower (private crowding-out) |
| B1 inflation | no difference (BCB sets rates) | higher |
| B2 real rate | lower (fiscal–monetary coordination) | higher (risk premium forces BCB) |
| C1 primary balance | similar (Lula I–II surpluses) | lower |
| C2 debt change | similar | higher |
| D1 USD equity | no systematic difference | lower |
| D2 BRL | no systematic difference | weaker |
| D4 EMBI / D5 real yield | no difference | higher |
| E1 unemployment | lower | higher (labour rigidity) |
| E3 real min wage | higher | higher but at employment cost (E2 informality up) |
| E5 Gini / E6 poverty | lower | lower only during commodity booms (so adjusted effect ≈ 0) |
| F1–F5 health/safety | better | no difference |
| G1–G3 WGI | no difference | worse (CC) |
| H1 deforestation | lower | no difference / higher |

Both narratives agree on the sign for E3; disagree on most others. The pre-registration therefore defines "support for narrative X" per metric as: baseline point estimate has X's sign AND ≥ 80% of robustness-matrix cells share that sign AND the 80% cluster-bootstrap CI excludes zero. "No robust association" otherwise. Report every metric.

**Power statement (must appear verbatim in the report):** with term as the unit, the post-1995 sample has 3 left terms vs 3 non-left; the exact permutation distribution has C(6,3) = 20 labelings, so the smallest attainable two-sided p is 0.10. With all 9 terms (3 left vs 6 non-left): C(9,3) = 84, min p = 0.024. With 4-year mandates post-1995 (5 left: Lula I, Lula II, Dilma I, Dilma II, Lula III; 4 right: FHC I, FHC II, Temer, Bolsonaro): C(9,4) = 126, min p = 0.016, but mandates of the same president are not independent. Therefore no single metric can clear BH at q = 0.10 in the post-1995 term-level design; the study is an effect-size study with uncertainty bands, and the permutation p is reported with its floor.

---

## Robustness matrix (plan 3.4, verbatim)
### 3.4 Robustness matrix (every primary metric × every cell; summarise as sign-consistency share)
- Sample: 1985+ / 1995+ / 2003+.
- Unit: term / 4-year mandate (split FHC 1999-01-01, Lula 2007-01-01, Dilma 2015-01-01) / year-cluster.
- Lean coding: **A** centre-right → right (baseline); **B** centre-right → centre (right = Collor, Bolsonaro only); **C** Temer → centre, FHC → right; **D** drop transition/incomplete terms (Collor, Itamar, Temer, Lula III); **E** Dilma II (2015–16) coded as its own "crisis" unit and dropped.
- Attribution: contemporaneous / lag-1 / drop-first-year.
- Adjustment: raw / ToT / ToT+Brent (2000+).
- Transform: mean level / end−start change / rank.
Cells with fewer than 2 terms per side are left blank. Output `robustness_matrix.csv` (metric, cell, Δ, CI, sign) and a heatmap.
