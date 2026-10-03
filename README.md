# Brazil Macro Data Registry → Warehouse

A registry-driven data-engineering pipeline that resolves the Brazil macro metric
registry to real data sources, pulls what is pullable from **Dateno**, and lands
it in a local DuckDB warehouse with derived metrics and a "book scorecard" that
checks James Dale Davidson's 2012 *Brazil Is the New America* thesis against data.

## Source of truth

`registry/brazil_macro_data_allocation_metrics.csv` (112 metrics) is the spine —
it defines each `metric_id`'s theme, grain, update frequency, access cost,
ingestion complexity, and derived-metric logic. The pipeline never replaces it;
it only *resolves* and *materializes* it.

`registry/source_map.yml` is the resolution layer keyed by `metric_id`:
- **Tier 1 (22)** — pullable now from Dateno's structured timeseries (`ns: wb`).
- **Tier 2 (28)** — high-frequency native APIs (BCB SGS/Focus, IBGE SIDRA,
  ComexStat, ONS). Dateno carries **no** pullable timeseries for these. The first
  native adapter is built: `ingest/bcb_sgs.py` pulls **daily** Selic & BRL/USD and
  **monthly** IPCA & IBC-Br from the BCB SGS API into `warehouse/bronze/native/`.
- **Tier 3 (11)** — geospatial (INPE), portal files (ANP, Conab, B3), or paid
  (CDS, MSCI). Out of automated scope.

## What we learned about Dateno (important)

1. Dateno exposes **two surfaces**: a structured timeseries API (only two
   namespaces exist — `wb` World Bank, `ilostat` ILO) and a 1.5M-entry dataset
   **discovery** search (`search_datasets`) that returns metadata + URLs, not values.
2. The `wb` namespace **does** carry full World Development Indicators, but the
   per-country timeseries id uses **ISO-2** (`NY.GDP.MKTP.KD.ZG.BR`) while the WB
   Poverty & Equity database uses **ISO-3** (`...BRA`). Each id is validated by an
   actual export call — never assumed.
3. Frequency is **annual, country-level** — perfect for the book's structural /
   2012→2026 verdicts, useless for daily/monthly (those stay Tier 2).
4. The public REST API is `https://api.dateno.io/statsdb/0.1/ns/{ns}/ts/{ts_id}/export.csv`
   with an `apikey:` request header. Two gotchas: it 403s the default
   `Python-urllib` User-Agent (send a normal UA), and python.org Python on macOS
   needs `certifi`'s CA bundle. `ingest/dateno_pull.py` handles both.

## Layers

```
bronze  warehouse/bronze/<ts_id>.csv          raw Dateno annual exports, as pulled
        warehouse/bronze/native/<id>.csv      country series (BCB, IBGE, ComexStat, ANP, ONS...)
        warehouse/bronze/companies/<id>.csv   company series, keyed by entity_id (PETR, VALE...)
        warehouse/bronze/raw/                 gitignored download cache (zips, parquets)
silver  warehouse/silver/fact_time_series     long facts: metric_id x entity_id x date
                                              (daily | weekly | monthly | quarterly | annual | event)
gold    warehouse/gold/derived_metrics        scalar derived metrics (real rate, r-g, fiscal gap...)
        warehouse/gold/book_scorecard         computed evidence vs Davidson's bets
        warehouse/gold/hypothesis_tests       10 falsifiable tests with fixed thresholds + verdicts
        warehouse/gold/company_metrics        entity x quarter fundamentals
dq      dq/dq_report.csv                      per-series freshness vs expected lag
        warehouse/brazil_macro.duckdb         DuckDB warehouse (all tables)
```

## Setup

Python 3.8+ (developed on 3.13).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # pandas, pyyaml, certifi, duckdb, pyarrow, plotly
```

Environment variables:

| Variable | Needed for | Notes |
|---|---|---|
| `DATENO_API_KEY` | `ingest/dateno_pull.py` only | Keep it in `.env` (gitignored); load with `set -a; source .env; set +a`. |
| `DATENO_API_BASE` | optional | Defaults to `https://api.dateno.io`. |
| `BRAZIL_MACRO_AS_OF` | optional | `YYYY-MM-DD` as-of date for freshness checks (reproducible rebuilds). Defaults to today. |

Every other source (BCB, IBGE, ComexStat, IPEAData, ANP, ONS, B3, CVM, Tesouro) is public and keyless.

## Run

```bash
# 1. ingest (network). Slow ones: comexstat ~4 min (rate limit), ipeadata up to ~10 min,
#    first b3_market / ons_plants / cvm_financials runs download a few hundred MB into bronze/raw.
set -a; source .env; set +a
python3 ingest/dateno_pull.py      # World Bank annual structurals (Dateno)
python3 ingest/bcb_sgs.py          # BCB SGS (SOAP): rates, FX, credit, fiscal, BoP, vehicles
python3 ingest/bcb_focus.py        # Focus market expectations
python3 ingest/bcb_olinda.py       # Pix monthly
python3 ingest/caged.py            # Novo CAGED net hires (IPEAData)
python3 ingest/ibge_sidra.py       # PNAD income/employment/unemployment, PMC retail
python3 ingest/comexstat.py        # trade by product (FOB + tonnes) and destination
python3 ingest/ipeadata.py         # EMBI, Ibovespa, Brent, ANP oil/gas
python3 ingest/anp_production.py   # offshore oil, pre-salt share, operated oil by company
python3 ingest/ons_energy.py       # grid mix, load, reservoirs
python3 ingest/ons_plants.py       # CMO power cost; generation by company
python3 ingest/tesouro_bonds.py    # NTN-B / LTN yields
python3 ingest/b3_market.py        # Ibovespa weights, share prices, dividends
python3 ingest/cvm_financials.py   # company financial statements (ITR/DFP)
# 2. build (offline, seconds)
python3 pipeline.py                # bronze -> silver -> gold -> dq -> DuckDB
python3 coverage.py                # registry coverage report
python3 dashboard.py               # -> warehouse/dashboard.html (+ dashboard_artifact.html)
```

Query:
```sql
duckdb warehouse/brazil_macro.duckdb \
  "SELECT hyp_id, verdict, evidence FROM hypothesis_tests"
```

## The report: "Brazil, Tested"

`dashboard.py` renders one static page: ten hypothesis tests (each with its statistic
drawn against a threshold fixed in `hypotheses.py`), six companies (Petrobras, Vale,
Axia/ex-Eletrobras, Suzano, PRIO, with Itaú as the non-resource control: USD total
return since 2012, revenue and net income, physical output), the 2012-book scorecard,
a chaptered data library and a sources/freshness section. Charts are drawn client-side
from embedded JSON (Plotly from cdnjs) so they follow light/dark themes.

| Test | Hypothesis | Inputs |
|---|---|---|
| H1 | Petrobras earns on price, not volume | CVM revenue, Brent, ANP operated oil |
| H2 | Oil exports grow by volume; iron ore doesn't | ComexStat tonnes, ANP pre-salt |
| H3 | Vale is a China iron-ore price proxy | CVM revenue, iron-ore US$/t |
| H4 | Droughts are paid by thermal plants and consumers, not Axia | ONS EAR, plant generation, CMO |
| H5 | Resource champions lagged the index in dollars since 2012 | B3 prices + dividends, PTAX |
| H6 | Suzano is the currency hedge the index lacks | B3 total return, BRL/USD |
| L1 | Debt service is squeezing shoppers | BCB 29034, IBGE PMC |
| L2 | Formal hiring warns before unemployment turns | CAGED, PNAD |
| L3 | Interest outruns growth on public debt | BCB NFSP, gross debt, nominal GDP |
| L4 | Exports pivot from the US to China | ComexStat by destination |

H1–H6 came from an energy/resource-company review; L1–L4 from themes recurring in
@LatamData posts (Jul–Oct 2026).

## Current state (this build)

**Registry coverage: 78 / 112 metrics materialized (70%)** — run `coverage.py` for
the full per-metric `registry_coverage.csv`. Native sources are the base; Dateno is
demoted to the annual structural backbone + cross-checks. **~174,000 silver rows**,
288 series (country + company), 1960–2026.

Native adapters (`ingest/`):
- **bcb_sgs.py** — policy/credit/fiscal/external: Selic, BRL/USD, FX reserves (daily);
  IPCA m/m & 12m, IBC-Br, credit/GDP, delinquency, debt-to-income, gross/net debt,
  NFSP deficits (monthly).
- **bcb_focus.py** — market expectations (daily): focus_ipca_12m, focus_selic_12m,
  focus_gdp_growth, focus_fx (Olinda OData).
- **comexstat.py** — trade (monthly FOB, 2014–2026): exports/imports totals + soy,
  oil, iron-ore, beef, coffee, sugar exports + fertilizer imports (verified NCM groups).
- **tesouro_bonds.py** — gov bond yields (daily, constant-maturity): gov_real_yield_10y
  (NTN-B, 7.6%), gov_nominal_yield_5y (LTN, 14.0%).
- **ons_energy.py** — grid (daily, 2015–2026): generation total + hydro/wind-solar/
  thermal shares, thermal dispatch, load, stored-energy EAR (national, SIN).
- **ibge_sidra.py** — PNAD labor (monthly): real_average_income, employed_population.
- **comexstat.py** (extras) — niobium exports, potash imports, exports_to_china.
- **ipeadata.py** — embi_brazil (EMBI+ risk; feed ends 2024-07 → STALE, as the
  registry warned), ibovespa_level (daily, current), oil_production (ANP, kbbl/d).
- **dateno_pull.py** — 14 WB annual structural series + 2 `*_wb_annual` cross-checks.

Dateno mirror (`warehouse/bronze/dateno/{observations,catalog}.parquet`, Dateno schema):
Dateno's `wb`/`ilostat` namespaces mirror the World Bank and ILOSTAT, and our Dateno key
allows only 200 requests/day, so the full Brazil pull comes straight from those upstreams.
The rows use Dateno's ids (`<IND>.BR` / `<IND>.BRA`). The 22 series pulled natively through
Dateno (tier-1) always win on overlap. Shared merge logic lives in `ingest/_dateno_mirror.py`.
```bash
.venv/bin/python ingest/worldbank_bulk.py   # DataBank bulk zips + API v2 (all WB databases)
.venv/bin/python ingest/ilostat_bulk.py     # ILOSTAT rplumber, A/Q/M, all disaggregations
# add --build-only to rebuild from the gitignored cache in warehouse/bronze/raw/
```

Derived scalars (7, in gold/derived_metrics): `real_policy_rate` 10.4% (Selic − Focus
IPCA, ex-ante), `r_g_spread` +8.7pts, **`debt_stabilizing_primary_surplus_gap` +7.0%GDP**,
`credit_impulse` +1.1, `investment_rate_gap` +3.5pts, `fdi_coverage` 2.95×,
**`export_concentration_index` 48.5%**. Derived series (in silver): trade_balance,
hydro_stress_index, real_wage_bill, china_export_share, fertilizer_dependency_index,
potash_import_dependency_proxy, ibovespa_usd, oil_production_yoy, primary_balance,
interest_bill, credit growth.
**11 scorecard threads** now — incl. fiscal-sustainability, commodity-concentration,
hydropower-vulnerability (2021 EAR trough 24%), Brazil-vs-China demand dependence
(China 28% of exports, up from 18% in 2014), and **pre-salt oil** (output ~2.0x the
2010 average — the one energy bet Davidson got right while peak-oil failed).

DQ is frequency-aware (daily ≤10d, monthly ≤100d, annual ≤~3.5yr); only the two
genuinely-behind renewables series flag STALE.

### BCB SGS code verification
Transport: `api.bcb.gov.br` no longer resolves (NXDOMAIN at BCB's own DNS since 2026).
`ingest/bcb_sgs.py` uses the SGS SOAP service `www3.bcb.gov.br/wssgs/services/FachadaWSSGS`
(`getValoresSeriesXML`; needs a `SOAPAction` header; dates come back unpadded). Run
`python3 ingest/bcb_sgs.py --meta <codes>` to print a series' name, unit and periodicity.

Every SGS code was checked against known current reality before inclusion. Added in
this build: 10844 (IPCA services), 4449 (administered prices), 21379 (diffusion),
22701/22708/22709 (current account, BoP goods), 1373 (vehicle production), 7384–7387
summed (Fenabrave sales), 29034 (household debt service, s.a.), 4382 (nominal GDP 12m).
Rejected (wrong concept/units): `28763` (CAGED employment *stock*; net hires come from
IPEAData `CAGED12_SALDON12`), `19882` (stale 2021), `4469` as R$ series, `23703/23704`
(US$ stock not %GDP), `4513` (67%, not net debt), `29039` (commodity index), `1378`
(Anfavea total includes exports). NFSP series use BCB sign convention (positive =
deficit); the pipeline flips them for `primary_balance_gdp` and derives
`interest_bill_gdp = nominal − primary`.

### Next Tier-2 adapters (highest yield first)
- **ComexStat extras** → exports_by_product/destination, lithium/niobium/rare-earth,
  corn/cotton, derived fertilizer_dependency_index, potash proxy.
- **IBGE SIDRA extras** → median_age (projections), inflation_diffusion (IPCA items);
  labor_productivity_proxy needs a GDP-level series.
- **IPEAData** → embi_brazil (daily country-risk).
- **CVM / B3** → equity & fixed-income fund flows, Ibovespa.
- **ANP / Conab** → oil & gas production, grain harvest (file/portal parsing).
- Done in this build: cmo_power_cost (ONS CMO weekly), IPCA services/administered,
  ANP oil & gas, IPEAData EMBI/Ibovespa, company coverage (B3, CVM).
- Next: Conab grain harvest (`SerieHistoricaGraos.txt`), CVM fund flows
  (`inf_diario_fi`), ANP fuel prices vs import parity, B3 foreign-investor flows.

### Scorecard evidence computed from landed data (vs Davidson's 2012 bets)
- **Hyperinflation as inoculation** — CPI 1994 = 2,076% → 2023 = 4.6% (Real Plan held).
- **Commodity supercycle vs structural rise** — GDP growth 4.50% (2004–2010) vs
  0.55% (2015–2023): favors the cyclical/supercycle reading.
- **External financing quality** — FDI 2.95%GDP covers CA −1.00%GDP (2023), 2.95×.
- **Demographic window closing** — TFR 1.63 (2022); crossed below 2.1 in 2003.
- **Investment ceiling** — GFCF/GDP 16.5% (2023), ~3.5pts below a rerate threshold.
- **Virtual water / deforestation** — forest area −16.1% (1990→2022).

## Extending

- **More Tier 1**: add/verify the `metric_id`s already in `source_map.yml:tier1`,
  pull, re-run `pipeline.py`.
- **Tier 2 adapters**: implement BCB SGS / IBGE SIDRA / ComexStat clients writing
  to the same bronze contract (`indicator_id,…,date,value,…`), then map their
  `ts_id`s. The silver/gold/scorecard layers need no change.
- **Derived metrics**: `real_policy_rate` and `r_g_spread` unlock once Tier-2
  rate/expectations series land.
