"""Testing "Brazil is the New America" (Davidson 2012) against the Brazil Monitoring warehouse.

Run: /Users/zkid18/proj-personal/brazil-macro/.venv/bin/python brazil_thesis_test.py

PITFALLS (carried from plan.md):
- Native monthly dates are first-of-month; WB GEM monthly (wb/*_M.BRA) are month-end; WB/ILO annual are
  YYYY-12-31. Always join monthly data on date_trunc('month', date), annual via v_annual.
- v_annual uses catalog.agg (mean / last / sum). For returns (equity, FX) use year-end arg_max(value, date),
  never the mean roll-up of ibovespa_usd / brl_usd.
- wb/FR.INR.RINR.BR is the WB real LENDING rate, not the real policy rate.
- wb/TOT.BRA must be validated against wb/TT.PRI.MRCH.XD.WD.BR (rho > 0.9) before use.
- embi_brazil ends 2024-07; Doing Business ends 2019; PISA ends 2015; GFDD ends 2021.
- credit_gdp (BCB) and wb/FS.AST.PRVT.GD.ZS.BR differ by ~20 pts by definition.
- WB 2025 values are preliminary. Filter date <= current_date everywhere.
- No scipy/statsmodels: CIs via moving-block bootstrap, p-values via permutation (numpy only).
- Plotly HTML only (no PNG export).
- No peer countries in the warehouse: Brazil-vs-US comparisons only via inherently US-relative WB series.
"""
import json
import warnings
warnings.filterwarnings('ignore')
import os

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DB = "/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb"
OUT = os.path.dirname(os.path.abspath(__file__))
CH = os.path.join(OUT, "charts")
os.makedirs(CH, exist_ok=True)
con = duckdb.connect(DB, read_only=True)
N_BOOT = 2000
BREAK = 2010
TODAY = con.execute("select current_date").fetchone()[0]


# ----------------------------------------------------------------------------- helpers: data
def q(sql, params=None):
    return con.execute(sql, params or []).df()


_META = {}
_USED = set()


def meta(sid):
    if sid not in _META:
        r = q("""select c.source, c.agg, c.role, c.title, c.unit, c.freq,
                 (select max(date) from v_observations o where o.series_id = c.series_id
                   and o.date <= current_date and o.value is not null) as last_date
                 from catalog c where series_id = ?""", [sid])
        if r.empty:
            raise KeyError(sid)
        d = r.iloc[0].to_dict()
        d["last_date"] = str(pd.Timestamp(d["last_date"]).date()) if pd.notna(d["last_date"]) else None
        _META[sid] = d
    _USED.add(sid)
    return _META[sid]


def src(sids):
    if isinstance(sids, str):
        sids = [sids]
    return [{"series_id": s, "source": meta(s)["source"], "last_date": meta(s)["last_date"]} for s in sids]


def tag(value, sids, sql=None, note=None, **kw):
    d = {"value": _clean(value), "series": src(sids)}
    if sql:
        d["sql"] = " ".join(sql.split())
    if note:
        d["note"] = note
    d.update({k: _clean(v) for k, v in kw.items()})
    return d


def _clean(v):
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else round(float(v), 4)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


SQL_ANN = "SELECT year, value FROM v_annual WHERE series_id = ? AND is_complete AND year <= {y} ORDER BY year"


def ann(sid, complete=True, upto=None):
    """Annual values from v_annual (catalog.agg roll-up)."""
    meta(sid)
    upto = upto or TODAY.year
    cond = "AND is_complete" if complete else ""
    df = q(f"SELECT year, value FROM v_annual WHERE series_id = ? {cond} AND year <= ? ORDER BY year", [sid, upto])
    return df.set_index("year")["value"].astype(float)


def year_end(sid):
    meta(sid)
    df = q("""SELECT EXTRACT(year FROM date)::INT AS year, arg_max(value, date) AS v FROM v_observations
              WHERE series_id = ? AND date <= current_date GROUP BY 1 ORDER BY 1""", [sid])
    return df.set_index("year")["v"].astype(float)


def mon(sid, how="mean"):
    """Monthly series keyed on month start; how = 'mean' or 'last' (arg_max)."""
    meta(sid)
    agg = "arg_max(value, date)" if how == "last" else "avg(value)"
    df = q(f"""SELECT date_trunc('month', date) AS ym, {agg} AS v FROM v_observations
               WHERE series_id = ? AND date <= current_date AND value IS NOT NULL GROUP BY 1 ORDER BY 1""", [sid])
    s = df.set_index("ym")["v"].astype(float)
    s.index = pd.to_datetime(s.index)
    return s


def obs(sid):
    meta(sid)
    df = q("SELECT date, value FROM v_observations WHERE series_id = ? AND date <= current_date ORDER BY date", [sid])
    s = df.set_index("date")["value"].astype(float)
    s.index = pd.to_datetime(s.index)
    return s


def logdiff(s, k=1):
    s = s[s > 0]
    return np.log(s).diff(k)


def val(s, key):
    try:
        return float(s.loc[key])
    except KeyError:
        return np.nan


# ----------------------------------------------------------------------------- helpers: stats
def _corr(x, y):
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _rank(a):
    return pd.Series(a).rank().to_numpy()


def mbb_idx(n, block, rng):
    block = max(1, min(block, n))
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, nb)
    return (starts[:, None] + np.arange(block)).ravel()[:n]


def block_bootstrap_corr(x, y, block, n_boot=N_BOOT, seed=0):
    rng = np.random.default_rng(seed)
    n = len(x)
    rs = np.empty(n_boot)
    for b in range(n_boot):
        i = mbb_idx(n, block, rng)
        rs[b] = _corr(x[i], y[i])
    rs = rs[np.isfinite(rs)]
    return float(np.percentile(rs, 2.5)), float(np.percentile(rs, 97.5))


def perm_pvalue(x, y, n=N_BOOT, seed=1):
    rng = np.random.default_rng(seed)
    r0 = abs(_corr(x, y))
    c = sum(abs(_corr(x, rng.permutation(y))) >= r0 for _ in range(n))
    return (c + 1) / (n + 1)


def align(*ss):
    df = pd.concat(ss, axis=1).dropna()
    return df


def corr_stats(x, y, block, min_n, label=None, boot=True):
    df = align(x, y)
    n = len(df)
    out = {"n": n}
    if df.empty:
        out["insufficient"] = True
        return out
    out["start"], out["end"] = str(df.index[0])[:10], str(df.index[-1])[:10]
    if n < min_n:
        out["insufficient"] = True
        out["pearson"] = _corr(df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy())
        return out
    a, b = df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()
    out["pearson"] = _corr(a, b)
    out["spearman"] = _corr(_rank(a), _rank(b))
    if boot:
        out["ci95"] = block_bootstrap_corr(a, b, block)
        out["p_perm"] = perm_pvalue(a, b)
    return out


def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + [np.asarray(c) for c in X])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    r2 = 1 - resid.var() / y.var() if y.var() > 0 else np.nan
    return beta, r2, resid


def boot_ols(y, X, block, n_boot=N_BOOT, seed=2):
    """Point estimates + moving-block bootstrap 95% CI for every coefficient."""
    y = np.asarray(y)
    X = [np.asarray(c) for c in X]
    beta, r2, _ = ols(y, X)
    rng = np.random.default_rng(seed)
    bs = np.empty((n_boot, len(beta)))
    for b in range(n_boot):
        i = mbb_idx(len(y), block, rng)
        bs[b] = ols(y[i], [c[i] for c in X])[0]
    ci = np.percentile(bs, [2.5, 97.5], axis=0).T
    return {"beta": beta.tolist(), "ci95": ci.tolist(), "r2": r2, "n": len(y)}


def ccf(x, y, lags):
    """rho(x_t, y_{t+k}) for k in lags."""
    res = {}
    for k in lags:
        df = align(x, y.shift(-k))
        res[k] = (_corr(df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()), len(df))
    return res


def _year(idx):
    return idx.year if hasattr(idx, "year") else np.asarray(idx)


def split_stats(x, y, block, min_n, break_year=BREAK):
    df = align(x, y)
    yrs = np.asarray(_year(df.index))
    out = {}
    for name, m in [("full", np.ones(len(df), bool)), ("pre", yrs <= break_year), ("post", yrs > break_year),
                    ("pre2012", yrs <= 2012), ("post2012", yrs > 2012), ("ex2020", yrs != 2020)]:
        d = df[m]
        out[name] = corr_stats(d.iloc[:, 0], d.iloc[:, 1], block, min_n)
    return out


def interaction(x, y, block, break_year=BREAK):
    """y ~ x + post + post*x ; returns bootstrap CI on the post*x coefficient."""
    df = align(x, y)
    if len(df) < 20:
        return None
    post = (np.asarray(_year(df.index)) > break_year).astype(float)
    xv, yv = df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()
    r = boot_ols(yv, [xv, post, post * xv], block)
    return {"beta_x": r["beta"][1], "beta_x_ci": r["ci95"][1], "beta_post_x": r["beta"][3],
            "beta_post_x_ci": r["ci95"][3], "r2": r["r2"], "n": r["n"]}


def rolling_corr(x, y, window):
    df = align(x, y)
    return df.iloc[:, 0].rolling(window).corr(df.iloc[:, 1]).dropna()


def trend_pct(s):
    """Log-linear trend %/yr of a positive annual (int index) or dated series."""
    s = s[s > 0].dropna()
    if len(s) < 5:
        return np.nan
    t = np.asarray(s.index.year + (s.index.month - 1) / 12 if hasattr(s.index, "month") else s.index, float)
    return float((np.exp(np.polyfit(t, np.log(s.to_numpy()), 1)[0]) - 1) * 100)


def cagr(s, y0, y1):
    a, b = val(s, y0), val(s, y1)
    return (b / a) ** (1 / (y1 - y0)) * 100 - 100 if a > 0 and b > 0 else np.nan


def boot_mean_diff(a, b, block=3, n_boot=N_BOOT, seed=3):
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    d = np.empty(n_boot)
    for i in range(n_boot):
        d[i] = a[mbb_idx(len(a), block, rng)].mean() - b[mbb_idx(len(b), block, rng)].mean()
    return float(a.mean() - b.mean()), [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]


def fmt(v, d=1):
    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:,.{d}f}"


# ============================================================================= 0. anchors
def s0_anchors():
    rows = []

    def chk(name, sid, got, exp, tol_rel=0.02, tol_abs=None):
        ok = abs(got - exp) <= (tol_abs if tol_abs is not None else tol_rel * max(abs(exp), 1e-9))
        rows.append({"anchor": name, "series": sid, "expected": exp, "got": round(float(got), 4), "match": bool(ok)})

    oil = ann("oil_production", complete=False)
    chk("oil_production 2010 mean kbd", "oil_production", oil[2010], 2137)
    chk("oil_production 2026 YTD mean kbd", "oil_production", oil[2026], 4368)
    chk("oil_production Jul 2026 kbd", "oil_production", mon("oil_production")["2026-07-01"], 4601)
    ws = ann("wind_solar_generation_share", complete=False)
    chk("wind_solar_generation_share 2015 %", "wind_solar_generation_share", ws[2015], 4.7, tol_abs=0.2)
    chk("wind_solar_generation_share 2025 %", "wind_solar_generation_share", ws[2025], 29.8, tol_abs=0.3)
    for sid, y0, e0, y1, e1, ta in [("wb/EG.ELC.HYRO.ZS.BR", 2010, 78.2, 2024, 56.1, 0.2),
                                     ("wb/ER.H2O.FWTL.ZS.BR", 2010, 1.32, 2022, 1.20, 0.02),
                                     ("wb/AG.PRD.CREL.MT.BR", 2010, 75.2e6, 2024, 139.0e6, None),
                                     ("wb/AG.YLD.CREL.KG.BR", 2010, 4041, 2024, 5003, None),
                                     ("wb/GOV_WGI_CC_EST.BR", 2010, -0.015, 2024, -0.409, 0.01),
                                     ("wb/NY.GDP.PCAP.PP.KD.BR", 2010, 18062, 2025, 20025, None),
                                     ("wb/PA.NUS.GDP.PLI.BR", 2010, 78.9, 2025, 45.7, 0.2)]:
        s = ann(sid)
        chk(f"{sid} {y0}", sid, val(s, y0), e0, tol_abs=ta)
        chk(f"{sid} {y1}", sid, val(s, y1), e1, tol_abs=ta)
    cg = ann("credit_gdp", complete=False)
    chk("credit_gdp 2010 (Dec)", "credit_gdp", cg[2010], 44.1, tol_abs=0.3)
    chk("credit_gdp 2008 (Dec)", "credit_gdp", cg[2008], 39.7, tol_abs=0.3)
    chk("credit_gdp Aug 2026", "credit_gdp", mon("credit_gdp")["2026-08-01"], 55.4, tol_abs=0.3)
    hd = ann("household_debt_income", complete=False)
    chk("household_debt_income 2010 mean", "household_debt_income", hd[2010], 31.7, tol_abs=0.5)
    chk("household_debt_income 2026 YTD mean", "household_debt_income", hd[2026], 49.8, tol_abs=0.5)
    rr = ann("real_policy_rate", complete=False)
    chk("real_policy_rate 2010 mean", "real_policy_rate", rr[2010], 5.0, tol_abs=0.2)
    chk("real_policy_rate 2026 YTD mean", "real_policy_rate", rr[2026], 10.4, tol_abs=0.2)
    gini = ann("wb/SI.POV.GINI.BR")
    chk("Gini 2024", "wb/SI.POV.GINI.BR", gini[2024], 50.3, tol_abs=0.1)
    chk("Gini 2008", "wb/SI.POV.GINI.BR", gini[2008], 54.0, tol_abs=0.1)
    ib = year_end("ibovespa_usd")
    chk("Ibovespa USD 2025 return %", "ibovespa_usd", (ib[2025] / ib[2024] - 1) * 100, 50.8, tol_abs=0.5)
    fx = year_end("brl_usd")
    chk("brl_usd year-end 2024", "brl_usd", fx[2024], 6.192, tol_abs=0.01)
    chk("brl_usd year-end 2025", "brl_usd", fx[2025], 5.502, tol_abs=0.01)
    chk("BRL appreciation 2025 %", "brl_usd", (fx[2024] / fx[2025] - 1) * 100, 12.5, tol_abs=0.3)
    tot, xg = ann("wb/FI.RES.TOTL.CD.BR"), ann("wb/FI.RES.XGLD.CD.BR")
    gold = tot - xg
    chk("gold reserves 2010 $bn", "wb/FI.RES.TOTL.CD.BR-XGLD", gold[2010] / 1e9, 1.5, tol_abs=0.15)
    chk("gold reserves 2025 $bn", "wb/FI.RES.TOTL.CD.BR-XGLD", gold[2025] / 1e9, 24.2, tol_abs=0.3)
    chk("gold share of reserves 2025 %", "wb/FI.RES.TOTL.CD.BR-XGLD", gold[2025] / tot[2025] * 100, 6.8, tol_abs=0.1)
    acc = ann("wb/account.t.d.BRA")
    chk("Findex account 2011", "wb/account.t.d.BRA", acc[2011], 55.9, tol_abs=0.2)
    chk("Findex account 2024", "wb/account.t.d.BRA", acc[2024], 86.4, tol_abs=0.2)
    pix = ann("pix_transactions_count") * 1e6  # unit = million_tx
    pop = ann("population")
    chk("Pix count 2025 bn", "pix_transactions_count", pix[2025] / 1e9, 71.3, tol_abs=0.5)
    chk("Pix per person 2025", "pix_transactions_count/population", pix[2025] / pop[2025], 326, tol_abs=5)
    df = pd.DataFrame(rows)
    return df


# ============================================================================= 1. claim map
CLAIMS = []


def claim(cid, area, column, text, status, statistic, threshold, verdict, thesis_dir, sids, note=""):
    """verdict: Supported / Partial / Refuted / Untestable (truth of the note's statement).
    thesis_dir: 'pro' if the statement, when true, favours the Brazil-is-the-new-America thesis; 'con' if it is a
    weakness the note concedes. Thesis score: pro -> S=1,P=.5,R=0; con -> S=0,P=.5,R=1."""
    sids = [s for s in (sids or [])]
    lasts = [meta(s)["last_date"] for s in sids]
    if verdict == "Untestable":
        score = None
    else:
        base = {"Supported": 1.0, "Partial": 0.5, "Refuted": 0.0}[verdict]
        score = base if thesis_dir == "pro" else 1 - base
    CLAIMS.append({"claim_id": cid, "area": area, "pillar": column, "claim": text, "status": status,
                   "statistic": statistic, "threshold": threshold, "verdict": verdict, "thesis_dir": thesis_dir,
                   "thesis_score": score, "series_ids": ";".join(sids), "last_dates": ";".join(str(x) for x in lasts),
                   "note": note})


def stale(sid, cutoff="2022-01-01"):
    return meta(sid)["last_date"] < cutoff


def s1_claim_map(R3):
    R = {}
    # ---------------- ENERGY
    oil = ann("oil_production")
    pre = trend_pct(oil.loc[2000:2010]); post = trend_pct(oil.loc[2011:2025])
    nei = ann("wb/EG.IMP.CONS.ZS.BR")
    R["E1"] = tag({"trend_2000_2010": pre, "trend_2011_2025": post, "net_energy_imports_2000": nei[2000],
                   "net_energy_imports_latest": nei.iloc[-1], "latest_year": int(nei.index[-1])},
                  ["oil_production", "wb/EG.IMP.CONS.ZS.BR"], SQL_ANN)
    v = "Supported" if post > 0 and nei.iloc[-1] < 0 else ("Partial" if post > 0 else "Refuted")
    claim("E1", "Energy", "physical", "Oil production rising (pre-salt)", "T",
          f"trend {fmt(pre)}%/yr 2000-10 vs {fmt(post)}%/yr 2011-25; net energy imports {fmt(nei[2000])}% (2000) -> {fmt(nei.iloc[-1])}% ({nei.index[-1]})",
          "post-2010 trend > 0 and net imports < 0", v, "pro", ["oil_production", "wb/EG.IMP.CONS.ZS.BR"])

    rn = ann("wb/EG.ELC.RNEW.ZS.BR")
    sl = trend_pct(rn.loc[2011:])
    R["E2"] = tag({"renew_elec_2010": rn[2010], "latest": rn.iloc[-1], "latest_year": int(rn.index[-1]),
                   "trend_post2010": sl}, "wb/EG.ELC.RNEW.ZS.BR", SQL_ANN)
    v = "Supported" if rn.iloc[-1] >= 75 and sl >= -0.5 else ("Refuted" if rn.iloc[-1] < 60 else "Partial")
    if stale("wb/EG.ELC.RNEW.ZS.BR") and v == "Supported":
        v = "Partial"
    claim("E2", "Energy", "physical", "One of the cleanest grids", "P",
          f"renewable electricity {fmt(rn[2010])}% (2010) -> {fmt(rn.iloc[-1])}% ({rn.index[-1]}); WS share 2025 cited in E4",
          ">= 75% and not falling", v, "pro", ["wb/EG.ELC.RNEW.ZS.BR"],
          "Level true; series stale (2021) -> Partial; 'one of the cleanest' ranking needs peers (untestable)")
    return R


# The rest of section 1 needs section-3 outputs; assembled in s1_rest().
def s1_rest(R, S3, R3):
    # ---- E3 fragility (from 3d)
    d = S3["3d"]
    ratio = d["low_ear_cmo_ratio"]["value"]
    claim("E3a", "Energy", "physical", "Hydro is core but fragile (drought -> power cost)", "T",
          f"CMO {fmt(ratio, 2)}x higher in months with EAR<40%; drought years 2015/2017/2021 mean CMO {d['drought_table']['value']['drought_mean_cmo']:.0f} vs {d['drought_table']['value']['other_mean_cmo']:.0f} R$/MWh",
          "CMO ratio > 2x in low-EAR months", "Supported" if ratio > 2 else "Refuted", "con",
          ["stored_energy_ear", "cmo_power_cost", "wb/EG.ELC.HYRO.ZS.BR"])
    ear_min = d["ear_min_by_year"]["value"]
    rank2021 = sorted(ear_min, key=lambda k: ear_min[k]).index("2021") + 1
    claim("E3b", "Energy", "physical", "2021 drought worst in 91 years", "P",
          f"national EAR 2021 min {ear_min['2021']:.1f}% ranks #{rank2021} lowest of {len(ear_min)} years (2015-2026); 2017 min {ear_min.get('2017', np.nan):.1f}%",
          "2021 in top-2 stress years", "Partial", "con", ["stored_energy_ear", "cmo_power_cost"],
          "'91 years' refers to SE/CO inflows, not in warehouse; on national EAR and CMO, 2021 is not the sample extreme")
    ws_last = d["ws_share"]["value"]
    shrink = d["slope_shrinks"]["value"]
    v = "Supported" if ws_last >= 20 and shrink else ("Partial" if ws_last >= 20 else "Refuted")
    claim("E4", "Energy", "physical", "Wind+solar now significant; diversification makes the thesis sturdier", "T",
          f"WS share 2025 {fmt(ws_last)}%; EAR->logCMO slope 2015-21 {fmt(d['subsample_slopes']['value']['2015_2021'], 3)} vs 2022-26 {fmt(d['subsample_slopes']['value']['2022_2026'], 3)}",
          "share >= 20% and EAR->CMO sensitivity smaller in 2022-26", v, "pro",
          ["wind_solar_generation_share", "stored_energy_ear", "cmo_power_cost"],
          "log slope did not shrink (CMO ~0 floor in 2022-23); levels slope fell ~2/3 but confounded by full reservoirs since 2022")
    for cid, text, sids, note in [
        ("E5", "Cane ethanol E30 / flex-fuel", ["wb/EG.USE.CRNW.ZS.BR"], "no ethanol series; proxy combustible renewables % energy only"),
        ("E6", "Caatinga solar", [], "no regional data"),
        ("E7", "EU CBAM favours Brazilian charcoal / clean steel", ["exports_to_eu"], "no steel/charcoal series")]:
        claim(cid, "Energy", "physical", text, "U", "", "", "Untestable", "pro", sids, note)

    # ---------------- WATER
    fw = ann("wb/ER.H2O.FWTL.ZS.BR")
    sl = float(np.polyfit(fw.loc[2000:].index, fw.loc[2000:].values, 1)[0])
    R["W1"] = tag({"withdrawal_pct_2010": fw[2010], "latest": fw.iloc[-1], "latest_year": int(fw.index[-1]),
                   "slope_pts_per_yr_2000+": sl}, "wb/ER.H2O.FWTL.ZS.BR", SQL_ANN)
    v = "Supported" if fw.iloc[-1] < 5 and abs(sl) < 0.05 else ("Refuted" if fw.iloc[-1] > 20 else "Partial")
    claim("W1", "Water", "physical", "Huge freshwater; withdrawals far below renewal", "T",
          f"withdrawals {fmt(fw.iloc[-1], 2)}% of internal resources ({fw.index[-1]}); slope {sl:+.3f} pts/yr",
          "< 5% and flat", v, "pro", ["wb/ER.H2O.FWTL.ZS.BR"])
    claim("W2", "Water", "physical", "Contrast with Ogallala / North China Plain / Punjab", "U", "", "", "Untestable", "pro", [],
          "no peer data")
    fr = ann("wb/AG.LND.FRST.K2.BR"); spei = ann("wb/EN.CLC.SPEI.XD.BR")
    R["W3_context"] = tag({"forest_1990": fr[1990], "forest_latest": fr.iloc[-1], "forest_change_pct": (fr.iloc[-1] / fr[1990] - 1) * 100,
                           "spei_mean_2011_2023": spei.loc[2011:].mean(), "spei_mean_1991_2010": spei.loc[1991:2010].mean()},
                          ["wb/AG.LND.FRST.K2.BR", "wb/EN.CLC.SPEI.XD.BR"], SQL_ANN,
                          note="context only (not a note claim; not scored)")

    # ---------------- AGRO
    P, A, Y = ann("wb/AG.PRD.CREL.MT.BR"), ann("wb/AG.LND.CREL.HA.BR"), ann("wb/AG.YLD.CREL.KG.BR")
    dec = {}
    for (y0, y1) in [(1977, 2010), (2010, 2024), (1977, 2024)]:
        dp, da = np.log(P[y1] / P[y0]), np.log(A[y1] / A[y0])
        dec[f"{y0}_{y1}"] = {"prod_growth_pct": (P[y1] / P[y0] - 1) * 100, "area_share": da / dp, "yield_share": 1 - da / dp,
                             "prod_start_Mt": P[y0] / 1e6, "prod_end_Mt": P[y1] / 1e6}
    R["A1"] = tag(dec, ["wb/AG.PRD.CREL.MT.BR", "wb/AG.LND.CREL.HA.BR", "wb/AG.YLD.CREL.KG.BR"], SQL_ANN)
    ys = [dec[k]["yield_share"] for k in ["1977_2010", "2010_2024"]]
    v = "Supported" if min(ys) > 0.5 else ("Refuted" if max(ys) < 0.5 else "Partial")
    claim("A1", "Agro", "physical", "Grain output 47 Mt (1977) -> 354 Mt with far smaller area growth", "T",
          f"cereals {dec['1977_2010']['prod_start_Mt']:.0f} -> {dec['2010_2024']['prod_end_Mt']:.0f} Mt; yield share of output growth {ys[0]:.0%} (1977-2010), {ys[1]:.0%} (2010-24), {dec['1977_2024']['yield_share']:.0%} (1977-2024)",
          "yield share > 50% in both windows", v, "pro", ["wb/AG.PRD.CREL.MT.BR", "wb/AG.LND.CREL.HA.BR", "wb/AG.YLD.CREL.KG.BR"],
          "WB cereals only (soy excluded); the 47->354 Mt CONAB 'grãos' levels are not in the warehouse; post-2010 growth is mostly AREA (second-crop corn)")
    ex = {s: ann(s) for s in ["soy_exports", "beef_exports", "coffee_exports", "sugar_exports"]}
    g = {s: (ex[s][2025] / ex[s][2014] - 1) * 100 for s in ex}
    R["A2"] = tag({s: {"2014_usd_bn": ex[s][2014] / 1e9, "2025_usd_bn": ex[s][2025] / 1e9, "growth_pct": g[s]} for s in ex},
                  list(ex), SQL_ANN)
    claim("A2", "Agro", "physical", "#1 exporter of soy, beef, sugar, coffee, OJ, chicken, cotton", "P",
          "; ".join(f"{s.split('_')[0]} ${ex[s][2014] / 1e9:.1f}bn->${ex[s][2025] / 1e9:.1f}bn" for s in ex),
          "export values growing (world rank untestable)", "Partial", "pro", list(ex), "no OJ/chicken/cotton series; world rank needs peers")
    claim("A3", "Agro", "physical", "Northern frontier / Arco Norte ports", "U", "", "", "Untestable", "pro", [], "no port/regional data")
    fz = ann("fertilizer_imports")
    t = trend_pct(fz.loc[2014:2025])
    R["A4"] = tag({"2014_usd_bn": fz[2014] / 1e9, "2025_usd_bn": fz[2025] / 1e9, "trend_pct_yr": t}, "fertilizer_imports", SQL_ANN)
    claim("A4", "Agro", "physical", "Hidden dependency on imported fertilizer", "T",
          f"fertilizer imports ${fz[2014] / 1e9:.1f}bn (2014) -> ${fz[2025] / 1e9:.1f}bn (2025), trend {t:+.1f}%/yr",
          "imports rising", "Supported" if t > 0 else "Refuted", "con", ["fertilizer_imports"])

    # ---------------- MINERALS
    nb = ann("niobium_exports")
    claim("M1", "Minerals", "physical", "Niobium dominance", "P",
          f"niobium exports ${nb[2014] / 1e9:.2f}bn (2014) -> ${nb[2025] / 1e9:.2f}bn (2025), trend {trend_pct(nb.loc[2014:2025]):+.1f}%/yr",
          "USD exports large/growing (world share untestable)", "Partial", "pro", ["niobium_exports"])
    claim("M2", "Minerals", "physical", "#2 rare-earth reserves", "U", "", "", "Untestable", "pro", [], "no reserves data")
    ht = q("SELECT hyp_id, statistic, verdict, evidence, as_of FROM hypothesis_tests").set_index("hyp_id")
    claim("M3", "Minerals", "physical", "High-grade iron ore", "P",
          f"H2: {ht.loc['H2', 'evidence']}; H3: {ht.loc['H3', 'evidence']}", "volume/price evidence (grade untestable)",
          "Partial", "pro", ["iron_ore_exports_kg", "iron_ore_unit_value"], "cites hypothesis_tests H2/H3")
    li = ann("wb/NW.NCA.MLIT.TO.BR")
    claim("M4", "Minerals", "physical", "Lithium", "P",
          f"lithium natural capital ${li.iloc[0] / 1e6:.0f}m ({li.index[0]}) -> ${li.iloc[-1] / 1e6:.0f}m ({li.index[-1]})",
          "rising", "Partial", "pro", ["wb/NW.NCA.MLIT.TO.BR"], "stale (2020) -> Partial at most")
    ces = S3["china_share"]
    claim("M5", "Minerals", "physical", "Brazil as hedge vs China processing dominance", "P",
          f"China share of exports {ces['first']:.1f}% (12m to {ces['first_date']}) -> {ces['last']:.1f}% (12m to {ces['last_date']}): China is Brazil's buyer, not a rival",
          "reframed: dependence on China as buyer", "Partial", "pro", ["exports_to_china", "exports_total"])

    # ---------------- CREDIT
    cg = mon("credit_gdp"); cga = ann("credit_gdp", complete=False); wbc = ann("wb/FS.AST.PRVT.GD.ZS.BR")
    R["C1"] = tag({"bcb_2000": cga[2000], "bcb_2004": cga[2004], "bcb_2008": cga[2008], "bcb_latest": cg.iloc[-1],
                   "bcb_latest_date": str(cg.index[-1].date()), "wb_2008": wbc[2008], "wb_2025": wbc[2025]},
                  ["credit_gdp", "wb/FS.AST.PRVT.GD.ZS.BR"], SQL_ANN)
    claim("C1", "Credit", "institutional", "Credit/GDP ~30% (2008) -> ~54% now; room to grow", "T",
          f"BCB credit/GDP {cga[2008]:.1f}% (Dec 2008) -> {cg.iloc[-1]:.1f}% ({cg.index[-1]:%b %Y}); WB broader def {wbc[2008]:.1f}% -> {wbc[2025]:.1f}%",
          "path rising; quoted levels match", "Partial", "pro", ["credit_gdp", "wb/FS.AST.PRVT.GD.ZS.BR"],
          f"direction right; '~30% in 2008' is wrong (39.7%); 30% matches 2000-04 ({cga[2000]:.1f}%/{cga[2004]:.1f}%)")
    dsr = mon("household_debt_service_ratio"); hdi = mon("household_debt_income")
    at_max = dsr.iloc[-1] >= dsr.max() - 0.3
    claim("C2", "Credit", "institutional", "Household debt rising / stretched", "T",
          f"debt/income {hdi.loc['2010'].mean():.1f}% (2010) -> {hdi.iloc[-1]:.1f}% ({hdi.index[-1]:%b %Y}); debt service {dsr.iloc[-1]:.1f}% (series max {dsr.max():.1f}%)",
          "DSR at/near series max", "Supported" if at_max else "Partial", "con",
          ["household_debt_income", "household_debt_service_ratio"])
    rp = mon("real_policy_rate"); se = mon("selic_target", "last"); ip = mon("ipca_12m")
    apr = "2026-04-01"
    R["C3"] = tag({"selic_apr2026_end": se[apr], "ipca12m_apr2026": ip[apr], "real_policy_apr2026": rp[apr],
                   "real_policy_latest": rp.iloc[-1], "real_latest_date": str(rp.index[-1].date()),
                   "ipca12m_2026_range": [ip.loc["2026"].min(), ip.loc["2026"].max()],
                   "wb_lending_rate_2025": ann("wb/FR.INR.LEND.BR")[2025], "wb_spread_2024": ann("wb/FR.INR.LNDP.BR")[2024]},
                  ["real_policy_rate", "selic_target", "ipca_12m", "wb/FR.INR.LEND.BR", "wb/FR.INR.LNDP.BR"])
    claim("C3", "Credit", "institutional", "Cost of credit is the problem: Selic 14.5%, inflation 5-6%, real 8-11%", "T",
          f"Apr 2026: Selic {se[apr]:.2f}%, IPCA 12m {ip[apr]:.2f}% (2026 range {ip.loc['2026'].min():.2f}-{ip.loc['2026'].max():.2f}), ex-ante real {rp[apr]:.1f}%; lending spread {ann('wb/FR.INR.LNDP.BR')[2024]:.1f} pts (2024)",
          "ex-ante real policy rate > 5%", "Supported" if rp[apr] > 5 else "Refuted", "con",
          ["real_policy_rate", "selic_target", "ipca_12m", "wb/FR.INR.LNDP.BR"],
          "Selic and real-rate numbers correct; 'inflation 5-6%' is too high (IPCA 12m 3.8-4.7% in 2026); 'highest in world' untestable")
    sp = ann("wb/FR.INR.LNDP.BR"); c5 = ann("wb/GFDD.OI.06.BR"); c3b = ann("wb/GFDD.OI.01.BR"); roe = ann("wb/GFDD.EI.06.BR")
    ni = ann("net_income_brl@ITUB"); rv = ann("revenue_brl@ITUB")
    claim("C4", "Credit", "institutional", "Banks super-profitable: wide spreads, concentration", "T",
          f"spread {sp.iloc[-1]:.1f} pts ({sp.index[-1]}); 5-bank conc {c5.iloc[-1]:.1f}% / 3-bank {c3b[2000]:.1f}->{c3b.iloc[-1]:.1f}% ({c5.index[-1]}); bank ROE {roe.iloc[-1]:.1f}% ({roe.index[-1]}); Itaú net income/revenue {ni[2025] / rv[2025] * 100:.1f}% (2025)",
          "spread > 20 pts and 5-bank conc > 60%", "Partial" if (sp.iloc[-1] > 20 and c5.iloc[-1] > 60) else "Refuted", "con",
          ["wb/FR.INR.LNDP.BR", "wb/GFDD.OI.06.BR", "wb/GFDD.OI.01.BR", "net_income_brl@ITUB", "revenue_brl@ITUB"],
          "thresholds met but concentration/ROE series stale (2021) -> Partial")
    tot, xg = ann("wb/FI.RES.TOTL.CD.BR"), ann("wb/FI.RES.XGLD.CD.BR"); gold = tot - xg
    R["C5"] = tag({str(y): {"gold_usd_bn": gold[y] / 1e9, "share_pct": gold[y] / tot[y] * 100} for y in [2010, 2020, 2024, 2025]},
                  ["wb/FI.RES.TOTL.CD.BR", "wb/FI.RES.XGLD.CD.BR"], SQL_ANN)
    claim("C5", "Credit", "institutional", "BCB buying gold (+43t in 2025), diversifying away from USD", "P",
          f"gold ${gold[2020] / 1e9:.1f}bn ({gold[2020] / tot[2020] * 100:.1f}% of reserves, 2020) -> ${gold[2025] / 1e9:.1f}bn ({gold[2025] / tot[2025] * 100:.1f}%, 2025); 2024->25 x{gold[2025] / gold[2024]:.2f}",
          "gold share rising sharply", "Partial", "pro", ["wb/FI.RES.TOTL.CD.BR", "wb/FI.RES.XGLD.CD.BR"],
          "value share rising; tonnage (+43t) untestable (no gold price in warehouse to split price vs volume)")
    acc = ann("wb/account.t.d.BRA"); pix = ann("pix_transactions_count") * 1e6; pop = ann("population")
    ppc = pix[2025] / pop[2025]
    claim("C6", "Credit", "institutional", "Pix near-universal", "T",
          f"account ownership {acc[2011]:.1f}% (2011) -> {acc.iloc[-1]:.1f}% ({acc.index[-1]}); Pix {pix[2025] / 1e9:.1f}bn tx in 2025 = {ppc:.0f}/person",
          "account > 80% and Pix > 100/person/yr", "Supported" if acc.iloc[-1] > 80 and ppc > 100 else "Partial", "pro",
          ["wb/account.t.d.BRA", "pix_transactions_count", "population"])
    gd = mon("gross_public_debt_gdp")
    claim("C7", "Credit", "institutional", "Hyperinflation as a 'vaccine' against debt", "P",
          f"private credit {cg.iloc[-1]:.1f}% of GDP (modest) but gross public debt {gd.iloc[-1]:.1f}% ({gd.index[-1]:%b %Y}); r-g +5.1 pts (L3)",
          "low leverage overall", "Partial", "pro", ["credit_gdp", "gross_public_debt_gdp", "r_minus_g"],
          "private side fits; public-debt side contradicts")

    # ---------------- INSTITUTIONS
    gi = ann("wb/SI.POV.GINI.BR")
    slp = float(np.polyfit(gi.loc[2011:].index, gi.loc[2011:].values, 1)[0])
    slp_pre = float(np.polyfit(gi.loc[1995:2010].index, gi.loc[1995:2010].values, 1)[0])
    claim("I1", "Institutions", "institutional", "Inequality persists", "T",
          f"Gini {gi[2009]:.1f} (2009; no 2010 survey) -> {gi[2011]:.1f} (2011) -> {gi.iloc[-1]:.1f} ({gi.index[-1]}); slope {slp_pre:+.2f}/yr 1995-2010 vs {slp:+.2f}/yr 2011+",
          "Gini > 45 ('persists')", "Supported" if gi.iloc[-1] > 45 else "Refuted", "con", ["wb/SI.POV.GINI.BR"],
          "persists in level, but still slowly improving")
    wgi_ids = [f"wb/GOV_WGI_{k}_EST.BR" for k in ["CC", "GE", "RL", "RQ", "VA", "PV"]]
    wg = pd.concat({s: ann(s) for s in wgi_ids}, axis=1)
    pre_m, post_m = wg.loc[1996:2010].mean(), wg.loc[2011:2024].mean()
    R["I2"] = tag({"pre_mean": pre_m.to_dict(), "post_mean": post_m.to_dict(), "cc_2010": wg.loc[2010, wgi_ids[0]],
                   "cc_2024": wg.loc[2024, wgi_ids[0]], "rl_2010": wg.loc[2010, wgi_ids[2]], "rl_2024": wg.loc[2024, wgi_ids[2]]},
                  wgi_ids, SQL_ANN)
    worse = int((post_m < pre_m).sum())
    claim("I2", "Institutions", "institutional", "Corruption / weak institutions persist", "T",
          f"WGI: {worse}/6 dimensions lower in 2011-24 than 1996-2010; control of corruption {wg.loc[2010, wgi_ids[0]]:+.2f} -> {wg.loc[2024, wgi_ids[0]]:+.2f}; rule of law {wg.loc[2010, wgi_ids[2]]:+.2f} -> {wg.loc[2024, wgi_ids[2]]:+.2f}",
          "post-2010 WGI mean <= pre-2010", "Supported" if worse >= 4 else "Partial", "con", wgi_ids,
          "worsened, not just persisted")
    db = ann("wb/IC.BUS.EASE.DFRN.XQ.DB1719.BR")
    claim("I3", "Institutions", "institutional", "Hard to do business", "P",
          f"Doing Business score {db.iloc[-1]:.1f}/100 ({db.index[-1]})", "score < 65", "Partial", "con",
          ["wb/IC.BUS.EASE.DFRN.XQ.DB1719.BR"], "discontinued 2019 -> Partial")
    pisa = ann("wb/LO.PISA.MAT.BR"); hca = ann("wb/NW.HCA.PC.BR")
    claim("I4", "Institutions", "institutional", "Weak schools", "P",
          f"PISA maths {pisa.iloc[-1]:.0f} ({pisa.index[-1]}); human capital/capita ${hca[2010]:,.0f} (2010) -> ${hca.iloc[-1]:,.0f} ({hca.index[-1]})",
          "PISA < 420", "Partial", "con", ["wb/LO.PISA.MAT.BR", "wb/NW.HCA.PC.BR"], "PISA stale (2015) -> Partial")
    tx = ann("wb/GC.TAX.TOTL.GD.ZS.BR")
    claim("I5", "Institutions", "institutional", "Tax complexity", "P",
          f"tax revenue {tx.iloc[-1]:.1f}% of GDP ({tx.index[-1]}); compliance-time series end 2019", "complexity measure",
          "Partial", "con", ["wb/GC.TAX.TOTL.GD.ZS.BR", "wb/PAY.TAX.COIT.AU.HRS.DB1719.BR"], "complexity itself only in stale DB data")
    gf = ann("wb/NE.GDI.FTOT.ZS.BR")
    d_, ci_ = boot_mean_diff(gf.loc[2011:2025].values, gf.loc[1996:2010].values)
    R["I6"] = tag({"gfcf_mean_1996_2010": gf.loc[1996:2010].mean(), "gfcf_mean_2011_2025": gf.loc[2011:2025].mean(),
                   "diff": d_, "diff_ci95": ci_, "gfcf_2010": gf[2010], "gfcf_2025": gf[2025]}, "wb/NE.GDI.FTOT.ZS.BR", SQL_ANN)
    claim("I6", "Institutions", "institutional", "Expensive capital -> low investment", "T",
          f"GFCF {gf[2010]:.1f}% (2010) -> {gf[2025]:.1f}% (2025); mean 2011-25 minus 1996-2010 = {d_:+.1f} pts (CI {ci_[0]:+.1f}, {ci_[1]:+.1f})",
          "GFCF < 20% and post-2010 mean not higher", "Supported" if gf.loc[2011:].mean() < 20 and d_ <= 0.5 else "Partial", "con",
          ["wb/NE.GDI.FTOT.ZS.BR"])
    claim("I7", "Institutions", "institutional", "Slow start: slavery, plantations, land concentration", "U", "", "", "Untestable",
          "con", [], "historical; no land-Gini")

    # ---------------- MARKET: trade & allocation
    claim("G1", "Trade", "market", "China share of Brazil's trade rising", "T",
          f"China share of exports (12m) {ces['first']:.1f}% -> {ces['last']:.1f}%; trend {ces['trend_pts_yr']:+.2f} pts/yr; L4 (12m to Aug 2026): US -14.3%, China +19.0%",
          "share rising", "Supported" if ces["trend_pts_yr"] > 0 else "Refuted", "pro", ["exports_to_china", "exports_total", "exports_to_us"])
    claim("G2", "Trade", "market", "Global South share of trade rising", "P",
          f"proxy non-US/EU share {ces['ns_first']:.1f}% -> {ces['ns_last']:.1f}%", "proxy rising",
          "Partial" if ces["ns_last"] > ces["ns_first"] else "Refuted", "pro", ["exports_to_us", "exports_to_eu", "exports_total"],
          "only China/US/EU destinations exist")
    claim("G3", "Trade", "market", "EU-Mercosur deal benefits", "U", "", "", "Untestable", "pro", ["exports_to_eu"])
    claim("R1", "Allocation", "market", "Ibovespa ~+51% in USD in 2025", "T", f"{R3['ibov_2025']:.1f}%", "within 2 pts of 51%",
          "Supported" if abs(R3["ibov_2025"] - 51) < 2 else "Refuted", "pro", ["ibovespa_usd"])
    claim("R2", "Allocation", "market", "BRL +12-13% vs USD in 2025", "T", f"{R3['brl_2025']:.1f}%", "12-13%",
          "Supported" if 11.5 <= R3["brl_2025"] <= 13.5 else "Refuted", "pro", ["brl_usd"])
    pef = ann("wb/BX.PEF.TOTL.CD.WD.BR")
    claim("R3", "Allocation", "market", "Foreign B3 inflows R$56.5bn Jan-Apr 2026", "U",
          f"no B3 flow series; WB annual portfolio equity net inflows ${pef[2024] / 1e9:.1f}bn (2024), ${pef[2025] / 1e9:.1f}bn (2025)",
          "", "Untestable", "pro", ["wb/BX.PEF.TOTL.CD.WD.BR"], "annual WB data shows net OUTflows in 2024-25 (different period/definition)")
    mc = ann("wb/CM.MKT.LCAP.GD.ZS.BR"); ry = ann("gov_real_yield_10y", complete=False)
    claim("R4", "Allocation", "market", "Rerating underway", "P",
          f"market cap/GDP {mc[2010]:.1f}% (2010) -> {mc.iloc[-1]:.1f}% ({mc.index[-1]}); 10y real yield {ry.iloc[-1]:.2f}% (2026 YTD) vs {ry.loc[2015:2024].mean():.2f}% avg 2015-24",
          "valuation rising", "Partial", "pro", ["wb/CM.MKT.LCAP.GD.ZS.BR", "gov_real_yield_10y"], "embi_brazil stale (2024-07)")

    # ---- Section-3 correlation claims (market column)
    a = S3["3a"]
    r2 = a["ols_ibov_tot_brent"]["value"]["r2"]
    rho = a["corr_ibov_brent"]["value"]["full"]["pearson"]
    claim("X3a", "Correlation", "market", "Brazil growth/equity is driven by the commodity cycle (3a)", "T",
          f"monthly OLS dlog Ibov USD ~ dlog ToT + dlog Brent R2={r2:.2f}; rho(Ibov,Brent)={rho:.2f}",
          "R2 > 0.3 (or rho > 0.4)", "Supported" if r2 > 0.3 or rho > 0.4 else ("Partial" if rho > 0.2 else "Refuted"), "pro",
          ["ibovespa_usd", "brent_usd", "wb/TOT.BRA"])
    b = S3["3b"]
    v = "Supported" if b["binding"] else ("Partial" if b["any_negative"] else "Refuted")
    claim("X3b", "Correlation", "institutional", "Cost of credit is binding (real rate -> credit/activity, 3b)", "T",
          b["summary"], "rho < -0.3 at lag 6-18m with CI excluding 0 (>=2 credit/activity series)", v, "con",
          ["real_policy_rate", "household_credit_growth", "corporate_credit_growth", "ibc_br", "delinquency_rate"],
          "binds on credit only in the post-2010 window (full-sample CIs straddle 0, 2008-10 flips sign); activity (IBC-Br) shows no negative response")
    c = S3["3c"]
    v = "Supported" if c["converted"] else "Refuted"
    claim("X3c", "Correlation", "market", "Endowment gains convert into income / USD returns (3c)", "T", c["summary"],
          "GDP pc PPP CAGR post-2010 > pre-2010, or USD equity above 2010 level", v, "pro",
          ["wb/NY.GDP.PCAP.PP.KD.BR", "wb/DSTKMKTXD_M.BRA"])
    e = S3["3e"]
    claim("X3e", "Correlation", "market", "Brazil equity is a commodity hedge (beta>0, CI excl. 0, 3e)", "T", e["summary"],
          "beta > 0 with CI excluding 0", "Supported" if e["hedge"] else "Refuted", "pro",
          ["ibovespa_usd", "brent_usd", "iron_ore_unit_value"],
          "rubric met, but rho only 0.31 ('partial hedge') and the domestic control Itaú has the same composite beta -> largely a global risk-on beta, not a commodity-specific hedge")
    return R


# ============================================================================= 2. comparative frame
def s2_comparative():
    R = {}
    pli = ann("wb/PA.NUS.GDP.PLI.BR")
    stk = year_end("wb/DSTKMKTXD_M.BRA")
    reer = ann("wb/PX.REX.REER.BR")
    gpc = ann("wb/NY.GDP.PCAP.PP.KD.BR")
    R["price_level_us100"] = tag({str(y): val(pli, y) for y in [1990, 2000, 2010, 2019, 2025]}, "wb/PA.NUS.GDP.PLI.BR", SQL_ANN)
    R["equity_usd_index_yearend"] = tag({str(y): val(stk, y) for y in [1994, 2000, 2010, 2019, 2025]}, "wb/DSTKMKTXD_M.BRA",
                                        "SELECT EXTRACT(year FROM date)::INT, arg_max(value,date) FROM v_observations WHERE series_id='wb/DSTKMKTXD_M.BRA' GROUP BY 1")
    R["reer"] = tag({str(y): val(reer, y) for y in [1990, 2000, 2010, 2019, 2025]}, "wb/PX.REX.REER.BR", SQL_ANN)
    R["gdp_pc_ppp"] = tag({str(y): val(gpc, y) for y in [1990, 2000, 2010, 2019, 2025]} | {
        "cagr_2000_2010": cagr(gpc, 2000, 2010), "cagr_2010_2025": cagr(gpc, 2010, 2025),
        "cagr_1990_2010": cagr(gpc, 1990, 2010)}, "wb/NY.GDP.PCAP.PP.KD.BR", SQL_ANN)
    # pre vs post mean annual growth with block-bootstrap CI on the difference
    panel = {}
    for sid, lab in [("wb/NY.GDP.MKTP.KD.ZG.BR", "real GDP growth %"), ("wb/NY.GDP.PCAP.PP.KD.BR", "GDP pc PPP growth %"),
                     ("ilostat/GDP_205U_NOC_NB.BRA", "output per worker growth %"), ("wb/NE.GDI.FTOT.ZS.BR", "GFCF % GDP (level)"),
                     ("wb/AG.YLD.CREL.KG.BR", "cereal yield growth %"), ("oil_production", "oil output growth %")]:
        s = ann(sid)
        g = s if "level" in lab or sid.endswith("KD.ZG.BR") else (s.pct_change() * 100)
        pre_, post_ = g.loc[1991:2010].dropna(), g.loc[2011:2025].dropna()
        pre_ = pre_.loc[2001:] if sid == "oil_production" else pre_
        dd, ci = boot_mean_diff(post_.values, pre_.values)
        ex = g.loc[2011:2025].drop(2020, errors="ignore").dropna().mean()
        panel[lab] = tag({"pre_mean": pre_.mean(), "post_mean": post_.mean(), "diff_post_minus_pre": dd, "ci95": ci,
                          "post_mean_ex2020": ex, "n_pre": len(pre_), "n_post": len(post_),
                          "post2012_mean": g.loc[2013:2025].dropna().mean()}, sid, SQL_ANN)
    R["pre_post_panel"] = panel
    R["note"] = ("No peer countries in warehouse; US comparison only via US-relative WB series (PLI, US=100) and the USD equity index. "
                 "Convergence-to-US GDP ratio cannot be computed in-warehouse.")
    return R


# ============================================================================= 3. correlations
def build_monthly():
    last = ["ibovespa_usd", "brl_usd", "brent_usd", "wb/DSTKMKTXD_M.BRA", "total_return_usd@IBOV", "total_return_usd@PETR",
            "total_return_usd@VALE", "total_return_usd@SUZB", "total_return_usd@ITUB", "total_return_usd@PRIO",
            "total_return_usd@AXIA", "total_return_brl@IBOV", "credit_gdp"]
    mean = ["wb/TOT.BRA", "real_policy_rate", "selic_target", "ipca_12m", "household_credit_growth", "corporate_credit_growth",
            "delinquency_rate", "ibc_br", "bop_goods_exports", "iron_ore_unit_value", "stored_energy_ear", "cmo_power_cost",
            "thermal_generation_share", "wind_solar_generation_share", "hydro_generation_share", "ipca_administered_prices",
            "exports_total", "exports_to_china", "exports_to_us", "exports_to_eu"]
    d = {s: mon(s, "last") for s in last} | {s: mon(s, "mean") for s in mean}
    df = pd.DataFrame(d)
    return df


SQL_M = """SELECT series_id, date_trunc('month', date) AS ym,
  CASE WHEN series_id IN ('ibovespa_usd','brl_usd','brent_usd','wb/DSTKMKTXD_M.BRA') THEN arg_max(value, date) ELSE avg(value) END AS v
FROM v_observations WHERE date <= current_date AND series_id IN (...) GROUP BY 1,2"""


def china_share(M):
    c12 = M["exports_to_china"].rolling(12).sum(); t12 = M["exports_total"].rolling(12).sum()
    u12 = M["exports_to_us"].rolling(12).sum(); e12 = M["exports_to_eu"].rolling(12).sum()
    sh = (c12 / t12 * 100).dropna(); ns = ((1 - (u12 + e12) / t12) * 100).dropna()
    t = sh.index.year + (sh.index.month - 1) / 12
    return {"first": sh.iloc[0], "first_date": str(sh.index[0].date()), "last": sh.iloc[-1], "last_date": str(sh.index[-1].date()),
            "trend_pts_yr": float(np.polyfit(t, sh.values, 1)[0]), "ns_first": ns.iloc[0], "ns_last": ns.iloc[-1],
            "series": src(["exports_to_china", "exports_total", "exports_to_us", "exports_to_eu"])}


def s3a(M):
    R = {}
    # ToT validation
    tot_a = M["wb/TOT.BRA"].groupby(M.index.year).mean()
    tt = ann("wb/TT.PRI.MRCH.XD.WD.BR")
    v = align(tot_a.loc[2005:2024], tt.loc[2005:2024])
    rho_v = _corr(v.iloc[:, 0].values, v.iloc[:, 1].values)
    R["tot_validation"] = tag({"rho": rho_v, "n": len(v), "pass": rho_v > 0.9}, ["wb/TOT.BRA", "wb/TT.PRI.MRCH.XD.WD.BR"],
                              note="annual mean of wb/TOT.BRA vs WB net barter ToT index, 2005-2024")
    use_tot = rho_v > 0.9
    # monthly returns
    ib = logdiff(M["ibovespa_usd"]); br = logdiff(M["brent_usd"]); fx = logdiff(M["brl_usd"])
    tot = logdiff(M["wb/TOT.BRA"]) if use_tot else None
    R["corr_ibov_brent"] = tag(split_stats(br, ib, 12, 36), ["ibovespa_usd", "brent_usd"], SQL_M)
    R["corr_brl_brent"] = tag(split_stats(br, fx, 12, 36), ["brl_usd", "brent_usd"], SQL_M,
                              note="brl_usd is BRL per USD: negative rho = BRL strengthens when Brent rises")
    if use_tot:
        R["corr_ibov_tot"] = tag(split_stats(tot, ib, 12, 36), ["ibovespa_usd", "wb/TOT.BRA"], SQL_M)
        R["corr_brl_tot"] = tag(split_stats(tot, fx, 12, 36), ["brl_usd", "wb/TOT.BRA"], SQL_M)
        df = align(ib, tot, br)
        r = boot_ols(df.iloc[:, 0].values, [df.iloc[:, 1].values, df.iloc[:, 2].values], 12)
        R["ols_ibov_tot_brent"] = tag({"beta_tot": r["beta"][1], "beta_tot_ci": r["ci95"][1], "beta_brent": r["beta"][2],
                                       "beta_brent_ci": r["ci95"][2], "r2": r["r2"], "n": r["n"],
                                       "start": str(df.index[0].date()), "end": str(df.index[-1].date())},
                                      ["ibovespa_usd", "wb/TOT.BRA", "brent_usd"], SQL_M)
        for nm, m in [("pre", df.index.year <= BREAK), ("post", df.index.year > BREAK)]:
            d = df[m]; rr = ols(d.iloc[:, 0].values, [d.iloc[:, 1].values, d.iloc[:, 2].values])
            R["ols_ibov_tot_brent"]["value"][f"r2_{nm}"] = round(float(rr[1]), 4)
        R["interaction_ibov_tot"] = tag(interaction(tot, ib, 12), ["ibovespa_usd", "wb/TOT.BRA"])
    R["interaction_ibov_brent"] = tag(interaction(br, ib, 12), ["ibovespa_usd", "brent_usd"])
    rc = rolling_corr(br, ib, 60)
    R["rolling60_ibov_brent"] = tag({"min": rc.min(), "max": rc.max(), "last": rc.iloc[-1], "last_date": str(rc.index[-1].date()),
                                     "mean_pre": rc[rc.index.year <= BREAK].mean(), "mean_post": rc[rc.index.year > BREAK].mean()},
                                    ["ibovespa_usd", "brent_usd"])
    # quarterly GDP vs ToT CCF
    gq = obs("wb/NYGDPMKTPSAKD_Q.BRA"); gq.index = gq.index.to_period("Q")
    tq = M["wb/TOT.BRA"].groupby(M.index.to_period("Q")).mean()
    dg, dt = logdiff(gq), logdiff(tq)
    cc = {}
    for nm, sel in [("full", slice(None)), ("pre", slice(None, "2010Q4")), ("post", slice("2011Q1", None))]:
        cc[nm] = {k: {"rho": v_[0], "n": v_[1]} for k, v_ in ccf(dt.loc[sel], dg.loc[sel], range(0, 5)).items()}
    d0 = align(dt, dg); d0.index = d0.index.to_timestamp()
    R["ccf_gdpq_tot"] = tag({"ccf": cc, "lag0": split_stats(d0.iloc[:, 0], d0.iloc[:, 1], 4, 10)},
                            ["wb/NYGDPMKTPSAKD_Q.BRA", "wb/TOT.BRA"], note="rho(dlog ToT_t, dlog GDP_{t+k}), k quarters")
    # annual GDP growth vs dlog TT
    gy = ann("wb/NY.GDP.MKTP.KD.ZG.BR"); dtt = logdiff(tot_a) * 100
    R["annual_gdp_tot"] = tag(split_stats(dtt.loc[1992:2025], gy.loc[1992:2025], 3, 10), ["wb/NY.GDP.MKTP.KD.ZG.BR", "wb/TOT.BRA"])
    # monthly IBC-Br YoY vs ToT YoY
    ibc = logdiff(M["ibc_br"], 12); ty = logdiff(M["wb/TOT.BRA"], 12)
    R["ibc_yoy_tot_yoy"] = tag(split_stats(ty, ibc, 12, 36), ["ibc_br", "wb/TOT.BRA"],
                               note="YoY on YoY: overlapping windows inflate apparent rho; block bootstrap partly corrects")
    # chart: rolling corr
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rc.index, y=rc.values, name="60m corr(dlog Ibov USD, dlog Brent)"))
    if use_tot:
        rt = rolling_corr(tot, ib, 60)
        fig.add_trace(go.Scatter(x=rt.index, y=rt.values, name="60m corr(dlog Ibov USD, dlog ToT)"))
    rf = rolling_corr(br, -fx, 60)
    fig.add_trace(go.Scatter(x=rf.index, y=rf.values, name="60m corr(BRL strength, dlog Brent)"))
    fig.add_vline(x="2010-12-31", line_dash="dash"); fig.add_hline(y=0.4, line_dash="dot")
    fig.update_layout(title="3a: rolling 60-month correlation, Brazil USD equity / BRL vs commodities",
                      yaxis_title="Pearson rho", template="plotly_white")
    fig.write_html(os.path.join(CH, "3a_rolling_corr.html"), include_plotlyjs="cdn")
    return R


def s3b(M):
    R = {}
    rr = M["real_policy_rate"]
    exp = (M["selic_target"] - M["ipca_12m"]).rename("expost")
    ys = {"household_credit_growth": M["household_credit_growth"], "corporate_credit_growth": M["corporate_credit_growth"],
          "credit_gdp_d12": M["credit_gdp"].diff(12), "ibc_br_yoy": logdiff(M["ibc_br"], 12) * 100,
          "delinquency_rate": M["delinquency_rate"]}
    best = {}
    lags = range(-12, 25)
    for nm, y in ys.items():
        c = ccf(rr, y, lags)
        win = {k: v for k, v in c.items() if 6 <= k <= 18 and v[1] >= 36}
        k_min = min(win, key=lambda k: win[k][0])  # most negative in 6-18
        k_abs = max({k: v for k, v in c.items() if v[1] >= 36}, key=lambda k: abs(c[k][0]))
        df = align(rr, y.shift(-k_min))
        ci = block_bootstrap_corr(df.iloc[:, 0].values, df.iloc[:, 1].values, 12)
        ss = split_stats(rr, y.shift(-k_min), 12, 36)
        c_ex = ccf(exp, y, [k_min])[k_min]
        best[nm] = {"lag_most_negative_6_18": k_min, "rho": win[k_min][0], "n": win[k_min][1], "ci95": ci,
                    "lag_max_abs": k_abs, "rho_max_abs": c[k_abs][0],
                    "pre_rho": ss["pre"].get("pearson"), "pre_n": ss["pre"]["n"], "post_rho": ss["post"].get("pearson"),
                    "post_n": ss["post"]["n"], "post_ci": ss["post"].get("ci95"), "ex2020_rho": ss["ex2020"].get("pearson"),
                    "expost_rate_rho_same_lag": c_ex[0], "ccf": {k: round(v[0], 3) for k, v in c.items()}}
    R["ccf_real_rate"] = tag(best, ["real_policy_rate", "selic_target", "ipca_12m", "household_credit_growth",
                                    "corporate_credit_growth", "credit_gdp", "ibc_br", "delinquency_rate"], SQL_M,
                             note="rho(real_rate_t, Y_{t+k}); both sides persistent -> CIs from 12-month block bootstrap; spurious-correlation risk remains")
    # annual OLS: dGFCF ~ real rate
    gf = ann("wb/NE.GDI.FTOT.ZS.BR"); ra = ann("real_policy_rate"); gy = ann("wb/NY.GDP.MKTP.KD.ZG.BR")
    df = align(ra.loc[2002:2025], gf.diff().loc[2002:2025])
    r = boot_ols(df.iloc[:, 1].values, [df.iloc[:, 0].values], 3)
    df2 = align(ra.loc[2002:2025], gy.loc[2002:2025])
    r2 = boot_ols(df2.iloc[:, 1].values, [df2.iloc[:, 0].values], 3)
    R["annual_ols"] = tag({"dGFCF_on_real_rate": {"beta": r["beta"][1], "ci95": r["ci95"][1], "r2": r["r2"], "n": r["n"]},
                           "gdp_growth_on_real_rate": {"beta": r2["beta"][1], "ci95": r2["ci95"][1], "r2": r2["r2"], "n": r2["n"]}},
                          ["wb/NE.GDI.FTOT.ZS.BR", "real_policy_rate", "wb/NY.GDP.MKTP.KD.ZG.BR"], SQL_ANN)
    ht = q("SELECT statistic, evidence, as_of FROM hypothesis_tests WHERE hyp_id='L3'").iloc[0]
    rg = mon("r_minus_g")
    R["r_minus_g"] = tag({"latest": rg.iloc[-1], "date": str(rg.index[-1].date()), "L3_evidence": ht["evidence"]}, "r_minus_g")
    binding_full = [nm for nm, b in best.items() if nm != "delinquency_rate" and b["rho"] < -0.3 and b["ci95"][1] < 0]
    binding_post = [nm for nm, b in best.items() if nm != "delinquency_rate" and (b["post_rho"] or 0) < -0.3
                    and b["post_ci"] and b["post_ci"][1] < 0]
    binding = binding_full or binding_post
    R["binding_full_sample"] = binding_full
    R["binding_post2010"] = binding_post
    anyneg = [nm for nm, b in best.items() if nm != "delinquency_rate" and b["rho"] < 0]
    hc = best["household_credit_growth"]; cc_ = best["corporate_credit_growth"]; ib = best["ibc_br_yoy"]
    summary = (f"rho(real rate_t, Y_t+k), most negative lag 6-18m: household credit {hc['rho']:.2f} @k={hc['lag_most_negative_6_18']} "
               f"(CI {hc['ci95'][0]:.2f},{hc['ci95'][1]:.2f}, n={hc['n']}); corporate {cc_['rho']:.2f} @k={cc_['lag_most_negative_6_18']} "
               f"(CI {cc_['ci95'][0]:.2f},{cc_['ci95'][1]:.2f}); IBC-Br YoY {ib['rho']:.2f} @k={ib['lag_most_negative_6_18']} "
               f"(CI {ib['ci95'][0]:.2f},{ib['ci95'][1]:.2f}); post-2010 at same lag: household {hc['post_rho']:.2f} (CI {hc['post_ci'][0]:.2f},{hc['post_ci'][1]:.2f}, n={hc['post_n']}), "
               f"corporate {cc_['post_rho']:.2f} (CI {cc_['post_ci'][0]:.2f},{cc_['post_ci'][1]:.2f}); delinquency +{best['delinquency_rate']['rho_max_abs']:.2f} @k={best['delinquency_rate']['lag_max_abs']}; annual dGFCF beta {r['beta'][1]:.2f} (CI {r['ci95'][1][0]:.2f},{r['ci95'][1][1]:.2f}, n={r['n']})")
    R["binding"] = len(binding) >= 2
    R["binding_series"] = binding
    R["any_negative"] = len(anyneg) >= 2
    R["summary"] = summary
    # chart CCF
    fig = go.Figure()
    for nm, b in best.items():
        fig.add_trace(go.Scatter(x=list(b["ccf"].keys()), y=list(b["ccf"].values()), mode="lines+markers", name=nm))
    fig.add_vrect(x0=6, x1=18, fillcolor="grey", opacity=0.1, line_width=0); fig.add_hline(y=-0.3, line_dash="dot")
    fig.update_layout(title="3b: cross-correlation, ex-ante real policy rate (t) vs Y (t+k months)", xaxis_title="k (months)",
                      yaxis_title="Pearson rho", template="plotly_white")
    fig.write_html(os.path.join(CH, "3b_ccf_real_rate.html"), include_plotlyjs="cdn")
    return R


def zreb(s, base=2010):
    z = (s - s.mean()) / s.std()
    return z - z.get(base, np.nan)


def s3c(M):
    R = {}
    oil = ann("oil_production"); bop = np.log(ann("bop_goods_exports"))
    phys = {"oil_production": oil, "wb/AG.YLD.CREL.KG.BR": ann("wb/AG.YLD.CREL.KG.BR"), "wb/AG.PRD.CREL.MT.BR": ann("wb/AG.PRD.CREL.MT.BR"),
            "wb/NV.AGR.EMPL.KD.BR": ann("wb/NV.AGR.EMPL.KD.BR"), "wb/EG.ELC.RNEW.ZS.BR": ann("wb/EG.ELC.RNEW.ZS.BR"),
            "wb/EG.IMP.CONS.ZS.BR": -ann("wb/EG.IMP.CONS.ZS.BR"),
            "wb/NW.NCA.TOTL.PC.BR+SSOI": ann("wb/NW.NCA.TOTL.PC.BR") + ann("wb/NW.NCA.SSOI.PC.BR"),
            "bop_goods_exports(log)": bop}
    wgi_ids = [f"wb/GOV_WGI_{k}_EST.BR" for k in ["CC", "GE", "RL", "RQ", "VA", "PV"]]
    wg = pd.concat({s: ann(s) for s in wgi_ids}, axis=1).mean(axis=1)
    inst = {"WGI mean(6)": wg, "-wb/SI.POV.GINI.BR": -ann("wb/SI.POV.GINI.BR"), "wb/NE.GDI.FTOT.ZS.BR": ann("wb/NE.GDI.FTOT.ZS.BR"),
            "wb/NW.HCA.PC.BR": ann("wb/NW.HCA.PC.BR")}
    stk = year_end("wb/DSTKMKTXD_M.BRA").loc[:2025]
    outc = {"wb/NY.GDP.PCAP.PP.KD.BR": ann("wb/NY.GDP.PCAP.PP.KD.BR"), "ilostat/GDP_205U_NOC_NB.BRA": ann("ilostat/GDP_205U_NOC_NB.BRA"),
            "ilostat/SDG_0821_NOC_RT.BRA": ann("ilostat/SDG_0821_NOC_RT.BRA"), "wb/PA.NUS.GDP.PLI.BR": ann("wb/PA.NUS.GDP.PLI.BR"),
            "wb/DSTKMKTXD_M.BRA(year-end)": stk}
    for s in ["wb/NW.NCA.SSOI.PC.BR", "wb/GOV_WGI_CC_EST.BR"]:
        meta(s)
    comps = {}
    for nm, d in [("endowment", phys), ("institutions", inst), ("outcome", outc)]:
        df = pd.DataFrame({k: zreb(v.loc[1995:2025]) for k, v in d.items()}).loc[1996:2025]
        comps[nm] = df.mean(axis=1, skipna=True)
        comps[nm + "_n"] = df.notna().sum(axis=1)
    C = pd.DataFrame(comps)
    R["composites"] = tag({"z_rebased_2010_0": C[["endowment", "institutions", "outcome"]].round(3).to_dict(orient="index"),
                           "n_components": C[["endowment_n", "institutions_n", "outcome_n"]].to_dict(orient="index"),
                           "2025": {k: C.loc[2025, k] for k in ["endowment", "institutions", "outcome"]},
                           "2024": {k: C.loc[2024, k] for k in ["endowment", "institutions", "outcome"]}},
                          ["oil_production", "wb/AG.YLD.CREL.KG.BR", "wb/AG.PRD.CREL.MT.BR", "wb/NV.AGR.EMPL.KD.BR",
                           "wb/EG.ELC.RNEW.ZS.BR", "wb/EG.IMP.CONS.ZS.BR", "wb/NW.NCA.TOTL.PC.BR", "bop_goods_exports"] + wgi_ids +
                          ["wb/SI.POV.GINI.BR", "wb/NE.GDI.FTOT.ZS.BR", "wb/NW.HCA.PC.BR", "wb/NY.GDP.PCAP.PP.KD.BR",
                           "ilostat/GDP_205U_NOC_NB.BRA", "ilostat/SDG_0821_NOC_RT.BRA", "wb/PA.NUS.GDP.PLI.BR", "wb/DSTKMKTXD_M.BRA"],
                          note="each component z-scored over 1995-2025 and shifted so 2010 = 0; equal weights; mean of available "
                               "components (natural-capital and renewables series end 2020-2021; wind/solar excluded since it starts 2015)")
    # CAGR table
    tab = {}
    for nm, s in [("oil_production", oil), ("wb/AG.YLD.CREL.KG.BR", phys["wb/AG.YLD.CREL.KG.BR"]),
                  ("wb/AG.PRD.CREL.MT.BR", phys["wb/AG.PRD.CREL.MT.BR"]), ("wb/NV.AGR.EMPL.KD.BR", phys["wb/NV.AGR.EMPL.KD.BR"]),
                  ("bop_goods_exports", ann("bop_goods_exports")), ("wb/NY.GDP.PCAP.PP.KD.BR", outc["wb/NY.GDP.PCAP.PP.KD.BR"]),
                  ("ilostat/GDP_205U_NOC_NB.BRA", outc["ilostat/GDP_205U_NOC_NB.BRA"]), ("wb/PA.NUS.GDP.PLI.BR", outc["wb/PA.NUS.GDP.PLI.BR"]),
                  ("wb/DSTKMKTXD_M.BRA(year-end)", stk), ("wb/NW.HCA.PC.BR", inst["wb/NW.HCA.PC.BR"])]:
        last_y = int(s.dropna().index.max())
        tab[nm] = {"cagr_2000_2010": cagr(s, 2000, 2010), "cagr_2010_last": cagr(s, 2010, min(last_y, 2025)), "last_year": min(last_y, 2025)}
    R["cagr_table"] = tag(tab, ["oil_production", "bop_goods_exports", "wb/NY.GDP.PCAP.PP.KD.BR", "wb/DSTKMKTXD_M.BRA"], SQL_ANN)
    # OLS dlog GDPpc ~ dlog ToT + dWGI
    tot_a = M["wb/TOT.BRA"].groupby(M.index.year).mean()
    gpc = outc["wb/NY.GDP.PCAP.PP.KD.BR"]
    df = align(logdiff(gpc) * 100, logdiff(tot_a) * 100, wg.diff()).loc[1997:2024]
    r = boot_ols(df.iloc[:, 0].values, [df.iloc[:, 1].values, df.iloc[:, 2].values], 3)
    R["ols_gdppc"] = tag({"beta_dlogToT": r["beta"][1], "ci_dlogToT": r["ci95"][1], "beta_dWGI": r["beta"][2], "ci_dWGI": r["ci95"][2],
                          "r2": r["r2"], "n": r["n"]}, ["wb/NY.GDP.PCAP.PP.KD.BR", "wb/TOT.BRA"] + wgi_ids, SQL_ANN,
                         note="low power (n~27); coefficients per 1% ToT change and per 1-unit WGI change")
    c0, c1 = cagr(gpc, 2000, 2010), cagr(gpc, 2010, 2025)
    eq10, eq25 = val(stk, 2010), val(stk, 2025)
    R["converted"] = bool(c1 > c0 or eq25 > eq10)
    R["summary"] = (f"GDP pc PPP CAGR {c0:.2f}%/yr 2000-10 vs {c1:.2f}%/yr 2010-25; USD equity index {eq10:.1f} (Dec 2010) -> {eq25:.1f} (Dec 2025); "
                    f"composites 2025 (z, 2010=0): endowment {C.loc[2025, 'endowment']:+.2f}, institutions {C.loc[2025, 'institutions']:+.2f}, "
                    f"outcome {C.loc[2025, 'outcome']:+.2f}")
    # chart
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Composites (z-units, 2010 = 0)", "Index 2010 = 100"))
    for nm, col in [("endowment", "#2a7"), ("institutions", "#c44"), ("outcome", "#36c")]:
        fig.add_trace(go.Scatter(x=C.index, y=C[nm], name=nm, line=dict(color=col)), 1, 1)
    for nm, s in [("GDP pc PPP", gpc), ("Oil output", oil), ("Cereal yield", phys["wb/AG.YLD.CREL.KG.BR"]),
                  ("USD equity index", stk), ("Price level (US=100)", outc["wb/PA.NUS.GDP.PLI.BR"])]:
        s = s.loc[1995:2025]
        fig.add_trace(go.Scatter(x=s.index, y=s / s[2010] * 100, name=nm, line=dict(dash="dot")), 1, 2)
    fig.add_vline(x=2010, line_dash="dash")
    fig.update_layout(title="3c: endowment improved, institutions weakened, outcomes did not converge", template="plotly_white")
    fig.write_html(os.path.join(CH, "3c_three_line_index.html"), include_plotlyjs="cdn")
    return R


def s3d(M):
    R = {}
    ear = M["stored_energy_ear"]; cmo = M["cmo_power_cost"]; lc = np.log(cmo.clip(lower=1))
    adm = M["ipca_administered_prices"]; th = M["thermal_generation_share"]; ws = M["wind_solar_generation_share"]
    R["ear_logcmo_lags"] = tag({k: corr_stats(ear, lc.shift(-k), 12, 36) for k in range(0, 4)}, ["stored_energy_ear", "cmo_power_cost"], SQL_M,
                               note="EAR in levels (bounded %); log CMO")
    R["ear_admin_lags"] = tag({k: corr_stats(ear, adm.shift(-k), 12, 36, boot=(k in (0, 3, 6))) for k in range(0, 7)},
                              ["stored_energy_ear", "ipca_administered_prices"], SQL_M)
    R["thermal_logcmo"] = tag(corr_stats(th, lc, 12, 36), ["thermal_generation_share", "cmo_power_cost"], SQL_M)
    df = align(ear, cmo)
    low = df[df.iloc[:, 0] < 40]; hi = df[df.iloc[:, 0] >= 40]
    R["low_ear_cmo_ratio"] = tag(low.iloc[:, 1].mean() / hi.iloc[:, 1].mean(), ["stored_energy_ear", "cmo_power_cost"],
                                 n_low=len(low), cmo_low=low.iloc[:, 1].mean(), cmo_other=hi.iloc[:, 1].mean(),
                                 note="cross-check with hypothesis_tests H4 (3.1x)")
    # annual drought table
    A = pd.DataFrame({"cmo": ann("cmo_power_cost", complete=False), "thermal": ann("thermal_generation_share", complete=False),
                      "admin": ann("ipca_administered_prices", complete=False), "ear_mean": ann("stored_energy_ear", complete=False)}).loc[2015:]
    dr = A.index.isin([2015, 2017, 2021])
    R["drought_table"] = tag({"by_year": A.round(3).to_dict(orient="index"), "drought_mean_cmo": A.loc[dr, "cmo"].mean(),
                              "other_mean_cmo": A.loc[~dr, "cmo"].mean(), "drought_mean_admin": A.loc[dr, "admin"].mean(),
                              "other_mean_admin": A.loc[~dr, "admin"].mean(), "drought_mean_thermal": A.loc[dr, "thermal"].mean(),
                              "other_mean_thermal": A.loc[~dr, "thermal"].mean()},
                             ["cmo_power_cost", "thermal_generation_share", "ipca_administered_prices", "stored_energy_ear"], SQL_ANN,
                             note="2015 thermal share covers Jul-Dec only; 2026 partial year")
    em = obs("stored_energy_ear")
    R["ear_min_by_year"] = tag({str(k): float(v) for k, v in em.groupby(em.index.year).min().items()}, "stored_energy_ear")
    # interaction OLS
    d = align(lc, ear, ws)
    y, e, w = d.iloc[:, 0].values, d.iloc[:, 1].values, d.iloc[:, 2].values
    r = boot_ols(y, [e, e * w, w], 12)
    R["ols_interaction"] = tag({"beta_ear": r["beta"][1], "ci_ear": r["ci95"][1], "beta_ear_x_ws": r["beta"][2], "ci_ear_x_ws": r["ci95"][2],
                                "beta_ws": r["beta"][3], "ci_ws": r["ci95"][3], "r2": r["r2"], "n": r["n"],
                                "start": str(d.index[0].date()), "end": str(d.index[-1].date())},
                               ["cmo_power_cost", "stored_energy_ear", "wind_solar_generation_share"], SQL_M,
                               note="log CMO ~ EAR + EAR*WS + WS; positive EAR*WS = WS share makes CMO less sensitive to reservoirs")
    d2 = align(lc, ear)
    slopes, cis = {}, {}
    for nm, m in [("2015_2021", d2.index.year <= 2021), ("2022_2026", d2.index.year >= 2022)]:
        s = d2[m]
        rr = boot_ols(s.iloc[:, 0].values, [s.iloc[:, 1].values], 12)
        slopes[nm], cis[nm] = rr["beta"][1], rr["ci95"][1]
        slopes[nm + "_n"] = rr["n"]; slopes[nm + "_r2"] = rr["r2"]
    # bootstrap the slope difference
    rng = np.random.default_rng(7)
    a_ = d2[d2.index.year <= 2021].values; b_ = d2[d2.index.year >= 2022].values
    diffs = []
    for _ in range(N_BOOT):
        ia, ib_ = mbb_idx(len(a_), 12, rng), mbb_idx(len(b_), 12, rng)
        diffs.append(ols(b_[ib_, 0], [b_[ib_, 1]])[0][1] - ols(a_[ia, 0], [a_[ia, 1]])[0][1])
    dci = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]
    R["subsample_slopes"] = tag(slopes | {"ci_2015_2021": cis["2015_2021"], "ci_2022_2026": cis["2022_2026"],
                                          "diff_late_minus_early": slopes["2022_2026"] - slopes["2015_2021"], "diff_ci95": dci},
                                ["cmo_power_cost", "stored_energy_ear"], SQL_M,
                                note="slope of log CMO on EAR (per pt of storage); less negative = less sensitive")
    # robustness: levels (CMO hits ~0 floor in 2022-23, which distorts log CMO)
    d3 = align(cmo, ear); lv = {}
    for nm, m in [("2015_2021", d3.index.year <= 2021), ("2022_2026", d3.index.year >= 2022)]:
        rr = boot_ols(d3[m].iloc[:, 0].values, [d3[m].iloc[:, 1].values], 12)
        lv[nm] = {"beta_R$_per_pt": rr["beta"][1], "ci95": rr["ci95"][1], "n": rr["n"]}
    lv["months_cmo_below_5"] = int((cmo.loc["2015":] < 5).sum())
    R["subsample_slopes_levels"] = tag(lv, ["cmo_power_cost", "stored_energy_ear"], SQL_M,
                                       note="CMO R$/MWh on EAR, levels; robustness to the CMO floor")
    shrink = abs(slopes["2022_2026"]) < abs(slopes["2015_2021"])
    R["slope_shrinks"] = tag(bool(shrink), ["cmo_power_cost", "stored_energy_ear"],
                             significant=bool(dci[0] > 0 or dci[1] < 0))
    rc = rolling_corr(ear, lc, 36)
    R["rolling36"] = tag({"first": rc.iloc[0], "last": rc.iloc[-1], "min": rc.min(), "max": rc.max(), "last_date": str(rc.index[-1].date())},
                         ["stored_energy_ear", "cmo_power_cost"])
    wsa = ann("wind_solar_generation_share")
    R["ws_share"] = tag(wsa[2025], "wind_solar_generation_share")
    # chart: scatter by period
    fig = make_subplots(rows=1, cols=2, subplot_titles=("EAR vs CMO by period", "Rolling 36m corr(EAR, log CMO)"))
    for nm, m, col in [("2015-2021", d2.index.year <= 2021, "#c44"), ("2022-2026", d2.index.year >= 2022, "#2a7")]:
        s = d2[m]
        fig.add_trace(go.Scatter(x=s.iloc[:, 1], y=np.exp(s.iloc[:, 0]), mode="markers", name=nm, marker=dict(color=col),
                                 text=[f"{i:%Y-%m}" for i in s.index]), 1, 1)
    fig.add_trace(go.Scatter(x=rc.index, y=rc.values, name="rolling corr", line=dict(color="#36c")), 1, 2)
    fig.update_yaxes(type="log", title_text="CMO R$/MWh (log)", row=1, col=1)
    fig.update_xaxes(title_text="stored energy EAR %", row=1, col=1)
    fig.update_layout(title="3d: reservoirs vs marginal power cost", template="plotly_white")
    fig.write_html(os.path.join(CH, "3d_ear_vs_cmo.html"), include_plotlyjs="cdn")
    return R


def s3e(M):
    R = {}
    br = logdiff(M["brent_usd"]); io = logdiff(M["iron_ore_unit_value"])
    z = lambda s: (s - s.mean()) / s.std()
    comp = br.copy()
    both = align(br, io)
    comp.loc[both.index] = (z(both.iloc[:, 0]) * br.std() + z(both.iloc[:, 1]) * br.std()) / 2  # scale to Brent vol
    comp = comp.dropna()
    tot = logdiff(M["wb/TOT.BRA"])
    rets = {"ibovespa_usd": logdiff(M["ibovespa_usd"])}
    for t in ["PETR", "VALE", "SUZB", "PRIO", "AXIA", "ITUB"]:
        rets[t] = logdiff(M[f"total_return_usd@{t}"])
    rets["IBOV_TR_USD"] = logdiff(M["total_return_usd@IBOV"])
    out = {}
    for nm, r in rets.items():
        row = {}
        for xn, x in [("brent", br), ("iron_ore", io), ("tot", tot), ("composite", comp)]:
            df = align(r, x)
            if len(df) < 36:
                continue
            b = boot_ols(df.iloc[:, 0].values, [df.iloc[:, 1].values], 12)
            row[xn] = {"beta": b["beta"][1], "ci95": b["ci95"][1], "r2": b["r2"], "n": b["n"],
                       "rho": _corr(df.iloc[:, 0].values, df.iloc[:, 1].values)}
        out[nm] = row
    R["betas"] = tag(out, ["ibovespa_usd", "brent_usd", "iron_ore_unit_value", "wb/TOT.BRA"] + [f"total_return_usd@{t}" for t in
                                                                                             ["PETR", "VALE", "SUZB", "PRIO", "AXIA", "ITUB", "IBOV"]],
                     SQL_M, note="monthly log returns; composite = mean z of dlog Brent & dlog iron-ore unit value (2014+), Brent alone before")
    ib = rets["ibovespa_usd"]
    R["corr_ibov_composite"] = tag(split_stats(comp, ib, 12, 36), ["ibovespa_usd", "brent_usd", "iron_ore_unit_value"], SQL_M)
    # pre/post 2010 betas to Brent (ibovespa_usd from 2000)
    pp = {}
    for nm, m in [("2000_2010", lambda i: i.year <= 2010), ("2011_2026", lambda i: i.year > 2010), ("2013_2026", lambda i: i.year > 2012)]:
        df = align(ib, br); df = df[m(df.index)]
        b = boot_ols(df.iloc[:, 0].values, [df.iloc[:, 1].values], 12)
        pp[nm] = {"beta": b["beta"][1], "ci95": b["ci95"][1], "r2": b["r2"], "n": b["n"]}
    R["ibov_brent_beta_pre_post"] = tag(pp, ["ibovespa_usd", "brent_usd"], SQL_M)
    R["interaction_ibov_brent"] = tag(interaction(br, ib, 12), ["ibovespa_usd", "brent_usd"])
    # decomposition: USD TR = BRL TR + FX
    brl_tr = logdiff(M["total_return_brl@IBOV"]); fxr = -logdiff(M["brl_usd"])  # + = BRL strengthens
    dec = {}
    for nm, y in [("usd_total", rets["IBOV_TR_USD"]), ("brl_local", brl_tr), ("fx_brl_vs_usd", fxr)]:
        df = align(y, comp)
        b = boot_ols(df.iloc[:, 0].values, [df.iloc[:, 1].values], 12)
        dec[nm] = {"beta_composite": b["beta"][1], "ci95": b["ci95"][1], "r2": b["r2"], "n": b["n"]}
    R["decomposition"] = tag(dec, ["total_return_usd@IBOV", "total_return_brl@IBOV", "brl_usd", "brent_usd", "iron_ore_unit_value"], SQL_M,
                             note="USD beta ~= local beta + FX beta (log returns are additive)")
    # up/down capture
    df = align(ib, comp)
    up = df[df.iloc[:, 1] > 0]; dn = df[df.iloc[:, 1] < 0]
    R["up_down"] = tag({"mean_ibov_up_pct": up.iloc[:, 0].mean() * 100, "mean_ibov_down_pct": dn.iloc[:, 0].mean() * 100,
                        "mean_comp_up_pct": up.iloc[:, 1].mean() * 100, "mean_comp_down_pct": dn.iloc[:, 1].mean() * 100,
                        "up_capture": up.iloc[:, 0].mean() / up.iloc[:, 1].mean(), "down_capture": dn.iloc[:, 0].mean() / dn.iloc[:, 1].mean(),
                        "n_up": len(up), "n_down": len(dn)}, ["ibovespa_usd", "brent_usd", "iron_ore_unit_value"], SQL_M)
    R["up_down"]["value"]["asymmetry_ratio"] = round(R["up_down"]["value"]["down_capture"] / R["up_down"]["value"]["up_capture"], 4)
    # rolling 60m beta to Brent
    d = align(ib, br)
    cov = d.iloc[:, 0].rolling(60).cov(d.iloc[:, 1]); var = d.iloc[:, 1].rolling(60).var()
    rb = (cov / var).dropna()
    di = align(rets["ITUB"], br)
    rbi = (di.iloc[:, 0].rolling(60).cov(di.iloc[:, 1]) / di.iloc[:, 1].rolling(60).var()).dropna()
    R["rolling60_beta"] = tag({"ibov_last": rb.iloc[-1], "ibov_min": rb.min(), "ibov_max": rb.max(), "ibov_mean_pre": rb[rb.index.year <= 2010].mean(),
                               "ibov_mean_post": rb[rb.index.year > 2010].mean(), "itub_last": rbi.iloc[-1], "last_date": str(rb.index[-1].date())},
                              ["ibovespa_usd", "brent_usd", "total_return_usd@ITUB"])
    # H5 / H6 citations
    ht = q("SELECT hyp_id, evidence FROM hypothesis_tests WHERE hyp_id IN ('H5','H6')").set_index("hyp_id")["evidence"].to_dict()
    R["cites"] = ht
    cs = R["corr_ibov_composite"]["value"]["full"]
    bc = out["ibovespa_usd"]["composite"]
    hedge = bc["beta"] > 0 and bc["ci95"][0] > 0
    R["hedge"] = bool(hedge)
    cls = "commodity proxy / high beta" if cs["pearson"] > 0.4 else ("partial hedge" if cs["pearson"] >= 0.2 else "not a commodity hedge")
    R["classification"] = cls
    R["summary"] = (f"Ibov USD on composite: beta {bc['beta']:.2f} (CI {bc['ci95'][0]:.2f},{bc['ci95'][1]:.2f}), rho {cs['pearson']:.2f} "
                    f"(CI {cs['ci95'][0]:.2f},{cs['ci95'][1]:.2f}, n={cs['n']}) -> '{cls}'; pre/post-2010 Brent beta "
                    f"{pp['2000_2010']['beta']:.2f} vs {pp['2011_2026']['beta']:.2f}")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rb.index, y=rb.values, name="Ibovespa USD"))
    fig.add_trace(go.Scatter(x=rbi.index, y=rbi.values, name="Itaú TR USD (domestic control)"))
    for t, col in [("PETR", "#c44"), ("VALE", "#2a7")]:
        dd = align(rets[t], br)
        rt = (dd.iloc[:, 0].rolling(60).cov(dd.iloc[:, 1]) / dd.iloc[:, 1].rolling(60).var()).dropna()
        fig.add_trace(go.Scatter(x=rt.index, y=rt.values, name=f"{t} TR USD", line=dict(color=col, dash="dot")))
    fig.add_hline(y=0, line_dash="dot"); fig.add_vline(x="2010-12-31", line_dash="dash")
    fig.update_layout(title="3e: rolling 60-month beta of monthly USD returns to dlog Brent", yaxis_title="beta", template="plotly_white")
    fig.write_html(os.path.join(CH, "3e_rolling_beta.html"), include_plotlyjs="cdn")
    return R


# ============================================================================= 4. verdict
def s4_verdict(S3):
    cm = pd.DataFrame(CLAIMS)
    pill = {}
    for p in ["physical", "institutional", "market"]:
        d = cm[cm.pillar == p]
        t = d[d.verdict != "Untestable"]
        score = t.thesis_score.mean()
        pill[p] = {"score": score, "n_total": len(d), "n_testable": len(t), "coverage": len(t) / len(d),
                   "label": "Supported" if score >= 0.75 else ("Partial" if score >= 0.5 else "Refuted"),
                   "counts": t.verdict.value_counts().to_dict()}
    phys_ok = pill["physical"]["score"] >= 0.75
    inst_low = pill["institutional"]["score"] <= 0.50
    conv = S3["3c"]["converted"]; hedge = S3["3e"]["hedge"]
    ps = pill["physical"]["score"]
    if phys_ok and inst_low and conv and hedge:
        overall = "Holds"
    elif ps < 0.5:
        overall = "Refuted"
    elif phys_ok:
        overall = "Holds for the physical column; institutional column refuted; returns not delivered post-2010"
    else:
        overall = ("Holds only partly for the physical column (score %.2f, below the 0.75 bar); institutional column refuted; "
                   "returns not delivered post-2010" % ps)
    # sensitivity of the physical score
    d = cm[(cm.pillar == "physical") & (cm.verdict != "Untestable")]
    sens = {"pro_claims_only": d[d.thesis_dir == "pro"].thesis_score.mean(),
            "status_T_only": d[d.status == "T"].thesis_score.mean(),
            "note_truth_rate (S=1,P=.5,R=0, ignoring thesis direction)": d.verdict.map({"Supported": 1, "Partial": .5, "Refuted": 0}).mean()}
    return {"pillars": pill, "physical_sensitivity": sens, "physical_gt_institutional_supported": bool(phys_ok and inst_low),
            "physical_minus_institutional": ps - pill["institutional"]["score"],
            "investment_thesis": {"endowment_converted": conv, "equity_hedge": hedge}, "overall": overall,
            "scoring_note": ("thesis_score per claim: pro-thesis claim Supported=1/Partial=.5/Refuted=0; for weaknesses the note concedes "
                             "(con) the score is inverted, so a pillar score measures how far the evidence favours the 'new America' thesis "
                             "in that column. Untestable excluded from the denominator.")}


# ============================================================================= report
def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def main():
    res = {"run_date": str(TODAY), "db": DB}
    print("== 0. anchors")
    A = s0_anchors()
    print(A.to_string())
    res["anchors"] = A.to_dict(orient="records")
    M = build_monthly()
    print("== 2. comparative"); S2 = s2_comparative(); res["s2_comparative"] = S2
    print("== 3a"); a = s3a(M)
    print("== 3b"); b = s3b(M)
    print("== 3c"); c = s3c(M)
    print("== 3d"); d = s3d(M)
    print("== 3e"); e = s3e(M)
    S3 = {"3a": _strip(a), "3b": b, "3c": c, "3d": d, "3e": e, "china_share": china_share(M)}
    ib, fx = year_end("ibovespa_usd"), year_end("brl_usd")
    R3 = {"ibov_2025": (ib[2025] / ib[2024] - 1) * 100, "brl_2025": (fx[2024] / fx[2025] - 1) * 100}
    print("== 1. claims")
    R1 = s1_claim_map(R3)
    R1.update(s1_rest(R1, S3, R3))
    res["s1_evidence"] = R1
    res["s3"] = {k: v for k, v in S3.items()}
    V = s4_verdict(S3)
    res["s4_verdict"] = V
    cm = pd.DataFrame(CLAIMS)
    cm.to_csv(os.path.join(OUT, "claim_map.csv"), index=False)
    res["claim_map"] = cm.to_dict(orient="records")
    res["series_used"] = {s: {k: _META[s][k] for k in ["source", "last_date", "title", "role", "agg"]} for s in sorted(_USED)}
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(_clean(res), f, indent=1, default=str)
    write_report(_clean(res))
    print(V["overall"])
    return res


def _strip(d):
    return d



# ============================================================================= report.md
def _ci(c):
    return f"[{c[0]:+.2f}, {c[1]:+.2f}]" if c else "n/a"


def _cs(d):
    if d.get("insufficient"):
        return f"n={d['n']} (insufficient)"
    return f"ρ={d['pearson']:+.2f} (Spearman {d['spearman']:+.2f}), CI {_ci(d['ci95'])}, p_perm={d['p_perm']:.3f}, n={d['n']}"


def _split_table(sp):
    rows = ["| window | result |", "|---|---|"]
    for k in ["full", "pre", "post", "pre2012", "post2012", "ex2020"]:
        if k in sp:
            rows.append(f"| {k} ({sp[k].get('start', '')[:7]}→{sp[k].get('end', '')[:7]}) | {_cs(sp[k])} |")
    return "\n".join(rows)


def _srcline(t):
    return "; ".join(f"`{x['series_id']}` ({x['source']}, last {x['last_date']})" for x in t["series"])


def write_report(res):
    S3, V, S2 = res["s3"], res["s4_verdict"], res["s2_comparative"]
    cm = pd.DataFrame(res["claim_map"])
    plan = open(os.path.join(OUT, "plan.md")).read()
    constraints = plan.split("**0.1")[1].split("**0.6")[0]
    constraints = "**0.1" + constraints
    a, b, c, d, e = S3["3a"], S3["3b"], S3["3c"], S3["3d"], S3["3e"]
    gpc = S2["gdp_pc_ppp"]["value"]; pli = S2["price_level_us100"]["value"]; stk = S2["equity_usd_index_yearend"]["value"]
    L = []
    w = L.append
    w("# Is Brazil still \"the New America\"? Testing Davidson (2012) against the warehouse, data to 2026\n")
    w(f"Run date {res['run_date']} · warehouse `{res['db']}` (read-only) · script `brazil_thesis_test.py` · full numbers in `results.json`, claims in `claim_map.csv`, charts in `charts/`.\n")
    w("## 1. Summary verdict\n")
    w(f"**{V['overall']}.**\n")
    w("Driving numbers:\n")
    w(f"1. **Endowment up, income flat.** Physical-endowment composite +{c['composites']['value']['2025']['endowment']:.2f} z vs 2010; outcome composite {c['composites']['value']['2025']['outcome']:+.2f} z; "
      f"GDP per capita PPP grew {gpc['cagr_2000_2010']:.2f}%/yr in 2000–10 but only {gpc['cagr_2010_2025']:.2f}%/yr in 2010–25 "
      f"(`wb/NY.GDP.PCAP.PP.KD.BR`, World Bank, last 2025-12-31; {gpc['2010']:,.0f} → {gpc['2025']:,.0f} int$ 2021). "
      f"Oil output doubled (`oil_production`, IPEAData, last 2026-07-01: 2,137 → 4,601 kbd).")
    w(f"2. **Institutions worsened.** Institutional composite {c['composites']['value']['2025']['institutions']:+.2f} z vs 2010; WGI control of corruption −0.02 → −0.41 and rule of law −0.04 → −0.45 (2010 → 2024, `wb/GOV_WGI_CC_EST.BR`, `wb/GOV_WGI_RL_EST.BR`, World Bank, last 2024-12-31); GFCF 20.5% → 16.8% of GDP.")
    w(f"3. **Returns not delivered.** USD equity index {stk['2010']:.1f} (Dec 2010) → {stk['2025']:.1f} (Dec 2025) even after 2025's +50.8% (`wb/DSTKMKTXD_M.BRA`, World Bank, last 2025-12-31); price level vs US 78.9 → 45.7 (`wb/PA.NUS.GDP.PLI.BR`). "
      f"Brazil equity does carry a positive commodity beta ({e['summary'].split(' -> ')[0]}), but Itaú (a domestic bank) has the same beta, so it is mostly a global risk-on beta.\n")
    w("Pillar scores (thesis-favourability, see rubric in §6):\n")
    w("| pillar | score | label | testable / total (coverage) | verdict counts |\n|---|---|---|---|---|")
    for p, x in V["pillars"].items():
        w(f"| {p} | {x['score']:.2f} | {x['label']} | {x['n_testable']}/{x['n_total']} ({x['coverage']:.0%}) | {x['counts']} |")
    w(f"\nPhysical-score sensitivity: pro-thesis claims only {V['physical_sensitivity']['pro_claims_only']:.2f}; fully-testable (T) claims only {V['physical_sensitivity']['status_T_only']:.2f}. "
      "The physical column is ahead of the institutional one (the note's reading holds in direction), but it does not clear the plan's 0.75 bar: most physical claims can only be tested by proxy or stale series (→ Partial), and two weaknesses the note itself concedes (hydro fragility, fertilizer import dependence) are confirmed.\n")
    w("## 2. Data constraints (verbatim from plan §0.1–0.5)\n")
    w(constraints.strip() + "\n")
    w("### Anchor check (plan §0.6)\n")
    an = pd.DataFrame(res["anchors"])
    w(f"{int(an.match.sum())}/{len(an)} anchors reproduced within tolerance. (First run flagged Pix count as off by 10⁶ — `pix_transactions_count` is in millions; fixed in code, not a data issue.)\n")
    w(md_table(an[["anchor", "series", "expected", "got", "match"]]) + "\n")
    w("## 3. Claim map\n")
    w("`verdict` = is the note's statement true in the data. `thesis_dir` = pro if the statement, when true, favours the thesis; con if it is a weakness. Untestable claims are excluded from scores.\n")
    w(md_table(cm[["claim_id", "pillar", "claim", "status", "statistic", "threshold", "verdict", "thesis_dir", "thesis_score", "note"]].fillna("")) + "\n")
    w("Series ids and last dates per claim are in `claim_map.csv` (`series_ids`, `last_dates`).\n")
    w("### Note claims that are factually wrong or off\n")
    w("- **Credit/GDP \"~30% in 2008\"** — wrong: BCB `credit_gdp` was 39.7% in Dec 2008 (Banco Central SGS, last 2026-08-01); ~30% matches 2000–04 (Dec 2000 " + f"{res['s1_evidence']['C1']['value']['bcb_2000']:.1f}%, Dec 2004 {res['s1_evidence']['C1']['value']['bcb_2004']:.1f}%). \"~54% now\" is close (55.4%, Aug 2026).")
    c3 = res["s1_evidence"]["C3"]["value"]
    w(f"- **\"Inflation 5–6%\"** — too high: `ipca_12m` was {c3['ipca12m_apr2026']:.2f}% in Apr 2026 and ranged {c3['ipca12m_2026_range'][0]:.2f}–{c3['ipca12m_2026_range'][1]:.2f}% in 2026 (BCB, last 2026-08-01). Selic 14.5% (Apr 2026 end) and real 8–11% (ex-ante {c3['real_policy_apr2026']:.1f}%) are right.")
    w("- **\"2021 drought worst in 91 years\"** — not visible in national data: 2021 EAR minimum 23.6% ranks only 6th-lowest of 2015–2026 (2017: 17.8%, 2015: 20.2%); 2021 mean CMO R$530 < 2015 R$567 (`stored_energy_ear`, `cmo_power_cost`, ONS, last 2026-10-02). The 91-year claim is about SE/CO inflows, which the warehouse lacks.")
    w(f"- **\"47 Mt → 354 Mt with far smaller area growth\"** — direction right over 1977–2024 (yield = 82% of cereal output growth), but since 2010 area expansion drove 65% of growth (second-crop corn): WB `wb/AG.PRD.CREL.MT.BR`/`AG.LND.CREL.HA.BR` (last 2024-12-31). The 47/354 Mt levels are CONAB grains incl. soy, not in warehouse.")
    w(f"- **\"Foreign B3 inflows R$56.5bn Jan–Apr 2026\"** — untestable; the only flow series (`wb/BX.PEF.TOTL.CD.WD.BR`, World Bank, last 2025-12-31) shows net portfolio-equity OUTflows of $17.5bn (2024) and $5.0bn (2025).")
    w("- **\"Wind+solar make the thesis sturdier\"** — share is real (29.8% in 2025) but the drop in EAR→power-price sensitivity is not robust (falls in levels, not in logs, and confounded by full reservoirs since 2022; see 3d).")
    w("- Confirmed exactly: Ibovespa +50.8% in USD in 2025; BRL +12.5% vs USD in 2025; Pix 326 transactions/person in 2025; gold 6.8% of reserves (2025).\n")
    w("## 4. Comparative frame (Brazil vs its 2010 self; US only via US-relative series)\n")
    w(S2["note"] + "\n")
    w("| series | 1990 | 2000 | 2010 | 2019 | 2025 |\n|---|---|---|---|---|---|")
    for nm, key in [("GDP pc PPP (2021 int$) `wb/NY.GDP.PCAP.PP.KD.BR`", "gdp_pc_ppp"), ("Price level, US=100 `wb/PA.NUS.GDP.PLI.BR`", "price_level_us100"),
                    ("REER (2010=100) `wb/PX.REX.REER.BR`", "reer")]:
        v = S2[key]["value"]
        w(f"| {nm} | " + " | ".join(fmt(v.get(str(y)), 1) for y in [1990, 2000, 2010, 2019, 2025]) + " |")
    v = S2["equity_usd_index_yearend"]["value"]
    w("| USD equity index, year-end `wb/DSTKMKTXD_M.BRA` | – | " + " | ".join(fmt(v.get(str(y)), 1) for y in [2000, 2010, 2019, 2025]) + " |")
    w("\nPre-2010 (1991–2010) vs post-2010 (2011–2025) annual means, block-bootstrap (block 3) CI on the difference:\n")
    w("| measure | pre | post | post − pre [95% CI] | post ex-2020 | post 2013+ |\n|---|---|---|---|---|---|")
    for k, t in S2["pre_post_panel"].items():
        x = t["value"]
        w(f"| {k} (`{t['series'][0]['series_id']}`, last {t['series'][0]['last_date']}) | {x['pre_mean']:.2f} (n={x['n_pre']}) | {x['post_mean']:.2f} (n={x['n_post']}) | {x['diff_post_minus_pre']:+.2f} {_ci(x['ci95'])} | {x['post_mean_ex2020']:.2f} | {x['post2012_mean']:.2f} |")
    w("\nReading: Brazil became ~42% cheaper relative to the US (PLI 78.9 → 45.7) and real GDP growth fell by 1.8 pts/yr after 2010 (CI excludes 0). Convergence to US income cannot be computed in-warehouse (no US series).\n")
    w("## 5. Correlation analyses\n")
    w("Method: growth rates / log-differences; Pearson + Spearman; 95% CI from moving-block bootstrap (block 12 monthly, 4 quarterly, 3 annual; 2,000 resamples); p-values by permutation (2,000 shuffles); n<36 monthly / n<10 annual not reported. Pre = ≤2010, post = ≥2011; robustness: split at 2012, ex-2020.\n")
    w("Monthly panel SQL (one query per series in code; equivalent to):\n```sql\n" + SQL_M.replace("(...)", "('ibovespa_usd','brl_usd','brent_usd','wb/TOT.BRA', ... )") +
      "\n-- equity/FX/credit_gdp/total_return_*: arg_max(value, date) (month-end); rates, EAR, CMO, flows: avg(value)\n```\nAnnual SQL:\n```sql\n" +
      SQL_ANN.format(y="current year") + "\n-- year-end FX/equity:\nSELECT EXTRACT(year FROM date)::INT AS year, arg_max(value, date) FROM v_observations WHERE series_id = ? AND date <= current_date GROUP BY 1\n```\n")
    # 3a
    w("### 3a. Growth, BRL, Ibovespa (USD) vs terms of trade / Brent\n")
    tv = a["tot_validation"]["value"]
    w(f"ToT validation: annual mean of `wb/TOT.BRA` vs `wb/TT.PRI.MRCH.XD.WD.BR` 2005–24 ρ={tv['rho']:.3f} (n={tv['n']}) → passes (>0.9), monthly ToT used.\n")
    w(f"**Monthly Δlog Ibovespa USD vs Δlog Brent** ({_srcline(a['corr_ibov_brent'])}):\n\n" + _split_table(a["corr_ibov_brent"]["value"]) + "\n")
    w(f"**Monthly Δlog BRL/USD vs Δlog Brent** (negative = BRL strengthens with oil):\n\n" + _split_table(a["corr_brl_brent"]["value"]) + "\n")
    w(f"**Monthly Δlog Ibovespa USD vs Δlog ToT**: full {_cs(a['corr_ibov_tot']['value']['full'])} — no monthly link with the broad ToT index.\n")
    o = a["ols_ibov_tot_brent"]["value"]
    w(f"OLS Δlog Ibov USD ~ Δlog ToT + Δlog Brent ({o['start'][:7]}→{o['end'][:7]}, n={o['n']}): β_ToT={o['beta_tot']:+.2f} {_ci(o['beta_tot_ci'])}, β_Brent={o['beta_brent']:+.2f} {_ci(o['beta_brent_ci'])}, R²={o['r2']:.2f} (pre {o['r2_pre']:.2f}, post {o['r2_post']:.2f}). "
      f"Post×Brent interaction {a['interaction_ibov_brent']['value']['beta_post_x']:+.2f} {_ci(a['interaction_ibov_brent']['value']['beta_post_x_ci'])} (not significant). "
      f"Rolling 60m ρ(Ibov, Brent): mean {a['rolling60_ibov_brent']['value']['mean_pre']:.2f} pre vs {a['rolling60_ibov_brent']['value']['mean_post']:.2f} post, latest {a['rolling60_ibov_brent']['value']['last']:.2f} ({a['rolling60_ibov_brent']['value']['last_date'][:7]}).\n")
    g = a["ccf_gdpq_tot"]["value"]
    w(f"**Quarterly Δlog real GDP vs Δlog ToT** (`wb/NYGDPMKTPSAKD_Q.BRA`, World Bank, last 2025-12-31), lag 0:\n\n" + _split_table(g["lag0"]) + "\n")
    w("CCF ρ(ToT_t, GDP_t+k), k = 0..4 quarters: " + "; ".join(f"{nm}: " + ", ".join(f"k{k}={x['rho']:+.2f}" for k, x in g["ccf"][nm].items()) for nm in ["full", "pre", "post"]) + "\n")
    w("**Annual real GDP growth vs Δlog ToT** (`wb/NY.GDP.MKTP.KD.ZG.BR`):\n\n" + _split_table(a["annual_gdp_tot"]["value"]) + "\n")
    w("Read-out: equity R² < 0.3 → Brazil's USD equity is **not** a pure commodity proxy; its link runs through Brent (ρ≈0.44 post-2010), not through the broad ToT index. GDP's sensitivity to ToT **fell** after 2010 (quarterly ρ 0.46 → 0.28, post CI includes 0): the endowment matters less for growth, not more. Chart: `charts/3a_rolling_corr.html`.\n")
    # 3b
    w("### 3b. High real rate vs credit, investment, GDP\n")
    w(f"X = `real_policy_rate` (Derived, ex-ante Selic − Focus IPCA 12m, last {meta('real_policy_rate')['last_date']}). ρ(real rate_t, Y_t+k), k = −12…+24 months.\n")
    w("| Y | most-negative lag in 6–18m | ρ full [CI] (n) | ρ pre-2010 (n) | ρ post-2010 [CI] (n) | ex-2020 | ex-post rate ρ |\n|---|---|---|---|---|---|---|")
    for nm, x in b["ccf_real_rate"]["value"].items():
        w(f"| {nm} | {x['lag_most_negative_6_18']} | {x['rho']:+.2f} {_ci(x['ci95'])} ({x['n']}) | {fmt(x['pre_rho'], 2)} ({x['pre_n']}) | {fmt(x['post_rho'], 2)} {_ci(x['post_ci'])} ({x['post_n']}) | {fmt(x['ex2020_rho'], 2)} | {fmt(x['expost_rate_rho_same_lag'], 2)} |")
    ao = b["annual_ols"]["value"]
    w(f"\nAnnual OLS 2002–2025: ΔGFCF%GDP on real rate β={ao['dGFCF_on_real_rate']['beta']:+.3f} {_ci(ao['dGFCF_on_real_rate']['ci95'])}, R²={ao['dGFCF_on_real_rate']['r2']:.2f}, n={ao['dGFCF_on_real_rate']['n']}; "
      f"GDP growth on real rate β={ao['gdp_growth_on_real_rate']['beta']:+.3f} {_ci(ao['gdp_growth_on_real_rate']['ci95'])}. r − g latest {b['r_minus_g']['value']['latest']:+.1f} pts ({b['r_minus_g']['value']['date'][:7]}; L3: {b['r_minus_g']['value']['L3_evidence']}).\n")
    w(f"Read-out: the cost of credit binds on **credit** post-2010 (household ρ −0.49, corporate ρ −0.42 at 7–10 month lags, CIs exclude 0) and predicts delinquency 9 months ahead (ρ +0.84); +1 pt real rate ≈ −0.10 pt GFCF/GDP the same year. It does **not** show up in monthly activity (IBC-Br ρ ≈ 0 or positive). Full-sample CIs straddle 0 because 2008–10 (counter-cyclical public-bank lending) flips the sign. Caveat: both sides persistent; block bootstrap mitigates but does not remove spurious-correlation risk. Chart: `charts/3b_ccf_real_rate.html`.\n")
    # 3c
    w("### 3c. Endowment improved, income did not converge\n")
    w(c["composites"]["note"] + "\n")
    cz = c["composites"]["value"]
    w(f"Composites (z, 2010 = 0): 2024 endowment {cz['2024']['endowment']:+.2f}, institutions {cz['2024']['institutions']:+.2f}, outcome {cz['2024']['outcome']:+.2f}; 2025 endowment {cz['2025']['endowment']:+.2f}, institutions {cz['2025']['institutions']:+.2f}, outcome {cz['2025']['outcome']:+.2f}.\n")
    w("| series | CAGR 2000–10 | CAGR 2010–last | last year |\n|---|---|---|---|")
    for k, x in c["cagr_table"]["value"].items():
        w(f"| `{k}` | {x['cagr_2000_2010']:+.2f}% | {x['cagr_2010_last']:+.2f}% | {x['last_year']} |")
    og = c["ols_gdppc"]["value"]
    w(f"\nOLS Δlog GDP pc PPP ~ Δlog ToT + ΔWGI mean (1997–2024, n={og['n']}): β_ToT={og['beta_dlogToT']:+.2f} {_ci(og['ci_dlogToT'])}, β_WGI={og['beta_dWGI']:+.2f} {_ci(og['ci_dWGI'])}, R²={og['r2']:.2f}. Low power; ToT is the only significant driver of year-to-year income growth, institutions' year-to-year changes are too noisy to identify.\n")
    w(f"Read-out: {c['summary']}. Endowment up, institutions down, outcome down → physical gains did not convert into income or USD returns. Chart: `charts/3c_three_line_index.html`.\n")
    # 3d
    w("### 3d. Reservoirs vs power cost and inflation\n")
    w("EAR (level, bounded %) vs log CMO, lags 0–3: " + "; ".join(f"k{k}: {_cs(x)}" for k, x in d["ear_logcmo_lags"]["value"].items()) + "\n")
    w("EAR vs administered-price inflation lags 0/3/6: " + "; ".join(f"k{k}: {_cs(x)}" for k, x in d["ear_admin_lags"]["value"].items() if k in ("0", "3", "6")) + "\n")
    w(f"Thermal share vs log CMO: {_cs(d['thermal_logcmo']['value'])}.\n")
    lr = d["low_ear_cmo_ratio"]
    dt = d["drought_table"]["value"]
    w(f"Months with EAR < 40% (n={lr['n_low']}): CMO R${lr['cmo_low']:.0f} vs R${lr['cmo_other']:.0f} → {lr['value']:.2f}× (warehouse H4: 3.1×). Drought years 2015/2017/2021 vs others: CMO R${dt['drought_mean_cmo']:.0f} vs R${dt['other_mean_cmo']:.0f}; admin-price inflation {dt['drought_mean_admin']:.2f} vs {dt['other_mean_admin']:.2f} %/mo; thermal share {dt['drought_mean_thermal']:.1f}% vs {dt['other_mean_thermal']:.1f}%.\n")
    oi = d["ols_interaction"]["value"]; ss = d["subsample_slopes"]["value"]
    w(f"Diversification test — OLS log CMO ~ EAR + EAR×WS + WS ({oi['start'][:7]}→{oi['end'][:7]}, n={oi['n']}): β_EAR={oi['beta_ear']:+.3f} {_ci(oi['ci_ear'])}, β_EAR×WS={oi['beta_ear_x_ws']:+.4f} {_ci(oi['ci_ear_x_ws'])}, R²={oi['r2']:.2f}. "
      f"Sub-sample slope of log CMO on EAR: 2015–21 {ss['2015_2021']:+.3f} {_ci(ss['ci_2015_2021'])} (n={ss['2015_2021_n']}) vs 2022–26 {ss['2022_2026']:+.3f} {_ci(ss['ci_2022_2026'])} (n={ss['2022_2026_n']}); difference {ss['diff_late_minus_early']:+.3f} {_ci(ss['diff_ci95'])}. "
      f"Rolling 36m ρ(EAR, log CMO): {d['rolling36']['value']['first']:+.2f} (first window) → {d['rolling36']['value']['last']:+.2f} ({d['rolling36']['value']['last_date'][:7]}). "
      f"Robustness in levels (CMO hit ~0 in {d['subsample_slopes_levels']['value']['months_cmo_below_5']} months of 2022–23, which distorts logs): R$/MWh per EAR point 2015–21 {d['subsample_slopes_levels']['value']['2015_2021']['beta_R$_per_pt']:+.1f} {_ci(d['subsample_slopes_levels']['value']['2015_2021']['ci95'])} vs 2022–26 {d['subsample_slopes_levels']['value']['2022_2026']['beta_R$_per_pt']:+.1f} {_ci(d['subsample_slopes_levels']['value']['2022_2026']['ci95'])}.\n")
    w("Read-out (mixed; partly contradicts plan expectation): wind+solar reached 29.8% of generation in 2025 and the *correlation* between reservoirs and price weakened. In logs the slope did **not** shrink and the EAR×WS interaction is ~0; in levels the R$/MWh sensitivity per storage point fell by about two-thirds (−14.9 → −4.9, CIs barely overlap). But reservoirs have been much fuller since 2022 (min EAR 34–59% vs 18–24% in 2015–21) and CMO is convex in EAR, so a flatter slope at high storage is expected with or without wind+solar; and the late window has had no drought to test. Verdict E4: Partial — share is significant, the sturdiness claim is not yet demonstrated. Chart: `charts/3d_ear_vs_cmo.html`.\n")
    # 3e
    w("### 3e. Brazil equity vs the commodity cycle: hedge or high-beta proxy?\n")
    w("Monthly log-return betas (block-bootstrap CI) to Δlog Brent / iron-ore unit value / ToT / composite:\n")
    w("| asset | β Brent [CI] | β iron ore [CI] | β composite [CI] | ρ composite | n |\n|---|---|---|---|---|---|")
    for nm, x in e["betas"]["value"].items():
        w(f"| {nm} | {x['brent']['beta']:+.2f} {_ci(x['brent']['ci95'])} | {x['iron_ore']['beta']:+.2f} {_ci(x['iron_ore']['ci95'])} | {x['composite']['beta']:+.2f} {_ci(x['composite']['ci95'])} | {x['composite']['rho']:+.2f} | {x['composite']['n']} |")
    w("\nΔlog Ibovespa USD vs Δlog composite:\n\n" + _split_table(e["corr_ibov_composite"]["value"]["full"] and e["corr_ibov_composite"]["value"]) + "\n")
    pp = e["ibov_brent_beta_pre_post"]["value"]
    w("Ibovespa-USD beta to Brent: " + "; ".join(f"{k}: {x['beta']:+.2f} {_ci(x['ci95'])} (R² {x['r2']:.2f}, n={x['n']})" for k, x in pp.items()) + "\n")
    dc = e["decomposition"]["value"]
    w(f"Decomposition (2012+): USD total-return beta {dc['usd_total']['beta_composite']:+.2f} {_ci(dc['usd_total']['ci95'])} = local BRL {dc['brl_local']['beta_composite']:+.2f} {_ci(dc['brl_local']['ci95'])} + FX {dc['fx_brl_vs_usd']['beta_composite']:+.2f} {_ci(dc['fx_brl_vs_usd']['ci95'])}.\n")
    ud = e["up_down"]["value"]
    w(f"Up/down capture vs composite: up {ud['up_capture']:.2f} (n={ud['n_up']}), down {ud['down_capture']:.2f} (n={ud['n_down']}), asymmetry {ud['asymmetry_ratio']:.2f} (<1 = captures less downside than upside).\n")
    rb = e["rolling60_beta"]["value"]
    w(f"Rolling 60m Brent beta: mean {rb['ibov_mean_pre']:.2f} pre-2010 vs {rb['ibov_mean_post']:.2f} post; latest {rb['ibov_last']:.2f} ({rb['last_date'][:7]}); Itaú latest {rb['itub_last']:.2f}. Warehouse H5: {e['cites']['H5']}. H6: {e['cites']['H6']}.\n")
    w(f"Read-out: classification **{e['classification']}** (ρ 0.2–0.4). β>0 with CI excluding 0 → meets the plan's 'hedge' test, but (i) R² is only ~0.09–0.16, (ii) Itaú — the domestic-bank control — has the same composite beta (+0.35), so most of the co-movement is global risk appetite, and (iii) the latest rolling beta has fallen to ~0.1. Only PETR/PRIO are genuine oil-beta vehicles (β 0.5–1.0). Chart: `charts/3e_rolling_beta.html`.\n")
    # 6
    w("## 6. Pillar scores and rubric roll-up\n")
    w(V["scoring_note"] + " Pillar label: ≥0.75 Supported, 0.50–0.74 Partial, <0.50 Refuted. Columns: physical = Energy, Water, Agro, Minerals; institutional = Credit, Institutions (+3b); market = Trade, Allocation, 3a, 3c, 3e. 3d feeds claim E4 (physical).\n")
    for p, x in V["pillars"].items():
        w(f"- **{p}**: {x['score']:.2f} → {x['label']}; coverage {x['n_testable']}/{x['n_total']} = {x['coverage']:.0%}; {x['counts']}")
    w(f"\nOverall logic: (1) physical ≥ 0.75 and institutional ≤ 0.50? physical {V['pillars']['physical']['score']:.2f}, institutional {V['pillars']['institutional']['score']:.2f} → "
      f"{'yes' if V['physical_gt_institutional_supported'] else 'no — institutional is low as expected, but physical misses the bar (direction holds: gap ' + format(V['physical_minus_institutional'], '+.2f') + ')'}. "
      f"(2) investment thesis: endowment converted into income/returns = {V['investment_thesis']['endowment_converted']}; equity is a commodity hedge (β>0, CI excl. 0) = {V['investment_thesis']['equity_hedge']}. "
      f"→ **{V['overall']}**.\n")
    w("## 7. Untestable claims (with this warehouse)\n")
    for _, r in cm[cm.verdict == "Untestable"].iterrows():
        w(f"- {r['claim_id']} {r['claim']} — {r['note'] or r['statistic']}")
    w("- Also untestable inside testable claims: world rankings (cleanest grid, #1 exporter, niobium/rare-earth shares, highest real rate in the world), gold tonnage (+43t), the 91-year drought, CONAB grain levels, ore grade, any Brazil-vs-US/China convergence ratio (no peer-country series).\n")
    w("## 8. Appendix A — every series used\n")
    w("| series_id | source | role | agg | last date |\n|---|---|---|---|---|")
    for sid, m in sorted(res["series_used"].items()):
        w(f"| `{sid}` | {m['source']} | {m['role']} | {m['agg']} | {m['last_date']} |")
    w("\nStale (last < 2022): " + ", ".join(f"`{s}`" for s, m in sorted(res["series_used"].items()) if m["last_date"] and m["last_date"] < "2022-01-01") + ".\n")
    w("## Appendix B — External data (not from warehouse)\n\nNone used. The verdict depends only on warehouse data.\n")
    w("## Recommendation\n\nIngest the same WB indicators for US/CN/IN/MX via the Dateno `wb/` namespace (e.g. `wb/NY.GDP.PCAP.PP.KD.US`) so the literal Brazil-vs-America comparison becomes possible.\n")
    open(os.path.join(OUT, "report.md"), "w").write("\n".join(L))


if __name__ == "__main__":
    main()
