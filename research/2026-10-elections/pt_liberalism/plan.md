# Plan: "Is Lula's PT as left as people think?" — a regime-level economic-liberalism study

Executor dir: `/private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/pt_liberalism/`
Warehouse: `/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb` (`duckdb.connect(DB, read_only=True)`). Python: `/Users/zkid18/proj-personal/brazil-macro/.venv/bin/python` (duckdb, pandas, numpy, plotly). Today 2026-10-05; warehouse data end 2026-08/09; Lula III incomplete.

## 0. What exploration found (carry forward verbatim)

**0.1 Verified in-warehouse series (id → freq, coverage, `catalog.agg`).**
- Fiscal: `primary_balance_gdp` (M, 2002-11→2026-08, +=surplus, agg last), `primary_result_nfsp` (same, NFSP sign), `nominal_deficit_gdp`, `interest_bill_gdp` (M, 2002-11→), `gross_public_debt_gdp` (M, 2006-12→2026-08, last), `net_public_debt_gdp` (M, 2001-12→2026-08), `implicit_interest_rate`, `r_minus_g`, `nominal_gdp_growth` (M, 2001→), `gdp_nominal_12m_brl` (M, 2000→). WB (A): `wb/GC.TAX.TOTL.GD.ZS.BR`, `wb/GC.REV.XGRT.GD.ZS.BR`, `wb/GC.NLD.TOTL.GD.ZS.BR`, `wb/GC.DOD.TOTL.GD.ZS.BR`, `wb/GC.XPN.TRFT.ZS.BR` (subsidies+transfers, % of expense), `wb/GC.XPN.TOTL.GD.ZS.BR` (expense % GDP, 2010→2023) — all central-government, 2010→2024 only; `wb/NE.CON.GOVT.ZS.BR` and `wb/NE.CON.GOVT.KD.ZG.BR` (real gov-consumption growth, 1961→2025); `wb/NY.GDP.MKTP.KD.ZG.BR`, `wb/NY.GDP.MKTP.CN.BR` (nominal GDP LCU).
- Monetary: `selic_target` (D, 2000→2026-10-03; step function, 13.75 since 2026-09-17), `real_policy_rate` (M, 2001-12→2026-09), `ipca_12m` (M, 2000→2026-08), `ipca_monthly`, `ipca_administered_prices` (M, % m/m, 2000→2026-08 — **monthly change, must be compounded**), `ipca_services`, `focus_ipca_12m` (D, 2001-12→2026-09-25), `focus_selic_12m` (D, 2000→), `inflation_diffusion`, `gov_real_yield_10y` (D, 2015→), `embi_brazil` (D, 2000→**2024-07-30**).
- Credit: `credit_gdp` (M, 2000→2026-08), `household_credit_balance`/`corporate_credit_balance` (M, 2007-03→), `wb/FS.AST.PRVT.GD.ZS.BR`, `wb/FS.AST.CGOV.GD.ZS.BR`, `wb/GFDD.EI.08.BR` (credit to govt & SOEs % GDP, 1980→2020), `wb/GFDD.OI.20a.BR` (government bank assets % total, **2011→2016 only**), `wb/FR.INR.RINR.BR` (WB real lending rate, 1997→2025).
- Trade: `wb/TM.TAX.MRCH.WM.AR.ZS.BR` (applied weighted, 1989→**2022**), `wb/TM.TAX.MRCH.SM.AR.ZS.BR` (simple), `wb/TM.TAX.MANF.WM.AR.ZS.BR`, `wb/TM.TAX.MRCH.WM.FN.ZS.BR` (MFN), `wb/TM.TAX.MRCH.BR.ZS.BR`/`BC` (bound rate/coverage 1995→2022), `wb/NE.TRD.GNFS.ZS.BR`, `wb/NE.IMP.GNFS.ZS.BR`, `wb/TG.VAL.TOTL.GD.ZS.BR` (1960→2025), `wb/GC.TAX.INTT.RV.ZS.BR` (trade taxes % revenue 2010→24), regional export shares `wb/TX.VAL.MRCH.{HI,R1,R3,R4,R5,R6,AL}.ZS.BR` (1960→**2023**), `china_export_share`, `exports_to_china/us/eu`, `exports_total` (M, 2014→2026-08).
- SOE/Petrobras: `brent_usd` (D), `brl_usd` (D), `company_metrics` for `PETR` (Q, 2012-03→2026-06: revenue, ebit, net_income, capex, dividends_paid, net_debt; **`quarter_end` is VARCHAR — cast**), `total_return_usd@PETR` (M, 2012→), `dividend_yield_ttm@PETR`. **No ANP pump-price, refinery-gate or import-parity series exist** (the `ANP` source holds only production series).
- Labour/social: `ilostat/EAR_INEE_NOC_NB.BRA` (nominal monthly minimum wage, A, 1994→2024: 70→1,412), `wb/FP.CPI.TOTL.BR` (A, 2010=100), `wb/per_sa_cc.cov_pop_tot.BRA` (CCT coverage %, 2006→2022, sparse; 2020 = 5.95 is a definitional anomaly — flag), `wb/per_sa_allsa.cov_pop_tot.BR`, `wb/SI.POV.GINI.BR`, `real_average_income`, `unemployment_rate`.
- External/FX: `fx_reserves` (D, 2000→2026-10-01, US$ mn), `wb/FI.RES.TOTL.MO.BR` (1975→2025), `wb/BN.KLT.PTXL.CD.BR`, `wb/BX.PEF.TOTL.CD.WD.BR`, `wb/BX.KLT.DINV.WD.GD.ZS.BR`, `wb/REER_M.BRA` (1987→2024-10), `wb/PX.REX.REER.BR`, `current_account_usd`.
- Controls: `wb/TOT.BRA` (M, 1991→2025-12), `wb/TT.PRI.MRCH.XD.WD.BR` (A, 2005→2024), `brent_usd`. Environment: `wb/AG.LND.PFLS.HA.BR` (primary forest loss, 2002→2025).
- Governance: `wb/GOV_WGI_RQ_EST.BR` (Regulatory Quality, 1996→2024, biennial to 2002): 0.19 (2003, 2010–12) → −0.29 (2024).
- Missing from warehouse (tested): any inflation-target series, earmarked/BNDES/TJLP series, public-bank credit share, fuel prices, IOF rates, trade-agreement counts, antidumping counts, privatisation values, Fraser/Heritage. All external (section 2).

**0.2 External BCB SGS codes verified live on 2026-10-05 via `ingest/bcb_sgs.py: meta()` (the JSON host `api.bcb.gov.br` is NXDOMAIN; use the SOAP helper).** Import pattern that writes nothing to the project:
```python
import sys; sys.path.insert(0, '/Users/zkid18/proj-personal/brazil-macro/ingest'); import bcb_sgs
vals = bcb_sgs.fetch_values([20593], '01/03/2007', '01/10/2026')[20593]   # [(iso_date, value), ...]
```
Pull **one code per call** (a batch with a bad/annual code returns HTTP 500; `fetch_values([13521], …)` for the annual target fails with "list index out of range" — hard-code targets from CMN resolutions instead, see 2.2). Verified codes: 20539 total credit balance (M, 2007-03→2026-08), 20593 **earmarked** (recursos direcionados) total, 20542 free-resources total, 20625 free credit % GDP, 2007 credit by **public-control** banks (M, 2000→2026-08), 2043 private-control banks, 256 TJLP (M, 2000→2026-10), 27572 TLP monthly factor, 11428 IPCA free items (% m/m), 4449 IPCA administered (% m/m; already in warehouse), 13521 inflation target (A; `meta` works: 3.00 for 2026). Codes 2044/3995/7408/27803 are **not** what their numbers suggest; do not use.

**0.3 Anchor numbers (reproduce first; stop and report if any differs by > 0.05).**
Regime monthly means with exact boundaries from section 1 (prototype regimes; `v_observations`, `date <= current_date`):

| Regime | real_policy_rate | primary_balance_gdp | ipca_12m | selic_target | embi_brazil | credit_gdp first→last | gross debt first→last | net debt first→last |
|---|---|---|---|---|---|---|---|---|
| FHC II (1999→2002) | 13.28 (2001-12→) | 3.25 (2002-11→) | 7.44 (2000→) | 18.09 | 995 | 26.3→25.8 | – | 31.3→37.7 |
| Lula-Palocci (2003-01→2006-03) | 13.33 | 3.58 | 9.12 | 19.49 | 564 | 25.6→28.1 | – | 37.6→30.8 |
| Lula-Mantega (2006-04→2010-12) | 7.28 | 2.85 | 4.65 | 11.70 | 245 | 28.5→44.1 | 55.5 (2006-12)→51.8 | 30.5→25.8 |
| Dilma NME (2011-01→2014-12) | 4.20 | 2.08 | 6.14 | 9.91 | 203 | 43.7→52.2 | 52.4→56.3 | 25.5→20.8 |
| Levy (2015-01→2016-05-11) | 7.36 | −1.19 | 9.25 | 13.68 | 377 | 52.1→51.9 | 57.2→67.6 | 20.8→26.1 |
| Temer (2016-05-12→2018-12) | 5.25 | −2.05 | 4.57 | 9.77 | 286 | 51.3→46.6 | 67.5→75.3 | 28.6→39.5 |
| Bolsonaro (2019→2022) | 2.30 | −2.26 | 6.14 | 6.50 | 292 | 46.0→53.2 | 75.4→71.7 | 40.1→47.0 |
| Lula III (2023→2026-08) | 8.88 | −0.84 | 4.61 | 13.21 | 223 (→2024-07) | 52.9→55.4 | 71.4→82.9 | 46.3→60.8 |

Yearly real_policy_rate means: 2003 15.66, 2012 3.17, 2013 2.48, 2020 −0.43, 2021 0.18, 2025 9.71, 2026 10.38. Selic step facts: the 2011 "forced cut" is in the data as 12.50→12.00 effective **2011-09-01** (Copom 2011-08-31); 2012 had 7 cuts to 7.25; 2017 8 cuts; 2025 min 12.25 / max 15.00; 2026 five cuts to 13.75. Focus within-year SD (`focus_ipca_12m`): 2002 2.39, 2003 1.80, 2015 0.44, 2016 0.70, 2021 0.54, 2023 0.65, 2025 0.51, 2026 0.20.
Administered vs headline IPCA (Jan–Dec compounding of monthly changes): 2012 adm 3.65 vs IPCA 5.84; 2013 1.54 vs 5.91; 2014 5.32 vs 6.41; 2015 **18.07** vs 10.67; 2017 7.99 vs 2.95; 2021 16.90 vs 10.06; **2022 −3.83 vs 5.78** (Bolsonaro's election-year fuel/electricity tax cuts); 2023 9.13 vs 4.62; 2025 5.28 vs 4.26.
SGS anchors (year-end shares): earmarked share of credit 33.5% (2007) → 49.9% (2016) → 40.1% (2022) → 43.9% (Aug 2026); public-bank share 36.7% (2006) → 56.0% (2015) → 42.3% (2022) → 41.7% (2026); TJLP yearly mean 11.5 (2003) → 5.00 (2013–14) → 9.17 (2026).
WB tariffs (applied weighted / simple): 1995 10.97/13.23; 2003 9.53/14.39; 2008 6.74/13.08; 2012 7.76/13.75; **2013 10.08/14.81** (Dilma's tariff-line increases); 2019 7.97/13.43; 2022 7.26/13.29. Trade % GDP: 2003 28.1; 2010 22.8; 2019 28.9; 2022 38.8; 2025 35.3. High-income export share: 68.4% (1995) → 51.7% (2010) → 42.6% (2023); EAP-LMIC share 5.8 → 18.4 → 35.8.
Petrobras (annual sums, R$ bn): dividends 2013 5.8, 2015–17 0, 2021 72.2, **2022 194.2, 2023 97.9, 2024 100.3, 2025 45.2**; net income 2014 −21.6, 2015 −34.8; net debt 147 (2012) → 392 (2015) → 225 (2022) → 333 (2025). `total_return_usd@PETR` year-end: 2014 30.0, 2015 13.6, 2022 83.2, 2023 175.9, 2026 324.9.
FX reserves year-end US$ bn: 2002 37.8, 2006 85.8, 2008 193.8, 2011 352.0, 2019 356.9, 2022 324.7, 2026-10-01 362.6.

**0.4 Pitfalls (hard-code as checks).** `first`/`last` are reserved in DuckDB — alias as `first_v`/`last_v`. `company_metrics.quarter_end` is VARCHAR. `v_by_term` merges Lula I–II and Lula III (politics plan 0.2) — never use it. WB annual values dated YYYY-12-31; native monthly dated first-of-month; join on year / `date_trunc('month')`. `v_annual` agg for `selic_target`, `ipca_12m`, `real_policy_rate` is mean; for `fx_reserves`, `primary_balance_gdp`, `gross_public_debt_gdp`, `credit_gdp` it is last. Filter `date <= current_date`; 2026 is never `is_complete`. macOS has no `timeout` binary. Subagents cannot write `.md` → write `report.txt` and `preregistration.txt`. Prior Congress work lives in `scratchpad/congress/` — do not build coalition metrics here.

**0.5 Election context (external, fenced).** First round 2026-10-04: Flávio Bolsonaro 47.03%, Lula 45.16% (exports study facts A49/C63); run-off 2026-10-25. Use only for the one-paragraph Lula IV note.

## 1. Regime registry (unit of analysis)

Half-open `[start, end)`; label, party, lean, and the documented trigger. Every date marked (v) must be confirmed with a primary source (Planalto decree/law page, BCB, DOU, Petrobras RI) and logged in `external_facts.csv` before computation; if a source disagrees, use the source's date.

| id | Regime | Start | End | Defining policy facts to verify (v) |
|---|---|---|---|---|
| R1 | FHC I (non-PT) | 1995-01-01 | 1999-01-15 | Real plan crawling peg; privatisations (Vale 1997, Telebrás 1998); Jan-1999 float (v) |
| R2 | FHC II (non-PT) | 1999-01-15 | 2003-01-01 | Inflation targeting Jun-1999; LRF 2000-05-04; primary-surplus targets under IMF |
| R3 | Lula I orthodox: Palocci/Meirelles (PT) | 2003-01-01 | 2006-03-28 | Palocci resigns 2006-03-27, Mantega sworn 2006-03-28 (v); surplus target raised to 4.25% GDP Feb-2003 (v); EC 41 pension reform 2003-12-19 (v); Meirelles BCB 2003-01→2010-12 |
| R4 | Lula developmentalist: Mantega/PAC (PT) | 2006-03-28 | 2011-01-01 | PAC launched 2007-01-22 (v); Treasury loans to BNDES from MP 453 Jan-2009 (v); IPI cuts Dec-2008; MCMV Mar-2009; IOF 2% on portfolio inflows 2009-10-20 (v), 6% 2010-10 (v) |
| R5 | Dilma "Nova Matriz" (PT) | 2011-01-01 | 2015-01-01 | Surprise Selic cut 2011-08-31 (in data); Plano Brasil Maior 2011-08-02 (v); Petrobras price lag 2011–14; MP 579 electricity 2012-09-11 (v); Inovar-Auto 2012 (v); tariff rises on 100 lines Camex Res. 70/2012 (v); payroll-tax exemptions 2011–14 |
| R6 | Levy austerity (PT) | 2015-01-01 | 2016-05-12 | Levy 2015-01-01→2015-12-18, Barbosa 2015-12-21→2016-05-12 (v); administered-price realignment 2015 (in data); IOF already removed Jun-2013 |
| R7 | Temer (non-PT) | 2016-05-12 | 2019-01-01 | Petrobras import parity Oct-2016 (v); EC 95 spending cap 2016-12-15; labour reform 2017-07-13; TLP Law 13,483 2017-09-21 (v); BNDES repayments to Treasury from 2016 (v) |
| R8 | Bolsonaro/Guedes (non-PT) | 2019-01-01 | 2023-01-01 | EC 103 pensions 2019-11-12; BCB autonomy LC 179 2021-02-24; CET cuts 10% Nov-2021 and 10% May-2022 (v); Eletrobras privatisation Jun-2022 (v); EC 123 fuel-tax cuts Jul-2022 (v) |
| R9 | Lula III: Haddad/Campos Neto→Galípolo (PT) | 2023-01-01 | 2026-08-31 (data end) | Arcabouço LC 200 2023-08-31; EC 132 tax reform 2023-12-20; Petrobras drops import-parity 2023-05-16 (v); extraordinary-dividend fight 2024-03-07, Prates out 2024-05 (v); Nova Indústria Brasil Jan-2024 (v); min-wage rule Law 14,663 2023-08 (v); Galípolo governor 2025-01-01 (v); Selic 15% Jun-2025→(v); EU–Mercosur concluded 2024-12-06, signed 2026-01-17, provisional 2026-05-01 (exports facts C04, C07) |

PT regimes: R3, R4, R5, R6, R9 (n=5). Non-PT: R1, R2, R7, R8 (n=4). Boundary alternatives (robustness grid): R3/R4 split at 2007-01-01 (Lula II) or 2008-09-15 (GFC); R5 start 2011-08-31; R6 end 2015-12-18 (Levy only); R9 split at 2025-01-01 (Galípolo) — reported as R9a/R9b descriptively; term units (Lula I–II, Dilma, Lula III vs FHC, Temer, Bolsonaro) as in the politics study.

## 2. Index design

**Scoring rule (pre-specified).** Every component is converted to an **annual** series 1995–2026 (2026 partial, flagged), with the sign chosen so that **+ = more economically liberal/orthodox**. Components are z-scored across the pooled years 1995–2025; sub-index = mean of available component z's (need ≥ 2); the Economic Liberalism Index **ELI = mean of sub-indices (a), (b), (c), (d), (e), (g)**. Sub-index (f) "Left/social" is kept **separate** (sign: + = more redistributive) and is never inside ELI. Regime score = mean of the regime's annual values (years attributed by the 1-July rule; monthly series attributed exactly to regime dates and also averaged to calendar years). Report both regime-level and term-level versions. Regime enters a sub-index only with ≥ 2 components and ≥ 24 months (or ≥ 2 annual obs).

### (a) Fiscal discipline
| id | Component | Series / source | Transform | Sign |
|---|---|---|---|---|
| F1 | Primary balance % GDP | `primary_balance_gdp` (Dec value) 2002→; **external** 1995–2002 BCB "Necessidades de financiamento do setor público – resultado primário, % PIB, anual" (bcb.gov.br/estatisticas/tabelasespeciais; or IPEAData via `ingest/ipeadata.py` pattern) | annual level | + |
| F2 | Real central-govt primary spending growth minus real GDP growth | **external** Tesouro "Resultado do Tesouro Nacional" série histórica (despesa primária total, monthly 1997→; tesourotransparente.gov.br) deflated by `ipca_monthly`; fallback `wb/NE.CON.GOVT.KD.ZG.BR` − `wb/NY.GDP.MKTP.KD.ZG.BR` | annual pts | − |
| F3 | Change in tax burden | **external** Receita Federal "Carga Tributária no Brasil" (general govt, annual 1995→2024); cross-check `wb/GC.TAX.TOTL.GD.ZS.BR` 2010→24 | Δ pts/yr | − (flag ambiguity; sensitivity: drop F3) |
| F4 | Debt dynamics | Δ`gross_public_debt_gdp` (2007→), Δ`net_public_debt_gdp` (2002→), **external** BCB net debt % GDP annual 1995→2001 (verify `meta(4513)`) | Δ pts/yr | − |
| F5 | Fiscal-rule events (descriptive) | `political_events` 2000-05-04, 2016-12-15, 2023-08-31 | dummy | n/a |

### (b) Monetary orthodoxy
| id | Component | Series / source | Transform | Sign |
|---|---|---|---|---|
| M1 | Real policy rate minus neutral | `real_policy_rate`; neutral r* = **external** BCB Inflation Report estimates (table of IR boxes with dates/URLs, linearly interpolated); fallback 10-yr trailing median of `real_policy_rate`; both reported | annual mean of gap | + |
| M2 | Inflation vs target | Dec `ipca_12m` − target π* (hard-coded CMN targets 1999→2026 with resolution numbers: 1999 8, 2000 6, 2001 4, 2002 3.5, 2003 4 (adj. 8.5), 2004 5.5, 2005 4.5 … 2019 4.25, 2020 4.0, 2021 3.75, 2022 3.5, 2023 3.25, 2024 3.0, 2025+ 3.0 continuous — verify each) | −|dev| | + |
| M3 | Months inside the band | share of months `ipca_12m` ∈ [π*−tol, π*+tol] (tol 2.0 to 2002, 2.5 2003–05, 2.0 2006–16, 1.5 2017→) | share | + |
| M4 | Expectation anchoring | mean(`focus_ipca_12m` − π*) and within-year SD | −gap, −SD | + |
| M5 | Taylor-rule residual ("forced cuts") | `selic_target` − [r* + π^e + 1.5(π^e − π*)], π^e = `focus_ipca_12m` (monthly mean); negative residual = looser than rule | annual mean | + |
| M6 | BCB autonomy | de jure dummy (LC 179 from 2021-02-24); de facto coded 0/1/2: governor retained across transition (Meirelles 2003, Campos Neto 2023), governor replaced at transition (Tombini 2011, Goldfajn 2016, Campos Neto 2019 — Ilan→RCN), public presidential pressure episodes (2011–12 Dilma; 2023–24 Lula vs Campos Neto) | ordinal | + |

### (c) State role in credit (+ = smaller state)
| id | Component | Series / source | Sign |
|---|---|---|---|
| C1 | Earmarked share of credit | SGS 20593/20539 (2007-03→); pre-2007 **external** BCB old-methodology series (verify via `meta` on "recursos direcionados" codes; else start 2007) | − |
| C2 | BNDES disbursements % GDP | **external** BNDES "Desembolsos anuais" (bndes.gov.br transparência, 1995→2025) ÷ `wb/NY.GDP.MKTP.CN.BR`; plus Treasury-to-BNDES loan stock (BNDES/Tesouro) | − |
| C3 | TJLP/TLP subsidy | SGS 256 (TJLP) − `selic_target` monthly mean; post-2018 TLP via SGS 27572 (subsidy ≈ 0 by law) | + (less negative = more liberal) |
| C4 | Public banks' share of credit | SGS 2007/(2007+2043) (2000→); cross-check `wb/GFDD.OI.20a.BR` 2011–16 | − |
| C5 | Credit to govt & SOEs % GDP (descriptive) | `wb/GFDD.EI.08.BR` 1995→2020 | − |

### (d) Trade openness
| id | Component | Series / source | Sign |
|---|---|---|---|
| T1 | Applied tariff, weighted & simple | `wb/TM.TAX.MRCH.WM.AR.ZS.BR`, `wb/TM.TAX.MRCH.SM.AR.ZS.BR` (→2022); 2023–25 **external** WTO Tariff Profiles (Brazil MFN simple average) | − |
| T2 | Trade % GDP, ToT/REER-adjusted | `wb/NE.TRD.GNFS.ZS.BR` residual from OLS on log `wb/TOT.BRA` and log `wb/PX.REX.REER.BR` | + (descriptive weight 0.5) |
| T3 | Trade agreements signed/in force per year | **external** list (SICE/OAS, Mercosur, MDIC): Mercosur–India PTA 2004/2009, –Israel 2007, –Egypt 2010, –Palestine 2011, –SACU 2008/16, Brazil–Peru 2016, Brazil–Chile 2018, –Singapore 2023, –EFTA 2025-09-16 (C47), EU–Mercosur 2019/2024/2026; OECD accession request 2017 | + |
| T4 | Local-content rules | coded −1/0/+1 per regime from ANP bidding-round rules (2003–16 rise, 2017 relaxation, 2024 NIB) with sources | + |
| T5 | Antidumping initiations per year | **external** WTO AD statistics by reporting member (Brazil, 1995→2024) | − |
| T6 | Trade taxes % revenue | `wb/GC.TAX.INTT.RV.ZS.BR` (2010→24) | − |

### (e) SOE and market intervention
| id | Component | Series / source | Sign |
|---|---|---|---|
| S1 | Petrobras fuel price vs import parity | **external** ANP weekly pump prices (dados abertos "série histórica de preços de combustíveis", 2004→) and Abicom PPI gap (2017→); pre-2017 gap = Petrobras refinery-gate price (Petrobras RI "histórico de preços") vs USGC gasoline/diesel (EIA) × `brl_usd`; warehouse fallback: residual of log `revenue_usd_bn@PETR` on log `brent_usd` (H1 pattern), `net_income_brl@PETR`, Δ`net_debt_brl_bn@PETR` | −|gap| |
| S2 | Administered-price repression | compounded 12m `ipca_administered_prices` vs free items (SGS 11428 compounded; fallback `ipca_12m`); S2 = −max(0, free − admin) averaged (penalises repression; catch-up years flagged) | + |
| S3 | Privatisations/concessions | **external** count and value per year: BNDES PND results 1991–2002, PPI (ppi.gov.br) 2016→, Eletrobras 2022, airports/roads auctions (ANAC/ANTT) | + |
| S4 | Sectoral intervention events | coded list: MP 579 (2012), Inovar-Auto, 2022 EC 123, 2023 Petrobras policy, dividend fight | − |
| S5 | Petrobras payout vs capex (descriptive) | `dividends_paid_brl@PETR` / (dividends + `capex_brl@PETR`) annual 2012→ | n/a |

### (f) Labour and social — the "left" pillar (+ = more redistributive; outside ELI)
| id | Component | Series / source |
|---|---|---|
| L1 | Real minimum-wage growth | `ilostat/EAR_INEE_NOC_NB.BRA` ÷ `wb/FP.CPI.TOTL.BR` (1994→2024); 2025–26 **external** (R$ 1,518 in 2025; 2026 value v); rule coded (INPC+GDP(t−2) 2007–19 and 2023→; INPC only 2020–22) |
| L2 | Transfers % GDP | `wb/GC.XPN.TRFT.ZS.BR` × `wb/GC.XPN.TOTL.GD.ZS.BR`/100 (2010→23); **external** Bolsa Família/Auxílio Brasil spending % GDP (MDS/Tesouro, 2004→2025) and INSS benefits % GDP (RTN) |
| L3 | CCT coverage | `wb/per_sa_cc.cov_pop_tot.BRA` (sparse; descriptive) |
| L4 | Labour/pension regulation events | 2003 EC 41, 2017 labour reform, 2019 EC 103, 2023 min-wage law — coded |
| L5 | Social spending | cite politics report (health/education % GDP) — do not recompute |

### (g) External and FX
| id | Component | Series / source | Sign |
|---|---|---|---|
| X1 | Reserve accumulation | Δ year-end `fx_reserves` / GDP (`wb/NY.GDP.MKTP.CD.BR`); `wb/FI.RES.TOTL.MO.BR` | + (prudence; weight 0.5) |
| X2 | Capital controls | **external** IOF-on-inflows rate by month (Decrees 6,983/2009, 7,330/2010, 7,412/2010, 8,023/2013) → annual mean rate; cross-check Chinn–Ito KAOPEN (Brazil, 1995→2022, web.pdx.edu/~ito) | − |
| X3 | FX-regime intervention | **external** BCB FX-swap stock (US$ bn, 2013→; BCB open data) and spot sales (2019–20, 2022); warehouse proxy: annual corr(Δ`fx_reserves`, Δlog `brl_usd`) | − (descriptive) |

### 2.2 External cross-checks and rhetoric
- **Fraser EFW** (efotw-2025 master index, Brazil 1995→2023: summary + areas 1–5). **Heritage IEF** (1995→2025; fiscal health, government spending, tax burden, monetary, trade, investment, financial freedom). Map: Fraser area 1/Heritage spending→(a); area 3/monetary freedom→(b); area 4/trade freedom→(d); area 5+financial freedom→(c),(e). Record exact file URLs and vintage in `external_facts.csv`.
- **Party positions**: Manifesto Project (MARPOR) `rile` and `per401/per403/per412/per413` for PT and PSDB if Brazil is covered (check manifesto-project.wzb.eu; API key needed) — else skip and say so. V-Party `v2pariglef` (PT at 2002/06/10/14/18/22 elections) as a secondary anchor.
- **Own text coding (reproducible)**. Corpus A: PT programmes — "Carta ao Povo Brasileiro" (2002-06-22), Programa de Governo 2002, 2006, 2010 (Dilma), 2014, 2022 "Diretrizes" (TSE DivulgaCand PDFs from 2014; FPA archive earlier); comparators: PSDB 1998/2002, "Ponte para o Futuro" (PMDB 2015), Bolsonaro 2018, Flávio 2026 (exports fact A30). Corpus B: Brazil's UN General Debate statements 1995→2024 (UNGDC, Harvard Dataverse doi:10.7910/DVN/0TJX8Y) — same venue every year, every president; for foreign-policy rhetoric. Corpus C (optional): Lula/Dilma inauguration and 1-May speeches (biblioteca.presidencia.gov.br).
  Dictionaries (Portuguese, stemmed, counts per 1,000 tokens): LIBERAL = {responsabilidade fiscal, superávit primário, equilíbrio fiscal, estabilidade, metas de inflação, autonomia do banco central, abertura comercial, livre comércio, concessão/concessões, privatização, competitividade, produtividade, ajuste, reforma tributária, investimento privado}; DEVELOPMENTALIST/LEFT = {desenvolvimentismo, BNDES, indústria nacional, conteúdo local, papel do estado, estatal/estatais, Petrobras, salário mínimo, distribuição de renda, bolsa família, justiça social, trabalhadores, soberania, neoliberal, mercado financeiro (negative context), juros altos}; FP-SOUTH = {sul-sul, BRICS, África, países em desenvolvimento, multilateral, ONU, Mercosul, integração regional, soberania, Amazônia/clima}; FP-WEST = {Estados Unidos, OCDE, aliança, Israel, ocidente, segurança}. Rhetoric score = (LIBERAL − LEFT)/(LIBERAL + LEFT). Caveats to print: dictionary validity, document length, translation, single coder; 20-sentence random audit sample saved to results.json.

## 3. Foreign-policy progressivism axis (FP)

Define "progressive" explicitly as **South–South/autonomist, multilateralist, climate-forward**; values stance toward autocracies is a separate sub-score. Five sub-dimensions coded per regime on −2..+2 with one sourced fact per cell (external_facts.csv): FP1 South–South/autonomy (BRICS 2009 founding, 2014 Fortaleza/NDB, 2019 Brasília summit hosted by Bolsonaro, 2025 Rio; IBSA; Africa embassies; OECD accession push = −; Jerusalem/Abraham = −); FP2 multilateralism (G20-WTO 2003, UNSC reform, COP hosting/withdrawal, Migration Compact exit 2019, COP30 2025, TFFF); FP3 climate/Amazon actions (PPCDAm 2004, Amazon Fund 2008/freeze 2019/relaunch 2023, Forest Code 2012) plus outcome `wb/AG.LND.PFLS.HA.BR` and INPE PRODES annual (external, 1988→); FP4 Venezuela/Russia stance (Chávez alliance, Venezuela Mercosur entry 2012, suspension 2016–17, Guaidó 2019, 2024 non-recognition, Bolsonaro Moscow Feb-2022, Lula "peace club" 2023, Kazan 2024) — reported with and without; FP5 EU–Mercosur/trade diplomacy (1999 launch, 2010 relaunch, 2019, 2024, 2026). Quantitative anchors (descriptive, outcome not policy): `wb/TX.VAL.MRCH.HI.ZS.BR`, `wb/TX.VAL.MRCH.R1.ZS.BR`, `wb/TX.VAL.MRCH.R6.ZS.BR`, `wb/TX.VAL.MRCH.AL.ZS.BR` (→2023), `china_export_share` (2014→); UNGA ideal-point distance Brazil–USA by session (Bailey–Strezhnev–Voeten, Harvard Dataverse doi:10.7910/DVN/LEJUQZ; fallback US State Dept "Voting Practices in the UN" coincidence %). FP composite = mean of FP1–FP5 z's; uncertainty via Monte Carlo ±1 perturbation of every coded cell (2,000 draws). Reuse exports facts B01–B52, C01–C63 where relevant (cite ids; do not re-collect).

## 4. Pre-registered hypotheses (write `preregistration.txt` with UTC timestamp before any index is computed)

Δ = mean(PT regimes) − mean(non-PT regimes), z units. Decision rule for every H: "supported" = sign as hypothesised AND 80% cluster-bootstrap CI excludes 0 AND ≥ 80% of robustness cells share the sign; "refuted" = the mirror with opposite sign; otherwise "indeterminate". Permutation p reported with its floor.

| H | User's hypothesis (prediction) | Competing narrative (prediction) | Statistic |
|---|---|---|---|
| H1 | Fiscal (a) and monetary (b) sub-indices of PT regimes are not systematically less liberal than non-PT, after ToT and starting-condition adjustment: Δ_a, Δ_b ≥ −0.3 z | "PT = fiscal populism": Δ_a ≤ −0.5 z and Δ_b ≤ −0.5 z | Δ raw, ToT-adjusted, start-adjusted; equivalence test (TOST, margin 0.5 z) |
| H2 | Dilma NME (R5) is the outlier: ELI(R5) is the minimum of the 5 PT regimes and lies > 1 within-PT SD below the PT median; excluding R5, Δ_ELI ≥ −0.3 | "NME is the PT's true colours": R5 is within 0.5 SD of R4 and R9; R4 (Mantega) is equally low | rank of R5; gap R5 − median(PT); gap R5 − R4; floor p = 1/5 under exchangeability |
| H3 | Lula III vs Lula-Palocci: fiscal (a) lower (Δ_a(R9−R3) < −0.5 z) but monetary (b) equal or higher (Δ_b(R9−R3) ≥ 0) with M6 (autonomy) and M5 driving it; government-pressure coding negative while BCB-outcome components positive | "Lula III is loose on both": Δ_b(R9−R3) < −0.5 z after neutral-rate adjustment | pairwise regime contrasts with bootstrap CIs; decomposition of (b) into BCB-outcome (M1–M5) vs government-stance (M6) |
| H4 | The "left" appears in (f) and (c): Δ_f ≥ +0.8 z and Δ_c ≤ −0.5 z while |Δ_ELI| < 0.5 z | "Left shows everywhere": Δ_ELI ≤ −0.8 z with (a),(b),(d),(e) all negative | Δ per sub-index; ratio |Δ_f|/|Δ_ELI| with bootstrap CI |
| H5 | Trade openness (d) barely differs by lean: |Δ_d| < 0.5 z (TOST) | "PT = protectionist": Δ_d ≤ −0.5 z (tariff-line rises 2012–13, AD surge, local content) | TOST; T1/T5 individually |
| H6 | Foreign policy diverges more than economic policy: |Δ_FP| > |Δ_ELI| + 0.5 z | "Both diverge": |Δ_FP| ≈ |Δ_ELI| | difference of absolute Δ's, bootstrap CI; 2-D trajectory distances |
| H0 | Rhetoric is lefter than action: Spearman ρ(rhetoric score, ELI) across regime-documents < 0.5, and mean(rhetoric z) < mean(action z) for PT | "Rhetoric = action": ρ > 0.7 | ρ with permutation; paired gap |
| H7 | External indices agree: Spearman ρ(Fraser/Heritage, ELI) across regimes > 0.5 | disagree (< 0.2) | ρ; per-area concordance |

**Power statement (verbatim in the report):** with regime as the unit, 5 PT vs 4 non-PT regimes give C(9,4) = 126 labelings, so the smallest attainable two-sided permutation p is 2/126 = 0.016; with terms (3 vs 3) it is 0.10; H2's within-PT rank test has floor 0.20. Regimes of the same president are not independent. Nothing is expected to clear BH at q = 0.10; the study is an effect-size study with uncertainty bands.

## 5. Methods

### 5.1 Core SQL (prepend to every query; regimes as a VALUES CTE, no temp objects)
```sql
WITH reg(rid, label, party, s, e) AS (VALUES
  (1,'FHC I','PSDB',DATE '1995-01-01',DATE '1999-01-15'), (2,'FHC II','PSDB',DATE '1999-01-15',DATE '2003-01-01'),
  (3,'Lula-Palocci','PT',DATE '2003-01-01',DATE '2006-03-28'), (4,'Lula-Mantega','PT',DATE '2006-03-28',DATE '2011-01-01'),
  (5,'Dilma NME','PT',DATE '2011-01-01',DATE '2015-01-01'), (6,'Levy','PT',DATE '2015-01-01',DATE '2016-05-12'),
  (7,'Temer','MDB',DATE '2016-05-12',DATE '2019-01-01'), (8,'Bolsonaro','PL',DATE '2019-01-01',DATE '2023-01-01'),
  (9,'Lula III','PT',DATE '2023-01-01',DATE '2027-01-01')),
-- monthly panel of native series (daily -> monthly: arg_max for stocks/prices, avg for rates)
m AS (
  SELECT series_id, date_trunc('month', date) AS ym,
         CASE WHEN series_id IN ('fx_reserves','brl_usd','brent_usd') THEN arg_max(value, date) ELSE avg(value) END AS v
  FROM v_observations WHERE date <= current_date AND series_id IN (
    'selic_target','real_policy_rate','ipca_12m','ipca_monthly','ipca_administered_prices','focus_ipca_12m','focus_selic_12m',
    'primary_balance_gdp','nominal_deficit_gdp','interest_bill_gdp','gross_public_debt_gdp','net_public_debt_gdp','credit_gdp',
    'fx_reserves','brl_usd','brent_usd','embi_brazil','gov_real_yield_10y','wb/TOT.BRA','wb/REER_M.BRA','gdp_nominal_12m_brl')
  GROUP BY 1,2),
-- annual panel (WB/ILO), year -> regime in office on 1 July
a AS (
  SELECT a.series_id, a.year, a.value, a.is_complete, r.rid
  FROM v_annual a LEFT JOIN reg r ON make_date(a.year,7,1) >= r.s AND make_date(a.year,7,1) < r.e
  WHERE a.year BETWEEN 1995 AND 2025 AND a.series_id IN (
    'wb/TM.TAX.MRCH.WM.AR.ZS.BR','wb/TM.TAX.MRCH.SM.AR.ZS.BR','wb/TM.TAX.MANF.WM.AR.ZS.BR','wb/NE.TRD.GNFS.ZS.BR','wb/NE.IMP.GNFS.ZS.BR',
    'wb/GC.TAX.INTT.RV.ZS.BR','wb/GC.TAX.TOTL.GD.ZS.BR','wb/GC.REV.XGRT.GD.ZS.BR','wb/GC.XPN.TRFT.ZS.BR','wb/GC.XPN.TOTL.GD.ZS.BR',
    'wb/NE.CON.GOVT.KD.ZG.BR','wb/NY.GDP.MKTP.KD.ZG.BR','wb/NY.GDP.MKTP.CN.BR','wb/NY.GDP.MKTP.CD.BR','wb/FS.AST.PRVT.GD.ZS.BR',
    'wb/GFDD.EI.08.BR','wb/GFDD.OI.20a.BR','wb/FI.RES.TOTL.MO.BR','wb/PX.REX.REER.BR','wb/TT.PRI.MRCH.XD.WD.BR',
    'ilostat/EAR_INEE_NOC_NB.BRA','wb/FP.CPI.TOTL.BR','wb/per_sa_cc.cov_pop_tot.BRA','wb/GOV_WGI_RQ_EST.BR',
    'wb/TX.VAL.MRCH.HI.ZS.BR','wb/TX.VAL.MRCH.R1.ZS.BR','wb/TX.VAL.MRCH.R3.ZS.BR','wb/TX.VAL.MRCH.R6.ZS.BR','wb/TX.VAL.MRCH.AL.ZS.BR',
    'wb/AG.LND.PFLS.HA.BR'))
SELECT * FROM a;   -- or: SELECT m.*, r.rid FROM m JOIN reg r ON m.ym >= r.s AND m.ym < r.e
```
Administered-vs-free inflation (12-month compounding; same pattern for SGS 11428 once pulled):
```sql
SELECT date, 100*(exp(sum(ln(1+value/100)) OVER (ORDER BY date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW))-1) AS adm_12m
FROM v_observations WHERE series_id='ipca_administered_prices' ORDER BY date;
```
Petrobras annual: `SELECT year(CAST(quarter_end AS DATE)) y, sum(dividends_paid_brl), sum(capex_brl), sum(net_income_brl), arg_max(net_debt_brl_bn, quarter_end) FROM company_metrics WHERE entity_id='PETR' GROUP BY 1`.
Selic change counts (for M5 descriptive): `lag(value) OVER (ORDER BY date)` on `selic_target`, count `value <> p` and `value < p` per year.

### 5.2 Estimators (numpy only; seed 0; 5,000 resamples; copy `_ols_r2` from `/Users/zkid18/proj-personal/brazil-macro/hypotheses.py:76-81`)
1. Regime-level Δ with exact permutation over the 126 PT/non-PT labelings; two-stage cluster bootstrap (resample regimes within group, then years within regime) for 80%/95% CIs; length-weighted variant.
2. Year-level y_t = α + β·PT_t + ε with regime-cluster bootstrap (identical point estimate; readers expect it).
3. ToT adjustment: for each annual component, OLS on Δlog ToT_t and log ToT_t (1995–2025; `wb/TOT.BRA` annual mean, 2026 proxied by Brent and flagged), re-run 1–2 on residuals; also Brent as third regressor 2000+.
4. Starting conditions: regress each regime's sub-index on its start-level state (debt, real rate, IPCA, unemployment at start month) pooled across regimes; report residual Δ. Flag that R3, R6, R7, R9 all start in or after crises.
5. Crisis exclusion: drop 2009, 2015–16, 2020 (pre-specified); sensitivity drop 2002–03.
6. Multiple comparisons: BH at q = 0.10 across the 7 sub-index Δ's (family 1) and across the ~30 components (family 2); report q-values even though the floor makes passing impossible.
7. Robustness grid: {boundaries: baseline / Lula split 2007 / Lula split 2008-09 / NME from 2011-08-31 / Levy-only R6 / R9 split 2025} × {unit: regime / term / year-cluster} × {adjustment: raw / ToT / ToT+start} × {crisis years: in / out} × {F3 in / out} × {FP4 in / out} → `robustness_matrix.csv` with sign-consistency share per hypothesis.
8. Rhetoric: token counts per document → scores; bootstrap over sentences for CIs; Spearman vs ELI.

## 6. Deliverables and run order

Files in `scratchpad/pt_liberalism/`: `preregistration.txt` (sections 1, 2 signs, 4, 5.2.7 verbatim, timestamp; script asserts it exists before computing), `pt_liberalism_study.py` (functions: `regimes()`, `monthly_panel()`, `annual_panel()`, `pull_sgs(code, start)` → CSV cache in the executor dir only, `load_external()`, `components()`, `zscore_pool()`, `subindex()`, `eli()`, `fp_axis()`, `rhetoric()`, `perm_test()`, `cluster_bootstrap()`, `tot_adjust()`, `start_adjust()`, `robustness_grid()`, `bh()`, `charts()`, `write_outputs()`), `results.json` (every number with value, series_id/fact_id, source, last_date, sql), `regime_table.csv` (rid, label, party, start, end, months, per-sub-index score, ELI, FP, Fraser, Heritage, rhetoric, n components), `index_components.csv` (component_id, sub_index, series_ids/fact_ids, source, freq, coverage, transform, sign, annual values pivoted or long, z), `external_facts.csv` (same schema as the exports study: fact_id, claim, date, source_url, publisher, accessed, used_in (component/regime ids), confidence, channel), `external_series.csv` (long: series_key, date, value, source_url, accessed — all SGS/BNDES/ANP/Fraser/Heritage/UNGA/tariff/AD pulls), `robustness_matrix.csv`, `rhetoric_scores.csv`, `charts/`: `1_subindex_timeline.html` (7 panels, regime bands coloured by party, events as vlines), `2_trajectory_2d.html` (ELI × FP by regime, chronological arrows, Monte-Carlo error bars), `3_regime_scorecard.html` (heatmap regimes × sub-indices + ELI + external indices), `4_rhetoric_vs_action.html`, `5_external_crosscheck.html` (Fraser/Heritage vs ELI), `6_robustness_heatmap.html`, `7_components_small_multiples.html` (admin vs free inflation, earmarked share, public-bank share, TJLP−Selic, tariffs, primary balance, Taylor residual, Petrobras payout). `report.txt` (and the same text in the final message): Summary with per-pillar verdict table (supported / partly / refuted for H0–H7); Data constraints (section 0 verbatim); Regime registry with verified sources; Pre-registration; Results per sub-index with SQL shown; 2-D trajectory reading; Rhetoric vs action; External-index concordance; Robustness; What cannot be concluded (n = 9 regimes, same-president dependence, outcome-vs-policy confounds in T2/X1/trade shares, external-source confidence, no Congress controls — see `scratchpad/congress/`); one paragraph on Lula IV (team continuity Haddad/Galípolo whose BCB term runs to end-2028, arcabouço constraints, which past regime 2023–26 most resembles; cite politics report scenarios, do not redo them).

Run order: reproduce anchors (0.3) → write preregistration.txt → pull/verify external data and log facts (stop and list gaps if a primary source cannot be found; never silently substitute) → panels → components → sub-indices and ELI → FP axis → rhetoric → tests H0–H7 → adjustments → robustness → BH → charts → report. If any anchor differs, stop and report.

### Critical Files for Implementation
- `/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb` — all verified series (`v_observations`, `v_annual`, `company_metrics`, `political_terms`, `political_events`)
- `/Users/zkid18/proj-personal/brazil-macro/ingest/bcb_sgs.py` — `fetch_values()` (line 161) and `meta()` (line 186): the only working path to the external SGS codes 20593/20539/2007/2043/256/27572/11428
- `/private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/politics/plan.md` and `politics/report.md` — term keys, date conventions, ToT control, term means to reconcile with, scenarios to cite
- `/private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/exports/external_facts.csv` — fact schema to reuse and the EU–Mercosur/BRICS/China/Petrobras facts (B01–B52, C01–C63) for the FP axis
- `/Users/zkid18/proj-personal/brazil-macro/semantic/views.sql` — `v_annual` agg semantics and the `v_by_term` merge bug to avoid
- `/Users/zkid18/proj-personal/brazil-macro/hypotheses.py` — numpy OLS helper (`_ols_r2`, lines 76–81) and the H1 Petrobras-revenue-on-Brent pattern reused for the S1 fallback