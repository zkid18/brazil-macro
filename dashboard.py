"""dashboard.py — build the "Brazil, Tested" report from the warehouse.

Reads silver/gold/dq and emits one self-contained page. Charts are drawn in the
browser from embedded JSON (Plotly from cdnjs), so colors follow the viewer's
light/dark theme and off-screen charts render lazily.

Outputs:
  warehouse/dashboard.html            full document — open locally in a browser
  warehouse/dashboard_artifact.html   same page as a body fragment (for publishing
                                      as an artifact, whose host adds the skeleton)

Run:  python3 dashboard.py
"""
from __future__ import annotations
import html, json, math, pathlib
import numpy as np
import pandas as pd
import hypotheses as H

ROOT = pathlib.Path(__file__).resolve().parent
SILVER = ROOT / "warehouse" / "silver" / "fact_time_series.parquet"
GOLD = ROOT / "warehouse" / "gold"
DQ = ROOT / "dq" / "dq_report.csv"
OUT = ROOT / "warehouse" / "dashboard.html"
OUT_ARTIFACT = ROOT / "warehouse" / "dashboard_artifact.html"
PLOTLY = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.34.0/plotly-basic.min.js"
FONTS = ("https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400"
         "&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&display=swap")

COMPANY_SLOT = {"PETR": "c1", "VALE": "c2", "AXIA": "c3", "SUZB": "c4", "PRIO": "c5", "ITUB": "c6"}
VERDICT_KEY = {"Supported": "ok", "Not supported": "no", "Mixed": "mixed",
               "Insufficient data": "na"}
GROUP_ORDER = ["Companies & energy", "Households & labour", "Public finances", "Trade"]

# Library chapters: (anchor, title, one-line scope, metric_ids in reading order)
CHAPTERS = [
    ("rates", "Rates & risk", "Policy rate, market expectations, government yields, country risk.",
     ["selic_target", "focus_selic_12m", "gov_real_yield_10y", "gov_nominal_yield_5y", "embi_brazil"]),
    ("prices", "Prices", "IPCA consumer inflation and its components.",
     ["ipca_12m", "focus_ipca_12m", "ipca_monthly", "ipca_services", "ipca_administered_prices",
      "inflation_diffusion", "ipca_headline"]),
    ("activity", "Activity", "Monthly activity, spending and payments.",
     ["ibc_br", "gdp_real_growth", "focus_gdp_growth", "retail_sales_volume", "vehicle_sales",
      "vehicle_production", "pix_transactions_count", "pix_transactions_value"]),
    ("credit", "Credit & households", "Household and corporate credit, debt burden, defaults.",
     ["credit_gdp", "household_debt_service_ratio", "household_debt_income", "delinquency_rate",
      "household_credit_growth", "corporate_credit_growth"]),
    ("labour", "Labour", "PNAD household survey and CAGED formal-job register.",
     ["unemployment_rate", "caged_net_hires", "employed_population", "real_average_income",
      "real_wage_bill", "labor_participation_rate"]),
    ("fiscal", "Public finances", "Debt, deficits and the interest bill.",
     ["gross_public_debt_gdp", "net_public_debt_gdp", "primary_balance_gdp", "interest_bill_gdp",
      "nominal_deficit_gdp", "implicit_interest_rate", "nominal_gdp_growth", "r_minus_g"]),
    ("markets", "Currency & equities", "The real, reserves and the Ibovespa.",
     ["brl_usd", "focus_fx", "fx_reserves", "ibovespa_level", "ibovespa_usd"]),
    ("trade", "Trade", "Exports by product and destination, prices per tonne, the external balance.",
     ["exports_total", "imports_total", "trade_balance", "exports_to_china", "exports_to_us",
      "exports_to_eu", "china_export_share", "soy_exports", "oil_exports", "iron_ore_exports",
      "pulp_exports", "beef_exports", "beef_exports_to_china", "coffee_exports", "sugar_exports",
      "niobium_exports", "oil_export_unit_value", "iron_ore_unit_value", "pulp_unit_value",
      "current_account_usd", "current_account_gdp", "fdi_idp"]),
    ("oil", "Oil & gas", "Production, the pre-salt share and the oil price.",
     ["oil_production", "oil_production_offshore_kbd", "presalt_share", "gas_production_mm3d",
      "brent_usd", "oil_exports_kg"]),
    ("power", "Power & water", "Reservoirs, the generation mix and the cost of power.",
     ["stored_energy_ear", "hydro_generation_share", "thermal_generation_share",
      "wind_solar_generation_share", "hydro_stress_index", "cmo_power_cost", "electricity_load",
      "thermal_dispatch_mwh", "renewable_share_electricity_matrix",
      "renewable_share_total_energy_matrix"]),
    ("land", "Agriculture & land", "Fertilizer dependence, harvests and forest cover.",
     ["fertilizer_imports", "potash_imports", "fertilizer_dependency_index",
      "potash_import_dependency_proxy", "cereal_production", "forest_area_km2"]),
    ("structure", "Long-run structure", "World Bank annual series: people, investment, output mix.",
     ["fertility_rate", "working_age_share", "dependency_ratio", "investment_rate_gdp",
      "gdp_agriculture_share", "gdp_industry_share", "gdp_services_share", "gni_per_capita"]),
]

UNIT = {  # bronze unit -> (display unit, scale divisor)
    "pct": ("%", 1), "pct_pa": ("% a year", 1), "pct_yoy": ("% year on year", 1),
    "pct_mom": ("% month on month", 1), "pct_gdp": ("% of GDP", 1),
    "pct_gdp_nfsp": ("% of GDP, + = deficit", 1), "pct_income": ("% of income", 1),
    "pct_pts": ("percentage points", 1), "annual_pct": ("% a year", 1),
    "brl_per_usd": ("R$ per US$", 1), "bps": ("basis points", 1), "points": ("index points", 1),
    "index_usd": ("Ibovespa ÷ BRL/USD", 1), "usd_fob": ("US$ bn, FOB", 1e9),
    "usd_mn": ("US$ bn", 1e3), "usd": ("US$", 1), "brl_mn": ("R$ bn", 1e3),
    "thousand_tonnes": ("million tonnes", 1e3), "usd_per_t": ("US$ per tonne", 1),
    "kbbl_day": ("thousand barrels/day", 1), "kbd": ("thousand barrels/day", 1),
    "mm3_day": ("million m³/day", 1), "usd_per_bbl": ("US$ per barrel", 1),
    "brl_per_mwh": ("R$ per MWh", 1), "mwmed": ("average GW", 1e3),
    "index_0_100": ("index, 0–100", 1), "index": ("index", 1), "index_2022_100": ("index, 2022 = 100", 1),
    "units": ("thousand vehicles", 1e3), "million_tx": ("billion transactions", 1e3),
    "brl_bn": ("R$ trillion", 1e3), "jobs": ("thousand jobs", 1e3),
    "thousand_persons": ("million people", 1e3), "brl_real": ("R$ a month, real", 1),
    "brl_bn_month": ("R$ bn a month, real", 1), "ratio": ("ratio", 1),
    "births_per_woman": ("births per woman", 1), "pct_working_age": ("% of working-age pop.", 1),
    "pct_population": ("% of population", 1), "pct_labor_force": ("% of labour force", 1),
    "pct_of_exports": ("% of exports", 1), "metric_tons": ("million tonnes", 1e6),
    "km2": ("million km²", 1e6), "gwh": ("TWh", 1e3), "pct_gdp_pts": ("pts of GDP", 1),
}
SOURCE_NAME = {
    "bcb_sgs": "Banco Central (SGS)", "bcb_focus": "Banco Central (Focus survey)",
    "bcb_olinda": "Banco Central (Pix data)", "ibge_sidra": "IBGE (SIDRA)",
    "comexstat": "ComexStat (MDIC)", "ipeadata": "IPEAData", "ons": "ONS",
    "tesouro": "Tesouro Direto", "tesouro_direto": "Tesouro Direto", "anp": "ANP",
    "b3_cotahist": "B3 (COTAHIST)", "b3_dividends": "B3 (dividends)",
    "b3_ibov_portfolio": "B3 (Ibovespa portfolio)", "cvm_itr_dfp": "CVM (ITR/DFP filings)",
    "derived": "Derived in this report", "dateno_wb": "World Bank via Dateno",
    "ons_open_data": "ONS", "bcb_olinda_pix": "Banco Central (Pix data)", "epe_ben": "World Bank via Dateno",
}
# Why a series flagged as behind is behind (shown in the freshness table)
LAG_NOTE = {
    "embi_brazil": "IPEAData stopped updating the J.P. Morgan EMBI+ feed in July 2024.",
    "vehicle_production": "Anfavea publishes with a lag; BCB mirrors it later.",
    "renewable_share_electricity_matrix": "World Bank series discontinued after 2015.",
}
DEFAULT_LAG = "Latest year the World Bank has published."
# Plain-English gloss shown under library titles (first use of each Portuguese/market term)
GLOSS = {
    "selic_target": "Selic: the central bank's policy interest rate.",
    "focus_selic_12m": "Focus: the central bank's weekly survey of market forecasts.",
    "focus_ipca_12m": "IPCA: the official consumer-price index.", "ipca_12m": "IPCA: the official consumer-price index.",
    "gov_real_yield_10y": "NTN-B: inflation-linked Treasury bond; the yield is a real rate.",
    "gov_nominal_yield_5y": "LTN: fixed-rate, zero-coupon Treasury bill/bond.",
    "embi_brazil": "EMBI+: J.P. Morgan's spread of Brazil's dollar bonds over US Treasuries.",
    "ibc_br": "IBC-Br: the central bank's monthly proxy for GDP.",
    "caged_net_hires": "CAGED: the labour ministry's register of formal (signed-card) jobs.",
    "unemployment_rate": "PNAD: IBGE's household labour survey, rolling quarters.",
    "stored_energy_ear": "EAR: water stored in hydro reservoirs, as % of maximum.",
    "cmo_power_cost": "CMO: the grid operator's marginal cost of the next MWh (SE/CO region).",
    "retail_sales_volume": "PMC: IBGE's monthly retail trade survey, seasonally adjusted.",
    "nominal_deficit_gdp": "NFSP: public-sector borrowing requirement; positive = deficit.",
    "fdi_idp": "IDP: direct investment into Brazil (FDI).",
    "electricity_load": "SIN: Brazil's national interconnected grid.",
    "pix_transactions_count": "Pix: the central bank's instant-payment system (since Nov 2020).",
}
GLOSSARY = [
    ("Selic", "The central bank's policy interest rate."),
    ("IPCA", "The official consumer-price index (IBGE)."),
    ("Focus", "The central bank's weekly survey of market forecasts."),
    ("CAGED", "The labour ministry's monthly register of formal jobs; 'net hires' = hires minus separations."),
    ("PNAD", "IBGE's household survey; source of the unemployment rate."),
    ("EAR", "Stored energy: water in hydro reservoirs as a % of their maximum."),
    ("CMO", "Marginal operating cost: what the next MWh costs the grid, set by the operator ONS."),
    ("SIN", "The national interconnected power grid."),
    ("NTN-B / LTN", "Inflation-linked / fixed-rate Treasury bonds."),
    ("EMBI+", "Spread of Brazil's dollar bonds over US Treasuries, in basis points."),
    ("NFSP", "Public-sector borrowing requirement; positive means a deficit."),
    ("Operated output", "Oil produced at fields a company operates, including partners' shares (not equity output)."),
    ("Total return", "Price change plus dividends reinvested on the ex-dividend date."),
    ("ρ (rho), R²", "Correlation coefficient (−1 to 1); share of variance explained by a regression (0 to 1)."),
]

FREQ_RULE = {"daily": "W-FRI", "weekly": None, "monthly": None, "quarterly": None,
             "annual": None, "event": None}


# ----------------------------------------------------------------------------- data helpers
def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def series(silver, mid, ent="BR"):
    s = silver[(silver.metric_id == mid) & (silver.entity_id == ent)]
    if s.empty:
        return None
    return s.assign(dt=pd.to_datetime(s.date)).sort_values("dt").set_index("dt")["value"]


def pts(s, start=None, rule=None, scale=1.0, nd=4):
    """Series -> (x list, y list) for JSON, optionally resampled and scaled."""
    if s is None:
        return [], []
    s = s.dropna()
    if start:
        s = s[s.index >= start]
    if rule:
        s = s.resample(rule).last().dropna()
    xs, ys = [], []
    if len(s) > 2:
        gaps = s.index.to_series().diff().dt.days
        typical = gaps.median()
    for i, (d, v) in enumerate(s.items()):
        # break the line where the gap is far longer than the series' normal spacing
        if i and len(s) > 2 and gaps.iloc[i] > max(45, 4 * typical):
            xs.append((d - pd.Timedelta(days=1)).strftime("%Y-%m-%d")); ys.append(None)
        xs.append(d.strftime("%Y-%m-%d"))
        ys.append(None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v) / scale, nd))
    return xs, ys


def index_to(s, base_date):
    s = s.dropna()
    b = s[s.index >= base_date]
    if b.empty:
        return None
    return s[s.index >= base_date] / b.iloc[0] * 100


def fmt(v, nd=1, unit=""):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:,.{nd}f}{unit}"


def source_of(silver, mid):
    s = silver[silver.metric_id == mid]
    if s.empty:
        return ""
    src = s.resolved_source.iloc[0]
    if str(src).startswith("dateno"):
        return "World Bank via Dateno"
    return SOURCE_NAME.get(s.source_id.iloc[0], s.source_id.iloc[0])


# ----------------------------------------------------------------------------- chart specs
def line(name, s, slot, **kw):
    x, y = pts(s, kw.pop("start", None), kw.pop("rule", None), kw.pop("scale", 1.0))
    return dict(name=name, x=x, y=y, c=slot, **kw)


def hyp_charts(silver):
    """One chart spec per hypothesis: list of panels, each with its own y axis."""
    C = {}
    q = lambda s: s.resample("QE").mean() if s is not None else None  # noqa: E731

    rev = series(silver, "revenue_usd_bn", "PETR")
    brent, vol = series(silver, "brent_usd"), series(silver, "operated_oil_production_kbd", "PETR")
    if rev is not None and brent is not None:
        base = "2016-01-01"
        ps = [line("Petrobras revenue (US$)", index_to(rev, base), "c1"),
              line("Brent price", index_to(q(brent), base), "ink", dash="dot")]
        if vol is not None:
            ps.append(line("Petrobras-operated output", index_to(q(vol), base), "muted"))
        C["h1"] = dict(panels=[dict(y="Index, Q1 2016 = 100", series=ps)],
                       note="Quarterly. All three lines indexed to Q1 2016 = 100.")

    oil, iron = series(silver, "oil_exports_kg"), series(silver, "iron_ore_exports_kg")
    if oil is not None and iron is not None:
        o = index_to(oil.rolling(12).sum(), "2016-12-01")
        i = index_to(iron.rolling(12).sum(), "2016-12-01")
        C["h2"] = dict(panels=[dict(y="Index, 12 months to Dec 2016 = 100", series=[
            line("Crude oil export tonnes", o, "c1"), line("Iron ore export tonnes", i, "c2")])],
            note="Rolling 12-month export volumes, ComexStat net weight.")

    vrev, uv = series(silver, "revenue_usd_bn", "VALE"), series(silver, "iron_ore_unit_value")
    if vrev is not None and uv is not None:
        base = "2016-01-01"
        C["h3"] = dict(panels=[dict(y="Index, Q1 2016 = 100", series=[
            line("Vale revenue (US$)", index_to(vrev, base), "c2"),
            line("Iron ore export price (US$/t)", index_to(q(uv), base), "ink", dash="dot")])],
            note="Quarterly. Both indexed to Q1 2016 = 100.")

    ear, sh = series(silver, "stored_energy_ear"), series(silver, "generation_share_sin", "AXIA")
    cmo = series(silver, "cmo_power_cost")
    if ear is not None and sh is not None:
        em = ear.resample("MS").mean()
        em = em[em.index >= "2016-01-01"]
        low = [[d.strftime("%Y-%m-%d"), (d + pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")]
               for d, v in em.items() if v < 40]
        panels = [dict(y="% ", series=[line("Reservoir storage (EAR)", em, "c1"),
                                       line("Axia share of generation", sh, "c3")],
                       hline=dict(y=40, label="40% storage"), shade=low)]
        if cmo is not None:
            panels.append(dict(y="R$ per MWh", height=170, series=[
                line("Marginal power cost (CMO)", cmo.resample("MS").mean(), "ink",
                     start="2016-01-01")], shade=low))
        C["h4"] = dict(panels=panels, note="Monthly. Shaded months: storage below 40%.")

    tr = {e: series(silver, "total_return_usd", e) for e in ("PETR", "VALE", "IBOV")}
    if all(v is not None for v in tr.values()):
        C["h5"] = dict(panels=[dict(y="US$, Jan 2012 = 100", log=True, series=[
            line("Petrobras", tr["PETR"], "c1"), line("Vale", tr["VALE"], "c2"),
            line("Ibovespa", tr["IBOV"], "ink", dash="dot")], hline=dict(y=100, label="")) ],
            note="Month-end total return in US dollars, dividends reinvested. Log scale.")

    s, it, fx = (series(silver, "total_return_brl", "SUZB"), series(silver, "total_return_brl", "ITUB"),
                 series(silver, "brl_usd"))
    if s is not None and it is not None and fx is not None:
        dfx = (fx.resample("ME").last().pct_change() * 100)
        def pair(tr_):
            r = tr_.pct_change() * 100
            r.index = r.index.to_period("M")
            f = dfx.copy(); f.index = f.index.to_period("M")
            d = pd.concat([f.rename("fx"), r.rename("r")], axis=1).dropna()
            return [round(v, 2) for v in d.fx], [round(v, 2) for v in d.r], \
                   [p.strftime("%b %Y") for p in d.index]
        sx, sy, sl = pair(s)
        ix, iy, il = pair(it)
        C["h6"] = dict(kind="scatter", panels=[dict(y="Stock return, % in the month",
                       x="Change in BRL per US$, % (right = real weaker)", series=[
                           dict(name="Suzano", x=sx, y=sy, labels=sl, c="c4"),
                           dict(name="Itaú", x=ix, y=iy, labels=il, c="c6")])],
                       note="One dot per month since 2012.")

    dsr, ret = series(silver, "household_debt_service_ratio"), series(silver, "retail_sales_volume")
    if dsr is not None and ret is not None:
        C["l1"] = dict(panels=[
            dict(y="% of income", height=170, series=[line("Debt service ratio", dsr, "c1", start="2012-01-01")]),
            dict(y="% year on year", height=170, series=[line("Retail sales volume", ret.pct_change(12) * 100,
                                                            "c2", start="2012-01-01")], hline=dict(y=0, label=""))],
            note="Monthly. Debt service = interest + principal as a share of disposable income (BCB).")

    cg, un = series(silver, "caged_net_hires"), series(silver, "unemployment_rate")
    if cg is not None and un is not None:
        C["l2"] = dict(panels=[
            dict(y="thousand jobs", height=170, bars=True, series=[
                line("CAGED net formal hires, 3-month avg", cg.rolling(3).mean(), "c1", scale=1e3)],
                hline=dict(y=0, label="")),
            dict(y="% of labour force", height=170, series=[
                line("Unemployment rate (PNAD)", un, "c2", start="2020-01-01")])],
            note="Monthly. CAGED is not seasonally adjusted: December is always negative.")

    r, g = series(silver, "implicit_interest_rate"), series(silver, "nominal_gdp_growth")
    if r is not None and g is not None:
        C["l3"] = dict(panels=[dict(y="% a year", series=[
            line("Interest rate on gross debt (r)", r, "c1", start="2008-01-01"),
            line("Nominal GDP growth (g)", g, "c2", start="2008-01-01")])],
            note="Monthly, 12-month windows. r = interest bill ÷ debt a year earlier.")

    dest = {k: series(silver, f"exports_to_{k}") for k in ("china", "us", "eu")}
    if all(v is not None for v in dest.values()):
        C["l4"] = dict(panels=[dict(y="US$ bn, rolling 12 months", series=[
            line("China", dest["china"].rolling(12).sum(), "c1", scale=1e9, start="2015-01-01"),
            line("European Union", dest["eu"].rolling(12).sum(), "c3", scale=1e9, start="2015-01-01"),
            line("United States", dest["us"].rolling(12).sum(), "c2", scale=1e9, start="2015-01-01")],
            vline=dict(x="2025-08-06", label="US 50% tariff"))],
            note="Exports, FOB, by destination (ComexStat).")
    return C


def company_charts(silver):
    C = {}
    ib = series(silver, "total_return_usd", "IBOV")
    tr_panels = []
    for e, (nm, tk, _) in H.COMPANIES.items():
        s = series(silver, "total_return_usd", e)
        if s is None:
            continue
        ser = [line(nm, s, COMPANY_SLOT[e])]
        if ib is not None:
            ser.append(line("Ibovespa", ib, "ink", dash="dot"))
        tr_panels.append(dict(title=f"{nm} ({tk})", y="US$", log=True, series=ser,
                              hline=dict(y=100, label="")))
    if tr_panels:
        C["c_tr"] = dict(grid=True, panels=tr_panels, shared_legend=["Company", "Ibovespa"],
                         note="US$100 invested in January 2012, dividends reinvested, month-end. Log scale.")

    rv_panels = []
    for e, (nm, tk, _) in H.COMPANIES.items():
        r, n = series(silver, "revenue_usd_bn", e), series(silver, "net_income_usd_bn", e)
        if r is None:
            continue
        if e == "ITUB":  # bank "revenue" (intermediation income) is not comparable; show profit only
            ser = [dict(line("Net income", n, COMPANY_SLOT[e], start="2014-01-01"), bars=True)]
            title = f"{nm} — net income only"
        else:
            ser = [dict(line("Revenue", r, COMPANY_SLOT[e], start="2014-01-01"), bars=True)]
            if n is not None:
                ser.append(line("Net income", n, "ink", start="2014-01-01"))
            title = nm
        rv_panels.append(dict(title=title, y="US$ bn a quarter", series=ser, hline=dict(y=0, label="")))
    if rv_panels:
        C["c_rev"] = dict(grid=True, panels=rv_panels, note="Quarterly, converted at the quarter's "
                          "average BRL/USD. For Itaú only net income is shown: a bank's 'revenue' line is not comparable.")

    phys = []
    for e, mid, title, y, scale, slot in [
            ("PETR", "operated_oil_production_kbd", "Petrobras — oil it operates", "thousand barrels/day", 1, "c1"),
            ("PRIO", "operated_oil_production_kbd", "PRIO — oil it operates", "thousand barrels/day", 1, "c5"),
            ("AXIA", "generation_gwh", "Axia — power generated", "TWh a month", 1e3, "c3"),
            ("BR", "iron_ore_exports_kg", "Brazil iron ore exports (Vale context)", "million tonnes a month", 1e3, "c2"),
            ("BR", "pulp_exports_kg", "Brazil pulp exports (Suzano context)", "million tonnes a month", 1e3, "c4")]:
        s = series(silver, mid, e)
        if s is not None:
            phys.append(dict(title=title, y=y, series=[line(title.split(" — ")[0].split(" (")[0], s, slot,
                                                            scale=scale, start="2016-01-01")]))
    if phys:
        C["c_phys"] = dict(grid=True, panels=phys, note="Monthly. Operated oil is gross production at "
                           "fields the company operates (ANP), not its equity share. Vale and Suzano "
                           "do not publish monthly volumes to a free API; national export tonnes are shown as context.")
    return C


def library_chart(silver, mid, stale=frozenset()):
    s = silver[(silver.metric_id == mid) & (silver.entity_id == "BR")]
    if s.empty:
        return None
    unit, scale = UNIT.get(s.unit.iloc[0], (s.unit.iloc[0], 1))
    freq = s.freq.iloc[0]
    ser = series(silver, mid)
    x, y = pts(ser, rule=FREQ_RULE.get(freq), scale=scale)
    last_v = ser.iloc[-1] / scale
    nd = 0 if abs(last_v) >= 1000 else (1 if abs(last_v) >= 10 else 2)
    if s.unit.iloc[0].startswith("pct") or s.unit.iloc[0] == "annual_pct":
        nd = 2  # rates move in 25 bp steps (Selic 13.75%)
    return dict(id=f"m_{mid}", title=s.metric_name.iloc[0], unit=unit, freq=freq,
                gloss=GLOSS.get(mid, ""), stale=mid in stale,
                source=source_of(silver, mid), last=f"{last_v:,.{nd}f}",
                last_date=ser.index[-1].strftime("%b %Y" if freq != "daily" else "%d %b %Y"),
                annual=freq == "annual", x=x, y=y)


# ----------------------------------------------------------------------------- company table
def company_rows(silver):
    w = silver[silver.metric_id == "ibov_weight"]
    rows = []
    for e, (nm, tk, role) in H.COMPANIES.items():
        def last(mid, ent=e):
            s = series(silver, mid, ent)
            return (s.iloc[-1], s.index[-1]) if s is not None and len(s) else (None, None)
        px, pxd = last("share_close_brl")
        tr = series(silver, "total_return_usd", e)
        tr12 = None
        if tr is not None and len(tr) > 13:  # a true 12-month window ending at the last observation
            base = tr.loc[:tr.index[-1] - pd.DateOffset(years=1)]
            tr12 = (tr.iloc[-1] / base.iloc[-1] - 1) * 100 if len(base) else None
        rev, ni = series(silver, "revenue_usd_bn", e), series(silver, "net_income_usd_bn", e)
        nd, _ = last("net_debt_brl_bn")
        dy, _ = last("dividend_yield_ttm")
        # all listed share classes of the issuer (PETR3 + PETR4, ...), latest snapshot
        wl = w[w.entity_id.str[:4] == e]
        wt = wl[wl.date == wl.date.max()].groupby("date").value.sum()
        rows.append(dict(
            id=e, name=nm, ticker=tk, role=role, slot=COMPANY_SLOT[e],
            weight=float(wt.iloc[-1]) if len(wt) else None,
            price=px, price_date=pxd.strftime("%d %b %Y") if pxd is not None else "",
            tr_since=tr.iloc[-1] if tr is not None else None, tr12=tr12,
            rev_ttm=(rev.iloc[-4:].sum() if rev is not None and len(rev) >= 4 else None) if e != "ITUB" else None,
            ni_ttm=ni.iloc[-4:].sum() if ni is not None and len(ni) >= 4 else None,
            ttm_to=f"{rev.index[-1].year}-Q{rev.index[-1].quarter}" if rev is not None else "",
            net_debt=nd, div_yield=dy))
    return rows


# ----------------------------------------------------------------------------- html pieces
def verdict_pill(v):
    k = VERDICT_KEY.get(v, "na")
    icon = {"ok": "M3 8.5l3 3 7-7", "no": "M4 4l8 8M12 4l-8 8", "mixed": "M3 8h10",
            "na": "M8 4v5M8 11.5v.5"}[k]
    return (f"<span class='pill pill-{k}'><svg viewBox='0 0 16 16' aria-hidden='true'>"
            f"<path d='{icon}'/></svg>{esc(v)}</span>")


def gauge(r):
    """Number line: the pre-registered threshold and where the statistic landed."""
    lo, hi, t, st = r.axis_lo, r.axis_hi, r.threshold_value, r.statistic
    if lo is None or hi is None or (isinstance(lo, float) and math.isnan(lo)):
        return ""
    clamp = lambda v: max(0.0, min(100.0, (v - lo) / (hi - lo) * 100))  # noqa: E731
    pass_right = r.threshold_dir in (">", ">=")
    tp = clamp(t)
    zone = (f"left:{tp:.2f}%;right:0" if pass_right else f"left:0;right:{100 - tp:.2f}%")
    unit = f" {r.stat_unit}" if r.stat_unit else ""
    sym = {">=": "≥", "<=": "≤"}.get(r.threshold_dir, r.threshold_dir)
    nd = 2 if abs(hi - lo) <= 2 else 1
    if hi - lo > 100:
        nd = 0
    stat_html = val_html = ""
    if st is not None and not (isinstance(st, float) and math.isnan(st)):
        sp = clamp(st)
        off = " off" if st < lo or st > hi else ""
        stat_html = f"<span class='g-dot v-{VERDICT_KEY.get(r.verdict, 'na')}{off}' style='left:{sp:.2f}%'></span>"
        val_html = f"<span class='g-val' style='left:{sp:.2f}%'>{st:+,.{nd}f}{esc(unit)}</span>"
    return (f"<div class='gauge' role='img' aria-label='{esc(r.stat_label)}: "
            f"{'' if st is None else f'{st:.{nd}f}'}{esc(unit)}; passes if {esc(sym)} {t:g}'>"
            f"{val_html}<div class='g-track'><span class='g-zone' style='{zone}'></span>"
            f"<span class='g-thr' style='left:{tp:.2f}%'></span>{stat_html}</div>"
            f"<div class='g-axis'><span>{lo:g}</span><span class='g-thr-l' style='left:{tp:.2f}%'>"
            f"{esc(sym)} {t:g}</span><span>{hi:g}</span></div></div>")


def ledger(hyp):
    rows = []
    for g in GROUP_ORDER:
        sub = hyp[hyp.group == g]
        if sub.empty:
            continue
        rows.append(f"<tr class='lg-group'><th colspan='4' scope='colgroup'>{esc(g)}</th></tr>")
        for r in sub.itertuples():
            rows.append(
                f"<tr><td class='lg-id'><a href='#{r.hyp_id.lower()}'>{esc(r.hyp_id)}</a></td>"
                f"<td class='lg-q'><a href='#{r.hyp_id.lower()}'>{esc(r.title)}</a>"
                f"<span>{esc(r.question)}</span></td>"
                f"<td class='lg-g'>{gauge(r)}</td><td class='lg-v'>{verdict_pill(r.verdict)}</td></tr>")
    return ("<div class='tbl-wrap'><table class='ledger'><thead><tr><th scope='col'>Test</th>"
            "<th scope='col'>Hypothesis</th><th scope='col'>Result vs threshold</th>"
            "<th scope='col'>Verdict</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def hyp_detail(r, has_chart):
    chart = (f"<div class='chart' data-chart='{r.hyp_id.lower()}'></div>" if has_chart else
             "<p class='empty'>Chart unavailable: an input series is missing from this build.</p>")
    return f"""
<article class='test' id='{r.hyp_id.lower()}'>
  <header class='test-h'>
    <span class='test-id'>{esc(r.hyp_id)}</span>
    <h3>{esc(r.title)}</h3>
    {verdict_pill(r.verdict)}
  </header>
  <div class='test-body'>
    <dl class='test-dl'>
      <div><dt>Claim</dt><dd>{esc(r.claim)}</dd></div>
      <div><dt>Test</dt><dd>{esc(r.test)}</dd></div>
      <div><dt>Threshold</dt><dd>{esc(r.threshold)}</dd></div>
      <div><dt>Result</dt><dd class='result'>{esc(r.evidence) or 'Not computed: inputs missing.'}</dd></div>
      <div><dt>Data</dt><dd class='inputs'>{esc(r.inputs)}{f" · as of {esc(r.as_of)}" if r.as_of else ""}</dd></div>
    </dl>
    <figure class='test-fig'>{chart}</figure>
  </div>
</article>"""


def company_table(rows):
    body = []
    for r in rows:
        body.append(
            f"<tr><th scope='row'><span class='swatch s-{r['slot']}' aria-hidden='true'></span>"
            f"<span class='co-name'>{esc(r['name'])}</span><span class='co-role'>{esc(r['ticker'])} · "
            f"{esc(r['role'])}</span></th>"
            f"<td>{fmt(r['weight'], 1, '%')}</td>"
            f"<td>{fmt(r['price'], 2)}<span class='sub'>{esc(r['price_date'])}</span></td>"
            f"<td>{fmt(r['tr_since'], 0)}</td><td>{fmt(r['tr12'], 0, '%')}</td>"
            f"<td>{fmt(r['rev_ttm'], 1)}</td><td>{fmt(r['ni_ttm'], 1)}<span class='sub'>{esc(r['ttm_to'])}</span></td>"
            f"<td>{fmt(r['net_debt'], 0)}</td><td>{fmt(r['div_yield'], 1, '%')}</td></tr>")
    return ("<div class='tbl-wrap'><table class='data co'><thead><tr><th scope='col'>Company</th>"
            "<th scope='col'>Ibovespa weight</th><th scope='col'>Share price, R$</th>"
            "<th scope='col'>US$100 in Jan 2012 is now</th><th scope='col'>Total return, last 12 months (US$)</th>"
            "<th scope='col'>Revenue, US$ bn (4 qtrs)</th><th scope='col'>Net income, US$ bn (4 qtrs)</th>"
            "<th scope='col'>Net debt, R$ bn</th><th scope='col'>Dividend yield (12m)</th></tr></thead>"
            "<tbody>" + "".join(body) + "</tbody></table></div>")


def scorecard_list(sc):
    items = "".join(
        f"<li><h3>{esc(r.thread)}</h3><p class='ev'>{esc(r.evidence)}</p></li>" for r in sc.itertuples())
    return f"<ol class='book'>{items}</ol>"


def library(silver, stale=frozenset()):
    tabs, panes, specs = [], [], {}
    for i, (aid, title, scope, mids) in enumerate(CHAPTERS):
        cards = []
        for mid in mids:
            c = library_chart(silver, mid, stale)
            if c is None:
                continue
            specs[c["id"]] = c
            cards.append(
                f"<figure class='lib-card'><figcaption><h3>{esc(c['title'])}</h3>"
                f"<p>{esc(c['unit'])} · {esc(c['freq'])} · {esc(c['source'])}</p>"
                + (f"<p class='gloss'>{esc(c['gloss'])}</p>" if c['gloss'] else "")
                + (f"<p class='last'><span class='stale'>Not updated since {esc(c['last_date'])}</span> "
                   f"last value <strong>{esc(c['last'])}</strong></p>" if c['stale'] else
                   f"<p class='last'>Latest <strong>{esc(c['last'])}</strong> <span>{esc(c['last_date'])}</span></p>")
                + f"</figcaption><div class='chart sm' data-lib='{c['id']}'></div></figure>")
        if not cards:
            continue
        sel = "true" if not tabs else "false"
        tabs.append(f"<button role='tab' id='tab-{aid}' aria-controls='pane-{aid}' aria-selected='{sel}' "
                    f"tabindex='{0 if sel == 'true' else -1}' data-tab='{aid}'>{esc(title)}"
                    f"<span class='count'>{len(cards)}</span></button>")
        panes.append(f"<section role='tabpanel' id='pane-{aid}' aria-labelledby='tab-{aid}' "
                     f"{'' if sel == 'true' else 'hidden'}><p class='scope'>{esc(scope)}</p>"
                     f"<div class='lib-grid'>{''.join(cards)}</div></section>")
    return (f"<div class='tabs' role='tablist' aria-label='Library chapters'>{''.join(tabs)}</div>"
            + "".join(panes)), specs


def sources_table(silver, dq):
    lin = (silver[silver.entity_id.isin(["BR"] + list(H.COMPANIES))]
           .assign(src=lambda d: d.apply(lambda r: "World Bank via Dateno" if str(r.resolved_source).startswith("dateno")
                                         else SOURCE_NAME.get(r.source_id, r.source_id), axis=1))
           .groupby("src").agg(series=("metric_id", "nunique"), first=("date", "min"), last=("date", "max"))
           .reset_index().sort_values("series", ascending=False))
    rows = "".join(f"<tr><th scope='row'>{esc(r.src)}</th><td>{r.series}</td><td>{esc(r.first[:4])}</td>"
                   f"<td>{esc(r.last)}</td></tr>" for r in lin.itertuples())
    stale = dq[dq.check != "fresh"]
    names = silver.drop_duplicates("metric_id").set_index("metric_id").metric_name
    stale_rows = "".join(f"<tr><th scope='row'>{esc(names.get(r.metric_id, r.metric_id))}</th><td>{esc(r.freq)}</td>"
                         f"<td>{esc(r.last)}</td><td class='wrap-cell'>{esc(LAG_NOTE.get(r.metric_id, DEFAULT_LAG))}</td></tr>"
                         for r in stale.itertuples())
    return rows, stale_rows, len(dq), len(stale)


# ----------------------------------------------------------------------------- page
CSS = r"""
/* Layout: masthead + sticky contents bar over a single 72rem column; the reading
   measure is 68ch; tables and the library grid use the full column. */
:root{
  --paper:#f5f6f3; --paper-2:#ebeee8; --ink:#16201b; --ink-2:#47524c; --ink-3:#6b746f;
  --rule:#d5dad3; --accent:#0d5c55; --accent-ink:#0a4a44; --focus:#0d5c55;
  --ok:#1d6b3a; --ok-bg:#e1efe4; --no:#a2332b; --no-bg:#f6e3e0; --mixed:#8a5a00; --mixed-bg:#f6ecd6;
  --na:#5d6661; --na-bg:#e6e9e5; --zone:#d8e8de; --shade:#e9d9b8;
  --c1:#2a78d6; --c2:#eb6834; --c3:#1baf7a; --c4:#eda100; --c5:#e87ba4; --c6:#4a3aa7;
  --chart-ink:#16201b; --chart-muted:#8a938e; --grid:#e2e6e0;
  --serif:"Source Serif 4", "Iowan Old Style", Georgia, serif;
  --sans:"Public Sans", "Helvetica Neue", Arial, sans-serif;
  --step--1:.8125rem; --step-0:1rem; --step-1:1.1875rem; --step-2:1.5rem; --step-3:2rem; --step-4:2.875rem;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --paper:#111714; --paper-2:#18201c; --ink:#e7ebe8; --ink-2:#b4bdb8; --ink-3:#8e9893;
  --rule:#2b3530; --accent:#5cc2b5; --accent-ink:#7fd3c7; --focus:#7fd3c7;
  --ok:#7fcf97; --ok-bg:#183323; --no:#f09a8f; --no-bg:#3a1d1a; --mixed:#e7b75a; --mixed-bg:#352a12;
  --na:#a3aca7; --na-bg:#232b27; --zone:#1b3527; --shade:#3a3120;
  --c1:#3987e5; --c2:#d95926; --c3:#199e70; --c4:#c98500; --c5:#d55181; --c6:#9085e9;
  --chart-ink:#e7ebe8; --chart-muted:#7d8782; --grid:#253029; color-scheme:dark;
}}
:root[data-theme="dark"]{
  --paper:#111714; --paper-2:#18201c; --ink:#e7ebe8; --ink-2:#b4bdb8; --ink-3:#8e9893;
  --rule:#2b3530; --accent:#5cc2b5; --accent-ink:#7fd3c7; --focus:#7fd3c7;
  --ok:#7fcf97; --ok-bg:#183323; --no:#f09a8f; --no-bg:#3a1d1a; --mixed:#e7b75a; --mixed-bg:#352a12;
  --na:#a3aca7; --na-bg:#232b27; --zone:#1b3527; --shade:#3a3120;
  --c1:#3987e5; --c2:#d95926; --c3:#199e70; --c4:#c98500; --c5:#d55181; --c6:#9085e9;
  --chart-ink:#e7ebe8; --chart-muted:#7d8782; --grid:#253029; color-scheme:dark;
}
*{box-sizing:border-box}
html{scroll-padding-top:4.5rem}
body{margin:0;background:var(--paper);color:var(--ink);font:400 var(--step-0)/1.55 var(--sans);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
::selection{background:var(--accent);color:var(--paper)}
a{color:var(--accent-ink);text-underline-offset:.18em;text-decoration-thickness:1px}
a:hover{text-decoration-thickness:2px}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:2px}
.wrap{max-width:72rem;margin:0 auto;padding-inline:clamp(1rem,3vw,2rem)}
h1,h2,h3,h4{font-family:var(--serif);font-weight:600;text-wrap:balance;margin:0;color:var(--ink)}
p{margin:0}
.num,.data td,.ledger .g-val,.g-axis{font-variant-numeric:tabular-nums}

/* masthead */
.mast{padding-block:clamp(2.5rem,6vw,4.5rem) 2rem;border-bottom:1px solid var(--rule)}
.mast h1{font-size:clamp(2.25rem,6vw,var(--step-4));line-height:1.05;letter-spacing:-.02em;font-weight:700}
.mast h1 em{font-style:normal;color:var(--accent-ink)}
.mast .lede{max-width:62ch;margin-top:1rem;font-size:var(--step-1);color:var(--ink-2);line-height:1.5}
.facts{display:flex;flex-wrap:wrap;gap:.5rem 2rem;margin-top:1.5rem;font-size:var(--step--1);color:var(--ink-3)}
.facts strong{color:var(--ink);font-weight:600}
.tally{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:1.25rem}

/* contents bar */
.toc{position:sticky;top:env(safe-area-inset-top,0px);z-index:10;background:color-mix(in srgb,var(--paper) 92%,transparent);
  backdrop-filter:saturate(1.2) blur(8px);border-bottom:1px solid var(--rule)}
.toc ol{list-style:none;margin:0;padding:0;display:flex;gap:.25rem;overflow-x:auto;scrollbar-width:none}
.toc ol::-webkit-scrollbar{display:none}
.toc a{display:block;padding:.85rem .75rem;font-size:var(--step--1);font-weight:600;color:var(--ink-2);
  text-decoration:none;white-space:nowrap;border-bottom:2px solid transparent}
.toc a:hover{color:var(--ink)}
.toc a[aria-current="true"]{color:var(--ink);border-bottom-color:var(--accent)}

/* sections */
.sec{padding-block:clamp(2.5rem,5vw,4rem) 0}
.sec > h2{font-size:var(--step-3);line-height:1.15;letter-spacing:-.01em}
.sec-intro{max-width:68ch;margin-top:.75rem;color:var(--ink-2)}
.sec-intro + *{margin-top:1.75rem}
.sub-h{font-size:var(--step-2);margin-top:3rem}
.note{font-size:var(--step--1);color:var(--ink-3);max-width:72ch;margin-top:.75rem}

/* verdict pills */
.pill{display:inline-flex;align-items:center;gap:.35rem;padding:.2rem .6rem .2rem .45rem;border-radius:999px;
  font:600 var(--step--1)/1.2 var(--sans);white-space:nowrap}
.pill svg{width:.85rem;height:.85rem;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.pill-ok{color:var(--ok);background:var(--ok-bg)} .pill-no{color:var(--no);background:var(--no-bg)}
.pill-mixed{color:var(--mixed);background:var(--mixed-bg)} .pill-na{color:var(--na);background:var(--na-bg)}

/* tables */
.tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;vertical-align:top}
thead th{font:600 var(--step--1)/1.3 var(--sans);color:var(--ink-3);
  padding:.75rem .75rem .6rem;border-top:1px solid var(--ink);border-bottom:1px solid var(--rule)}
.ledger td{padding:1rem .75rem;border-bottom:1px solid var(--rule)}
.ledger .lg-group th{font:600 var(--step--1)/1.3 var(--sans);color:var(--ink);padding:1.4rem .75rem .5rem;
  border-bottom:1px solid var(--rule);text-transform:none;letter-spacing:0}
.lg-id a{font:700 var(--step-0)/1.3 var(--serif);color:var(--ink);text-decoration:none}
.lg-q{min-width:16rem}
.lg-q a{display:block;font-weight:600;color:var(--ink);text-decoration:none}
.lg-q a:hover{text-decoration:underline}
.lg-q span{display:block;color:var(--ink-3);font-size:var(--step--1);margin-top:.15rem}
.lg-g{width:34%;min-width:15rem}
.lg-v{white-space:nowrap}

/* gauge — the result vs the pre-registered threshold */
.gauge{position:relative;padding-top:1.35rem;min-width:13rem}
.g-track{position:relative;height:.5rem;border-radius:999px;background:var(--paper-2);box-shadow:inset 0 0 0 1px var(--rule)}
.g-zone{position:absolute;top:0;bottom:0;background:var(--zone);border-radius:999px}
.g-thr{position:absolute;top:-.3rem;bottom:-.3rem;width:2px;margin-left:-1px;background:var(--ink)}
.g-dot{position:absolute;top:50%;width:.85rem;height:.85rem;margin:-.425rem 0 0 -.425rem;border-radius:50%;
  border:2px solid var(--paper);box-shadow:0 1px 2px rgb(0 0 0 / .25)}
.g-dot.v-ok{background:var(--ok)} .g-dot.v-no{background:var(--no)} .g-dot.v-mixed{background:var(--mixed)} .g-dot.v-na{background:var(--na)}
.g-dot.off{border-style:dashed}
.g-val{position:absolute;top:0;transform:translateX(-50%);font:600 .75rem/1 var(--sans);color:var(--ink);white-space:nowrap}
.g-axis{position:relative;display:flex;justify-content:space-between;margin-top:.35rem;font-size:.6875rem;color:var(--ink-3)}
.g-thr-l{position:absolute;transform:translateX(-50%);color:var(--ink-2);font-weight:600;white-space:nowrap}

/* test articles */
.tests{display:grid;gap:0;margin-top:2rem}
.group-h{font-size:var(--step-2);margin-top:3rem;padding-bottom:.5rem;border-bottom:1px solid var(--ink)}
.test{padding-block:2rem;border-bottom:1px solid var(--rule)}
.test-h{display:flex;flex-wrap:wrap;align-items:baseline;gap:.5rem 1rem}
.test-id{font:700 var(--step-1)/1 var(--serif);color:var(--ink-3)}
.test-h h3{font-size:var(--step-2);line-height:1.2;flex:1 1 18rem}
.test-body{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:2rem;margin-top:1.25rem}
.test-dl{margin:0;display:grid;gap:.9rem;align-content:start}
.test-dl dt{font:600 .75rem/1.3 var(--sans);letter-spacing:.04em;text-transform:uppercase;color:var(--ink-3)}
.test-dl dd{margin:.2rem 0 0;max-width:62ch}
.test-dl .result{font-weight:600}
.test-dl .inputs{font-size:var(--step--1);color:var(--ink-3)}
.test-fig{margin:0;min-width:0}
.chart{width:100%;min-height:300px}
.chart.sm{min-height:170px}
.chart .panel{width:100%}
.legend{display:flex;flex-wrap:wrap;gap:.35rem 1rem;font-size:var(--step--1);color:var(--ink-2);margin:0 0 .4rem}
.legend i{display:inline-block;width:1rem;height:.2rem;border-radius:2px;vertical-align:middle;margin-right:.4rem}
.legend i.dot{background:transparent!important;border-top:2px dotted var(--chart-ink);height:0}
.fig-note{font-size:.75rem;color:var(--ink-3);margin-top:.5rem}
.empty{font-size:var(--step--1);color:var(--ink-3);padding:1.5rem;border:1px dashed var(--rule);border-radius:4px}

/* companies */
.data td,.data tbody th{padding:.8rem .75rem;border-bottom:1px solid var(--rule)}
.data td{white-space:nowrap;font-size:var(--step-0)}
.data .sub{display:block;font-size:.6875rem;color:var(--ink-3);margin-top:.1rem}
.co tbody th{min-width:15rem;font-weight:400}
.co-name{font-weight:600}
.co-role{display:block;font-size:var(--step--1);color:var(--ink-3);white-space:normal;max-width:24rem}
.swatch{display:inline-block;width:.7rem;height:.7rem;border-radius:2px;margin-right:.5rem;vertical-align:baseline}
.s-c1{background:var(--c1)} .s-c2{background:var(--c2)} .s-c3{background:var(--c3)}
.s-c4{background:var(--c4)} .s-c5{background:var(--c5)} .s-c6{background:var(--c6)}
.multiples{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,20rem),1fr));gap:1.75rem 2rem;margin-top:1rem}
.multiples h4{font:600 var(--step--1)/1.3 var(--sans);color:var(--ink)}
.mult-panel{min-width:0}

/* book */
.book{list-style:none;counter-reset:b;margin:1.75rem 0 0;padding:0;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(min(100%,21rem),1fr));gap:0 2.5rem}
.book li{padding:1rem 0 1.1rem;border-top:1px solid var(--rule)}
.book h3{font-size:var(--step-1);line-height:1.25}
.book .ev{margin-top:.4rem;color:var(--ink-2);font-size:var(--step--1)}

/* library */
.tabs{display:flex;gap:.4rem;flex-wrap:wrap;margin-top:1.5rem}
.tabs button{font:600 var(--step--1)/1 var(--sans);color:var(--ink-2);background:transparent;cursor:pointer;
  border:1px solid var(--rule);border-radius:999px;padding:.5rem .85rem;display:inline-flex;gap:.45rem;align-items:center}
.tabs button:hover{border-color:var(--ink-3);color:var(--ink)}
.tabs button[aria-selected="true"]{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.tabs .count{font-weight:500;opacity:.7}
.scope{margin-top:1.25rem;color:var(--ink-2);font-size:var(--step--1)}
.lib-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,19rem),1fr));gap:1.5rem 2rem;margin-top:1rem}
.lib-card{margin:0;min-width:0;padding-top:.85rem;border-top:1px solid var(--rule)}
.lib-card h3{font:600 var(--step-0)/1.3 var(--sans)}
.lib-card p{font-size:.75rem;color:var(--ink-3);margin-top:.15rem}
.lib-card .last{color:var(--ink-2);font-size:var(--step--1)}
.lib-card .last strong{color:var(--ink);font-variant-numeric:tabular-nums}
.lib-card .gloss{color:var(--ink-2);font-size:var(--step--1)}
.stale{display:inline-block;color:var(--mixed);background:var(--mixed-bg);border-radius:999px;padding:.05rem .5rem;font-weight:600;font-size:.75rem}

/* sources */
.cols{align-items:start;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,26rem),1fr));gap:2rem 3rem;margin-top:1.75rem}
.cols h3{font-size:var(--step-1);margin-bottom:.75rem}
.method{max-width:68ch;display:grid;gap:.75rem;align-content:start;color:var(--ink-2)}
.wrap-cell{white-space:normal!important;min-width:16rem;color:var(--ink-2)}
.method strong{color:var(--ink)}
.small td,.small th{font-size:var(--step--1)}
.foot{padding-block:3rem 4rem;margin-top:4rem;border-top:1px solid var(--rule);font-size:var(--step--1);color:var(--ink-3)}

@media (max-width:52rem){
  .test-body{grid-template-columns:minmax(0,1fr)}
}
@media (max-width:40rem){
  .ledger thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
  .ledger,.ledger tbody,.ledger tr,.ledger td,.ledger th{display:block}
  .ledger tr:not(.lg-group){display:grid;grid-template-columns:2.5rem minmax(0,1fr);column-gap:.5rem;
    padding:1rem 0;border-bottom:1px solid var(--rule)}
  .ledger td{border:0;padding:0}
  .ledger .lg-id{grid-row:1 / span 3}
  .ledger .lg-q{min-width:0}
  .ledger .lg-g{width:auto;min-width:0;margin-top:.6rem}
  .ledger .lg-v{margin-top:.75rem}
  .ledger .lg-group th{padding-inline:0}
  .tbl-wrap:has(.ledger){overflow-x:visible}
}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
"""

JS = r"""
(function(){
const SPEC = JSON.parse(document.getElementById('spec').textContent);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const col = c => css(c === 'ink' ? '--chart-ink' : c === 'muted' ? '--chart-muted' : '--' + c);
const FONT = '"Public Sans", "Helvetica Neue", Arial, sans-serif';
const done = new Map();   // element -> render fn (re-run on theme change)
const MOBILE = () => window.matchMedia('(max-width: 40rem)').matches;

function baseLayout(h, ytitle, opts){
  const ink = css('--ink-2'), grid = css('--grid');
  return {
    height: h, margin: {l: 52, r: 12, t: 8, b: opts.xtitle ? 52 : 30}, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: FONT, size: 12, color: ink}, showlegend: false, hovermode: opts.kind === 'scatter' ? 'closest' : 'x unified',
    hoverlabel: {bgcolor: css('--paper'), bordercolor: css('--rule'), font: {family: FONT, color: css('--ink'), size: 12}},
    xaxis: {showgrid: false, linecolor: css('--rule'), tickcolor: css('--rule'), ticks: 'outside', ticklen: 4,
            title: opts.xtitle ? {text: opts.xtitle, font: {size: 11}} : undefined, zeroline: opts.kind === 'scatter',
            zerolinecolor: css('--rule'), fixedrange: true},
    yaxis: {gridcolor: grid, zeroline: false, title: ytitle ? {text: ytitle, font: {size: 11}, standoff: 6} : undefined,
            type: opts.log ? 'log' : 'linear', fixedrange: true, automargin: true,
            tickvals: opts.log ? [10, 25, 50, 100, 200, 400, 800] : undefined,
            ticktext: opts.log ? ['10', '25', '50', '100', '200', '400', '800'] : undefined},
    shapes: [], annotations: []
  };
}
function traces(p, kind){
  return p.series.map(s => {
    const c = col(s.c);
    if (kind === 'scatter') return {type: 'scatter', mode: 'markers', name: s.name, x: s.x, y: s.y, text: s.labels,
      marker: {size: 7, color: c, opacity: .7, line: {width: 1, color: css('--paper')}},
      hovertemplate: '<b>' + s.name + '</b> %{text}<br>BRL %{x:+.1f}% · stock %{y:+.1f}%<extra></extra>'};
    if (s.bars || p.bars) return {type: 'bar', name: s.name, x: s.x, y: s.y, marker: {color: c},
      hovertemplate: '%{y:,.1f}<extra>' + s.name + '</extra>'};
    return {type: 'scatter', mode: 'lines', name: s.name, x: s.x, y: s.y, connectgaps: false,
      line: {color: c, width: s.c === 'muted' ? 1.5 : 2, dash: s.dash || 'solid'},
      hovertemplate: '%{y:,.1f}<extra>' + s.name + '</extra>'};
  });
}
function decorate(L, p){
  const ink = css('--ink-3');
  if (p.hline) { L.shapes.push({type: 'line', xref: 'paper', x0: 0, x1: 1, y0: p.hline.y, y1: p.hline.y,
      line: {color: css('--ink-3'), width: 1, dash: 'dash'}});
    if (p.hline.label) L.annotations.push({xref: 'paper', x: 1, y: p.hline.y, text: p.hline.label, showarrow: false,
      xanchor: 'right', yanchor: 'bottom', font: {size: 11, color: ink}}); }
  if (p.vline) { L.shapes.push({type: 'line', yref: 'paper', y0: 0, y1: 1, x0: p.vline.x, x1: p.vline.x,
      line: {color: ink, width: 1, dash: 'dot'}});
    L.annotations.push({yref: 'paper', y: 1, x: p.vline.x, text: p.vline.label, showarrow: false, xanchor: 'left',
      yanchor: 'top', xshift: 4, font: {size: 11, color: ink}}); }
  (p.shade || []).forEach(([a, b]) => L.shapes.push({type: 'rect', layer: 'below', yref: 'paper', y0: 0, y1: 1,
      x0: a, x1: b, fillcolor: css('--shade'), line: {width: 0}}));
}
function legendHTML(series){
  return '<p class="legend">' + series.map(s => '<span><i class="' + (s.dash ? 'dot' : '') +
    '" style="background:' + col(s.c) + '"></i>' + s.name + '</span>').join('') + '</p>';
}
function drawPanel(el, p, kind, h){
  const L = baseLayout(h, p.y, {kind, log: p.log, xtitle: p.x});
  if (MOBILE()) { L.margin.l = 44; }
  decorate(L, p);
  Plotly.react(el, traces(p, kind), L, {displayModeBar: false, responsive: true});
}
function renderChart(el, spec){
  const draw = () => {
    el.innerHTML = '';
    spec.panels.forEach((p, i) => {
      const wrap = document.createElement('div');
      wrap.className = spec.grid ? 'mult-panel' : 'panel';
      if (spec.grid && p.title) wrap.insertAdjacentHTML('beforeend', '<h4>' + p.title + '</h4>');
      if (!spec.grid || p.series.length > 1) wrap.insertAdjacentHTML('beforeend', legendHTML(p.series));
      const plot = document.createElement('div');
      wrap.appendChild(plot);
      el.appendChild(wrap);
      drawPanel(plot, p, spec.kind, p.height || (spec.grid ? 220 : (spec.panels.length > 1 ? 190 : 300)));
    });
    if (spec.note) el.insertAdjacentHTML('beforeend', '<p class="fig-note">' + spec.note + '</p>');
  };
  if (spec.grid) el.classList.add('multiples');
  draw(); done.set(el, draw);
}
function renderLib(el, c){
  const draw = () => {
    const L = baseLayout(170, '', {});
    L.margin = {l: 44, r: 8, t: 4, b: 24}; L.font.size = 11;
    const tr = [{type: 'scatter', mode: c.annual ? 'lines+markers' : 'lines', x: c.x, y: c.y,
      line: {color: col('c1'), width: 1.75}, marker: {size: 4, color: col('c1')},
      hovertemplate: '%{x|' + (c.freq === 'daily' || c.freq === 'weekly' ? '%d %b %Y' : c.annual ? '%Y' : '%b %Y') +
        '}: %{y:,.2f}<extra></extra>'}];
    L.hovermode = 'closest';
    L.shapes.push({type: 'line', yref: 'paper', y0: 0, y1: 1, x0: '2012-01-01', x1: '2012-01-01',
      line: {color: css('--ink-3'), width: 1, dash: 'dot'}});
    Plotly.react(el, tr, L, {displayModeBar: false, responsive: true});
  };
  draw(); done.set(el, draw);
}
const io = new IntersectionObserver(entries => entries.forEach(e => {
  if (!e.isIntersecting || done.has(e.target) || !window.Plotly) return;
  const t = e.target;
  if (t.dataset.chart && SPEC.charts[t.dataset.chart]) renderChart(t, SPEC.charts[t.dataset.chart]);
  else if (t.dataset.lib && SPEC.lib[t.dataset.lib]) renderLib(t, SPEC.lib[t.dataset.lib]);
  io.unobserve(t);
}), {rootMargin: '400px 0px'});
function observeAll(){ document.querySelectorAll('[data-chart],[data-lib]').forEach(el => { if (!done.has(el)) io.observe(el); }); }
function rerender(){ done.forEach(fn => fn()); }
if (window.Plotly) observeAll();
else document.querySelectorAll('[data-chart],[data-lib]').forEach(el =>
  el.innerHTML = '<p class="empty">Charts need the Plotly library, which did not load. The tables and verdicts above still hold.</p>');
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', rerender);
new MutationObserver(rerender).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});

// library tabs (roving tabindex, arrow keys)
const tabs = [...document.querySelectorAll('.tabs [role="tab"]')];
function select(t, focus){
  tabs.forEach(b => { const on = b === t; b.setAttribute('aria-selected', on); b.tabIndex = on ? 0 : -1;
    document.getElementById(b.getAttribute('aria-controls')).hidden = !on; });
  if (focus) t.focus();
  try { localStorage.setItem('bt-tab', t.dataset.tab); } catch (e) {}
  requestAnimationFrame(() => { observeAll(); window.dispatchEvent(new Event('resize')); });
}
tabs.forEach((t, i) => {
  t.addEventListener('click', () => select(t));
  t.addEventListener('keydown', e => {
    const k = {ArrowRight: 1, ArrowLeft: -1}[e.key];
    if (k) { e.preventDefault(); select(tabs[(i + k + tabs.length) % tabs.length], true); }
    if (e.key === 'Home') { e.preventDefault(); select(tabs[0], true); }
    if (e.key === 'End') { e.preventDefault(); select(tabs[tabs.length - 1], true); }
  });
});
try { const s = localStorage.getItem('bt-tab'); const t = tabs.find(b => b.dataset.tab === s); if (t) select(t); } catch (e) {}

// contents bar: mark the section in view
const links = [...document.querySelectorAll('.toc a')];
const secs = links.map(a => document.querySelector(a.getAttribute('href')));
const so = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) links.forEach(a => a.setAttribute('aria-current', a.getAttribute('href') === '#' + e.target.id));
}), {rootMargin: '-45% 0px -50% 0px'});
secs.forEach(s => s && so.observe(s));
})();
"""


PROGRESS = [  # (area, status, note) — the build log shown on the progress page
    ("Native adapters (BCB SGS/Focus/Pix, IBGE, ComexStat, IPEAData, ANP, ONS, Tesouro, B3, CVM)", "done",
     "14 adapters; BCB moved to SGS SOAP after api.bcb.gov.br went NXDOMAIN"),
    ("Company layer (Petrobras, Vale, Axia, Suzano, PRIO, Itaú)", "done",
     "prices, dividends, total return, CVM statements, operated oil, plant generation"),
    ("Merged catalog + observations + reconciliation (DuckDB, Parquet)", "done",
     "catalog.py; native canonical, Dateno/World Bank alternates; warehouse/export/*.parquet"),
    ("Brazil Monitoring platform (catalogue, curated pages, multi-series charts, SQL dock)", "done", "portal.py, published separately"),
    ("Dateno statsdb full Brazil pull (wb + ilostat)", "blocked",
     "API key capped at 200 requests/day, 500/month; full pull needs ~35k requests"),
    ("World Bank + ILOSTAT full Brazil pull from the upstreams Dateno mirrors", "done",
     "14,881 series (13,589 World Bank across 40 databases, 1,292 ILO); same ids as Dateno"),
    ("Dateno discovery for missing registry metrics", "done", "registry/dateno_candidates.json"),
    ("Health data (WHO Mortality DB, DATASUS SIM, IBGE PNS)", "done",
     "17 series; WHO NCD microdata needs registration, not ingested"),
    ("Political calendar overlay (terms since 1985, 34 events)", "done", "registry/political_*.csv"),
    ("Hypothesis tests (10)", "done", "reviewed for code, data and design; L2 re-specified on review"),
]


def progress_html(silver):
    try:
        cat = pd.read_parquet(GOLD / "catalog.parquet")
    except Exception:  # noqa: BLE001 — progress page still renders before catalog.py has run
        cat = pd.DataFrame(columns=["source", "series_id", "n_obs", "last"])
    by = (cat.groupby("source").agg(series=("series_id", "size"), obs=("n_obs", "sum"), last=("last", "max"))
          .sort_values("series", ascending=False))
    src = "".join(f"<tr><th scope='row'>{esc(k)}</th><td class='num'>{int(v.series):,}</td>"
                  f"<td class='num'>{int(v.obs):,}</td><td class='num'>{esc(str(v['last'])[:10])}</td></tr>"
                  for k, v in by.iterrows())
    cls = {"done": "ok", "in progress": "mixed", "researching": "mixed", "blocked": "no"}
    items = "".join(f"<tr><th scope='row'>{esc(a)}</th><td><span class='pill pill-{cls.get(st, 'na')}'>{esc(st)}</span></td>"
                    f"<td class='wrap-cell'>{esc(n)}</td></tr>" for a, st, n in PROGRESS)
    return (f"<div class='cols'><div><h3>Build log</h3><div class='tbl-wrap'><table class='data small'><thead><tr>"
            f"<th scope='col'>Area</th><th scope='col'>Status</th><th scope='col'>Note</th></tr></thead><tbody>{items}"
            f"</tbody></table></div></div><div><h3>Warehouse by source</h3><div class='tbl-wrap'><table class='data small'>"
            f"<thead><tr><th scope='col'>Source</th><th scope='col'>Series</th><th scope='col'>Observations</th>"
            f"<th scope='col'>Latest</th></tr></thead><tbody>{src}</tbody></table></div></div></div>")


def main():
    silver = pd.read_parquet(SILVER)
    hyp = pd.read_parquet(GOLD / "hypothesis_tests.parquet")
    sc = pd.read_parquet(GOLD / "book_scorecard.parquet")
    dq = pd.read_csv(DQ)

    hc = hyp_charts(silver)
    cc = company_charts(silver)
    lib_html, lib_specs = library(silver, frozenset(dq[dq.check != "fresh"].metric_id))
    co_rows = company_rows(silver)
    src_rows, stale_rows, n_dq, n_stale = sources_table(silver, dq)

    as_of = pd.Timestamp(silver[silver.freq == "daily"].date.max()).strftime("%d %B %Y")
    n_series = silver.groupby(["metric_id", "entity_id"]).ngroups
    counts = hyp.verdict.value_counts()
    tally = "".join(f"<span>{verdict_pill(v)} <span class='num'>× {counts.get(v, 0)}</span></span>"
                    for v in ["Supported", "Mixed", "Not supported", "Insufficient data"] if counts.get(v, 0))
    res_w = float(silver[silver.metric_id == "ibov_resource_energy_weight"].value.iloc[-1]) \
        if (silver.metric_id == "ibov_resource_energy_weight").any() else None
    five_w = sum(r["weight"] or 0 for r in co_rows if r["id"] in H.RESOURCE)

    tests_html = []
    for g in GROUP_ORDER:
        sub = hyp[hyp.group == g]
        if sub.empty:
            continue
        tests_html.append(f"<h3 class='group-h'>{esc(g)}</h3>")
        tests_html += [hyp_detail(r, r.hyp_id.lower() in hc) for r in sub.itertuples()]

    spec = json.dumps({"charts": {**hc, **cc}, "lib": lib_specs}, separators=(",", ":"), allow_nan=False)
    spec = spec.replace("</", "<\\/")

    body = f"""
<header class='mast'><div class='wrap'>
  <h1>Brazil macro: <em>progress &amp; tests</em></h1>
  <p class='lede'>Ten claims about Brazil's resource economy, its biggest resource companies and its
  households, each turned into a test with a threshold set before looking at the result, and run on
  free public data.</p>
  <div class='tally' aria-label='Verdict count'>{tally}</div>
  <p class='facts'><span>Data to <strong>{esc(as_of)}</strong></span>
  <span><strong>{n_series:,}</strong> series</span><span><strong>{len(silver):,}</strong> observations</span>
  <span>Sources: BCB, IBGE, ComexStat, ANP, ONS, B3, CVM, Tesouro, IPEAData, World Bank</span></p>
</div></header>
<nav class='toc' aria-label='Contents'><div class='wrap'><ol>
  <li><a href='#progress'>Progress</a></li><li><a href='#tests'>Ten tests</a></li><li><a href='#companies'>Six companies</a></li>
  <li><a href='#book'>The 2012 book</a></li><li><a href='#library'>Data library</a></li>
  <li><a href='#sources'>Sources &amp; method</a></li></ol></div></nav>
<main class='wrap'>
<section class='sec' id='progress' aria-labelledby='prog-h'>
  <h2 id='prog-h'>Progress</h2>
  <p class='sec-intro'>What is built, what is blocked, and what the warehouse holds. Browse every series in the
  data platform; this page tracks the build and the hypothesis tests run on it.</p>
  {progress_html(silver)}
</section>
<section class='sec' id='tests' aria-labelledby='tests-h'>
  <h2 id='tests-h'>Ten tests</h2>
  <p class='sec-intro'>Each row is one hypothesis. The bar shows where the statistic landed against its
  threshold; the shaded side passes. Select a test for its claim, method, inputs and chart.</p>
  {ledger(hyp)}
  <div class='tests'>{''.join(tests_html)}</div>
</section>

<section class='sec' id='companies' aria-labelledby='co-h'>
  <h2 id='co-h'>Six companies</h2>
  <p class='sec-intro'>Petrobras, Vale, Axia (formerly Eletrobras), Suzano and PRIO are {fmt(five_w, 1, '%')}
  of the Ibovespa; resource and energy sectors as a whole are {fmt(res_w, 1, '%')}. Itaú, the largest
  private bank, is the domestic, non-resource control. Weights are B3's current theoretical portfolio.</p>
  {company_table(co_rows)}
  <p class='note'>Total return reinvests cash dividends and interest on capital on the ex-date and adjusts
  for splits and bonus shares. Itaú's total return omits the 2021 XP spin-off (about −16% from then).
  Net debt is loans, debentures and leases minus cash. Financials are CVM consolidated filings.</p>
  <h3 class='sub-h'>What US$100 in January 2012 became</h3>
  <div class='chart' data-chart='c_tr'></div>
  <h3 class='sub-h'>Revenue and net income</h3>
  <div class='chart' data-chart='c_rev'></div>
  <h3 class='sub-h'>What they produce</h3>
  <div class='chart' data-chart='c_phys'></div>
</section>

<section class='sec' id='book' aria-labelledby='book-h'>
  <h2 id='book-h'>The 2012 book, checked</h2>
  <p class='sec-intro'>James Dale Davidson's <cite>Brazil Is the New America</cite> (2012) made a set of bets.
  The evidence for each, computed from the same warehouse.</p>
  {scorecard_list(sc)}
</section>

<section class='sec' id='library' aria-labelledby='lib-h'>
  <h2 id='lib-h'>Data library</h2>
  <p class='sec-intro'>Every country-level series in the warehouse, by chapter. Daily series are shown weekly.
  The dotted line marks January 2012.</p>
  {lib_html}
</section>

<section class='sec' id='sources' aria-labelledby='src-h'>
  <h2 id='src-h'>Sources &amp; method</h2>
  <div class='cols'>
    <div class='method'>
      <h3>How the verdicts work</h3>
      <p><strong>Thresholds are fixed in code</strong> (<code>hypotheses.py</code>) before the data is read, and
      every build re-runs every test, so a verdict can change as new data arrives.</p>
      <p><strong>Supported</strong>: every condition in the threshold is met. <strong>Mixed</strong>: some
      conditions are met, or the main statistic is in the agreed middle band. <strong>Not supported</strong>:
      the result falls on the refuting side. <strong>Insufficient data</strong>: an input is missing.</p>
      <p>Correlations are not causal estimates. Ownership of power plants is today's snapshot applied to
      history; operated oil output is gross, not equity; pre-salt share after 2023 extends ANP's own well
      classification.</p>
    </div>
    <div>
      <h3>Where the numbers come from</h3>
      <div class='tbl-wrap'><table class='data small'><thead><tr><th scope='col'>Source</th>
      <th scope='col'>Series</th><th scope='col'>From</th><th scope='col'>Latest</th></tr></thead>
      <tbody>{src_rows}</tbody></table></div>
    </div>
  </div>
  <h3 class='sub-h'>Freshness</h3>
  <p class='sec-intro'>{n_dq - n_stale} of {n_dq} series are within their expected publication lag.
  {"These are behind:" if n_stale else ""}</p>
  {"<div class='tbl-wrap'><table class='data small'><thead><tr><th scope='col'>Series</th><th scope='col'>Frequency</th><th scope='col'>Last observation</th><th scope='col'>Why</th></tr></thead><tbody>" + stale_rows + "</tbody></table></div>" if n_stale else ""}
</section>
</main>
<footer class='foot'><div class='wrap'>Built by <code>pipeline.py</code> and <code>dashboard.py</code> from the
brazil-macro warehouse. Figures are descriptive statistics from public data, not investment advice.</div></footer>
<script id='spec' type='application/json'>{spec}</script>
<script src='{PLOTLY}'></script>
<script>{JS}</script>
"""
    head = (f"<title>Brazil Macro Progress</title>\n<link rel='preconnect' href='https://fonts.googleapis.com'>"
            f"<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
            f"<link rel='stylesheet' href='{FONTS}'>\n<style>{CSS}</style>\n")
    OUT_ARTIFACT.write_text(head + body)
    OUT.write_text("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                   "<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>"
                   + head + "</head><body>" + body + "</body></html>")
    print(f"Wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")
    print(f"Wrote {OUT_ARTIFACT}")
    print(f"Open: file://{OUT}")


if __name__ == "__main__":
    main()
