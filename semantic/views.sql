-- semantic/views.sql — the semantic layer over the Brazil Monitoring warehouse.
-- Created by pipeline.py after the base tables load. Every view is read-only and
-- documented in semantic/model.yml. Agents should query these views first.

-- Every observation with its series metadata (one row per series x date).
CREATE OR REPLACE VIEW v_observations AS
SELECT o.series_id, CAST(o.date AS DATE) AS date, o.value,
       c.title, c.unit, c.freq, c.topic, c.subtopic, c.source, c.database,
       c.entity_id, c.entity_name, c.role, c.concept
FROM observations o JOIN catalog c USING (series_id);

-- Latest value of every series, with freshness.
CREATE OR REPLACE VIEW v_latest AS
SELECT series_id, title, topic, source, entity_name, unit, freq,
       CAST(last AS DATE) AS date, last_value AS value, status, role
FROM catalog;

-- Every series on an annual basis: mean of the year's observations (annual series
-- pass through). Use for cross-series comparison at a common frequency.
CREATE OR REPLACE VIEW v_annual AS
SELECT series_id, title, unit, topic, source, entity_name,
       EXTRACT(year FROM date)::INTEGER AS year,
       AVG(value) AS value, COUNT(*) AS n_obs_in_year
FROM v_observations
GROUP BY ALL;

-- Year-on-year % change for every annual-basis series.
CREATE OR REPLACE VIEW v_annual_yoy AS
SELECT series_id, title, unit, year, value,
       100 * (value / LAG(value) OVER (PARTITION BY series_id ORDER BY year) - 1) AS yoy_pct
FROM v_annual;

-- Each observation tagged with the president in office and their lean.
CREATE OR REPLACE VIEW v_politics AS
SELECT o.*, p.president, p.party, p.lean
FROM v_observations o
LEFT JOIN political_terms p ON o.date >= p.start AND o.date < p."end";

-- Averages of every series by presidential term (only terms with data).
CREATE OR REPLACE VIEW v_by_term AS
SELECT series_id, title, unit, president, lean, MIN(date) AS first_date, MAX(date) AS last_date,
       AVG(value) AS mean_value, COUNT(*) AS n_obs
FROM v_politics WHERE president IS NOT NULL
GROUP BY ALL;

-- Company fundamentals by quarter (CVM filings; USD at quarter-average BRL/USD).
CREATE OR REPLACE VIEW v_company_quarterly AS
SELECT entity_id, company, CAST(quarter_end AS DATE) AS quarter_end,
       revenue_brl, revenue_usd_bn, ebit_brl, net_income_brl, net_income_usd_bn,
       gross_debt_brl, cash_brl, net_debt_brl_bn, capex_brl, dividends_paid_brl
FROM company_metrics;

-- Where two sources measure the same concept: canonical vs alternate and their agreement.
CREATE OR REPLACE VIEW v_reconciliation AS
SELECT r.*, c1.title AS canonical_title, c2.title AS alternate_title
FROM reconciliation r
LEFT JOIN catalog c1 ON c1.series_id = r.canonical
LEFT JOIN catalog c2 ON c2.series_id = r.alternate;

-- Searchable list of series (use ILIKE on title/description/topic).
CREATE OR REPLACE VIEW v_search AS
SELECT series_id, title, topic, subtopic, source, database, entity_name, freq, unit,
       CAST(first AS DATE) AS first_date, CAST(last AS DATE) AS last_date, n_obs, role, description
FROM catalog;
