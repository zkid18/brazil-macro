# Brazil's exports under Lula IV vs Flávio Bolsonaro: exposure, the 2025 tariff experiment, channels and scenarios

As of 2026-10-05. Warehouse: `brazil_macro.duckdb` (read-only). ComexStat data run to **2026-08-01**. Code: `exports_policy_study.py`. Outputs: `results.json`, `exposure_map.csv`, `tariff_episode.csv`, `scenario_matrix.csv`, `cross_table.csv`, `scenario_revisions.csv`, `channels.csv`, `external_facts.csv`, `charts/*.html`.

Run-off context (external, A49/A50): the TSE first-round count was **Flávio 47.03%, Lula 45.16%**. The brief's 44.9% for Lula is wrong. The run-off is on 2026-10-25, and the last polls are within the margin of error, so both branches are treated as ~50/50.

## Summary

1. **The 2025 US tariff cost about $7.9bn a year.** US-bound exports were 19.3 points below their own pre-trend over the 13 months Aug 2025–Aug 2026 (`exports_to_us`, ComexStat, last 2026-08-01). That is a gap of **−$8.5bn over 13 months, ≈ −$7.9bn/yr, 2.3% of 2025 exports and 0.35% of GDP**. The seasonal-factor counterfactual gives −$9.4bn (−19.9%). The pre-registered placebo test is **not significant**: rank p = 0.23, because COVID-era placebo windows dominate the distribution. Excluding the COVID windows gives p = 0.018, and the 4-month window gives p = 0.029. Those two tests are post-hoc. Read the effect as a real but noisily identified fall.
2. **Diversion dominated: total exports did not fall.** Total exports were 9.4 points above pre-trend, and up 7.7% on two years earlier. That growth is confounded by the 2026 Brent shock: oil explains 30% of 2026 year-to-date export growth. The diversion rate is bounded between 0 and 1. Its central value is 0.44, the fungible-commodity share of the US product mix (A14). That gives a **net national loss of −$4.4bn/yr (range −$7.9bn to ≈ $0)**. Realised oil prices relative to Brent show no discount after the tariff (0.87 vs 0.85–0.90 before).
3. **China's "+19%" is mostly a base effect.** Against two years earlier, exports to China are up only **+4.1%**. Exports to China collapsed in H2 2024 ($10.2bn in Jul 2024 → $5.2bn in Dec 2024). The L4 "pivot to China" headline overstates the policy content.
4. **The destination mix did not move with the president's lean.** China / US / EU / rest shares were 29.5 / 11.5 / 13.9 / 45.1 under Bolsonaro and 29.4 / 10.9 / 14.2 / 45.4 under Lula III.
5. **Several web findings change the plan's baseline.**
   - The IEEPA 50% tariff was voided on 20 Feb 2026. Since 22–24 Jul 2026 the US layer is **Section 301 25% + forced-labour 12.5%**, and it hits only 16.5% (US$6.6bn) of US-bound exports.
   - China's **beef safeguard quota is now binding**: 55% over quota, 67% in total, from 1 Oct 2026.
   - The **EU suspended Brazilian beef, poultry, eggs and honey** from 3 Sep 2026.
   - The **EU–Mercosur interim agreement has been provisionally applied since 1 May 2026**.

   All four apply to both candidates. Nine scenario cells were revised (`scenario_revisions.csv`).
6. **The candidate is second-order.**
   - With the case held fixed, Flávio and Lula differ by only **≈ $2–3bn/yr** at the central values. Best cases: Lula +$7 to +20bn, Flávio +$5 to +18bn. Worst cases: Lula −$21 to −6bn, Flávio −$27 to −6bn.
   - Which case materialises moves exports by about $25–30bn/yr.
   - A ±10% terms-of-trade state moves them by **$29–43bn/yr**, the high state minus the low state. That is ±2.3–3.1 points of GDP-per-capita growth through β, an upper bound.
   - The commodity and geopolitical state dominates the candidate.

## Data constraints (plan §0, reproduced)

- **0.1** ComexStat monthly, `usd_fob`, 2014-01→2026-08. The only product×destination series is `beef_exports_to_china` (pre-access months 2014-03…2015-05 set to 0). There is no soy→China, coffee→US, oil→US, Argentina, Mercosur, India or Middle East series. There is no soy, beef or coffee tonnage, and no NCM split of exempt vs non-exempt goods.
- **0.2** `bop_goods_exports` (BCB) reconciles with ComexStat: 2025 is $350.5bn vs $348.3bn, and 2026 YTD is $251.8bn vs $250.9bn. Reproduced exactly. `wb/TOT.BRA` ends 2025-12. `wb/REER_M.BRA` ends 2024-10. WB regional shares end 2023.
- **0.3** Every tariff-episode anchor reproduced within tolerance (`anchor_mismatches = []` in results.json). The figures are listed in §2 below.
- **0.5** Confounders. `brent_usd` monthly means: 62.5 (Dec 2025) → 117.3 (Apr 2026) → 114.1 (Sep 2026); the external cause is the Iran war and the Hormuz closure (C59). Oil unit value: $454/t (2025) → $549/t (2026 YTD). `brl_usd`: 6.10 (Dec 2024) → 4.98 (May 2026) → 5.22 (Oct 2026).
- **0.9** Conventions. OLS by `np.linalg.lstsq`. Moving-block bootstrap, 2,000 draws, seed 0, block 3 annual / 12 monthly. Permutation and placebo p-values. Never use 2026 from `v_annual` as a year (`is_complete = FALSE`). Filter `date <= current_date`. Plotly HTML only.

## 1. Export exposure map (`exposure_map.csv`, 2025 complete year)

| Bucket | $bn 2025 | % exports | % GDP | CAGR 2019–25 | 2026 YTD YoY | series_id |
|---|---|---|---|---|---|---|
| US | 37.7 | 10.8 | 1.65 | 4.0 | −9.7 | `exports_to_us` |
| China | 99.9 | 28.7 | 4.38 | 7.9 | +15.0 | `exports_to_china` |
| EU-27 | 49.8 | 14.3 | 2.18 | 8.8 | +15.0 | `exports_to_eu` |
| Mercosur/LatAm (proxy) | 43.5 | 12.5 | 1.91 | – | – | `wb/TX.VAL.MRCH.R3.ZS.BR` (2023 share; upper bound, includes Mexico, Colombia, Peru) |
| Rest (India/MENA/ASEAN/Africa/Japan) | 117.4 | 33.7 | 5.15 | – | +11.0 (rest incl. LatAm) | residual |

Products, 2025 share of exports: oil 12.8, soy 12.5, iron ore 7.5, beef 4.8, coffee 4.3, sugar 4.1, pulp 2.9, niobium 0.8. The tracked groups total 49.6%, and the residual (manufactures and other) is 50.4%. WB classes for 2025: food 40.7, fuel 16.1, ores 12.2, manufactures 23.8. That gives a commodity-priced share of **69.0%**. Four-bucket HHI for 2025 is 3,279; it is a lower bound because "rest" covers many countries. The China share was 18.4% (2014) → 32.4% (2020) → 28.7% (2025).

Price vs volume (Δlog ×100):
- Oil 2019→2025: value +61, tonnes +49, price +12. In 2026 YTD: value +21, tonnes +6, price +16, so the 2026 gain is mostly price.
- Iron ore, 2026 YTD: −1.4.
- Pulp, 2026 YTD: tonnes −7, price +10.
- WB aggregate 2015→2024: volume 100→139.5, unit value 100→129.4.

Charts: `charts/1_destination_shares.html`, `charts/2_product_shares.html`.

## 2. The 2025 tariff as a natural experiment (`tariff_episode.csv`)

**Pre-registered thresholds, written before the results:**
- The effect is "material" if the 13-month DiD is below −10 points with placebo p < 0.10.
- Diversion is "dominant" if the total-exports DiD is ≥ 0 and the two-year total change is ≥ +5%.
- The China base effect is "dominant" if the two-year China change is less than half the one-year change.

```sql
-- monthly panel (pivoted in pandas); all estimators run on it
SELECT series_id, date_trunc('month', date) AS ym,
       CASE WHEN series_id IN ('brl_usd','brent_usd','focus_fx') THEN avg(value) ELSE max(value) END AS v
FROM v_observations WHERE date <= current_date AND series_id IN ('exports_total','exports_to_us','exports_to_china','exports_to_eu', ...)
GROUP BY 1,2 ORDER BY 2,1;
```

| Estimator | US | China | EU | Rest | Total |
|---|---|---|---|---|---|
| Same-month YoY, Aug–Nov 2025 (4 m) | −25.1% (DiD −29.9) | +28.0 (DiD +34.6) | −3.9 (−7.7) | +3.3 (+1.0) | +4.7 (+4.7) |
| Same-month YoY, Aug–Dec 2025 (5 m) DiD | −26.4 | +36.1 | −1.6 | +4.9 | +8.0 |
| 13 m (Aug 2025–Aug 2026) YoY / DiD vs Jan–Jul 2025 pre-trend | −14.4 / **−19.3** | +19.7 / +26.3 | +10.0 / +6.2 | +9.5 / +7.2 | +9.4 / +9.4 |
| Pre-trend, Jan–Jul 2025 YoY | +4.8 | −6.6 | +3.8 | +2.3 | 0.0 |
| Seasonal-factor counterfactual gap, 13 m | −$9.4bn (−19.9%) | +$27.6bn (+30.0%) | +$2.8bn (+5.1%) | +$11.6bn (+6.7%) | +$34.1bn (+9.3%) |
| Two-year change (vs Aug 2023–Aug 2024) | −11.4 | **+4.1** | +12.7 | +13.6 | +7.7 |

**Placebo tests.** Breaks were placed at every month 2016-01…2024-06 (n = 102), ending there so no window overlaps the real treatment.
- **US, 13-month DiD:** placebo rank p = **0.23**, with a 5–95% band of [−34.8, +60.6]. The largest placebo moves are the 2020-11…2021-03 COVID-rebound windows (+66 to +72).
- **US robustness (post-hoc):** excluding windows that touch Mar 2020–Jun 2021 (n = 54) gives p = **0.018** and a band of [−12.2, +22.8]. The 4-month DiD gives p = **0.029**.
- **China:** upper-tail p = 0.078. The comparable placebo moves are the 2019 soy-reversal windows (−55 to −61) and Mar 2024, as the plan expected.
- **Total:** p = 0.28 (not unusual).

**Verdicts.**
- **"Material": fails on the pre-registered test** (p = 0.23 > 0.10). It passes on the post-hoc ex-COVID and 4-month versions.
- **"Diversion dominant": passes.** The total DiD is +9.4 and the two-year change +7.7%. The 2026 oil price explains about 30% of YTD growth, so "dominant" is generous.
- **"China base effect dominant": passes.** The two-year change is +4.1% vs a one-year change of +19.7%.

The plan's expected read-out holds, with weaker statistical support for the US effect than expected.

**Elasticity outputs.**
- **E_tariff** (realised fall in US-bound exports): −25% (4 months) to −14% (13 months) for a 50% tariff. MDIC's figures (A04) show 35.9% of US-bound exports hit by the full 50%, 44.6% outside the 40%, and 19.5% under Section 232.
- **G_US:** −$7.9bn/yr. Part of it is not tariff-driven: crude oil was exempt yet fell 30% in 2025 (A15). G_US is therefore an upper bound on the tariff effect.
- **Diversion:** the gain above pre-trend outside the US was China +$26.2bn, EU +$3.3bn and rest +$12.1bn over 13 months. That is 4.9× |G_US|, so the upper-bound diversion rate is capped at 1. The lower bound is 0. The central rate is 0.44, the fungible share of the US mix (H1 2025: crude, oil products, semi-finished steel, coffee, beef, juices, pig iron and pulp total $8.73bn of $20.03bn; A14). **Net loss: −$4.4bn/yr central, range −$7.9bn to ≈ 0.**
- **Price cost of diversion:** no visible cost. `oil_export_unit_value`/(Brent×7.33) was 0.90 before (Jan–Jul 2025) and 0.87 after, vs 0.85 in 2024 and 0.86 in 2023. `pulp_unit_value` was $467/t before and $485/t after.
- **Time profile:** US YoY troughed at −24.7% (mean of Aug–Nov 2025), then averaged −15.3% over Dec 2025–May 2026, then **+2.7%** over Jun–Aug 2026. Jun–Aug 2026 is −0.5% vs Jun–Aug 2024. The recovery coincides with the Nov 2025 food relief (A09) and the IEEPA ruling that cut the layer to Section 122 at 10% (A16, A17). The new Section 301 25% + 12.5% layer started 22–24 Jul 2026 (A21, A22), and its effect is not yet visible (one month).

Charts: `charts/3_tariff_yoy.html`, `charts/4_us_counterfactual.html`, `charts/5_china_base_effect.html`.

## 3. Elasticities and the GDP mapping

**Terms-of-trade channel.** Regression of `wb/NY.GDP.PCAP.KD.ZG.BR` on 100·Δlog annual-mean `wb/TOT.BRA`:
- 1992–2025: β = **0.244**, 90% CI [0.171, 0.318], R² 0.35, n 34, permutation p < 0.001.
- 1997–: β = 0.257 [0.168, 0.343].
- 2003–: β = 0.274 [0.151, 0.364].
- Using `wb/TT.PRI.MRCH.XD.WD.BR` (2006–2024): β = 0.279 [0.149, 0.366].

The band used is 0.24–0.29. β is reduced-form and moves with the global cycle, so it is an upper bound for a pure price shock. A ±10% ToT state is near the p90/p10 of annual Δlog ToT (+0.095 / −0.049; sd 0.063).

**Direct-demand channel** (volume and market-access shocks): ΔGDP% = ΔX/GDP × (1−m) × k, with m ∈ [0.10, 0.20], k ∈ [1.0, 1.5] and GDP = $2,280bn (`wb/NY.GDP.MKTP.CD.BR`, 2025). For G_US this gives −0.28% to −0.47% of the GDP level, once.

**FX.** Regression of Δlog `wb/TX.QTY.MRCH.XD.WD.BR` on Δlog `wb/PX.REX.REER.BR` + Δlog ToT, 2006–2024 (n 19):
- b_REER = 0.05, 90% CI [−0.39, 0.20], R² 0.07. Adding a lag 1 gives a summed coefficient of 0.07 [−0.50, 0.28].
- Monthly version (12-month-sum exports on the 12-month-mean BRL, Brent control): b_fx between −0.05 and +0.08 at every lag 0–12, and every CI includes 0.

The pre-registered read-out holds: **FX does not move USD export values**. It moves BRL margins, imports and the fertiliser bill. The 5 Oct rally (BRL +4% to ≈R$5.00, C60) is therefore not an export channel. Chart: `charts/6_tot_vs_gdppc.html`.

## 4. Historical analogues

| Term (warehouse window) | China % | US % | EU % | Rest % | EU $bn/yr | US $bn/yr | China $bn/yr | beef→China $bn/yr |
|---|---|---|---|---|---|---|---|---|
| Temer 2016-05→2018-12 | 23.6 | 12.6 | 14.5 | 49.2 | 31.2 | 27.1 | 50.7 | 1.1 |
| Bolsonaro 2019-01→2022-12 | 29.5 | 11.5 | 13.9 | 45.1 | 36.3 | 29.9 | 77.1 | 4.6 |
| Lula III 2023-01→2026-08 | 29.4 | 10.9 | 14.2 | 45.4 | 49.5 | 37.9 | 102.5 | 7.1 |

- **The mix is flat across lean.** Confounders: COVID and the 2021–22 commodity boom. Term-level lean statistics belong to the politics study and are not recomputed here.
- **Bolsonaro and China.** Despite the rhetoric (Taiwan visit 2018; Eduardo's 5G/COVID spats), no Chinese trade measures followed (B25–B27). The China share rose and beef→China quadrupled; African swine fever is a confounder. This record is the central case for Flávio.
- **Deforestation** (`wb/AG.LND.PFLS.HA.BR`, primary forest loss). The 2019–22 mean is 1.60m ha. The 2023–25 mean is 1.86m ha including the 2024 fire year (2.82m), or 1.38m ha excluding it. Tree-cover loss (`wb/AG.LND.FRLS.HA.BR`) is 3.07m vs 3.36m ha. The Lula III mean is **not** lower once 2024 is included. INPE's PRODES clear-cut measure fell 11% in 2025 (C28), and DETER alerts fell 37% in 2025–26 (C29). EU exports rose in every high-deforestation year (chart 8), so there is no visible market penalty so far. The EUDR, which starts 30 Dec 2026 (C23), is what changes that.
- **2018 US–China round 1.** Soy YoY ran −3.4 / +17.1 / **+42.7 / +106.8** over 2018Q1–Q4, then +10.6 / **−27.9 / −34.1** / −12.5 over 2019Q1–Q4. That is a windfall of +$7.3bn in 2018 reversed by −$7.0bn in 2019. The 2025 standoff: soy +55% in 2025Q4, +11% and +17% in 2026Q1–Q2. Escalation gains are large and transitory.

Chart: `charts/8_deforestation_vs_eu.html`.

## 5. Channels (`channels.csv`, 15 rows; fact ids in external_facts.csv)

| # | Channel | Who holds the lever | Lula IV | Flávio | Exposure | Elasticity / analogue |
|---|---|---|---|---|---|---|
| C1 | US tariffs/301 | Counterpart; president negotiates | 3 Trump meetings; Nov-25 carve-out; 301 final Jul-26 | "tarifa do Lula"; promises a deal; met Trump May-26 | US $37.7bn; 37.5% layer on ~$6.6bn | G_US −7.9bn/yr |
| C2 | Family–Washington link | Counterpart + STF | adversary | amnesty in transition; Eduardo a defendant | indirect | qualitative |
| C3 | Russia secondary tariffs | US (waiver) | buys Russian diesel and fertiliser | n/a | imports (potash 40% Russian) | ≈0 on exports: Brazil is not a top-5 crude/gas buyer (A45) |
| C4 | China alignment | President + Beijing | deep engagement; beef quota not flexed | "pragmatic"; BRICS exit floated; Pix vs UnionPay | China $99.9bn | 2019–22: no measures; Australia ≈14% of flows |
| C5 | BRICS / de-dollarisation | President | hosted Rio 2025; swap renewed | may leave | ≈0 direct | via C1 only |
| C6 | EU–Mercosur | EU institutions + president | signed, provisional since May-26 | important "to EU audiences"; programme silent | EU $49.8bn | Ipea +$7bn by 2040; EU +23.5% May–Aug 26 |
| C7 | Environment/EUDR | President + Congress + EU | PRODES −11%, DETER −37% | omits Paris; "amarras ambientais" | ~$12–15bn EUDR-exposed (proxy) | worst −2 to −5bn |
| C8 | CBAM | EU | SBCE law | – | EU iron & steel $1.74bn | < $0.5bn |
| C9 | Mercosur/Argentina | President + partners | ties downgraded Aug-26 | Milei ally; loosen Mercosur | Argentina $18.1bn (−19% H1-26) | ±1–4bn |
| C10 | India/Middle East | President | India $30bn target | Jerusalem move within 6 months | ME chicken $3.1bn | 2019: delistings, no sustained loss |
| C11 | Petrobras/oil | Petrobras/ANP/Ibama | Foz do Amazonas licensed | no privatisation | oil $44.5bn | capacity- and Brent-driven |
| C12 | Sanitary access | MAPA (technocratic) | 639 openings | Tereza Cristina advising | beef $16.5bn | suspensions 1–3.4 months |
| C13 | Critical minerals | President (Cimce) | sovereignty-first | fast-track US | niobium $2.66bn | small, strategic |
| C14 | FX | BCB/fiscal | Selic 13.75% | market rally on lead | – | no USD volume effect |
| C15 | Run-off | voters | 45.16% | 47.03% | – | ~50/50 |

## 6. Scenario matrix (`scenario_matrix.csv`)

Impacts are changes in **annual exports** against a status quo: 2025 levels under the policies in force on 2026-10-05. That status quo already includes the Section 301 + forced-labour layer, the binding China beef quota, the EU meat suspension and the provisionally applied EU–Mercosur deal. The GDP column is the direct-demand channel only (% of GDP level, one-off). The 2027–30 cumulative figures are in the CSV (annual × [first-year phase + 3]). Probabilities are qualitative: low < 25%, medium 25–60%, high > 60%. They describe the case conditional on that candidate winning; rationales are in the CSV.

### 6a. Candidate × case × partner (US$bn/yr; % of 2025 exports; % GDP)

| Candidate | Case | US | China | EU | Mercosur/LatAm | Rest | **Sum** (not strictly additive) |
|---|---|---|---|---|---|---|---|
| Lula IV | best | +1 to +3 (med) | +3 to +8 (med) | +1 to +3 (med-high) | +1 to +3 (low-med) | +1 to +3 (med) | **+7 to +20; +2.0–5.7%; +0.25–1.18% GDP** |
| Lula IV | worst | −5 to −2 (low-med) | −10 to −3 (med) | −2 to 0 (med) | −3 to −1 (med) | −1 to 0 (low) | **−21 to −6; −6.0 to −1.7%; −1.24 to −0.21% GDP** |
| Flávio | best | +2 to +6 (med) | 0 to +3 (high) | 0 to +2 (low-med) | +2 to +4 (med) | +1 to +3 (low) | **+5 to +18; +1.4–5.2%; +0.18–1.07% GDP** |
| Flávio | worst | 0 to +2 (med) | −15 to −3 (low) | −5 to −2 (low-med) | −4 to −2 (low-med) | −3 to −1 (med trigger / low cost) | **−27 to −6; −7.8 to −1.7%; −1.60 to −0.21% GDP** |

**Mechanisms, one line each:**
- **Lula best.** US: more carve-outs, not removal of Section 301. China: plant listings and soy share held. EU: interim agreement phase-in plus beef relisting. LatAm: Argentine recovery. Rest: India and Gulf openings.
- **Lula worst.** US: escalation from the 37.5% layer (exemptions narrowed, Magnitsky re-imposed). China: the US–China truce shifts soy share; this is not Lula's choice. EU: the beef ban lasts two years and the CJEU opinion is adverse. LatAm: Milei hostility and Chinese cars displacing Brazilian autos.
- **Flávio best.** US: the 301 and forced-labour layer is lifted in a bilateral deal; Section 232 stays. China: pragmatic continuity, as in 2019–22. EU: the deal is kept. LatAm: alignment with Milei. Rest: MAPA continuity.
- **Flávio worst.** US: relief requires Pix, ethanol and digital concessions, so it is partial. China: alignment with the US triggers Australia-style coercion. EU: deforestation rises before the EUDR start, with high-risk classification and importer de-risking. LatAm: Mercosur loosened into a free-trade area, eroding auto preferences. Rest: the Jerusalem move causes halal delistings.

**Correlation assumptions.** Under Flávio, US relief and China friction are negatively correlated, and the worst case stacks partial US relief on the China tail. Under Lula, US persistence and China access are positively correlated. The Lula-worst China cell is driven by US–China détente, which would also ease US pressure.

**Revisions to the plan's §6.2 ranges after web research** (`scenario_revisions.csv`):
- **US cells shrunk.** IEEPA was voided, and the current 301 layer covers only $6.6bn of goods. Section 232 (24% of US-bound exports) cannot be negotiated away country by country. Lula best goes from +2/+4 to +1/+3; Lula worst from −6/−3 to −5/−2; Flávio best from +4/+8 to +2/+6; Flávio worst from +2/+4 to 0/+2.
- **China cells.** Lula worst goes from −13/−6 to −10/−3, because diversion of soy already works (B11) and the beef quota binds under either candidate. Flávio worst goes from −20/−5 to −15/−3, using the Australia analogue at ≈14% of flows with partial re-routing (B19, B20).
- **EU and LatAm cells.** Lula worst EU goes from −0.5/0 to −2/0 because of the beef suspension. Lula worst LatAm is unchanged, with new evidence.
- **Détente overlay** goes from −10/−5 to −8/−2.

### 6b. Candidate × global state (US$bn/yr: candidate sum + overlay)

| | Candidate only | ToT high (+10%) | ToT low (−10%) | US–China escalation | US–China détente |
|---|---|---|---|---|---|
| Lula best | +7 to +20 | +21 to +42 | −15 to +6 | +12 to +35 | −1 to +18 |
| Lula worst | −21 to −6 | −7 to +16 | −43 to −20 | −16 to +9 | −21 to −6 (détente already inside the cell) |
| Flávio best | +5 to +18 | +19 to +40 | −17 to +4 | +10 to +33 | −3 to +16 |
| Flávio worst | −27 to −6 | −13 to +16 | −49 to −20 | −22 to +9 | −35 to −8 |

**Overlays:**
- **ToT ±10%.** Applied to the 69.0% commodity-priced share with pass-through 0.6–0.9, this gives **±$14–22bn/yr**. That is smaller than the plan's ±$25–35bn, which does not follow from its own formula. The β mapping gives ±2.3–3.1 points of GDP-per-capita growth, an upper bound; the mechanical income effect is about ±1.5% of GDP. The 2026 Brent shock means a ToT-high state is partly live already.
- **US–China.** Escalation: +$5 to +15bn, transitory over 4–6 quarters. Détente: −$8 to −2bn.

**Which dominates.** With the case held fixed, the candidate gap is ≈ $2bn (best) to $3bn (worst) at the central values. The tail gap, either candidate's best minus the other's worst, is at most $47bn. Moving from ToT low to ToT high is worth **$29–43bn/yr**. The US–China state is worth $7–23bn. **The commodity state dominates the candidate.** The US–China state is about as large as any single candidate cell. The candidate choice mainly changes *which partner carries the risk*, not the expected size of the export bill. Chart: `charts/7_scenario_tornado.html`.

### 6c. Asymmetries

- **Flávio.**
  - His upside is concentrated in the US: 10.8% of exports, with only ~$6.6bn under the removable 37.5% layer, and it depends on Trump. He has an explicit pro-US alignment, a White House visit and a "tarifa do Lula" framing (A27, A28), but Section 301 is a trade finding about Pix, ethanol and digital trade (A19). Those concessions are hard to deliver.
  - His downside tails sit in the largest partner (China, 28.7%), in EU market access (EUDR from 30 Dec 2026; a programme without Paris or the NDC, C35), in Mercosur (loosening it) and in the Gulf (Jerusalem pledge, B37).
  - His realistic central case is the 2019–22 record: unchanged mix, with "pragmatic" China language (A31).
  - He cannot undo EU–Mercosur, which is already provisionally applied (C07).
- **Lula.**
  - His upside is continuity with China and the EU (43% of exports), EU–Mercosur already in force, and the India push.
  - His downside is persistent US coercion. Rubio blames Lula personally (A25), and Magnitsky re-imposition was discussed (A12). A US–China détente that erodes the soy windfall is outside his control.
  - His central case is today's data: US −9.7% YTD, China +15.0%, EU +15.0%.
- **Both** face the China beef quota (67% from Oct 2026; ABIEC expects beef exports −10% in 2026; B14, B15), the EU meat suspension (C19), Argentina's auto displacement by China (C43) and Brent.

## 7. What cannot be concluded

- There is no product×destination data except beef→China, so the exempt/non-exempt split of US-bound exports is external (A04, A23). Soy→China, crude→US and coffee→US are inferred from totals.
- There is no 2026 ToT. It is proxied by Brent and unit values, labelled as a proxy.
- There is no Mercosur, India or MENA destination series after 2023. The LatAm proxy is an upper bound.
- The US tariff effect is not significant on the pre-registered placebo (p = 0.23). Its significance rests on post-hoc exclusions.
- β is reduced-form, n = 34 annual observations. The FX regression has n = 19.
- Scenario ranges are judgement bounded by analogues, not estimates. Probabilities are qualitative and conditional on the candidate winning.
- Every external fact is fenced in Appendix B. Several rest on one secondary source (confidence column). In particular, A47's 81% Russian diesel share is low confidence, A39 (Trump's endorsement) is contested, and B11 comes from StoneX alone.

## 8. Future work (plan §1.3)

Extend `ingest/comexstat.py`. `fetch_by_country("export")` already returns every destination, so keeping Argentina, India, Saudi Arabia, UAE, Egypt, Japan, Mexico, Chile, Netherlands, Spain and Germany costs no extra API calls. Further additions:
- NCM×country series: soy→China, coffee→US, beef→US, oil→US/China, iron ore→China, pulp→US/EU/China.
- `economicBlock` filters for Mercosul and Oriente Médio.
- `metricKG` companions for soy, beef, coffee and sugar.
- The US 301 Annex as exempt and non-exempt NCM groups × country 249.
- A US Census mirror (imports from Brazil by HS).

Register all of these in `registry/brazil_macro_data_allocation_metrics.csv` (row 45).
