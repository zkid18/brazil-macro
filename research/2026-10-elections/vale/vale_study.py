"""Vale and Brazilian politics: returns by term, event study, fundamentals, Petrobras contrast.

Inputs
  warehouse/brazil_macro.duckdb (read-only): total_return_usd@VALE/@IBOV/@PETR, brl_usd, v_company_quarterly,
    iron_ore_exports(_kg), iron_ore_unit_value, exports_to_china, china_export_share, dividend_yield_ttm@VALE, wb/TOT.BRA
  data/ (fetch_external.py): Yahoo adjusted closes VALE PBR BHP RIO EWZ SPY XOM; FRED PIORECRUSDM, POILBREUSDM
Pre-registration: preregistration.txt (terms, models, events, tests fixed before running this).
"""
import json, itertools
import numpy as np, pandas as pd, duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

H = Path(__file__).parent
D = H / "data"
DB = H.parents[2] / "warehouse" / "brazil_macro.duckdb"
TODAY = pd.Timestamp("2026-10-10")
con = duckdb.connect(str(DB), read_only=True)

TERMS = [("FHC (Apr-Dec 2002)", "right", "2002-04", "2002-12"),
         ("Lula I-II", "left", "2003-01", "2010-12"), ("Dilma", "left", "2011-01", "2016-08"),
         ("Temer", "right", "2016-09", "2018-12"), ("Bolsonaro", "right", "2019-01", "2022-12"),
         ("Lula III", "left", "2023-01", "2026-09")]
FULL = [t for t in TERMS if not t[0].startswith("FHC")]
LEAN = {t[0]: t[1] for t in TERMS}
OUT = {"meta": {"generated": str(TODAY.date()), "prereg": "preregistration.txt"}}


def term_of(d):
    for n, l, a, b in TERMS:
        if pd.Timestamp(a) <= d <= pd.Timestamp(b) + pd.offsets.MonthEnd(0):
            return n
    return None


def wh(sid):
    df = con.sql(f"select date, value from v_observations where series_id='{sid}' and date <= current_date order by date").df()
    df["date"] = pd.to_datetime(df.date)
    return df.set_index("date").value


def wh_meta(sid):
    r = con.sql(f"select source, max(date) from v_observations where series_id='{sid}' and date<=current_date group by source").fetchone()
    return {"series_id": sid, "source": r[0], "last_date": str(r[1])[:10]}


SOURCES = {}
# ---------------------------------------------------------------- load
px = {}
for t in ["VALE", "PBR", "BHP", "RIO", "EWZ", "SPY", "XOM"]:
    s = pd.read_csv(D / f"yahoo_{t}.csv", parse_dates=["date"]).set_index("date").adjclose
    px[t] = s[~s.index.duplicated()]
px = pd.DataFrame(px)
ysrc = json.load(open(D / "sources.json"))
for t in px:
    SOURCES[f"yahoo:{t}"] = {"series_id": f"yahoo:{t} adjclose (USD, dividends reinvested)", "source": "Yahoo Finance",
                             "last_date": str(px[t].dropna().index.max().date()), "url": ysrc[t]}
fred = {}
for s in ["PIORECRUSDM", "POILBREUSDM"]:
    f = pd.read_csv(D / f"fred_{s}.csv", parse_dates=["observation_date"]).set_index("observation_date").iloc[:, 0]
    fred[s] = f
    SOURCES[f"fred:{s}"] = {"series_id": f"fred:{s}", "source": "IMF via FRED", "last_date": str(f.index.max().date()), "url": ysrc[s]}
iron = fred["PIORECRUSDM"]; brent = fred["POILBREUSDM"]

# monthly log returns (month-end adjclose), months labelled by month start
me = px.resample("ME").last()
me.index = me.index.to_period("M").to_timestamp()
rm = np.log(me).diff()
rm["MIN"] = rm[["BHP", "RIO"]].mean(axis=1)
rm["IRON"] = np.log(iron).diff()
rm["BRENT"] = np.log(brent).diff()
rm = rm.loc["2002-04":"2026-09"]
rm["term"] = [term_of(d) for d in rm.index]
rm["lean"] = rm.term.map(LEAN)

# cross-check Yahoo VALE vs warehouse total_return_usd@VALE
w_vale = wh("total_return_usd@VALE"); w_ibov = wh("total_return_usd@IBOV"); w_petr = wh("total_return_usd@PETR")
for sid in ["total_return_usd@VALE", "total_return_usd@IBOV", "total_return_usd@PETR", "brl_usd", "dividend_yield_ttm@VALE",
            "iron_ore_exports_kg", "iron_ore_exports", "iron_ore_unit_value", "exports_to_china", "china_export_share", "wb/TOT.BRA",
            "share_close_adj_brl@VALE"]:
    SOURCES[sid] = wh_meta(sid)
SOURCES["v_company_quarterly@VALE"] = {"series_id": "v_company_quarterly (VALE, PETR)", "source": "CVM",
                                       "last_date": str(con.sql("select max(quarter_end) from v_company_quarterly where company ilike '%vale%'").fetchone()[0])}


def wm(s):
    s = s.copy(); s.index = s.index.to_period("M").to_timestamp(); s = s[~s.index.duplicated(keep="last")]
    return np.log(s).diff()


chk = pd.concat([rm.VALE, wm(w_vale).rename("WH")], axis=1).dropna()
OUT["crosscheck"] = {"corr_yahoo_VALE_vs_total_return_usd@VALE_monthly": round(chk.corr().iloc[0, 1], 3), "n_months": len(chk),
                     "mean_diff_pp_per_yr": round((chk.VALE - chk.WH).mean() * 1200, 2)}


# ---------------------------------------------------------------- Q1 factor models
def ols(y, X):
    X = np.column_stack([np.ones(len(X)), X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    return b, e, 1 - e.var() / y.var()


MODELS = {"iron_only": ["IRON"], "iron_miners": ["IRON", "MIN"], "miners_only": ["MIN"], "ewz_only": ["EWZ"],
          "iron_miners_ewz": ["IRON", "MIN", "EWZ"]}
PMODELS = {"brent_only": ["BRENT"], "brent_xom": ["BRENT", "XOM"], "brent_xom_ewz": ["BRENT", "XOM", "EWZ"], "ewz_only": ["EWZ"]}


def fit(asset, cols, df):
    d = df.dropna(subset=[asset] + cols)
    b, e, r2 = ols(d[asset].values, d[cols].values)
    resid = pd.Series(e + b[0], index=d.index)  # keep intercept: alpha = a + e
    return {"beta": dict(zip(["const"] + cols, np.round(b, 4))), "r2": round(r2, 3), "n": len(d)}, resid


def block_boot_gap(x, lab, B=5000, block=12, seed=42):
    """x: residual series; lab: 'left'/'right'. Returns observed gap (ann. pp), null p (labels fixed, residuals block-resampled
    circularly) and 90% CI (pairs resampled in moving blocks)."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x); L = np.asarray(lab) == "left"; R = np.asarray(lab) == "right"; n = len(x)
    obs = (x[L].mean() - x[R].mean()) * 1200
    nb = int(np.ceil(n / block)); null = np.empty(B); ci = np.empty(B)
    for i in range(B):
        st = rng.integers(0, n, nb)
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        xs = x[idx]
        null[i] = (xs[L].mean() - xs[R].mean()) * 1200
        Ls, Rs = L[idx], R[idx]
        ci[i] = (xs[Ls].mean() - xs[Rs].mean()) * 1200 if Rs.any() and Ls.any() else np.nan
    return {"gap_left_minus_right_pp_yr": round(obs, 2), "p_block_null": round(float(np.mean(np.abs(null) >= abs(obs))), 3),
            "ci90": [round(float(np.nanpercentile(ci, 5)), 2), round(float(np.nanpercentile(ci, 95)), 2)]}


def perm_terms(x, terms):
    names = [t[0] for t in FULL]
    obs_right = {"Temer", "Bolsonaro"}
    def stat(right):
        m = pd.Series(np.asarray(x), index=terms)
        lab = np.where(pd.Series(terms).isin(right), "right", np.where(pd.Series(terms).isin(names), "left", "x"))
        return (m.values[lab == "left"].mean() - m.values[lab == "right"].mean()) * 1200
    obs = stat(obs_right)
    allc = [stat(set(c)) for c in itertools.combinations(names, 2)]
    return {"gap": round(obs, 2), "perm_p_two_sided": round(np.mean(np.abs(allc) >= abs(obs) - 1e-9), 2), "n_perms": len(allc),
            "rank_of_observed_low_to_high": int(sorted(allc).index(min(allc, key=lambda v: abs(v - obs)))) + 1}


q1 = {"models": {}, "terms": [], "tests": {}}
resids = {}
for name, cols in MODELS.items():
    info, res = fit("VALE", cols, rm); q1["models"][name] = info; resids[name] = res
for name, cols in PMODELS.items():
    info, res = fit("PBR", cols, rm); q1["models"]["PBR_" + name] = info; resids["PBR_" + name] = res
# robustness: 2012+ betas, iron ore lead/lag
rm2 = rm.loc["2012-01":]
q1["models"]["iron_miners_2012plus"] = fit("VALE", ["IRON", "MIN"], rm2)[0]
rmL = rm.copy(); rmL["IRON_lead"] = rmL.IRON.shift(-1); rmL["IRON_lag"] = rmL.IRON.shift(1)
q1["models"]["iron_leadlag_miners"], resids["iron_leadlag_miners"] = fit("VALE", ["IRON", "IRON_lead", "IRON_lag", "MIN"], rmL)

rows = []
for n, l, a, b in TERMS:
    s = rm.loc[a:b]
    r = {"term": n, "lean": l, "months": len(s)}
    for t in ["VALE", "EWZ", "PBR", "MIN", "SPY"]:
        r[f"{t}_ann_pct"] = round((np.exp(s[t].mean() * 12) - 1) * 100, 1)
    ir = s.IRON.dropna()
    r["iron_ore_ann_pct"] = round((np.exp(ir.mean() * 12) - 1) * 100, 1)
    r["iron_ore_avg_usd_t"] = round(iron.loc[a:b].mean(), 1)
    r["VALE_minus_EWZ_pp"] = round((s.VALE - s.EWZ).mean() * 1200, 1)
    for m in ["iron_only", "iron_miners", "ewz_only", "iron_miners_ewz"]:
        r[f"alpha_{m}_pp_yr"] = round(resids[m].loc[a:b].mean() * 1200, 1)
    for m in ["brent_xom", "ewz_only"]:
        r[f"PBR_alpha_{m}_pp_yr"] = round(resids["PBR_" + m].loc[a:b].mean() * 1200, 1)
    # warehouse (2012+) Vale vs Ibovespa total return in USD
    wv = wm(w_vale).loc[a:b].dropna(); wi = wm(w_ibov).loc[a:b].dropna()
    j = pd.concat([wv, wi], axis=1).dropna()
    r["WH_VALE_minus_IBOV_pp_2012plus"] = round((j.iloc[:, 0] - j.iloc[:, 1]).mean() * 1200, 1) if len(j) >= 6 else None
    r["WH_months"] = len(j)
    rows.append(r)
T1 = pd.DataFrame(rows)
T1.to_csv(H / "term_returns.csv", index=False)
q1["terms"] = rows

full = rm.loc["2003-01":"2026-09"]
for m in ["iron_only", "iron_miners", "ewz_only", "iron_miners_ewz", "iron_leadlag_miners", "PBR_brent_xom", "PBR_ewz_only"]:
    x = resids[m].reindex(full.index).dropna()
    lab = full.lean.reindex(x.index)
    q1["tests"][m] = block_boot_gap(x.values, lab.values)
    q1["tests"][m].update({"perm": perm_terms(x.values, full.term.reindex(x.index).values)})
# raw relative returns
for nm, ser in {"VALE_minus_EWZ": full.VALE - full.EWZ, "VALE_raw": full.VALE, "EWZ_raw": full.EWZ, "PBR_minus_EWZ": full.PBR - full.EWZ}.items():
    q1["tests"][nm] = block_boot_gap(ser.values, full.lean.values)
    q1["tests"][nm].update({"perm": perm_terms(ser.values, full.term.values)})
# EXPLORATORY (not pre-registered): drop the two dam-collapse months (Nov-2015 Mariana, Jan-2019 Brumadinho)
x = resids["iron_miners"].reindex(full.index).dropna()
x = x.drop([pd.Timestamp("2015-11-01"), pd.Timestamp("2019-01-01")], errors="ignore")
q1["tests"]["EXPLORATORY_iron_miners_ex_disaster_months"] = block_boot_gap(x.values, full.lean.reindex(x.index).values)
q1["EXPLORATORY_term_alpha_ex_disasters"] = {n: round(x.loc[a:b].mean() * 1200, 1) for n, l, a, b in FULL}
OUT["Q1_returns_by_term"] = q1

# ---------------------------------------------------------------- Q2 event study (daily)
rd = np.log(px).diff()
rd["MIN"] = rd[["BHP", "RIO"]].mean(axis=1)
rd = rd.loc["2002-03-22":]
EVENTS = [  # (id, date, label, kind, lean_of_winner)
    ("R2002", "2002-10-27", "2002 run-off: Lula wins", "election", "left"),
    ("R2006", "2006-10-29", "2006 run-off: Lula re-elected", "election", "left"),
    ("R2010", "2010-10-31", "2010 run-off: Dilma wins", "election", "left"),
    ("R2014", "2014-10-26", "2014 run-off: Dilma re-elected", "election", "left"),
    ("R2018", "2018-10-28", "2018 run-off: Bolsonaro wins", "election", "right"),
    ("R2022", "2022-10-30", "2022 run-off: Lula wins", "election", "left"),
    ("F2026", "2026-10-04", "2026 first round: Flávio 47.0 vs Lula 45.2", "election", "right"),
    ("E1", "2011-04-01", "Agnelli ouster agreed (gov't pressure)", "interference", None),
    ("E2", "2024-01-20", "Bloomberg: Lula pushes Mantega for CEO", "interference", None),
    ("E3", "2024-03-11", "Bartolomeo extended / Penido resigns", "interference", None),
    ("E4", "2024-08-26", "Pimenta named CEO (not gov't pick)", "governance_positive", None),
    ("E5", "2024-10-25", "Mariana R$170bn settlement signed", "settlement", None),
    ("X1", "2015-11-05", "Mariana dam collapse (benchmark)", "disaster", None),
    ("X2", "2019-01-25", "Brumadinho dam collapse (benchmark)", "disaster", None),
]
WIN = {"CAR_0_1": (0, 1), "CAR_0_4": (0, 4), "CAR_m20_m1": (-20, -1), "CAR_m5_5": (-5, 4)}
EMODELS = {"VALE": {"M2_miners_ewz": ["MIN", "EWZ"], "M1_miners_spy": ["MIN", "SPY"]},
           "PBR": {"M2_xom_ewz": ["XOM", "EWZ"], "M1_xom_spy": ["XOM", "SPY"]},
           "EWZ": {"M1_spy": ["SPY"]}}
dates = rd.index


def car(asset, cols, d0, windows=WIN):
    i0 = dates.searchsorted(pd.Timestamp(d0))
    if i0 >= len(dates) or i0 < 130:
        return None
    # pre-registered window [-260,-30]; deviation: R2002 uses the ~150 days available since the VALE ADR listed (Mar 2002)
    est = rd.iloc[max(0, i0 - 260):i0 - 30][[asset] + cols].dropna()
    b, e, _ = ols(est[asset].values, est[cols].values)
    sd = e.std(ddof=len(cols) + 1)
    out = {"day0": str(dates[i0].date())}
    for k, (a, z) in windows.items():
        if i0 + z >= len(dates):
            z = len(dates) - 1 - i0
            out[k + "_truncated_to"] = int(z)
        w = rd.iloc[i0 + a:i0 + z + 1][[asset] + cols].dropna()
        ar = w[asset].values - (b[0] + w[cols].values @ b[1:])
        out[k] = round(ar.sum() * 100, 2)
        out[k + "_t"] = round(ar.sum() / (sd * np.sqrt(len(ar))), 2)
        out[k + "_raw"] = round(w[asset].sum() * 100, 2)
    return out


ev_rows = []
for eid, d, lab, kind, lean in EVENTS:
    for asset, ms in EMODELS.items():
        for mname, cols in ms.items():
            c = car(asset, cols, d)
            if c is None:
                continue
            ev_rows.append({"event": eid, "date": d, "label": lab, "kind": kind, "winner_lean": lean, "asset": asset, "model": mname, **c})
EV = pd.DataFrame(ev_rows)
EV.to_csv(H / "event_study.csv", index=False)

# placebo distribution (VALE M2, PBR M2, VALE M1)
rng = np.random.default_rng(7)
ev_idx = [dates.searchsorted(pd.Timestamp(e[1])) for e in EVENTS]
cand = [i for i in range(300, len(dates) - 6) if dates[i] >= pd.Timestamp("2003-01-01") and all(abs(i - j) > 10 for j in ev_idx)]
pl_days = rng.choice(cand, 1000, replace=False)
PL = {}
for asset, mname, cols in [("VALE", "M2_miners_ewz", ["MIN", "EWZ"]), ("VALE", "M1_miners_spy", ["MIN", "SPY"]), ("PBR", "M2_xom_ewz", ["XOM", "EWZ"]),
                           ("EWZ", "M1_spy", ["SPY"])]:
    vals = [car(asset, cols, dates[i], {"CAR_0_1": (0, 1), "CAR_0_4": (0, 4)}) for i in pl_days]
    PL[(asset, mname)] = pd.DataFrame([{k: v[k] for k in ["CAR_0_1", "CAR_0_4"]} for v in vals if v])


def pctile(asset, mname, k, v):
    return round(float((PL[(asset, mname)][k] < v).mean() * 100), 1)


EV["pctile_vs_placebo_CAR_0_1"] = [pctile(r.asset, r.model, "CAR_0_1", r.CAR_0_1) if (r.asset, r.model) in PL else None for r in EV.itertuples()]
EV.to_csv(H / "event_study.csv", index=False)
q2 = {"placebo": {f"{a}|{m}": {"CAR_0_1_sd": round(df.CAR_0_1.std(), 2), "CAR_0_1_p5_p95": [round(df.CAR_0_1.quantile(.05), 2), round(df.CAR_0_1.quantile(.95), 2)],
                               "n": len(df)} for (a, m), df in PL.items()}}
v2 = EV[(EV.asset == "VALE") & (EV.model == "M2_miners_ewz")].set_index("event")
v1 = EV[(EV.asset == "VALE") & (EV.model == "M1_miners_spy")].set_index("event")
p2 = EV[(EV.asset == "PBR") & (EV.model == "M2_xom_ewz")].set_index("event")
e1 = EV[(EV.asset == "EWZ")].set_index("event")
left_wins = ["R2002", "R2006", "R2010", "R2014", "R2022"]
interf = ["E1", "E2", "E3"]


def placebo_mean_p(asset, mname, k, ids, obs):
    """share of placebo draws of a mean of len(ids) random CARs that is <= observed (one-sided low) """
    d = PL[(asset, mname)][k].values
    sims = rng.choice(d, (5000, len(ids))).mean(axis=1)
    return round(float((sims <= obs).mean()), 3)


for nm, tab, a, m in [("VALE_vs_miners_EWZ", v2, "VALE", "M2_miners_ewz"), ("VALE_vs_miners_SPY", v1, "VALE", "M1_miners_spy"),
                      ("PBR_vs_XOM_EWZ", p2, "PBR", "M2_xom_ewz"), ("EWZ_vs_SPY", e1, "EWZ", "M1_spy")]:
    lw = tab.loc[left_wins, "CAR_0_1"].mean()
    q2[nm] = {"mean_CAR01_left_wins": round(lw, 2), "CAR01_2018_right_win": tab.loc["R2018", "CAR_0_1"],
              "CAR01_2026_first_round": tab.loc["F2026", "CAR_0_1"], "CAR04_2026_first_round": tab.loc["F2026", "CAR_0_4"],
              "p_left_wins_mean_this_low_vs_placebo": placebo_mean_p(a, m, "CAR_0_1", left_wins, lw)}
    if a == "VALE":
        im = tab.loc[interf, "CAR_0_1"].mean()
        q2[nm].update({"mean_CAR01_interference_E1_E3": round(im, 2),
                       "p_interference_mean_this_low_vs_placebo": placebo_mean_p(a, m, "CAR_0_1", interf, im),
                       "E1_Agnelli_CAR_m20_m1": tab.loc["E1", "CAR_m20_m1"], "E1_Agnelli_CAR_m5_5": tab.loc["E1", "CAR_m5_5"]})
OUT["Q2_event_study"] = q2

# ---------------------------------------------------------------- Q3 fundamentals
cq = con.sql("select * from v_company_quarterly where entity_id in ('VALE','PETR') or company ilike '%vale%' or company ilike '%petro%' order by quarter_end").df()
cq["quarter_end"] = pd.to_datetime(cq.quarter_end)
fx = wh("brl_usd")
fxq = fx.resample("QE").mean()
cq["fx"] = cq.quarter_end.map(lambda d: fxq.asof(d))
cq["co"] = np.where(cq.company.str.contains("Vale", case=False), "VALE", "PETR")
for c in ["revenue_brl", "ebit_brl", "net_income_brl", "capex_brl", "dividends_paid_brl"]:
    cq[c.replace("_brl", "_usd_bn")] = cq[c] / cq.fx  # CVM values are R$ bn
cq["net_debt_usd_bn"] = cq.net_debt_brl_bn / cq.fx
cq["year"] = cq.quarter_end.dt.year
ann = cq.groupby(["co", "year"]).agg(q=("quarter_end", "count"), revenue=("revenue_usd_bn", "sum"), ebit=("ebit_usd_bn", "sum"),
                                     ni=("net_income_usd_bn", "sum"), capex=("capex_usd_bn", "sum"), div=("dividends_paid_usd_bn", "sum"),
                                     net_debt=("net_debt_usd_bn", "last")).reset_index()
# sign conventions: CVM cash-flow lines are negative outflows
for c in ["capex", "div"]:
    ann[c] = ann[c].abs()
ann["ebit_margin_pct"] = ann.ebit / ann.revenue * 100
ann["payout_pct"] = ann["div"] / ann.ni.where(ann.ni > 0) * 100
ann["div_over_ebit_pct"] = ann["div"] / ann.ebit.where(ann.ebit > 0) * 100
ann["capex_over_rev_pct"] = ann.capex / ann.revenue * 100
ann["nd_over_ebit"] = ann.net_debt / ann.ebit.where(ann.ebit > 0)
ann["iron_usd_t"] = ann.year.map(iron.groupby(iron.index.year).mean())
ann["brent_usd_bbl"] = ann.year.map(brent.groupby(brent.index.year).mean())
# Brazil iron ore export volume (ComexStat; Vale is the dominant exporter)
kg = wh("iron_ore_exports_kg"); ann["br_iron_exports_mt"] = ann.year.map(kg.groupby(kg.index.year).sum() / 1e3)  # thousand tonnes -> Mt
ann.loc[ann.year >= 2026, "br_iron_exports_mt"] = np.nan  # partial year
YEAR_TERM = {**{y: "Dilma" for y in range(2012, 2017)}, 2017: "Temer", 2018: "Temer", **{y: "Bolsonaro" for y in range(2019, 2023)},
             **{y: "Lula III" for y in range(2023, 2027)}}
ann["term"] = ann.year.map(YEAR_TERM); ann["lean"] = ann.term.map(LEAN)
annV = ann[ann.co == "VALE"].copy()
annV = annV[annV.year <= 2025]  # full years for regressions; 2026 H1 reported separately
q3 = {"annual": [], "term_means": [], "iron_regressions": {}}
for c in ["div", "capex", "ebit_margin_pct", "payout_pct", "capex_over_rev_pct", "nd_over_ebit", "net_debt", "br_iron_exports_mt", "div_over_ebit_pct"]:
    d = annV.dropna(subset=[c, "iron_usd_t"])
    b, e, r2 = ols(d[c].values, d[["iron_usd_t"]].values)
    d = d.assign(res=e)
    tm = d.groupby("term").res.mean()
    gap = d[d.lean == "left"].res.mean() - d[d.lean == "right"].res.mean()
    q3["iron_regressions"][c] = {"slope_per_usd10_iron": round(b[1] * 10, 3), "r2": round(r2, 2), "n_years": len(d),
                                 "resid_by_term": tm.round(2).to_dict(), "left_minus_right_resid": round(gap, 2),
                                 "resid_sd": round(e.std(), 2)}
annV.round(3).to_csv(H / "fundamentals_annual.csv", index=False)
q3["annual"] = annV.round(2).to_dict("records")
tmeans = annV.groupby("term")[["iron_usd_t", "div", "capex", "ebit_margin_pct", "payout_pct", "capex_over_rev_pct", "nd_over_ebit", "br_iron_exports_mt"]].mean().round(2)
tmeans = tmeans.reindex(["Dilma", "Temer", "Bolsonaro", "Lula III"])
tmeans.to_csv(H / "fundamentals_by_term.csv")
q3["term_means"] = tmeans.reset_index().to_dict("records")
h1 = cq[(cq.co == "VALE") & (cq.year == 2026)]
q3["vale_2026_H1"] = {"quarters": len(h1), "div_usd_bn": round(h1.dividends_paid_usd_bn.abs().sum(), 2), "capex_usd_bn": round(h1.capex_usd_bn.abs().sum(), 2),
                      "net_income_usd_bn": round(h1.net_income_usd_bn.sum(), 2), "net_debt_usd_bn_end": round(h1.net_debt_usd_bn.iloc[-1], 2) if len(h1) else None}
dy = wh("dividend_yield_ttm@VALE")
q3["dividend_yield_ttm_by_term_pct"] = {n: round(dy.loc[a:b].mean() * (100 if dy.max() < 1 else 1), 2) for n, l, a, b in TERMS if len(dy.loc[a:b])}
q3["dividend_yield_ttm_latest"] = {"value": round(float(dy.iloc[-1]), 4), "date": str(dy.index[-1].date())}
OUT["Q3_fundamentals"] = q3

# ---------------------------------------------------------------- Q4 Petrobras contrast + variance decomposition
q4 = {}
def r2(asset, cols, df=rm):
    d = df.dropna(subset=[asset] + cols); return ols(d[asset].values, d[cols].values)[2]
for asset, glob in [("VALE", ["IRON", "MIN"]), ("PBR", ["BRENT", "XOM"])]:
    g = r2(asset, glob); gb = r2(asset, glob + ["EWZ"]); e_ = r2(asset, ["EWZ"])
    # Brazil factor orthogonal to global commodities+SPY
    dd = rm.dropna(subset=["EWZ", "SPY", "IRON", "BRENT", "MIN", "XOM", asset]).copy()
    _, eb, _ = ols(dd.EWZ.values, dd[["SPY", "IRON", "BRENT"]].values); dd["BRZ"] = eb
    gpure = r2(asset, glob + ["SPY"], dd); gpb = r2(asset, glob + ["SPY", "BRZ"], dd)
    q4[asset] = {"r2_global_commodity": round(g, 3), "r2_global_plus_EWZ": round(gb, 3), "r2_EWZ_only": round(e_, 3),
                 "r2_global_plus_SPY": round(gpure, 3), "incremental_r2_pure_Brazil_factor": round(gpb - gpure, 3)}
    # beta to pure Brazil factor
    b, _, _ = ols(dd[asset].values, dd[glob + ["SPY", "BRZ"]].values)
    q4[asset]["beta_pure_Brazil_factor"] = round(b[-1], 2)
q4["gap_compare_pp_yr"] = {"VALE_iron_miners": q1["tests"]["iron_miners"]["gap_left_minus_right_pp_yr"],
                           "PBR_brent_xom": q1["tests"]["PBR_brent_xom"]["gap_left_minus_right_pp_yr"],
                           "VALE_minus_EWZ_raw": q1["tests"]["VALE_minus_EWZ"]["gap_left_minus_right_pp_yr"],
                           "PBR_minus_EWZ_raw": q1["tests"]["PBR_minus_EWZ"]["gap_left_minus_right_pp_yr"],
                           "EWZ_raw": q1["tests"]["EWZ_raw"]["gap_left_minus_right_pp_yr"]}
# Political-risk premium proxy: rolling 24m beta of Vale to pure Brazil factor, by term
dd = rm.dropna(subset=["EWZ", "SPY", "IRON", "BRENT", "MIN", "VALE"]).copy()
_, eb, _ = ols(dd.EWZ.values, dd[["SPY", "IRON", "BRENT"]].values); dd["BRZ"] = eb
q4["VALE_beta_to_pure_Brazil_factor_by_term"] = {}
for n, l, a, b_ in TERMS:
    s = dd.loc[a:b_]
    if len(s) > 18:
        bb, _, _ = ols(s.VALE.values, s[["IRON", "MIN", "SPY", "BRZ"]].values)
        bp, _, _ = ols(s.PBR.values, s[["BRENT", "XOM", "SPY", "BRZ"]].values)
        q4["VALE_beta_to_pure_Brazil_factor_by_term"][n] = {"VALE": round(bb[-1], 2), "PBR": round(bp[-1], 2), "months": len(s)}
# what share of Vale's cumulative USD return per term is explained by the factor model
OUT["Q4_petrobras_contrast"] = q4

# ---------------------------------------------------------------- latest context (for scenarios)
ctx = {"iron_ore_latest": {"value": round(iron.iloc[-1], 1), "date": str(iron.index[-1].date()), "series": "fred:PIORECRUSDM"},
       "iron_ore_2025_avg": round(iron.loc["2025"].mean(), 1), "iron_ore_2021_peak_month": round(iron.loc["2021"].max(), 1),
       "brl_usd_latest": {"value": round(fx.iloc[-1], 4), "date": str(fx.index[-1].date())},
       "VALE_adr_ytd_2026_pct": round((px.VALE.dropna().iloc[-1] / px.VALE.loc[:"2025-12-31"].dropna().iloc[-1] - 1) * 100, 1),
       "EWZ_ytd_2026_pct": round((px.EWZ.dropna().iloc[-1] / px.EWZ.loc[:"2025-12-31"].dropna().iloc[-1] - 1) * 100, 1),
       "VALE_adr_last": {"value": round(px.VALE.dropna().iloc[-1], 2), "date": str(px.VALE.dropna().index[-1].date())}}
ue = wh("iron_ore_unit_value"); ctx["iron_ore_export_unit_value_latest"] = {"value": round(ue.iloc[-1], 1), "date": str(ue.index[-1].date())}
ce = wh("china_export_share"); ctx["china_export_share_latest"] = {"value": round(ce.iloc[-1], 1), "date": str(ce.index[-1].date()),
                                                                   "avg_2025": round(ce.loc["2025"].mean(), 1)}
ie = wh("iron_ore_exports"); ctx["iron_ore_exports_usd_bn_2025"] = round(ie.loc["2025"].sum() / 1e9, 2)
ctx["iron_ore_exports_usd_bn_2026_jan_aug"] = round(ie.loc["2026"].sum() / 1e9, 2)
ctx["iron_ore_exports_usd_bn_2025_jan_aug"] = round(ie.loc["2025-01":"2025-08"].sum() / 1e9, 2)
kg26 = kg.loc["2026"].sum() / 1e3; kg25 = kg.loc["2025-01":"2025-08"].sum() / 1e3
ctx["iron_ore_exports_mt_2026_jan_aug_vs_2025"] = [round(kg26, 1), round(kg25, 1)]
# sensitivity: implied Vale move from iron ore move
ctx["vale_beta_iron_monthly"] = q1["models"]["iron_only"]["beta"]["IRON"]
# annual-frequency check (2003-2025): Vale vs iron ore average price change, miners and EWZ
ya = np.log(px.resample("YE").last()).diff().loc["2003":"2025"]
ya["IRON"] = np.log(iron.resample("YE").mean()).diff().loc["2003":"2025"]
ya["MIN"] = ya[["BHP", "RIO"]].mean(axis=1)
ctx["annual_2003_2025"] = {"corr_VALE_IRON": round(ya.VALE.corr(ya.IRON), 2), "corr_VALE_MIN": round(ya.VALE.corr(ya.MIN), 2),
                           "corr_VALE_EWZ": round(ya.VALE.corr(ya.EWZ), 2), "corr_PBR_EWZ": round(ya.PBR.corr(ya.EWZ), 2),
                           "r2_VALE_on_IRON": round(fit("VALE", ["IRON"], ya)[0]["r2"], 3), "r2_VALE_on_MIN": round(fit("VALE", ["MIN"], ya)[0]["r2"], 3)}
OUT["context"] = ctx
OUT["sources"] = SOURCES
json.dump(OUT, open(H / "results.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))

# ---------------------------------------------------------------- charts
SH = {"left": "rgba(200,60,60,0.08)", "right": "rgba(40,90,200,0.08)"}
def shade(fig, row=None, col=None):
    for n, l, a, b in TERMS:
        kw = dict(x0=a + "-01", x1=str((pd.Timestamp(b) + pd.offsets.MonthEnd(0)).date()), fillcolor=SH[l], line_width=0, layer="below")
        if row:
            fig.add_vrect(row=row, col=col, **kw)
        else:
            fig.add_vrect(annotation_text=n.split(" (")[0], annotation_position="top left", annotation_font_size=10, **kw)

cum = np.exp(rm[["VALE", "EWZ", "PBR"]].fillna(0).cumsum()) * 100
ir_idx = iron.loc["2002-03":] / iron.loc["2002-03"].iloc[0] * 100
fig = go.Figure()
for c, col in [("VALE", "#1b7f5a"), ("EWZ", "#888"), ("PBR", "#d08a00")]:
    fig.add_scatter(x=cum.index, y=cum[c], name={"VALE": "Vale ADR total return", "EWZ": "MSCI Brazil (EWZ) total return", "PBR": "Petrobras ADR total return"}[c], line_color=col)
fig.add_scatter(x=ir_idx.index, y=ir_idx, name="Iron ore price (IMF CFR China)", line=dict(color="#7b3f00", dash="dot"))
shade(fig)
fig.update_layout(title="Vale tracks iron ore, not the president (USD, Mar-2002 = 100, log scale; red = left, blue = right)",
                  yaxis_type="log", template="plotly_white", legend=dict(orientation="h", y=-0.15))
fig.write_html(H / "charts/vale_vs_iron_ore_by_term.html", include_plotlyjs="cdn")

fig = go.Figure()
tt = T1[T1.term != "FHC (Apr-Dec 2002)"]
fig.add_bar(x=tt.term, y=tt["VALE_ann_pct"], name="Vale raw USD return %/yr", marker_color="#9ccfb8")
fig.add_bar(x=tt.term, y=tt["alpha_iron_miners_pp_yr"], name="Vale alpha after iron ore + miners (pp/yr)", marker_color="#1b7f5a")
fig.add_bar(x=tt.term, y=tt["PBR_alpha_brent_xom_pp_yr"], name="Petrobras alpha after Brent + XOM (pp/yr)", marker_color="#d08a00")
fig.add_bar(x=tt.term, y=tt["iron_ore_ann_pct"], name="Iron ore %/yr", marker_color="#7b3f00")
fig.update_layout(barmode="group", template="plotly_white", title="Returns by presidential term: raw vs factor-adjusted (USD)",
                  yaxis_title="% or pp per year", legend=dict(orientation="h", y=-0.2))
fig.write_html(H / "charts/term_alphas_vale_vs_petrobras.html", include_plotlyjs="cdn")

ee = EV[EV.model.isin(["M2_miners_ewz", "M2_xom_ewz", "M1_spy"])]
fig = go.Figure()
for a, col in [("VALE", "#1b7f5a"), ("PBR", "#d08a00"), ("EWZ", "#888")]:
    s = ee[ee.asset == a]
    fig.add_bar(x=s.event + " " + s.label.str.slice(0, 32), y=s.CAR_0_1, name={"VALE": "Vale vs miners+EWZ", "PBR": "Petrobras vs XOM+EWZ", "EWZ": "Brazil (EWZ) vs S&P 500"}[a], marker_color=col)
sd = q2["placebo"]["VALE|M2_miners_ewz"]["CAR_0_1_p5_p95"]
fig.add_hrect(y0=sd[0], y1=sd[1], fillcolor="rgba(27,127,90,0.08)", line_width=0, annotation_text="Vale placebo 5-95%")
fig.update_layout(barmode="group", template="plotly_white", title="Two-day abnormal returns CAR[0,+1] around elections and Vale governance events (%)",
                  yaxis_title="%", xaxis_tickangle=-40, legend=dict(orientation="h", y=1.08), height=600)
fig.write_html(H / "charts/event_cars.html", include_plotlyjs="cdn")

fig = make_subplots(rows=2, cols=2, subplot_titles=["Dividends paid (US$ bn) vs iron ore (US$/t, rhs)", "Capex (US$ bn)", "Payout (% of net income)", "Net debt / EBIT (x)"],
                    specs=[[{"secondary_y": True}, {}], [{}, {}]])
A = annV
fig.add_bar(x=A.year, y=A["div"], name="Dividends", marker_color="#1b7f5a", row=1, col=1)
fig.add_scatter(x=A.year, y=A.iron_usd_t, name="Iron ore", line_color="#7b3f00", row=1, col=1, secondary_y=True)
fig.add_bar(x=A.year, y=A.capex, name="Capex", marker_color="#4a6fa5", row=1, col=2)
fig.add_bar(x=A.year, y=A.payout_pct, name="Payout", marker_color="#999", row=2, col=1)
fig.add_bar(x=A.year, y=A.nd_over_ebit, name="ND/EBIT", marker_color="#b55", row=2, col=2)
for r_, c_ in [(1, 1), (1, 2), (2, 1), (2, 2)]:
    for x0, x1, l in [(2011.5, 2016.5, "left"), (2016.5, 2018.5, "right"), (2018.5, 2022.5, "right"), (2022.5, 2025.5, "left")]:
        fig.add_vrect(x0=x0, x1=x1, fillcolor=SH[l], line_width=0, layer="below", row=r_, col=c_)
fig.update_layout(template="plotly_white", title="Vale fundamentals by year (CVM, converted at average BRL/USD; red = left term, blue = right)", showlegend=False, height=700)
fig.write_html(H / "charts/fundamentals.html", include_plotlyjs="cdn")
print(json.dumps({k: OUT[k] for k in ["crosscheck"]}, indent=1))
print("done")
