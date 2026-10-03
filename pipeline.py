"""pipeline.py — Brazil macro registry warehouse (bronze -> silver -> gold).

Registry-driven: registry/brazil_macro_data_allocation_metrics.csv is the source
of truth for metric semantics; registry/source_map.yml resolves each metric_id to
a Dateno timeseries (Tier 1) or a native/manual source (Tier 2/3).

Layers:
  bronze  warehouse/bronze/<ts_id>.csv         raw Dateno exports (as pulled)
  silver  warehouse/silver/fact_time_series     normalized long facts (matches
                                                 the registry's normalized_table)
  gold    warehouse/gold/derived_metrics         annual-feasible derived metrics
          warehouse/gold/book_scorecard          evidence vs Davidson's 2012 bets
  dq      dq/dq_report.csv                        freshness/null/range checks

Warehouse engine: DuckDB over parquet (warehouse/brazil_macro.duckdb).
Run:  python3 pipeline.py
"""
from __future__ import annotations
import os, pathlib, datetime as dt
import duckdb, yaml, pandas as pd
import hypotheses
import catalog

ROOT = pathlib.Path(__file__).resolve().parent
BRONZE = ROOT / "warehouse" / "bronze"
SILVER = ROOT / "warehouse" / "silver"
GOLD = ROOT / "warehouse" / "gold"
DQ = ROOT / "dq"
DB = ROOT / "warehouse" / "brazil_macro.duckdb"
REGISTRY_CSV = ROOT / "registry" / "brazil_macro_data_allocation_metrics.csv"
SOURCE_MAP = ROOT / "registry" / "source_map.yml"
# As-of date for freshness checks. Injectable for reproducible rebuilds
# (BRAZIL_MACRO_AS_OF=YYYY-MM-DD); defaults to today.
RUN_TS = os.environ.get("BRAZIL_MACRO_AS_OF", dt.date.today().isoformat())

for d in (SILVER, GOLD, DQ):
    d.mkdir(parents=True, exist_ok=True)


def load_maps():
    with open(SOURCE_MAP) as fh:
        smap = yaml.safe_load(fh)
    reg = pd.read_csv(REGISTRY_CSV)
    tier1 = smap.get("tier1", {})
    # ts_id -> (metric_id, unit, note)
    ts_to_metric = {v["ts_id"]: (m, v.get("unit"), v.get("note", "")) for m, v in tier1.items()}
    reg_meta = reg.set_index("metric_id")[["metric_name", "theme", "source_id"]].to_dict("index")
    return smap, tier1, ts_to_metric, reg_meta


SCHEMA = ["metric_id", "entity_id", "metric_name", "theme", "source_id", "resolved_source",
          "freq", "date", "year", "value", "unit", "ingested_via", "load_ts"]
COUNTRY = "BR"  # entity_id for country-level series; companies use their own key


def _silver_wb(ts_to_metric, reg_meta) -> list:
    """Dateno World Bank annual exports -> long facts (date = year-12-31)."""
    frames = []
    for csv in sorted(BRONZE.glob("*.csv")):
        ts_id = csv.stem
        if ts_id not in ts_to_metric:
            continue  # unmapped bronze file — skip, reported by coverage
        metric_id, unit, _ = ts_to_metric[ts_id]
        meta = reg_meta.get(metric_id, {})
        raw = pd.read_csv(csv)
        raw = raw[raw["value"].notna()].copy()
        raw["year"] = raw["date"].astype(int)
        frames.append(pd.DataFrame({
            "metric_id": metric_id, "entity_id": COUNTRY,
            "metric_name": meta.get("metric_name", raw["indicator_name"].iloc[0] if len(raw) else metric_id),
            "theme": meta.get("theme", "unknown"),
            "source_id": meta.get("source_id", "dateno_wb"),
            "resolved_source": f"dateno:wb/{ts_id}",
            "freq": "annual",
            "date": raw["year"].astype(str) + "-12-31",
            "year": raw["year"],
            "value": raw["value"].astype(float),
            "unit": unit,
            "ingested_via": "dateno_rest_export",
            "load_ts": RUN_TS,
        }))
    return frames


def _silver_native() -> list:
    """Native canonical bronze (BCB, ComexStat, ONS, B3, CVM, ...) -> long facts.

    Reads bronze/native (country series) and bronze/companies (entity series).
    Lineage comes from each file's own source_id; empty files are skipped."""
    frames = []
    files = sorted((BRONZE / "native").glob("*.csv")) + sorted((BRONZE / "companies").glob("*.csv"))
    for csv in files:
        raw = pd.read_csv(csv, dtype={"date": str})
        raw = raw[raw["value"].notna()].copy()
        if raw.empty:
            print(f"[warn] empty bronze file skipped: {csv.relative_to(ROOT)}")
            continue
        ent = raw["entity_id"].fillna(COUNTRY) if "entity_id" in raw else COUNTRY
        raw["year"] = raw["date"].str[:4].astype(int)
        frames.append(pd.DataFrame({
            "metric_id": raw["metric_id"], "entity_id": ent, "metric_name": raw["metric_name"],
            "theme": raw["theme"], "source_id": raw["source_id"],
            "resolved_source": raw["source_id"], "freq": raw["freq"],
            "date": raw["date"], "year": raw["year"],
            "value": raw["value"].astype(float), "unit": raw["unit"],
            "ingested_via": "native_api", "load_ts": RUN_TS,
        }))
    return frames


def _series(silver, metric_id, entity=COUNTRY):
    """Return a date-indexed value Series for one metric (sorted)."""
    s = silver[(silver.metric_id == metric_id) & (silver.entity_id == entity)].copy()
    if s.empty:
        return None
    s["dt"] = pd.to_datetime(s["date"])
    return s.sort_values("dt").set_index("dt")["value"]


def _emit(silver, metric_id, name, theme, unit, values, freq="monthly", source="derived_native",
          entity=COUNTRY):
    """Build a silver-shaped frame for a computed series."""
    if values is None:
        return None
    v = values.dropna()
    if v.empty:
        return None
    return pd.DataFrame({
        "metric_id": metric_id, "entity_id": entity, "metric_name": name, "theme": theme,
        "source_id": "derived", "resolved_source": source, "freq": freq,
        "date": v.index.strftime("%Y-%m-%d"), "year": v.index.year,
        "value": v.to_numpy(), "unit": unit,
        "ingested_via": "pipeline_derive", "load_ts": RUN_TS,
    })


def derive_native_series(silver) -> list:
    """Monthly series derived from native BCB SGS inputs (appended to silver)."""
    out = []
    nfsp_p = _series(silver, "primary_result_nfsp")   # +=deficit
    nfsp_n = _series(silver, "nominal_deficit_gdp")    # +=deficit
    if nfsp_p is not None:  # primary BALANCE = -(NFSP primary), +=surplus
        out.append(_emit(silver, "primary_balance_gdp", "Primary balance / GDP (+=surplus)",
                         "fiscal", "pct_gdp", -nfsp_p))
    if nfsp_p is not None and nfsp_n is not None:  # interest = nominal - primary (NFSP)
        out.append(_emit(silver, "interest_bill_gdp", "Interest bill / GDP",
                         "fiscal", "pct_gdp", (nfsp_n - nfsp_p).dropna()))
    for base, mid, nm in [("household_credit_balance", "household_credit_growth",
                           "Household credit growth (YoY)"),
                          ("corporate_credit_balance", "corporate_credit_growth",
                           "Corporate credit growth (YoY)")]:
        bal = _series(silver, base)
        if bal is not None and len(bal) > 12:
            out.append(_emit(silver, mid, nm, "domestic_demand", "pct_yoy",
                             (bal.pct_change(12) * 100).dropna()))
    # trade_balance (US$ FOB) = total exports - total imports (ComexStat, monthly)
    ex, im = _series(silver, "exports_total"), _series(silver, "imports_total")
    if ex is not None and im is not None:
        tb = (ex - im).dropna()
        out.append(_emit(silver, "trade_balance", "Trade balance (FOB)",
                         "external_trade", "usd_fob", tb))
    # real_wage_bill = employed (thousand) * real avg income (R$) -> R$ bn/month
    emp, inc = _series(silver, "employed_population"), _series(silver, "real_average_income")
    if emp is not None and inc is not None:
        wb = (emp * inc / 1e6).dropna()
        out.append(_emit(silver, "real_wage_bill", "Real wage bill (employed x real income)",
                         "labor", "brl_bn_month", wb))
    # hydro_stress_index (daily) = 0.5*(100-EAR%) + 0.5*thermal_share%  (0-100, higher=stress)
    ear, ts = _series(silver, "stored_energy_ear"), _series(silver, "thermal_generation_share")
    if ear is not None and ts is not None:
        hs = (0.5 * (100 - ear) + 0.5 * ts).dropna()
        out.append(_emit(silver, "hydro_stress_index", "Hydro stress index",
                         "energy_water", "index_0_100", hs, freq="daily"))
    # china_export_share = exports to China / total exports (monthly)
    cn = _series(silver, "exports_to_china")
    if ex is not None and cn is not None:
        out.append(_emit(silver, "china_export_share", "Exports to China (% of total)",
                         "external_trade", "pct", (cn / ex * 100).dropna()))
    # fertilizer_dependency_index = fertilizer imports / tracked agri exports (monthly)
    fert = _series(silver, "fertilizer_imports")
    agri = [_series(silver, m) for m in ["soy_exports", "beef_exports", "coffee_exports", "sugar_exports"]]
    agri = [a for a in agri if a is not None]
    if fert is not None and agri:
        agri_sum = sum(agri[1:], agri[0])
        out.append(_emit(silver, "fertilizer_dependency_index",
                         "Fertilizer imports / tracked agri exports", "derived_agriculture",
                         "ratio", (fert / agri_sum).dropna()))
    # potash_import_dependency_proxy = potash imports / total fertilizer imports (monthly)
    pot = _series(silver, "potash_imports")
    if pot is not None and fert is not None:
        out.append(_emit(silver, "potash_import_dependency_proxy",
                         "Potash imports / fertilizer imports", "agriculture_risk",
                         "pct", (pot / fert * 100).dropna()))
    # ibovespa_usd = Ibovespa level / BRL-USD (foreign-investor view), daily
    ibov, fx = _series(silver, "ibovespa_level"), _series(silver, "brl_usd")
    if ibov is not None and fx is not None:
        out.append(_emit(silver, "ibovespa_usd", "Ibovespa in USD", "market_repricing",
                         "index_usd", (ibov / fx).dropna(), freq="daily"))
    # oil_production_yoy = YoY % change of monthly oil production
    oil = _series(silver, "oil_production")
    if oil is not None and len(oil) > 12:
        out.append(_emit(silver, "oil_production_yoy", "Oil production YoY growth",
                         "oil_gas", "pct_yoy", (oil.pct_change(12) * 100).dropna()))
    return [f for f in out if f is not None]


def build_silver(ts_to_metric, reg_meta) -> pd.DataFrame:
    wb = _silver_wb(ts_to_metric, reg_meta)
    native = _silver_native()
    if not (wb or native):
        raise SystemExit("No bronze found. Run ingest/dateno_pull.py (and bcb_sgs.py).")
    native_ids = {m for f in native for m in f["metric_id"].unique()}
    # Native is the base: where a WB annual series overlaps a native one, keep the
    # WB copy only as a cross-check under a *_wb_annual id.
    for f in wb:
        mid = f["metric_id"].iloc[0]
        if mid in native_ids:
            f["metric_id"] = f"{mid}_wb_annual"
            f["metric_name"] = f["metric_name"] + " (WB annual, cross-check)"
    silver = pd.concat(wb + native, ignore_index=True)
    silver = pd.concat([silver] + derive_native_series(silver), ignore_index=True)
    silver = pd.concat([silver] + hypotheses.derive_company_series(silver, RUN_TS),
                       ignore_index=True)
    silver = silver[SCHEMA].sort_values(["metric_id", "entity_id", "date"]).reset_index(drop=True)
    silver.to_parquet(SILVER / "fact_time_series.parquet", index=False)
    return silver


def latest(df, metric_id, entity=COUNTRY):
    s = df[(df.metric_id == metric_id) & (df.entity_id == entity)]
    return None if s.empty else s.sort_values("date").iloc[-1]


def trailing_12m_ipca(silver):
    """Compound the last 12 monthly IPCA %% changes into a 12-month inflation rate."""
    s = silver[(silver.metric_id == "ipca_monthly") & (silver.entity_id == COUNTRY)].sort_values("date")
    if len(s) < 12:
        return None
    last12 = s["value"].tail(12).to_numpy()
    factor = 1.0
    for v in last12:
        factor *= (1.0 + v / 100.0)
    return (factor - 1.0) * 100.0


def mean_window(df, metric_id, y0, y1):
    s = df[(df.metric_id == metric_id) & (df.entity_id == COUNTRY) & (df.year >= y0) & (df.year <= y1)]
    return None if s.empty else float(s["value"].mean())


def real_rate_inputs(silver) -> dict:
    """Single definition of r and g used everywhere (derived table AND scorecard):
    r = Selic target - expected 12m IPCA (Focus; falls back to realized 12m IPCA),
    g = expected real GDP growth (Focus; falls back to the latest realized year)."""
    selic = latest(silver, "selic_target")
    fipca, ipca12 = latest(silver, "focus_ipca_12m"), latest(silver, "ipca_12m")
    infl = fipca if fipca is not None else ipca12
    fg, g = latest(silver, "focus_gdp_growth"), latest(silver, "gdp_real_growth")
    grow = fg if fg is not None else g
    return dict(
        real_rate=(selic.value - infl.value) if selic is not None and infl is not None else None,
        growth=grow.value if grow is not None else None,
        infl_basis="Focus expected IPCA 12m" if fipca is not None else "IPCA 12m (ex-post)",
        growth_basis="Focus expected GDP growth" if fg is not None else "realized GDP growth",
        year=int(selic.year) if selic is not None else None)


def fiscal_gap(silver, rr) -> dict | None:
    """Primary surplus needed to stabilize gross debt/GDP, minus the actual one."""
    debt, pbal = latest(silver, "gross_public_debt_gdp"), latest(silver, "primary_balance_gdp")
    if debt is None or pbal is None or rr["real_rate"] is None or rr["growth"] is None:
        return None
    r, g = rr["real_rate"] / 100, rr["growth"] / 100
    required = debt.value * (r - g) / (1 + g)  # % of GDP
    return dict(year=int(debt.year), debt=debt.value, primary=pbal.value,
                required=required, gap=required - pbal.value)


def trailing_12m_share(silver, parts, total="exports_total"):
    """Share (%) of `parts` in `total` over the last 12 months both have (seasonality-safe)."""
    tot = _series(silver, total)
    ser = [x for p in parts if (x := _series(silver, p)) is not None]
    if tot is None or not ser:
        return None
    df = pd.concat([tot.rename("tot")] + [x.rename(i) for i, x in enumerate(ser)], axis=1).dropna()
    if len(df) < 12:
        return None
    last = df.tail(12)
    return dict(share=last.drop(columns="tot").sum().sum() / last["tot"].sum() * 100,
                end=last.index[-1], start=last.index[0])


def build_derived(silver) -> pd.DataFrame:
    rows = []
    # investment_rate_gap = target(20) - investment_rate_gdp   (T1-feasible)
    inv = latest(silver, "investment_rate_gdp")
    if inv is not None:
        rows.append(dict(derived_metric="investment_rate_gap", year=int(inv.year),
                         value=round(20.0 - inv.value, 3), unit="pct_gdp_pts",
                         logic="target 20% - GFCF/GDP", status="computed"))
    else:
        rows.append(dict(derived_metric="investment_rate_gap", year=None, value=None,
                         unit="pct_gdp_pts", logic="target 20% - GFCF/GDP",
                         status="pending: investment_rate_gdp not ingested"))
    # fdi_coverage_current_account_deficit = FDI / |CA| when CA<0   (T1-feasible)
    fdi, ca = latest(silver, "fdi_idp"), latest(silver, "current_account_gdp")
    if fdi is not None and ca is not None and ca.value < 0:
        rows.append(dict(derived_metric="fdi_coverage_current_account_deficit",
                         year=int(min(fdi.year, ca.year)),
                         value=round(fdi.value / abs(ca.value), 3), unit="ratio",
                         logic="FDI%GDP / |CA%GDP| (CA<0)", status="computed"))
    else:
        rows.append(dict(derived_metric="fdi_coverage_current_account_deficit", year=None,
                         value=None, unit="ratio", logic="FDI%GDP / |CA%GDP| (CA<0)",
                         status="pending or CA>=0"))
    # real_policy_rate = Selic target - Focus expected IPCA 12m (ex-ante; registry formula)
    rr = real_rate_inputs(silver)
    rpr, g_val = rr["real_rate"], rr["growth"]
    if rpr is not None:
        rows.append(dict(derived_metric="real_policy_rate", year=rr["year"],
                         value=round(rpr, 3), unit="pct_pa",
                         logic=f"Selic target - {rr['infl_basis']}", status="computed"))
    else:
        rows.append(dict(derived_metric="real_policy_rate", year=None, value=None,
                         unit="pct_pa", logic="Selic - expected IPCA 12m", status="pending"))
    # r_g_spread = real policy rate - expected real GDP growth (both forward-looking)
    if rpr is not None and g_val is not None:
        rows.append(dict(derived_metric="r_g_spread", year=rr["year"],
                         value=round(rpr - g_val, 3), unit="pct_pts",
                         logic=f"real_policy_rate - {rr['growth_basis']}", status="computed"))
    # debt_stabilizing_primary_surplus_gap (the book's key fiscal-sustainability metric)
    fs = fiscal_gap(silver, rr)
    if fs is not None:
        rows.append(dict(derived_metric="debt_stabilizing_primary_surplus_gap",
                         year=fs["year"], value=round(fs["gap"], 3), unit="pct_gdp",
                         logic="debt% x (r-g)/(1+g) - actual primary balance; +=tightening needed",
                         status="computed"))
    else:
        rows.append(dict(derived_metric="debt_stabilizing_primary_surplus_gap", year=None,
                         value=None, unit="pct_gdp", logic="debt*(r-g)/(1+g) - primary balance",
                         status="pending"))
    # credit_impulse = 12m change in credit/GDP (proxy for credit flow into demand)
    cg = _series(silver, "credit_gdp")
    if cg is not None and len(cg) > 12:
        ci = (cg.iloc[-1] - cg.iloc[-13])
        rows.append(dict(derived_metric="credit_impulse", year=int(cg.index[-1].year),
                         value=round(float(ci), 3), unit="pct_gdp_pts_yoy",
                         logic="credit/GDP(t) - credit/GDP(t-12m)", status="computed"))
    # export_concentration_index = tracked commodity groups / total exports (trailing 12m)
    prods = ["soy_exports", "oil_exports", "iron_ore_exports", "beef_exports",
             "coffee_exports", "sugar_exports"]
    ec = trailing_12m_share(silver, prods)
    if ec is not None:
        rows.append(dict(derived_metric="export_concentration_index",
                         year=int(ec["end"].year), value=round(float(ec["share"]), 2),
                         unit="pct_of_exports",
                         logic="6 tracked commodity groups / total exports, trailing 12 months",
                         status="computed"))
    out = pd.DataFrame(rows)
    out.to_parquet(GOLD / "derived_metrics.parquet", index=False)
    return out


def build_scorecard(silver) -> pd.DataFrame:
    """Compute evidence for the book's research-line verdicts from landed data."""
    rows = []

    # Hyperinflation inoculation — Real Plan disinflation
    cpi94 = silver[(silver.metric_id == "ipca_headline") & (silver.year == 1994)]
    cpi_last = latest(silver, "ipca_headline")
    if not cpi94.empty and cpi_last is not None:
        rows.append(dict(
            thread="Hyperinflation as inoculation", theme="inflation",
            evidence=f"CPI {int(cpi94.iloc[0].year)}={cpi94.iloc[0].value:,.0f}% -> "
                     f"{int(cpi_last.year)}={cpi_last.value:.1f}%",
            reading="Real Plan disinflation confirmed; low-inflation regime durable to 2023."))

    # Commodity supercycle vs structural rise — boom vs post-boom growth
    boom = mean_window(silver, "gdp_real_growth", 2004, 2010)
    post = mean_window(silver, "gdp_real_growth", 2015, 2023)
    if boom is not None and post is not None:
        rows.append(dict(
            thread="Commodity supercycle or structural rise", theme="macro_activity",
            evidence=f"avg GDP growth 2004-2010={boom:.2f}% vs 2015-2023={post:.2f}%",
            reading="Boom-era growth far exceeds post-2014; favors cyclical (supercycle) reading."))

    # External balance / financing quality
    ca = latest(silver, "current_account_gdp")
    fdi = latest(silver, "fdi_idp")
    if ca is not None and fdi is not None:
        cov = fdi.value / abs(ca.value) if ca.value < 0 else float("inf")
        rows.append(dict(
            thread="External financing quality", theme="external_sector",
            evidence=f"CA={ca.value:.2f}%GDP, FDI={fdi.value:.2f}%GDP ({int(ca.year)}); "
                     f"FDI/|CA|={cov:.2f}",
            reading="FDI more than covers the current-account deficit — high-quality financing."))

    # Fiscal sustainability — high real rates + primary deficit => rising debt
    rr = real_rate_inputs(silver)
    fs = fiscal_gap(silver, rr)
    ib = latest(silver, "interest_bill_gdp")
    if fs is not None and ib is not None:
        rows.append(dict(
            thread="Fiscal sustainability / structurally high real rates", theme="fiscal",
            evidence=f"gross debt {fs['debt']:.0f}%GDP, interest bill {ib.value:.1f}%GDP, "
                     f"primary {fs['primary']:+.1f}%GDP; real rate {rr['real_rate']:.1f}% vs "
                     f"growth {rr['growth']:.1f}% -> stabilizing gap {fs['gap']:+.1f}pts",
            reading="Real rate >> growth with a primary deficit: debt path needs a large "
                    "fiscal tightening — Davidson's 'high interest bill' risk, quantified."))

    # Commodity export concentration — soy/oil/iron-ore dominance (trailing 12 months)
    ec = trailing_12m_share(silver, ["soy_exports", "oil_exports", "iron_ore_exports"])
    if ec is not None:
        rows.append(dict(
            thread="Commodity export concentration", theme="external_trade",
            evidence=f"soy+oil+iron-ore = {ec['share']:.0f}% of exports over the 12 months to "
                     f"{ec['end'].strftime('%Y-%m')}",
            reading="Exports concentrated in a few commodities — China-demand & price "
                    "sensitivity, the cyclical core of the supercycle reading."))

    # Pre-salt oil — the book's "Rio is the new Houston" energy bet
    oil = _series(silver, "oil_production")
    if oil is not None:
        o2010 = oil[(oil.index >= "2010-01-01") & (oil.index <= "2010-12-31")].mean()
        rows.append(dict(
            thread="Pre-salt oil — Rio is the new Houston", theme="oil_gas",
            evidence=f"oil output {oil.iloc[-1]:,.0f} kbbl/d ({oil.index[-1].strftime('%Y-%m')}), "
                     f"~{oil.iloc[-1]/o2010:.1f}x the 2010 average ({o2010:,.0f})",
            reading="Brazil DID become a major oil producer via pre-salt — the one energy "
                    "bet Davidson got right, even as his peak-oil/$200-oil call failed."))

    # China demand dependence — single-partner concentration of the export engine
    cn = _series(silver, "china_export_share")
    nb = latest(silver, "niobium_exports")
    if cn is not None:
        recent = cn[cn.index >= "2024-01-01"].mean()
        rows.append(dict(
            thread="Brazil vs China — demand dependence", theme="external_trade",
            evidence=f"China = {recent:.0f}% of exports (2024+ avg), up from {cn.iloc[:12].mean():.0f}% "
                     f"in {cn.index[0].year}" + (f"; niobium ~US${nb.value/1e6:.0f}M/mo" if nb is not None else ""),
            reading="The export engine increasingly rides on one buyer (China) — the "
                    "'Brazil vs China' bet cuts both ways: customer, not just rival."))

    # Hydropower dependence as vulnerability — 2021 drought trough + wind/solar hedge
    hsh = _series(silver, "hydro_generation_share")
    ear = _series(silver, "stored_energy_ear")
    wss = _series(silver, "wind_solar_generation_share")
    if hsh is not None and ear is not None and wss is not None:
        ear21 = ear[(ear.index >= "2021-01-01") & (ear.index <= "2021-12-31")]
        trough = f"{ear21.min():.0f}%" if not ear21.empty else "n/a"
        rows.append(dict(
            thread="Hydropower dependence as vulnerability", theme="energy_water",
            evidence=f"hydro share {hsh.iloc[-1]:.0f}% (avg {hsh.mean():.0f}%); 2021 EAR trough "
                     f"{trough}; wind+solar now {wss.iloc[-1]:.0f}%",
            reading="Grid still hydro-led and drought-exposed (2021 reservoir trough); "
                    "wind+solar is the real diversification hedge, not a given dividend."))

    # Demographic window closing — TFR vs 2.1 replacement, and crossing year
    tfr_s = silver[silver.metric_id == "fertility_rate"].sort_values("year")
    tfr_last = latest(silver, "fertility_rate")
    if tfr_last is not None:
        below = tfr_s[tfr_s.value < 2.1]
        crossed = int(below.year.min()) if not below.empty else None
        rows.append(dict(
            thread="The demographic window is closing", theme="demography",
            evidence=f"TFR {int(tfr_last.year)}={tfr_last.value:.2f} "
                     f"(crossed below 2.1 replacement in {crossed})",
            reading="Fertility below replacement and falling — demographic dividend is closing."))

    # Investment-ceiling — GFCF/GDP far below the ~20%+ a rerate needs
    inv = latest(silver, "investment_rate_gdp")
    if inv is not None:
        rows.append(dict(
            thread="Resource determinism vs institutions (investment ceiling)",
            theme="investment_productivity",
            evidence=f"GFCF/GDP {int(inv.year)}={inv.value:.1f}% (vs ~20% target; gap "
                     f"{20.0 - inv.value:+.1f}pts)",
            reading="Chronically low investment caps the growth ceiling regardless of endowments."))

    # Virtual water / deforestation tradeoff — forest-area change since 1990
    fa = silver[silver.metric_id == "forest_area_km2"].sort_values("year")
    if len(fa) >= 2:
        f0, f1 = fa.iloc[0], fa.iloc[-1]
        pct = (f1.value - f0.value) / f0.value * 100
        rows.append(dict(
            thread="Virtual water and the deforestation tradeoff", theme="environment_risk",
            evidence=f"Forest area {int(f0.year)}={f0.value:,.0f} -> {int(f1.year)}="
                     f"{f1.value:,.0f} km2 ({pct:+.1f}%)",
            reading="Sustained forest loss degrades the water cycle underpinning the agri/endowment thesis."))

    out = pd.DataFrame(rows)
    out.to_parquet(GOLD / "book_scorecard.parquet", index=False)
    return out


def build_dq(silver, tier1) -> pd.DataFrame:
    """Per-metric coverage/freshness across all frequencies + missing Tier-1."""
    run = pd.Timestamp(RUN_TS)
    # expected max staleness (days) before a series is flagged stale, by freq
    # WB annual data is structurally ~2yr lagged; only flag genuinely-behind series.
    tol = {"daily": 10, "weekly": 21, "monthly": 100, "quarterly": 200, "annual": 1300, "event": 4000}
    rows = []
    for (metric_id, entity_id), g in silver.groupby(["metric_id", "entity_id"]):
        freq = g["freq"].iloc[0]
        last_date = pd.Timestamp(g["date"].max())
        stale_days = (run - last_date).days
        rows.append(dict(
            metric_id=metric_id, entity_id=entity_id, freq=freq, n_obs=int(len(g)),
            first=g["date"].min(), last=g["date"].max(),
            stale_days=stale_days,
            check="STALE" if stale_days > tol.get(freq, 550) else "fresh"))
    for metric_id in tier1:  # surface any mapped-but-not-ingested Tier-1 series
        if metric_id not in set(silver.metric_id):
            rows.append(dict(metric_id=metric_id, entity_id=COUNTRY, freq="annual", n_obs=0, first=None,
                             last=None, stale_days=None, check="NOT_INGESTED"))
    out = pd.DataFrame(rows).sort_values(["freq", "metric_id"]).reset_index(drop=True)
    out.to_csv(DQ / "dq_report.csv", index=False)
    return out


def build_company_gold(silver) -> pd.DataFrame:
    """Wide entity x quarter table of company fundamentals (gold/company_metrics)."""
    q = silver[(silver.entity_id.isin(list(hypotheses.COMPANIES))) & (silver.freq == "quarterly")]
    if q.empty:
        out = pd.DataFrame(columns=["entity_id", "company", "quarter_end"])
    else:
        out = (q.pivot_table(index=["entity_id", "date"], columns="metric_id", values="value")
                .reset_index().rename(columns={"date": "quarter_end"}))
        out.insert(1, "company", out.entity_id.map(lambda e: hypotheses.COMPANIES[e][0]))
    out.to_parquet(GOLD / "company_metrics.parquet", index=False)
    return out


def build_hypotheses(silver) -> pd.DataFrame:
    out = hypotheses.build_hypothesis_tests(silver)
    out.to_parquet(GOLD / "hypothesis_tests.parquet", index=False)
    return out


def persist_duckdb(silver, derived, scorecard, dq, company=None, hyp=None):
    con = duckdb.connect(str(DB))
    if company is not None:
        con.execute("CREATE OR REPLACE TABLE company_metrics AS SELECT * FROM company")
    if hyp is not None:
        con.execute("CREATE OR REPLACE TABLE hypothesis_tests AS SELECT * FROM hyp")
    con.execute("CREATE OR REPLACE TABLE fact_time_series AS SELECT * FROM silver")
    con.execute("CREATE OR REPLACE TABLE derived_metrics AS SELECT * FROM derived")
    con.execute("CREATE OR REPLACE TABLE book_scorecard AS SELECT * FROM scorecard")
    con.execute("CREATE OR REPLACE TABLE dq_report AS SELECT * FROM dq")
    con.close()


def main():
    smap, tier1, ts_to_metric, reg_meta = load_maps()
    silver = build_silver(ts_to_metric, reg_meta)
    derived = build_derived(silver)
    scorecard = build_scorecard(silver)
    dq = build_dq(silver, tier1)
    company = build_company_gold(silver)
    hyp = build_hypotheses(silver)
    persist_duckdb(silver, derived, scorecard, dq, company, hyp)
    # merged, research-ready layer: every series (native + Dateno/World Bank/ILO) in one
    # catalog + one long observations table, with source reconciliation
    cat, obs, rec = catalog.build(as_of=RUN_TS, used_in=catalog.used_in_from(hyp))
    con = duckdb.connect(str(DB))
    for name, df in (("catalog", cat), ("observations", obs), ("reconciliation", rec)):
        con.register("df_" + name, df)
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM df_{name}")
    ex_p = GOLD / "excluded_series.parquet"
    if ex_p.exists():  # curated-out survey one-offs, with reason
        con.execute(f"CREATE OR REPLACE TABLE excluded_series AS SELECT * FROM read_parquet('{ex_p}')")
    dims_p = ROOT / "warehouse" / "export" / "observations_dims.parquet"
    if dims_p.exists():  # ILO disaggregations (sex, age, ...) behind the headline series
        con.execute(f"CREATE OR REPLACE TABLE observations_dims AS SELECT * FROM read_parquet('{dims_p}')")
    for name in ("political_terms", "political_events"):  # registry/<name>.csv, public record
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_csv_auto('{ROOT / 'registry' / (name + '.csv')}')")
    con.execute((ROOT / "semantic" / "views.sql").read_text())  # semantic layer (model.yml)
    con.execute("CREATE OR REPLACE VIEW latest AS SELECT c.series_id, c.title, c.topic, c.source, "
                "c.unit, c.last AS date, c.last_value AS value, c.status FROM catalog c")
    con.close()
    print(f"Merged catalog: {len(cat):,} series, {len(obs):,} observations, "
          f"{len(rec)} reconciled concept pairs")

    reg_n = len(pd.read_csv(REGISTRY_CSV))
    t1, t2, t3 = len(tier1), len(smap.get("tier2", {}).get("metric_ids", [])), \
        len(smap.get("tier3", {}).get("metric_ids", []))
    present = set(silver.metric_id.unique())
    t1_in = len(present & set(tier1))
    native = sorted(silver[silver.freq != "annual"].metric_id.unique())
    by_freq = silver.groupby("freq").size().to_dict()

    print("=" * 72)
    print("BRAZIL MACRO REGISTRY — warehouse build complete")
    print("=" * 72)
    print(f"Registry metrics            : {reg_n}")
    print(f"Resolved -> T1/T2/T3        : {t1} / {t2} / {t3}")
    print(f"Tier-1 (annual) ingested    : {t1_in}/{t1}")
    print(f"Tier-2 native ingested      : {len(native)}  ({', '.join(native)})")
    print(f"Silver rows                 : {len(silver)}  by freq: {by_freq}")
    print(f"DuckDB                      : {DB.relative_to(ROOT)}")
    print("\n--- Coverage & freshness (dq_report) ---")
    print(dq.to_string(index=False))
    print("\n--- Derived metrics ---")
    print(derived.to_string(index=False))
    print("\n--- Book scorecard (computed evidence vs Davidson's 2012 bets) ---")
    for _, r in scorecard.iterrows():
        print(f"\n• {r.thread}  [{r.theme}]")
        print(f"    evidence: {r.evidence}")
        print(f"    reading : {r.reading}")
    print("\nDone.")


if __name__ == "__main__":
    main()
