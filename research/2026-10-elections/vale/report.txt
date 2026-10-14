# Vale and Brazilian politics: does the president matter for a "private" champion?

Study date 2026-10-10 · run-off 25 Oct 2026 (Lula IV vs Flávio Bolsonaro; first round Flávio 47.03%, Lula 45.16%) · pre-registration: `preregistration.txt` · code: `vale_study.py`, `fetch_external.py` · numbers: `results.json`

## Headline

**Vale trades like a global iron-ore miner with a small Brazil discount. It does not trade like a political football. Petrobras does.**

1. **Left-vs-right gap after controls: small and not significant.** Strip out Vale's exposure to iron ore and to the global miners (BHP and Rio Tinto). After that, Vale earned **4.9 pp/yr less under left governments than under right ones**. The 90% CI runs from -20.8 to +11.9 pp/yr, the block-bootstrap p is 0.61 and the term-permutation p is 0.70. We pre-registered a small, non-significant gap, and that is what we found.
2. **Elections move Brazil and Petrobras, not Vale.** On 5–6 Oct 2026, after Flávio led the first round:
   - Brazil (EWZ) rose **+10.7%** against the S&P 500.
   - Petrobras rose **+8.9%** against Exxon and the S&P 500.
   - Vale rose only **+1.25%** against the global miners and the S&P 500, a normal move (74th percentile of 1,000 random days).
   - Measured against Brazil, Vale lagged by **-4.7%**.

   Across the five left-wing wins since 2002, Vale's average 2-day abnormal return is **-0.85%** (placebo p 0.16). Petrobras's is **-4.7%** (p 0.001).
3. **Government interference has cost little and briefly.**
   - The Agnelli ouster (2011) and the 2024 attempt to install Mantega moved Vale by **-1.5% to -2.7%** over two days. The interference events average -0.9% (placebo p 0.19).
   - The board's choice of a market-friendly CEO (Pimenta, 26 Aug 2024) was worth **+3.1%**.
   - For scale, one operational disaster, Brumadinho, cost **-31.4%** in two days.
4. **Brazil-specific risk explains about 9% of Vale's monthly return variance, against 41% for Petrobras.** Vale's beta to a "pure Brazil" factor is 0.50; Petrobras's is 1.20. Global miners alone explain 64% of Vale's monthly variance.
5. **Fundamentals follow iron ore, not the president.**
   - Dividends rise by about **US$0.9bn/yr for every US$10/t** on the iron ore price (R² 0.66, 2012–2025).
   - The left-minus-right residual is -US$0.9bn/yr, inside one standard deviation (US$1.9bn).
   - The one visible "left" footprint is Dilma-era capex (US$10.8bn/yr, 28% of revenue). That was a super-cycle project pipeline approved before 2011.
6. **For 25 Oct, the run-off matters to Vale mainly through the Brazil factor (beta about 0.5) and China relations, not through interference.**
   - My judgement is that a Flávio win is mildly positive for Vale: about +5 to +10% from a Brazil re-rating, minus some China-relations risk. That is well under half of what it means for Petrobras or the Ibovespa.
   - A Lula IV win is mildly negative: about -3 to -8%, mostly through Brazil's fiscal risk premium plus some board-interference noise.
   - Iron ore and China will matter more for Vale than either outcome. A US$10/t move in iron ore is worth about US$0.9bn/yr of dividends.

Note how 2026 has gone so far: Vale's ADR is up **+7.5%** year to date, against **+38.4%** for EWZ (Yahoo adjclose, to 2026-10-09). This year's Brazil rally, which is partly an election rally, has largely passed Vale by.

---

## Data and sources

| What | series_id | source | last obs |
|---|---|---|---|
| Vale USD total return (cross-check) | `total_return_usd@VALE` | Derived from B3 (warehouse) | 2026-10-02 |
| Ibovespa USD total return | `total_return_usd@IBOV` | Derived (warehouse) | 2026-10-01 |
| Petrobras USD total return | `total_return_usd@PETR` | Derived (warehouse) | 2026-10-02 |
| Fundamentals | `v_company_quarterly` (VALE, PETR) | CVM | 2026-06-30 |
| FX | `brl_usd` | Banco Central (SGS) | 2026-10-02 |
| Dividend yield | `dividend_yield_ttm@VALE` | Derived (warehouse) | 2026-10-02 |
| Brazil iron ore exports | `iron_ore_exports`, `iron_ore_exports_kg`, `iron_ore_unit_value` | ComexStat (MDIC) | 2026-08-01 |
| China share of exports | `china_export_share` | Derived from ComexStat | 2026-08-01 |
| Daily adjusted closes, USD (VALE, PBR, BHP, RIO, EWZ, SPY, XOM) | `yahoo:<ticker>` | Yahoo Finance (external, `data/`) | 2026-10-09 |
| Iron ore CFR China, monthly average | `fred:PIORECRUSDM` | IMF via FRED (external) | 2026-07-01 |
| Brent, monthly average | `fred:POILBREUSDM` | IMF via FRED (external) | 2026-07-01 |

**Why external data was needed.** The warehouse's Vale price history starts in 2012. That would leave out Lula I–II, the 2002–2010 elections and the 2011 Agnelli episode. The warehouse also has no benchmark iron ore price, only Brazil's export unit value from 2014.

**Cross-check.** Monthly Yahoo VALE ADR returns correlate **0.995** with `total_return_usd@VALE` over 176 overlapping months. The mean difference is -0.05 pp/yr.

**Terms** (defined here, not taken from `v_politics`):

| Term | Lean | Months |
|---|---|---|
| FHC | right | Apr–Dec 2002 only; reported but excluded from tests |
| Lula I–II | left | 2003-01 to 2010-12 |
| Dilma | left | 2011-01 to 2016-08 |
| Temer | right | 2016-09 to 2018-12 |
| Bolsonaro | right | 2019-01 to 2022-12 |
| Lula III | left | 2023-01 to 2026-09 |

SQL used against the warehouse, read-only:
```sql
SELECT date, value FROM v_observations WHERE series_id = 'total_return_usd@VALE' AND date <= current_date ORDER BY date;
-- same pattern for total_return_usd@IBOV, total_return_usd@PETR, brl_usd, dividend_yield_ttm@VALE,
-- iron_ore_exports, iron_ore_exports_kg (unit: thousand_tonnes), iron_ore_unit_value, china_export_share
SELECT * FROM v_company_quarterly WHERE entity_id IN ('VALE','PETR') ORDER BY quarter_end;   -- values in R$ bn
SELECT series_id, title, source, freq, first_date, last_date FROM v_search
 WHERE series_id ILIKE '%VALE%' OR title ILIKE '%iron%' OR title ILIKE '%china%';
```

---

## Q1. Shareholder returns by term

Returns are monthly log returns in USD, with dividends reinvested (VALE ADR). The full-sample factor model, 2002-05 to 2026-07 (n = 292), is:

- r_VALE = -0.0013 + 0.12·Δiron + 1.04·miners, R² = 0.645.
- The iron ore price on its own explains little (R² 0.048). The IMF series is a monthly average, so it lags the market. A one-month lead of iron ore adds explanatory power, and the residual gap barely moves (-4.5 pp/yr).
- Annually, 2003–2025, Vale correlates 0.93 with the miners, 0.92 with EWZ and only 0.23 with the iron ore average.

**Returns by term** (source: `term_returns.csv`; alpha is the model residual in pp/yr, with the intercept included)

| Term | Lean | Months | Vale %/yr | EWZ %/yr | Iron ore %/yr (avg $/t) | Vale − EWZ | α iron only | **α iron + miners** | α iron + miners + EWZ | Vale − Ibov (warehouse, 2012+) |
|---|---|---|---|---|---|---|---|---|---|---|
| Lula I–II | L | 96 | +43.4 | +36.6 | +38.2 (52) | +4.9 | +27.0 | **+6.7** | +0.3 | – |
| Dilma | L | 68 | -24.8 | -11.4 | -16.4 (110) | -16.5 | -23.5 | **-12.5** | -11.2 | -14.4 |
| Temer | R | 28 | +54.0 | +8.7 | +5.5 (70) | +34.9 | +41.7 | **+16.9** | +20.8 | +33.1 |
| Bolsonaro | R | 48 | +15.5 | -1.5 | +12.8 (120) | +15.9 | +11.0 | **-6.6** | -0.2 | +16.2 |
| Lula III | L | 45 | +2.4 | +13.8 | -2.5 (111) | -10.6 | +5.7 | **-9.0** | -10.5 | -11.8 |

**Left-minus-right tests** (pp/yr; months 2003-01 to 2026-09)

| Measure | Gap L−R | 90% CI (block) | p (block null) | p (term permutation, 10 perms) |
|---|---|---|---|---|
| **Vale α, iron + miners (primary)** | **-4.9** | -20.8 to +11.9 | 0.61 | 0.70 |
| Vale α, iron only | -16.3 | -45.4 to +12.1 | 0.41 | 0.70 |
| Vale α, iron + miners + EWZ | -13.2 | -28.5 to +3.4 | 0.10 | 0.20 |
| Vale − EWZ, raw | -28.3 | -51.5 to -6.0 | 0.016 | 0.10 (lowest possible) |
| Vale raw | -17.2 | -48.8 to +13.2 | 0.44 | 0.70 |
| EWZ raw | +11.1 | -9.2 to +31.9 | 0.48 | 0.70 |
| Petrobras α, Brent + XOM | +1.4 | -20.4 to +22.9 | 0.93 | 1.00 |
| *Exploratory:* Vale α iron + miners, excluding the Nov-2015 and Jan-2019 dam months | -7.6 | -21.8 to +6.7 | 0.41 | – |

**How to read this**

- **H1 is not supported, as expected.** Once Vale is priced against the global miners, the left-vs-right gap is -5 pp/yr. That is small relative to the noise, and it rests on five terms.
- **Vale does lag Brazil (EWZ) badly under the left, but that mostly says something about EWZ.** The -28 pp/yr gap against EWZ is the only result with p < 0.05 on the block bootstrap. It is a gap between a global stock and a domestic index. Under Temer and Bolsonaro the miners boomed while Brazil's domestic market went nowhere (EWZ +8.7 and -1.5 %/yr). Under Lula III the reverse happened: Brazil +13.8 %/yr, iron ore flat.
- **Even the best-controlled model hangs on two terms.** With iron, miners and EWZ, the gap is -13 pp/yr (p 0.10). It is driven by Temer (+21, which covers the 2017 shareholder-agreement and Novo Mercado reform) and by Dilma (-11, which covers the China slowdown and the Mariana collapse). Lula I–II shows about zero (+0.3). Treat it as suggestive at most.
- **Bolsonaro's term carries Brumadinho** (Jan 2019, -31% in 2 days). Excluding the disaster months moves Bolsonaro's alpha from -6.6 to -1.7. Lula III's -9.0 pp/yr is unchanged; it is weighed down by the 2024 succession saga and a Q4-2025 net loss of R$21.0bn (CVM; the cause was not investigated here).

Chart: `charts/vale_vs_iron_ore_by_term.html`, `charts/term_alphas_vale_vs_petrobras.html`

---

## Q2. Event study

Method:
- Daily USD log returns. Day 0 is the first NYSE session on or after the event (the Monday after a Sunday election).
- Market model estimated on [-260,-30]. The primary model is Vale against the miners plus EWZ (M2). M1 swaps EWZ for the S&P 500, so it keeps the Brazil-wide move in the abnormal return.
- Deviation from the pre-registration: the 2002 estimation window is about 150 days, because the VALE ADR listed in Mar-2002.
- Placebo: 1,000 random days (seed 7), excluding ±10 days around events. Vale's M2 placebo SD of CAR[0,+1] is 1.95%, with a 5–95% range of -3.0 to +3.2%.

**CAR[0,+1] in %** (source: `event_study.csv`; t-stat in parentheses; pct = percentile against placebo)

| Event | Vale vs miners+EWZ | Vale vs miners+SPY | Petrobras vs XOM+EWZ | Petrobras vs XOM+SPY | EWZ vs SPY |
|---|---|---|---|---|---|
| 2002 run-off, Lula wins | +0.8 | -1.1 | -4.3 (2.8 pct) | -8.3 | -4.9 (2.4 pct) |
| 2006 run-off, Lula re-elected | -0.7 | -0.6 | -0.5 | -0.1 | +0.6 |
| 2010 run-off, Dilma wins | -0.4 | +0.6 | -0.4 | +0.9 | +1.7 |
| 2014 run-off, Dilma re-elected | **-4.7 (t -3.0; 1.3 pct)** | -5.1 | **-9.2 (t -4.4)** | -11.0 | -1.6 |
| 2018 run-off, Bolsonaro wins | **-4.9 (t -3.0; 1.1 pct)** | -4.6 | -0.8 | -0.4 | +0.3 (EWZ +30% in the 20 prior days) |
| 2022 run-off, Lula wins | +0.6 | +1.6 | **-8.9 (t -3.6)** | -3.8 | +6.0 |
| **2026 first round, Flávio leads** | **-4.7 (1.2 pct)** | **+1.25 (73.6 pct)** | +2.3 | **+8.9 (t 3.7)** | **+10.7 (t 5.4)** |
| E1 Agnelli ouster agreed, 2011-04-01 | -1.5 (18 pct); run-up [-20,-1] **-7.2** | 0.0 | -0.1 | +1.9 | +2.3 |
| E2 Bloomberg: Lula pushes Mantega, 2024-01-20 | +1.4 | +1.1 | +0.6 | +0.1 | -0.6 |
| E3 Bartolomeo extended / Penido resigns, 2024-03-11* | **-2.7 (6.7 pct)** | -2.2 | +0.8 | +1.0 | -0.3 |
| E4 Pimenta named CEO, 2024-08-26 | **+3.1 (94.5 pct)** | +3.1 | +5.9 | +6.5 | +1.0 |
| E5 Mariana R$170bn settlement, 2024-10-25 | **+3.2 (94.7 pct)** | +3.0 | +0.2 | +0.7 | +0.6 |
| Benchmark: Mariana collapse, 2015-11-05 | -2.5 | +0.3 | – | – | – |
| Benchmark: Brumadinho, 2019-01-25 | **-31.4 (t -18)** | -33.1 | -1.2 | -2.9 | -1.8 |

\*E3's date comes from memory and was not re-verified this session (see `external_facts.csv`).

The 2026 event runs through day 4 (9 Oct): Vale -1.3% against miners+SPY and -8.2% against miners+EWZ; EWZ +12.0%; Petrobras +12.9% against XOM+SPY.

**Aggregate tests** (pre-registered; placebo p is the share of random means at or below the observed)

| Statistic | Vale | Petrobras | EWZ |
|---|---|---|---|
| Mean CAR[0,+1], 5 left wins | -0.85% (p 0.16) | **-4.67% (p 0.001)** | +0.35% (p 0.63) |
| CAR[0,+1], 2018 right win | -4.9% | -0.8% | +0.3% |
| Mean CAR[0,+1], interference E1–E3 | -0.91% (p 0.19) | – | – |

**How to read this**

- **H2 is partly rejected.** Left wins have hurt Petrobras consistently: 2002, 2014 and 2022 were each -4 to -9% abnormal. They have barely touched Vale. The two significant Vale moves, 2014 and 2018, went in the same direction for a left and a right winner. That points to noise or iron-ore news, not partisanship.
- **The 2026 first round is the cleanest test.** Brazil re-rated by +10.7% in two days. Vale moved only about as much as the global miners. Petrobras, a state-controlled company, captured most of the Brazil move.
- **H3 is weakly supported and not significant.** Interference shows up as a slow bleed rather than a jump: -7.2% abnormal in the 20 days before Agnelli's exit as pressure leaked, and -2.7% on E3. Markets rewarded the board for resisting, with +3.1% on the Pimenta appointment. Settling legal overhangs with the government was also positive (Mariana, +3.2%).

Chart: `charts/event_cars.html`

---

## Q3. Fundamentals by term (CVM 2012Q1–2026Q2, converted to USD at the quarterly-average `brl_usd`)

**Averages by term** (source: `fundamentals_by_term.csv`; years assigned by majority of months; 2012–2016 counted as Dilma)

| Term (years) | Iron ore $/t | Dividends paid US$bn/yr | Capex US$bn/yr | Capex/revenue | EBIT margin | ND/EBIT | Brazil iron ore exports, Mt/yr (ComexStat) | Avg TTM dividend yield |
|---|---|---|---|---|---|---|---|---|
| Dilma (2012–16) | 95 | 3.3 | **10.8** | **28%** | 14% | 2.8x | 327 (2014–16) | 6.5% |
| Temer (2017–18) | 71 | 2.4 | 3.8 | 11% | 32% | 1.3x | 354 | 2.6% |
| Bolsonaro (2019–22) | 120 | 6.0 | 4.7 | 11% | 29% | 3.3x (2019: 12.5x, Brumadinho) | 329 | 7.8% |
| Lula III (2023–25) | 112 | 4.4 | 6.1 | 16% | 25% | 1.3x | **369** (record 392 Mt in 2025) | **8.7%** |

**What iron ore explains** (annual regression on iron ore, 2012–2025; residuals by term)

| Metric | Slope per +US$10/t | R² | L−R residual | Residual SD |
|---|---|---|---|---|
| Dividends paid (US$bn) | **+0.91** | **0.66** | -0.93 | 1.90 |
| Capex (US$bn) | +0.43 | 0.11 | +4.75 (Dilma +4.0) | 3.5 |
| EBIT margin (pp) | +3.2 | 0.28 | -11.1 | 14.9 |
| Net debt (US$bn) | -1.14 | 0.15 | +11.7 (Dilma +9.6) | 8.1 |
| Dividends/EBIT (pp) | +4.0 | 0.38 | **+9.0** (left pays out more) | 13.9 |

Payout as a share of net income is reported in `results.json` but is not meaningful here: 2013–14 net income was close to zero, which pushes payout above 700%.

**How to read this**

- **H4 is mostly supported.** Dividends are an iron ore story. Two-thirds of their annual variance is explained by the price.
- **Lula III has not squeezed shareholders.** Its dividend yield (8.7%) is the highest of any term, and dividends/EBIT is above what the iron ore price would predict.
- **The one "left" signature is Dilma-era capex and net debt.** It was the tail of the super-cycle build-out (S11D and others) planned around 2011. In 2016–17 it gave way to capital discipline under the 2017 governance reform. With one term per regime, that cannot be separated from the commodity cycle.
- **Volumes have been rising under Lula III.** Brazil's iron ore exports set a record in 2025 (392 Mt). Jan–Aug 2026 shipments are 244.6 Mt against 249.8 Mt a year earlier, and export value is US$16.0bn against US$16.3bn (`iron_ore_exports`, `iron_ore_exports_kg`, ComexStat, to 2026-08).
- **2026 H1** (CVM to 2026-06-30): dividends US$2.75bn, capex US$2.43bn, net income US$3.25bn, net debt US$13.5bn.

Chart: `charts/fundamentals.html`

---

## Q4. Contrast with Petrobras: how much "Brazil risk" is in Vale?

| Monthly USD returns 2002–2026 | Vale | Petrobras |
|---|---|---|
| R², global commodity factors (Vale: iron + miners; PBR: Brent + XOM) | **0.645** | 0.263 |
| R², EWZ alone | 0.521 | 0.725 |
| R², global + EWZ | 0.731 | 0.743 |
| Extra R² from a **pure Brazil factor** (EWZ orthogonalised to S&P, iron ore, Brent) | **0.092** | **0.411** |
| Beta to the pure Brazil factor | **0.50** | **1.20** |
| Left − right gap, α after global factors (pp/yr) | -4.9 (p 0.61) | +1.4 (p 0.93) |
| Mean CAR[0,+1] at left election wins | -0.85% | -4.67% |
| CAR[0,+1] at the 2026 first round (vs global + S&P) | +1.25% | +8.9% |

**Beta to the pure Brazil factor, by term**

| Company | Lula I–II | Dilma | Temer | Bolsonaro | Lula III |
|---|---|---|---|---|---|
| Vale | 0.67 | 0.51 | 0.31 | 0.48 | 0.43 |
| Petrobras | 1.15 | 1.71 | 1.25 | 1.28 | 0.71 |

**How to read this.** Vale is the natural experiment for a privatised commodity champion. About 65% of its monthly variance is global and about 9% is Brazil-specific; for Petrobras it is 26% and 41%. Vale's exposure to Brazil risk fell after the 2017 reform: it was 0.67 under Lula I–II and has been 0.3–0.5 since. Its political-risk premium works mostly through:

1. the general Brazil discount (cost of capital, BRL), at roughly half of Petrobras's beta;
2. occasional, short-lived governance scares worth a few percent;
3. lumpy legal and regulatory settlements with the state, such as Mariana and the railway concessions.

None of these shows a partisan pattern in the returns. One caveat on the contrast: Petrobras's term alphas do not show a left–right gap either (+1.4 pp/yr). Its political sensitivity shows up in discrete repricings on election days and in its Brazil beta, not in average returns per term. The parallel Petrobras study covers this in depth.

---

## Q5. October 2026 scenarios (JUDGEMENT, clearly separated from the measured results)

**Anchors from the data**

| Anchor | Value |
|---|---|
| Vale beta to the pure Brazil factor | 0.5 |
| Brazil re-rating on the first-round result (EWZ vs S&P, CAR[0,+1]) | +10.7% |
| Vale's move on the same event | about +1% against miners |
| Interference events | -1.5% to -2.7% each, short-lived |
| Board resisting interference | +3.1% |
| Dividends per US$10/t of iron ore | about +US$0.9bn/yr |
| Iron ore price | US$101.6/t in Jul-2026 (`fred:PIORECRUSDM`); 2025 average US$103.7 |
| Brazil iron ore exports | US$26.3bn in 2025 (`iron_ore_exports`) |
| China's share of Brazil's exports | 25.2% in Aug-2026, 28.5% average in 2025 (`china_export_share`) |

**External context** (`external_facts.csv`)

- Iron ore was exempted from the 2025 US tariff add-on. The 2026 Section 301 action covers most goods but exempts energy and pig iron. The US is not a material iron ore market for Vale, so US relations reach Vale indirectly, through the BRL and the Brazil risk premium.
- CFEM on iron ore is 3.5% of gross sales net of sales taxes (Lei 13.540/2017).
- Flávio promises "pragmatic" relations with China, but would "reevaluate" BRICS membership and names the US, Argentina and Israel as main partners. Lula hosted Xi in Nov 2024 and signed 37 agreements.
- JPMorgan sees Brazilian equities +50% in a fiscal-adjustment (Flávio) case and -21% in a deterioration case.

| Channel | Lula IV, best | Lula IV, worst | Flávio, best | Flávio, worst |
|---|---|---|---|---|
| Brazil factor (beta about 0.5) | Credible fiscal path, so Brazil is roughly flat: Vale about 0% | Fiscal slippage, Brazil -15 to -20%: Vale **-7 to -10%** | Fiscal-adjustment rally (Brazil +20 to +40%): Vale **+10 to +20%** | Rally fades, institutional conflict (amnesty, STF): Vale about 0% |
| Interference / governance | No repeat of 2024; Pimenta stays: 0% | New push on the board or CEO via Previ and allied directors, as in 2011 and 2024: **-3 to -7%**, short-lived | Hands-off: 0 to +2% | Little risk; right governments have not pressured Vale (no such event in the sample) |
| Royalties, taxes (CFEM, export levy, Imposto Seletivo on extraction) | Status quo at 3.5% | CFEM raised or an export levy on ore to fund the budget: each +1 pp of CFEM is roughly US$0.2–0.26bn/yr sector-wide at 2025 export values; capitalised at about 10x, that is a few percent of Vale's market value per point (judgement; Vale's share count is not in the warehouse) | Status quo or lower | Status quo |
| Settlements and concessions (Mariana, railways) | Agreements in place; low new risk | Reopening of concession terms or new environmental claims | Faster licensing | Little change |
| China (main buyer of iron ore) | Close ties (Xi 2024, BRICS): neutral to slightly positive | – | Pragmatic trade continues: neutral | Anti-BRICS rhetoric, Pix/UnionPay restrictions and US alignment cool ties. Ore buying is driven by price and quality, so I expect sentiment effects, not volumes: -2 to -5% |
| US relations | Tariff conflict persists, but iron ore is exempt; indirect via BRL | – | Tariff relief helps the BRL and Brazil; neutral for ore | – |
| **Net for Vale (judgement)** | **about 0%** | **-8 to -15%** | **+8 to +18%** | **-2 to -5%** |

**Bottom line (judgement)**

- Under either winner, Vale's political range is roughly **±10–15%**. Petrobras and the Ibovespa face much wider ranges.
- The election is not the main risk for Vale. Iron ore (China steel demand) and dam and legal risk matter more. A US$20/t fall in iron ore would cut about US$1.8bn/yr of dividends, more than any plausible policy change.
- If Flávio wins, expect Vale to underperform the Brazil rally again, as it has in 2026 year to date (+7.5% against EWZ +38.4%) and as it did on 5 Oct.
- If Lula wins, the specific Vale risk to watch is a renewed push on board seats or the CEO. The 2024 Mantega attempt failed because the 2021 corporation structure held. Previ's 8.09% stake and the golden share are the levers to monitor.

---

## Caveats

- **Few terms.** There are five full terms and only two on the right, so the term-label permutation cannot go below p = 0.10. Terms are confounded with the 2003–11 commodity super-cycle (Lula I–II), the 2014–15 China slowdown plus Mariana (Dilma), the 2017 governance reform (Temer), and Brumadinho plus COVID (Bolsonaro). Everything in Q1 and Q3 is descriptive.
- **Timing of the iron ore series.** The IMF series is a monthly average, so it lags price moves. The global-miner factor (BHP, RIO) absorbs most iron ore and China news. Since BHP and RIO are themselves iron ore miners, "after miners" partly means "relative to peers".
- **2026 event window.** Only 5 trading days after the first round are available (to 2026-10-09). The pre-registered [0,+5] window was replaced by [0,+4].
- **Benchmark contains Vale.** EWZ includes Vale (roughly 10–15%) and Petrobras, so the M2 models slightly understate both companies' Brazil sensitivity.
- **Fundamentals.** CVM data starts in 2012. Production and C1 cost are not in the warehouse; Brazil-wide ComexStat export tonnage is used as a volume proxy, and Vale is the dominant but not the only exporter. Iron ore exports to China specifically are not in the warehouse.
- **External facts.** The E3 date (Bartolomeo extension and Penido resignation, Mar 2024) and the railway renegotiation amount (about R$11bn, Dec 2024) are from memory. They were not re-verified because the web-search budget was exhausted, and are flagged UNVERIFIED in `external_facts.csv`. The railway event was therefore left out of the event study. Agnelli's day 0 (2011-04-01) is approximate; the 20-day run-up window covers the March 2011 leaks.
- **Exploratory analyses.** The ex-disaster robustness check, the per-term Brazil betas and the annual correlations were not pre-registered.
