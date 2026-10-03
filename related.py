"""related.py — the related-datasets graph behind the "Related datasets" panel.

For every series, a short ranked list of other series worth looking at next, each with a
reason and a one-line explanation. Edges (strongest first):

  same_concept   the same statistic from another source (gold/reconciliation)
  lineage        a derived series and its inputs ("Built from" / "Feeds into")
  company        commodity / sector series <-> the companies exposed to it (curated rules)
  entity         other headline metrics of the same company
  curated        series shown together on a curated Brazil Monitoring chart
  comove         Brazilian monthly series whose year-on-year changes move together
  family         same World Bank / ILO indicator family (sex, age, unit variants)
  text           similar title + description within the same topic (fallback)

Output: gold/related_series (series_id, related_id, reason, score, explanation), loaded
into DuckDB as `related_series` with the view `v_related`; portal.py ships it to the site.
Run:  python3 related.py   (pipeline.py calls it after catalog.py)
"""
from __future__ import annotations
import math, pathlib, re
from collections import defaultdict
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
GOLD = ROOT / "warehouse" / "gold"
TOP_K = 10
CAPS = {"same_concept": 3, "lineage": 4, "company": 3, "entity": 3, "curated": 3, "comove": 3, "family": 2, "text": 3,
        "neighbor": 4}
WEIGHT = {"same_concept": 1.0, "lineage": 0.95, "company": 0.8, "curated": 0.7, "comove": 0.65,
          "entity": 0.6, "family": 0.5, "text": 0.35, "neighbor": 0.25}
COMPANIES = ["PETR", "VALE", "AXIA", "SUZB", "PRIO", "ITUB"]
CO_NAME = {"PETR": "Petrobras", "VALE": "Vale", "AXIA": "Axia", "SUZB": "Suzano", "PRIO": "PRIO", "ITUB": "Itaú"}
HEADLINE = ["revenue_usd_bn", "total_return_usd", "net_income_usd_bn", "operated_oil_production_kbd",
            "generation_share_sin"]

# derived series -> inputs (mirrors pipeline.derive_native_series and hypotheses.derive_company_series)
LINEAGE = {
    "trade_balance": ["exports_total", "imports_total"],
    "china_export_share": ["exports_to_china", "exports_total"],
    "primary_balance_gdp": ["primary_result_nfsp"],
    "interest_bill_gdp": ["nominal_deficit_gdp", "primary_result_nfsp"],
    "household_credit_growth": ["household_credit_balance"],
    "corporate_credit_growth": ["corporate_credit_balance"],
    "real_wage_bill": ["employed_population", "real_average_income"],
    "hydro_stress_index": ["stored_energy_ear", "thermal_generation_share"],
    "fertilizer_dependency_index": ["fertilizer_imports", "soy_exports", "beef_exports", "coffee_exports", "sugar_exports"],
    "potash_import_dependency_proxy": ["potash_imports", "fertilizer_imports"],
    "ibovespa_usd": ["ibovespa_level", "brl_usd"],
    "oil_production_yoy": ["oil_production"],
    "oil_export_unit_value": ["oil_exports", "oil_exports_kg"],
    "iron_ore_unit_value": ["iron_ore_exports", "iron_ore_exports_kg"],
    "pulp_unit_value": ["pulp_exports", "pulp_exports_kg"],
    "implicit_interest_rate": ["interest_bill_gdp", "gross_public_debt_gdp", "gdp_nominal_12m_brl"],
    "real_policy_rate": ["selic_target", "focus_ipca_12m"],
    "nominal_gdp_growth": ["gdp_nominal_12m_brl"],
    "r_minus_g": ["implicit_interest_rate", "nominal_gdp_growth"],
    "total_return_usd@IBOV": ["ibovespa_level", "brl_usd"],
    "total_return_brl@IBOV": ["ibovespa_level"],
}
for _e in COMPANIES:
    LINEAGE |= {
        f"revenue_usd_bn@{_e}": [f"revenue_brl@{_e}", "brl_usd"],
        f"net_income_usd_bn@{_e}": [f"net_income_brl@{_e}", "brl_usd"],
        f"net_debt_brl_bn@{_e}": [f"gross_debt_brl@{_e}", f"cash_brl@{_e}"],
        f"total_return_brl@{_e}": [f"share_close_adj_brl@{_e}", f"dividend_per_share_brl@{_e}"],
        f"total_return_usd@{_e}": [f"share_close_adj_brl@{_e}", f"dividend_per_share_brl@{_e}", "brl_usd"],
        f"dividend_yield_ttm@{_e}": [f"dividend_per_share_brl@{_e}", f"share_close_adj_brl@{_e}"],
    }

# commodity / sector exposure -> companies (labelled as exposure, not causality)
EXPOSURE = {
    "oil": (["PETR", "PRIO"], ["oil_production", "oil_production_offshore_kbd", "presalt_share", "brent_usd",
                              "oil_exports", "oil_exports_kg", "oil_export_unit_value", "gas_production_mm3d"]),
    "iron ore and China": (["VALE"], ["iron_ore_exports", "iron_ore_exports_kg", "iron_ore_unit_value", "china_export_share",
                                      "exports_to_china"]),
    "pulp": (["SUZB"], ["pulp_exports", "pulp_exports_kg", "pulp_unit_value"]),
    "the real": (["SUZB", "VALE"], ["brl_usd", "focus_fx"]),
    "power and reservoirs": (["AXIA"], ["stored_energy_ear", "cmo_power_cost", "hydro_generation_share",
                                       "electricity_load", "hydro_stress_index", "thermal_generation_share"]),
    "rates and credit": (["ITUB"], ["selic_target", "focus_selic_12m", "credit_gdp", "delinquency_rate",
                                   "household_credit_balance", "household_debt_service_ratio"]),
}

_STOP = set("of the and in to for by a an as at on per total rate annual current constant brazil percent "
            "value index share population people number ratio".split())


def _toks(t: str) -> list:
    return [w for w in re.findall(r"[a-z]{3,}", str(t).lower()) if w not in _STOP]


def build(cat: pd.DataFrame, obs: pd.DataFrame, rec: pd.DataFrame, curated: list | None = None) -> pd.DataFrame:
    have = set(cat.series_id)
    info = cat.set_index("series_id")
    title = info.title.astype(str)
    edges = []  # (a, b, reason, strength 0-1, explanation)

    def add(a, b, reason, strength, expl):
        if a in have and b in have and a != b:
            edges.append((a, b, reason, float(strength), expl))

    # same concept (reconciliation, both directions)
    for r in rec.itertuples():
        diff = getattr(r, "median_rel_diff_pct", None)
        agree = f" · within {diff:.1f}%" if diff is not None and not pd.isna(diff) else ""
        add(r.canonical, r.alternate, "same_concept", 1, f"Same statistic, {info.source.get(r.alternate, '')}{agree}")
        add(r.alternate, r.canonical, "same_concept", 1, f"Same statistic, {info.source.get(r.canonical, '')}{agree}")

    # lineage
    for d, ins in LINEAGE.items():
        for i in ins:
            add(d, i, "lineage", 1, "Input to this series")
            add(i, d, "lineage", 0.9, "Built from this series")
        # inputs of the same derived series belong together (e.g. export value + tonnes -> price)
        for i in ins:
            for j in ins:
                if i != j and "@" not in d:
                    add(i, j, "lineage", 0.85, f"Used together in: {title.get(d, d)}")

    # company exposure
    for label, (cos, series) in EXPOSURE.items():
        for co in cos:
            heads = [f"{m}@{co}" for m in HEADLINE if f"{m}@{co}" in have][:3]
            for s in series:
                for h in heads:
                    add(s, h, "company", 1 if h.startswith(("revenue", "operated", "generation")) else 0.85,
                        f"{CO_NAME[co]} is exposed to {label}")
                    add(h, s, "company", 0.9, f"Driver: {label}")

    # same entity (company headline metrics)
    for co in COMPANIES:
        ids = [x for x in have if x.endswith("@" + co)]
        heads = [f"{m}@{co}" for m in HEADLINE if f"{m}@{co}" in have]
        for a in ids:
            for h in heads:
                add(a, h, "entity", 0.8, f"Same company: {CO_NAME[co]}")

    # curated co-membership
    for c in curated or []:
        for ch in c.get("charts", []):
            ss = [x for x in ch["s"] if x in have]
            for a in ss:
                for b in ss:
                    add(a, b, "curated", 0.9, f"Charted together: {ch['t']}")

    topic = info.topic.astype(str)
    # co-movement among monthly Brazilian series (YoY of monthly means, n>=36, |rho|>=0.7)
    nat = cat[(cat.ns == "native") & cat.freq.isin(["daily", "weekly", "monthly"]) & (cat.entity_id == "BR")].series_id
    o = obs[obs.series_id.isin(set(nat))]
    if not o.empty:
        m = (o.assign(k=pd.to_datetime(o.date).dt.to_period("M")).groupby(["k", "series_id"]).value.mean()
             .unstack().sort_index())
        m = m[m.index >= pd.Period("2005-01", "M")]
        with np.errstate(all="ignore"):
            yoy = m.pct_change(12, fill_method=None).replace([np.inf, -np.inf], np.nan)
        cols = list(yoy.columns)
        V = yoy.to_numpy()
        for i, a in enumerate(cols):
            x = V[:, i]
            for j in range(i + 1, len(cols)):
                y = V[:, j]
                ok = ~np.isnan(x) & ~np.isnan(y)
                n = int(ok.sum())
                if n < 120 or topic.get(a) != topic.get(cols[j]):  # >= 10 years, same topic: no spurious links
                    continue
                r = float(np.corrcoef(x[ok], y[ok])[0, 1])
                if abs(r) >= 0.7:
                    yrs = f"{yoy.index[ok][0].year}–{yoy.index[ok][-1].year}"
                    e = f"Moves {'with' if r > 0 else 'against'} this series (ρ={r:+.2f}, {yrs}, yearly change)"
                    add(a, cols[j], "comove", min(1, abs(r)), e)
                    add(cols[j], a, "comove", min(1, abs(r)), e)

    # indicator family (World Bank: first 3 code parts; ILO: indicator stem before _SEX/_AGE)
    intl = cat[cat.ns != "native"]
    fam = intl.series_id.str.replace(r"^wb/([^.]+\.[^.]+\.[^.]+).*$", r"wb/\1", regex=True) \
        .str.replace(r"^(ilostat/[A-Z0-9]+_[A-Z0-9]+)_.*$", r"\1", regex=True)
    rank = info["rank"].astype(float)
    for f, grp in intl.groupby(fam.to_numpy()):
        ids = list(grp.series_id)
        if 1 < len(ids) <= 60:
            best = sorted(ids, key=lambda x: -rank.get(x, 0))[:4]
            for a in ids:
                for b in best:
                    add(a, b, "family", 0.8, "Same indicator family")

    # text similarity within topic (idf-weighted token overlap), fallback only
    docs = {sid: set(_toks(f"{t} {d}")) for sid, t, d in zip(cat.series_id, cat.title, cat.description.fillna(""))}
    df = defaultdict(int)
    for toks in docs.values():
        for t in toks:
            df[t] += 1
    N = len(docs)
    idf = {t: math.log(N / (1 + c)) for t, c in df.items()}
    topic = info.topic.astype(str)
    by_topic_tok = defaultdict(lambda: defaultdict(set))
    for sid, toks in docs.items():
        for t in toks:
            if df[t] < 400:  # very common words carry no signal
                by_topic_tok[topic.get(sid)][t].add(sid)
    for sid, toks in docs.items():
        tp = topic.get(sid)
        scores = defaultdict(float)
        for t in toks:
            for other in by_topic_tok[tp].get(t, ()):
                if other != sid:
                    scores[other] += idf[t]
        if not scores:
            continue
        norm_a = math.sqrt(sum(idf.get(t, 0) ** 2 for t in toks)) or 1
        best = []
        for other, sc in scores.items():
            norm_b = math.sqrt(sum(idf.get(t, 0) ** 2 for t in docs[other])) or 1
            cos = sc / (norm_a * norm_b)
            if cos >= 0.35:
                best.append((cos, other))
        for cos, other in sorted(best, reverse=True)[:4]:
            add(sid, other, "text", cos, "Similar description")

    # fallback: series with few links get the best-ranked neighbours from the same dataset + topic
    cnt = defaultdict(int)
    for a, *_ in edges:
        cnt[a] += 1
    dsn = info["dataset"].astype(str)
    grp = cat.assign(_ds=cat.series_id.map(dsn), _tp=cat.series_id.map(topic)).sort_values("rank", ascending=False)
    for (_, _), g in grp.groupby(["_ds", "_tp"], sort=False):
        top = list(g.series_id[:6])
        for sid in g.series_id:
            if cnt[sid] >= 3:
                continue
            for o in [x for x in top if x != sid][:4]:
                add(sid, o, "neighbor", 0.8, f"Same dataset & topic: {dsn.get(o, '')}")
    # last resort: a series alone in its dataset + topic gets the top-ranked series of its topic
    linked = {e[0] for e in edges}
    for _, g in grp.groupby("_tp", sort=False):
        top = list(g.series_id[:5])
        for sid in g.series_id:
            if sid not in linked:
                for o in [x for x in top if x != sid][:4]:
                    add(sid, o, "neighbor", 0.6, f"Same topic: {topic.get(o, '')}")

    E = pd.DataFrame(edges, columns=["series_id", "related_id", "reason", "strength", "explanation"])
    if E.empty:
        return pd.DataFrame(columns=["series_id", "related_id", "reason", "score", "explanation", "pos"])
    # one edge per pair: keep the strongest reason
    E["w"] = E.reason.map(WEIGHT) * E.strength
    E = E.sort_values("w", ascending=False).drop_duplicates(["series_id", "related_id"])
    rmax = max(rank.max(), 1e-9)
    quality = 0.6 + 0.4 * E.related_id.map(rank).fillna(0) / rmax
    stale = E.related_id.map(info.status).eq("stale")
    E["score"] = (E.w * quality * np.where(stale, 0.85, 1.0)).round(4)
    # greedy top-K with caps per reason and at most 5 from one dataset
    ds = info["dataset"].astype(str)
    out = []
    for sid, g in E.sort_values("score", ascending=False).groupby("series_id", sort=False):
        used, per_ds, k = defaultdict(int), defaultdict(int), 0
        for r in g.itertuples():
            if used[r.reason] >= CAPS[r.reason] or per_ds[ds.get(r.related_id)] >= 5:
                continue
            used[r.reason] += 1
            per_ds[ds.get(r.related_id)] += 1
            out.append((sid, r.related_id, r.reason, r.score, r.explanation, k))
            k += 1
            if k >= TOP_K:
                break
    return pd.DataFrame(out, columns=["series_id", "related_id", "reason", "score", "explanation", "pos"])


def main():
    import importlib.util, sys
    sys.path.insert(0, str(ROOT))
    from portal import CURATED  # noqa: E402 — curated chart co-membership
    cat = pd.read_parquet(GOLD / "catalog.parquet")
    obs = pd.read_parquet(GOLD / "observations.parquet")
    rec = pd.read_parquet(GOLD / "reconciliation.parquet")
    rel = build(cat, obs, rec, CURATED)
    rel.to_parquet(GOLD / "related_series.parquet", index=False)
    cov = rel.series_id.nunique()
    print(f"related: {len(rel):,} edges for {cov:,} of {len(cat):,} series; by reason: "
          f"{rel.reason.value_counts().to_dict()}")
    return rel


if __name__ == "__main__":
    main()
