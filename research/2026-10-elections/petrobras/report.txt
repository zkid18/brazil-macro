# 09 · Petrobras under left and right governments, and what the 25 Oct 2026 run-off means for it

**Data.** The Brazil Monitoring warehouse (read-only), extended where it stops:
- **Petrobras PN total return:** `share_close_brl@PETR` + `dividend_per_share_brl@PETR` (B3, daily, last 2026-10-02). Back to 2000 with B3 COTAHIST annual files and the B3 cash-dividend API; forward to 2026-10-09 with COTAHIST daily files. The rebuilt series matches the warehouse's `total_return_usd@PETR` exactly for 2012–2026 (monthly correlation 1.000, return difference 0.0 pp/yr).
- **Market and macro:**
  - `ibovespa_level` (IPEAData, last 2026-10-01), extended with BOVA11 to 2026-10-09;
  - `brent_usd` (IPEAData, last 2026-09-29), extended with FRED DCOILBRENTEU to 2026-10-06;
  - `brl_usd` (BCB SGS, last 2026-10-02), extended with SGS 1 to 2026-10-09.
- **Fundamentals:** `v_company_quarterly` for PETR (CVM, last quarter 2026-06-30); `oil_production` (IPEAData, last 2026-07); `operated_oil_production_kbd@PETR` (ANP, last 2026-08).
- **Fuel prices:** ANP weekly producer/importer prices for gasoline A and diesel (include PIS/Cofins/CIDE, exclude ICMS; last week 2026-09-28).
- **Fiscal:** Tesouro Nacional RTN table 1.1 (monthly, last 2026-07) and `gdp_nominal_12m_brl` (BCB, last 2026-08).
- **Exports and index weights:** `oil_exports`, `iron_ore_exports`, `soy_exports`, `exports_total` (ComexStat, last 2026-08); B3 Ibovespa portfolio snapshot of 2026-10-03.

**Files.**
- Scripts: `fetch.py`, `petrobras_study.py`.
- Outputs: `results.json` and the CSVs.
- Charts: `charts/*.html`.
- Hypotheses, written before any results: `preregistration.txt`.
- External facts with URLs: `external_facts.csv`.

**Terms (defined here, not from `v_by_term`):**

| Term | Months | Lean |
|---|---|---|
| FHC (data only from 2000) | 2000 – Dec 2002 | right |
| Lula I–II | Jan 2003 – Dec 2010 | left |
| Dilma | Jan 2011 – Aug 2016 | left |
| Temer | Sep 2016 – Dec 2018 | right |
| Bolsonaro | Jan 2019 – Dec 2022 | right |
| Lula III | Jan 2023 – now (term stats to Sep 2026) | left |

---

## Headline

1. **"Left is bad for Petrobras" is too simple. The data show something narrower: the government changes Petrobras through discrete governance shocks, not through a steady left-vs-right drag.**
   - Over whole terms, the left-minus-right gap in Brent-adjusted returns has the wrong sign: +11 pp/yr (permutation p = 0.70).
   - Against the Ibovespa, the left trails the right by 13 pp/yr. That gap is suggestive but not robust: bootstrap p = 0.10, permutation 4 of 20.
2. **Lula III is not Dilma.**
   - Shareholder returns: Petrobras returned +42.5%/yr in USD in Jan 2023 – Sep 2026, beating the Ibovespa by 21 pp/yr. That is the best of the six terms against the market. Under Dilma it lost 20%/yr and trailed the market by 7 pp/yr.
   - Pricing: fuel prices follow Brent far more under Lula III than under Dilma. Quarterly pass-through is 0.58 for gasoline and 0.79 for diesel, against 0.23 and 0.23 under Dilma.
3. **The government-driven events are where the damage shows up, and it is large and statistically clear.** On the day of the event and the next, Petrobras lost (abnormal return vs the Ibovespa):
   - −8.5% when Bolsonaro fired CEO Castello Branco in Feb 2021;
   - −11.4% when the board withheld extraordinary dividends in Mar 2024;
   - −9.3% when Lula fired CEO Prates in May 2024;
   - −10.5% after Lula's 2022 run-off win;
   - −9.5% after Dilma's 2014 re-election.

   Across the 15 pre-registered events, the signed mean is +3.5% in the predicted direction (placebo p < 0.001); 12 of 15 have the predicted sign. **Both sides interfered:** Bolsonaro fired three CEOs in 2021–22.
4. **Petrobras is the most important single company in the election story, but not "the" most important piece.** On election days it moves about as much as the real (BRL), relative to normal volatility:
   - pre-registered set: mean |z| 1.52 vs 1.50;
   - with the exploratory first rounds added, the BRL leads (2.17 vs 1.88).
   - **On 5 Oct 2026, after Flávio's first-round lead, Petrobras ranked 4th of 6 assets.** It gained 5.0%, against Itaú +11.8%, Ibovespa ex-Petrobras +6.6% and the BRL +5.0% (z 5.8). This election is being traded through rates, the currency and banks first.
5. **The fiscal channel is real but small at the margin.**
   - Petrobras dividends to the Union plus net oil royalties come to 3.5–3.7% of federal net revenue, or 0.65% of GDP (2023–25).
   - A 10 pp change in Petrobras payout moves Union receipts by about R$3.9bn (0.03% of GDP).
   - A US$10/bbl change in Brent moves net royalties by about R$10bn (0.08% of GDP).
   - Petrobras matters to the budget only in boom years like 2022, when it supplied 1.1% of GDP and turned a −0.64% primary balance into +0.46%. It cannot fix the "budget is the weak link" problem by itself.
6. **The most live risk for Petrobras in Oct 2026 is the oil shock, whoever wins.**
   - Brent is at US$114–136 (FRED, 2–6 Oct 2026).
   - Petrobras's gasoline producer price, *including* federal taxes, fell to 0.96× Brent in Sep 2026, the lowest ratio in the sample.
   - The government is already paying diesel subsidies (MP 1,340 / 1,363 / 1,391).
   - The next president inherits a large fuel-price gap. How it is closed matters more for Petrobras than the party label.

---

## 1. Shareholder returns by term (monthly, USD)

Petrobras PN total return in USD against the Ibovespa in USD and Brent. Sources: `share_close_brl@PETR`, `dividend_per_share_brl@PETR`, `ibovespa_level`, `brent_usd`, `brl_usd`; Feb 2000 – Sep 2026. File: `term_returns.csv`.

**Abnormal returns.**
- **Brent model:** monthly PETR USD return = a + 0.485 × Brent return. R² is only 0.22, so Brent explains a fifth of Petrobras's monthly moves.
- **Two-factor model:** Brent 0.21, Ibovespa USD 1.06.

| Term | Lean | Months | PETR TR USD %/yr | Ibov USD %/yr | Brent %/yr | PETR vs Ibov pp/yr | Brent-adjusted pp/yr | Brent+Ibov model pp/yr |
|---|---|---|---|---|---|---|---|---|
| FHC (2000–02) | right | 35 | −12.7 | −30.2 | +5.3 | +22.3 | −16.1 | +23.3 |
| Lula I–II | left | 96 | +39.5 | +37.9 | +14.5 | +1.2 | +26.8 | −3.4 |
| Dilma | left | 68 | −19.9 | −13.9 | −11.1 | −7.3 | −16.5 | −4.0 |
| Temer | right | 28 | +20.2 | +10.8 | +2.3 | +8.2 | +17.3 | +7.1 |
| Bolsonaro | right | 48 | +14.5 | −1.8 | +13.1 | +15.3 | +7.5 | +12.9 |
| Lula III | left | 45 | **+42.5** | +15.3 | +9.4 | **+21.2** | **+31.1** | +18.6 |

**Left minus right (pooled months, annualised).** The pre-registered hypothesis H1 (left < right on the Brent-adjusted measure) is **not supported**.

| Measure | Left − right, pp/yr | 90% block-bootstrap CI | Permutation (20 labellings) |
|---|---|---|---|
| Brent-adjusted (pre-registered) | **+11.1** | −12.8 to +35.4 | p = 0.70 |
| Excess vs Ibovespa | −13.0 | −29.6 to +3.3 | 4 of 20, p = 0.20 (bootstrap p = 0.10) |
| Brent + Ibovespa model | −13.6 | −29.0 to +1.8 | p = 0.15 |
| Brent-adjusted, ex-FHC | +2.5 | | |
| Brent-adjusted, ex GFC and COVID months | +8.0 | | |

- **The left terms are a mixed bag:**
  - Lula I–II (supercycle, pre-salt discovery, 2010 capitalisation) and Lula III (record output, high payout) did very well;
  - Dilma (fuel-price caps, Lava Jato, impairments) was the worst term.
- **Against the local market there is a mild right-leaning tilt, carried by Dilma and the FHC years.** Lula III breaks the pattern.
- **With six terms, this is descriptive.** The smallest attainable permutation p is 0.05.
- **Since the first round:** from 2 Oct to 9 Oct 2026, PETR4 total return rose +9.4% vs the Ibovespa +8.2% and the BRL +4.7% (COTAHIST, BOVA11, SGS 1).

Charts: `charts/petr_vs_ibov_brent.html`, `charts/term_abnormal_returns.html`.

## 2. Event study: what moves Petrobras is governance

**Method.**
- Day 0 is the first session on or after the event; evening and weekend news moves to the next session.
- Market model: PETR4 total return (BRL) on the Ibovespa, estimated over sessions −250 to −21.
- Brent model: PETR USD return on Brent USD return.
- Placebo: 2,000 random sessions outside ±20 days of any event (Ibovespa model: 5th–95th percentile for days 0..+1 is −4.0% to +3.9%).

File: `event_study.csv`. Chart: `charts/event_study.html`.

| Day 0 | Event | CAR 0..+1 vs Ibov | placebo p | CAR 0..+5 vs Ibov | CAR 0..+1 vs Brent | raw 0..+1 |
|---|---|---|---|---|---|---|
| 2002-10-28 | Lula wins run-off | −2.0% | 0.34 | −0.5% | −4.3% | −4.7% |
| 2006-10-30 | Lula re-elected | −0.0% | 0.98 | −0.4% | −0.6% | −0.1% |
| 2010-11-01 | Dilma wins | +3.5% | 0.12 | +4.8% | +4.3% | +4.9% |
| 2014-10-27 | Dilma re-elected | **−9.5%** | 0.01 | −16.4% | −8.3% | −8.1% |
| 2018-10-29 | Bolsonaro wins | −1.1% | 0.56 | −7.9% | +0.6% | +1.4% |
| 2022-10-31 | Lula wins | **−10.5%** | 0.01 | −19.4% | −5.6% | −8.7% |
| **2026-10-05** | **First round: Flávio 47.0 vs Lula 45.2** | +2.3% | 0.27 | +5.1% (0..+4) | +11.3% (p 0.02) | +5.1% |
| 2016-10-14 | PPI import-parity policy adopted | +1.9% | 0.36 | +3.3% | +7.5% | +7.0% |
| 2023-05-16 | PPI abandoned | −0.6% | 0.74 | +0.9% | −1.8% | −0.0% |
| 2021-02-22 | Bolsonaro fires Castello Branco | **−8.5%** | 0.01 | −11.2% | −14.7% | −12.7% |
| 2022-03-29 | Govt names Pires (replacing Silva e Luna) | +3.0% | 0.16 | +1.2% | +4.3% | +4.3% |
| 2022-05-24 | Govt fires Coelho | −1.5% | 0.44 | −9.0% | −2.5% | −1.1% |
| 2024-05-15 | Lula fires Prates | **−9.3%** | 0.01 | −8.5% | −9.5% | −9.1% |
| 2024-03-08 | Board withholds extra dividends | **−11.4%** | 0.01 | −10.9% | −13.4% | −12.5% |
| 2024-04-19 | Govt agrees to pay 50% of the reserve | +2.7% | 0.21 | +3.8% | +4.9% | +4.1% |

**Exploratory events (not pre-registered).**
- First rounds, CAR vs Ibovespa: 2014 +5.6%, 2018 +3.3%, 2022 +0.7%.
- Parente's resignation, 1 Jun 2018: −11.4%.

**Group tests (pre-registered, n = 15, CAR signed so that "+" means the predicted direction).**

| Model and window | Signed mean | Placebo p | Correct sign | Sign test p |
|---|---|---|---|---|
| Ibovespa, 0..+1 | +3.5% | < 0.001 | 12 of 15 | 0.018 |
| Ibovespa, 0..+5 | +4.9% | < 0.001 | | |
| Brent, 0..+1 | +5.1% | < 0.001 | 13 of 15 | 0.004 |

By type (Ibovespa model, 0..+1): elections +2.8%, CEO removals +4.1%, dividends +7.0%, pricing +1.2%.

**Reading.**
- **Investors punish the government interfering with management, dividends and prices, under either side.** The big negative governance shocks come from every camp: Lula III twice (Mar and May 2024, −11.4% and −9.3%), Bolsonaro once (Feb 2021, −8.5%) and Temer once (Parente's exit after the 2018 truckers'-strike diesel concession, −11.4%).
- **The formal pricing-policy switches barely moved the stock relative to the market.** In 2023 the end of import-parity pricing had been fully expected since the campaign.
- **Elections hit Petrobras only when the result surprised against the market.** The Dilma 2014 and Lula 2022 wins came after first rounds that had raised hopes for the right.
- **The 2026 first round is a modest positive:**
  - +2.3% vs the Ibovespa;
  - +11.3% vs Brent, but Brent fell 7.4% that day (135.5 → 125.5), which inflates the Brent-model number.

## 3. What does the government actually change at Petrobras?

Annual series: `petrobras_annual.csv`. CVM fundamentals start in 2012, so Dilma's term covers 2012Q1–2016Q2 only. By term: `fundamentals_by_term.csv`.

| Term | Brent avg | Revenue US$bn/yr | Net income US$bn/yr | Dividends US$bn/yr | Payout % | Capex US$bn/yr | Net debt US$bn, term end | National oil output growth %/yr |
|---|---|---|---|---|---|---|---|---|
| Lula I–II | 62 | – | – | – | – | – | – | +4.9 |
| Dilma (2012–16Q2) | 87 | 126 | 1.1 | 2.2 | n/m (losses) | **32.6** | **103.6** | +3.7 |
| Temer | 60 | 91 | 1.1 | 0.3 | 21 | 13.1 | 69.4 | +0.2 |
| Bolsonaro | 69 | 85 | 16.5 | 13.6 | **82** | **7.6** | 43.0 | +3.9 |
| Lula III (to 2026Q2) | 79 | 97 | 19.5 | 14.3 | 74 | 15.8 | 60.4 | **+9.5** |

**Sources.**
- Revenue: `revenue_usd_bn@PETR`.
- Net income, dividends, capex and net debt: `net_income_brl@PETR`, `dividends_paid_brl@PETR`, `capex_brl@PETR`, `net_debt_brl_bn@PETR`, converted at average or end-quarter `brl_usd`. CVM, last 2026-06-30.
- Production: `oil_production`, IPEAData, last 2026-07. Petrobras-operated output (`operated_oil_production_kbd@PETR`, ANP) grew +9.4%/yr in Lula III and +4.0%/yr under Bolsonaro.

**What changes between governments:**
- **Capex vs cash returned: the clearest lever.**
  - Dilma spent US$33bn/yr, including refineries such as Abreu e Lima and Comperj, and ran net debt above US$100bn.
  - Bolsonaro cut capex to US$7.6bn/yr and paid out 82% of net income.
  - Lula III sits in between and is moving back towards capex:
    - capex rose from US$12.1bn (2023) to US$19.6bn (2025);
    - payout fell from 79% to 41% (2023 → 2025) and 23% in 2026H1;
    - net debt rose from US$43bn to US$60bn.
  - That is the direction of a "Lula IV" Petrobras.
- **Output is not a left/right story.** Pre-salt units contracted years earlier came on stream under Lula III, and national output grew +9.5%/yr, from 3.0 to 4.6m b/d.

**Fuel pricing vs Brent.** Producer prices in USD/bbl divided by Brent; files `fuel_prices_by_term.csv`, `fuel_prices_monthly.csv`, chart `charts/fuel_price_vs_brent.html`.

| Term | Brent | Gasoline ÷ Brent | Diesel ÷ Brent | Gasoline vs PPI-era avg | Pass-through, gasoline | Pass-through, diesel |
|---|---|---|---|---|---|---|
| Lula I–II | 62 | 1.84 | 1.60 | +10% | 0.32 | 0.32 |
| Dilma | 90 | 1.41 | 1.38 | **−16%** | **0.23** | **0.23** |
| Temer | 61 | 1.85 | 1.75 | +11% | 0.51 | 0.32 |
| Bolsonaro | 69 | 1.59 | 1.50 | −5% | **0.74** | 0.71 |
| Lula III | 81 | 1.43 | 1.49 | −15% | 0.58 | **0.79** |
| *Sep 2026* | *114* | ***0.96*** | *1.07* | | | |

- **Pass-through** is the slope of quarterly changes in the USD fuel price on quarterly changes in Brent. **This is the clean, tax-robust signal:**
  - Dilma held prices flat whatever Brent did (0.23);
  - pass-through has been 0.5–0.8 under every government since the 2016 PPI rule, including Lula III.
- **The ratio levels are contaminated by federal taxes.** The ANP prices include PIS/Cofins/CIDE, which are fixed in R$ per litre. They were raised in 2015 and 2017, zeroed in 2021–23 and restored in 2023. Fixed per-litre taxes also mechanically lower the ratio when Brent is high.
- **Controlling for Brent, there is no left-term discount in the spread level:** gasoline +1.2 US$/bbl (permutation p = 0.65), diesel −0.1 (p = 0.50).
- **Sep 2026 is the outlier.** Gasoline A sells at US$109/bbl *including* federal taxes, against Brent at US$114. If PIS/Cofins + CIDE are at their 2023 statutory level (about R$0.89/litre), taxes are roughly US$27/bbl. Ex-tax, that implies a discount to import parity on the order of 30–40% (rough, judgement). With diesel also subsidised by the Treasury, the 2026 oil shock is being absorbed by Petrobras and the budget.

## 4. Petrobras as a fiscal channel

**Method.** File: `fiscal_channel_annual.csv`. Chart: `charts/fiscal_channel.html`.
- **Union dividends from Petrobras** = `dividends_paid_brl@PETR` × 29.02% (the Union's direct share of total capital; Petrobras IR, Sep 2026).
- **Royalties and special participation** = RTN line 1.4.4 "Exploração de Recursos Naturais" minus line 2.4 transfers to states and municipalities. This line also includes mining (CFEM) and water fees, but oil dominates.
- **Denominators:** RTN line 3 "Receita Líquida" and `gdp_nominal_12m_brl`.

| Term (full years) | Petrobras dividends to Union, % of net revenue | Net royalties, % of net revenue | Oil channel, % of net revenue | Oil channel, % of GDP | Primary balance, % of GDP (RTN) |
|---|---|---|---|---|---|
| Dilma (2012–16) | 0.12 | 1.13 | 1.26 | 0.23 | −0.37 |
| Temer (2017–18) | 0.03 | 1.57 | 1.60 | 0.28 | −1.80 |
| Bolsonaro (2019–22) | 1.17 | 2.24 | 3.41 | 0.61 | −2.75 (2020 COVID) |
| Lula III (2023–25) | 1.13 | 2.58 | 3.71 | 0.67 | −0.98 |

- **Peak year 2022:**
  - Union Petrobras dividends were R$56bn, 3.0% of net revenue;
  - the oil channel was 1.1% of GDP;
  - the central-government primary balance was +0.46% of GDP, but −0.64% without the oil channel.
- **The channel is shrinking:**
  - 2025: Union dividends R$13bn (0.56% of net revenue);
  - Jan–Jul 2026: R$5.6bn, with net royalties at 3.7% of net revenue on the oil shock.
- **Petrobras is roughly a quarter to two-thirds of the RTN "Dividendos e Participações" line:** 27% in 2020, 65% in 2022, 26% in 2025.

**Scenario arithmetic.** Inputs: trailing four quarters to 2026Q2; net income R$133bn, payout 29%; 12-month GDP R$13.3tn.

| Lever | Change in Union receipts |
|---|---|
| Payout ±10 pp | ±R$3.9bn (0.03% of GDP) |
| Brent ±US$10/bbl, net royalties (proportional, same FX) | ±R$10bn (0.08% of GDP) |
| Bolsonaro-style 80% payout vs Lula III's 2025–26 ~30–40% | about +R$15–19bn (≈0.12–0.15% of GDP) |

The last row is the only budget-relevant lever, and it conflicts with a capex-heavy Lula IV plan.

- **Link to "the budget is the weak link":** Petrobras can flatter a single year's primary balance, as in 2022, but cannot close a gap of 1–2% of GDP.
- **The bigger fiscal exposure in 2026 runs the other way.** The Treasury is paying diesel subsidies of R$1.00–1.12/litre (MPs 1,363 and 1,391). Holding fuel prices down with Brent above US$110 costs the budget more than any likely dividend increase brings in. (The subsidy cost is not in the warehouse, so it is not quantified here.)

## 5. Is Petrobras "the most important piece" of the election story?

**Pre-registered rule.** "Supported" requires both:
1. Petrobras has the largest mean |z| of the two-day election move among PETR, Ibovespa ex-Petrobras, BRL, Itaú, Vale and Axia;
2. Petrobras ranks first on at least two weight measures.

**Election sensitivity.** File: `election_sensitivity.csv`. Chart: `charts/election_sensitivity.html`. Method:
- z is the two-day move divided by the asset's own pre-event volatility × √2;
- Ibovespa ex-Petrobras is built with a 12% Petrobras weight.

| Asset | Mean \|z\|, 7 pre-registered elections (run-offs 2002–22 + 2026 R1) | Mean \|move\| | Mean \|z\|, 10 incl. 2014/18/22 first rounds | 2026 first round, 2-day move |
|---|---|---|---|---|
| Petrobras PN | **1.52** | 4.7% | 1.88 | +5.0% (z 2.1) |
| BRL vs USD | 1.50 | 1.6% | **2.17** | +5.0% (z **5.8**) |
| Itaú | 1.42 | 3.5% | 1.65 | **+11.8%** (z 5.3) |
| Ibovespa ex-Petrobras | 1.34 | 2.7% | 1.65 | +6.6% (z 3.7) |
| Vale | 0.94 | 2.6% | 0.84 | −2.4% (z −1.0) |
| Axia/Eletrobras | 0.79 | 2.7% | 1.37 | +4.4% (z 1.6) |

**Weight in the economy.**

| Measure | Petrobras / oil | Comparison | Rank |
|---|---|---|---|
| Ibovespa weight, single name (B3, 2026-10-03) | **13.5%** (PETR3 + PETR4) | Vale 9.9, Itaú 8.9, Axia 4.8 | 1st |
| Ibovespa weight vs the big-bank block | 13.5% | 22.5% (ITUB, BBDC, BBAS, BPAC, SANB, ITSA) | 2nd |
| Crude oil share of goods exports, 2025 (ComexStat) | **12.8%** | soy 12.5, iron ore 7.6 | 1st |
| Crude oil share of goods exports, Jan–Aug 2026 | 14.7% | soy 15.7 | 2nd |
| Oil channel, % of federal net revenue (2023–25) | 3.7% | | Not compared against other firms |
| FDI | Not measured | Oil cannot be separated in the BCB data used in study 08 | |

The national oil figures include all producers. Petrobras operates about 87% of output (4.01m of 4.60m b/d; `operated_oil_production_kbd@PETR` and `oil_production`).

- **On the letter of the rule, the claim is "supported", but only by a hair.**
  - Petrobras's lead over the BRL on the pre-registered set is 0.03 z.
  - It ranks first on two weight measures (single-name index weight, 2025 exports).
- **In substance, the claim does not hold as stated:**
  - Add the three exploratory first rounds and the BRL is the most election-sensitive asset.
  - In the actual 2026 first-round reaction, Petrobras ranked 4th of 6. The market traded Flávio's lead through the real, banks and domestic cyclicals.
  - Petrobras's index weight is smaller than the bank block.
- **Better framing:** Petrobras is the single company most exposed to *governance* risk, and the place where a president's choices show up fastest (CEO firings, dividends, pricing). But the election's main macro transmission runs through fiscal credibility → rates → BRL → banks, which is the "budget is the weak link" theme.

## 6. Scenarios for the 25 Oct 2026 run-off (JUDGEMENT, not model output)

**Valuation anchors.**
- PETR4 R$56.00 (2026-10-09). Trailing net income R$133bn → EPS ≈ R$10.2 (approximate share count 13.04bn; `external_facts.csv`).
- P/E ≈ 5.5×; trailing dividend yield 7.1% (`dividend_yield_ttm@PETR`, 2026-10-02).
- Historical median P/E by term (`valuation_by_term.csv`): Dilma 10.2×, Temer 20.5× (depressed earnings), Bolsonaro 5.4×, Lula III 4.9×. Lula III's median trailing dividend yield was 17.8%.
- P/E is distorted by earnings swings, so the ranges below are rough re-rating bands applied to current EPS.

**Big caveat:** current EPS reflects Brent averaging ~US$80 over the trailing year. At US$115–135, earnings could rise if Petrobras is allowed to price at parity, or the gain could be absorbed by price caps. That choice is the main swing factor for either winner.

| Scenario | What happens (judgement) | P/E band | PETR4 implied | vs R$56 |
|---|---|---|---|---|
| **Lula IV, continuity** (Lula III playbook) | 'Commercial strategy' pricing with lags; payout ~40–50% of FCF; capex rising (Margem Equatorial, refining, fertilisers); state-chosen CEO; diesel subsidies via the Treasury | 4.5–5.5× | R$46–56 | −18% to 0% |
| **Lula IV, worst case** (Dilma-lite) | Prices frozen through the oil shock; dividends cut to the minimum to fund capex; another CEO or board clash like Mar/May 2024; net debt above US$70bn | 3.5–4.0× | R$36–41 | −36% to −27% |
| **Flávio, market-friendly** | Parity pricing restored, higher payout (Bolsonaro-era ~80%), capex discipline, technocratic CEO; part already priced (+9.4% since 2 Oct) | 6.0–7.0× | R$61–72 | +10% to +28% |
| **Flávio, interventionist** (2021–22 replay) | Fuel-price pressure with Brent above US$110 and a populist incentive; CEO churn as under Jair Bolsonaro (three CEOs in 15 months); pressure to hold diesel down | 4.0–5.0× | R$41–51 | −27% to −9% |
| **Flávio, privatisation talk becomes credible** | Plan to cut the Union's stake or sell refining/distribution; needs Congress and years; low probability | 7.0–8.5× | R$72–87 | +28% to +55% |

**Reading.**
- **The market-implied skew favours Flávio for Petrobras.** But his own record on Petrobras is unknown: no verified statement on privatisation, pricing or dividends was found (`external_facts.csv`). His father's record includes the single worst governance day in the sample (−12.7% raw, Feb 2021).
- **The election shifts the *odds* of good or bad Petrobras governance; it does not settle them.** The event study shows interference costs about 8–11% per episode whoever does it.
- **For the budget, Flávio's higher-payout scenario adds ~0.1–0.15% of GDP a year.** That is helpful but small against a primary deficit near 1% of GDP and debt heading to 93–108% of GDP (study 02).

---

## Caveats

1. **Six terms (three left, three right).** Every term comparison is descriptive. Permutation p-values cannot fall below 0.05, and the bootstrap treats months, not terms, as the unit.
2. **FHC covers only 2000–02.** The term labels are also coarse: Lula I–II spans both the supercycle and the 2008 crash, and Dilma includes Lava Jato and a 70% Brent collapse.
3. **The Brent beta model explains about 22% of monthly variance.** Brent-adjusted term returns pick up much more than politics: global EM flows, BRL, the 2010 capitalisation dilution and Lava Jato write-downs.
4. **Event dates come from 6-K filings where available.** The 2022 Pires/Coelho dates, the 19 Apr 2024 dividend reversal date and Parente's exit are from memory (medium confidence). Placebo p-values are two-sided empirical ranks on 2,000 random days.
5. **Event-window limits:**
   - the 2026 first-round window is truncated: Ibovespa model through day +4 (9 Oct), Brent model through day +1 (Brent ends 6 Oct);
   - Ibovespa after 1 Oct 2026 is proxied by BOVA11;
   - FRED and IPEA Brent differ by up to US$1.9 on overlapping days.
6. **Pre-2012 data:**
   - Petrobras prices are rebuilt from COTAHIST, with the 2000 grouping and the 2005 (1:4) and 2008 (1:2) splits adjusted; dividends come from the B3 API;
   - comparison stocks before 2012 use VALE5, ITAU4/ITUB4 and ELET3 price returns with split days dropped (none in election windows).
7. **Ibovespa ex-Petrobras uses a fixed 12% weight.** The real weight ranged from about 8% to 20% over 2000–26, so the 2008–10 figures are approximate.
8. **Fuel ratios include federal taxes and are not import-parity gaps.** Pass-through is the robust measure. A true parity gap needs crack spreads, freight and ex-tax prices, which are not in the warehouse.
9. **Fiscal estimates:**
   - Union dividends assume a constant 29.02% stake, which changed slightly over time;
   - the RTN natural-resource line includes mining and water fees;
   - Petrobras's income taxes and the 2026 diesel subsidy cost are not included;
   - the 2026 row is partial: Jan–Jul RTN vs H1 CVM.
10. **CVM `dividends_paid_brl` is cash paid in the period, not declared.** Payout ratios therefore lag declarations; 2024's 274% reflects 2023 dividends paid in 2024.
11. **External facts are capped.** The web-search budget was exhausted for this session. External facts were limited to filings reused from earlier studies, a few fetched pages and some memory items flagged as medium confidence. Flávio's Petrobras positions remain unverified.
12. **Section 6 is judgement.** The P/E bands are not forecasts.

---

### Appendix: SQL used (warehouse, read-only)

```sql
-- daily prices, dividends, macro (each pulled with this pattern)
SELECT date, value FROM observations
WHERE series_id = 'share_close_brl@PETR'           -- also dividend_per_share_brl@PETR, brent_usd,
  AND date::DATE <= DATE '2026-10-10';              -- brl_usd, ibovespa_level, share_close_adj_brl@VALE/ITUB/AXIA,
                                                    -- oil_production, operated_oil_production_kbd@PETR,
                                                    -- oil_exports, iron_ore_exports, soy_exports, exports_total,
                                                    -- gdp_nominal_12m_brl, dividend_yield_ttm@PETR, total_return_usd@PETR
-- quarterly fundamentals
SELECT * FROM v_company_quarterly
WHERE entity_id = 'PETR' AND quarter_end <= DATE '2026-10-10' ORDER BY quarter_end;
-- discovery
SELECT series_id, title, source, freq, first_date, last_date, role FROM v_search
WHERE series_id ILIKE '%PETR%' OR title ILIKE '%petrob%' OR title ILIKE '%diesel%' OR title ILIKE '%oil%';
```
