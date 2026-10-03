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

-- Every series on an annual basis, using its roll-up rule (catalog.agg): flows are summed
-- (exports, deaths, revenue), stocks and running totals take the year's last value (debt,
-- balances, reserves, 12-month sums), rates/prices/indices are averaged. is_complete marks
-- past years with a full set of observations (12 months, 4 quarters, ~50 weeks, ~200 days);
-- the current year is never complete.
CREATE OR REPLACE VIEW v_annual AS
WITH y AS (
  SELECT o.series_id, o.title, o.unit, o.topic, o.source, o.entity_name, o.freq, c.agg,
         EXTRACT(year FROM o.date)::INTEGER AS year, o.date, o.value
  FROM v_observations o JOIN catalog c USING (series_id))
SELECT series_id, title, unit, topic, source, entity_name, agg, year,
       CASE agg WHEN 'sum' THEN SUM(value) WHEN 'last' THEN arg_max(value, date) ELSE AVG(value) END AS value,
       COUNT(*) AS n_obs_in_year,
       year < EXTRACT(year FROM current_date)          -- the current year is never complete
       AND CASE freq WHEN 'monthly' THEN COUNT(*) >= 12 WHEN 'quarterly' THEN COUNT(*) >= 4
                     WHEN 'weekly' THEN COUNT(*) >= 50 WHEN 'daily' THEN COUNT(*) >= 200 ELSE TRUE END AS is_complete
FROM y
GROUP BY series_id, title, unit, topic, source, entity_name, freq, agg, year;

-- Year-on-year % change between CONSECUTIVE complete years only.
CREATE OR REPLACE VIEW v_annual_yoy AS
WITH a AS (
  SELECT *, LAG(value) OVER w AS prev_value, LAG(year) OVER w AS prev_year, LAG(is_complete) OVER w AS prev_complete
  FROM v_annual WINDOW w AS (PARTITION BY series_id ORDER BY year))
SELECT series_id, title, unit, year, value, 100 * (value / prev_value - 1) AS yoy_pct
FROM a WHERE is_complete AND prev_complete AND prev_year = year - 1 AND abs(prev_value) > 1e-9;

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

-- Related datasets: up to 10 per series, ranked, with the reason and a one-line explanation
-- (same_concept | lineage | company | entity | curated | comove | family | text).
CREATE OR REPLACE VIEW v_related AS
SELECT r.series_id, r.pos, r.related_id, c.title AS related_title, c.dataset AS related_dataset,
       r.reason, r.score, r.explanation
FROM related_series r JOIN catalog c ON c.series_id = r.related_id;

-- ILO breakdowns with readable labels (sex, age, occupation, economic activity, ...).
CREATE OR REPLACE VIEW v_observations_dims AS
SELECT d.series_id, CAST(d.date AS DATE) AS date, d.value, d.classif1,
       l1.label AS sex_or_dim1, d.classif2,
       (SELECT string_agg(coalesce(l.label, x), ' | ') FROM unnest(string_split(d.classif2, '|')) AS u(x)
        LEFT JOIN dim_labels l ON l.code = x) AS breakdown
FROM observations_dims d LEFT JOIN dim_labels l1 ON l1.code = d.classif1;
