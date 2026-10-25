"""Study 2: hydrology/climate -> power cost -> inflation, agro and EU access (plan PART B).
numpy/pandas/duckdb/plotly only; seed 0. Pre-registration must exist before analysis.
Run: /Users/zkid18/proj-personal/brazil-macro/.venv/bin/python hydro_study.py
"""
import json, math, sys, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, duckdb

OUT = Path(__file__).resolve().parent
assert (OUT / "preregistration.txt").exists(), "preregistration.txt must exist before any analysis"
DB = "/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb"
con = duckdb.connect(DB, read_only=True)
SEED, NBOOT = 0, 2000
SQL, META, R = {}, {}, {}


def q(name, sql):
    SQL[name] = sql.strip()
    return con.execute(sql).df()


def num(value, series, sql):
    """every reported warehouse number: value + provenance."""
    series = [series] if isinstance(series, str) else list(series)
    return {"value": None if value is None or (isinstance(value, float) and not np.isfinite(value)) else
            (round(float(value), 4) if not isinstance(value, (list, dict, str)) else value),
            "series_id": series, "source": sorted({META.get(s, {}).get("source", "?") for s in series}),
            "last_date": {s: META.get(s, {}).get("last") for s in series}, "sql": sql}


# ----------------------------------------------------------------------------- helpers (copied from politics study)
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X))
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    r2 = 1 - r.var() / y.var() if y.var() > 0 else 0.0
    return b, r, r2


def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    q_ = np.empty(n); prev = 1.0
    for i in range(n - 1, -1, -1):
        prev = min(prev, p[o[i]] * n / (i + 1)); q_[o[i]] = prev
    return q_


def block_boot(df, fn, block=12, nboot=NBOOT, seed=SEED):
    """moving-block bootstrap over rows of df (time-ordered); fn(df)->array of stats."""
    rng = np.random.default_rng(seed)
    n = len(df); nb = int(math.ceil(n / block)); starts_max = max(n - block, 0)
    out = []
    for _ in range(nboot):
        st = rng.integers(0, starts_max + 1, size=nb)
        idx = np.concatenate([np.arange(s, s + block) for s in st])[:n]
        try:
            out.append(fn(df.iloc[idx]))
        except Exception:
            continue
    return np.array(out)


def ci(a, lo=5, hi=95):
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    return [float(np.percentile(a, lo)), float(np.percentile(a, hi))] if len(a) else [None, None]


def boot_p(a):
    """two-sided bootstrap p for H0: stat = 0 (share of draws on the other side x2)."""
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    if not len(a):
        return None
    return float(min(1.0, 2 * min((a <= 0).mean(), (a >= 0).mean())))


# ----------------------------------------------------------------------------- data
MONTHLY_IDS = ['stored_energy_ear', 'cmo_power_cost', 'hydro_generation_share', 'thermal_generation_share',
               'wind_solar_generation_share', 'thermal_dispatch_mwh', 'electricity_load', 'hydro_stress_index',
               'ipca_administered_prices', 'ipca_monthly', 'ipca_services', 'ipca_12m', 'inflation_diffusion',
               'focus_ipca_12m', 'focus_selic_12m', 'selic_target', 'real_policy_rate', 'brent_usd',
               'generation_gwh@AXIA', 'generation_share_sin@AXIA', 'generation_gwh@PETR', 'generation_share_sin@PETR',
               'gas_production_mm3d', 'ibc_br', 'wb/IPTOTSAKD_M.BRA', 'soy_exports', 'coffee_exports', 'sugar_exports',
               'exports_to_eu', 'total_return_usd@AXIA', 'total_return_usd@PETR']
ANNUAL_IDS = ['wb/EN.CLC.SPEI.XD.BR', 'wb/EN.CLC.HEAT.XD.BR', 'wb/EN.CLC.CDDY.XD.BR', 'wb/EG.ELC.HYRO.ZS.BR',
              'wb/EG.ELC.NGAS.ZS.BR', 'wb/AG.YLD.CREL.KG.BR', 'wb/AG.PRD.CREL.MT.BR', 'wb/NV.AGR.TOTL.KD.ZG.BR',
              'wb/NY.GDP.MKTP.KD.ZG.BR', 'wb/EG.USE.ELEC.KH.PC.BR', 'wb/AG.LND.PFLS.HA.BR', 'wb/AG.LND.FRLS.HA.BR',
              'wb/TOT.BRA', 'ipca_12m']


def load_meta():
    ids = MONTHLY_IDS + ANNUAL_IDS + ['wb/NYGDPMKTPSAKD_Q.BRA']
    m = q("meta", f"""SELECT series_id, source, freq, first_date, last_date, title, role FROM v_search
                      WHERE series_id IN ({','.join(repr(i) for i in ids)})""")
    for r in m.itertuples():
        META[r.series_id] = {"source": r.source, "freq": r.freq, "first": str(r.first_date), "last": str(r.last_date),
                             "title": r.title, "role": r.role}


def anchors():
    a = {}
    ear = q("anchor_ear", """SELECT year(date) AS y, avg(value) AS mean, min(value) AS mn,
            sum(CASE WHEN value < 40 THEN 1 ELSE 0 END) AS days_lt40
            FROM v_observations WHERE series_id='stored_energy_ear' AND date <= current_date GROUP BY 1 ORDER BY 1""")
    cmo = q("anchor_cmo", """SELECT year(date) AS y, avg(value) AS mean, max(value) AS mx,
            sum(CASE WHEN value > 500 THEN 1 ELSE 0 END) AS weeks_gt500
            FROM v_observations WHERE series_id='cmo_power_cost' AND date <= current_date GROUP BY 1 ORDER BY 1""")
    adm = q("anchor_admin", """SELECT year(date) AS y, sum(value) AS admin_sum FROM v_observations
            WHERE series_id='ipca_administered_prices' AND date <= current_date GROUP BY 1 ORDER BY 1""")
    plan = {"ear_mean": {2015: 31.3, 2017: 32.6, 2021: 34.1, 2022: 62.2, 2023: 77.5, 2024: 61.1, 2025: 62.0},
            "days_lt40": {2015: 341, 2016: 125, 2017: 308, 2018: 236, 2019: 184, 2020: 147, 2021: 253, 2022: 8, 2023: 0},
            "cmo_mean": {2008: 138, 2014: 829, 2015: 567, 2021: 530, 2022: 31, 2024: 100, 2025: 248},
            "admin_sum": {2015: 16.8, 2021: 15.8, 2022: -3.7, 2023: 8.8, 2024: 4.6, 2025: 5.2}}
    e, c, d = ear.set_index("y"), cmo.set_index("y"), adm.set_index("y")
    mism = []
    for y, v in plan["ear_mean"].items():
        if abs(e.loc[y, "mean"] - v) > 0.15: mism.append(("ear_mean", y, v, e.loc[y, "mean"]))
    for y, v in plan["days_lt40"].items():
        if int(e.loc[y, "days_lt40"]) != v: mism.append(("days_lt40", y, v, e.loc[y, "days_lt40"]))
    for y, v in plan["cmo_mean"].items():
        if abs(c.loc[y, "mean"] - v) > 1: mism.append(("cmo_mean", y, v, c.loc[y, "mean"]))
    for y, v in plan["admin_sum"].items():
        if abs(d.loc[y, "admin_sum"] - v) > 0.1: mism.append(("admin_sum", y, v, d.loc[y, "admin_sum"]))
    a["mismatches"] = [list(map(lambda x: x if isinstance(x, str) else float(x), m)) for m in mism]
    a["ear"] = ear.round(2).to_dict("records"); a["cmo"] = cmo.round(1).to_dict("records")
    a["admin"] = adm[adm.y >= 2013].round(2).to_dict("records")
    a["notes"] = ["2026 YTD EAR mean 64.5 vs plan 64.1 and 2026 YTD load 80.5 vs plan 81.5 GWmed: moving YTD windows; not breaking."]
    if mism:
        print("ANCHOR MISMATCHES:", mism)
    R["anchors"] = a
    return ear, cmo, adm


def monthly_panel():
    ids = ",".join(repr(i) for i in MONTHLY_IDS)
    df = q("monthly_panel", f"""SELECT series_id, date_trunc('month', date) AS ym, avg(value) AS v, min(value) AS v_min
        FROM v_observations WHERE date <= current_date AND series_id IN ({ids}) GROUP BY 1,2 ORDER BY 2,1""")
    p = df.pivot(index="ym", columns="series_id", values="v")
    p.index = pd.to_datetime(p.index)
    p = p.asfreq("MS")
    # IPCA price index (chained) and real CMO in 2026-08 BRL
    idx = (1 + p["ipca_monthly"] / 100).cumprod()
    base = idx.loc["2026-08-01"]
    p["ipca_index"] = idx
    p["cmo_real"] = p["cmo_power_cost"] * base / idx
    p["log_cmo_real"] = np.log(p["cmo_real"] + 10)
    p["S"] = np.clip(40 - p["stored_energy_ear"], 0, None) / 10
    p["brent12"] = 100 * np.log(p["brent_usd"]).diff(12)
    lt = (p["stored_energy_ear"] < 40).astype(float).where(p["stored_energy_ear"].notna())
    # episode month: in a run of >= 3 consecutive months EAR < 40
    run_id = (lt != lt.shift()).cumsum()
    run_len = lt.groupby(run_id).transform("size")
    p["episode"] = ((lt == 1) & (run_len >= 3)).astype(float).where(lt.notna())
    return p


def annual_panel():
    ids = ",".join(repr(i) for i in ANNUAL_IDS)
    a = q("annual_panel", f"""SELECT series_id, year, value, is_complete FROM v_annual
          WHERE series_id IN ({ids}) AND year <= year(current_date) ORDER BY 1,2""")
    w = a[a.is_complete].pivot(index="year", columns="series_id", values="value")
    ons = q("annual_ons", """SELECT series_id, year(date) AS year, avg(value) AS v, count(*) AS n
          FROM v_observations WHERE date <= current_date AND series_id IN
          ('stored_energy_ear','cmo_power_cost','electricity_load','hydro_generation_share','wind_solar_generation_share',
           'thermal_generation_share','ibc_br','ipca_administered_prices','exports_to_eu','soy_exports','coffee_exports','sugar_exports')
          GROUP BY 1,2 ORDER BY 1,2""")
    o = ons.pivot(index="year", columns="series_id", values="v")
    sums = q("annual_sums", """SELECT series_id, year(date) AS year, sum(value) AS v FROM v_observations
          WHERE date <= current_date AND series_id IN ('ipca_administered_prices','exports_to_eu','soy_exports','coffee_exports','sugar_exports')
          GROUP BY 1,2""").pivot(index="year", columns="series_id", values="v")
    o = o.drop(columns=[c for c in sums.columns if c in o.columns]).join(sums.add_suffix("_sum"), how="outer")
    o.columns = ["ons_" + c for c in o.columns]
    return w.join(o, how="outer")


def episodes(p):
    d = q("ear_daily", """SELECT date, value FROM v_observations WHERE series_id='stored_energy_ear' AND date <= current_date ORDER BY date""")
    d["date"] = pd.to_datetime(d["date"]); s = d.set_index("date").value
    low = s < 40
    # merge gaps <= 7 days above 40
    runs, start, last_low = [], None, None
    for t, v in low.items():
        if v:
            if start is None:
                start = t
            elif (t - last_low).days > 8:
                runs.append((start, last_low)); start = t
            last_low = t
    if start is not None:
        runs.append((start, last_low))
    rows = []
    cmo_w = q("cmo_weekly", "SELECT date, value FROM v_observations WHERE series_id='cmo_power_cost' AND date <= current_date ORDER BY date")
    cmo_w["date"] = pd.to_datetime(cmo_w["date"]); cw = cmo_w.set_index("date").value
    for a, b in runs:
        days = (b - a).days + 1
        if days < 90:
            continue
        m0 = pd.Timestamp(a.year, a.month, 1)
        m12 = m0 + pd.DateOffset(months=11)
        pre = m0 - pd.DateOffset(months=1)
        def at(col, t):
            return p[col].get(t, np.nan)
        rows.append({
            "start": a.date(), "end": b.date(), "days": days, "min_ear": round(s[a:b].min(), 1),
            "cmo_mean": round(cw[a:b].mean(), 0), "cmo_max": round(cw[a:b].max(), 0),
            "thermal_share_mean": round(p.loc[m0:pd.Timestamp(b.year, b.month, 1), "thermal_generation_share"].mean(), 1),
            "admin_ipca_12m_after": round(p.loc[m0:m12, "ipca_administered_prices"].sum(), 2),
            "headline_ipca_12m_after": round(p.loc[m0:m12, "ipca_monthly"].sum(), 2),
            "focus_ipca_change_12m": round(at("focus_ipca_12m", m12) - at("focus_ipca_12m", pre), 2),
            "selic_change_bp_12m": round(100 * (at("selic_target", m12) - at("selic_target", pre)), 0),
            "brent_change_pct_12m": round(100 * (at("brent_usd", m12) / at("brent_usd", pre) - 1), 1),
        })
    ep = pd.DataFrame(rows)
    ep.to_csv(OUT / "episodes.csv", index=False)
    # placebo: 2,000 draws of len(ep) random start months 2015-01..2025-08 (exploratory, plan B3 "placebo months")
    rng = np.random.default_rng(SEED)
    months = pd.date_range("2015-01-01", "2025-08-01", freq="MS")
    def stat(m0):
        m12 = m0 + pd.DateOffset(months=11); pre = m0 - pd.DateOffset(months=1)
        return (p.loc[m0:m12, "ipca_administered_prices"].sum(), p.loc[m0:m12, "ipca_monthly"].sum(),
                p["focus_ipca_12m"].get(m12, np.nan) - p["focus_ipca_12m"].get(pre, np.nan),
                100 * (p["selic_target"].get(m12, np.nan) - p["selic_target"].get(pre, np.nan)))
    allst = np.array([stat(m) for m in months])
    k = len(ep); draws = np.array([np.nanmean(allst[rng.choice(len(months), k, replace=False)], axis=0) for _ in range(NBOOT)])
    obs = ep[["admin_ipca_12m_after", "headline_ipca_12m_after", "focus_ipca_change_12m", "selic_change_bp_12m"]].mean().values
    R["episode_placebo"] = {"names": ["admin_12m", "headline_12m", "focus_ipca_chg", "selic_chg_bp"],
        "episode_mean": [round(float(x), 2) for x in obs], "all_months_mean": [round(float(x), 2) for x in np.nanmean(allst, 0)],
        "p_one_sided": [round(float((draws[:, j] >= obs[j]).mean()), 4) for j in range(4)], "k": k,
        "note": "exploratory; random start months 2015-01..2025-08, 2,000 draws, seed 0"}
    R["episodes"] = {"sql": SQL["ear_daily"], "rule": ">= 90 consecutive days EAR < 40 (gaps <= 7 days merged)",
                     "rows": json.loads(ep.to_json(orient="records", date_format="iso"))}
    return ep


# ----------------------------------------------------------------------------- W1
def w1_price(p):
    d = p.loc["2015-01-01":, ["cmo_power_cost", "cmo_real", "log_cmo_real", "stored_energy_ear", "episode",
                              "wind_solar_generation_share", "brent_usd", "thermal_generation_share"]].dropna(
        subset=["cmo_power_cost", "stored_energy_ear"])
    ep, ne = d[d.episode == 1], d[d.episode == 0]
    ratio = ep.cmo_power_cost.mean() / ne.cmo_power_cost.mean()
    ratio_real = ep.cmo_real.mean() / ne.cmo_real.mean()
    lt40 = d[(d.index >= "2016-01-01") & (d.stored_energy_ear < 40)]; ge40 = d[(d.index >= "2016-01-01") & (d.stored_energy_ear >= 40)]
    h4 = lt40.cmo_power_cost.mean() / ge40.cmo_power_cost.mean()
    rb = block_boot(d, lambda x: x[x.episode == 1].cmo_power_cost.mean() / x[x.episode == 0].cmo_power_cost.mean())
    # regression with WS interaction (WS from 2015-07)
    r = d.dropna(subset=["wind_solar_generation_share", "brent_usd", "log_cmo_real"]).copy()
    r["earc"] = r.stored_energy_ear - 50; r["wsc"] = r.wind_solar_generation_share - 15
    r["lb"] = np.log(r.brent_usd)
    def fit(x):
        b, *_ = ols(x.log_cmo_real.values, [x.earc.values, x.wsc.values, (x.earc * x.wsc).values, x.lb.values])
        return b
    b = fit(r)
    _, res, r2 = ols(r.log_cmo_real.values, [r.earc.values, r.wsc.values, (r.earc * r.wsc).values, r.lb.values])
    bb = block_boot(r, fit)
    # thermal share response
    tb, _, tr2 = ols(r.thermal_generation_share.values, [r.stored_energy_ear.values])
    out = {
        "n_months": int(len(d)), "n_episode": int(len(ep)),
        "cmo_episode_mean": num(ep.cmo_power_cost.mean(), "cmo_power_cost", SQL["monthly_panel"]),
        "cmo_other_mean": num(ne.cmo_power_cost.mean(), "cmo_power_cost", SQL["monthly_panel"]),
        "ratio_nominal": num(ratio, ["cmo_power_cost", "stored_energy_ear"], SQL["monthly_panel"]),
        "ratio_nominal_ci90": ci(rb), "ratio_real": round(ratio_real, 2),
        "h4_replication_ratio_2016plus_ear_lt40": round(h4, 2),
        "reg": {"n": int(len(r)), "r2": round(r2, 3), "coef_names": ["const", "EAR-50", "WS-15", "(EAR-50)x(WS-15)", "log Brent"],
                "b": [round(x, 4) for x in b], "ci90": [[round(v, 4) for v in ci(bb[:, k])] for k in range(len(b))],
                "p_boot": [boot_p(bb[:, k]) for k in range(len(b))],
                "note": "log(CMO_real+10). EAR slope at WS=15 is b1; slope at WS=30 is b1 + 15*b3."},
        "ear_slope_ws15": round(b[1], 4), "ear_slope_ws30": round(b[1] + 15 * b[3], 4),
        "thermal_share_per_ear_pt": round(tb[1], 3), "thermal_r2": round(tr2, 3),
    }
    met = ratio >= 2
    dadd = (b[3] > 0) and ci(bb[:, 3])[0] > 0
    out["verdict"] = ("Both agree" if met else "Null/inconclusive") + ("; D addition supported (slope flattens with WS)" if dadd
                     else "; D addition not supported (EAR x WS CI includes 0 or wrong sign)")
    out["p_primary"] = boot_p(np.log(rb))
    R["W1"] = out
    return out


# ----------------------------------------------------------------------------- W2/W3 local projections
def lp(p, outcome, kind, H=12, shock="S", drop_years=(), start="2015-01-01", controls=("brent12", "ylag")):
    d = p.loc[start:].copy()
    y = d[outcome]
    if kind == "cum":
        cs = y.cumsum()
        lag = cs.shift(1) - cs.shift(13)
    else:
        lag = y.shift(1) - y.shift(13)
    res = []
    for h in range(H + 1):
        if kind == "cum":
            yy = cs.shift(-h) - cs.shift(1)
        else:
            yy = y.shift(-h) - y.shift(1)
        if outcome == "selic_target":
            yy = yy * 100
        X = pd.DataFrame({"y": yy, "s": d[shock], "brent12": d["brent12"], "ylag": lag * (100 if outcome == "selic_target" else 1)})
        X = X[[c for c in ["y", "s"] + list(controls)]].dropna()
        X = X[~X.index.year.isin(drop_years)]
        if len(X) < 30:
            res.append({"h": h, "n": len(X), "b": None, "ci90": [None, None]}); continue
        f = lambda x: ols(x.y.values, [x[c].values for c in ["s"] + list(controls)])[0][1]
        b = f(X)
        bb = block_boot(X, f, nboot=1000)
        res.append({"h": h, "n": int(len(X)), "b": round(float(b), 4), "ci90": [round(v, 4) for v in ci(bb)], "p_boot": boot_p(bb)})
    return res


def w2_w3_local_projections(p):
    p = p.copy()
    p["S_cont"] = -(p["stored_energy_ear"] - p.loc["2015-01-01":, "stored_energy_ear"].mean()) / 10
    out = {"shock": "S = max(0, 40-EAR)/10 (one unit = 10 pts below 40)", "controls": "Brent 12m log change, own lagged 12m change",
           "sample": "2015-01 .. 2026-08", "bootstrap": "moving block 12, 1000 draws per horizon"}
    specs = {"admin": ("ipca_administered_prices", "cum"), "headline": ("ipca_monthly", "cum"),
             "services": ("ipca_services", "cum"),
             "focus_ipca": ("focus_ipca_12m", "chg"), "focus_selic": ("focus_selic_12m", "chg"), "selic_bp": ("selic_target", "chg")}
    for k, (sid, kind) in specs.items():
        out[k] = {"series_id": sid, "irf": lp(p, sid, kind)}
    out["robust"] = {}
    for tag, kw in {"drop2015": {"drop_years": (2015,)}, "drop2022": {"drop_years": (2022,)},
                    "continuous_ear": {"shock": "S_cont"}, "no_controls": {"controls": ()}}.items():
        out["robust"][tag] = {k: lp(p, specs[k][0], specs[k][1], **kw)[12] for k in ["admin", "headline", "focus_ipca", "selic_bp"]}
    # verdicts
    a12 = out["admin"]["irf"][12]
    W2 = "F" if (a12["b"] >= 1.0 and a12["ci90"][0] > 0) else ("D" if (a12["b"] < 0.5 or a12["ci90"][0] <= 0) else "Partial")
    fpk = max(out["focus_ipca"]["irf"], key=lambda r: r["b"] if r["b"] is not None else -9)
    spk = max(out["selic_bp"]["irf"], key=lambda r: r["b"] if r["b"] is not None else -9)
    f_ok = fpk["b"] >= 0.5 and fpk["ci90"][0] > 0
    s_ok = spk["b"] >= 50 and spk["ci90"][0] > 0
    W3 = "F" if (f_ok and s_ok) else ("Partial" if (f_ok or s_ok or (fpk["ci90"][0] > 0) or (spk["ci90"][0] > 0)) else "D")
    out["W2_verdict"] = W2; out["W3_verdict"] = W3
    out["focus_peak"] = fpk; out["selic_peak"] = spk
    # 2021 decomposition
    j, n_ = pd.Timestamp("2021-01-01"), pd.Timestamp("2021-11-01")
    def roll12(col, t):
        x = p.loc[t - pd.DateOffset(months=11):t, col]
        return 100 * ((1 + x / 100).prod() - 1)
    adm_j, adm_n = roll12("ipca_administered_prices", j), roll12("ipca_administered_prices", n_)
    hd_j, hd_n = p.loc[j, "ipca_12m"], p.loc[n_, "ipca_12m"]
    out["decomp_2021"] = {"ipca_12m_jan": hd_j, "ipca_12m_nov": hd_n, "admin_12m_jan": round(adm_j, 2), "admin_12m_nov": round(adm_n, 2),
                          "focus_jan": round(p.loc[j, "focus_ipca_12m"], 2), "focus_nov": round(p.loc[n_, "focus_ipca_12m"], 2),
                          "selic_jan": round(p.loc[j, "selic_target"], 2), "selic_dec_mean": round(p.loc["2021-12-01", "selic_target"], 2),
                          "brent_chg_pct_jan_nov": round(100 * (p.loc[n_, "brent_usd"] / p.loc[j, "brent_usd"] - 1), 1)}
    R["W2W3"] = out
    return out


# ----------------------------------------------------------------------------- W4 output
def w4_output(p, A):
    g = q("gdp_q", "SELECT date, value FROM v_observations WHERE series_id='wb/NYGDPMKTPSAKD_Q.BRA' ORDER BY date")
    g["date"] = pd.to_datetime(g["date"]); gs = g.set_index("date").value
    yoy = (gs / gs.shift(4) - 1) * 100
    out = {"gdp_q_yoy_2000_2002": {str(k.date()): round(v, 2) for k, v in yoy["2000-03-31":"2002-12-31"].items()},
           "gdp_q_yoy_2021": {str(k.date()): round(v, 2) for k, v in yoy["2021-03-31":"2021-12-31"].items()},
           "gdp_q_yoy_2014_2015": {str(k.date()): round(v, 2) for k, v in yoy["2014-03-31":"2015-12-31"].items()},
           "wb_gdp_growth": {int(y): round(A.loc[y, "wb/NY.GDP.MKTP.KD.ZG.BR"], 2) for y in range(1998, 2004)},
           "hydro_share_wb": {int(y): round(A.loc[y, "wb/EG.ELC.HYRO.ZS.BR"], 1) for y in (1999, 2000, 2001, 2002)},
           "elec_kwh_pc": {int(y): round(A.loc[y, "wb/EG.USE.ELEC.KH.PC.BR"], 0) for y in (1999, 2000, 2001, 2002, 2003)}}
    kw = A["wb/EG.USE.ELEC.KH.PC.BR"]
    out["elec_kwh_pc_2001_pct"] = round(100 * (kw[2001] / kw[2000] - 1), 1)
    # 2001: deviation of GDP growth from the 1998-2000 and 2002-2004 average
    gg = A["wb/NY.GDP.MKTP.KD.ZG.BR"]
    out["gdp_2001_vs_neighbours"] = round(gg[2001] - np.mean([gg[2000], gg[2002]]), 2)
    # post-2015 IBC-Br on S
    d = p.loc["2015-01-01":].copy()
    d["ibc12"] = 100 * np.log(d["ibc_br"]).diff(12)
    d["load12"] = 100 * np.log(d["electricity_load"]).diff(12)
    def reg(excl, ycol):
        x = d[["S", "brent12", ycol]].dropna()
        for a, b in excl:
            x = x[~((x.index >= a) & (x.index <= b))]
        f = lambda z: ols(z[ycol].values, [z.S.values, z.brent12.values])[0][1]
        bb = block_boot(x, f)
        return {"n": int(len(x)), "b": round(f(x), 3), "ci90": [round(v, 3) for v in ci(bb)], "p_boot": boot_p(bb)}
    out["ibc_on_S_excl2020"] = reg([("2020-03-01", "2020-12-01")], "ibc12")
    out["ibc_on_S_excl2020_2021"] = reg([("2020-03-01", "2021-12-01")], "ibc12")
    out["load_on_S_excl2020_2021"] = reg([("2020-03-01", "2021-12-01")], "load12")
    out["ibc_episode_vs_other"] = {"episode": round(d.loc[d.episode == 1, "ibc12"].mean(), 2), "other": round(d.loc[d.episode == 0, "ibc12"].mean(), 2)}
    r = out["ibc_on_S_excl2020"]
    out["verdict"] = "F" if (r["b"] < 0 and r["ci90"][1] < 0) else "D"
    out["p_primary"] = r["p_boot"]
    out["sql"] = SQL["gdp_q"]
    R["W4"] = out
    return out


# ----------------------------------------------------------------------------- W5 agro
def w5_agro(A, p):
    y = A["wb/AG.YLD.CREL.KG.BR"]; s = A["wb/EN.CLC.SPEI.XD.BR"]; va = A["wb/NV.AGR.TOTL.KD.ZG.BR"]
    d = pd.DataFrame({"dly": 100 * np.log(y).diff(), "spei": s, "va": va}).loc[1962:2023].dropna(subset=["spei"])
    d["tr"] = (d.index - 1990) / 10
    def fit(x, col):
        x = x.dropna(subset=[col])
        return ols(x[col].values, [x.spei.values, (x.spei * x.tr).values, x.tr.values])[0]
    out = {}
    for col, name in [("dly", "cereal_yield_dlog"), ("va", "agri_va_growth")]:
        x = d.dropna(subset=[col])
        b = fit(x, col)
        bb = block_boot(x, lambda z: fit(z, col), block=3)
        b0 = ols(x[col].values, [x.spei.values])[0]
        bb0 = block_boot(x, lambda z: ols(z[col].values, [z.spei.values])[0][1], block=3)
        out[name] = {"n": int(len(x)), "years": [int(x.index.min()), int(x.index.max())],
                     "b_spei_simple": round(b0[1], 3), "ci90_simple": [round(v, 3) for v in ci(bb0)], "p_simple": boot_p(bb0),
                     "b_spei_at_1990": round(b[1], 3), "b_spei_x_decade": round(b[2], 3),
                     "ci90_spei": [round(v, 3) for v in ci(bb[:, 1])], "ci90_interaction": [round(v, 3) for v in ci(bb[:, 2])],
                     "b_spei_at_2020": round(b[1] + 3 * b[2], 3)}
        # split sample
        for lab, (a0, a1) in {"pre2000": (1962, 1999), "post2000": (2000, 2023)}.items():
            z = x.loc[a0:a1]
            out[name]["b_spei_" + lab] = round(ols(z[col].values, [z.spei.values])[0][1], 3)
    # exploratory: previous-year SPEI (season straddles calendar years)
    d["spei_l1"] = d.spei.shift(1)
    x = d.dropna(subset=["dly", "spei_l1"])
    bl = block_boot(x, lambda z: ols(z.dly.values, [z.spei.values, z.spei_l1.values])[0], block=3)
    bL = ols(x.dly.values, [x.spei.values, x.spei_l1.values])[0]
    out["cereal_yield_dlog"]["exploratory_with_lag"] = {"b_spei": round(bL[1], 3), "b_spei_lag1": round(bL[2], 3),
        "ci90_lag1": [round(v, 3) for v in ci(bl[:, 2])]}
    cy = out["cereal_yield_dlog"]
    pos = cy["b_spei_simple"] > 0 and cy["ci90_simple"][0] > 0
    out["verdict"] = ("F" if (pos and cy["b_spei_x_decade"] >= 0) else
                      ("D" if (cy["b_spei_x_decade"] < 0 or not pos) else "Partial"))
    out["p_primary"] = cy["p_simple"]
    # exports in USD vs SPEI / EAR (descriptive)
    ex = {}
    for c in ["soy_exports", "coffee_exports", "sugar_exports"]:
        col = "ons_" + c + "_sum"
        e = A[col].loc[2014:2025]
        g = 100 * np.log(e).diff()
        z = pd.DataFrame({"g": g, "spei": A["wb/EN.CLC.SPEI.XD.BR"], "ear": A["ons_stored_energy_ear"]}).loc[2015:2025]
        ex[c] = {"corr_spei": round(z[["g", "spei"]].dropna().corr().iloc[0, 1], 2), "n_spei": int(z[["g", "spei"]].dropna().shape[0]),
                 "corr_ear": round(z[["g", "ear"]].dropna().corr().iloc[0, 1], 2),
                 "usd_bn": {int(k): round(v / 1e9, 2) for k, v in e.items()}}
    out["exports_usd"] = ex
    out["yield_yoy_drought_years"] = {int(k): round(v, 1) for k, v in d.dly.loc[[2012, 2015, 2016, 2017, 2019, 2021, 2023]].items() if np.isfinite(v)}
    out["yield_yoy_2024"] = round(100 * np.log(y[2024] / y[2023]), 1)
    R["W5"] = out
    return out


# ----------------------------------------------------------------------------- W6 bands
BANDS = [(20, 30), (30, 40), (40, 50), (50, 60), (60, 101)]


def w6_bands(p):
    d = p.loc["2015-01-01":, ["stored_energy_ear", "log_cmo_real", "cmo_real", "cmo_power_cost"]].dropna()
    d["period"] = np.where(d.index < "2022-01-01", "2015-21", "2022-26")
    rows = []
    for lo, hi in BANDS:
        b = d[(d.stored_energy_ear >= lo) & (d.stored_energy_ear < hi)]
        e, l = b[b.period == "2015-21"], b[b.period == "2022-26"]
        row = {"band": f"{lo}-{hi if hi < 101 else '+'}", "n_2015_21": len(e), "n_2022_26": len(l),
               "cmo_real_mean_2015_21": round(e.cmo_real.mean(), 0) if len(e) else None,
               "cmo_real_mean_2022_26": round(l.cmo_real.mean(), 0) if len(l) else None,
               "cmo_real_median_2015_21": round(e.cmo_real.median(), 0) if len(e) else None,
               "cmo_real_median_2022_26": round(l.cmo_real.median(), 0) if len(l) else None}
        if len(e) >= 3 and len(l) >= 3:
            obs = l.log_cmo_real.mean() - e.log_cmo_real.mean()
            rng = np.random.default_rng(SEED)
            draws = [rng.choice(l.log_cmo_real.values, len(l)).mean() - rng.choice(e.log_cmo_real.values, len(e)).mean() for _ in range(NBOOT)]
            row.update({"dlog_cmo_late_minus_early": round(obs, 3), "ci90": [round(v, 3) for v in ci(draws)], "p_boot": boot_p(np.array(draws))})
        rows.append(row)
    # slope comparison (piecewise linear: EAR slope by period, levels and logs)
    sl = {}
    for per in ["2015-21", "2022-26"]:
        z = d[d.period == per]
        sl[per] = {"n": len(z), "dlogcmo_per_ear_pt": round(ols(z.log_cmo_real.values, [z.stored_energy_ear.values])[0][1], 4),
                   "brl_per_ear_pt_real": round(ols(z.cmo_real.values, [z.stored_energy_ear.values])[0][1], 2),
                   "ear_range": [round(z.stored_energy_ear.min(), 1), round(z.stored_energy_ear.max(), 1)]}
    # common-support slope: only months with EAR in 40-65 in both periods
    cs = {}
    for per in ["2015-21", "2022-26"]:
        z = d[(d.period == per) & (d.stored_energy_ear >= 40) & (d.stored_energy_ear < 65)]
        cs[per] = {"n": len(z), "dlogcmo_per_ear_pt": round(ols(z.log_cmo_real.values, [z.stored_energy_ear.values])[0][1], 4),
                   "cmo_real_mean": round(z.cmo_real.mean(), 0), "ear_mean": round(z.stored_energy_ear.mean(), 1)}
    # 2024 episode vs 2017-18 at similar EAR (40-50)
    a24 = d.loc["2024-07-01":"2024-12-01"]; a1718 = d.loc["2017-01-01":"2018-12-01"]
    a1718s = a1718[(a1718.stored_energy_ear >= 40) & (a1718.stored_energy_ear < 55)]
    cmp24 = {"2024_h2_ear_mean": round(a24.stored_energy_ear.mean(), 1), "2024_h2_cmo_real_mean": round(a24.cmo_real.mean(), 0),
             "2024_h2_cmo_nominal_mean": round(a24.cmo_power_cost.mean(), 0),
             "2017_18_ear40_55_n": len(a1718s), "2017_18_ear40_55_ear_mean": round(a1718s.stored_energy_ear.mean(), 1),
             "2017_18_ear40_55_cmo_real_mean": round(a1718s.cmo_real.mean(), 0)}
    tested = [r for r in rows if "dlog_cmo_late_minus_early" in r]
    lower_all = all(r["dlog_cmo_late_minus_early"] < 0 for r in tested) and len(tested) > 0
    any_sig = any(r["ci90"][1] < 0 for r in tested)
    b4050 = next((r for r in rows if r["band"] == "40-50"), {})
    not_lower_4050 = ("dlog_cmo_late_minus_early" in b4050) and b4050["dlog_cmo_late_minus_early"] >= 0
    verdict = "D" if (lower_all and any_sig) else ("F" if not_lower_4050 else "Partial")
    out = {"bands": rows, "slopes_full": sl, "slopes_common_support_40_65": cs, "cmp_2024_vs_2017_18": cmp24,
           "verdict": verdict, "untestable": "bands 20-30 and 30-40 have no 2022-26 months (declared in advance)",
           "p_primary": b4050.get("p_boot")}
    R["W6"] = out
    return out, d


# ----------------------------------------------------------------------------- W7 demand
def w7_demand(A, p):
    d = pd.DataFrame({"load": A["ons_electricity_load"], "cdd": A["wb/EN.CLC.CDDY.XD.BR"], "heat": A["wb/EN.CLC.HEAT.XD.BR"],
                      "ibc": A["ons_ibc_br"], "kwh": A["wb/EG.USE.ELEC.KH.PC.BR"]}).loc[2015:2025]
    d["load_g"] = 100 * np.log(d.load).diff(); d["ibc_g"] = 100 * np.log(d.ibc).diff(); d["dcdd"] = d.cdd.diff()
    d["kwh_g"] = 100 * np.log(d.kwh).diff()
    fit = d.loc[2016:2022]
    b, r, r2 = ols(fit.load_g.values, [fit.dcdd.values, fit.ibc_g.values])
    b1, r_1, r2_1 = ols(fit.load_g.values, [fit.ibc_g.values])
    res = {}
    for yv in range(2016, 2026):
        row = d.loc[yv]
        pred_full = b[0] + b[1] * row.dcdd + b[2] * row.ibc_g if np.isfinite(row.dcdd) else np.nan
        pred_ibc = b1[0] + b1[1] * row.ibc_g
        res[yv] = {"load_g": round(row.load_g, 2), "ibc_g": round(row.ibc_g, 2), "dcdd": None if not np.isfinite(row.dcdd) else round(row.dcdd, 1),
                   "resid_full": None if not np.isfinite(pred_full) else round(row.load_g - pred_full, 2),
                   "resid_ibc_only": round(row.load_g - pred_ibc, 2)}
    r23 = [res[y]["resid_full"] if res[y]["resid_full"] is not None else res[y]["resid_ibc_only"] for y in (2023, 2024, 2025)]
    mean_r = float(np.mean(r23))
    # monthly robustness: load YoY on IBC YoY 2016-2022 (excl 2020-03..2021-06), predict 2023-2026
    m = p.loc["2015-01-01":, ["electricity_load", "ibc_br"]].copy()
    m["lg"] = 100 * np.log(m.electricity_load).diff(12); m["ig"] = 100 * np.log(m.ibc_br).diff(12)
    m = m.dropna()
    tr = m.loc["2016-01-01":"2022-12-01"]; tr = tr[~((tr.index >= "2020-03-01") & (tr.index <= "2021-06-01"))]
    bm, _, r2m = ols(tr.lg.values, [tr.ig.values])
    post = m.loc["2023-01-01":]
    pr = (post.lg - (bm[0] + bm[1] * post.ig))
    monthly_res = {str(y): round(pr[pr.index.year == y].mean(), 2) for y in sorted(set(pr.index.year))}
    # ONS added estimated MMGD to "carga" from 2023-04-29 (fact W27): y/y growth May-2023..Apr-2024 is mechanically inflated
    win = {"2023-01..2023-04 (pre-MMGD)": ("2023-01-01", "2023-04-01"), "2023-05..2024-04 (MMGD break in y/y)": ("2023-05-01", "2024-04-01"),
           "2024-05..2024-12": ("2024-05-01", "2024-12-01"), "2025-01..2026-09": ("2025-01-01", "2026-09-01")}
    mmgd = {k: {"resid_pp": round(pr.loc[a:b].mean(), 2), "load_yoy": round(post.lg.loc[a:b].mean(), 2), "ibc_yoy": round(post.ig.loc[a:b].mean(), 2)}
            for k, (a, b) in win.items()}
    verdict = "F" if mean_r >= 2 else ("D" if abs(mean_r) < 1 else "Partial")
    out = {"annual_fit_2016_2022": {"b": [round(x, 3) for x in b], "names": ["const", "dCDD", "IBC growth"], "r2": round(r2, 3), "n": 7},
           "ibc_only_fit": {"b": [round(x, 3) for x in b1], "r2": round(r2_1, 3)},
           "by_year": res, "resid_mean_2023_25": round(mean_r, 2), "verdict_by_rule": verdict,
           "monthly_check": {"b": [round(x, 3) for x in bm], "r2": round(r2m, 3), "n": len(tr), "resid_mean_by_year": monthly_res},
           "mmgd_windows": mmgd,
           "cdd": {int(k): round(v, 1) for k, v in A["wb/EN.CLC.CDDY.XD.BR"].loc[2014:2024].items()},
           "load_gwmed": {int(k): round(v / 1000, 2) for k, v in A["ons_electricity_load"].loc[2015:2026].items()},
           "kwh_pc_growth": {int(k): round(v, 2) for k, v in d.kwh_g.loc[2016:2024].items()},
           "sql": SQL["annual_ons"]}
    R["W7"] = out
    return out


# ----------------------------------------------------------------------------- W8 trend
def w8_trend(A):
    rng = np.random.default_rng(SEED)
    out = {}
    pv = []
    for sid, hotter in [("wb/EN.CLC.SPEI.XD.BR", "lower"), ("wb/EN.CLC.HEAT.XD.BR", "higher"), ("wb/EN.CLC.CDDY.XD.BR", "higher")]:
        s = A[sid].dropna()
        a, b = s.loc[1960:1999].values, s.loc[2010:].values
        obs = b.mean() - a.mean(); obs_v = b.var(ddof=1) / a.var(ddof=1)
        allv = np.concatenate([a, b]); n = len(b); cnt = 0; cntv = 0
        for _ in range(10000):
            rng.shuffle(allv)
            dd = allv[:n].mean() - allv[n:].mean()
            if (hotter == "lower" and dd <= obs) or (hotter == "higher" and dd >= obs):
                cnt += 1
            vv = allv[:n].var(ddof=1) / allv[n:].var(ddof=1)
            if vv >= obs_v:
                cntv += 1
        p1 = (cnt + 1) / 10001; pvv = (cntv + 1) / 10001
        pv.append(p1)
        out[sid] = {"mean_1960_99": round(a.mean(), 3), "mean_2010_on": round(b.mean(), 3), "n": [len(a), len(b)],
                    "last_year": int(s.index.max()), "diff": round(obs, 3), "p_one_sided": round(p1, 4),
                    "var_ratio": round(obs_v, 2), "p_var": round(pvv, 4),
                    "direction_ok": bool((obs < 0) if hotter == "lower" else (obs > 0))}
    k = sum(1 for sid, v in out.items() if v["p_one_sided"] < 0.10 and v["direction_ok"])
    out["n_sig"] = k
    out["verdict"] = "F" if k >= 2 else ("D" if k == 0 else "Partial")
    out["p_primary"] = float(min(pv))
    s = A["wb/EN.CLC.SPEI.XD.BR"].dropna()
    out["driest_since_1990"] = [[int(y), round(v, 2)] for y, v in s.loc[1990:].sort_values().head(7).items()]
    R["W8"] = out
    return out


# ----------------------------------------------------------------------------- W9 companies
def w9_companies(p):
    d = p.loc["2016-01-01":, ["generation_gwh@AXIA", "generation_share_sin@AXIA", "generation_gwh@PETR", "generation_share_sin@PETR",
                              "episode", "stored_energy_ear", "total_return_usd@AXIA", "total_return_usd@PETR", "gas_production_mm3d"]].copy()
    out = {}
    for c in ["generation_gwh@AXIA", "generation_share_sin@AXIA", "generation_gwh@PETR", "generation_share_sin@PETR"]:
        x = d[[c, "episode"]].dropna()
        dev = x[c] - x.groupby(x.index.year)[c].transform("mean")
        if c.startswith("generation_gwh"):
            dev = 100 * dev / x.groupby(x.index.year)[c].transform("mean")
        out[c] = {"episode_dev": round(dev[x.episode == 1].mean(), 2), "other_dev": round(dev[x.episode == 0].mean(), 2),
                  "n_episode": int((x.episode == 1).sum()), "unit": "pct of same-year mean" if c.startswith("generation_gwh") else "pts vs same-year mean"}
        # raw episode vs other
        out[c]["episode_mean"] = round(x.loc[x.episode == 1, c].mean(), 1); out[c]["other_mean"] = round(x.loc[x.episode == 0, c].mean(), 1)
    # annual generation for 2021 vs 2023
    ann = d[["generation_gwh@AXIA", "generation_gwh@PETR"]].groupby(d.index.year).sum()
    out["annual_gwh"] = {k: {int(y): round(v, 0) for y, v in ann[k].items()} for k in ann.columns}
    for c in ["total_return_usd@AXIA", "total_return_usd@PETR"]:
        x = pd.DataFrame({"r": 100 * np.log(d[c]).diff(), "dear": d.stored_energy_ear.diff()}).dropna()
        f = lambda z: ols(z.r.values, [z.dear.values])[0][1]
        bb = block_boot(x, f)
        out[c] = {"n": int(len(x)), "b_ret_per_ear_pt": round(f(x), 3), "ci90": [round(v, 3) for v in ci(bb)], "p_boot": boot_p(bb)}
    out["verdict"] = "descriptive"
    R["W9"] = out
    return out


# ----------------------------------------------------------------------------- W10 EU
def w10_eu(A):
    d = pd.DataFrame({"frls": A["wb/AG.LND.FRLS.HA.BR"], "pfls": A["wb/AG.LND.PFLS.HA.BR"], "spei": A["wb/EN.CLC.SPEI.XD.BR"],
                      "eu": A["ons_exports_to_eu_sum"]}).loc[2002:2025]
    d["eu_g"] = 100 * np.log(d.eu).diff()
    fire = [2016, 2017, 2024]
    out = {"frls_mha": {int(k): round(v / 1e6, 2) for k, v in d.frls.items()},
           "pfls_mha": {int(k): round(v / 1e6, 2) for k, v in d.pfls.dropna().items()},
           "eu_usd_bn": {int(k): round(v / 1e9, 1) for k, v in d.eu.dropna().items()},
           "eu_growth": {int(k): round(v, 1) for k, v in d.eu_g.dropna().items()}}
    z = d.loc[2002:2023, ["frls", "spei"]].dropna()
    out["corr_frls_spei_2002_23"] = round(z.corr().iloc[0, 1], 2)
    z2 = d.loc[2015:2025, ["eu_g", "frls"]].dropna()
    out["corr_eu_growth_frls_2015_25"] = round(z2.corr().iloc[0, 1], 2)
    nf = [y for y in range(2015, 2026) if y not in fire]
    out["eu_growth_fire_years"] = round(d.eu_g.loc[[y for y in fire if y >= 2015]].mean(), 1)
    out["eu_growth_other_years"] = round(d.eu_g.loc[nf].mean(), 1)
    out["fire_years"] = fire
    out["verdict"] = "descriptive"
    R["W10"] = out
    return out


# ----------------------------------------------------------------------------- W11 policy
def w11_policy(p, A):
    d = pd.DataFrame({"admin": A["ons_ipca_administered_prices_sum"]}).loc[2015:2025]
    S = p.loc["2015-01-01":"2025-12-01", "S"].groupby(p.loc["2015-01-01":"2025-12-01"].index.year).mean()
    d["S"] = S
    d["elec"] = [1.0 if y in (2018, 2022) else 0.0 for y in d.index]
    b, r, r2 = ols(d.admin.values, [d.S.values, d.elec.values])
    b0, r0, r20 = ols(d.admin.values, [d.S.values])
    out = {"annual": {int(y): {"admin": round(row.admin, 2), "S_mean": round(row.S, 3)} for y, row in d.iterrows()},
           "ols": {"b": [round(x, 3) for x in b], "names": ["const", "S_mean", "election_2018_2022"], "r2": round(r2, 3), "n": len(d)},
           "ols_no_dummy": {"b": [round(x, 3) for x in b0], "r2": round(r20, 3)},
           "resid_2022_no_dummy": round(float(r0[list(d.index).index(2022)]), 2)}
    # admin pass-through per unit S in drought years
    pt = {}
    for y in (2015, 2017, 2018, 2021, 2022):
        pt[y] = round(d.loc[y, "admin"] / d.loc[y, "S"], 2) if d.loc[y, "S"] > 0.05 else None
    out["admin_per_unit_S"] = pt
    # what 2022 would have been: 2022 S is ~0.02 (wet) — the relevant counterfactual is 2021's lagged flags
    out["admin_2021_2022_avg"] = round((d.loc[2021, "admin"] + d.loc[2022, "admin"]) / 2, 2)
    out["admin_2023"] = round(d.loc[2023, "admin"], 2)
    out["verdict"] = "Both agree (quantified with external fiscal-cost facts)"
    R["W11"] = out
    return out


# ----------------------------------------------------------------------------- charts
C1, C2, C3, C4, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#8a8984"


def _layout(fig, title, h=520):
    fig.update_layout(title=dict(text=title, x=0.01, font=dict(size=16, color="#0b0b0b")), template="plotly_white",
                      paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb", height=h, hovermode="x unified",
                      font=dict(family="Inter, Helvetica, Arial, sans-serif", size=12, color="#52514e"),
                      legend=dict(orientation="h", y=-0.12), margin=dict(l=60, r=30, t=70, b=60))
    fig.update_xaxes(gridcolor="#ecebe8", linecolor="#c3c2b7"); fig.update_yaxes(gridcolor="#ecebe8", zerolinecolor="#c3c2b7")
    return fig


def _shade(fig, ep, rows=None):
    for r in ep.itertuples():
        fig.add_vrect(x0=str(r.start), x1=str(r.end), fillcolor=C2, opacity=0.10, line_width=0, layer="below",
                      **({"row": "all", "col": 1} if rows else {}))


def charts(P, A, EP):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    cd = OUT / "charts"; cd.mkdir(exist_ok=True)
    daily = q("chart_daily", """SELECT series_id, date, value FROM v_observations WHERE date <= current_date AND series_id IN
             ('stored_energy_ear','cmo_power_cost','thermal_generation_share') ORDER BY date""")
    daily["date"] = pd.to_datetime(daily["date"])
    g = {k: v.set_index("date").value for k, v in daily.groupby("series_id")}
    # 1 EAR / CMO / thermal with episode shading (stacked panels, no dual axis)
    f = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                      subplot_titles=("Stored energy EAR, % (stored_energy_ear, ONS, daily)",
                                      "Marginal cost CMO SE/CO, R$/MWh (cmo_power_cost, ONS, weekly)",
                                      "Thermal share of generation, % (thermal_generation_share, ONS, 7-day mean)"))
    f.add_trace(go.Scatter(x=g["stored_energy_ear"].index, y=g["stored_energy_ear"], name="EAR %", line=dict(color=C1, width=2)), 1, 1)
    f.add_hline(y=40, line=dict(color=GREY, dash="dot", width=1), row=1, col=1)
    cm = g["cmo_power_cost"].loc["2015-01-01":]
    f.add_trace(go.Scatter(x=cm.index, y=cm, name="CMO R$/MWh", line=dict(color=C2, width=2)), 2, 1)
    th = g["thermal_generation_share"].rolling(7).mean()
    f.add_trace(go.Scatter(x=th.index, y=th, name="Thermal share %", line=dict(color=C4, width=2)), 3, 1)
    _shade(f, EP, rows=True)
    _layout(f, "Droughts 2015-2026: storage, power cost and thermal dispatch (shaded = EAR < 40% for >= 90 days)", 820)
    f.write_html(cd / "1_ear_cmo_thermal.html", include_plotlyjs="cdn")
    # 2 CMO 2005-2026
    cw = g["cmo_power_cost"]
    f = go.Figure(go.Scatter(x=cw.index, y=cw, name="CMO SE/CO", line=dict(color=C2, width=2)))
    for d0, t in [("2008-01-18", "2008: 637"), ("2014-02-14", "2014: mean 829, max 1,778"), ("2015-01-23", "2015: max 2,159"),
                  ("2021-08-27", "2021: max 3,044")]:
        y0 = cw.loc[:d0].iloc[-1] if len(cw.loc[:d0]) else 0
        f.add_annotation(x=d0, y=y0, text=t, showarrow=True, arrowhead=0, ax=0, ay=-30, font=dict(color="#0b0b0b"))
    _layout(f, "CMO SE/CO weekly, 2005-2026, R$/MWh nominal (cmo_power_cost, ONS)")
    f.write_html(cd / "2_cmo_2005_2026.html", include_plotlyjs="cdn")
    # 3 LP IRFs
    W = R["W2W3"]
    f = make_subplots(rows=2, cols=2, subplot_titles=("Administered IPCA, cumulative pp", "Headline IPCA, cumulative pp",
                                                       "Focus IPCA 12m, change pp", "Selic target, change bp"))
    for (k, rr, cc) in [("admin", 1, 1), ("headline", 1, 2), ("focus_ipca", 2, 1), ("selic_bp", 2, 2)]:
        irf = W[k]["irf"]; h = [r["h"] for r in irf]; b = [r["b"] for r in irf]
        lo = [r["ci90"][0] for r in irf]; hi = [r["ci90"][1] for r in irf]
        f.add_trace(go.Scatter(x=h + h[::-1], y=hi + lo[::-1], fill="toself", fillcolor="rgba(42,120,214,0.15)", line=dict(width=0),
                               showlegend=False, hoverinfo="skip"), rr, cc)
        f.add_trace(go.Scatter(x=h, y=b, name=k, line=dict(color=C1, width=2), mode="lines+markers", marker=dict(size=8),
                               showlegend=False), rr, cc)
        f.add_hline(y=0, line=dict(color=GREY, width=1), row=rr, col=cc)
    f.update_xaxes(title_text="months after shock (h)")
    _layout(f, "Local projections: response to 10 pts of EAR below 40%, 2015-2026 (90% block-bootstrap band)", 700)
    f.write_html(cd / "3_lp_irfs.html", include_plotlyjs="cdn")
    # 4 EAR band boxplots
    d = P.loc["2015-01-01":, ["stored_energy_ear", "cmo_real"]].dropna().copy()
    d["period"] = np.where(d.index < "2022-01-01", "2015-21", "2022-26")
    d["band"] = pd.cut(d.stored_energy_ear, [20, 30, 40, 50, 60, 101], labels=["20-30", "30-40", "40-50", "50-60", "60+"], right=False)
    f = go.Figure()
    for per, col in [("2015-21", C2), ("2022-26", C1)]:
        z = d[d.period == per]
        f.add_trace(go.Box(x=z.band.astype(str), y=z.cmo_real, name=per, marker_color=col, boxpoints="all", jitter=0.3, pointpos=0))
    f.update_layout(boxmode="group", hovermode="closest")
    _layout(f, "Real CMO (R$/MWh, Aug-2026 prices) by EAR band: 2015-21 vs 2022-26 (bands < 40 have no post-2022 months)")
    f.update_layout(hovermode="closest")
    f.write_html(cd / "4_ear_band_boxplots.html", include_plotlyjs="cdn")
    # 5 SPEI / heat / yield (three panels)
    f = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                      subplot_titles=("SPEI (wb/EN.CLC.SPEI.XD.BR; lower = drier)", "Heat-index-35 days (wb/EN.CLC.HEAT.XD.BR)",
                                      "Cereal yield, % change y/y (wb/AG.YLD.CREL.KG.BR)"))
    s = A["wb/EN.CLC.SPEI.XD.BR"].dropna(); hd = A["wb/EN.CLC.HEAT.XD.BR"].dropna()
    yl = (100 * np.log(A["wb/AG.YLD.CREL.KG.BR"]).diff()).dropna()
    f.add_trace(go.Bar(x=s.index, y=s, name="SPEI", marker_color=[C2 if v < 0 else C1 for v in s]), 1, 1)
    f.add_trace(go.Bar(x=hd.index, y=hd, name="Heat-35 days", marker_color=C4), 2, 1)
    f.add_trace(go.Bar(x=yl.index, y=yl, name="Cereal yield y/y %", marker_color=C3), 3, 1)
    _layout(f, "Climate trend and crop yields, 1960-2024 (World Bank via Dateno)", 820)
    f.write_html(cd / "5_spei_heat_yield.html", include_plotlyjs="cdn")
    # 6 load growth vs fitted (residual)
    w7 = R["W7"]["by_year"]
    ys = sorted(w7); lg = [w7[y]["load_g"] for y in ys]
    res = [w7[y]["resid_full"] if w7[y]["resid_full"] is not None else w7[y]["resid_ibc_only"] for y in ys]
    f = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Load growth, % y/y (electricity_load, ONS)",
                                                                          "Unexplained growth: residual after CDD and IBC-Br (fit 2016-22), pp"))
    f.add_trace(go.Bar(x=ys, y=lg, name="Load y/y %", marker_color=C1), 1, 1)
    f.add_trace(go.Bar(x=ys, y=res, name="Residual pp", marker_color=[C2 if (y >= 2023) else GREY for y in ys]), 2, 1)
    f.add_hline(y=2, line=dict(color=GREY, dash="dot"), row=2, col=1)
    _layout(f, "Demand check: did load outrun heat and activity in 2023-25? (2025 residual from IBC-only model)", 700)
    f.write_html(cd / "6_load_vs_cdd_residual.html", include_plotlyjs="cdn")
    # 7 Axia / Petrobras generation
    f = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Axia generation, GWh/month (generation_gwh@AXIA, ONS)",
                                                                          "Petrobras generation, GWh/month (generation_gwh@PETR, ONS)"))
    ax = P["generation_gwh@AXIA"].dropna(); pe = P["generation_gwh@PETR"].dropna()
    f.add_trace(go.Scatter(x=ax.index, y=ax, name="Axia", line=dict(color=C1, width=2)), 1, 1)
    f.add_trace(go.Scatter(x=pe.index, y=pe, name="Petrobras", line=dict(color=C2, width=2)), 2, 1)
    _shade(f, EP[EP.end.astype(str) >= "2016-01-01"], rows=True)
    _layout(f, "Company channel: hydro-heavy Axia vs thermal-heavy Petrobras in drought episodes (shaded)", 700)
    f.write_html(cd / "7_axia_petrobras_generation.html", include_plotlyjs="cdn")


# ----------------------------------------------------------------------------- scenarios
FID = {}   # semantic key -> external fact ids (filled from external_facts.csv by fact_ids())


def fact_ids():
    f = OUT / "external_facts.csv"
    if not f.exists():
        return
    ef = pd.read_csv(f)
    for ch, g in ef.groupby("channel"):
        FID[ch] = ";".join(g.fact_id.astype(str))


def fx(*chs):
    return ";".join(FID.get(c, "") for c in chs if FID.get(c)).strip(";")


def scenarios():
    fact_ids()
    W = R
    ep_gap_admin = W["episode_placebo"]["episode_mean"][0] - W["episode_placebo"]["all_months_mean"][0]
    ep_gap_head = W["episode_placebo"]["episode_mean"][1] - W["episode_placebo"]["all_months_mean"][1]
    # base states; prior = plan B4; data = this study; used = rule (replace when midpoints differ > 50%)
    S = {
     "Wet": dict(cmo="0-150", admin=(0, 0), head=(0, 0), focus=(0, 0), selic=(0, 0), gdp=(0, 0), axia="+0 to +5%",
                 petr="thermal 0.5-1.0x non-episode level (~400-800 GWh/m)", agro=(0, 3), analog="2022-2025 (0 days EAR < 40)",
                 prior=dict(selic=(0, 0), gdp=(0, 0))),
     "One drought year": dict(cmo="300-600", admin=(1, 3), head=(0.3, 1.0), focus=(0, 0.3), selic=(0, 50), gdp=(-0.1, -0.5),
                 axia="-3 to -8% (annual)", petr="thermal 1.5-2.5x (episode mean 1,988 vs 817 GWh/m)", agro=(-5, 3),
                 analog="2017, 2018, 2019-20 episodes (EAR min 18-25, CMO 250-410 mean)",
                 prior=dict(selic=(25, 75), gdp=(-0.1, -0.3))),
     "Severe": dict(cmo="500-900 (weeks > 1,000)", admin=(3, 6), head=(1.0, 2.0), focus=(0.2, 0.8), selic=(25, 150), gdp=(-0.3, -1.0),
                 axia="-8 to -15% (2021: -11% vs 2020)", petr="thermal 3-4x (2021: 28.1 TWh vs 7.5 in 2022)", agro=(-6, 4),
                 analog="2014-15, 2021 (CMO max 2,159 / 3,044; admin 16.8 / 15.8)",
                 prior=dict(selic=(75, 200), gdp=(-0.3, -0.6))),
     "Rationing tail": dict(cmo="> 900, administrative cuts", admin=(6, 10), head=(2.0, 3.5), focus=(0.8, 1.5), selic=(100, 300),
                 gdp=(-1.5, -2.5), axia="-15 to -25% (volume curtailed)", petr="thermal maxed; LNG imports", agro=(-8, 2),
                 analog="2001 (GDP 1.4% vs 4.4/3.1 neighbours = -2.3 pts; kWh/cap -7.8%)",
                 prior=dict(selic=(200, 400), gdp=(-1.0, -2.0))),
    }
    prob = {"Wet": "medium (SIN EAR 60.7% on 2026-10-04 vs 23.8% in 2021; 2022-26 had 0 days < 40)",
            "One drought year": "medium (very strong El Niño 2026-27: N/NE drier, SE/CO ambiguous - 2015/16 101.6% vs 2023/24 68.4% MLT)",
            "Severe": "low (needs two poor wet seasons from 60% storage; 2014-15 / 2021 started from ~20-35%)",
            "Rationing tail": "low (< 5%: WS ~30%, thermal fleet, but LRCAP 2026 only 2.2 of 4.2 GW contracted)"}
    rows = []
    for st, v in S.items():
        for pol in ["pass-through", "suppression"]:
            for div in ["WS 35-40% + storage/transmission", "WS 35-40% without storage/transmission"]:
                a0, a1 = v["admin"]; h0, h1 = v["head"]; f0, f1 = v["focus"]; s0, s1 = v["selic"]
                dmul = 0.8 if div.startswith("WS 35-40% +") and st != "Wet" else 1.0   # W6: point estimates ~ -25% log CMO in bands >= 40 (not significant)
                if pol == "suppression" and st != "Wet":
                    adm = (round(a0 * 0.2 * dmul, 1), round(a1 * 0.3 * dmul, 1)); hd = (round(h0 * 0.3 * dmul, 1), round(h1 * 0.4 * dmul, 1))
                    fisc = {"One drought year": "R$ 10-25bn", "Severe": "R$ 25-60bn", "Rationing tail": "R$ 50-100bn"}[st]
                    sel = (round(s0 * 0.5), round(s1 * 0.75))     # credibility/fiscal premium offsets part of the inflation relief
                else:
                    adm = (round(a0 * dmul, 1), round(a1 * dmul, 1)); hd = (round(h0 * dmul, 1), round(h1 * dmul, 1)); fisc = "0"
                    sel = (round(s0 * dmul), round(s1 * dmul))
                rows.append({"hydro_state": st, "policy": pol, "diversification": div, "probability_qual": prob[st],
                    "cmo_mean_range_brl_mwh": v["cmo"], "admin_ipca_pp_range": f"{adm[0]:+} to {adm[1]:+}",
                    "headline_ipca_pp_range": f"{hd[0]:+} to {hd[1]:+}", "focus_shift_pp": f"{f0 * dmul:+.1f} to {f1 * dmul:+.1f}",
                    "selic_modifier_bp": f"{sel[0]:+} to {sel[1]:+}", "selic_prior_bp": f"{v['prior']['selic'][0]:+} to {v['prior']['selic'][1]:+}",
                    "gdp_pts": f"{v['gdp'][0]:+} to {v['gdp'][1]:+}", "gdp_prior_pts": f"{v['prior']['gdp'][0]:+} to {v['prior']['gdp'][1]:+}",
                    "agro_export_usd_bn": f"{v['agro'][0]:+} to {v['agro'][1]:+} (volume vs coffee/sugar price offset)",
                    "axia_generation_pct": v["axia"], "petrobras_thermal": v["petr"], "fiscal_cost_if_suppressed_brl_bn": fisc,
                    "eu_access_modifier": ("none" if st == "Wet" else
                        "fire-year tail: EUDR/high-risk reclassification probability low -> medium; -$2 to -5bn on the exports EU cell; no penalty seen in 2016/2017/2024"),
                    "analogue_years": v["analog"],
                    "warehouse_series": "stored_energy_ear;cmo_power_cost;ipca_administered_prices;ipca_monthly;focus_ipca_12m;selic_target;ibc_br;generation_gwh@AXIA;generation_gwh@PETR;exports_to_eu",
                    "external_fact_ids": fx("hydrology_outlook", "enso", "tariff_flags", "ipca_weights") + (";" + fx("fiscal_suppression") if pol == "suppression" else "")
                                          + (";" + fx("rationing_2001") if st == "Rationing tail" else "") + (";" + fx("fire_eudr") if st != "Wet" else ""),
                    "rule_note": "Selic and GDP ranges replaced from plan priors where W3/W4 data midpoints differed > 50% (prior kept in *_prior columns)"})
    sm = pd.DataFrame(rows)
    # best / worst
    best = {"hydro_state": "BEST", "policy": "pass-through (flags green)", "diversification": "WS 35-40% + storage/transmission",
            "probability_qual": "medium", "cmo_mean_range_brl_mwh": "0-150", "admin_ipca_pp_range": "-1 to 0 (admin < 3-4%/yr; green flag)",
            "headline_ipca_pp_range": "-0.3 to 0", "focus_shift_pp": "-0.2 to 0", "selic_modifier_bp": "-50 to 0",
            "gdp_pts": "0 to +0.2", "agro_export_usd_bn": "+0 to +5 (record crops)", "axia_generation_pct": "+0 to +5%",
            "petrobras_thermal": "minimal", "fiscal_cost_if_suppressed_brl_bn": "0", "eu_access_modifier": "none",
            "analogue_years": "2023 (EAR 77.5, CMO 0, agri VA +16.3%)", "external_fact_ids": fx("hydrology_outlook", "enso", "agro")}
    worst = {"hydro_state": "WORST", "policy": "suppression in election year 2030", "diversification": "without storage/transmission; load +5-7%/yr",
             "probability_qual": "low", "cmo_mean_range_brl_mwh": "> 900", "admin_ipca_pp_range": "+6 to +10 (pass-through) or R$ 40-100bn fiscal",
             "headline_ipca_pp_range": "+2.0 to +3.5 (or +0.6 to +1.4 if suppressed)", "focus_shift_pp": "+0.8 to +1.6",
             "selic_modifier_bp": "+100 to +300", "gdp_pts": "-1.0 to -2.5", "agro_export_usd_bn": "-8 to +2",
             "axia_generation_pct": "-15 to -25%", "petrobras_thermal": "maxed", "fiscal_cost_if_suppressed_brl_bn": "R$ 40-100bn",
             "eu_access_modifier": "fire year + EUDR high-risk tail: -$2 to -5bn", "analogue_years": "2001 + 2021 + 2022 policy",
             "external_fact_ids": fx("rationing_2001", "fiscal_suppression", "fire_eudr", "load_datacentre")}
    sm = pd.concat([sm, pd.DataFrame([best, worst])], ignore_index=True)
    sm.to_csv(OUT / "scenario_matrix.csv", index=False)
    # cross-tab vs ToT states (exports study 6b)
    ct = pd.DataFrame([
        {"state": "ToT +10% (exports study)", "headline_ipca_pp": "-1.1 (reduced-form, Dec/Dec)", "selic_bp": "reduced-form -500 (2002/2015-driven; not causal)",
         "gdp": "+2.3 to +3.1 GDP-pc growth pts (upper bound); ~+1.5% GDP income", "exports_usd_bn_yr": "+14 to +22"},
        {"state": "ToT -10% (exports study)", "headline_ipca_pp": "+1.1", "selic_bp": "reduced-form +500 (not causal)",
         "gdp": "-2.3 to -3.1 pts (upper bound); ~-1.5% GDP income", "exports_usd_bn_yr": "-14 to -22"},
        {"state": "Hydro best (wet + diversification)", "headline_ipca_pp": "-0.3 to 0", "selic_bp": "-50 to 0", "gdp": "0 to +0.2", "exports_usd_bn_yr": "0 to +5"},
        {"state": "Hydro one drought year", "headline_ipca_pp": "+0.3 to +1.0", "selic_bp": "0 to +50", "gdp": "-0.1 to -0.5", "exports_usd_bn_yr": "-5 to +3"},
        {"state": "Hydro severe (pass-through)", "headline_ipca_pp": "+1.0 to +2.0", "selic_bp": "+25 to +150", "gdp": "-0.3 to -1.0", "exports_usd_bn_yr": "-6 to +4"},
        {"state": "Hydro worst (rationing tail / suppression 2030)", "headline_ipca_pp": "+2.0 to +3.5 or R$40-100bn fiscal", "selic_bp": "+100 to +300", "gdp": "-1.0 to -2.5", "exports_usd_bn_yr": "-8 to +2 (plus EU tail -2 to -5)"},
        {"state": "Combined: ToT -10% + severe drought", "headline_ipca_pp": "+2.1 to +3.1", "selic_bp": "+25 to +150 on top of the ToT response", "gdp": "-0.3 to -1.0 on top of ToT", "exports_usd_bn_yr": "-20 to -28 (central)"},
        {"state": "Combined: ToT +10% + wet", "headline_ipca_pp": "-1.1 to -1.4", "selic_bp": "-50 to 0 on top of ToT", "gdp": "ToT gain + 0 to +0.2", "exports_usd_bn_yr": "+14 to +27"},
    ])
    ct.to_csv(OUT / "cross_table_tot.csv", index=False)
    R["scenarios"] = {"n_rows": len(sm), "ep_gap_admin_pp": round(ep_gap_admin, 2), "ep_gap_headline_pp": round(ep_gap_head, 2),
                      "cross_table": ct.to_dict("records")}
    return sm, ct


def tornado(sm, ct):
    import plotly.graph_objects as go
    items = [("ToT -10% / +10%", -1.1, 1.1), ("Hydro: wet+diversified (best)", -0.3, 0.0), ("Hydro: one drought year", 0.3, 1.0),
             ("Hydro: severe, pass-through", 1.0, 2.0), ("Hydro: severe, suppression", 0.3, 0.8), ("Hydro: rationing tail", 2.0, 3.5)]
    items2 = [("ToT -10% / +10%", -22, 22), ("Hydro: wet+diversified (best)", 0, 5), ("Hydro: one drought year", -5, 3),
              ("Hydro: severe", -6, 4), ("Hydro: rationing tail + EU fire tail", -13, 2)]
    from plotly.subplots import make_subplots
    f = make_subplots(rows=1, cols=2, subplot_titles=("Headline IPCA, pp (range)", "Exports, US$bn/yr (range)"), horizontal_spacing=0.25)
    for i, (lab, lo, hi) in enumerate(items):
        f.add_trace(go.Bar(y=[lab], x=[hi - lo], base=[lo], orientation="h", marker_color=GREY if lab.startswith("ToT") else C2,
                           name=lab, showlegend=False, hovertemplate=f"{lab}: {lo:+} to {hi:+} pp<extra></extra>"), 1, 1)
    for i, (lab, lo, hi) in enumerate(items2):
        f.add_trace(go.Bar(y=[lab], x=[hi - lo], base=[lo], orientation="h", marker_color=GREY if lab.startswith("ToT") else C1,
                           name=lab, showlegend=False, hovertemplate=f"{lab}: {lo:+} to {hi:+} bn<extra></extra>"), 1, 2)
    _layout(f, "Scenario tornado 2027-30: hydrology states vs the exports study's ToT +/-10% states (grey)", 560)
    f.update_layout(hovermode="closest")
    f.write_html(OUT / "charts" / "8_scenario_tornado_vs_tot.html", include_plotlyjs="cdn")


# ----------------------------------------------------------------------------- run
if __name__ == "__main__":
    load_meta()
    anchors()
    P = monthly_panel()
    A = annual_panel()
    P.to_csv(OUT / "hydro_panel_monthly.csv")
    A.to_csv(OUT / "hydro_panel_annual.csv")
    EP = episodes(P)
    w1_price(P)
    w2_w3_local_projections(P)
    w4_output(P, A)
    w5_agro(A, P)
    w6_bands(P)
    w7_demand(A, P)
    w8_trend(A)
    w9_companies(P)
    w10_eu(A)
    w11_policy(P, A)
    charts(P, A, EP)
    SM, CT = scenarios()
    tornado(SM, CT)
    # BH over primary p-values
    prim = {k: R[k].get("p_primary") for k in ["W1", "W4", "W5", "W6", "W8"] if R[k].get("p_primary") is not None}
    a12 = R["W2W3"]["admin"]["irf"][12]; prim["W2"] = a12.get("p_boot")
    prim["W3"] = R["W2W3"]["focus_peak"].get("p_boot")
    ks = list(prim); qs = bh([prim[k] for k in ks])
    R["bh"] = {k: {"p": round(prim[k], 4), "q": round(float(v), 4)} for k, v in zip(ks, qs)}
    R["meta"] = META
    R["sql"] = SQL
    R["run_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    def js(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.bool_,)): return bool(o)
        if isinstance(o, (pd.Timestamp, dt.date)): return str(o)
        return str(o)
    (OUT / "results.json").write_text(json.dumps(R, default=js, indent=1))
    print(json.dumps({k: R[k] for k in R if k not in ("meta", "sql", "anchors", "episodes")}, default=js, indent=1)[:60000])
    print(EP.to_string())
