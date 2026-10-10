# Plan: Brazil political lean vs economic and market outcomes, 1985–2026, with conditional 2027–2030 scenarios

## 0. What exploration found (executor must carry these forward)

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

**0.9 Anchor numbers already computed (reproduce first; stop if any differs).** Annual means by president, year attributed to president in office on July 1:

| Metric (series) | Sarney 85–89 | Collor 90–92 | Itamar 93–94 | FHC 95–02 | Lula I–II 03–10 | Dilma 11–15 | Temer 16–18 | Bolsonaro 19–22 | Lula III 23–25 |
|---|---|---|---|---|---|---|---|---|---|
| GDP growth `wb/NY.GDP.MKTP.KD.ZG.BR` | 4.39 | −1.29 | 5.39 | 2.43 | (merged 3.75 in v_by_term — recompute split) | 1.17 | −0.06 | 1.43 | — |
| GFCF %GDP `wb/NE.GDI.FTOT.ZS.BR` | 22.45 | 19.07 | 20.02 | 18.53 | — | 19.99 | 15.06 | 16.94 | — |
| Gini `wb/SI.POV.GINI.BR` | 59.62 | 56.80 | 60.10 | 59.17 | — | 52.60 | 53.53 | 51.78 | — |
| WGI CC `wb/GOV_WGI_CC_EST.BR` | — | — | — | 0.12 | — | −0.09 | −0.41 | −0.39 | — |

Quarterly GDP (`wb/NYGDPMKTPSAKD_Q.BRA`, quarter attributed by mid-quarter date), annualised growth first→last quarter of term: Collor 2.53, Itamar 7.34, FHC 1.92, Lula I–II 4.29, Dilma −0.18, Temer 1.28, Bolsonaro 1.67, Lula III 2.42 (2023Q1–2025Q4). Monthly term means (exact term dates): `real_policy_rate` FHC(2001-12→2002) 13.28, Lula I–II 9.74, Dilma 5.02, Temer 5.25, Bolsonaro 2.30, Lula III 8.88; `primary_balance_gdp` Lula I–II 3.15, Dilma 1.22, Temer −2.05, Bolsonaro −2.26, Lula III −0.84; `ipca_12m` FHC(2000–02) 7.44, Lula I–II 6.46, Dilma 6.95, Temer 4.57, Bolsonaro 6.14, Lula III 4.61; `gross_public_debt_gdp` Lula I–II(2006-12→) 56.96, Dilma 55.72, Temer 72.93, Bolsonaro 78.74, Lula III 76.20. Calendar-year `ibovespa_usd` returns: 2002 −45.5, 2003 +141.3, 2008 −55.5, 2015 −41.0, 2016 +66.5, 2024 −29.9, 2025 +50.8, 2026 YTD +22.7. Event prototypes (t−1 → t+60 trading days): 2002-10-27 BRL 3.80→3.49, EMBI 1785→1398, Ibov USD 2,634→3,002 (panic peaked at t−20: BRL 3.89, EMBI 2397); 2014-10-26 Ibov USD 20,940→18,708, BRL 2.48→2.60, EMBI 243→288; 2016-04-17 BRL 3.53→3.29, real 10y 6.14→6.16; 2018-10-28 Ibov USD 23,323→26,669, real 10y 4.84→4.24; 2022-10-30 BRL 5.35→5.10, Ibov USD 21,428→22,396, real 10y 5.83→6.16.

---

## 1. Inventory

### 1.1 Views and tables
- `political_terms` (9 rows, above), `political_events` (34 rows) — built from `/Users/zkid18/proj-personal/brazil-macro/registry/*.csv` at `pipeline.py:584`.
- `v_politics` = `v_observations LEFT JOIN political_terms ON date >= start AND date < end` (raw-date attribution); `v_by_term` = AVG by (series, president, lean) — merges the two Lula presidencies. Use only `v_observations`, `v_annual` (with `is_complete`), `catalog.agg`.
- Gold tables to cite, not recompute: `hypothesis_tests` (L3 r−g = +5.06 pts as of 2026-08; L1 debt-service; H5 Ibovespa USD $99 for $100 since 2012), `book_scorecard` (GDP 4.50% 2004–10 vs 0.55% 2015–23; debt 83%, interest 8.9%, primary −0.6%), `derived_metrics` (`debt_stabilizing_primary_surplus_gap` 2026 = 6.9 pts using real rate 9.1 vs Focus growth; `r_g_spread` 7.69).

### 1.2 Pre-registered metric list (verified ids; coverage; transform; which terms it reaches)

Buckets are symmetric: each side's preferred scorecard appears in full. "Transform" is fixed now, before results.

**A. Growth and investment**
| # | Metric | Series (source, freq, coverage) | Transform at term level | Terms covered |
|---|---|---|---|---|
| A1 | Real GDP growth | `wb/NY.GDP.MKTP.KD.ZG.BR` (WB, A, 1961→2025); `wb/NYGDPMKTPSAKD_Q.BRA` (Q, 1990Q1→2025Q4) for exact boundaries; `ibc_br` (BCB, M, 2003→2026-07) for 2026 | mean of annual; quarterly annualised first→last | all 9 |
| A2 | GDP per capita growth | `wb/NY.GDP.PCAP.KD.ZG.BR` (A, 1961→2025) | mean | all 9 |
| A3 | GFCF % GDP | `wb/NE.GDI.FTOT.ZS.BR` (A, 1970→2025) | mean level and end−start change | all 9 |
| A4 | Industrial production growth | `wb/IPTOTSAKD_M.BRA` (GEM, M, 1991→2025-12) | annualised log change over term | 2–9 |
| A5 | Output per worker growth | `ilostat/SDG_0821_NOC_RT.BRA` (A, 2000→2025) | mean | 4(partial)–9 |

**B. Prices, rates, money**
| B1 | Inflation | `wb/NY.GDP.DEFL.KD.ZG.BR` (A, 1961→2025) as `log(1+π/100)`; `ipca_12m` (BCB, M, 2000→2026-08) Dec-level | mean of log-inflation; mean 12m IPCA | all 9 (IPCA 4–9) |
| B2 | Ex-ante real policy rate | `real_policy_rate` (derived, M, 2001-12→2026-09); ex-post `selic_target − ipca_12m` (2000→) | mean | 4(tail)–9 |
| B3 | Inflation-expectation anchoring | `focus_ipca_12m` (Focus, D, 2001-12→2026-09-25) | term mean and within-term std | 4(tail)–9 |
| B4 | Real lending rate | `wb/FR.INR.RINR.BR` (A, 1997→2025) — WB real *lending* rate, not policy | mean | 4–9 |
| B5 | Credit to private sector % GDP | `credit_gdp` (BCB, M, 2000→2026-08); `wb/FS.AST.PRVT.GD.ZS.BR` (A, 1960→2025) | end−start change | all 9 (WB) |

**C. Fiscal**
| C1 | Primary balance % GDP | `primary_balance_gdp` (derived from NFSP, M, 2002-11→2026-08); `wb/GC.NLD.TOTL.GD.ZS.BR` (A, 2010→2024) alt | mean | 5–9 |
| C2 | Gross debt % GDP change | `gross_public_debt_gdp` (BCB, M, 2006-12→2026-08) | end−start, pts | 5(from 2006-12)–9 |
| C3 | Net debt % GDP change | `net_public_debt_gdp` (BCB, M, 2001-12→2026-08) | end−start | 4(tail)–9 |
| C4 | Interest bill % GDP | `interest_bill_gdp` (M, 2002-11→2026-08) | mean | 5–9 |
| C5 | Government consumption % GDP | `wb/NE.CON.GOVT.ZS.BR` (A, 1960→2025) | mean, change | all 9 |
| C6 | Tax revenue % GDP | `wb/GC.TAX.TOTL.GD.ZS.BR` (A, 2010→2024) | mean | 6–9 (descriptive) |

**D. External and markets**
| D1 | USD equity return | `wb/DSTKMKTXD_M.BRA` (M, 1994→2025) chained to `ibovespa_usd` (derived, D, 2000→2026-10-01) | annualised log return, term start→end (first obs ≥ start to last obs < end) | 4–9 (3 partial) |
| D2 | BRL vs USD | `brl_usd` (BCB, D, 2000→2026-10-02); `wb/DPANUSSPB_M.BRA` (M, 1988→2025) | annualised log change (nominal, 1995+ only) | 4–9 |
| D3 | Real effective exchange rate | `wb/REER_M.BRA` (M, 1987→2024-10); `wb/PX.REX.REER.BR` (A, 1980→2025) | mean level and change | all 9 |
| D4 | Country risk | `embi_brazil` (IPEAData, D, 2000→**2024-07-30**) | mean, change | 4(tail)–8, 9 partial |
| D5 | 10y real yield | `gov_real_yield_10y` (Tesouro, D, 2015→2026-10-02) | mean, change | 6(tail)–9 |
| D6 | Current account % GDP | `wb/BN.CAB.XOKA.GD.ZS.BR` (A, 1975→2025) | mean | all 9 |
| D7 | FDI inflows % GDP | `wb/BX.KLT.DINV.WD.GD.ZS.BR` (A, 1970→2025) | mean | all 9 |
| D8 | Reserves, months of imports | `wb/FI.RES.TOTL.MO.BR` (A, 1975→2025); `fx_reserves` (D, 2000→) | end−start | all 9 |
| D9 | Exports % GDP | `wb/NE.EXP.GNFS.ZS.BR` (A, 1960→2025) | change | all 9 |
| D10 | Market cap % GDP | `wb/CM.MKT.LCAP.GD.ZS.BR` (A, 2000→2025) | change | 5–9 |

**E. Labour and distribution**
| E1 | Unemployment | `wb/SL.UEM.TOTL.ZS.BR` (ILO modelled, A, 1991→2025); `unemployment_rate` (IBGE, M, 2012-03→2026-08) | mean and end−start | 2–9 |
| E2 | Informality | `wb/JI.EMP.IFRM.ZS.BRA` (A, 1981→2020); `ilostat/SDG_0831_SEX_ECO_RT.BRA` (A, 2009→2025) | within-series change only | 1–8 / 6–9 |
| E3 | Real minimum wage | `ilostat/EAR_INEE_NOC_NB.BRA` (A, 1994→2024) ÷ `wb/FP.CPI.TOTL.BR` (2010=100, A, 1980→2025) | annualised log change | 4–9 (9 to 2024) |
| E4 | Real average labour income | `real_average_income` (IBGE, M, 2012-03→2026-08) | annualised change | 6(tail)–9 |
| E5 | Gini | `wb/SI.POV.GINI.BR` (A, 1981→2024; no 1991/1994/2000/2010) | end−start | all 9 |
| E6 | Poverty headcount $3.00 / $8.30 (2021 PPP) | `wb/SI.POV.DDAY.BR`, `wb/SI.POV.UMIC.BR` (A, 1981→2024) | end−start | all 9 |
| E7 | Income share bottom 20% / top 10% | `wb/SI.DST.FRST.20.BR`, `wb/SI.DST.10TH.10.BR` | end−start | all 9 |
| E8 | Labour income share | `ilostat/LAP_2GDP_NOC_RT.BRA` (A, 2004→2025) | change | 5–9 |
| E9 | Earnings Gini | `ilostat/EAR_EMTG_SEX_NB.BRA` (A, 1989→2025, filter value>0) | change | 1(tail)–9 |

**F. Health, education, safety**
| F1 | Infant mortality | `wb/SP.DYN.IMRT.IN.BR` (A, 1960→2024) | annualised log change (trend-dominated; low power) | all 9 |
| F2 | Life expectancy | `wb/SP.DYN.LE00.IN.BR` (A, 1960→2024) | change/yr | all 9 |
| F3 | Govt health spend % GDP | `wb/SH.XPD.GHED.GD.ZS.BR` (A, 2000→2023) | mean | 5–9 |
| F4 | Education spend % GDP | `wb/SE.XPD.TOTL.GD.ZS.BR` (A, 1995→2022) | mean | 4–8 |
| F5 | Homicide rate | `homicide_rate` (WHO, A, 2000→2023); `homicide_deaths` (DATASUS, M, 1996→2026-05) ÷ `population` | change | 4(tail)–9 |
| F6 | Social safety-net coverage | `wb/per_sa_allsa.cov_pop_tot.BR` (A, 2006→2022) | descriptive | 5–8 |

**G. Institutions**
| G1–G6 | WGI Control of Corruption, Government Effectiveness, Rule of Law, Regulatory Quality, Voice, Political Stability | `wb/GOV_WGI_{CC,GE,RL,RQ,VA,PV}_EST.BR` (A, 1996→2024, biennial to 2002) | end−start | 4–9 |

**H. Environment**
| H1 | Primary forest loss | `wb/AG.LND.PFLS.HA.BR` (A, 2002→2025) | mean ha/yr | 5–9 |
| H2 | LULUCF CO2 | `wb/EN.GHG.CO2.LU.MT.CE.AR5.BR` (A, 2000→2022 after dropping 2023) | mean | 5–8 |
| H3 | CO2 per capita ex-LULUCF | `wb/EN.GHG.CO2.PC.CE.AR5.BR` (A, 1970→2024) | change | all 9 |

**Controls:** `wb/TOT.BRA` (M), `wb/TT.PRI.MRCH.XD.WD.BR` (A), UVI ratio `wb/TX.UVI.MRCH.XD.WD.BR / wb/TM.UVI.MRCH.XD.WD.BR` (A, 1980→2024), `brent_usd` (D, 2000→), `wb/DXGSRMRCHNSXD_M.BRA` (M export price). Build one annual ToT series: TT.PRI where available, else UVI ratio rescaled to TT.PRI on 2005–2024 overlap.

Total: ~40 metrics; **26 primary** (A1–A3, B1–B2, C1–C2, C4, D1–D3, D6–D7, E1, E3, E5–E6, F1, F5, G1–G3, H1, plus composites) and the rest secondary/descriptive. Minimum data rule: a term enters a metric only with ≥ 2 annual or ≥ 12 monthly observations inside the term (Itamar and Collor will drop out of several).

---

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

## 3. Methods

### 3.1 Term key and attribution SQL (CTE to prepend to every query; no temp objects needed)
```sql
WITH terms AS (
  SELECT row_number() OVER (ORDER BY start) AS term_id,
         president || ' ' || strftime(start, '%Y') AS term_label,
         start, "end", president, party, lean,
         CASE lean WHEN 'left' THEN 'left' WHEN 'centre' THEN 'centre' ELSE 'right' END AS lean3  -- coding A
  FROM political_terms),
-- annual: year t -> president in office on 1 July of t (majority rule); lag1: 1 July of t-1
yr AS (
  SELECT a.series_id, a.year, a.value, a.is_complete,
         t0.term_id AS term_id_c, t1.term_id AS term_id_lag1,
         (EXTRACT(year FROM t0.start) = a.year) AS is_first_year
  FROM v_annual a
  LEFT JOIN terms t0 ON make_date(a.year,7,1) >= t0.start AND make_date(a.year,7,1) < t0."end"
  LEFT JOIN terms t1 ON make_date(a.year-1,7,1) >= t1.start AND make_date(a.year-1,7,1) < t1."end"
  WHERE a.year BETWEEN 1985 AND 2025 AND a.series_id IN (...))
SELECT * FROM yr;
```
Monthly/daily: `JOIN terms t ON o.date >= t.start AND o.date < t."end"` (exact); lag-1 variant uses `o.date - INTERVAL 12 MONTH`. Quarterly GDP: attribute by `date - INTERVAL 45 DAY` (mid-quarter). Term start/end values for "change" metrics: `arg_min(value, date)` / `arg_max(value, date)` within `[start, end)`; for Lula III, end = last available date, flagged `incomplete = TRUE`. Year-end panel for returns:
```sql
SELECT series_id, EXTRACT(year FROM date)::INT AS year, arg_max(value, date) AS year_end
FROM v_observations WHERE series_id IN ('ibovespa_usd','brl_usd','wb/DSTKMKTXD_M.BRA','wb/DPANUSSPB_M.BRA','wb/REER_M.BRA','fx_reserves','embi_brazil','gov_real_yield_10y')
  AND date <= current_date GROUP BY 1,2;
```
Monthly panel (pivot in pandas), aggregating daily with `arg_max` for prices/FX and `avg` for rates:
```sql
SELECT series_id, date_trunc('month', date) AS ym,
       CASE WHEN series_id IN ('ibovespa_usd','brl_usd','brent_usd','fx_reserves','wb/DSTKMKTXD_M.BRA') THEN arg_max(value, date) ELSE avg(value) END AS v
FROM v_observations WHERE date <= current_date AND series_id IN ('ibovespa_usd','brl_usd','brent_usd','embi_brazil','selic_target','focus_ipca_12m','focus_selic_12m','focus_gdp_growth','focus_fx','real_policy_rate','ipca_12m','gov_real_yield_10y','gov_nominal_yield_5y','primary_balance_gdp','gross_public_debt_gdp','net_public_debt_gdp','interest_bill_gdp','unemployment_rate','real_average_income','credit_gdp','ibc_br','wb/TOT.BRA','wb/IPTOTSAKD_M.BRA','wb/REER_M.BRA','wb/DXGSRMRCHNSXD_M.BRA','fx_reserves')
GROUP BY 1,2 ORDER BY 2,1;
```

### 3.2 Estimators (all numpy; seed = 0; 5,000 resamples)
1. **Term-level difference in means** (unit = term): Δ = mean(left) − mean(right); exact permutation of lean labels across terms when the number of labelings ≤ 5,000 (always true here), else random. Report Δ, permutation p, the design's minimum attainable p, and an 80%/95% CI from a **cluster (term) bootstrap** on the underlying annual/monthly observations. Length-weighted version as robustness.
2. **Year-level with term clusters**: y_it = α + β·left_i + ε; cluster bootstrap over terms; identical point estimate to the weighted term mean, included because readers expect it.
3. **Global-cycle adjustment**: for each annual metric, OLS on the full 1985–2025 sample `y_t = a + b1·Δlog ToT_t + b2·log ToT_t (+ b3·Δlog Brent_t, 2000+ only) + e_t`; re-run 1 and 2 on `e_t`. Also the reverse: lean dummies first, then ask whether adding ToT reduces the lean coefficient (report both R² pieces = Q0). Keep ≤ 3 regressors; n ≈ 40 years.
4. **Inherited conditions**: (a) lag-1 attribution; (b) drop first year of each term; (c) for level metrics (debt, Gini, unemployment, real rate), regress the term change on the start level pooled across terms and report the lean difference in the residual ("starting-point-adjusted change").
5. **Rank-based check**: Spearman/rank version of 1 (robust to hyperinflation outliers).
6. **Within-president contrast**: Lula I–II vs Lula III and FHC I vs FHC II (split at 2007/1999) — if lean were the driver, same-lean, same-person terms should look alike; if ToT drives, they should differ with the cycle. Descriptive, no test.

### 3.3 Event study (daily)
Events: run-offs 2002-10-27, 2006-10-29, 2010-10-31, 2014-10-26, 2018-10-28, 2022-10-30 (+ first rounds 2002-10-06, 2006-10-01, 2010-10-03, 2014-10-05, 2018-10-07, 2022-10-02, 2026-10-04); inaugurations (first trading day ≥ Jan 1 of 2003/2007/2011/2015/2019/2023); impeachment votes 2016-04-17, 2016-05-12, 2016-08-31; policy events 2016-12-15, 2021-02-24, 2023-08-31. Series: Δlog `ibovespa_usd`, Δlog `ibovespa_level`, Δlog `brl_usd` (sign so + = BRL appreciation), Δ`embi_brazil` (bp), Δ`gov_real_yield_10y` (bp), Δ`focus_fx`, Δ`focus_selic_12m`. Windows: [−1,+1], [−5,+5], [−20,+20], [−60,+60], plus pre-run-up [−120,−1]. Benchmark: no world index exists, so "abnormal" = raw cumulative change minus the series' own mean over an estimation window [−250,−121]; significance by placebo: draw 2,000 random non-event dates (≥ 90 days from any listed event) and compare. Classify each event ex ante as "left win/continuity" (2002, 2006, 2010, 2014, 2022, 2023-01 inauguration) or "right/centre-right transition" (2016 impeachment, 2018, 2019-01) and compare the two groups' cumulative abnormal changes (n = 6 vs 3; permutation across events). Daily `brent_usd` as covariate in [−60,+60] regressions. Coverage guard from 0.6.

### 3.4 Robustness matrix (every primary metric × every cell; summarise as sign-consistency share)
- Sample: 1985+ / 1995+ / 2003+.
- Unit: term / 4-year mandate (split FHC 1999-01-01, Lula 2007-01-01, Dilma 2015-01-01) / year-cluster.
- Lean coding: **A** centre-right → right (baseline); **B** centre-right → centre (right = Collor, Bolsonaro only); **C** Temer → centre, FHC → right; **D** drop transition/incomplete terms (Collor, Itamar, Temer, Lula III); **E** Dilma II (2015–16) coded as its own "crisis" unit and dropped.
- Attribution: contemporaneous / lag-1 / drop-first-year.
- Adjustment: raw / ToT / ToT+Brent (2000+).
- Transform: mean level / end−start change / rank.
Cells with fewer than 2 terms per side are left blank. Output `robustness_matrix.csv` (metric, cell, Δ, CI, sign) and a heatmap.

### 3.5 Multiple comparisons
Holm across the 4 composites; BH across the 26 primary metrics (per adjustment variant separately, reporting q-values); no correction on secondary metrics (descriptive only). Report the full table even if nothing survives — expected given the power floor.

---

## 4. Scenario design 2027–2030 (conditional on the 2026 outcome)

**4.1 Outcome branches.** S-L: left (PT continuity), S-R: right/centre-right, S-C: centre. S-C has no usable historical analogue (Sarney/Itamar are hyperinflation-era) → present S-C as a blend with explicitly wider ranges or under coding B (FHC/Temer as "centre"), labelled as such. If the result becomes known before execution, keep all three branches and mark the realised one.

**4.2 What history suggests (lean-conditional, cycle-adjusted ranges).** For each of: GDP growth, log-inflation, primary balance, Δdebt/GDP, real policy rate, REER change, USD equity return/yr, ΔGini, Δunemployment, real min-wage growth: take the 4-year-mandate outcomes (10 mandates since 1985, 8 since 1995), fit `outcome = α_lean + β·ΔToT_mandate (+ γ·start level)`, and report for each lean the historical min / p25 / median / p75 / max of the raw outcome and the model-implied value under three commodity paths (ΔToT at its historical p25 / p50 / p75 of 4-year changes; log ToT as of 2025 = 1.05, near the top of its 1991–2025 range, so mean reversion is itself a scenario input). Ranges only; never a point. n ≤ 10 → "illustrative".

**4.3 Starting-condition adjustment.** Plug warehouse values from 0.4 into the γ term: debt 82.9, real rate 9.3, inflation 4.2, Gini 50.3, unemployment 5.3, REER 62 (2024-10, 2010 = 100), primary −0.6. Flag that Lula III and Bolsonaro started from very different points (unemployment 12 vs 5; real rate 2.3 vs 8.9), so "term averages" are not comparable without this.

**4.4 Market-implied path vs history.** Focus (2026-09-25): Selic 12.0 at end-2027, IPCA 4.65 (12m), GDP 1.41 (2027), BRL 5.28; NTN-B 10y 7.52% real; LTN 5y 14.15% nominal → rough ex-ante real 5y ≈ 14.15 − 4.65 ≈ 9.5% (maturity mismatch, label as rough). Compare with term-mean `real_policy_rate` by lean (Lula I–II 9.7, Dilma 5.0, Temer 5.3, Bolsonaro 2.3, Lula III 8.9) — history shows no lean ordering; the swing variable is the fiscal–monetary mix, not lean.

**4.5 Debt arithmetic grid (the one deterministic piece).** `d_{t+1} = d_t·(1+r)/(1+g) − pb`, d_2026 = 82.9, nominal r from `implicit_interest_rate` (12.29) and g from `nominal_gdp_growth` (7.23), i.e. r−g = 5.06 (`r_minus_g`), cross-checked with `hypothesis_tests` L3 and `derived_metrics.debt_stabilizing_primary_surplus_gap`. Grid: r−g ∈ {2, 4, 6} × pb ∈ {−1, 0, +1, +2} → debt/GDP 2030. Overlay the lean-conditional pb ranges from 4.2 (post-2002 left terms: +3.15, +1.22, −0.84; right: −2.05, −2.26) and say plainly that these spans are wider than any lean difference.

**4.6 Key swing variables (ranked by their in-sample explanatory power from Q0):** ToT/commodity path (incl. Brent at 114 and Brazil's oil-exporter status: `oil_exports`, `presalt_share`), fiscal-rule credibility (events 2016-12-15, 2023-08-31; observable via `gov_real_yield_10y` and `focus_selic_12m` moves after announcements), real-rate path (BCB autonomy law 2021), external shocks (US tariff 2025-08-06; `exports_to_us` vs `exports_to_china`, L4).

**4.7 Pre-election market-pricing check (2026).** Compute for each of `brl_usd`, `ibovespa_usd`, `ibovespa_level`, `gov_real_yield_10y`, `gov_nominal_yield_5y`, `focus_fx`, `focus_selic_12m`, `focus_ipca_12m`, `focus_gdp_growth`, `fx_reserves`: change over [2026-01-01→10-02], [2026-07-01→10-02], [2026-09-01→10-02], [t−5→t−1]; then the same pre-first-round windows for 2002/2006/2010/2014/2018/2022 and a z-score of 2026 vs that six-election distribution. Confounds to state: Selic cuts, Brent, tariff. Interpretation rule fixed now: a 2026 pre-election move inside the historical interquartile range = "no unusual election premium priced"; outside = report direction without attributing it to a candidate.

---

## 5. Executor deliverables (`/private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/politics/`)

1. `preregistration.md` — sections 2 and 3.4 verbatim, written and timestamped **before** results are computed (first script action writes it; the script asserts the file exists before any analysis).
2. `politics_lean_study.py` — run with `/Users/zkid18/proj-personal/brazil-macro/.venv/bin/python`; `duckdb.connect(DB, read_only=True)`; structure: `terms()`, `annual_panel()`, `monthly_panel()`, `year_end_panel()`, `quarterly_gdp()`, `attribute(df, rule)`, `term_stat(metric, transform)`, `perm_test(values, labels)`, `cluster_bootstrap(obs, cluster_ids, stat)`, `tot_adjust(y, tot)`, `event_study(series, dates, windows)`, `robustness_grid()`, `bh(pvals)`, `holm(pvals)`, `scenarios()`, `pre_election_check()`; `catalog.agg` read from the DB; every number emitted as `{value, series_id, source, last_date, sql}`.
3. `results.json`, `metric_table.csv` (metric_id, bucket, series_ids, source, freq, first/last date, transform, n_left, n_right, mean_left, mean_right, diff, ci80, ci95, perm_p, p_min_attainable, bh_q, diff_tot_adj, ci_tot_adj, sign_consistency_share, left_narrative_expects, right_narrative_expects, verdict), `term_table.csv` (own term keys and coverage per metric), `robustness_matrix.csv`, `event_study.csv`, `scenarios.csv`.
4. `charts/*.html` (plotly): timeline strip (lean bands over GDP growth and ToT); forest plot raw vs ToT-adjusted Δ per metric; robustness heatmap; event-study panels by event group; 2026 campaign tape vs six prior election years; debt/GDP 2027–2030 fan by scenario grid; composite indices by term.
5. `report.md` — Summary (lead with Q0 and the power statement); Data constraints (0.1–0.8 verbatim); Term table and coding; Pre-registered hypotheses; Results tables per family with the SQL shown; Event study; Robustness; Scenarios (ranges, market-implied vs history, swing variables); What can/cannot be concluded (association not causation; n = 6–9 terms; no peers, no Congress data, no US/world controls; terms confounded with ToT, GFC, Lava Jato, COVID, 2026 oil shock); Appendix listing every series with source and last date.
6. Run order: anchor table (0.9) → preregistration → panels → term stats → adjustments → event study → robustness → multiple comparisons → scenarios → pre-election check → report. If any anchor differs, stop and report.

### Critical Files for Implementation
- `/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb` — the data; tables `political_terms`, `political_events`, `observations`, `catalog`, gold `hypothesis_tests`, `derived_metrics`, `book_scorecard`
- `/Users/zkid18/proj-personal/brazil-macro/semantic/views.sql` — exact definitions of `v_politics`/`v_by_term` (the president-string merge bug), `v_annual` (`agg`, `is_complete`), `v_observations`
- `/Users/zkid18/proj-personal/brazil-macro/registry/political_terms.csv` and `/Users/zkid18/proj-personal/brazil-macro/registry/political_events.csv` — source of lean coding and the event list; where a 2026 result would appear if the owner adds it
- `/Users/zkid18/proj-personal/brazil-macro/hypotheses.py` — numpy-only OLS/aggregation helpers to copy (`_ols_r2`, `_m_last`, `_q_mean`) and L3 (r−g) definition to reconcile scenario arithmetic
- `/private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/plan.md` — prior plan's date conventions, `v_annual` rules and `wb/TOT.BRA` validation, which this plan reuses