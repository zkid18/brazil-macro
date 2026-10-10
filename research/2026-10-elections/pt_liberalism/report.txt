IS LULA'S PT AS LEFT AS PEOPLE THINK? A REGIME-LEVEL ECONOMIC-LIBERALISM STUDY, 1995-2026
Executed 2026-10-05 from plan.md (pre-registered 2026-10-05T21:08:22Z, preregistration.txt). Warehouse: brazil_macro.duckdb (read-only); data end 2026-08 (monthly) / 2026-10-03 (Selic).

=====================================================================
SUMMARY
=====================================================================
Verdict. On realised policy, PT governments were not less economically liberal than non-PT ones; on average they were slightly more liberal. ELI PT minus non-PT: +0.26 z (80% CI +0.05/+0.46; perm p 0.26, floor 0.029; positive in 94% of 384 cells). Foreign policy is where they differ: FP +0.87 z (+0.57/+1.28; p 0.024). The user's hypothesis broadly holds; its "left shows in credit" detail does not.

Hypotheses: H0 rhetoric lefter than action, supported. H1 fiscal/monetary not less liberal, supported. H2 NME outlier, indeterminate (leaning yes). H3 Lula III looser fiscal but tighter monetary than Palocci, supported. H4 left in credit and social, not supported. H5 trade similar, indeterminate (leaning yes). H6 FP diverges more, partly supported. H7 Fraser/Heritage agree, refuted.

Pillars (PT minus non-PT, z): fiscal +0.56, monetary +0.12, credit +0.50, trade -0.20, SOE -0.45, external +1.25, social +0.45.

Scorecard (a fiscal / b monetary / c credit / d trade / e SOE / f social / g external / ELI):
FHC I -0.25/na/-1.11/-0.07/+0.75/-0.52/na/-0.17
FHC II -0.31/-0.38/-0.01/-0.25/+0.45/+0.31/-0.04/-0.09
Palocci +0.85/+0.05/+0.31/+0.41/+0.44/+0.03/+0.60/+0.44
Mantega +0.36/+0.31/+0.51/+0.21/-0.17/+0.41/+1.35/+0.43
NME +0.28/-0.50/-0.36/-0.70/-0.45/+0.04/+0.49/-0.21
Levy* -0.57/-0.54/-0.95/-0.50/+0.89/-1.02/-0.68/-0.39
Temer -0.39/+0.28/-0.55/+0.59/+0.61/-0.33/-0.55/0.00
Bolsonaro -0.18/+0.09/+0.55/+0.30/-0.68/-0.22/-0.73/-0.11
Lula III -0.37/+0.60/+0.43/-0.13/-0.51/+0.57/na/0.00
(*16 months; excluded by the coverage rule)

Lula I to III. Fiscal (a) fell from +0.85 to -0.37: primary balance +3.6 to -0.9% of GDP; debt went from falling 2.4 to rising 3.1 pts/yr. Monetary (b) rose from +0.05 to +0.60: real rate from neutral to 4.1 pp above it; Selic from 2.1 pp below a Taylor rule to 2.1 pp above. That tightness came from the autonomous BCB, which Lula attacked; the government-stance code fell from 2.0 to 1.5.

Where the left shows: redistribution (minimum wage, Bolsa Família); SOE intervention (administered prices, Petrobras); BNDES flows (C2 -1.06); local content (-1.87); anti-dumping (-0.90); foreign policy.

2-D trajectory. Economics is compressed (ELI -0.4 to +0.45); FP spans -1.25 to +0.86. Lula I-II sit top-right (liberal and progressive). NME moves left. Bolsonaro is the FP floor. Lula III is top on FP and middling on economics, nearest Lula-Mantega.

Caveats: only 8 eligible regimes, and nothing clears BH. Same-president dependence. Lagged credit and debt outcomes. Commodity boom. Single-coder coded cells. S1 uses a fallback and S3 is missing.

Charts: scratchpad/pt_liberalism/charts/1_subindex_timeline.html, 2_trajectory_2d.html, 3_regime_scorecard.html, 4_rhetoric_vs_action.html, 5_external_crosscheck.html, 6_robustness_heatmap.html, 7_components_small_multiples.html.

=====================================================================
1. VERDICT TABLE (decision rule from plan section 4)
=====================================================================
Generic rule: "supported" means all three of the following; "refuted" is the mirror; otherwise "indeterminate".
- the prediction holds at the point estimate
- the 80% two-stage cluster-bootstrap CI is on the predicted side
- at least 80% of robustness cells share the prediction
Adaptation for threshold and equivalence hypotheses (H1, H5, H6): the CI condition is applied to the stated margin. H1: lower 80% bound above -0.5. H5: 80% CI inside +/-0.5 (TOST). H6: lower 80% bound of |dFP|-|dELI| above +0.5. This adaptation is my operationalisation; the generic rule does not fit one-sided or equivalence claims literally.

| H | User prediction | Result | Cells meeting prediction | Verdict |
|---|---|---|---|---|
| H0 | rho(rhetoric, ELI) < 0.5; PT rhetoric z < PT action z | rho = 0.18 (perm p 0.49, n = 18 programmes); PT rhetoric z -0.63 vs action z +0.44 (gap -1.07); non-PT rhetoric +0.51 vs action -0.35 | n/a | SUPPORTED (single-coder dictionary) |
| H1 | dA, dB >= -0.3 | dA +0.56 [80%: +0.21, +0.91]; dB +0.12 [-0.28, +0.53]. ToT-adjusted +0.61 / +0.07; ToT+start +0.53 / -0.03 | 100% (competing view, both <= -0.5: 0%) | SUPPORTED |
| H2 | R5 lowest PT ELI, >1 SD below PT median; ex-R5 dELI >= -0.3 | R5 is the PT minimum (-0.21 vs median +0.22, SD 0.32: 1.3 SD below); ex-R5 dELI +0.38; R5-R4 -0.63 [-0.77, -0.50] | 75% full criterion; 100% "R5 is min" | INDETERMINATE (leaning supported). Fails under the GFC split and the R9 split. With the 16-month Levy/Barbosa period admitted, Levy (-0.39) is below NME |
| H3 | dA(R9-R3) < -0.5 and dB(R9-R3) >= 0, BCB outcomes up and government stance down | dA -1.22 [-1.48, -0.95]; dB +0.55 [+0.20, +0.91]; BCB-outcome part -0.18 -> +0.65; M6 government stance +1.21 -> +0.36 (z) | 100% (competing view dB < -0.5: 0%) | SUPPORTED |
| H4 | dF >= +0.8, dC <= -0.5, abs(dELI) < 0.5 | dF +0.45 [+0.10, +0.77]; dC +0.50 [+0.01, +0.97] (wrong sign); dELI +0.26 | 0% (dF > 0 in 100%; dC < 0 in 0%) | NOT SUPPORTED. The redistributive half holds in direction but below threshold; the credit half is refuted. The competing "left everywhere" view (dELI <= -0.8) is also refuted (0% of cells) |
| H5 | abs(dD) < 0.5 (TOST) | dD -0.20 [-0.58, +0.18] | 94% | INDETERMINATE (leaning supported). The 80% CI pokes 0.08 past the -0.5 margin |
| H6 | abs(dFP) > abs(dELI) + 0.5 | dFP +0.87 [+0.57, +1.28] (perm p 0.024, floor 0.016); abs(dFP)-abs(dELI) = +0.61 [80%: +0.29, +1.04; 95%: +0.11, +1.25] | 87.5% | PARTLY SUPPORTED. Foreign policy diverges more than economics (CI excludes 0), but the +0.5 margin is not cleared at 80% |
| H7 | rho(Fraser/Heritage, ELI) > 0.5 | rho Fraser 0.14, Heritage 0.10 (n = 8 regimes); annual rho -0.05 / +0.05 | n/a | REFUTED (below 0.2) |

Verdict per pillar (PT minus non-PT, z; 80% CI; share of robustness cells with the same sign):
| Pillar | Delta | 80% CI | Same sign | Verdict |
|---|---|---|---|---|
| (a) Fiscal discipline | +0.56 | [+0.21, +0.91] | 100% | PT more disciplined (Lula I-II); Lula III below average |
| (b) Monetary orthodoxy | +0.12 | [-0.28, +0.53] | 68% | no difference |
| (c) State role in credit | +0.50 | [+0.01, +0.97] | 100% | PT not more statist on stocks/subsidy; more statist on BNDES flows (C2) |
| (d) Trade openness | -0.20 | [-0.58, +0.18] | 100% | small PT tilt to protection (local content, AD); PT applied tariffs lower |
| (e) SOE/intervention | -0.45 | [-0.91, +0.04] | 100% | PT more interventionist |
| (g) External/FX | +1.25 | [+0.74, +1.64] | 100% | PT more prudent/open (reserves, KAOPEN); 3 vs 3 regimes |
| ELI | +0.26 | [+0.05, +0.46] | 94% | PT slightly more liberal |
| (f) Left/social (outside ELI) | +0.45 | [+0.10, +0.77] | 100% | PT more redistributive |
| FP progressivism | +0.87 | [+0.57, +1.28] | 100% | PT much more progressive |

=====================================================================
2. DATA CONSTRAINTS (plan section 0, verbatim)
=====================================================================
0.1 Verified in-warehouse series (id -> freq, coverage, catalog.agg).
- Fiscal: primary_balance_gdp (M, 2002-11->2026-08, +=surplus, agg last), primary_result_nfsp (same, NFSP sign), nominal_deficit_gdp, interest_bill_gdp (M, 2002-11->), gross_public_debt_gdp (M, 2006-12->2026-08, last), net_public_debt_gdp (M, 2001-12->2026-08), implicit_interest_rate, r_minus_g, nominal_gdp_growth (M, 2001->), gdp_nominal_12m_brl (M, 2000->). WB (A): wb/GC.TAX.TOTL.GD.ZS.BR, wb/GC.REV.XGRT.GD.ZS.BR, wb/GC.NLD.TOTL.GD.ZS.BR, wb/GC.DOD.TOTL.GD.ZS.BR, wb/GC.XPN.TRFT.ZS.BR (subsidies+transfers, % of expense), wb/GC.XPN.TOTL.GD.ZS.BR (expense % GDP, 2010->2023) — all central-government, 2010->2024 only; wb/NE.CON.GOVT.ZS.BR and wb/NE.CON.GOVT.KD.ZG.BR (real gov-consumption growth, 1961->2025); wb/NY.GDP.MKTP.KD.ZG.BR, wb/NY.GDP.MKTP.CN.BR (nominal GDP LCU).
- Monetary: selic_target (D, 2000->2026-10-03; step function, 13.75 since 2026-09-17), real_policy_rate (M, 2001-12->2026-09), ipca_12m (M, 2000->2026-08), ipca_monthly, ipca_administered_prices (M, % m/m, 2000->2026-08 — monthly change, must be compounded), ipca_services, focus_ipca_12m (D, 2001-12->2026-09-25), focus_selic_12m (D, 2000->), inflation_diffusion, gov_real_yield_10y (D, 2015->), embi_brazil (D, 2000->2024-07-30).
- Credit: credit_gdp (M, 2000->2026-08), household_credit_balance/corporate_credit_balance (M, 2007-03->), wb/FS.AST.PRVT.GD.ZS.BR, wb/FS.AST.CGOV.GD.ZS.BR, wb/GFDD.EI.08.BR (credit to govt & SOEs % GDP, 1980->2020), wb/GFDD.OI.20a.BR (government bank assets % total, 2011->2016 only), wb/FR.INR.RINR.BR (WB real lending rate, 1997->2025).
- Trade: wb/TM.TAX.MRCH.WM.AR.ZS.BR (applied weighted, 1989->2022), wb/TM.TAX.MRCH.SM.AR.ZS.BR (simple), wb/TM.TAX.MANF.WM.AR.ZS.BR, wb/TM.TAX.MRCH.WM.FN.ZS.BR (MFN), wb/TM.TAX.MRCH.BR.ZS.BR/BC (bound rate/coverage 1995->2022), wb/NE.TRD.GNFS.ZS.BR, wb/NE.IMP.GNFS.ZS.BR, wb/TG.VAL.TOTL.GD.ZS.BR (1960->2025), wb/GC.TAX.INTT.RV.ZS.BR (trade taxes % revenue 2010->24), regional export shares wb/TX.VAL.MRCH.{HI,R1,R3,R4,R5,R6,AL}.ZS.BR (1960->2023), china_export_share, exports_to_china/us/eu, exports_total (M, 2014->2026-08).
- SOE/Petrobras: brent_usd (D), brl_usd (D), company_metrics for PETR (Q, 2012-03->2026-06: revenue, ebit, net_income, capex, dividends_paid, net_debt; quarter_end is VARCHAR — cast), total_return_usd@PETR (M, 2012->), dividend_yield_ttm@PETR. No ANP pump-price, refinery-gate or import-parity series exist (the ANP source holds only production series).
- Labour/social: ilostat/EAR_INEE_NOC_NB.BRA (nominal monthly minimum wage, A, 1994->2024: 70->1,412), wb/FP.CPI.TOTL.BR (A, 2010=100), wb/per_sa_cc.cov_pop_tot.BRA (CCT coverage %, 2006->2022, sparse; 2020 = 5.95 is a definitional anomaly — flag), wb/per_sa_allsa.cov_pop_tot.BR, wb/SI.POV.GINI.BR, real_average_income, unemployment_rate.
- External/FX: fx_reserves (D, 2000->2026-10-01, US$ mn), wb/FI.RES.TOTL.MO.BR (1975->2025), wb/BN.KLT.PTXL.CD.BR, wb/BX.PEF.TOTL.CD.WD.BR, wb/BX.KLT.DINV.WD.GD.ZS.BR, wb/REER_M.BRA (1987->2024-10), wb/PX.REX.REER.BR, current_account_usd.
- Controls: wb/TOT.BRA (M, 1991->2025-12), wb/TT.PRI.MRCH.XD.WD.BR (A, 2005->2024), brent_usd. Environment: wb/AG.LND.PFLS.HA.BR (primary forest loss, 2002->2025).
- Governance: wb/GOV_WGI_RQ_EST.BR (Regulatory Quality, 1996->2024, biennial to 2002): 0.19 (2003, 2010–12) -> -0.29 (2024).
- Missing from warehouse (tested): any inflation-target series, earmarked/BNDES/TJLP series, public-bank credit share, fuel prices, IOF rates, trade-agreement counts, antidumping counts, privatisation values, Fraser/Heritage. All external (section 2).

0.2 External BCB SGS codes verified live on 2026-10-05 via ingest/bcb_sgs.py: meta() (the JSON host api.bcb.gov.br is NXDOMAIN; use the SOAP helper). Pull one code per call. Verified codes: 20539 total credit balance (M, 2007-03->2026-08), 20593 earmarked (recursos direcionados) total, 20542 free-resources total, 20625 free credit % GDP, 2007 credit by public-control banks (M, 2000->2026-08), 2043 private-control banks, 256 TJLP (M, 2000->2026-10), 27572 TLP monthly factor, 11428 IPCA free items (% m/m), 4449 IPCA administered (% m/m; already in warehouse), 13521 inflation target (A; meta works: 3.00 for 2026). Codes 2044/3995/7408/27803 are not what their numbers suggest; do not use.

0.3 Anchor numbers: ALL REPRODUCED within 0.05 (anchors.py).
- Regime means: real_policy_rate, primary_balance_gdp, ipca_12m, selic_target, embi_brazil.
- First/last values: credit, gross debt, net debt.
- Yearly real_policy_rate.
- Selic step facts: the 2011 cut is 12.50 -> 12.00 effective 2011-09-01; 2012 had 7 cuts; 2017 had 8; 2025 min 12.25 / max 15.00; 2026 five cuts to 13.75.
- Focus within-year SDs.
- Administered vs headline IPCA: 2015 18.07 vs 10.67; 2022 -3.83 vs 5.78.
- SGS shares: earmarked 33.5 / 49.9 / 40.1 / 43.9; public-bank 36.7 / 56.0 / 42.3 / 41.7.
- TJLP yearly means: 11.5 / 5.00 / 9.17.
- WB tariffs, trade share, export shares, Petrobras dividends and net income, PETR total return, FX reserves.
- Lula-Palocci Selic mean is 19.50 with the exact 2006-03-28 boundary, vs the 19.49 anchor.

Pitfalls observed (0.4): first/last aliased; quarter_end cast; v_by_term never used; WB on YYYY-12-31; 2026 never complete; date <= current_date filtered.

Executor-side data notes and deviations (declared in preregistration.txt before computation unless marked *):
D1. Warehouse net_public_debt_gdp is a narrower concept than BCB DLSP consolidated (SGS 4513).
  - The warehouse series reads 37.7% at 2002-12; SGS 4513 reads 51.5% at 2001-12, and IPEAData/BCB gives 59.9% for 2002.
  - Baseline F4 follows the plan (warehouse series). The SGS 4513 sensitivity changes dA by +0.01.
D2. Lula-Palocci/Mantega boundary uses the exact 2006-03-28.
D3. Coverage rule enforced, so R6 (Levy/Barbosa, 16.4 months, one 1-July year) is excluded from every baseline test.
  - Baseline is therefore 4 PT vs 4 non-PT: 70 labelings, floor p 2/70 = 0.029, not the 0.016 in the power statement.
  - Results with R6 admitted are reported as "with R6".
*D4. 2003/2004 inflation targets: CMN's original 2003 target was 3.25%, revised to 4.0% (CMN 2,972) and then adjusted to 8.5% by the BCB open letter of 2003-01-21.
  - I use the in-force targets the plan lists: 4.0 for 2003 and 5.5 for 2004, tolerance 2.5.
  - Sensitivity with 2003 = 8.5: dB +0.14, R9-R3 dB +0.30.
*D5. Neutral rate: BCB/Copom r* figures exist only from 2016.
  - From 2016 they are market proxies or analyst surveys reported in BCB boxes; Copom's own 4.0/4.5/4.75/5.0 starts in 2023.
  - Baseline r* = these figures interpolated from 2016-01, with the plan's fallback (10-year trailing median of real_policy_rate) before that. No backward extrapolation.
  - Sensitivity: fallback throughout, giving dB +0.19 and R9-R3 dB +0.48.
*D6. T3 trade agreements use the full OAS SICE Brazil agreement index (20 agreements 1996-2026, fact RM16) plus Mercosur-Palestine.
  - The research list missed the 1996 Mercosur-Chile and Mercosur-Bolivia ACEs, which would have biased T3 against FHC.
  - Two entries the researcher could not verify were dropped: Brazil-Peru 2016 and the OECD roadmap date.
*D7. Tax burden (F3): Receita Federal CTB changes for 1996-2010, with the 2005 GDP-revision break dropped; Tesouro STN general-government CTB changes from 2011, to avoid the 2020 FGTS/Sistema S break.
*D8. English UN corpus: the pre-registered Portuguese dictionaries were translated term by term. I briefly added "inequality/hunger/poverty" and then removed them before the final run to stay faithful to the pre-registered list.
*D9. IOF on inflows (X2b) is descriptive only. Rates before 2008 (the 1990s controls) could not be verified, and entering zeros would be a silent substitution. Chinn-Ito KAOPEN carries X2.

GAPS (listed, not substituted):
Components and series:
- S1: no ANP/Abicom import-parity gap; the plan's warehouse fallback is used (Petrobras USD revenue residual on Brent, 2012+ only).
- S3: no consistent yearly privatisation series (BNDES gives only period totals); component dropped.
- X3: FX-swap stock not obtained.
- C1: pre-2007 earmarked share not pulled.
- L2b: Bolsa Família 2004-07 not separate in RTN.
- C2: BNDES R$100bn repayment date not verified (RA33).
Facts and coding:
- Camex Resolution 70/2012 and the 2013 second list (RA24/RA25) not verified.
- The 2007 minimum-wage valuation agreement is unsourced and was dropped from L4.
- Number of Africa embassies, Rounds 5-7 local-content percentages, Mercosur-Israel entry into force, Singapore signing date, PPCDAm/G4 years (RC70-72) not found.
Party positions:
- MARPOR coverage of PT/PSDB unconfirmed (needs an API key); skipped.
- V-Party has no 2022 value.
Rhetoric corpus:
- PSDB 2002 (Serra) and 2006 (Alckmin) programmes not obtained.
- UN 2025 speech not obtained.
- Harvard UNGDC requires a guestbook form; the Birmingham UNGDC site and UN verbatim records were used instead.
The session's 200-call web-search budget was exhausted; remaining sources were opened directly (planalto.gov.br, bcb.gov.br, SEC EDGAR, OAS SICE, Wikipedia).

=====================================================================
3. REGIME REGISTRY (half-open [start, end); 1-July rule for annual data)
=====================================================================
| id | Regime | Party | Start | End | Months | Verified triggers (fact ids in external_facts.csv) |
|---|---|---|---|---|---|---|
| R1 | FHC I | PSDB | 1995-01-01 | 1999-01-15 | 48.5 | float mid-Jan 1999 (RA01); EC 9/1995 (RM01); Law 9,478/1997 (RM02); EC 20/1998 (RM03) |
| R2 | FHC II | PSDB | 1999-01-15 | 2003-01-01 | 47.5 | IT Decree 3,088 1999-06-21 (RA02); CMN 2,615 (RA03); LRF LC 101 2000-05-04 (RA04) |
| R3 | Lula-Palocci | PT | 2003-01-01 | 2006-03-28 | 38.9 | Palocci out / Mantega in 2006-03-27 (RA05, medium: posse day 27 vs 28 not separable); surplus target 4.25% (RA06, source date 2003-03-18); EC 41 2003-12-19 (RA07); Meirelles 2003-2010 (RA08); 2003 target adjusted 8.5% (RA09) |
| R4 | Lula-Mantega | PT | 2006-03-28 | 2011-01-01 | 57.1 | PAC 2007-01-22 (RA10); IPI cut Decree 6,687 2008-12-11 (RA11); MP 453 2009-01-22 (RA12); MCMV MP 459 2009-03-25 (RA13); IOF 1.5% 2008-03-17 / 0 2008-10-22 (RM08/RM09); IOF 2% 2009-10-20 (RA14), 4% 2010-10-05 (RA15), 6% 2010-10-19 (RA16), Decree 7,412 (RA17); pre-salt Law 12,351 2010-12-22 (RM04) |
| R5 | Dilma NME | PT | 2011-01-01 | 2015-01-01 | 48.0 | Tombini (RA19); Plano Brasil Maior MP 540 2011-08-02 (RA20); Decree 7,567 IPI (RM05); Law 12,546 payroll (RA21); MP 579 2012-09-11 (RA22); Inovar-Auto Law 12,715 / Decree 7,819 (RA23); IOF zeroed Decree 8,023 2013-06-05 (RA18); Camex 70/2012 GAP (RA24) |
| R6 | Levy/Barbosa | PT | 2015-01-01 | 2016-05-12 | 16.4 | Levy 2015-01-01 to 2015-12-18 (RA26); Barbosa announced 2015-12-18 (RA27; posse 21-Dec unverified); MPs 664/665 (RM10); Dilma suspended 2016-05-12 (RA28) |
| R7 | Temer | MDB | 2016-05-12 | 2019-01-01 | 31.7 | Goldfajn 2016-06-09 (RA34); Petrobras import parity 2016-10-14 (RA29); Law 13,365 2016-11-29 (RM06); EC 95 2016-12-15 (RA30); labour reform 2017-07-13 (RA31); TLP Law 13,483 2017-09-21 (RA32); diesel subsidy MP 838 2018-05-30 (RM11) |
| R8 | Bolsonaro/Guedes | PL | 2019-01-01 | 2023-01-01 | 48.0 | Campos Neto 2019-02-28 (RA35); EC 103 2019-11-12 (RA36); LC 179 2021-02-24 (RA37); Gecex 269 2021-11-04 (RA38), Gecex 353 2022-05-23 (RA39); Eletrobras Law 14,182 / completed 2022-06-14 (RA40/RA41); Petrobras CEO removal Feb-2021 (RM12); LC 194 2022-06-23 (RA42/RM14); EC 123 2022-07-14 (RA43/RM13) |
| R9 | Lula III (Haddad; Campos Neto -> Galípolo) | PT | 2023-01-01 | 2026-08-31 (data end) | 44.0 | Lula vs Campos Neto 2023-02-02 (RA44); Petrobras drops parity 2023-05-16 (RA45); Law 14,663 2023-08-28 (RA46); LC 200 2023-08-30 (RA47); EC 132 2023-12-20 (RA48); NIB 2024-01-22 (RA49); dividend retention 2024-03-07 (RA50) and AGM payout 2024-04-25 (RA51); Prates out 2024-05-14 (RA52); continuous target (RA53); Law 15,077 min-wage cap (RA54); LC 211 (RA55); Galípolo 2025-01-01 (RA56); Selic 15% 2025-06-18 (RA57); cuts from 2026-03-18 to 13.75 (RA58, C62); minimum wage R$1,518 (2025, RA59) and R$1,621 (2026, RA60); diesel subsidies 2026 (RA61-63); EU-Mercosur signed 2026-01-17 / provisional 2026-05-01 (C04, C07) |
Date differences vs plan:
- Palocci exit 2006-03-27 (plan: 28).
- LC 200 dated 2023-08-30 (plan: 31).
- Inovar-Auto law 2012-09-17.
- Petrobras 2023 strategy approved 15 May, announced 16 May.
- 2026 minimum wage R$1,621 (Decree 12,797).
None of these moves a 1-July year attribution.

=====================================================================
4. PRE-REGISTRATION
=====================================================================
preregistration.txt was written at 2026-10-05T21:08:22Z, after the anchors and SGS pulls but before any component, sub-index or test was computed. The script asserts the file exists before it runs.
It contains, verbatim:
- plan sections 1, 2 (signs), 3 and 4
- section 5.2, including the 5.2.7 robustness grid
- declared deviations D1-D4
Deviations D4-D9 above, marked *, were decided after the external data arrived but before any hypothesis statistic was viewed. The exception is D8, which I applied after a descriptive rhetoric dry run, to restore fidelity to the pre-registered dictionary.
Power statement (verbatim): "with regime as the unit, 5 PT vs 4 non-PT regimes give C(9,4) = 126 labelings, so the smallest attainable two-sided permutation p is 2/126 = 0.016; with terms (3 vs 3) it is 0.10; H2's within-PT rank test has floor 0.20. Regimes of the same president are not independent. Nothing is expected to clear BH at q = 0.10; the study is an effect-size study with uncertainty bands." Realised:
- R6 excluded by the coverage rule, so 4 vs 4: 70 labelings, floor 0.029.
- (g) has 3 vs 3, floor 0.10.
- FP keeps 5 vs 4, floor 0.016.
- H2 rank floor 1/4 = 0.25.

=====================================================================
5. METHODS IN BRIEF
=====================================================================
Index construction:
- Each component becomes an annual series for 1995-2026; 2026 is partial and flagged.
- Signs are set so that + means more liberal/orthodox; for (f), + means more redistributive.
- Components are z-scored over pooled 1995-2025.
- A sub-index is the weighted mean of available z's, with at least 2 components per year.
- A regime's score is the mean of its 1-July years; it needs at least 2 years.
- ELI is the mean of the regime's (a)(b)(c)(d)(e)(g) scores, with at least 3 present.
- FP is the mean of z(FP1..FP5) across the 9 coded regimes.
Inference:
- Delta = mean(PT) - mean(non-PT).
- Exact permutation p-values.
- Two-stage cluster bootstrap: regimes within group, then years within regime; 5,000 draws, seed 0. Coding Monte Carlo (+/-1 per FP cell, 2,000 draws) is folded into the FP draws.
- ToT adjustment: OLS of each non-coded component on log ToT and its change, 1995-2025.
- Start adjustment: residual of regime score on standardised IPCA 12m and Selic in the month before the regime starts.
- Crisis-out drops 2009, 2015, 2016 and 2020.
- BH correction over 7 sub-indices and over about 30 components.
Robustness grid (384 cells):
- 6 boundary variants
- unit: regime, term, or year-cluster
- adjustment: raw, ToT, or ToT+start (no start adjustment at year level)
- crisis years in or out
- F3 in or out
- FP4 in or out

Core SQL (shown as run; full strings in results.json "sql.*"):
  -- monthly panel
  SELECT series_id, date_trunc('month', date) AS ym,
         CASE WHEN series_id IN ('fx_reserves','brl_usd','brent_usd') THEN arg_max(value, date) ELSE avg(value) END AS v,
         max(date) AS last_date
  FROM v_observations WHERE date <= current_date AND series_id IN ('selic_target','real_policy_rate','ipca_12m','ipca_monthly',
    'ipca_administered_prices','focus_ipca_12m','focus_selic_12m','primary_balance_gdp','nominal_deficit_gdp','interest_bill_gdp',
    'gross_public_debt_gdp','net_public_debt_gdp','credit_gdp','fx_reserves','brl_usd','brent_usd','embi_brazil','gov_real_yield_10y',
    'wb/TOT.BRA','wb/REER_M.BRA','gdp_nominal_12m_brl','unemployment_rate') GROUP BY 1,2;
  -- annual panel (WB / ILO), year attributed by the 1-July rule in Python
  SELECT series_id, year, value, is_complete, agg FROM v_annual WHERE year BETWEEN 1995 AND 2026 AND series_id IN (<33 ids listed in the plan>);
  -- regime anchors (reproduction)
  WITH reg(rid,label,s,e) AS (VALUES (2,'FHC II',DATE '1999-01-15',DATE '2003-01-01'), ... ,(9,'Lula III',DATE '2023-01-01',DATE '2027-01-01'))
  SELECT r.rid, r.label, o.series_id, avg(value), arg_min(value,date) AS first_v, arg_max(value,date) AS last_v
  FROM v_observations o JOIN reg r ON o.date >= r.s AND o.date < r.e WHERE o.date <= current_date AND series_id IN (...) GROUP BY ALL;
  -- administered-price compounding
  SELECT year(date), 100*(exp(sum(ln(1+value/100)))-1) FROM v_observations WHERE series_id='ipca_administered_prices' GROUP BY 1;
  -- Petrobras
  SELECT year(CAST(quarter_end AS DATE)) y, sum(dividends_paid_brl), sum(capex_brl), sum(net_income_brl), arg_max(net_debt_brl_bn, CAST(quarter_end AS DATE))
  FROM company_metrics WHERE entity_id='PETR' GROUP BY 1;
  SELECT year(CAST(quarter_end AS DATE)) y, sum(revenue_usd_bn) FROM company_metrics WHERE entity_id='PETR' GROUP BY 1 HAVING count(*)=4;
  -- Focus dispersion
  SELECT date, value FROM v_observations WHERE series_id='focus_ipca_12m' AND date<=current_date;   -- SD by year in Python
External SGS (SOAP, one code per call):
- 20593 / 20539 (earmarked share)
- 2007 / 2043 (public-bank share)
- 256 (TJLP), 27572 (TLP Jm), 433 (IPCA), 4189 (Selic monthly)
- 11428 (free IPCA), 4449 (administered IPCA), 4513 (DLSP)
Latest observations used (warehouse, all canonical BCB except where noted):
- monthly to 2026-08-01: primary_balance_gdp (derived), gross_public_debt_gdp, net_public_debt_gdp, ipca_12m, ipca_administered_prices, credit_gdp
- real_policy_rate (derived) 2026-09-01; focus_ipca_12m 2026-09-25; selic_target 2026-10-03; fx_reserves 2026-10-01
- embi_brazil 2024-07-30; wb/TOT.BRA 2025; WB tariffs 2022; KAOPEN 2023; Fraser 2023; Heritage edition 2026

=====================================================================
6. RESULTS PER SUB-INDEX
=====================================================================
Component regime means (natural units; monthly components averaged over exact regime dates). Order: FHC I / FHC II / Lula-Palocci / Lula-Mantega / NME / Levy / Temer / Bolsonaro / Lula III.

(a) FISCAL DISCIPLINE: dA +0.56 [80% +0.21, +0.91; 95% +0.01, +1.07]; perm p 0.11; ToT-adjusted +0.61; start-adjusted +0.50; crisis-out +0.39; term-level +0.38 (p 0.30).
- F1 primary balance % GDP: -0.2 / 3.1 / 3.6 / 2.9 / 1.6 / -1.9 / -1.9 / -2.0 / -0.9.
  - BCB NFSP for 1995-2001 recomputed on current GDP (RB facts; 2002 matches the published 3.19).
- F2 real primary-spending growth minus real GDP growth (Tesouro RTN, from 1997; 1997 is the first growth year): ... / 2.8 / 1.6 / 5.2 / 1.6 / 5.6 / -0.1 / 1.8 / 2.2.
- F3 change in tax burden, pp/yr: 0.0 / +1.5 / -1.7 / -0.2 / -0.2 / +0.2 / +0.2 / +0.2 / +0.4.
- F4 change in debt, pp GDP/yr: +3.7 / +4.7 / -2.4 / -0.9 / -0.1 / +5.2 / +4.6 / +0.5 / +3.1.
Reading:
- The PT fiscal advantage is Lula I-II plus the NME's early years: surpluses of 3-3.6% of GDP with debt falling. FHC II also ran 3%+ surpluses, but its debt rose with the 1999 and 2002 devaluations.
- Lula III (-0.37) sits near Temer (-0.39) and FHC II (-0.31). Its primary deficit is smaller than Temer's or Bolsonaro's, but debt is rising about 3 pts a year.

(b) MONETARY ORTHODOXY: dB +0.12 [-0.28, +0.53]; perm p 0.77; ToT +0.07; start -0.03; same sign in 68% of cells. No difference.
- M1 real rate minus r*, pp: n.a. / 0.0 / 0.0 / -4.3 / -3.9 / +1.5 / +1.4 / -0.8 / +4.1.
- M2 -|Dec IPCA - target|: n.a. / -4.2 / -2.9 / -0.9 / -1.7 / -6.2 / -1.4 / -2.3 / -1.4.
- M3 share of months in band: n.a. / 0.33 / 0.54 / 1.00 / 0.69 / 0.00 / 0.45 / 0.42 / 0.55.
- M4a -(Focus minus target): n.a. / -2.2 / -1.4 / +0.1 / -1.2 / -1.8 / 0.0 / -0.5 / -1.3.
- M5 Selic minus Taylor rule, pp: n.a. / -3.2 / -2.1 / -4.2 / -5.8 / -1.2 / +1.5 / -1.5 / +2.1.
- M6 autonomy code (0-3): 1 / 1 / 2 / 2 / 0.5 / 1 / 1 / 1.5 / 1.5.
Reading:
- NME is the monetary low (-0.50): Taylor residual -5.8 pp, with the 2011-12 forced cuts and presidential pressure.
- Lula III is the monetary high (+0.60).
- Sensitivities: r* from the trailing median throughout gives dB +0.19; 2003 target 8.5 gives dB +0.14.

(c) STATE ROLE IN CREDIT (+ = smaller state): dC +0.50 [+0.01, +0.97]; perm p 0.29; ToT +0.46; start +0.19; term +0.31.
- C1 earmarked share, % (2007+): n.a. / n.a. / n.a. / 34.7 / 42.0 / 49.0 / 49.1 / 42.0 / 42.0.
- C2 BNDES disbursements, % GDP: 1.5 / 2.0 / 2.1 / 3.2 / 3.3 / 2.3 / 1.2 / 0.8 / 1.2.
- C2b Treasury credit to BNDES, % GDP: n.a. / 0.6 / 0.8 / 2.4 / 7.7 / 8.6 / 5.8 / 1.8 / 0.9.
- C3 TJLP/TLP minus Selic, pp: -19.0 / -9.1 / -9.2 / -5.2 / -4.4 / -7.0 / -1.7 / +3.8 / -1.5.
- C4 public-bank share, %: 54.8 / 43.4 / 38.4 / 37.4 / 47.6 / 55.7 / 54.8 / 45.5 / 42.4.
Reading: the sign is driven by three things.
- FHC I's enormous implicit subsidy: TJLP 19 pp below a 25-40% Selic, and a 55% public-bank share before PROES.
- Temer's inherited Dilma-era stocks: 49% earmarked, 55% public banks.
- The flow measure points the other way: BNDES disbursements average 2.1-3.3% of GDP under Lula-Mantega and NME vs 0.8-2.0% under non-PT. The C2 component delta is -1.06.
Credit stocks are lagged outcomes, and much of the "statism" attributed to Temer was built in 2009-14. A fair reading is that PT expanded state credit in 2008-14, while Lula I and Lula III did not. This half of H4 is not supported as specified.

(d) TRADE OPENNESS: dD -0.20 [-0.58, +0.18]; perm p 0.57; ToT -0.16; term -0.07.
- T1 tariff level, z: 1.4 / 1.2 / -0.4 / -0.8 / -0.1 / -0.3 / -0.3 / -0.5 / -0.8.
  - Applied tariffs were highest under FHC and lowest under Lula-Mantega and Lula III.
  - The NME's 2013 rise (weighted 7.76 -> 10.08) shows clearly.
  - The WTO MFN simple average is spliced for 2023-25 by ratio.
- T3 agreements per year: 1.0 / 1.0 / 2.3 / 1.4 / 0.25 / 0 / 1.3 / 0.5 / 1.0.
- T4 local content: +1 / 0 / -1 / -1 / -1 / -1 / +1 / +1 / -1.
- T5 anti-dumping initiations per year: 13 / 13 / 6 / 19 / 38 / 23 / 8.3 / 5.3 / 25.3.
Component deltas: T1 +1.03 (PT lower tariffs), T2 +0.80, T3 +0.28, T4 -1.87, T5 -0.90, T6 -0.50.
PT governments relied on non-tariff and contingent protection (local content, anti-dumping, Inovar-Auto), while applied tariffs were lower than under FHC. The net is a small negative.

(e) SOE AND MARKET INTERVENTION: dE -0.45 [-0.91, +0.04]; perm p 0.34; ToT -0.38; term -0.39 (p 0.40).
- S1 Petrobras revenue residual on Brent (2012+ fallback): NME +0.09, Levy +0.24, Temer +0.08, Bolsonaro -0.12, Lula III -0.09.
  - This is weak: it confounds volumes and the post-2016 pricing.
- S2 administered-price repression, pp: 0 / 0 / 0 / -1.9 / -3.1 / 0 / -0.2 / -2.1 / -1.4.
  - This captures NME's 2012-14 fuel and power freeze.
  - It also captures Bolsonaro's 2022 election-year fuel-tax cuts: administered prices -3.83% vs IPCA 5.78%.
- S4 net intervention events per year: -0.5 / 0 / 0 / 0.2 / 0.75 / 0 / -0.33 / 0.75 / 1.0.
- S5 Petrobras payout ratio (descriptive): NME 7.6%, Levy 0%, Temer 1.7%, Bolsonaro 45.7%, Lula III 44.0%.
  - Lula III kept a payout ratio as high as Bolsonaro's despite the 2024 dividend fight.
Reading: Bolsonaro (-0.68) is as interventionist as the PT's worst. NME is -0.45 and Lula III -0.51. FHC (+0.75 / +0.45), Temer (+0.61) and Lula-Palocci (+0.44) are the market-friendly regimes. S3 privatisations is missing, which probably flatters PT relative to FHC (1997-98 Vale and Telebrás) and Bolsonaro (Eletrobras 2022).

(g) EXTERNAL AND FX: dG +1.25 [+0.74, +1.64]; perm p 0.10 (floor 0.10, 3 vs 3).
- Lula III is n.a. in the baseline: KAOPEN ends in 2023, so it has only one year with 2 or more components.
- X1 reserve accumulation, % GDP: n.a. / 0.45 / 0.90 / 3.08 / 0.72 / -0.39 / 0.32 / -0.64 / 0.42.
- X2 KAOPEN: -1.77 / -0.98 / -0.09 / +0.28 / -0.17 / -1.25 / -1.25 / -1.25 / -1.25.
- X2b IOF on inflows (descriptive): 0.84% (Lula-Mantega) and 3.64% (NME) annual mean; zero otherwise from 1999.
Reading: Chinn-Ito codes Brazil most open in 2006-09, despite the IOF in 2009-13. This index is known to be sticky, and the result leans on one external index.

(f) LEFT/SOCIAL (outside ELI; + = more redistributive): dF +0.45 [+0.10, +0.77]; perm p 0.11; ToT +0.48; term +0.42 (p 0.20).
- L1 real minimum-wage growth, %/yr: 0.7 / 4.4 / 4.7 / 6.3 / 2.9 / -0.2 / 1.3 / 0.1 / 3.3.
- L2a transfers, % GDP (2010+): 16.5 / 16.9 / 17.6 / 19.1 / 20.7 / 20.4 (Lula-Mantega to Lula III).
- L2b Bolsa Família + Auxílio, % GDP (2008+): 0.35 / 0.44 / 0.45 / 0.44 / 0.53 / 1.40.
- L4 net pro-labour events per year: -0.25 / 0 / -0.33 / 0 / +0.25 / -1.0 / -0.33 / -0.25 / 0.
Reading:
- The redistributive signal is real but smaller than the user's +0.8 threshold.
- FHC II (+0.31) had strong real minimum-wage gains.
- Bolsonaro's 2020-22 transfers (Auxílio Emergencial/Brasil) raise non-PT L2.
- The politics study's distribution composite was +0.92 z left vs right. Health and education spending showed no lean signal (politics report section F: health spend Δ -0.33 pp GDP, education -0.03; cited, not recomputed).

Multiple comparisons:
- Family 1 (7 sub-indices): BH q from 0.27 (a, f, g) to 0.77 (b).
- Family 2 (30 components): minimum q 0.357.
- Nothing passes q = 0.10, as the power statement anticipated.
- Smallest component permutation p-values (0.029, the floor): T4 local content and X2 KAOPEN.

=====================================================================
7. LULA I vs LULA III (H3 detail)
=====================================================================
Pairwise R9 - R3 (bootstrap 80% CI):
- a -1.22 [-1.48, -0.95]
- b +0.55 [+0.20, +0.91]
- c +0.12 [+0.02, +0.21]
- d -0.55 [-0.89, -0.20]
- e -0.96 [-1.23, -0.68]
- f +0.54 [-0.13, +1.19]
- ELI -0.44 [-0.57, -0.34]
Fiscal changes:
- primary balance +3.6 -> -0.9% GDP
- debt change -2.4 -> +3.1 pts/yr
- tax burden -1.7 -> +0.4 pp/yr
Monetary changes:
- real rate minus r*: 0.0 -> +4.1 pp
- Taylor residual: -2.1 -> +2.1 pp
- inflation miss: 2.9 -> 1.4 pp
- months in band: 54% -> 55%
- expectations gap: -1.4 -> -1.3 pp (still unanchored)
Decomposition of (b), z:
- BCB-outcome part (M1-M5): -0.18 -> +0.65
- government-stance part (M6): +1.21 -> +0.36. Lula III has de jure autonomy (LC 179) and the BCB was more hawkish, but Lula publicly attacked Campos Neto in 2023-24 (RA44), whereas Meirelles was shielded.
Reading: the monetary orthodoxy of Lula III belongs to the BCB under LC 179, a Bolsonaro-era law, and the government opposed it. Lula III is more interventionist than Palocci on SOEs (Petrobras drops import parity in 2023, the dividend fight and Prates's removal in 2024, NIB, 2026 diesel subsidies). Lula III is also more redistributive (Bolsa Família 1.40% of GDP, the min-wage rule restored), within the arcabouço and the Dec-2024 cap on minimum-wage gains (Law 15,077).
Sensitivities: R9-R3 dB is +0.48 (r* trailing median), +0.30 (2003 target 8.5) and +0.55 (SGS 4513 net debt). Splitting R9 at 2025 (Galípolo) leaves H3 holding in 100% of the regime cells.

=====================================================================
8. H2: THE NOVA MATRIZ AS OUTLIER
=====================================================================
PT ELI among eligible regimes:
- Lula-Palocci +0.44
- Lula-Mantega +0.43
- Lula III 0.00
- NME -0.21
NME is the minimum: 1.3 within-PT SDs below the PT median (SD 0.32). Excluding NME, dELI is +0.38. NME minus Lula-Mantega is -0.63 [-0.77, -0.50], so the competing claim that Mantega was equally low is refuted. NME minus Lula III is -0.21 [-0.31, -0.08].
Why only "indeterminate":
- The full criterion holds in 75% of cells, below the 80% threshold.
- Splitting Lula at the GFC (2008-09-15) moves 2006-08 into R3 and lifts the PT median.
- With the 16-month Levy/Barbosa period admitted, its ELI (-0.39, a recession year with an 18% administered-price catch-up) is below NME.
Reading: NME is the outlier among full PT governments. Lula III is closer to NME than Lula I-II on trade and SOE, but far more orthodox on monetary policy.

=====================================================================
9. 2-D TRAJECTORY (ELI x FP; chart 2)
=====================================================================
Chronological path (ELI, FP):
- FHC I (-0.17, -0.27)
- FHC II (-0.09, -0.13)
- Lula-Palocci (+0.44, +0.43)
- Lula-Mantega (+0.43, +0.74)
- Dilma NME (-0.21, +0.15)
- Levy/Barbosa (-0.39 relaxed, -0.24)
- Temer (0.00, -0.29)
- Bolsonaro (-0.11, -1.25)
- Lula III (0.00, +0.86)
Reading:
1. The economic axis is compressed (range 0.65 z among eligible regimes); the foreign-policy axis is wide (2.1 z). The PT/non-PT split runs along FP, not ELI.
2. Lula I-II is the "liberal-progressive" quadrant, high on both axes. This is the configuration the user describes.
3. The PT's economic drift: Palocci -> Mantega flat on ELI with more FP activism, then NME a sharp move left on ELI, then Lula III back to the middle.
4. Bolsonaro is the FP outlier: Migration Compact exit, COP25 cancelled, Amazon Fund frozen, Guaidó recognised. Economically he is indistinguishable from FHC or Temer, and below Lula I-II.
5. Lula III's sub-index profile is nearest Lula-Mantega (RMS 0.38), then Bolsonaro (0.44). On fiscal and monetary alone it is nearest Temer (0.23).
FP sensitivity (PT-minus-non-PT dFP):
- baseline +0.87
- without FP4 (Venezuela/Russia) +0.67
- without FP5 (trade diplomacy, where Temer and Bolsonaro score high) +1.32
- without FP4 and FP5 +1.19
FP is coded per regime, so it is an ordinal judgement with one sourced fact per cell (fp_coding.csv). Spearman rho of FP with Brazil-USA UNGA ideal-point distance is only 0.22. The UNGA anchor shows Bolsonaro closest to the US (distance 2.20 vs 2.6-3.1 otherwise), but it does not separate PT from FHC.
Outcome anchors (not policy):
- High-income export share fell from 67-70% (FHC) to 42.6% (Lula III), and the EAP share rose from 4.8% to 35.8%, steadily under both camps.
- PRODES Amazon deforestation averaged 24,061 km2/yr (Lula-Palocci), 10,662 (Mantega), 5,473 (NME), 7,459 (Temer), 11,403 (Bolsonaro) and 7,104 (Lula III).

=====================================================================
10. RHETORIC VS ACTION (H0; chart 4; rhetoric_scores.csv)
=====================================================================
Corpus A: 20 campaign programmes.
- PT: Carta ao Povo Brasileiro 2002, programmes 2002, 2006, 2010 (2 documents), 2014, 2018, 2022, 2026.
- PSDB: 1994, 1998, 2010, 2014, 2018. Also Ponte para o Futuro 2015, PSL/Bolsonaro 2018, PL 2022, Flávio 2026, MDB/Meirelles 2018, PSB/Marina 2014.
Rhetoric score = (LIBERAL - LEFT) / (LIBERAL + LEFT); 80% sentence-bootstrap bands.
PT documents:
- Carta +0.47 (the only liberal-leaning PT text)
- PT programme 2002 -0.32, 2006 -0.26
- Dilma 2010 -0.70 / -0.33, 2014 -0.08
- Haddad 2018 -0.43, Lula 2022 -0.50, Lula 2026 -0.22
Non-PT documents:
- Ponte +0.58, Bolsonaro 2018 +0.26, PL 2022 +0.32
- Aécio +0.38, Marina +0.33, FHC 1998 +0.21
- FHC 1994 -0.04, Serra 2010 -0.70, Flávio 2026 -0.04
Results:
- rho(rhetoric, ELI of the following regime) = 0.18, perm p 0.49, n = 18 (documents tagged to R1-R9).
- PT mean rhetoric z -0.63 vs action z +0.44 (PT talks left and governs centre-right of the sample). Non-PT: rhetoric +0.51 vs action -0.35.
- H0 supported.
Corpus B: Brazil's UNGA openings 1995-2024 (30 statements; English).
- Economic rhetoric score by regime: FHC +0.39 / +0.60, Lula +0.05 / 0.00, Dilma -0.02 / -0.33, Temer 0.00, Bolsonaro +0.23, Lula III -0.50.
- South-South terms per 1k tokens: highest in Lula III (14.0) and Lula-Mantega (12.2), lowest under Bolsonaro (6.3).
- rho(UN FP rhetoric, FP axis) = 0.41; rho(UN economic rhetoric, ELI) = -0.08.
Caveats:
- dictionary validity: a random 20-sentence audit is in results.json "rhetoric_audit_sample". Example: "estabilidade/stability" also catches non-economic uses.
- unequal document length (Carta 1,759 tokens vs FHC 1998 81,574)
- the English corpus uses a translated dictionary
- the UN text is the delegation's English version; 2025 is missing
- single coder; no PSDB 2002/2006 programme
Corpus C (speeches) was not attempted.

=====================================================================
11. EXTERNAL-INDEX CONCORDANCE (H7; chart 5)
=====================================================================
Fraser EFW 2025 edition (efotw.org API; summary 1995, 2000-2023), regime means: 4.34 / 5.86 / 6.27 / 6.36 / 6.37 / 6.10 / 6.54 / 6.51 / 6.68 (2023 only for Lula III).
Heritage IEF, editions 1995-2026 shifted one year back to the data year: 53.6 / 62.0 / 61.6 / 56.2 / 57.3 / 56.5 / 52.1 / 53.5 / 53.6.
- 1995-2009 values are back-casts from the archived 2010 file (medium confidence).
Concordance with ELI:
- rho with ELI across 8 regimes: Fraser 0.14, Heritage 0.10. Annual rho: -0.05 / +0.05.
- Area concordance: Fraser area 1 (size of government) vs (a) 0.60; area 5 (regulation) vs (c) 0.50; area 3 (sound money) vs (b) 0.43; area 4 (trade) vs (d) 0.26. Heritage components vs ELI pillars range from -0.49 (financial vs c) to +0.17.
- H7 refuted.
Why the indices diverge:
- Fraser has a secular upward trend: it rewards the end of 1990s high inflation and Bolsonaro/Temer-era regulation.
- Heritage peaks under FHC II and Lula-Palocci and falls after 2010.
- Neither tracks fiscal flows or BNDES/administered-price intervention the way ELI does.
- Both still put PT regimes at or above non-PT on average: Fraser +0.54 points, Heritage +1.76 points. On levels they do not contradict the headline; they disagree on ranks.
V-Party v2pariglef (economic left-right, + = right):
- PT moved from -2.63 (1994) and -2.24 (1998) to -1.46 (2002/06), -1.30 (2010) and -1.46 (2014), then back to -1.90 (2018). No 2022 value.
- PSDB +0.4 to +1.5; PSL 2018 +3.25.
- The expert-coded party position moderated sharply exactly when the PT took office. This is consistent with the "orthodox in office" reading, though experts still place it clearly left of PSDB.

=====================================================================
12. ROBUSTNESS (robustness_matrix.csv, chart 6; 384 cells)
=====================================================================
Share of cells where each user prediction holds:
- H1 100%
- H2 75% (100% in baseline, 2007-split, NME-from-Aug-2011 and Levy-only variants; 17% under the GFC split; 33% under the R9 split)
- H3 100%
- H4 0%
- H5 94%
- H6 87.5%
Sign consistency of the deltas, with medians (10th to 90th percentile):
- ELI positive in 94%, median +0.20 (+0.01 to +0.26). The only negative cells are term-level + ToT+start + crisis-out (24 cells).
- a: 100%, +0.36
- b: 68%, +0.04
- c: 100%, +0.31
- d: 100% negative, -0.25
- e: 100% negative, -0.32
- f: 100% positive, +0.46
- g: 100% positive, +1.25
- FP: 100% positive, +0.87
Other checks:
- Boundary variants barely move anything; ELI median is 0.19-0.21 in every variant.
- Term-level estimates are smaller: baseline term ELI +0.15 (p 0.60) and a +0.38; robustness-cell medians ELI +0.13 and a +0.26 (Lula I-II pooled); FP +1.05.
- The single biggest robustness lever is the coverage rule for Levy/Barbosa: admitting R6 cuts dELI from +0.26 to +0.14 and dA from +0.56 to +0.39.

=====================================================================
13. WHAT CANNOT BE CONCLUDED
=====================================================================
1. Sample size: n = 8 eligible regimes (9 for FP).
   - The permutation floor is 0.029 and the best sub-index p is 0.10-0.11. Nothing survives BH.
   - Regimes of the same president (R3/R4; R5/R6; R3/R4/R9) are not independent.
   - These are effect sizes with bands, not significance claims.
2. Outcomes vs policy:
   - Debt changes (F4), reserve accumulation (X1), the ToT/REER-adjusted trade share (T2) and credit stocks (C1, C2b, C4) are outcomes.
   - They carry inherited positions and the 2003-11 commodity boom.
   - ToT and start-state adjustments do not change signs, but they cannot remove regime-specific luck.
   - Lagged credit stocks penalise Temer for Dilma's BNDES build-up.
3. Coded components (M6, S4, L4, T4, FP1-FP5) are single-coder judgements, each tied to a sourced fact.
   - FP depends on the coding of FP5 (trade diplomacy) and FP4.
4. Missing or fallback components:
   - S1 (Petrobras pricing) uses a weak fallback.
   - S3 (privatisations) and X3 (FX swaps) are missing.
   - Pre-2007 earmarked credit, pre-2016 BCB r* and pre-2008 IOF are absent.
   - R1 has no monetary sub-index (no inflation targeting before 1999).
   - R9's (g) is missing in the baseline (KAOPEN ends 2023).
5. External-source confidence: several facts rest on Wikipedia lists or press (medium confidence in external_facts.csv). Heritage before 2010 is back-cast.
6. Lula III is incomplete: 2026 runs Jan-Aug and is flagged partial; election-year dynamics are not yet in the data.
7. No Congress controls. The PT never held a congressional majority, and policy reflects coalition bargaining. That work lives in scratchpad/congress/, which does not exist in this session; no coalition metrics were built here.
8. "Liberal" here means realised macro orthodoxy and market-friendliness. It does not mean ideology, and it says nothing about distributional outcomes beyond (f).

=====================================================================
14. LULA IV (one paragraph; conditional)
=====================================================================
First round 2026-10-04: Flávio Bolsonaro 47.03%, Lula 45.16%; run-off 2026-10-25 (exports fact C63). If Lula wins:
- Team continuity is likely: Haddad's economic team, and Galípolo at the BCB with a term to end-2028 under LC 179 (RA56).
- Lula IV would start with the BCB at 13.75% after five 2026 cuts (C62). It would be bound by the arcabouço (LC 200 / LC 211) and the Law 15,077 cap of at most 2.5% real minimum-wage gains.
- Lula III, the best guide, resembles Lula-Mantega on its overall profile and Temer on fiscal/monetary: an autonomous, hawkish BCB; small primary deficits with rising debt; more SOE and industrial-policy intervention than Lula I; strong transfers; and progressive foreign policy.
- The politics report's left-branch scenarios: primary balance history range 0.9 to 3.0% of GDP (model 0.8-2.3), real policy rate model 7.0-8.9%, gross debt 2030 84-107% (median-pb 93; Lula III run-rate 104). Those fiscal ranges are dominated by Lula I-II surpluses. On this study's evidence, the Lula III run-rate (-0.9% primary, +3.1 pts debt/yr) is the more relevant prior.
- None of this assumes the outcome.

=====================================================================
FILES (scratchpad/pt_liberalism/)
=====================================================================
Core outputs:
- preregistration.txt
- pt_liberalism_study.py (run: .venv/bin/python pt_liberalism_study.py)
- anchors.py
- results.json
- regime_table.csv
- index_components.csv
- external_facts.csv: 175 facts, RA/RB/RC/RM plus reused exports facts
- external_series.csv: SGS plus ext series
- robustness_matrix.csv
- rhetoric_scores.csv
External inputs:
- ext/: raw research files, corpus/ with manifest.csv, cmn_targets.csv, neutral_rate.csv, fp_coding.csv, local_content.csv, trade_agreements_sice.csv
- cache/: SGS CSVs, o.pkl
Charts:
- charts/1_subindex_timeline.html
- charts/2_trajectory_2d.html
- charts/3_regime_scorecard.html
- charts/4_rhetoric_vs_action.html
- charts/5_external_crosscheck.html
- charts/6_robustness_heatmap.html
- charts/7_components_small_multiples.html

