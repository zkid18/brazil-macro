# Is Brazil still "the New America"? Testing Davidson (2012) against the warehouse, data to 2026

Run date 2026-10-05 · warehouse `/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb` (read-only) · script `brazil_thesis_test.py` · full numbers in `results.json`, claims in `claim_map.csv`, charts in `charts/`.

## 1. Summary verdict

**Holds only partly for the physical column (score 0.50, below the 0.75 bar); institutional column refuted; returns not delivered post-2010.**

Driving numbers:

1. **Endowment up, income flat.** Physical-endowment composite +1.92 z vs 2010; outcome composite -0.81 z; GDP per capita PPP grew 2.58%/yr in 2000–10 but only 0.69%/yr in 2010–25 (`wb/NY.GDP.PCAP.PP.KD.BR`, World Bank, last 2025-12-31; 18,062 → 20,025 int$ 2021). Oil output doubled (`oil_production`, IPEAData, last 2026-07-01: 2,137 → 4,601 kbd).
2. **Institutions worsened.** Institutional composite -2.16 z vs 2010; WGI control of corruption −0.02 → −0.41 and rule of law −0.04 → −0.45 (2010 → 2024, `wb/GOV_WGI_CC_EST.BR`, `wb/GOV_WGI_RL_EST.BR`, World Bank, last 2024-12-31); GFCF 20.5% → 16.8% of GDP.
3. **Returns not delivered.** USD equity index 104.9 (Dec 2010) → 75.9 (Dec 2025) even after 2025's +50.8% (`wb/DSTKMKTXD_M.BRA`, World Bank, last 2025-12-31); price level vs US 78.9 → 45.7 (`wb/PA.NUS.GDP.PLI.BR`). Brazil equity does carry a positive commodity beta (Ibov USD on composite: beta 0.29 (CI 0.12,0.47), rho 0.31 (CI 0.11,0.49, n=320)), but Itaú (a domestic bank) has the same beta, so it is mostly a global risk-on beta.

Pillar scores (thesis-favourability, see rubric in §6):

| pillar | score | label | testable / total (coverage) | verdict counts |
|---|---|---|---|---|
| physical | 0.50 | Partial | 13/19 (68%) | {'Partial': 9, 'Supported': 4} |
| institutional | 0.32 | Refuted | 14/15 (93%) | {'Partial': 7, 'Supported': 7} |
| market | 0.69 | Partial | 8/10 (80%) | {'Supported': 4, 'Partial': 3, 'Refuted': 1} |

Physical-score sensitivity: pro-thesis claims only 0.60; fully-testable (T) claims only 0.50. The physical column is ahead of the institutional one (the note's reading holds in direction), but it does not clear the plan's 0.75 bar: most physical claims can only be tested by proxy or stale series (→ Partial), and two weaknesses the note itself concedes (hydro fragility, fertilizer import dependence) are confirmed.

## 2. Data constraints (verbatim from plan §0.1–0.5)

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

### Anchor check (plan §0.6)

39/39 anchors reproduced within tolerance. (First run flagged Pix count as off by 10⁶ — `pix_transactions_count` is in millions; fixed in code, not a data issue.)

| anchor | series | expected | got | match |
|---|---|---|---|---|
| oil_production 2010 mean kbd | oil_production | 2137.0 | 2137.0833 | True |
| oil_production 2026 YTD mean kbd | oil_production | 4368.0 | 4367.5251 | True |
| oil_production Jul 2026 kbd | oil_production | 4601.0 | 4601.4667 | True |
| wind_solar_generation_share 2015 % | wind_solar_generation_share | 4.7 | 4.6538 | True |
| wind_solar_generation_share 2025 % | wind_solar_generation_share | 29.8 | 29.7847 | True |
| wb/EG.ELC.HYRO.ZS.BR 2010 | wb/EG.ELC.HYRO.ZS.BR | 78.2 | 78.2003 | True |
| wb/EG.ELC.HYRO.ZS.BR 2024 | wb/EG.ELC.HYRO.ZS.BR | 56.1 | 56.1399 | True |
| wb/ER.H2O.FWTL.ZS.BR 2010 | wb/ER.H2O.FWTL.ZS.BR | 1.32 | 1.3208 | True |
| wb/ER.H2O.FWTL.ZS.BR 2022 | wb/ER.H2O.FWTL.ZS.BR | 1.2 | 1.2001 | True |
| wb/AG.PRD.CREL.MT.BR 2010 | wb/AG.PRD.CREL.MT.BR | 75200000.0 | 75160152.06 | True |
| wb/AG.PRD.CREL.MT.BR 2024 | wb/AG.PRD.CREL.MT.BR | 139000000.0 | 138980898.51 | True |
| wb/AG.YLD.CREL.KG.BR 2010 | wb/AG.YLD.CREL.KG.BR | 4041.0 | 4040.6 | True |
| wb/AG.YLD.CREL.KG.BR 2024 | wb/AG.YLD.CREL.KG.BR | 5003.0 | 5002.6 | True |
| wb/GOV_WGI_CC_EST.BR 2010 | wb/GOV_WGI_CC_EST.BR | -0.015 | -0.0151 | True |
| wb/GOV_WGI_CC_EST.BR 2024 | wb/GOV_WGI_CC_EST.BR | -0.409 | -0.4089 | True |
| wb/NY.GDP.PCAP.PP.KD.BR 2010 | wb/NY.GDP.PCAP.PP.KD.BR | 18062.0 | 18062.1581 | True |
| wb/NY.GDP.PCAP.PP.KD.BR 2025 | wb/NY.GDP.PCAP.PP.KD.BR | 20025.0 | 20024.6968 | True |
| wb/PA.NUS.GDP.PLI.BR 2010 | wb/PA.NUS.GDP.PLI.BR | 78.9 | 78.9061 | True |
| wb/PA.NUS.GDP.PLI.BR 2025 | wb/PA.NUS.GDP.PLI.BR | 45.7 | 45.7182 | True |
| credit_gdp 2010 (Dec) | credit_gdp | 44.1 | 44.08 | True |
| credit_gdp 2008 (Dec) | credit_gdp | 39.7 | 39.68 | True |
| credit_gdp Aug 2026 | credit_gdp | 55.4 | 55.44 | True |
| household_debt_income 2010 mean | household_debt_income | 31.7 | 31.7342 | True |
| household_debt_income 2026 YTD mean | household_debt_income | 49.8 | 49.8271 | True |
| real_policy_rate 2010 mean | real_policy_rate | 5.0 | 5.0132 | True |
| real_policy_rate 2026 YTD mean | real_policy_rate | 10.4 | 10.3837 | True |
| Gini 2024 | wb/SI.POV.GINI.BR | 50.3 | 50.3 | True |
| Gini 2008 | wb/SI.POV.GINI.BR | 54.0 | 54.0 | True |
| Ibovespa USD 2025 return % | ibovespa_usd | 50.8 | 50.7504 | True |
| brl_usd year-end 2024 | brl_usd | 6.192 | 6.1923 | True |
| brl_usd year-end 2025 | brl_usd | 5.502 | 5.5024 | True |
| BRL appreciation 2025 % | brl_usd | 12.5 | 12.5382 | True |
| gold reserves 2010 $bn | wb/FI.RES.TOTL.CD.BR-XGLD | 1.5 | 1.5186 | True |
| gold reserves 2025 $bn | wb/FI.RES.TOTL.CD.BR-XGLD | 24.2 | 24.2163 | True |
| gold share of reserves 2025 % | wb/FI.RES.TOTL.CD.BR-XGLD | 6.8 | 6.7546 | True |
| Findex account 2011 | wb/account.t.d.BRA | 55.9 | 55.8604 | True |
| Findex account 2024 | wb/account.t.d.BRA | 86.4 | 86.3812 | True |
| Pix count 2025 bn | pix_transactions_count | 71.3 | 71.3201 | True |
| Pix per person 2025 | pix_transactions_count/population | 326.0 | 325.6194 | True |

## 3. Claim map

`verdict` = is the note's statement true in the data. `thesis_dir` = pro if the statement, when true, favours the thesis; con if it is a weakness. Untestable claims are excluded from scores.

| claim_id | pillar | claim | status | statistic | threshold | verdict | thesis_dir | thesis_score | note |
|---|---|---|---|---|---|---|---|---|---|
| E1 | physical | Oil production rising (pre-salt) | T | trend 5.1%/yr 2000-10 vs 4.1%/yr 2011-25; net energy imports 23.6% (2000) -> -13.7% (2023) | post-2010 trend > 0 and net imports < 0 | Supported | pro | 1.0 |  |
| E2 | physical | One of the cleanest grids | P | renewable electricity 84.7% (2010) -> 77.4% (2021); WS share 2025 cited in E4 | >= 75% and not falling | Partial | pro | 0.5 | Level true; series stale (2021) -> Partial; 'one of the cleanest' ranking needs peers (untestable) |
| E3a | physical | Hydro is core but fragile (drought -> power cost) | T | CMO 3.47x higher in months with EAR<40%; drought years 2015/2017/2021 mean CMO 482 vs 156 R$/MWh | CMO ratio > 2x in low-EAR months | Supported | con | 0.0 |  |
| E3b | physical | 2021 drought worst in 91 years | P | national EAR 2021 min 23.6% ranks #6 lowest of 12 years (2015-2026); 2017 min 17.8% | 2021 in top-2 stress years | Partial | con | 0.5 | '91 years' refers to SE/CO inflows, not in warehouse; on national EAR and CMO, 2021 is not the sample extreme |
| E4 | physical | Wind+solar now significant; diversification makes the thesis sturdier | T | WS share 2025 29.8%; EAR->logCMO slope 2015-21 -0.065 vs 2022-26 -0.087 | share >= 20% and EAR->CMO sensitivity smaller in 2022-26 | Partial | pro | 0.5 | log slope did not shrink (CMO ~0 floor in 2022-23); levels slope fell ~2/3 but confounded by full reservoirs since 2022 |
| E5 | physical | Cane ethanol E30 / flex-fuel | U |  |  | Untestable | pro |  | no ethanol series; proxy combustible renewables % energy only |
| E6 | physical | Caatinga solar | U |  |  | Untestable | pro |  | no regional data |
| E7 | physical | EU CBAM favours Brazilian charcoal / clean steel | U |  |  | Untestable | pro |  | no steel/charcoal series |
| W1 | physical | Huge freshwater; withdrawals far below renewal | T | withdrawals 1.20% of internal resources (2022); slope +0.010 pts/yr | < 5% and flat | Supported | pro | 1.0 |  |
| W2 | physical | Contrast with Ogallala / North China Plain / Punjab | U |  |  | Untestable | pro |  | no peer data |
| A1 | physical | Grain output 47 Mt (1977) -> 354 Mt with far smaller area growth | T | cereals 31 -> 139 Mt; yield share of output growth 115% (1977-2010), 35% (2010-24), 82% (1977-2024) | yield share > 50% in both windows | Partial | pro | 0.5 | WB cereals only (soy excluded); the 47->354 Mt CONAB 'grãos' levels are not in the warehouse; post-2010 growth is mostly AREA (second-crop corn) |
| A2 | physical | #1 exporter of soy, beef, sugar, coffee, OJ, chicken, cotton | P | soy $23.3bn->$43.5bn; beef $5.7bn->$16.5bn; coffee $6.1bn->$14.9bn; sugar $9.5bn->$14.1bn | export values growing (world rank untestable) | Partial | pro | 0.5 | no OJ/chicken/cotton series; world rank needs peers |
| A3 | physical | Northern frontier / Arco Norte ports | U |  |  | Untestable | pro |  | no port/regional data |
| A4 | physical | Hidden dependency on imported fertilizer | T | fertilizer imports $4.6bn (2014) -> $7.8bn (2025), trend +9.6%/yr | imports rising | Supported | con | 0.0 |  |
| M1 | physical | Niobium dominance | P | niobium exports $1.74bn (2014) -> $2.66bn (2025), trend +4.7%/yr | USD exports large/growing (world share untestable) | Partial | pro | 0.5 |  |
| M2 | physical | #2 rare-earth reserves | U |  |  | Untestable | pro |  | no reserves data |
| M3 | physical | High-grade iron ore | P | H2: Oil export tonnes +8.2%/yr vs iron ore +1.0%/yr since 2016; pre-salt = 79% of oil output (Aug 2026); H3: ρ(Vale revenue, iron-ore US$/t) = 0.77 over 42 quarters; tonnes trend +1.0%/yr | volume/price evidence (grade untestable) | Partial | pro | 0.5 | cites hypothesis_tests H2/H3 |
| M4 | physical | Lithium | P | lithium natural capital $2m (1995) -> $174m (2020) | rising | Partial | pro | 0.5 | stale (2020) -> Partial at most |
| M5 | physical | Brazil as hedge vs China processing dominance | P | China share of exports 18.4% (12m to 2014-12-01) -> 29.6% (12m to 2026-08-01): China is Brazil's buyer, not a rival | reframed: dependence on China as buyer | Partial | pro | 0.5 |  |
| C1 | institutional | Credit/GDP ~30% (2008) -> ~54% now; room to grow | T | BCB credit/GDP 39.7% (Dec 2008) -> 55.4% (Aug 2026); WB broader def 45.8% -> 75.1% | path rising; quoted levels match | Partial | pro | 0.5 | direction right; '~30% in 2008' is wrong (39.7%); 30% matches 2000-04 (27.3%/25.5%) |
| C2 | institutional | Household debt rising / stretched | T | debt/income 31.7% (2010) -> 49.9% (Jul 2026); debt service 28.7% (series max 28.7%) | DSR at/near series max | Supported | con | 0.0 |  |
| C3 | institutional | Cost of credit is the problem: Selic 14.5%, inflation 5-6%, real 8-11% | T | Apr 2026: Selic 14.50%, IPCA 12m 4.39% (2026 range 3.81-4.72), ex-ante real 10.7%; lending spread 32.5 pts (2024) | ex-ante real policy rate > 5% | Supported | con | 0.0 | Selic and real-rate numbers correct; 'inflation 5-6%' is too high (IPCA 12m 3.8-4.7% in 2026); 'highest in world' untestable |
| C4 | institutional | Banks super-profitable: wide spreads, concentration | T | spread 32.5 pts (2024); 5-bank conc 79.4% / 3-bank 38.7->70.4% (2021); bank ROE 13.2% (2021); Itaú net income/revenue 11.6% (2025) | spread > 20 pts and 5-bank conc > 60% | Partial | con | 0.5 | thresholds met but concentration/ROE series stale (2021) -> Partial |
| C5 | institutional | BCB buying gold (+43t in 2025), diversifying away from USD | P | gold $4.1bn (1.2% of reserves, 2020) -> $24.2bn (6.8%, 2025); 2024->25 x2.23 | gold share rising sharply | Partial | pro | 0.5 | value share rising; tonnage (+43t) untestable (no gold price in warehouse to split price vs volume) |
| C6 | institutional | Pix near-universal | T | account ownership 55.9% (2011) -> 86.4% (2024); Pix 71.3bn tx in 2025 = 326/person | account > 80% and Pix > 100/person/yr | Supported | pro | 1.0 |  |
| C7 | institutional | Hyperinflation as a 'vaccine' against debt | P | private credit 55.4% of GDP (modest) but gross public debt 82.9% (Aug 2026); r-g +5.1 pts (L3) | low leverage overall | Partial | pro | 0.5 | private side fits; public-debt side contradicts |
| I1 | institutional | Inequality persists | T | Gini 53.7 (2009; no 2010 survey) -> 52.9 (2011) -> 50.3 (2024); slope -0.46/yr 1995-2010 vs -0.16/yr 2011+ | Gini > 45 ('persists') | Supported | con | 0.0 | persists in level, but still slowly improving |
| I2 | institutional | Corruption / weak institutions persist | T | WGI: 4/6 dimensions lower in 2011-24 than 1996-2010; control of corruption -0.02 -> -0.41; rule of law -0.04 -> -0.45 | post-2010 WGI mean <= pre-2010 | Supported | con | 0.0 | worsened, not just persisted |
| I3 | institutional | Hard to do business | P | Doing Business score 59.1/100 (2019) | score < 65 | Partial | con | 0.5 | discontinued 2019 -> Partial |
| I4 | institutional | Weak schools | P | PISA maths 377 (2015); human capital/capita $51,838 (2010) -> $63,922 (2020) | PISA < 420 | Partial | con | 0.5 | PISA stale (2015) -> Partial |
| I5 | institutional | Tax complexity | P | tax revenue 15.4% of GDP (2024); compliance-time series end 2019 | complexity measure | Partial | con | 0.5 | complexity itself only in stale DB data |
| I6 | institutional | Expensive capital -> low investment | T | GFCF 20.5% (2010) -> 16.8% (2025); mean 2011-25 minus 1996-2010 = -0.7 pts (CI -2.3, +1.2) | GFCF < 20% and post-2010 mean not higher | Supported | con | 0.0 |  |
| I7 | institutional | Slow start: slavery, plantations, land concentration | U |  |  | Untestable | con |  | historical; no land-Gini |
| G1 | market | China share of Brazil's trade rising | T | China share of exports (12m) 18.4% -> 29.6%; trend +1.05 pts/yr; L4 (12m to Aug 2026): US -14.3%, China +19.0% | share rising | Supported | pro | 1.0 |  |
| G2 | market | Global South share of trade rising | P | proxy non-US/EU share 71.4% -> 75.9% | proxy rising | Partial | pro | 0.5 | only China/US/EU destinations exist |
| G3 | market | EU-Mercosur deal benefits | U |  |  | Untestable | pro |  |  |
| R1 | market | Ibovespa ~+51% in USD in 2025 | T | 50.8% | within 2 pts of 51% | Supported | pro | 1.0 |  |
| R2 | market | BRL +12-13% vs USD in 2025 | T | 12.5% | 12-13% | Supported | pro | 1.0 |  |
| R3 | market | Foreign B3 inflows R$56.5bn Jan-Apr 2026 | U | no B3 flow series; WB annual portfolio equity net inflows $-17.5bn (2024), $-5.0bn (2025) |  | Untestable | pro |  | annual WB data shows net OUTflows in 2024-25 (different period/definition) |
| R4 | market | Rerating underway | P | market cap/GDP 70.0% (2010) -> 38.2% (2025); 10y real yield 7.63% (2026 YTD) vs 5.17% avg 2015-24 | valuation rising | Partial | pro | 0.5 | embi_brazil stale (2024-07) |
| X3a | market | Brazil growth/equity is driven by the commodity cycle (3a) | T | monthly OLS dlog Ibov USD ~ dlog ToT + dlog Brent R2=0.12; rho(Ibov,Brent)=0.34 | R2 > 0.3 (or rho > 0.4) | Partial | pro | 0.5 |  |
| X3b | institutional | Cost of credit is binding (real rate -> credit/activity, 3b) | T | rho(real rate_t, Y_t+k), most negative lag 6-18m: household credit -0.19 @k=10 (CI -0.64,0.12, n=222); corporate -0.18 @k=7 (CI -0.59,0.08); IBC-Br YoY 0.13 @k=6 (CI -0.15,0.37); post-2010 at same lag: household -0.49 (CI -0.77,-0.07, n=178), corporate -0.42 (CI -0.74,-0.06); delinquency +0.84 @k=9; annual dGFCF beta -0.10 (CI -0.29,-0.01, n=24) | rho < -0.3 at lag 6-18m with CI excluding 0 (>=2 credit/activity series) | Supported | con | 0.0 | binds on credit only in the post-2010 window (full-sample CIs straddle 0, 2008-10 flips sign); activity (IBC-Br) shows no negative response |
| X3c | market | Endowment gains convert into income / USD returns (3c) | T | GDP pc PPP CAGR 2.58%/yr 2000-10 vs 0.69%/yr 2010-25; USD equity index 104.9 (Dec 2010) -> 75.9 (Dec 2025); composites 2025 (z, 2010=0): endowment +1.92, institutions -2.16, outcome -0.81 | GDP pc PPP CAGR post-2010 > pre-2010, or USD equity above 2010 level | Refuted | pro | 0.0 |  |
| X3e | market | Brazil equity is a commodity hedge (beta>0, CI excl. 0, 3e) | T | Ibov USD on composite: beta 0.29 (CI 0.12,0.47), rho 0.31 (CI 0.11,0.49, n=320) -> 'partial hedge'; pre/post-2010 Brent beta 0.21 vs 0.29 | beta > 0 with CI excluding 0 | Supported | pro | 1.0 | rubric met, but rho only 0.31 ('partial hedge') and the domestic control Itaú has the same composite beta -> largely a global risk-on beta, not a commodity-specific hedge |

Series ids and last dates per claim are in `claim_map.csv` (`series_ids`, `last_dates`).

### Note claims that are factually wrong or off

- **Credit/GDP "~30% in 2008"** — wrong: BCB `credit_gdp` was 39.7% in Dec 2008 (Banco Central SGS, last 2026-08-01); ~30% matches 2000–04 (Dec 2000 27.3%, Dec 2004 25.5%). "~54% now" is close (55.4%, Aug 2026).
- **"Inflation 5–6%"** — too high: `ipca_12m` was 4.39% in Apr 2026 and ranged 3.81–4.72% in 2026 (BCB, last 2026-08-01). Selic 14.5% (Apr 2026 end) and real 8–11% (ex-ante 10.7%) are right.
- **"2021 drought worst in 91 years"** — not visible in national data: 2021 EAR minimum 23.6% ranks only 6th-lowest of 2015–2026 (2017: 17.8%, 2015: 20.2%); 2021 mean CMO R$530 < 2015 R$567 (`stored_energy_ear`, `cmo_power_cost`, ONS, last 2026-10-02). The 91-year claim is about SE/CO inflows, which the warehouse lacks.
- **"47 Mt → 354 Mt with far smaller area growth"** — direction right over 1977–2024 (yield = 82% of cereal output growth), but since 2010 area expansion drove 65% of growth (second-crop corn): WB `wb/AG.PRD.CREL.MT.BR`/`AG.LND.CREL.HA.BR` (last 2024-12-31). The 47/354 Mt levels are CONAB grains incl. soy, not in warehouse.
- **"Foreign B3 inflows R$56.5bn Jan–Apr 2026"** — untestable; the only flow series (`wb/BX.PEF.TOTL.CD.WD.BR`, World Bank, last 2025-12-31) shows net portfolio-equity OUTflows of $17.5bn (2024) and $5.0bn (2025).
- **"Wind+solar make the thesis sturdier"** — share is real (29.8% in 2025) but the drop in EAR→power-price sensitivity is not robust (falls in levels, not in logs, and confounded by full reservoirs since 2022; see 3d).
- Confirmed exactly: Ibovespa +50.8% in USD in 2025; BRL +12.5% vs USD in 2025; Pix 326 transactions/person in 2025; gold 6.8% of reserves (2025).

## 4. Comparative frame (Brazil vs its 2010 self; US only via US-relative series)

No peer countries in warehouse; US comparison only via US-relative WB series (PLI, US=100) and the USD equity index. Convergence-to-US GDP ratio cannot be computed in-warehouse.

| series | 1990 | 2000 | 2010 | 2019 | 2025 |
|---|---|---|---|---|---|
| GDP pc PPP (2021 int$) `wb/NY.GDP.PCAP.PP.KD.BR` | 12,633.3 | 14,005.3 | 18,062.2 | 18,018.6 | 20,024.7 |
| Price level, US=100 `wb/PA.NUS.GDP.PLI.BR` | 38.6 | 41.4 | 78.9 | 56.2 | 45.7 |
| REER (2010=100) `wb/PX.REX.REER.BR` | 114.7 | 76.5 | 100.0 | 69.9 | 59.1 |
| USD equity index, year-end `wb/DSTKMKTXD_M.BRA` | – | 19.4 | 104.9 | 71.1 | 75.9 |

Pre-2010 (1991–2010) vs post-2010 (2011–2025) annual means, block-bootstrap (block 3) CI on the difference:

| measure | pre | post | post − pre [95% CI] | post ex-2020 | post 2013+ |
|---|---|---|---|---|---|
| real GDP growth % (`wb/NY.GDP.MKTP.KD.ZG.BR`, last 2025-12-31) | 3.17 (n=20) | 1.34 (n=15) | -1.83 [-3.94, -0.36] | 1.66 | 1.09 |
| GDP pc PPP growth % (`wb/NY.GDP.PCAP.PP.KD.BR`, last 2025-12-31) | 1.83 (n=20) | 0.73 (n=15) | -1.11 [-3.34, +0.50] | 1.05 | 0.51 |
| output per worker growth % (`ilostat/GDP_205U_NOC_NB.BRA`, last 2025-12-31) | 1.15 (n=19) | 0.40 (n=15) | -0.75 [-2.32, +0.38] | 0.08 | 0.12 |
| GFCF % GDP (level) (`wb/NE.GDI.FTOT.ZS.BR`, last 2025-12-31) | 18.50 (n=20) | 17.54 (n=15) | -0.96 [-2.67, +0.67] | 17.61 | 17.06 |
| cereal yield growth % (`wb/AG.YLD.CREL.KG.BR`, last 2024-12-31) | 4.65 (n=20) | 2.13 (n=14) | -2.52 [-6.41, +2.16] | 2.39 | 1.37 |
| oil output growth % (`oil_production`, last 2026-07-01) | 5.44 (n=10) | 4.12 (n=15) | -1.32 [-3.41, +1.26] | 4.04 | 4.70 |

Reading: Brazil became ~42% cheaper relative to the US (PLI 78.9 → 45.7) and real GDP growth fell by 1.8 pts/yr after 2010 (CI excludes 0). Convergence to US income cannot be computed in-warehouse (no US series).

## 5. Correlation analyses

Method: growth rates / log-differences; Pearson + Spearman; 95% CI from moving-block bootstrap (block 12 monthly, 4 quarterly, 3 annual; 2,000 resamples); p-values by permutation (2,000 shuffles); n<36 monthly / n<10 annual not reported. Pre = ≤2010, post = ≥2011; robustness: split at 2012, ex-2020.

Monthly panel SQL (one query per series in code; equivalent to):
```sql
SELECT series_id, date_trunc('month', date) AS ym,
  CASE WHEN series_id IN ('ibovespa_usd','brl_usd','brent_usd','wb/DSTKMKTXD_M.BRA') THEN arg_max(value, date) ELSE avg(value) END AS v
FROM v_observations WHERE date <= current_date AND series_id IN ('ibovespa_usd','brl_usd','brent_usd','wb/TOT.BRA', ... ) GROUP BY 1,2
-- equity/FX/credit_gdp/total_return_*: arg_max(value, date) (month-end); rates, EAR, CMO, flows: avg(value)
```
Annual SQL:
```sql
SELECT year, value FROM v_annual WHERE series_id = ? AND is_complete AND year <= current year ORDER BY year
-- year-end FX/equity:
SELECT EXTRACT(year FROM date)::INT AS year, arg_max(value, date) FROM v_observations WHERE series_id = ? AND date <= current_date GROUP BY 1
```

### 3a. Growth, BRL, Ibovespa (USD) vs terms of trade / Brent

ToT validation: annual mean of `wb/TOT.BRA` vs `wb/TT.PRI.MRCH.XD.WD.BR` 2005–24 ρ=1.000 (n=20) → passes (>0.9), monthly ToT used.

**Monthly Δlog Ibovespa USD vs Δlog Brent** (`ibovespa_usd` (Derived, last 2026-10-01); `brent_usd` (IPEAData, last 2026-09-29)):

| window | result |
|---|---|
| full (2000-02→2026-09) | ρ=+0.34 (Spearman +0.24), CI [+0.12, +0.54], p_perm=0.001, n=320 |
| pre (2000-02→2010-12) | ρ=+0.22 (Spearman +0.18), CI [-0.09, +0.50], p_perm=0.013, n=131 |
| post (2011-01→2026-09) | ρ=+0.44 (Spearman +0.29), CI [+0.15, +0.65], p_perm=0.001, n=189 |
| pre2012 (2000-02→2012-12) | ρ=+0.24 (Spearman +0.21), CI [-0.03, +0.51], p_perm=0.002, n=155 |
| post2012 (2013-01→2026-09) | ρ=+0.45 (Spearman +0.28), CI [+0.13, +0.66], p_perm=0.001, n=165 |
| ex2020 (2000-02→2026-09) | ρ=+0.22 (Spearman +0.20), CI [+0.05, +0.40], p_perm=0.001, n=308 |

**Monthly Δlog BRL/USD vs Δlog Brent** (negative = BRL strengthens with oil):

| window | result |
|---|---|
| full (2000-02→2026-09) | ρ=-0.23 (Spearman -0.20), CI [-0.37, -0.07], p_perm=0.001, n=320 |
| pre (2000-02→2010-12) | ρ=-0.15 (Spearman -0.16), CI [-0.43, +0.12], p_perm=0.079, n=131 |
| post (2011-01→2026-09) | ρ=-0.28 (Spearman -0.22), CI [-0.42, -0.10], p_perm=0.001, n=189 |
| pre2012 (2000-02→2012-12) | ρ=-0.17 (Spearman -0.19), CI [-0.44, +0.05], p_perm=0.036, n=155 |
| post2012 (2013-01→2026-09) | ρ=-0.29 (Spearman -0.20), CI [-0.44, -0.09], p_perm=0.001, n=165 |
| ex2020 (2000-02→2026-09) | ρ=-0.16 (Spearman -0.18), CI [-0.32, -0.02], p_perm=0.007, n=308 |

**Monthly Δlog Ibovespa USD vs Δlog ToT**: full ρ=+0.05 (Spearman +0.04), CI [-0.06, +0.16], p_perm=0.363, n=311 — no monthly link with the broad ToT index.

OLS Δlog Ibov USD ~ Δlog ToT + Δlog Brent (2000-02→2025-12, n=311): β_ToT=+0.06 [-0.39, +0.57], β_Brent=+0.28 [+0.11, +0.40], R²=0.12 (pre 0.05, post 0.21). Post×Brent interaction +0.07 [-0.23, +0.40] (not significant). Rolling 60m ρ(Ibov, Brent): mean 0.17 pre vs 0.47 post, latest 0.16 (2026-09).

**Quarterly Δlog real GDP vs Δlog ToT** (`wb/NYGDPMKTPSAKD_Q.BRA`, World Bank, last 2025-12-31), lag 0:

| window | result |
|---|---|
| full (1991-04→2025-10) | ρ=+0.38 (Spearman +0.32), CI [+0.17, +0.50], p_perm=0.001, n=139 |
| pre (1991-04→2010-10) | ρ=+0.46 (Spearman +0.39), CI [+0.13, +0.60], p_perm=0.001, n=79 |
| post (2011-01→2025-10) | ρ=+0.28 (Spearman +0.17), CI [-0.03, +0.46], p_perm=0.035, n=60 |
| pre2012 (1991-04→2012-10) | ρ=+0.47 (Spearman +0.40), CI [+0.16, +0.60], p_perm=0.001, n=87 |
| post2012 (2013-01→2025-10) | ρ=+0.26 (Spearman +0.13), CI [-0.13, +0.46], p_perm=0.058, n=52 |
| ex2020 (1991-04→2025-10) | ρ=+0.37 (Spearman +0.29), CI [+0.11, +0.51], p_perm=0.001, n=135 |

CCF ρ(ToT_t, GDP_t+k), k = 0..4 quarters: full: k0=+0.38, k1=+0.04, k2=-0.02, k3=+0.01, k4=+0.08; pre: k0=+0.46, k1=+0.05, k2=-0.15, k3=-0.03, k4=+0.04; post: k0=+0.28, k1=-0.02, k2=+0.04, k3=+0.00, k4=+0.10

**Annual real GDP growth vs Δlog ToT** (`wb/NY.GDP.MKTP.KD.ZG.BR`):

| window | result |
|---|---|
| full (1992→2025) | ρ=+0.60 (Spearman +0.64), CI [+0.39, +0.79], p_perm=0.001, n=34 |
| pre (1992→2010) | ρ=+0.71 (Spearman +0.75), CI [+0.52, +0.82], p_perm=0.001, n=19 |
| post (2011→2025) | ρ=+0.43 (Spearman +0.41), CI [+0.04, +0.69], p_perm=0.105, n=15 |
| pre2012 (1992→2012) | ρ=+0.71 (Spearman +0.74), CI [+0.57, +0.87], p_perm=0.001, n=21 |
| post2012 (2013→2025) | ρ=+0.41 (Spearman +0.34), CI [-0.11, +0.70], p_perm=0.163, n=13 |
| ex2020 (1992→2025) | ρ=+0.64 (Spearman +0.66), CI [+0.45, +0.82], p_perm=0.001, n=33 |

Read-out: equity R² < 0.3 → Brazil's USD equity is **not** a pure commodity proxy; its link runs through Brent (ρ≈0.44 post-2010), not through the broad ToT index. GDP's sensitivity to ToT **fell** after 2010 (quarterly ρ 0.46 → 0.28, post CI includes 0): the endowment matters less for growth, not more. Chart: `charts/3a_rolling_corr.html`.

### 3b. High real rate vs credit, investment, GDP

X = `real_policy_rate` (Derived, ex-ante Selic − Focus IPCA 12m, last 2026-09-01). ρ(real rate_t, Y_t+k), k = −12…+24 months.

| Y | most-negative lag in 6–18m | ρ full [CI] (n) | ρ pre-2010 (n) | ρ post-2010 [CI] (n) | ex-2020 | ex-post rate ρ |
|---|---|---|---|---|---|---|
| household_credit_growth | 10 | -0.19 [-0.64, +0.12] (222) | 0.31 (44) | -0.49 [-0.77, -0.07] (178) | -0.15 | -0.19 |
| corporate_credit_growth | 7 | -0.18 [-0.59, +0.08] (222) | 0.13 (41) | -0.42 [-0.74, -0.06] (181) | -0.16 | -0.15 |
| credit_gdp_d12 | 6 | -0.19 [-0.47, +0.15] (291) | -0.60 (109) | -0.35 [-0.66, +0.03] (182) | -0.08 | -0.11 |
| ibc_br_yoy | 6 | +0.13 [-0.15, +0.37] (271) | -0.16 (90) | -0.08 [-0.43, +0.26] (181) | 0.18 | 0.17 |
| delinquency_rate | 18 | +0.63 [+0.44, +0.78] (186) | 0.75 (16) | 0.63 [+0.45, +0.78] (170) | 0.56 | 0.42 |

Annual OLS 2002–2025: ΔGFCF%GDP on real rate β=-0.100 [-0.29, -0.01], R²=0.16, n=24; GDP growth on real rate β=+0.114 [-0.24, +0.37]. r − g latest +5.1 pts (2026-08; L3: Aug 2026: interest rate on debt 12.3% vs nominal growth 7.2% → r − g = +5.1 pts).

Read-out: the cost of credit binds on **credit** post-2010 (household ρ −0.49, corporate ρ −0.42 at 7–10 month lags, CIs exclude 0) and predicts delinquency 9 months ahead (ρ +0.84); +1 pt real rate ≈ −0.10 pt GFCF/GDP the same year. It does **not** show up in monthly activity (IBC-Br ρ ≈ 0 or positive). Full-sample CIs straddle 0 because 2008–10 (counter-cyclical public-bank lending) flips the sign. Caveat: both sides persistent; block bootstrap mitigates but does not remove spurious-correlation risk. Chart: `charts/3b_ccf_real_rate.html`.

### 3c. Endowment improved, income did not converge

each component z-scored over 1995-2025 and shifted so 2010 = 0; equal weights; mean of available components (natural-capital and renewables series end 2020-2021; wind/solar excluded since it starts 2015)

Composites (z, 2010 = 0): 2024 endowment +1.51, institutions -2.40, outcome -1.07; 2025 endowment +1.92, institutions -2.16, outcome -0.81.

| series | CAGR 2000–10 | CAGR 2010–last | last year |
|---|---|---|---|
| `oil_production` | +5.37% | +4.00% | 2025 |
| `wb/AG.YLD.CREL.KG.BR` | +4.33% | +1.54% | 2024 |
| `wb/AG.PRD.CREL.MT.BR` | +4.91% | +4.49% | 2024 |
| `wb/NV.AGR.EMPL.KD.BR` | +5.01% | +4.72% | 2025 |
| `bop_goods_exports` | +13.81% | +3.77% | 2025 |
| `wb/NY.GDP.PCAP.PP.KD.BR` | +2.58% | +0.69% | 2025 |
| `ilostat/GDP_205U_NOC_NB.BRA` | +1.52% | +0.37% | 2025 |
| `wb/PA.NUS.GDP.PLI.BR` | +6.66% | -3.57% | 2025 |
| `wb/DSTKMKTXD_M.BRA(year-end)` | +18.36% | -2.13% | 2025 |
| `wb/NW.HCA.PC.BR` | +3.00% | +2.12% | 2020 |

OLS Δlog GDP pc PPP ~ Δlog ToT + ΔWGI mean (1997–2024, n=25): β_ToT=+0.29 [+0.14, +0.40], β_WGI=-2.23 [-24.17, +6.88], R²=0.35. Low power; ToT is the only significant driver of year-to-year income growth, institutions' year-to-year changes are too noisy to identify.

Read-out: GDP pc PPP CAGR 2.58%/yr 2000-10 vs 0.69%/yr 2010-25; USD equity index 104.9 (Dec 2010) -> 75.9 (Dec 2025); composites 2025 (z, 2010=0): endowment +1.92, institutions -2.16, outcome -0.81. Endowment up, institutions down, outcome down → physical gains did not convert into income or USD returns. Chart: `charts/3c_three_line_index.html`.

### 3d. Reservoirs vs power cost and inflation

EAR (level, bounded %) vs log CMO, lags 0–3: k0: ρ=-0.63 (Spearman -0.60), CI [-0.82, -0.31], p_perm=0.001, n=142; k1: ρ=-0.55 (Spearman -0.49), CI [-0.75, -0.13], p_perm=0.001, n=141; k2: ρ=-0.46 (Spearman -0.37), CI [-0.69, +0.05], p_perm=0.001, n=140; k3: ρ=-0.42 (Spearman -0.28), CI [-0.67, +0.18], p_perm=0.001, n=139

EAR vs administered-price inflation lags 0/3/6: 

Thermal share vs log CMO: ρ=+0.57 (Spearman +0.59), CI [+0.39, +0.76], p_perm=0.001, n=136.

Months with EAR < 40% (n=54): CMO R$427 vs R$123 → 3.47× (warehouse H4: 3.1×). Drought years 2015/2017/2021 vs others: CMO R$482 vs R$156; admin-price inflation 1.12 vs 0.36 %/mo; thermal share 23.2% vs 14.5%.

Diversification test — OLS log CMO ~ EAR + EAR×WS + WS (2015-07→2026-10, n=136): β_EAR=-0.103 [-0.15, -0.04], β_EAR×WS=+0.0006 [-0.00, +0.00], R²=0.45. Sub-sample slope of log CMO on EAR: 2015–21 -0.065 [-0.08, -0.04] (n=84) vs 2022–26 -0.087 [-0.13, -0.01] (n=58); difference -0.022 [-0.08, +0.06]. Rolling 36m ρ(EAR, log CMO): -0.66 (first window) → -0.19 (2026-10). Robustness in levels (CMO hit ~0 in 21 months of 2022–23, which distorts logs): R$/MWh per EAR point 2015–21 -14.9 [-16.35, -6.62] vs 2022–26 -4.9 [-7.87, -1.17].

Read-out (mixed; partly contradicts plan expectation): wind+solar reached 29.8% of generation in 2025 and the *correlation* between reservoirs and price weakened. In logs the slope did **not** shrink and the EAR×WS interaction is ~0; in levels the R$/MWh sensitivity per storage point fell by about two-thirds (−14.9 → −4.9, CIs barely overlap). But reservoirs have been much fuller since 2022 (min EAR 34–59% vs 18–24% in 2015–21) and CMO is convex in EAR, so a flatter slope at high storage is expected with or without wind+solar; and the late window has had no drought to test. Verdict E4: Partial — share is significant, the sturdiness claim is not yet demonstrated. Chart: `charts/3d_ear_vs_cmo.html`.

### 3e. Brazil equity vs the commodity cycle: hedge or high-beta proxy?

Monthly log-return betas (block-bootstrap CI) to Δlog Brent / iron-ore unit value / ToT / composite:

| asset | β Brent [CI] | β iron ore [CI] | β composite [CI] | ρ composite | n |
|---|---|---|---|---|---|
| ibovespa_usd | +0.26 [+0.10, +0.38] | +0.15 [+0.02, +0.28] | +0.29 [+0.12, +0.47] | +0.31 | 320 |
| PETR | +0.52 [+0.36, +0.68] | +0.20 [-0.03, +0.43] | +0.62 [+0.22, +0.87] | +0.42 | 176 |
| VALE | +0.20 [+0.12, +0.46] | +0.15 [-0.05, +0.37] | +0.27 [+0.10, +0.50] | +0.24 | 176 |
| SUZB | +0.20 [+0.11, +0.45] | +0.12 [-0.08, +0.29] | +0.29 [+0.13, +0.43] | +0.28 | 176 |
| PRIO | +0.76 [+0.58, +1.00] | +0.40 [+0.15, +0.60] | +0.97 [+0.52, +1.30] | +0.45 | 176 |
| AXIA | +0.27 [+0.03, +0.37] | +0.26 [+0.04, +0.48] | +0.42 [+0.15, +0.63] | +0.27 | 176 |
| ITUB | +0.24 [+0.03, +0.33] | +0.18 [+0.03, +0.36] | +0.35 [+0.11, +0.50] | +0.33 | 176 |
| IBOV_TR_USD | +0.28 [+0.11, +0.36] | +0.15 [+0.02, +0.28] | +0.37 [+0.13, +0.54] | +0.40 | 176 |

Δlog Ibovespa USD vs Δlog composite:

| window | result |
|---|---|
| full (2000-02→2026-09) | ρ=+0.31 (Spearman +0.23), CI [+0.11, +0.49], p_perm=0.001, n=320 |
| pre (2000-02→2010-12) | ρ=+0.22 (Spearman +0.18), CI [-0.09, +0.50], p_perm=0.013, n=131 |
| post (2011-01→2026-09) | ρ=+0.40 (Spearman +0.26), CI [+0.15, +0.58], p_perm=0.001, n=189 |
| pre2012 (2000-02→2012-12) | ρ=+0.24 (Spearman +0.21), CI [-0.03, +0.51], p_perm=0.002, n=155 |
| post2012 (2013-01→2026-09) | ρ=+0.39 (Spearman +0.24), CI [+0.13, +0.59], p_perm=0.001, n=165 |
| ex2020 (2000-02→2026-09) | ρ=+0.23 (Spearman +0.20), CI [+0.06, +0.41], p_perm=0.001, n=308 |

Ibovespa-USD beta to Brent: 2000_2010: +0.21 [-0.09, +0.46] (R² 0.05, n=131); 2011_2026: +0.29 [+0.13, +0.37] (R² 0.20, n=189); 2013_2026: +0.28 [+0.11, +0.36] (R² 0.21, n=165)

Decomposition (2012+): USD total-return beta +0.37 [+0.13, +0.54] = local BRL +0.26 [+0.07, +0.40] + FX +0.09 [+0.03, +0.16].

Up/down capture vs composite: up 0.26 (n=184), down 0.18 (n=136), asymmetry 0.69 (<1 = captures less downside than upside).

Rolling 60m Brent beta: mean 0.13 pre-2010 vs 0.37 post; latest 0.09 (2026-09); Itaú latest 0.04. Warehouse H5: US$100 in Jan 2012 → Petrobras $325, Vale $140, Ibovespa $99 (Oct 2026, dividends reinvested). H6: ρ(Suzano, BRL weakening) = +0.18; ρ(Itaú, BRL weakening) = -0.57 over 177 months.

Read-out: classification **partial hedge** (ρ 0.2–0.4). β>0 with CI excluding 0 → meets the plan's 'hedge' test, but (i) R² is only ~0.09–0.16, (ii) Itaú — the domestic-bank control — has the same composite beta (+0.35), so most of the co-movement is global risk appetite, and (iii) the latest rolling beta has fallen to ~0.1. Only PETR/PRIO are genuine oil-beta vehicles (β 0.5–1.0). Chart: `charts/3e_rolling_beta.html`.

## 6. Pillar scores and rubric roll-up

thesis_score per claim: pro-thesis claim Supported=1/Partial=.5/Refuted=0; for weaknesses the note concedes (con) the score is inverted, so a pillar score measures how far the evidence favours the 'new America' thesis in that column. Untestable excluded from the denominator. Pillar label: ≥0.75 Supported, 0.50–0.74 Partial, <0.50 Refuted. Columns: physical = Energy, Water, Agro, Minerals; institutional = Credit, Institutions (+3b); market = Trade, Allocation, 3a, 3c, 3e. 3d feeds claim E4 (physical).

- **physical**: 0.50 → Partial; coverage 13/19 = 68%; {'Partial': 9, 'Supported': 4}
- **institutional**: 0.32 → Refuted; coverage 14/15 = 93%; {'Partial': 7, 'Supported': 7}
- **market**: 0.69 → Partial; coverage 8/10 = 80%; {'Supported': 4, 'Partial': 3, 'Refuted': 1}

Overall logic: (1) physical ≥ 0.75 and institutional ≤ 0.50? physical 0.50, institutional 0.32 → no — institutional is low as expected, but physical misses the bar (direction holds: gap +0.18). (2) investment thesis: endowment converted into income/returns = False; equity is a commodity hedge (β>0, CI excl. 0) = True. → **Holds only partly for the physical column (score 0.50, below the 0.75 bar); institutional column refuted; returns not delivered post-2010**.

## 7. Untestable claims (with this warehouse)

- E5 Cane ethanol E30 / flex-fuel — no ethanol series; proxy combustible renewables % energy only
- E6 Caatinga solar — no regional data
- E7 EU CBAM favours Brazilian charcoal / clean steel — no steel/charcoal series
- W2 Contrast with Ogallala / North China Plain / Punjab — no peer data
- A3 Northern frontier / Arco Norte ports — no port/regional data
- M2 #2 rare-earth reserves — no reserves data
- I7 Slow start: slavery, plantations, land concentration — historical; no land-Gini
- G3 EU-Mercosur deal benefits — 
- R3 Foreign B3 inflows R$56.5bn Jan-Apr 2026 — annual WB data shows net OUTflows in 2024-25 (different period/definition)
- Also untestable inside testable claims: world rankings (cleanest grid, #1 exporter, niobium/rare-earth shares, highest real rate in the world), gold tonnage (+43t), the 91-year drought, CONAB grain levels, ore grade, any Brazil-vs-US/China convergence ratio (no peer-country series).

## 8. Appendix A — every series used

| series_id | source | role | agg | last date |
|---|---|---|---|---|
| `beef_exports` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `bop_goods_exports` | Banco Central (SGS) | canonical | sum | 2026-08-01 |
| `brent_usd` | IPEAData | canonical | mean | 2026-09-29 |
| `brl_usd` | Banco Central (SGS) | canonical | mean | 2026-10-02 |
| `cmo_power_cost` | ONS | canonical | mean | 2026-10-02 |
| `coffee_exports` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `corporate_credit_growth` | Derived | derived | mean | 2026-08-01 |
| `credit_gdp` | Banco Central (SGS) | canonical | last | 2026-08-01 |
| `delinquency_rate` | Banco Central (SGS) | canonical | mean | 2026-08-01 |
| `exports_to_china` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `exports_to_eu` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `exports_to_us` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `exports_total` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `fertilizer_imports` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `gov_real_yield_10y` | Tesouro Direto | canonical | mean | 2026-10-02 |
| `gross_public_debt_gdp` | Banco Central (SGS) | canonical | last | 2026-08-01 |
| `household_credit_growth` | Derived | derived | mean | 2026-08-01 |
| `household_debt_income` | Banco Central (SGS) | canonical | mean | 2026-07-01 |
| `household_debt_service_ratio` | Banco Central (SGS) | canonical | mean | 2026-07-01 |
| `hydro_generation_share` | ONS | canonical | mean | 2026-10-01 |
| `ibc_br` | Banco Central (SGS) | canonical | mean | 2026-07-01 |
| `ibovespa_usd` | Derived | derived | mean | 2026-10-01 |
| `ilostat/GDP_205U_NOC_NB.BRA` | ILO (Dateno) | canonical | mean | 2025-12-31 |
| `ilostat/SDG_0821_NOC_RT.BRA` | ILO (Dateno) | canonical | mean | 2025-12-31 |
| `ipca_12m` | Banco Central (SGS) | canonical | mean | 2026-08-01 |
| `ipca_administered_prices` | Banco Central (SGS) | canonical | mean | 2026-08-01 |
| `iron_ore_exports_kg` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `iron_ore_unit_value` | Derived | derived | mean | 2026-08-01 |
| `net_income_brl@ITUB` | CVM | canonical | sum | 2026-06-30 |
| `niobium_exports` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `oil_production` | IPEAData | canonical | mean | 2026-07-01 |
| `pix_transactions_count` | Banco Central (Pix) | canonical | sum | 2026-09-01 |
| `population` | IBGE (SIDRA) | canonical | mean | 2025-12-31 |
| `r_minus_g` | Derived | derived | mean | 2026-08-01 |
| `real_policy_rate` | Derived | derived | mean | 2026-09-01 |
| `revenue_brl@ITUB` | CVM | canonical | sum | 2026-06-30 |
| `selic_target` | Banco Central (SGS) | canonical | mean | 2026-10-03 |
| `soy_exports` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `stored_energy_ear` | ONS | canonical | mean | 2026-10-02 |
| `sugar_exports` | ComexStat (MDIC) | canonical | sum | 2026-08-01 |
| `thermal_generation_share` | ONS | canonical | mean | 2026-10-01 |
| `total_return_brl@IBOV` | Derived | derived | last | 2026-10-01 |
| `total_return_usd@AXIA` | Derived | derived | last | 2026-10-02 |
| `total_return_usd@IBOV` | Derived | derived | last | 2026-10-01 |
| `total_return_usd@ITUB` | Derived | derived | last | 2026-10-02 |
| `total_return_usd@PETR` | Derived | derived | last | 2026-10-02 |
| `total_return_usd@PRIO` | Derived | derived | last | 2026-10-02 |
| `total_return_usd@SUZB` | Derived | derived | last | 2026-10-02 |
| `total_return_usd@VALE` | Derived | derived | last | 2026-10-02 |
| `wb/AG.LND.CREL.HA.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/AG.LND.FRST.K2.BR` | World Bank (Dateno) | canonical | mean | 2023-12-31 |
| `wb/AG.PRD.CREL.MT.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/AG.YLD.CREL.KG.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/BX.PEF.TOTL.CD.WD.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/CM.MKT.LCAP.GD.ZS.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/DSTKMKTXD_M.BRA` | World Bank (Dateno) | canonical | last | 2025-12-31 |
| `wb/EG.ELC.HYRO.ZS.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/EG.ELC.RNEW.ZS.BR` | World Bank (Dateno) | canonical | mean | 2021-12-31 |
| `wb/EG.IMP.CONS.ZS.BR` | World Bank (Dateno) | canonical | mean | 2023-12-31 |
| `wb/EG.USE.CRNW.ZS.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/EN.CLC.SPEI.XD.BR` | World Bank (Dateno) | canonical | mean | 2023-12-31 |
| `wb/ER.H2O.FWTL.ZS.BR` | World Bank (Dateno) | canonical | mean | 2022-12-31 |
| `wb/FI.RES.TOTL.CD.BR` | World Bank (Dateno) | alternate | mean | 2025-12-31 |
| `wb/FI.RES.XGLD.CD.BR` | World Bank (Dateno) | alternate | mean | 2025-12-31 |
| `wb/FR.INR.LEND.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/FR.INR.LNDP.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/FS.AST.PRVT.GD.ZS.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/GC.TAX.TOTL.GD.ZS.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/GFDD.EI.06.BR` | World Bank (Dateno) | canonical | mean | 2021-12-31 |
| `wb/GFDD.OI.01.BR` | World Bank (Dateno) | canonical | mean | 2021-12-31 |
| `wb/GFDD.OI.06.BR` | World Bank (Dateno) | canonical | mean | 2021-12-31 |
| `wb/GOV_WGI_CC_EST.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/GOV_WGI_GE_EST.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/GOV_WGI_PV_EST.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/GOV_WGI_RL_EST.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/GOV_WGI_RQ_EST.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/GOV_WGI_VA_EST.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/IC.BUS.EASE.DFRN.XQ.DB1719.BR` | World Bank (Dateno) | canonical | mean | 2019-12-31 |
| `wb/LO.PISA.MAT.BR` | World Bank (Dateno) | canonical | mean | 2015-12-31 |
| `wb/NE.GDI.FTOT.ZS.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/NV.AGR.EMPL.KD.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/NW.HCA.PC.BR` | World Bank (Dateno) | canonical | mean | 2020-12-31 |
| `wb/NW.NCA.MLIT.TO.BR` | World Bank (Dateno) | canonical | mean | 2020-12-31 |
| `wb/NW.NCA.SSOI.PC.BR` | World Bank (Dateno) | canonical | mean | 2020-12-31 |
| `wb/NW.NCA.TOTL.PC.BR` | World Bank (Dateno) | canonical | mean | 2020-12-31 |
| `wb/NY.GDP.MKTP.KD.ZG.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/NY.GDP.PCAP.PP.KD.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/NYGDPMKTPSAKD_Q.BRA` | World Bank (Dateno) | canonical | sum | 2025-12-31 |
| `wb/PA.NUS.GDP.PLI.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/PAY.TAX.COIT.AU.HRS.DB1719.BR` | World Bank (Dateno) | canonical | mean | 2019-12-31 |
| `wb/PX.REX.REER.BR` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/SI.POV.GINI.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/TOT.BRA` | World Bank (Dateno) | canonical | mean | 2025-12-31 |
| `wb/TT.PRI.MRCH.XD.WD.BR` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wb/account.t.d.BRA` | World Bank (Dateno) | canonical | mean | 2024-12-31 |
| `wind_solar_generation_share` | ONS | canonical | mean | 2026-10-01 |

Stale (last < 2022): `wb/EG.ELC.RNEW.ZS.BR`, `wb/GFDD.EI.06.BR`, `wb/GFDD.OI.01.BR`, `wb/GFDD.OI.06.BR`, `wb/IC.BUS.EASE.DFRN.XQ.DB1719.BR`, `wb/LO.PISA.MAT.BR`, `wb/NW.HCA.PC.BR`, `wb/NW.NCA.MLIT.TO.BR`, `wb/NW.NCA.SSOI.PC.BR`, `wb/NW.NCA.TOTL.PC.BR`, `wb/PAY.TAX.COIT.AU.HRS.DB1719.BR`.

## Appendix B — External data (not from warehouse)

None used. The verdict depends only on warehouse data.

## Recommendation

Ingest the same WB indicators for US/CN/IN/MX via the Dateno `wb/` namespace (e.g. `wb/NY.GDP.PCAP.PP.KD.US`) so the literal Brazil-vs-America comparison becomes possible.
