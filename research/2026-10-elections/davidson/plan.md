# Plan: testing "Brazil is the New America" (Davidson 2012) against the warehouse, 2010–2026

## 0. What exploration found (read this before anything else)

**0.1 There are no peer countries in the warehouse.** All 7,652 World Bank series are Brazil-only (`.BR` 3,916 + `.BRA` 3,736; `entity_name = 'Brazil'` for every one). No `.US`, `.CN`, `.IN`, `.MX`, `.WLD` ids exist, and `excluded_series` contains none either. The literal "Brazil vs America" trajectory comparison **cannot** be done from this warehouse. Section 2 redesigns the comparative frame around (a) Brazil-vs-its-2010-self and (b) WB series that are *inherently US-relative*. Any external US number must be quarantined in an "external data" appendix with source and date, or omitted.

**0.2 Python environment is minimal.** `/Users/zkid18/proj-personal/brazil-macro/.venv` has `duckdb 1.5.6`, `pandas 3.0.6`, `numpy 2.5.3`, `plotly 7.1.0`, `pyarrow`. No scipy, statsmodels, matplotlib, or kaleido. Consequences: OLS via `np.linalg.lstsq`; correlations via `np.corrcoef`; confidence intervals / p-values via **block bootstrap and permutation** (implemented in numpy); charts via plotly `.write_html()` only (no PNG). Do not assume `pip install` is allowed.

**0.3 Date conventions differ by source — join on year-month, never on raw date.**
- Native monthly (BCB, ComexStat, IBGE, ANP, ONS monthly): first of month, e.g. `2024-12-01`.
- WB Global Economic Monitor monthly (`wb/*_M.BRA`): month-end, e.g. `2024-12-31`.
- WB/ILO annual: `YYYY-12-31`. Daily: actual date.
- Use `date_trunc('month', date)` for monthly joins and `v_annual` for annual.

**0.4 `v_annual` aggregation rules (`catalog.agg`) matter.** `ibovespa_usd`, `brl_usd`, `brent_usd`, `selic_target` are `mean`; `credit_gdp`, `fx_reserves`, `ibovespa_level`, `total_return_usd@IBOV` are `last`; exports are `sum`. For **returns** (equity, FX) you must compute year-end values with `arg_max(value, date)` from `v_observations`; the `mean` roll-up of `ibovespa_usd` is wrong for that purpose.

**0.5 Reuse, don't recompute, the warehouse's own gold tables.** `hypothesis_tests` (H1–H6, L1–L4; built in `/Users/zkid18/proj-personal/brazil-macro/hypotheses.py`) and `book_scorecard` (11 threads; built in `/Users/zkid18/proj-personal/brazil-macro/pipeline.py:373 build_scorecard`). Directly relevant and citeable:
- H4: CMO 3.1× in months with EAR < 40% (drought → price, not output).
- H5: US$100 in Jan 2012 → Petrobras $325, Vale $140, Ibovespa $99 (Oct 2026).
- H2/H3: oil export tonnes +8.2%/yr vs iron ore +1.0%/yr; Vale revenue ρ = 0.77 with iron-ore price.
- L3: r − g = +5.1 pts (Aug 2026). L4: post-tariff exports US −14.3%, China +19.0%.
- Scorecard: GDP growth 4.5% (2004–10) vs 0.55% (2015–23); GFCF 16.5%; hydro share 55%; China 29% of exports; forest −16.1% since 1990.

**0.6 Sanity values already verified (anchor numbers the executor should reproduce first):**
| Series | 2010 | latest |
|---|---|---|
| `oil_production` (kbd, annual mean) | 2,137 | 4,368 (2026 avg; 4,601 Jul 2026) |
| `wind_solar_generation_share` (%) | 4.7 (2015) | 29.8 (2025) |
| `wb/EG.ELC.HYRO.ZS.BR` (%) | 78.2 | 56.1 (2024) |
| `wb/ER.H2O.FWTL.ZS.BR` (% of internal resources) | 1.32 | 1.20 (2022) |
| `wb/AG.PRD.CREL.MT.BR` (Mt cereals) | 75.2 | 139.0 (2024) |
| `wb/AG.YLD.CREL.KG.BR` (kg/ha) | 4,041 | 5,003 (2024) |
| `credit_gdp` (BCB, %) | 44.1 | 55.4 (Aug 2026); 2008 = 39.7 (note says ~30) |
| `household_debt_income` (%) | 31.7 | 49.8 (2026) |
| `real_policy_rate` (% annual mean) | 5.0 | 10.4 (2026) |
| `wb/GOV_WGI_CC_EST.BR` | −0.015 | −0.409 (2024) |
| `wb/SI.POV.GINI.BR` | — | 50.3 (2024); 54.0 (2008) |
| `wb/NY.GDP.PCAP.PP.KD.BR` (2021 int$) | 18,062 | 20,025 (2025) |
| `wb/PA.NUS.GDP.PLI.BR` (price level, US=100) | 78.9 | 45.7 (2025) |
| `ibovespa_usd` calendar-year return | — | 2025: **+50.8%** (confirms note) |
| `brl_usd` year-end | — | 6.192 → 5.502 in 2025 = BRL **+12.5%** (confirms note) |
| Gold in reserves = `wb/FI.RES.TOTL.CD.BR` − `wb/FI.RES.XGLD.CD.BR` | $1.5bn (0.5%) | $24.2bn, 6.8% of reserves (2025) |
| `wb/account.t.d.BRA` (Findex account ownership %) | 55.9 (2011) | 86.4 (2024) |
| `pix_transactions_count` | — | 71.3bn in 2025 ≈ 326 per person (`population` 219m) |

---

## 1. Claim → evidence map

Legend: **T** = testable, **P** = partially testable (proxy / stale / level-only), **U** = untestable with this warehouse. All ids verified to exist (source, freq, first→last shown). Filter `date <= current_date` everywhere.

### ENERGY

| # | Claim | Series (source, freq, coverage) | Test | Supports if | Refutes if | Status |
|---|---|---|---|---|---|---|
| E1 | Oil production rising | `oil_production` (IPEAData, M, 2000-01→2026-07); `oil_production_offshore_kbd` (ANP, M, 2012→2026-08); `presalt_share` (ANP, M, 2016→); `oil_exports_kg`, `oil_exports` (ComexStat, M, 2014→); `wb/EG.IMP.CONS.ZS.BR` net energy imports (A, 1990→2023); `wb/NY.GDP.PETR.RT.ZS.BR` oil rents (A, →2021) | Log-linear trend %/yr 2000–2010 vs 2011–2026; net-energy-import sign | post-2010 trend > 0 and net imports < 0 (already −13.7% in 2023, from +23.6% in 2000) | trend ≤ 0 | **T** |
| E2 | One of the cleanest grids | `wb/EG.ELC.RNEW.ZS.BR` (A, 1990→2021, 77.4%); `wb/EG.FEC.RNEW.ZS.BR` (A, →2021, 46.5%); `wb/EG.ELC.FOSL.ZS.BR` (A, →2023); `wb/EN.GHG.CO2.PC.CE.AR5.BR` (A, 1970→2024) | Level + trend | renewable electricity ≥ 75% and not falling post-2010 | < 60% | **P** (level only; "one of the cleanest" ranking needs peers → U) |
| E3 | Hydro is core but fragile; 2021 drought worst in 91 years | `wb/EG.ELC.HYRO.ZS.BR` (A, 1990→2024); ONS daily 2015→2026-10: `hydro_generation_share`, `stored_energy_ear`, `thermal_generation_share`, `thermal_dispatch_mwh`; `cmo_power_cost` (ONS, W, 2005→2026-10); `hydro_stress_index` (derived, D, 2015-07→); `ipca_administered_prices` (BCB, M) | Event study: 2021 vs other years on CMO, thermal share, admin-price inflation; EAR<40% months vs rest (cite H4) | 2021 in top-2 stress years; CMO ratio > 2× in low-EAR months | 2021 unremarkable | **T** for fragility; **P** for "worst in 91 yrs" — national EAR 2021 min 23.6% is *not* the sample low (2017: 17.8%, 2015: 20.2%); CMO 2021 avg R$530 vs 2015 R$567. The "91 years" refers to SE/CO inflows, not in warehouse. |
| E4 | Wind+solar now significant; diversification makes thesis sturdier | `wind_solar_generation_share` (ONS, D, 2015-07→); plus E3 series | Level; and regress log(CMO) on EAR with EAR×WS interaction; rolling 36-m corr(EAR, log CMO) | share ≥ 20% and EAR→CMO sensitivity smaller in 2023–26 than 2015–21 | sensitivity unchanged | **T** |
| E5 | Cane ethanol E30, flex-fuel | none for ethanol; weak proxy `wb/EG.USE.CRNW.ZS.BR` combustible renewables & waste % energy (A, 1990→2024); `vehicle_sales` not by fuel | — | — | — | **U** (report proxy level only, labelled) |
| E6 | Caatinga solar | none (no regional data) | — | — | — | **U** |
| E7 | EU CBAM favours Brazilian charcoal / clean steel | no steel/charcoal series; `exports_to_eu` (ComexStat, M, 2014→2026-08) is confounded | — | — | — | **U** (mention Jan–Aug 2026 vs 2025 EU exports as anecdote only) |

### WATER

| # | Claim | Series | Test | Supports if | Refutes if | Status |
|---|---|---|---|---|---|---|
| W1 | Huge freshwater, withdrawals far below renewal | `wb/ER.H2O.FWTL.ZS.BR` (A, 1987→2022); `wb/ER.H2O.INTR.PC.BR` (A, 1961→2022); `wb/ER.H2O.INTR.K3.BR`; `wb/ER.H2O.FWTL.K3.BR`; sector shares `wb/ER.H2O.FWAG.ZS.BR`, `FWIN`, `FWDM` | Level and slope | withdrawals < 5% of internal resources, slope flat | > 20% or rising fast | **T** |
| W2 | vs Ogallala / North China Plain / Punjab | no peer data | — | — | — | **U** |
| W3 | Risk side (not in note, but needed for honesty): drought and forest-water nexus | `wb/EN.CLC.SPEI.XD.BR` drought index (A, 1960→2023); `wb/AG.LND.FRST.K2.BR` (A, 1990→2023); `wb/AG.LND.PFLS.HA.BR` primary forest loss (A, 2002→2025); `wb/NW.NCA.FSTW.PC.BR` forest-water ecosystem natural capital (A, 1995→2020) | Trend | — | — | **T** (context) |

### AGRO

| # | Claim | Series | Test | Supports if | Refutes if | Status |
|---|---|---|---|---|---|---|
| A1 | Grain output 47 Mt (1977) → 354 Mt with far smaller area growth | WB **cereals only** (soy excluded; CONAB "grãos" not in warehouse): `wb/AG.PRD.CREL.MT.BR` (A, 1961→2024); `wb/AG.LND.CREL.HA.BR` (A, 1961→2024); `wb/AG.YLD.CREL.KG.BR` (A, 1961→2024); `wb/AG.PRD.CROP.XD.BR`, `wb/AG.PRD.FOOD.XD.BR`, `wb/AG.PRD.LVSK.XD.BR` (A, →2022); `wb/NV.AGR.EMPL.KD.BR` ag VA/worker (A, 1991→2025); `wb/AG.LND.AGRI.ZS.BR`, `wb/AG.LND.ARBL.HA.BR`, `wb/AG.CON.FERT.ZS.BR` (→2023) | Decomposition Δlog(prod) = Δlog(area) + Δlog(yield), 1977–2010 vs 2010–2024 | yield share of output growth > 50% in both windows | area share > 50% | **T** on direction; the 354 Mt level itself is **U** (different definition) |
| A2 | #1 exporter of soy, beef, sugar, coffee, OJ, chicken, cotton | `soy_exports`, `beef_exports`, `coffee_exports`, `sugar_exports` (ComexStat, M, 2014→2026-08); `wb/TX.VAL.FOOD.ZS.UN.BR`, `wb/TX.VAL.AGRI.ZS.UN.BR` (A, 1962→2025) | USD growth 2014→2025 (soy $23.3bn→$43.5bn; beef $5.7bn→$16.5bn) | — | — | **P** (growth testable; world rank **U**; no OJ/chicken/cotton series) |
| A3 | Northern frontier / Arco Norte ports | none | — | — | — | **U** |
| A4 | Hidden dependency: fertilizer imports | `fertilizer_imports`, `potash_imports`, `fertilizer_dependency_index`, `potash_import_dependency_proxy` (M, 2014→) | Trend | — | — | **T** (counter-evidence) |

### MINERALS

| # | Claim | Series | Test | Status |
|---|---|---|---|---|
| M1 | Niobium dominance | `niobium_exports` (ComexStat, M, 2014→2026-08; ~$305m/mo) | USD trend only; world share **U** | **P** |
| M2 | #2 rare-earth reserves | none | — | **U** |
| M3 | High-grade iron ore | `iron_ore_exports`, `iron_ore_exports_kg`, `iron_ore_unit_value` (M, 2014→); `wb/NY.GDP.MINR.RT.ZS.BR` (A, →2021, 4.5% in 2021); `wb/TX.VAL.MMTL.ZS.UN.BR` (A, 1962→2025); `wb/NW.NCA.MIRO.TO.BR` iron-ore natural capital (A, 1995→2020) | Cite H2/H3; grade **U** | **P** |
| M4 | Lithium | `wb/NW.NCA.MLIT.TO.BR`, `wb/NW.NCA.MLIT.PC.BR` (A, 1995→2020) | Natural-capital valuation trend | **P** |
| M5 | Hedge vs China processing | Dependence on China as *buyer*: `exports_to_china`, `china_export_share`, `beef_exports_to_china` | Rising China share cuts both ways | **P** (reframe) |

### CREDIT

| # | Claim | Series | Test | Supports if | Status |
|---|---|---|---|---|---|
| C1 | Credit/GDP ~30% (2008) → ~54% now; vs US mature debt economy | `credit_gdp` (BCB, M, 2000→2026-08); `wb/FS.AST.PRVT.GD.ZS.BR` (A, 1960→2025, 75.1% in 2025 — broader definition); `wb/FD.AST.PRVT.GD.ZS.BR` | Level path; report both definitions | path rising | **T** (note: 2008 was 39.7% BCB / 45.8% WB — the note's "30%" matches 2000–2004; direction right, number off). US comparison **U** |
| C2 | Household debt rising | `household_debt_income` (M, 2005→2026-07); `household_debt_service_ratio` (M, 2005→; 28.7% = series high, cite L1); `household_credit_growth` (M, 2008→); `delinquency_rate` (M, 2011→) | Trend, highs | DSR at/near max | **T** |
| C3 | Cost of credit is the problem; highest real rates in world (Selic 14.5%, inflation 5–6%, real 8–11%) | `selic_target` (D); `ipca_12m` (M); `focus_ipca_12m` (D); `real_policy_rate` (derived, M, 2001-12→2026-09); `gov_real_yield_10y` (Tesouro, D, 2015→); `wb/FR.INR.LEND.BR` (A, 1997→2025, 45.3%); `wb/FR.INR.LNDP.BR` spread (A, →2024, 32.5 pts); `wb/FR.INR.RINR.BR` (A, →2025, 37.5% — **this is the WB real *lending* rate, not the policy rate; do not conflate**) | Levels; check Apr 2026 `ipca_12m` exactly (2026 avg is 4.35%, so "5–6%" may be high) | ex-ante real policy rate > 5% | **T** on level; "highest in world" **U** |
| C4 | Banks super-profitable: wide spreads, concentration | `wb/GFDD.EI.01.BR` NIM, `wb/GFDD.EI.06.BR` ROE, `wb/GFDD.OI.01.BR` 3-bank conc. (38.7% 2000 → 70.4% 2021), `wb/GFDD.OI.06.BR` 5-bank (79.4%), all A, 2000→2021; `wb/FR.INR.LNDP.BR`; `net_income_brl@ITUB`, `revenue_brl@ITUB` (CVM, Q, 2012→2026-06); `total_return_usd@ITUB` | Levels; ITUB ROE proxy = 4×net income / revenue trend | spread > 20 pts and 5-bank conc. > 60% | **T** (GFDD stale 2021; ITUB extends) |
| C5 | BCB buying gold (+43t 2025), diversifying from USD | gold USD = `wb/FI.RES.TOTL.CD.BR` − `wb/FI.RES.XGLD.CD.BR` (A, 1960→2025; both `role='alternate'`, fine); `fx_reserves` (BCB, D) | Gold value and share 2020→2025 | share rising sharply (3.3% → 6.8%) | **P** — tonnage **U** (no gold price in warehouse to split price vs volume; $10.9bn → $24.2bn = 2.2× cannot be price alone, say so without quoting an external gold return) |
| C6 | Pix near-universal | `pix_transactions_count`, `pix_transactions_value` (BCB, M, 2020-11→2026-09); `population` (IBGE, A); Findex `wb/account.t.d.BRA`, `wb/fin2.t.d.BRA` (A, 2011/14/17/21/24) | per-capita Pix count; account ownership | account > 80%, Pix > 100/person/yr | **T** |
| C7 | Hyperinflation as "vaccine" against debt | `ipca_12m`; `wb/NY.GDP.DEFL.KD.ZG.BR` (A, 1961→2025); `gross_public_debt_gdp` (M, 2006→, 82.9%); `net_public_debt_gdp`; `credit_gdp` | Private credit modest **but** public debt high | — | **P** (interpretive; public-debt side contradicts) |

### INSTITUTIONS

| # | Claim | Series | Test | Status |
|---|---|---|---|---|
| I1 | Inequality persists | `wb/SI.POV.GINI.BR` (A, 1981→2024); `wb/SI.DST.10TH.10.BR`, `wb/SI.DST.FRST.20.BR`; `ilostat/EAR_EMTG_SEX_NB.BRA` earnings Gini (A, 1989→2025); `ilostat/LAP_2GDP_NOC_RT.BRA` labour share (A, 2004→2025) | Slope pre/post-2010; level | **T** ("persists" if Gini > 45; "improving" if slope < 0) |
| I2 | Corruption / weak institutions persist | WGI `wb/GOV_WGI_CC_EST.BR`, `_GE_EST`, `_RL_EST`, `_RQ_EST`, `_VA_EST`, `_PV_EST` (A, 1996→2024; also `_SC` 0–100 versions) | mean 1996–2010 vs 2011–2024; slope | **T** (CC −0.015 → −0.41; RL −0.04 → −0.45 suggests *worsening*) |
| I3 | Ease of doing business | `wb/IC.BUS.EASE.DFRN.XQ.DB1719.BR` (2015→2019); `wb/IC.REG.DURS.BR` (2013→2019); `wb/ENF.CONT.DURS.DY.BR`; `wb/LP.LPI.OVRL.XQ.BR` (2007→2022) | Level | **P** (Doing Business discontinued 2019) |
| I4 | Weak schools | `wb/LO.PISA.MAT.BR`, `wb/LO.PISA.REA.BR` (2000→**2015** only); `wb/SE.XPD.TOTL.GD.ZS.BR` (1995→2022); `wb/SE.SEC.ENRR.BR`, `wb/SE.TER.ENRR.BR` (2012→2024); `wb/SE.ADT.LITR.ZS.BR` (→2024); `wb/NW.HCA.PC.BR` human capital/capita (1995→2020) | Level/trend | **P** (PISA stale) |
| I5 | Tax complexity | `wb/PAY.TAX.COIT.AU.HRS.DB1719.BR`, `wb/PAY.TAX.TOT.TAX.RT.ZS.BR` (2013→2019); `wb/GC.TAX.TOTL.GD.ZS.BR` (2010→2024) | Level | **P** (stale) |
| I6 | Expensive capital → low investment | `wb/NE.GDI.FTOT.ZS.BR` GFCF (A, 1970→2025; 20.5% 2010 → 16.8% 2025); `wb/NY.GNS.ICTR.ZS.BR`; plus C3 | Pre/post-2010 mean | **T** |
| I7 | Slow start: slavery / plantation / land concentration / weak schooling | historical, no land-Gini series | — | **U** |

### GEOPOLITICS / TRADE

| # | Claim | Series | Test | Status |
|---|---|---|---|---|
| G1 | China share of Brazil trade rising | `china_export_share` (derived, M, 2014→2026-08); `exports_to_china`, `exports_to_us`, `exports_to_eu`, `exports_total` (ComexStat, M, 2014→) | 12-m rolling share trend; cite L4 | **T** (pre-2014 **U** in warehouse; scorecard cites 18% in 2014 → 29%) |
| G2 | Global South share rising | only China/US/EU destinations exist | Proxy: 1 − (US+EU)/total | **P** (labelled proxy) |
| G3 | EU–Mercosur | `exports_to_eu` trend only | — | **U** |

### ALLOCATION

| # | Claim | Series | Result already seen | Status |
|---|---|---|---|---|
| R1 | Ibovespa ~+51% USD in 2025 | `ibovespa_usd` (derived, D, 2000→2026-10-01); `total_return_usd@IBOV` (M, 2012→); `wb/DSTKMKTXD_M.BRA` equity index in USD (M, 1994→2025, extends history) | +50.8% year-end/year-end | **T** ✔ |
| R2 | BRL +12–13% vs USD in 2025 | `brl_usd` (BCB, D) | 6.192 → 5.502 = +12.5% | **T** ✔ |
| R3 | Foreign B3 inflows R$56.5bn Jan–Apr 2026 | none (no B3 flow series); `wb/BX.PEF.TOTL.CD.WD.BR` annual portfolio equity net inflows (−$5.0bn 2025, −$17.5bn 2024) | — | **U** (annual WB series contradicts a 2024–25 inflow story; report) |
| R4 | Rerating | `wb/CM.MKT.LCAP.GD.ZS.BR` (A, 2000→2025); `embi_brazil` (D, →2024-07 **stale**); `gov_real_yield_10y`; `dividend_yield_ttm@*` | Levels | **P** |

---

## 2. Comparative frame (redesigned for a Brazil-only warehouse)

**2.1 Brazil vs its 2010 self (primary).** For every pillar, a panel of anchor years 1990 / 2000 / 2010 / 2019 / 2025 and pre-2010 vs post-2010 CAGR or mean, with a block-bootstrap CI on the difference. Pre-window 1991–2010 (or 2000–2010 for native series), post-window 2011–2025 (annual) / 2011–2026-09 (monthly). Robustness: split at 2012 (publication year) and exclude 2020.

**2.2 Brazil relative to the US via inherently US-relative WB series (secondary, in-warehouse).**
- `wb/PA.NUS.GDP.PLI.BR` price level index (US = 100): 78.9 (2010) → 45.7 (2025). Brazil has become ~40% *cheaper* relative to the US — reads as both "no real convergence" and "cheap assets".
- `wb/DSTKMKTXD_M.BRA` local equity index in USD: 104.9 (Dec 2010) → 75.9 (Dec 2025). Brazilian equities in USD are still **below** their 2010 level after the 2025 rally.
- `wb/PX.REX.REER.BR` (A, 1980→2025) and `wb/REER_M.BRA` (M, →2024-10) real effective exchange rate.
- `wb/NY.GDP.PCAP.PP.KD.BR` growth: 18,062 → 20,025 (2010→2025) ≈ 0.7%/yr. Convergence-to-US ratio **cannot** be computed in-warehouse. If the executor chooses to add a single external US GDP-per-capita-PPP anchor, it must sit in an appendix titled "External data (not from warehouse)" with source and access date; the primary verdict must not depend on it.

**2.3 Recommendation for the warehouse owner (out of scope for this run):** ingest the same WB indicators for US/CN/IN/MX via the Dateno `wb/` namespace (e.g. `wb/NY.GDP.PCAP.PP.KD.US`). The comparative frame in the request becomes trivial once those exist.

---

## 3. Central correlation analyses

**Common method rules (apply to every analysis):**
1. Correlate growth rates / log-differences, never levels. Bounded mean-reverting series (EAR %, shares, real rate) may be used in levels, but say so.
2. Annual panel via `v_annual` with `is_complete = TRUE`; year-end values for FX/equity via `arg_max(value, date)`.
3. Monthly panel: aggregate daily to month-end (`arg_max`) for prices/FX/equity, month-mean for rates/EAR/CMO; join on `date_trunc('month', date)`.
4. Report Pearson and Spearman, n, and a 95% CI from a **moving-block bootstrap** (block = 12 for monthly, 4 for quarterly, 3 for annual; 2,000 resamples). p-values by permutation (2,000 shuffles). Do not report any statistic with n < 10 (annual) or n < 36 (monthly).
5. Structural break at 2010 (book cutoff): compute every statistic for pre and post windows, and the OLS with a `post2010 × X` interaction; report the interaction coefficient with its bootstrap CI. Robustness: split at 2012; exclude 2020.
6. Rolling windows: 60-month for monthly series, 10-year for annual.
7. OLS in numpy: `X = np.column_stack([np.ones(n), x...]); beta = np.linalg.lstsq(X, y, rcond=None)[0]`; R² manually (pattern already in `hypotheses.py: _ols_r2`).

**Monthly panel SQL (one query, pivot in pandas):**
```sql
SELECT series_id, date_trunc('month', date) AS ym,
       CASE WHEN series_id IN ('ibovespa_usd','brl_usd','brent_usd','wb/DSTKMKTXD_M.BRA','fx_reserves')
            THEN arg_max(value, date) ELSE avg(value) END AS v
FROM v_observations
WHERE date <= current_date AND series_id IN (
  'ibovespa_usd','brl_usd','brent_usd','wb/TOT.BRA','wb/DSTKMKTXD_M.BRA',
  'real_policy_rate','selic_target','ipca_12m','focus_ipca_12m',
  'household_credit_growth','corporate_credit_growth','credit_gdp','delinquency_rate',
  'ibc_br','wb/IPTOTSAKD_M.BRA','exports_total','bop_goods_exports','wb/DXGSRMRCHNSCD_M.BRA',
  'iron_ore_unit_value','oil_export_unit_value','pulp_unit_value',
  'stored_energy_ear','cmo_power_cost','thermal_generation_share','wind_solar_generation_share',
  'hydro_generation_share','hydro_stress_index','ipca_administered_prices','ipca_monthly',
  'total_return_usd@IBOV','total_return_usd@PETR','total_return_usd@VALE','total_return_usd@SUZB',
  'total_return_usd@ITUB','total_return_brl@IBOV','gov_real_yield_10y','embi_brazil')
GROUP BY 1,2 ORDER BY 2,1;
```

**Annual panel SQL:**
```sql
SELECT series_id, year, value
FROM v_annual
WHERE is_complete AND year BETWEEN 1990 AND 2025 AND series_id IN (
  'wb/NY.GDP.MKTP.KD.ZG.BR','wb/NY.GDP.PCAP.PP.KD.BR','wb/NY.GDP.PCAP.KD.ZG.BR',
  'wb/NE.GDI.FTOT.ZS.BR','wb/NY.GNS.ICTR.ZS.BR','wb/TT.PRI.MRCH.XD.WD.BR','wb/TX.UVI.MRCH.XD.WD.BR',
  'wb/FS.AST.PRVT.GD.ZS.BR','wb/FR.INR.LNDP.BR','wb/FR.INR.LEND.BR','wb/PA.NUS.GDP.PLI.BR','wb/PX.REX.REER.BR',
  'wb/GOV_WGI_CC_EST.BR','wb/GOV_WGI_GE_EST.BR','wb/GOV_WGI_RL_EST.BR','wb/GOV_WGI_RQ_EST.BR','wb/GOV_WGI_VA_EST.BR','wb/GOV_WGI_PV_EST.BR',
  'wb/SI.POV.GINI.BR','wb/AG.PRD.CREL.MT.BR','wb/AG.LND.CREL.HA.BR','wb/AG.YLD.CREL.KG.BR','wb/NV.AGR.EMPL.KD.BR',
  'wb/EG.ELC.HYRO.ZS.BR','wb/EG.ELC.RNEW.ZS.BR','wb/EG.IMP.CONS.ZS.BR','wb/ER.H2O.FWTL.ZS.BR','wb/ER.H2O.INTR.PC.BR',
  'wb/NY.GDP.TOTL.RT.ZS.BR','wb/NW.NCA.TOTL.PC.BR','wb/NW.NCA.SSOI.PC.BR','wb/NW.HCA.PC.BR','wb/NW.PCA.PC.BR',
  'ilostat/GDP_205U_NOC_NB.BRA','ilostat/SDG_0821_NOC_RT.BRA','wb/CM.MKT.LCAP.GD.ZS.BR','wb/BX.PEF.TOTL.CD.WD.BR',
  'oil_production','real_policy_rate','credit_gdp','household_debt_income','wind_solar_generation_share','stored_energy_ear','cmo_power_cost')
ORDER BY 1,2;
```
Plus year-end equity/FX:
```sql
SELECT series_id, EXTRACT(year FROM date)::INT AS year, arg_max(value, date) AS year_end
FROM v_observations WHERE series_id IN ('ibovespa_usd','brl_usd','wb/DSTKMKTXD_M.BRA','ibovespa_level') AND date <= current_date
GROUP BY 1,2 ORDER BY 1,2;
```

**Validation step before using `wb/TOT.BRA`:** it is a ratio (~0.84–1.13) described generically. Compute the annual mean and correlate it with `wb/TT.PRI.MRCH.XD.WD.BR` on 2005–2024; proceed only if ρ > 0.9, otherwise fall back to the annual index plus `brent_usd` / `iron_ore_unit_value` for monthly work.

### 3a. Growth, BRL, Ibovespa (USD) vs commodity terms of trade / export prices / exports
- **Y:** Δlog real GDP quarterly `wb/NYGDPMKTPSAKD_Q.BRA` (1990Q1→2025Q4, constant 2010 US$, SA; `agg = sum`, so take quarterly observations directly from `v_observations`); annual `wb/NY.GDP.MKTP.KD.ZG.BR`; monthly `ibc_br` YoY; Δlog `brl_usd` (month-end); Δlog `ibovespa_usd` (month-end; `wb/DSTKMKTXD_M.BRA` for 1994–1999 extension).
- **X:** Δlog `wb/TOT.BRA` (M, 1991→2025), Δlog `brent_usd`, Δlog `iron_ore_unit_value` (2014→), Δlog `bop_goods_exports` (2000→), Δlog `wb/DXGSRMRCHNSCD_M.BRA` (1990→). Commodity composite = mean z-score of Δlog Brent and Δlog iron-ore unit value (2014+), Brent alone before.
- **Analyses:** cross-correlation function at lags 0…+4 quarters (ToT leading GDP); OLS Δlog Ibov USD ~ Δlog ToT + Δlog Brent (beta, R²); rolling 60-m corr(Δlog Ibov USD, Δlog Brent); all pre/post-2010.
- **Read-out:** monthly R² > 0.3 → equity is a commodity proxy; GDP sensitivity to ToT falling post-2010 would mean endowment matters *less* for growth, not more.

### 3b. High real rate vs credit growth, investment, GDP
- **X:** `real_policy_rate` (level, monthly); ex-post alternative `selic_target − ipca_12m`.
- **Y:** `household_credit_growth`, `corporate_credit_growth` (YoY, 2008-03→), Δ12m `credit_gdp`, `ibc_br` YoY, `delinquency_rate` (level); annual Δ`wb/NE.GDI.FTOT.ZS.BR`, `wb/NY.GDP.MKTP.KD.ZG.BR`.
- **Analyses:** CCF of real rate at t vs each Y at t+k, k = −12…+24 months; report lag of max |ρ| with CI (expect negative at 6–18 m). Annual OLS: GFCF change ~ real rate (n ≈ 24). Cite L3 (r − g) and `r_minus_g` series.
- **Read-out:** ρ < −0.3 at some lag 6–18 m with CI excluding 0 → "cost of credit is binding" supported.

### 3c. Decomposition: endowment improved, income did not converge
- **Physical endowment composite** (z-scores, rebased 2010 = 0, equal weights): `oil_production` (annual mean), `wb/AG.YLD.CREL.KG.BR`, `wb/AG.PRD.CREL.MT.BR`, `wb/NV.AGR.EMPL.KD.BR`, `wb/EG.ELC.RNEW.ZS.BR`, −`wb/EG.IMP.CONS.ZS.BR`, `wb/NW.NCA.TOTL.PC.BR` + `wb/NW.NCA.SSOI.PC.BR` (→2020), `wind_solar_generation_share` (2015+), `bop_goods_exports` (log).
- **Institutional composite:** mean of six WGI `_EST` series; −`wb/SI.POV.GINI.BR`; `wb/NE.GDI.FTOT.ZS.BR`; `wb/NW.HCA.PC.BR`.
- **Outcome:** `wb/NY.GDP.PCAP.PP.KD.BR`, `ilostat/GDP_205U_NOC_NB.BRA` output/worker, `ilostat/SDG_0821_NOC_RT.BRA`, `wb/PA.NUS.GDP.PLI.BR`, `wb/DSTKMKTXD_M.BRA` year-end.
- **Analyses:** one chart, three lines indexed 2010 = 100 (endowment, outcome, institutions). Table of CAGR 2000–2010 vs 2011–2025. Annual OLS Δlog GDP pc ~ Δlog ToT + ΔWGI_mean (1997–2024, n ≈ 27) — low power; present coefficients with bootstrap CIs and say so.
- **Read-out:** endowment composite up, outcome flat, institutions down → exactly the note's "true for physical column, weaker for institutional", *plus* the finding that physical gains did not convert into income — this is the headline.

### 3d. Hydro share / reservoirs vs power cost and inflation in drought years
- Monthly: EAR (level) vs log CMO (contemporaneous and lags 0–3); EAR vs `ipca_administered_prices` at lags 0–6; `thermal_generation_share` vs CMO.
- Drought-year dummy (2015, 2017, 2021) vs others on annual mean CMO, thermal share, administered inflation (`v_annual` already shows CMO 567 / 350 / 530 vs 31–248 in other years; admin inflation 1.40 / 0.65 / 1.31 %/mo).
- Diversification: OLS log CMO ~ EAR + EAR×WS_share + WS_share; sub-sample 2015–2021 vs 2022–2026 slope on EAR. Rolling 36-m corr(EAR, log CMO).
- **Read-out:** EAR→CMO slope shrinks in 2022–26 → "wind+solar makes the thesis sturdier" supported.

### 3e. Brazil equity vs commodity cycle: hedge or high-beta proxy?
- Monthly log returns of `ibovespa_usd`, `total_return_usd@{PETR,VALE,SUZB,PRIO,AXIA,ITUB}` vs Δlog Brent, Δlog iron-ore unit value, Δlog ToT, and the composite.
- Decompose USD return = BRL return (`total_return_brl@IBOV`) + FX return; estimate commodity beta of each component (pattern in H6).
- Up/down capture: mean Ibov USD return in composite-up vs composite-down months; asymmetry ratio.
- Rolling 60-m beta to Brent 2000→2026; pre/post-2010 betas; contrast with ITUB (domestic control).
- **Thresholds:** ρ(Δlog Ibov USD, Δlog composite) > 0.4 → "commodity proxy / high beta"; 0.2–0.4 → "partial hedge"; < 0.2 → "not a commodity hedge". For the "hedge to the physical side of AI" conclusion to be *supported*, beta must be positive with CI excluding 0 **and** 3c must show the endowment-to-returns link is at least non-negative post-2010 (H5 says resource champions beat the index since 2012, but the index itself was flat in USD: $99 for $100).

---

## 4. Verdict rubric

**Per claim:** Supported / Partially supported / Refuted / Untestable, using the thresholds in Section 1 (or Section 3 for correlation claims). "Partially" when only a proxy exists, the series is stale (> 3 years old), or the direction holds but the quoted number does not.

**Per pillar:** score = (#Supported + 0.5 × #Partial) / #testable claims (Untestable excluded from the denominator; report coverage = testable/total so the reader sees how much of the note the warehouse can reach). ≥ 0.75 Supported; 0.50–0.74 Partial; < 0.50 Refuted.

**Columns:**
- Physical = Energy, Water, Agro, Minerals.
- Institutional = Credit, Institutions.
- Market = Trade, Allocation, plus the Section 3 correlation results.

**Overall verdict logic:**
1. "Physical > institutional" (the note's own reading) is **supported** if physical score ≥ 0.75 and institutional ≤ 0.50.
2. "Thesis holds post-2010 as an *investment* thesis" additionally requires: 3c shows endowment gains converting into income/returns (GDP pc PPP CAGR post-2010 > pre-2010, or USD equity above 2010 level — currently 75.9 vs 104.9 says no), and 3e shows Brazil equity is a hedge (beta > 0, CI excludes 0) rather than merely high-beta.
3. Output one of: **"Holds"** / **"Holds for the physical column; institutional column refuted; returns not delivered post-2010"** / **"Refuted"**, with the two or three numbers that drove the call.

**Minimum-evidence rules:** no verdict on n < 10 annual or n < 36 monthly obs; stale series (last date < 2022) can only yield "Partial"; every number must carry series_id, source, last date.

---

## 5. Deliverables for the executor

All in `/private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/`:

1. **`brazil_thesis_test.py`** — one script, run with `/Users/zkid18/proj-personal/brazil-macro/.venv/bin/python`. Structure:
   - `con = duckdb.connect('/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb', read_only=True)`
   - helpers: `q(sql) -> DataFrame`; `monthly_panel()`; `annual_panel()`; `year_end(series)`; `logdiff(s)`; `block_bootstrap_corr(x, y, block, n_boot=2000, seed=0)`; `perm_pvalue(x, y, n=2000)`; `ols(y, X) -> (beta, r2, resid)`; `ccf(x, y, lags)`; `split_stats(df, xcol, ycol, break_year=2010)`; `rolling_corr(x, y, window)`.
   - sections `s1_claim_map()`, `s2_comparative()`, `s3a()…s3e()`, `s4_verdict()`, each returning dicts; every number tagged `{value, series_id, source, last_date, sql}`.
   - outputs: `results.json`, `claim_map.csv` (claim, pillar, status, statistic, threshold, verdict, series_ids, last_dates), `charts/*.html` (plotly; at minimum: 3c three-line index chart, 3e rolling beta, 3d EAR-vs-CMO scatter by period, 3a rolling corr), and `report.md`.
   - `catalog.agg` is read from the DB for any series roll-up, so the script never hard-codes it.
2. **`report.md`** — sections: Summary verdict; Data constraints (0.1–0.5 above, verbatim); Claim map table; Comparative frame; Correlation results (each with the SQL shown, n, ρ, CI, pre/post-2010); Pillar scores and the rubric roll-up; Untestable claims list; Appendix: every series used with source and last date; optional "External data (not from warehouse)" appendix, clearly fenced.
3. Reproduction order: anchor table (0.6) first — if any anchor value differs, stop and report; then Section 1 queries; then panels; then 3a–3e; then verdict.

**Pitfalls to carry into the script header as comments:** month-end vs first-of-month dates; `v_annual` mean vs last for returns; WB `FR.INR.RINR` ≠ real policy rate; `wb/TOT.BRA` validation; `embi_brazil` ends 2024-07; Doing Business ends 2019, PISA ends 2015, GFDD ends 2021; `credit_gdp` (BCB) and `wb/FS.AST.PRVT.GD.ZS.BR` differ by ~20 pts in level by definition; WB 2025 values are preliminary; no scipy — bootstrap/permutation only; plotly HTML only.

### Critical Files for Implementation
- `/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb` — the data (open `read_only=True`)
- `/Users/zkid18/proj-personal/brazil-macro/semantic/views.sql` — exact definitions of `v_annual` (agg rules, `is_complete`), `v_observations`, `v_search`
- `/Users/zkid18/proj-personal/brazil-macro/semantic/model.yml` — id patterns, named metrics (`real_policy_rate`, `hydro_stress_index`), date conventions, rules
- `/Users/zkid18/proj-personal/brazil-macro/hypotheses.py` — numpy-only OLS/correlation/total-return patterns to copy (`_ols_r2`, `_trend_pct_per_year`, `_q_mean`, `_m_last`) and the H1–H6/L1–L4 definitions to cite
- `/Users/zkid18/proj-personal/brazil-macro/pipeline.py` (lines 261–501) — `build_scorecard` and the single r/g definition, so the executor's numbers reconcile with `book_scorecard`