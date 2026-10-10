"""Brazil political lean vs economic, social and market outcomes, 1985-2026.
Executes the pre-registered plan in plan.md. numpy/pandas/duckdb/plotly only. seed = 0.
Run: /Users/zkid18/proj-personal/brazil-macro/.venv/bin/python politics_lean_study.py
"""
import itertools, json, math, os, sys, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, duckdb

OUT = Path(__file__).resolve().parent
assert (OUT / "preregistration.md").exists(), "preregistration.md must exist before any analysis"
DB = "/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb"
con = duckdb.connect(DB, read_only=True)
SEED, NBOOT = 0, 5000
SQL = {}          # name -> SQL text (shown in report)
META = {}         # series_id -> {source, freq, first, last, title}


def q(name, sql, params=None):
    SQL[name] = sql.strip()
    return con.execute(sql, params).df() if params is not None else con.execute(sql).df()


# ----------------------------------------------------------------------------- terms
SHORT = {"José Sarney": "Sarney", "Fernando Collor": "Collor", "Itamar Franco": "Itamar",
         "Fernando Henrique Cardoso": "FHC", "Dilma Rousseff": "Dilma", "Michel Temer": "Temer",
         "Jair Bolsonaro": "Bolsonaro"}

TERM_SQL = """
SELECT row_number() OVER (ORDER BY start) AS term_id,
       president || ' ' || strftime(start, '%Y') AS term_label,
       start, "end", president, party, lean,
       CASE lean WHEN 'left' THEN 'left' WHEN 'centre' THEN 'centre' ELSE 'right' END AS lean3
FROM political_terms ORDER BY start"""


def terms():
    t = q("terms", TERM_SQL)
    t["start"] = pd.to_datetime(t["start"]); t["end"] = pd.to_datetime(t["end"])
    def short(r):
        if r.president.startswith("Luiz"):
            return "Lula I–II" if r.start.year == 2003 else "Lula III"
        return SHORT[r.president]
    t["short"] = t.apply(short, axis=1)
    return t


T = terms()
TID = dict(zip(T.short, T.term_id))
# lean codings (plan 3.4). value: 'left' | 'right' | 'centre' | None(dropped)
CODINGS = {
    "A": {"Sarney": "centre", "Collor": "right", "Itamar": "centre", "FHC": "right", "Lula I–II": "left",
          "Dilma": "left", "Temer": "right", "Bolsonaro": "right", "Lula III": "left"},
}
CODINGS["B"] = {**CODINGS["A"], "FHC": "centre", "Temer": "centre"}
CODINGS["C"] = {**CODINGS["A"], "Temer": "centre", "FHC": "right"}
CODINGS["D"] = {**CODINGS["A"], "Collor": None, "Itamar": None, "Temer": None, "Lula III": None}
CODINGS["E"] = dict(CODINGS["A"])  # + drop Dilma II years 2015-2016 (applied at panel level)

# 4-year mandates (unit 2)
MANDATES = [("Sarney", "1985-03-15", "1990-03-15", "Sarney"), ("Collor", "1990-03-15", "1992-12-29", "Collor"),
            ("Itamar", "1992-12-29", "1995-01-01", "Itamar"), ("FHC I", "1995-01-01", "1999-01-01", "FHC"),
            ("FHC II", "1999-01-01", "2003-01-01", "FHC"), ("Lula I", "2003-01-01", "2007-01-01", "Lula I–II"),
            ("Lula II", "2007-01-01", "2011-01-01", "Lula I–II"), ("Dilma I", "2011-01-01", "2015-01-01", "Dilma"),
            ("Dilma II", "2015-01-01", "2016-05-12", "Dilma"), ("Temer", "2016-05-12", "2019-01-01", "Temer"),
            ("Bolsonaro", "2019-01-01", "2023-01-01", "Bolsonaro"), ("Lula III", "2023-01-01", "2027-01-01", "Lula III")]
M = pd.DataFrame(MANDATES, columns=["mandate", "start", "end", "term"])
M["start"] = pd.to_datetime(M.start); M["end"] = pd.to_datetime(M.end)

YEARS = np.arange(1985, 2027)


def in_office(d, table, col):
    r = table[(table.start <= d) & (table["end"] > d)]
    return r[col].iloc[0] if len(r) else None


ATTR = pd.DataFrame({"year": YEARS})
ATTR["term_c"] = [in_office(pd.Timestamp(y, 7, 1), T, "short") for y in YEARS]
ATTR["term_lag1"] = [in_office(pd.Timestamp(y - 1, 7, 1), T, "short") for y in YEARS]
ATTR["mand_c"] = [in_office(pd.Timestamp(y, 7, 1), M, "mandate") for y in YEARS]
ATTR["mand_lag1"] = [in_office(pd.Timestamp(y - 1, 7, 1), M, "mandate") for y in YEARS]
first_t = ATTR.groupby("term_c").year.min(); first_m = ATTR.groupby("mand_c").year.min()
ATTR["first_t"] = ATTR.apply(lambda r: r.year == first_t[r.term_c], axis=1)
ATTR["first_m"] = ATTR.apply(lambda r: r.year == first_m[r.mand_c], axis=1)
ATTR = ATTR.set_index("year")
M2T = dict(zip(M.mandate, M.term))

# ----------------------------------------------------------------------------- data access
ANNUAL_SQL = """
SELECT series_id, CAST(EXTRACT(year FROM date) AS INT) AS year,
       CASE WHEN any_value(c.agg) = 'sum' THEN sum(value)
            WHEN any_value(c.agg) = 'last' THEN arg_max(value, date)
            ELSE avg(value) END AS value,
       count(*) AS n_obs, max(date) AS last_obs
FROM v_observations o JOIN catalog c USING (series_id)
WHERE date <= current_date AND series_id IN (SELECT unnest($ids))
GROUP BY 1, 2 ORDER BY 1, 2"""
YEAR_END_SQL = """
SELECT series_id, CAST(EXTRACT(year FROM date) AS INT) AS year, arg_max(value, date) AS year_end, max(date) AS d
FROM v_observations
WHERE date <= current_date AND series_id IN ('ibovespa_usd','brl_usd','wb/DSTKMKTXD_M.BRA','wb/DPANUSSPB_M.BRA',
      'wb/REER_M.BRA','fx_reserves','embi_brazil','gov_real_yield_10y','ibc_br')
GROUP BY 1, 2 ORDER BY 1, 2"""
META_SQL = """
SELECT o.series_id, any_value(o.title) AS title, any_value(o.source) AS source, any_value(o.freq) AS freq,
       any_value(o.role) AS role, min(o.date) AS first_date, max(o.date) AS last_date, count(*) AS n
FROM v_observations o WHERE o.date <= current_date AND o.series_id IN (SELECT unnest($ids)) GROUP BY 1"""

ALL_IDS = """wb/NY.GDP.MKTP.KD.ZG.BR wb/NYGDPMKTPSAKD_Q.BRA ibc_br wb/NY.GDP.PCAP.KD.ZG.BR wb/NE.GDI.FTOT.ZS.BR
wb/IPTOTSAKD_M.BRA ilostat/SDG_0821_NOC_RT.BRA wb/NY.GDP.DEFL.KD.ZG.BR ipca_12m real_policy_rate selic_target
focus_ipca_12m wb/FR.INR.RINR.BR credit_gdp wb/FS.AST.PRVT.GD.ZS.BR primary_balance_gdp gross_public_debt_gdp
net_public_debt_gdp interest_bill_gdp wb/NE.CON.GOVT.ZS.BR wb/GC.TAX.TOTL.GD.ZS.BR wb/DSTKMKTXD_M.BRA ibovespa_usd
ibovespa_level brl_usd wb/DPANUSSPB_M.BRA wb/REER_M.BRA wb/PX.REX.REER.BR embi_brazil gov_real_yield_10y
gov_nominal_yield_5y wb/BN.CAB.XOKA.GD.ZS.BR wb/BX.KLT.DINV.WD.GD.ZS.BR wb/FI.RES.TOTL.MO.BR fx_reserves
wb/NE.EXP.GNFS.ZS.BR wb/CM.MKT.LCAP.GD.ZS.BR wb/SL.UEM.TOTL.ZS.BR unemployment_rate wb/JI.EMP.IFRM.ZS.BRA
ilostat/SDG_0831_SEX_ECO_RT.BRA ilostat/EAR_INEE_NOC_NB.BRA wb/FP.CPI.TOTL.BR real_average_income wb/SI.POV.GINI.BR
wb/SI.POV.DDAY.BR wb/SI.POV.UMIC.BR wb/SI.DST.FRST.20.BR wb/SI.DST.10TH.10.BR ilostat/LAP_2GDP_NOC_RT.BRA
ilostat/EAR_EMTG_SEX_NB.BRA wb/SP.DYN.IMRT.IN.BR wb/SP.DYN.LE00.IN.BR wb/SH.XPD.GHED.GD.ZS.BR wb/SE.XPD.TOTL.GD.ZS.BR
homicide_rate homicide_deaths population wb/per_sa_allsa.cov_pop_tot.BR wb/GOV_WGI_CC_EST.BR wb/GOV_WGI_GE_EST.BR
wb/GOV_WGI_RL_EST.BR wb/GOV_WGI_RQ_EST.BR wb/GOV_WGI_VA_EST.BR wb/GOV_WGI_PV_EST.BR wb/AG.LND.PFLS.HA.BR
wb/EN.GHG.CO2.LU.MT.CE.AR5.BR wb/EN.GHG.CO2.PC.CE.AR5.BR wb/TOT.BRA wb/TT.PRI.MRCH.XD.WD.BR wb/TX.UVI.MRCH.XD.WD.BR
wb/TM.UVI.MRCH.XD.WD.BR brent_usd wb/DXGSRMRCHNSXD_M.BRA focus_selic_12m focus_gdp_growth focus_fx
implicit_interest_rate nominal_gdp_growth r_minus_g nominal_deficit_gdp oil_exports presalt_share exports_to_us
exports_to_china""".split()


def annual_panel():
    a = q("annual_panel", ANNUAL_SQL.replace("$ids", "$1"), [ALL_IDS])
    return a


def year_end_panel():
    return q("year_end_panel", YEAR_END_SQL)


meta_df = q("meta", META_SQL.replace("$ids", "$1"), [ALL_IDS])
for r in meta_df.itertuples():
    META[r.series_id] = dict(title=r.title, source=r.source, freq=r.freq, role=r.role,
                             first_date=str(r.first_date)[:10], last_date=str(r.last_date)[:10], n=int(r.n))
AP = annual_panel()
YE = year_end_panel()


def A(sid, y0=1984, complete_only=True):
    """annual series; drop partial years for daily/monthly except 2026 (kept, flagged)."""
    d = AP[AP.series_id == sid].set_index("year")
    f = META[sid]["freq"]
    if complete_only and f in ("monthly", "daily"):
        need = 12 if f == "monthly" else 200
        keep = (d.n_obs >= need) | (d.index == 2026)
        d = d[keep]
    s = d.value
    return s[s.index >= y0]


def YEs(sid):
    return YE[YE.series_id == sid].set_index("year").year_end


def interp(s):
    s = s.sort_index()
    full = s.reindex(range(int(s.index.min()), int(s.index.max()) + 1))
    return full.interpolate(limit_area="inside")


def dlog(s):
    return 100 * np.log(s).diff()


# ----------------------------------------------------------------------------- ToT control
def tot_series():
    tt = A("wb/TT.PRI.MRCH.XD.WD.BR", 1979)
    uvi = A("wb/TX.UVI.MRCH.XD.WD.BR", 1979) / A("wb/TM.UVI.MRCH.XD.WD.BR", 1979)
    ov = tt.index.intersection(uvi.index)
    k = np.exp(np.mean(np.log(tt[ov]) - np.log(uvi[ov])))
    tot = (uvi * k).copy()
    tot.loc[tt.index] = tt
    m = A("wb/TOT.BRA", 1990)
    if 2025 not in tot.index and 2025 in m.index:
        tot.loc[2025] = tot.loc[2024] * m[2025] / m[2024]
    tot = tot.sort_index()
    rho = np.corrcoef(np.log(tt[ov]), np.log(uvi[ov]))[0, 1]
    return tot, dict(rescale_k=k, rho_overlap=rho, n_overlap=len(ov))


TOT, TOT_INFO = tot_series()
LTOT = np.log(TOT) * 100
DLTOT = LTOT.diff()
BRENT = A("brent_usd", 2000)
DLBRENT = dlog(BRENT)

# ----------------------------------------------------------------------------- metric definitions
# orient: +1 if higher value = "better" in the composite sense (only used for composites)
# exp_L / exp_R: expected sign of Δ(left−right) under each narrative (+1, -1, 0 = no difference), text
MET = {}


def met(mid, bucket, name, series, s, unit, primary, expL, expR, note=""):
    MET[mid] = dict(bucket=bucket, name=name, series=series, s=s.dropna().sort_index(), unit=unit,
                    primary=primary, expL=expL, expR=expR, note=note)


def build_metrics():
    # A growth
    gdp = A("wb/NY.GDP.MKTP.KD.ZG.BR")
    ibc = AP[AP.series_id == "ibc_br"].set_index("year")
    # 2026 partial: IBC-Br Jan–Jul 2026 vs Jan–Jul 2025
    ib = q("ibc_2026", """SELECT date, value FROM v_observations WHERE series_id='ibc_br' AND date <= current_date ORDER BY date""")
    ib["date"] = pd.to_datetime(ib.date)
    last = ib.date.max(); m26 = ib[(ib.date.dt.year == 2026)]; m25 = ib[(ib.date.dt.year == 2025) & (ib.date.dt.month <= last.month)]
    gdp.loc[2026] = 100 * (m26.value.mean() / m25.value.mean() - 1)
    met("A1", "A Growth", "Real GDP growth", ["wb/NY.GDP.MKTP.KD.ZG.BR", "ibc_br (2026 YTD)"], gdp, "% y/y", True, (+1, "higher"), (-1, "lower"))
    met("A2", "A Growth", "GDP per capita growth", ["wb/NY.GDP.PCAP.KD.ZG.BR"], A("wb/NY.GDP.PCAP.KD.ZG.BR"), "% y/y", True, (+1, "higher"), (-1, "lower"))
    met("A3", "A Growth", "Investment (GFCF) % GDP", ["wb/NE.GDI.FTOT.ZS.BR"], A("wb/NE.GDI.FTOT.ZS.BR"), "% GDP", True, (+1, "higher"), (-1, "lower"))
    met("A4", "A Growth", "Industrial production growth", ["wb/IPTOTSAKD_M.BRA"], dlog(A("wb/IPTOTSAKD_M.BRA", 1991)), "% y/y (log)", False, (+1, "higher"), (-1, "lower"))
    met("A5", "A Growth", "Output per worker growth", ["ilostat/SDG_0821_NOC_RT.BRA"], A("ilostat/SDG_0821_NOC_RT.BRA"), "% y/y", False, (+1, "higher"), (-1, "lower"))
    # B prices / rates
    defl = A("wb/NY.GDP.DEFL.KD.ZG.BR")
    met("B1", "B Prices & rates", "Inflation (GDP deflator, log)", ["wb/NY.GDP.DEFL.KD.ZG.BR"], 100 * np.log1p(defl / 100), "100·log(1+π)", True, (0, "no difference"), (+1, "higher"))
    met("B1b", "B Prices & rates", "IPCA 12m (Dec)", ["ipca_12m"], YEs_month("ipca_12m"), "%", False, (0, "no difference"), (+1, "higher"))
    met("B2", "B Prices & rates", "Real policy rate (ex-ante)", ["real_policy_rate"], A("real_policy_rate", 2002), "% p.a.", True, (-1, "lower"), (+1, "higher"))
    met("B3", "B Prices & rates", "Focus IPCA 12m expectation", ["focus_ipca_12m"], A("focus_ipca_12m", 2002), "%", False, (0, "no difference"), (+1, "higher"))
    met("B4", "B Prices & rates", "Real lending rate (WB)", ["wb/FR.INR.RINR.BR"], A("wb/FR.INR.RINR.BR"), "%", False, (-1, "lower"), (+1, "higher"))
    met("B5", "B Prices & rates", "Δ Private credit % GDP", ["wb/FS.AST.PRVT.GD.ZS.BR"], A("wb/FS.AST.PRVT.GD.ZS.BR", 1984).diff(), "pts/yr", False, (+1, "higher"), (0, "no difference"))
    # C fiscal
    met("C1", "C Fiscal", "Primary balance % GDP", ["primary_balance_gdp"], A("primary_balance_gdp", 2003), "% GDP (Dec, 12m)", True, (0, "similar"), (-1, "lower"))
    gd = A("gross_public_debt_gdp", 2006)
    gd = pd.concat([pd.Series({2006: con.execute("SELECT value FROM v_observations WHERE series_id='gross_public_debt_gdp' ORDER BY date LIMIT 1").fetchone()[0]}), gd[gd.index > 2006]])
    global GD_LVL; GD_LVL = gd.sort_index()
    met("C2", "C Fiscal", "Δ Gross debt % GDP", ["gross_public_debt_gdp"], gd.diff(), "pts/yr", True, (0, "similar"), (+1, "higher"))
    met("C3", "C Fiscal", "Δ Net debt % GDP", ["net_public_debt_gdp"], A("net_public_debt_gdp", 2002).diff(), "pts/yr", False, (0, "similar"), (+1, "higher"))
    met("C4", "C Fiscal", "Interest bill % GDP", ["interest_bill_gdp"], A("interest_bill_gdp", 2003), "% GDP", True, (0, "similar"), (+1, "higher"))
    met("C5", "C Fiscal", "Government consumption % GDP", ["wb/NE.CON.GOVT.ZS.BR"], A("wb/NE.CON.GOVT.ZS.BR"), "% GDP", False, (+1, "higher"), (+1, "higher"))
    met("C6", "C Fiscal", "Tax revenue % GDP", ["wb/GC.TAX.TOTL.GD.ZS.BR"], A("wb/GC.TAX.TOTL.GD.ZS.BR"), "% GDP", False, (+1, "higher"), (+1, "higher"))
    # D markets / external
    wbeq = YEs("wb/DSTKMKTXD_M.BRA"); ib = YEs("ibovespa_usd")
    eq = pd.concat([dlog(wbeq).loc[1995:2000], dlog(ib).loc[2001:]])
    met("D1", "D Markets & external", "USD equity return (log)", ["wb/DSTKMKTXD_M.BRA (1995–2000)", "ibovespa_usd (2001–2026 YTD)"], eq, "% /yr (log)", True, (0, "no difference"), (-1, "lower"))
    fxw = YEs("wb/DPANUSSPB_M.BRA"); fx = YEs("brl_usd")
    brl = pd.concat([-dlog(fxw).loc[1995:2000], -dlog(fx).loc[2001:]])
    met("D2", "D Markets & external", "BRL appreciation vs USD (log)", ["wb/DPANUSSPB_M.BRA (1995–2000)", "brl_usd (2001–2026 YTD)"], brl, "% /yr (+ = stronger BRL)", True, (0, "no difference"), (-1, "weaker"))
    met("D3", "D Markets & external", "Real effective exchange rate", ["wb/PX.REX.REER.BR"], A("wb/PX.REX.REER.BR"), "index 2010=100 (+ = stronger)", True, (0, "no difference"), (-1, "weaker"))
    met("D4", "D Markets & external", "EMBI spread", ["embi_brazil"], A("embi_brazil", 2000), "bp", False, (0, "no difference"), (+1, "higher"))
    met("D5", "D Markets & external", "10y real yield (NTN-B)", ["gov_real_yield_10y"], A("gov_real_yield_10y", 2015), "% p.a.", False, (0, "no difference"), (+1, "higher"))
    met("D6", "D Markets & external", "Current account % GDP", ["wb/BN.CAB.XOKA.GD.ZS.BR"], A("wb/BN.CAB.XOKA.GD.ZS.BR"), "% GDP", True, (0, "no difference"), (-1, "lower"))
    met("D7", "D Markets & external", "FDI inflows % GDP", ["wb/BX.KLT.DINV.WD.GD.ZS.BR"], A("wb/BX.KLT.DINV.WD.GD.ZS.BR"), "% GDP", True, (0, "no difference"), (-1, "lower"))
    met("D8", "D Markets & external", "Δ Reserves (months of imports)", ["wb/FI.RES.TOTL.MO.BR"], A("wb/FI.RES.TOTL.MO.BR", 1984).diff(), "months/yr", False, (0, "no difference"), (0, "no difference"))
    met("D9", "D Markets & external", "Δ Exports % GDP", ["wb/NE.EXP.GNFS.ZS.BR"], A("wb/NE.EXP.GNFS.ZS.BR", 1984).diff(), "pts/yr", False, (0, "no difference"), (0, "no difference"))
    met("D10", "D Markets & external", "Δ Market cap % GDP", ["wb/CM.MKT.LCAP.GD.ZS.BR"], A("wb/CM.MKT.LCAP.GD.ZS.BR").diff(), "pts/yr", False, (0, "no difference"), (-1, "lower"))
    # E labour & distribution
    un = A("wb/SL.UEM.TOTL.ZS.BR", 1991)
    nat = A("unemployment_rate", 2012)
    un.loc[2026] = nat[2026] + (un[2025] - nat[2025])   # 2026 YTD native, level-matched on 2025
    met("E1", "E Labour & distribution", "Unemployment rate", ["wb/SL.UEM.TOTL.ZS.BR", "unemployment_rate (2026 YTD, level-matched)"], un, "%", True, (-1, "lower"), (+1, "higher"))
    met("E1c", "E Labour & distribution", "Δ Unemployment rate", ["wb/SL.UEM.TOTL.ZS.BR"], un.diff(), "pts/yr", False, (-1, "falls more"), (+1, "rises more"))
    inf_a = interp(A("wb/JI.EMP.IFRM.ZS.BRA") * 100).diff()
    inf_b = interp(A("ilostat/SDG_0831_SEX_ECO_RT.BRA")).diff()
    infm = pd.concat([inf_a.loc[:2020], inf_b.loc[2021:]])
    met("E2", "E Labour & distribution", "Δ Informality (within-series)", ["wb/JI.EMP.IFRM.ZS.BRA (≤2020)", "ilostat/SDG_0831_SEX_ECO_RT.BRA (2021+)"], infm, "pts/yr", False, (-1, "falls"), (+1, "rises (min-wage cost)"))
    mw = A("ilostat/EAR_INEE_NOC_NB.BRA") / A("wb/FP.CPI.TOTL.BR")
    met("E3", "E Labour & distribution", "Real minimum wage growth", ["ilostat/EAR_INEE_NOC_NB.BRA", "wb/FP.CPI.TOTL.BR"], dlog(mw), "% /yr (log)", True, (+1, "higher"), (+1, "higher (at employment cost)"))
    met("E4", "E Labour & distribution", "Real average labour income growth", ["real_average_income"], dlog(A("real_average_income", 2012)), "% /yr (log)", False, (+1, "higher"), (0, "no difference"))
    gini = interp(A("wb/SI.POV.GINI.BR", 1981))
    met("E5", "E Labour & distribution", "Δ Gini", ["wb/SI.POV.GINI.BR (gaps interpolated)"], gini.diff(), "pts/yr", True, (-1, "falls more"), (0, "≈0 after ToT"))
    met("E5L", "E Labour & distribution", "Gini (level)", ["wb/SI.POV.GINI.BR"], A("wb/SI.POV.GINI.BR", 1981), "index", False, (-1, "lower"), (0, "≈0 after ToT"))
    pov = interp(A("wb/SI.POV.DDAY.BR", 1981))
    met("E6", "E Labour & distribution", "Δ Poverty $3.00/day", ["wb/SI.POV.DDAY.BR (gaps interpolated)"], pov.diff(), "pts/yr", True, (-1, "falls more"), (0, "≈0 after ToT"))
    met("E6b", "E Labour & distribution", "Δ Poverty $8.30/day", ["wb/SI.POV.UMIC.BR"], interp(A("wb/SI.POV.UMIC.BR", 1981)).diff(), "pts/yr", False, (-1, "falls more"), (0, "≈0 after ToT"))
    met("E7a", "E Labour & distribution", "Δ Income share bottom 20%", ["wb/SI.DST.FRST.20.BR"], interp(A("wb/SI.DST.FRST.20.BR", 1981)).diff(), "pts/yr", False, (+1, "rises"), (0, "≈0"))
    met("E7b", "E Labour & distribution", "Δ Income share top 10%", ["wb/SI.DST.10TH.10.BR"], interp(A("wb/SI.DST.10TH.10.BR", 1981)).diff(), "pts/yr", False, (-1, "falls"), (0, "≈0"))
    met("E8", "E Labour & distribution", "Δ Labour income share", ["ilostat/LAP_2GDP_NOC_RT.BRA"], A("ilostat/LAP_2GDP_NOC_RT.BRA").diff(), "pts/yr", False, (+1, "rises"), (0, "≈0"))
    eg = A("ilostat/EAR_EMTG_SEX_NB.BRA"); eg = eg[eg > 0]
    met("E9", "E Labour & distribution", "Δ Earnings Gini", ["ilostat/EAR_EMTG_SEX_NB.BRA (value>0)"], interp(eg).diff(), "pts/yr", False, (-1, "falls"), (0, "≈0"))
    # F health / education / safety
    met("F1", "F Health, education, safety", "Infant mortality change (log)", ["wb/SP.DYN.IMRT.IN.BR"], dlog(A("wb/SP.DYN.IMRT.IN.BR", 1984)), "% /yr (− = improving)", True, (-1, "falls faster"), (0, "no difference"))
    met("F2", "F Health, education, safety", "Life expectancy gain", ["wb/SP.DYN.LE00.IN.BR"], A("wb/SP.DYN.LE00.IN.BR", 1984).diff(), "years/yr", False, (+1, "higher"), (0, "no difference"))
    met("F3", "F Health, education, safety", "Govt health spend % GDP", ["wb/SH.XPD.GHED.GD.ZS.BR"], A("wb/SH.XPD.GHED.GD.ZS.BR"), "% GDP", False, (+1, "higher"), (0, "no difference"))
    met("F4", "F Health, education, safety", "Education spend % GDP", ["wb/SE.XPD.TOTL.GD.ZS.BR"], interp(A("wb/SE.XPD.TOTL.GD.ZS.BR")), "% GDP", False, (+1, "higher"), (0, "no difference"))
    hr = A("homicide_rate", 2000)
    hd = A("homicide_deaths", 1996); popu = A("population", 2000)
    ds = (hd / popu * 1e5).dropna(); ds = ds[ds.index <= 2025]
    hr_ext = hr.copy()
    for y in (2024, 2025):
        if y in ds.index and y - 1 in ds.index:
            hr_ext.loc[y] = hr_ext.loc[y - 1] + (ds[y] - ds[y - 1])
    met("F5", "F Health, education, safety", "Δ Homicide rate", ["homicide_rate (WHO 2000–2023)", "homicide_deaths/population (DATASUS, 2024–25 diffs; preliminary)"], hr_ext.sort_index().diff(), "per 100k /yr", True, (-1, "falls more"), (0, "no difference"))
    met("F6", "F Health, education, safety", "Social safety-net coverage", ["wb/per_sa_allsa.cov_pop_tot.BR"], A("wb/per_sa_allsa.cov_pop_tot.BR"), "% pop", False, (+1, "higher"), (0, "no difference"))
    # G institutions (WGI)
    for k, nm, prim in [("CC", "Control of Corruption", True), ("GE", "Government Effectiveness", True), ("RL", "Rule of Law", True),
                        ("RQ", "Regulatory Quality", False), ("VA", "Voice & Accountability", False), ("PV", "Political Stability", False)]:
        s = interp(A(f"wb/GOV_WGI_{k}_EST.BR", 1996)).diff()
        met("G" + k, "G Institutions (WGI)", "Δ WGI " + nm, [f"wb/GOV_WGI_{k}_EST.BR (1996–2002 biennial, interpolated)"], s, "est. units/yr", prim,
            (0, "no difference"), (-1, "worse") if k == "CC" else (0, "no difference"))
    # H environment
    met("H1", "H Environment", "Primary forest loss", ["wb/AG.LND.PFLS.HA.BR"], A("wb/AG.LND.PFLS.HA.BR") / 1e6, "Mha/yr", True, (-1, "lower"), (0, "no difference / higher"))
    lu = A("wb/EN.GHG.CO2.LU.MT.CE.AR5.BR"); lu = lu[lu.index <= 2022]
    met("H2", "H Environment", "LULUCF CO2", ["wb/EN.GHG.CO2.LU.MT.CE.AR5.BR (2023 carry-forward dropped)"], lu, "Mt", False, (-1, "lower"), (0, "no difference"))
    met("H3", "H Environment", "Δ CO2 per capita ex-LULUCF", ["wb/EN.GHG.CO2.PC.CE.AR5.BR"], A("wb/EN.GHG.CO2.PC.CE.AR5.BR", 1984).diff(), "t/yr", False, (0, "no difference"), (0, "no difference"))
    for k in MET:
        MET[k]["s"] = MET[k]["s"][(MET[k]["s"].index >= 1985) & (MET[k]["s"].index <= 2026)]


def YEs_month(sid):
    d = q(f"dec_{sid}", f"SELECT CAST(EXTRACT(year FROM date) AS INT) y, arg_max(value, date) v FROM v_observations WHERE series_id='{sid}' AND date<=current_date GROUP BY 1")
    return d.set_index("y").v.sort_index()


build_metrics()
PRIMARY = [k for k, v in MET.items() if v["primary"]]
OK_PRIMARY = ["A1", "A2", "A3", "B1", "B2", "C1", "C2", "C4", "D1", "D2", "D3", "D6", "D7", "E1", "E3", "E5", "E6", "F1", "F5", "GCC", "GGE", "GRL", "H1"]
assert set(PRIMARY) == set(OK_PRIMARY), set(PRIMARY) ^ set(OK_PRIMARY)


# ----------------------------------------------------------------------------- ToT adjustment
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X))
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    r2 = 1 - r.var() / y.var() if y.var() > 0 else 0.0
    return b, r, r2


def tot_adjust(s, brent=False):
    """residual of y_t on ΔlogToT_t, logToT_t (+ΔlogBrent_t), re-centred on mean(y)."""
    df = pd.DataFrame({"y": s, "d": DLTOT, "l": LTOT})
    cols = ["d", "l"]
    if brent:
        df["b"] = DLBRENT; cols.append("b")
    df = df.dropna(subset=["y"] + cols)
    df = df[df.index.isin(s.index)]
    if len(df) < 8:
        return None
    b, r, r2 = ols(df.y.values, [df[c].values for c in cols])
    return pd.Series(r + df.y.mean(), index=df.index)


# ----------------------------------------------------------------------------- unit statistics
def unit_stats(s, unit="term", attr="c", coding="A", y0=1985, min_years=2):
    """dict unit -> (lean, array of yearly values). unit: term | mandate."""
    s = s[(s.index >= y0)]
    col = ("term_" if unit in ("term", "year") else "mand_") + ("lag1" if attr == "lag1" else "c")
    out = {}
    for y, v in s.items():
        if y not in ATTR.index or pd.isna(v):
            continue
        u = ATTR.at[y, col]
        if u is None or (isinstance(u, float) and np.isnan(u)):
            continue
        if attr == "dropfirst" and ATTR.at[y, "first_t" if unit in ("term", "year") else "first_m"]:
            continue
        if coding == "E" and y in (2015, 2016) and ATTR.at[y, "term_c"] == "Dilma":
            continue
        term = u if unit in ("term", "year") else M2T[u]
        lean = CODINGS[coding][term]
        if lean is None:
            continue
        out.setdefault(u, [lean, []])[1].append(v)
    return {u: (l, np.array(v)) for u, (l, v) in out.items() if len(v) >= min_years}


def delta(us, weighted=False, rank=False):
    L = [u for u, (l, _) in us.items() if l == "left"]; R = [u for u, (l, _) in us.items() if l == "right"]
    if len(L) < 2 or len(R) < 2:
        return None
    if weighted:
        lv = np.concatenate([us[u][1] for u in L]); rv = np.concatenate([us[u][1] for u in R])
        return lv.mean() - rv.mean()
    m = {u: v.mean() for u, (l, v) in us.items() if l in ("left", "right")}
    if rank:
        keys = list(m); rk = pd.Series([m[k] for k in keys], index=keys).rank()
        return rk[L].mean() - rk[R].mean()
    return np.mean([m[u] for u in L]) - np.mean([m[u] for u in R])


def perm_test(values, labels):
    """exact permutation of lean labels across units; returns (p, p_min_attainable, n_labelings)."""
    values = np.asarray(values, float); labels = np.asarray(labels)
    n, k = len(values), int((labels == "left").sum())
    obs = values[labels == "left"].mean() - values[labels != "left"].mean()
    ds = []
    for comb in itertools.combinations(range(n), k):
        mask = np.zeros(n, bool); mask[list(comb)] = True
        ds.append(values[mask].mean() - values[~mask].mean())
    ds = np.abs(np.array(ds))
    p = np.mean(ds >= abs(obs) - 1e-12)
    pmin = np.mean(ds >= ds.max() - 1e-12)
    return p, pmin, len(ds)


def cluster_bootstrap(us, rng, nboot=NBOOT):
    """two-stage: resample units within lean group, then years within unit. returns array of Δ."""
    L = [u for u, (l, _) in us.items() if l == "left"]; R = [u for u, (l, _) in us.items() if l == "right"]
    def unit_draws(v):
        idx = rng.integers(0, len(v), size=(nboot, len(v)))
        return v[idx].mean(1)
    def grp(units):
        B = np.vstack([unit_draws(us[u][1]) for u in units])      # (k, nboot)
        pick = rng.integers(0, len(units), size=(nboot, len(units)))
        return B[pick, np.arange(nboot)[:, None]].mean(1)
    return grp(L) - grp(R)


def term_stat(mid, adj="raw", **kw):
    s = MET[mid]["s"]
    if adj == "tot":
        s = tot_adjust(s)
    elif adj == "totbrent":
        s = tot_adjust(s[s.index >= 2001], brent=True)
    if s is None:
        return {}
    return unit_stats(s, **kw)


def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    q_ = np.empty(n); prev = 1.0
    for i in range(n - 1, -1, -1):
        prev = min(prev, p[o[i]] * n / (i + 1)); q_[o[i]] = prev
    return q_


def holm(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    adj = np.empty(n); run = 0.0
    for i, j in enumerate(o):
        run = max(run, min(1.0, (n - i) * p[j])); adj[j] = run
    return adj


# ----------------------------------------------------------------------------- main term-level results
rng = np.random.default_rng(SEED)
LEAN_A = CODINGS["A"]
TERM_ORDER = list(T.short)


def analyse_metric(mid):
    out = dict(metric_id=mid, **{k: MET[mid][k] for k in ("bucket", "name", "unit", "primary")})
    s = MET[mid]["s"]
    out["series_ids"] = "; ".join(MET[mid]["series"])
    sids = [x.split(" ")[0] for x in MET[mid]["series"]]
    out["source"] = "; ".join(sorted({META[x]["source"] for x in sids if x in META}))
    out["freq"] = "; ".join(sorted({META[x]["freq"] for x in sids if x in META}))
    out["first_year"], out["last_year"] = int(s.index.min()), int(s.index.max())
    out["last_date"] = max(META[x]["last_date"] for x in sids if x in META)
    for adj in ("raw", "tot"):
        us = term_stat(mid, adj)
        tag = "" if adj == "raw" else "_tot"
        L = [u for u, (l, _) in us.items() if l == "left"]; R = [u for u, (l, _) in us.items() if l == "right"]
        out["n_left" + tag], out["n_right" + tag] = len(L), len(R)
        if adj == "raw":
            out["term_values"] = {u: round(float(v.mean()), 3) for u, (l, v) in us.items()}
            out["term_nyears"] = {u: len(v) for u, (l, v) in us.items()}
        if len(L) < 2 or len(R) < 2:
            continue
        d = delta(us)
        lr = [u for u in us if us[u][0] in ("left", "right")]
        p, pmin, nl = perm_test([us[u][1].mean() for u in lr], [us[u][0] for u in lr])
        bs = cluster_bootstrap(us, rng)
        out["mean_left" + tag] = float(np.mean([us[u][1].mean() for u in L]))
        out["mean_right" + tag] = float(np.mean([us[u][1].mean() for u in R]))
        out["diff" + tag] = float(d)
        out["diff_weighted" + tag] = float(delta(us, weighted=True))
        out["ci80" + tag] = [float(np.percentile(bs, 10)), float(np.percentile(bs, 90))]
        out["ci95" + tag] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
        out["perm_p" + tag], out["p_min_attainable" + tag], out["n_labelings" + tag] = float(p), float(pmin), nl
        out["rank_diff" + tag] = float(delta(us, rank=True))
    return out


RESULTS = {mid: analyse_metric(mid) for mid in MET}
# ----------------------------------------------------------------------------- Q0: variance decomposition
def shapley_r2(y, Xa, Xb):
    _, _, ra = ols(y, Xa); _, _, rb = ols(y, Xb); _, _, rab = ols(y, Xa + Xb)
    sa = 0.5 * (ra + (rab - rb)); sb = 0.5 * (rb + (rab - ra))
    return dict(r2_lean=ra, r2_tot=rb, r2_both=rab, shap_lean=sa, shap_tot=sb)


def q0(mid):
    s = MET[mid]["s"]
    # year level (1985-2025, ToT available)
    df = pd.DataFrame({"y": s, "d": DLTOT, "l": LTOT}).dropna()
    df = df[df.index.isin(ATTR.index)]
    df["lean"] = [LEAN_A[ATTR.at[y, "term_c"]] for y in df.index]
    df["term"] = [ATTR.at[y, "term_c"] for y in df.index]
    res = {}
    if len(df) >= 8:
        Xl = [(df.lean == "left").astype(float).values, (df.lean == "centre").astype(float).values]
        Xl = [x for x in Xl if x.std() > 0]
        res["year"] = shapley_r2(df.y.values, Xl, [df.d.values, df.l.values])
        res["year"]["n"] = len(df)
    # term level: term mean of y vs left dummy and term mean ΔlogToT (1 regressor each)
    g = df.groupby("term").agg(y=("y", "mean"), d=("d", "mean"), l=("l", "mean"), lean=("lean", "first"), n=("y", "size"))
    g = g[g.n >= 2]
    if len(g) >= 5:
        res["term"] = shapley_r2(g.y.values, [(g.lean == "left").astype(float).values], [g.d.values])
        res["term_level"] = shapley_r2(g.y.values, [(g.lean == "left").astype(float).values], [g.l.values])
        res["term"]["n"] = len(g)
    return res


Q0 = {mid: q0(mid) for mid in MET}

# ----------------------------------------------------------------------------- inherited conditions (starting-point adjusted change)
LEVEL_FOR_CHANGE = {"C2": "gross_public_debt_gdp", "E5": None, "E1c": None, "B2": None}


def start_adjusted(mid, level_series):
    """term change (end - start) regressed on start level; Δ(left-right) of residuals."""
    lv = level_series
    rows = []
    for t in TERM_ORDER:
        yrs = ATTR.index[ATTR.term_c == t]
        y0, y1 = yrs.min() - 1, min(yrs.max(), lv.index.max())
        if y0 in lv.index and y1 in lv.index and y1 > y0 + 1:
            rows.append((t, LEAN_A[t], lv[y0], (lv[y1] - lv[y0]) / (y1 - y0)))
    d = pd.DataFrame(rows, columns=["term", "lean", "start", "chg"])
    d = d[d.lean.isin(["left", "right", "centre"])]
    if (d.lean == "left").sum() < 2 or (d.lean == "right").sum() < 2:
        return None
    b, r, _ = ols(d.chg.values, [d.start.values])
    d["resid"] = r
    lr = d[d.lean.isin(["left", "right"])]
    raw = lr[lr.lean == "left"].chg.mean() - lr[lr.lean == "right"].chg.mean()
    adj = lr[lr.lean == "left"].resid.mean() - lr[lr.lean == "right"].resid.mean()
    return dict(raw=raw, adj=adj, slope=b[1], n=len(d), table=d.round(3).to_dict("records"))


START_ADJ = {
    "C2 gross debt": start_adjusted("C2", GD_LVL),
    "E5 Gini": start_adjusted("E5", interp(A("wb/SI.POV.GINI.BR", 1981))),
    "E1 unemployment": start_adjusted("E1", MET["E1"]["s"]),
    "B2 real policy rate": start_adjusted("B2", MET["B2"]["s"]),
    "E6 poverty $3": start_adjusted("E6", interp(A("wb/SI.POV.DDAY.BR", 1981))),
}

# ----------------------------------------------------------------------------- composites
COMPOSITES = {
    "COMP-G Growth": [("A1", 1), ("A2", 1), ("A3", 1), ("A4", 1)],
    "COMP-S Orthodox stability": [("B1", -1), ("B2", -1), ("C1", 1), ("C2", -1), ("D6", 1), ("D8", 1)],
    "COMP-D Distribution": [("E1", -1), ("E5", -1), ("E6", -1), ("E3", 1), ("E2", -1)],
    "COMP-M Markets": [("D1", 1), ("D2", 1), ("D4", -1), ("D5", -1)],
}


def composite(name, adj="raw", **kw):
    zs = []
    for mid, sign in COMPOSITES[name]:
        us = term_stat(mid, adj, **kw)
        m = pd.Series({u: v.mean() for u, (l, v) in us.items()})
        if len(m) < 3 or m.std() == 0:
            continue
        zs.append(sign * (m - m.mean()) / m.std())
    if not zs:
        return None
    Z = pd.concat(zs, axis=1)
    c = Z.mean(axis=1)[Z.notna().sum(axis=1) >= 2]
    return c


COMP_RES = {}
for name in COMPOSITES:
    for adj in ("raw", "tot"):
        c = composite(name, adj)
        lab = np.array([LEAN_A[u] for u in c.index])
        keep = np.isin(lab, ["left", "right"])
        p, pmin, nl = perm_test(c.values[keep], lab[keep])
        # bootstrap: resample terms within group
        vals_l = c.values[lab == "left"]; vals_r = c.values[lab == "right"]
        bl = vals_l[rng.integers(0, len(vals_l), (NBOOT, len(vals_l)))].mean(1)
        br = vals_r[rng.integers(0, len(vals_r), (NBOOT, len(vals_r)))].mean(1)
        bs = bl - br
        COMP_RES[(name, adj)] = dict(by_term=c.round(3).to_dict(), diff=float(vals_l.mean() - vals_r.mean()),
                                     ci80=[float(np.percentile(bs, 10)), float(np.percentile(bs, 90))],
                                     ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                                     perm_p=float(p), p_min=float(pmin), n_left=int(len(vals_l)), n_right=int(len(vals_r)))
for adj in ("raw", "tot"):
    names = list(COMPOSITES)
    hp = holm([COMP_RES[(n, adj)]["perm_p"] for n in names])
    for n, h in zip(names, hp):
        COMP_RES[(n, adj)]["holm_p"] = float(h)

# ----------------------------------------------------------------------------- robustness matrix
SAMPLES = {"1985+": 1985, "1995+": 1995, "2003+": 2003}
UNITS = ["term", "mandate", "year"]
CODES = ["A", "B", "C", "D", "E"]
ATTRS = ["c", "lag1", "dropfirst"]
ADJS = ["raw", "tot", "totbrent"]
TRANS = ["mean", "rank"]


def robustness_grid():
    rows = []
    cache = {}
    for mid in PRIMARY:
        for adj in ADJS:
            s = MET[mid]["s"]
            if adj == "tot":
                s = tot_adjust(s)
            elif adj == "totbrent":
                s = tot_adjust(s[s.index >= 2001], brent=True)
            if s is None:
                continue
            for (sn, y0), unit, code, at in itertools.product(SAMPLES.items(), UNITS, CODES, ATTRS):
                us = unit_stats(s, unit="mandate" if unit == "mandate" else "term", attr=at, coding=code, y0=y0)
                for tr in TRANS:
                    if unit == "year" and tr == "rank":
                        continue
                    d = delta(us, weighted=(unit == "year"), rank=(tr == "rank"))
                    rows.append(dict(metric_id=mid, sample=sn, unit=unit, coding=code, attribution=at, adjustment=adj,
                                     transform=tr, diff=None if d is None else float(d),
                                     sign=None if d is None else int(np.sign(d))))
    return pd.DataFrame(rows)


ROB = robustness_grid()
SIGN_SHARE = {}
for mid in PRIMARY:
    base = RESULTS[mid].get("diff")
    r = ROB[(ROB.metric_id == mid) & ROB["diff"].notna()]
    if base is None or not len(r):
        SIGN_SHARE[mid] = None; continue
    SIGN_SHARE[mid] = float((r.sign == np.sign(base)).mean())
    RESULTS[mid]["sign_consistency_share"] = SIGN_SHARE[mid]
    RESULTS[mid]["n_cells"] = int(len(r))
    RESULTS[mid]["share_positive_by_dim"] = {dim: r.groupby(dim).sign.apply(lambda x: float((x > 0).mean())).to_dict()
                                             for dim in ("sample", "unit", "coding", "attribution", "adjustment", "transform")}

# multiple comparisons: BH across primary metrics (raw and ToT separately)
for tag in ("", "_tot"):
    ids = [m for m in PRIMARY if ("perm_p" + tag) in RESULTS[m]]
    qs = bh([RESULTS[m]["perm_p" + tag] for m in ids])
    for m, qq in zip(ids, qs):
        RESULTS[m]["bh_q" + tag] = float(qq)


def verdict(r, mid):
    if "diff" not in r:
        return "insufficient data (<2 terms per side)"
    d = r["diff"]; ci = r["ci80"]; share = r.get("sign_consistency_share")
    robust = share is not None and share >= 0.8 and (ci[0] > 0 or ci[1] < 0)
    if not robust:
        return "no robust association"
    sg = int(np.sign(d))
    match = [n for n, e in (("left", MET[mid]["expL"][0]), ("right", MET[mid]["expR"][0])) if e == sg]
    against = [n for n, e in (("left", MET[mid]["expL"][0]), ("right", MET[mid]["expR"][0])) if e == -sg or e == 0]
    txt = "robust-by-CI Δ" + ("+" if sg > 0 else "−") + " (perm p %.2f, floor %.2f)" % (r["perm_p"], r["p_min_attainable"])
    if match: txt += "; sign matches " + " & ".join(match) + " narrative"
    if against: txt += "; contradicts " + " & ".join(against) + " narrative's expectation"
    return txt


for mid in MET:
    if MET[mid]["primary"]:
        RESULTS[mid]["verdict"] = verdict(RESULTS[mid], mid)
    else:
        RESULTS[mid]["verdict"] = "secondary — descriptive only"

# within-president contrasts (descriptive)
def mandate_values(mid):
    us = unit_stats(MET[mid]["s"], unit="mandate", min_years=1)
    return {u: float(v.mean()) for u, (l, v) in us.items()}


WITHIN = {mid: mandate_values(mid) for mid in ["A1", "B1", "B2", "C1", "C2", "D1", "D2", "E1", "E3", "E5", "E6", "F1", "F5", "GCC", "H1"]}
MAND_TOT = {}
for mm in M.mandate:
    yrs = ATTR.index[ATTR.mand_c == mm]
    MAND_TOT[mm] = dict(dltot=float(DLTOT.reindex(yrs).mean()), ltot=float(LTOT.reindex(yrs).mean()),
                        years=f"{yrs.min()}–{yrs.max()}")

# ----------------------------------------------------------------------------- event study
EVENTS = [  # date, label, group
    ("2002-10-06", "2002 R1", "first round"), ("2002-10-27", "2002 run-off (Lula)", "left win"),
    ("2006-10-01", "2006 R1", "first round"), ("2006-10-29", "2006 run-off (Lula)", "left win"),
    ("2010-10-03", "2010 R1", "first round"), ("2010-10-31", "2010 run-off (Dilma)", "left win"),
    ("2014-10-05", "2014 R1", "first round"), ("2014-10-26", "2014 run-off (Dilma)", "left win"),
    ("2018-10-07", "2018 R1", "first round"), ("2018-10-28", "2018 run-off (Bolsonaro)", "right transition"),
    ("2022-10-02", "2022 R1", "first round"), ("2022-10-30", "2022 run-off (Lula)", "left win"),
    ("2026-10-04", "2026 R1", "first round"),
    ("2003-01-01", "2003 inauguration (Lula)", "inauguration-left"), ("2007-01-01", "2007 inauguration", "inauguration-left"),
    ("2011-01-01", "2011 inauguration (Dilma)", "inauguration-left"), ("2015-01-01", "2015 inauguration", "inauguration-left"),
    ("2019-01-01", "2019 inauguration (Bolsonaro)", "right transition"), ("2023-01-01", "2023 inauguration (Lula)", "left win"),
    ("2016-04-17", "2016 Chamber impeachment vote", "right transition"), ("2016-05-12", "2016 Temer acting", "other"),
    ("2016-08-31", "2016 Senate removal", "other"),
    ("2016-12-15", "2016 spending cap", "policy"), ("2021-02-24", "2021 BCB autonomy", "policy"),
    ("2023-08-31", "2023 fiscal framework", "policy"), ("2025-08-06", "2025 US tariff", "policy"),
]
ES_SERIES = {"ibovespa_usd": ("logpct", 1), "ibovespa_level": ("logpct", 1), "brl_usd": ("logpct", -1),
             "embi_brazil": ("bp", 1), "gov_real_yield_10y": ("bp100", 1), "focus_fx": ("level", 1),
             "focus_selic_12m": ("level", 1)}
WINDOWS = {"[-1,+1]": (-1, 1), "[-5,+5]": (-5, 5), "[-20,+20]": (-20, 20), "[-60,+60]": (-60, 60),
           "[0,+60]": (0, 60), "pre [-120,-1]": (-120, -1), "[-5,-1]": (-5, -1)}
DAILY_SQL = """SELECT series_id, date, value FROM v_observations
WHERE date <= current_date AND series_id IN ('ibovespa_usd','ibovespa_level','brl_usd','embi_brazil','gov_real_yield_10y',
 'gov_nominal_yield_5y','focus_fx','focus_selic_12m','focus_ipca_12m','focus_gdp_growth','fx_reserves','brent_usd','selic_target')
ORDER BY series_id, date"""
DAILY = q("daily_panel", DAILY_SQL)
DAILY["date"] = pd.to_datetime(DAILY.date)
DS = {k: g.set_index("date").value for k, g in DAILY.groupby("series_id")}
EVENT_DATES = [pd.Timestamp(e[0]) for e in EVENTS]
BRENT_D = (100 * np.log(DS["brent_usd"]).diff()).dropna()


def daily_changes(sid):
    x = DS[sid]; kind, sign = ES_SERIES[sid]
    if kind == "logpct":
        d = 100 * np.log(x).diff()
    elif kind == "bp":
        d = x.diff()
    elif kind == "bp100":
        d = 100 * x.diff()
    else:
        d = x.diff()
    return sign * d.dropna()


def car(d, t0, a, b, est=(-250, -121), brent=None, raw=False):
    """abnormal cumulative change over [a,b] relative to t0 index; None if guard fails."""
    n = len(d)
    if t0 + est[0] < 0 or t0 + a < 1 or t0 + b >= n + (1 if b < 0 else 0):
        return None
    if t0 + b >= n:
        return None
    seg = d.iloc[t0 + a: t0 + b + 1]
    # guard against silent gaps: calendar span must be plausible
    span = (seg.index[-1] - seg.index[0]).days
    if span > 2.2 * (b - a + 1) + 15:
        return None
    if raw:
        return float(seg.sum())
    est_seg = d.iloc[t0 + est[0]: t0 + est[1] + 1]
    if brent is not None:   # market model on Brent daily log change, beta from estimation window
        bb = brent.reindex(d.index)
        xe = bb.iloc[t0 + est[0]: t0 + est[1] + 1]; ok = xe.notna() & est_seg.notna()
        if ok.sum() < 60:
            return None
        X = np.column_stack([np.ones(ok.sum()), xe[ok].values]); beta = np.linalg.lstsq(X, est_seg[ok].values, rcond=None)[0]
        xs = bb.iloc[t0 + a: t0 + b + 1].fillna(0.0)
        return float((seg - beta[0] - beta[1] * xs).sum())
    mu = est_seg.mean()
    return float(seg.sum() - mu * len(seg))


def event_index(d, date):
    idx = d.index.searchsorted(pd.Timestamp(date))
    return idx  # first obs on/after event date (may equal len(d) if after data end)


def event_study():
    rows = []
    for sid in ES_SERIES:
        d = daily_changes(sid)
        for date, label, grp in EVENTS:
            t0 = event_index(d, date)
            for wn, (a, b) in WINDOWS.items():
                live = not (t0 >= len(d) and b >= 0)
                v = car(d, t0, a, b) if live else None
                raw = car(d, t0, a, b, raw=True) if live else None
                vb = car(d, t0, a, b, brent=BRENT_D) if (live and sid in ("ibovespa_usd", "brl_usd") and pd.Timestamp(date).year >= 2001) else None
                rows.append(dict(series_id=sid, event_date=date, event=label, group=grp, window=wn, car=v, raw_change=raw, car_brent_adj=vb))
    ev = pd.DataFrame(rows)
    # placebo distributions
    pl_rows = []
    rngp = np.random.default_rng(SEED)
    for sid in ES_SERIES:
        d = daily_changes(sid)
        ok = np.ones(len(d), bool)
        for e in EVENT_DATES:
            ok &= np.abs((d.index - e).days) > 90
        cand = np.where(ok)[0]
        cand = cand[(cand > 260) & (cand < len(d) - 70)]
        draws = rngp.choice(cand, size=min(2000, len(cand)), replace=len(cand) < 2000)
        for wn, (a, b) in WINDOWS.items():
            vals = np.array([car(d, t, a, b) for t in draws], dtype=object)
            vals = np.array([v for v in vals if v is not None], float)
            pl_rows.append(dict(series_id=sid, window=wn, placebo_sd=float(vals.std()), placebo_n=len(vals), placebo=vals))
    PL = {(r["series_id"], r["window"]): r for r in pl_rows}
    def pz(r):
        if r.car is None or pd.isna(r.car):
            return pd.Series({"placebo_p": np.nan, "z": np.nan})
        pl = PL[(r.series_id, r.window)]["placebo"]
        return pd.Series({"placebo_p": float(np.mean(np.abs(pl) >= abs(r.car))), "z": r.car / pl.std()})
    ev[["placebo_p", "z"]] = ev.apply(pz, axis=1)
    return ev, PL


EV, PLACEBO = event_study()


def event_group_compare():
    rows = []
    for sid in ES_SERIES:
        for wn in WINDOWS:
            e = EV[(EV.series_id == sid) & (EV.window == wn) & EV.group.isin(["left win", "right transition"]) & EV.car.notna()]
            nl, nr = (e.group == "left win").sum(), (e.group == "right transition").sum()
            if nl < 2 or nr < 1:
                rows.append(dict(series_id=sid, window=wn, n_left=nl, n_right=nr)); continue
            vals = e.car.values.astype(float); lab = np.where(e.group == "left win", "left", "right")
            p, pmin, nlab = perm_test(vals, lab)
            rows.append(dict(series_id=sid, window=wn, n_left=nl, n_right=nr, mean_left_win=vals[lab == "left"].mean(),
                             mean_right_transition=vals[lab == "right"].mean(), diff=vals[lab == "left"].mean() - vals[lab == "right"].mean(),
                             perm_p=p, p_min=pmin))
    return pd.DataFrame(rows)


EVG = event_group_compare()

# 1994/1998 monthly descriptive
M94_SQL = """SELECT series_id, date, value FROM v_observations WHERE series_id IN ('wb/DSTKMKTXD_M.BRA','wb/DPANUSSPB_M.BRA')
AND ((date BETWEEN '1994-04-01' AND '1995-01-31') OR (date BETWEEN '1998-04-01' AND '1999-01-31')) ORDER BY 1,2"""
M9498 = q("monthly_1994_1998", M94_SQL)

# ----------------------------------------------------------------------------- 2026 pre-election check (4.7)
PRE_SERIES = {"brl_usd": "logpct_inv", "ibovespa_usd": "logpct", "ibovespa_level": "logpct", "gov_real_yield_10y": "bp100",
              "gov_nominal_yield_5y": "bp100", "focus_fx": "level", "focus_selic_12m": "level", "focus_ipca_12m": "level",
              "focus_gdp_growth": "level", "fx_reserves": "logpct"}
R1 = {2002: "2002-10-06", 2006: "2006-10-01", 2010: "2010-10-03", 2014: "2014-10-05", 2018: "2018-10-07", 2022: "2022-10-02", 2026: "2026-10-04"}


def pre_election_check():
    rows = []
    for sid, kind in PRE_SERIES.items():
        x = DS[sid]
        for yr, d1 in R1.items():
            d1 = pd.Timestamp(d1)
            pre = x[x.index < d1]
            if not len(pre) or (d1 - pre.index[-1]).days > 14:
                continue
            end_v, end_d = pre.iloc[-1], pre.index[-1]
            wins = {"YTD (Jan 1→t−1)": pd.Timestamp(yr, 1, 1), "Jul 1→t−1": pd.Timestamp(yr, 7, 1), "Sep 1→t−1": pd.Timestamp(yr, 9, 1)}
            for wn, ws in wins.items():
                base = x[x.index < ws]
                if not len(base) or (ws - base.index[-1]).days > 10:
                    continue
                b = base.iloc[-1]
                rows.append(dict(series_id=sid, year=yr, window=wn, change=chg(b, end_v, kind), end_date=str(end_d.date())))
            if len(pre) >= 6:
                rows.append(dict(series_id=sid, year=yr, window="t−5→t−1", change=chg(pre.iloc[-6], end_v, kind), end_date=str(end_d.date())))
    df = pd.DataFrame(rows)
    out = []
    for (sid, wn), g in df.groupby(["series_id", "window"]):
        hist = g[g.year < 2026].change.values; cur = g[g.year == 2026].change
        if not len(cur):
            continue
        c = float(cur.iloc[0])
        r = dict(series_id=sid, window=wn, change_2026=c, n_hist=len(hist))
        if len(hist) >= 2:
            p25, p75 = np.percentile(hist, [25, 75])
            r.update(hist_mean=hist.mean(), hist_sd=hist.std(ddof=1), z=(c - hist.mean()) / hist.std(ddof=1) if hist.std(ddof=1) > 0 else np.nan,
                     hist_p25=p25, hist_p75=p75, inside_iqr=bool(p25 <= c <= p75),
                     hist_values="; ".join(f"{int(y)}:{v:+.2f}" for y, v in zip(g[g.year < 2026].year, hist)))
        out.append(r)
    return df, pd.DataFrame(out)


def chg(a, b, kind):
    if kind == "logpct":
        return 100 * np.log(b / a)
    if kind == "logpct_inv":
        return -100 * np.log(b / a)   # + = BRL appreciation
    if kind == "bp100":
        return 100 * (b - a)
    return b - a


PRE_RAW, PRE = pre_election_check()

# ----------------------------------------------------------------------------- scenarios 2027-2030
def latest(sid):
    r = con.execute("SELECT date, value FROM v_observations WHERE series_id=? AND date<=current_date ORDER BY date DESC LIMIT 1", [sid]).fetchone()
    return dict(series_id=sid, date=str(r[0]), value=float(r[1]), source=META.get(sid, {}).get("source"))


SQL["latest"] = "SELECT date, value FROM v_observations WHERE series_id=? AND date<=current_date ORDER BY date DESC LIMIT 1"
START = {k: latest(k) for k in ["selic_target", "real_policy_rate", "ipca_12m", "focus_ipca_12m", "focus_selic_12m", "focus_gdp_growth",
                                 "focus_fx", "gov_real_yield_10y", "gov_nominal_yield_5y", "brl_usd", "ibovespa_usd", "ibovespa_level",
                                 "gross_public_debt_gdp", "net_public_debt_gdp", "primary_balance_gdp", "nominal_deficit_gdp",
                                 "interest_bill_gdp", "r_minus_g", "implicit_interest_rate", "nominal_gdp_growth", "unemployment_rate",
                                 "fx_reserves", "brent_usd", "credit_gdp", "wb/SI.POV.GINI.BR", "wb/SI.POV.DDAY.BR", "wb/PX.REX.REER.BR", "wb/REER_M.BRA",
                                 "wb/TOT.BRA", "oil_exports", "presalt_share", "exports_to_us", "exports_to_china", "real_average_income"]}

SCEN_OUTCOMES = [("A1", "GDP growth", "% /yr"), ("B1", "Inflation (deflator, log)", "100·log(1+π) /yr"), ("B2", "Real policy rate", "% p.a."),
                 ("C1", "Primary balance", "% GDP"), ("C2", "Δ Gross debt", "pts GDP /yr"), ("D3r", "REER change", "% /yr"),
                 ("D1", "USD equity return", "% /yr (log)"), ("D2", "BRL vs USD", "% /yr (+ = stronger)"), ("E5", "Δ Gini", "pts /yr"),
                 ("E6", "Δ Poverty $3.00", "pts /yr"), ("E1c", "Δ Unemployment", "pts /yr"), ("E3", "Real min wage growth", "% /yr"),
                 ("F1", "Infant mortality change", "% /yr"), ("F5", "Δ Homicide rate", "per 100k /yr")]
MET["D3r"] = dict(bucket="D", name="REER change", series=["wb/PX.REX.REER.BR"], s=dlog(A("wb/PX.REX.REER.BR", 1984)).loc[1985:], unit="% /yr",
                  primary=False, expL=(0, ""), expR=(0, ""))

# 4-year ΔToT distribution (annualised mean ΔlogToT over rolling 4y windows, 1986-2025)
roll4 = DLTOT.loc[1986:2025].rolling(4).mean().dropna()
TOT_PATHS = {"ToT falls (p25)": float(np.percentile(roll4, 25)), "ToT flat-ish (p50)": float(np.percentile(roll4, 50)),
             "ToT rises (p75)": float(np.percentile(roll4, 75))}
LTOT_NOW = float(LTOT.loc[2025]); LTOT_PCTL = float((LTOT.loc[1991:2025] <= LTOT_NOW).mean())


SCEN_Y0 = 1995   # post-Real-Plan mandates only: hyperinflation-era terms are not analogues for 2027-30


def scenarios():
    rows, fits = [], {}
    for mid, nm, unit in SCEN_OUTCOMES:
        for coding, branches in (("A", {"S-L Lula IV (left)": "left", "S-R Flávio Bolsonaro (right)": "right"}),
                                 ("B", {"S-C centre (coding B: FHC/Temer as centre)": "centre"})):
            # inflation: 1995 is the Real-plan transition year (deflator ~ +70%), not a regime analogue -> start 1996
            us = unit_stats(MET[mid]["s"], unit="mandate", coding=coding, min_years=2, y0=1996 if mid == "B1" else SCEN_Y0)
            if not us:
                continue
            d = pd.DataFrame([(u, l, v.mean(), MAND_TOT[u]["dltot"]) for u, (l, v) in us.items()], columns=["mandate", "lean", "y", "dtot"]).dropna()
            for br, lean in branches.items():
                h = d[d.lean == lean]
                if len(h) < 2:
                    rows.append(dict(metric_id=mid, outcome=nm, unit=unit, branch=br, n_hist=len(h), note="<2 historical mandates")); continue
                # model: y = α_lean + β·ΔToT (pooled β across all leans present)
                leans = sorted(d.lean.unique())
                X = [(d.lean == l).astype(float).values for l in leans[1:]] + [d.dtot.values]
                b, res, r2 = ols(d.y.values, X)
                beta = b[-1]
                alpha = b[0] + (b[1 + leans[1:].index(lean)] if lean in leans[1:] else 0.0)
                rsd = res.std(ddof=min(len(X) + 1, len(res) - 1)) if len(res) > len(X) + 1 else np.nan
                r = dict(metric_id=mid, outcome=nm, unit=unit, branch=br, n_hist=len(h), hist_mandates=", ".join(h.mandate),
                         hist_min=h.y.min(), hist_p25=h.y.quantile(.25), hist_median=h.y.median(), hist_p75=h.y.quantile(.75), hist_max=h.y.max(),
                         beta_tot=beta, r2=r2, n_fit=len(d), resid_sd=rsd)
                for pn, pv in TOT_PATHS.items():
                    mu = alpha + beta * pv
                    r[f"model {pn}"] = mu
                    r[f"model {pn} lo"] = mu - 1.28 * rsd if not np.isnan(rsd) else np.nan
                    r[f"model {pn} hi"] = mu + 1.28 * rsd if not np.isnan(rsd) else np.nan
                rows.append(r)
    return pd.DataFrame(rows)


SCEN = scenarios()


def debt_path(d0, rg, pb, g=START["nominal_gdp_growth"]["value"], years=4):
    g = g / 100; r = g + rg / 100; path = [d0]
    for _ in range(years):
        path.append(path[-1] * (1 + r) / (1 + g) - pb)
    return path


D0 = START["gross_public_debt_gdp"]["value"]
DEBT_GRID = pd.DataFrame([dict(r_minus_g=rg, primary_balance=pb, **{f"debt_{2026 + i}": v for i, v in enumerate(debt_path(D0, rg, pb))})
                          for rg in (2, 4, 6) for pb in (-1, 0, 1, 2)])
DEBT_GRID["current_r_minus_g"] = START["r_minus_g"]["value"]
debt_stab_pb = {rg: D0 * (rg / 100) / (1 + START["nominal_gdp_growth"]["value"] / 100) for rg in (2, 4, START["r_minus_g"]["value"], 6)}

# lean-conditional primary balance history (post-2002 mandates)
pb_m = unit_stats(MET["C1"]["s"], unit="mandate", min_years=1)
PB_HIST = {u: (l, float(v.mean())) for u, (l, v) in pb_m.items()}
pb_t = unit_stats(MET["C1"]["s"], unit="term", min_years=1)
PB_TERM = {u: (l, float(v.mean())) for u, (l, v) in pb_t.items()}

# debt/GDP 2030 by branch: primary balance from that lean's post-2002 mandate history (p25/median/p75) x r-g {4, current, 6}
pbs = pd.DataFrame([(u, l, v) for u, (l, v) in PB_HIST.items()], columns=["mandate", "lean", "pb"])
pb_annual = MET["C1"]["s"]
BOLSO_EX2020 = float(pb_annual.loc[[2019, 2021, 2022]].mean())
DEBT_BRANCH = []
for br, lean in (("S-L Lula IV (left)", "left"), ("S-R Flávio Bolsonaro (right)", "right")):
    h = pbs[pbs.lean == lean].pb
    for qn, pbv in (("pb p25", h.quantile(.25)), ("pb median", h.median()), ("pb p75", h.quantile(.75))):
        for rg in (4.0, START["r_minus_g"]["value"], 6.0):
            DEBT_BRANCH.append(dict(branch=br, pb_case=qn, primary_balance=float(pbv), r_minus_g=float(rg),
                                    debt_2030=float(debt_path(D0, rg, pbv)[-1]), hist_mandates=", ".join(pbs[pbs.lean == lean].mandate)))
DEBT_BRANCH = pd.DataFrame(DEBT_BRANCH)
# common reference: Lula III's own pb run-rate and Bolsonaro ex-2020
DEBT_REF = {f"pb={pb:.2f} ({lab}), r-g={rg:.2f}": float(debt_path(D0, rg, pb)[-1])
            for lab, pb in (("current 12m, Aug 2026", START["primary_balance_gdp"]["value"]), ("Bolsonaro ex-2020 mean", BOLSO_EX2020))
            for rg in (4.0, START["r_minus_g"]["value"], 6.0)}

# Q0 summary
def q0_summary():
    rows = []
    for mid in PRIMARY:
        for lvl in ("term", "year"):
            r = Q0[mid].get(lvl)
            if r:
                rows.append(dict(metric_id=mid, name=MET[mid]["name"], bucket=MET[mid]["bucket"], level=lvl, n=r["n"],
                                 r2_lean=r["r2_lean"], r2_tot=r["r2_tot"], r2_both=r["r2_both"], shap_lean=r["shap_lean"], shap_tot=r["shap_tot"],
                                 tot_ge_lean=bool(r["shap_tot"] >= r["shap_lean"])))
    return pd.DataFrame(rows)


Q0S = q0_summary()

# market-implied
MKT = dict(
    focus_selic_12m=START["focus_selic_12m"], focus_ipca_12m=START["focus_ipca_12m"], focus_gdp=START["focus_gdp_growth"], focus_fx=START["focus_fx"],
    ntnb10=START["gov_real_yield_10y"], ltn5=START["gov_nominal_yield_5y"],
    implied_real_policy_12m=100 * ((1 + START["focus_selic_12m"]["value"] / 100) / (1 + START["focus_ipca_12m"]["value"] / 100) - 1),
    rough_real_5y=START["gov_nominal_yield_5y"]["value"] - START["focus_ipca_12m"]["value"],
)
# market-implied r-g for debt dynamics: nominal LTN 5y as funding cost proxy vs nominal growth = Focus GDP + Focus IPCA
MKT["implied_nominal_g"] = START["focus_gdp_growth"]["value"] + START["focus_ipca_12m"]["value"]
MKT["implied_r_minus_g_ltn"] = START["gov_nominal_yield_5y"]["value"] - MKT["implied_nominal_g"]

# ----------------------------------------------------------------------------- outputs
def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) and math.isnan(o)) or (isinstance(o, np.floating) and np.isnan(o)) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return jsonable(o.tolist())
    return o


def write_outputs():
    # metric table
    rows = []
    for mid, r in RESULTS.items():
        if mid == "D3r":
            continue
        m = MET[mid]
        rows.append(dict(metric_id=mid, bucket=m["bucket"], name=m["name"], primary=m["primary"], series_ids=r["series_ids"], source=r["source"],
                         freq=r["freq"], first_year=r["first_year"], last_year=r["last_year"], last_date=r["last_date"], unit=m["unit"],
                         transform="term mean of annual values", n_left=r.get("n_left"), n_right=r.get("n_right"),
                         mean_left=r.get("mean_left"), mean_right=r.get("mean_right"), diff=r.get("diff"), diff_weighted=r.get("diff_weighted"),
                         ci80=r.get("ci80"), ci95=r.get("ci95"), perm_p=r.get("perm_p"), p_min_attainable=r.get("p_min_attainable"),
                         n_labelings=r.get("n_labelings"), bh_q=r.get("bh_q"), diff_tot_adj=r.get("diff_tot"), ci_tot_adj=r.get("ci80_tot"),
                         ci95_tot_adj=r.get("ci95_tot"), perm_p_tot=r.get("perm_p_tot"), bh_q_tot=r.get("bh_q_tot"), rank_diff=r.get("rank_diff"),
                         sign_consistency_share=r.get("sign_consistency_share"), n_cells=r.get("n_cells"),
                         q0_term_shap_lean=Q0[mid].get("term", {}).get("shap_lean"), q0_term_shap_tot=Q0[mid].get("term", {}).get("shap_tot"),
                         q0_year_shap_lean=Q0[mid].get("year", {}).get("shap_lean"), q0_year_shap_tot=Q0[mid].get("year", {}).get("shap_tot"),
                         left_narrative_expects=m["expL"][1], right_narrative_expects=m["expR"][1], verdict=r["verdict"]))
    MT = pd.DataFrame(rows)
    MT.to_csv(OUT / "metric_table.csv", index=False)
    # term table
    tt = []
    for mid, r in RESULTS.items():
        if mid == "D3r":
            continue
        for u in TERM_ORDER:
            if u in r.get("term_values", {}):
                tt.append(dict(metric_id=mid, term=u, term_id=TID[u], lean_A=LEAN_A[u], value=r["term_values"][u], n_years=r["term_nyears"][u],
                               incomplete=(u == "Lula III")))
    TT = pd.DataFrame(tt)
    # exact-date monthly anchors
    ex = q("exact_monthly_term_means", f"""WITH terms AS ({TERM_SQL})
SELECT o.series_id, t.term_id, t.term_label, round(avg(o.value), 2) AS mean_exact, count(*) AS n_months, max(o.date) AS last_obs
FROM v_observations o JOIN terms t ON o.date >= t.start AND o.date < t."end"
WHERE o.date <= current_date AND o.series_id IN ('real_policy_rate','primary_balance_gdp','ipca_12m','gross_public_debt_gdp','unemployment_rate','interest_bill_gdp')
GROUP BY 1, 2, 3 ORDER BY 1, 2""")
    TT.to_csv(OUT / "term_table.csv", index=False)
    ex.to_csv(OUT / "term_table_exact_monthly.csv", index=False)
    ROB.to_csv(OUT / "robustness_matrix.csv", index=False)
    EV.to_csv(OUT / "event_study.csv", index=False)
    EVG.to_csv(OUT / "event_study_groups.csv", index=False)
    SCEN.to_csv(OUT / "scenarios.csv", index=False)
    DEBT_GRID.to_csv(OUT / "debt_grid.csv", index=False)
    PRE.to_csv(OUT / "pre_election_2026.csv", index=False)
    DEBT_BRANCH.to_csv(OUT / "debt_by_branch.csv", index=False)
    Q0S.to_csv(OUT / "q0_variance_decomposition.csv", index=False)
    PRE_RAW.to_csv(OUT / "pre_election_raw.csv", index=False)
    res = dict(generated=dt.datetime.now(dt.timezone.utc).isoformat(), db=DB, tot_info=TOT_INFO, tot_paths=TOT_PATHS, ltot_2025=LTOT_NOW,
               ltot_2025_percentile_1991_2025=LTOT_PCTL, q0=Q0, start_adjusted=START_ADJ,
               composites={f"{k[0]}|{k[1]}": v for k, v in COMP_RES.items()}, within_president=WITHIN, mandate_tot=MAND_TOT,
               starting_conditions=START, market_implied=MKT, debt_stabilising_pb=debt_stab_pb, pb_history_mandate=PB_HIST,
               pb_history_term=PB_TERM, series_meta=META, sql=SQL, debt_ref=DEBT_REF, bolsonaro_pb_ex2020=BOLSO_EX2020,
               metrics={k: {kk: vv for kk, vv in v.items()} for k, v in RESULTS.items()},
               placebo_sd={f"{k[0]}|{k[1]}": v["placebo_sd"] for k, v in PLACEBO.items()},
               external_fenced=dict(note="NOT in warehouse; user-supplied external fact",
                                    first_round_2026_10_04={"Flávio Bolsonaro (PL, right)": 47.0, "Lula (PT, left)": 44.9},
                                    runoff="2026-10-25",
                                    sources=["https://www.cnn.com/2026/10/04/americas/brazil-president-elections-2026-latam-intl",
                                             "https://www.washingtonpost.com/world/2026/10/04/bolsonaro-lula-head-runoff-5-takeaways-brazils-election/"]))
    (OUT / "results.json").write_text(json.dumps(jsonable(res), indent=1, ensure_ascii=False, default=str))
    return MT, TT


MT, TT = write_outputs()

if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 30)
    cols = ["metric_id", "name", "n_left", "n_right", "mean_left", "mean_right", "diff", "ci80", "perm_p", "p_min_attainable", "bh_q",
            "diff_tot_adj", "ci_tot_adj", "sign_consistency_share", "q0_term_shap_lean", "q0_term_shap_tot", "verdict"]
    print(MT[MT.primary][cols].round(3).to_string())
    print(MT[~MT.primary][["metric_id", "name", "n_left", "n_right", "diff", "ci80", "perm_p", "diff_tot_adj"]].round(3).to_string())
    for k, v in COMP_RES.items():
        print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "by_term"})
    print(json.dumps(jsonable(START_ADJ), default=str)[:3000])
