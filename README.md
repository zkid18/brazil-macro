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
bronze  warehouse/bronze/<ts_id>.csv        raw Dateno annual exports, as pulled
        warehouse/bronze/native/<id>.csv    raw native (BCB SGS) daily/monthly
silver  warehouse/silver/fact_time_series   normalized long facts; date + freq
                                            (annual | monthly | daily)
gold    warehouse/gold/derived_metrics      annual-feasible derived metrics
        warehouse/gold/book_scorecard       computed evidence vs Davidson's bets
dq      dq/dq_report.csv                     per-metric coverage/freshness
        warehouse/brazil_macro.duckdb        DuckDB warehouse (all tables)
```

## Run

```bash
export DATENO_API_KEY=...           # Dateno apikey (never commit it)
python3 ingest/dateno_pull.py       # Tier-1 annual (World Bank) -> bronze
python3 ingest/bcb_sgs.py           # Tier-2 native daily/monthly (BCB SGS) -> bronze/native
python3 pipeline.py                 # bronze -> silver -> gold -> dq -> DuckDB
python3 dashboard.py                # -> warehouse/dashboard.html (open in browser)
```

Query:
```sql
duckdb warehouse/brazil_macro.duckdb \
  "SELECT * FROM book_scorecard"
```

## Current state (this build)

**Registry coverage: 70 / 112 metrics materialized (62%)** — run `coverage.py` for
the full per-metric `registry_coverage.csv`. Native sources are the base; Dateno is
demoted to the annual structural backbone + cross-checks. **~96,000 silver rows**,
1960–2026, across daily/monthly/annual.

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
Every SGS code was checked against known current reality before inclusion. Rejected
codes (wrong concept/units): `28763`,`19882`(stale 2021),`4469`(R$ not %),`22701`
(US$ flow),`23703/23704`(US$ stock not %GDP),`29034`(404),`4513`(67%, not net debt).
NFSP series use BCB sign convention (positive = deficit); the pipeline flips them
for `primary_balance_gdp` and derives `interest_bill_gdp = nominal − primary`.

### Next Tier-2 adapters (highest yield first)
- **ComexStat extras** → exports_by_product/destination, lithium/niobium/rare-earth,
  corn/cotton, derived fertilizer_dependency_index, potash proxy.
- **IBGE SIDRA extras** → median_age (projections), inflation_diffusion (IPCA items);
  labor_productivity_proxy needs a GDP-level series.
- **IPEAData** → embi_brazil (daily country-risk).
- **CVM / B3** → equity & fixed-income fund flows, Ibovespa.
- **ANP / Conab** → oil & gas production, grain harvest (file/portal parsing).
- Deferred: cmo_power_cost (ONS PLD dataset); IPCA services/administered (SGS
  segment codes were ambiguous on probe — need confident identification first).

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
