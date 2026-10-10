# Brazil: political lean vs economic, social and market outcomes, 1985–2026 — with conditional 2027–2030 scenarios

_Generated 2026-10-05 20:12 UTC from `/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb` (read-only). Pre-registration: `preregistration.md` (written before results). Code: `politics_lean_study.py`, `make_charts.py`, `make_report.py`. Every warehouse number below carries its series_id; latest dates are in the Appendix._

## 0. External fact (NOT in the warehouse — fenced)

```text
EXTERNAL, user-supplied, not in brazil_macro.duckdb (political_events ends with the 2026-10-04 'first round' row and no result):
  First round 2026-10-04: Flávio Bolsonaro (PL, right) 47.0% · Lula (PT, left) 44.9%. Run-off 2026-10-25.
  Sources: CNN https://www.cnn.com/2026/10/04/americas/brazil-president-elections-2026-latam-intl
           Washington Post https://www.washingtonpost.com/world/2026/10/04/bolsonaro-lula-head-runoff-5-takeaways-brazils-election/
Use in this report: only to choose which scenario branches are presented as primary (Lula IV vs Flávio Bolsonaro).
It does not enter any estimate. Market data in the warehouse end 2026-10-01/02, so the market reaction to the
first-round result is NOT observable here.
```

## 1. Summary

**Q0 — how much of the between-term variation is lean, and how much is the terms-of-trade (ToT) cycle?** Across the 23 primary metrics, a Shapley split of between-term R² gives lean a median share of **0.09** vs ToT **0.26**; ToT matches or beats lean in **17/23** metrics at term level (year level: lean 0.13 vs ToT 0.09, ToT ≥ lean in 13/23). The pre-registered H0-primary (ToT explains at least as much as lean for A1, D1, D2, C2) **holds at term level for all four** (A1 GDP growth lean 0.09 vs ToT 0.31; D1 USD equity 0.02 vs 0.88; D2 BRL 0.14 vs 0.80; C2 Δdebt 0.00 vs 0.32), but at year level GDP growth tilts the other way (lean 0.19 vs ToT 0.12). Where lean does carry more weight it is in **policy instruments** — real policy rate, primary balance, interest bill, real minimum wage — and, at year level, in **labour and distribution** (unemployment lean 0.31 vs ToT 0.02; Δ Gini 0.26 vs 0.10); not in markets, the external accounts or debt. Neither factor explains most of the variance in most outcomes; the bulk is term-specific shocks (2002 confidence crisis, GFC, 2015–16 recession and impeachment, COVID, 2026 oil shock).

**Power statement (must appear verbatim in the report):** with term as the unit, the post-1995 sample has 3 left terms vs 3 non-left; the exact permutation distribution has C(6,3) = 20 labelings, so the smallest attainable two-sided p is 0.10. With all 9 terms (3 left vs 6 non-left): C(9,3) = 84, min p = 0.024. With 4-year mandates post-1995 (5 left: Lula I, Lula II, Dilma I, Dilma II, Lula III; 4 right: FHC I, FHC II, Temer, Bolsonaro): C(9,4) = 126, min p = 0.016, but mandates of the same president are not independent. Therefore no single metric can clear BH at q = 0.10 in the post-1995 term-level design; the study is an effect-size study with uncertainty bands, and the permutation p is reported with its floor.

Consequently **nothing clears Benjamini–Hochberg at q = 0.10 and no composite clears Holm at α = 0.10**; the results below are effect sizes with honest bands. The 80% cluster-bootstrap CIs (3–4 terms per side) are narrower than the permutation test implies; read 'robust-by-CI' as 'consistent direction', not 'significant'.

### Per-bucket findings (Δ = mean of left terms − mean of right/centre-right terms, coding A)

Buckets E (labour & distribution) and F (health, education, safety) are given the same space as fiscal and markets: the user's framing — that institutional quality is better read through health, social policy, poverty, inequality and education than through corruption indices — is adopted here. WGI is reported last among the social buckets for that reason.

**A. Growth.**
- **A1 Real GDP growth** — Δ L−R +1.96 % y/y (80% CI [+0.18, +3.78]; perm p 0.17, floor 0.029; sign-consistent in 98% of 480 cells; ToT-adjusted +2.34). Left terms grew faster, and the gap **widens** after ToT adjustment — but Collor (−1.3%) and Temer (−0.1%) sit on the right, and Dilma (1.2%) on the left; 2003+ only has Temer/Bolsonaro as 'right'.
- **A2 GDP per capita growth** — Δ L−R +2.45 % y/y (80% CI [+0.63, +4.27]; perm p 0.17, floor 0.029; sign-consistent in 97% of 480 cells; ToT-adjusted +2.35). 
- **A3 Investment (GFCF) % GDP** — Δ L−R +0.90 % GDP (80% CI [-0.56, +2.46]; perm p 0.51, floor 0.029; sign-consistent in 98% of 480 cells; ToT-adjusted +1.62). Investment shows no robust lean pattern raw; after ToT adjustment the left edge is +1.6 pts but the permutation test is uninformative.
- Composite COMP-G: Δ +0.72 z (80% CI [+0.30, +1.15], perm p 0.14, Holm 0.43); ToT-adj +1.09.

**B. Prices and rates.**
- **B1 Inflation (GDP deflator, log)** — Δ L−R -61.68 100·log(1+π) (80% CI [-135.65, -0.70]; perm p 0.57, floor 0.029; sign-consistent in 59% of 480 cells; ToT-adjusted -7.48). The raw gap is entirely Collor's hyperinflation (coded right); post-1995 and rank versions flip sign or vanish. No lean signal in inflation.
- **B2 Real policy rate (ex-ante)** — Δ L−R +3.89 % p.a. (80% CI [+1.14, +6.72]; perm p 0.30, floor 0.100; sign-consistent in 88% of 330 cells; ToT-adjusted +4.18). Real policy rates were **higher** under PT terms (Lula I–II 9.7, Lula III 8.9 vs Temer 5.3, Bolsonaro 2.3 — `real_policy_rate`), the right narrative's sign. But only 2 right terms exist post-2001, and both started after the 2015–16 recession; the start-level-adjusted gap is +1.0 pt.
**C. Fiscal.**
- **C1 Primary balance % GDP** — Δ L−R +2.99 % GDP (Dec, 12m) (80% CI [+0.98, +5.06]; perm p 0.20, floor 0.100; sign-consistent in 100% of 270 cells; ToT-adjusted +3.25). Left terms ran larger primary surpluses (Lula I–II +3.2% vs Temer −2.1%, Bolsonaro −2.3% incl. COVID). This contradicts the right narrative's expectation; but FHC's 1999–2002 surpluses are outside `primary_balance_gdp` coverage (starts 2002-11), and Lula III (−0.8) breaks the pattern.
- **C2 Δ Gross debt % GDP** — Δ L−R +0.36 pts/yr (80% CI [-3.43, +4.63]; perm p 1.00, floor 0.100; sign-consistent in 46% of 270 cells; ToT-adjusted +0.73). Gross-debt change has **no** lean pattern (sign-consistency below 50%). Only 4 terms observed (series starts 2006-12).
- **C4 Interest bill % GDP** — Δ L−R +1.12 % GDP (80% CI [+0.09, +2.12]; perm p 0.40, floor 0.100; sign-consistent in 93% of 270 cells; ToT-adjusted +1.03). Higher interest bill under left terms — mechanically tied to the higher real rate (B2).
- Composite COMP-S 'orthodox stability': Δ +0.16 z (80% CI [-0.20, +0.51], perm p 0.54) — no difference.

**D. Markets and external.**
- **D1 USD equity return (log)** — Δ L−R +1.38 % /yr (log) (80% CI [-25.74, +28.73]; perm p 1.00, floor 0.100; sign-consistent in 82% of 450 cells; ToT-adjusted +5.90). USD equity returns: no lean pattern; ToT explains ~0.9 of between-term variance.
- **D2 BRL appreciation vs USD (log)** — Δ L−R +5.80 % /yr (+ = stronger BRL) (80% CI [-7.27, +18.54]; perm p 0.60, floor 0.100; sign-consistent in 100% of 450 cells; ToT-adjusted +6.87). BRL: left terms saw a stronger BRL on average (driven by Lula I–II's commodity boom and FHC II's 1999/2002 devaluations — the 2002 'Lula panic' is booked to FHC under July-1 attribution); ToT explains ~0.8.
- **D3 Real effective exchange rate** — Δ L−R -4.01 index 2010=100 (+ = stronger) (80% CI [-18.06, +9.80]; perm p 0.77, floor 0.029; sign-consistent in 10% of 480 cells; ToT-adjusted -2.98). 
- Composite COMP-M: Δ +0.25 z (80% CI [-0.48, +1.05], perm p 0.70) — no difference over full terms. The lean signal in markets is in **event windows**, not in term averages (section 6).

**E. Labour and distribution (equal prominence).**
- **E1 Unemployment rate** — Δ L−R -2.36 % (80% CI [-4.11, -0.55]; perm p 0.17, floor 0.029; sign-consistent in 100% of 480 cells; ToT-adjusted -2.44). Unemployment was lower in left terms in **every** specification cell; start-level-adjusted change still favours left (−0.66 pt/yr). Temer/Bolsonaro inherited the 2015–16 recession (start 8.5% / 12.3%).
- **E3 Real minimum wage growth** — Δ L−R +3.06 % /yr (log) (80% CI [+0.97, +5.14]; perm p 0.10, floor 0.100; sign-consistent in 99% of 450 cells; ToT-adjusted +3.38). Real minimum wage grew ~3 pts/yr faster under left terms (Lula I–II +5.5%/yr, Lula III +3.3%, Dilma +2.2% vs Bolsonaro +0.1%, FHC +0.4%) — the one result both narratives predicted; its 'employment cost' (informality up, E2) is **not** visible: informality fell faster under left terms (E2 Δ −1.7 pts/yr, secondary).
- **E5 Δ Gini** — Δ L−R +0.29 pts/yr (80% CI [-0.88, +1.51]; perm p 0.97, floor 0.029; sign-consistent in 25% of 480 cells; ToT-adjusted +0.31). Gini change: the baseline sign is **misleading** — it is driven by Collor's 1990–92 'fall' (−3.4 pts/yr), which straddles the PNAD 1992 redesign (no 1991 survey). In 1995+ samples left terms reduce Gini faster in 87% of cells (Lula III −0.8/yr, Lula I–II −0.6 vs Temer +0.7, FHC −0.2). Start-level-adjusted Δ = −0.38 pts/yr. Pre-registered verdict stays 'no robust association'.
- **E6 Δ Poverty $3.00/day** — Δ L−R -0.89 pts/yr (80% CI [-1.99, +0.14]; perm p 0.29, floor 0.029; sign-consistent in 92% of 480 cells; ToT-adjusted -1.15). Extreme poverty ($3.00/day) fell faster under left terms in 96–100% of cells; ToT adjustment enlarges it (−1.15 pts/yr); 80% CI just touches zero raw. The $8.30 line (secondary) shows the same: Δ −2.1 pts/yr.
- Composite **COMP-D Distribution**: Δ **+0.92 z** (80% CI [+0.75, +1.10], perm p **0.029 = the design floor**, Holm 0.11); ToT-adjusted +1.00 z (p 0.029). Every left term scores above every right term on this composite — the most extreme labeling possible. It is the strongest lean association in the study and it **survives** the ToT control, but it still misses Holm at 0.10 (0.114) because of the 35-labeling floor.

**F. Health, education, safety (equal prominence).**
- **F1 Infant mortality change (log)** — Δ L−R -0.12 % /yr (− = improving) (80% CI [-2.63, +2.30]; perm p 0.97, floor 0.029; sign-consistent in 72% of 480 cells; ToT-adjusted -0.47). Infant mortality fell at ~3.3–3.4%/yr under both; the decline slowed after 2015 regardless of lean (Dilma −3.1, Temer −1.5, Bolsonaro −1.0, Lula III −1.2). In the 2003+ sample left terms are faster in every cell, but that is Lula I–II vs post-2016.
- **F5 Δ Homicide rate** — Δ L−R -0.02 per 100k /yr (80% CI [-1.41, +1.51]; perm p 1.00, floor 0.100; sign-consistent in 32% of 450 cells; ToT-adjusted +0.12). Homicide rate: no lean pattern; the biggest falls came under Bolsonaro (−1.5/100k/yr) and Lula III (−1.5, DATASUS 2024–25 preliminary).
- Secondary (descriptive, no inference): life-expectancy gain Δ +0.24 yrs/yr; govt health spending Δ -0.33 % GDP (WB, 2000–2023: right terms slightly higher — Bolsonaro's COVID years); education spending Δ -0.03 % GDP (to 2022); safety-net coverage Δ -6.7 pts (WB ASPIRE, 2006–2022, sparse).

**G. Institutions (WGI).**
- **GCC Δ WGI Control of Corruption** — Δ L−R -0.01 est. units/yr (80% CI [-0.07, +0.05]; perm p 0.80, floor 0.100; sign-consistent in 92% of 450 cells; ToT-adjusted -0.01). Control of Corruption deteriorated slightly more in left terms in 90–100% of cells, but by 0.01 units/yr — invisible against the WGI's own standard errors (~0.1–0.2).
- **GGE Δ WGI Government Effectiveness** — Δ L−R +0.02 est. units/yr (80% CI [-0.04, +0.08]; perm p 0.30, floor 0.100; sign-consistent in 88% of 450 cells; ToT-adjusted +0.01). 
- **GRL Δ WGI Rule of Law** — Δ L−R +0.02 est. units/yr (80% CI [-0.03, +0.07]; perm p 0.60, floor 0.100; sign-consistent in 93% of 450 cells; ToT-adjusted +0.02). 
- Read with the user's framing: on the outcome measures of state capacity that matter to households (E, F), left terms score better on distribution and the same on health and safety; the perception-based WGI shows no lean signal.

**H. Environment.**
- **H1 Primary forest loss** — Δ L−R -0.49 Mha/yr (80% CI [-1.00, +0.01]; perm p 0.40, floor 0.100; sign-consistent in 90% of 330 cells; ToT-adjusted -0.43). Primary-forest loss was lower in left terms in ~92% of cells (Lula I–II/Dilma/Lula III vs Temer/Bolsonaro, 2002+ only), CI touches zero; fire years (2016, 2024) and only 2 right terms limit it.

### Event study (daily; abnormal = raw change minus own-trend over [−250,−121])

- Six left wins/continuity events vs three right/centre-right transitions (2016 impeachment vote, 2018 run-off, 2019 inauguration). Over [0,+60] trading days, Ibovespa-USD abnormal return averaged **-3.8%** after left wins vs **+19.4%** after right transitions (Δ -23.1, permutation p 0.012, floor 0.012); BRL -0.5% vs +9.5% (p 0.04); 10y real yield (only 2016+) -11 bp vs -66 bp. Around the event itself ([−1,+1]) the difference is small and insignificant (Ibov USD -5.6, p 0.21).
- Caveats: the three right events are one episode (2016–2019, all from a post-recession trough with impeachment-era repricing), 2018 run-off and 2019 inauguration windows overlap, and 2022 run-off/2023 inauguration overlap. Brent-adjusted versions keep the sign and size (Ibov USD [0,+60]: −2.7% vs +17.7%). EMBI shows **no** lean difference at any window. Focus Selic/FX 'reactions' at 1 January inaugurations are mechanical (the 12-month-ahead horizon rolls at year start) and are ignored.
- First-round analogues: the largest single first-round moves in the data are 2014 (Ibov USD +10.1% [−1,+1], placebo p 0.03), 2018 (BRL +4.5%, NTN-B 10y −42 bp, p ≤ 0.02) and 2022 (Ibov USD +12.0%, BRL +4.4%, p ≤ 0.02) — all first rounds in which the right-of-centre candidate finished stronger than prices had implied (judged from the price action itself). Whether 2026 belongs to that group cannot be checked here.
- **2026**: the first-round reaction (Oct 5 onward) is not in the warehouse (`ibovespa_usd` ends 2026-10-01, `brl_usd` / NTN-B 2026-10-02). Pre-election pricing: all 2026 moves over [Jul 1→t−1], [Sep 1→t−1], [t−5→t−1] in BRL, Ibov USD and Ibov BRL sit inside the six-election interquartile range ⇒ by the pre-registered rule, **no unusual election premium was priced** before the vote. YTD the 2026 tape is unusually *strong* (Ibov USD +20.5% vs a historical IQR of −6.3 to +7.5; BRL +5.2% vs −13.3 to +3.4), the opposite of 2002's pre-election panic. Focus IPCA 12m rose more than usual Jul→t−1 (+0.52 vs IQR −0.18 to +0.44) — the oil shock, not obviously the election. The 10y real yield fell 42 bp Jul→t−1 (z −2.9 vs n=2 history; confounded by the Sep 17 Selic cut to 13.75).

### 2027–2030 scenarios — primary branches: Lula IV (left) vs Flávio Bolsonaro (right); centre secondary

History ranges are the post-1995 4-year mandates (inflation: 1996+, dropping the Real-plan transition year) of each lean (left: Lula I, Lula II, Dilma I, Lula III; right: FHC I, FHC II, Temer, Bolsonaro; Dilma II has <2 years). 'Model' = α_lean + β·ΔToT fitted on all 8 mandates, evaluated at ToT paths p25/p50/p75 of historical 4-year ToT changes (-1.4, +1.7, +3.5 log-pts/yr). ToT in 2025 sits at the 89% percentile of 1991–2025, so mean reversion (the p25 path) is a live risk. n ≤ 8 ⇒ illustrative ranges, never forecasts.

| outcome | Lula IV (left) | Flávio Bolsonaro (right) | centre (secondary) |
|---|---|---|---|
| GDP growth, %/yr | hist 2.5 to 3.8 (med 3.0); model 3.0 to 3.4 | hist 1.1 to 2.4 (med 1.9); model 1.4 to 1.8 | hist 1.1 to 2.4 (med 2.3); model 1.4 to 1.8 |
| Inflation (deflator, log %) | hist 6.8 to 7.9 (med 7.5); model 7.0 to 7.2 | hist 7.0 to 8.2 (med 7.7); model 7.5 to 7.7 | hist 6.4 to 8.7 (med 7.6); model 7.4 to 7.7 |
| Real policy rate, % | hist 6.1 to 9.9 (med 7.8); model 7.0 to 8.9 | hist 3.1 to 4.8 (med 3.9); model 2.6 to 4.6 | n<2 |
| Primary balance, % GDP | hist 0.9 to 3.0 (med 2.2); model 0.8 to 2.3 | hist -2.0 to -1.9 (med -2.0); model -2.9 to -1.5 | n<2 |
| BRL vs USD, %/yr (+ stronger) | hist -2.9 to 7.8 (med 3.1); model -7.9 to 7.8 | hist -13.3 to -5.5 (med -8.1); model -17.8 to -2.1 | hist -17.9 to -4.3 (med -8.8); model -18.0 to -2.3 |
| Ibovespa USD, %/yr | hist 5.0 to 24.7 (med 15.3); model 0.1 to 23.3 | hist -5.6 to 8.0 (med 0.4); model -8.6 to 14.7 | hist -7.1 to 13.3 (med 2.7); model -6.3 to 17.9 |
| Δ Gini, pts/yr | hist -0.7 to -0.5 (med -0.6); model -0.7 to -0.5 | hist -0.4 to 0.1 (med -0.2); model -0.1 to 0.0 | hist -0.2 to 0.3 (med -0.0); model -0.0 to 0.2 |
| Δ poverty $3.00, pts/yr | hist -1.0 to -0.9 (med -0.9); model -1.0 to -0.9 | hist -0.8 to -0.2 (med -0.6); model -0.5 to -0.5 | hist -1.0 to -0.1 (med -0.7); model -0.5 to -0.4 |
| Δ unemployment, pts/yr | hist -0.5 to -0.3 (med -0.4); model -0.7 to -0.3 | hist -0.1 to 1.0 (med 0.5); model 0.2 to 0.6 | hist 0.5 to 1.1 (med 0.9); model 0.6 to 1.1 |
| Real min wage, %/yr | hist 3.1 to 5.1 (med 4.0); model 3.5 to 5.5 | hist -0.8 to 2.0 (med 0.7); model -0.5 to 1.5 | hist -1.0 to 2.7 (med 1.3); model -0.5 to 1.5 |
| Infant mortality, %/yr | hist -5.5 to -2.8 (med -4.3); model -4.4 to -3.9 | hist -6.2 to -1.4 (med -3.8); model -4.0 to -3.5 | hist -6.3 to -3.8 (med -6.2); model -4.8 to -4.6 |
| Gross debt/GDP 2030, % | 84–107 (median-pb, r−g 5.06: 93; Lula III run-rate 104) | 104–112 (median-pb, r−g 5.06: 108; Bolsonaro ex-2020 run-rate 98) | use grid |

Read the market rows with care: the right branch's BRL/equity history is dominated by FHC II (1999 float, 2001 energy crisis, 2002 pre-Lula panic booked to FHC), and the left branch's by Lula I–II's commodity boom; the event study points the other way for the first 60 days after a right win (Ibov USD +19% vs −4% abnormal). The fiscal rows are equally context-bound (Lula I–II surpluses vs COVID 2020). Gini/poverty/unemployment/min-wage rows are where the lean gap is most stable across specifications.

**Market-implied (as of 2026-09-25 Focus / 2026-10-02 curve; a probability-weighted mix of both outcomes, pre-first-round):** GDP 2027 1.41% (`focus_gdp_growth`), IPCA 12m 4.65% (`focus_ipca_12m`), Selic 12m ahead 12.00% (`focus_selic_12m`) ⇒ real ≈ 7.0%; NTN-B 10y real 7.52% (`gov_real_yield_10y`); LTN 5y 14.15% (`gov_nominal_yield_5y`) ⇒ rough real 5y ≈ 9.5%; BRL 5.28 (`focus_fx`). Markets price growth near the **right-branch** history (≈1–2%) and a real rate near the **left-branch** history (≈7–9%) — i.e. they price neither narrative's best case. The marginal funding cost implies r−g ≈ 8.1 pts (LTN 5y minus Focus nominal growth) vs 5.06 on the stock (`r_minus_g`, 2026-08-01).

**Debt arithmetic is the one deterministic piece.** From 82.9% (`gross_public_debt_gdp`, 2026-08-01), stabilising debt needs a primary surplus of ≈3.9% GDP at today's r−g; the current 12m primary is -0.62%. The 4×3 grid spans 81–107% of GDP in 2030. Lean-conditional primary-balance history spans −2.0 to +3.5 — wider than any lean difference, and each side's history is dominated by its context (left median is lifted by Lula I–II's commodity boom; right median is dragged by COVID 2020 — Bolsonaro ex-2020 averaged +0.38%, Lula III -0.93%). With r−g = 5.06: Lula III run-rate ⇒ 104% in 2030; Bolsonaro ex-2020 run-rate ⇒ 98%. Both branches see debt rise unless r−g falls or pb exceeds ~+4%.

**Swing variables (ranked by in-sample explanatory power from Q0):** (1) the commodity/ToT path — Brent at $114 (`brent_usd`, 2026-09-29) helps an oil exporter (pre-salt share and oil exports below), but ToT is near a cycle high; (2) the fiscal–monetary mix: r−g and the credibility of the fiscal rule (2016 spending cap and 2023 framework both moved real yields on announcement); (3) the real-rate path set by an autonomous BCB (2021 law), which history shows does not order by lean; (4) external shocks — the 2025 US tariff (`exports_to_us` vs `exports_to_china`). Lean itself ranks behind (1) for markets and debt, and ahead of it only for distribution and policy instruments.

### Caveats

- Association, not causation: 9 terms, 3 left vs 4 right (coding A); terms are confounded with the commodity super-cycle (Lula I–II), GFC, Lava Jato and the 2015–16 recession (Dilma II/Temer), COVID (Bolsonaro), and the 2026 oil shock (Lula III, incomplete).
- No Congress composition data in the warehouse → coalition effects untested; no peer countries, US rates, dollar index, VIX or world GDP → the only global control is Brazil's own ToT (+Brent from 2000).
- Survey breaks (PNAD 1992, PNAD-C 2012), WB interpolation of forest area, preliminary DATASUS 2024–26, biennial WGI before 2002, and 2026 partial-year values (IBC-Br Jan–Jul, unemployment Jan–Aug) are documented below.
- July-1 attribution books 2002's pre-Lula market panic to FHC and 2016's recovery to Temer; lag-1 and drop-first-year cells exist to test this (see robustness).

## 2. Data constraints (plan §0.1–0.8, verbatim, then executor updates)

**0.1 The 2026 result is unknown to both the warehouse and the planner.** `political_events` contains only `2026-10-04 | General election: first round | election`; `political_terms` ends with Lula III `2023-01-01 → 2027-01-01` with note "general election 4 Oct 2026 (run-off 25 Oct)". The registry CSVs (`/Users/zkid18/proj-personal/brazil-macro/registry/political_events.csv`, `political_terms.csv`) and git log carry nothing newer. My training knowledge ends before the vote. Executor step 1: re-query `political_events WHERE date >= '2026-10-04'` and `git -C /Users/zkid18/proj-personal/brazil-macro log -3 -- registry/`; if still nothing, all scenarios are **conditional on outcome** (left / right / centre), and the report must say the result was not assumed.

**0.2 `v_by_term` is unusable as-is for this study.** It groups by `president`, and Lula I–II and Lula III share the string `Luiz Inácio Lula da Silva`, so they collapse into one "term" (e.g. GDP growth n=11, 2003→2025). Also `v_politics` joins on the raw observation date: annual WB values are dated `YYYY-12-31`, so 1992 goes to Itamar (Collor resigned 29 Dec) and 2016 goes to Temer. The executor must build its own term key (`term_id = row_number() OVER (ORDER BY start)`, label `president || ' ' || year(start)`) and explicit year-attribution rules (section 3.2). Never use `v_by_term` for results.

**0.3 Term table (`political_terms`, DATE columns start/end, half-open `[start, end)`):**

| id | start | end | president | party | lean (as coded) |
|---|---|---|---|---|---|
| 1 | 1985-03-15 | 1990-03-15 | Sarney | PMDB | centre |
| 2 | 1990-03-15 | 1992-12-29 | Collor | PRN | right |
| 3 | 1992-12-29 | 1995-01-01 | Itamar Franco | no party/PMDB | centre |
| 4 | 1995-01-01 | 2003-01-01 | FHC | PSDB | centre-right |
| 5 | 2003-01-01 | 2011-01-01 | Lula I–II | PT | left |
| 6 | 2011-01-01 | 2016-05-12 | Dilma | PT | left |
| 7 | 2016-05-12 | 2019-01-01 | Temer | MDB | centre-right |
| 8 | 2019-01-01 | 2023-01-01 | Bolsonaro | PSL/PL | right |
| 9 | 2023-01-01 | 2027-01-01 | Lula III | PT | left (incomplete: data to 2026-10) |

Four lean labels exist (left / centre / centre-right / right), not three. **No Congress composition table exists** anywhere in the warehouse; coalition effects cannot be tested (say so; recommend a registry CSV as future work). `political_events` has 34 dated events (elections 1989/94/98/2002/06/10/14/18/22/26, impeachment votes 1992-09-29, 2016-04-17, 2016-08-31, Temer sworn in, spending cap 2016-12-15, BCB autonomy 2021-02-24, fiscal framework 2023-08-31, US tariff 2025-08-06) — use these as the event list.

**0.4 Current starting conditions are in the warehouse and differ from the brief.** The brief says Selic 14.5%; the warehouse says Selic was cut to **13.75% on 2026-09-17** (`selic_target`, last 2026-10-03; 15.00 at end-2025, 14.50 in Apr–May 2026). Use warehouse values, with series_id and date:

| Series | Value | Date |
|---|---|---|
| `selic_target` | 13.75 | 2026-10-03 |
| `real_policy_rate` (Selic − Focus IPCA 12m) | 9.27 | 2026-09-01 |
| `ipca_12m` | 4.22 | 2026-08-01 |
| `focus_ipca_12m` / `focus_selic_12m` / `focus_gdp_growth` / `focus_fx` | 4.65 / 12.00 / 1.41 / 5.28 | 2026-09-25 |
| `gov_real_yield_10y` (NTN-B) / `gov_nominal_yield_5y` (LTN) | 7.52 / 14.15 | 2026-10-02 |
| `brl_usd` | 5.2238 | 2026-10-02 |
| `ibovespa_usd` / `ibovespa_level` | 35,945 / 187,198 | 2026-10-01 |
| `gross_public_debt_gdp` / `net_public_debt_gdp` | 82.86 / 60.79 | 2026-08-01 |
| `primary_balance_gdp` / `nominal_deficit_gdp` / `interest_bill_gdp` / `r_minus_g` | −0.62 / 9.48 / 8.86 / 5.06 | 2026-08-01 |
| `unemployment_rate` | 5.3 | 2026-08-01 |
| `fx_reserves` | 362,616 US$ mn | 2026-10-01 |
| `brent_usd` | 113.96 (126.69 in Mar 2026 — a 2026 oil shock is in the data) | 2026-09-29 |
| `credit_gdp` | 55.44 | 2026-08-01 |

**0.5 Campaign-window tape exists through 2026-10-02.** Prototype (t = first trading day after 2026-10-04 is not yet in the DB; t−1 = 2026-10-01/02): from t−60 trading days (~2026-07-07) to t−1: `ibovespa_usd` 33,654 → 35,945 (+6.8%); `brl_usd` 5.11 → 5.22 (BRL −2.2%); `gov_real_yield_10y` 7.83 → 7.52 (−31 bp). YTD (end-2025 → Oct 1): Ibov USD +22.7%, BRL +5.3%, 10y real +18 bp, LTN 5y 13.60 → 14.15, Focus GDP-next-year 1.80 → 1.41, Focus IPCA 12m 4.02 → 4.65. Confounds inside the window: Selic cuts (Sep 17), Brent 61 → 114, US tariff (Aug 2025). `embi_brazil` ends **2024-07-30** and cannot be used for Lula III after mid-2024 or for 2026.

**0.6 Event-study coverage.** Daily `ibovespa_usd`, `ibovespa_level`, `brl_usd`, `embi_brazil`, `selic_target`, `focus_*`, `fx_reserves` all start 2000-01 → cover 2002, 2006, 2010, 2014, 2016, 2018, 2022 (±90 calendar days ≈ 125 obs each). `gov_real_yield_10y`/`gov_nominal_yield_5y` start 2015-01-02 → cover 2016, 2018, 2022, 2026 only. 1994 and 1998 have only monthly `wb/DSTKMKTXD_M.BRA` and `wb/DPANUSSPB_M.BRA` (6 obs per window) → descriptive only. **Guard every window:** use a series only if `first_date <= t − window` and `last_date >= t + window`; my prototype without this guard silently returned 2015 values for 2002 and 2024 values for 2026.

**0.7 Global-cycle controls available (and not).** In-warehouse: `wb/TOT.BRA` (monthly terms of trade 1991-01→2025-12) ≡ `wb/TT.PRI.MRCH.XD.WD.BR` (annual 2005→2024; ρ = 0.99996) ≈ `wb/TX.UVI.MRCH.XD.WD.BR / wb/TM.UVI.MRCH.XD.WD.BR` (annual 1980→2024; ρ = 0.993 vs TOT 1991–2024) — so the UVI ratio extends ToT to 1985 for Sarney/Collor. `brent_usd` daily 2000→2026-09-29. Export price index monthly `wb/DXGSRMRCHNSXD_M.BRA` 1991→2025. **Not in warehouse:** any US rate, dollar index, VIX, world GDP, global commodity index, peer countries. The "global cycle" control is therefore Brazil's own ToT (+ Brent post-2000). State this limit; an optional external-data appendix must be fenced and must not drive any verdict.

**0.8 Series pitfalls found (hard-code as checks):**
- `ilostat/EAR_EMTG_SEX_NB.BRA` (earnings Gini) carries `-1.00` placeholders in 1995–1999 → filter `value > 0`.
- `wb/AG.LND.FRST.K2.BR` is FAO linear interpolation between 1990/2000/2010/2015/2020 (constant −37,809 km²/yr through the 1990s) → cannot attribute to terms; use `wb/AG.LND.PFLS.HA.BR` (primary forest loss, 2002→2025, GFW; fire spikes 2016, 2024) and `wb/EN.GHG.CO2.LU.MT.CE.AR5.BR` (2000→2023; 2023 = 2022 carry-forward → drop 2023).
- Unemployment: `ilostat/UNE_DEAP_SEX_AGE_RT.BRA` (1981→2025) has survey breaks (3–5% in the 1980s, 7–11% 1992–2001, PNAD-C from 2012); `wb/UNEMPSA__M.BRA` (note double underscore; 2001-10→2025-12) jumps from the PME metro rate (~15%) to PNAD-C (~7%) in 2012. Use `wb/SL.UEM.TOTL.ZS.BR` (ILO modelled, 1991→2025; role alternate but reconciles with native at ρ = 0.998) for the long annual series and native `unemployment_rate` (2012-03→2026-08) for the recent terms. Exclude unemployment before 1991.
- Informality: `wb/JI.EMP.IFRM.ZS.BRA` (share 0–1, 1981→2020, gaps) and `ilostat/SDG_0831_SEX_ECO_RT.BRA` (%, 2009→2025) are different definitions (0.34–0.54 vs 36–47) → only within-series changes, never pooled levels.
- Nominal series are meaningless in 1985–1994 (hyperinflation): use `log(1 + π/100)` for inflation, REER (`wb/REER_M.BRA` 1987→2024-10; `wb/PX.REX.REER.BR` annual 1980→2025) instead of nominal BRL, and no nominal rate metrics before 1995.
- WGI is biennial 1996–2002 then annual. GFDD ends 2021, Doing Business 2019, PISA 2015 → descriptive only, not term-tested.
- `wb/CM.MKT.INDX.ZG.BR` (S&P index) diverges from Ibovespa in 2022 (−4.4 vs +12.3) → do not use. USD equity long series = `wb/DSTKMKTXD_M.BRA` (1994–1999, ρ = 0.995 with `ibovespa_usd` on annual returns) chained to `ibovespa_usd` (2000→2026-10-01), year-end via `arg_max(value, date)`.
- `v_annual` agg: `ibovespa_usd`, `brl_usd`, `brent_usd`, `selic_target` are `mean` → for returns/changes compute year-end values yourself. Monthly native dates are first-of-month, GEM monthly are month-end, WB/ILO annual are Dec 31 → join on `date_trunc('month', date)` / year. Filter `date <= current_date`. WB 2025 values preliminary.
- Python env: duckdb, pandas, numpy, plotly only (confirmed `/Users/zkid18/proj-personal/brazil-macro/.venv`). Numpy helpers to copy: `_ols_r2`, `_m_last`, `_q_mean`, `_trend_pct_per_year` in `/Users/zkid18/proj-personal/brazil-macro/hypotheses.py:60-95`.

**Executor updates (2026-10-05):** 0.1 re-checked — `political_events` still has no 2026 result and `git log -- registry/` shows nothing newer (latest b79840b). The first-round result is supplied externally (section 0) and is used only to order the scenario branches. All §0.9 anchors reproduced exactly (Ibovespa USD 2026 YTD +22.8% vs +22.7% — rounding). ToT splice: UVI ratio rescaled to TT.PRI (k = 100.001, ρ = 0.99998 over 20 overlapping years); 2025 extended with `wb/TOT.BRA`. 2026 GDP = IBC-Br Jan–Jul 2026 vs Jan–Jul 2025; 2026 unemployment = native `unemployment_rate` Jan–Aug mean, level-matched to the WB ILO-modelled 2025 value. Interpolated gaps: Gini, poverty, income shares, WGI 1997/1999/2001, education spending, informality.

## 3. Term table and lean coding

| term_id | short | start | end | party | lean | years attributed (1 Jul rule) | coding A | coding B | coding C | coding D | mean ΔlogToT /yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Sarney | 1985-03-15 | 1990-03-15 | PMDB | centre | 1985–1989 | centre | centre | centre | centre | +3.6 |
| 2 | Collor | 1990-03-15 | 1992-12-29 | PRN | right | 1990–1992 | right | right | right | dropped | +3.3 |
| 3 | Itamar | 1992-12-29 | 1995-01-01 | no party / PMDB | centre | 1993–1994 | centre | centre | centre | dropped | +10.5 |
| 4 | FHC | 1995-01-01 | 2003-01-01 | PSDB | centre-right | 1995–2002 | right | centre | right | right | -0.3 |
| 5 | Lula I–II | 2003-01-01 | 2011-01-01 | PT | left | 2003–2010 | left | left | left | left | +3.2 |
| 6 | Dilma | 2011-01-01 | 2016-05-12 | PT | left | 2011–2015 | left | left | left | left | -3.4 |
| 7 | Temer | 2016-05-12 | 2019-01-01 | MDB | centre-right | 2016–2018 | right | centre | centre | dropped | +2.2 |
| 8 | Bolsonaro | 2019-01-01 | 2023-01-01 | PSL / PL | right | 2019–2022 | right | right | right | right | +1.7 |
| 9 | Lula III | 2023-01-01 | 2027-01-01 | PT | left | 2023–2026 | left | left | left | dropped | +1.2 |

Coding E = coding A with Dilma II's 2015–16 years dropped. Mandate unit splits FHC (1999), Lula (2007), Dilma (2015). Lula III is incomplete (data to 2026-08/10).

Term-attribution SQL (prepended to every term query; 1 July majority rule for annual data):
```sql
SELECT row_number() OVER (ORDER BY start) AS term_id,
       president || ' ' || strftime(start, '%Y') AS term_label,
       start, "end", president, party, lean,
       CASE lean WHEN 'left' THEN 'left' WHEN 'centre' THEN 'centre' ELSE 'right' END AS lean3
FROM political_terms ORDER BY start
```

## 4. Pre-registered hypotheses

See `preregistration.md` (timestamped before any result). Families: (1) four composites, Holm at α = 0.10; (2) 23 primary metrics, BH at q = 0.10 (the plan said '~26'; the verified primary list has 23 metrics — composites are tested separately in family 1); (3) secondary metrics, descriptive. Support for a narrative requires: baseline sign matches AND ≥ 80% of robustness cells share it AND the 80% cluster-bootstrap CI excludes zero.

| id | metric | left_expects | right_expects |
|---|---|---|---|
| A1 | Real GDP growth | higher | lower |
| A2 | GDP per capita growth | higher | lower |
| A3 | Investment (GFCF) % GDP | higher | lower |
| B1 | Inflation (GDP deflator, log) | no difference | higher |
| B2 | Real policy rate (ex-ante) | lower | higher |
| C1 | Primary balance % GDP | similar | lower |
| C2 | Δ Gross debt % GDP | similar | higher |
| C4 | Interest bill % GDP | similar | higher |
| D1 | USD equity return (log) | no difference | lower |
| D2 | BRL appreciation vs USD (log) | no difference | weaker |
| D3 | Real effective exchange rate | no difference | weaker |
| D6 | Current account % GDP | no difference | lower |
| D7 | FDI inflows % GDP | no difference | lower |
| E1 | Unemployment rate | lower | higher |
| E3 | Real minimum wage growth | higher | higher (at employment cost) |
| E5 | Δ Gini | falls more | ≈0 after ToT |
| E6 | Δ Poverty $3.00/day | falls more | ≈0 after ToT |
| F1 | Infant mortality change (log) | falls faster | no difference |
| F5 | Δ Homicide rate | falls more | no difference |
| GCC | Δ WGI Control of Corruption | no difference | worse |
| GGE | Δ WGI Government Effectiveness | no difference | no difference |
| GRL | Δ WGI Rule of Law | no difference | no difference |
| H1 | Primary forest loss | lower | no difference / higher |

## 5. Results

### 5.1 Q0 — variance decomposition (Shapley R²; term level: term mean on left dummy vs term-mean ΔlogToT; year level: lean dummies vs [ΔlogToT, logToT])

| metric_id | name | level | n | r2_lean | r2_tot | r2_both | shap_lean | shap_tot | tot_ge_lean |
|---|---|---|---|---|---|---|---|---|---|
| A1 | Real GDP growth | term | 9 | 0.02 | 0.25 | 0.4 | 0.09 | 0.31 | True |
| A1 | Real GDP growth | year | 41 | 0.2 | 0.13 | 0.31 | 0.19 | 0.12 | False |
| A2 | GDP per capita growth | term | 9 | 0.09 | 0.15 | 0.41 | 0.18 | 0.23 | True |
| A2 | GDP per capita growth | year | 41 | 0.17 | 0.13 | 0.31 | 0.17 | 0.14 | False |
| A3 | Investment (GFCF) % GDP | term | 9 | 0.01 | 0.03 | 0.03 | 0.0 | 0.03 | True |
| A3 | Investment (GFCF) % GDP | year | 41 | 0.36 | 0.15 | 0.37 | 0.29 | 0.08 | False |
| B1 | Inflation (GDP deflator, log) | term | 9 | 0.23 | 0.59 | 0.62 | 0.13 | 0.49 | True |
| B1 | Inflation (GDP deflator, log) | year | 41 | 0.47 | 0.5 | 0.56 | 0.27 | 0.3 | True |
| B2 | Real policy rate (ex-ante) | term | 5 | 0.47 | 0.13 | 0.88 | 0.61 | 0.27 | False |
| B2 | Real policy rate (ex-ante) | year | 24 | 0.13 | 0.42 | 0.56 | 0.13 | 0.42 | True |
| C1 | Primary balance % GDP | term | 5 | 0.55 | 0.0 | 0.6 | 0.57 | 0.03 | False |
| C1 | Primary balance % GDP | year | 23 | 0.32 | 0.09 | 0.41 | 0.32 | 0.09 | False |
| C2 | Δ Gross debt % GDP | term | 5 | 0.0 | 0.32 | 0.33 | 0.0 | 0.32 | True |
| C2 | Δ Gross debt % GDP | year | 19 | 0.0 | 0.38 | 0.38 | 0.0 | 0.38 | True |
| C4 | Interest bill % GDP | term | 5 | 0.34 | 0.03 | 0.51 | 0.41 | 0.1 | False |
| C4 | Interest bill % GDP | year | 23 | 0.12 | 0.17 | 0.26 | 0.1 | 0.16 | True |
| D1 | USD equity return (log) | term | 6 | 0.0 | 0.86 | 0.9 | 0.02 | 0.88 | True |
| D1 | USD equity return (log) | year | 31 | 0.01 | 0.06 | 0.08 | 0.02 | 0.06 | True |
| D2 | BRL appreciation vs USD (log) | term | 6 | 0.07 | 0.73 | 0.93 | 0.14 | 0.8 | True |
| D2 | BRL appreciation vs USD (log) | year | 31 | 0.09 | 0.08 | 0.18 | 0.09 | 0.09 | False |
| D3 | Real effective exchange rate | term | 9 | 0.03 | 0.03 | 0.05 | 0.02 | 0.02 | True |
| D3 | Real effective exchange rate | year | 41 | 0.0 | 0.01 | 0.02 | 0.01 | 0.01 | True |
| D6 | Current account % GDP | term | 9 | 0.08 | 0.62 | 0.62 | 0.04 | 0.58 | True |
| D6 | Current account % GDP | year | 41 | 0.17 | 0.36 | 0.45 | 0.13 | 0.32 | True |
| D7 | FDI inflows % GDP | term | 9 | 0.17 | 0.49 | 0.5 | 0.09 | 0.41 | True |
| D7 | FDI inflows % GDP | year | 41 | 0.4 | 0.61 | 0.64 | 0.21 | 0.42 | True |
| E1 | Unemployment rate | term | 8 | 0.1 | 0.14 | 0.46 | 0.21 | 0.25 | True |
| E1 | Unemployment rate | year | 35 | 0.31 | 0.02 | 0.32 | 0.31 | 0.02 | False |
| E3 | Real minimum wage growth | term | 6 | 0.69 | 0.12 | 0.86 | 0.71 | 0.15 | False |
| E3 | Real minimum wage growth | year | 30 | 0.15 | 0.04 | 0.21 | 0.16 | 0.05 | False |
| E5 | Δ Gini | term | 9 | 0.04 | 0.26 | 0.26 | 0.02 | 0.24 | True |
| E5 | Δ Gini | year | 40 | 0.19 | 0.03 | 0.36 | 0.26 | 0.1 | False |
| E6 | Δ Poverty $3.00/day | term | 9 | 0.0 | 0.24 | 0.29 | 0.02 | 0.26 | True |
| E6 | Δ Poverty $3.00/day | year | 40 | 0.05 | 0.09 | 0.12 | 0.04 | 0.08 | True |
| F1 | Infant mortality change (log) | term | 9 | 0.01 | 0.06 | 0.06 | 0.0 | 0.06 | True |
| F1 | Infant mortality change (log) | year | 40 | 0.0 | 0.03 | 0.07 | 0.02 | 0.05 | True |
| F5 | Δ Homicide rate | term | 6 | 0.0 | 0.28 | 0.29 | 0.0 | 0.29 | True |
| F5 | Δ Homicide rate | year | 25 | 0.02 | 0.01 | 0.03 | 0.02 | 0.01 | False |
| GCC | Δ WGI Control of Corruption | term | 6 | 0.02 | 0.44 | 0.47 | 0.02 | 0.44 | True |
| GCC | Δ WGI Control of Corruption | year | 28 | 0.01 | 0.11 | 0.13 | 0.01 | 0.12 | True |
| GGE | Δ WGI Government Effectiveness | term | 6 | 0.3 | 0.14 | 0.43 | 0.3 | 0.13 | False |
| GGE | Δ WGI Government Effectiveness | year | 28 | 0.0 | 0.02 | 0.02 | 0.0 | 0.02 | True |
| GRL | Δ WGI Rule of Law | term | 6 | 0.09 | 0.08 | 0.17 | 0.09 | 0.08 | False |
| GRL | Δ WGI Rule of Law | year | 28 | 0.02 | 0.13 | 0.15 | 0.02 | 0.13 | True |
| H1 | Primary forest loss | term | 5 | 0.31 | 0.47 | 0.58 | 0.21 | 0.37 | True |
| H1 | Primary forest loss | year | 24 | 0.16 | 0.08 | 0.23 | 0.16 | 0.07 | False |

### 5.2 Family 1 — composites (Holm across 4)

| composite | adjustment | n L/R | Δ (z) | 80% CI | 95% CI | perm p | floor | Holm p |
|---|---|---|---|---|---|---|---|---|
| COMP-G Growth | raw | 3/4 | +0.72 | [+0.30, +1.15] | [+0.10, +1.32] | 0.143 | 0.029 | 0.429 |
| COMP-G Growth | tot | 3/4 | +1.09 | [+0.57, +1.58] | [+0.31, +1.79] | 0.114 | 0.029 | 0.343 |
| COMP-S Orthodox stability | raw | 3/4 | +0.16 | [-0.20, +0.51] | [-0.38, +0.69] | 0.543 | 0.029 | 1.000 |
| COMP-S Orthodox stability | tot | 3/4 | +0.31 | [-0.11, +0.75] | [-0.31, +0.99] | 0.429 | 0.029 | 0.857 |
| COMP-D Distribution | raw | 3/4 | +0.92 | [+0.75, +1.10] | [+0.69, +1.20] | 0.029 | 0.029 | 0.114 |
| COMP-D Distribution | tot | 3/4 | +1.00 | [+0.84, +1.17] | [+0.80, +1.29] | 0.029 | 0.029 | 0.114 |
| COMP-M Markets | raw | 3/3 | +0.25 | [-0.48, +1.05] | [-0.81, +1.31] | 0.700 | 0.100 | 1.000 |
| COMP-M Markets | tot | 3/3 | +0.53 | [-0.31, +1.36] | [-0.61, +1.66] | 0.600 | 0.100 | 0.857 |

Composite values by term (z-mean, raw):

| composite | Sarney | Collor | Itamar | FHC | Lula I–II | Dilma | Temer | Bolsonaro | Lula III |
|---|---|---|---|---|---|---|---|---|---|
| COMP-G Growth | 1.12 | -1.12 | 1.30 | 0.05 | 0.53 | -0.34 | -1.08 | -0.46 | -0.01 |
| COMP-S Orthodox stability | -0.07 | 0.53 | -0.17 | -0.43 | 0.57 | 0.08 | -0.29 | 0.00 | -0.30 |
| COMP-D Distribution | 0.35 | -0.22 | 0.05 | -0.24 | 0.59 | 0.37 | -0.84 | -0.45 | 0.50 |
| COMP-M Markets | – | – | – | -1.17 | 0.94 | -0.63 | 0.44 | 0.24 | -0.04 |

### 5.3 Family 2 — primary metrics, by bucket (BH q across 23)

#### A Growth

| id | metric | unit | n L/R | mean L | mean R | Δ L−R | 80% CI | perm p (floor) | BH q | sign-cons. | ToT-adj Δ | ToT-adj 80% CI | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Real GDP growth | % y/y | 3/4 | 2.59 | 0.63 | +1.96 | [+0.18, +3.78] | 0.17 (0.029) | 0.86 | 98% | +2.34 | [+0.77, +3.99] | robust-by-CI Δ+ (perm p 0.17, floor 0.03); sign matches left narrative; contradicts right narrative's expectation |
| A2 | GDP per capita growth | % y/y | 3/4 | 1.99 | -0.46 | +2.45 | [+0.63, +4.27] | 0.17 (0.029) | 0.86 | 97% | +2.35 | [+0.77, +3.89] | robust-by-CI Δ+ (perm p 0.17, floor 0.03); sign matches left narrative; contradicts right narrative's expectation |
| A3 | Investment (GFCF) % GDP | % GDP | 3/4 | 18.30 | 17.40 | +0.90 | [-0.56, +2.46] | 0.51 (0.029) | 0.99 | 98% | +1.62 | [+0.21, +3.03] | no robust association |

Secondary (descriptive):

| id | metric | unit | n L/R | Δ L−R | 80% CI | perm p (floor) | ToT-adj Δ |
|---|---|---|---|---|---|---|---|
| A4 | Industrial production growth | % y/y (log) | 3/3 | +0.61 | [-2.22, +3.41] | 0.90 (0.100) | +1.20 |
| A5 | Output per worker growth | % y/y | 3/3 | +1.25 | [-0.09, +2.54] | 0.10 (0.100) | +1.31 |

#### B Prices & rates

| id | metric | unit | n L/R | mean L | mean R | Δ L−R | 80% CI | perm p (floor) | BH q | sign-cons. | ToT-adj Δ | ToT-adj 80% CI | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | Inflation (GDP deflator, log) | 100·log(1+π) | 3/4 | 6.81 | 68.49 | -61.68 | [-135.65, -0.70] | 0.57 (0.029) | 0.99 | 59% | -7.48 | [-49.57, +29.60] | no robust association |
| B2 | Real policy rate (ex-ante) | % p.a. | 3/2 | 7.84 | 3.95 | +3.89 | [+1.14, +6.72] | 0.30 (0.100) | 0.86 | 88% | +4.18 | [+1.82, +6.57] | robust-by-CI Δ+ (perm p 0.30, floor 0.10); sign matches right narrative; contradicts left narrative's expectation |

Secondary (descriptive):

| id | metric | unit | n L/R | Δ L−R | 80% CI | perm p (floor) | ToT-adj Δ |
|---|---|---|---|---|---|---|---|
| B1b | IPCA 12m (Dec) | % | 3/3 | -0.63 | [-2.75, +1.30] | 0.70 (0.100) | -0.20 |
| B3 | Focus IPCA 12m expectation | % | 3/2 | +0.63 | [-0.12, +1.36] | 0.40 (0.100) | +0.61 |
| B4 | Real lending rate (WB) | % | 3/3 | -6.51 | [-18.48, +5.22] | 0.80 (0.100) | -2.68 |
| B5 | Δ Private credit % GDP | pts/yr | 3/4 | +7.16 | [-3.32, +21.97] | 0.11 (0.029) | +7.44 |

#### C Fiscal

| id | metric | unit | n L/R | mean L | mean R | Δ L−R | 80% CI | perm p (floor) | BH q | sign-cons. | ToT-adj Δ | ToT-adj 80% CI | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | Primary balance % GDP | % GDP (Dec, 12m) | 3/2 | 1.02 | -1.97 | +2.99 | [+0.98, +5.06] | 0.20 (0.100) | 0.86 | 100% | +3.25 | [+1.30, +5.07] | robust-by-CI Δ+ (perm p 0.20, floor 0.10); contradicts left & right narrative's expectation |
| C2 | Δ Gross debt % GDP | pts/yr | 3/2 | 1.54 | 1.18 | +0.36 | [-3.43, +4.63] | 1.00 (0.100) | 1.00 | 46% | +0.73 | [-2.62, +4.36] | no robust association |
| C4 | Interest bill % GDP | % GDP | 3/2 | 6.60 | 5.48 | +1.12 | [+0.09, +2.12] | 0.40 (0.100) | 0.92 | 93% | +1.03 | [+0.10, +1.98] | robust-by-CI Δ+ (perm p 0.40, floor 0.10); sign matches right narrative; contradicts left narrative's expectation |

Secondary (descriptive):

| id | metric | unit | n L/R | Δ L−R | 80% CI | perm p (floor) | ToT-adj Δ |
|---|---|---|---|---|---|---|---|
| C3 | Δ Net debt % GDP | pts/yr | 3/2 | -3.48 | [-6.98, -0.09] | 0.30 (0.100) | -3.84 |
| C5 | Government consumption % GDP | % GDP | 3/4 | -0.32 | [-0.88, +0.30] | 0.57 (0.029) | -1.67 |
| C6 | Tax revenue % GDP | % GDP | 2/2 | +0.61 | [+0.07, +1.24] | 0.33 (0.333) | +0.09 |

#### D Markets & external

| id | metric | unit | n L/R | mean L | mean R | Δ L−R | 80% CI | perm p (floor) | BH q | sign-cons. | ToT-adj Δ | ToT-adj 80% CI | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | USD equity return (log) | % /yr (log) | 3/3 | 6.34 | 4.95 | +1.38 | [-25.74, +28.73] | 1.00 (0.100) | 1.00 | 82% | +5.90 | [-19.55, +32.85] | no robust association |
| D2 | BRL appreciation vs USD (log) | % /yr (+ = stronger BRL) | 3/3 | -2.56 | -8.35 | +5.80 | [-7.27, +18.54] | 0.60 (0.100) | 0.99 | 100% | +6.87 | [-5.18, +19.01] | no robust association |
| D3 | Real effective exchange rate | index 2010=100 (+ = stronger) | 3/4 | 76.02 | 80.03 | -4.01 | [-18.06, +9.80] | 0.77 (0.029) | 1.00 | 10% | -2.98 | [-16.37, +10.55] | no robust association |
| D6 | Current account % GDP | % GDP | 3/4 | -2.17 | -1.89 | -0.28 | [-1.66, +1.13] | 0.80 (0.029) | 1.00 | 21% | +0.57 | [-0.44, +1.57] | no robust association |
| D7 | FDI inflows % GDP | % GDP | 3/4 | 3.10 | 2.64 | +0.46 | [-0.47, +1.47] | 0.83 (0.029) | 1.00 | 16% | -0.41 | [-0.85, +0.04] | no robust association |

Secondary (descriptive):

| id | metric | unit | n L/R | Δ L−R | 80% CI | perm p (floor) | ToT-adj Δ |
|---|---|---|---|---|---|---|---|
| D4 | EMBI spread | bp | 2/3 | -227.62 | [-518.66, +23.38] | 0.80 (0.100) | -158.18 |
| D5 | 10y real yield (NTN-B) | % p.a. | 1/2 | – | – | – | – |
| D8 | Δ Reserves (months of imports) | months/yr | 3/4 | +0.64 | [-0.70, +1.90] | 0.46 (0.029) | +0.77 |
| D9 | Δ Exports % GDP | pts/yr | 3/4 | -0.97 | [-1.75, -0.24] | 0.03 (0.029) | -1.24 |
| D10 | Δ Market cap % GDP | pts/yr | 3/3 | -1.34 | [-10.54, +8.22] | 0.80 (0.100) | +2.53 |

#### E Labour & distribution

| id | metric | unit | n L/R | mean L | mean R | Δ L−R | 80% CI | perm p (floor) | BH q | sign-cons. | ToT-adj Δ | ToT-adj 80% CI | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | Unemployment rate | % | 3/4 | 7.88 | 10.23 | -2.36 | [-4.11, -0.55] | 0.17 (0.029) | 0.86 | 100% | -2.44 | [-4.10, -0.73] | robust-by-CI Δ− (perm p 0.17, floor 0.03); sign matches left narrative; contradicts right narrative's expectation |
| E3 | Real minimum wage growth | % /yr (log) | 3/3 | 3.65 | 0.59 | +3.06 | [+0.97, +5.14] | 0.10 (0.100) | 0.86 | 99% | +3.38 | [+1.44, +5.44] | robust-by-CI Δ+ (perm p 0.10, floor 0.10); sign matches left & right narrative |
| E5 | Δ Gini | pts/yr | 3/4 | -0.56 | -0.85 | +0.29 | [-0.88, +1.51] | 0.97 (0.029) | 1.00 | 25% | +0.31 | [-0.89, +1.57] | no robust association |
| E6 | Δ Poverty $3.00/day | pts/yr | 3/4 | -0.83 | 0.07 | -0.89 | [-1.99, +0.14] | 0.29 (0.029) | 0.86 | 92% | -1.15 | [-2.35, +0.02] | no robust association |

Secondary (descriptive):

| id | metric | unit | n L/R | Δ L−R | 80% CI | perm p (floor) | ToT-adj Δ |
|---|---|---|---|---|---|---|---|
| E1c | Δ Unemployment rate | pts/yr | 3/3 | -0.72 | [-1.67, +0.29] | 0.40 (0.100) | -0.67 |
| E2 | Δ Informality (within-series) | pts/yr | 3/4 | -1.70 | [-2.42, -0.99] | 0.06 (0.029) | -1.45 |
| E4 | Real average labour income growth | % /yr (log) | 2/2 | +2.82 | [+0.29, +5.32] | 0.33 (0.333) | +1.85 |
| E5L | Gini (level) | index | 3/4 | -2.32 | [-4.97, +0.32] | 0.34 (0.029) | -0.77 |
| E6b | Δ Poverty $8.30/day | pts/yr | 3/4 | -2.09 | [-3.85, -0.23] | 0.11 (0.029) | -2.10 |
| E7a | Δ Income share bottom 20% | pts/yr | 3/4 | +0.03 | [-0.17, +0.24] | 0.71 (0.029) | +0.01 |
| E7b | Δ Income share top 10% | pts/yr | 3/4 | +0.49 | [-0.66, +1.71] | 0.94 (0.029) | +0.46 |
| E8 | Δ Labour income share | pts/yr | 3/2 | +0.68 | [+0.05, +1.33] | 0.20 (0.100) | +0.59 |
| E9 | Δ Earnings Gini | pts/yr | 3/4 | +0.00 | [-0.01, +0.02] | 0.94 (0.029) | -0.00 |

#### F Health, education, safety

| id | metric | unit | n L/R | mean L | mean R | Δ L−R | 80% CI | perm p (floor) | BH q | sign-cons. | ToT-adj Δ | ToT-adj 80% CI | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | Infant mortality change (log) | % /yr (− = improving) | 3/4 | -3.39 | -3.28 | -0.12 | [-2.63, +2.30] | 0.97 (0.029) | 1.00 | 72% | -0.47 | [-2.86, +1.78] | no robust association |
| F5 | Δ Homicide rate | per 100k /yr | 3/3 | -0.43 | -0.42 | -0.02 | [-1.41, +1.51] | 1.00 (0.100) | 1.00 | 32% | +0.12 | [-1.22, +1.57] | no robust association |

Secondary (descriptive):

| id | metric | unit | n L/R | Δ L−R | 80% CI | perm p (floor) | ToT-adj Δ |
|---|---|---|---|---|---|---|---|
| F2 | Life expectancy gain | years/yr | 3/4 | +0.24 | [-0.05, +0.61] | 0.26 (0.029) | +0.28 |
| F3 | Govt health spend % GDP | % GDP | 2/3 | -0.33 | [-0.54, -0.13] | 0.30 (0.100) | -0.38 |
| F4 | Education spend % GDP | % GDP | 2/3 | -0.03 | [-0.83, +0.80] | 1.00 (0.100) | -0.16 |
| F6 | Social safety-net coverage | % pop | 2/2 | -6.66 | [-13.87, -0.79] | 0.33 (0.333) | -6.31 |

#### G Institutions (WGI)

| id | metric | unit | n L/R | mean L | mean R | Δ L−R | 80% CI | perm p (floor) | BH q | sign-cons. | ToT-adj Δ | ToT-adj 80% CI | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GCC | Δ WGI Control of Corruption | est. units/yr | 3/3 | -0.02 | -0.01 | -0.01 | [-0.07, +0.05] | 0.80 (0.100) | 1.00 | 92% | -0.01 | [-0.07, +0.04] | no robust association |
| GGE | Δ WGI Government Effectiveness | est. units/yr | 3/3 | -0.00 | -0.02 | +0.02 | [-0.04, +0.08] | 0.30 (0.100) | 0.86 | 88% | +0.01 | [-0.04, +0.07] | no robust association |
| GRL | Δ WGI Rule of Law | est. units/yr | 3/3 | -0.00 | -0.02 | +0.02 | [-0.03, +0.07] | 0.60 (0.100) | 0.99 | 93% | +0.02 | [-0.02, +0.07] | no robust association |

Secondary (descriptive):

| id | metric | unit | n L/R | Δ L−R | 80% CI | perm p (floor) | ToT-adj Δ |
|---|---|---|---|---|---|---|---|
| GRQ | Δ WGI Regulatory Quality | est. units/yr | 3/3 | -0.03 | [-0.08, +0.02] | 0.50 (0.100) | -0.02 |
| GVA | Δ WGI Voice & Accountability | est. units/yr | 3/3 | +0.07 | [+0.00, +0.15] | 0.30 (0.100) | +0.08 |
| GPV | Δ WGI Political Stability | est. units/yr | 3/3 | -0.08 | [-0.17, -0.00] | 0.10 (0.100) | -0.09 |

#### H Environment

| id | metric | unit | n L/R | mean L | mean R | Δ L−R | 80% CI | perm p (floor) | BH q | sign-cons. | ToT-adj Δ | ToT-adj 80% CI | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | Primary forest loss | Mha/yr | 3/2 | 1.36 | 1.85 | -0.49 | [-1.00, +0.01] | 0.40 (0.100) | 0.92 | 90% | -0.43 | [-0.90, +0.06] | no robust association |

Secondary (descriptive):

| id | metric | unit | n L/R | Δ L−R | 80% CI | perm p (floor) | ToT-adj Δ |
|---|---|---|---|---|---|---|---|
| H2 | LULUCF CO2 | Mt | 2/3 | +20.04 | [-500.75, +570.98] | 0.90 (0.100) | +211.49 |
| H3 | Δ CO2 per capita ex-LULUCF | t/yr | 3/4 | +0.05 | [-0.01, +0.12] | 0.17 (0.029) | +0.05 |

### 5.4 Term values (term mean of annual values) for the primary metrics

| metric | Sarney | Collor | Itamar | FHC | Lula I–II | Dilma | Temer | Bolsonaro | Lula III |
|---|---|---|---|---|---|---|---|---|---|
| A1 Real GDP growth (% y/y) | 4.39 | -1.29 | 5.39 | 2.43 | 4.08 | 1.17 | -0.06 | 1.43 | 2.53 |
| A2 GDP per capita growth (% y/y) | 2.34 | -2.97 | 3.73 | 0.98 | 3.02 | 0.36 | -0.78 | 0.92 | 2.58 |
| A3 Investment (GFCF) % GDP (% GDP) | 22.45 | 19.07 | 20.02 | 18.53 | 18.15 | 19.99 | 15.06 | 16.94 | 16.76 |
| B1 Inflation (GDP deflator, log) (100·log(1+π)) | 158.16 | 245.23 | 309.77 | 15.73 | 8.02 | 7.54 | 5.26 | 7.72 | 4.87 |
| B2 Real policy rate (ex-ante) (% p.a.) | – | – | – | – | 9.74 | 4.80 | 5.59 | 2.30 | 8.97 |
| C1 Primary balance % GDP (% GDP (Dec, 12m)) | – | – | – | – | 3.12 | 0.88 | -1.90 | -2.03 | -0.93 |
| C2 Δ Gross debt % GDP (pts/yr) | – | – | – | – | -0.93 | 2.75 | 3.26 | -0.90 | 2.79 |
| C4 Interest bill % GDP (% GDP) | – | – | – | – | 6.31 | 5.65 | 6.00 | 4.97 | 7.85 |
| D1 USD equity return (log) (% /yr (log)) | – | – | – | -7.13 | 32.10 | -26.42 | 23.82 | -1.82 | 13.33 |
| D2 BRL appreciation vs USD (log) (% /yr (+ = stronger BRL)) | – | – | – | -17.87 | 9.40 | -17.03 | 0.26 | -7.44 | -0.03 |
| D3 Real effective exchange rate (index 2010=100 (+ = stronger)) | 74.19 | 98.49 | 90.66 | 87.12 | 79.95 | 87.17 | 74.69 | 59.83 | 60.96 |
| D6 Current account % GDP (% GDP) | -0.23 | 0.20 | -0.11 | -3.45 | -0.50 | -3.71 | -1.91 | -2.42 | -2.31 |
| D7 FDI inflows % GDP (% GDP) | 0.48 | 0.39 | 0.47 | 3.10 | 2.48 | 3.58 | 3.85 | 3.22 | 3.25 |
| E1 Unemployment rate (%) | – | 6.99 | 6.30 | 9.70 | 9.61 | 7.44 | 12.23 | 12.01 | 6.58 |
| E3 Real minimum wage growth (% /yr (log)) | – | – | – | 0.44 | 5.50 | 2.20 | 1.25 | 0.07 | 3.25 |
| E5 Δ Gini (pts/yr) | 0.98 | -3.37 | 3.35 | -0.21 | -0.60 | -0.28 | 0.67 | -0.50 | -0.80 |
| E6 Δ Poverty $3.00/day (pts/yr) | -2.24 | 1.23 | -2.77 | -0.96 | -1.06 | -0.47 | 0.50 | -0.50 | -0.95 |
| F1 Infant mortality change (log) (% /yr (− = improving)) | -3.65 | -4.34 | -5.57 | -6.31 | -5.88 | -3.10 | -1.49 | -0.97 | -1.21 |
| F5 Δ Homicide rate (per 100k /yr) | – | – | – | 0.87 | -0.13 | 0.35 | -0.58 | -1.54 | -1.52 |
| GCC Δ WGI Control of Corruption (est. units/yr) | – | – | – | -0.00 | -0.01 | -0.07 | -0.02 | -0.01 | 0.02 |
| GGE Δ WGI Government Effectiveness (est. units/yr) | – | – | – | -0.01 | 0.01 | -0.02 | -0.04 | -0.01 | 0.01 |
| GRL Δ WGI Rule of Law (est. units/yr) | – | – | – | 0.01 | 0.03 | -0.04 | -0.06 | -0.01 | -0.00 |
| H1 Primary forest loss (Mha/yr) | – | – | – | – | 1.36 | 0.86 | 2.10 | 1.60 | 1.86 |

### 5.5 Inherited conditions — starting-point-adjusted change (term change regressed on start level)

| metric | n_terms | raw_diff | start_adjusted_diff | slope_on_start |
|---|---|---|---|---|
| C2 gross debt | 4 | +1.59 | +0.68 | -0.105 |
| E5 Gini | 9 | +0.29 | -0.38 | -0.243 |
| E1 unemployment | 7 | -0.72 | -0.66 | -0.192 |
| B2 real policy rate | 5 | +0.27 | +0.98 | -0.200 |
| E6 poverty $3 | 9 | -0.89 | -1.18 | -0.049 |

### 5.6 Within-president contrasts (descriptive; mandate means)

| metric | FHC I | FHC II | Lula I | Lula II | Lula III | Dilma I | Dilma II | Temer | Bolsonaro |
|---|---|---|---|---|---|---|---|---|---|
| A1 Real GDP growth | 2.54 | 2.32 | 3.52 | 4.64 | 2.53 | 2.35 | -3.55 | -0.06 | 1.43 |
| B1 Inflation (GDP deflator, log) | 23.86 | 7.6 | 8.59 | 7.45 | 4.87 | 7.61 | 7.29 | 5.26 | 7.72 |
| B2 Real policy rate (ex-ante) |  | 13.22 | 12.8 | 6.69 | 8.97 | 4.2 | 7.21 | 5.59 | 2.3 |
| C1 Primary balance % GDP |  |  | 3.46 | 2.78 | -0.93 | 1.57 | -1.86 | -1.9 | -2.03 |
| C2 Δ Gross debt % GDP |  |  |  | -0.93 | 2.79 | 1.13 | 9.22 | 3.26 | -0.9 |
| D1 USD equity return (log) | 2.72 | -16.98 | 46.88 | 17.32 | 13.33 | -19.82 | -52.82 | 23.82 | -1.82 |
| D2 BRL appreciation vs USD (log) | -8.76 | -26.98 | 12.56 | 6.23 | -0.03 | -11.66 | -38.53 | 0.26 | -7.44 |
| E1 Unemployment rate | 8.57 | 10.83 | 10.37 | 8.85 | 6.58 | 7.16 | 8.54 | 12.23 | 12.01 |
| E3 Real minimum wage growth | -3.31 | 4.2 | 6.28 | 4.71 | 3.25 | 2.8 | -0.17 | 1.25 | 0.07 |
| E5 Δ Gini | -0.05 | -0.38 | -0.62 | -0.58 | -0.8 | -0.3 | -0.2 | 0.67 | -0.5 |
| E6 Δ Poverty $3.00/day | -1.19 | -0.73 | -1.2 | -0.91 | -0.95 | -0.74 | 0.6 | 0.5 | -0.5 |
| F1 Infant mortality change (log) | -6.19 | -6.42 | -6.55 | -5.2 | -1.2 | -3.34 | -2.17 | -1.49 | -0.97 |
| F5 Δ Homicide rate |  | 0.87 | -0.39 | 0.14 | -1.52 | 0.69 | -1.01 | -0.58 | -1.54 |
| GCC Δ WGI Control of Corruption | 0.02 | -0.02 | -0.08 | 0.05 | 0.02 | -0.06 | -0.12 | -0.02 | -0.01 |
| H1 Primary forest loss |  | 1.62 | 1.71 | 1.02 | 1.86 | 0.87 | 0.83 | 2.1 | 1.6 |

Mandate ToT backdrop (mean ΔlogToT, log-pts/yr): Sarney +3.6, Collor +3.3, Itamar +10.5, FHC I +3.1, FHC II -3.8, Lula I +1.7, Lula II +4.8, Dilma I -1.1, Dilma II -12.4, Temer +2.2, Bolsonaro +1.7, Lula III +1.2. Same-person, same-lean mandates differ as much as opposite-lean ones: Lula II vs Lula III growth, FHC I vs FHC II BRL — the cycle moves with ToT, not with the person.

SQL behind the annual panel (catalog `agg` applied: last for stocks like debt/primary 12m, sum for counts, mean otherwise):
```sql
SELECT series_id, CAST(EXTRACT(year FROM date) AS INT) AS year,
       CASE WHEN any_value(c.agg) = 'sum' THEN sum(value)
            WHEN any_value(c.agg) = 'last' THEN arg_max(value, date)
            ELSE avg(value) END AS value,
       count(*) AS n_obs, max(date) AS last_obs
FROM v_observations o JOIN catalog c USING (series_id)
WHERE date <= current_date AND series_id IN (SELECT unnest($ids))
GROUP BY 1, 2 ORDER BY 1, 2
```
Year-end panel for returns:
```sql
SELECT series_id, CAST(EXTRACT(year FROM date) AS INT) AS year, arg_max(value, date) AS year_end, max(date) AS d
FROM v_observations
WHERE date <= current_date AND series_id IN ('ibovespa_usd','brl_usd','wb/DSTKMKTXD_M.BRA','wb/DPANUSSPB_M.BRA',
      'wb/REER_M.BRA','fx_reserves','embi_brazil','gov_real_yield_10y','ibc_br')
GROUP BY 1, 2 ORDER BY 1, 2
```

## 6. Event study

Daily changes; abnormal = raw cumulative change − (window length × mean daily change over [−250,−121]); Brent-adjusted variant = market model on Brent daily log change, estimated on the same window. Significance by placebo: 2,000 random non-event dates ≥ 90 days from any listed event. Coverage guard: a window is used only if the series has the full estimation and event window with no >2× calendar gap.

```sql
SELECT series_id, date, value FROM v_observations
WHERE date <= current_date AND series_id IN ('ibovespa_usd','ibovespa_level','brl_usd','embi_brazil','gov_real_yield_10y',
 'gov_nominal_yield_5y','focus_fx','focus_selic_12m','focus_ipca_12m','focus_gdp_growth','fx_reserves','brent_usd','selic_target')
ORDER BY series_id, date
```

**Left wins vs right/centre-right transitions (6 vs 3 events; permutation across events, floor 1/84 = 0.012):**

| series_id | window | n_left | n_right | mean_left_win | mean_right_transition | diff | perm_p | p_min |
|---|---|---|---|---|---|---|---|---|
| ibovespa_usd | [-1,+1] | 6 | 3 | 0.09 | 5.67 | -5.58 | 0.21 | 0.01 |
| ibovespa_usd | [-5,+5] | 6 | 3 | 2.53 | 10.41 | -7.88 | 0.19 | 0.01 |
| ibovespa_usd | [-20,+20] | 6 | 3 | 3.15 | 17.0 | -13.86 | 0.04 | 0.01 |
| ibovespa_usd | [-60,+60] | 6 | 3 | -11.81 | 51.22 | -63.04 | 0.01 | 0.01 |
| ibovespa_usd | [0,+60] | 6 | 3 | -3.75 | 19.36 | -23.11 | 0.01 | 0.01 |
| ibovespa_usd | pre [-120,-1] | 6 | 3 | -19.53 | 29.98 | -49.51 | 0.1 | 0.01 |
| ibovespa_usd | [-5,-1] | 6 | 3 | -0.04 | 5.5 | -5.54 | 0.21 | 0.01 |
| brl_usd | [-1,+1] | 6 | 3 | 0.24 | 0.93 | -0.69 | 0.64 | 0.01 |
| brl_usd | [-5,+5] | 6 | 3 | 0.48 | 3.63 | -3.15 | 0.31 | 0.01 |
| brl_usd | [-20,+20] | 6 | 3 | -0.6 | 9.3 | -9.91 | 0.01 | 0.01 |
| brl_usd | [-60,+60] | 6 | 3 | -7.87 | 23.18 | -31.05 | 0.01 | 0.01 |
| brl_usd | [0,+60] | 6 | 3 | -0.52 | 9.46 | -9.98 | 0.04 | 0.01 |
| brl_usd | pre [-120,-1] | 6 | 3 | -14.18 | 18.66 | -32.84 | 0.06 | 0.01 |
| brl_usd | [-5,-1] | 6 | 3 | -0.78 | 1.92 | -2.7 | 0.05 | 0.01 |
| embi_brazil | [-1,+1] | 6 | 3 | 12.46 | 2.61 | 9.85 | 0.8 | 0.01 |
| embi_brazil | [-5,+5] | 6 | 3 | -33.47 | -31.32 | -2.16 | 1.0 | 0.01 |
| embi_brazil | [-20,+20] | 6 | 3 | -135.19 | -59.22 | -75.98 | 0.99 | 0.01 |
| embi_brazil | [-60,+60] | 6 | 3 | -83.05 | -145.16 | 62.11 | 0.79 | 0.01 |
| embi_brazil | [0,+60] | 6 | 3 | -44.28 | -61.7 | 17.42 | 0.9 | 0.01 |
| embi_brazil | pre [-120,-1] | 6 | 3 | 149.46 | -83.92 | 233.38 | 0.4 | 0.01 |
| embi_brazil | [-5,-1] | 6 | 3 | -26.4 | -18.21 | -8.19 | 0.87 | 0.01 |
| gov_real_yield_10y | [-1,+1] | 2 | 3 | -0.2 | -13.89 | 13.69 | 0.3 | 0.1 |
| gov_real_yield_10y | [-5,+5] | 2 | 3 | -0.4 | -27.03 | 26.63 | 0.3 | 0.1 |
| gov_real_yield_10y | [-20,+20] | 2 | 3 | 2.6 | -105.9 | 108.5 | 0.1 | 0.1 |
| gov_real_yield_10y | [-60,+60] | 2 | 3 | -26.9 | -198.67 | 171.77 | 0.1 | 0.1 |
| gov_real_yield_10y | [0,+60] | 2 | 3 | -10.9 | -66.26 | 55.36 | 0.1 | 0.1 |
| gov_real_yield_10y | pre [-120,-1] | 2 | 3 | -38.5 | -135.82 | 97.32 | 0.5 | 0.1 |
| gov_real_yield_10y | [-5,-1] | 2 | 3 | -14.5 | -19.59 | 5.09 | 0.9 | 0.1 |
| focus_selic_12m | [-1,+1] | 6 | 3 | -0.36 | 0.18 | -0.54 | 0.69 | 0.02 |
| focus_selic_12m | [-5,+5] | 6 | 3 | -0.22 | 0.06 | -0.28 | 0.79 | 0.02 |
| focus_selic_12m | [-20,+20] | 6 | 3 | 0.33 | -0.73 | 1.05 | 0.49 | 0.01 |
| focus_selic_12m | [-60,+60] | 6 | 3 | -0.49 | -1.96 | 1.46 | 0.46 | 0.01 |
| focus_selic_12m | [0,+60] | 6 | 3 | -0.88 | -0.88 | -0.0 | 1.0 | 0.01 |
| focus_selic_12m | pre [-120,-1] | 6 | 3 | 0.92 | -1.69 | 2.61 | 0.23 | 0.01 |
| focus_selic_12m | [-5,-1] | 6 | 3 | 0.11 | -0.09 | 0.2 | 0.52 | 0.01 |

Brent-adjusted group means (ibovespa_usd, brl_usd; 2001+ events):

| series_id | window | left win | right transition |
|---|---|---|---|
| brl_usd | [-1,+1] | 0.2 | 0.71 |
| brl_usd | [-20,+20] | -0.53 | 9.41 |
| brl_usd | [-5,+5] | 0.45 | 3.35 |
| brl_usd | [-5,-1] | -0.8 | 1.83 |
| brl_usd | [-60,+60] | -7.28 | 23.17 |
| brl_usd | [0,+60] | -0.17 | 9.1 |
| brl_usd | pre [-120,-1] | -13.96 | 19.0 |
| ibovespa_usd | [-1,+1] | 0.17 | 5.36 |
| ibovespa_usd | [-20,+20] | 3.68 | 16.01 |
| ibovespa_usd | [-5,+5] | 2.64 | 9.79 |
| ibovespa_usd | [-5,-1] | 0.0 | 5.15 |
| ibovespa_usd | [-60,+60] | -9.77 | 47.85 |
| ibovespa_usd | [0,+60] | -2.69 | 17.67 |
| ibovespa_usd | pre [-120,-1] | -18.11 | 27.53 |

Per-event abnormal changes (log % for prices, + = stronger BRL; bp for spreads/yields):

| event_date | event | group | brl_usd [-1,+1] | brl_usd [0,+60] | brl_usd pre [-120,-1] | embi_brazil [-1,+1] | embi_brazil [0,+60] | embi_brazil pre [-120,-1] | gov_real_yield_10y [-1,+1] | gov_real_yield_10y [0,+60] | gov_real_yield_10y pre [-120,-1] | ibovespa_usd [-1,+1] | ibovespa_usd [0,+60] | ibovespa_usd pre [-120,-1] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2002-10-06 | 2002 R1 | first round | -0.6 | -4.3 | -61.7 | 71.0 | -332.9 | 1577.2 |  |  |  | -4.4 | 8.7 | -122.0 |
| 2002-10-27 | 2002 run-off (Lula) | left win | 0.8 | 3.6 | -53.6 | 74.5 | -335.9 | 940.6 |  |  |  | -1.4 | 4.0 | -85.5 |
| 2003-01-01 | 2003 inauguration (Lula) | inauguration-left | 2.3 | 14.5 | -4.5 | -86.6 | -717.7 | -725.9 |  |  |  | 6.2 | 25.2 | 20.9 |
| 2006-10-01 | 2006 R1 | first round | 0.5 | -0.1 | -5.0 | 6.5 | 35.4 | 133.5 |  |  |  | -0.1 | 9.2 | -32.5 |
| 2006-10-29 | 2006 run-off (Lula) | left win | -0.5 | -4.6 | -12.6 | 12.7 | 24.0 | 87.2 |  |  |  | -2.3 | -10.4 | -50.8 |
| 2007-01-01 | 2007 inauguration | inauguration-left | -0.1 | 0.6 | -4.9 | 2.8 | -3.0 | -31.6 |  |  |  | -0.4 | -0.2 | 8.2 |
| 2010-10-03 | 2010 R1 | first round | 0.8 | 0.2 | 3.1 | -1.2 | -8.6 | 58.3 |  |  |  | 3.0 | -7.0 | -12.5 |
| 2010-10-31 | 2010 run-off (Dilma) | left win | 1.1 | 3.0 | 6.9 | 2.1 | -7.7 | -32.4 |  |  |  | 3.3 | -2.8 | 15.6 |
| 2011-01-01 | 2011 inauguration (Dilma) | inauguration-left | 0.7 | 2.9 | 7.9 | -13.8 | -34.5 | -69.5 |  |  |  | 3.5 | 2.9 | 21.1 |
| 2014-10-05 | 2014 R1 | first round | 3.1 | -6.3 | -12.0 | -0.1 | 19.7 | 22.4 |  |  |  | 10.1 | -21.7 | -5.3 |
| 2014-10-26 | 2014 run-off (Dilma) | left win | 0.6 | -4.0 | -10.4 | -3.6 | 53.9 | 55.5 |  |  |  | 3.8 | -8.1 | -7.7 |
| 2015-01-01 | 2015 inauguration | inauguration-left | -2.2 | -22.1 | -24.4 | 20.9 | 82.4 | 79.2 |  |  |  | -7.8 | -22.2 | -37.6 |
| 2016-04-17 | 2016 Chamber impeachment vote | right transition | -0.6 | 19.3 | 35.3 | 4.7 | -113.2 | -165.2 | -17.4 | -67.0 | -270.7 | 2.1 | 26.5 | 54.0 |
| 2016-05-12 | 2016 Temer acting | other | -0.2 | 19.4 | 31.0 | -7.7 | -109.4 | -115.9 | -34.6 | -29.9 | -176.8 | -2.3 | 35.9 | 55.6 |
| 2016-08-31 | 2016 Senate removal | other | 0.4 | -4.6 | 12.0 | 9.9 | 7.0 | -176.2 | 2.5 | 55.0 | -9.1 | -0.4 | -3.6 | 22.9 |
| 2016-12-15 | 2016 spending cap | policy | -1.4 | -1.9 | -11.9 | 7.8 | 35.9 | 131.2 | -7.2 | -22.7 | 106.8 | -3.2 | 6.3 | -8.6 |
| 2018-10-07 | 2018 R1 | first round | 4.5 | 8.2 | -5.2 | -18.0 | 2.5 | 28.1 | -41.6 | -105.5 | 100.8 | 8.0 | 16.6 | -15.5 |
| 2018-10-28 | 2018 run-off (Bolsonaro) | right transition | 0.2 | 2.3 | 6.4 | -1.2 | -22.3 | 5.5 | -8.2 | -63.3 | 9.5 | 3.3 | 13.9 | 0.9 |
| 2019-01-01 | 2019 inauguration (Bolsonaro) | right transition | 3.1 | 6.8 | 14.3 | 4.2 | -49.7 | -92.2 | -16.1 | -68.5 | -146.3 | 11.6 | 17.7 | 35.0 |
| 2021-02-24 | 2021 BCB autonomy | policy | 1.3 | 13.1 | 20.7 | -7.1 | -24.8 | -25.5 | 8.5 | 55.7 | 8.7 | 1.3 | 26.8 | 50.1 |
| 2022-10-02 | 2022 R1 | first round | 4.4 | -3.1 | -27.1 | -34.2 | -15.1 | 25.2 | -20.5 | -7.4 | -32.8 | 12.0 | -5.7 | -38.3 |
| 2022-10-30 | 2022 run-off (Lula) | left win | 2.6 | 0.0 | -13.0 | -11.4 | 16.1 | -37.2 | -9.3 | 26.4 | 5.1 | 4.7 | 1.5 | 0.7 |
| 2023-01-01 | 2023 inauguration (Lula) | left win | -3.1 | -1.1 | -2.3 | 0.4 | -16.2 | -117.0 | 8.9 | -48.2 | -82.1 | -7.6 | -6.7 | 10.5 |
| 2023-08-31 | 2023 fiscal framework | policy | -1.3 | -1.0 | 4.6 | 0.0 | 10.1 | -3.5 | 15.3 | 20.4 | -128.8 | -1.5 | 9.5 | 22.5 |
| 2025-08-06 | 2025 US tariff | policy | 0.9 | 4.2 | 6.8 |  |  | 0.1 | -1.6 | -68.2 | -164.0 | 3.5 | 14.6 | 11.5 |
| 2026-10-04 | 2026 R1 | first round |  |  | -9.7 |  |  | 0.1 |  |  | 22.8 |  |  | -41.8 |

Events individually outside the placebo 95% band (two-sided p < 0.05), windows [−1,+1], [−5,+5], [0,+60]:

| event | series_id | window | car | raw_change | placebo_p | z |
|---|---|---|---|---|---|---|
| 2002 run-off (Lula) | ibovespa_usd | [-5,+5] | 16.8 | 18.43 | 0.04 | 2.01 |
| 2014 R1 | ibovespa_usd | [-1,+1] | 10.15 | 10.12 | 0.03 | 2.42 |
| 2022 R1 | ibovespa_usd | [-1,+1] | 11.96 | 12.41 | 0.02 | 2.86 |
| 2019 inauguration (Bolsonaro) | ibovespa_usd | [-1,+1] | 11.6 | 11.18 | 0.02 | 2.77 |
| 2014 R1 | ibovespa_level | [-1,+1] | 7.12 | 7.06 | 0.02 | 2.41 |
| 2022 R1 | ibovespa_level | [-1,+1] | 7.58 | 7.66 | 0.02 | 2.56 |
| 2019 inauguration (Bolsonaro) | ibovespa_level | [-1,+1] | 6.93 | 6.9 | 0.03 | 2.34 |
| 2002 run-off (Lula) | brl_usd | [-5,+5] | 8.12 | 9.01 | 0.03 | 2.43 |
| 2018 R1 | brl_usd | [-1,+1] | 4.52 | 4.33 | 0.02 | 2.8 |
| 2018 R1 | brl_usd | [-5,+5] | 8.38 | 7.68 | 0.02 | 2.51 |
| 2022 R1 | brl_usd | [-1,+1] | 4.43 | 4.76 | 0.02 | 2.74 |
| 2002 R1 | embi_brazil | [-1,+1] | 70.95 | 62.0 | 0.02 | 2.84 |
| 2002 R1 | embi_brazil | [-5,+5] | -146.17 | -179.0 | 0.02 | -2.92 |
| 2002 run-off (Lula) | embi_brazil | [-1,+1] | 74.52 | 72.0 | 0.02 | 2.98 |
| 2002 run-off (Lula) | embi_brazil | [-5,+5] | -220.78 | -230.0 | 0.01 | -4.41 |
| 2018 R1 | gov_real_yield_10y | [-1,+1] | -41.63 | -42.0 | 0.01 | -3.16 |
| 2018 R1 | gov_real_yield_10y | [-5,+5] | -79.65 | -81.0 | 0.01 | -3.13 |
| 2002 R1 | focus_fx | [-5,+5] | 0.31 | 0.29 | 0.0 | 5.05 |
| 2002 R1 | focus_fx | [0,+60] | 0.69 | 0.6 | 0.01 | 2.87 |
| 2016 Chamber impeachment vote | focus_fx | [-1,+1] | -0.11 | -0.09 | 0.01 | -4.39 |
| 2016 Chamber impeachment vote | focus_fx | [-5,+5] | -0.18 | -0.1 | 0.02 | -2.9 |
| 2016 Chamber impeachment vote | focus_fx | [0,+60] | -0.87 | -0.45 | 0.0 | -3.61 |
| 2002 R1 | focus_selic_12m | [-1,+1] | 0.43 | 0.38 | 0.03 | 2.0 |
| 2002 R1 | focus_selic_12m | [-5,+5] | 1.18 | 1.0 | 0.03 | 2.47 |
| 2002 run-off (Lula) | focus_selic_12m | [-1,+1] | 0.51 | 0.45 | 0.02 | 2.37 |
| 2002 run-off (Lula) | focus_selic_12m | [-5,+5] | 1.47 | 1.25 | 0.02 | 3.08 |
| 2014 run-off (Dilma) | focus_selic_12m | [-1,+1] | 0.45 | 0.5 | 0.03 | 2.11 |
| 2019 inauguration (Bolsonaro) | focus_selic_12m | [-1,+1] | 0.84 | 0.87 | 0.0 | 3.92 |
| 2023 inauguration (Lula) | focus_selic_12m | [-1,+1] | -3.19 | -3.12 | 0.0 | -14.85 |
| 2023 inauguration (Lula) | focus_selic_12m | [-5,+5] | -2.98 | -2.75 | 0.0 | -6.26 |
| 2023 inauguration (Lula) | focus_selic_12m | [0,+60] | -3.54 | -2.25 | 0.02 | -2.15 |

1994 and 1998 (monthly only — descriptive): wb/DPANUSSPB_M.BRA 1994-09: 0.86; wb/DPANUSSPB_M.BRA 1994-11: 0.84; wb/DPANUSSPB_M.BRA 1998-09: 1.18; wb/DPANUSSPB_M.BRA 1998-11: 1.19; wb/DSTKMKTXD_M.BRA 1994-09: 15.97; wb/DSTKMKTXD_M.BRA 1994-11: 14.48; wb/DSTKMKTXD_M.BRA 1998-09: 14.03; wb/DSTKMKTXD_M.BRA 1998-11: 17.96

**Constant-mean caveat:** the abnormal model subtracts the estimation-window drift; for 2026 that window (Oct 2025–Apr 2026) was a strong rally, so the 2026 pre-run-up 'abnormal' Ibov-USD figure (−41.8%) is mostly the removed drift — the raw change is in `event_study.csv` (`raw_change`).

## 7. Robustness

Grid per primary metric: sample (1985+/1995+/2003+) × unit (term / 4-year mandate / year-weighted) × lean coding (A–E) × attribution (contemporaneous / lag-1 / drop first year) × adjustment (raw / ToT / ToT+Brent, 2001+) × transform (mean / rank). Cells with < 2 units per side are blank. Full grid: `robustness_matrix.csv`; heatmap: `charts/robustness_heatmap.html`.

| id | metric | cells | share Δ>0 | Δ>0 1985+ | Δ>0 1995+ | Δ>0 2003+ | Δ>0 coding A | Δ>0 coding B | Δ>0 coding C | Δ>0 coding D | Δ>0 coding E | Δ>0 lag1 | Δ>0 ToT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Real GDP growth | 480 | 98% | 98% | 98% | 100% | 100% | 100% | 100% | 91% | 100% | 98% | 99% |
| A2 | GDP per capita growth | 480 | 97% | 97% | 96% | 100% | 100% | 100% | 100% | 84% | 100% | 96% | 96% |
| A3 | Investment (GFCF) % GDP | 480 | 98% | 97% | 97% | 100% | 100% | 93% | 90% | 100% | 100% | 100% | 99% |
| B1 | Inflation (GDP deflator, log) | 480 | 32% | 16% | 37% | 60% | 41% | 0% | 20% | 24% | 43% | 28% | 58% |
| B2 | Real policy rate (ex-ante) | 330 | 88% | 83% | 83% | 100% | 100% | – | 73% | 0% | 99% | 73% | 91% |
| C1 | Primary balance % GDP | 270 | 100% | 100% | 100% | 100% | 100% | – | – | – | 100% | 100% | 100% |
| C2 | Δ Gross debt % GDP | 270 | 46% | 46% | 46% | 46% | 49% | – | – | – | 42% | 67% | 70% |
| C4 | Interest bill % GDP | 270 | 93% | 93% | 93% | 93% | 96% | – | – | – | 91% | 97% | 93% |
| D1 | USD equity return (log) | 450 | 82% | 91% | 91% | 48% | 72% | – | 98% | 80% | 84% | 69% | 82% |
| D2 | BRL appreciation vs USD (log) | 450 | 100% | 100% | 100% | 98% | 99% | – | 100% | 100% | 99% | 100% | 100% |
| D3 | Real effective exchange rate | 480 | 85% | 68% | 96% | 100% | 85% | 63% | 73% | 96% | 89% | 95% | 79% |
| D6 | Current account % GDP | 480 | 72% | 69% | 91% | 40% | 68% | 13% | 82% | 89% | 70% | 61% | 79% |
| D7 | FDI inflows % GDP | 480 | 16% | 33% | 3% | 0% | 8% | 90% | 26% | 4% | 7% | 19% | 12% |
| E1 | Unemployment rate | 480 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| E3 | Real minimum wage growth | 450 | 99% | 99% | 99% | 100% | 100% | – | 98% | 98% | 100% | 100% | 100% |
| E5 | Δ Gini | 480 | 25% | 40% | 13% | 11% | 19% | 83% | 32% | 18% | 16% | 27% | 26% |
| E6 | Δ Poverty $3.00/day | 480 | 3% | 3% | 4% | 0% | 0% | 3% | 4% | 9% | 0% | 1% | 4% |
| F1 | Infant mortality change (log) | 480 | 17% | 19% | 23% | 0% | 14% | 0% | 32% | 20% | 12% | 38% | 25% |
| F5 | Δ Homicide rate | 450 | 56% | 46% | 46% | 93% | 73% | – | 20% | 29% | 80% | 61% | 61% |
| GCC | Δ WGI Control of Corruption | 450 | 2% | 0% | 0% | 10% | 3% | – | 0% | 0% | 4% | 0% | 3% |
| GGE | Δ WGI Government Effectiveness | 450 | 88% | 86% | 86% | 93% | 90% | – | 84% | 80% | 92% | 91% | 97% |
| GRL | Δ WGI Rule of Law | 450 | 93% | 91% | 91% | 100% | 99% | – | 82% | 84% | 100% | 100% | 97% |
| H1 | Primary forest loss | 330 | 7% | 8% | 8% | 7% | 7% | – | 20% | 0% | 7% | 16% | 7% |

Reading: E1 unemployment (0% positive → always lower under left), E6 poverty, E3 minimum wage, C1 primary balance, D2 BRL, A1/A2 growth are directionally stable; B1 inflation, C2 debt change, F5 homicides, D6/D7 flip with sample or coding. E5 Gini flips between the 1985+ baseline (Collor artifact) and 1995+ (left better).

## 8. Multiple comparisons

| id | metric | perm_p | floor | bh_q | perm_p_tot | bh_q_tot |
|---|---|---|---|---|---|---|
| A1 | Real GDP growth | 0.17 | 0.029 | 0.86 | 0.11 | 0.63 |
| A2 | GDP per capita growth | 0.17 | 0.029 | 0.86 | 0.17 | 0.63 |
| A3 | Investment (GFCF) % GDP | 0.51 | 0.029 | 0.99 | 0.26 | 0.63 |
| B1 | Inflation (GDP deflator, log) | 0.57 | 0.029 | 0.99 | 0.83 | 0.94 |
| B2 | Real policy rate (ex-ante) | 0.30 | 0.100 | 0.86 | 0.20 | 0.63 |
| C1 | Primary balance % GDP | 0.20 | 0.100 | 0.86 | 0.20 | 0.63 |
| C2 | Δ Gross debt % GDP | 1.00 | 0.100 | 1.00 | 0.80 | 0.94 |
| C4 | Interest bill % GDP | 0.40 | 0.100 | 0.92 | 0.50 | 0.77 |
| D1 | USD equity return (log) | 1.00 | 0.100 | 1.00 | 0.90 | 0.94 |
| D2 | BRL appreciation vs USD (log) | 0.60 | 0.100 | 0.99 | 0.40 | 0.76 |
| D3 | Real effective exchange rate | 0.77 | 0.029 | 1.00 | 0.83 | 0.94 |
| D6 | Current account % GDP | 0.80 | 0.029 | 1.00 | 0.43 | 0.76 |
| D7 | FDI inflows % GDP | 0.83 | 0.029 | 1.00 | 0.26 | 0.63 |
| E1 | Unemployment rate | 0.17 | 0.029 | 0.86 | 0.14 | 0.63 |
| E3 | Real minimum wage growth | 0.10 | 0.100 | 0.86 | 0.10 | 0.63 |
| E5 | Δ Gini | 0.97 | 0.029 | 1.00 | 0.94 | 0.94 |
| E6 | Δ Poverty $3.00/day | 0.29 | 0.029 | 0.86 | 0.23 | 0.63 |
| F1 | Infant mortality change (log) | 0.97 | 0.029 | 1.00 | 0.91 | 0.94 |
| F5 | Δ Homicide rate | 1.00 | 0.100 | 1.00 | 0.80 | 0.94 |
| GCC | Δ WGI Control of Corruption | 0.80 | 0.100 | 1.00 | 0.60 | 0.86 |
| GGE | Δ WGI Government Effectiveness | 0.30 | 0.100 | 0.86 | 0.30 | 0.63 |
| GRL | Δ WGI Rule of Law | 0.60 | 0.100 | 0.99 | 0.50 | 0.77 |
| H1 | Primary forest loss | 0.40 | 0.100 | 0.92 | 0.30 | 0.63 |

No primary metric clears BH at q = 0.10 (smallest q ≈ 0.86); no composite clears Holm at 0.10 (smallest 0.114, COMP-D). This was expected from the power floor and is reported, not hidden.

## 9. Scenarios 2027–2030 (full detail)

Branches: **S-L Lula IV (left)** and **S-R Flávio Bolsonaro (right)** are primary (external first-round result, section 0); **S-C centre** is secondary and uses coding B (FHC and Temer as 'centre') because Sarney/Itamar are hyperinflation-era. Fits use post-1995 mandates only. 'lo/hi' = model ± 1.28 × residual SD (≈80% band).

| metric_id | outcome | unit | branch | n_hist | hist_mandates | hist_min | hist_p25 | hist_median | hist_p75 | hist_max | beta_tot | r2 | n_fit | model ToT falls (p25) | model ToT falls (p25) lo | model ToT falls (p25) hi | model ToT flat-ish (p50) | model ToT flat-ish (p50) lo | model ToT flat-ish (p50) hi | model ToT rises (p75) | model ToT rises (p75) lo | model ToT rises (p75) hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | GDP growth | % /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | 2.35 | 2.48 | 3.02 | 3.8 | 4.64 | 0.08 | 0.45 | 8.0 | 3.03 | 1.49 | 4.57 | 3.27 | 1.73 | 4.81 | 3.4 | 1.86 | 4.94 |
| A1 | GDP growth | % /yr | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -0.06 | 1.06 | 1.88 | 2.38 | 2.54 | 0.08 | 0.45 | 8.0 | 1.39 | -0.15 | 2.93 | 1.63 | 0.09 | 3.17 | 1.76 | 0.22 | 3.31 |
| A1 | GDP growth | % /yr | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | -0.06 | 1.13 | 2.32 | 2.43 | 2.54 | 0.08 | 0.46 | 8.0 | 1.45 | -0.27 | 3.16 | 1.7 | -0.02 | 3.42 | 1.85 | 0.13 | 3.56 |
| B1 | Inflation (deflator, log) | 100·log(1+π) /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | 4.87 | 6.8 | 7.53 | 7.85 | 8.59 | 0.05 | 0.03 | 8.0 | 6.96 | 4.57 | 9.35 | 7.13 | 4.74 | 9.53 | 7.23 | 4.84 | 9.62 |
| B1 | Inflation (deflator, log) | 100·log(1+π) /yr | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | 5.26 | 7.02 | 7.66 | 8.23 | 9.73 | 0.05 | 0.03 | 8.0 | 7.46 | 5.07 | 9.85 | 7.63 | 5.24 | 10.02 | 7.73 | 5.34 | 10.12 |
| B1 | Inflation (deflator, log) | 100·log(1+π) /yr | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | 5.26 | 6.43 | 7.6 | 8.67 | 9.73 | 0.05 | 0.03 | 8.0 | 7.43 | 4.76 | 10.1 | 7.6 | 4.92 | 10.27 | 7.69 | 5.02 | 10.36 |
| B2 | Real policy rate | % p.a. | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | 4.2 | 6.06 | 7.83 | 9.93 | 12.8 | 0.39 | 0.38 | 6.0 | 6.96 | 2.14 | 11.79 | 8.2 | 3.37 | 13.03 | 8.91 | 4.08 | 13.73 |
| B2 | Real policy rate | % p.a. | S-R Flávio Bolsonaro (right) | 2 | Temer, Bolsonaro | 2.3 | 3.13 | 3.95 | 4.77 | 5.59 | 0.39 | 0.38 | 6.0 | 2.62 | -2.21 | 7.44 | 3.85 | -0.98 | 8.68 | 4.56 | -0.27 | 9.39 |
| B2 | Real policy rate | % p.a. | S-C centre (coding B: FHC/Temer as centre) | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| C1 | Primary balance | % GDP | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -0.93 | 0.94 | 2.17 | 2.95 | 3.46 | 0.29 | 0.67 | 6.0 | 0.84 | -1.46 | 3.14 | 1.74 | -0.56 | 4.05 | 2.26 | -0.04 | 4.57 |
| C1 | Primary balance | % GDP | S-R Flávio Bolsonaro (right) | 2 | Temer, Bolsonaro | -2.03 | -2.0 | -1.97 | -1.93 | -1.9 | 0.29 | 0.67 | 6.0 | -2.94 | -5.25 | -0.64 | -2.04 | -4.34 | 0.27 | -1.52 | -3.82 | 0.78 |
| C1 | Primary balance | % GDP | S-C centre (coding B: FHC/Temer as centre) | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| C2 | Δ Gross debt | pts GDP /yr | S-L Lula IV (left) | 3 | Lula II, Dilma I, Lula III | -0.93 | 0.1 | 1.13 | 1.96 | 2.79 | -0.35 | 0.14 | 5.0 | 2.05 | -1.27 | 5.36 | 0.96 | -2.36 | 4.27 | 0.33 | -2.98 | 3.65 |
| C2 | Δ Gross debt | pts GDP /yr | S-R Flávio Bolsonaro (right) | 2 | Temer, Bolsonaro | -0.9 | 0.14 | 1.18 | 2.22 | 3.26 | -0.35 | 0.14 | 5.0 | 2.36 | -0.96 | 5.67 | 1.27 | -2.05 | 4.58 | 0.64 | -2.67 | 3.96 |
| C2 | Δ Gross debt | pts GDP /yr | S-C centre (coding B: FHC/Temer as centre) | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| D3r | REER change | % /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -4.19 | -1.54 | 2.21 | 5.64 | 7.34 | 2.08 | 0.82 | 8.0 | -4.47 | -8.77 | -0.17 | 2.08 | -2.23 | 6.38 | 5.84 | 1.53 | 10.14 |
| D3r | REER change | % /yr | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -14.03 | -6.67 | -1.68 | 1.53 | 3.52 | 2.08 | 0.82 | 8.0 | -8.13 | -12.44 | -3.83 | -1.58 | -5.89 | 2.72 | 2.17 | -2.13 | 6.48 |
| D3r | REER change | % /yr | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | -14.03 | -6.59 | 0.86 | 2.19 | 3.52 | 2.15 | 0.85 | 8.0 | -7.39 | -11.78 | -3.0 | -0.63 | -5.02 | 3.77 | 3.25 | -1.14 | 7.65 |
| D1 | USD equity return | % /yr (log) | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -19.82 | 5.04 | 15.33 | 24.71 | 46.88 | 4.69 | 0.4 | 8.0 | 0.08 | -25.75 | 25.91 | 14.85 | -10.98 | 40.68 | 23.33 | -2.5 | 49.16 |
| D1 | USD equity return | % /yr (log) | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -16.98 | -5.61 | 0.45 | 7.99 | 23.82 | 4.69 | 0.4 | 8.0 | -8.59 | -34.42 | 17.23 | 6.18 | -19.65 | 32.0 | 14.66 | -11.17 | 40.49 |
| D1 | USD equity return | % /yr (log) | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | -16.98 | -7.13 | 2.72 | 13.27 | 23.82 | 4.9 | 0.43 | 8.0 | -6.33 | -34.58 | 21.92 | 9.09 | -19.16 | 37.34 | 17.95 | -10.31 | 46.2 |
| D2 | BRL vs USD | % /yr (+ = stronger) | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -11.66 | -2.94 | 3.1 | 7.81 | 12.56 | 3.17 | 0.77 | 8.0 | -7.93 | -16.77 | 0.92 | 2.06 | -6.79 | 10.9 | 7.79 | -1.05 | 16.64 |
| D2 | BRL vs USD | % /yr (+ = stronger) | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -26.98 | -13.32 | -8.1 | -5.52 | 0.26 | 3.17 | 0.77 | 8.0 | -17.85 | -26.69 | -9.0 | -7.86 | -16.71 | 0.98 | -2.13 | -10.97 | 6.72 |
| D2 | BRL vs USD | % /yr (+ = stronger) | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | -26.98 | -17.87 | -8.76 | -4.25 | 0.26 | 3.16 | 0.77 | 8.0 | -17.97 | -27.85 | -8.08 | -8.02 | -17.9 | 1.87 | -2.3 | -12.19 | 7.58 |
| E5 | Δ Gini | pts /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -0.8 | -0.67 | -0.6 | -0.51 | -0.3 | 0.03 | 0.38 | 8.0 | -0.67 | -1.21 | -0.12 | -0.57 | -1.12 | -0.03 | -0.52 | -1.06 | 0.03 |
| E5 | Δ Gini | pts /yr | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -0.5 | -0.41 | -0.21 | 0.13 | 0.67 | 0.03 | 0.38 | 8.0 | -0.13 | -0.68 | 0.41 | -0.04 | -0.58 | 0.51 | 0.02 | -0.53 | 0.56 |
| E5 | Δ Gini | pts /yr | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | -0.38 | -0.21 | -0.05 | 0.31 | 0.67 | 0.04 | 0.58 | 8.0 | -0.0 | -0.5 | 0.5 | 0.13 | -0.37 | 0.63 | 0.21 | -0.29 | 0.71 |
| E6 | Δ Poverty $3.00 | pts /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -1.2 | -1.01 | -0.93 | -0.87 | -0.74 | 0.01 | 0.22 | 8.0 | -0.97 | -1.7 | -0.24 | -0.95 | -1.68 | -0.22 | -0.94 | -1.67 | -0.21 |
| E6 | Δ Poverty $3.00 | pts /yr | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -1.19 | -0.84 | -0.61 | -0.25 | 0.5 | 0.01 | 0.22 | 8.0 | -0.5 | -1.23 | 0.23 | -0.47 | -1.2 | 0.26 | -0.46 | -1.19 | 0.27 |
| E6 | Δ Poverty $3.00 | pts /yr | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | -1.19 | -0.96 | -0.73 | -0.11 | 0.5 | 0.01 | 0.22 | 8.0 | -0.49 | -1.3 | 0.33 | -0.46 | -1.28 | 0.36 | -0.45 | -1.26 | 0.37 |
| E1c | Δ Unemployment | pts /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -0.91 | -0.54 | -0.37 | -0.3 | -0.24 | 0.07 | 0.4 | 8.0 | -0.67 | -1.58 | 0.23 | -0.46 | -1.37 | 0.44 | -0.34 | -1.25 | 0.56 |
| E1c | Δ Unemployment | pts /yr | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -0.77 | -0.1 | 0.51 | 0.99 | 1.26 | 0.07 | 0.4 | 8.0 | 0.23 | -0.68 | 1.13 | 0.44 | -0.47 | 1.34 | 0.56 | -0.35 | 1.46 |
| E1c | Δ Unemployment | pts /yr | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | 0.12 | 0.51 | 0.89 | 1.08 | 1.26 | 0.1 | 0.88 | 8.0 | 0.57 | 0.12 | 1.03 | 0.88 | 0.42 | 1.33 | 1.05 | 0.6 | 1.51 |
| E3 | Real min wage growth | % /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | 2.8 | 3.14 | 3.98 | 5.11 | 6.28 | -0.4 | 0.55 | 8.0 | 5.5 | 2.43 | 8.56 | 4.22 | 1.16 | 7.29 | 3.49 | 0.43 | 6.56 |
| E3 | Real min wage growth | % /yr | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -3.31 | -0.78 | 0.66 | 1.99 | 4.2 | -0.4 | 0.55 | 8.0 | 1.46 | -1.61 | 4.52 | 0.19 | -2.88 | 3.25 | -0.54 | -3.61 | 2.52 |
| E3 | Real min wage growth | % /yr | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | -3.31 | -1.03 | 1.25 | 2.72 | 4.2 | -0.4 | 0.55 | 8.0 | 1.49 | -1.93 | 4.91 | 0.23 | -3.19 | 3.65 | -0.5 | -3.92 | 2.93 |
| F1 | Infant mortality change | % /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -6.55 | -5.54 | -4.27 | -2.8 | -1.2 | 0.11 | 0.02 | 8.0 | -4.41 | -8.1 | -0.72 | -4.06 | -7.75 | -0.38 | -3.86 | -7.55 | -0.18 |
| F1 | Infant mortality change | % /yr | S-R Flávio Bolsonaro (right) | 4 | FHC I, FHC II, Temer, Bolsonaro | -6.42 | -6.25 | -3.84 | -1.36 | -0.97 | 0.11 | 0.02 | 8.0 | -4.02 | -7.71 | -0.33 | -3.67 | -7.36 | 0.02 | -3.47 | -7.16 | 0.22 |
| F1 | Infant mortality change | % /yr | S-C centre (coding B: FHC/Temer as centre) | 3 | FHC I, FHC II, Temer | -6.42 | -6.31 | -6.19 | -3.84 | -1.49 | 0.04 | 0.25 | 8.0 | -4.78 | -8.38 | -1.19 | -4.65 | -8.25 | -1.06 | -4.58 | -8.17 | -0.98 |
| F5 | Δ Homicide rate | per 100k /yr | S-L Lula IV (left) | 4 | Lula I, Lula II, Dilma I, Lula III | -1.52 | -0.67 | -0.13 | 0.28 | 0.69 | -0.2 | 0.29 | 7.0 | 0.34 | -0.95 | 1.62 | -0.29 | -1.57 | 1.0 | -0.65 | -1.93 | 0.64 |
| F5 | Δ Homicide rate | per 100k /yr | S-R Flávio Bolsonaro (right) | 3 | FHC II, Temer, Bolsonaro | -1.54 | -1.06 | -0.58 | 0.14 | 0.87 | -0.2 | 0.29 | 7.0 | -0.13 | -1.41 | 1.16 | -0.75 | -2.04 | 0.53 | -1.11 | -2.4 | 0.18 |
| F5 | Δ Homicide rate | per 100k /yr | S-C centre (coding B: FHC/Temer as centre) | 2 | FHC II, Temer | -0.58 | -0.22 | 0.14 | 0.51 | 0.87 | -0.14 | 0.47 | 7.0 | 0.23 | -1.04 | 1.51 | -0.22 | -1.5 | 1.06 | -0.48 | -1.76 | 0.8 |

Debt/GDP 2030 grid (`gross_public_debt_gdp` start, nominal g = `nominal_gdp_growth` 7.23%):

| r_minus_g | primary_balance | debt_2026 | debt_2027 | debt_2028 | debt_2029 | debt_2030 | current_r_minus_g |
|---|---|---|---|---|---|---|---|
| 2.0 | -1.0 | 82.9 | 85.4 | 88.0 | 90.6 | 93.3 | 5.1 |
| 2.0 | 0.0 | 82.9 | 84.4 | 86.0 | 87.6 | 89.2 | 5.1 |
| 2.0 | 1.0 | 82.9 | 83.4 | 84.0 | 84.5 | 85.1 | 5.1 |
| 2.0 | 2.0 | 82.9 | 82.4 | 81.9 | 81.5 | 81.0 | 5.1 |
| 4.0 | -1.0 | 82.9 | 87.0 | 91.2 | 95.6 | 100.2 | 5.1 |
| 4.0 | 0.0 | 82.9 | 86.0 | 89.2 | 92.5 | 95.9 | 5.1 |
| 4.0 | 1.0 | 82.9 | 85.0 | 87.1 | 89.4 | 91.7 | 5.1 |
| 4.0 | 2.0 | 82.9 | 84.0 | 85.1 | 86.3 | 87.5 | 5.1 |
| 6.0 | -1.0 | 82.9 | 88.5 | 94.4 | 100.7 | 107.4 | 5.1 |
| 6.0 | 0.0 | 82.9 | 87.5 | 92.4 | 97.6 | 103.0 | 5.1 |
| 6.0 | 1.0 | 82.9 | 86.5 | 90.3 | 94.4 | 98.7 | 5.1 |
| 6.0 | 2.0 | 82.9 | 85.5 | 88.3 | 91.2 | 94.3 | 5.1 |

Debt by branch (pb from each lean's post-2002 mandate history):

| branch | pb_case | primary_balance | r_minus_g | debt_2030 | hist_mandates |
|---|---|---|---|---|---|
| S-L Lula IV (left) | pb p25 | -0.93 | 4.0 | 99.88 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-L Lula IV (left) | pb p25 | -0.93 | 5.06 | 103.64 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-L Lula IV (left) | pb p25 | -0.93 | 6.0 | 107.08 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-L Lula IV (left) | pb median | 1.57 | 4.0 | 89.3 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-L Lula IV (left) | pb median | 1.57 | 5.06 | 92.91 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-L Lula IV (left) | pb median | 1.57 | 6.0 | 96.2 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-L Lula IV (left) | pb p75 | 2.78 | 4.0 | 84.16 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-L Lula IV (left) | pb p75 | 2.78 | 5.06 | 87.69 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-L Lula IV (left) | pb p75 | 2.78 | 6.0 | 90.92 | Lula I, Lula II, Dilma I, Dilma II, Lula III |
| S-R Flávio Bolsonaro (right) | pb p25 | -2.0 | 4.0 | 104.38 | Temer, Bolsonaro |
| S-R Flávio Bolsonaro (right) | pb p25 | -2.0 | 5.06 | 108.2 | Temer, Bolsonaro |
| S-R Flávio Bolsonaro (right) | pb p25 | -2.0 | 6.0 | 111.7 | Temer, Bolsonaro |
| S-R Flávio Bolsonaro (right) | pb median | -1.97 | 4.0 | 104.25 | Temer, Bolsonaro |
| S-R Flávio Bolsonaro (right) | pb median | -1.97 | 5.06 | 108.07 | Temer, Bolsonaro |
| S-R Flávio Bolsonaro (right) | pb median | -1.97 | 6.0 | 111.57 | Temer, Bolsonaro |
| S-R Flávio Bolsonaro (right) | pb p75 | -1.93 | 4.0 | 104.11 | Temer, Bolsonaro |
| S-R Flávio Bolsonaro (right) | pb p75 | -1.93 | 5.06 | 107.94 | Temer, Bolsonaro |
| S-R Flávio Bolsonaro (right) | pb p75 | -1.93 | 6.0 | 111.43 | Temer, Bolsonaro |

Reference paths: pb=-0.62 (current 12m, Aug 2026), r-g=4.00 → 98.6%; pb=-0.62 (current 12m, Aug 2026), r-g=5.06 → 102.3%; pb=-0.62 (current 12m, Aug 2026), r-g=6.00 → 105.7%; pb=0.38 (Bolsonaro ex-2020 mean), r-g=4.00 → 94.3%; pb=0.38 (Bolsonaro ex-2020 mean), r-g=5.06 → 98.0%; pb=0.38 (Bolsonaro ex-2020 mean), r-g=6.00 → 101.4%. Debt-stabilising primary: r−g 2: 1.55%, r−g 4: 3.09%, r−g 5.057817253900551: 3.91%, r−g 6: 4.64%. Warehouse gold `derived_metrics.debt_stabilizing_primary_surplus_gap` (2026) = 6.9 pts, computed with r−g 7.69 (real policy rate − Focus growth) — a harsher marginal-rate view; `hypothesis_tests` L3 confirms r−g = +5.06 on the stock (Aug 2026).

Starting conditions used (series_id, value, date, source):

| series_id | value | date | source |
|---|---|---|---|
| selic_target | 13.75 | 2026-10-03 | Banco Central (SGS) |
| real_policy_rate | 9.27 | 2026-09-01 | Derived |
| ipca_12m | 4.22 | 2026-08-01 | Banco Central (SGS) |
| focus_ipca_12m | 4.65 | 2026-09-25 | Banco Central (Focus) |
| focus_selic_12m | 12.00 | 2026-09-25 | Banco Central (Focus) |
| focus_gdp_growth | 1.41 | 2026-09-25 | Banco Central (Focus) |
| focus_fx | 5.28 | 2026-09-25 | Banco Central (Focus) |
| gov_real_yield_10y | 7.52 | 2026-10-02 | Tesouro Direto |
| gov_nominal_yield_5y | 14.15 | 2026-10-02 | Tesouro Direto |
| brl_usd | 5.22 | 2026-10-02 | Banco Central (SGS) |
| ibovespa_usd | 35,945.01 | 2026-10-01 | Derived |
| ibovespa_level | 187,198.00 | 2026-10-01 | IPEAData |
| gross_public_debt_gdp | 82.86 | 2026-08-01 | Banco Central (SGS) |
| net_public_debt_gdp | 60.79 | 2026-08-01 | Banco Central (SGS) |
| primary_balance_gdp | -0.62 | 2026-08-01 | Derived |
| nominal_deficit_gdp | 9.48 | 2026-08-01 | Banco Central (SGS) |
| interest_bill_gdp | 8.86 | 2026-08-01 | Derived |
| r_minus_g | 5.06 | 2026-08-01 | Derived |
| implicit_interest_rate | 12.29 | 2026-08-01 | Derived |
| nominal_gdp_growth | 7.23 | 2026-08-01 | Derived |
| unemployment_rate | 5.30 | 2026-08-01 | IBGE (SIDRA) |
| fx_reserves | 362,616.00 | 2026-10-01 | Banco Central (SGS) |
| brent_usd | 113.96 | 2026-09-29 | IPEAData |
| credit_gdp | 55.44 | 2026-08-01 | Banco Central (SGS) |
| wb/SI.POV.GINI.BR | 50.30 | 2024-12-31 | World Bank (Dateno) |
| wb/SI.POV.DDAY.BR | 3.00 | 2024-12-31 | World Bank (Dateno) |
| wb/PX.REX.REER.BR | 59.08 | 2025-12-31 | World Bank (Dateno) |
| wb/REER_M.BRA | 57.05 | 2024-10-31 | World Bank (Dateno) |
| wb/TOT.BRA | 1.09 | 2025-12-31 | World Bank (Dateno) |
| oil_exports | 4,828,278,519.00 | 2026-08-01 | ComexStat (MDIC) |
| presalt_share | 78.96 | 2026-08-01 | ANP |
| exports_to_us | 3,190,410,423.00 | 2026-08-01 | ComexStat (MDIC) |
| exports_to_china | 8,340,152,574.00 | 2026-08-01 | ComexStat (MDIC) |
| real_average_income | 3,777.00 | 2026-08-01 | IBGE (SIDRA) |

Note vs the original brief: the warehouse has Selic **13.75** (cut on 2026-09-17), not 14.5. Brent is $114 (126.7 in Mar 2026): a 2026 oil shock is in the data, which flatters an oil exporter's ToT and fiscal take but raises inflation expectations (Focus IPCA 12m 4.02 → 4.65 YTD).

## 10. 2026 pre-election market-pricing check

Change from window start to the last observation before 2026-10-04 (log % for prices, + = stronger BRL; bp for yields; level for Focus), vs the same windows before the 2002–2022 first rounds. Rule fixed in advance: inside the historical IQR ⇒ 'no unusual election premium'; outside ⇒ report direction without attributing it to a candidate.

| series_id | window | change_2026 | n_hist | hist_mean | hist_p25 | hist_p75 | z | inside_iqr | hist_values |
|---|---|---|---|---|---|---|---|---|---|
| brl_usd | Jul 1→t−1 | -0.91 | 6 | -5.78 | -10.09 | -0.39 | 0.43 | True | 2002:-25.19; 2006:-0.46; 2010:+6.91; 2014:-12.40; 2018:-0.37; 2022:-3.17 |
| brl_usd | Sep 1→t−1 | -0.81 | 6 | -4.13 | -9.12 | 2.85 | 0.35 | True | 2002:-19.13; 2006:-1.64; 2010:+4.35; 2014:-10.73; 2018:+6.63; 2022:-4.30 |
| brl_usd | YTD (Jan 1→t−1) | 5.2 | 6 | -8.9 | -13.32 | 3.42 | 0.71 | False | 2002:-45.55; 2006:+7.38; 2010:+3.51; 2014:-6.23; 2018:-15.69; 2022:+3.17 |
| brl_usd | t−5→t−1 | -0.47 | 6 | 1.08 | -1.44 | 3.05 | -0.46 | True | 2002:+5.19; 2006:+1.98; 2010:+1.82; 2014:-2.53; 2018:+3.40; 2022:-3.40 |
| focus_fx | Jul 1→t−1 | -0.02 | 6 | 0.12 | -0.04 | 0.2 | -0.6 | True | 2002:+0.55; 2006:-0.05; 2010:-0.10; 2014:+0.00; 2018:+0.23; 2022:+0.10 |
| focus_fx | Sep 1→t−1 | -0.02 | 6 | 0.05 | 0.0 | 0.1 | -0.69 | False | 2002:+0.25; 2006:+0.00; 2010:-0.05; 2014:+0.00; 2018:+0.13; 2022:+0.00 |
| focus_fx | YTD (Jan 1→t−1) | -0.22 | 6 | 0.12 | -0.06 | 0.38 | -0.91 | False | 2002:+0.60; 2006:-0.10; 2010:+0.05; 2014:+0.05; 2018:+0.49; 2022:-0.40 |
| focus_fx | t−5→t−1 | 0.0 | 6 | 0.04 | 0.0 | 0.04 | -0.51 | True | 2002:+0.17; 2006:+0.00; 2010:+0.00; 2014:+0.05; 2018:+0.00; 2022:+0.00 |
| focus_gdp_growth | Jul 1→t−1 | -0.28 | 6 | -0.26 | -0.43 | 0.0 | -0.05 | True | 2002:-0.90; 2006:-0.20; 2010:+0.00; 2014:-0.50; 2018:+0.00; 2022:+0.03 |
| focus_gdp_growth | Sep 1→t−1 | -0.09 | 6 | -0.06 | -0.08 | 0.0 | -0.17 | False | 2002:-0.40; 2006:+0.00; 2010:+0.00; 2014:-0.10; 2018:+0.00; 2022:+0.15 |
| focus_gdp_growth | YTD (Jan 1→t−1) | -0.39 | 6 | -0.26 | -0.58 | 0.13 | -0.27 | True | 2002:+0.20; 2006:+0.00; 2010:-0.70; 2014:-1.00; 2018:-0.20; 2022:+0.17 |
| focus_gdp_growth | t−5→t−1 | -0.02 | 6 | -0.01 | -0.01 | 0.0 | -0.21 | False | 2002:-0.10; 2006:+0.00; 2010:+0.00; 2014:-0.01; 2018:+0.00; 2022:+0.03 |
| focus_ipca_12m | Jul 1→t−1 | 0.52 | 6 | 0.2 | -0.18 | 0.44 | 0.57 | False | 2002:+1.11; 2006:-0.24; 2010:+0.31; 2014:+0.48; 2018:+0.02; 2022:-0.47 |
| focus_ipca_12m | Sep 1→t−1 | 0.09 | 6 | -0.0 | -0.29 | 0.25 | 0.24 | True | 2002:+0.40; 2006:-0.43; 2010:+0.14; 2014:+0.14; 2018:+0.29; 2022:-0.55 |
| focus_ipca_12m | YTD (Jan 1→t−1) | 0.63 | 6 | 0.29 | 0.05 | 0.63 | 0.69 | True | 2002:+0.94; 2006:-0.42; 2010:+0.72; 2014:+0.37; 2018:+0.14; 2022:+0.02 |
| focus_ipca_12m | t−5→t−1 | 0.02 | 6 | 0.01 | 0.01 | 0.03 | 0.45 | True | 2002:+0.01; 2006:-0.03; 2010:+0.01; 2014:+0.05; 2018:+0.03; 2022:+0.00 |
| focus_selic_12m | Jul 1→t−1 | 0.0 | 6 | 0.02 | -0.09 | 0.0 | -0.05 | True | 2002:+0.00; 2006:-0.50; 2010:+0.00; 2014:-0.12; 2018:+0.00; 2022:+0.75 |
| focus_selic_12m | Sep 1→t−1 | 0.0 | 6 | 0.02 | 0.0 | 0.22 | -0.08 | True | 2002:+0.00; 2006:-0.50; 2010:+0.25; 2014:+0.13; 2018:+0.00; 2022:+0.25 |
| focus_selic_12m | YTD (Jan 1→t−1) | -0.25 | 6 | -0.19 | -1.56 | 1.19 | -0.04 | True | 2002:-2.00; 2006:-2.50; 2010:+1.00; 2014:+1.38; 2018:+1.25; 2022:-0.25 |
| focus_selic_12m | t−5→t−1 | 0.0 | 6 | 0.08 | 0.0 | 0.0 | -0.41 | True | 2002:+0.00; 2006:+0.00; 2010:+0.00; 2014:+0.50; 2018:+0.00; 2022:+0.00 |
| fx_reserves | Jul 1→t−1 | -1.35 | 6 | 1.76 | -3.21 | 6.54 | -0.34 | True | 2002:-9.94; 2006:+15.79; 2010:+8.59; 2014:+0.37; 2018:+0.06; 2022:-4.30 |
| fx_reserves | Sep 1→t−1 | -2.72 | 6 | 0.64 | -0.95 | 2.23 | -1.07 | False | 2002:+1.01; 2006:+2.64; 2010:+5.40; 2014:-1.13; 2018:-0.44; 2022:-3.62 |
| fx_reserves | YTD (Jan 1→t−1) | 1.22 | 6 | 7.88 | 2.24 | 12.36 | -0.48 | False | 2002:+5.84; 2006:+31.06; 2010:+14.53; 2014:+4.39; 2018:+1.53; 2022:-10.05 |
| fx_reserves | t−5→t−1 | -0.51 | 6 | -0.4 | -0.82 | -0.25 | -0.14 | True | 2002:-1.42; 2006:-0.35; 2010:+0.83; 2014:-0.24; 2018:-0.27; 2022:-0.97 |
| gov_nominal_yield_5y | Jul 1→t−1 | -22.0 | 2 | -57.0 | -70.5 | -43.5 | 0.92 | False | 2018:-30.00; 2022:-84.00 |
| gov_nominal_yield_5y | Sep 1→t−1 | -39.0 | 2 | -62.0 | -83.5 | -40.5 | 0.38 | False | 2018:-105.00; 2022:-19.00 |
| gov_nominal_yield_5y | YTD (Jan 1→t−1) | 55.0 | 2 | 93.5 | 72.25 | 114.75 | -0.64 | False | 2018:+51.00; 2022:+136.00 |
| gov_nominal_yield_5y | t−5→t−1 | 2.0 | 2 | -5.0 | -26.0 | 16.0 | 0.12 | True | 2018:-47.00; 2022:+37.00 |
| gov_real_yield_10y | Jul 1→t−1 | -42.0 | 2 | -11.5 | -15.25 | -7.75 | -2.88 | False | 2018:-19.00; 2022:-4.00 |
| gov_real_yield_10y | Sep 1→t−1 | -13.0 | 2 | -16.5 | -18.25 | -14.75 | 0.71 | False | 2018:-20.00; 2022:-13.00 |
| gov_real_yield_10y | YTD (Jan 1→t−1) | 18.0 | 2 | 54.5 | 48.25 | 60.75 | -2.06 | False | 2018:+42.00; 2022:+67.00 |
| gov_real_yield_10y | t−5→t−1 | 2.0 | 2 | -12.5 | -20.75 | -4.25 | 0.62 | False | 2018:-29.00; 2022:+4.00 |
| ibovespa_level | Jul 1→t−1 | 8.45 | 6 | 3.52 | 0.26 | 12.02 | 0.4 | True | 2002:-18.47; 2006:-0.50; 2010:+14.19; 2014:+2.55; 2018:+12.34; 2022:+11.03 |
| ibovespa_level | Sep 1→t−1 | 5.37 | 6 | -1.24 | -8.46 | 5.48 | 0.77 | True | 2002:-11.44; 2006:+0.60; 2010:+7.51; 2014:-11.66; 2018:+7.10; 2022:+0.47 |
| ibovespa_level | YTD (Jan 1→t−1) | 15.0 | 6 | -1.55 | 2.99 | 7.03 | 0.91 | False | 2002:-38.27; 2006:+8.57; 2010:+2.36; 2014:+5.72; 2018:+7.46; 2022:+4.86 |
| ibovespa_level | t−5→t−1 | 1.74 | 6 | 1.84 | -0.4 | 4.4 | -0.02 | True | 2002:+6.05; 2006:+4.63; 2010:+2.94; 2014:-4.78; 2018:+3.69; 2022:-1.51 |
| ibovespa_usd | Jul 1→t−1 | 7.85 | 6 | -2.25 | -7.63 | 10.95 | 0.44 | True | 2002:-43.67; 2006:-0.95; 2010:+21.10; 2014:-9.85; 2018:+11.98; 2022:+7.87 |
| ibovespa_usd | Sep 1→t−1 | 4.86 | 6 | -5.37 | -17.75 | 8.64 | 0.57 | True | 2002:-30.56; 2006:-1.04; 2010:+11.87; 2014:-22.39; 2018:+13.74; 2022:-3.83 |
| ibovespa_usd | YTD (Jan 1→t−1) | 20.5 | 6 | -10.45 | -6.3 | 7.48 | 0.84 | False | 2002:-83.83; 2006:+15.95; 2010:+5.87; 2014:-0.51; 2018:-8.23; 2022:+8.02 |
| ibovespa_usd | t−5→t−1 | 1.19 | 6 | 2.91 | -2.5 | 6.97 | -0.23 | True | 2002:+11.24; 2006:+6.61; 2010:+4.75; 2014:-7.31; 2018:+7.09; 2022:-4.92 |

Confounds inside the 2026 window: Selic cut to 13.75 on 2026-09-17, Brent 61 → 114 over 2026, the 2025 US tariff. `embi_brazil` ends 2024-07-30 and cannot be used. Reading: BRL, Ibovespa (USD and BRL) and Focus Selic moves over the 3-month, 1-month and 1-week windows are inside the historical IQR; Focus IPCA rose more than usual Jul→t−1 (oil); YTD equity and BRL strength and the Jul→t−1 fall in 10y real yields are outside it (direction: easier financial conditions, not an election premium). The market reaction to Flávio Bolsonaro's first-round lead is not observable in this warehouse.

## 11. What can and cannot be concluded

**Can:** (i) Over 1985–2026, the commodity/ToT cycle explains more of the between-term variation in markets, the BRL, the current account and debt dynamics than presidential lean does. (ii) Left (PT) terms are consistently associated with lower unemployment, faster real minimum-wage growth, faster poverty reduction and (post-1995) faster Gini decline — the distribution composite separates the two sides completely — and this survives the ToT control. (iii) Left terms also had higher real policy rates and higher interest bills, and — against the right narrative — larger primary surpluses on average (driven by Lula I–II). (iv) Markets reacted better in the 60 days after the three right/centre-right transitions than after six left wins; the event-day reaction itself does not differ. (v) Health and safety outcomes (infant mortality, homicides) and WGI scores show no lean pattern.

**Cannot:** causal effects of lean; anything at conventional significance (term-level permutation floor 0.029; 0.10 for post-2001 series); coalition/Congress effects (no data); separation of lean from the specific shocks each term met; the 2026 first-round market reaction; any point forecast for 2027–2030.

## Appendix — every series used (source, coverage, latest observation)

| series_id | source | freq | role | first | last | n |
|---|---|---|---|---|---|---|
| brent_usd | IPEAData | daily | canonical | 2000-01-04 | 2026-09-29 | 8571 |
| brl_usd | Banco Central (SGS) | daily | canonical | 2000-01-03 | 2026-10-02 | 6720 |
| credit_gdp | Banco Central (SGS) | monthly | canonical | 2000-01-01 | 2026-08-01 | 320 |
| embi_brazil | IPEAData | daily | canonical | 2000-01-03 | 2024-07-30 | 6335 |
| exports_to_china | ComexStat (MDIC) | monthly | canonical | 2014-01-01 | 2026-08-01 | 152 |
| exports_to_us | ComexStat (MDIC) | monthly | canonical | 2014-01-01 | 2026-08-01 | 152 |
| focus_fx | Banco Central (Focus) | daily | canonical | 2000-01-13 | 2026-09-25 | 6699 |
| focus_gdp_growth | Banco Central (Focus) | daily | canonical | 1999-07-01 | 2026-09-25 | 6810 |
| focus_ipca_12m | Banco Central (Focus) | daily | canonical | 2001-12-12 | 2026-09-25 | 6222 |
| focus_selic_12m | Banco Central (Focus) | daily | canonical | 2000-01-20 | 2026-09-25 | 6694 |
| fx_reserves | Banco Central (SGS) | daily | canonical | 2000-01-03 | 2026-10-01 | 6719 |
| gov_nominal_yield_5y | Tesouro Direto | daily | canonical | 2015-01-02 | 2026-10-02 | 2927 |
| gov_real_yield_10y | Tesouro Direto | daily | canonical | 2015-01-02 | 2026-10-02 | 2927 |
| gross_public_debt_gdp | Banco Central (SGS) | monthly | canonical | 2006-12-01 | 2026-08-01 | 237 |
| homicide_deaths | DATASUS (SIM) | monthly | canonical | 1996-01-01 | 2026-05-01 | 365 |
| homicide_rate | WHO Mortality Database | annual | canonical | 2000-12-31 | 2023-12-31 | 24 |
| ibc_br | Banco Central (SGS) | monthly | canonical | 2003-01-01 | 2026-07-01 | 283 |
| ibovespa_level | IPEAData | daily | canonical | 2000-01-03 | 2026-10-01 | 6658 |
| ibovespa_usd | Derived | daily | derived | 2000-01-03 | 2026-10-01 | 6638 |
| ilostat/EAR_EMTG_SEX_NB.BRA | ILO (Dateno) | annual | canonical | 1989-12-31 | 2025-12-31 | 31 |
| ilostat/EAR_INEE_NOC_NB.BRA | ILO (Dateno) | annual | canonical | 1994-12-31 | 2024-12-31 | 31 |
| ilostat/LAP_2GDP_NOC_RT.BRA | ILO (Dateno) | annual | canonical | 2004-12-31 | 2025-12-31 | 22 |
| ilostat/SDG_0821_NOC_RT.BRA | ILO (Dateno) | annual | canonical | 2000-12-31 | 2025-12-31 | 26 |
| ilostat/SDG_0831_SEX_ECO_RT.BRA | ILO (Dateno) | annual | canonical | 2009-12-31 | 2025-12-31 | 16 |
| implicit_interest_rate | Derived | monthly | derived | 2007-12-01 | 2026-08-01 | 225 |
| interest_bill_gdp | Derived | monthly | derived | 2002-11-01 | 2026-08-01 | 286 |
| ipca_12m | Banco Central (SGS) | monthly | canonical | 2000-01-01 | 2026-08-01 | 320 |
| net_public_debt_gdp | Banco Central (SGS) | monthly | canonical | 2001-12-01 | 2026-08-01 | 297 |
| nominal_deficit_gdp | Banco Central (SGS) | monthly | canonical | 2002-11-01 | 2026-08-01 | 286 |
| nominal_gdp_growth | Derived | monthly | derived | 2001-01-01 | 2026-08-01 | 308 |
| oil_exports | ComexStat (MDIC) | monthly | canonical | 2014-01-01 | 2026-08-01 | 152 |
| population | IBGE (SIDRA) | annual | canonical | 2000-12-31 | 2025-12-31 | 26 |
| presalt_share | ANP | monthly | canonical | 2016-01-01 | 2026-08-01 | 128 |
| primary_balance_gdp | Derived | monthly | derived | 2002-11-01 | 2026-08-01 | 286 |
| r_minus_g | Derived | monthly | derived | 2007-12-01 | 2026-08-01 | 225 |
| real_average_income | IBGE (SIDRA) | monthly | canonical | 2012-03-01 | 2026-08-01 | 174 |
| real_policy_rate | Derived | monthly | derived | 2001-12-01 | 2026-09-01 | 298 |
| selic_target | Banco Central (SGS) | daily | canonical | 2000-01-03 | 2026-10-03 | 9771 |
| unemployment_rate | IBGE (SIDRA) | monthly | canonical | 2012-03-01 | 2026-08-01 | 174 |
| wb/AG.LND.PFLS.HA.BR | World Bank (Dateno) | annual | canonical | 2002-12-31 | 2025-12-31 | 24 |
| wb/BN.CAB.XOKA.GD.ZS.BR | World Bank (Dateno) | annual | canonical | 1975-12-31 | 2025-12-31 | 51 |
| wb/BX.KLT.DINV.WD.GD.ZS.BR | World Bank (Dateno) | annual | canonical | 1970-12-31 | 2025-12-31 | 56 |
| wb/CM.MKT.LCAP.GD.ZS.BR | World Bank (Dateno) | annual | canonical | 2000-12-31 | 2025-12-31 | 26 |
| wb/DPANUSSPB_M.BRA | World Bank (Dateno) | monthly | canonical | 1988-03-31 | 2025-12-31 | 454 |
| wb/DSTKMKTXD_M.BRA | World Bank (Dateno) | monthly | canonical | 1994-01-31 | 2025-12-31 | 384 |
| wb/DXGSRMRCHNSXD_M.BRA | World Bank (Dateno) | monthly | canonical | 1991-01-31 | 2025-12-31 | 420 |
| wb/EN.GHG.CO2.LU.MT.CE.AR5.BR | World Bank (Dateno) | annual | canonical | 2000-12-31 | 2023-12-31 | 24 |
| wb/EN.GHG.CO2.PC.CE.AR5.BR | World Bank (Dateno) | annual | canonical | 1970-12-31 | 2024-12-31 | 55 |
| wb/FI.RES.TOTL.MO.BR | World Bank (Dateno) | annual | canonical | 1975-12-31 | 2025-12-31 | 51 |
| wb/FP.CPI.TOTL.BR | World Bank (Dateno) | annual | canonical | 1980-12-31 | 2025-12-31 | 46 |
| wb/FR.INR.RINR.BR | World Bank (Dateno) | annual | canonical | 1997-12-31 | 2025-12-31 | 29 |
| wb/FS.AST.PRVT.GD.ZS.BR | World Bank (Dateno) | annual | canonical | 1960-12-31 | 2025-12-31 | 64 |
| wb/GC.TAX.TOTL.GD.ZS.BR | World Bank (Dateno) | annual | canonical | 2010-12-31 | 2024-12-31 | 15 |
| wb/GOV_WGI_CC_EST.BR | World Bank (Dateno) | annual | canonical | 1996-12-31 | 2024-12-31 | 26 |
| wb/GOV_WGI_GE_EST.BR | World Bank (Dateno) | annual | canonical | 1996-12-31 | 2024-12-31 | 26 |
| wb/GOV_WGI_PV_EST.BR | World Bank (Dateno) | annual | canonical | 1996-12-31 | 2024-12-31 | 26 |
| wb/GOV_WGI_RL_EST.BR | World Bank (Dateno) | annual | canonical | 1996-12-31 | 2024-12-31 | 26 |
| wb/GOV_WGI_RQ_EST.BR | World Bank (Dateno) | annual | canonical | 1996-12-31 | 2024-12-31 | 26 |
| wb/GOV_WGI_VA_EST.BR | World Bank (Dateno) | annual | canonical | 1996-12-31 | 2024-12-31 | 26 |
| wb/IPTOTSAKD_M.BRA | World Bank (Dateno) | monthly | canonical | 1991-01-31 | 2025-12-31 | 420 |
| wb/JI.EMP.IFRM.ZS.BRA | World Bank (Dateno) | annual | canonical | 1981-12-31 | 2020-12-31 | 36 |
| wb/NE.CON.GOVT.ZS.BR | World Bank (Dateno) | annual | canonical | 1960-12-31 | 2025-12-31 | 66 |
| wb/NE.EXP.GNFS.ZS.BR | World Bank (Dateno) | annual | canonical | 1960-12-31 | 2025-12-31 | 66 |
| wb/NE.GDI.FTOT.ZS.BR | World Bank (Dateno) | annual | canonical | 1970-12-31 | 2025-12-31 | 56 |
| wb/NY.GDP.DEFL.KD.ZG.BR | World Bank (Dateno) | annual | canonical | 1961-12-31 | 2025-12-31 | 65 |
| wb/NY.GDP.MKTP.KD.ZG.BR | World Bank (Dateno) | annual | canonical | 1961-12-31 | 2025-12-31 | 65 |
| wb/NY.GDP.PCAP.KD.ZG.BR | World Bank (Dateno) | annual | canonical | 1961-12-31 | 2025-12-31 | 65 |
| wb/NYGDPMKTPSAKD_Q.BRA | World Bank (Dateno) | quarterly | canonical | 1990-03-31 | 2025-12-31 | 144 |
| wb/PX.REX.REER.BR | World Bank (Dateno) | annual | canonical | 1980-12-31 | 2025-12-31 | 46 |
| wb/REER_M.BRA | World Bank (Dateno) | monthly | canonical | 1987-01-31 | 2024-10-31 | 454 |
| wb/SE.XPD.TOTL.GD.ZS.BR | World Bank (Dateno) | annual | canonical | 1995-12-31 | 2022-12-31 | 25 |
| wb/SH.XPD.GHED.GD.ZS.BR | World Bank (Dateno) | annual | canonical | 2000-12-31 | 2023-12-31 | 24 |
| wb/SI.DST.10TH.10.BR | World Bank (Dateno) | annual | canonical | 1981-12-31 | 2024-12-31 | 40 |
| wb/SI.DST.FRST.20.BR | World Bank (Dateno) | annual | canonical | 1981-12-31 | 2024-12-31 | 40 |
| wb/SI.POV.DDAY.BR | World Bank (Dateno) | annual | canonical | 1981-12-31 | 2024-12-31 | 40 |
| wb/SI.POV.GINI.BR | World Bank (Dateno) | annual | canonical | 1981-12-31 | 2024-12-31 | 40 |
| wb/SI.POV.UMIC.BR | World Bank (Dateno) | annual | canonical | 1981-12-31 | 2024-12-31 | 40 |
| wb/SL.UEM.TOTL.ZS.BR | World Bank (Dateno) | annual | alternate | 1991-12-31 | 2025-12-31 | 35 |
| wb/SP.DYN.IMRT.IN.BR | World Bank (Dateno) | annual | canonical | 1960-12-31 | 2024-12-31 | 65 |
| wb/SP.DYN.LE00.IN.BR | World Bank (Dateno) | annual | canonical | 1960-12-31 | 2024-12-31 | 65 |
| wb/TM.UVI.MRCH.XD.WD.BR | World Bank (Dateno) | annual | canonical | 1980-12-31 | 2024-12-31 | 45 |
| wb/TOT.BRA | World Bank (Dateno) | monthly | canonical | 1991-01-31 | 2025-12-31 | 420 |
| wb/TT.PRI.MRCH.XD.WD.BR | World Bank (Dateno) | annual | canonical | 2005-12-31 | 2024-12-31 | 20 |
| wb/TX.UVI.MRCH.XD.WD.BR | World Bank (Dateno) | annual | canonical | 1980-12-31 | 2024-12-31 | 45 |
| wb/per_sa_allsa.cov_pop_tot.BR | World Bank (Dateno) | annual | canonical | 2006-12-31 | 2022-12-31 | 12 |

Files: `results.json` (all numbers with series_ids and SQL), `metric_table.csv`, `term_table.csv`, `term_table_exact_monthly.csv`, `q0_variance_decomposition.csv`, `robustness_matrix.csv`, `event_study.csv`, `event_study_groups.csv`, `pre_election_2026.csv`, `scenarios.csv`, `debt_grid.csv`, `debt_by_branch.csv`; charts in `charts/` (timeline, forest, robustness_heatmap, event_study, campaign_2026, debt_fan, composites). Charts are light-mode plotly HTML (CDN plotly.js).
