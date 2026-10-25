# Plan: US tariffs on Brazil under Lula III — what they did, and what escalation would do

Executor: an Opus agent. Reuse the conventions of the earlier studies verbatim: anchors reproduced first (stop on mismatch), `preregistration.txt` written before any result, numpy-only estimators (OLS by `np.linalg.lstsq`, block/cluster bootstrap, permutation and placebo p-values, seed 0), Plotly HTML only, every warehouse number emitted as `{value, series_id, source, last_date, sql}`, external facts fenced in `external_facts.csv` with URLs and access dates. Subagents cannot write `.md`: write `report.txt` and paste the report into the final message.

Paths:
- Warehouse (read-only): `/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb`
- Python: `/Users/zkid18/proj-personal/brazil-macro/.venv/bin/python` (duckdb, pandas, numpy, plotly; no scipy, no openpyxl, no requests, no PDF libs). `/opt/homebrew/bin/pdftotext` exists and is needed (§1.5).
- Executor dir (create): `/Users/zkid18/proj-personal/brazil-macro/research/2026-10-elections/us_tariffs/` with `cache/` (add `us_tariffs/cache/` to `/Users/zkid18/proj-personal/brazil-macro/research/2026-10-elections/.gitignore`).
- Prior work to reuse, not redo: `exports/report.md`, `exports/results.json` (keys `anchor.*`, `tariff.placebo`, `tariff.recovery`, `diversion`, `elasticity.*`), `exports/external_facts.csv` (A01–C63), `exports/scenario_matrix.csv`, `congress/report.md` §7, `congress/congress_core.py` (event-study engine), `congress/exports_cell_modifiers.csv`.
- Charts also copied to `/Users/zkid18/proj-personal/brazil-macro/research/2026-10-elections/review/charts/` with prefix `07_us_tariffs__`.

---

## 0. What exploration found (anchors; reproduce first, stop on mismatch)

**0.1 Warehouse anchors (`v_annual`, `v_observations`, ComexStat vintage 2026-08).** `exports_to_us` annual: 2023 36.915, 2024 **40.369**, 2025 **37.682**, 2026 Jan–Aug 24.105 (US$bn). Monthly Jun-25→Aug-26 (US$bn): 3.347, 3.829, 2.845, 2.666, 2.307, 2.592, 3.412, 2.374, 2.530, 2.859, 3.158, 2.986, 3.424, 3.584, 3.190. `political_events` has one tariff row (2025-08-06). Market series available daily: `brl_usd` (→2026-10-02), `ibovespa_usd` (→2026-10-01), `gov_real_yield_10y`, `gov_nominal_yield_5y` (→2026-10-02), `focus_fx`, `focus_selic_12m`, `fx_reserves`, `brent_usd` (→2026-09-29), `share_close_adj_brl@{SUZB,VALE,PETR,PRIO,ITUB,AXIA}`; monthly `total_return_usd@SUZB`, `caged_net_hires` (national only), `ipca_*`. `embi_brazil` ends 2024-07-30 (no CDS anywhere). No Embraer, Gerdau, JBS, WEG, Tupy or CSN in the warehouse.

**0.2 ComexStat live API (tested 2026-10-06, all work).** Brazil→US by NCM-8, monthly, one call for 2023-01→2026-12: **121,957 rows, 6,282 NCMs, months 2023-01→2026-09** (September 2026 is already published; the warehouse stops at August). Sums: 2024 40.369, 2025 37.682 (match the warehouse to the dollar), 2026 Jan–Sep 27.462. Also tested: NCM×country for a filtered NCM list (coffee, 558 rows/4 months), state detail (`details:["state"]`), SH4 detail (`details:["heading"]`), state×heading annual (11,727 rows), NCM×state annual (30,663 rows), heading-list×country monthly (8 headings 2023–26: 15,699 rows, 198 countries, 4.1 MB). Imports from the US by heading: 2024 **40.65**, 2025 **45.14** US$bn. A 429 appears if calls are <~10 s apart; the existing retry loop handles it.

Top NCMs to the US, 2024 (US$bn, share of 40.369): 27090010 crude 5.831 (14.4%); 72071200 semi-finished steel 2.774 (6.9); 09011110 green coffee 1.896 (4.7); 47032900 pulp 1.552 (3.8); 72011000 pig iron 1.423 (3.5); 88024090 aircraft >15t 1.421 (3.5); 27101259 gasoline 0.997; 88023039 jets 7–15t 0.956; 02023000 frozen boneless beef 0.885; 72249000 alloy semis 0.738; 20091200 OJ NFC 0.637; 84291190 bulldozers 0.520; 84295199 loaders 0.503; 17011400 sugar 0.440; 68029990 stone 0.414; 16025000 beef preparations 0.394; 27101911 jet fuel 0.392; 28182010 alumina 0.388; 26011210 iron ore 0.387; 44091000 profiled conifer wood 0.375; 44182900 doors 0.342; 84292090 graders 0.312; 27101922 fuel oil 0.307; 85042300 transformers >10 MVA 0.306; 44123900 plywood 0.271; 15021012 tallow 0.267; 88073000 aircraft parts 0.239; 87041090 dumpers 0.237; 44071100 sawn conifer 0.228; 28046900 silicon 0.227; 20091900 other OJ 0.222; 68029390 granite 0.218; 40111000 car tyres 0.208; 84119100 turbojet parts 0.206; 33011290 orange oil 0.203; 20091100 FCOJ 0.187; 21011110 instant coffee 0.173; 85042100 transformers ≤650 kVA 0.168; 17019900 refined sugar 0.164; 72029300 ferroniobium 0.162; 22071010 ethanol 0.161; 24012030 tobacco 0.157; 35040090 proteins 0.156; 93062100 shotgun cartridges 0.153; 73042939 steel tubes 0.152. Top 45 = 70.2% of the total.

Imports from the US by SH4, 2024 (US$bn): 8411 turbines/jet engines **6.17** (15.2%), 2710 fuels 3.95, 2711 gas 2.19, 3901 polyethylene 1.57, 8802 aircraft 1.55, 2709 crude 1.45, 2701 coal 1.41, 3004 medicines 0.93, 3808 agrochemicals 0.87, 3002 blood products 0.75, 3105 fertilisers 0.56, 8708 auto parts 0.50.

**0.3 US-side mirror.** The US Census trade API now **requires a key** ("Missing Key" HTML on every call; the brief's "no key for small pulls" is wrong). USITC DataWeb needs a token (POST → 307 to login). **UN Comtrade public preview works with no key**: US (842) imports (M) from Brazil (76), monthly, available **through 2026-07**; 500 records per call, exactly one period per call, 429 at <2 s spacing (2.5 s is safe); a 40-code `cmdCode` list in one call works (38 rows); `AG2` works (92 rows); omitting `partnerCode` returns all partners (partner 0 = World). Aug-2025 coffee (0901) check: world 964.8, Colombia 218.8, Brazil 150.2, Switzerland 86.1, Mexico 72.1, Peru 52.3, Vietnam 50.3, Guatemala 49.5 (US$ mn, CIF). Jul-2026 top from Brazil: 2709 546.9, 8802 173.5, 2710 142.3, 7201 142.1, 0901 137.7, 4703 134.8.

**0.4 Primary sources without web searches.** The Federal Register API (no key) lists every relevant presidential document and USTR notice with document numbers (§3). Raw text is machine-readable for the USTR 301 notice (2,182 unique HTS-8 lines in its annex) but the annexes of EO 14323, EO 14361 and the Section 122 proclamation are **images** in the FR. The current USITC HTS Chapter 99 PDF (14 MB, `https://hts.usitc.gov/reststop/file?release=currentRelease&filename=Chapter%2099`, piped through `pdftotext -layout`) contains the lists as text: U.S. note 2(x)(iii)(a) (heading 9903.01.81, the EO 14323 Annex I as amended), 2(x)(iii)(b) (9903.01.90, the Nov-2025 relief), 2(x)(iv) civil aircraft (9903.01.82), 232 carve-out (9903.01.83), and the Section 301 Brazil note for headings 9903.05.01–.09 (2,273 codes; (a)(ii) exempt subheadings = 9903.05.03, (iii) particular articles = 9903.05.04, (iv) civil aircraft = 9903.05.05, (v) pharmaceutical uses = 9903.05.06, (vi) = 9903.05.07). `pdftotext` on the govinfo PDF of EO 14323 yields 1,446 HTS tokens; on EO 14361 and the Section 122 proclamation it yields 0 (image annexes), so use the Chapter 99 PDF for those.

Two timeline facts found in those texts that the prior study did not have: (i) the **Section 232 aircraft proclamation (signed 2026-07-09, 91 FR 43507) imposed no tariff**; it directs negotiations and allows action "if an agreement is not entered into within 180 days" (≈ 2027-01-05, four days after the inauguration) — a live escalation trigger for Embraer; (ii) the "Ensuring Affordable Beef" proclamation (signed 2026-02-06) added 80,000 t to the 2026 beef TRQ and allocated **all of it to Argentina** — the US expanded beef access and chose not to give any of it to Brazil.

**0.5 Other no-key sources tested.** BLS API v1 (no key, 25 queries/day): `CUUR0000SEFP01` Coffee, `CUUR0000SEFC` Beef and veal, `CUUR0000SEFC01` Uncooked ground beef, `CUUR0000SEFN02` Frozen noncarbonated juices and drinks, `CUUR0000SEFN03` Nonfrozen juices, `CUUR0000SA0`; PPI `WPU0121` returns data (verify its name in `wp.item`); `wp.item` codes found: 026301 Coffee, 024203 Frozen juices incl. OJ, 101702 Semifinished steel mill products, 101712 Ferroalloys. SIDRA (no key): PNAD unemployment by UF quarterly (table 4099, through 2026-Q2) and PIM-PF industrial production by UF monthly (table 8888, 2022=100, through Jul 2026). IPEAData timed out all day (CAGED by UF is not reachable). B3 COTAHIST zips are reachable (A2024 79 MB, A2025 89 MB, A2026 93 MB; Range requests work); Yahoo, stooq and brapi are blocked or need tokens — so Embraer and peers come from COTAHIST, converted to USD with `brl_usd`.

---

## 1. Data pulls: exact calls (all cached under `us_tariffs/cache/`, never into the warehouse)

### 1.1 ComexStat (`POST https://api-comexstat.mdic.gov.br/general`, headers as in `/Users/zkid18/proj-personal/brazil-macro/ingest/comexstat.py`; sleep 11 s between calls; on 429 sleep 15+5·attempt and retry; cache each response as `cache/comexstat/<name>.json` and normalise to `cache/comexstat/<name>.parquet`)

| name | body | size seen |
|---|---|---|
| `us_ncm_m` | `{"flow":"export","monthDetail":true,"period":{"from":"2023-01","to":"2026-12"},"filters":[{"filter":"country","values":["249"]}],"details":["ncm"],"metrics":["metricFOB","metricKG"]}` | 121,957 rows, 22 MB, 11 s |
| `us_heading_m` | same with `"details":["heading"]` | ~30k rows |
| `us_state_m` | same with `"details":["state"]` | ~1.3k rows |
| `us_state_heading_y` | `monthDetail:false`, period 2023-01→2026-12, `"details":["state","heading"]` | 11.7k rows / 2 yrs |
| `us_state_heading_m_top` | monthly, filters `country 249` + `heading` = top-40 list, `details:["state","heading"]` | est. 20k rows |
| `div_heading_country_m_{k}` | `{"flow":"export","monthDetail":true,"period":{"from":"2023-01","to":"2026-12"},"filters":[{"filter":"heading","values":[<10 headings>]}],"details":["heading","country"],"metrics":["metricFOB","metricKG"]}` — 4 chunks for the top-40 HS4 | ~20k rows / 5 MB each |
| `div_ncm_country_m` | monthly, filter `ncm` = the firm-specific NCM list (§4), `details:["ncm","country"]` | one call |
| `imp_us_heading_y` | `{"flow":"import","monthDetail":false,"period":{"from":"2023-01","to":"2026-12"},"filters":[{"filter":"country","values":["249"]}],"details":["heading"],"metrics":["metricFOB"]}` | 2.1k rows |
| tables | `GET /tables/countries` (281 rows; US 249, China 160), `GET /tables/uf` (34), `GET /tables/ncm` (1.8 MB; `coNcm`, `noNCM`, `unit`), `GET /tables/economic-blocks` (12) | `/tables/states` and `/tables/headings` return 500 |

Row keys: `coNcm, ncm, headingCode, heading, country (Portuguese name), state (name), year, monthNumber, metricFOB (string), metricKG (string)`. Country names are Portuguese ("Estados Unidos", "Alemanha", "Países Baixos (Holanda)"); join to `/tables/countries` for ids. The `period` is a year×month grid; `to: 2026-12` returns through the latest published month (2026-09).

Load into an in-memory DuckDB (`duckdb.connect()`), not the warehouse:
```sql
CREATE TABLE us_ncm AS
SELECT coNcm AS ncm, substr(coNcm,1,4) AS hs4, substr(coNcm,1,6) AS hs6,
       make_date(year::INT, monthNumber::INT, 1) AS ym,
       metricFOB::DOUBLE AS fob, metricKG::DOUBLE AS kg
FROM read_parquet('cache/comexstat/us_ncm_m.parquet');
-- anchor: SELECT year(ym), sum(fob)/1e9 FROM us_ncm GROUP BY 1 → 2024 40.369, 2025 37.682
CREATE TABLE div AS  -- heading × country × month, all destinations
SELECT headingCode AS hs4, country, make_date(year::INT, monthNumber::INT, 1) AS ym,
       metricFOB::DOUBLE AS fob, metricKG::DOUBLE AS kg
FROM read_parquet('cache/comexstat/div_heading_country_m_*.parquet');
```

### 1.2 UN Comtrade public preview (`GET https://comtradeapi.un.org/public/v1/preview/C/M/HS?...`, no key, sleep 2.5 s, cache every call as `cache/comtrade/<reporter>_<period>_<cmd>_<partner>.json`; stop gracefully on a sustained 429 and record what was pulled — the daily cap is undocumented, so budget ≤ 450 calls)
- Bilateral by HS4, one call per month: `reporterCode=842&partnerCode=76&period=YYYYMM&flowCode=M&cmdCode=<top-40 HS4 comma-list>&partner2Code=0&motCode=0&customsCode=C00` for 2024-01→2026-07 (31 calls; extend back to 2023-01 if budget allows, +12).
- Competitor mirror, one call per HS4 per month with **no** `partnerCode`: HS4 ∈ {0901, 0202, 2009, 7201, 7207, 4703, 8802, 7202, 2709, 1701, 4407, 6802} for 2024-01→2026-07 (12 × 31 = 372 calls). Fields: `primaryValue` (CIF), `fobvalue`, `netWgt`, `partnerCode`. Use `fobvalue` when comparing with ComexStat FOB; use `primaryValue/netWgt` for US landed unit values.
- Data availability check first: `GET https://comtradeapi.un.org/public/v1/getDA/C/M/HS?reporterCode=842` (returned periods 201001…202607).
- If the parent supplies `CENSUS_API_KEY`, add `https://api.census.gov/data/timeseries/intltrade/imports/hs?get=I_COMMODITY,GEN_VAL_MO,CON_VAL_MO,CAL_DUT_MO&time=from+2024-01+to+2026-08&CTY_CODE=3510&COMM_LVL=HS4&key=...` — `CAL_DUT_MO` (calculated duties) gives the realised effective tariff by line, which Comtrade cannot. Otherwise skip; do not spend searches on it.

### 1.3 Federal Register API (no key; `cache/fr/`)
- Document lists: `https://www.federalregister.gov/api/v1/documents.json?conditions[term]=Brazil&conditions[type][]=PRESDOCU&conditions[publication_date][gte]=2025-04-01&per_page=100&order=oldest&fields[]=document_number&fields[]=publication_date&fields[]=signing_date&fields[]=title&fields[]=executive_order_number&fields[]=html_url&fields[]=citation`; the same with `conditions[term]=Brazil Section 301&conditions[agencies][]=trade-representative-office-of-united-states`; and `conditions[term]="Section 232" imports adjusting`.
- Full text: `https://www.federalregister.gov/api/v1/documents/<docnum>.json?fields[]=raw_text_url&fields[]=pdf_url&fields[]=images` then GET `raw_text_url`.
- PDFs: `curl -sL https://www.govinfo.gov/content/pkg/FR-YYYY-MM-DD/pdf/<docnum>.pdf | pdftotext -layout - -`.

### 1.4 USITC HTS (no key; `cache/hts/`)
- `curl -sL "https://hts.usitc.gov/reststop/file?release=currentRelease&filename=Chapter%2099" | pdftotext -layout - - > cache/hts/chapter99.txt` (14 MB; ~41k lines). Parse by markers, not line numbers: find "As provided in heading 9903.01.81" → the (x)(iii)(a) list until "(b) As provided in heading 9903.01.90"; then (b) until "(iv) As provided in heading 9903.01.82"; for the 301 note find "heading 9903.05.03" … "9903.05.07". Codes are `dddd.dd.dd` (8) or `dddd.dd.dd.dd` (10) — keep both, map at HS6 = first 6 digits.
- `https://hts.usitc.gov/reststop/exportList?from=9903.01.77&to=9903.01.90&format=JSON&styles=false` and `https://hts.usitc.gov/reststop/search?keyword=Brazil` for the heading texts (both verified).

### 1.5 BLS v1 (`POST https://api.bls.gov/publicAPI/v1/timeseries/data/`, body `{"seriesid":[...],"startyear":"2019","endyear":"2026"}`; ≤ 25 series per query; two queries total). CPI: SEFP01, SEFC, SEFC01, SEFN02, SEFN03, SAF11, SA0; PPI: WPU026301, WPU024203, WPU101702, WPU101712, WPU0121 (verify names from `https://download.bls.gov/pub/time.series/wp/wp.item`, browser User-Agent required).

### 1.6 B3 COTAHIST for firm prices (`cache/cotahist/`)
Copy `parse_cotahist`, `cotahist_file` and the BDI/TPMERC filter from `/Users/zkid18/proj-personal/brazil-macro/ingest/b3_market.py` into the study script with its own `TICKERS` = {EMBR3, GGBR4, CSNA3, JBSS3, MRFG3, BEEF3, BRFS3, WEGE3, TUPY3, SUZB3, KLBN11, DXCO3, ALPA4, GRND3, VULC3, SMTO3, CMIN3, USIM5, CBAV3, SLCE3} (files A2024, A2025, A2026 + daily `COTAHIST_D{DDMMYYYY}.ZIP` for sessions after the annual file; delete zips after parsing). Unadjusted closes are fine for ±20-day windows; check the B3 corporate-actions endpoint only if a >15% one-day gap coincides with no tariff news. USD = close / `brl_usd`.

### 1.7 SIDRA (no key): `https://apisidra.ibge.gov.br/values/t/4099/n3/all/v/4099/p/all?formato=json` (unemployment by UF, quarterly) and `https://apisidra.ibge.gov.br/values/t/8888/n3/all/v/all/p/all?formato=json` (PIM-PF by UF, monthly, 14 locations).

### 1.8 Warehouse SQL (read-only)
```sql
-- monthly trade panel (reuse exports study)
SELECT series_id, date_trunc('month', date) AS ym,
       CASE WHEN series_id IN ('brl_usd','brent_usd','focus_fx') THEN avg(value) ELSE max(value) END AS v
FROM v_observations WHERE date <= current_date AND series_id IN
 ('exports_total','exports_to_us','exports_to_china','exports_to_eu','coffee_exports','beef_exports','pulp_exports',
  'oil_exports','oil_exports_kg','pulp_exports_kg','brl_usd','brent_usd','focus_fx','caged_net_hires','ipca_12m')
GROUP BY 1,2 ORDER BY 2,1;
-- daily market panel for the event study
SELECT series_id, date, value FROM v_observations
WHERE date >= '2024-01-01' AND series_id IN ('brl_usd','ibovespa_usd','gov_real_yield_10y','gov_nominal_yield_5y',
  'focus_fx','fx_reserves','brent_usd','share_close_adj_brl@SUZB','share_close_adj_brl@VALE','share_close_adj_brl@PETR','share_close_adj_brl@ITUB')
ORDER BY 1,2;
```

---

## 2. Pre-registration (`preregistration.txt`, written after the anchors in §0 reproduce and before any pull in §1 beyond `us_ncm_m`)

Symmetric hypotheses, each with the competing narrative, the statistic, and the verdict rule. Verdict rule throughout: "supports Hx" when the baseline sign matches, ≥ 80% of robustness cells share the sign, and the 80% cluster-bootstrap CI excludes zero; "consistent with Hx', not proof" when the CI straddles zero.

- **H1 (small and diffuse)**: net national loss after diversion ≤ 0.2% of GDP ($4.6bn) and no single HS4 lost more than $1bn/yr. **H1' (concentrated and large)**: loss on lines at the full rate ≥ 25% of their 2024 value, the top 10 treated HS4 carry ≥ 70% of the gross loss, and the top 5 states carry ≥ 75%. Statistic: triple-diff gross loss by HS4 (§5.1), diversion-adjusted (§5.2).
- **H2 (commodities divert, manufactures do not)**: diversion rate d ≥ 0.6 for the commodity group (coffee 0901, beef 0202/1602, pig iron 7201, semi-finished steel 7207/7224, pulp 4703, sugar 1701, tallow 1502, tobacco 2401, alumina 2818, crude 2709 as a special case) and d ≤ 0.3 for the manufactured group (aircraft 8802/8807, earthmoving machinery 8429, transformers 8504, footwear 6403/6402, furniture 9403, wood products 4409/4418/4412/4407, tyres 4011, stone 6802, arms 9306, tubes 7304). **H2'**: no difference (|d_comm − d_manuf| < 0.2). Statistic: d_i = ΔROW_i / |ΔUS_i| capped at [0,1] from the treated-vs-exempt DiD on exports to non-US destinations (§5.2), cluster bootstrap over HS4.
- **H3 (the US bears the cost on low-substitutability lines)**: for lines where Brazil's share of US imports > 30% (expected: pig iron, ferroniobium, OJ, green coffee, semi-finished slabs, pulp), (i) Brazil's US unit value relative to its ROW unit value did not fall by more than 5% in R2 (no price absorption by Brazil), (ii) US landed unit values from Brazil rose relative to competitors, and (iii) the Nov-2025 relief list is concentrated on those lines (share of relieved value among >30%-share lines vs <10%-share lines). **H3' (Brazil absorbed)**: relative unit values fell ≥ 5% and the relief list is uncorrelated with the Brazil share. Statistic: unit-value DiD (§5.3), the US mirror (§5.4), and a 2×2 revealed-preference table.
- **H4 (trade-only escalation costs < 1% of GDP; only financial sanctions cross it)**: in the matrix (§6), rung (c)'s central net loss < $23bn (1% of 2025 GDP $2,280bn), and rung (d) exceeds $23bn only when the financial-sanction block (capital-flow, FDI and correspondent-banking effects from analogues) is included. **H4'**: trade effects alone in rung (c) exceed 1% because manufactured lines (aircraft, machinery) do not divert. This is a modelling hypothesis; the verdict is the computed matrix under the central elasticity set, with the low/high sets reported.
- **H5 (markets treated the tariff as noise)**: mean CAR of escalation dates on `brl_usd`, `ibovespa_usd`, `gov_real_yield_10y`, Embraer and the exposed-firm basket is inside the placebo 5–95% band in the [-5,+5] window. **H5'**: escalation dates have |CAR| beyond the 90th placebo percentile and de-escalation dates the mirror sign, with an exact permutation p < 0.10 for the escalation-vs-de-escalation group difference (§5.6).
- **H6 (state concentration without an employment signal)**: five states (SP, MG, RJ, ES, SC or RS) carry ≥ 75% of the treated-line loss, and exposed states' PIM-PF and unemployment do not diverge from unexposed states by more than one cross-state sd after Aug 2025. **H6'**: divergence > 1 sd in the direction of the exposure.
- **H7 (the 2025 fall was mostly not the 40% tariff)**: crude (exempt) and Section 232 steel explain ≥ 50% of the Aug-2025→Jul-2026 fall in US-bound exports. **H7'**: lines at the 40% explain ≥ 50%. Statistic: decomposition of the 13-month gap by tariff status (§5.1).
- **H8 (revealed preference on the US side)**: the Nov-2025 relief covered the lines with the highest US CPI salience × Brazil share (coffee CPI up double digits y/y in Oct 2025; beef CPI at a record), so the relief is predicted by US consumer prices, not by Brazilian concessions. **H8'**: relief tracked the Lula–Trump meetings (Oct 6 and Oct 26, 2025) and covered lines regardless of CPI salience. Statistic: the 2×2 of relieved vs not × (CPI salience high vs low), plus the dates.

Thresholds for the coverage anchors (stop rule): the computed share of 2024 US-bound exports at the full 301+forced-labour rate must be 16.5% ± 3 pts, exempt 52.7% ± 5, Section 232 24.2% ± 5 (MDIC, A23); for R2 the share hit by the full 50% must be 35.9% ± 4 and under 232 19.5% ± 4 (A04); after the Nov relief 22% ± 4 at 40% (A10); post-SCOTUS 46% ± 5 at no extra tariff (A18). A mismatch beyond tolerance means the HS6 mapping is wrong: inspect before continuing.

---

## 3. Tariff timeline (`tariff_timeline.csv`)

Columns: `measure_id, regime, date_signed, date_effective, date_end, authority, instrument (EO/Proclamation/FR notice/OFAC/State), fr_document_number, fr_citation, rate_pct, stacking_rule, scope, exemption_source (HTS note / annex), ncm_list_file, share_us_bound_2024_pct (computed), share_us_bound_2025_pct, status_2026_10_06, primary_url, secondary_url, fact_ids, confidence`.

Regimes used by the panel (τ is the added ad valorem rate on top of the pre-2025 MFN; the stacking rule and the competitor rates are recorded separately):

| Regime | Dates | What applies to Brazilian goods |
|---|---|---|
| R0 | ≤ 2025-03-11 | MFN only |
| R1 | 2025-03-12 → 2025-08-05 | Section 232 steel/aluminium 25% (Procl. 2025-02832/02833, 2025-02-18), raised to 50% on 2025-06-04 (2025-10524); autos/parts 25% (2025-05930, 2025-04-03); copper 50% from 2025-08-01 (2025-14893); IEEPA reciprocal 10% baseline from 2025-04-05 (EO 14257, 2025-06063) |
| R2 | 2025-08-06 → 2025-11-12 | + IEEPA 40% (EO 14323, 2025-14896, signed 2025-07-30; HTS 9903.01.77) with Annex I exemptions (9903.01.81; civil aircraft 9903.01.82; 232 goods 9903.01.83; in-transit 9903.01.78) |
| R3 | 2025-11-13 → 2026-02-23 | EO 14361 (2025-21417, signed 2025-11-20, retroactive to 2025-11-13; 9903.01.90) removes the 40% from beef, coffee, fruit, juices etc.; also verify the all-country EO of 2025-11-14 removing the reciprocal 10% from agricultural products (search the FR API with term "agricultural products" "reciprocal", Nov 2025) and timber/lumber 232 (2025-19482, 2025-10-06) |
| R4 | 2026-02-24 → 2026-07-21 | SCOTUS *Learning Resources v. Trump* 2026-02-20 voids IEEPA tariffs; EO 14389 "Ending Certain Tariff Actions" (2026-03832, signed 2026-02-20); Section 122 10% surcharge 2026-02-24→2026-07-24 (2026-03824) with Annex I/II exemptions; 232 strengthened 2026-04-09 (2026-06960) and 2026-06-04 (2026-11314); critical-minerals 232 (2026-01045, signed 2026-01-14 — check the annex for ferroniobium 7202.93) |
| R5 | 2026-07-22 → | Section 301 25% (USTR notice 2026-14542; presidential memorandum 2026-14654; HTS 9903.05.01) with the exemption annex (9903.05.03–.07: raw materials, Section 232 goods, civil aircraft, pharma uses; high-purity dissolving pulp removed from the exemption list) + forced-labour 301 12.5% from 2026-07-24 (USTR 2026-15181; presidential 2026-15274; Brazil in the 54-economy 12.5% group; 232 goods and Annex A excluded). Section 122 lapsed 2026-07-24. Aircraft 232: no tariff, negotiation clock to ≈ 2027-01-05 (2026-14334). National emergency w.r.t. Brazil continued 2026-07-28 (2026-15389) — the IEEPA sanctions basis remains live. |

Items that need web verification (budget ≤ 25 searches here): Magnitsky designation 2025-07-30 (Treasury sb0257) and delisting 2025-12-12 (OFAC recent actions) and the Aug-2026 re-imposition discussion (A12); visa revocations (Moraes 2025-07-18; ambassador Viotti Aug 2026; consular suspension Oct 2026, A38); the Lindsey O. Graham Sanctioning Russia and Iran Act (signed 2026-09-18; secondary tariffs ≤ 100% on top-5 Russian crude/gas buyers from 2026-10-18; whether Brazil is on any list, A44–A45); whether Brazil is a respondent in the Mar-2026 "structural excess capacity" 301 (dockets USTR-2026-0067/0068) — steel; what the Jun-2026 232 proclamation did to Brazilian slabs (TRQ? 50%?); the Reciprocity Law 15.122/2025 text (Camex, countermeasures incl. IP and services); the EO 14257 Annex I and the 2025-07-31 EO on reciprocal rates for competitors (Vietnam 20%, Colombia 10%, Indonesia 19%, India 25%→50% on 2025-08-27, Switzerland 39%, Mexico/Canada USMCA-exempt); MDIC coverage pages (A23 URL; the Feb-2026 page in A18).

Compute `share_us_bound_2024_pct` for every regime from `us_ncm` × the HS6-mapped lists:
```sql
-- status per NCM per regime (lists loaded from cache/hts/*.csv as hs6 sets; 232 list = HTS chapters 72/73/76 derivatives + 8703/8708 + copper 74 + wood 44 (check the 232 scope files) )
CREATE TABLE status AS
SELECT n.ncm, n.hs6,
  CASE WHEN hs6 IN (SELECT hs6 FROM sec232) THEN '232'
       WHEN hs6 IN (SELECT hs6 FROM annex_i_14323) THEN 'exempt_40'
       ELSE 'full_50' END AS r2,
  CASE WHEN hs6 IN (SELECT hs6 FROM sec232) THEN '232'
       WHEN hs6 IN (SELECT hs6 FROM annex_i_14323) OR hs6 IN (SELECT hs6 FROM relief_14361) THEN 'exempt_40'
       ELSE 'full_50' END AS r3,
  CASE WHEN hs6 IN (SELECT hs6 FROM sec232) THEN '232'
       WHEN hs6 IN (SELECT hs6 FROM annex_301_exempt) THEN 'exempt_301'
       ELSE 'full_37_5' END AS r5
FROM (SELECT DISTINCT ncm, hs6 FROM us_ncm) n;
SELECT r5, sum(fob)/1e9 AS bn, 100*sum(fob)/sum(sum(fob)) OVER () AS pct
FROM us_ncm JOIN status USING (ncm) WHERE year(ym)=2024 GROUP BY 1;   -- expect 16.5 / 52.7 / 24.2 (+ residual)
```
HS6 mapping rule: an HS6 is "exempt" if every HTS-8/10 line under it appears in the list; "partial" if some do (record the exempt share as the value-weighted share using the Comtrade HS6 split where available, else 0.5); "covered" otherwise. Keep a `mapping_notes` column. Cross-check the three anchors above before anything else.

---

## 4. Product exposure map (`product_exposure.csv`)

Unit: top-40 HS4 by 2024 US-bound value plus any HS4 needed for the named firms (add 7202 ferroniobium, 0409 honey, 0304/0306 fish and shrimp, 6403 footwear, 9403 furniture, 8409/7325 Tupy castings, 8504 WEG transformers, 2401 tobacco, 2207 ethanol, 1602 beef preparations, 8807 aircraft parts). Columns:

`hs4, description, value_us_2024_bn, value_us_2025_bn, value_us_2026ytd_bn, us_share_of_brazil_exports_2024 (from div: fob_US / fob_world), brazil_share_of_us_imports_2024 (Comtrade, annual = sum of months or the 2024 annual preview call), n_suppliers_gt5pct, supplier_hhi, top3_competitors, substitutability_class (low/med/high: low if Brazil share > 30% and HHI > 2,500 or a scope/technical lock-in such as E175), status_r1..r5 (rate %), full_rate_now_pct, firms (static list with sources), states_top3 (from us_state_heading_y, 2024 value shares), state_share_top3, unit_value_available (kg>0), class (commodity/manufactured), notes`.

Firm/state mapping is a static table with a source column (company filings or MDIC state data; one search each at most): Embraer (8802/8807; SP São José dos Campos, Gavião Peixoto), Suzano/Klabin/Eldorado (4703; BA, MA, SP, MS, ES), WEG (8504/8501; SC Jaraguá do Sul), JBS/Marfrig/Minerva/BRF (0202/1602/0207; SP, MS, GO, MT, RS), Gerdau/CSN/ArcelorMittal/Usiminas (7207/7224/7208; MG, RJ, ES), Tupy (7325/8409; SC Joinville, MG Betim), Cutrale/Citrosuco/LDC (2009/3301; SP), pig iron (7201; MG, PA, MA, ES — independent *guseiros*), CBMM (7202.93; MG Araxá), coffee (0901/2101; MG, ES, SP), footwear (6403/6402; RS Vale dos Sinos, CE, BA), furniture (9403; SC, RS), honey (0409; PI, CE), fish (0304; PR tilapia), machinery (8429/8431; Caterpillar Piracicaba SP, Komatsu, CNH), tobacco (2401; RS), granite (6802; ES), alumina (2818; PA Hydro Alunorte), tallow (1502; SP, MT).

---

## 5. Measured effects by product (`did_results.csv`)

**5.1 Brazil-side triple-difference (product × destination × month).** Panel: HS4 × month, Jan 2023 → Sep 2026, outcomes `log(1 + fob_US)` and the share `fob_US / fob_world`; treatment intensity τ_{i,t} from the regime table (full rate on the line, including 232 for steel; 10% reciprocal for exempt lines in R1–R3 until the Nov-14 ag EO; Section 122 for all in R4). Specification (numpy): two-way FE by within-transformation (product and month demeaning), regressors = event-time dummies for R2, R3, R4, R5 interacted with the covered/exempt/232 status, with the triple-diff version replacing the outcome by `log(fob_US) − log(fob_ROW)`. Inference: cluster bootstrap by HS4 (2,000 draws, seed 0, 80% and 90% CIs); placebo = permute status across HS4 (2,000). Robustness grid: HS4 vs NCM-8; levels vs shares; with/without crude 2709 (exempt but −30% in 2025 for non-tariff reasons; A15); with/without 232 lines; pre-period Jan 2023–Jun 2025 vs Jan 2024–Jun 2025; drop coffee and beef (relief in R3 mid-sample). Report the implied elasticity ε = coefficient / Δτ per class and the gross loss by HS4 = 2024 value × (1 − e^{coef}), and the H7 decomposition of the 13-month gap (Aug 2025–Aug 2026 vs the exports study's −$8.5bn) by status. Export the event-time coefficients for chart 03.

**5.2 Diversion by product.** For each HS4, DiD of exports to non-US destinations (China, EU-27, Mercosur, rest) for covered vs exempt lines, same windows; d_i = max(0, min(1, ΔROW_i / |ΔUS_i|)) with bootstrap CI; group means for the commodity and manufactured classes (H2). Also destination-level detail for coffee (Germany, Belgium, Italy, Japan), beef (China, Chile, Egypt), pig iron (Mexico, Italy, Turkey), pulp (China, Netherlands), aircraft (by country of airline, lumpy — treat descriptively).

**5.3 Unit values.** `uv = fob/kg` by HS4 (and NCM for coffee 09011110, beef 02023000, pig iron 72011000, slabs 72071200, pulp 47032900, OJ 20091200/20091100, sugar 17011400): the ratio uv_US / uv_ROW before (Jan 2024–Jul 2025) and in each regime; DiD covered vs exempt; the coffee and beef price spikes of 2025 are the reason for the ratio, not the level.
```sql
SELECT hs4, ym, sum(CASE WHEN country='Estados Unidos' THEN fob END)/nullif(sum(CASE WHEN country='Estados Unidos' THEN kg END),0) AS uv_us,
       sum(CASE WHEN country<>'Estados Unidos' THEN fob END)/nullif(sum(CASE WHEN country<>'Estados Unidos' THEN kg END),0) AS uv_row
FROM div WHERE kg > 0 GROUP BY 1,2 ORDER BY 1,2;
```

**5.4 US-side mirror (Comtrade).** For the 12 HS4 in §1.2: Brazil's share of US imports by month, competitors' shares, and US landed unit values (primaryValue/netWgt) from Brazil vs competitors. DiD of Brazil share around each regime against the competitor set, with the **relative** tariff wedge as the treatment (Brazil's added rate minus the competitor's: e.g. coffee in R2 = 50 − Colombia 10 − Vietnam 20; in R5 = 37.5 vs Colombia's 12.5 forced-labour rate and Vietnam's rate — build a small competitor-rate table from the FR). Compare with ComexStat (FOB, Brazilian export month) allowing a 1–2 month shipping lag.

**5.5 States and employment.** From `us_state_heading_y` and `us_state_heading_m_top`: each UF's US-bound exports by status, the UF loss = Σ_i (HS4 loss from 5.1 × UF share of that HS4), and the UF-level DiD of monthly US-bound exports (treated share as intensity, 27 UFs, cluster bootstrap by UF). Employment proxies: SIDRA PIM-PF by UF (14 locations) and PNAD unemployment by UF (27), DiD on the treated-share intensity from 2025-Q3; `caged_net_hires` nationally as context. State n is small: report as effect sizes with bands and label exploratory.

**5.6 Market event study.** Import from `/Users/zkid18/proj-personal/brazil-macro/research/2026-10-elections/congress/congress_core.py`: `daily_changes`, `car`, `run_event_study`, `perm_test`, `WINDOWS`; extend `ES_SERIES` with `gov_nominal_yield_5y`, `focus_fx` and the COTAHIST tickers in USD (log %), and the "exposed basket" (equal-weighted EMBR3, GGBR4, CSNA3, JBSS3, SUZB3, WEGE3, TUPY3, ALPA4, GRND3, DXCO3). Estimation window [-250,-121], Brent market-model variant for BRL and Ibovespa, placebo 2,000 dates ≥ 90 days from any event. Event list (first trading day on/after; group escalation E, de-escalation D, control C):
E 2025-07-09 letter (trade 07-10); E 2025-07-30 EO 14323 + Magnitsky; E 2025-08-06 effective; D 2025-09-23 UNGA; D 2025-10-06 call; D 2025-10-26 Kuala Lumpur; D 2025-11-20 relief; D 2025-12-12 Magnitsky lifted; D 2026-02-20 SCOTUS; D 2026-05-07 White House; E 2026-06-01/04 301 determination; E 2026-07-15 301 final; E 2026-07-22 effective; E 2026-08-16 FT re-imposition report; E 2026-10-01 consular suspension; C 2025-04-02 "Liberation Day" (Brazil at the 10% floor); C 2025-04-11 Reciprocity Law; C 2026-10-05 first-round result. Group difference E vs D by exact permutation; headline window [-5,+5]; Embraer alone with its own placebo.

---

## 6. Escalation scenario matrix (`escalation_matrix.csv`)

Rows: rung × (Brazil cost block, US cost block, markets block, retaliation block, probability block). Columns: `rung, definition, legal_route, trigger(s), covered_share_us_bound_pct, export_loss_gross_low/central/high_bn, diversion_rate_used, export_loss_net_low/central/high_bn, pct_exports, pct_gdp_direct (ΔX/GDP × (1−m) × k, m∈[0.10,0.20], k∈[1.0,1.5], reuse exports §3), top5_hs4_losses, top5_states, firms_hit, brl_pct, ibov_usd_pct, ntnb_bp, embraer_pct, source_of_market_numbers, retaliation_option, retaliation_cost_to_brazil_bn, us_consumer_cost_bn, us_cpi_items (coffee/beef/juices pts), us_input_shortages, us_exporter_exposure_bn, us_fdi_exposure_bn, prob_lula_iv, prob_flavio, trigger_probs, analogue, fact_ids, uncertainty_note`.

Rungs:
- **(a) status quo**: 301 25% + 12.5% on ~16.5% of US-bound trade; 232 on ~24%; exemptions as in R5; aircraft 232 clock running.
- **(b) 301 raised to 50–100% on current coverage** (USTR modification under 301(b)/(c); 30-day notice): same coverage, higher τ.
- **(c) coverage widened**: exemption annex removed (coffee, beef, OJ, pig iron, pulp, iron ore pellets, alumina, stone…), civil aircraft exemption removed and/or a 232 aircraft tariff at the 180-day mark, energy (crude, fuels) included; 232 steel at 50% with no TRQ.
- **(d) "total" regime**: ≥ 100–500% across the board (301 or a Graham-Act-type secondary tariff), plus financial measures: SDN designations of officials (Magnitsky re-imposition, a broader EO under the still-live national emergency), SDN listings of state entities (Petrobras/BNDES/Banco do Brasil analogues to PDVSA 2019), or secondary sanctions on counterparties.
- **(e) negotiated de-escalation**: 301 suspended or converted into a monitored agreement (Pix/digital, ethanol TRQ, deforestation); 232 stays; aircraft deal.

Mechanics (all in the script, every input traceable):
1. Export loss by product: ΔX_i = X_i,2024 × (1 − exp(ε_i · Δτ_i)) with ε_i from §5.1 by class (bounded by analogues: the 2025 realised fall of −14% to −25% for a 40–50% rate on covered lines implies ε ≈ −0.5 to −1.0; the US–China 2018–19 literature gives −1.5 to −2.5 at HS10 over 12 months — record the sources). Net = gross × (1 − d_i) with d from §5.2 (commodity 0.6–1.0, manufactured 0–0.3). Cap at the line's 2024 value. For (d) add a financial block from analogues: Russia 2022 (trade re-routing but a 10–15% import/GDP shock), Venezuela 2019 (oil exports −50% within a year after PDVSA SDN), India Aug 2025–Feb 2026 (50% for 5.5 months; verify export response and INR), Canada/Mexico 2025 (USMCA exemption made coverage small).
2. Sector and state incidence from §4–§5.5 weights.
3. Markets: scale the §5.6 escalation CARs (per rung severity) and the analogue moves (INR record low Aug 2025, COP Jan 2025, CNY −10% 2018–19, RUB 2022). Yields via the congress study's rate scenarios as the prior.
4. Retaliation: Reciprocity Law 15.122 (Camex; tariffs, IP suspension, services) applied to the import list in §0.2 — the top US lines are Embraer's and airlines' jet engines (8411, $6.2bn), fuels, LNG, polyethylene, aircraft, coal, medicines, agrochemicals, fertilisers: cost-to-Brazil = input-price shock on those lines (share of imports with no near substitute); digital services (US services surplus with Brazil — one search for BEA/USTR figures).
5. US-side cost: for each relieved/low-substitutability line, pass-through × Brazil share × US consumption: coffee CPI (Brazil 30–35% of US green coffee; pass-through 0.9 at the border, retail share of green-bean cost ~40%; CPI weight from BLS), OJ (Brazil share of US OJ imports ~60–70%), beef (Brazil's share of a record 2025 import level; the Argentina TRQ reallocation shows the substitution route), pig iron (~60% of US imports; EAF input), ferroniobium (CBMM; the US has no domestic source, Canada's Niobec is the alternative), E175 (the only in-production 76-seat scope-clause jet; US regional fleet dependence — 1–2 searches), pulp. US goods surplus with Brazil: ComexStat says +$0.3bn (2024) and +$7.5bn (2025); Census-basis figures differ (verify one number); US exporters' exposure = the §0.2 import list; US FDI stock in Brazil (BEA, one search) and US holdings of Brazilian securities (TIC, one search).
6. Probabilities: qualitative (low < 25%, medium 25–60%, high > 60%) by run-off winner (Lula IV / Flávio) and by trigger: amnesty/dosimetria (congress §7: the main link), STF actions against Bolsonaro, Pix/digital (301 core), BRICS (Jul-2025 threat, A40), China alignment, Russian oil (Graham Act list due 2026-10-18), the aircraft-232 clock (≈ 2027-01-05), election-interference claims (A38). Rationale column with fact ids; state explicitly that these are judgements.

---

## 7. Deliverables, run order, charts, report

Run order: (1) anchors §0 → `results.json["anchors"]`; (2) `preregistration.txt`; (3) pulls §1.1 → §1.4 → §1.5 → §1.6 → §1.7, then §1.2 (longest); (4) timeline and coverage checks §3 (stop rule); (5) exposure §4; (6) effects §5; (7) matrix §6; (8) charts; (9) `report.txt`, copy charts to `review/charts/07_us_tariffs__*.html`.

Files in `us_tariffs/`: `us_tariffs_study.py` (single script, sections numbered as here, `R`/`SQLLOG` pattern from `exports_policy_study.py`), `preregistration.txt`, `cache/` (git-ignored), `results.json` (every number with series_id/source/last_date/sql or the cache file name and API call), `tariff_timeline.csv`, `product_exposure.csv`, `did_results.csv` (one row per estimator × unit × window × robustness cell), `escalation_matrix.csv`, `external_facts.csv` (continue ids: D01… for US legal texts, E01… for US-side market facts, F01… for analogues; same columns as `exports/external_facts.csv`), `api_calls.csv` (endpoint, body/url, rows, bytes, seconds, cached file), `charts/`, `report.txt`.

Charts (Plotly HTML): `01_coverage_by_regime` (stacked area: US-bound exports by tariff status, monthly, R0–R5 shading), `02_exposure_treemap` (top-40 HS4, colour = current rate, hover = Brazil share of US imports, firms, states), `03_did_event_time` (coefficients covered/exempt/232 with bootstrap bands), `04_diversion_by_product` (ΔUS vs ΔROW per HS4, by class), `05_unit_value_ratios` (uv_US/uv_ROW for the 7 lines), `06_us_mirror_shares` (Brazil vs competitors, 12 HS4), `07_state_exposure` (bars by UF: exposure, loss, PIM-PF/PNAD divergence), `08_event_study` (CAR by date and series with placebo bands; Embraer panel), `09_escalation_tornado` (rungs a–e: Brazil net loss and US consumer cost), `10_us_cpi_and_relief` (CPI coffee/beef/juices with regime shading and the Nov-2025 relief marker).

Report (`report.txt`, and in the final message): Summary (10 lines, numbers first); Data and sources (what works, what needs a key, exact calls, vintages: ComexStat to 2026-09, Comtrade to 2026-07, warehouse to 2026-08); Timeline table; Exposure map; Measured effects with H1–H8 verdicts and the robustness grid; States and employment; Markets; Escalation matrix with the US-side block and the probability table; Analogue table; What cannot be concluded; Appendix A (series, source, last date); Appendix B (external facts, fenced); Appendix C (API call log).

Pitfalls to copy into the script header: ComexStat first-of-month dates; Comtrade `primaryValue` is CIF for imports (use `fobvalue` against ComexStat) and lags shipments by 1–2 months; HS6 mapping is many-to-one (record partials); crude is exempt but fell 30% for non-tariff reasons (exclude from the control group in the main spec; report both); coffee and beef prices roughly doubled in 2025 (use unit-value ratios, not levels); the Nov-2025 relief and the Nov-14 all-country ag EO overlap (two τ changes); Section 122 applied to everyone (R4 wedge vs competitors ≈ 0); the forced-labour 12.5% applies to 54 economies including Colombia, Peru, Chile, China and Japan (relative wedge, not absolute, for the mirror); 2026 BRL appreciation (6.10 → 4.98) and the Brent shock confound 2026 levels; the aircraft 232 clock and the Graham Act list date (2026-10-18) are inside the forecast horizon; placebo windows must exclude Mar 2020–Jun 2021 in a robustness cell (the exports study's COVID issue); `v_annual` 2026 is incomplete; never write to the warehouse; sleep 11 s (ComexStat) and 2.5 s (Comtrade); the web-search cap is ~200 — the priority list in §3 and §6 is ≤ 60 searches, everything else comes from the APIs.

### Critical Files for Implementation
- `/Users/zkid18/proj-personal/brazil-macro/ingest/comexstat.py` — the request pattern, headers, country ids, PAUSE/429 handling and `EXTRA` filter shapes to copy for the NCM×country, state and heading pulls
- `/Users/zkid18/proj-personal/brazil-macro/research/2026-10-elections/exports/exports_policy_study.py` — the `rec`/`q`/`SQLLOG`/`results.json` conventions, the monthly-panel SQL, `did_at`, `seasonal_cf`, the block bootstrap and the GDP mapping to reuse unchanged
- `/Users/zkid18/proj-personal/brazil-macro/research/2026-10-elections/congress/congress_core.py` — `daily_changes`, `car`, `run_event_study`, `perm_test`, `WINDOWS`, `ES_SERIES` for the market event study
- `/Users/zkid18/proj-personal/brazil-macro/ingest/b3_market.py` — `parse_cotahist`/`cotahist_file` and the BDI 02 / TPMERC 010 filter for Embraer and the exposed-firm basket
- `/Users/zkid18/proj-personal/brazil-macro/research/2026-10-elections/exports/external_facts.csv` — fact ids A01–A51 (tariff facts) to cite rather than re-verify, and the schema for the new D/E/F series