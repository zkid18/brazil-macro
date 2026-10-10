# Brazil research, Oct 2026: summary of all seven studies

Data comes from the Brazil Monitoring warehouse: monthly series through 2026-08, daily through 2026-10-02. Facts from outside the warehouse are logged with URLs in each study's `external_facts.csv` (one level up). Each study was planned and pre-registered by Fable, then executed by Opus.

**Reading order:** this file, then the `0X_*.md` reports, then `charts/`. Charts are named `0X_study__chart.html`; open them in a browser.

---

## The big picture in five lines
1. **Commodity prices drive Brazil.** Terms of trade (export prices relative to import prices) is the only significant driver of GDP-per-capita growth. It also moves stocks, the real and exports more than any president, Congress or drought does.
2. **Brazil's physical endowment is real, but since 2010 it hasn't turned into income or returns.** GDP per capita grew 0.7%/yr in 2010–25. Brazilian equities in USD are still below their 2010 level.
3. **Left vs right matters for social outcomes and policy instruments, not for growth or markets:**
   - unemployment, minimum wage, inequality and poverty favour the left;
   - real rates and primary balance also differ by lean.
4. **The PT is less left than its reputation in economic policy and more distinctive in foreign policy.**
5. **The candidate in the 25 Oct run-off changes who carries the export risk, not how big it is.** Flávio's upside is concentrated in the US; his tail risks sit in China, the EU and the Gulf. Lula keeps China and the EU but faces continued US pressure.

---

## 01 Davidson, "Brazil is the New America" (`01_davidson.md`)
- **Verdict:** holds for the physical side. Institutions are split. Returns were not delivered.
- **Physical side up:**
  - Oil output rose from 2.1 to 4.6m barrels/day between 2010 and 2026.
  - Wind and solar went from 5% to 30% of power generation.
  - Water withdrawals are about 1.2% of renewable freshwater.
- **Income and returns did not follow:**
  - GDP per capita grew 2.6%/yr in 2000–10 and only 0.7%/yr in 2010–25.
  - The USD equity index stood at 104.9 in 2010 and 75.9 in 2025.
- **Governance scores worsened.** Corruption control fell from −0.02 to −0.41, and the drops coincide with the Mensalão and Lava Jato investigations. **Social institutions improved strongly:**
  - poverty at $6.85/day fell from 56% to 21%;
  - infant mortality fell from 29 to 12 per 1,000;
  - Gini fell from 59 to 50.
- **The high real rate binds credit only after 2010.** The correlation with household credit is ρ −0.49 at a 7–10 month lag.
- **Equities and commodities:** Ibovespa's beta to commodities is 0.29, but domestic Itaú has the same beta. The equity market behaves like global risk appetite, not a commodity hedge.
- **Facts in the original note that were wrong:**
  - credit/GDP in 2008 was 39.7%, not 30%;
  - inflation in Apr 2026 was 4.4%, not 5–6%;
  - the 2021 drought was not the worst on national reservoir data.
- **AI raw materials:** the AI-relevant exports are small (niobium is 0.8% of exports). Exports to China are mostly soy, oil and iron ore.

## 02 Left vs right presidents, 1985–2026 (`02_politics.md`)
- **Terms of trade explain more than lean:**

  | Outcome | Lean | Terms of trade |
  |---|---|---|
  | Median across metrics | 0.09 | 0.26 |
  | Equities | 0.02 | 0.88 |
  | Real (BRL) | 0.14 | 0.80 |

- **Left minus right:**
  - unemployment −2.4 pp;
  - real minimum wage +3.1%/yr;
  - poverty −0.9 pp/yr;
  - distribution composite +0.92 SD; every left term scores above every right term.
- **No lean difference in:** health, safety, governance scores (WGI), debt or inflation.
- **Market reaction after elections:** Ibovespa +19% after right-wing transitions vs −4% after left wins. All right-wing transitions belong to one 2016–19 episode, so treat this cautiously.
- **2027–30 ranges for growth:** Lula IV 2.5–3.8% (probably optimistic), Flávio 1.1–2.4%; the market (Focus survey) expects 1.4%. Debt reaches about 93–108% of GDP either way.
- **Caveat:** only 3 left and 4 right terms, so nothing survives multiple-testing correction.

## 03 Exports under Lula IV vs Flávio (`03_exports.md`)
- **The 2025 US tariff cost** about −$7.9bn/yr (upper bound). Net of exports diverted to other buyers it was about −$4.4bn/yr. The placebo test isn't significant (p 0.23).
- **The China "+19%" headline is mostly a base effect:** against two years earlier, exports to China rose only +4%.
- **The destination mix did not move with the president:** China / US / EU shares were 29.5 / 11.5 / 13.9% under Bolsonaro and 29.4 / 10.9 / 14.2% under Lula III.
- **Scenarios, in US$bn per year:**

  | | Best | Worst |
  |---|---|---|
  | Lula | +7 to +20 | −21 to −6 |
  | Flávio | +5 to +18 | −27 to −6 (China coercion tail) |

- **Commodities dominate.** A ±10% move in terms of trade shifts exports by ±$14–22bn, more than any candidate cell.
- **New facts:**
  - the US Supreme Court voided the IEEPA tariffs; today's US tariffs are Section 301 (25%) plus 12.5% and cover only $6.6bn of goods;
  - EU–Mercosur has applied provisionally since 1 May 2026;
  - China's beef quota is now binding;
  - the EU suspended Brazilian meat from 3 Sep 2026.

## 04 Congress (`04_congress.md`)
- **2027 Congress:**
  - Chamber: PL 121 seats, the least fragmented since 2002;
  - Senate: PL 28 seats, a record.
- **Under Flávio:**
  - constitutional amendments (PECs) can pass without the MDB (342 deputies vs 308 needed, 55 senators vs 49);
  - his vetoes would be strong.
- **Under Lula:**
  - PECs need almost the whole centrão;
  - his vetoes are weak (41 senators can override without the centrão).
- **Alignment between president and Congress shows little effect on fiscal outcomes, rates or vote success.** The government wins about 75% of votes regardless. The one exception is investment, which is higher with alignment (ρ +0.64).
- **The trend is Congress gaining power over time:**
  - MP conversion fell from 81% to 23%;
  - veto overrides rose from 5% to 49%;
  - parliamentary amendments (emendas) went from R$11.7bn (2019) to R$43.5bn (2025) to R$61.4bn (2026 budget), about a fifth of discretionary spending.
- **Links to foreign policy:**
  - the main link to the US is the amnesty/dosimetria bill. Congress overrode Lula's veto in Apr 2026, and Moraes suspended the law;
  - the trade deals (EU, EFTA, Singapore) are already ratified;
  - environmental veto overrides feed the EU's EUDR deforestation-rule risk.
- **Most likely scenarios:**
  - Flávio with an aligned Congress: 10-year real yield (NTN-B) 5.5–6.8%, debt in 2030 85–95% of GDP;
  - Lula with a transactional Congress: NTN-B 7.0–8.5%, debt 98–107%.

## 05 Drought → power cost → inflation (`05_hydro.md`)
- **Power prices:** the system marginal cost of power (CMO) is 3.5x higher in drought months. Wind and solar have not yet significantly reduced that sensitivity, and the system hasn't been tested below 40% reservoir storage since 2022.
- **Prices and policy:** drought raises administered prices by about 3 pp over 12 months; electricity added about 1.1 pp to IPCA in 2021. Inflation expectations rise less than 0.3 pp, and the Selic barely reacts unless oil prices rise too.
- **Climate:** it is getting drier and hotter. Six of the seven driest years since 1990 fell in 2012–2023.
- **Data centres:** no visible load from data centres yet. The 2023–24 jump in load is mostly a measurement change.
- **Fire years:** they follow El Niño. A very strong El Niño is building for 2026–27, and 2027 would be the first year of the EUDR, so the EU-access risk rises.
- **Scenarios:**

  | | Inflation | Selic | GDP |
  |---|---|---|---|
  | Worst (rationing) | +2 to +3.5 pp | +100 to +300 bp | −1 to −2.5 |
  | Severe drought | about the same as a −10% terms-of-trade shock | | |

  For exports, terms of trade still dominate.

## 06 How left is the PT? (`06_pt_liberalism.md`)
- **Economic liberalism index:** PT minus non-PT is **+0.26 z**, so the PT was slightly *more* liberal. On foreign policy the gap is **+0.87 z**, where the PT is clearly more progressive.
- **Lula I (Palocci):** the most orthodox regime of all, with a 3.6% primary surplus and debt falling.
- **Lula III compared with Lula I:**
  - looser fiscal policy: −0.9% primary balance, debt rising 3 pts/yr;
  - tighter monetary policy, coming from the now-autonomous central bank (a Bolsonaro-era law), which Lula attacked;
  - more state-firm intervention: Petrobras, the NIB industrial policy, diesel subsidies.
- **Where the PT is to the left:**
  - redistribution: minimum wage, Bolsa Família;
  - state-firm and price intervention;
  - BNDES lending flows;
  - local-content rules and anti-dumping;
  - foreign policy.

  The left does **not** show in fiscal or monetary policy.
- **Dilma's Nova Matriz is the PT outlier.** Bolsonaro's interventionism (2022 fuel-tax cuts) is as strong as the PT's worst.
- **Rhetoric vs action:** PT rhetoric is left and its action centre-right (−0.63 z vs +0.44 z).
- **The Fraser and Heritage indices disagree on rankings**, though they also place the PT at or above non-PT on levels.

## 07 US tariffs under Lula III, deep dive (`07_us_tariffs.md`)
- **Timeline.**
  - From 2025-08-06: 40% + 10% on about 34% of US-bound exports.
  - Nov 2025: food relief cut the covered share to 22%.
  - 2026-02-20: the Supreme Court voided the IEEPA tariffs; a 10% stopgap applied to all countries.
  - Since Jul 2026: Section 301 25% + 12.5% on about 16% of US-bound exports.
  - Section 232 (steel and similar, applied to all countries) has covered about 25% throughout.
- **Damage was real but small nationally.** Lines at the full rate lost 35–44% of their US sales. In total that is about **$4.5bn/yr gross and $2.4bn/yr net of diversion (0.11% of GDP)**. This replaces the exports study's $7.9bn upper bound. No single product lost more than $0.5bn.
- **The hit was local.** Wood, sugar, footwear and machinery took it, with SP, SC, MG, RS and PR carrying 72%. There is no employment signal.
- **Who paid.** Brazil did not cut its prices, so US buyers paid the duty (about $4.6bn/yr) and switched suppliers. Brazil lost volume. The Nov-2025 relief went exactly to the lines salient in the US consumer price index (coffee, beef; p = 0.005).
- **Markets mostly ignored it.** The real, the Ibovespa and NTN-B real yields showed nothing unusual on tariff dates. Embraer was the exception: −11.7% on the threat letter, +18.7% when aircraft were exempted.
- **The 2025 fall was the tariff after all.** It was not crude and steel; lines taxed at 40% explain 72% of the year-on-year decline.
- **Escalation ladder** (Brazil's net loss; probabilities are judgement, Lula IV / Flávio):

  | Rung | Net loss | Probability |
  |---|---|---|
  | (b) 301 raised to 50–100% | $0.6bn | 20% / 5% |
  | (c) exemptions removed (coffee, OJ, pig iron, aircraft) | $3.7bn (up to $12bn), 0.17% GDP; US import prices for coffee +8%, pig iron +25% | 15% / 3% |
  | (d) "total" regime + financial sanctions | $13.7bn trade (0.6% GDP), about 2.6% GDP with finance; BRL could fall 10–38% | 5% / 1% |
  | (e) de-escalation deal | +$1.2bn | 20% / 56% |

- **Key dates.**
  - Graham Act Russian-oil list on 2026-10-18. Brazil is not a top-5 crude/gas buyer, so low risk.
  - Aircraft-232 deadline around 2027-01-05, the Embraer risk.
  - Amnesty, the main political trigger.
- **Caveats.** The Jul-2026 regime has only 2 months of data. Two annexes had to be inferred. There are no Census realised-duty data. No web searches were left, so the rung (d) analogues are unverified.

---

## Caveats across all seven studies
- **Small samples:** 7–13 presidential terms or regimes per study. These are effect sizes with uncertainty bands, and almost nothing survives multiple-testing correction.
- **Association, not causation.** Terms of trade, the global cycle and inherited conditions confound everything.
- **The warehouse is Brazil-only**, so there is no US or peer-country comparison.
- **Web-search budget ran out in later studies.** A few external facts are low-confidence or unverified; they are flagged in `external_facts.csv`.

## Where everything else lives
`../<study>/` holds each study's plan, pre-registration, script, CSVs and `external_facts.csv`. Raw downloads are git-ignored.
