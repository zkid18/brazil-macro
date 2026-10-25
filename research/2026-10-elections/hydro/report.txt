STUDY 2 - HYDROLOGY/CLIMATE -> POWER COST -> INFLATION, AGRO AND EU ACCESS (Brazil, 2027-2030)
Run 2026-10-05. Warehouse brazil_macro.duckdb (read-only). Script: scratchpad/hydro/hydro_study.py. Pre-registration: preregistration.txt (2026-10-05T21:07:59Z, written before any W estimate).

======================================================================================================
SUMMARY
======================================================================================================
Why this: of ten candidates, it has the deepest unused data (ONS daily, CMO since 2005, IPCA, Focus, climate since 1960) and the most channels. 2015-21 had 125 or more days a year below 40% EAR; 2022-26 almost none. A very strong El Nino is building (ONI +2.16).

Verdicts (pre-registered):
- W1 Both agree: CMO 3.5x in droughts (CI 1.9-5.8); wind+solar did not significantly flatten the slope.
- W2 D: administered +0.37 pp per 10 EAR pts (CI -1.2/+1.9); exploratory episodes +3.0 pp (p 0.04).
- W3 D: Focus +0.24 pp (CI -0.15 to +0.55); Selic about 0.
- W4 F, fragile: IBC-Br -1.28 pp; -0.54 (n.s.) without 2021; 2001 -2.3 pts.
- W5 D/null: national SPEI has the wrong sign.
- W6 Partial: lower in all testable bands, none significant.
- W7 Partial by rule; D after a measurement-break fix.
- W8 F: drier and hotter (p ≤ 0.0002).
- W9: Petrobras thermal 2.4x; Axia -11 to -14% in 2021.
- W10: no EU penalty in fire years yet.
- W11 Both agree: 2022 suppression about -6 pp administered.

Transmission: droughts reach power prices and 12-month administered prices (+3 pp); electricity added about 1.1 pp to 2021 IPCA. Focus and the Selic moved only alongside Brent (2020-21: Focus +1.6, Selic +350-920 bp); pure hydro adds under 0.3 pp to Focus.

Diversification: no significant drop (real CMO ~25% lower at 40-60% EAR); untested below 40%.

Load: the 2023-24 excess (+8.7 pp) sits in the window when ONS added distributed generation to load (from Apr 2023). Since 2025 the residual is -1.5 pp. No data-centre signal yet. The 26.2 GW of requests are uncontracted.

Scenarios:
- Best: IPCA -0.3 to 0 pp, Selic -50 to 0 bp, exports 0 to +$5bn.
- Worst: IPCA +2.0 to +3.5 pp (or R$40-100bn fiscal), Selic +100 to +300 bp, GDP -1.0 to -2.5, exports -$8 to +2bn plus an EU tail of -$2 to -5bn.
- A severe drought (+1 to +2 pp IPCA) matches ToT -10% (+1.1 pp) but is 3-5x smaller for exports (ToT ±$14-22bn).

Limits: ~4 episodes; EAR from 2015; CMO SE/CO only; no electricity CPI or CONAB; fiscal costs unverified.

Charts: scratchpad/hydro/charts/1-8 (*.html).

======================================================================================================
1. WHY THIS UNCERTAINTY (plan B1 ranking)
======================================================================================================
#  Uncertainty                           Impact        Warehouse depth                      Covered?            Decision
1  Commodity/China cycle                 very high     ToT, Brent, ComexStat               yes (exports)       covered
2  Fiscal/debt, r-g                      high          NFSP, debt, NTN-B                    yes (politics)      covered
3  Climate/hydrology -> power -> CPI     medium-high   ONS daily 2015->, CMO 2005->,        only H4/E3/E4       PICK
                                                       IPCA comps 2000->, Focus, SPEI 1960->
4  BCB credibility/expectations          high          Focus, IPCA, Selic, NTN-B            partly              folded into 3 (transmission)
5  Petrobras governance/fuel policy      medium        CVM quarterly                        partly (H1)         runner-up
6  Organised crime / US FTO              medium        homicides                            no                  later
7  Tax reform IBS/CBS                    medium        WB tax 2010-24 only                  no                  not testable
8  STF-Congress-executive conflict       high          none                                 Study 1             -
9  Demographics/pension                  long-run      many                                 scorecard           -
10 AI/data-centre power demand           low-medium    electricity_load only                no                  folded into 3 (W7)
Why now: 2026-27 brings a very strong El Nino (ONI JAS 2026 +2.16; NOAA >90% chance of a very strong event, 75% chance of a historic one; W15, W16). CMSE expects lower hydro output in the North (W05-W07). The EUDR applies from 30 Dec 2026 (W42, C23). 2030 is an election year inside the horizon.

======================================================================================================
2. DATA CONSTRAINTS (plan 0.6-0.7) AND ANCHOR CHECK
======================================================================================================
Anchors reproduced (run before pre-registration; SQL below). Zero mismatches on the checked set:
- EAR annual mean/min: 2015 31.3/20.2, 2017 32.6/17.8, 2021 34.1/23.6, 2022 62.2/33.8, 2023 77.5/58.7, 2024 61.1/43.7, 2025 61.9/44.3.
- Days with EAR < 40: 341, 125, 308, 236, 184, 147, 253 for 2015-21; 8 in 2022; 0 in 2023-26.
- CMO annual mean (max): 2008 138 (637), 2014 829 (1,778), 2015 567 (2,159), 2021 530 (3,044), 2022 31, 2023 0, 2024 100 (625), 2025 248, 2026 YTD 231.
- Weeks with CMO > 500: 2014 43, 2015 17, 2021 15, 2017 12, 2018 10, 2024 3.
- Administered-price annual sums: 2015 16.8, 2021 15.8, 2022 -3.7, 2023 8.8, 2024 4.6, 2025 5.2 (2026 YTD 2.7).
- 2021 path: EAR 37.95 (Jul) to 24.27 (Oct). CMO 1,056 (Jul), 2,734 (Aug). Focus 3.45 to 5.29. ipca_12m 4.56 to 10.74. Selic 2.00 to 8.86 (December monthly mean).
- Other anchors also match: hydro share, wind+solar 4.7 to 29.8, load 61.4 to 79.6 GWmed, SPEI, heat days, yields, agri VA, 2001 GDP 4.24 to -0.93.
Differences (moving YTD windows, not breaking): 2026 YTD EAR mean 64.5 (plan 64.1); 2026 YTD load 80.5 GWmed (plan 81.5). Plan B4 says the "wet" base rate in 2015-21 was 1/7; the data say 0/7, since every year 2015-21 had at least 125 days below 40%.
Section 0.1 re-check: political_terms has 9 rows, political_events has 34, and registry/ is last touched at b79840b. The warehouse has no electricity-tariff or IPCA electricity sub-item, no CONAB, no PLD and no EAR before 2015.
Reconciliation with an external source: warehouse stored_energy_ear is 60.87 on 2026-10-02. ONS open data gives SIN 60.7% on 2026-10-04 (W01).
Gaps: CMO is SE/CO only. WB "cereal" excludes soy. Export series are USD only (no tonnage). SPEI is national (masks the SE/CO vs N/NE split). wb/AG.LND.PRCP.MM.BR is a constant and was not used. ONS load includes estimated MMGD from 2023-04-29 (W27), a level break inside the series.

Core SQL (all queries are stored verbatim in results.json["sql"]):
  -- anchors
  SELECT year(date) AS y, avg(value) AS mean, min(value) AS mn, sum(CASE WHEN value < 40 THEN 1 ELSE 0 END) AS days_lt40
  FROM v_observations WHERE series_id='stored_energy_ear' AND date <= current_date GROUP BY 1 ORDER BY 1;
  SELECT year(date) AS y, avg(value) AS mean, max(value) AS mx, sum(CASE WHEN value > 500 THEN 1 ELSE 0 END) AS weeks_gt500
  FROM v_observations WHERE series_id='cmo_power_cost' AND date <= current_date GROUP BY 1 ORDER BY 1;
  SELECT year(date) AS y, sum(value) AS admin_sum FROM v_observations WHERE series_id='ipca_administered_prices' AND date <= current_date GROUP BY 1;
  -- monthly panel (plan B3)
  SELECT series_id, date_trunc('month', date) AS ym, avg(value) AS v, min(value) AS v_min
  FROM v_observations WHERE date <= current_date AND series_id IN ('stored_energy_ear','cmo_power_cost', ... 31 ids ...) GROUP BY 1,2 ORDER BY 2,1;
  -- annual panel
  SELECT series_id, year, value, is_complete FROM v_annual WHERE series_id IN ('wb/EN.CLC.SPEI.XD.BR', ... ) AND year <= year(current_date);
  -- (only is_complete = TRUE rows are used)

======================================================================================================
3. PRE-REGISTRATION (verbatim file: preregistration.txt)
======================================================================================================
Shock S_t = max(0, 40 - EAR_t)/10, so one unit is 10 pts below 40. Episode month = a run of 3 or more months with EAR < 40. Daily episode = 90 or more days below 40.
Estimators: moving-block bootstrap (block 12 or 3, 2,000 draws, seed 0). Local projections at h = 0..12 with Brent 12m and own-lag controls.
Thresholds as in plan B2. "Supports" labels follow the rule set in that file. Exploratory additions made after it are flagged "exploratory":
- the episode placebo
- lagged SPEI
- the MMGD window split in W7
- excluding 2021 in W4

======================================================================================================
4. EPISODES (episodes.csv; daily EAR < 40 for >= 90 days, gaps <= 7 days merged)
======================================================================================================
start       end         days  minEAR  CMO mean/max  thermal%  admin12m  IPCA12m  dFocus  dSelic bp  dBrent%
2015-01-01  2015-07-14  195   20.2    905/2159      25.2      16.77     10.19    +0.37   +255       -39
2015-08-08  2016-01-26  172   27.5    147/260       23.9       8.26      8.41    -0.08   +47        -21
2016-09-24  2017-05-21  240   30.5    208/472       18.0       6.12      2.43    -0.97   -500       +14
2017-07-18  2018-03-08  234   17.8    412/861       21.5      11.20      4.31    -0.16   -375       +60
2018-07-16  2019-03-15  243   25.1    351/785       17.2       3.71      3.32    -0.71      0       -14
2019-09-13  2020-02-24  165   22.3    257/362       19.7       1.16      2.42    -0.66   -396       -24
2020-10-01  2021-03-04  155   23.1    309/744       20.4      14.75      9.80    +1.59   +352       +83
2021-06-25  2022-01-08  198   23.6    793/3044      26.7      11.53     11.15    +1.60   +924       +65
(The 2015 episode is left-censored: EAR starts 2015-01-01.) Pattern: Focus and the Selic rose only in the three episodes where Brent also rose or the tariff realignment hit (2015). In the other five they fell.

======================================================================================================
5. RESULTS W1-W11 (series_id, source, last date in Appendix A)
======================================================================================================
W1 Drought -> power price.
Series: stored_energy_ear, cmo_power_cost, wind_solar_generation_share and brent_usd (ONS and IPEAData), 2015-01 to 2026-10, 142 months, 54 of them episode months.
- CMO averages R$427/MWh in episode months vs R$123 otherwise: ratio 3.47x, 90% block-bootstrap CI 1.91-5.77. In real terms (Aug-2026 BRL) the ratio is 4.4x.
- H4 replication (EAR < 40 months, 2016+): 3.13x, which matches the warehouse H4 and Davidson.
- OLS of log(CMO_real+10), n 134, R2 0.50:
  - EAR slope -0.069 per point at WS 15% (CI -0.077 to -0.046).
  - EAR x WS interaction +0.0007 (CI -0.0019 to +0.0025, p 0.75), so the slope is -0.058 at WS 30%.
  - log Brent 0.008 (CI -1.32 to 0.73).
- Thermal share rises 0.23 pts per EAR point lost (R2 0.49).
VERDICT: Both agree (ratio ≥ 2x). D's addition, that wind+solar flattens sensitivity, is NOT supported: right sign, about 16% flatter, CI includes 0. Charts 1 and 2.

W2 Drought -> administered and headline inflation.
LP (ipca_administered_prices and ipca_monthly, BCB SGS, last 2026-08). Responses are cumulative pp per 10 pts below 40:
  h        0      3      6      9      12
  admin   +0.13  +0.14  +0.59  +0.92  +0.37   (h12 CI -1.20 to +1.94, p 0.70)
  headline+0.11  +0.24  +0.28  +0.24  +0.21   (h12 CI -0.55 to +1.11)
  services +0.10 +0.24  -0.23  -0.57  -0.62
Robustness at h12 (admin): drop 2015 +0.37; drop 2022 -0.17; continuous EAR +0.56 (CI -0.14 to +1.11); no controls +0.49.
VERDICT (pre-registered): D. The admin response is below +0.5 pp and its CI includes 0.
Exploratory checks, which point the other way on 12-month aggregates:
- Episode placebo (8 episodes vs 2,000 draws of 8 random start months): admin over the next 12 months is 9.19 vs 6.21 unconditional, +3.0 pp, one-sided p 0.036. Headline is 6.50 vs 5.28, +1.2 pp, p 0.08.
- Annual OLS 2015-25 (n 11): admin = 4.18 + 9.9·mean S - 6.0·election dummy (R2 0.58).
Reading: drought pass-through is real but policy-timed, through flags, the 2015 realignment and the 2022 reversal. So it does not show up as a stable monthly impulse.
Administered prices also contain fuels (Brent). Electricity alone (IBGE, W33-W34): +21.21% in 2021 x weight 5.08% gives about +1.1 pp of headline; -19.01% in 2022 gives about -0.8 pp. Chart 3.

W3 Drought -> expectations and Selic.
- Focus IPCA 12m peaks at +0.24 pp (h12, CI -0.15 to +0.55). Focus Selic 12m is +0.23 at h0, then about 0.
- Selic target peaks at +25 bp (h5, CI -71 to +110), and -11 bp at h12.
- Episode placebo: Focus +0.12 vs -0.20 (p 0.18); Selic +38 vs +15 bp (p 0.40).
2021 decomposition:
- ipca_12m rose 4.56 to 10.74 (+6.18).
- Administered 12m (compounded) rose 1.79 to 19.23. At a 25% weight (unverified, W35) that is about +4.4 pp, but it includes fuels with Brent +48% Jan-Nov.
- Electricity alone is about +1.1 pp.
- Focus rose 3.45 to 5.29 and the Selic 2.00 to 8.86 (December mean).
VERDICT: D. Neither Focus ≥ +0.5 nor Selic ≥ +50 bp with CI > 0. The 2021 rise in expectations and the Selic coincided with Brent +48-83%, post-COVID demand and fiscal noise. Hydro was one part of it. Chart 3.

W4 Drought -> output.
2001 (WB): GDP growth was 4.39 (2000), 1.39 (2001), 3.05 (2002), so 2001 was -2.33 pts vs its neighbours. Quarterly YoY went 4.24 (Q1), 2.30, 0.58, -0.93 (Q4). kWh per capita fell 7.8%. Confounds: the US recession, 9/11, Argentina.
Post-2015, IBC-Br 12m growth on S (Brent control, 2020-03..12 excluded, n 117): -1.28 pp per unit (CI -2.71 to -0.10, p 0.076). This meets F's rule.
Fragile:
- excluding 2020-03..2021-12 gives -0.54 (CI -1.70 to +0.25);
- load on S is -0.97 (CI -2.85 to +0.78);
- 2015-16 is a recession driven by other causes, and 2021 had no rationing (Q4 YoY +1.66).
VERDICT: F by rule, NOT robust. A rationing-type outcome costs about 2 pts. A price-only drought has an effect between 0 and -1.3 pp that the data cannot pin down.

W5 Drought -> agro.
1962-2023 (n 62), 100·dlog cereal yield (wb/AG.YLD.CREL.KG.BR) on SPEI:
- b = -1.32 (CI -2.98 to +0.13, p 0.14): WRONG sign (wetter means lower yield).
- SPEI x decade interaction: -0.55 (CI -1.42 to +0.29).
- Pre-2000 +0.03; post-2000 -2.67.
- Exploratory lagged SPEI: +1.27 (CI -0.73 to +3.25).
- Agri VA growth: -0.24 (CI -0.90 to +0.69).
Drought-year cereal yield changes are mixed: 2016 -17.9%, 2021 -16.0%, 2024 -6.5%, but 2015 +7.5% and 2023 +8.4%.
Export USD (ComexStat, 2015-23, n 9): corr with SPEI is soy +0.60, coffee +0.58, sugar -0.25. Coffee earned a record $11.4bn (2024) and $14.9bn (2025) after drought, because price offset volume.
VERDICT: D/null. National SPEI is the wrong regional measure. El Nino dries the North/Northeast and wets the South; La Nina dries the South. External context: CONAB 2025/26 was 361.7 Mt, with a record soy crop of 180.4 Mt. The 2026/27 first estimate is 366.6 Mt with soy area growth the smallest in 20 years. Coffee 2026 is a record 67.6M bags (W18-W20). Chart 5.

W6 Did diversification lower sensitivity? Real CMO by EAR band, 2015-21 vs 2022-26:
  band   n early/late  mean early/late (R$ real)  dlog late-early (90% CI)
  20-30  21/0          723/-                      untestable
  30-40  31/0          595/-                      untestable
  40-50  17/7          273/249                    -0.25 (-1.14, +0.51) p 0.62
  50-60  11/10          99/142                    -0.28 (-1.11, +0.59) p 0.54
  60+     2/39         116/98                     n too small early
- Common-support slope (EAR 40-65): -0.091 to -0.053 dlog per point. In levels the slope went from -24.0 to -5.3 R$ real per point (full ranges).
- 2024-H2: EAR 53.5, real CMO 218. 2017-18 months at EAR 40-55 (mean EAR 43.0): real CMO 364.
VERDICT: Partial. The direction is D in every testable band, but no CI excludes 0. Below 40% EAR, the regime that matters, nothing has been tested since 2022. Davidson E4 "Partial" stands. Chart 4.

W7 Load growth: heat, activity or data centres?
Annual fit 2016-22: load growth = 1.49 + 0.001·dCDD + 0.67·IBC growth (R2 0.53, n 7). Residuals:
- 2023 +3.24, 2024 +2.73, 2025 -2.17 (IBC-only model; CDD ends 2024). Mean +1.27, which is Partial under the pre-registered rule.
- Monthly check: 2023 +4.6, 2024 +4.4, 2025 -1.3, 2026 -1.8.
Exploratory measurement break: ONS added estimated MMGD to "carga" from 2023-04-29 (W27). Windows:
  2023-01..04              load y/y -0.2,  residual -2.95
  2023-05..2024-04 (break) load y/y +10.8, residual +8.73
  2024-05..12              load y/y +4.5,  residual +1.77
  2025-01..2026-09         load y/y +0.5,  residual -1.48
VERDICT: Partial by rule. D after the correction: the 2023-24 "excess" is mostly a measurement break, and from 2025 load is running below what activity implies.
External context:
- Data centres had 26.2 GW of grid-connection requests at end-2025, explicitly not contracted demand (W25).
- PDE 2035 reference case: +3.3%/yr to 115 GWmed. High case: +5.2%/yr with data-centre and H2 load, mostly 2031-35 (W24).
- REDATA passed the Senate on 2026-09-02 (W26).
- Possible inconsistency: ONS PMO forecasts Sep/Oct 2026 load at +4.7-4.9% y/y (W03, W09), while warehouse 2026 YTD load is +1.1%. Monitor.
Data-centre load is a 2030s risk, not visible in 2023-26 data. Chart 6.

W8 Climate trend.
Permutation test, 1960-99 vs 2010-latest, 10,000 shuffles:
- SPEI mean +0.16 to -1.11 (p 0.0002).
- Heat-35 days 0.15 to 0.72 (p 0.0001); variance x6.0 (p 0.002).
- CDD 4,121 to 4,653 (p 0.0001).
Six of the seven driest years since 1990 are 2012-2023: 2015 -2.56, 2023 -2.31, 2016 -2.27, 2012 -2.01, 2017 -1.89, 2019 -1.67.
VERDICT: F (3 of 3). Caveat: the WB/CCKP products are reanalysis-based. Chart 5.

W9 Companies.
Axia:
- Within-year monthly deviation: -1.1% in episodes vs +0.5% otherwise. Share of SIN -0.5 vs +0.2 pts.
- Annual: 112.2 TWh in 2021 vs 126.4 (2020) and 131.2 (2022), i.e. -11% and -14%.
Petrobras:
- 1,988 vs 817 GWh/month (2.4x); 28.1 TWh in 2021 vs 7.5 in 2022 (3.7x). Share 4.2 vs 1.6%.
USD returns on dEAR:
- Axia -0.30% per point (CI -0.78 to +0.08): falling storage is mildly positive for Axia, consistent with price offsets.
- Petrobras -0.15% per point (CI -0.82 to +0.23).
Descriptive reading: Axia volume loss is -1 to -2% monthly and -11% to -14% in a severe year, smaller than F's -10 to -20% per month. Petrobras is the drought hedge. Chart 7.

W10 Drought/fire -> EU access.
Tree-cover loss (wb/AG.LND.FRLS.HA.BR) spikes in 2016 (5.38 Mha), 2017 (4.52) and 2024 (4.39), each after an El Nino (2015/16, 2023/24). Corr with SPEI 2002-23 is -0.40.
Primary forest loss: 2016 2.83 and 2024 2.82 Mha, vs 1.1-1.8 typical.
EU export growth: 3.0% in fire years vs 2.9% in others. Exports were $48.3bn (2024) and $49.8bn (2025).
INPE fire counts: 278,299 in 2024 (highest since 2010) and 136,393 in 2025. PRODES 2025 was 5,731 km², -12% (W40-W41).
VERDICT: descriptive. No market penalty yet. But a very strong El Nino in 2026-27 implies a medium-to-high probability of a 2027 fire year, in the EUDR's first year (30 Dec 2026; Brazil "standard risk", W42-W43, C23-C25).

W11 Policy suppression vs pass-through.
- Administered inflation per unit of mean annual S: 2015 19.3, 2021 22.9, 2017-18 about 10.
- 2022: -3.72 pp despite the drought hangover, a residual of -6.5 pp vs the drought-only model. Election dummy -6.0 pp (n 11).
- Electricity in IPCA: -19.0% in 2022 (W34). That came from the LC 194/2022 ICMS cap, flag normalisation and sector loans; the loans were later repaid early with Eletrobras privatisation money (W30).
- The fiscal cost could NOT be verified: about R$27bn federal compensation (W29) and LC 194 losses (W28) are both low confidence with no URL. The TCU put the 2001 rationing cost at R$45.2bn (W32, medium).
VERDICT: Both agree. Suppression turns about 6 pp of administered inflation (about 1.5 pp of headline) into a fiscal and sector-debt cost.

BH (q = 0.10) over primary p-values: W1 q 0.000, W8 q 0.0003, W4 q 0.18, W5 q 0.25, W3 q 0.52, W2 q 0.70, W6 q 0.70. Only W1 and W8 survive.

======================================================================================================
6. SCENARIOS 2027-30 (scenario_matrix.csv: 16 cells + BEST/WORST; cross_table_tot.csv)
======================================================================================================
Probabilities (qualitative):
- Wet: MEDIUM. SIN EAR is 60.7% now vs 23.8% on the same date in 2021, and yellow flags have turned green (W12).
- One drought year: MEDIUM. The very strong El Nino dries the N/NE; SE/CO is ambiguous, 101.6% of MLT in 2015/16 vs 68.4% in 2023/24 (W10).
- Severe: LOW. It needs two poor wet seasons starting from 60% storage.
- Rationing tail: LOW (< 5%). Wind+solar is about 34% (last day), but LRCAP 2026 contracted only 2.2 of 4.2 GW (W07).
Ranges, pass-through and no storage/transmission (with storage/transmission the ranges are about 20% lower, an assumption from W6's point estimates):
  state             CMO R$/MWh  admin pp   headline pp  Focus pp    Selic bp    GDP pts      agro $bn
  Wet               0-150       0          0            0           0           0            0 to +3
  One drought year  300-600     +1 to +3   +0.3 to +1.0 0 to +0.3   0 to +50    -0.1 to -0.5 -5 to +3
  Severe            500-900     +3 to +6   +1.0 to +2.0 +0.2 to +0.8 +25 to +150 -0.3 to -1.0 -6 to +4
  Rationing tail    >900        +6 to +10  +2.0 to +3.5 +0.8 to +1.5 +100 to +300 -1.5 to -2.5 -8 to +2
Data-driven revisions from the plan's priors (rule: midpoint off by more than 50%):
- Selic: one-drought +25-75 becomes 0-50; severe +75-200 becomes +25-150; rationing +200-400 becomes +100-300 (W3).
- GDP: one-drought -0.1 to -0.3 becomes -0.1 to -0.5; severe -0.3 to -0.6 becomes -0.3 to -1.0; rationing becomes -1.5 to -2.5 (W4, 2001).
- Axia: the prior -10 to -20% becomes -3 to -8% (one year) and -8 to -15% (severe) (W9).
Suppression variant: headline falls to about 30-40% of the pass-through range. The cost becomes fiscal or sector debt:
- one drought year R$10-25bn
- severe R$25-60bn
- rationing R$50-100bn
These are ASSUMPTIONS anchored on unverified W29 (~R$27bn) and medium W32 (R$45.2bn). Not verified.
EU modifier: in any drought or fire year, the EUDR "high-risk reclassification / importer de-risking" tail moves from low to medium probability, worth -$2 to -5bn on the exports EU cell. No penalty was observed in 2016, 2017 or 2024.
BEST (medium probability): wet + diversified. CMO 0-150, administered prices < 3-4%/yr, headline -0.3 to 0, Selic -50 to 0, GDP 0 to +0.2, agro 0 to +$5bn (2023 analogue: EAR 77.5, CMO 0, agri VA +16.3%).
WORST (low probability): rationing tail, or severe drought + 2030 election-year suppression + fire year:
- headline +2.0 to +3.5 pp, or +0.6 to +1.4 if suppressed at a cost of R$40-100bn;
- Selic +100 to +300 bp;
- GDP -1.0 to -2.5;
- agro -$8 to +2bn, plus the EU tail of -$2 to -5bn.

Cross-tab against the exports study's ToT states (6b):
  state                              headline IPCA       Selic                exports $bn/yr
  ToT +10% / -10%                    -1.1 / +1.1 (*)     reduced-form +/-500 (*, not causal)   +/-14 to 22
  Hydro best                         -0.3 to 0           -50 to 0             0 to +5
  One drought year                   +0.3 to +1.0        0 to +50             -5 to +3
  Severe (pass-through)              +1.0 to +2.0        +25 to +150          -6 to +4
  Worst / rationing                  +2.0 to +3.5        +100 to +300         -8 to +2 (EU tail -2 to -5)
  ToT -10% + severe drought          +2.1 to +3.1        ToT response +25-150  about -20 to -28
(*) Warehouse reduced form, 2001-2025 (n 24): Dec/Dec change in ipca_12m on 100·dlog wb/TOT.BRA has slope -0.11 (r -0.25). Selic year-end change slope -50 bp per pt (r -0.42), driven by 2002 and 2015, so treat it as an upper bound.
Which dominates:
- Inflation: a severe drought is the same order as a ToT -10% state.
- Exports: the ToT state dominates by 3-5x.
- Growth: only the rationing tail rivals ToT.
Chart 8.

======================================================================================================
7. LIMITS (honest)
======================================================================================================
- Sample and power: EAR starts in 2015, with about 4 independent drought episodes (2015, 2017-18, 2019-20, 2021) all in one regime. 2022-26 has no month below 40%, so the post-diversification system is untested where it matters.
- Monthly LPs have overlapping, persistent shocks. Results are effect sizes with bands, and only W1 and W8 survive BH.
- Missing in the warehouse: CMO is SE/CO weekly only; no PLD; no IPCA electricity sub-item; administered prices mix fuels and electricity.
- The administered-price weight (~25%) and every fiscal-cost number are unverified (W28, W29, W31, W35). The fiscal ranges are assumptions.
- National SPEI and WB cereal yields (no soy) cannot test the regional agro channel. CONAB losses for 2021/22 and 2023/24 are unverified (W22, W23).
- ONS load has an MMGD break from 2023-04-29 that the warehouse does not flag.
- 2001 and 2014-15 are confounded by recessions and global shocks. 2021 is confounded by Brent, COVID and fiscal factors.
- Scenario ranges are judgement-weighted, anchored on episodes, and probabilities are qualitative.
- External facts are fenced (Appendix B). The web-search budget ran out, so 8 facts remain unverified and 5 have no URL.
Future work: ingest ONS EAR/ENA 2000-2014, ANEEL flags, IPCA sub-item 2201 via ingest/ibge_sidra.py, CONAB yields and ComexStat KG. Flag the MMGD break in electricity_load. Add PLD from CCEE and regional EAR/CMO.

======================================================================================================
APPENDIX A - warehouse series (source; first -> last observation used)
======================================================================================================
stored_energy_ear ONS daily 2015-01-01->2026-10-02 (last 60.87) | cmo_power_cost ONS weekly 2005-01-07->2026-10-02 (last 42.43)
hydro/thermal/wind_solar_generation_share ONS daily 2015-07-01->2026-10-01 (last 54.8/11.2/34.0) | electricity_load ONS daily 2015-01-01->2026-10-01
thermal_dispatch_mwh ONS 2015-01-01->2026-10-01 | generation_gwh@AXIA/@PETR, generation_share_sin@AXIA/@PETR ONS monthly 2016-01->2026-09
ipca_administered_prices, ipca_monthly, ipca_services, ipca_12m (last 4.22), inflation_diffusion BCB SGS monthly 2000-01->2026-08
focus_ipca_12m (last 4.65), focus_selic_12m (last 12.0) BCB Focus daily ->2026-09-25 | selic_target BCB SGS daily ->2026-10-03 (13.75)
real_policy_rate Derived ->2026-09 (9.27) | brent_usd IPEAData daily ->2026-09-29 (113.96) | ibc_br BCB SGS monthly 2003-01->2026-07
soy/coffee/sugar_exports, exports_to_eu ComexStat monthly 2014-01->2026-08 | gas_production_mm3d ANP 2012-01->2026-08
total_return_usd@AXIA/@PETR Derived monthly 2012-01-31->2026-10-02 | wb/NYGDPMKTPSAKD_Q.BRA WB quarterly 1990Q1->2025Q4
wb/EN.CLC.SPEI.XD.BR 1960->2023 | wb/EN.CLC.HEAT.XD.BR, wb/EN.CLC.CDDY.XD.BR 1960->2024 | wb/AG.YLD.CREL.KG.BR, wb/AG.PRD.CREL.MT.BR 1961->2024
wb/NV.AGR.TOTL.KD.ZG.BR, wb/NY.GDP.MKTP.KD.ZG.BR 1961->2025 | wb/EG.ELC.HYRO.ZS.BR, wb/EG.USE.ELEC.KH.PC.BR 1990->2024
wb/AG.LND.FRLS.HA.BR 2001->2025, wb/AG.LND.PFLS.HA.BR 2002->2025 | wb/TOT.BRA monthly ->2025-12 (World Bank via Dateno)

======================================================================================================
APPENDIX B - external facts (fenced; full rows in external_facts.csv, 50 rows)
======================================================================================================
Hydrology outlook: W01-W06, W08, W10 (ONS open data, CMSE/MME, Cenario Energia). W11 (91-year claim) is unverified.
Flags: W12-W14 (ANEEL, FGV Energia). ENSO: W15-W17 (NOAA CPC, Conab). Agro: W18-W21 (Conab); W22-W23 unverified.
Load and data centres: W09, W24-W26 (EPE PDE 2035, Cenario Energia). ONS method: W27 (dados.ons.org.br, MMGD from 2023-04-29).
Fiscal: W28, W29, W31 unverified with no URL; W30 medium. 2001: W32 (pt.wikipedia citing TCU, medium).
IPCA weights: W33-W34 (IBGE SIDRA 7060); W35 unverified. Tariff policy: W36-W38, W44. Thermal capacity: W07, W39.
Fires and EUDR: W40-W43 (INPE, EC, EUR-Lex). Reused from the exports study: C05, C07, C23-C26.
