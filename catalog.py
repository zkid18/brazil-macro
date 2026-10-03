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
STALE_DAYS = {"daily": 10, "weekly": 21, "monthly": 100, "quarterly": 200, "annual": 1300, "event": 4000}

# Concepts measured by both a native source and Dateno (World Bank / ILO). Native first.
# (concept, native series_id, native->annual rule, Dateno ts_id candidates)
CONCEPTS = [
    ("inflation_annual", "ipca_12m", "dec", ["wb/FP.CPI.TOTL.ZG.BR"]),
    ("unemployment_rate", "unemployment_rate", "mean", ["wb/SL.UEM.TOTL.ZS.BR", "wb/SL.UEM.TOTL.NE.ZS.BR"]),
    ("fx_reserves_usd", "fx_reserves", "dec_x1e6", ["wb/FI.RES.TOTL.CD.BR", "wb/FI.RES.XGLD.CD.BR"]),
    ("gross_public_debt_gdp", "gross_public_debt_gdp", "dec", ["wb/GC.DOD.TOTL.GD.ZS.BR"]),
    ("brl_per_usd", "brl_usd", "mean", ["wb/PA.NUS.FCRF.BR"]),
    ("current_account_usd", "current_account_usd", "sum_x1e6", ["wb/BN.CAB.XOKA.CD.BR"]),
    ("real_gdp_growth", "gdp_real_growth", "dec", ["wb/NY.GDP.MKTP.KD.ZG.BR"]),
    ("exports_goods_usd", "bop_goods_exports", "sum_x1e6", ["wb/BX.GSR.MRCH.CD.BR", "wb/TX.VAL.MRCH.CD.WT.BR"]),
    ("imports_goods_usd", "bop_goods_imports", "sum_x1e6", ["wb/BM.GSR.MRCH.CD.BR", "wb/TM.VAL.MRCH.CD.WT.BR"]),
    ("lending_rate_vs_selic", "selic_target", "mean", ["wb/FR.INR.LEND.BR"]),
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
    folded = [fold_topic(f"{cat.subtopic.iat[i]} | {db.iat[i]} | {cat.title.iat[i]}") for i in range(len(cat))]
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
    cat["used_in_tests"] = cat.series_id.map(used_in or {}).fillna("")
    rec = reconcile(cat, obs)
    cols = ["series_id", "title", "topic", "source", "ns", "entity_id", "entity_name", "metric_id",
            "freq", "unit", "first", "last", "n_obs", "last_value", "status", "role", "concept",
            "used_in_tests", "resolved_source", "description"] + [x for x in ("database", "subtopic") if x in cat]
    cat = cat[cols].sort_values(["topic", "title"]).reset_index(drop=True)
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
