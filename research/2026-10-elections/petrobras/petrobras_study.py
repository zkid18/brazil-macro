"""petrobras_study.py — Petrobras and Brazilian governments (left vs right), Oct 2026 run-off.

Inputs: warehouse (read-only) + ./cache (fetch.py, ANP producer prices CSV, Tesouro RTN xlsx).
Outputs: results.json, *.csv, charts/*.html.   Pre-registration: preregistration.txt.
Run: .venv/bin/python research/2026-10-elections/petrobras/petrobras_study.py
"""
import glob, itertools, json, pathlib, sys
import duckdb, numpy as np, pandas as pd
import plotly.graph_objects as go

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CACHE, CH = HERE / "cache", HERE / "charts"
CH.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
import xlsx_lite  # noqa: E402

TODAY = pd.Timestamp("2026-10-10")
rng = np.random.default_rng(20261010)
con = duckdb.connect(str(ROOT / "warehouse/brazil_macro.duckdb"), read_only=True)
R = {"meta": {"run_date": str(TODAY.date()), "notes": []}}
LAST = {}  # series_id -> last date used


def ser(sid, start="1990-01-01"):
    df = con.execute("select date, value from observations where series_id=? and date::DATE<=?::DATE and date::DATE>=?::DATE order by date",
                     [sid, str(TODAY.date()), start]).df()
    s = df.set_index(pd.to_datetime(df.date)).value.astype(float)
    LAST[sid] = str(s.index.max().date())
    return s


TERMS = [("FHC", "2000-01-01", "2002-12-31", "right"), ("Lula I-II", "2003-01-01", "2010-12-31", "left"),
         ("Dilma", "2011-01-01", "2016-08-31", "left"), ("Temer", "2016-09-01", "2018-12-31", "right"),
         ("Bolsonaro", "2019-01-01", "2022-12-31", "right"), ("Lula III", "2023-01-01", "2026-12-31", "left")]
TERM_NAMES = [t[0] for t in TERMS]
LEAN = {t[0]: t[3] for t in TERMS}


def term_of(d):
    for n, a, b, _ in TERMS:
        if pd.Timestamp(a) <= d <= pd.Timestamp(b):
            return n
    return None


# ============================================================ 1. DATA ASSEMBLY
def load_cot():
    df = pd.concat([pd.read_csv(f, dtype={"date": str, "bdi": str, "tpmerc": str}) for f in glob.glob(str(CACHE / "cotahist_*.csv"))])
    df = df[df.tpmerc.str.zfill(3) == "010"]
    df["date"] = pd.to_datetime(df.date)
    df["p"] = df.close / df.fatcot
    df["pri"] = (df.bdi.str.zfill(2) != "02").astype(int)
    return df.sort_values(["ticker", "date", "pri"]).drop_duplicates(["ticker", "date"])


cot = load_cot()


def cot_px(tk):
    return cot[cot.ticker == tk].set_index("date").p.sort_index()


# ---- Petrobras PN daily total return (BRL)
# raw prices: COTAHIST 2000-2011, warehouse 2012-01-02..2026-10-02 (raw==adjusted, verified), COTAHIST D files after.
p_old = cot_px("PETR4")[:"2011-12-31"]
p_wh = ser("share_close_brl@PETR")
p_new = cot_px("PETR4")["2026-10-03":]
petr_px = pd.concat([p_old, p_wh, p_new]).sort_index()
petr_px = petr_px[~petr_px.index.duplicated()]
lr = np.log(petr_px).diff()
# known share-count events before 2012 (B3 corporate actions + COTAHIST gaps): log ratio of shares per old share
SPLITS = {"2000-06-23": np.log(1 / 100), "2005-09-01": np.log(4), "2008-04-28": np.log(2)}
for d, l in SPLITS.items():
    lr.loc[d] += l
# dividends: B3 json (ex-dates < 2012) as yield on prior close; warehouse dividend_per_share (ex-date) after
dj = pd.DataFrame(json.load(open(CACHE / "petr_cash_div.json")))
dj = dj[(dj.typeStock.str.strip() == "PN") & dj.corporateAction.str.strip().isin(["DIVIDENDO", "JRS CAP PROPRIO", "RENDIMENTO"])].copy()
dj["com"] = pd.to_datetime(dj.lastDatePriorEx, dayfirst=True)
num = lambda s: float(str(s).replace(".", "").replace(",", "."))
dj["y"] = dj.valueCash.map(num) / dj.closingPricePriorExDate.map(num)
sessions = petr_px.index
dj["ex"] = [sessions[sessions.searchsorted(c, side="right")] for c in dj.com]
dy_old = dj[(dj.ex >= "2000-01-04") & (dj.ex < "2012-01-02")].groupby("ex").y.sum()
dps = ser("dividend_per_share_brl@PETR")
prev_close = petr_px.shift(1)
dy_new = (dps / prev_close.reindex(dps.index)).groupby(level=0).sum()
divy = pd.concat([dy_old, dy_new]).groupby(level=0).sum().reindex(lr.index).fillna(0)
petr_tr_lr = np.log(np.exp(lr) + divy).fillna(0)  # total-return log return
petr_tr_lr.iloc[0] = 0
petr_tr_brl = np.exp(petr_tr_lr.cumsum())

# ---- FX, Brent, Ibovespa daily
fx = ser("brl_usd", "2000-01-01")
fx_ext = pd.Series({pd.Timestamp(d): v for d, v in [("2026-10-05", 4.9859), ("2026-10-06", 4.9698), ("2026-10-07", 4.9935),
                                                     ("2026-10-08", 5.0119), ("2026-10-09", 4.9892)]})  # SGS 1 pulled 2026-10-10
fx = pd.concat([fx, fx_ext[fx_ext.index > fx.index.max()]])
LAST["brl_usd(+SGS1 ext)"] = str(fx.index.max().date())
brent = ser("brent_usd", "2000-01-01")
fred = pd.read_csv(CACHE / "fred_brent.csv")
fred.columns = ["date", "v"]
fred = fred[pd.to_numeric(fred.v, errors="coerce").notna()]
fred = pd.Series(fred.v.astype(float).values, index=pd.to_datetime(fred.date))
brent = pd.concat([brent, fred[fred.index > brent.index.max()]])
LAST["brent_usd(+FRED DCOILBRENTEU ext)"] = str(brent.index.max().date())
ibov = ser("ibovespa_level", "2000-01-01")
bova = cot_px("BOVA11")["2026-09-01":]
ib_ext = ibov.iloc[-1] * bova[bova.index >= ibov.index.max()] / bova.loc[ibov.index.max()]
ibov = pd.concat([ibov, ib_ext[ib_ext.index > ibov.index.max()]])
LAST["ibovespa_level(+BOVA11 ext)"] = str(ibov.index.max().date())

# check fred vs warehouse overlap
ov = pd.concat([ser("brent_usd", "2020-01-01"), fred], axis=1, join="inner").dropna()
R["meta"]["brent_fred_vs_ipea_max_abs_diff"] = float((ov.iloc[:, 0] - ov.iloc[:, 1]).abs().max())


def other_px(name):
    """price-only daily series for comparison assets (COTAHIST before 2012 / after 2026-10-02, warehouse adj in between)."""
    old_tk, wh = {"VALE": ("VALE5", "share_close_adj_brl@VALE"), "ITUB": ("ITAU4|ITUB4", "share_close_adj_brl@ITUB"),
                  "AXIA": ("ELET3", "share_close_adj_brl@AXIA")}[name]
    parts = []
    for tk in old_tk.split("|"):
        parts.append(np.log(cot_px(tk)[:"2011-12-31"]).diff())
    old = pd.concat(parts).sort_index()
    old = old[old.abs() < 0.25]  # drop split/grouping days (none fall in election windows)
    w = np.log(ser(wh)).diff().dropna()
    newtk = {"VALE": "VALE3", "ITUB": "ITUB4", "AXIA": "AXIA3"}[name]
    nw = cot_px(newtk)
    nw = np.log(nw).diff()["2026-10-03":]
    return pd.concat([old, w, nw]).sort_index()


# ---- daily return panel (log)
D = pd.DataFrame({"petr_brl": petr_tr_lr, "ibov": np.log(ibov).diff(), "brent": np.log(brent).diff(),
                  "fx": np.log(fx).diff()})
D = D[D.index >= "2000-01-04"]
D["petr_usd"] = D.petr_brl - D.fx
D["ibov_usd"] = D.ibov - D.fx
D["brl"] = -D.fx  # + = BRL appreciates
for n in ["VALE", "ITUB", "AXIA"]:
    D[n.lower()] = other_px(n)
W_PETR = 0.12
D["ibov_ex"] = (D.ibov - W_PETR * D.petr_brl) / (1 - W_PETR)
D = D[D.petr_brl.notna() & D.ibov.notna()]

# ---- monthly panel (USD log returns)
lvl = pd.DataFrame({"petr_usd": petr_tr_brl / fx.reindex(petr_tr_brl.index).ffill(),
                    "ibov_usd": ibov / fx.reindex(ibov.index).ffill(), "brent": brent}).ffill()
M = np.log(lvl.resample("ME").last()).diff()
M = M[(M.index >= "2000-02-01") & (M.index <= "2026-09-30")].dropna()
M["term"] = [term_of(d) for d in M.index]
# cross-check with the warehouse total return series
wh_tr = ser("total_return_usd@PETR")
chk = pd.concat([lvl.petr_usd.resample("ME").last(), wh_tr.resample("ME").last()], axis=1).dropna()["2012-02":"2026-09"]
chk = np.log(chk).diff().dropna()
R["meta"]["monthly_corr_vs_warehouse_total_return_usd@PETR"] = float(chk.corr().iloc[0, 1])
R["meta"]["ann_return_diff_vs_warehouse_pp"] = float((chk.iloc[:, 0].mean() - chk.iloc[:, 1].mean()) * 1200)

# ============================================================ Q1 RETURNS BY TERM
X = np.column_stack([np.ones(len(M)), M.brent])
beta1 = np.linalg.lstsq(X, M.petr_usd, rcond=None)[0]
M["ab1"] = M.petr_usd - beta1[1] * M.brent
X2 = np.column_stack([np.ones(len(M)), M.brent, M.ibov_usd])
beta2 = np.linalg.lstsq(X2, M.petr_usd, rcond=None)[0]
M["ab2"] = M.petr_usd - beta2[1] * M.brent - beta2[2] * M.ibov_usd
M["xs_ibov"] = M.petr_usd - M.ibov_usd
R["q1_models"] = {"brent_beta": float(beta1[1]), "alpha_monthly": float(beta1[0]),
                  "two_factor": {"brent": float(beta2[1]), "ibov_usd": float(beta2[2])},
                  "r2_brent_only": float(1 - ((M.petr_usd - X @ beta1) ** 2).sum() / ((M.petr_usd - M.petr_usd.mean()) ** 2).sum()),
                  "sample": f"{M.index.min().date()}..{M.index.max().date()}", "n_months": int(len(M))}

rows = []
for n in TERM_NAMES:
    g = M[M.term == n]
    rows.append(dict(term=n, lean=LEAN[n], months=len(g), first=str(g.index.min().date()), last=str(g.index.max().date()),
                     petr_tr_usd_ann=100 * (np.exp(g.petr_usd.mean() * 12) - 1),
                     ibov_usd_ann=100 * (np.exp(g.ibov_usd.mean() * 12) - 1),
                     brent_ann=100 * (np.exp(g.brent.mean() * 12) - 1),
                     excess_vs_ibov_pp=100 * g.xs_ibov.mean() * 12,
                     brent_adj_abnormal_pp=100 * g.ab1.mean() * 12,
                     two_factor_abnormal_pp=100 * g.ab2.mean() * 12,
                     cum_petr_usd_pct=100 * (np.exp(g.petr_usd.sum()) - 1)))
term_tab = pd.DataFrame(rows)
term_tab.round(2).to_csv(HERE / "term_returns.csv", index=False)
R["q1_term_table"] = term_tab.round(2).to_dict("records")


def lr_diff(df, col, left_terms):
    return df[df.term.isin(left_terms)][col].mean() - df[~df.term.isin(left_terms)][col].mean()


LEFT = [t for t in TERM_NAMES if LEAN[t] == "left"]


def block_boot(df, col, B=5000, block=12):
    out = []
    groups = [df[df.term.isin(LEFT)][col].values, df[~df.term.isin(LEFT)][col].values]
    for _ in range(B):
        ms = []
        for x in groups:
            n = len(x)
            starts = rng.integers(0, n, int(np.ceil(n / block)))
            idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
            ms.append(x[idx].mean())
        out.append(ms[0] - ms[1])
    return np.array(out)


q1 = {}
for col in ["petr_usd", "xs_ibov", "ab1", "ab2"]:
    obs = lr_diff(M, col, LEFT)
    bs = block_boot(M, col)
    perms = [lr_diff(M, col, list(c)) for c in itertools.combinations(TERM_NAMES, 3)]
    q1[col] = dict(left_minus_right_ann_pp=float(obs * 1200),
                   boot_90ci_ann_pp=[float(np.percentile(bs, 5) * 1200), float(np.percentile(bs, 95) * 1200)],
                   boot_p_one_sided_lt0=float(np.mean((bs - obs) <= obs)) if obs < 0 else float(np.mean((bs - obs) >= obs)),
                   perm_p_one_sided=float(np.mean(np.array(perms) <= obs + 1e-12)),
                   perm_rank=f"{int(np.sum(np.array(perms) <= obs + 1e-12))} of 20")
# exclude FHC (partial, 2000-02) as robustness
M5 = M[M.term != "FHC"]
q1["ab1_exFHC_left_minus_right_ann_pp"] = float(lr_diff(M5, "ab1", LEFT) * 1200)
# drop 2008-09 GFC & 2020 covid robustness
Mx = M[~((M.index >= "2008-09-01") & (M.index <= "2009-03-31")) & ~((M.index >= "2020-02-01") & (M.index <= "2020-06-30"))]
q1["ab1_ex_crises_left_minus_right_ann_pp"] = float(lr_diff(Mx, "ab1", LEFT) * 1200)
R["q1_tests"] = q1
# since 2026 first round
R["q1_since_first_round"] = {
    "petr_brl_pct_2026-10-02_to_10-09": float(100 * (petr_tr_brl.loc["2026-10-09"] / petr_tr_brl.loc["2026-10-02"] - 1)),
    "ibov_pct": float(100 * (ibov.loc["2026-10-09"] / ibov.loc["2026-10-02"] - 1)),
    "brl_pct": float(100 * (fx.loc["2026-10-02"] / fx.loc["2026-10-09"] - 1))}

# ============================================================ Q2 EVENT STUDY
# sign: +1 = predicted positive for Petrobras (pro-market), -1 = predicted negative
EVENTS = [
    ("2002-10-27", "Election run-off: Lula (PT) wins", "election", -1, True),
    ("2006-10-29", "Election run-off: Lula re-elected", "election", -1, True),
    ("2010-10-31", "Election run-off: Dilma wins", "election", -1, True),
    ("2014-10-26", "Election run-off: Dilma re-elected", "election", -1, True),
    ("2018-10-28", "Election run-off: Bolsonaro wins", "election", +1, True),
    ("2022-10-30", "Election run-off: Lula wins", "election", -1, True),
    ("2026-10-04", "First round 2026: Flávio 47.0 vs Lula 45.2", "election", +1, True),
    ("2014-10-05", "First round 2014: Aécio into run-off (exploratory)", "election_r1", +1, False),
    ("2018-10-07", "First round 2018: Bolsonaro 46% (exploratory)", "election_r1", +1, False),
    ("2022-10-02", "First round 2022: Bolsonaro beats polls (exploratory)", "election_r1", +1, False),
    ("2016-10-14", "PPI import-parity pricing policy adopted", "pricing", +1, True),
    ("2023-05-16", "PPI abandoned; 'commercial strategy'", "pricing", -1, True),
    ("2021-02-19", "Bolsonaro removes CEO Castello Branco (announced Fri evening)", "ceo", -1, True),
    ("2022-03-28", "Govt names Adriano Pires to replace Silva e Luna", "ceo", -1, True),
    ("2022-05-23", "Govt removes CEO José Mauro Coelho", "ceo", -1, True),
    ("2024-05-14", "Lula removes CEO Prates; Magda Chambriard named (evening)", "ceo", -1, True),
    ("2018-06-01", "CEO Parente resigns after truckers' strike (intraday)", "ceo", -1, False),
    ("2024-03-07", "Board withholds extraordinary dividends (evening)", "dividend", -1, True),
    ("2024-04-19", "Govt/board agree to pay 50% of extraordinary dividends", "dividend", +1, True),
]
IDX = D.index


def day0(date, evening):
    d = pd.Timestamp(date)
    i = IDX.searchsorted(d, side="right" if evening else "left")
    return i


EVENING = {"2021-02-19", "2022-03-28", "2022-05-23", "2024-05-14", "2024-03-07", "2016-10-14x"}


def car(i0, y, x, windows=((0, 1), (0, 5), (-5, -1)), est=(-250, -21)):
    a, b = i0 + est[0], i0 + est[1]
    if a < 0:
        return None
    e = D.iloc[a:b][[y, x]].dropna()
    if len(e) < 120:
        return None
    bb = np.polyfit(e[x], e[y], 1)
    sd = (e[y] - np.polyval(bb, e[x])).std()
    out = {"beta": bb[0], "sd": sd}
    for w0, w1 in windows:
        seg = D.iloc[max(i0 + w0, 0): i0 + w1 + 1][[y, x]]
        if len(seg) < (w1 - w0 + 1) or seg.isna().any().any():
            seg = seg.dropna()
            out[f"n{w0}{w1}"] = len(seg)
        ar = seg[y] - np.polyval(bb, seg[x])
        out[f"car{w0},{w1}"] = ar.sum() if len(seg) else np.nan
        out[f"raw{w0},{w1}"] = seg[y].sum() if len(seg) else np.nan
        out[f"len{w0},{w1}"] = len(seg)
    return out


MODELS = {"ibov": ("petr_brl", "ibov"), "brent": ("petr_usd", "brent")}
ev_rows = []
ev_idx = []
for date, label, kind, sign, prereg in EVENTS:
    i0 = day0(date, date in EVENING or pd.Timestamp(date).weekday() >= 5)
    ev_idx.append(i0)
    row = dict(date=date, day0=str(IDX[i0].date()), event=label, kind=kind, predicted_sign=sign, preregistered=prereg)
    for m, (y, x) in MODELS.items():
        c = car(i0, y, x)
        for k in ["car0,1", "car0,5", "car-5,-1", "raw0,1", "raw0,5"]:
            row[f"{m}_{k}"] = 100 * c[k] if c else np.nan
        row[f"{m}_days0,5"] = c["len0,5"] if c else 0
    ev_rows.append(row)
ev = pd.DataFrame(ev_rows)

# placebo distribution
excl = set()
for i0 in ev_idx:
    excl.update(range(i0 - 20, i0 + 21))
cand = [i for i in range(260, len(IDX) - 6) if i not in excl and IDX[i] <= pd.Timestamp("2026-09-20")]
pl_idx = rng.choice(cand, 2000, replace=False)
pl = {m: {"car0,1": [], "car0,5": []} for m in MODELS}
for i in pl_idx:
    for m, (y, x) in MODELS.items():
        c = car(i, y, x, windows=((0, 1), (0, 5)))
        if c:
            pl[m]["car0,1"].append(100 * c["car0,1"])
            pl[m]["car0,5"].append(100 * c["car0,5"])
pl = {m: {k: np.array([v for v in vv if np.isfinite(v)]) for k, vv in d.items()} for m, d in pl.items()}


def emp_p(x, dist):
    if not np.isfinite(x):
        return np.nan
    return float(min(1.0, 2 * min(np.mean(dist <= x), np.mean(dist >= x))))


for m in MODELS:
    for k in ["car0,1", "car0,5"]:
        ev[f"{m}_{k}_placebo_p"] = [emp_p(x, pl[m][k]) for x in ev[f"{m}_{k}"]]
ev.round(3).to_csv(HERE / "event_study.csv", index=False)
R["q2_placebo"] = {m: {k: {"n": int(len(v)), "sd_pct": float(v.std()), "p5": float(np.percentile(v, 5)),
                           "p95": float(np.percentile(v, 95))} for k, v in d.items()} for m, d in pl.items()}

# group statistics on pre-registered events (signed CAR)
pre = ev[ev.preregistered]
grp = {}
for m in MODELS:
    for k in ["car0,1", "car0,5"]:
        sub = pre[[f"{m}_{k}", "predicted_sign"]].dropna()
        s = sub[f"{m}_{k}"] * sub.predicted_sign
        sg = sub.predicted_sign.values
        sims = np.array([(rng.choice(pl[m][k], len(s)) * sg).mean() for _ in range(10000)])
        # binomial sign test
        from math import comb
        nk, npos = len(s), int((s > 0).sum())
        p_sign = sum(comb(nk, j) for j in range(npos, nk + 1)) / 2 ** nk
        grp[f"{m}_{k}"] = dict(n=nk, mean_signed_car_pct=float(s.mean()), placebo_p_one_sided=float(np.mean(sims >= s.mean())),
                               n_correct_sign=npos, sign_test_p=float(p_sign))
    for kind in ["election", "ceo", "pricing", "dividend"]:
        s = (ev[(ev.kind == kind) & ev.preregistered][f"{m}_car0,1"] * ev[(ev.kind == kind) & ev.preregistered].predicted_sign).dropna()
        grp[f"{m}_car0,1_{kind}"] = dict(n=int(len(s)), mean_signed_car_pct=float(s.mean()))
R["q2_groups"] = grp
R["q2_events"] = ev.round(2).replace({np.nan: None}).to_dict("records")

# ============================================================ Q5a ELECTION SENSITIVITY ACROSS ASSETS
ASSETS = {"petr_brl": "Petrobras PN", "ibov_ex": "Ibovespa ex-Petrobras", "brl": "BRL vs USD", "itub": "Itaú",
          "vale": "Vale", "axia": "Axia/Eletrobras"}
el = [(d, l, s) for d, l, k, s, p in EVENTS if k in ("election", "election_r1")]
zrows = []
for d, l, s in el:
    i0 = day0(d, True)
    for a, nm in ASSETS.items():
        est = D.iloc[max(i0 - 250, 0): i0 - 20][a].dropna()
        seg = D.iloc[i0:i0 + 2][a]
        seg5 = D.iloc[i0:i0 + 6][a]
        if len(est) < 100 or seg.isna().any():
            continue
        sd = est.std()
        zrows.append(dict(date=d, event=l, asset=nm, r01_pct=100 * seg.sum(), z01=seg.sum() / (sd * np.sqrt(2)),
                          r05_pct=100 * seg5.dropna().sum(), z05=seg5.dropna().sum() / (sd * np.sqrt(len(seg5.dropna()))),
                          signed_z01=s * seg.sum() / (sd * np.sqrt(2)), sd_daily_pct=100 * sd))
Z = pd.DataFrame(zrows)
Z.round(3).to_csv(HERE / "election_sensitivity.csv", index=False)
common = Z.groupby("date").asset.nunique()
common_dates = common[common == len(ASSETS)].index
zs = (Z[Z.date.isin(common_dates)].groupby("asset")
      .agg(n=("z01", "size"), mean_abs_z01=("z01", lambda x: x.abs().mean()), mean_signed_z01=("signed_z01", "mean"),
           mean_abs_r01_pct=("r01_pct", lambda x: x.abs().mean()), mean_abs_z05=("z05", lambda x: x.abs().mean()))
      .sort_values("mean_abs_z01", ascending=False))
zs_runoffs = (Z[Z.date.isin(common_dates) & Z.date.isin([d for d, l, k, s, p in EVENTS if k == "election"])]
              .groupby("asset").agg(n=("z01", "size"), mean_abs_z01=("z01", lambda x: x.abs().mean()),
                                    mean_abs_r01_pct=("r01_pct", lambda x: x.abs().mean())).sort_values("mean_abs_z01", ascending=False))
R["q5_election_sensitivity_all_common"] = zs.round(3).reset_index().to_dict("records")
R["q5_election_sensitivity_preregistered_runoffs+2026"] = zs_runoffs.round(3).reset_index().to_dict("records")
R["q5_common_event_dates"] = list(common_dates)
# Oct 2026 first round snapshot raw returns, all assets
R["q5_2026_first_round_r01"] = Z[Z.date == "2026-10-04"][["asset", "r01_pct", "z01"]].round(2).to_dict("records")

# ============================================================ Q3 FUNDAMENTALS
q = con.execute("select * from v_company_quarterly where entity_id='PETR' and quarter_end<=?::DATE order by quarter_end", [str(TODAY.date())]).df()
q["quarter_end"] = pd.to_datetime(q.quarter_end)
for c_ in ["revenue_brl", "ebit_brl", "net_income_brl", "capex_brl", "dividends_paid_brl", "net_debt_brl_bn"]:
    LAST[c_ + "@PETR"] = str(q.quarter_end.max().date())
fxq = fx.resample("QE").mean()
q["fxavg"] = fxq.reindex(q.quarter_end).values
q["fxend"] = fx.resample("QE").last().reindex(q.quarter_end).values
q["capex_usd"] = q.capex_brl / q.fxavg
q["div_usd"] = q.dividends_paid_brl / q.fxavg
q["ni_usd"] = q.net_income_brl / q.fxavg
q["nd_usd"] = q.net_debt_brl_bn / q.fxend
q["ebit_usd"] = q.ebit_brl / q.fxavg
q["term"] = [term_of(d) for d in q.quarter_end]
brq = brent.resample("QE").mean()
q["brent"] = brq.reindex(q.quarter_end).values
fund = []
for n in TERM_NAMES:
    g = q[q.term == n]
    if g.empty:
        continue
    yrs = len(g) / 4
    fund.append(dict(term=n, quarters=len(g), first_q=str(g.quarter_end.min().date()), last_q=str(g.quarter_end.max().date()),
                     brent_avg=g.brent.mean(),
                     revenue_usd_bn_yr=g.revenue_usd_bn.sum() / yrs, net_income_usd_bn_yr=g.ni_usd.sum() / yrs,
                     dividends_usd_bn_yr=g.div_usd.sum() / yrs, capex_usd_bn_yr=g.capex_usd.sum() / yrs,
                     payout_pct=100 * g.dividends_paid_brl.sum() / g.net_income_brl.sum(),
                     div_share_of_div_plus_capex_pct=100 * g.dividends_paid_brl.sum() / (g.dividends_paid_brl.sum() + g.capex_brl.sum()),
                     net_debt_usd_bn_end=g.nd_usd.iloc[-1], net_debt_usd_bn_start=g.nd_usd.iloc[0],
                     nd_to_ebit_end=g.net_debt_brl_bn.iloc[-1] / g.ebit_brl.iloc[-4:].sum() if len(g) >= 4 else np.nan,
                     ebit_margin_pct=100 * g.ebit_brl.sum() / g.revenue_brl.sum(),
                     revenue_usd_per_brent=(g.revenue_usd_bn / g.brent).mean()))
fund = pd.DataFrame(fund)
# production
prod_nat = ser("oil_production", "2000-01-01")
prod_op = ser("operated_oil_production_kbd@PETR")
pr = []
for n in TERM_NAMES:
    a, b = [(t[1], t[2]) for t in TERMS if t[0] == n][0]
    pn = prod_nat[a:b]
    po = prod_op[a:b]
    yrs = (pn.index[-1] - pn.index[0]).days / 365.25
    pr.append(dict(term=n, national_oil_kbd_avg=pn.mean(), national_oil_growth_pct_yr=100 * ((pn.iloc[-1] / pn.iloc[0]) ** (1 / yrs) - 1) if yrs > 0.5 else np.nan,
                   petr_operated_kbd_avg=po.mean() if len(po) else np.nan,
                   petr_operated_growth_pct_yr=100 * ((po.iloc[-1] / po.iloc[0]) ** (1 / ((po.index[-1] - po.index[0]).days / 365.25)) - 1) if len(po) > 12 else np.nan))
fund = pd.DataFrame(pr).merge(fund, on="term", how="left")
fund.round(2).to_csv(HERE / "fundamentals_by_term.csv", index=False)
R["q3_fundamentals_by_term"] = fund.round(2).replace({np.nan: None}).to_dict("records")
qa = q.assign(year=q.quarter_end.dt.year).groupby("year").agg(
    net_income_brl_bn=("net_income_brl", "sum"), dividends_paid_brl_bn=("dividends_paid_brl", "sum"),
    capex_brl_bn=("capex_brl", "sum"), capex_usd_bn=("capex_usd", "sum"), div_usd_bn=("div_usd", "sum"),
    net_debt_brl_bn_end=("net_debt_brl_bn", "last"), net_debt_usd_bn_end=("nd_usd", "last"), quarters=("quarter_end", "size"))
qa["payout_pct"] = 100 * qa.dividends_paid_brl_bn / qa.net_income_brl_bn
qa.round(2).to_csv(HERE / "petrobras_annual.csv")

# ---- fuel prices vs Brent (ANP producer prices, include PIS/Cofins/CIDE, exclude ICMS)
fp = pd.read_csv(CACHE / "anp_producer_prices.csv", parse_dates=["week_start"])
fp["prod"] = fp["product"].map(lambda s: "gasoline" if s.startswith("Gasolina A (") or s.startswith("Gasolina A Comum") else
                               ("diesel" if s.startswith("Óleo Diesel (") or s.startswith("Óleo Diesel²") else None))
fp = fp.dropna(subset=["prod"])
fpm = fp.groupby(["prod", pd.Grouper(key="week_start", freq="ME")]).brazil_brl.mean().unstack(0)
fxm = fx.resample("ME").mean()
brm = brent.resample("ME").mean()
L_PER_BBL = 158.987
fuel = pd.DataFrame({k: fpm[k] / fxm.reindex(fpm.index) * L_PER_BBL for k in ["gasoline", "diesel"]})
fuel["brent"] = brm.reindex(fuel.index)
fuel = fuel.dropna()
fuel["gas_ratio"] = fuel.gasoline / fuel.brent
fuel["dsl_ratio"] = fuel.diesel / fuel.brent
fuel["gas_spread"] = fuel.gasoline - fuel.brent
fuel["dsl_spread"] = fuel.diesel - fuel.brent
fuel["term"] = [term_of(d) for d in fuel.index]
LAST["ANP producer prices (gasoline A, diesel)"] = str(fp.week_start.max().date())
ppi_ref = fuel["2017-01":"2022-12"][["gas_ratio", "dsl_ratio"]].mean()
fuel_t = []
for n in TERM_NAMES:
    g = fuel[fuel.term == n]
    if g.empty:
        continue
    # pass-through: quarterly (non-overlapping) log change of USD fuel price on log change of Brent
    gq = np.log(g[["gasoline", "diesel", "brent"]].resample("QE").mean()).diff().dropna()
    pt = {k: float(np.polyfit(gq.brent, gq[k], 1)[0]) if len(gq) > 4 else np.nan for k in ["gasoline", "diesel"]}
    fuel_t.append(dict(term=n, months=len(g), brent_avg=g.brent.mean(), gasoline_usd_bbl=g.gasoline.mean(), diesel_usd_bbl=g.diesel.mean(),
                       gas_ratio=g.gas_ratio.mean(), dsl_ratio=g.dsl_ratio.mean(),
                       gas_ratio_vs_ppi_era_pct=100 * (g.gas_ratio.mean() / ppi_ref.gas_ratio - 1),
                       dsl_ratio_vs_ppi_era_pct=100 * (g.dsl_ratio.mean() / ppi_ref.dsl_ratio - 1),
                       gas_spread_usd_bbl=g.gas_spread.mean(), dsl_spread_usd_bbl=g.dsl_spread.mean(),
                       passthrough_gas_q=pt["gasoline"], passthrough_dsl_q=pt["diesel"],
                       sd_monthly_change_gas_pct=100 * np.log(g.gasoline).diff().std()))
fuel_t = pd.DataFrame(fuel_t)
fuel_t.round(3).to_csv(HERE / "fuel_prices_by_term.csv", index=False)
fuel.round(3).to_csv(HERE / "fuel_prices_monthly.csv")
R["q3_fuel_by_term"] = fuel_t.round(3).to_dict("records")
R["q3_fuel_latest"] = fuel.iloc[-3:][["gasoline", "diesel", "brent", "gas_ratio", "dsl_ratio"]].round(2).reset_index().astype(str).to_dict("records")
# monthly regression: fuel spread on left dummy controlling for Brent level (descriptive)
fuel["left"] = fuel.term.map(lambda t: LEAN[t] == "left").astype(float)
for k in ["gas_spread", "dsl_spread"]:
    Xf = np.column_stack([np.ones(len(fuel)), fuel.brent, fuel.left])
    bf = np.linalg.lstsq(Xf, fuel[k], rcond=None)[0]
    perms = []
    for c in itertools.combinations(TERM_NAMES, 3):
        lf = fuel.term.isin(c).astype(float)
        perms.append(np.linalg.lstsq(np.column_stack([np.ones(len(fuel)), fuel.brent, lf]), fuel[k], rcond=None)[0][2])
    R.setdefault("q3_fuel_left_dummy", {})[k] = dict(left_coef_usd_bbl=float(bf[2]), brent_coef=float(bf[1]),
                                                     perm_p_one_sided_lt=float(np.mean(np.array(perms) <= bf[2] + 1e-9)))

# ============================================================ Q4 FISCAL CHANNEL
rtn = xlsx_lite.read_sheet(CACHE / "rtn.xlsx", "1.1")
hdr = rtn[3]
dates = pd.to_datetime([pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(v)) for v in hdr[1:] if isinstance(v, float)])
lines = {"total_revenue": "1. RECEITA TOTAL", "dividends": "1.4.2", "natural_resources": "1.4.4", "nr_transfers": "2.4 ",
         "net_revenue": "3. RECEITA LÍQUIDA", "primary": "5. RESULTADO PRIMÁRIO", "cide": "1.1.09"}
rt = {}
for k, pat in lines.items():
    row = [r for r in rtn if isinstance(r[0], str) and r[0].strip().startswith(pat.strip()) and (pat != "2.4 " or "Recursos Naturais" in r[0])][0]
    rt[k] = pd.Series([float(v) if isinstance(v, (int, float)) else np.nan for v in row[1:1 + len(dates)]], index=dates)
rt = pd.DataFrame(rt) / 1000  # R$ bn
LAST["Tesouro RTN (table 1.1)"] = str(rt.index.max().date())
rty = rt.groupby(rt.index.year).sum()
rty["months"] = rt.groupby(rt.index.year).size()
UNION_STAKE = 0.2902  # Union direct share of total capital, Petrobras IR, Sep 2026
CONTROL_STAKE = 0.3545
qd = q.assign(year=q.quarter_end.dt.year).groupby("year").dividends_paid_brl.sum()
gdp = ser("gdp_nominal_12m_brl")
gdp_d = gdp[gdp.index.month == 12]; gdp_y = pd.Series(gdp_d.values / 1000, index=gdp_d.index.year)
fis = pd.DataFrame({"rtn_dividends_bn": rty.dividends, "rtn_natres_gross_bn": rty.natural_resources,
                    "rtn_natres_net_bn": rty.natural_resources - rty.nr_transfers, "net_revenue_bn": rty.net_revenue,
                    "primary_bn": rty.primary, "months": rty.months, "petr_div_paid_bn": qd,
                    "gdp_bn": gdp_y}).loc[2012:]
fis["petr_div_to_union_bn"] = fis.petr_div_paid_bn * UNION_STAKE
fis["petr_div_to_control_group_bn"] = fis.petr_div_paid_bn * CONTROL_STAKE
fis["petr_share_of_rtn_dividends_pct"] = 100 * fis.petr_div_to_union_bn / fis.rtn_dividends_bn
fis["union_petr_div_pct_net_rev"] = 100 * fis.petr_div_to_union_bn / fis.net_revenue_bn
fis["natres_net_pct_net_rev"] = 100 * fis.rtn_natres_net_bn / fis.net_revenue_bn
fis["oil_channel_pct_net_rev"] = fis.union_petr_div_pct_net_rev + fis.natres_net_pct_net_rev
fis["oil_channel_pct_gdp"] = 100 * (fis.petr_div_to_union_bn + fis.rtn_natres_net_bn) / fis.gdp_bn
fis["primary_pct_gdp"] = 100 * fis.primary_bn / fis.gdp_bn
fis["primary_ex_oil_channel_pct_gdp"] = fis.primary_pct_gdp - fis.oil_channel_pct_gdp
fis.round(3).to_csv(HERE / "fiscal_channel_annual.csv")
fis["term"] = [term_of(pd.Timestamp(f"{y}-06-30")) for y in fis.index]
R["q4_fiscal_annual"] = fis.round(3).reset_index().rename(columns={"index": "year"}).replace({np.nan: None}).to_dict("records")
full = fis[fis.months == 12]
R["q4_fiscal_by_term"] = full.groupby("term")[["union_petr_div_pct_net_rev", "natres_net_pct_net_rev", "oil_channel_pct_net_rev",
                                                "oil_channel_pct_gdp", "primary_pct_gdp"]].mean().round(3).reset_index().to_dict("records")
# scenario arithmetic (latest 4 quarters)
ttm = q.iloc[-4:]
ni_ttm, div_ttm = ttm.net_income_brl.sum(), ttm.dividends_paid_brl.sum()
gdp_last = gdp.iloc[-1] / 1000
LAST["gdp_nominal_12m_brl"] = str(gdp.index.max().date())
nr_12m = (rt.natural_resources - rt.nr_transfers).iloc[-12:].sum()
brent_12m = brent[rt.index[-12]: rt.index[-1] + pd.offsets.MonthEnd(0)].mean()
R["q4_scenarios"] = {
    "ttm_net_income_brl_bn": float(ni_ttm), "ttm_dividends_paid_brl_bn": float(div_ttm), "ttm_quarters": [str(d.date()) for d in ttm.quarter_end],
    "union_receipts_per_10pp_payout_brl_bn": float(0.10 * ni_ttm * UNION_STAKE),
    "union_receipts_per_10pp_payout_pct_gdp": float(100 * 0.10 * ni_ttm * UNION_STAKE / gdp_last),
    "natres_net_12m_brl_bn": float(nr_12m), "brent_avg_same_12m": float(brent_12m),
    "natres_per_10usd_brent_brl_bn_proportional": float(nr_12m * 10 / brent_12m),
    "natres_per_10usd_brent_pct_gdp": float(100 * nr_12m * 10 / brent_12m / gdp_last),
    "gdp_12m_brl_bn": float(gdp_last),
    "payout_ttm_pct": float(100 * div_ttm / ni_ttm)}

# ============================================================ Q5b WEIGHT IN THE ECONOMY
iw = pd.read_csv(ROOT / "warehouse/bronze/companies/ibov_weight.csv")
iw = iw[iw.date == iw.date.max()]
grp_w = lambda tks: float(iw[iw.entity_id.isin(tks)].value.sum())
banks = [t for t in ["ITUB4", "BBDC3", "BBDC4", "BBAS3", "BPAC11", "SANB11", "ITSA4"] if t in set(iw.entity_id)]
R["q5_ibov_weight_pct"] = {"date": str(iw.date.max()), "Petrobras (PETR3+PETR4)": grp_w(["PETR3", "PETR4"]), "Vale": grp_w(["VALE3"]),
                           "Itaú": grp_w(["ITUB4"]), "Axia": grp_w(["AXIA3"]), "listed big banks": grp_w(banks), "banks_tickers": banks,
                           "largest_single_names": iw.groupby("metric_name").value.sum().sort_values(ascending=False).head(6).round(2).to_dict()}
ex = {k: ser(k) for k in ["oil_exports", "iron_ore_exports", "soy_exports", "exports_total"]}
exy = pd.DataFrame(ex).groupby(lambda d: d.year).sum()
exy["n"] = pd.DataFrame(ex).groupby(lambda d: d.year).size()
for k in ["oil_exports", "iron_ore_exports", "soy_exports"]:
    exy[k + "_share_pct"] = 100 * exy[k] / exy.exports_total
R["q5_export_shares_pct"] = exy[[c for c in exy.columns if c.endswith("share_pct")] + ["n"]].round(2).loc[[2014, 2018, 2022, 2024, 2025, 2026]].reset_index().rename(columns={"index": "year"}).to_dict("records")

# pre-registered decision rule
pz = zs_runoffs.mean_abs_z01
first_z = pz.idxmax() == "Petrobras PN"
w_ranks = {"ibov_single_name_first": R["q5_ibov_weight_pct"]["Petrobras (PETR3+PETR4)"] > max(R["q5_ibov_weight_pct"][k] for k in ["Vale", "Itaú", "Axia"]),
           "ibov_vs_banks_block_first": R["q5_ibov_weight_pct"]["Petrobras (PETR3+PETR4)"] > R["q5_ibov_weight_pct"]["listed big banks"],
           "crude_top_export_2025": bool(exy.loc[2025, "oil_exports_share_pct"] > max(exy.loc[2025, "iron_ore_exports_share_pct"], exy.loc[2025, "soy_exports_share_pct"])),
           "crude_top_export_2026ytd": bool(exy.loc[2026, "oil_exports_share_pct"] > max(exy.loc[2026, "iron_ore_exports_share_pct"], exy.loc[2026, "soy_exports_share_pct"]))}
n_w = sum([w_ranks["ibov_single_name_first"], w_ranks["crude_top_export_2025"]])
R["q5_decision"] = {"petr_largest_mean_abs_z_prereg_set": bool(first_z), "margin_vs_second": float(pz.sort_values().iloc[-1] - pz.sort_values().iloc[-2]),
                    "second": pz.sort_values().index[-2], "weight_checks": w_ranks, "n_weight_firsts_counted": int(n_w),
                    "verdict_letter_of_rule": "SUPPORTED" if (first_z and n_w >= 2) else ("PARTLY" if (first_z or n_w >= 2) else "REJECTED"),
                    "petr_first_in_all_common_set_incl_first_rounds": bool(zs.mean_abs_z01.idxmax() == "Petrobras PN"),
                    "petr_rank_2026_first_round_abs_z": int((Z[Z.date == "2026-10-04"].z01.abs().rank(ascending=False)[Z[Z.date == "2026-10-04"].asset == "Petrobras PN"]).iloc[0])}

# ============================================================ Q6 VALUATION (judgement inputs)
SHARES_BN = 13.044496930  # total ON+PN shares (Petrobras IR; external_facts)
pm = petr_px.resample("ME").last()
ni_ttm_q = q.set_index("quarter_end").net_income_brl.rolling(4).sum()
pe = (pm * SHARES_BN / ni_ttm_q.reindex(pm.index, method="ffill")).dropna()
pe = pe[pe.index >= "2013-03-31"]
dyt = ser("dividend_yield_ttm@PETR")
val = []
for n in TERM_NAMES:
    a, b = [(t[1], t[2]) for t in TERMS if t[0] == n][0]
    p_ = pe[a:b]
    p_ = p_[(p_ > 0) & (p_ < 60)]
    d_ = dyt[a:b]
    if len(p_) == 0:
        continue
    val.append(dict(term=n, pe_median=p_.median(), pe_p25=p_.quantile(.25), pe_p75=p_.quantile(.75), dy_median=d_.median(), months=len(p_)))
val = pd.DataFrame(val)
val.round(2).to_csv(HERE / "valuation_by_term.csv", index=False)
mcap_now = petr_px.iloc[-1] * SHARES_BN
R["q6_valuation"] = {"by_term": val.round(2).to_dict("records"), "price_PETR4_last": float(petr_px.iloc[-1]), "price_date": str(petr_px.index[-1].date()),
                     "mcap_brl_bn_approx": float(mcap_now), "ni_ttm_brl_bn": float(ni_ttm), "pe_now": float(mcap_now / ni_ttm),
                     "dy_ttm_pct_last": float(dyt.iloc[-1]), "dy_date": str(dyt.index[-1].date())}

# ============================================================ CHARTS
COL = {"petr": "#2a78d6", "ibov": "#eb6834", "brent": "#1baf7a", "left": "rgba(227,73,72,0.07)", "right": "rgba(42,120,214,0.07)",
       "grid": "#e6e5e0", "ink": "#0b0b0b", "ink2": "#52514e"}
LAYOUT = dict(template="plotly_white", font=dict(family="Inter, system-ui, sans-serif", size=13, color=COL["ink"]),
              margin=dict(l=60, r=30, t=80, b=60), hovermode="x unified",
              legend=dict(orientation="h", y=1.08, x=0))


def shade(fig, start="2000-01-01"):
    for n, a, b, lean in TERMS:
        a = max(pd.Timestamp(a), pd.Timestamp(start))
        fig.add_vrect(x0=a, x1=min(pd.Timestamp(b), TODAY), fillcolor=COL[lean], line_width=0, layer="below",
                      annotation_text=n, annotation_position="top left", annotation_font_size=10, annotation_font_color=COL["ink2"])


def save(fig, name, title, sub):
    fig.update_layout(title=dict(text=f"{title}<br><sup style='color:{COL['ink2']}'>{sub}</sup>"), **LAYOUT)
    fig.write_html(CH / name, include_plotlyjs="cdn")


lv = np.exp(np.log(lvl[lvl.index >= "2000-01-03"]).diff().fillna(0).cumsum()) * 100
lvm = lv.resample("ME").last()
fig = go.Figure()
for k, nm, c in [("petr_usd", "Petrobras PN total return (USD)", COL["petr"]), ("ibov_usd", "Ibovespa (USD)", COL["ibov"]), ("brent", "Brent (USD)", COL["brent"])]:
    fig.add_trace(go.Scatter(x=lvm.index, y=lvm[k], name=nm, line=dict(color=c, width=2)))
shade(fig)
fig.update_yaxes(type="log", title="Index, Jan 2000 = 100 (log scale)")
save(fig, "petr_vs_ibov_brent.html", "Petrobras vs Ibovespa vs Brent, 2000–Oct 2026",
     "Red shading = left (PT) terms, blue = right/centre-right. Sources: B3 COTAHIST/warehouse share_close_brl@PETR + dividends, ibovespa_level, brent_usd, brl_usd")

tt = term_tab
fig = go.Figure()
for k, nm, c in [("excess_vs_ibov_pp", "vs Ibovespa (pp/yr)", COL["ibov"]), ("brent_adj_abnormal_pp", "Brent-adjusted abnormal (pp/yr)", COL["brent"]),
                 ("two_factor_abnormal_pp", "Brent+Ibovespa model (pp/yr)", "#4a3aa7")]:
    fig.add_trace(go.Bar(x=tt.term, y=tt[k], name=nm, marker_color=c, hovertemplate="%{x}: %{y:.1f} pp/yr"))
fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
fig.update_yaxes(title="Percentage points per year", zeroline=True, zerolinecolor=COL["ink2"])
save(fig, "term_abnormal_returns.html", "Petrobras abnormal return by presidential term (USD, monthly)",
     "Left terms: Lula I–II, Dilma, Lula III. FHC covers 2000–02 only. Model betas estimated on 2000–2026")

e2 = ev[ev.preregistered | (ev.kind == "election_r1")].copy()
e2["lab"] = e2.day0 + " · " + e2.event
fig = go.Figure()
fig.add_trace(go.Bar(y=e2.lab, x=e2["ibov_car0,1"], orientation="h", name="vs Ibovespa model", marker_color=COL["ibov"],
                     hovertemplate="%{y}<br>CAR[0,+1] %{x:.1f}%"))
fig.add_trace(go.Bar(y=e2.lab, x=e2["brent_car0,1"], orientation="h", name="vs Brent model (USD)", marker_color=COL["brent"],
                     hovertemplate="%{y}<br>CAR[0,+1] %{x:.1f}%"))
p5, p95 = R["q2_placebo"]["ibov"]["car0,1"]["p5"], R["q2_placebo"]["ibov"]["car0,1"]["p95"]
fig.add_vrect(x0=p5, x1=p95, fillcolor="rgba(82,81,78,0.08)", line_width=0, annotation_text="90% of placebo days", annotation_position="bottom right")
fig.update_layout(barmode="group", height=760, margin=dict(l=420))
fig.update_xaxes(title="Cumulative abnormal return, days 0 to +1 (%)")
fig.update_yaxes(autorange="reversed")
save(fig, "event_study.html", "Petrobras abnormal return around political events", "Grey band: 5th–95th percentile of 2,000 random placebo days (Ibovespa model)")

zz = Z[Z.date.isin(common_dates)].copy()
fig = go.Figure()
palette = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]
for (a, nm), c in zip(ASSETS.items(), palette):
    g = zz[zz.asset == nm]
    fig.add_trace(go.Bar(x=g.date, y=g.z01, name=nm, marker_color=c, hovertemplate=nm + " %{x}: z=%{y:.1f}<extra></extra>"))
fig.update_layout(barmode="group", hovermode="closest")
fig.update_yaxes(title="Two-day move / normal two-day volatility (z)")
save(fig, "election_sensitivity.html", "Who moves most on election results? Standardised 2-day moves",
     "z = return over days 0..+1 divided by the asset's own pre-event daily volatility × √2. BRL: + = real appreciates")

fig = go.Figure()
fig.add_trace(go.Scatter(x=fuel.index, y=fuel.gas_ratio, name="Gasoline A producer price ÷ Brent", line=dict(color=COL["petr"], width=2)))
fig.add_trace(go.Scatter(x=fuel.index, y=fuel.dsl_ratio, name="Diesel producer price ÷ Brent", line=dict(color=COL["ibov"], width=2)))
shade(fig, "2002-01-01")
fig.update_yaxes(title="Ratio (USD/bbl ÷ USD/bbl)")
save(fig, "fuel_price_vs_brent.html", "Brazilian refinery-gate fuel prices relative to Brent",
     "ANP weighted producer/importer prices (incl. PIS/Cofins/CIDE, excl. ICMS) converted at brl_usd; brent_usd. Taxes changed in 2015, 2017, 2021–23")

fy = qa.loc[:2026]
fig = go.Figure()
fig.add_trace(go.Bar(x=fy.index, y=fy.div_usd_bn, name="Dividends paid (US$ bn)", marker_color=COL["petr"]))
fig.add_trace(go.Bar(x=fy.index, y=fy.capex_usd_bn, name="Capex (US$ bn)", marker_color=COL["ibov"]))
fig.update_layout(barmode="group")
fig.update_yaxes(title="US$ bn per year (2026 = H1)")
save(fig, "dividends_capex.html", "Petrobras cash dividends vs capex by year", "CVM: dividends_paid_brl@PETR, capex_brl@PETR (2012–2026H1) at average brl_usd")

ff = fis[fis.months == 12]
fig = go.Figure()
fig.add_trace(go.Bar(x=ff.index, y=ff.union_petr_div_pct_net_rev, name="Union's share of Petrobras dividends", marker_color=COL["petr"]))
fig.add_trace(go.Bar(x=ff.index, y=ff.natres_net_pct_net_rev, name="Royalties & special participation (net of transfers)", marker_color=COL["brent"]))
fig.update_layout(barmode="stack", bargap=0.3)
fig.update_yaxes(title="% of federal net revenue")
save(fig, "fiscal_channel.html", "Oil money in the federal budget", "Tesouro RTN table 1.1 (net revenue, natural-resource revenue); dividends_paid_brl@PETR × 29.02% Union stake")

# ============================================================ WRITE
R["series_last_dates"] = LAST
json.dump(R, open(HERE / "results.json", "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print(json.dumps({k: R[k] for k in ["meta", "q1_models", "q1_tests", "q2_groups", "q4_scenarios", "q5_ibov_weight_pct", "q6_valuation"]}, indent=1, default=str))
print(term_tab.round(2).to_string())
print(ev[["day0", "event", "ibov_car0,1", "ibov_car0,1_placebo_p", "ibov_car0,5", "brent_car0,1", "brent_car0,1_placebo_p", "ibov_raw0,1"]].round(2).to_string())
print(zs.round(2).to_string()); print(zs_runoffs.round(2).to_string())
print(fund.round(2).to_string()); print(fuel_t.round(2).to_string())
print(fis.round(2).to_string())
print(val.round(2).to_string())
print(R["q5_export_shares_pct"])
print(R["q3_fuel_left_dummy"]); print(R["q5_decision"]); print(R["q5_ibov_weight_pct"])
