"""Brazil exports under Lula IV vs Flávio Bolsonaro: exposure map, 2025 tariff natural experiment,
elasticities, analogues, scenario matrix.

Pitfalls (from plan §7):
- ComexStat dates are first-of-month, WB GEM month-end -> join on date_trunc('month').
- v_annual 2026 is incomplete (8 months) -> never use 2026 from v_annual as a year.
- China H2-2024 base effect: exports_to_china collapsed Jul->Dec 2024; use two-year changes.
- Soy seasonality: never compare adjacent months; same-month-prior-year or seasonal factors.
- 2026 Brent shock and BRL appreciation confound 2026 YTD.
- wb/TOT.BRA ends 2025-12 (proxy 2026 with unit values, labelled); wb/REER_M.BRA ends 2024-10.
- beef_exports_to_china gaps 2014-15 (pre-access) -> treated as 0.
- WB regional shares end 2023; LatAm LMIC != Mercosur (upper-bound proxy).
- hypothesis_tests L4 is a 12m/12m comparison with no base adjustment.
- beta is reduced-form (co-moves with the global cycle) -> upper bound for a pure price shock.
- No scipy: OLS by np.linalg.lstsq, CIs by moving-block bootstrap, p-values by permutation/placebo rank.
- plotly HTML only. Politics study owns lean statistics: cite, do not recompute.
"""
import json, os, sys
import duckdb, numpy as np, pandas as pd

DB = "/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb"
OUT = os.path.dirname(os.path.abspath(__file__))
CH = os.path.join(OUT, "charts")
os.makedirs(CH, exist_ok=True)
con = duckdb.connect(DB, read_only=True)
RNG = np.random.default_rng(0)
R = {}          # results: key -> {value, series_id, source, last_date, sql}
SQLLOG = {}
GDP_KEY = "wb/NY.GDP.MKTP.CD.BR"

CAT = con.sql("""SELECT c.series_id, c.source, c.agg, max(o.date) last_date
                 FROM catalog c LEFT JOIN observations o USING(series_id) GROUP BY ALL""").df().set_index("series_id")


def rec(key, value, series_id, sql=None, note=None):
    sids = series_id if isinstance(series_id, (list, tuple)) else [series_id]
    src = sorted({str(CAT.loc[s, "source"]) for s in sids if s in CAT.index})
    last = max([str(CAT.loc[s, "last_date"])[:10] for s in sids if s in CAT.index] or [""])
    v = None if value is None else (float(value) if np.isscalar(value) else value)
    R[key] = {"value": v, "series_id": series_id, "source": "; ".join(src), "last_date": last,
              "sql": sql}
    if note:
        R[key]["note"] = note
    return value


def q(sql, name=None):
    if name:
        SQLLOG[name] = sql
    return con.sql(sql).df()


# ---------------------------------------------------------------- panels
MONTHLY = ['exports_total', 'imports_total', 'exports_to_us', 'exports_to_china', 'exports_to_eu', 'china_export_share',
           'soy_exports', 'oil_exports', 'oil_exports_kg', 'iron_ore_exports', 'iron_ore_exports_kg', 'beef_exports',
           'beef_exports_to_china', 'coffee_exports', 'sugar_exports', 'pulp_exports', 'pulp_exports_kg', 'niobium_exports',
           'fertilizer_imports', 'potash_imports', 'iron_ore_unit_value', 'oil_export_unit_value', 'pulp_unit_value',
           'bop_goods_exports', 'brl_usd', 'brent_usd', 'focus_fx', 'wb/TOT.BRA', 'wb/DXGSRMRCHNSXD_M.BRA',
           'wb/DXGSRMRCHNSCD_M.BRA', 'wb/REER_M.BRA', 'trade_balance']
PANEL_SQL = f"""SELECT series_id, date_trunc('month', date) AS ym,
       CASE WHEN series_id IN ('brl_usd','brent_usd','focus_fx') THEN avg(value) ELSE max(value) END AS v
FROM v_observations WHERE date <= current_date AND series_id IN ({','.join("'" + s + "'" for s in MONTHLY)})
GROUP BY 1,2 ORDER BY 2,1"""


def monthly_panel():
    df = q(PANEL_SQL, "monthly_panel")
    p = df.pivot(index="ym", columns="series_id", values="v").sort_index()
    p.index = pd.to_datetime(p.index)
    # beef->China pre-access months = 0 within ComexStat coverage
    m = (p.index >= "2014-01-01") & (p.index <= "2026-08-01")
    p.loc[m, "beef_exports_to_china"] = p.loc[m, "beef_exports_to_china"].fillna(0)
    p["exports_rest"] = p["exports_total"] - p["exports_to_us"] - p["exports_to_china"] - p["exports_to_eu"]
    return p


P = monthly_panel()
LAST = pd.Timestamp("2026-08-01")
BN = 1e9


def ssum(s, a, b):
    return P.loc[a:b, s].sum() / BN


def smean(s, a, b):
    return P.loc[a:b, s].mean()


def yoy(s, a, b):
    a0, b0 = pd.Timestamp(a) - pd.DateOffset(years=1), pd.Timestamp(b) - pd.DateOffset(years=1)
    return 100 * (P.loc[a:b, s].sum() / P.loc[a0:b0, s].sum() - 1)


def annual():
    sql = """WITH a AS (SELECT year, series_id, value FROM v_annual WHERE is_complete AND series_id IN
 ('exports_total','exports_to_us','exports_to_china','exports_to_eu','soy_exports','oil_exports','iron_ore_exports',
  'beef_exports','coffee_exports','sugar_exports','pulp_exports','niobium_exports','beef_exports_to_china'))
SELECT * FROM a PIVOT (max(value) FOR series_id IN ('exports_total','exports_to_us','exports_to_china','exports_to_eu',
 'soy_exports','oil_exports','iron_ore_exports','beef_exports','coffee_exports','sugar_exports','pulp_exports',
 'niobium_exports','beef_exports_to_china')) ORDER BY year"""
    return q(sql, "annual").set_index("year")


A = annual()
GDP = q(f"SELECT year, value FROM v_annual WHERE series_id='{GDP_KEY}' AND is_complete ORDER BY year").set_index("year")["value"]
GDP25 = GDP.loc[2025] / BN


# ---------------------------------------------------------------- anchors (plan §0.3–0.8)
ANCHOR_EXPECT = {
    "us_mayjul25_avg": 3.590, "us_mayjul24_avg": 3.364, "us_augnov25_avg": 2.603, "us_augnov24_avg": 3.474,
    "us_augnov_yoy": -25.1, "tot_augnov25_avg": 29.93, "tot_augnov24_avg": 28.59,
    "us_13m": 37.93, "us_13m_prev": 44.32, "cn_13m": 119.33, "cn_13m_prev": 99.67, "eu_13m": 58.61, "eu_13m_prev": 53.29,
    "rest_13m": 185.4, "rest_13m_prev": 169.4, "tot_13m": 401.3, "tot_13m_prev": 366.7,
    "pre_us": 4.8, "pre_cn": -6.6, "pre_eu": 3.8, "pre_tot": 0.0, "did_us": -19.3, "gap_us_13m": -8.5,
    "ytd_tot": 250.9, "ytd_tot_prev": 227.4, "ytd_us": 24.1, "ytd_us_prev": 26.7, "ytd_cn": 77.1, "ytd_cn_prev": 67.0,
    "ytd_eu": 37.3, "ytd_eu_prev": 32.5, "two_year_cn": 4.1, "two_year_us": -11.4, "two_year_eu": 12.7, "two_year_tot": 7.7,
    "tot2025": 348.3, "cn_sh_2025": 28.7, "eu_sh_2025": 14.3, "us_sh_2025": 10.8,
}


def anchors():
    a = {}
    a["us_mayjul25_avg"] = ssum("exports_to_us", "2025-05", "2025-07") / 3
    a["us_mayjul24_avg"] = ssum("exports_to_us", "2024-05", "2024-07") / 3
    a["us_augnov25_avg"] = ssum("exports_to_us", "2025-08", "2025-11") / 4
    a["us_augnov24_avg"] = ssum("exports_to_us", "2024-08", "2024-11") / 4
    a["us_augnov_yoy"] = yoy("exports_to_us", "2025-08", "2025-11")
    a["tot_augnov25_avg"] = ssum("exports_total", "2025-08", "2025-11") / 4
    a["tot_augnov24_avg"] = ssum("exports_total", "2024-08", "2024-11") / 4
    for k, s in [("us", "exports_to_us"), ("cn", "exports_to_china"), ("eu", "exports_to_eu"),
                 ("rest", "exports_rest"), ("tot", "exports_total")]:
        a[f"{k}_13m"] = ssum(s, "2025-08", "2026-08")
        a[f"{k}_13m_prev"] = ssum(s, "2024-08", "2025-08")
        a[f"{k}_13m_prev2"] = ssum(s, "2023-08", "2024-08")
        a[f"pre_{k}"] = yoy(s, "2025-01", "2025-07")
        a[f"yoy13_{k}"] = 100 * (a[f"{k}_13m"] / a[f"{k}_13m_prev"] - 1)
        a[f"did_{k}"] = a[f"yoy13_{k}"] - a[f"pre_{k}"]
        a[f"two_year_{k}"] = 100 * (a[f"{k}_13m"] / a[f"{k}_13m_prev2"] - 1)
        a[f"ytd_{k}"] = ssum(s, "2026-01", "2026-08")
        a[f"ytd_{k}_prev"] = ssum(s, "2025-01", "2025-08")
    a["gap_us_13m"] = a["us_13m"] - a["us_13m_prev"] * (1 + a["pre_us"] / 100)
    a["gap_us_yr"] = a["gap_us_13m"] * 12 / 13
    a["tot2025"] = A.loc[2025, "exports_total"] / BN
    for k, s in [("cn", "exports_to_china"), ("eu", "exports_to_eu"), ("us", "exports_to_us")]:
        a[f"{k}_sh_2025"] = 100 * A.loc[2025, s] / A.loc[2025, "exports_total"]
    a["gap_us_pct_exports"] = 100 * a["gap_us_yr"] / a["tot2025"]
    a["gap_us_pct_gdp"] = 100 * a["gap_us_yr"] / GDP25
    # China base effect
    a["cn_jul24"] = P.loc["2024-07-01", "exports_to_china"] / BN
    a["cn_dec24"] = P.loc["2024-12-01", "exports_to_china"] / BN
    # bop cross-check
    a["bop_2025"] = P.loc["2025-01":"2025-12", "bop_goods_exports"].sum() / 1e3
    a["bop_ytd26"] = P.loc["2026-01":"2026-08", "bop_goods_exports"].sum() / 1e3
    diffs = []
    for k, v in ANCHOR_EXPECT.items():
        if k in a:
            d = a[k] - v
            tol = 0.15 if abs(v) < 20 else max(0.6, 0.005 * abs(v))
            if abs(d) > tol:
                diffs.append((k, v, round(a[k], 3)))
    for k, v in a.items():
        rec(f"anchor.{k}", v, ["exports_to_us", "exports_to_china", "exports_to_eu", "exports_total"], PANEL_SQL[:60] + "…")
    R["anchor_mismatches"] = {"value": diffs}
    return a, diffs


def seasonality():
    s = {}
    for col in ["exports_to_china", "exports_to_us", "soy_exports"]:
        x = P.loc["2015-01":"2024-12", col]
        sh = x / x.groupby(x.index.year).transform("sum")
        s[col] = sh.groupby(sh.index.month).mean()
    return pd.DataFrame(s)


def products_0_4():
    out = {}
    prods = ["beef_exports", "beef_exports_to_china", "soy_exports", "oil_exports", "oil_exports_kg", "iron_ore_exports",
             "coffee_exports", "pulp_exports", "pulp_exports_kg", "sugar_exports", "niobium_exports"]
    for p_ in prods:
        out[p_] = {"post_augdec25": yoy(p_, "2025-08", "2025-12"), "pre_janjul25": yoy(p_, "2025-01", "2025-07"),
                   "ytd26": yoy(p_, "2026-01", "2026-08")}
        rec(f"product_response.{p_}", out[p_], p_)
    return pd.DataFrame(out).T


def confounders_0_5():
    c = {"brent_dec25": smean("brent_usd", "2025-12", "2025-12"), "brent_apr26": smean("brent_usd", "2026-04", "2026-04"),
         "brent_sep26": smean("brent_usd", "2026-09", "2026-09"),
         "oil_uv_2025": P.loc["2025", "oil_exports"].sum() / P.loc["2025", "oil_exports_kg"].sum() * 1 / 1e3 * 1e3,
         "brl_dec24": smean("brl_usd", "2024-12", "2024-12"), "brl_may26": smean("brl_usd", "2026-05", "2026-05"),
         "brl_oct26": smean("brl_usd", "2026-10", "2026-10")}
    # oil unit value: usd / thousand tonnes -> usd/t = usd/(kt*1000)
    c["oil_uv_2025"] = P.loc["2025", "oil_exports"].sum() / (P.loc["2025", "oil_exports_kg"].sum() * 1000)
    c["oil_uv_ytd26"] = P.loc["2026-01":"2026-08", "oil_exports"].sum() / (P.loc["2026-01":"2026-08", "oil_exports_kg"].sum() * 1000)
    c["oil_uv_series_2025"] = P.loc["2025", "oil_export_unit_value"].mean()
    c["oil_uv_series_ytd26"] = P.loc["2026-01":"2026-08", "oil_export_unit_value"].mean()
    # contribution of oil to 2026 YTD growth
    d_tot = ssum("exports_total", "2026-01", "2026-08") - ssum("exports_total", "2025-01", "2025-08")
    d_oil = ssum("oil_exports", "2026-01", "2026-08") - ssum("oil_exports", "2025-01", "2025-08")
    c["ytd_total_delta_bn"], c["ytd_oil_delta_bn"] = d_tot, d_oil
    c["oil_share_of_ytd_growth"] = 100 * d_oil / d_tot
    # oil price vs volume within 2026 YTD
    t26 = P.loc["2026-01":"2026-08", "oil_exports_kg"].sum(); t25 = P.loc["2025-01":"2025-08", "oil_exports_kg"].sum()
    c["oil_tonnes_ytd_yoy"] = 100 * (t26 / t25 - 1)
    for k, v in c.items():
        rec(f"confound.{k}", v, ["brent_usd", "brl_usd", "oil_exports", "oil_exports_kg"])
    return c


# ---------------------------------------------------------------- exposure (plan §2)
def exposure_map(a):
    tot = A["exports_total"]
    sh = pd.DataFrame({"cn_sh": 100 * A["exports_to_china"] / tot, "us_sh": 100 * A["exports_to_us"] / tot,
                       "eu_sh": 100 * A["exports_to_eu"] / tot})
    sh["rest_sh"] = 100 - sh.sum(axis=1)
    sh["hhi4"] = (sh[["cn_sh", "us_sh", "eu_sh", "rest_sh"]] ** 2).sum(axis=1)
    wb = q("""SELECT series_id, year, value FROM v_annual WHERE series_id LIKE 'wb/TX.VAL.MRCH.%' AND year BETWEEN 2014 AND 2023""",
           "wb_regional").pivot(index="year", columns="series_id", values="value")
    pc = q("""SELECT series_id, year, value FROM v_annual WHERE series_id IN ('wb/TX.VAL.FOOD.ZS.UN.BR','wb/TX.VAL.FUEL.ZS.UN.BR',
             'wb/TX.VAL.MMTL.ZS.UN.BR','wb/TX.VAL.MANF.ZS.UN.BR','wb/TX.VAL.AGRI.ZS.UN.BR') AND year>=2019""", "wb_product_class")\
        .pivot(index="year", columns="series_id", values="value")
    t25 = tot.loc[2025] / BN
    r3 = wb.loc[2023, "wb/TX.VAL.MRCH.R3.ZS.BR"]
    rows = []

    def row(kind, name, v25, v19, ytd26, ytd25, sid, note=""):
        rows.append({"kind": kind, "bucket": name, "usd_bn_2025": v25, "pct_exports_2025": 100 * v25 / t25,
                     "pct_gdp_2025": 100 * v25 / GDP25,
                     "cagr_2019_2025": (100 * ((v25 / v19) ** (1 / 6) - 1)) if v19 else None,
                     "ytd2026_yoy": (100 * (ytd26 / ytd25 - 1)) if ytd25 else None,
                     "series_id": sid, "source": CAT.loc[sid.split(" ")[0], "source"] if sid.split(" ")[0] in CAT.index else "",
                     "last_date": str(CAT.loc[sid.split(" ")[0], "last_date"])[:10] if sid.split(" ")[0] in CAT.index else "", "note": note})
    for name, s in [("US", "exports_to_us"), ("China", "exports_to_china"), ("EU", "exports_to_eu")]:
        row("partner", name, A.loc[2025, s] / BN, A.loc[2019, s] / BN, ssum(s, "2026-01", "2026-08"), ssum(s, "2025-01", "2025-08"), s)
    latam = r3 / 100 * t25
    rest_resid = (A.loc[2025, "exports_total"] - A.loc[2025, "exports_to_us"] - A.loc[2025, "exports_to_china"] - A.loc[2025, "exports_to_eu"]) / BN
    row("partner", "Mercosur/LatAm (proxy)", latam, None, None, None, "wb/TX.VAL.MRCH.R3.ZS.BR",
        f"WB LatAm LMIC share 2023 = {r3:.1f}% x 2025 total; upper bound for Mercosur (includes Mexico, Colombia, Peru)")
    row("partner", "Rest (India/MENA/ASEAN/Africa/Japan/other)", rest_resid - latam, None,
        ssum("exports_rest", "2026-01", "2026-08"), ssum("exports_rest", "2025-01", "2025-08"), "exports_total",
        "total - US - China - EU - LatAm proxy; YTD YoY refers to total-US-China-EU incl. LatAm")
    prods = [("oil", "oil_exports"), ("soy", "soy_exports"), ("iron ore", "iron_ore_exports"), ("beef", "beef_exports"),
             ("coffee", "coffee_exports"), ("sugar", "sugar_exports"), ("pulp", "pulp_exports"), ("niobium", "niobium_exports"),
             ("beef->China", "beef_exports_to_china")]
    tracked = 0
    for name, s in prods:
        v = A.loc[2025, s] / BN
        if s != "beef_exports_to_china":
            tracked += v
        row("product", name, v, A.loc[2019, s] / BN, ssum(s, "2026-01", "2026-08"), ssum(s, "2025-01", "2025-08"), s)
    row("product", "other (incl. manufactures)", t25 - tracked, None, None, None, "exports_total", "residual")
    ex = pd.DataFrame(rows)
    ex.to_csv(os.path.join(OUT, "exposure_map.csv"), index=False)
    # product HHI (8 groups + residual), labelled
    ps = ex[(ex.kind == "product") & (ex.bucket != "beef->China")]["pct_exports_2025"]
    rec("exposure.product_hhi_9", float((ps ** 2).sum()), "exports_total", note="8 groups + residual; residual treated as one bucket -> overstated")
    rec("exposure.hhi4_2025", sh.loc[2025, "hhi4"], ["exports_to_china", "exports_to_us", "exports_to_eu"], note="lower bound on concentration")
    rec("exposure.tracked8_share", 100 * tracked / t25, "exports_total")
    for c_ in pc.columns:
        rec(f"exposure.{c_}.2025", pc.loc[2025, c_] if 2025 in pc.index else None, c_)
    rec("exposure.wb_regional_2023", wb.loc[2023].to_dict(), list(wb.columns))
    return ex, sh, wb, pc


def price_vs_volume():
    out = []
    for name, v, kg in [("oil", "oil_exports", "oil_exports_kg"), ("iron ore", "iron_ore_exports", "iron_ore_exports_kg"),
                        ("pulp", "pulp_exports", "pulp_exports_kg")]:
        for lab, (a0, a1, b0, b1) in {"2019->2025": ("2019-01", "2019-12", "2025-01", "2025-12"),
                                      "2026YTD vs 2025YTD": ("2025-01", "2025-08", "2026-01", "2026-08"),
                                      "post-tariff Aug25-Aug26 vs Aug24-Aug25": ("2024-08", "2025-08", "2025-08", "2026-08")}.items():
            dv = np.log(P.loc[b0:b1, v].sum() / P.loc[a0:a1, v].sum())
            dq = np.log(P.loc[b0:b1, kg].sum() / P.loc[a0:a1, kg].sum())
            out.append({"product": name, "window": lab, "dlog_value": 100 * dv, "dlog_tonnes": 100 * dq, "dlog_unit_value": 100 * (dv - dq)})
    wbq = q("""SELECT series_id, year, value FROM v_annual WHERE series_id IN ('wb/TX.QTY.MRCH.XD.WD.BR','wb/TX.UVI.MRCH.XD.WD.BR')
               AND year IN (2015, 2024)""", "wb_qty_uvi").pivot(index="year", columns="series_id", values="value")
    df = pd.DataFrame(out)
    rec("pvv.table", df.to_dict("records"), ["oil_exports_kg", "iron_ore_exports_kg", "pulp_exports_kg"])
    rec("pvv.wb_2015_2024", wbq.to_dict(), ["wb/TX.QTY.MRCH.XD.WD.BR", "wb/TX.UVI.MRCH.XD.WD.BR"])
    return df, wbq


# ---------------------------------------------------------------- tariff natural experiment (plan §3)
def did_at(series, brk, post_n=13, pre_n=7):
    brk = pd.Timestamp(brk)
    post = pd.date_range(brk, periods=post_n, freq="MS")
    pre = pd.date_range(brk - pd.DateOffset(months=pre_n), periods=pre_n, freq="MS")
    s = P[series]
    def yy(idx):
        prev = idx - pd.DateOffset(years=1)
        a_, b_ = s.reindex(idx), s.reindex(prev)
        if a_.isna().any() or b_.isna().any():
            return np.nan
        return 100 * (a_.sum() / b_.sum() - 1)
    return yy(post) - yy(pre), yy(post), yy(pre)


def seasonal_cf(series, brk, post_n=13, pre_n=7, seas_years=(2015, 2024)):
    """Counterfactual = s_m x trailing-12m level before break x (1 + pre-trend)."""
    brk = pd.Timestamp(brk)
    s = P[series]
    x = s.loc[f"{seas_years[0]}-01":f"{seas_years[1]}-12"]
    shr = x / x.groupby(x.index.year).transform("sum")
    sf = shr.groupby(shr.index.month).mean()
    trail = s.loc[brk - pd.DateOffset(months=12): brk - pd.DateOffset(months=1)].sum()
    _, _, pre = did_at(series, brk, post_n, pre_n)
    post = pd.date_range(brk, periods=post_n, freq="MS")
    cf = pd.Series([sf[m.month] * trail * (1 + pre / 100) for m in post], index=post)
    act = s.reindex(post)
    return act, cf


def tariff_episode(a):
    rows = []
    out = {}
    for ser in ["exports_to_us", "exports_to_china", "exports_to_eu", "exports_rest", "exports_total"]:
        for n in [4, 5, 13]:
            d, post, pre = did_at(ser, "2025-08-01", n)
            rows.append({"estimator": "same-month YoY DiD", "series": ser, "window_months": n, "post_yoy": post,
                         "pre_yoy_janjul25": pre, "did_pts": d})
        act, cf = seasonal_cf(ser, "2025-08-01")
        gap = (act - cf).sum() / BN
        rows.append({"estimator": "seasonal-factor counterfactual", "series": ser, "window_months": 13,
                     "actual_bn": act.sum() / BN, "cf_bn": cf.sum() / BN, "gap_bn": gap, "gap_bn_yr": gap * 12 / 13,
                     "gap_pct": 100 * (act.sum() / cf.sum() - 1)})
        rows.append({"estimator": "two-year change", "series": ser, "window_months": 13,
                     "post_yoy": a[f"two_year_{ {'exports_to_us':'us','exports_to_china':'cn','exports_to_eu':'eu','exports_rest':'rest','exports_total':'tot'}[ser]}"]})
    # placebo: breaks 2016-01..2024-06 (post window must end <= 2025-07 to avoid contamination)
    breaks = pd.date_range("2016-01-01", "2024-06-01", freq="MS")
    plac = {}
    for ser in ["exports_to_us", "exports_to_china", "exports_total"]:
        dd, gg = [], []
        for b in breaks:
            d, _, _ = did_at(ser, b)
            act, cf = seasonal_cf(ser, b, seas_years=(2015, 2024))
            dd.append(d); gg.append(100 * (act.sum() / cf.sum() - 1))
        dd, gg = np.array(dd), np.array(gg)
        d0, _, _ = did_at(ser, "2025-08-01")
        act, cf = seasonal_cf(ser, "2025-08-01")
        g0 = 100 * (act.sum() / cf.sum() - 1)
        ok = ~np.isnan(dd)
        plac[ser] = {"did_actual": d0, "did_placebo_p05": np.nanpercentile(dd, 5), "did_placebo_p95": np.nanpercentile(dd, 95),
                     "did_placebo_sd": np.nanstd(dd), "did_p_lower": (np.sum(dd[ok] <= d0) + 1) / (ok.sum() + 1),
                     "did_p_upper": (np.sum(dd[ok] >= d0) + 1) / (ok.sum() + 1),
                     "gap_actual_pct": g0, "gap_placebo_p05": np.nanpercentile(gg, 5), "gap_placebo_p95": np.nanpercentile(gg, 95),
                     "gap_p_lower": (np.sum(gg <= g0) + 1) / (len(gg) + 1), "n_placebo": int(ok.sum()),
                     "did_placebo_series": dd.tolist(), "gap_placebo_series": gg.tolist(),
                     "breaks": [str(b)[:10] for b in breaks]}
        # largest placebo moves (to say where 2018/2020 soy episodes sit)
        top = np.argsort(-np.abs(np.nan_to_num(dd)))[:5]
        plac[ser]["largest_placebo"] = [(str(breaks[i])[:7], float(dd[i])) for i in top]
    # robustness: 4-month window, and excluding placebo windows touching COVID (2020-03..2021-06)
    for ser in ["exports_to_us", "exports_to_china", "exports_total"]:
        d4 = np.array([did_at(ser, b, 4)[0] for b in breaks]); d40 = did_at(ser, "2025-08-01", 4)[0]
        dd = np.array(plac[ser]["did_placebo_series"])
        covid = np.array([(b + pd.DateOffset(months=13) >= pd.Timestamp("2020-03-01")) and (b - pd.DateOffset(months=19) <= pd.Timestamp("2021-06-01"))
                          for b in breaks])
        keep = ~covid & ~np.isnan(dd)
        plac[ser]["did4_actual"] = d40
        plac[ser]["did4_p_lower"] = (np.sum(d4[~np.isnan(d4)] <= d40) + 1) / ((~np.isnan(d4)).sum() + 1)
        plac[ser]["did4_p_upper"] = (np.sum(d4[~np.isnan(d4)] >= d40) + 1) / ((~np.isnan(d4)).sum() + 1)
        plac[ser]["did_excovid_p_lower"] = (np.sum(dd[keep] <= plac[ser]["did_actual"]) + 1) / (keep.sum() + 1)
        plac[ser]["did_excovid_p_upper"] = (np.sum(dd[keep] >= plac[ser]["did_actual"]) + 1) / (keep.sum() + 1)
        plac[ser]["n_excovid"] = int(keep.sum())
        plac[ser]["did_excovid_p05_p95"] = [np.percentile(dd[keep], 5), np.percentile(dd[keep], 95)]
        d4k = d4[keep & ~np.isnan(d4)]
        plac[ser]["did4_excovid_p_lower"] = (np.sum(d4k <= d40) + 1) / (len(d4k) + 1)
        plac[ser]["did4_placebo_series"] = d4.tolist()
    # bootstrap CI for the US 13m DiD using residual months (block 12) – resample monthly YoY ratios pre-period
    # Simple, transparent: CI from placebo 5/95 percentiles shifted to the estimate
    for ser in plac:
        p_ = plac[ser]
        p_["did_ci90"] = [p_["did_actual"] - (np.nanpercentile(p_["did_placebo_series"], 95) - np.nanmedian(p_["did_placebo_series"])),
                          p_["did_actual"] - (np.nanpercentile(p_["did_placebo_series"], 5) - np.nanmedian(p_["did_placebo_series"]))]
    # recovery test: Jun-Aug 2026 US YoY vs Aug-Nov 2025 trough
    us_yoy_m = {str(m)[:7]: 100 * (P.loc[m, "exports_to_us"] / P.loc[m - pd.DateOffset(years=1), "exports_to_us"] - 1)
                for m in pd.date_range("2025-01-01", "2026-08-01", freq="MS")}
    rec_ = {"us_yoy_monthly": us_yoy_m,
            "trough_augnov25_mean_yoy": np.mean([us_yoy_m[k] for k in ["2025-08", "2025-09", "2025-10", "2025-11"]]),
            "junaug26_mean_yoy": np.mean([us_yoy_m[k] for k in ["2026-06", "2026-07", "2026-08"]]),
            "dec25_may26_mean_yoy": np.mean([us_yoy_m[k] for k in ["2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]])}
    # 2-year version for the recovery months (strips 2025 base which was pre-tariff for Jun-Jul)
    rec_["junaug26_vs_junaug24"] = 100 * (P.loc["2026-06":"2026-08", "exports_to_us"].sum() / P.loc["2024-06":"2024-08", "exports_to_us"].sum() - 1)
    te = pd.DataFrame(rows)
    out.update({"placebo": plac, "recovery": rec_})
    rec("tariff.placebo", {k: {kk: vv for kk, vv in v.items() if not kk.endswith("series") and kk != "breaks"} for k, v in plac.items()},
        ["exports_to_us", "exports_to_china", "exports_total"])
    rec("tariff.recovery", rec_, "exports_to_us")
    return te, out


def diversion_bounds(a, fungible_share=None):
    g13 = a["gap_us_13m"]
    gains = {}
    for k, s in [("cn", "exports_to_china"), ("eu", "exports_to_eu"), ("rest", "exports_rest")]:
        gains[k] = a[f"{k}_13m"] - a[f"{k}_13m_prev"] * (1 + a[f"pre_{k}"] / 100)
    nonus = sum(gains.values())
    # two-year (base-effect-free) gain for China: 13m vs same months 2y earlier, scaled by nothing
    d = {"G_US_13m": g13, "G_US_yr": g13 * 12 / 13, "gain_above_pretrend_13m": gains, "nonus_gain_13m": nonus,
         "upper_bound_rate": min(1.0, nonus / abs(g13)), "lower_bound_rate": 0.0,
         "net_loss_no_diversion_yr": g13 * 12 / 13}
    if fungible_share is not None:
        d["central_rate"] = fungible_share
        d["net_loss_central_yr"] = g13 * 12 / 13 * (1 - fungible_share)
    # realised oil price vs Brent (US$/t / (US$/bbl * 7.33))
    ratio = P["oil_export_unit_value"] / (P["brent_usd"] * 7.33)
    d["oil_realisation_pre_jan_jul25"] = ratio.loc["2025-01":"2025-07"].mean()
    d["oil_realisation_post_aug25_aug26"] = ratio.loc["2025-08":"2026-08"].mean()
    d["oil_realisation_2024"] = ratio.loc["2024"].mean()
    d["oil_realisation_2023"] = ratio.loc["2023"].mean()
    d["pulp_uv_pre"] = P.loc["2025-01":"2025-07", "pulp_unit_value"].mean()
    d["pulp_uv_post"] = P.loc["2025-08":"2026-08", "pulp_unit_value"].mean()
    d["pulp_uv_2024"] = P.loc["2024", "pulp_unit_value"].mean()
    rec("diversion", d, ["exports_to_us", "exports_to_china", "exports_to_eu", "exports_total", "oil_export_unit_value", "brent_usd", "pulp_unit_value"])
    return d


# ---------------------------------------------------------------- elasticities (plan §4)
def ols(y, X):
    X1 = np.column_stack([np.ones(len(y))] + [np.asarray(x) for x in X])
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    r = y - X1 @ b
    return b, 1 - r.var() / y.var()


def block_boot(y, X, block=3, n=2000):
    y = np.asarray(y); X = [np.asarray(x) for x in X]
    T = len(y); nb = int(np.ceil(T / block))
    bs = []
    for _ in range(n):
        starts = RNG.integers(0, T - block + 1, nb)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:T]
        b, _ = ols(y[idx], [x[idx] for x in X])
        bs.append(b)
    return np.array(bs)


def perm_p(y, X, j=1, n=2000):
    b0, _ = ols(y, X)
    cnt = 0
    for _ in range(n):
        Xp = list(X); Xp[j - 1] = RNG.permutation(np.asarray(X[j - 1]))
        b, _ = ols(y, Xp)
        cnt += abs(b[j]) >= abs(b0[j])
    return (cnt + 1) / (n + 1)


def tot_beta():
    tot = q("SELECT year, value FROM v_annual WHERE series_id='wb/TOT.BRA' AND is_complete ORDER BY year", "tot_annual").set_index("year")["value"]
    g = q("SELECT year, value FROM v_annual WHERE series_id='wb/NY.GDP.PCAP.KD.ZG.BR' AND is_complete ORDER BY year", "gdppc_growth").set_index("year")["value"]
    dlt = 100 * np.log(tot).diff()
    res = {}
    for lab, y0 in [("1992-2025", 1992), ("1997-2025", 1997), ("2003-2025", 2003)]:
        d = pd.concat([g, dlt], axis=1, keys=["g", "dtot"]).dropna().loc[y0:2025]
        b, r2 = ols(d["g"].values, [d["dtot"].values])
        bs = block_boot(d["g"].values, [d["dtot"].values], 3)
        res[lab] = {"beta": b[1], "ci90": [np.percentile(bs[:, 1], 5), np.percentile(bs[:, 1], 95)],
                    "ci95": [np.percentile(bs[:, 1], 2.5), np.percentile(bs[:, 1], 97.5)], "r2": r2, "n": len(d),
                    "p_perm": perm_p(d["g"].values, [d["dtot"].values])}
    tt = q("SELECT year, value FROM v_annual WHERE series_id='wb/TT.PRI.MRCH.XD.WD.BR' ORDER BY year", "ttpri").set_index("year")["value"]
    d = pd.concat([g, 100 * np.log(tt).diff()], axis=1, keys=["g", "dtt"]).dropna()
    b, r2 = ols(d["g"].values, [d["dtt"].values]); bs = block_boot(d["g"].values, [d["dtt"].values], 3)
    res["TT.PRI 2006-2024"] = {"beta": b[1], "ci90": [np.percentile(bs[:, 1], 5), np.percentile(bs[:, 1], 95)], "r2": r2, "n": len(d)}
    dl = np.log(tot).diff().dropna()
    res["tot_stats"] = {"level_2025": tot.loc[2025], "min": tot.min(), "min_year": int(tot.idxmin()), "max": tot.max(),
                        "max_year": int(tot.idxmax()), "dlog_sd": dl.std(), "p10": dl.quantile(.1), "p90": dl.quantile(.9),
                        "min_dlog": dl.min(), "min_dlog_year": int(dl.idxmin()), "max_dlog": dl.max(), "max_dlog_year": int(dl.idxmax())}
    rec("elasticity.tot_beta", res, ["wb/TOT.BRA", "wb/NY.GDP.PCAP.KD.ZG.BR", "wb/TT.PRI.MRCH.XD.WD.BR"])
    return res, pd.concat([g, dlt], axis=1, keys=["g", "dtot"]).dropna().loc[1992:2025]


def fx_elasticity():
    s = q("""SELECT series_id, year, value FROM v_annual WHERE series_id IN ('wb/TX.QTY.MRCH.XD.WD.BR','wb/PX.REX.REER.BR','wb/TOT.BRA')
             AND is_complete ORDER BY year""", "fx_annual").pivot(index="year", columns="series_id", values="value")
    dl = np.log(s).diff()
    out = {}
    d = pd.DataFrame({"q": dl["wb/TX.QTY.MRCH.XD.WD.BR"], "reer": dl["wb/PX.REX.REER.BR"], "reer1": dl["wb/PX.REX.REER.BR"].shift(1),
                      "tot": dl["wb/TOT.BRA"]}).dropna().loc[2006:2024]
    for lab, cols in [("lag0", ["reer", "tot"]), ("lag0+1", ["reer", "reer1", "tot"])]:
        b, r2 = ols(d["q"].values, [d[c].values for c in cols])
        bs = block_boot(d["q"].values, [d[c].values for c in cols], 3)
        out[lab] = {"b_reer": b[1], "ci90": [np.percentile(bs[:, 1], 5), np.percentile(bs[:, 1], 95)], "r2": r2, "n": len(d),
                    "b_reer_sum": b[1] + (b[2] if lab == "lag0+1" else 0)}
        if lab == "lag0+1":
            sm = bs[:, 1] + bs[:, 2]
            out[lab]["sum_ci90"] = [np.percentile(sm, 5), np.percentile(sm, 95)]
    # monthly: yoy log of 12m-sum exports on yoy log of 12m-mean BRL, lags 0..12, control yoy log 12m-mean Brent
    x12 = P["exports_total"].rolling(12).sum(); f12 = P["brl_usd"].rolling(12).mean(); b12 = P["brent_usd"].rolling(12).mean()
    dx, df_, db = np.log(x12).diff(12), np.log(f12).diff(12), np.log(b12).diff(12)
    mon = {}
    for L in [0, 3, 6, 9, 12]:
        dd = pd.DataFrame({"x": dx, "fx": df_.shift(L), "br": db}).dropna().loc["2015-01":"2026-08"]
        b, r2 = ols(dd["x"].values, [dd["fx"].values, dd["br"].values])
        bs = block_boot(dd["x"].values, [dd["fx"].values, dd["br"].values], 12, 1000)
        mon[f"lag{L}"] = {"b_fx": b[1], "ci90": [np.percentile(bs[:, 1], 5), np.percentile(bs[:, 1], 95)], "b_brent": b[2], "r2": r2, "n": len(dd)}
    out["monthly"] = mon
    rec("elasticity.fx", out, ["wb/TX.QTY.MRCH.XD.WD.BR", "wb/PX.REX.REER.BR", "wb/TOT.BRA", "exports_total", "brl_usd", "brent_usd"],
        note="b_fx>0 means BRL depreciation (higher BRL/USD) raises USD exports")
    return out


# ---------------------------------------------------------------- analogues (plan §4.3)
def analogues():
    terms = q("SELECT president, start, \"end\" FROM political_terms WHERE start >= '2016-01-01'", "terms")
    rows = []
    for _, t in terms.iterrows():
        a0 = max(pd.Timestamp(t["start"]), pd.Timestamp("2014-01-01")); a1 = min(pd.Timestamp(t["end"]), LAST + pd.DateOffset(days=1))
        sl = P.loc[a0:a1 - pd.DateOffset(days=1)]
        n = len(sl); tot = sl["exports_total"].sum()
        rows.append({"president": t["president"], "from": str(a0)[:7], "to": str(sl.index[-1])[:7], "months": n,
                     "cn_sh": 100 * sl["exports_to_china"].sum() / tot, "us_sh": 100 * sl["exports_to_us"].sum() / tot,
                     "eu_sh": 100 * sl["exports_to_eu"].sum() / tot, "rest_sh": 100 * sl["exports_rest"].sum() / tot,
                     "eu_bn_yr": sl["exports_to_eu"].sum() / BN * 12 / n, "us_bn_yr": sl["exports_to_us"].sum() / BN * 12 / n,
                     "cn_bn_yr": sl["exports_to_china"].sum() / BN * 12 / n, "beefcn_bn_yr": sl["beef_exports_to_china"].sum() / BN * 12 / n,
                     "total_bn_yr": tot / BN * 12 / n})
    terms_df = pd.DataFrame(rows)
    defo = q("""SELECT series_id, year, value FROM v_annual WHERE series_id IN ('wb/AG.LND.PFLS.HA.BR','wb/AG.LND.FRLS.HA.BR')
               AND year >= 2015 ORDER BY year""", "deforestation").pivot(index="year", columns="series_id", values="value")
    d = {"pfls": defo["wb/AG.LND.PFLS.HA.BR"].to_dict(), "frls": defo["wb/AG.LND.FRLS.HA.BR"].to_dict(),
         "pfls_mean_2019_22": defo.loc[2019:2022, "wb/AG.LND.PFLS.HA.BR"].mean(),
         "pfls_mean_2023_25": defo.loc[2023:2025, "wb/AG.LND.PFLS.HA.BR"].mean(),
         "pfls_mean_2023_25_ex2024": defo.loc[[2023, 2025], "wb/AG.LND.PFLS.HA.BR"].mean(),
         "frls_mean_2019_22": defo.loc[2019:2022, "wb/AG.LND.FRLS.HA.BR"].mean(),
         "frls_mean_2023_25": defo.loc[2023:2025, "wb/AG.LND.FRLS.HA.BR"].mean()}
    # 2018 US-China round 1: quarterly YoY of soy and exports_to_china
    qq = P.loc[:"2026-06", ["soy_exports", "exports_to_china", "exports_to_us"]].resample("QS").sum()  # complete quarters only
    qy = 100 * (qq / qq.shift(4) - 1)
    soy18 = qy.loc["2018-01":"2019-12"].round(1)
    soy18.index = [f"{i.year}Q{i.quarter}" for i in soy18.index]
    # 2025 analogue: soy in the US-China standoff
    soy25 = qy.loc["2025-01":"2026-07"].round(1)
    soy25.index = [f"{i.year}Q{i.quarter}" for i in soy25.index]
    # soy windfall size: 2018 soy above 2017
    w18 = (P.loc["2018", "soy_exports"].sum() - P.loc["2017", "soy_exports"].sum()) / BN
    w19 = (P.loc["2019", "soy_exports"].sum() - P.loc["2018", "soy_exports"].sum()) / BN
    out = {"terms": terms_df.to_dict("records"), "deforestation": d, "soy_2018_quarterly_yoy": soy18.to_dict(),
           "soy_2025_quarterly_yoy": soy25.to_dict(), "soy_windfall_2018_bn": w18, "soy_reversal_2019_bn": w19,
           "soy_2017": P.loc["2017", "soy_exports"].sum() / BN, "soy_2018": P.loc["2018", "soy_exports"].sum() / BN,
           "julaug26_yoy": {c: 100 * (P.loc["2026-07":"2026-08", c].sum() / P.loc["2025-07":"2025-08", c].sum() - 1)
                            for c in ["soy_exports", "exports_to_china", "exports_to_us", "exports_total"]},
           "soy_2025": P.loc["2025", "soy_exports"].sum() / BN, "soy_2024": P.loc["2024", "soy_exports"].sum() / BN}
    rec("analogues", out, ["exports_to_china", "exports_to_us", "exports_to_eu", "beef_exports_to_china", "soy_exports",
                           "wb/AG.LND.PFLS.HA.BR", "wb/AG.LND.FRLS.HA.BR"])
    return out, terms_df, defo


def gold_tables():
    g = {}
    try:
        g["L4"] = q("SELECT hyp_id, title, statistic, verdict, evidence, as_of FROM hypothesis_tests WHERE hyp_id LIKE 'L4%'").to_dict("records")
    except Exception as e:
        g["L4"] = str(e)
    try:
        g["political_events_tariff"] = q("SELECT * FROM political_events WHERE date >= '2025-01-01' ORDER BY date").astype(str).to_dict("records")
    except Exception as e:
        g["political_events_tariff"] = str(e)
    R["gold"] = {"value": g, "series_id": "hypothesis_tests/political_events", "source": "warehouse gold tables"}
    return g


if __name__ == "__main__" and (len(sys.argv) < 2 or sys.argv[1] == "analysis"):
    a, diffs = anchors()
    print("ANCHOR MISMATCHES:", diffs)
    for k in ["gap_us_13m", "gap_us_yr", "gap_us_pct_exports", "gap_us_pct_gdp", "did_us", "did_cn", "did_eu", "did_tot", "did_rest",
              "two_year_us", "two_year_cn", "two_year_eu", "two_year_tot", "cn_jul24", "cn_dec24", "bop_2025", "bop_ytd26"]:
        print(k, round(a[k], 3))
    print(seasonality().round(3))
    print(products_0_4().round(1))
    print({k: round(v, 2) for k, v in confounders_0_5().items()})
    ex, sh, wb, pc = exposure_map(a)
    print(ex.round(2).to_string()); print(sh.round(1).to_string()); print(pc.round(1).to_string())
    print(wb.loc[2023].round(1).to_string())
    pv, wbq = price_vs_volume(); print(pv.round(1).to_string()); print(wbq)
    te, tout = tariff_episode(a); print(te.round(2).to_string())
    for k, v in tout["placebo"].items():
        print(k, {kk: (np.round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if not kk.endswith("series") and kk != "breaks"})
    print({k: v for k, v in tout["recovery"].items() if k != "us_yoy_monthly"})
    print({k: round(v, 1) for k, v in tout["recovery"]["us_yoy_monthly"].items()})
    dv = diversion_bounds(a); print(dv)
    tb, _ = tot_beta(); print(json.dumps(tb, indent=1, default=float))
    fx = fx_elasticity(); print(json.dumps(fx, indent=1, default=float))
    an, tdf, defo = analogues(); print(tdf.round(1).to_string()); print(json.dumps({k: v for k, v in an.items() if k != "terms"}, indent=1, default=str))
    print(gold_tables())


# ================================================================ scenario matrix (plan §6)
# Ranges fixed per plan §6.2 BEFORE web research; any post-research change is listed in SCEN_REVISIONS.
# impact = change in annual exports vs a status-quo baseline (2025 levels under the policies in force on 2026-10-05), US$bn/yr.
# phase27 = share of the annual effect realised in 2027 (first year); 2027-30 cumulative = annual x (phase27 + 3).
SCEN = {
 ("Lula IV", "best", "US"): dict(lo=2, hi=4, phase27=0.5, prob="medium", kind="volume",
     mech="incremental negotiated relief on top of the Nov-2025 food carve-out (Nov-2025 template)", src="tariff_episode G_US; Nov-2025 relief"),
 ("Lula IV", "worst", "US"): dict(lo=-6, hi=-3, phase27=0.75, prob="low", kind="volume",
     mech="tariff persists, exemptions narrowed, Section 301 remedies added", src="tariff_episode E_tariff -14 to -25%"),
 ("Lula IV", "best", "China"): dict(lo=3, hi=8, phase27=0.5, prob="medium", kind="volume",
     mech="continued sanitary/plant listings, favourable beef quota use, soy share held", src="analogue Lula III beef->China"),
 ("Lula IV", "worst", "China"): dict(lo=-13, hi=-6, phase27=1.0, prob="medium", kind="volume",
     mech="US-China truce shifts soy back to the US (-5 to -10) + China beef quota binds (-1 to -3); not Lula's choice", src="2018->2019 soy reversal; truce soy commitments"),
 ("Lula IV", "best", "EU"): dict(lo=1, hi=3, phase27=0.3, prob="medium", kind="volume",
     mech="EU-Mercosur in force (TRQ phase-in) + EUDR standard-risk", src="EU-Mercosur TRQs / impact studies"),
 ("Lula IV", "worst", "EU"): dict(lo=-0.5, hi=0, phase27=1.0, prob="medium", kind="volume",
     mech="EP/CJEU blockage keeps status quo; CBAM small cost", src="CBAM exposure"),
 ("Lula IV", "best", "Mercosur/LatAm"): dict(lo=1, hi=3, phase27=0.5, prob="medium", kind="volume",
     mech="Argentine recovery, bloc discipline held by EU deal", src="Brazil->Argentina exports"),
 ("Lula IV", "worst", "Mercosur/LatAm"): dict(lo=-3, hi=-1, phase27=0.5, prob="low", kind="volume",
     mech="Milei-Lula hostility, Argentine import substitution / CET erosion", src="Brazil->Argentina exports"),
 ("Lula IV", "best", "Rest"): dict(lo=1, hi=3, phase27=0.3, prob="medium", kind="volume",
     mech="India/GCC/ASEAN openings (MAPA market-opening track)", src="C10/C12"),
 ("Lula IV", "worst", "Rest"): dict(lo=-1, hi=0, phase27=1.0, prob="low", kind="volume",
     mech="no new deals; Gaza-stance frictions with no measurable trade cost", src="C10"),
 ("Flávio Bolsonaro", "best", "US"): dict(lo=4, hi=8, phase27=0.5, prob="medium", kind="volume",
     mech="tariff lifted (recovery 50-100% of G_US, lag 6-12 m) + Section 301 risk removed", src="tariff_episode G_US"),
 ("Flávio Bolsonaro", "worst", "US"): dict(lo=2, hi=4, phase27=0.5, prob="medium", kind="volume",
     mech="relief conditional on concessions (ethanol, digital/Pix, China distance) -> partial", src="tariff_episode G_US"),
 ("Flávio Bolsonaro", "best", "China"): dict(lo=0, hi=3, phase27=0.5, prob="high", kind="volume",
     mech="pragmatic continuity, as Bolsonaro 2019-22 (China share 23.6 -> 29.5%)", src="analogue Bolsonaro term mix"),
 ("Flávio Bolsonaro", "worst", "China"): dict(lo=-20, hi=-5, phase27=0.75, prob="low", kind="volume",
     mech="alignment with US on China (Huawei/Taiwan/BRICS) triggers Australia-type coercion: sanitary suspensions to multi-product curbs", src="Australia 2020-23 analogue; 2021 BSE suspension"),
 ("Flávio Bolsonaro", "best", "EU"): dict(lo=0, hi=2, phase27=0.3, prob="low", kind="volume",
     mech="agreement already in train is kept; TRQ phase-in", src="EU-Mercosur"),
 ("Flávio Bolsonaro", "worst", "EU"): dict(lo=-5, hi=-2, phase27=0.25, prob="low", kind="volume",
     mech="deforestation surge -> EUDR high-risk / importer de-risking on ~$12-15bn exposed flows; safeguards triggered; CBAM", src="EUDR exposure; 2019 Amazon-fires episode"),
 ("Flávio Bolsonaro", "best", "Mercosur/LatAm"): dict(lo=2, hi=4, phase27=0.5, prob="medium", kind="volume",
     mech="Milei alignment, Argentine recovery, managed CET flexibilisation", src="Brazil->Argentina exports"),
 ("Flávio Bolsonaro", "worst", "Mercosur/LatAm"): dict(lo=-4, hi=-2, phase27=0.5, prob="low", kind="volume",
     mech="Mercosur loosened to a free-trade area; preference margins for autos/parts eroded", src="Brazil->Argentina exports"),
 ("Flávio Bolsonaro", "best", "Rest"): dict(lo=1, hi=3, phase27=0.3, prob="low", kind="volume",
     mech="Gulf/India deals continue (technocratic MAPA/Itamaraty track)", src="C10"),
 ("Flávio Bolsonaro", "worst", "Rest"): dict(lo=-3, hi=-1, phase27=0.75, prob="low", kind="volume",
     mech="Jerusalem-embassy-type Arab friction on halal protein (2019 analogue)", src="C10 2019 episode"),
}
OVERLAYS = {
 "ToT high (+10%)": dict(kind="price", dlogtot=np.log(1.10)),
 "ToT low (-10%)": dict(kind="price", dlogtot=np.log(0.90)),
 "US-China escalation": dict(kind="volume", lo=5, hi=15, mech="soy/beef windfall to Brazil (2018 and 2025 analogues), transitory 4-6 quarters"),
 "US-China détente": dict(kind="volume", lo=-10, hi=-5, mech="China honours US soy purchase commitments; Brazil loses part of the windfall"),
}
SCEN_REVISIONS = []      # filled after web research: (cell, old, new, reason, fact_ids)
FACT_IDS = {}            # cell -> fact ids
PROB_RATIONALE = {}      # cell -> rationale citing fact ids
IMPORT_CONTENT = (0.10, 0.20); MULT = (1.0, 1.5)
COMMODITY_SHARE = None   # filled from WB product classes 2025
PASS_THROUGH = (0.6, 0.9)


def gdp_direct(x_lo, x_hi):
    """Direct demand channel, % of GDP level: dX/GDP x (1-m) x k. Returns (low, high) by magnitude ordering."""
    vals = [100 * x / GDP25 * (1 - m) * k for x in (x_lo, x_hi) for m in IMPORT_CONTENT for k in MULT]
    return min(vals), max(vals)


def scenario_matrix(beta_band):
    tot25 = A.loc[2025, "exports_total"] / BN
    ex = pd.read_csv(os.path.join(OUT, "exposure_map.csv"))
    base = {"US": ex.loc[ex.bucket == "US", "usd_bn_2025"].item(), "China": ex.loc[ex.bucket == "China", "usd_bn_2025"].item(),
            "EU": ex.loc[ex.bucket == "EU", "usd_bn_2025"].item(),
            "Mercosur/LatAm": ex.loc[ex.bucket.str.startswith("Mercosur"), "usd_bn_2025"].item(),
            "Rest": ex.loc[ex.bucket.str.startswith("Rest"), "usd_bn_2025"].item()}
    sid = {"US": "exports_to_us", "China": "exports_to_china", "EU": "exports_to_eu", "Mercosur/LatAm": "wb/TX.VAL.MRCH.R3.ZS.BR",
           "Rest": "exports_total (residual)"}
    rows = []
    for (cand, case, partner), c in SCEN.items():
        cen = (c["lo"] + c["hi"]) / 2
        g = gdp_direct(c["lo"], c["hi"])
        rows.append({"candidate": cand, "case": case, "partner": partner, "global_state": "", "mechanism": c["mech"],
                     "probability_qual": c["prob"], "probability_rationale": PROB_RATIONALE.get((cand, case, partner), ""),
                     "baseline_usd_bn_2025": round(base[partner], 2), "impact_low_usd_bn_yr": c["lo"], "impact_central": cen,
                     "impact_high": c["hi"], "impact_pct_exports_low": round(100 * c["lo"] / tot25, 2),
                     "impact_pct_exports_high": round(100 * c["hi"] / tot25, 2),
                     "impact_pct_partner_low": round(100 * c["lo"] / base[partner], 1), "impact_pct_partner_high": round(100 * c["hi"] / base[partner], 1),
                     "gdp_direct_pct_low": round(g[0], 3), "gdp_direct_pct_high": round(g[1], 3), "gdp_tot_pts": "",
                     "usd_bn_2027": f"{c['lo']*c['phase27']:.1f} to {c['hi']*c['phase27']:.1f}",
                     "usd_bn_2027_30_cum": f"{c['lo']*(c['phase27']+3):.1f} to {c['hi']*(c['phase27']+3):.1f}",
                     "horizon": "1-yr and 4-yr", "elasticity_source": c["src"], "warehouse_series": sid[partner],
                     "external_fact_ids": ";".join(FACT_IDS.get((cand, case, partner), [])),
                     "uncertainty_note": "volume/market-access shock; direct-demand GDP mapping m in [0.10,0.20], k in [1.0,1.5]"})
    # sums per candidate-case
    for cand in ["Lula IV", "Flávio Bolsonaro"]:
        for case in ["best", "worst"]:
            cells = [c for (cn, cs, _), c in SCEN.items() if cn == cand and cs == case]
            lo, hi = sum(c["lo"] for c in cells), sum(c["hi"] for c in cells)
            g = gdp_direct(lo, hi)
            corr = ("US relief and China friction negatively correlated under Flávio: the best case assumes they do not co-occur; "
                    "the worst case stacks partial US relief with China coercion (joint tail)") if cand.startswith("Fl") else \
                   ("US persistence and China access positively correlated under Lula (both reflect non-alignment); "
                    "the China-worst cell is driven by US-China détente, which also eases US pressure")
            rows.append({"candidate": cand, "case": case, "partner": "SUM (not strictly additive)", "mechanism": corr,
                         "probability_qual": "", "baseline_usd_bn_2025": round(tot25, 1), "impact_low_usd_bn_yr": lo,
                         "impact_central": (lo + hi) / 2, "impact_high": hi, "impact_pct_exports_low": round(100 * lo / tot25, 2),
                         "impact_pct_exports_high": round(100 * hi / tot25, 2), "gdp_direct_pct_low": round(g[0], 3),
                         "gdp_direct_pct_high": round(g[1], 3), "horizon": "1-yr", "warehouse_series": "exports_total"})
    # overlays
    for name, o in OVERLAYS.items():
        if o["kind"] == "price":
            sgn = np.sign(o["dlogtot"])
            lo_ = sgn * COMMODITY_SHARE / 100 * abs(np.exp(o["dlogtot"]) - 1) * PASS_THROUGH[0] * tot25
            hi_ = sgn * COMMODITY_SHARE / 100 * abs(np.exp(o["dlogtot"]) - 1) * PASS_THROUGH[1] * tot25
            lo, hi = min(lo_, hi_), max(lo_, hi_)
            pts = [beta_band[0] * 100 * o["dlogtot"], beta_band[1] * 100 * o["dlogtot"]]
            income = 100 * o["dlogtot"] * EXPORT_GDP_SHARE / 100
            rows.append({"candidate": "any", "case": "", "partner": "all", "global_state": name,
                         "mechanism": f"commodity price state on the {COMMODITY_SHARE:.1f}% commodity-priced share, pass-through 0.6-0.9; "
                                      f"mechanical ToT income effect ≈ {income:+.2f}% of GDP",
                         "probability_qual": "medium (≈p90/p10 of annual Δlog ToT)", "baseline_usd_bn_2025": round(tot25, 1),
                         "impact_low_usd_bn_yr": round(lo, 1), "impact_central": round((lo + hi) / 2, 1), "impact_high": round(hi, 1),
                         "impact_pct_exports_low": round(100 * lo / tot25, 2), "impact_pct_exports_high": round(100 * hi / tot25, 2),
                         "gdp_tot_pts": f"{min(pts):+.2f} to {max(pts):+.2f} pts GDP-pc growth (β upper bound)",
                         "horizon": "1-yr", "elasticity_source": "tot_beta (β band)", "warehouse_series": "wb/TOT.BRA; wb/TX.VAL.*.ZS.UN.BR",
                         "uncertainty_note": "β reduced-form, co-moves with global cycle -> upper bound"})
        else:
            g = gdp_direct(o["lo"], o["hi"])
            rows.append({"candidate": "any", "case": "", "partner": "China (+US)", "global_state": name, "mechanism": o["mech"],
                         "probability_qual": "", "baseline_usd_bn_2025": round(base["China"], 1), "impact_low_usd_bn_yr": o["lo"],
                         "impact_central": (o["lo"] + o["hi"]) / 2, "impact_high": o["hi"],
                         "impact_pct_exports_low": round(100 * o["lo"] / tot25, 2), "impact_pct_exports_high": round(100 * o["hi"] / tot25, 2),
                         "gdp_direct_pct_low": round(g[0], 3), "gdp_direct_pct_high": round(g[1], 3), "horizon": "4-6 quarters",
                         "elasticity_source": "analogues soy 2018/2019, 2025", "warehouse_series": "soy_exports; exports_to_china",
                         "external_fact_ids": ";".join(FACT_IDS.get(name, []))})
    sm = pd.DataFrame(rows); sm["global_state"] = sm["global_state"].fillna("")
    sm.to_csv(os.path.join(OUT, "scenario_matrix.csv"), index=False)
    # cross-table candidate x global state (US$bn/yr: candidate sum range + overlay range)
    ct = []
    ov = sm[sm.global_state != ""].set_index("global_state")
    for cand in ["Lula IV", "Flávio Bolsonaro"]:
        for case in ["best", "worst"]:
            s_ = sm[(sm.candidate == cand) & (sm.case == case) & (sm.partner.str.startswith("SUM"))].iloc[0]
            r = {"candidate": cand, "case": case, "candidate_only": f"{s_.impact_low_usd_bn_yr:+.0f} to {s_.impact_high:+.0f}"}
            for gs in ov.index:
                o = ov.loc[gs]
                lo, hi = s_.impact_low_usd_bn_yr + o.impact_low_usd_bn_yr, s_.impact_high + o.impact_high
                # interactions: under détente, Lula-worst China cell already contains the détente soy loss -> do not double count
                note = ""
                if gs == "US-China détente" and cand == "Lula IV" and case == "worst":
                    lo, hi = s_.impact_low_usd_bn_yr, s_.impact_high; note = "*"
                r[gs] = f"{lo:+.0f} to {hi:+.0f}{note}"
            ct.append(r)
    ct = pd.DataFrame(ct)
    ct.to_csv(os.path.join(OUT, "cross_table.csv"), index=False)
    sums = sm[sm.partner.str.startswith("SUM")].set_index(["candidate", "case"])
    cand_delta_max = max(sums.loc[("Flávio Bolsonaro", "best"), "impact_high"] - sums.loc[("Lula IV", "worst"), "impact_low_usd_bn_yr"],
                         sums.loc[("Lula IV", "best"), "impact_high"] - sums.loc[("Flávio Bolsonaro", "worst"), "impact_low_usd_bn_yr"])
    cand_delta_central = {"Flávio best - Lula worst": sums.loc[("Flávio Bolsonaro", "best"), "impact_central"] - sums.loc[("Lula IV", "worst"), "impact_central"],
                          "Lula best - Flávio worst": sums.loc[("Lula IV", "best"), "impact_central"] - sums.loc[("Flávio Bolsonaro", "worst"), "impact_central"],
                          "Flávio best - Lula best": sums.loc[("Flávio Bolsonaro", "best"), "impact_central"] - sums.loc[("Lula IV", "best"), "impact_central"]}
    tot_delta = (ov.loc["ToT high (+10%)", "impact_low_usd_bn_yr"] - ov.loc["ToT low (-10%)", "impact_high"],
                 ov.loc["ToT high (+10%)", "impact_high"] - ov.loc["ToT low (-10%)", "impact_low_usd_bn_yr"])
    usc_delta = (ov.loc["US-China escalation", "impact_low_usd_bn_yr"] - ov.loc["US-China détente", "impact_high"],
                 ov.loc["US-China escalation", "impact_high"] - ov.loc["US-China détente", "impact_low_usd_bn_yr"])
    dom = {"candidate_delta_max_bn": cand_delta_max, "candidate_delta_central": cand_delta_central,
           "tot_state_delta_bn": tot_delta, "us_china_state_delta_bn": usc_delta}
    rec("scenario.dominance", dom, ["exports_total", "wb/TOT.BRA"])
    return sm, ct, dom


# ================================================================ charts
COL = {"China": "#eb6834", "US": "#2a78d6", "EU": "#1baf7a", "Rest": "#eda100", "Total": "#52514e"}
LAYOUT = dict(template="plotly_white", font=dict(family="Inter, system-ui, sans-serif", size=13, color="#0b0b0b"),
              paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb", hovermode="x unified",
              legend=dict(orientation="h", y=-0.15), margin=dict(l=60, r=30, t=70, b=70))


def charts(a, sh, tout, tb_df, tb, sm, ov_rows, defo, terms_df):
    import plotly.graph_objects as go
    def save(fig, name, title, ytitle=None):
        fig.update_layout(title=dict(text=title, x=0.01), **LAYOUT)
        if ytitle:
            fig.update_yaxes(title=ytitle, gridcolor="#e1e0d9", zerolinecolor="#c3c2b7")
        fig.update_xaxes(gridcolor="#e1e0d9")
        fig.write_html(os.path.join(CH, name), include_plotlyjs="cdn")
    # 1 destination shares 12m rolling
    r12 = P[["exports_to_china", "exports_to_us", "exports_to_eu", "exports_rest", "exports_total"]].rolling(12).sum().loc["2015-01":]
    fig = go.Figure()
    for k, c in [("China", "exports_to_china"), ("EU", "exports_to_eu"), ("US", "exports_to_us"), ("Rest", "exports_rest")]:
        fig.add_trace(go.Scatter(x=r12.index, y=100 * r12[c] / r12["exports_total"], name=k, stackgroup="one", line=dict(width=0.5, color=COL[k]),
                                 hovertemplate="%{y:.1f}%"))
    fig.add_vline(x="2025-08-01", line_dash="dot", line_color="#52514e")
    fig.add_annotation(x="2025-08-01", y=100, text="US 50% tariff (Aug 2025)", showarrow=False, yshift=10)
    save(fig, "1_destination_shares.html", "Brazil exports by destination, 12-month rolling share (ComexStat, to Aug 2026)", "% of exports")
    # 2 product shares annual
    prods = ["oil_exports", "soy_exports", "iron_ore_exports", "beef_exports", "coffee_exports", "sugar_exports", "pulp_exports", "niobium_exports"]
    yrs = A.index[A.index >= 2014]
    fig = go.Figure()
    pal = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
    for i, p_ in enumerate(prods):
        fig.add_trace(go.Bar(x=yrs, y=100 * A.loc[yrs, p_] / A.loc[yrs, "exports_total"], name=p_.replace("_exports", "").replace("_", " "),
                             marker_color=pal[i], hovertemplate="%{y:.1f}%"))
    fig.update_layout(barmode="stack")
    save(fig, "2_product_shares.html", "Eight tracked product groups, % of exports (complete years; residual = manufactures & other)", "% of exports")
    # 3 same-month YoY
    fig = go.Figure()
    idx = pd.date_range("2024-01-01", "2026-08-01", freq="MS")
    for k, c in [("US", "exports_to_us"), ("China", "exports_to_china"), ("EU", "exports_to_eu"), ("Total", "exports_total")]:
        y = [100 * (P.loc[m, c] / P.loc[m - pd.DateOffset(years=1), c] - 1) for m in idx]
        fig.add_trace(go.Scatter(x=idx, y=y, name=k, line=dict(width=2, color=COL[k]), hovertemplate="%{y:.1f}%"))
    fig.add_vline(x="2025-08-01", line_dash="dot"); fig.add_vline(x="2025-11-01", line_dash="dot", line_color="#898781")
    fig.add_hline(y=0, line_color="#c3c2b7")
    save(fig, "3_tariff_yoy.html", "Same-month YoY change in exports by destination (dotted: Aug-2025 tariff, Nov-2025 relief)", "% YoY")
    # 4 US counterfactual
    act, cf = seasonal_cf("exports_to_us", "2025-08-01")
    pl = tout["placebo"]["exports_to_us"]
    fig = go.Figure()
    hist = P.loc["2023-01":"2026-08", "exports_to_us"] / BN
    fig.add_trace(go.Scatter(x=hist.index, y=hist, name="actual", line=dict(width=2, color=COL["US"])))
    lo_band = cf / BN * (1 + pl["did_excovid_p05_p95"][0] / 100); hi_band = cf / BN * (1 + pl["did_excovid_p05_p95"][1] / 100)
    fig.add_trace(go.Scatter(x=cf.index, y=hi_band, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=cf.index, y=lo_band, fill="tonexty", fillcolor="rgba(137,135,129,0.18)", line=dict(width=0),
                             name="placebo 5–95% band (ex-COVID)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=cf.index, y=cf / BN, name="seasonal counterfactual", line=dict(width=2, dash="dash", color="#52514e")))
    save(fig, "4_us_counterfactual.html", f"Exports to the US vs seasonal-factor counterfactual: gap {(act.sum()-cf.sum())/BN:.1f} $bn over 13 months", "US$ bn / month")
    # 5 China one-year vs two-year
    fig = go.Figure()
    labs = ["US", "China", "EU", "Rest", "Total"]; keys = ["us", "cn", "eu", "rest", "tot"]
    fig.add_trace(go.Bar(x=labs, y=[a[f"yoy13_{k}"] for k in keys], name="vs 1 year earlier", marker_color="#2a78d6", texttemplate="%{y:.1f}%"))
    fig.add_trace(go.Bar(x=labs, y=[a[f"two_year_{k}"] for k in keys], name="vs 2 years earlier (base-effect-free)", marker_color="#eb6834", texttemplate="%{y:.1f}%"))
    save(fig, "5_china_base_effect.html", "Aug 2025–Aug 2026 exports: one-year vs two-year change (China '+19%' is mostly a weak 2024 base)", "% change")
    # 6 ToT scatter
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tb_df["dtot"], y=tb_df["g"], mode="markers+text", text=[str(y) for y in tb_df.index], textposition="top center",
                             textfont=dict(size=9, color="#898781"), marker=dict(size=9, color="#2a78d6"), name="year"))
    xs = np.linspace(tb_df["dtot"].min(), tb_df["dtot"].max(), 20); b = tb["1992-2025"]["beta"]
    icpt = tb_df["g"].mean() - b * tb_df["dtot"].mean()
    fig.add_trace(go.Scatter(x=xs, y=icpt + b * xs, name=f"OLS β={b:.2f}", line=dict(color="#eb6834", width=2)))
    fig.update_xaxes(title="100 × Δlog terms of trade (wb/TOT.BRA)")
    save(fig, "6_tot_vs_gdppc.html", "Terms-of-trade change vs GDP-per-capita growth, 1992–2025", "GDP pc growth, %")
    # 7 tornado
    cells = sm[(sm.partner != "all") & ~sm.partner.str.startswith("SUM") & (sm.global_state.fillna("") == "")].copy()
    cells["label"] = cells.candidate.str.replace("Flávio Bolsonaro", "Flávio") + " " + cells.case + " · " + cells.partner
    ovs = sm[sm.global_state.fillna("") != ""].copy(); ovs["label"] = "GLOBAL · " + ovs.global_state
    tt = pd.concat([cells, ovs]); tt["span"] = tt.impact_high - tt.impact_low_usd_bn_yr
    tt = tt.sort_values("span")
    colors = ["#898781" if l.startswith("GLOBAL") else ("#e34948" if "Flávio" in l else "#2a78d6") for l in tt.label]
    fig = go.Figure(go.Bar(y=tt.label, x=tt.span, base=tt.impact_low_usd_bn_yr, orientation="h", marker_color=colors,
                           hovertemplate="%{y}: %{base:.1f} to %{customdata:.1f} $bn/yr<extra></extra>", customdata=tt.impact_high))
    fig.add_vline(x=0, line_color="#52514e")
    fig.update_xaxes(title="US$ bn/yr vs status quo")
    fig.update_layout(height=900, hovermode="closest")
    save(fig, "7_scenario_tornado.html", "Scenario ranges: candidate cells (blue = Lula, red = Flávio) vs global states (grey)")
    # 8 deforestation by term vs EU exports
    yrs = list(range(2016, 2026))
    fig = go.Figure()
    fig.add_trace(go.Bar(x=yrs, y=[defo.loc[y, "wb/AG.LND.PFLS.HA.BR"] / 1e6 for y in yrs], name="primary forest loss (m ha)", marker_color="#1baf7a",
                         hovertemplate="%{y:.2f} m ha"))
    save(fig, "8a_deforestation.html", "Primary forest loss, m ha (wb/AG.LND.PFLS.HA.BR); Bolsonaro 2019–22, Lula III 2023–", "m ha")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=yrs, y=[A.loc[y, "exports_to_eu"] / BN for y in yrs], name="exports to EU ($bn)", marker_color="#2a78d6",
                         hovertemplate="%{y:.1f} $bn"))
    save(fig, "8b_eu_exports.html", "Exports to the EU-27, US$ bn (exports_to_eu): no visible penalty in the high-deforestation years", "US$ bn")
    # combined 8 as small multiples in one html
    with open(os.path.join(CH, "8_deforestation_vs_eu.html"), "w") as f:
        f.write("<html><head><meta charset='utf-8'><title>Deforestation vs EU exports</title></head><body style='background:#fcfcfb'>"
                "<iframe src='8a_deforestation.html' style='width:100%;height:480px;border:0'></iframe>"
                "<iframe src='8b_eu_exports.html' style='width:100%;height:480px;border:0'></iframe></body></html>")


# ================================================================ post-research revisions (plan §6.2 ranges -> revised; each with fact ids)
# Fungible (commodity) share of the Brazil->US mix, H1 2025 (A14): crude 2.38 + oil products 0.83 + semi-finished steel 1.52 +
# coffee 1.17 + beef 0.74 + juices 0.74 + pig iron 0.68 + pulp 0.67 = US$8.73bn of US$20.03bn exports_to_us Jan-Jun 2025.
FUNGIBLE_US = (2.38 + 0.83 + 1.52 + 1.17 + 0.74 + 0.74 + 0.68 + 0.67)

REVISIONS = [
 (("Lula IV", "best", "US"), dict(lo=1, hi=3), "IEEPA 50% voided Feb-2026; current layer is Sec.301 25% + forced-labour 12.5% on only 16.5% (US$6.6bn) of US-bound exports; a Lula deal would carve out more lines, not remove 301", ["A16", "A21", "A22", "A23", "A26"]),
 (("Lula IV", "worst", "US"), dict(lo=-5, hi=-2), "escalation from today's 37.5% layer (exemption list narrowed, 301 rate raised, Magnitsky re-imposition discussed Aug-2026); the 2025 shock is already in the base", ["A12", "A21", "A23", "A25", "A38"]),
 (("Flávio Bolsonaro", "best", "US"), dict(lo=2, hi=6), "301/forced-labour layer lifted in a bilateral deal; recovery capped because 24% of US-bound exports sit under Sec.232 (not country-negotiable) and the 2025 crude drop (-30%) was not tariff-driven", ["A15", "A21", "A22", "A23", "A27", "A28"]),
 (("Flávio Bolsonaro", "worst", "US"), dict(lo=0, hi=2), "301 remedies tied to Pix/ethanol/digital concessions that Congress/BCB resist; relief partial and slow", ["A19", "A20", "A24", "A30"]),
 (("Lula IV", "worst", "China"), dict(lo=-10, hi=-3), "US-China truce/soy pledges shift soy share (China share of Brazil soy 75%->69% H1-26) but Brazil re-routed volume (+8% total soy); beef safeguard is already binding for both candidates (baseline)", ["B06", "B09", "B10", "B11", "B14"]),
 (("Flávio Bolsonaro", "worst", "China"), dict(lo=-15, hi=-3), "Australia analogue: ~A$20bn/yr (~14% of its China exports) hit, much re-routed for fungible goods; scaled to Brazil's ~US$100bn China flow and soy/iron-ore fungibility", ["B19", "B20", "B21", "B22", "A29", "B24"]),
 (("Lula IV", "best", "EU"), dict(lo=1, hi=3), "interim agreement provisionally applied since 1 May 2026 (exports to EU +23.5% May-Aug) + beef relisting after the Sep-2026 antimicrobial suspension", ["C07", "C14", "C18", "C19", "C20"]),
 (("Lula IV", "worst", "EU"), dict(lo=-2, hi=0), "EU beef suspension (US$1.8bn/yr) lasts up to two years; adverse CJEU opinion (2027) unsettles provisional application", ["C05", "C06", "C19", "C20"]),
 (("Lula IV", "worst", "Mercosur/LatAm"), dict(lo=-3, hi=-1), "Brazil-Argentina diplomatic downgrade (Aug-2026), Chinese cars displacing Brazilian autos (-28% H1-26), US-Argentina deal perforating the CET", ["C42", "C43", "C44", "C45", "C50"]),
]
PROB_RATIONALE.update({
 ("Lula IV", "best", "US"): "medium: Lula-Trump met 3 times (A07, A08, A26) and the Nov-2025 carve-out (A09) shows incremental relief happens, but Rubio blames Lula personally (A25)",
 ("Lula IV", "worst", "US"): "low-medium: 301 already final (A21); escalation signals exist (A12, A38) but no new action announced",
 ("Lula IV", "best", "China"): "medium: continuity of plant listings (B38, B39) and 639 market openings (B44); beef quota not flexed (B14)",
 ("Lula IV", "worst", "China"): "medium: truce extended to Jan-2027 with soy pledges (B09, B10), but pledges are behind schedule and diversion works (B11)",
 ("Lula IV", "best", "EU"): "medium-high: interim agreement in force (C07), early gains visible (C18)",
 ("Lula IV", "worst", "EU"): "medium: beef suspension in place (C19), CJEU opinion pending (C06)",
 ("Lula IV", "best", "Mercosur/LatAm"): "low-medium: Argentina sales falling (C43) and ties downgraded (C50)",
 ("Lula IV", "worst", "Mercosur/LatAm"): "medium: already under way (C43, C50)",
 ("Lula IV", "best", "Rest"): "medium: India target raised to US$30bn by 2030 (B29), PTA expansion talks (B30)",
 ("Lula IV", "worst", "Rest"): "low: Israel trade small (B36); Graham Act targets crude/gas buyers, not diesel (A45, A46)",
 ("Flávio Bolsonaro", "best", "US"): "medium: Trump received Flávio (A27); Flávio calls it 'tarifa do Lula' and promises a deal (A28); 301 is a trade finding, so removal needs concessions",
 ("Flávio Bolsonaro", "worst", "US"): "medium: 301 targets Pix/ethanol/digital/deforestation (A19) - structural asks no president delivers alone",
 ("Flávio Bolsonaro", "best", "China"): "high: Flávio says 'economically pragmatic' (A31, B23); 2019-22 record had no Chinese trade measures (B25-B27)",
 ("Flávio Bolsonaro", "worst", "China"): "low: triggers exist (BRICS exit floated A29, Pix vs UnionPay B24) but China depends on Brazilian soy (73.6% of its imports, B05)",
 ("Flávio Bolsonaro", "best", "EU"): "low-medium: agreement already provisionally applied (C07); campaign calls it important to EU audiences (C22)",
 ("Flávio Bolsonaro", "worst", "EU"): "low-medium: EUDR applies 30 Dec 2026 (C23, C24); programme omits Paris/NDC and promises to cut 'amarras ambientais' (C35); Brazil standard-risk today (C25); deforestation currently falling (C28, C29)",
 ("Flávio Bolsonaro", "best", "Mercosur/LatAm"): "medium: Milei alliance (C50), Uruguay backs flexibility (C51)",
 ("Flávio Bolsonaro", "worst", "Mercosur/LatAm"): "low-medium: programme silent on Mercosur but campaign talks of freeing Brazil from its constraints (A30, C22)",
 ("Flávio Bolsonaro", "best", "Rest"): "low: MAPA continuity (B44, B46), but no specific Asia/Gulf deal agenda in the programme (A30)",
 ("Flávio Bolsonaro", "worst", "Rest"): "medium trigger / low cost: embassy move pledged within 6 months (B37); 2019 precedent = 33 Saudi plant delistings, no sustained loss found (B33, B34); ME chicken US$3.1bn (B35)",
})
FACT_IDS.update({
 ("Lula IV", "best", "China"): ["B38", "B39", "B44", "B14"], ("Flávio Bolsonaro", "best", "China"): ["A31", "B23", "B25", "B26", "B27"],
 ("Flávio Bolsonaro", "best", "EU"): ["C07", "C22"], ("Flávio Bolsonaro", "worst", "EU"): ["C23", "C24", "C25", "C26", "C27", "C35", "C36", "C38"],
 ("Lula IV", "best", "Mercosur/LatAm"): ["C42", "C43"], ("Flávio Bolsonaro", "best", "Mercosur/LatAm"): ["C44", "C50", "C51"],
 ("Flávio Bolsonaro", "worst", "Mercosur/LatAm"): ["A30", "C22", "C42"], ("Lula IV", "best", "Rest"): ["B29", "B30", "B32"],
 ("Lula IV", "worst", "Rest"): ["B36", "A45", "A46"], ("Flávio Bolsonaro", "best", "Rest"): ["B44", "B46"],
 ("Flávio Bolsonaro", "worst", "Rest"): ["B33", "B34", "B35", "B37"],
 "US-China escalation": ["B04", "B05"], "US-China détente": ["B06", "B09", "B10", "B11"],
})
OVERLAY_REVISIONS = [("US-China détente", dict(lo=-8, hi=-2), "since the Nov-2025 truce China's share of Brazil soy fell 75%->69% yet total soy +8% (B11) and soy_exports +15.2% YTD: re-routing works", ["B09", "B10", "B11"])]


def apply_revisions():
    for cell, new, why, ids in REVISIONS:
        old = (SCEN[cell]["lo"], SCEN[cell]["hi"])
        SCEN[cell].update(new)
        SCEN_REVISIONS.append({"cell": " / ".join(cell), "plan_range": f"{old[0]:+g} to {old[1]:+g}", "revised": f"{new['lo']:+g} to {new['hi']:+g}",
                               "reason": why, "fact_ids": ";".join(ids)})
        FACT_IDS[cell] = sorted(set(FACT_IDS.get(cell, []) + ids))
    for name, new, why, ids in OVERLAY_REVISIONS:
        old = (OVERLAYS[name]["lo"], OVERLAYS[name]["hi"]); OVERLAYS[name].update(new)
        SCEN_REVISIONS.append({"cell": name, "plan_range": f"{old[0]:+g} to {old[1]:+g}", "revised": f"{new['lo']:+g} to {new['hi']:+g}", "reason": why, "fact_ids": ";".join(ids)})
    for k, v in FACT_IDS.items():
        pass
    pd.DataFrame(SCEN_REVISIONS).to_csv(os.path.join(OUT, "scenario_revisions.csv"), index=False)
    rec("scenario.revisions", SCEN_REVISIONS, "n/a")


def merge_external_facts():
    fs = [pd.read_csv(os.path.join(OUT, "web", f)) for f in ["facts_A.csv", "facts_B.csv", "facts_C.csv"]]
    ef = pd.concat(fs, ignore_index=True)
    used = {}
    for cell, ids in FACT_IDS.items():
        lab = " / ".join(cell) if isinstance(cell, tuple) else cell
        for i in ids:
            used.setdefault(i, []).append(lab)
    ef["used_in_scenario_ids"] = ef["fact_id"].map(lambda i: " | ".join(used.get(i, [])))
    ef = ef[["fact_id", "claim", "date", "source_url", "publisher", "accessed", "used_in_scenario_ids", "confidence", "channel"]]
    ef.to_csv(os.path.join(OUT, "external_facts.csv"), index=False)
    return ef


def write_results():
    def conv(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, (pd.Timestamp,)):
            return str(o)[:10]
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)
    R["_sql"] = {"value": SQLLOG}
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(R, f, indent=1, default=conv, ensure_ascii=False)


def run_full(fungible_share):
    global COMMODITY_SHARE, EXPORT_GDP_SHARE
    a, diffs = anchors()
    seas = seasonality(); rec("seasonality", seas.round(4).to_dict(), ["exports_to_china", "exports_to_us", "soy_exports"])
    prod = products_0_4(); conf = confounders_0_5()
    ex, sh, wb, pc = exposure_map(a)
    COMMODITY_SHARE = float(pc.loc[2025, ["wb/TX.VAL.FOOD.ZS.UN.BR", "wb/TX.VAL.FUEL.ZS.UN.BR", "wb/TX.VAL.MMTL.ZS.UN.BR"]].sum())
    EXPORT_GDP_SHARE = 100 * A.loc[2025, "exports_total"] / BN / GDP25
    rec("commodity_share_2025", COMMODITY_SHARE, ["wb/TX.VAL.FOOD.ZS.UN.BR", "wb/TX.VAL.FUEL.ZS.UN.BR", "wb/TX.VAL.MMTL.ZS.UN.BR"])
    pv, wbq = price_vs_volume()
    te, tout = tariff_episode(a)
    dv = diversion_bounds(a, fungible_share)
    tb, tb_df = tot_beta(); fx = fx_elasticity(); an, terms_df, defo = analogues(); gold_tables()
    # tariff_episode.csv: estimator rows + elasticity outputs
    extra = pd.DataFrame([
        {"estimator": "E_tariff (realised % fall, US-bound)", "series": "exports_to_us", "window_months": 4, "post_yoy": a["us_augnov_yoy"]},
        {"estimator": "E_tariff (realised % fall, US-bound)", "series": "exports_to_us", "window_months": 13, "post_yoy": a["yoy13_us"]},
        {"estimator": "G_US $bn/yr (pre-trend DiD)", "series": "exports_to_us", "window_months": 13, "gap_bn_yr": a["gap_us_yr"]},
        {"estimator": "diversion upper bound rate", "series": "non-US", "window_months": 13, "gap_pct": 100 * dv["upper_bound_rate"]},
        {"estimator": "diversion central rate (fungible share of US mix)", "series": "non-US", "window_months": 13, "gap_pct": 100 * fungible_share},
        {"estimator": "net national loss central $bn/yr", "series": "exports_total", "window_months": 13, "gap_bn_yr": dv["net_loss_central_yr"]},
    ])
    pl = pd.DataFrame([{"estimator": "placebo", "series": k, **{kk: vv for kk, vv in v.items() if not kk.endswith("series") and kk not in ("breaks", "largest_placebo")}}
                       for k, v in tout["placebo"].items()])
    pd.concat([te, extra, pl]).to_csv(os.path.join(OUT, "tariff_episode.csv"), index=False)
    apply_revisions(); merge_external_facts()
    beta_band = (min(tb["1992-2025"]["beta"], 0.25), 0.29)
    sm, ct, dom = scenario_matrix(beta_band)
    charts(a, sh, tout, tb_df, tb, sm, None, defo, terms_df)
    write_results()
    return dict(a=a, diffs=diffs, prod=prod, conf=conf, ex=ex, sh=sh, wb=wb, pc=pc, pv=pv, wbq=wbq, te=te, tout=tout, dv=dv, tb=tb,
                fx=fx, an=an, terms_df=terms_df, defo=defo, sm=sm, ct=ct, dom=dom)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "full":
    FUNG = FUNGIBLE_US / (P.loc["2025-01":"2025-06", "exports_to_us"].sum() / BN)
    rec("diversion.fungible_share_us_mix", FUNG, "exports_to_us", note="numerator external (A14)")
    o = run_full(FUNG)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print("mismatches", o["diffs"])
    print(o["ct"].to_string()); print(o["dom"])
    print(o["sm"][["candidate", "case", "partner", "global_state", "impact_low_usd_bn_yr", "impact_high", "impact_pct_exports_low",
                   "impact_pct_exports_high", "gdp_direct_pct_low", "gdp_direct_pct_high", "gdp_tot_pts", "usd_bn_2027", "usd_bn_2027_30_cum"]].to_string())
    print(o["dv"])
