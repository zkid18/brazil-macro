"""Foreign investment by presidential term, Dilma → Temer → Bolsonaro → Lula III (Lula I–II as context).

Source: BCB SGS BPM6 monthly balance of payments (US$ mn), pulled into bcb_bop_monthly.csv
(codes listed in CODES below); GDP = SGS 4385 (monthly GDP, US$ mn). ToT/Brent/real Selic from the warehouse.
Flows are BoP sign convention for liabilities: + = foreigners putting money into Brazil.
"""
import json, numpy as np, pandas as pd, duckdb
from pathlib import Path

H = Path(__file__).parent
CODES = {"idp_net": 22885, "idp_in": 22886, "idp_out": 22887, "idp_equity_ex_reinv": 22891, "idp_reinv_earn": 22892,
         "idp_intercompany": 22893, "ide_outward_net": 22865, "port_liab_net": 22924, "port_eq_domestic": 22930,
         "port_funds_liab": 22936, "port_debt_domestic": 22942, "port_debt_external": 22945, "fin_account_net": 22863,
         "gdp_usd_mn": 4385}
TERMS = [("Lula I–II", "left", "2003-01", "2010-12"), ("Dilma I–II", "left", "2011-01", "2016-08"),
         ("Temer", "right", "2016-09", "2018-12"), ("Bolsonaro", "right", "2019-01", "2022-12"),
         ("Lula III", "left", "2023-01", "2026-08")]

df = pd.read_csv(H / "bcb_bop_monthly.csv", parse_dates=["date"]).set_index("date")
df["port_eq_total"] = df.port_eq_domestic + df.port_funds_liab
df["new_equity_capital"] = df.idp_equity_ex_reinv  # fresh money, excludes retained profits
FLOWS = ["idp_net", "idp_equity_ex_reinv", "idp_reinv_earn", "idp_intercompany", "ide_outward_net",
         "port_liab_net", "port_eq_total", "port_debt_domestic", "port_debt_external"]

def term_of(d):
    for n, l, a, b in TERMS:
        if pd.Timestamp(a) <= d <= pd.Timestamp(b) + pd.offsets.MonthEnd(0):
            return n
df["term"] = [term_of(d) for d in df.index]

# 1) term table: flow as % of GDP over the whole term (sum flows / sum GDP), plus US$ bn per year
rows = []
for n, l, a, b in TERMS:
    s = df.loc[a:b]
    r = {"term": n, "lean": l, "months": len(s), "gdp_usd_bn_yr": s.gdp_usd_mn.sum() / len(s) * 12 / 1e3}
    for f in FLOWS:
        r[f + "_pct_gdp"] = s[f].sum() / s.gdp_usd_mn.sum() * 100
        r[f + "_usd_bn_yr"] = s[f].sum() / len(s) * 12 / 1e3
    rows.append(r)
T = pd.DataFrame(rows).set_index("term")
T.to_csv(H / "term_table.csv")

# 2) calendar-year table (for charts and peer comparison)
Y = df[FLOWS + ["gdp_usd_mn"]].groupby(df.index.year).sum()
Y = Y[Y.index <= 2025]
YP = Y[FLOWS].div(Y.gdp_usd_mn, axis=0) * 100
YP.to_csv(H / "annual_pct_gdp.csv")
ytd = df.loc["2026-01":"2026-08"]; ytd_prev = df.loc["2025-01":"2025-08"]
YTD = {f: {"2026_jan_aug_usd_bn": ytd[f].sum() / 1e3, "2025_jan_aug_usd_bn": ytd_prev[f].sum() / 1e3} for f in FLOWS}

# 3) controlled regression on 12-month rolling flows/GDP: lean dummy + global/commodity controls
con = duckdb.connect(str(H.parents[2] / "warehouse/brazil_macro.duckdb"), read_only=True)
def m(sid, agg="avg"):
    q = f"select date_trunc('month', date) d, {agg}(value) v from v_observations where series_id=? and date<=current_date group by 1 order by 1"
    return con.execute(q, [sid]).df().set_index("d").v.rename(sid)
ctrl = pd.concat([m("wb/TOT.BRA"), m("brent_usd"), m("real_policy_rate"), m("brl_usd")], axis=1)
ctrl.index = pd.to_datetime(ctrl.index)
R = df[FLOWS + ["gdp_usd_mn"]].rolling(12).sum()
R = R[FLOWS].div(R.gdp_usd_mn, axis=0) * 100
R = R.join(ctrl).join(df.term)
R["left"] = R.term.map({n: int(l == "left") for n, l, *_ in TERMS})
R["tot_yoy"] = np.log(R["wb/TOT.BRA"]).diff(12) * 100
R["brent_yoy"] = np.log(R["brent_usd"]).diff(12) * 100
R = R.loc["2011-12":]  # Dilma onward: the four terms the user asked about

def ols(y, X):
    X = np.column_stack([np.ones(len(X)), X]); b = np.linalg.lstsq(X, y, rcond=None)[0]
    return b

def block_boot(d, ycol, xcols, B=2000, block=12, seed=7):
    d = d.dropna(subset=[ycol] + xcols)
    y, X = d[ycol].values, d[xcols].values; n = len(d)
    b0 = ols(y, X)[1]
    rng = np.random.default_rng(seed); bs = []
    nb = int(np.ceil(n / block))
    for _ in range(B):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, n - block, nb)])[:n]
        bs.append(ols(y[idx], X[idx])[1])
    lo, hi = np.percentile(bs, [10, 90])
    # term-label permutation: shuffle lean across the 4 terms (only 6 distinct 2-left/2-right assignments, so p floor = 1/6)
    return {"beta_left": b0, "ci80": [lo, hi], "n": n}

def term_perm(d, ycol, xcols):
    d = d.dropna(subset=[ycol] + xcols).copy(); terms = ["Dilma I–II", "Temer", "Bolsonaro", "Lula III"]
    import itertools
    obs = None; vals = []
    for combo in itertools.combinations(terms, 2):
        d["lp"] = d.term.isin(combo).astype(int)
        b = ols(d[ycol].values, d[["lp"] + xcols[1:]].values)[1]
        if set(combo) == {"Dilma I–II", "Lula III"}: obs = b
        vals.append(b)
    return {"perm_p_two_sided": float(np.mean(np.abs(vals) >= abs(obs) - 1e-12)), "all_assignments": vals}

REG = {}
for f in ["idp_net", "idp_equity_ex_reinv", "port_eq_total", "port_debt_domestic"]:
    REG[f] = {"raw": block_boot(R, f, ["left"]),
              "controls": block_boot(R, f, ["left", "tot_yoy", "brent_yoy", "real_policy_rate"]),
              "perm_raw": term_perm(R, f, ["left"])["perm_p_two_sided"]}

# 4) election windows: portfolio equity in the 6 months before vs after the 2nd round
EV = {}
for name, d in [("2014 Dilma re-elected", "2014-10"), ("2018 Bolsonaro elected", "2018-10"), ("2022 Lula elected", "2022-10")]:
    t = pd.Period(d, "M")
    pre = df.loc[str(t - 6):str(t - 1)]; post = df.loc[str(t + 1):str(t + 6)]
    EV[name] = {f: {"pre6_usd_bn": pre[f].sum() / 1e3, "post6_usd_bn": post[f].sum() / 1e3}
                for f in ["port_eq_total", "port_debt_domestic", "idp_equity_ex_reinv"]}

out = {"source": "BCB SGS BPM6 monthly (codes in CODES); GDP SGS 4385; last obs " + str(df.index.max().date()),
       "codes": CODES, "terms": T.round(3).reset_index().to_dict("records"), "ytd_2026": YTD,
       "regressions_12m_rolling_pct_gdp_2011_12_on": REG, "election_windows": EV}
json.dump(out, open(H / "results.json", "w"), indent=1, default=float)
pd.set_option("display.width", 250)
cols = [c for c in T.columns if c.endswith("_pct_gdp")]
print(T[cols].round(2).T.to_string())
print(T[[c for c in T.columns if c.endswith("_usd_bn_yr")]].round(1).T.to_string())
print(json.dumps({k: {kk: (vv if not isinstance(vv, dict) else {a: (round(b, 3) if isinstance(b, float) else b) for a, b in vv.items()}) for kk, vv in v.items()} for k, v in REG.items()}, indent=1, default=lambda x: [round(i, 3) for i in x]))
print(json.dumps(EV, indent=1, default=float))
print(json.dumps(YTD, indent=1))
