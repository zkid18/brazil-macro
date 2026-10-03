"""catalog.py — merge every source into one research-ready warehouse.

Inputs
  warehouse/silver/fact_time_series.parquet   native + company + derived series (pipeline.py)
  warehouse/bronze/dateno/catalog.parquet       every Brazil series in Dateno statsdb (wb, ilostat)
  warehouse/bronze/dateno/observations.parquet  their values (ingest/dateno_bulk.py)

Outputs (gold, also loaded into warehouse/brazil_macro.duckdb)
  catalog          one row per series: series_id, title, topic, source, entity, freq, unit,
                   coverage, latest value, freshness, role (canonical / alternate / derived)
  observations     long: series_id, date, value  (every observation of every series)
  reconciliation   concept-level comparison where two sources measure the same thing:
                   overlap, mean absolute difference, correlation, which one is canonical

series_id
  native / company / derived : <metric_id>            or <metric_id>@<ENTITY>  (PETR, VALE, ...)
  Dateno                     : wb/<ts_id>  ilostat/<ts_id>

Rule for overlaps: the native, higher-frequency source is canonical (fresher, official
publisher); the Dateno/World Bank series is kept as an alternate with its history, and the
reconciliation table shows how far apart they are on common years.
Run:  python3 catalog.py   (pipeline.py calls it)
"""
from __future__ import annotations
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
SILVER = ROOT / "warehouse" / "silver" / "fact_time_series.parquet"
DATENO = ROOT / "warehouse" / "bronze" / "dateno"
GOLD = ROOT / "warehouse" / "gold"
EXPORT = ROOT / "warehouse" / "export"

# --- topics: one vocabulary across sources -------------------------------------------
TOPIC_OF_THEME = {
    "macro_policy": "Money & rates", "expectations": "Money & rates", "market_repricing": "Markets",
    "inflation": "Prices", "macro_activity": "Output & activity", "domestic_demand": "Credit & households",
    "labor": "Labour", "fiscal": "Public finances", "external_sector": "External sector",
    "external_trade": "Trade", "agriculture_trade": "Trade", "energy_trade": "Trade",
    "minerals_trade": "Trade", "forestry_trade": "Trade", "derived_trade": "Trade",
    "agriculture_risk": "Agriculture & land", "derived_agriculture": "Agriculture & land",
    "oil_gas": "Energy", "energy_water": "Energy", "structural_energy": "Energy",
    "demography": "Population", "investment_productivity": "Output & activity",
    "companies": "Companies", "unknown": "Output & activity", "health": "Health",
}
# World Development Indicators code prefix -> topic (WDI naming convention)
WDI_PREFIX = [
    ("NY.", "Output & activity"), ("NV.", "Output & activity"), ("NE.", "Output & activity"),
    ("SL.", "Labour"), ("SP.", "Population"), ("SM.", "Population"), ("SH.", "Health"),
    ("SN.", "Health"), ("SE.", "Education"), ("SI.", "Poverty & inequality"),
    ("SG.", "Gender"), ("EG.", "Energy"), ("EN.", "Environment"), ("ER.", "Environment"),
    ("AG.", "Agriculture & land"), ("FP.", "Prices"), ("PA.", "Prices"), ("FR.", "Money & rates"),
    ("FM.", "Money & rates"), ("FS.", "Money & rates"), ("FD.", "Money & rates"),
    ("FB.", "Money & rates"), ("FX.", "Money & rates"), ("FI.", "External sector"),
    ("BN.", "External sector"), ("BX.", "External sector"), ("BM.", "External sector"),
    ("DT.", "External debt"), ("GC.", "Public finances"), ("GB.", "Science & technology"),
    ("IP.", "Science & technology"), ("IT.", "Infrastructure"), ("IS.", "Infrastructure"),
    ("IC.", "Business environment"), ("IE.", "Business environment"), ("IQ.", "Governance"),
    ("CM.", "Markets"), ("TX.", "Trade"), ("TM.", "Trade"), ("TG.", "Trade"), ("ST.", "Trade"),
    ("MS.", "Public finances"), ("VC.", "Governance"), ("CC.", "Governance"), ("GE.", "Governance"),
    ("PV.", "Governance"), ("RL.", "Governance"), ("RQ.", "Governance"), ("VA.", "Governance"),
    ("PER_", "Social protection"), ("HD.", "Education"), ("UIS.", "Education"),
]
ILO_PREFIX = [("UNE_", "Labour"), ("EMP_", "Labour"), ("EAP_", "Labour"), ("EAR_", "Wages & earnings"),
              ("HOW_", "Labour"), ("INJ_", "Health"), ("SDG_", "Labour"), ("POP_", "Population"),
              ("CPI_", "Prices"), ("GDP_", "Output & activity"), ("LAP_", "Wages & earnings"),
              ("LUU_", "Labour"), ("EIP_", "Labour"), ("TRU_", "Labour"), ("CLD_", "Labour"),
              ("SOC_", "Social protection"), ("STR_", "Labour"), ("TRD_", "Labour")]
SOURCE_NAME = {
    "bcb_sgs": "Banco Central (SGS)", "bcb_focus": "Banco Central (Focus)", "bcb_olinda_pix": "Banco Central (Pix)",
    "ibge_sidra": "IBGE (SIDRA)", "comexstat": "ComexStat (MDIC)", "ipeadata": "IPEAData",
    "ons": "ONS", "ons_open_data": "ONS", "tesouro_direto": "Tesouro Direto", "anp": "ANP",
    "b3_cotahist": "B3", "b3_dividends": "B3", "b3_ibov_portfolio": "B3", "cvm_itr_dfp": "CVM",
    "derived": "Derived", "dateno_wb": "World Bank (Dateno)", "dateno_ilostat": "ILO (Dateno)", "epe_ben": "World Bank (Dateno)",
    "datasus_sim": "DATASUS (SIM)", "who_mdb": "WHO Mortality Database",
}
ENTITY_NAME = {"BR": "Brazil", "PETR": "Petrobras", "VALE": "Vale", "AXIA": "Axia (ex-Eletrobras)",
               "SUZB": "Suzano", "PRIO": "PRIO", "ITUB": "Itaú Unibanco", "IBOV": "Ibovespa"}
# CCDR republishes the Worldwide Governance Indicators already carried by WDI
CCDR_WGI = re.compile(r"^wb/(CC|GE|PV|RL|RQ|VA)\.(EST|SC|PER\.RNK)\.BRA$")
JUNK_TITLE = (r"^p-value|standard error|lower bound|upper bound|confidence interval|number of sources|"
              r"\bstd\.? ?err|margin of error")
# Brazilian-source series that duplicate another Brazilian-source series (dropped -> kept)
NATIVE_DUPS = {"gas_production": "gas_production_mm3d"}
# topic fixes for native series whose bronze theme is too broad
TOPIC_OVERRIDE = {"population": "Population", "ibc_br": "Output & activity", "retail_sales_volume": "Output & activity",
                  "vehicle_sales": "Output & activity", "vehicle_production": "Output & activity",
                  "pix_transactions_count": "Output & activity", "pix_transactions_value": "Output & activity"}
UNIT_OK = re.compile(r"(%|percent|us\$|lcu|\$|usd|number|people|persons|tonnes|tons|kilotonnes|kg|index|ratio|years|"
                     r"days|hours|per |km|hectares|kwh|gwh|mw|liters|litres|metric|currency|rate|score|scale|share|"
                     r"births|deaths|cases|units|thousands|millions|billions|ppp|constant|current|real|nominal)", re.I)


def clean_unit(u):
    if u is None or (isinstance(u, float) and np.isnan(u)) or u is pd.NA:
        return None
    u = str(u).strip()
    u = re.sub(r"^[A-Z]{2,4}, ", "", u)          # "DOD, current US$" -> "current US$"
    return u if UNIT_OK.search(u) and len(u) <= 60 else None


MIN_OBS = 5  # World Bank / ILO series with fewer observations are survey one-offs, not time series
STALE_DAYS = {"daily": 10, "weekly": 21, "monthly": 100, "quarterly": 200, "annual": 1300, "event": 4000}

# Concepts measured by both a native source and Dateno (World Bank / ILO). Native first.
# (concept, native series_id, native->annual rule, Dateno ts_id candidates)
CONCEPTS = [
    ("unemployment_rate", "unemployment_rate", "mean", ["wb/SL.UEM.TOTL.ZS.BR", "wb/SL.UEM.TOTL.NE.ZS.BR"]),
    ("fx_reserves_usd", "fx_reserves", "dec_x1e6", ["wb/FI.RES.TOTL.CD.BR", "wb/FI.RES.XGLD.CD.BR"]),
    ("brl_per_usd", "brl_usd", "mean", ["wb/PA.NUS.FCRF.BR"]),
    ("current_account_usd", "current_account_usd", "sum_x1e6", ["wb/BN.CAB.XOKA.CD.BR"]),
    ("real_gdp_growth", "gdp_real_growth", "dec", ["wb/NY.GDP.MKTP.KD.ZG.BR"]),
    ("exports_goods_usd", "bop_goods_exports", "sum_x1e6", ["wb/BX.GSR.MRCH.CD.BR", "wb/TX.VAL.MRCH.CD.WT.BR"]),
    ("imports_goods_usd", "bop_goods_imports", "sum_x1e6", ["wb/BM.GSR.MRCH.CD.BR", "wb/TM.VAL.MRCH.CD.WT.BR"]),
    ("labor_participation", "labor_participation_rate", "dec", ["wb/SL.TLF.CACT.ZS.BR"]),
]


FOLD = [  # (keywords, topic) — first match wins; matched against "subtopic | database | title"
    (("findex", "financial inclusion", "consumer protection", "account ownership"), "Financial inclusion"),
    (("external debt", "international debt", "qeds", "debt service", "net flows", "amortization", "disbursement"), "External debt"),
    (("public sector debt", "qpsd", "fiscal", "expenditures", "revenue", "government finance", "bureaucracy", "tax"), "Public finances"),
    (("health", "mortality", "nutrition", "disease", "hiv", "immuniz", "life expectancy"), "Health"),
    (("education", "attainment", "learning", "school", "primary", "secondary", "tertiary", "literacy", "edstats"), "Education"),
    (("social protection", "aspire", "safety net", "pension", "atlas of social"), "Social protection"),
    (("disability",), "Disability"),
    (("gender", "women", "female"), "Gender"),
    (("poverty", "inequality", "gini", "quintile", "equity lab", "prosperity", "income share"), "Poverty & inequality"),
    (("unemployment", "employment", "labour", "labor", "earnings", "wage", "hours of work", "informal", "child labour", "jobs"), "Labour"),
    (("population", "demograph", "fertility", "migration", "age dependency"), "Population"),
    (("emission", "mitigation", "climate", "environment", "co2", "forest", "water", "pollution", "wealth accounts"), "Environment"),
    (("energy", "electric", "renewable", "fuel"), "Energy"),
    (("agricultur", "land", "crop", "food", "livestock"), "Agriculture & land"),
    (("export", "import", "trade", "tariff", "exporter dynamics"), "Trade"),
    (("inflation", "price", "cpi", "deflator", "exchange rate", "ppp"), "Prices"),
    (("interest", "monetary", "credit", "bank", "financial sector", "stock market", "markets"), "Money & rates"),
    (("business", "enterprise", "firm", "doing business", "regulat", "private sector"), "Business environment"),
    (("governance", "corruption", "rule of law", "statistical performance", "statistical capacity", "worldwide"), "Governance"),
    (("infrastructure", "transport", "internet", "telecom", "ict"), "Infrastructure"),
    (("science", "research", "patent", "r&d", "technology"), "Science & technology"),
    (("gdp", "national accounts", "gross", "output", "growth", "consumption", "investment", "economic monitor"), "Output & activity"),
]


def fold_topic(text: str) -> str | None:
    t = text.lower()
    for keys, topic in FOLD:
        if any(k in t for k in keys):
            return topic
    return None


def topic_for(code: str, rules) -> str:
    for p, t in rules:
        if code.startswith(p):
            return t
    return "Other"


def _freshness(freq, last, as_of):
    if pd.isna(last):
        return "no data"
    return "stale" if (as_of - pd.Timestamp(last)).days > STALE_DAYS.get(freq, 1300) else "fresh"


def native_part(silver: pd.DataFrame, as_of) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = silver[~silver.metric_id.isin(["ibov_weight"])].copy()
    s["series_id"] = np.where(s.entity_id == "BR", s.metric_id, s.metric_id + "@" + s.entity_id)
    # the 22 Dateno/WB series that pipeline.py already carries: keep them under their wb/ id
    is_wb = s.resolved_source.astype(str).str.startswith("dateno:wb/")
    s.loc[is_wb, "series_id"] = "wb/" + s.loc[is_wb, "resolved_source"].str.split("wb/").str[1]
    obs = s[["series_id", "date", "value"]].copy()
    g = s.sort_values("date").groupby("series_id")
    cat = g.agg(title=("metric_name", "first"), metric_id=("metric_id", "first"),
                entity_id=("entity_id", "first"), theme=("theme", "first"), source_id=("source_id", "first"),
                resolved_source=("resolved_source", "first"), freq=("freq", "first"), unit=("unit", "first"),
                first=("date", "first"), last=("date", "last"), n_obs=("value", "size"),
                last_value=("value", "last")).reset_index()
    cat["ns"] = np.where(cat.series_id.str.startswith("wb/"), "wb", "native")
    cat["topic"] = cat.theme.map(TOPIC_OF_THEME).fillna("Other")
    cat.loc[cat.ns == "wb", "topic"] = cat.loc[cat.ns == "wb", "series_id"].str[3:].map(
        lambda c: topic_for(c, WDI_PREFIX))
    cat["source"] = cat.source_id.map(SOURCE_NAME).fillna(cat.source_id)
    cat.loc[cat.ns == "wb", "source"] = "World Bank (Dateno)"
    cat["role"] = np.where(cat.source_id == "derived", "derived", "canonical")
    cat["description"] = ""
    return cat, obs


def dateno_part(as_of) -> tuple[pd.DataFrame, pd.DataFrame]:
    EXPORT.mkdir(parents=True, exist_ok=True)
    cp, op = DATENO / "catalog.parquet", DATENO / "observations.parquet"
    if not (cp.exists() and op.exists()):
        return pd.DataFrame(), pd.DataFrame(columns=["series_id", "date", "value"])
    c = pd.read_parquet(cp)
    # only the columns the merge needs; string columns as categoricals keep 4.6M rows small
    o = pd.read_parquet(op, columns=["ns", "ts_id", "date", "value", "classif1", "classif2"])
    for col in ("ns", "ts_id", "classif1", "classif2"):
        o[col] = o[col].astype("category")
    c["series_id"] = c["ns"] + "/" + c["ts_id"]
    o["series_id"] = (o["ns"].astype(str) + "/" + o["ts_id"].astype(str)).astype("category")
    o["date"] = pd.to_datetime(o["date"]).dt.strftime("%Y-%m-%d")
    o = o[o.value.notna()]
    # ILO series carry disaggregations (sex, age, ...): the merged table keeps the headline
    # (all-totals) row per date; every breakdown goes to observations_dims.
    import sys
    sys.path.insert(0, str(ROOT / "ingest"))
    from _dateno_mirror import headline_mask  # noqa: E402
    dims = o[["series_id", "date", "classif1", "classif2", "value"]]
    dims = dims[dims.classif1.notna() | dims.classif2.notna()]
    dims.to_parquet(EXPORT / "observations_dims.parquet", index=False, compression="zstd")
    o = o[headline_mask(o).to_numpy()].drop_duplicates(["series_id", "date"])[["series_id", "date", "value"]]
    # annual values for the current (incomplete) or future years are partial sums or projections
    o = o[~(o.date >= f"{as_of.year}-01-01")]
    agg = o.sort_values("date").groupby("series_id").agg(
        first=("date", "first"), last=("date", "last"), n_obs=("value", "size"), last_value=("value", "last"))
    cols = {k: k for k in c.columns}
    cat = pd.DataFrame({
        "series_id": c.series_id, "title": c.get("name", c.ts_id).astype(str).str.replace(r"\s+-\s+Brazil$", "", regex=True),
        "metric_id": c.indicator_id, "entity_id": "BR", "theme": "", "source_id": "dateno_" + c.ns,
        "resolved_source": "dateno:" + c.series_id,
        "freq": (c["freq"].map({"A": "annual", "Q": "quarterly", "M": "monthly", "D": "daily"}).fillna(c["freq"])
                 if "freq" in cols else "annual"),
        "unit": c["unit"] if "unit" in cols else "",
        "ns": c.ns, "description": c[[x for x in ("definition", "description") if x in cols][0]]
        if any(x in cols for x in ("definition", "description")) else "",
        "source": np.where(c.ns == "wb", "World Bank (Dateno)", "ILO (Dateno)"),
        "database": c[[x for x in ("database", "source_name", "source") if x in cols][0]]
        if any(x in cols for x in ("database", "source_name", "source")) else "",
    }).set_index("series_id").join(agg).reset_index()
    cat = cat[cat.n_obs.fillna(0) > 0]
    cat["topic"] = [topic_for(m, WDI_PREFIX if ns == "wb" else ILO_PREFIX) for m, ns in zip(cat.metric_id, cat.ns)]
    # Publisher topic labels are fine-grained (230+); fold them into the platform's topic
    # vocabulary by keyword, with the database name as a fallback. The original label is
    # kept as `subtopic`.
    sub = c.set_index(c.ns + "/" + c.ts_id)["topic"] if "topic" in cols else pd.Series(dtype=str)
    db = cat.set_index("series_id")["database"].astype(str)
    cat["subtopic"] = cat.series_id.map(sub).fillna("")
    # most specific first: the part of the publisher label after the last ':' (WDI labels
    # read "Social Protection & Labor: Unemployment"), then the title, then the full label
    folded = [fold_topic(str(cat.subtopic.iat[i]).split(":")[-1]) or fold_topic(str(cat.title.iat[i]))
              or fold_topic(f"{cat.subtopic.iat[i]} | {db.iat[i]}") for i in range(len(cat))]
    cat["topic"] = [f or t for f, t in zip(folded, cat.topic)]
    cat["role"] = "canonical"
    return cat, o


def to_annual(s: pd.Series, rule: str) -> pd.Series:
    y = s.groupby(s.index.year)
    out = {"dec": y.last(), "mean": y.mean(), "sum": y.sum()}[rule.split("_")[0]]
    if "x1e6" in rule:
        out = out * 1e6
    if rule.startswith("sum"):  # drop incomplete years
        out = out[y.size() >= 12]
    return out


def reconcile(cat, obs) -> pd.DataFrame:
    rows = []
    have = set(cat.series_id)
    for concept, nat, rule, alts in CONCEPTS:
        if nat not in have:
            continue
        ns = obs[obs.series_id == nat].assign(dt=lambda d: pd.to_datetime(d.date)).set_index("dt").value
        a_nat = to_annual(ns, rule) if cat.loc[cat.series_id == nat, "freq"].iloc[0] != "annual" else \
            ns.groupby(ns.index.year).last()
        for alt in alts:
            if alt not in have:
                continue
            w = obs[obs.series_id == alt].assign(y=lambda d: pd.to_datetime(d.date).dt.year).set_index("y").value
            j = pd.concat([a_nat.rename("n"), w.rename("w")], axis=1).dropna()
            if len(j) < 3:
                continue
            rel = (j.n - j.w).abs() / j.w.abs().replace(0, np.nan)
            rows.append(dict(concept=concept, canonical=nat, alternate=alt, overlap_years=len(j),
                             first_year=int(j.index.min()), last_year=int(j.index.max()),
                             mean_abs_diff=float((j.n - j.w).abs().mean()),
                             median_rel_diff_pct=float(rel.median() * 100) if rel.notna().any() else None,
                             correlation=float(j.n.corr(j.w)) if len(j) > 3 else None,
                             annualization=rule))
    rec = pd.DataFrame(rows)
    if not rec.empty:  # mark Dateno twins as alternates of the native canonical series
        cat.loc[cat.series_id.isin(rec.alternate), "role"] = "alternate"
        cat["concept"] = cat.series_id.map(
            {**dict(zip(rec.alternate, rec.concept)), **dict(zip(rec.canonical, rec.concept))})
    else:
        cat["concept"] = None
    return rec


# Dataset = the named product a series belongs to (publisher database for World Bank /
# ILO; the publisher's system for native series). Shown next to every series.
NATIVE_DATASET = {
    "Banco Central (SGS)": "Banco Central — SGS time series", "Banco Central (Focus)": "Banco Central — Focus survey",
    "Banco Central (Pix)": "Banco Central — Pix statistics", "IBGE (SIDRA)": "IBGE — SIDRA (PNAD, PMC, PNS)",
    "ComexStat (MDIC)": "ComexStat — foreign trade", "IPEAData": "IPEAData", "ANP": "ANP — oil & gas production",
    "ONS": "ONS — power system operator", "Tesouro Direto": "Tesouro Direto — bond prices",
    "B3": "B3 — prices, dividends, Ibovespa", "CVM": "CVM — company filings (ITR/DFP)",
    "DATASUS (SIM)": "DATASUS — mortality register (SIM)", "WHO Mortality Database": "WHO Mortality Database",
    "Derived": "Brazil Monitoring — derived",
}


# How a series rolls up to a year (v_annual): flows are summed, stocks / running totals take the
# last value, everything else (rates, prices, indices, averages) is averaged.
FLOW_NATIVE = re.compile(r"^(exports_.*|imports_.*|.*_exports(_kg)?|.*_imports|beef_exports_to_china|trade_balance|"
                         r"current_account_usd|bop_goods_.*|caged_net_hires|deaths_.*|homicide_deaths|suicide_deaths|"
                         r"traffic_deaths|infant_deaths|vehicle_.*|pix_transactions_.*|revenue_.*|ebit_brl|net_income_.*|"
                         r"capex_brl|dividends_paid_brl|dividend_per_share_brl|generation_gwh)$")
STOCK_NATIVE = re.compile(r"(balance$|_gdp$|_debt_brl|net_debt|gross_public_debt|net_public_debt|cash_brl|fx_reserves|"
                          r"_12m_brl$|share_close|total_return|ibovespa_level|^population$)")


def agg_rule(row) -> str:
    sid = str(row.series_id).split("@")[0]
    if row.freq == "annual":
        return "mean"
    if row.ns == "native":
        if FLOW_NATIVE.match(sid):
            return "sum"
        return "last" if STOCK_NATIVE.search(sid) else "mean"
    if re.match(r"wb/DP\.DOD\.", sid):            # quarterly public sector debt outstanding (PSD titles)
        return "last"
    if re.match(r"wb/NYGDPMKTP(SA|NS)?(CD|CN|KD|KN)_Q\.", sid):   # quarterly GDP, not annualised
        return "sum"
    t = (str(row.title) + " " + str(row.unit or "")).lower()   # GEM keeps "Price" in the unit
    if re.search(r"\b(exports?|imports?)\b", t) and not re.search(r"price|index|share|%|unit value|cover|months", t):
        return "sum"
    if re.search(r"reserves|stock|outstanding|debt", t):
        return "last"
    return "mean"


def add_dataset_and_rank(cat: pd.DataFrame) -> pd.DataFrame:
    """dataset name + an importance rank used to order search results and lists:
    official native series first, then World Development Indicators / ILO headline, then
    other World Bank databases; longer, fresher series rank higher; sparse survey
    breakdowns (a handful of observations) sink."""
    db = cat["database"].astype("string").fillna("") if "database" in cat else pd.Series("", index=cat.index)
    cat["dataset"] = np.where(db.str.len() > 0, db, cat.source.map(NATIVE_DATASET).fillna(cat.source))
    base = np.select(
        [(cat.ns == "native") & (cat.role == "canonical"), cat.ns == "native",
         cat.dataset.eq("World Development Indicators"), cat.ns == "ilostat"],
        [4.0, 3.0, 2.5, 1.8], default=1.0)
    years = (pd.to_datetime(cat["last"], errors="coerce") - pd.to_datetime(cat["first"], errors="coerce")).dt.days / 365.25
    depth = np.log1p(cat.n_obs.fillna(0).astype(float)) + np.log1p(years.fillna(0).clip(lower=0))
    fresh = np.where(cat.status == "fresh", 1.0, 0.75)
    alt = np.where(cat.role == "alternate", 0.8, 1.0)
    cat["rank"] = (base * depth * fresh * alt).round(3)
    return cat



# ---- duplicate removal -----------------------------------------------------------------
# The same statistic often reaches the warehouse twice: a World Bank (GEM, WDI) or ILO copy
# of an official Brazilian series, or the same indicator in two World Bank databases. Twins
# are detected on VALUES, not titles, and only one copy is kept:
#   official Brazilian (native) > World Development Indicators > ILO > other World Bank.
DUP_RULES = {  # basis: (min overlapping points, min correlation, max |ratio-1| after 10^k scaling)
    "annual": (8, 0.97, 0.05), "quarterly": (12, 0.97, 0.05), "monthly": (24, 0.97, 0.05),
    "intl_annual": (10, 0.995, 0.01),
}


FLOW_UNITS = {"usd_fob", "usd_mn", "usd", "brl_mn", "brl_bn", "deaths", "units", "jobs", "million_tx",
              "thousand_tonnes", "gwh", "persons"}
QUALIFIERS = {"female", "male", "women", "men", "youth", "rural", "urban", "basic", "advanced", "intermediate",
              "aged", "financial", "east", "asia", "pacific", "europe", "america", "china", "neet", "poorest",
              "richest", "quintile", "constant", "underemployment", "combined", "services"}
_STOP = {"total", "rate", "annual", "current", "brazil", "the", "and", "for", "with", "from",
         "monthly", "quarterly", "index", "percent", "value", "data", "share", "per", "years", "year", "all",
         "estimate", "modeled", "national", "series", "level", "balance", "amount", "number", "average"}
_SYN = {"imports": "import", "exports": "export", "unemployment": "unemploy", "unemployed": "unemploy",
        "inflation": "price", "prices": "price", "cpi": "price", "ipca": "price", "consumer": "price",
        "reserves": "reserve", "renewables": "renewable", "homicides": "homicide", "goods": "goods",
        "electricity": "electric", "electric": "electric", "deaths": "death", "gdp": "gdp", "bop": "bop"}


def _tokens(t: str) -> set:
    import re as _re
    w = _re.findall(r"[a-z]{3,}", t.lower())
    return {_SYN.get(x, x) for x in w if x not in _STOP}


def _priority(cat: pd.DataFrame) -> pd.Series:
    db = cat["database"].astype("string").fillna("") if "database" in cat else ""
    return pd.Series(np.select([cat.ns == "native", db == "World Development Indicators", cat.ns == "ilostat"],
                               [0, 1, 2], default=3), index=cat.index)


def _matrix(obs, ids, rule, how="mean"):
    """date-bucketed matrix (bucket x series) for the given ids."""
    o = obs[obs.series_id.isin(ids)]
    if o.empty:
        return pd.DataFrame()
    dt = pd.to_datetime(o.date)
    key = {"annual": dt.dt.year, "quarterly": dt.dt.to_period("Q").astype(str), "monthly": dt.dt.to_period("M").astype(str)}[rule]
    g = o.assign(k=key.to_numpy()).groupby(["k", "series_id"], observed=True).value
    return (g.mean() if how == "mean" else g.sum()).unstack()


def _match(A: pd.DataFrame, B: pd.DataFrame, n_min, r_min, tol, scale=True):
    """Pairs (a, b, n, corr, ratio) where column a of A and column b of B agree."""
    if A.empty or B.empty:
        return []
    idx = A.index.union(B.index)
    A, B = A.reindex(idx), B.reindex(idx)
    Bv = B.to_numpy(dtype=float)
    out = []
    for a in A.columns:
        x = A[a].to_numpy(dtype=float)
        m = ~np.isnan(Bv) & ~np.isnan(x)[:, None]
        n = m.sum(0)
        ok = n >= n_min
        if not ok.any():
            continue
        X = np.where(m, x[:, None], np.nan); Y = np.where(m, Bv, np.nan)
        with np.errstate(all="ignore"):
            xm, ym = np.nanmean(X, 0), np.nanmean(Y, 0)
            cov = np.nanmean((X - xm) * (Y - ym), 0)
            corr = cov / (np.nanstd(X, 0) * np.nanstd(Y, 0))
            ratio = np.nanmedian(Y / X, 0)
            # changes must agree too: kills coincidental co-trending series
            dX, dY = np.diff(X, axis=0), np.diff(Y, axis=0)
            dxm, dym = np.nanmean(dX, 0), np.nanmean(dY, 0)
            dcorr = np.nanmean((dX - dxm) * (dY - dym), 0) / (np.nanstd(dX, 0) * np.nanstd(dY, 0))
        k = np.where(scale & np.isfinite(ratio) & (ratio > 0), np.round(np.log10(np.abs(ratio))), 0)
        near = np.abs(ratio / 10.0 ** k - 1) <= tol
        hit = ok & (corr >= r_min) & near & (dcorr >= min(0.9, r_min))
        for j in np.flatnonzero(hit):
            out.append((a, B.columns[j], int(n[j]), float(corr[j]), float(ratio[j])))
    return out


PROTECT: set = set()


def remove_duplicates(cat: pd.DataFrame, obs: pd.DataFrame):
    """Return (cat, obs, removed, pairs). Never removes a native series."""
    pri = _priority(cat).set_axis(cat.series_id)
    nat = cat[(cat.ns == "native") & (cat.entity_id == "BR")].series_id
    intl = cat[cat.ns != "native"]
    pairs = []
    for rule in ("annual", "quarterly", "monthly"):
        tgt = intl[intl.freq == rule].series_id
        if tgt.empty:
            continue
        B = _matrix(obs, set(tgt), rule)
        n_min, r_min, tol = DUP_RULES[rule]
        unit = cat.set_index("series_id").unit.astype(str)
        flows = {x for x in nat if unit.get(x, "") in FLOW_UNITS}
        for how in (("mean", "sum") if rule != "monthly" else ("mean",)):
            # flows (US$, R$, counts) aggregate by sum; rates, levels and indices by mean
            ids = flows if how == "sum" else set(nat) - (flows if rule != "monthly" else set())
            A = _matrix(obs, ids, rule, how)
            pairs += [(b, a, n, c, r, f"{rule} {how}") for a, b, n, c, r in _match(A, B, n_min, r_min, tol)]
    # international twins of World Development Indicators (same scale, stricter)
    wdi = intl[(intl.freq == "annual") & (pri.reindex(intl.series_id).to_numpy() == 1)].series_id
    rest = intl[(intl.freq == "annual") & (pri.reindex(intl.series_id).to_numpy() > 1)].series_id
    if len(wdi) and len(rest):
        n_min, r_min, tol = DUP_RULES["intl_annual"]
        pairs += [(b, a, n, c, r, "annual vs WDI") for a, b, n, c, r in
                  _match(_matrix(obs, set(wdi), "annual"), _matrix(obs, set(rest), "annual"), n_min, r_min, tol, scale=False)]
    # same title among international series: identical values = duplicate regardless of database
    norm = intl.assign(_t=intl.title.astype(str).str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip())
    for t, g in norm.groupby("_t"):
        if len(g) < 2:
            continue
        for rule in set(g.freq):
            ids = list(g[g.freq == rule].series_id)
            if len(ids) < 2 or rule not in ("annual", "quarterly", "monthly"):
                continue
            M = _matrix(obs, set(ids), rule)
            pairs += [(b, a, n, c, r, f"{rule} same title") for a, b, n, c, r in _match(M, M, 5, 0.8, 0.35, scale=False) if a != b]
    if not pairs:
        return cat, obs, pd.DataFrame(columns=["series_id", "kept", "basis"]), pd.DataFrame()
    P = pd.DataFrame(pairs, columns=["dup", "keep", "n", "corr", "ratio", "basis"])
    P = P[P.dup != P.keep]
    # titles must name the same thing: >= 2 meaningful shared words
    title = cat.set_index("series_id").title.astype(str)
    shared = [len(_tokens(title.get(a, "")) & _tokens(title.get(b, ""))) for a, b in zip(P.dup, P.keep)]
    # >= 2 shared words between international copies; >= 1 when the kept copy is a native
    # series (its short Brazilian title, e.g. "Unemployment rate (PNAD)", names the concept once)
    need = np.where(P.keep.map(pri).to_numpy() == 0, 1, 2)
    P = P[(np.array(shared) >= need) | P.basis.str.endswith("same title").to_numpy()]
    # a subgroup / different-concept word on one side only means it is not the same statistic
    qual = [bool((_tokens(title.get(a, "")) ^ _tokens(title.get(b, ""))) & QUALIFIERS) for a, b in zip(P.dup, P.keep)]
    P = P[~np.array(qual, dtype=bool)]
    # a percentage is never a scaled copy of a count: no 10^k allowance when the kept unit is a rate
    unit = cat.set_index("series_id").unit.astype(str)
    pct_keep = P.keep.map(unit).fillna("").str.startswith(("pct", "annual_pct"))
    P = P[~(pct_keep & (np.abs(np.log10(P.ratio.abs().clip(lower=1e-12))) > 0.03))]
    rk = cat.set_index("series_id")["rank"] if "rank" in cat else pd.Series(dtype=float)
    kp, dp_, kr, dr = P.keep.map(pri), P.dup.map(pri), P.keep.map(rk).fillna(0), P.dup.map(rk).fillna(0)
    better = (kp < dp_) | ((kp == dp_) & ((kr > dr) | ((kr == dr) & (P.keep < P.dup))))
    P = P[better]                      # keep the higher-priority (then higher-ranked) copy
    P = P.sort_values(["dup", "corr"], ascending=[True, False]).drop_duplicates("dup")
    # do not delete a series that is itself kept as the twin of another
    P = P[~P.dup.isin(set(P.keep))]
    P = P[~P.dup.isin(PROTECT)]   # merged ILO families carry breakdown tables: never drop them
    removed = P.rename(columns={"dup": "series_id", "keep": "kept"})
    cat = cat[~cat.series_id.isin(set(removed.series_id))]
    obs = obs[~obs.series_id.isin(set(removed.series_id))]
    return cat, obs, removed, P



# ---- ILO table families -----------------------------------------------------------------
# ILO publishes one statistic as several tables that differ only in breakdowns, e.g.
# EAR_EMTA_SEX_NB / _SEX_AGE_NB / _SEX_OCU_NB / _SEX_AGE_CUR_NB ("Average monthly earnings of
# employees by sex / by sex and age / ..."). They are merged into one series: the table with
# the fewest breakdowns represents the family (title without the "by ..." clause) and every
# member's breakdowns stay selectable on the site ("Breakdown table"). Tokens that are not
# breakdown dimensions (measure variants such as SKN/SKS, EC2) keep families apart.
ILO_DIMS = {"SEX", "AGE", "ECO", "OCU", "EDU", "GEO", "CUR", "STE", "IFL", "INS", "EST", "CBR", "MTS", "HHT",
            "DSB", "NOC", "LMS", "NAT", "MJH", "WKT", "IND", "HOW", "DUR", "CAT", "REL", "JOB", "TEN", "MIG", "HHS", "DIS"}


def _ilo_family(series_id: str):
    code = series_id.split("/", 1)[1].rsplit(".", 1)[0]
    suf = ""
    m = re.match(r"(.*?)(_[QM])$", code)
    if m:
        code, suf = m.groups()
    t = code.split("_")
    if len(t) < 3:
        return None, []
    mid, unit = t[2:-1], t[-1]
    dims = [x for x in mid if x in ILO_DIMS]
    other = [x for x in mid if x not in ILO_DIMS]
    return "_".join(t[:2] + other + [unit]) + suf, dims


def merge_ilo_families(cat: pd.DataFrame, obs: pd.DataFrame):
    """Return (cat, obs, members) with one representative per ILO table family."""
    ilo = cat[cat.ns == "ilostat"]
    fam = {}
    for sid in ilo.series_id:
        key, dims = _ilo_family(sid)
        if key:
            fam.setdefault(key, []).append((sid, dims))
    rows, drop = [], set()
    title = cat.set_index("series_id").title.astype(str)
    for key, mem in fam.items():
        if len(mem) < 2:
            continue
        mem.sort(key=lambda x: (len(x[1]), "CUR" in x[1], x[0]))
        rep = mem[0][0]
        for sid, dims in mem:
            t = title.get(sid, "")
            label = ("by " + t.split(" by ", 1)[1]) if " by " in t else t
            rows.append((rep, sid, label, len(dims)))
            if sid != rep:
                drop.add(sid)
        base = title.get(rep, "")
        unit = re.search(r"\(([^()]*)\)\s*$", base)
        cat.loc[cat.series_id == rep, "title"] = base.split(" by ")[0].strip() + (f" ({unit.group(1)})" if unit and " by " in base else "")
    members = pd.DataFrame(rows, columns=["series_id", "member_id", "breakdown", "n_dims"])
    reps = members.series_id.unique()
    ci = cat.set_index("series_id")
    rt = ci.title
    clash = ci.loc[ci.index.isin(reps), ["title", "freq"]]
    clash = clash[clash.duplicated(keep=False)]   # same title AND frequency
    for sid in clash.index:   # e.g. two "Employment (thousands)" families differing by measure variant
        cat.loc[cat.series_id == sid, "title"] = title.get(sid, rt[sid])
    cat = cat[~cat.series_id.isin(drop)]
    obs = obs[~obs.series_id.isin(drop)]
    return cat, obs, members


def build(as_of: str | None = None, used_in: dict | None = None):
    as_of = pd.Timestamp(as_of or pd.Timestamp.today().normalize())
    silver = pd.read_parquet(SILVER)
    nc, no = native_part(silver, as_of)
    dc, do = dateno_part(as_of)
    if not dc.empty:  # bulk Dateno copy supersedes the 22 legacy wb/ series from silver
        nc, no = nc[~nc.series_id.isin(dc.series_id)], no[~no.series_id.isin(dc.series_id)]
    cat = pd.concat([nc, dc], ignore_index=True)
    obs = pd.concat([no, do], ignore_index=True)
    obs = obs.drop_duplicates(["series_id", "date"], keep="last").sort_values(["series_id", "date"])
    cat["entity_name"] = cat.entity_id.map(ENTITY_NAME).fillna(cat.entity_id)
    # company series: lead the title with the company so search results are self-explanatory
    co = (cat.entity_id != "BR") & ~cat.apply(lambda r: str(r.title).startswith(str(r.entity_name).split(" (")[0]), axis=1)
    cat.loc[co, "title"] = cat.loc[co, "entity_name"].str.split(" \\(").str[0] + ": " + cat.loc[co, "title"]
    cat["status"] = [_freshness(f, l, as_of) for f, l in zip(cat.freq, cat["last"])]
    # DATASUS publishes with a long preliminary lag: incomplete recent months are dropped at
    # ingest, so judge freshness against ~6 months, not a month
    ds_m = cat.source.eq("DATASUS (SIM)")
    cat.loc[ds_m, "status"] = [("fresh" if (as_of - pd.Timestamp(l)).days <= 200 else "stale") for l in cat.loc[ds_m, "last"]]
    cat = cat[~cat.series_id.isin(["ibov_resource_energy_weight"])]   # one-point snapshot, not a series
    cat["used_in_tests"] = cat.series_id.map(used_in or {}).fillna("")
    rec = reconcile(cat, obs)
    cols = ["series_id", "title", "topic", "source", "ns", "entity_id", "entity_name", "metric_id",
            "freq", "unit", "first", "last", "n_obs", "last_value", "status", "role", "concept",
            "used_in_tests", "resolved_source", "description"] + [x for x in ("database", "subtopic") if x in cat]
    cat = add_dataset_and_rank(cat)
    # Curation: one-off survey items are not time series. Drop World Bank / ILO series with
    # fewer than MIN_OBS observations or questionnaire-coded titles; native series are never
    # dropped. Excluded rows are kept (with the reason) in excluded_series for transparency.
    coded = cat.title.astype(str).str.match(r"^\d{2,3}_|.*_#[A-Z]") | cat.title.astype(str).str.contains(
        JUNK_TITLE, case=False, regex=True)
    sparse = (cat.ns != "native") & (cat.n_obs.fillna(0) < MIN_OBS)
    drop = (cat.ns != "native") & (sparse | coded | cat.series_id.str.match(CCDR_WGI.pattern))
    excluded = cat[drop].assign(reason=np.where(coded[drop], "questionnaire item or statistical by-product (p-value, standard error, bound)", f"fewer than {MIN_OBS} observations"))
    excluded[["series_id", "title", "dataset", "n_obs", "reason"]].to_parquet(GOLD / "excluded_series.parquet", index=False)
    cat = cat[~drop]
    obs = obs[obs.series_id.isin(set(cat.series_id))]
    for k, v in TOPIC_OVERRIDE.items():
        cat.loc[cat.series_id == k, "topic"] = v
    cat.loc[cat.ns != "native", "unit"] = cat.loc[cat.ns != "native", "unit"].map(clean_unit)
    gem = cat.dataset.astype(str).eq("Global Economic Monitor") if "dataset" in cat else cat.title.str.contains(",,", na=False)
    gem = gem | cat.title.astype(str).str.contains(r"^[^(]*,[^ ]", regex=True) & (cat.ns == "wb")
    def gem_split(t):   # "GDP,current US$,millions,seas. adj.," -> ("GDP (seas. adj.)", "current US$, millions")
        parts = [x.strip() for x in str(t).split(",") if x.strip()]
        if len(parts) < 2:
            return str(t), None
        head, rest = parts[0], parts[1:]
        adj = [x for x in rest if "adj" in x.lower()]
        unit = ", ".join(x for x in rest if "adj" not in x.lower())
        return head + (f" ({adj[0]})" if adj else ""), unit or None
    if gem.any():
        tu = cat.loc[gem, "title"].map(gem_split)
        cat.loc[gem, "title"] = [a for a, _ in tu]
        cat.loc[gem & cat.unit.isna(), "unit"] = [u for (_, u), g in zip(tu, cat.loc[gem, "unit"].isna()) if g]
    blank = (cat.ns != "native") & cat.unit.isna()
    cat.loc[blank, "unit"] = cat.loc[blank, "title"].astype(str).str.findall(r"\(([^()]*)\)").map(
        lambda xs: next((u for u in (clean_unit(x) for x in reversed(xs)) if u), None))
    # Global Economic Monitor annual series duplicate their monthly versions and some aggregate
    # badly (e.g. months of import cover as reserves / annual imports): keep the monthly one
    ids = set(cat.series_id)
    gem_annual = [x for x in ids if x.startswith("wb/") and x.endswith(".BRA") and x[:-4] + "_M.BRA" in ids]
    cat, obs = cat[~cat.series_id.isin(gem_annual)], obs[~obs.series_id.isin(gem_annual)]
    excluded = pd.concat([excluded, pd.DataFrame({"series_id": gem_annual, "title": gem_annual, "dataset": "", "n_obs": None,
                          "reason": "annual copy of a monthly Global Economic Monitor series"})], ignore_index=True)
    cat["title"] = cat.title.astype(str).str.replace(r"^\d{2,3}\.\s?", "", regex=True)          # "044.Share of ..." -> "Share of ..."
    cat.loc[(cat.ns != "native") & cat.title.str.contains(r"\breserves\b", case=False), "topic"] = "External sector"
    cat.loc[cat.topic.eq("Other") & cat.title.str.contains("DAC|aid|ODA|grant", case=False, na=False), "topic"] = "External sector"
    nd = [k for k in NATIVE_DUPS if k in set(cat.series_id) and NATIVE_DUPS[k] in set(cat.series_id)]
    cat, obs = cat[~cat.series_id.isin(nd)], obs[~obs.series_id.isin(nd)]
    excluded = pd.concat([excluded, pd.DataFrame({"series_id": nd, "title": nd, "dataset": "", "n_obs": None,
                          "reason": ["duplicate of " + NATIVE_DUPS[k] + " (same Brazilian statistic, two publishers)" for k in nd]})],
                         ignore_index=True)
    # ILO table families -> one series per statistic, breakdown tables kept as members
    cat, obs, members = merge_ilo_families(cat, obs)
    PROTECT.clear(); PROTECT.update(members.series_id.unique())
    members.to_parquet(GOLD / "series_members.parquet", index=False)
    merged = members[members.series_id != members.member_id]
    excluded = pd.concat([excluded[["series_id", "title", "dataset", "n_obs", "reason"]],
                          pd.DataFrame({"series_id": merged.member_id, "title": merged.breakdown, "dataset": "",
                                        "n_obs": None, "reason": "merged into " + merged.series_id + " (breakdown table)"})],
                         ignore_index=True)
    excluded.to_parquet(GOLD / "excluded_series.parquet", index=False)
    print(f"ILO families merged: {merged.series_id.nunique()} series absorb {len(merged)} breakdown tables")
    # duplicates: keep one copy of each statistic (see remove_duplicates); log the rest
    cat, obs, removed, pairs = remove_duplicates(cat, obs)
    if len(removed):
        t = cat.set_index("series_id").title
        dup_rows = pd.DataFrame({"series_id": removed.series_id, "title": removed.series_id, "dataset": "",
                                 "n_obs": removed.n, "reason": "duplicate of " + removed.kept + " (" + removed.basis
                                 + ", ρ=" + removed["corr"].round(3).astype(str) + ")"})
        excluded = pd.concat([excluded[["series_id", "title", "dataset", "n_obs", "reason"]], dup_rows], ignore_index=True)
        excluded.to_parquet(GOLD / "excluded_series.parquet", index=False)
        dup_rec = pd.DataFrame({"concept": "duplicate:" + removed.kept, "canonical": removed.kept, "alternate": removed.series_id,
                                "overlap_years": removed.n, "first_year": None, "last_year": None, "mean_abs_diff": None,
                                "median_rel_diff_pct": ((removed.ratio / 10.0 ** np.round(np.log10(removed.ratio.abs().clip(lower=1e-12))) - 1).abs() * 100).round(2),
                                "correlation": removed["corr"],
                                "annualization": removed.basis})
        rec = pd.concat([rec, dup_rec], ignore_index=True)
        print(f"duplicates removed: {len(removed)}")
    cat["agg"] = [agg_rule(r) for r in cat.itertuples()]
    cols += ["dataset", "rank", "agg"]
    cat = cat[cols].sort_values(["topic", "rank"], ascending=[True, False]).reset_index(drop=True)
    # World Bank metadata carries U+FFFD where a typographic apostrophe was mangled upstream
    for c in ("title", "description", "unit", "database"):
        if c in cat:
            cat[c] = cat[c].astype("string").str.replace("\ufffd", "'", regex=False)
    GOLD.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    for name, df in (("catalog", cat), ("observations", obs), ("reconciliation", rec)):
        df.to_parquet(GOLD / f"{name}.parquet", index=False)
        df.to_parquet(EXPORT / f"{name}.parquet", index=False, compression="zstd")
    return cat, obs, rec


def used_in_from(hyp: pd.DataFrame) -> dict:
    """Map series_id -> 'H1, H5' from hypothesis_tests.inputs strings like 'revenue_usd_bn[PETR]'."""
    m: dict[str, list] = {}
    for r in hyp.itertuples():
        for tok in re.split(r",\s*(?![^\[]*\])", r.inputs or ""):
            tok = tok.strip()
            mm = re.match(r"([a-z0-9_]+)(?:\[([A-Z,]+)\])?", tok)
            if not mm:
                continue
            ids = [mm.group(1)] if not mm.group(2) else [f"{mm.group(1)}@{e}" for e in mm.group(2).split(",")]
            for i in ids:
                m.setdefault(i, []).append(r.hyp_id)
    return {k: ", ".join(sorted(set(v))) for k, v in m.items()}


if __name__ == "__main__":
    hyp_p = GOLD / "hypothesis_tests.parquet"
    used = used_in_from(pd.read_parquet(hyp_p)) if hyp_p.exists() else {}
    c, o, r = build(used_in=used)
    print(f"catalog: {len(c):,} series ({c.ns.value_counts().to_dict()}), observations: {len(o):,}")
    print(c.topic.value_counts().to_string())
    print(r.to_string() if not r.empty else "no reconciliation pairs yet")
