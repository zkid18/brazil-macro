"""portal.py — build "Brazil Monitoring", the browsable data platform over the warehouse.

Every series in gold/catalog (native BCB, IBGE, ComexStat, ANP, ONS, B3, CVM, Tesouro,
IPEAData and every Brazil series in Dateno's World Bank and ILO namespaces) is searchable,
filterable, charted and queryable with SQL in the browser.

Output: warehouse/portal/
  index.html          the app (body fragment; the artifact host adds the document skeleton)
  standalone.html     same app as a full document, for local use (serve the folder:
                      `python3 -m http.server -d warehouse/portal` — fetch() needs http)
  data/catalog.json   one compact record per series
  data/obs-NNN.json   observations, chunked; loaded on demand per series
  data/meta.json      reconciliation pairs, Dateno candidates for missing metrics, build facts

Run:  python3 portal.py   (after pipeline.py)
"""
from __future__ import annotations
import json, math, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
GOLD = ROOT / "warehouse" / "gold"
OUT = ROOT / "warehouse" / "portal"
DATA = OUT / "data"
CHUNK_BYTES = 1_500_000
PLOTLY = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.34.0/plotly-basic.min.js"
ALASQL = "https://cdnjs.cloudflare.com/ajax/libs/alasql/4.4.0/alasql.min.js"
FONTS = ("https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400"
         "&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap")
EPOCH = pd.Timestamp("1970-01-01")

UNIT = {  # bronze unit -> readable unit
    "pct": "%", "pct_pa": "% a year", "pct_yoy": "% year on year", "pct_mom": "% month on month",
    "pct_gdp": "% of GDP", "pct_gdp_nfsp": "% of GDP (+ = deficit)", "pct_income": "% of income",
    "pct_pts": "percentage points", "annual_pct": "% a year", "brl_per_usd": "R$ per US$",
    "bps": "basis points", "points": "index points", "index_usd": "index (US$)", "usd_fob": "US$ (FOB)",
    "usd_mn": "US$ million", "usd": "US$", "brl_mn": "R$ million", "thousand_tonnes": "thousand tonnes",
    "usd_per_t": "US$ per tonne", "kbbl_day": "thousand barrels/day", "kbd": "thousand barrels/day",
    "mm3_day": "million m³/day", "usd_per_bbl": "US$ per barrel", "brl_per_mwh": "R$ per MWh",
    "mwmed": "average MW", "index_0_100": "index 0–100", "index_2022_100": "index (2022 = 100)",
    "index_2012_100": "index (Jan 2012 = 100)", "units": "vehicles", "million_tx": "million transactions",
    "brl_bn": "R$ billion", "usd_bn": "US$ billion", "jobs": "jobs", "thousand_persons": "thousand people",
    "brl_real": "R$ a month (real)", "brl_bn_month": "R$ billion a month (real)", "gwh": "GWh",
    "brl": "R$", "brl_per_share": "R$ per share", "births_per_woman": "births per woman",
    "pct_working_age": "% of working-age pop.", "pct_population": "% of population",
    "pct_labor_force": "% of labour force", "metric_tons": "tonnes", "km2": "km²", "ratio": "ratio",
}

# Curated collections: overview pages in the centre panel. Each chart lists the series it
# draws (same unit on one chart; mixed units are rebased in the browser). Missing series
# are dropped at build time, so a collection degrades gracefully.
CO = ["PETR", "VALE", "AXIA", "SUZB", "PRIO", "ITUB"]
CURATED = [
    dict(id="overview", title="Brazil at a glance",
         desc="Policy rate, inflation, jobs, the currency and public debt: the headline macro series, each from its official publisher.",
         kpis=["selic_target", "ipca_12m", "unemployment_rate", "brl_usd", "gross_public_debt_gdp", "wb/NY.GDP.MKTP.KD.ZG.BR"],
         charts=[dict(t="Policy rate vs inflation", d="Selic target against 12-month IPCA inflation and the market's expected IPCA (Focus survey).", s=["selic_target", "ipca_12m", "focus_ipca_12m"]),
                 dict(t="Real per US dollar", d="Official BRL/USD rate (BCB) and the market's year-ahead expectation.", s=["brl_usd", "focus_fx"]),
                 dict(t="Unemployment", d="PNAD rolling-quarter rate (IBGE) with the World Bank / ILO annual series as cross-check.", s=["unemployment_rate", "wb/SL.UEM.TOTL.ZS.BR"]),
                 dict(t="Public debt", d="Gross and net general-government debt, % of GDP (BCB).", s=["gross_public_debt_gdp", "net_public_debt_gdp"])]),
    dict(id="energy", title="Oil, gas & power",
         desc="Pre-salt oil, the power mix and the hydro reservoirs that decide what electricity costs.",
         kpis=["oil_production", "presalt_share", "brent_usd", "stored_energy_ear", "cmo_power_cost", "wind_solar_generation_share"],
         charts=[dict(t="Oil production", d="National (IPEAData/ANP) and offshore (ANP), thousand barrels a day.", s=["oil_production", "oil_production_offshore_kbd"]),
                 dict(t="Pre-salt share of oil output", d="ANP well-level classification.", s=["presalt_share"]),
                 dict(t="Power generation mix", d="Shares of national (SIN) generation, ONS.", s=["hydro_generation_share", "thermal_generation_share", "wind_solar_generation_share"]),
                 dict(t="Reservoirs and the cost of power", d="Stored energy (EAR, %) and the marginal operating cost (CMO, R$/MWh) — different units, so shown rebased.", s=["stored_energy_ear", "cmo_power_cost"]),
                 dict(t="Brent", d="US$ per barrel, daily (EIA via IPEAData).", s=["brent_usd"])]),
    dict(id="companies", title="Resource companies",
         desc="Petrobras, Vale, Axia (ex-Eletrobras), Suzano and PRIO, with Itaú as the non-resource control: returns, revenue and physical output.",
         kpis=[f"total_return_usd@{e}" for e in CO],
         charts=[dict(t="Total return in US dollars", d="Jan 2012 = 100, dividends reinvested (B3, PTAX).", s=[f"total_return_usd@{e}" for e in CO] + ["total_return_usd@IBOV"]),
                 dict(t="Revenue, US$ billion a quarter", d="CVM consolidated filings at the quarter's average BRL/USD.", s=[f"revenue_usd_bn@{e}" for e in CO[:5]]),
                 dict(t="Oil the companies operate", d="Gross production at operated fields (ANP), thousand barrels a day.", s=["operated_oil_production_kbd@PETR", "operated_oil_production_kbd@PRIO"]),
                 dict(t="Net debt, R$ billion", d="Loans, debentures and leases minus cash (CVM).", s=[f"net_debt_brl_bn@{e}" for e in CO[:5]]),
                 dict(t="Dividend yield, trailing 12 months", d="Cash dividends and JCP over the share price (B3).", s=[f"dividend_yield_ttm@{e}" for e in CO])]),
    dict(id="trade", title="Trade & China",
         desc="What Brazil sells, to whom, and at what price per tonne.",
         kpis=["exports_total", "trade_balance", "china_export_share", "iron_ore_unit_value", "oil_export_unit_value", "exports_to_us"],
         charts=[dict(t="Exports by destination", d="Monthly FOB, US$ (ComexStat).", s=["exports_to_china", "exports_to_eu", "exports_to_us"]),
                 dict(t="China's share of exports", d="% of total exports (derived).", s=["china_export_share"]),
                 dict(t="Commodity exports", d="Monthly FOB, US$ (ComexStat).", s=["soy_exports", "oil_exports", "iron_ore_exports", "pulp_exports", "beef_exports", "coffee_exports"]),
                 dict(t="Export prices per tonne", d="FOB value ÷ net weight (derived).", s=["oil_export_unit_value", "iron_ore_unit_value", "pulp_unit_value"])]),
    dict(id="prices", title="Prices & markets",
         desc="Inflation by component, government bond yields, country risk and the stock market.",
         kpis=["ipca_12m", "focus_ipca_12m", "gov_real_yield_10y", "gov_nominal_yield_5y", "embi_brazil", "ibovespa_level"],
         charts=[dict(t="Inflation components", d="Monthly % change: headline, services, administered prices (IBGE via BCB).", s=["ipca_monthly", "ipca_services", "ipca_administered_prices"]),
                 dict(t="Government bond yields", d="NTN-B real ~10y and LTN nominal ~5y (Tesouro Direto).", s=["gov_real_yield_10y", "gov_nominal_yield_5y"]),
                 dict(t="Ibovespa in reais and dollars", d="Index level and the index in US dollars — rebased.", s=["ibovespa_level", "ibovespa_usd"])]),
    dict(id="households", title="Labour & households",
         desc="Jobs, income, debt burden and spending.",
         kpis=["unemployment_rate", "caged_net_hires", "real_average_income", "household_debt_service_ratio", "delinquency_rate", "retail_sales_volume"],
         charts=[dict(t="Formal job creation", d="Novo CAGED net hires, monthly (not seasonally adjusted).", s=["caged_net_hires"]),
                 dict(t="Household debt burden", d="Debt service and debt-to-income, % of income (BCB).", s=["household_debt_service_ratio", "household_debt_income"]),
                 dict(t="Spending", d="Retail volume (PMC), vehicle sales and Pix payments — rebased.", s=["retail_sales_volume", "vehicle_sales", "pix_transactions_value"]),
                 dict(t="Real income and the wage bill", d="PNAD, rebased.", s=["real_average_income", "real_wage_bill"])]),
    dict(id="fiscal", title="Public finances",
         desc="Debt, deficits, the interest bill and the r − g arithmetic.",
         kpis=["gross_public_debt_gdp", "primary_balance_gdp", "interest_bill_gdp", "implicit_interest_rate", "nominal_gdp_growth", "r_minus_g"],
         charts=[dict(t="Primary balance and the interest bill", d="% of GDP, 12-month (BCB, NFSP).", s=["primary_balance_gdp", "interest_bill_gdp"]),
                 dict(t="Interest rate on debt vs nominal growth", d="Implicit rate on gross debt and nominal GDP growth, % a year.", s=["implicit_interest_rate", "nominal_gdp_growth"]),
                 dict(t="Gross debt: BCB vs World Bank", d="General government (BCB) vs central government (World Bank via Dateno).", s=["gross_public_debt_gdp", "wb/GC.DOD.TOTL.GD.ZS.BR"])]),
    dict(id="health", title="Health",
         desc="Deaths by cause from Brazil's mortality register (DATASUS SIM) and the WHO Mortality Database.",
         kpis=["deaths_total", "homicide_rate", "suicide_rate", "traffic_death_rate", "ncd_death_share", "adult_smoking_prevalence"],
         charts=[dict(t="Deaths by cause, monthly", d="DATASUS SIM, by residence; latest months preliminary.", s=["homicide_deaths", "suicide_deaths", "traffic_deaths"]),
                 dict(t="Death rates per 100,000", d="WHO Mortality Database counts over IBGE population.", s=["homicide_rate", "suicide_rate", "traffic_death_rate", "lung_cancer_rate_male", "lung_cancer_rate_female"]),
                 dict(t="Ageing and chronic disease", d="Share of deaths at 65+ and from non-communicable causes, %.", s=["deaths_65plus_share", "ncd_death_share"])]),
]


def _num(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    v = float(v)
    return float(f"{v:.6g}")


def main():
    cat = pd.read_parquet(GOLD / "catalog.parquet")
    obs = pd.read_parquet(GOLD / "observations.parquet")
    rec = pd.read_parquet(GOLD / "reconciliation.parquet") if (GOLD / "reconciliation.parquet").exists() else pd.DataFrame()
    hyp = pd.read_parquet(GOLD / "hypothesis_tests.parquet") if (GOLD / "hypothesis_tests.parquet").exists() else pd.DataFrame()
    cand_p = ROOT / "registry" / "dateno_candidates.json"
    cand = json.loads(cand_p.read_text()) if cand_p.exists() else {}
    reg = pd.read_csv(ROOT / "registry" / "brazil_macro_data_allocation_metrics.csv")
    DATA.mkdir(parents=True, exist_ok=True)
    for f in DATA.glob("obs-*.json"):
        f.unlink()

    # ---- observations, chunked in catalog order
    obs = obs.assign(d=((pd.to_datetime(obs.date) - EPOCH).dt.days).astype(int))
    grouped = {k: g for k, g in obs.groupby("series_id", sort=False)}
    chunk_of, chunks, cur, size = {}, [], {}, 0
    for sid in cat.series_id:
        g = grouped.get(sid)
        if g is None:
            continue
        rec_ = [g.d.tolist(), [_num(v) for v in g.value]]
        b = len(json.dumps(rec_, separators=(",", ":")))
        if size + b > CHUNK_BYTES and cur:
            chunks.append(cur); cur, size = {}, 0
        cur[sid] = rec_; size += b
        chunk_of[sid] = len(chunks)
    if cur:
        chunks.append(cur)
    for i, ch in enumerate(chunks):
        (DATA / f"obs-{i:03d}.json").write_text(json.dumps(ch, separators=(",", ":"), allow_nan=False))

    # ---- catalog
    def s(x):
        return "" if x is None or (not isinstance(x, (list, dict)) and pd.isna(x)) else str(x)
    keys = ["id", "t", "tp", "src", "ns", "ent", "f", "u", "a", "b", "n", "lv", "st", "r", "c", "used", "ds", "db", "ch", "m"]
    rows = []
    for r in cat.itertuples():
        rows.append([r.series_id, s(r.title), s(r.topic), s(r.source), s(r.ns), s(r.entity_name), s(r.freq),
                     UNIT.get(s(r.unit), s(r.unit)), s(r.first)[:10], s(r.last)[:10], int(r.n_obs or 0),
                     _num(r.last_value), s(r.status), s(r.role), s(r.concept), s(r.used_in_tests),
                     s(r.description)[:280], s(getattr(r, "database", "")), chunk_of.get(r.series_id, -1),
                     s(r.metric_id)])
    (DATA / "catalog.json").write_text(json.dumps({"keys": keys, "rows": rows}, separators=(",", ":"),
                                                 ensure_ascii=False, allow_nan=False))

    # ---- meta: reconciliation, missing metrics + Dateno candidates, tests, build facts
    cov = pd.read_csv(ROOT / "registry_coverage.csv") if (ROOT / "registry_coverage.csv").exists() else pd.DataFrame()
    missing = []
    if not cov.empty:
        pend = cov[cov.status.str.startswith("pending")].merge(reg[["metric_id", "metric_name", "theme"]],
                                                                on="metric_id", how="left", suffixes=("", "_r"))
        for r in pend.itertuples():
            c = cand.get(r.metric_id, {})
            missing.append(dict(id=r.metric_id, name=s(r.metric_name), theme=s(r.theme), status=r.status,
                                hits=[dict(t=h.get("title"), u=h.get("url"), p=h.get("publisher"),
                                           f=h.get("formats", [])[:4]) for h in c.get("hits", [])[:5]]))
    have = set(cat.series_id)
    curated = []
    for c in CURATED:
        charts = [dict(c2, s=[x for x in c2["s"] if x in have]) for c2 in c["charts"]]
        curated.append(dict(c, kpis=[k for k in c["kpis"] if k in have], charts=[x for x in charts if x["s"]]))
    pol = dict(terms=pd.read_csv(ROOT / "registry" / "political_terms.csv").fillna("").to_dict("records"),
               events=pd.read_csv(ROOT / "registry" / "political_events.csv").fillna("").to_dict("records"))
    meta = dict(
        politics=pol,
        curated=curated,
        built=pd.Timestamp.today().strftime("%Y-%m-%d"),
        n_series=int(len(cat)), n_obs=int(len(obs)),
        # observed span only: World Bank population series carry projections to 2100
        years=[int(pd.to_datetime(obs.date).dt.year.min()),
               int(min(pd.to_datetime(obs.date).dt.year.max(), pd.Timestamp.today().year))],
        sources=cat.groupby("source").size().sort_values(ascending=False).to_dict(),
        reconciliation=json.loads(rec.to_json(orient="records")) if not rec.empty else [],
        missing=missing,
        tests=json.loads(hyp[["hyp_id", "title", "verdict", "evidence"]].to_json(orient="records")) if not hyp.empty else [],
        registry_total=int(len(reg)),
        registry_done=int(len(cov) - len(missing)) if not cov.empty else None,
    )
    (DATA / "meta.json").write_text(json.dumps(meta, separators=(",", ":"), ensure_ascii=False))

    # agent instructions: the copied prompt, /llms.txt, and AGENTS.md in the repo share one text
    prompt = (ROOT / "semantic" / "agent_prompt.md").read_text()
    meta_p = DATA / "meta.json"
    m = json.loads(meta_p.read_text()); m["agent_prompt"] = prompt
    meta_p.write_text(json.dumps(m, separators=(",", ":"), ensure_ascii=False))
    (OUT / "llms.txt").write_text("# Brazil Monitoring\n\n" + prompt.replace("{{FOCUS}}", "").replace("My question:\n", ""))
    (ROOT / "AGENTS.md").write_text("# Brazil Monitoring — instructions for AI agents\n\n"
                                    + prompt.replace("{{FOCUS}}", "").replace("My question:\n", ""))
    (OUT / "semantic").mkdir(exist_ok=True)
    for f in ("model.yml", "views.sql"):
        (OUT / "semantic" / f).write_text((ROOT / "semantic" / f).read_text())
    body = (ROOT / "portal_app.html").read_text().replace("{{PLOTLY}}", PLOTLY).replace("{{ALASQL}}", ALASQL)
    head = (f"<title>Brazil Monitoring</title>\n<link rel='preconnect' href='https://fonts.googleapis.com'>"
            f"<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin><link rel='stylesheet' href='{FONTS}'>\n")
    (OUT / "index.html").write_text(head + body)
    (OUT / "standalone.html").write_text(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>"
        + head + "</head><body>" + body + "</body></html>")
    total = sum(p.stat().st_size for p in DATA.glob("*.json"))
    print(f"portal: {len(cat):,} series, {len(obs):,} observations, {len(chunks)} chunks, "
          f"data {total / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
