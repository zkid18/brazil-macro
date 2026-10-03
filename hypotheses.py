"""hypotheses.py — company-level derivations + falsifiable hypothesis tests (gold).

Called by pipeline.py after silver is built. Two jobs:

1. derive_company_series(silver) -> silver-shaped frames appended to silver:
     revenue_usd_bn, net_income_usd_bn, net_debt_brl_bn      (quarterly, per company)
     total_return_brl / total_return_usd                      (monthly index, 2012-01=100)
     dividend_yield_ttm                                       (monthly, per company)
     *_unit_value_usd_t  (oil / iron ore / pulp export prices, country, monthly)
     implicit_interest_rate, nominal_gdp_growth, r_minus_g    (country, monthly)

2. build_hypothesis_tests(silver) -> gold table `hypothesis_tests`, one row per
   hypothesis: the claim, the test, the statistic, a pre-registered threshold and a
   verdict in {Supported, Not supported, Mixed, Insufficient data}. Thresholds are
   fixed here (not tuned to the data) so a verdict can flip as new data lands.

Every test degrades to "Insufficient data" if an input series is missing, so a
partial ingest still builds.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

COUNTRY = "BR"
BASE = "2012-01-01"  # Davidson's book year: the natural "since the book" origin
COMPANIES = {  # entity_id -> (display name, main ticker, one-line role)
    "PETR": ("Petrobras", "PETR4", "State-controlled oil major (also listed as PETR3)"),
    "VALE": ("Vale", "VALE3", "Iron-ore miner; China's steel mills are its customers"),
    "AXIA": ("Axia (ex-Eletrobras)", "AXIA3", "Largest power generator; privatized 2022"),
    "SUZB": ("Suzano", "SUZB3", "World's largest pulp producer; sells in US dollars"),
    "PRIO": ("PRIO", "PRIO3", "Private pre-salt-era oil producer"),
    "ITUB": ("Itaú Unibanco", "ITUB4", "Largest private bank — the non-resource control"),
}
RESOURCE = ["PETR", "VALE", "AXIA", "SUZB", "PRIO"]


# ----------------------------------------------------------------------------- helpers
def _s(silver, metric_id, entity=COUNTRY):
    s = silver[(silver.metric_id == metric_id) & (silver.entity_id == entity)]
    if s.empty:
        return None
    return s.assign(dt=pd.to_datetime(s["date"])).sort_values("dt").set_index("dt")["value"]


def _frame(metric_id, name, theme, unit, values, freq, entity=COUNTRY, run_ts=""):
    if values is None:
        return None
    v = values.replace([np.inf, -np.inf], np.nan).dropna()
    if v.empty:
        return None
    return pd.DataFrame({
        "metric_id": metric_id, "entity_id": entity, "metric_name": name, "theme": theme,
        "source_id": "derived", "resolved_source": "derived_companies", "freq": freq,
        "date": v.index.strftime("%Y-%m-%d"), "year": v.index.year,
        "value": v.to_numpy(dtype=float), "unit": unit,
        "ingested_via": "pipeline_derive", "load_ts": run_ts,
    })


def _q_mean(s):  # daily/monthly -> calendar-quarter mean, indexed at quarter end
    return s.resample("QE").mean() if s is not None else None


def _m_last(s):
    """Month-end last value; the final (possibly partial) month is dated at its last
    actual observation rather than a future month-end."""
    if s is None:
        return None
    m = s.resample("ME").last().dropna()
    if len(m) and m.index[-1] > s.index[-1]:
        m.index = m.index[:-1].append(pd.DatetimeIndex([s.index[-1]]))
    return m


def _q(d):
    return f"{d.year}-Q{d.quarter}"


def _ols_r2(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return 1 - resid.var() / y.var(), beta


def _trend_pct_per_year(s):
    """Log-linear trend growth (%/yr) of a positive series."""
    s = s[s > 0].dropna()
    if len(s) < 8:
        return None
    t = (s.index - s.index[0]).days / 365.25
    slope = np.polyfit(t, np.log(s.to_numpy()), 1)[0]
    return (np.exp(slope) - 1) * 100


def total_return_index(px, divs):
    """Daily total-return index from split-adjusted closes + cash dividends (reinvested
    on the ex-date). px, divs: date-indexed Series (BRL). Returns index, first day = 100."""
    px = px.dropna()
    d = divs.groupby(level=0).sum().reindex(px.index, fill_value=0.0) if divs is not None \
        else pd.Series(0.0, index=px.index)
    gross = (px + d) / px.shift(1)
    return 100 * gross.fillna(1.0).cumprod()


# ----------------------------------------------------------------------------- derived series
def derive_company_series(silver, run_ts="") -> list:
    out = []
    fx = _s(silver, "brl_usd")
    fx_q = _q_mean(fx)

    for ent in COMPANIES:
        name = COMPANIES[ent][0]
        for src, dst, label in [("revenue_brl", "revenue_usd_bn", "Revenue"),
                                ("net_income_brl", "net_income_usd_bn", "Net income")]:
            v = _s(silver, src, ent)
            if v is not None and fx_q is not None:
                usd = (v / fx_q.reindex(v.index, method="nearest")).dropna()
                out.append(_frame(dst, f"{label} in USD bn (quarterly)", "companies",
                                  "usd_bn", usd, "quarterly", ent, run_ts))
        debt, cash = _s(silver, "gross_debt_brl", ent), _s(silver, "cash_brl", ent)
        if debt is not None and cash is not None:
            out.append(_frame("net_debt_brl_bn", "Net debt (gross debt - cash), BRL bn",
                              "companies", "brl_bn", (debt - cash).dropna(), "quarterly",
                              ent, run_ts))
        px = _s(silver, "share_close_adj_brl", ent)
        if px is not None:
            px = px[px.index >= BASE]
            dv = _s(silver, "dividend_per_share_brl", ent)
            tr = total_return_index(px, dv)
            tr_m = _m_last(tr)
            tr_m = tr_m / tr_m.iloc[0] * 100
            out.append(_frame("total_return_brl", f"{name}: total return in BRL (2012=100)",
                              "companies", "index_2012_100", tr_m, "monthly", ent, run_ts))
            if fx is not None:
                fx_m = fx.reindex(tr_m.index, method="ffill")
                usd = tr_m / fx_m
                usd = usd / usd.dropna().iloc[0] * 100
                out.append(_frame("total_return_usd", f"{name}: total return in USD (2012=100)",
                                  "companies", "index_2012_100", usd, "monthly", ent, run_ts))
            if dv is not None:
                pm = _m_last(px)
                dsum = dv.groupby(level=0).sum()
                ttm = pd.Series([dsum[(dsum.index > d - pd.DateOffset(years=1)) & (dsum.index <= d)].sum()
                                 for d in pm.index], index=pm.index)
                yld = ttm / pm * 100
                out.append(_frame("dividend_yield_ttm", f"{name}: trailing-12m dividend yield",
                                  "companies", "pct", yld[yld.index >= "2013-01-01"],
                                  "monthly", ent, run_ts))

    # Ibovespa total-return in USD on the same 2012=100 basis (Ibovespa is a TR index)
    ibov = _s(silver, "ibovespa_level")
    if ibov is not None and fx is not None:
        mi = _m_last(ibov)
        m = (mi / fx.reindex(mi.index, method="ffill")).dropna()
        m = m[m.index >= BASE]
        out.append(_frame("total_return_usd", "Ibovespa: total return in USD (2012=100)",
                          "companies", "index_2012_100", m / m.iloc[0] * 100, "monthly",
                          "IBOV", run_ts))
        mb = _m_last(ibov)
        mb = mb[mb.index >= BASE]
        out.append(_frame("total_return_brl", "Ibovespa: total return in BRL (2012=100)",
                          "companies", "index_2012_100", mb / mb.iloc[0] * 100, "monthly",
                          "IBOV", run_ts))

    # export unit values (US$ per tonne) — price vs volume decomposition
    for fob, kg, mid, nm in [("oil_exports", "oil_exports_kg", "oil_export_unit_value",
                              "Crude oil export price (US$/t)"),
                             ("iron_ore_exports", "iron_ore_exports_kg", "iron_ore_unit_value",
                              "Iron ore export price (US$/t)"),
                             ("pulp_exports", "pulp_exports_kg", "pulp_unit_value",
                              "Pulp export price (US$/t)")]:
        f, k = _s(silver, fob), _s(silver, kg)
        if f is not None and k is not None:
            unit = silver.loc[silver.metric_id == kg, "unit"].iloc[0]
            tonnes = k * 1000 if unit == "thousand_tonnes" else k
            out.append(_frame(mid, nm, "derived_trade", "usd_per_t", (f / tonnes), "monthly",
                              run_ts=run_ts))

    # r - g on public debt: implicit interest rate vs nominal GDP growth
    ib, debt, ngdp = (_s(silver, "interest_bill_gdp"), _s(silver, "gross_public_debt_gdp"),
                      _s(silver, "gdp_nominal_12m_brl"))
    if ib is not None and debt is not None and ngdp is not None:
        ib, debt, ngdp = (x.resample("MS").last() for x in (ib, debt, ngdp))
        # interest paid over 12m / debt a year ago, both in R$: (I_t/Y_t) / (D_t-12/Y_t-12) x Y_t/Y_t-12
        r = (ib / debt.shift(12) * ngdp / ngdp.shift(12) * 100).dropna()
        g = (ngdp.pct_change(12) * 100).dropna()
        out.append(_frame("implicit_interest_rate", "Implicit interest rate on gross debt",
                          "fiscal", "pct_pa", r, "monthly", run_ts=run_ts))
        out.append(_frame("nominal_gdp_growth", "Nominal GDP growth (12m, YoY)", "fiscal",
                          "pct_yoy", g, "monthly", run_ts=run_ts))
        out.append(_frame("r_minus_g", "Interest rate on debt minus nominal growth (r-g)",
                          "fiscal", "pct_pts", (r - g).dropna(), "monthly", run_ts=run_ts))
    return [f for f in out if f is not None]


# ----------------------------------------------------------------------------- tests
def _row(hid, group, title, question, claim, test, threshold, stat=None, verdict=None,
         evidence="", so_what="", inputs=(), as_of=None, chart=None, why=""):
    return dict(hyp_id=hid, group=group, title=title, question=question, claim=claim,
                test=test, threshold=threshold, verdict_note=why,
                statistic=None if stat is None else float(round(stat, 4)),
                verdict=verdict or "Insufficient data", evidence=evidence, so_what=so_what,
                inputs=", ".join(inputs), as_of=as_of, chart=chart or "")


def _missing(*series):
    return any(s is None or len(s.dropna()) == 0 for s in series)


def h1_petrobras_price_not_volume(silver):
    meta = dict(hid="H1", group="Companies & energy",
                title="Petrobras earns on price, not volume",
                question="When Petrobras's dollar revenue moves, is it the oil price or how much it pumps?",
                claim="Brent explains at least 70% of the swings in Petrobras's quarterly USD revenue; "
                      "adding production volume explains less than 10 points more.",
                test="Regress log(quarterly revenue in USD) on log(Brent) and log(Petrobras-operated "
                     "output), 2016 onward. Compare R² with and without volume.",
                threshold="Supported if R²(Brent) ≥ 0.70 and volume adds < 0.10; Mixed if 0.50 ≤ R² < 0.70",
                inputs=("revenue_usd_bn[PETR]", "brent_usd", "operated_oil_production_kbd[PETR]"),
                chart="h1")
    rev, brent = _s(silver, "revenue_usd_bn", "PETR"), _s(silver, "brent_usd")
    vol = _s(silver, "operated_oil_production_kbd", "PETR")
    if _missing(rev, brent):
        return _row(**meta)
    df = pd.concat([rev.rename("rev"), _q_mean(brent).rename("brent")], axis=1)
    if vol is not None:
        df = df.join(_q_mean(vol).rename("vol"))
    df = df[df.index >= "2016-01-01"].dropna()
    if len(df) < 12:
        return _row(**meta)
    y = np.log(df.rev.to_numpy())
    r2_b, beta = _ols_r2(y, [np.log(df.brent.to_numpy())])
    add = None
    if "vol" in df:
        r2_f, _ = _ols_r2(y, [np.log(df.brent.to_numpy()), np.log(df.vol.to_numpy())])
        add = r2_f - r2_b
    ok = r2_b >= 0.70 and (add is None or add < 0.10)
    verdict = "Supported" if ok else ("Mixed" if r2_b >= 0.5 else "Not supported")
    why = (f"R² {r2_b:.2f} {'meets' if r2_b >= 0.70 else 'is below'} 0.70"
           + (f"; volume adds {add * 100:.1f} pts ({'under' if add < 0.10 else 'over'} the 10-pt limit)"
              if add is not None else ""))
    ev = (f"{len(df)} quarters {_q(df.index[0])}–{_q(df.index[-1])}: Brent alone explains "
          f"{r2_b:.0%} of revenue swings (elasticity {beta[1]:.2f})"
          + (f"; adding volume explains {add * 100:+.1f} pts more" if add is not None
             else "; volume series not available"))
    return _row(**meta, stat=r2_b, verdict=verdict, evidence=ev, as_of=f"{df.index[-1]:%Y-%m-%d}", why=why,
                so_what="Petrobras is mostly a bet on the oil price, not on how much oil Brazil "
                        "pumps — pre-salt growth matters less to the stock than Brent does.")


def h2_oil_volume_iron_flat(silver):
    meta = dict(hid="H2", group="Companies & energy",
                title="Oil exports grow by volume; iron ore doesn't",
                question="Is Brazil's export boom about selling more stuff, or getting better prices?",
                claim="Crude-oil export tonnes grow ≥ 5%/yr since 2016 while iron-ore tonnes stay "
                      "roughly flat (within ±2%/yr).",
                test="Log-linear trend of 12-month rolling export tonnes (ComexStat), 2016 onward.",
                threshold="Supported if oil ≥ +5%/yr and |iron ore| ≤ 2%/yr; Mixed if only one holds",
                inputs=("oil_exports_kg", "iron_ore_exports_kg", "presalt_share"), chart="h2")
    oil, iron = _s(silver, "oil_exports_kg"), _s(silver, "iron_ore_exports_kg")
    if _missing(oil, iron):
        return _row(**meta)
    o = oil.rolling(12).sum()[oil.index >= "2016-12-01"]
    i = iron.rolling(12).sum()[iron.index >= "2016-12-01"]
    go, gi = _trend_pct_per_year(o), _trend_pct_per_year(i)
    if go is None or gi is None:
        return _row(**meta)
    ps = _s(silver, "presalt_share")
    verdict = "Supported" if go >= 5 and abs(gi) <= 2 else ("Mixed" if go >= 5 or abs(gi) <= 2
                                                           else "Not supported")
    why = (f"oil {go:+.1f}%/yr {'meets' if go >= 5 else 'misses'} +5%; iron ore {gi:+.1f}%/yr "
           f"{'within' if abs(gi) <= 2 else 'outside'} ±2%")
    ev = (f"Oil export tonnes {go:+.1f}%/yr vs iron ore {gi:+.1f}%/yr since 2016"
          + (f"; pre-salt = {ps.iloc[-1]:.0f}% of oil output ({ps.index[-1]:%b %Y})" if ps is not None else ""))
    return _row(**meta, stat=go, verdict=verdict, evidence=ev, as_of=f"{o.index[-1]:%Y-%m-%d}", why=why,
                so_what="Oil is Brazil's genuine volume growth story (pre-salt); iron ore is a "
                        "mature volume business whose value rides on Chinese prices.")


def h3_vale_china_price(silver):
    meta = dict(hid="H3", group="Companies & energy",
                title="Vale is a China iron-ore price proxy",
                question="Does Vale's revenue follow what China pays for iron ore?",
                claim="Vale's quarterly USD revenue moves with the iron-ore export price "
                      "(correlation > 0.7) while export tonnes trend < 2%/yr.",
                test="Correlation of Vale quarterly USD revenue with the quarterly average "
                     "iron-ore export unit value (US$/t), 2016 onward.",
                threshold="Supported if ρ > 0.7 and |tonnes trend| < 2%/yr; Mixed if 0.4 ≤ ρ; Not supported if ρ < 0.4",
                inputs=("revenue_usd_bn[VALE]", "iron_ore_unit_value", "iron_ore_exports_kg",
                        "china_export_share"), chart="h3")
    rev, uv = _s(silver, "revenue_usd_bn", "VALE"), _s(silver, "iron_ore_unit_value")
    if _missing(rev, uv):
        return _row(**meta)
    df = pd.concat([rev.rename("rev"), _q_mean(uv).rename("uv")], axis=1)
    df = df[df.index >= "2016-01-01"].dropna()
    if len(df) < 12:
        return _row(**meta)
    rho = df.rev.corr(df.uv)
    iron = _s(silver, "iron_ore_exports_kg")
    gi = _trend_pct_per_year(iron.rolling(12).sum()[iron.index >= "2016-12-01"]) if iron is not None else None
    verdict = ("Supported" if rho > 0.7 and (gi is None or abs(gi) < 2) else
               "Mixed" if rho >= 0.4 else "Not supported")
    why = f"ρ {rho:.2f} {'above' if rho > 0.7 else 'below'} 0.7" + (
        f"; tonnes {gi:+.1f}%/yr {'within' if abs(gi) < 2 else 'outside'} ±2%" if gi is not None else "")
    ev = (f"ρ(Vale revenue, iron-ore US$/t) = {rho:.2f} over {len(df)} quarters"
          + (f"; tonnes trend {gi:+.1f}%/yr" if gi is not None else ""))
    return _row(**meta, stat=rho, verdict=verdict, evidence=ev, as_of=f"{df.index[-1]:%Y-%m-%d}", why=why,
                so_what="Owning Vale is largely owning the Chinese steel cycle.")


def h4_hydro_stress_axia(silver):
    meta = dict(hid="H4", group="Companies & energy",
                title="Droughts raise power costs more than they cut Axia's output",
                question="When reservoirs run low, does the hydro giant lose output, or does the price of power jump?",
                claim="In months when reservoir storage (EAR) is below 40%, the marginal cost of power "
                      "(CMO) is more than double its level in other months, while the share of national "
                      "generation from Axia (formerly Eletrobras, mostly hydro) falls by more than 3 points.",
                test="Compare low-storage months (EAR < 40%) with the rest, 2016 onward. Axia's share is "
                     "measured against its own calendar-year average, so the steady rise of rooftop solar "
                     "in the national total does not bias the comparison.",
                threshold="Supported if CMO ratio > 2× and share falls > 3 pts; Mixed if only one holds",
                inputs=("stored_energy_ear", "generation_share_sin[AXIA]", "cmo_power_cost"),
                chart="h4")
    ear, share, cmo = (_s(silver, "stored_energy_ear"), _s(silver, "generation_share_sin", "AXIA"),
                       _s(silver, "cmo_power_cost"))
    if _missing(ear, share, cmo):
        return _row(**meta)
    df = pd.concat([ear.resample("MS").mean().rename("ear"),
                    share.resample("MS").mean().rename("share"),
                    cmo.resample("MS").mean().rename("cmo")], axis=1).dropna()
    df = df[df.index >= "2016-01-01"]
    df["resid"] = df.share - df.groupby(df.index.year).share.transform("mean")
    low = df[df.ear < 40]
    if len(low) < 3 or len(df) - len(low) < 3:
        return _row(**meta, evidence=f"only {len(low)} low-storage months in overlap")
    rest = df[df.ear >= 40]
    drop = rest.resid.mean() - low.resid.mean()
    ratio = low.cmo.mean() / rest.cmo.mean() if rest.cmo.mean() else np.nan
    ok_c, ok_s = ratio > 2, drop > 3
    verdict = "Supported" if ok_s and ok_c else ("Mixed" if ok_s or ok_c else "Not supported")
    why = (f"CMO {ratio:.1f}× ({'over' if ok_c else 'under'} 2×); Axia share "
           f"{'falls' if drop >= 0 else 'rises'} {abs(drop):.1f} pts ({'over' if ok_s else 'under'} 3)")
    ev = (f"{len(low)} low-storage months: CMO averaged R${low.cmo.mean():,.0f}/MWh vs "
          f"R${rest.cmo.mean():,.0f} otherwise ({ratio:.1f}×); Axia's share was {abs(drop):.1f} pts "
          f"{'lower' if drop >= 0 else 'higher'} than its same-year average")
    return _row(**meta, stat=ratio, verdict=verdict, evidence=ev, as_of=f"{df.index[-1]:%Y-%m-%d}",
                why=why)


def _last_common(series):
    """Values of several monthly series at their latest common calendar month."""
    per = [s.copy() for s in series]
    for s in per:
        s.index = s.index.to_period("M")
    common = sorted(set.intersection(*(set(s.index) for s in per)))
    if not common:
        return None, None
    p = common[-1]
    return [float(s.loc[p]) for s in per], p


def h5_resource_champions_tr(silver):
    meta = dict(hid="H5", group="Companies & energy",
                title="Resource champions lagged the index in dollars since 2012",
                question="If you bought Petrobras or Vale when the book came out, did you beat the market?",
                claim="Petrobras (PETR4) and Vale (VALE3) both delivered a lower total return in US dollars "
                      "(dividends reinvested) than the Ibovespa from January 2012 to today.",
                test="USD total-return index, Jan 2012 = 100, for PETR4 and VALE3 vs the Ibovespa "
                     "(itself a total-return index) converted to USD, compared in the same month.",
                threshold="Supported if both are below the Ibovespa; Mixed if one is; Not supported if neither",
                inputs=("total_return_usd[PETR,VALE,IBOV]",), chart="h5")
    p, v, i = (_s(silver, "total_return_usd", e) for e in ("PETR", "VALE", "IBOV"))
    if _missing(p, v, i):
        return _row(**meta)
    (pe, ve, ie), per = _last_common([p, v, i])
    below = (pe < ie) + (ve < ie)
    verdict = {2: "Supported", 1: "Mixed", 0: "Not supported"}[below]
    why = (f"Petrobras {'below' if pe < ie else 'above'} and Vale {'below' if ve < ie else 'above'} "
           f"the Ibovespa")
    ev = (f"US$100 in Jan 2012 → Petrobras ${pe:.0f}, Vale ${ve:.0f}, Ibovespa ${ie:.0f} "
          f"({per.strftime('%b %Y')}, dividends reinvested)")
    return _row(**meta, stat=max(pe, ve) - ie, verdict=verdict, evidence=ev,
                as_of=f"{per.end_time:%Y-%m-%d}", why=why)


def h6_suzano_brl_hedge(silver):
    meta = dict(hid="H6", group="Companies & energy",
                title="Suzano is the currency hedge the index lacks",
                question="Does Suzano's stock rise when the real weakens?",
                claim="Suzano's monthly returns in reais correlate positively (ρ > 0.35) with the real's "
                      "depreciation, while Itaú's (the domestic control) correlate negatively.",
                test="Correlation of monthly total returns in BRL with the monthly % change in "
                     "BRL per USD, 2012 onward.",
                threshold="Supported if ρ(Suzano) > 0.35 and ρ(Itaú) < 0; Mixed if one holds",
                inputs=("total_return_brl[SUZB,ITUB]", "brl_usd"), chart="h6")
    s, it, fx = (_s(silver, "total_return_brl", "SUZB"), _s(silver, "total_return_brl", "ITUB"),
                 _s(silver, "brl_usd"))
    if _missing(s, it, fx):
        return _row(**meta)
    dfx = _m_last(fx).pct_change()
    df = pd.concat([s.pct_change().rename("s"), it.pct_change().rename("i"),
                    dfx.rename("fx")], axis=1).dropna()
    if len(df) < 24:
        return _row(**meta)
    rs, ri = df.s.corr(df.fx), df.i.corr(df.fx)
    ok_s, ok_i = rs > 0.35, ri < 0
    verdict = "Supported" if ok_s and ok_i else ("Mixed" if ok_s or ok_i else "Not supported")
    why = (f"Suzano ρ {rs:+.2f} ({'above' if ok_s else 'below'} 0.35); Itaú ρ {ri:+.2f} "
           f"({'negative' if ok_i else 'not negative'})")
    ev = f"ρ(Suzano, BRL weakening) = {rs:+.2f}; ρ(Itaú, BRL weakening) = {ri:+.2f} over {len(df)} months"
    return _row(**meta, stat=rs, verdict=verdict, evidence=ev, as_of=f"{df.index[-1]:%Y-%m-%d}", why=why)


def l1_debt_service_retail(silver):
    meta = dict(hid="L1", group="Households & labour",
                title="Debt service is squeezing shoppers",
                question="When families spend more of their income on loan payments, do they buy less?",
                claim="A rise in the household debt-service ratio is followed by slower retail "
                      "volumes: correlation of its 12-month change with retail-volume growth six "
                      "months later is below −0.3.",
                test="ρ(12-month change in debt-service ratio at t, retail volume growth year on year at t+6), "
                     "2012 onward.",
                threshold="Supported if ρ < −0.3; Mixed if −0.3 ≤ ρ < 0; Not supported if ρ ≥ 0",
                inputs=("household_debt_service_ratio", "retail_sales_volume"), chart="l1")
    dsr, ret = _s(silver, "household_debt_service_ratio"), _s(silver, "retail_sales_volume")
    if _missing(dsr, ret):
        return _row(**meta)
    d = dsr.resample("MS").last().diff(12)
    r = (ret.resample("MS").last().pct_change(12) * 100).shift(-6)
    df = pd.concat([d.rename("d"), r.rename("r")], axis=1)
    df = df[df.index >= "2012-01-01"].dropna()
    if len(df) < 24:
        return _row(**meta)
    rho = df.d.corr(df.r)
    verdict = "Supported" if rho < -0.3 else ("Mixed" if rho < 0 else "Not supported")
    why = f"ρ {rho:+.2f}: negative, but {'beyond' if rho < -0.3 else 'not beyond'} −0.3"
    ev = (f"ρ = {rho:+.2f} over {len(df)} months; debt service now {dsr.iloc[-1]:.1f}% of income "
          f"(series high {dsr.max():.1f}%, {dsr.idxmax():%b %Y})")
    return _row(**meta, stat=rho, verdict=verdict, evidence=ev, as_of=f"{dsr.index[-1]:%Y-%m-%d}", why=why)


def l2_caged_leads_pnad(silver):
    meta = dict(hid="L2", group="Households & labour",
                title="Formal hiring warns before unemployment turns",
                question="Does a slowdown in formal job creation show up before unemployment rises?",
                claim="Formal net hiring (CAGED, the labour ministry's register of formal jobs) leads "
                      "unemployment: its 12-month average correlates below −0.4 with the change in the "
                      "unemployment rate over the following 12 months.",
                test="ρ(CAGED 12-month average at t, unemployment(t+12) − unemployment(t)), 2021 onward. "
                     "12-month windows remove the seasonality of both unadjusted series; 2020 is excluded "
                     "as the COVID shock. (Revised on review from a 3-month / 6-month version that "
                     "leaned on the 2020 months.)",
                threshold="Supported if ρ < −0.4; Mixed if −0.4 ≤ ρ < 0; Not supported if ρ ≥ 0",
                inputs=("caged_net_hires", "unemployment_rate"), chart="l2")
    cg, un = _s(silver, "caged_net_hires"), _s(silver, "unemployment_rate")
    if _missing(cg, un):
        return _row(**meta)
    c = cg.resample("MS").last().rolling(12).mean()
    u = un.resample("MS").last()
    df = pd.concat([c.rename("c"), (u.shift(-12) - u).rename("du")], axis=1)
    df = df[df.index >= "2021-01-01"].dropna()
    if len(df) < 18:
        return _row(**meta)
    rho = df.c.corr(df.du)
    verdict = "Supported" if rho < -0.4 else ("Mixed" if rho < 0 else "Not supported")
    why = f"ρ {rho:+.2f} {'beyond' if rho < -0.4 else 'not beyond'} −0.4"
    ev = (f"ρ = {rho:+.2f} over {len(df)} months; latest CAGED {cg.iloc[-1] / 1000:+.0f}k jobs "
          f"({cg.index[-1]:%b %Y}), unemployment {un.iloc[-1]:.1f}%")
    return _row(**meta, stat=rho, verdict=verdict, evidence=ev, as_of=f"{cg.index[-1]:%Y-%m-%d}", why=why)


def l3_r_minus_g(silver):
    meta = dict(hid="L3", group="Public finances",
                title="Interest outruns growth on public debt",
                question="Is the government paying more interest than the economy grows?",
                claim="The implicit interest rate on public debt exceeds nominal GDP growth by more than "
                      "3 points, so debt/GDP rises even with a balanced primary budget.",
                test="r = the public sector's net interest bill over 12 months (BCB fiscal data) ÷ gross "
                     "government debt a year earlier, both in reais; g = 12-month nominal GDP growth. "
                     "Nominal, so not the same number as the real-rate spread in the 2012-book section.",
                threshold="Supported if r − g > 3 pts; Mixed if 0 < r − g ≤ 3; Not supported if ≤ 0",
                inputs=("interest_bill_gdp", "gross_public_debt_gdp", "gdp_nominal_12m_brl"),
                chart="l3")
    rg = _s(silver, "r_minus_g")
    if _missing(rg):
        return _row(**meta)
    r, g = _s(silver, "implicit_interest_rate"), _s(silver, "nominal_gdp_growth")
    last = rg.iloc[-1]
    verdict = "Supported" if last > 3 else ("Mixed" if last > 0 else "Not supported")
    why = f"r − g {last:+.1f} pts {'above' if last > 3 else 'at or below'} 3"
    ev = (f"{rg.index[-1]:%b %Y}: interest rate on debt {r.iloc[-1]:.1f}% vs nominal growth "
          f"{g.loc[rg.index[-1]]:.1f}% → r − g = {last:+.1f} pts")
    return _row(**meta, stat=last, verdict=verdict, evidence=ev, as_of=f"{rg.index[-1]:%Y-%m-%d}", why=why)


def l4_trade_pivot(silver):
    meta = dict(hid="L4", group="Trade",
                title="Exports pivot from the US to China",
                question="Since the 2025 US tariffs, has Brazil sold less to America and more to China?",
                claim="Over the last 12 months, exports to the US fell while exports to China rose, "
                      "versus the prior 12 months.",
                test="Sum of monthly FOB exports, last 12 months vs the 12 before, by destination.",
                threshold="Supported if US change < 0 and China change > 0; Mixed if one holds",
                inputs=("exports_to_us", "exports_to_china", "exports_to_eu"), chart="l4")
    us, cn = _s(silver, "exports_to_us"), _s(silver, "exports_to_china")
    if _missing(us, cn):
        return _row(**meta)
    end = min(us.index[-1], cn.index[-1])

    def chg(s):
        s = s.loc[:end]
        return (s.iloc[-12:].sum() / s.iloc[-24:-12].sum() - 1) * 100

    cu, cc = chg(us), chg(cn)
    eu = _s(silver, "exports_to_eu")
    verdict = "Supported" if cu < 0 < cc else ("Mixed" if cu < 0 or cc > 0 else "Not supported")
    why = f"US {cu:+.1f}% ({'fell' if cu < 0 else 'rose'}); China {cc:+.1f}% ({'rose' if cc > 0 else 'fell'})"
    ev = (f"12 months to {end:%b %Y} vs prior 12: US {cu:+.1f}%, China {cc:+.1f}%"
          + (f", EU {chg(eu):+.1f}%" if eu is not None else ""))
    return _row(**meta, stat=min(-cu, cc), verdict=verdict, evidence=ev, as_of=f"{end:%Y-%m-%d}", why=why)


# How each statistic is drawn on the result scale: label, threshold, direction that
# passes, axis range, unit. Compound conditions are spelled out in `threshold`.
GAUGE = {
    "H1": ("R² from Brent alone", 0.70, ">=", 0.0, 1.0, ""),
    "H2": ("Oil export tonnes, trend", 5.0, ">=", -5.0, 15.0, "%/yr"),
    "H3": ("Correlation ρ, revenue vs ore price", 0.70, ">", -1.0, 1.0, ""),
    "H4": ("Power cost, low vs normal storage", 2.0, ">", 0.0, 5.0, "×"),
    "H5": ("Better of the two minus Ibovespa", 0.0, "<", -300.0, 300.0, "US$"),
    "H6": ("Suzano ρ with a weaker real", 0.35, ">", -1.0, 1.0, ""),
    "L1": ("Correlation ρ", -0.30, "<", -1.0, 1.0, ""),
    "L2": ("Correlation ρ", -0.40, "<", -1.0, 1.0, ""),
    "L3": ("r − g", 3.0, ">", -6.0, 10.0, "pts"),
    "L4": ("Smaller of US fall, China rise", 0.0, ">", -40.0, 40.0, "%"),
}

TESTS = [h1_petrobras_price_not_volume, h2_oil_volume_iron_flat, h3_vale_china_price,
         h4_hydro_stress_axia, h5_resource_champions_tr, h6_suzano_brl_hedge,
         l1_debt_service_retail, l2_caged_leads_pnad, l3_r_minus_g, l4_trade_pivot]


def build_hypothesis_tests(silver) -> pd.DataFrame:
    rows = []
    for t in TESTS:
        # Missing inputs already degrade to "Insufficient data" inside each test; any
        # other exception is a bug and should fail the build loudly.
        rows.append(t(silver))
    out = pd.DataFrame(rows)
    g = out.hyp_id.map(GAUGE)
    for i, col in enumerate(["stat_label", "threshold_value", "threshold_dir", "axis_lo",
                             "axis_hi", "stat_unit"]):
        out[col] = g.map(lambda t: t[i])
    return out
