"""Core helpers for the Congress study (warehouse access, annual panel, ToT, estimators, event-study engine).
Estimator code copied (not imported) from scratchpad/politics/politics_lean_study.py, which runs its whole study on import.
numpy / pandas / duckdb only. seed = 0.
"""
import itertools, math
from pathlib import Path
import numpy as np, pandas as pd, duckdb

OUT = Path(__file__).resolve().parent
RES = OUT / "research"
WH = "/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb"
con = duckdb.connect()
con.execute(f"ATTACH '{WH}' AS br (READ_ONLY)")
con.execute("USE br")
SEED, NBOOT = 0, 5000
SQL = {}
META = {}


def q(name, sql, params=None):
    SQL[name] = sql.strip()
    return con.execute(sql, params).df() if params is not None else con.execute(sql).df()


# ----------------------------------------------------------------------------- annual panel
ANNUAL_SQL = """
SELECT series_id, CAST(EXTRACT(year FROM date) AS INT) AS year,
       CASE WHEN any_value(c.agg) = 'sum' THEN sum(value)
            WHEN any_value(c.agg) = 'last' THEN arg_max(value, date)
            ELSE avg(value) END AS value,
       arg_max(value, date) AS year_end, count(*) AS n_obs, max(date) AS last_obs
FROM v_observations o JOIN catalog c USING (series_id)
WHERE date <= current_date AND series_id IN (SELECT unnest($1))
GROUP BY 1, 2 ORDER BY 1, 2"""
META_SQL = """
SELECT o.series_id, any_value(o.title) AS title, any_value(o.source) AS source, any_value(o.freq) AS freq,
       any_value(o.role) AS role, min(o.date) AS first_date, max(o.date) AS last_date, count(*) AS n
FROM v_observations o WHERE o.date <= current_date AND o.series_id IN (SELECT unnest($1)) GROUP BY 1"""
IDS = """primary_balance_gdp gross_public_debt_gdp net_public_debt_gdp interest_bill_gdp r_minus_g implicit_interest_rate
nominal_gdp_growth wb/GC.NLD.TOTL.GD.ZS.BR wb/GC.NFN.TOTL.GD.ZS.BR wb/GC.XPN.TOTL.GD.ZS.BR wb/GC.XPN.TRFT.ZS.BR
wb/NE.GDI.FTOT.ZS.BR wb/NE.GDI.FTOT.KD.ZG.BR wb/NE.CON.GOVT.ZS.BR real_policy_rate selic_target embi_brazil
gov_real_yield_10y wb/FR.INR.RISK.BR wb/FR.INR.RINR.BR focus_selic_12m wb/NY.GDP.MKTP.KD.ZG.BR wb/SL.UEM.TOTL.ZS.BR
unemployment_rate ilostat/EAR_INEE_NOC_NB.BRA wb/FP.CPI.TOTL.BR wb/AG.LND.PFLS.HA.BR wb/AG.LND.FRLS.HA.BR
exports_to_eu wb/TT.PRI.MRCH.XD.WD.BR wb/TX.UVI.MRCH.XD.WD.BR wb/TM.UVI.MRCH.XD.WD.BR wb/TOT.BRA brent_usd
gdp_nominal_12m_brl ibc_br wb/REER_M.BRA wb/DPANUSSPB_M.BRA wb/NY.GDP.DEFL.KD.ZG.BR wb/GOV_WGI_RQ_EST.BR""".split()
AP = q("annual_panel", ANNUAL_SQL, [IDS])
for r in q("meta", META_SQL, [IDS]).itertuples():
    META[r.series_id] = dict(title=r.title, source=r.source, freq=r.freq, role=r.role,
                             first_date=str(r.first_date)[:10], last_date=str(r.last_date)[:10], n=int(r.n))


def A(sid, y0=1984, col="value", complete_only=True):
    d = AP[AP.series_id == sid].set_index("year")
    f = META[sid]["freq"]
    if complete_only and f in ("monthly", "daily"):
        need = 12 if f == "monthly" else 200
        d = d[(d.n_obs >= need) | (d.index == 2026)]
    s = d[col]
    return s[s.index >= y0].astype(float)


def dlog(s):
    return 100 * np.log(s).diff()


def tot_series():
    tt = A("wb/TT.PRI.MRCH.XD.WD.BR", 1979)
    uvi = A("wb/TX.UVI.MRCH.XD.WD.BR", 1979) / A("wb/TM.UVI.MRCH.XD.WD.BR", 1979)
    ov = tt.index.intersection(uvi.index)
    k = np.exp(np.mean(np.log(tt[ov]) - np.log(uvi[ov])))
    tot = (uvi * k).copy(); tot.loc[tt.index] = tt
    m = A("wb/TOT.BRA", 1990)
    if 2025 not in tot.index and 2025 in m.index:
        tot.loc[2025] = tot.loc[2024] * m[2025] / m[2024]
    return tot.sort_index()


TOT = tot_series()
LTOT = np.log(TOT) * 100
DLTOT = LTOT.diff()


def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X))
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    r2 = 1 - r.var() / y.var() if y.var() > 0 else 0.0
    return b, r, r2


def tot_adjust(s, lean=None):
    """residual of y_t on dlogToT_t, logToT_t (+ left dummy), re-centred on mean(y). (politics Q0)"""
    df = pd.DataFrame({"y": s, "d": DLTOT, "l": LTOT})
    cols = ["d", "l"]
    if lean is not None:
        df["lean"] = lean; cols.append("lean")
    df = df.dropna(subset=["y"] + cols)
    df = df[df.index.isin(s.index)]
    if len(df) < 6:
        return None
    b, r, r2 = ols(df.y.values, [df[c].values for c in cols])
    return pd.Series(r + df.y.mean(), index=df.index)


def spearman(x, y):
    x = pd.Series(x).rank().values; y = pd.Series(y).rank().values
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3 or np.std(x) == 0:
        return np.nan
    return float(np.polyfit(x, y, 1)[0])


def perm_p_slope(x, y, rng, nmax=20000):
    """two-sided permutation p of the OLS slope (shuffle x across units); exact enumeration if n <= 8."""
    x = np.asarray(x, float); y = np.asarray(y, float); n = len(x)
    obs = abs(slope(x, y))
    if n <= 8:
        vals = [abs(slope(np.array(p), y)) for p in itertools.permutations(x)]
        vals = np.array(vals); return float(np.mean(vals >= obs - 1e-12)), float(1 / math.factorial(n)) if len(set(x)) == n else float(np.mean(vals >= vals.max() - 1e-12))
    vals = np.array([abs(slope(rng.permutation(x), y)) for _ in range(nmax)])
    return float((np.sum(vals >= obs - 1e-12) + 1) / (nmax + 1)), 1 / (nmax + 1)


def cluster_boot_slope(x, y, cl, rng, nboot=NBOOT):
    """resample clusters (dyads) with replacement; slope of y on x. x,y,cl arrays (unit = year or dyad)."""
    x = np.asarray(x, float); y = np.asarray(y, float); cl = np.asarray(cl)
    u = np.unique(cl); idx = {c: np.where(cl == c)[0] for c in u}
    out = np.empty(nboot)
    for b in range(nboot):
        pick = rng.choice(u, size=len(u), replace=True)
        ii = np.concatenate([idx[c] for c in pick])
        xx = x[ii]
        out[b] = np.polyfit(xx, y[ii], 1)[0] if len(np.unique(xx)) >= 3 else np.nan
    return out[~np.isnan(out)]


def perm_test(values, labels):
    values = np.asarray(values, float); labels = np.asarray(labels)
    n, k = len(values), int((labels == "left").sum())
    obs = values[labels == "left"].mean() - values[labels != "left"].mean()
    ds = []
    for comb in itertools.combinations(range(n), k):
        mask = np.zeros(n, bool); mask[list(comb)] = True
        ds.append(values[mask].mean() - values[~mask].mean())
    ds = np.abs(np.array(ds))
    return float(np.mean(ds >= abs(obs) - 1e-12)), float(np.mean(ds >= ds.max() - 1e-12)), len(ds)


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


# ----------------------------------------------------------------------------- event-study engine (copied from politics)
ES_SERIES = {"ibovespa_usd": ("logpct", 1), "brl_usd": ("logpct", -1), "embi_brazil": ("bp", 1),
             "gov_real_yield_10y": ("bp100", 1), "focus_selic_12m": ("level", 1)}
WINDOWS = {"[-1,+1]": (-1, 1), "[-5,+5]": (-5, 5), "[-20,+20]": (-20, 20), "[-60,+60]": (-60, 60)}
DAILY_SQL = """SELECT series_id, date, value FROM v_observations
WHERE date <= current_date AND series_id IN ('ibovespa_usd','brl_usd','embi_brazil','gov_real_yield_10y','focus_selic_12m','brent_usd')
ORDER BY series_id, date"""
DAILY = q("daily_panel", DAILY_SQL)
DAILY["date"] = pd.to_datetime(DAILY.date)
DS = {k: g.set_index("date").value for k, g in DAILY.groupby("series_id")}
BRENT_D = (100 * np.log(DS["brent_usd"]).diff()).dropna()


def daily_changes(sid):
    x = DS[sid]; kind, sign = ES_SERIES[sid]
    if kind == "logpct":
        d = 100 * np.log(x).diff()
    elif kind == "bp100":
        d = 100 * x.diff()
    else:
        d = x.diff()
    return sign * d.dropna()


def car(d, t0, a, b, est=(-250, -121), brent=None, raw=False):
    n = len(d)
    if t0 + est[0] < 0 or t0 + a < 1 or t0 + b >= n:
        return None
    seg = d.iloc[t0 + a: t0 + b + 1]
    span = (seg.index[-1] - seg.index[0]).days
    if span > 2.2 * (b - a + 1) + 15:
        return None
    if raw:
        return float(seg.sum())
    est_seg = d.iloc[t0 + est[0]: t0 + est[1] + 1]
    if brent is not None:
        bb = brent.reindex(d.index)
        xe = bb.iloc[t0 + est[0]: t0 + est[1] + 1]; ok = xe.notna() & est_seg.notna()
        if ok.sum() < 60:
            return None
        X = np.column_stack([np.ones(ok.sum()), xe[ok].values]); beta = np.linalg.lstsq(X, est_seg[ok].values, rcond=None)[0]
        xs = bb.iloc[t0 + a: t0 + b + 1].fillna(0.0)
        return float((seg - beta[0] - beta[1] * xs).sum())
    return float(seg.sum() - est_seg.mean() * len(seg))


def event_index(d, date):
    return d.index.searchsorted(pd.Timestamp(date))


def run_event_study(events):
    """events: list of (date, label, group, stage). returns (ev DataFrame, placebo dict)."""
    rows = []
    for sid in ES_SERIES:
        d = daily_changes(sid)
        for date, label, grp, stage in events:
            t0 = event_index(d, date)
            for wn, (a, b) in WINDOWS.items():
                live = t0 < len(d)
                v = car(d, t0, a, b) if live else None
                raw = car(d, t0, a, b, raw=True) if live else None
                vb = car(d, t0, a, b, brent=BRENT_D) if (live and sid in ("ibovespa_usd", "brl_usd")) else None
                rows.append(dict(series_id=sid, event_date=date, event=label, group=grp, stage=stage, window=wn,
                                 car=v, raw_change=raw, car_brent_adj=vb))
    ev = pd.DataFrame(rows)
    rngp = np.random.default_rng(SEED)
    edates = [pd.Timestamp(e[0]) for e in events]
    PL = {}
    for sid in ES_SERIES:
        d = daily_changes(sid)
        ok = np.ones(len(d), bool)
        for e in edates:
            ok &= np.abs((d.index - e).days) > 90
        cand = np.where(ok)[0]; cand = cand[(cand > 260) & (cand < len(d) - 70)]
        draws = rngp.choice(cand, size=min(2000, len(cand)), replace=len(cand) < 2000)
        for wn, (a, b) in WINDOWS.items():
            vals = [car(d, t, a, b) for t in draws]
            PL[(sid, wn)] = np.array([v for v in vals if v is not None], float)

    def pz(r):
        if r.car is None or pd.isna(r.car):
            return pd.Series({"placebo_p": np.nan, "z": np.nan})
        pl = PL[(r.series_id, r.window)]
        return pd.Series({"placebo_p": float(np.mean(np.abs(pl) >= abs(r.car))), "z": r.car / pl.std()})
    ev[["placebo_p", "z"]] = ev.apply(pz, axis=1)
    return ev, PL
