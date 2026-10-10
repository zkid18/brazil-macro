US TARIFFS ON BRAZIL UNDER LULA III: WHAT THEY DID, AND WHAT ESCALATION WOULD DO
As of 2026-10-06. Code: us_tariffs_study.py (run: `python us_tariffs_study.py run_all`). Warehouse opened read-only.

SUMMARY
Timeline.
- 2025-08-06: IEEPA 40% + 10% on 34% of US-bound trade.
- 2025-11-13: food relief cuts the covered share to 22%.
- 2026-02-20: SCOTUS voids IEEPA; Section 122 10% for all.
- 2026-07-22/24: Section 301 25% + forced-labour 12.5% on 16%.
- Section 232 (~25%) throughout. MDIC anchors reproduce.

Damage.
- Full-rate lines lost 44% of US sales in the 40% window (35% net of pre-trend): $3.5bn/yr.
- All treated: $4.5bn/yr gross [3.2–5.8], $2.4bn net [1.4–3.5], 0.11% GDP.
- No HS4 lost > $0.47bn (sugar, beef, slabs, wood lead).
- States, gross $bn/yr: SP 1.25, SC 0.56, MG 0.51, RS 0.51, PR 0.44 (72% of the total).
- Diversion: commodities 0.55, manufactures 0.22.

Verdicts.
- H1 (small and diffuse) supported: small nationally, deep on covered lines.
- H2 (commodities divert, manufactures do not) consistent, not proof.
- H3 (the US bears the cost) consistent, not proof.
- H4 (trade-only escalation < 1% of GDP) supported.
- H5 (markets treated it as noise) supported.
- H6 partly: no employment signal; top-5 states carry 72% (< 75%).
- H7 rejected: 40% lines explain 72% of the y/y fall, crude + 232 24%.
- H8 (relief followed CPI salience) supported (p = 0.005).

Who paid. The US per unit (no Brazilian price cuts: coffee CIF vs competitors +14%, beef −3%; US duty ~$4.6bn/yr). Brazil paid in volume.

Markets: BRL, Ibovespa, NTN-B inside placebo bands; Embraer −11.7% on the letter (p 0.03), +18.7% on the aircraft exemption (p 0.002).

Escalation (net loss vs (a)):
| Rung | Loss $bn | % GDP | BRL / Ibov / NTN-B / Embraer | US duty $bn | P Lula / Flávio |
|---|---|---|---|---|---|
| (a) | 0 | 0 | flat | 4.6 | 40 / 35 |
| (b) | 0.6 (0.2–1.7) | 0.03 | −0.5–2% / −1–4% / +0–15bp / 0–3% | 5.3 | 20 / 5 |
| (c) | 3.7 (0.6–12) | 0.17 | −1–4% / −3–8% / +10–40bp / −10–25% | 9.9; coffee import price +7.6% | 15 / 3 |
| (d) | 13.7 (5–26) | 0.6 trade, 2.6 with finance | −10–38% / −20–55% / +100–190bp / −30–50% | 17.3 | 5 / 1 |
| (e) | +1.2 gain | −0.06 | +1–3% / +2–6% / −5–20bp / +5–19% | 3.5 | 20 / 56 |

Probabilities, finance block: judgement.

Triggers.
- Graham Act list, 2026-10-18 (Brazil is not a top-5 crude/gas buyer).
- Aircraft-232 clock, ~2027-01-05.
- Amnesty: Flávio pledges it in the transition; the dosimetria law was suspended by the STF.

Limits: HS6 mapping rule; two inferred annexes; no Census duties; R5 = 2 months; 0 web searches available.

Charts: review/charts/07_us_tariffs__01_coverage_by_regime … __10_us_cpi_and_relief.html.

====================================================================================================
1. DATA AND SOURCES
====================================================================================================
Vintages:
- ComexStat live API to 2026-09.
- Warehouse ComexStat to 2026-08.
- UN Comtrade (US imports, CIF) to 2026-07.
- BLS CPI/PPI to 2026-08.
- SIDRA PIM-PF to 2026-07 and PNAD to 2026-Q2.
- COTAHIST to 2026-10-06.
- Warehouse markets to 2026-10-02.
- HTS Chapter 99: the current USITC release.

What worked, with exact calls (all logged in api_calls.csv, 420 rows):
- ComexStat POST /general, 11 s spacing:
  - us_ncm_m: 121,957 rows, 6,282 NCMs.
  - us_heading_m, us_state_m, us_state_heading_y, us_state_heading_m_top.
  - world_heading_m (added so ROW = world − US for every HS4).
  - div_heading_country_m_0..4 (50 HS4 × all destinations).
  - div_ncm_country_m (32 firm NCMs).
  - imp_us_heading_y/m.
  - world_state_m.
  - world_ncm_m: a single call timed out on the server; it worked as four yearly calls (world_ncm_m_2023..2026).
  - Tables: countries, uf, ncm, economic-blocks.
- Comtrade public preview (no key), 316 calls:
  - Bilateral US←Brazil, 50 HS4, 2023-01..2026-07.
  - All-partner mirror, 12 HS4, 2023-01..2026-07.
  - The API returned HTTP 403 after call 199 and resumed later the same evening. 429s were handled with back-off.
- Federal Register API: document lists and raw text for 25 documents. govinfo PDFs for EO 14323 (702 HTS tokens), EO 14361 and EO 14326 (image annexes).
- USITC HTS Chapter 99 PDF → pdftotext (52,665 lines), plus the full HTS JSON (11,414 HTS-8 lines).
- BLS API v1: two queries, 12 series. WPU024203 (frozen juices PPI) ends in 2020. October 2025 is missing (BLS "-").
- SIDRA: 4099 (unemployment by UF) and 8888. PIM-PF needed the classification c544/129314; the default call returned only "..".
- B3 COTAHIST: A2021–A2026 + D06102026. Splices:
  - Embraer EMBR3 → EMBJ3 on 2025-11-03 (price ratio 1.003).
  - JBS JBSS3 → BDR JBSS32 on 2025-06-09 (ratio 2.0; spliced on returns).
- Direct primary pages: USTR Brazil, Census c3510, USGS niobium, TIC Table 5, Planalto Lei 15.122, AEA abstract.

Needs a key or unavailable (gaps):
- US Census API (realised duties, CAL_DUT_MO).
- USITC DataWeb.
- BEA FDI stock (no key, and no search budget).
- BLS wp.item (bot-blocked). PPI WPU0121's name is unverified.
- IPEAData/CAGED by UF.
- Web search: the session's 200-search budget was already exhausted before this study, so 0 searches were made. Every new external fact comes from a primary document fetched directly. The Venezuela 2019, Russia 2022 and India-INR analogues are NOT verified.

Warehouse SQL (read-only):
  SELECT year, value FROM v_annual WHERE series_id='exports_to_us' AND year BETWEEN 2023 AND 2026;
  SELECT date, value FROM v_observations WHERE series_id='exports_to_us' AND date BETWEEN '2025-06-01' AND '2026-08-01';
  SELECT value FROM v_annual WHERE series_id='wb/NY.GDP.MKTP.CD.BR' AND year=2025;                 -- 2,279.9bn
  SELECT series_id, date, value FROM v_observations WHERE date >= '2015-01-01' AND series_id IN
    ('brl_usd','ibovespa_usd','gov_real_yield_10y','gov_nominal_yield_5y','brent_usd');               -- event study
  (All SQL is stored in results.json["_sqllog"].)

Anchors (stop rule), all reproduced (results.json anchors.mismatches = []):
- exports_to_us: 2023 36.915, 2024 40.369, 2025 37.682, 2026 Jan–Aug 24.105.
- Monthly values Jun-25..Aug-26 are exact.
- The live ComexStat sums match the warehouse to the dollar. 2026 Jan–Sep is 27.462.
- The top-45 NCMs carry 70.2% of 2024.

====================================================================================================
2. TIMELINE (tariff_timeline.csv; 18 measures; FR document numbers in the file)
====================================================================================================
Share of 2024 US-bound exports by status (HS6 "any" rule), and trade-weighted added rate:

| Regime | Dates | Measures | 232 | Exempt | Full | Other | Added rate |
|---|---|---|---|---|---|---|---|
| R1 | 2025-03-12..08-05 | 232 steel/aluminium (50% from 06-04), autos 25%, copper 50%, reciprocal 10% | 23.2 | 27.1 | 49.7 (10%) | – | 13.8% |
| R2 | 2025-08-06..11-12 | EO 14323: 40% + 10% | 23.2 | 42.5 | 34.3 (anchor 35.9 ± 4) | – | 27.5% |
| R3 | 2025-11-13..2026-02-23 | EO 14361 relief + EO 14360 all-country agriculture | 24.7 | 53.4 | 22.0 (anchor 22 ± 4) | – | 21.6% |
| R4 | 2026-02-24..07-21 | Section 122 10% | 25.1 | 47.8 (anchor 46 ± 5) | 27.1 (10%) | – | 12.0% |
| R5 | 2026-07-22.. | Section 301 25% + forced-labour 12.5% | 25.1 (24.2 ± 5) | 52.2 (52.7 ± 5) | 16.0 at 37.5% (16.5 ± 3) | 4.7 at 12.5% only; 2.0 at 25% only | 16.3% |

Aircraft-232 (Proclamation 11040, 2026-07-09, D10): no tariff. If no agreement is reached within 180 days (~2027-01-05), other actions may follow.

The national emergency was continued on 2026-07-28 (D11), so the IEEPA sanctions route is live. Brazil is NOT a respondent in the excess-capacity 301 (D12).

The beef TRQ expansion of +80,000 t went entirely to Argentina (D07). The June-2026 232 changes give Brazil no quota (D01).

Mapping note:
- The plan's count/partial HS6 rule reproduces every anchor except R5 full: 20.4% vs 16.5 ± 3. That figure is close to GTA's independent 21.5% (A24).
- The MISS was inspected. It sits in partially listed HS6s (sugar, wood, engine parts).
- The "any listed HTS-8 ⇒ whole HS6" rule (MDIC maps NCM-8 → HTS-8) passes all seven anchors and is the primary. The count rule is a robustness cell.
- The EO 14360 and EO 14361 annexes are images and were inferred. Relief = the HTS 2(x)(iii)(a) list as amended, minus the EO 14323 Annex I PDF, plus (b). EO 14360 = the chapter 01–24 codes now in Annex II.

====================================================================================================
3. EXPOSURE MAP (product_exposure.csv; 50 HS4 = 80.4% of 2024 US-bound exports)
====================================================================================================
US$bn 2024 / 2025 / 2026 Jan–Sep; group; R5 added rate; Brazil share of US imports in 2024 (Comtrade CIF); top states.

| HS4 | Product | 2024 / 2025 / 2026 YTD | Group | R5 rate | Brazil share of US imports | Top competitors | Top states |
|---|---|---|---|---|---|---|---|
| 2709 | crude | 5.83 / 4.70 / 2.49 | exempt | 0 | 3.8% | Canada 59% | RJ 70% |
| 7207 | slabs | 2.80 / 2.60 / 2.00 | 232 | 50 | 76.0% (low substitutability) | Mexico 13, Canada 9 | RJ 57, ES 31 |
| 8802 | aircraft | 2.38 / 2.73 / 2.00 | exempt | 0 | 10.1% | Canada 36, Germany 25, France 22 | SP 94 (Embraer) |
| 0901 | coffee | 1.90 / 1.92 / 1.22 | relief | 0 | 22.4% | Colombia 17, Switzerland 13 | MG 80 |
| 2710 | fuels | 1.74 / 1.63 / 1.48 | exempt | – | – | – | – |
| 4703 | pulp | 1.55 / 1.23 / 1.02 | exempt | 0 | 42.5% | Canada 42 | ES 36, MA 25, MS 14 |
| 7201 | pig iron | 1.42 / 1.39 / 0.89 | exempt | 0 | 73.3% | Ukraine 18 | MG 68 |
| 8429 | earthmovers | 1.42 / 1.33 / 1.10 | 232 | 25 | – | – | SP 86 |
| 2009 | juices | 1.19 / 1.61 / 0.67 | exempt | – | 30.2% | Mexico 15 | SP 88 |
| 0202 | frozen beef | 0.89 / 1.09 / 1.54 | relief | 0 | 18.7% | Australia 34, New Zealand 21 | MS, GO, MT |
| 7224 | alloy semis | 0.74 | 232 | 50 | – | – | – |
| 6802 | stone | 0.70 | mostly exempt | 22.7 | 23.7% | – | ES 96 |
| 1701 | sugar | 0.60 / 0.23 / 0.08 | covered | 25 | 29.0% | – | SP 42 |
| 8504 | transformers | 0.56 | 232 | – | – | – | SP, MG, PR |
| 4409 / 4418 | wood | 0.48 / 0.40 | covered | 33–37.5 | – | – | PR, SC |
| 8409 | engine parts (Tupy) | 0.46 | 232 | – | – | – | SP 45, SC 39 |

Ferroniobium (7202.93): Brazil supplies 66% of US ferroniobium and niobium-metal imports, and US net import reliance is 100% (USGS, E03).

====================================================================================================
4. MEASURED EFFECTS AND VERDICTS (did_results.csv: 4,365 rows)
====================================================================================================
4.1 Triple difference: HS4 × month, Jan 2023–Sep 2026, log(US + k) − log(ROW + k), k = 1% of the 2024 mean month.
- Panel: 315 HS4 with ≥ $5m in 2024 (covered 177, 232 79, relief 21, exempt 37). Reference = exempt, excluding crude.
- Inference: cluster bootstrap by HS4 (2,000 draws); placebo = 2,000 permutations of group labels.

| Group | Jul-25 (letter) | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| Covered (full rate R2–R5) | −11% | −36.5% [80% CI −47.8, −22.9], placebo p 0.013 | −52.2% [−60.8, −41.4], p < 0.001 | −38.6% [−50.7, −24.2], p 0.011 | −46.4% [−57.6, −32.4], p 0.009 |
| Relief (coffee, beef...) | – | −9.9% [−35, +26], p 0.69 | −1.7% | +13% | +68% (beef boom; p 0.15) |
| 232 | – | −13.5% (p 0.46) | −10% | +1% | +19% (all n.s.) |

- Robustness grid: 144–288 cells (unit HS4/NCM-8 × triple/level/share × crude in/out × 232 in/out × pre-period 2023/2024 × drop coffee/beef × weighting × seasonal differencing).
  - Covered keeps its sign in 100% (R2, R3) and 94% (R4, R5) of cells. Median −37 / −53 / −34 / −43%.
  - Relief R2: 89% same sign (median −17%). 232 R2: 58%.
- Elasticity on ln(1+τ): commodity −1.42 [−1.85, −0.97], manufactured −0.76 [−1.18, −0.31], pooled −0.90.
- Covered-group ROW effect ≈ 0 (−2% to +3%). Covered lines did not divert in aggregate.

4.2 Losses (additive US$ gaps vs the same 2024 months, scaled by control growth; DD; the TD variant uses the product's own ROW).
- Covered, 40% window (Aug-25..Feb-26): −44.4% of the 2024 run-rate, $3.46bn/yr gross.
  - Pre-period placebo (Jan–Jun 2025 vs 2024): −14.7%. This reflects the R1 10% and the front-loading. Net of it: −34.8%.
  - R4: −33.2%. R5 (2 months): −44.8%.
- Relief, R2 window: $0.64bn/yr (−15%). 232: +$0.39bn/yr gross, ≈ 0.
- Crude (exempt, non-tariff): −35%, $2.06bn/yr.
- All treated: gross $4.50bn/yr [80% CI 3.22, 5.79]; net $2.42bn/yr [1.41, 3.54] = 0.11% of GDP.
- The TD variant is larger (covered $6.1bn) because ROW also boomed.
- Top gross losses ($bn/yr; d = diversion share):

| HS4 | Product | Group | Gross | d |
|---|---|---|---|---|
| 1701 | sugar | covered | 0.47 | 0 |
| 0202 | beef | relief | 0.46 | 1 |
| 7207 | slabs | 232 | 0.36 | 1 |
| 4418 | doors | covered | 0.22 | 0 |
| 4409 | mouldings | covered | 0.21 | 0 |
| 3301 | orange oil | relief | 0.19 | – |
| 8409 | engine parts | 232 | 0.17 | – |
| 7304 | tubes | 232 | 0.16 | – |
| 4412 | plywood | covered | 0.16 | – |
| 8112 | – | covered | 0.12 | – |

  The top 10 carry 42% of the gross loss; the largest single HS4 is $0.47bn.

4.3 Diversion (H2): d = clip(ΔROW / |ΔUS|), ROW in tonnes where reported, weighted by |ΔUS|.
- Commodity: 0.55 [0.32, 0.75] (n = 84). On the plan's named list: 0.68 [0.37, 0.98] (n = 6).
- Manufactured: 0.22 [0.17, 0.28]. On the plan's list: 0.12 [0, 0.28].
- Difference: 0.33 [0.09, 0.53].
- By group: covered 0.21, relief 0.63, 232 0.53.

4.4 Unit values (ComexStat US/ROW FOB unit-value ratio, change vs Jan-24..Jul-25):

| NCM | Product | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| 09011110 | green coffee | −0.7% | +0.6% | +2.4% | +6.2% |
| 02023000 | frozen beef | −10.2% | +1.6% | – | – |
| 72011000 | pig iron | +7.0% | – | – | – |
| 72071200 | slabs | −6.1% | – | – | – |
| 47032900 | eucalyptus pulp | −7.6% | −19% | – | – |
| 20091200 | OJ NFC | −10% | – | – | – |
| 17011400 | raw cane sugar | +2.9% | – | – | – |

- Covered-vs-exempt DiD on the log ratio, R2: +1.8% [−16, +26]. No evidence that Brazil cut prices on taxed lines.

4.5 US mirror (Comtrade, us_mirror.csv; base Jan-24..Mar-25; competitor rates from HTS 9903.02.xx, EO 14326 default 10%, forced-labour tiers).
- Coffee, R2: Brazil's share of US imports −8.0 pp at a relative wedge of +34.8 pp.
  - CIF unit value vs competitors +14%; duty-inclusive +40%.
  - Still −8.9 pp in R4 with a wedge of 0 (customer loss persisted).
- Beef: −11.0 pp in R2 (CIF −3%, duty-inclusive +28%). Fully recovered in R3/R4 (+2 pp). Beef was the 2026 boom line ($1.54bn Jan–Sep 2026 vs $0.89bn in all of 2024).
- Sugar: −15.9 pp. Pig iron and slabs fell in R4 (−21.5 and −31.4 pp) at a zero tariff wedge. That is non-tariff, or the 232 deal rates for the UK/EU/Japan/Korea, which are ignored here.
- Pooled slope: −0.20 pp of US import share per pp of relative wedge (n = 33 HS4 × regime cells, within-regime permutation p = 0.011).

4.6 Verdicts (pre-registered rules)
- H1 (small and diffuse): SUPPORTS H1. Net $2.4bn [1.4, 3.5] ≤ $4.6bn; maximum single HS4 $0.47bn < $1bn.
  - H1': the first leg holds (covered lines −44%, or −35% net of pre-trend, ≥ 25%). The concentration legs fail (top-10 HS4 42% < 70%; top-5 states 72% < 75%).
  - Read: nationally small, locally deep (wood, sugar, footwear, arms, tallow).
- H2 (commodities divert, manufactures do not): CONSISTENT WITH H2, NOT PROOF. Manufactured ≤ 0.3 (CI excludes 0.3). The commodity point estimate is 0.55 on the class rule (0.68 on the plan list) with a CI that includes 0.6. H2' (no difference) is rejected: the difference CI excludes 0.
- H3 (US bears the cost on low-substitutability lines): CONSISTENT WITH H3, NOT PROOF.
  - The >30%-share lines (pig iron 73%, slabs 76%, pulp 42%, OJ 30%) were all exempt or under the uniform 232 from the start. The US never taxed them Brazil-specifically.
  - On taxed lines Brazil did not cut CIF prices (coffee +14%, sugar +32%, beef −3% vs competitors), so US buyers paid the duty and substituted.
  - Test (i) is mixed (pulp −8%, OJ −10%), but those lines were untaxed.
  - H3' (absorption ≥ 5%) holds only for beef against ROW (−10%).
- H4 (trade-only escalation < 1% GDP): SUPPORTED (modelling).
  - Rung (c) central net $3.7bn (high case $12.0bn) < $22.8bn.
  - Rung (d) trade-only $13.7bn (high $26.2bn exceeds 1% of GDP only under the −2.5 elasticity set). With the financial block it reaches 2.6% of GDP.
  - H4' is rejected.
- H5 (markets treated the tariff as noise): SUPPORTED. Every escalation-group mean CAR [−5,+5] is inside the placebo 5–95% band:
  - BRL −0.15% (band −1.9, +2.1)
  - Ibovespa USD −1.5% (−4.5, +4.5)
  - NTN-B +1.6 bp (−14, +16)
  - Embraer +0.8% (−5.8, +6.1)
  - Exposed basket +0.2% (−3.6, +3.8)
  The exact E-vs-D permutation p is 0.33–0.98. Embraer's single events are the exception (§6).
- H6 (state concentration, no employment signal): PARTLY.
  - Employment leg supported. PNAD unemployment in exposed minus unexposed UFs rose 0.52 pp (0.53 cross-state sd < 1; slope p 0.09). PIM-PF gap 0.06 sd (n = 17).
  - Concentration leg narrowly fails (72% vs 75%).
  - H6' not supported. Exploratory, n = 27.
- H7 (the fall was mostly not the 40%): REJECTED; H7' SUPPORTED.
  - y/y change Aug-25..Jul-26 = −$6.81bn.
  - Lines at the full rate in R2: −$4.88bn (persistent −3.46, later relieved −1.42) = 72%.
  - Crude −1.48 and 232 −0.18 = 24%; other exempt −0.28.
  - The exports study's "crude and steel drove 2025" (A15) is a calendar-year artefact.
- H8 (relief predicted by US CPI salience): SUPPORTS H8 in the cross-section.
  - Among 44 food/ag HS4 covered in R2 (≥ $10m), all 5 CPI-salient lines were relieved, against 12 of 39 others (difference 0.69, permutation p = 0.005). By value: $3.42bn of the $3.76bn relieved was salient.
  - Coffee CPI was +18.9% y/y and beef +14.7% in Sep 2025 (E04).
  - The all-country EO 14360 (2025-11-14) cites "current domestic demand" (D04). EO 14361 cites "initial progress in negotiations" (D05).
  - H8' cannot be excluded on timing: the meetings and the CPI prints both precede the relief.

====================================================================================================
5. STATES AND EMPLOYMENT (exploratory)
====================================================================================================
- Gross / net loss, US$bn/yr:

| UF | Gross | Net |
|---|---|---|
| SP | 1.25 | 0.69 |
| SC | 0.56 | 0.43 |
| MG | 0.51 | 0.39 |
| RS | 0.51 | 0.25 |
| PR | 0.44 | 0.36 |
| RJ | 0.20 | −0.03 |
| GO | 0.17 | – |
| MS | 0.17 | – |
| PE | 0.13 | – |
| ES | 0.13 | – |

- Exposure (covered US-bound exports as % of the UF's total exports, 2024): PB 17%, CE 12%, SC 9.4%, AL 8.7%, PE 7.3%, SP 6.6%.
- UF DiD of US-bound exports per 10 pp of exposure: 40% window +4% [−33, +32]; R4/R5 −49% [−72, −28].
- PNAD and PIM-PF: see H6. CAGED by UF unavailable. ComexStat "state" = state of production.

====================================================================================================
6. MARKETS (event_study.csv; engine congress_core.car/perm_test)
====================================================================================================
Setup:
- Estimation window [−250, −121]; Brent market model for BRL and Ibovespa.
- Placebo: 2,000 dates ≥ 90 days from any event; COVID-excluded variant stored.
- Events: 7 E, 7 D, 3 C. The 2026-10-01 event lacks a full window.

Embraer [−1,+1]:
- 2025-07-10 letter: −11.7% (placebo p 0.026).
- 2025-07-30 EO with the civil-aircraft exemption: +18.7% (p 0.002). Relative to Ibovespa: −7.7 / +18.1.
- 2025-11-20 relief: −3.7%. 2026-05-07 White House: −6.7% (p 0.16). Every 301 date ≤ |2.2|%.

Macro series: no event has placebo p < 0.10 except the controls (Liberation Day BRL −5.4% [−5,+5], Reciprocity Law BRL +3.9%).

Read: markets priced aircraft exposure, the one line where the US nearly taxed Brazil's highest-value manufacture, and nothing else.

====================================================================================================
7. ESCALATION MATRIX (escalation_matrix.csv)
====================================================================================================
Mechanics:
- X_i,2024 by HS6 × R5 status fractions.
- X_r = X(1+τ_r)^ε. ε sets: low −0.5; central commodity −1.4 / manufactured −1.0 (this study); high −2.5 (US–China HS10 literature, F02 unverified).
- Net = gross × (1 − d), with d from §4.3. In rung (d), d is halved.
- GDP = ΔX/GDP × (1−m) × k, with m 0.10–0.20 and k 1.0–1.5.
- Markets: event-study scaling. Rung (d) uses the worst 63-day move since 2015 in the warehouse: BRL −37.5% (2020-05-14), Ibovespa USD −54.8%, NTN-B +190 bp.

| Rung | Gross central (low–high) | Net central (low–high) | % exports | % GDP | US duty $bn | US-side notes |
|---|---|---|---|---|---|---|
| (a) | 0 | 0 | 0 | 0 | 4.55 | GTA's unadjusted estimate is ~$7.0bn (A24) |
| (b) | 0.89 (0.27–2.25) | 0.58 (0.15–1.74) | 0.17 | 0.03 | 5.29 | – |
| (c) | 7.41 (1.52–16.68) | 3.70 (0.62–11.95) | 1.1 | 0.17 | 9.86 | see below |
| (d) | 17.66 (7.02–30.20) | 13.70 (5.17–26.16) | – | 0.64; +1–4 judgement financial; 2.64 total central | 17.31 | – |
| (e) | – | −1.22 gain (−0.62 to −2.04) | – | – | 3.49 | – |

Rung (c), US side:
- Import prices (Brazil share × τ × pass-through 0.9, ARD complete pass-through F01): coffee +7.6% (retail ≈ +3% with a 40% bean-cost share, a plan assumption), beef +6.3%, OJ +10.2%, pig iron +24.7%, pulp +14.3%, ferroalloys +5% (ferroniobium 66% Brazil), aircraft +3.4%.
- Slabs are already at 50% under 232, so there is no increment.
- Input shortages: EAF pig iron, slabs, ferroniobium (the US has no domestic source; Canada is the alternative), the E175 regional-jet supply. The E175 scope-clause dependence is not quantified (no search).

US exposure to retaliation:
- US goods exports to Brazil 2025: $45.1bn (ComexStat) / $54.3bn (Census, E02). Services exports $34.4bn; services surplus $27.4bn (E01).
- Of the goods, $13.9bn are inputs with no near substitute: jet engines 8411 $7.4bn, LNG, coal, medicines, agrochemicals, fertilisers.
- The Reciprocity Law allows duties on goods and services and IP suspension (D13).
- Cost to Brazil of retaliating on the $31bn of substitutable goods: ~$3.9–7.8bn (judgement).
- Brazil's US Treasury holdings: $168.0bn (Jul-2026), down from $201.8bn a year earlier (E05).
- US FDI stock in Brazil: gap.

Probabilities: judgements, the modal state through 2027 conditional on the run-off winner. Rationales in the CSV.
- Lula IV: a 40 / b 20 / c 15 / d 5 / e 20.
- Flávio: a 35 / b 5 / c 3 / d 1 / e 56.

Triggers:
- amnesty / dosimetria. Flávio pledges amnesty in the transition (A32); the override was suspended by Moraes (G09, G10). This is the main link.
- STF actions against the Bolsonaros (A36).
- Pix/digital and ethanol, the core of the 301 (A19).
- BRICS (A40) and China alignment.
- Russian oil: the Graham Act list on 2026-10-18. Brazil is not a top-5 crude/gas buyer (A45). Diesel exposure is A46/A47.
- The aircraft-232 clock (~2027-01-05, D10).
- Election-interference claims and the consular suspension (A38).
- The national-emergency anniversary, 2027-07 (D11).

====================================================================================================
8. ANALOGUES
====================================================================================================
Used and verified:
- R2 itself (−44% on covered lines at 50%).
- Amiti–Redding–Weinstein 2019 (complete pass-through, F01).
- India Aug-2025 50%, revoked Feb-2026 (A43).
- Section 122 (all countries).

Cited but NOT verified this session (no search budget):
- Fajgelbaum et al. 2020 (F02).
- Venezuela 2019 PDVSA SDN.
- Russia 2022.
- INR / COP / CNY moves.

The rung (d) financial block (1–4% of GDP) is therefore a labelled judgement.

====================================================================================================
9. WHAT CANNOT BE CONCLUDED
====================================================================================================
- R5 has two months of ComexStat data and none in Comtrade (July 2026 classed as R4). Its −45% may still include lagged R2–R4 customer loss.
- The covered lines show a −15% pre-period gap. The 40% effect is −35% to −44%, and hysteresis (R4 still −33% at a 10% wedge) cannot be separated from tariff anticipation.
- The HS6 mapping changes the R5 full share (16.0 vs 20.4%). Section 232 uses the current lists for all regimes. The EO 14360/14361 annexes are inferred.
- No realised effective tariffs (Census duties need a key). The US duty bill is modelled.
- The mirror ignores the 232 deal rates for UK/EU/Japan/Korea, which explains part of the slab and pig-iron share loss.
- State results: n = 27, production-state attribution, no CAGED.
- Markets: 7 vs 7 events, overlapping windows (07-30 and 08-06), and a crowded 2025–26 calendar thinning the placebo pool for firms (COTAHIST from 2021).
- Probabilities and the financial block are judgements. FDI stock and the E175 scope-clause facts are gaps.

====================================================================================================
APPENDIX A: SERIES (series_id, source, last date)
====================================================================================================
Warehouse:
- exports_to_us (ComexStat, 2026-08-01)
- wb/NY.GDP.MKTP.CD.BR (World Bank, 2025-12-31; 2,279.9bn)
- exports_total (ComexStat, 2026-08-01)
- brl_usd (BCB, 2026-10-02)
- ibovespa_usd (2026-10-01)
- gov_real_yield_10y (2026-10-02)
- gov_nominal_yield_5y (2026-10-02)
- brent_usd (2026-09-29)

Live:
- ComexStat (cache/comexstat/*, to 2026-09)
- Comtrade 842 (to 2026-07)
- BLS CUUR0000SEFP01/SEFC/SEFC01/SEFN02/SEFN03/SAF11/SA0 and WPU026301/101702/101712/0121 (to 2026-08)
- SIDRA 4099 (2026-Q2), 8888 c544/129314 (2026-07)
- COTAHIST (2026-10-06)

Every number in results.json carries {value, series_id, source, last_date, sql} or its cache file / call.

====================================================================================================
APPENDIX B: EXTERNAL FACTS (external_facts.csv, 62 rows; fenced; accessed 2026-10-06)
====================================================================================================
- A01–A28, A32, A38, A40, A43–A47, A49, A50: reused from exports. G08–G10: reused from congress.
- New, all from primary documents fetched directly:
  - D01–D13: Federal Register, HTS, Planalto.
  - E01–E06: USTR, Census, USGS, BLS, TIC, Comtrade.
  - F01–F02: literature. F02 is unverified, medium confidence.

====================================================================================================
APPENDIX C: API CALL LOG
====================================================================================================
api_calls.csv: 420 rows (ComexStat ~25, Comtrade 316, COTAHIST 7, ...). FR/HTS/BLS/SIDRA/web fetches are cached under cache/ (git-ignored).

Helper scripts fr_pull.py and fr_text.py were used for the FR pulls.
