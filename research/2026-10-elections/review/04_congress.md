BRAZIL'S CONGRESS AND THE PRESIDENT, 1987–2027: COMPOSITION, ALIGNMENT, DOMESTIC POLICY AND THE FOREIGN-POLICY LEVER
Study 1 (PART A of plan.md). Warehouse: brazil_macro.duckdb (read-only, natives to 2026-08 monthly / 2026-10-02 daily). Pre-registration: preregistration.txt (2026-10-05T21:07:48Z, written before any panel data or result).
Output folder: /private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/congress/

========================================================================================================
SUMMARY
========================================================================================================
2027 arithmetic (TSE). Chamber: PL 121, ENPP 8.83 (least fragmented since 2002). Blocs: left 124, PL+Novo+Missão 132, centrão 210, MDB/PSDB 47. Senate: PL 28 (record), PL+Novo 31, centrão 24, left 15, MDB/PSDB 10.
- Flávio: PECs pass without MDB (342/308, 55/49). Veto strong: an override needs ≥86 centrão deputies and ≥15/24 senators joining the left.
- Lula IV: PECs need ≥137/210 centrão deputies and 23/24 senators. Veto weak: PL+Novo+MDB+PSDB make 41 senators (dosimetria override, 2026-04-30).

Verdicts (12 dyads):
- G1: mixed. Primary balance, Δdebt, interest: no robust association. GFCF supports N1 (ρ +0.64, n=12; 87% of cells; survives detrending). Net lending: fragile.
- G2 rates: none (cells lean against N1: time trend).
- G3: N2. Follow-rate 75±5, flat. MP conversion (23%, Lula III) and overrides (5%→49%) shifted secularly.
- G4: more reforms under fragmented Chambers (ρ −0.55); list incomplete pre-2015.
- G5: N2. G6: null. G7: relief, from a single episode. G8: ρ 1.0 on n=4. G9: coattails ρ 0.44. G10: no alignment effect. G11: not testable.

Event study: tightening vs loosening votes do not differ (p 0.44–0.94). Largest move: the 2016 impeachment vote (Ibov USD +11.5%, NTN-B −42 bp, p 0.08–0.14).

Budget capture: emendas paid R$11.7bn (2019) → R$43.5bn (2025; 0.34% GDP, 21% of discretionary); LOA 2026 R$61.4bn. GFCF not lower (ρ +0.75); public investment weakly lower (ρ −0.42); yields unrelated.

Foreign policy: amnesty/override = main US link; environmental overrides = EU tail; Reciprocity Law = Lula escalation tail. Treaties ratified (EU, EFTA, Singapore) → 0. Minerals, BRICS: no Congress role.

Scenarios (NTN-B % / debt 2030 % GDP / FX / export modifiers):
- Flávio aligned (high): 5.5–6.8 / 85–95 / +3% to +6%. US-best medium→high; EU-worst low→medium.
- Flávio transactional (medium): 6.5–7.8 / 93–104 / 0 to +3%. US-best →medium-high; EU-worst →low-medium.
- Flávio opposed (low): 7.0–8.5 / 96–107 / −3% to +1%. No modifier.
- Lula aligned (low): 6.5–7.8 / 93–104 / ±2%. US-worst low→low-medium (reciprocity).
- Lula transactional (high): 7.0–8.5 / 98–107 / −4% to 0. EU-worst →medium-high.
- Lula opposed (medium): 7.5–9.5 / 100–112 / −6% to −2%. EU-worst →medium-high; US-best →medium-high (amnesty over the veto).
The commodity state (±$14–22bn) dominates every cell.

Limits: 12 dyads (4–9 with rates); trends; endogeneity; run-off unknown.

Charts: congress/charts/1_seats_enpp_timeline, 2_alignment_scatter, 3_event_study_groups, 4_emendas_investment_ntnb, 5_reform_heatmap, 6_arithmetic_2027, 7_scenario_tornado, 8_robustness_heatmap (.html).

========================================================================================================
1. DATA CONSTRAINTS (plan 0.1–0.5, reproduced first)
========================================================================================================
- Plan 0.1 reproduced:
  - political_terms has 9 rows, ending Lula III 2027-01-01; political_events has 34 rows, the last on 2026-10-04.
  - No Congress or emendas table exists. registry/ is unchanged since b79840b.
  - The warehouse holds no budget, emendas, FPA, coalition or seat series. All of these are external (fenced, G-ids).
- Plan 0.4 coverage reproduced exactly:
  - primary_balance_gdp 2002-11→2026-08; gross_public_debt_gdp 2006-12→2026-08; real_policy_rate 2001-12→2026-09.
  - embi_brazil 2000-01-03→2024-07-30 (stale); gov_real_yield_10y 2015-01-02→2026-10-02.
  - wb/GC.NFN.TOTL.GD.ZS.BR and wb/GC.NLD.TOTL.GD.ZS.BR run 2010→2024; wb/NE.GDI.FTOT.ZS.BR 1970→2025; wb/FR.INR.RISK.BR 1997→2025.
  - wb/FP.CPI.TOTL.ZG.BR, wb/GC.BAL.CASH.GD.ZS.BR and wb/NE.GDI.FPUB.ZS.BR are absent.
- Plan 0.5 event prototypes: all twelve t−1→t+20 Ibovespa-USD moves reproduce to 0.1 pp (anchors() asserts them), and so does NTN-B 3.31→3.88 for 2021-02-24.
- Plan 0.2 seat sums re-verified: 513 / 54 / 81.
  - Chamber: TSE open data (consulta_cand_2026, elected flags) plus Agência Câmara's list of all 513 (G01) match the plan party by party.
  - Senate: TSE per-state results (100% totalised) plus Agência Brasil and Congresso em Foco (G02, G03).
  - Discrepancy noted: English Wikipedia gives PL 29 senators and no unaffiliated senator. It changes none of the 41/49 thresholds' conclusions.

Anchor differences found (noted; none breaks the analysis):
(a) The historical sample is 12 dyads, not 13. The plan's "13 historical" count includes Collor×48 (10.5 months), which its own ≥12-month rule drops. The power statement below is unchanged in spirit, with n = 12.
(b) The dosimetria veto is not pending. Congress overrode it on 2026-04-30: Chamber 318–144, Senate 49–24 (Senado Notícias, G09). It was promulgated as Lei 15.402 on 2026-05-08, and Moraes suspended it on 2026-05-09 (G10). The plan's "veto awaits a joint session" is outdated, so the override was added to the foreign-policy event group.
(c) EFTA is not pending. Mercosur–EFTA was approved by DL 146 of 2026-06-22, promulgated by Decreto 13.126 of 2026-09-23 and in force for Brazil from 2026-10-01. Mercosur–Singapore was approved by DL 147 and Decreto 13.081 (G21). The "EFTA timing ±$0–1bn" modifier is therefore 0.
(d) Fragmentation claims. The Chamber ENPP of 8.83 is the least fragmented since the 2002 election (8.47); 2006 was 9.32. The plan said "since 2006". The Senate ENPP of 6.04 is not the most concentrated since 1988: 1999 was 4.58 and 2003 was 5.84. What is a record is the largest party, PL 28 (G04).
(e) Event dates verified on the Câmara and Senado APIs:
  - Fiscal framework: 2023-05-23, not 05-24.
  - PEC 45 first round: 2023-07-06, not 07-07, which was the second round.
  - Kamikaze first round: 2022-07-12, not 07-13.
(f) focus_selic_12m drops on 2023-01-08 (−3.23) and 2026-01-08 (−1.79), both with placebo p ≈ 0.00. These look like year-start horizon rolls in the Focus series, not news, and are disregarded.

========================================================================================================
2. PANEL AND SOURCES
========================================================================================================
Unit: president × legislature dyad. Annual attribution: the dyad in office on 1 July. 1990 is unattributed because Collor×48 is dropped.
SQL (in-memory DuckDB with the warehouse attached read-only; `leg` built in the same query):
  WITH leg AS (SELECT * FROM (VALUES (48, DATE '1987-02-01', DATE '1991-02-01'), … (58, DATE '2027-02-01', DATE '2031-02-01')) AS t(leg_id, start, "end")),
  dyad AS (SELECT l.leg_id, p.president, p.party, p.lean, greatest(l.start, p.start) AS start, least(l."end", p."end") AS "end"
           FROM leg l JOIN political_terms p ON p.start < l."end" AND p."end" > l.start)
  SELECT row_number() OVER (ORDER BY start) AS dyad_id, *, date_diff('month', start, "end") AS months FROM dyad WHERE date_diff('month', start, "end") >= 12 ORDER BY start;
Dyads (months): Sarney×48 (37), Collor×49 (22), Itamar×49 (25; political_terms starts Itamar at 1992-12-29), FHC×50 (48), FHC×51 (47), Lula×52 (48), Lula×53 (47), Dilma×54 (48), Dilma×55 (15), Temer×55 (32), Bolsonaro×56 (47), Lula×57 (47).

Files (CSV schemas as in plan A2, so they can be loaded into registry/):
- congress_seats.csv: 11 legislatures × chamber × party.
  - Chamber seats at election (Wikipedia/TSE, G26). No source gives seats at inauguration, so seats_basis = election.
  - Senate seats at the start of the legislature, 1995–2027 (Senate API, G27). The 1987 and 1991 Senate compositions are null: not sourceable.
  - Ideology: BLS 0–10 (Zucco–Power, nearest wave) and Bolognesi 2018 (G28).
  - bloc cut-offs: left ≤ 4, right ≥ 6. Centrão narrow and broad flags as in plan A2; old PSD (1987–2003) coded separately.
- congress_legislatures.csv: one row per dyad.
  - Coalition shares come from Figueiredo 2007, which uses seats at the cabinet date, up to 2005 (G19), and are computed from election seats from 2007.
  - Bolsonaro×56 had no formal coalition. Coded as his ministers' parties (PSL+DEM+Novo = 17.3%) and flagged.
  - Also: ENPP, distance, governability, MP, veto and first-round fields.
- congress_annual.csv: years 1987–2026 with the dyad and the emendas block.
- congress_panel.csv: dyad × metric means joined to the alignment variables.
- research/: the raw CSVs from the five research streams, each value with its URL.

Chamber ENPP by legislature start: 1987 2.83, 1991 8.71, 1995 8.14, 1999 7.13, 2003 8.47, 2007 9.32, 2011 10.37, 2015 13.27, 2019 16.41, 2023 9.91, 2027 8.83. These match the literature seeds (2.8, 8.7, 8.2, 7.1, 8.5, 9.3, 10.4, 13.2, 16.5).
Senate ENPP: 1995 6.23, 1999 4.58, 2003 5.84, 2007 6.30, 2011 7.75, 2015 8.01, 2019 11.82, 2023 8.83, 2027 6.04.

Alignment at dyad start (coalition share of Chamber seats / president's party share / ENPP / |president − Chamber| distance, BLS 0–10):
| Dyad | Coalition | President's party | ENPP | Distance |
|---|---|---|---|---|
| Sarney×48 | 0.78 | 0.53 | 2.8 | 1.68 |
| Collor×49 | 0.35 | 0.08 | 8.7 | 2.31 |
| Itamar×49 | 0.60 | — | 8.7 | 0.15 |
| FHC×50 | 0.56 | 0.12 | 8.1 | 0.36 |
| FHC×51 | 0.74 | 0.19 | 7.1 | 0.07 |
| Lula×52 | 0.43 | 0.18 | 8.5 | 2.42 |
| Lula×53 | 0.63 | 0.16 | 9.3 | 2.33 |
| Dilma×54 | 0.64 | 0.17 | 10.4 | 2.28 |
| Dilma×55 | 0.59 | 0.13 | 13.3 | 2.78 |
| Temer×55 | 0.59 | 0.13 | 13.3 | 2.27 |
| Bolsonaro×56 | 0.17* | 0.10 | 16.4 | 3.30 |
| Lula×57 | 0.52 (mid 0.69) | 0.13 | 9.9 | 2.99 |

Hypothetical 58th legislature (2027):
- Lula IV: party share 0.136 in the Chamber and 0.111 in the Senate; distance 3.02.
- Flávio: party share 0.236 in the Chamber and 0.346 in the Senate; distance 1.54.
- Chamber seat-weighted ideology: 5.93, second only to 2019 (6.01) and just above 2023 (5.89); right bloc 65%, left bloc 23%.

========================================================================================================
3. PRE-REGISTRATION (summary; full text in preregistration.txt)
========================================================================================================
The two narratives:
- N1, "Governability": fragmentation and misalignment hurt fiscal outcomes, rates, reforms and investment, and FPA power hurts the environment and EU access.
- N2, "Coalitional presidentialism works / Congress as a fiscal check".

Verdict rule: "supports Nx" requires all three of the following:
1. the baseline sign matches Nx;
2. at least 80% of robustness cells share that sign;
3. the 80% cluster-bootstrap CI excludes 0.

Power statement (verbatim, n corrected): "13 dyads, of which 6–8 have the rate/risk series; with a binary aligned/misaligned split of 6 vs 7, C(13,6) = 1,716 labelings (min p 0.001), but the explanatory variable is continuous and dyads of the same president are not independent; with the 2000+ sample there are 7 dyads. This is an effect-size study with bands; nothing is expected to clear BH at q = 0.10." Actual n = 12 dyads (see 1(a)). The rate and fiscal metrics have 4–9 dyads.

Deviations from the pre-registration, all disclosed:
(i) n = 12.
(ii) The baseline explanatory variable for the verdict is coalition_share_cd_start; the other three main variables are reported alongside.
(iii) Post-hoc additions, labelled as post-hoc: the detrended (partial-on-time) Spearman and the leave-one-dyad-out check.
(iv) The reform list for G4 is incomplete before 2015.
(v) Coalition shares mix two sources: Figueiredo up to 2005, computed from election seats afterwards.

========================================================================================================
4. RESULTS PER HYPOTHESIS
========================================================================================================
SQL for every annual outcome (results.json → sql.annual_panel):
  SELECT series_id, CAST(EXTRACT(year FROM date) AS INT) AS year,
         CASE WHEN any_value(c.agg)='sum' THEN sum(value) WHEN any_value(c.agg)='last' THEN arg_max(value,date) ELSE avg(value) END AS value,
         arg_max(value, date) AS year_end, count(*) AS n_obs, max(date) AS last_obs
  FROM v_observations o JOIN catalog c USING (series_id)
  WHERE date <= current_date AND series_id IN (…) GROUP BY 1,2 ORDER BY 1,2
Dyad statistic: the mean of the annual values attributed to the dyad. Δ debt uses year-end values.
Bootstrap: 5,000 draws, seed 0, over dyads; draws with fewer than 3 distinct x values are discarded. Permutation p: exact for n ≤ 8.
Robustness grid: 2,952 cells. The dimensions are sample (1987+/1995+/2003+), unit (dyad/year), six explanatory variables (one is the Bolognesi distance), attribution (contemporaneous/lag-1/drop-first-year) and adjustment (raw/ToT/ToT+lean). Two centrão codings are run separately. Output: robustness_matrix.csv, charts/8.

Dyad means used (series, source, last date):
- primary_balance_gdp: Derived/BCB, 2026-08.
- gross_public_debt_gdp: BCB SGS, 2026-08.
- interest_bill_gdp: Derived, 2026-08.
- wb/GC.NLD.TOTL.GD.ZS.BR: WB, 2024-12-31.
- wb/NE.GDI.FTOT.ZS.BR: WB, 2025-12-31.
- real_policy_rate: Derived, 2026-09.
- embi_brazil: IPEAData, 2024-07-30.
- gov_real_yield_10y: Tesouro Direto, 2026-10-02.
- wb/FR.INR.RISK.BR: WB, 2025-12-31.

| Dyad | pb | Δ debt | interest | NLD | GFCF | real rate | EMBI | NTN-B | risk premium |
|---|---|---|---|---|---|---|---|---|---|
| Sarney×48 | | | | | 24.8 | | | | |
| Collor×49 | | | | | 18.3 | | | | |
| Itamar×49 | | | | | 20.0 | | | | |
| FHC×50 | | | | | 19.2 | | | | 55.6 |
| FHC×51 | | | | | 17.9 | 13.2 | 994 | | 43.4 |
| Lula×52 | 3.46 | | 7.25 | | 17.1 | 12.8 | 502 | | 39.0 |
| Lula×53 | 2.78 | −1.65 | 5.36 | −2.48 | 19.3 | 6.7 | 247 | | 32.5 |
| Dilma×54 | 1.57 | +1.13 | 4.98 | −3.20 | 20.5 | 4.2 | 203 | | 24.9 |
| Dilma×55 | −1.86 | +9.22 | 8.36 | −8.03 | 17.8 | 7.2 | 346 | 6.67 | 29.8 |
| Temer×55 | −1.90 | +3.26 | 6.00 | −7.19 | 15.1 | 5.6 | 307 | 5.52 | 36.1 |
| Bolsonaro×56 | −2.03 | −0.90 | 4.97 | −6.69 | 16.9 | 2.3 | 292 | 4.16 | 26.7 |
| Lula×57 (incl. 2026 YTD) | −0.93 | +2.79 | 7.85 | −6.28 | 16.8 | 9.0 | 228 (to 2024) | 6.73 | 30.4 |

G1 — fragmentation → fiscal.
Baseline: slope on coalition_share_cd_start, ρ, 80% CI, permutation p, share of N1-sign cells.
- Primary balance (n=7): slope +3.7 pp per unit share, ρ +0.32, CI [−12.2, 9.6], p 0.65, N1 cells 86% → no robust association.
  - With the president's party share or ENPP, ρ is ±0.95, and that survives detrending (partial ρ 0.88 / −0.96, post-hoc).
  - Read this as the PT-heavy Lula I–II years with commodity-boom surpluses. With n = 7 it cannot be separated from the regime (fiscal rule, ToT); the ToT-adjusted slope is unchanged at 4.6.
- Δ gross debt (n=6): ρ −0.09, CI [−45, 14], N1 cells 45% → no robust association.
- Interest bill (n=7): ρ 0.00, N1 cells 42% → no robust association.
- GG net lending (n=6): ρ +0.43, CI [0.9, 39.5], N1 cells 82% → "supports N1" by the rule. But the permutation p is 0.59, leave-one-out ρ ranges 0.10–0.60, and detrended ρ is 0.12. Fragile.
- GFCF % GDP (n=12, 1987–2025): ρ +0.64, slope +7.6 pp of GDP per unit coalition share, CI [2.1, 14.6], p 0.096, N1 cells 87%. The ToT-adjusted slope is 6.6 [2.7, 13.8]. Detrended partial ρ is 0.61 and leave-one-out ρ is 0.54–0.75 → SUPPORTS N1. This is the most robust Congress-alignment association in the study. It is not causal: Sarney×48, with 78% coalition share, had 24.8% GFCF in a pre-stabilisation economy.
G1 verdict: mixed. Investment supports N1. The flow fiscal metrics show no robust association, which is consistent with N2.

G2 — alignment → real rate and risk premium.
- Real policy rate (n=8): ρ +0.24, N1 cells 17%.
- EMBI (n=8, to 2024-07): ρ +0.02, N1 cells 26%.
- NTN-B (n=4): ρ +0.40, N1 cells 18%.
- Lending risk premium (n=9): ρ +0.03, N1 cells 12%.
None meets the CI rule → no robust association (consistent with N2). The grid leans against N1: more fragmented and less aligned dyads had lower rates. That is the secular fall in rates since 2000 coinciding with rising ENPP, since ENPP correlates with time at ρ +0.75. After partialling out time, the ENPP–real-rate ρ is −0.75, so the sign persists but rests on n = 8. BH q for the primary family is ≥ 0.71 everywhere; Holm is the same.

G3 — alignment → governability.
- Basômetro follow-rate (G13; low-confidence source), 6 dyads, Lula I to Bolsonaro: 77, 79, 75, 65, 76, 76. Mean 74.7, sd 4.9. ρ with coalition share −0.20, with ENPP −0.54 (perm p 0.57).
  - This is N2's "≈75% regardless of fragmentation". The exception is Dilma II at 65, a collapse in a dyad whose coalition was 59% at start and 19% at mid-dyad.
- Arko's follow-rate for Lula III, 46.4–46.5% (G14), uses a different definition and is not pooled.
- MP conversion (G15): pre-2019 mean 80.6%, Bolsonaro 68.3%, Lula III 23% (38 of 192).
  - ρ with coalition share +0.26 (n=8, p 0.64).
  - The Lula III collapse came with a 52–69% coalition, so it is not alignment. It is Congress declining to process MPs: a regime change after 2019.
- Veto overrides as a share of vetoes appreciated (G16): Dilma 5%, Temer 15%, Bolsonaro 44%, Lula III 49%. A monotone secular rise in congressional assertiveness, independent of alignment.
- Executive win-rate (Limongi, G20): only Collor 65 and Itamar 66, plus the 1988–2006 average of 70.7. Not estimable.
G3 verdict: supports N2 on the success rate. The real change is secular: Congress asserting itself (MPs, vetoes, emendas).

G4 — alignment → reform output (reform_table.csv; economic ECs and major laws from the Câmara/Senado APIs, STF decisions excluded).
| Dyad | Reforms (tightening / loosening / institutional) | Per year |
|---|---|---|
| FHC×50 | 3 (2/0/1) | 0.75 |
| FHC×51 | 1 | 0.26 |
| Lula×52 | 2 | 0.50 |
| Dilma×55 | 1 (loosening) | 0.80 |
| Temer×55 | 3 (1/1/1) | 1.13 |
| Bolsonaro×56 | 9 (2/6/1) | 2.30 |
| Lula×57 | 4 (0/0/4) | 1.02 |
| Others | 0 | 0 |
Reforms per year against coalition share: ρ −0.55 (perm p 0.03); against ENPP: ρ +0.55 (p 0.006).
The N2 counter-examples are confirmed: the spending cap (Temer, 59% coalition), the pension reform (Bolsonaro, no formal coalition, ENPP 16.4) and the 2023 framework and tax reform (Lula III, 52%) all passed under weak or misaligned presidents. Bolsonaro×56's count is dominated by loosening ECs written by Congress (precatórios, Kamikaze, EC 100/105 impositivas).
Caveat: the 1987–2014 list is incomplete (for example, the 1995 privatisation ECs and EC 3/1993 are missing), so the negative ρ is partly a list-completeness artefact.
G4 verdict: no support for N1. Descriptively the pattern is the reverse: the most reforms passed in the most fragmented Chamber.

G5 — budget capture: see section 6. Verdict: N2 on GFCF and yields; weakly N1 on public net investment.

G6 — event study: see section 5. Verdict: null (consistent with N2: priced earlier or swamped).

G7 — impeachment and institutional shocks.
- 2016-04-17 Chamber impeachment vote, [−5,+5]: Ibovespa USD +11.5% (placebo p 0.14), BRL +5.3% (p 0.12), NTN-B −42 bp (p 0.08), EMBI −49 bp (p 0.18).
- Senate admission (2016-05-12) and removal (2016-08-31): ≈ 0 (p ≥ 0.23).
- 8 January 2023: Ibovespa +1.4%, NTN-B −4.5 bp, ≈ 0.
- 1992-09-29 (monthly, descriptive): wb/REER_M.BRA went 77.5 (Aug) → 78.3 (Sep) → 82.0 (Dec 1992). That is +4.7% real appreciation into Itamar's start, under high inflation. wb/DPANUSSPB_M.BRA keeps depreciating at the inflation pace.
Verdict: relief at resolution, with the move concentrated at the decisive Chamber vote. It rests on one episode, as N2 warned.

G8 — FPA power → forest loss → EU access.
- FPA share of the Chamber (G18): 37% (2011), 45% (2015), 44% (2019), 58% (2023).
- Primary forest loss per legislature (wb/AG.LND.PFLS.HA.BR, WB, last 2025-12-31): 0.87, 1.79, 1.60 and 1.86 Mha/yr.
- Spearman ρ = 1.00 on n = 4. One-sided exact p is 1/24 ≈ 0.04 at best, with no controls. The 2023–25 figure includes the 2024 fire year, which is why PFLS (unlike PRODES clear-cutting) did not fall under Lula III.
- exports_to_eu (ComexStat, to 2026-08): 2014 $36.2bn → 2022 $50.9bn → 2025 $49.8bn. No observable penalty, as in the exports study.
Verdict: descriptively consistent with N1 on forest loss, n = 4. No EU trade effect yet.

G9 — coattails. First-round vote share against the president's party Chamber share: ρ +0.44 (n=9). 2026: Flávio 47.0% → PL 23.6%; Lula 45.2% → PT 13.6%. Coattails are moderate, so composition is partly endogenous to the presidential race, and more so for the right in 2026.

G10 — treaty ratification lag, signature → decreto legislativo (G22):
| Treaty | Dyad | Months |
|---|---|---|
| Israel | Lula×53 | 24 |
| Egypt | Lula×53 | 62 |
| Palestine | Dilma×54 | 81 |
| Chile | Temer×55 | 35 |
| US ATEC | Bolsonaro×56 | 13 |
| Singapore | Lula×57 | 30.5 |
| EFTA | Lula×57 | 9.2 |
| EU | Lula×57 | 1.9 |
Verdict: no alignment pattern. Lags track agro or strategic gains and executive priority. The three 2026 approvals (EU unanimous; EFTA and Singapore both on 2026-06-22) came under a Congress that rejected 77% of Lula's decided MPs. That is N2: trade deals with agro gains pass regardless.

G11 — lean × alignment. Aligned dyads (coalition ≥ 50%) hold 4 left and 1–3 right; misaligned dyads hold 1 left (Lula×52) and 1–2 right (Bolsonaro×56, Collor×49).
| Metric | L−R, aligned | L−R, misaligned |
|---|---|---|
| GDP growth | −0.02 | +2.68 |
| Primary balance | +2.29 | +5.48 |
| Real rate | −2.64 | +10.49 |
| Unemployment | −2.68 | +0.87 |
| Real minimum-wage growth | +1.94 | +6.21 |
Verdict: not testable. Every misaligned contrast is Lula I against Bolsonaro or Collor. The direction (bigger lean gaps when misaligned) is the opposite of N1 but carries no information.

========================================================================================================
5. EVENT STUDY (event_study.csv; charts/3)
========================================================================================================
Design: constant-mean abnormal change; estimation window [−250,−121]; placebo of 2,000 random dates at least 90 days from any event (seed 0); Brent market-model variant for Ibovespa and BRL; exact permutation of G1 vs G2 labels across events. Primary event = first Chamber floor vote; secondary = promulgation.
SQL: SELECT series_id, date, value FROM v_observations WHERE date <= current_date AND series_id IN ('ibovespa_usd','brl_usd','embi_brazil','gov_real_yield_10y','focus_selic_12m','brent_usd') ORDER BY series_id, date
Series: ibovespa_usd (B3/derived, last 2026-10-01); brl_usd (BCB, 2026-10-02); embi_brazil (IPEAData, 2024-07-30); gov_real_yield_10y (Tesouro Direto, 2026-10-02); focus_selic_12m (BCB Focus, 2026-09-25).

Headline window [−5,+5], primary stage. G1 = 6 tightening/institutional Chamber votes; G2 = 4 Congress-led loosening votes.
| Series | G1 mean | G2 mean | Difference | Permutation p | Placebo sd |
|---|---|---|---|---|---|
| Ibovespa USD | +1.5% | +2.4% | −0.8 | 0.77 | 8.4 |
| BRL (+ = stronger) | +0.16% | +0.26% | −0.1 | 0.94 | 3.6 |
| NTN-B | −0.8 bp | −10.5 bp | +9.7 | 0.44 | 26.5 |
| EMBI | −7 bp | −14 bp | | 0.46 | |
| Focus Selic 12m | +0.00 pp | +0.36 pp | | 0.10 | |
In [−1,+1], Focus Selic 12m is +0.02 vs +0.20 (p 0.029), the only p < 0.05 in the family.
Secondary stage: EMBI [−20,+20] is +8 bp for G1 vs −40 bp for G2 (p 0.012, which is the permutation floor). Promulgations of tightening reforms coincided with wider spreads, opposite to N1. Two of those dates coincide with global moves: Nov 2019 and Feb 2021, the latter also the Petrobras CEO sacking.
No single reform vote has a placebo p below 0.10 on Ibovespa, BRL or NTN-B. The smallest are the 2021-02-24 BCB-autonomy sanction (NTN-B +47 bp, p 0.06; confounded) and the 2017-07-13 labour-law sanction (NTN-B −37 bp, p 0.12).

Foreign-policy votes, [−5,+5], placebo p:
- 2025-04-01 reciprocity approval: Ibovespa −9.0% (p 0.22). This is the "Liberation Day" week, a confound.
- 2025-12-10 dosimetria Chamber passage: Ibovespa −6.8%, NTN-B +14 bp (p ≥ 0.35).
- 2026-03-04 EU–Mercosur Senate approval: Ibovespa −5.6%, NTN-B +17 bp (p ≥ 0.43).
- 2026-04-30 veto override: Ibovespa −4.6%, NTN-B +16 bp (p ≥ 0.48).
None is distinguishable from noise.

Verdict G6: null. Markets do not reward or punish Congress's floor votes on average. Reforms are priced at committee stage or swamped by global news, as N2 expected.

========================================================================================================
6. BUDGET CAPTURE (G5; charts/4)
========================================================================================================
Emendas paid, cash including restos a pagar (Portal da Transparência full file, extract 2026-10-01; G12), as R$bn / % of GDP / % of Executive discretionary spending:
| Year | R$bn | % GDP | % discretionary |
|---|---|---|---|
| 2016 | 16.2 | 0.26 | 11.4 |
| 2017 | 10.2 | 0.15 | 8.7 |
| 2018 | 12.9 | 0.18 | 9.9 |
| 2019 | 11.7 | 0.16 | 7.1 |
| 2020 | 23.7 | 0.31 | 21.9 |
| 2021 | 25.2 | 0.28 | 20.3 |
| 2022 | 27.9 | 0.28 | 18.4 |
| 2023 | 32.9 | 0.30 | 17.9 |
| 2024 | 39.3 | 0.33 | 21.4 |
| 2025 | 43.5 | 0.34 | 21.2 |
| 2026 (Jan–Sep) | 35.1 | — | — |
- 2014–15 are missing because the Portal's payment file is incomplete for those years.
- Breakdown: impositivas (RP6+RP7) went from 5.7 (2016) to 34.0 (2025); RP9 was 8.5 / 10.2 / 11.5 in 2020–22, then ended (STF ADPF 854, Dec 2022); Pix rose from 0.6 (2020) to 6.9 (2025).
- Authorised (LOA dotação): 2024 44.6, 2025 48.5, 2026 61.4 (49.9 impositivas). 2026 = 0.48% of 2025 nominal GDP (R$12,739bn: gdp_nominal_12m_brl, BCB, Dec 2025).
- SIOP's "paid within year" figure for 2025 is R$31.5bn (G11). The Portal's within-year figure is 30.6, consistent.
- Denominator: gdp_nominal_12m_brl, BCB SGS, December value, last 2026-08-01. SQL: results.json sql.gdp_dec.

Spearman, 2016–2025 (n = 9–10):
| Outcome (series, last date) | vs emendas % GDP | vs share of discretionary |
|---|---|---|
| wb/GC.NFN.TOTL.GD.ZS.BR, public net investment (→2024) | −0.20 | −0.42 |
| wb/NE.GDI.FTOT.ZS.BR, GFCF (→2025) | +0.68 | +0.75 |
| gov_real_yield_10y, NTN-B (→2026-10-02) | +0.36 | +0.15 |
| r_minus_g, r−g (→2026-08) | −0.04 | −0.04 |
Rule changes are marked on the chart: EC 86/2015 (individual impositivas), EC 100/2019 (bancada), EC 105/2019 (Pix), ADPF 854 (RP9), Dino orders Aug 2024, LC 210/2024.

Reading:
- Capture is real and large. Emendas rose 3.7× in nominal terms (about 2.7× in real terms) from 2019 to 2025, to about a fifth of the discretionary envelope. That is the rigidity N1 describes: the fiscal-framework space is pre-committed. In the scenarios, emendas rigidity is costed at 0.3–0.5 pp/yr of primary-balance flexibility.
- Aggregate GFCF did not fall, and public net investment fell only weakly. Yields track r−g and the global cycle, not emendas.
Verdict: N2 on investment and yields. Rigidity is a governability and fiscal-flexibility cost, not yet a market-priced one. n = 10, descriptive.

========================================================================================================
7. FOREIGN-POLICY LEVER TABLE (plan A5, updated with verified facts; modifiers in exports_cell_modifiers.csv)
========================================================================================================
| Lever (basis) | Status, Oct 2026 | Exports channel | Congress modifier |
|---|---|---|---|
| Trade-agreement ratification (CF 49 I / 84 VIII) | EU DL 14/2026, in force 2026-05-01 (G05, C07). EFTA DL 146/2026, in force 2026-10-01; Singapore DL 147/2026 (G21). | C6, C9, C10 | 0. The pipeline is ratified, and Congress cannot undo provisional application. The remaining EU risk is EU-side (EP/CJEU, C05, C06). |
| Reciprocity Law 15.122/2025 (Camex decides; G06) | Unused | C1 | Lula IV + aligned Congress: the US-worst cell moves from low to low-medium (escalation tail −$2 to −5bn). Opposed Congress: retaliation becomes costlier, so the tail falls. Flávio: dormant. |
| Senate: ambassadors, external credit (CF 52 IV–VIII) | US ambassador slot vacant (A38) | C5, C14 | Lula IV + opposed Senate: delays to NDB/CAF loans and confirmations. Rest-best cell moves from medium to low-medium; ≈ $0 exports. |
| Environmental law; veto override 257/41 | Licensing law: 52 of 63 vetoes overridden (G17/C30). EUDR applies from 2026-12-30 (C23). Soy moratorium upheld by the STF (C33). | C7, C8 | Flávio-worst EU cell (−$2 to −5bn): low → medium if aligned, low → low-medium if transactional. Lula-worst EU cell: medium → medium-high if transactional or opposed (rollback path through overrides). |
| Critical minerals (Law 15.506; Cimce under the Presidency; B51) | In force Sep 2026 | C13 | Congress's role is spent. Flávio: +$0.5 to +2bn strategic in every alignment. Lula: sovereignty-first. |
| US sanctions / amnesty (veto override; Amin PL) | Dosimetria override done 2026-04-30 (G09); Lei 15.402 suspended by Moraes 2026-05-09 (G10). Magnitsky lifted 2025-12-12, citing the Chamber vote (A11); re-imposition discussed Aug 2026 (A12). Flávio pledges amnesty in the transition (A32). | C1, C2 | THE MAIN CONGRESS → US LINK. Flávio aligned: US-best moves medium → high; transactional: medium → medium-high. The $ cell stays +2 to +6bn, because Section 301 is a trade finding (A21). Lula IV opposed: Congress can pass the broad amnesty over a veto, so US-best moves medium → medium-high (+$0–0.5bn); the 301 layer stays (A25). Amnesty brings an STF-conflict premium (G10). |
| BRICS/NDB, Pix/UnionPay, FTO designation | Executive (A29, B24, A27) | C4, C5, C14 | No change from Congress; flag only for a PCC/CV terror-designation bill (correspondent banking). |
| Budget capture → fiscal → BRL/yields | LOA 2026 R$61.4bn (G11) | C14 | Small for export volumes (exports study 4.2); large for the risk premium (scenario rates below). |

========================================================================================================
8. SCENARIO MATRIX (scenario_matrix.csv; charts/7)
========================================================================================================
Run-off winner (25 Oct, unknown: last polls within the margin, A50; first round Flávio 47.03 vs Lula 45.16, A49) × the actual 2026 Congress × centrão alignment. The Feb-2027 presidencies are a sub-branch (G24): PL launched Marinho for the Senate and rules out Alcolumbre; Sóstenes is cited for the Chamber. A PL chair under Lula IV shifts probability from transactional to opposed; under Flávio it raises the odds of the aligned case.
Probabilities are conditional on the winner and qualitative. Ranges only.
- NTN-B: 2015–26 band 2.45–7.8; now 7.52 (2026-10-02). Pair with focus_selic_12m 12.0 (2026-09-25) and real_policy_rate 9.27 (2026-09).
- Debt: read from politics/debt_grid.csv, starting from 82.86 in 2026.

FLÁVIO × ALIGNED (probability high; analogue Temer×55, Bolsonaro 2021–22)
- Governability: win-rate 75–85, MP conversion 60–80.
- PECs feasible: Chamber 342 vs 308, Senate 55 (+10 MDB/PSDB) vs 49.
- Veto strong: an override needs at least 86 centrão deputies and 15 of 24 centrão senators with the entire left and MDB/PSDB.
- Fiscal: primary balance +0.5 to +2.0 by 2029. Debt 2030 85–95 (grid: r−g 2, pb +1 → 85.1; r−g 6, pb +2 → 94.3). r−g 2 to 4.
- Rates and FX: NTN-B 5.5–6.8; FX +3% to +6% (C61 adjustment case; C60 first-round reaction BRL +4%).
- Reform odds: framework revision high, PEC 65/2023 (BCB) high, administrative PEC medium-high.
- Exports cells: US-best medium → high (amnesty); US-worst medium → low-medium; EU-worst low → medium (−$2 to −5bn); Mercosur-worst low → low-medium (CET changes need Congress); China unchanged.

FLÁVIO × TRANSACTIONAL (medium; Bolsonaro 2019–20)
- Governability: win-rate 60–72, MP conversion 25–50. PECs feasible at a price; veto strong.
- Fiscal: primary balance −0.5 to +0.5; debt 93–104 (grid 91.7–103.0); r−g 4–6.
- Rates and FX: NTN-B 6.5–7.8; FX 0 to +3%.
- Exports cells: US-best medium → medium-high; EU-worst low → low-medium.

FLÁVIO × OPPOSED (low)
- Governability: win-rate 45–60, MP conversion 10–30. PECs blocked: the centrão (210) holds the 206-seat blocking minority.
- Veto moderate: an override needs at least 86 of 210 centrão deputies with the whole left, MDB and PSDB.
- Fiscal: primary balance −1.0 to 0 (rule-derived); debt 96–107; r−g 4–6.
- Rates and FX: NTN-B 7.0–8.5 (extrapolated); FX −3% to +1%.
- Exports cells: unchanged from the exports study (amnesty used as leverage).

LULA IV × ALIGNED (low)
- Governability: win-rate 75–85, MP conversion 60–80. PECs only with a near-unanimous centrão: 137 of 210 deputies and 23 of 24 senators. Veto moderate.
- Fiscal: primary balance −0.5 to +0.5; debt 93–104. Rates and FX: NTN-B 6.5–7.8; FX −2% to +2%.
- Exports cells: US-worst low → low-medium (the Reciprocity Law becomes usable).

LULA IV × TRANSACTIONAL (high; the Lula III pattern)
- Governability: win-rate 60–72, MP conversion 25–50 (Lula III actual: 23%). PECs hard.
- Veto weak: PL+Novo+Missão 132 + centrão 210 = 342 ≥ 257; Senate PL+Novo+MDB+PSDB = 41 without the centrão.
- Fiscal: primary balance −1.0 to 0 (emendas rigidity +0.3–0.5 pp/yr); debt 98–107 (grid 95.9–107.4); r−g 4–6.
- Rates and FX: NTN-B 7.0–8.5; FX −4% to 0.
- Exports cells: EU-worst medium → medium-high (override rollback path); US-best +$0–0.5bn (override already done).

LULA IV × OPPOSED (medium; Dilma×55)
- Governability: win-rate 45–60, MP conversion 10–30. PECs infeasible except Congress's own (emendas, amnesty, security). Veto very weak.
- Fiscal: primary balance −1.5 to −0.5, plus overrides on spending bills. Debt 100–112; the upper end extrapolates below the grid's pb = −1 (r−g 6, pb −1 → 107.4). r−g 5–7.
- Rates and FX: NTN-B 7.5–9.5; FX −6% to −2%.
- Exports cells: US-best medium → medium-high (amnesty over the veto); EU-worst medium → medium-high; Rest-best medium → low-medium (Senate credit delays).

Every cell: the commodity and ToT state (±10% ToT ≈ ±$14–22bn/yr of exports, from the exports overlay) outweighs every Congress modifier. Congress shifts probabilities in the US and EU tails; it does not move the central export dollar values.
Governability, fiscal and rate ranges follow the plan's pre-set rules. Cells the plan did not specify (Flávio opposed; Lula aligned) use the same rule and are labelled "rule-derived".

========================================================================================================
9. HONEST LIMITS (verbatim from the plan, n corrected)
========================================================================================================
- 13 dyads (12 after the ≥12-month rule).
- Rate and risk metrics only from 2000 (7 dyads; NTN-B 4).
- Congress composition is endogenous to presidential coattails (G9, ρ 0.44) and to the same ToT cycle.
- No counterfactual.
- Success-rate definitions differ across sources (Basômetro follow-rate, Arko follow-rate, Limongi win-rate); they were never pooled. The Basômetro figures rest on a low-confidence excerpt (G13).
- The 2026 Congress is a structural break: the least fragmented Chamber since 2002 and PL 28 of 81 in the Senate. There is no historical analogue of a single right-wing party this large.
- The run-off is unknown.
- External facts are fenced.
Additional limits:
- Fragmentation, alignment, rates and fiscal outcomes all trend over time (ENPP vs time ρ +0.75), so dyad associations are trend-contaminated. The post-hoc detrending helps only partly.
- Coalition shares mix Figueiredo's cabinet-date seats (to 2005) with election-seat computations (2007+).
- The Bolsonaro "coalition" is a coding choice (17%); GFCF survives dropping it (leave-one-out ρ 0.61).
- Seats are at election, not inauguration: party switching is ignored (1990s migrations; PSL 2019).
- The Senate is missing for 1987 and 1991.
- The Bolognesi scores are a single 2018 round applied to all legislatures.
- The reform list is incomplete before 2015.
- Emendas 2014–15 are missing, and 2016 is high (R$16.2bn) on the cash basis.
- FPA has n = 4.
- EMBI is stale after 2024-07-30.

========================================================================================================
CHARTS
========================================================================================================
1 /private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/congress/charts/1_seats_enpp_timeline.html
2 …/congress/charts/2_alignment_scatter.html
3 …/congress/charts/3_event_study_groups.html
4 …/congress/charts/4_emendas_investment_ntnb.html
5 …/congress/charts/5_reform_heatmap.html
6 …/congress/charts/6_arithmetic_2027.html
7 …/congress/charts/7_scenario_tornado.html
8 …/congress/charts/8_robustness_heatmap.html

Future work: load congress_seats.csv, congress_legislatures.csv and congress_annual.csv into registry/ (pipeline.py next to political_terms), with a v_by_legislature view keyed on leg_id; ingest the Portal emendas file and the RTN discretionary series natively; extend the reform list for 1988–2014 from the Planalto EC table; obtain CEBRAP BDL win-rates for 2007–2022.

========================================================================================================
APPENDIX A — SERIES USED (series_id · source · last observation)
========================================================================================================
- primary_balance_gdp · Derived (BCB) · 2026-08-01
- gross_public_debt_gdp · BCB SGS · 2026-08-01
- net_public_debt_gdp · BCB SGS · 2026-08-01
- interest_bill_gdp · Derived · 2026-08-01
- r_minus_g · Derived · 2026-08-01
- real_policy_rate · Derived · 2026-09-01
- embi_brazil · IPEAData · 2024-07-30
- gov_real_yield_10y · Tesouro Direto · 2026-10-02
- focus_selic_12m · BCB Focus · 2026-09-25
- ibovespa_usd · B3/derived · 2026-10-01
- brl_usd · BCB · 2026-10-02
- brent_usd · IPEAData · 2026-09-29
- gdp_nominal_12m_brl · BCB SGS · 2026-08-01
- exports_to_eu · ComexStat · 2026-08-01
- WB, last 2024-12-31: wb/GC.NLD.TOTL.GD.ZS.BR, wb/GC.NFN.TOTL.GD.ZS.BR
- WB, last 2025-12-31: wb/NE.GDI.FTOT.ZS.BR, wb/FR.INR.RISK.BR, wb/AG.LND.PFLS.HA.BR, wb/NY.GDP.MKTP.KD.ZG.BR, wb/SL.UEM.TOTL.ZS.BR, wb/FP.CPI.TOTL.BR, wb/DPANUSSPB_M.BRA
- WB, other: wb/REER_M.BRA (2024-10-31); wb/TT.PRI.MRCH.XD.WD.BR and TX/TM unit-value indices (2024); wb/TOT.BRA (2025-12-31)
- ilostat/EAR_INEE_NOC_NB.BRA · ILO · 2024-12-31
Every dyad mean and annual value used is in results.json → numbers (value, series_id, source, last_date, sql).

========================================================================================================
APPENDIX B — EXTERNAL FACTS (fenced; external_facts.csv, 55 rows)
========================================================================================================
G01–G29 are new; reused unchanged from the exports study: A11 A12 A21 A25 A26 A27 A29 A32 A38 A49 A50 A51 B24 B51 C05 C06 C07 C23 C24 C25 C30 C32 C33 C60 C61 C63.
Load-bearing facts with two sources: G01 (TSE + Agência Câmara), G02 (TSE + Congresso em Foco), G03 (Agência Brasil + CNN), G05 (Poder360 + Planalto), G06 (Migalhas + Câmara), G09 (Senado + Wikipedia), G21 (two Planalto decrees).
Single-source or low confidence: G10 (Wikipedia citing g1), G13 (Basômetro excerpt, low), G16, G18.
None of these numbers enters warehouse computations except as explanatory variables, and each carries its URL.
