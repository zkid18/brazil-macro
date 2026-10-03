# Brazil Monitoring

**One reconciled source of truth for Brazil's economic, social, energy and corporate data.**

Live: [br.nonamevc.com](https://br.nonamevc.com) · Database: [`brazil_macro.duckdb`](https://br.nonamevc.com/data/brazil_macro.duckdb) · Agents: [`llms.txt`](https://br.nonamevc.com/llms.txt)

---

## Why

Data on Brazil is scattered across dozens of publishers. Each one has its own API, codes, units,
calendars and revision habits. A simple question like "did real interest rates rise faster than
growth under each government?" means stitching together the central bank, the statistics
office, the Treasury and the World Bank. The analyst then has to decide which number is right
whenever two sources disagree.

Brazil Monitoring does that work once, and keeps doing it:

- **Collect.** Every series is pulled from its official publisher and refreshed on a schedule.
- **Normalise.** Everything lands in one long format: one row per series per date, with
  consistent dates, units, topics and entities (Brazil or a listed company).
- **Reconcile.** When two sources measure the same thing, one is marked canonical and the
  other is kept as an alternate. The gap between them is measured, not hidden.
- **Explain.** A semantic layer of views, named metrics, a glossary and rules makes the data
  usable by people and AI agents alike.
- **Serve.** A browsable site, a remote-queryable DuckDB file, and Parquet exports.

The result: about 8,000 curated time series (plus 4.3 million labour-market breakdowns) from 1960 to today. Duplicates across sources, one-off survey items and statistical by-products are removed but listed in `excluded_series`; ILO tables that differ only by breakdown are merged into one series with selectable breakdowns. The coverage
spans macro, prices, rates, fiscal, trade, labour, households, energy, health, education,
social protection, financial inclusion, and the largest resource companies.

## Data

The backbone is **[Dateno](https://dateno.io)**, an index of statistical data. Its World Bank
and ILO namespaces provide the long structural history for Brazil: development indicators,
debt, education, health, gender, labour. Series keep Dateno's identifiers (`wb/…`,
`ilostat/…`).

On top of that sit **Brazil's official publishers**, which add the high-frequency and
Brazil-specific series:
- **Banco Central:** rates, credit, fiscal, external accounts, Focus expectations, Pix.
- **IBGE:** prices, labour, retail, population.
- **Trade and energy:** ComexStat for trade; ANP and ONS for oil, gas and power.
- **Markets and companies:** Tesouro for bond yields; B3 and CVM for companies.
- **Health:** DATASUS and WHO.
- **Politics:** a calendar of presidential terms and events, so any series can be read
  against who was governing.

Where the native publisher and Dateno overlap, the native series is canonical. The
reconciliation table records how closely the two agree.

**Data model and semantic layer:** [`semantic/model.yml`](semantic/model.yml)

## Use it

- **Browse.** [br.nonamevc.com](https://br.nonamevc.com):
  - Search every series, or open curated pages such as Brazil at a glance, Oil, gas & power,
    Resource companies, Trade & China, and Health.
  - Plot several series together, and overlay presidential terms and political events.
- **Ask your AI agent.** Click **Copy prompt** on the site and paste it into Claude, ChatGPT
  or Cursor. The prompt tells the agent how to attach the database and read the semantic
  layer, so it answers from data rather than memory. This works like an MCP server without
  running one. The same instructions are in [`AGENTS.md`](AGENTS.md).
- **Query it remotely.** No download needed:

  ```sql
  INSTALL httpfs; LOAD httpfs;
  ATTACH 'https://br.nonamevc.com/data/brazil_macro.duckdb' AS br (READ_ONLY);
  USE br;
  SELECT * FROM v_search WHERE title ILIKE '%inflation%';
  SELECT president, lean, AVG(value) FROM v_politics WHERE series_id = 'ipca_12m' GROUP BY ALL;
  ```

- **Download.** Get the [DuckDB file](https://br.nonamevc.com/data/brazil_macro.duckdb) or the
  [Parquet exports](https://br.nonamevc.com/export/).

## Run it

Requires Python 3.10+.

```bash
git clone https://github.com/zkid18/brazil-macro && cd brazil-macro
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Build from the committed snapshots.** This is offline and takes about a minute:

```bash
python3 pipeline.py      # bronze snapshots -> warehouse/brazil_macro.duckdb (+ Parquet in warehouse/export/)
python3 portal.py        # -> warehouse/portal/ (the site)
python3 -m http.server -d warehouse/portal 8000   # open http://localhost:8000/standalone.html
```

**Refresh from the sources (the ETL).** Every Brazilian source is public and keyless;
Dateno needs a key (`echo "DATENO_API_KEY=..." > .env`).

```bash
./scripts/refresh.sh              # daily   — Brazilian sources, then rebuild
./scripts/refresh.sh --weekly     # weekly  — + full World Bank and ILO history
./scripts/refresh.sh --monthly    # monthly — everything: bulk caches re-downloaded, ILO labels,
                                  #           Dateno tier-1 pull and discovery, gap check
```

Every run is safe to repeat: one run at a time (lock), a failing source is logged and skipped
(the build uses its last good snapshot), and the warehouse and site are built into staging files
and swapped in only if the build succeeds and the catalogue did not shrink by more than 10%.
Each run writes `logs/last_run.json` (status, failed sources) and per-source logs in `logs/`.

**Deploy.** Production runs on a single Ubuntu droplet:
- nginx serves `warehouse/portal/` as the site, the DuckDB file under `/data/`, and the Parquet
  files under `/export/`.
- Cron runs `scripts/refresh.sh` daily, `--weekly` on Sundays and `--monthly` on the 1st.
- Plan for about 2.5 GB of memory during the build.

## Layout

```
ingest/       one adapter per source -> warehouse/bronze/ (committed snapshots)
pipeline.py   bronze -> silver -> gold, loads DuckDB, applies the semantic layer
catalog.py    merges all sources into catalog + observations, reconciles overlaps
semantic/     data model (model.yml), views (views.sql), agent instructions
portal.py     builds the Brazil Monitoring site (portal_app.html)
registry/     metric registry, political calendar
scripts/      refresh.sh (ingest + build), used by cron
```

## Sources and license

Data belongs to its publishers. Each series carries its source in `catalog.source`, so cite the
publisher when you use a series.
