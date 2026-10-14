# 08 · Foreign investment by term: Dilma → Temer → Bolsonaro → Lula III

**Data.** BCB SGS BPM6 monthly balance of payments, US$ mn, Jan 2003 – Aug 2026 (last obs 2026-08-01). Codes:
- Direct investment: 22885 IDP net, 22891 fresh equity (ex reinvested earnings), 22892 reinvested earnings, 22893 intercompany loans, 22865 outward FDI.
- Portfolio: 22930 equity in local market, 22936 funds, 22942 local-market debt, 22945 external-market debt.
- GDP: 4385.

Peers come from the World Bank (BX.KLT.DINV.WD.GD.ZS, 2003–2025), and the controls from the warehouse (`wb/TOT.BRA`, `brent_usd`, `real_policy_rate`). Script: `fdi_terms.py`. Tables: `term_table.csv`, `annual_pct_gdp.csv`, `peer_fdi_pct_gdp.csv`, `results.json`.

Term cut-offs: Dilma Jan 2011 – Aug 2016 · Temer Sep 2016 – Dec 2018 · Bolsonaro 2019–22 · Lula III Jan 2023 – Aug 2026.

## Headline
**Left versus right barely moves the total amount of foreign direct investment. It changes the type of foreign money that comes in.**
- **Left governments:** foreign money comes in through profits retained by companies already in Brazil, and through high-interest local bonds (the carry trade).
- **Right governments:** more fresh equity, meaning new foreign capital invested in companies, plus a little more stock-market money.

## 1. Direct investment (FDI into Brazil), % of GDP over the term

| | Dilma | Temer | Bolsonaro | Lula III |
|---|---|---|---|---|
| **FDI net, total** | 3.59 | **3.87** | 3.29 | 3.44 |
| · fresh equity capital | 2.08 | **2.54** | 1.97 | 1.72 |
| · reinvested earnings | 0.33 | 0.53 | 0.91 | **1.27** |
| · intercompany loans | **1.19** | 0.80 | 0.40 | 0.44 |
| FDI net, US$ bn/yr | 82.0 | 76.8 | 57.3 | 78.7 |
| Brazilian FDI abroad, US$ bn/yr | 11.6 | 12.9 | 17.2 | **31.8** |

- **Total FDI is flat: 3.3–3.9% of GDP under all four presidents.**
  - Total FDI in the controlled regression (monthly rolling 12-month flows, 2011–2026): left minus right = −0.00pp raw; −0.19pp with terms-of-trade, Brent and real-Selic controls. 80% interval −0.54 to −0.02.
  - Permutation test: p = 1.0 (reassigning the two "left" labels across the four terms).
- **Composition: fresh equity is lower under the left.**
  - Lula III has the lowest fresh equity of the four terms, 1.72% of GDP vs 2.54% under Temer.
  - Left vs right: −0.27pp raw, −0.43pp with controls (80% CI −0.69 to −0.24). The permutation p is 0.67: with only four terms, this test cannot reach significance.
- **Reinvested earnings explain how Lula III keeps total FDI up: 1.27% of GDP, about US$29bn/yr.** That is foreign companies already in Brazil keeping their profits there, not new decisions to enter the country. It also partly reflects strong local profits and a high Selic that makes keeping profits in reais attractive.
- **Intercompany loans fell steeply after Dilma.** These are loans from parent companies to their Brazilian subsidiaries. Under Dilma part of this was tax- and interest-driven funding rather than real investment.
- **Brazilian FDI abroad doubled under Lula III, to US$32bn/yr.** Brazilian companies are investing outside the country more than ever. This could be diversification or hedging political risk; the data cannot tell which.

## 2. Brazil vs other emerging markets (World Bank, FDI inflows % of GDP, annual mean by term)

| | Dilma | Temer | Bolsonaro | Lula III (2023–25) |
|---|---|---|---|---|
| Brazil | 3.67 | 3.71 | 3.23 | 3.22 |
| Peer median (CHL, COL, IDN, IND, MEX, TUR, ZAF) | 2.07 | 1.86 | 2.40 | 1.63 |
| Low & middle income aggregate | 2.49 | 1.86 | 1.77 | **1.15** |
| **Brazil minus peers** | +1.60 | **+1.85** | +0.83 | +1.59 |

- **Measured against its peers, Brazil attracted at least as much FDI under Lula III as under Bolsonaro.** Brazil kept about 3.2–3.4% of GDP while global FDI to emerging markets roughly halved, from 2.5% to 1.15% of GDP (de-risking, nearshoring to Mexico, higher US rates).
- **The weak Bolsonaro gap is mostly 2020–21:** COVID, plus South Africa's one-off 2021 Prosus/Naspers transaction distorting the peer median.
- **Peer-relative, the strongest term is Temer** (spending cap, labour reform, Petrobras pricing reform).

## 3. Portfolio money (hot money), % of GDP over the term

| | Dilma | Temer | Bolsonaro | Lula III |
|---|---|---|---|---|
| Equities + funds | **+0.40** | +0.08 | +0.16 | **−0.28** |
| Local-currency bonds | **+0.59** | −0.44 | +0.15 | **+0.58** |
| External bonds | +0.05 | −0.12 | −0.20 | +0.30 |
| Equity, US$ bn/yr | +9.1 | +1.6 | +2.7 | **−6.4** |

- **Foreigners have been net sellers of Brazilian stocks under Lula III**, about −US$6bn/yr. It is the only term with net equity outflows.
  - The effect is weak in the formal test: left minus right +0.25pp with controls, interval spans zero. Dilma's positive equity flows (2011–13, the post-crisis EM rush) offset Lula III.
  - So the equity outflow looks specific to Lula III, not a general left-wing pattern.
- **Local bonds: more inflow under the left.**
  - +0.82pp raw, +1.23pp with controls (80% CI 0.91 to 1.65). The permutation p of 0.33 is the lowest attainable bar one, with only 6 possible label assignments.
  - The likely channel: left governments coincide with high real rates, both Dilma 2015–16 and Lula III's 15% Selic, which attract carry trades. This is money foreigners can pull out quickly.
- **Election windows: 6 months before vs 6 months after the second round, US$ bn**

  | Election | Equity before → after | Local bonds before → after |
  |---|---|---|
  | 2014, Dilma re-elected | +10.0 → +7.2 | +17.1 → +11.5 |
  | 2018, Bolsonaro elected | −2.8 → −3.1 | −2.4 → +3.7 |
  | 2022, Lula elected | −5.8 → **+4.7** | +0.2 → +7.1 |

  - Despite the "market wants the right" narrative, foreign money flowed in after Lula's 2022 win. Most of it went to bonds, consistent with the carry-trade channel, plus a short equity rebound. That episode reversed in 2023–24.
  - This contrasts with the Ibovespa event study in study 02 (+19% in the 60 trading days after right-wing wins). Prices and flows tell different stories: the local price reaction can be large while net foreign flows stay small.

## 4. 2026 so far (Jan–Aug vs Jan–Aug 2025)
- **Total FDI: US$64.4bn vs 62.9bn, steady.** But fresh equity fell from 30.3 to **23.9 (−21%)**, while reinvested earnings rose from 26.9 to **36.2 (+34%)**. New money is pulling back ahead of the election; the total holds up because existing investors keep their profits in Brazil.
- **Equities: −US$3.8bn (vs −1.3bn).** Foreigners are still net sellers into the campaign.
- **External bonds: +US$9.2bn (vs −3.4bn).** Sovereign and corporate bond issuance abroad reopened.
- **Brazilian FDI abroad: US$26.7bn (vs 22.6bn).** Outflows keep rising.

## Read-through for the October 2026 scenarios
- **Flávio wins:** expect the right-wing pattern.
  - Fresh equity FDI and stock-market inflows recover (Temer-style), especially if the fiscal anchor is credible. The pent-up 2026 shortfall in fresh equity, about US$6bn, comes back first.
  - Carry-driven local-bond flows shrink once the Selic falls, which is a smaller cushion for the real.
- **Lula wins:** expect total FDI to stay around 3.3–3.5% of GDP, still mostly reinvested earnings.
  - Fresh equity stays at about 1.7% of GDP. Portfolio equity remains flat to negative.
  - Local-bond inflows persist while the Selic stays high. That makes this money the vulnerable part, because it can leave fast when rates fall or US tariffs escalate (see study 07).
- **Under either winner, the bigger drivers are external:** global EM appetite, the US rate path and terms of trade. The lean coefficients on total FDI are small and statistically indistinguishable from zero.

## Caveats
- **Four terms, two of each lean:** the permutation p cannot fall below 1/3 for a lean effect. Treat lean effects as descriptive.
- **The terms are also different eras:** Dilma had the post-2009 EM boom, then the 2015–16 recession; Bolsonaro had COVID; Lula III had a higher-for-longer US rate period.
- **Reinvested earnings are an estimate:** the BCB estimates them from company profits, so they are revised and move with the profit cycle and exchange rate.
- **FDI flows here are net of disinvestment, not new projects:** M&A and repatriations distort them. Greenfield announcements (fDi Markets, UNCTAD) were not used.
- **The equity flows (22930) are BoP flows, not the B3 foreign-investor tape.**
