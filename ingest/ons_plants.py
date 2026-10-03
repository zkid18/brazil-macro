"""ons_plants.py — ONS weekly CMO + plant-level generation x ownership (H4).

Sources (ONS open-data S3 bucket, CKAN portal dados.ons.org.br; no auth):

1. CMO semanal (Decomp marginal operating cost), one CSV per year since 2005:
     https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/cmo_se/CMO_SEMANAL_{yyyy}.csv
   `;`-separated, columns id_subsistema;nom_subsistema;din_instante;
   val_cmomediasemanal;val_cmoleve;val_cmomedia;val_cmopesada. Weekly (Friday
   operating-week dates) for N/NE/S/SE since 2005 (not only since 2012).
   We take id_subsistema == "SE" (Sudeste/Centro-Oeste, the price-setting
   subsystem) and `val_cmomediasemanal` = the load-weighted weekly average across
   the three patamares (leve/média/pesada). NB `val_cmomedia` is the "média"
   *load level*, not the average — we do not use it. CMO is not PLD (PLD is CMO
   clamped to ANEEL floor/cap; CCEE open data returns 403).

2. Hourly generation per plant ("Geração por Usina em Base Horária", package
   geracao-usina-2). Naming verified via CKAN package_show today:
     annual  .../geracao_usina_2_ho/GERACAO_USINA-2_{YYYY}.parquet     2000-2021 (25-47 MB)
     monthly .../geracao_usina_2_ho/GERACAO_USINA-2_{YYYY}_{MM}.parquet 2022-01 onward (~4.5 MB)
   Columns din_instante, ceg, nom_tipousina, cod_modalidadeoperacao, val_geracao
   (MWmed in the interval -> MWh per hour). Each file is aggregated to
   plant(ceg)-month GWh immediately; the aggregate is cached in
   warehouse/bronze/raw/ons_gu_agg/ and the raw parquet is deleted.
   Partial months (the in-progress month) are dropped.
   ~41 % of SIN generation has ceg "-": wind/solar "Conjunto de Usinas",
   "Pequenas Usinas" (Tipo III) and MMGD (distributed solar). These count in the
   SIN total but have no owner — none are Axia/Petrobras-scale assets.

3. Ownership snapshot: .../capacidade-geracao/CAPACIDADE_GERACAO.parquet
   (unit-level, nom_agenteproprietario, ceg). Joined on ceg; where one ceg has
   units of several owners (14 cegs), generation is split pro rata by
   val_potenciaefetiva.

Group definitions (owner-name based, current snapshot):
  AXIA = owners starting "AXIA" (AXIA ENERGIA = ex-Furnas, AXIA NORDESTE = ex-Chesf,
         AXIA NORTE = ex-Eletronorte, AXIA SUL = ex-CGT Eletrosul, AXIA SANTO
         ANTONIO, AXIA TELES PIRES) + legacy names FURNAS/CHESF/ELETRONORTE/
         ELETROSUL/ELETROBRAS. EXCLUDED: ELETRONUCLEAR (Angra; control moved to
         ENBPar at the 2022 privatisation, Axia keeps a minority equity stake —
         ~1.25 TWh/month, i.e. ~2 pp of share), ITAIPU (binational, moved to
         ENBPar 2022) and NORTE ENERGIA (Belo Monte; equity-accounted minority).
  PETR = owner "PETROBRAS" (its 14 thermal plants, ~5.1 GW).
Limitation: ownership is today's snapshot applied to all history. Santo Antônio
and Teles Pires were consolidated by Eletrobras only in 2022-23, and Petrobras
sold some thermal stakes over 2016-2021, so pre-2023 AXIA and pre-2021 PETR
volumes reflect today's perimeter, not the perimeter at the time.

Sanity check (2026-10-03): Sep-2026 SIN 59.30 TWh; AXIA 8.09 TWh = 13.64 %
(probe 8.06 TWh / 13.6 %; without the pro-rata split, i.e. whole multi-owner
cegs to the first owner, it is 8.15 TWh); PETR 0.708 TWh = 1.19 % (probe 0.71).
Annual AXIA share 17-23 %, PETR 0.8-4.7 % (peaks in 2017/2021 drought years).
CMO SE 2026-10-02 = R$ 42.43/MWh (matches probe); 2021 crisis peak R$ 3,044,
2023 ~0 (wet year) — consistent with history.

SIN denominator: the monthly plant sum (incl. MMGD) matches ons_energy's daily
`electricity_generation_by_source` (MWmed x 24, summed by month) within 0.2 %
every January 2016-2026, so no separate sin_generation_gwh series is written
(it would duplicate); the denominator is computed internally from the same files.

Outputs:
  bronze/native/cmo_power_cost.csv              weekly  brl_per_mwh
  bronze/companies/generation_gwh.csv           monthly gwh, entity AXIA, PETR
  bronze/companies/generation_share_sin.csv     monthly pct of SIN plant-sum generation

Run:  .venv/bin/python ingest/ons_plants.py   (first run ~450 MB of downloads)
"""
from __future__ import annotations
import io, sys, pathlib, datetime as dt
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_bytes, cached, write_bronze, NATIVE, COMPANIES, RAW_CACHE  # noqa: E402

S3 = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset"
CMO = S3 + "/cmo_se/CMO_SEMANAL_{y}.csv"
GU_YEAR = S3 + "/geracao_usina_2_ho/GERACAO_USINA-2_{y}.parquet"
GU_MONTH = S3 + "/geracao_usina_2_ho/GERACAO_USINA-2_{y}_{m:02d}.parquet"
CAP = S3 + "/capacidade-geracao/CAPACIDADE_GERACAO.parquet"
CMO_START, GEN_START, MONTHLY_FROM = 2005, 2016, 2022
AGG_DIR = RAW_CACHE / "ons_gu_agg"
SRC = "ons"

AXIA_PREFIX = ("AXIA",)
AXIA_LEGACY = {"FURNAS", "CHESF", "ELETRONORTE", "ELETROSUL", "CGT ELETROSUL", "ELETROBRAS"}
GROUPS = {"AXIA": lambda o: o.startswith(AXIA_PREFIX) or o in AXIA_LEGACY,
          "PETR": lambda o: o == "PETROBRAS"}


def num(col):
    return pd.to_numeric(col.astype(str).str.replace(",", ".", regex=False), errors="coerce")


# ---------------------------------------------------------------- CMO
def cmo_series() -> pd.DataFrame:
    frames = []
    for y in range(CMO_START, dt.date.today().year + 1):
        try:
            raw = get_bytes(CMO.format(y=y))
        except Exception as e:  # noqa: BLE001
            print(f"  [skip] CMO {y}: {e}")
            continue
        frames.append(pd.read_csv(io.BytesIO(raw), sep=";", dtype=str))
    c = pd.concat(frames, ignore_index=True)
    c = c[c.id_subsistema.str.strip() == "SE"]
    out = pd.DataFrame({"date": pd.to_datetime(c.din_instante), "value": num(c.val_cmomediasemanal)})
    out = out.dropna().drop_duplicates("date", keep="last")
    return out.assign(metric_id="cmo_power_cost",
                      metric_name="Marginal operating cost (CMO), SE/CO weekly average",
                      theme="energy_water", source_id=SRC, freq="weekly", unit="brl_per_mwh")


# ---------------------------------------------------------------- generation
def aggregate(path: pathlib.Path) -> pd.DataFrame:
    """Raw hourly parquet -> ceg x month GWh (+ hours coverage)."""
    g = pd.read_parquet(path, columns=["din_instante", "ceg", "val_geracao"])
    g["din_instante"] = pd.to_datetime(g.din_instante)
    g["val_geracao"] = g.val_geracao if pd.api.types.is_float_dtype(g.val_geracao) else num(g.val_geracao)
    ts = pd.Series(g.din_instante.unique()).sort_values()
    step_h = ts.diff().median() / pd.Timedelta(hours=1) if len(ts) > 1 else 1.0
    g["month"] = g.din_instante.dt.to_period("M").dt.to_timestamp()
    g["ceg"] = g.ceg.astype(str).str.strip()
    agg = g.groupby(["month", "ceg"], as_index=False).val_geracao.sum()
    agg["gwh"] = agg.val_geracao * step_h / 1e3
    last = g.groupby("month").din_instante.max().rename("last_ts").reset_index()
    return agg.drop(columns="val_geracao").merge(last, on="month")


def files():
    today = dt.date.today()
    for y in range(GEN_START, MONTHLY_FROM):
        yield f"{y}", GU_YEAR.format(y=y), False
    for y in range(MONTHLY_FROM, today.year + 1):
        for m in range(1, 13):
            if (y, m) > (today.year, today.month):
                break
            recent = (today.year * 12 + today.month) - (y * 12 + m) <= 1  # refresh last 2 files
            yield f"{y}_{m:02d}", GU_MONTH.format(y=y, m=m), recent


def plant_months() -> pd.DataFrame:
    AGG_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for key, url, refresh in files():
        agg_p = AGG_DIR / f"gu_{key}.parquet"
        if agg_p.exists() and not refresh:
            frames.append(pd.read_parquet(agg_p))
            continue
        name = f"GERACAO_USINA-2_{key}.parquet"
        try:
            raw = cached(url, name, max_age_days=0 if refresh else None, timeout=300)
        except Exception as e:  # noqa: BLE001
            print(f"  [skip] {name}: {e}")
            continue
        agg = aggregate(raw)
        agg.to_parquet(agg_p, index=False)
        raw.unlink()  # raw hourly no longer needed
        print(f"  [gen]  {key}: {len(agg)} plant-months, {agg.gwh.sum():,.0f} GWh")
        frames.append(agg)
    pm = pd.concat(frames, ignore_index=True)
    pm = pm.groupby(["month", "ceg"], as_index=False).agg(gwh=("gwh", "sum"), last_ts=("last_ts", "max"))
    # drop incomplete months (data must reach the last day of the month)
    month_last = pm.groupby("month").last_ts.max()
    complete = month_last[month_last.dt.normalize() >= (month_last.index + pd.offsets.MonthEnd(0))].index
    return pm[pm.month.isin(complete)].drop(columns="last_ts")


def ownership() -> pd.DataFrame:
    """ceg -> (group, weight) with pro-rata capacity split for multi-owner cegs."""
    c = pd.read_parquet(cached(CAP, "CAPACIDADE_GERACAO.parquet", max_age_days=7),
                        columns=["ceg", "nom_agenteproprietario", "val_potenciaefetiva"])
    c["ceg"] = c.ceg.astype(str).str.strip()
    c["own"] = c.nom_agenteproprietario.astype(str).str.strip().str.upper()
    c["mw"] = num(c.val_potenciaefetiva).fillna(0)
    w = c.groupby(["ceg", "own"]).mw.sum().reset_index()
    tot = w.groupby("ceg").mw.transform("sum")
    n = w.groupby("ceg").own.transform("count")
    w["weight"] = (w.mw / tot).where(tot > 0, 1 / n)
    w["group"] = None
    for gid, f in GROUPS.items():
        w.loc[w.own.map(f), "group"] = gid
    return w.dropna(subset=["group"])[["ceg", "group", "weight"]]


def main():
    print("ONS CMO semanal…")
    cmo = cmo_series()
    n = write_bronze(cmo, NATIVE / "cmo_power_cost.csv")
    last = cmo.sort_values("date").iloc[-1]
    print(f"[ok]   cmo_power_cost  {n} obs ({cmo.date.min():%Y-%m-%d}..{cmo.date.max():%Y-%m-%d}) "
          f"latest {last.value:.2f} brl_per_mwh")

    print("ONS plant generation (aggregating per file)…")
    pm = plant_months()
    own = ownership()
    sin = pm.groupby("month").gwh.sum()
    j = pm.merge(own, on="ceg")
    grp = (j.gwh * j.weight).groupby([j.group, j.month]).sum().rename("gwh").reset_index()

    print(f"  SIN (plant sum) latest {sin.index[-1]:%Y-%m}: {sin.iloc[-1]:,.0f} GWh")
    base = dict(source_id=SRC, freq="monthly")
    gen_df = pd.DataFrame({"date": grp.month, "value": grp.gwh.round(3), "entity_id": grp.group,
                           "metric_id": "generation_gwh",
                           "metric_name": "Electricity generation, owned plants (ONS)",
                           "theme": "companies", "unit": "gwh", **base})
    shr_df = gen_df.assign(value=(grp.gwh / grp.month.map(sin) * 100).round(4).values,
                           metric_id="generation_share_sin",
                           metric_name="Share of SIN generation, owned plants (ONS)", unit="pct")

    for df, path in [(gen_df, COMPANIES / "generation_gwh.csv"),
                     (shr_df, COMPANIES / "generation_share_sin.csv")]:
        write_bronze(df, path, entity=True)
        for e, d in df.groupby("entity_id"):
            d = d.sort_values("date")
            print(f"[ok]   {d.metric_id.iloc[0]:<22} {e:<4} {len(d)} obs "
                  f"({d.date.min():%Y-%m}..{d.date.max():%Y-%m}) latest {d.value.iloc[-1]:,.2f} {d.unit.iloc[0]}")


if __name__ == "__main__":
    main()
