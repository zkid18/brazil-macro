"""anp_production.py — Tier-2 native adapter: ANP oil & gas production open data.

Sources (all gov.br/anp "dados abertos"; gov.br is slow — long timeouts, GET
only (HEAD -> 403), every download goes through `cached()` into bronze/raw/):

A. National by state x location (TERRA/MAR), monthly, 1997 -> latest:
   .../dados-abertos/arquivos/ppgn-el/producao-petroleo-m3.csv        (m³/month)
   .../dados-abertos/arquivos/ppgn-el/producao-gas-natural-1000m3.csv (10³ m³/month)
   `;` separated, BOM, decimal comma, months as JAN..DEZ. Months not yet
   published are present as 0 -> dropped (national total must be > 0).
   -> oil_production_offshore_kbd = MAR m³ / days / 0.158987 / 1000   (kb/d)
   -> gas_production_mm3d         = (MAR+TERRA) 10³m³ / days / 1000    (MMm³/d)

B. Per-well production WITH operator and ANP's own pre-salt split, 2016-2023:
   page .../dados-abertos/producao-de-petroleo-e-gas-natural-por-poco lists
   annual zips (producao-por-poco-2016..2020.zip) and monthly zips for
   2021-2023 (inconsistent names: 2021_01_producao.zip, 2021-08-producao.zip,
   2022/producao-2022-01.zip, 2022/2022_05_producao.zip, 2023/producao-01.zip)
   — links are discovered from the page, not hard-coded. Each zip holds
   *_mar.csv, *_presal.csv (subset of mar: wells producing from pre-salt
   reservoirs, ANP classification) and *_terra.csv (not used).
   Headers drift (2016-2019 have a 4-line SIGEP preamble and a 2-row header;
   encoding is utf-8 in some years, latin-1 in 2023), so we parse positionally:
   find the header row with Campo/Operador/Período/"Petróleo (bbl/dia)",
   column 2 = ANP well name, keep rows whose Período is YYYY/MM.
   Petróleo (= óleo + condensado) in bbl/day (monthly average).
   The page publishes nothing after Dec-2023.

C. Per-well offshore production 2024 -> latest (no operator, no pre-sal flag):
   .../arquivos-producao-de-petroleo-e-gas-natural-nacional/pm/producao-mar-YYYY.csv
   (2024 is named pm/producao_por_poco_2024.csv; links discovered from the
   .../dados-abertos/fase-de-desenvolvimento-e-producao page). `,` separated,
   `[Col]` headers, decimal comma, '.' thousands, m³ per month.
   2023 is also downloaded, only to validate the method below against B.

D. Field register WITH current operator (as-of snapshot, today):
   .../arquivos-fase-de-desenvolvimento-e-producao/informacoes-sobre-campos/extracao-campo.csv
   (CAMPO, OPERADOR, ...). Used for 2024+ operator attribution.

Derived series
  presalt_share (pct, monthly 2016+): pre-salt Petróleo / national Petróleo (A).
    2016-2023: ANP *_presal.csv files (official flag).
    2024+: well-level carry-forward — a well in C counts as pre-salt if it ever
    appeared in a B pre-salt file; wells first seen after 2023 inherit their
    field's 2023 classification (pre-salt if >50% of the field's 2023 output
    was pre-salt). Validated on 2023 (C-method vs official B) — printed at run.
  operated_oil_production_kbd (companies/, entity PETR / PRIO, kbd, monthly):
    OFFSHORE oil operated (gross, 100% of field, NOT equity) — onshore is
    excluded throughout for consistency (2024+ onshore files lag offshore by a
    quarter; Petrobras onshore was ~22 kb/d in Dec-23, <1% of its operated).
    2016-2023: Operador column of B (per well, per month).
    2024+: field operator = Dec-2023 operator from B, overridden by D (current
    register) where they differ — i.e. operator changes during 2024-26 are
    applied to the whole 2024+ period (see OPERATOR_CHANGES printed at run).
    PRIO name variants matched: PetroRio*, Petro Rio *, Prio * (Jaguar, Bravo,
    Forte, Tigris). Petrobras: "Petrobras" / "PETROBRAS".

Verified 2026-10-03: A has data to Aug-26 (MAR oil 720,079 m³/d = 4,529 kb/d;
gas 215.0 MMm³/d in Jul-26, which matches IPEAData ANP12_PDGASN12 1.352 Mboe/d
x 158.987). Dec-23 per-well (B): Mar 3,505 kb/d, of which pre-sal 2,743 kb/d;
Petrobras operated 3,109 kb/d offshore. Cross-check vs IPEAData oil_production
(which is crude+condensate+LGN): ANP oil + producao-lgn-m3.csv matches it to
<0.03% every month 2012-2026; oil alone is 2-5% lower — expected.
Run:  python3 ingest/anp_production.py
"""
from __future__ import annotations
import sys, io, re, csv, zipfile, calendar, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import cached, write_bronze, NATIVE, COMPANIES  # noqa: E402
import pandas as pd  # noqa: E402

BBL = 0.158987  # m³ per barrel
GOV = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos"
URL_OIL_STATE = f"{GOV}/arquivos/ppgn-el/producao-petroleo-m3.csv"
URL_GAS_STATE = f"{GOV}/arquivos/ppgn-el/producao-gas-natural-1000m3.csv"
URL_LGN_STATE = f"{GOV}/arquivos/ppgn-el/producao-lgn-m3.csv"  # cross-check only
PAGE_POCO = f"{GOV}/producao-de-petroleo-e-gas-natural-por-poco"
PAGE_FASE = f"{GOV}/fase-de-desenvolvimento-e-producao"
URL_CAMPOS = (f"{GOV}/arquivos/arquivos-fase-de-desenvolvimento-e-producao/"
              "informacoes-sobre-campos/extracao-campo.csv")
START_B, LAST_B = 2016, 2023
TIMEOUT = 300
MONTHS = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
          "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}


def num(s: pd.Series) -> pd.Series:
    """Brazilian number strings ('1.234,56', ',578', '3127,441') -> float."""
    s = s.astype(str).str.strip()
    has_comma = s.str.contains(",", regex=False)
    s = s.where(~has_comma, s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(s.replace({"": None, "nan": None}), errors="coerce").fillna(0.0)


def days(d: pd.Series) -> pd.Series:
    return d.apply(lambda x: calendar.monthrange(x.year, x.month)[1])


def entity(op: str) -> str:
    o = str(op).strip().lower()
    if o.startswith("petrobras") or "petróleo brasileiro" in o:
        return "PETR"
    if re.match(r"^(prio\b|petro\s*rio)", o):
        return "PRIO"
    return "OTHER"


def norm_field(f: str) -> str:
    f = str(f).strip().upper()
    f = re.sub(r"^ANC_", "", f)
    return re.sub(r"_ECO$", "", f)


# ---------------------------------------------------------------- A: by state
def load_state(url, name):
    p = cached(url, name, max_age_days=5, timeout=TIMEOUT)
    d = pd.read_csv(p, sep=";", encoding="utf-8-sig", dtype=str)
    d["v"] = num(d["PRODUÇÃO"])
    d["date"] = pd.to_datetime(dict(year=d["ANO"].astype(int), month=d["MÊS"].map(MONTHS), day=1))
    t = d.groupby(["date", "LOCALIZAÇÃO"])["v"].sum().unstack(fill_value=0)
    t = t[(t.sum(axis=1) > 0)]
    t["days"] = days(t.index.to_series())
    return t


# ---------------------------------------------------------------- B: per well
def _decode(b: bytes) -> str:
    try:
        return b.decode("utf-8-sig")
    except UnicodeDecodeError:
        return b.decode("latin-1")


def parse_poco_csv(text: str) -> pd.DataFrame:
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    hi = next(i for i, r in enumerate(rows[:12])
              if "Campo" in r and "Operador" in r and any(c.startswith("Petróleo (bbl") for c in r))
    h = rows[hi]
    ic, io_, ip = h.index("Campo"), h.index("Operador"), h.index("Período")
    ipet = next(i for i, c in enumerate(h) if c.startswith("Petróleo (bbl"))
    out = [(r[2].strip(), r[ic].strip(), r[io_].strip(), r[ip], r[ipet]) for r in rows[hi + 1:]
           if len(r) > ipet and re.fullmatch(r"\d{4}/\d{2}", r[ip].strip())]
    df = pd.DataFrame(out, columns=["well", "field", "operator", "period", "petroleo"])
    df["kbd"] = num(df["petroleo"]) / 1000
    df["date"] = pd.to_datetime(df["period"].str.strip().str.replace("/", "-") + "-01")
    return df.drop(columns=["petroleo", "period"])


def load_per_well():
    page = cached(PAGE_POCO, "anp_page_poco.html", max_age_days=7, timeout=TIMEOUT).read_text(errors="ignore")
    links = sorted(set(re.findall(r'href="([^"]+por-poco/[^"]+\.zip)"', page)))
    mar, pre = [], []
    for u in links:
        tail = u.split("por-poco/")[1]
        yrs = re.findall(r"(20\d\d)", tail)
        if not yrs or not (START_B <= int(yrs[0]) <= LAST_B):
            continue
        z = zipfile.ZipFile(cached(u, "anp_poco_" + tail.replace("/", "_"), timeout=TIMEOUT))
        for n in z.namelist():
            low = n.lower()
            if not low.endswith(".csv") or "terra" in low:
                continue
            df = parse_poco_csv(_decode(z.read(n)))
            (pre if "presal" in low else mar).append(df)
    mar = pd.concat(mar, ignore_index=True).drop_duplicates(ignore_index=True)
    pre = pd.concat(pre, ignore_index=True).drop_duplicates(ignore_index=True)
    return mar, pre


# ---------------------------------------------------------------- C: producao-mar
def load_mar_files(min_year: int):
    page = cached(PAGE_FASE, "anp_page_fase.html", max_age_days=7, timeout=TIMEOUT).read_text(errors="ignore")
    links = sorted(set(re.findall(r'href="([^"]+/pm/(?:producao-mar-|producao_por_poco_)(\d{4})\.csv)"', page)))
    frames = []
    for u, y in links:
        if int(y) < min_year:
            continue
        p = cached(u, f"anp_pm_{y}.csv", max_age_days=(5 if int(y) >= 2026 else None), timeout=TIMEOUT)
        d = pd.read_csv(p, encoding="utf-8-sig", dtype=str)
        d.columns = [c.strip("[]") for c in d.columns]
        assert {"Mês/Ano", "Campo", "Poço", "Produção de Óleo (m³)"} <= set(d.columns), (u, d.columns[:9])
        d = d[d["Ambiente"].str.upper() == "MAR"]
        m3 = num(d["Produção de Óleo (m³)"]) + num(d["Produção de Condensado (m³)"])
        date = pd.to_datetime(d["Mês/Ano"].str.slice(3, 7) + "-" + d["Mês/Ano"].str.slice(0, 2) + "-01")
        out = pd.DataFrame({"well": d["Poço"].str.strip(), "field": d["Campo"].str.strip(),
                            "date": date, "m3": m3})
        frames.append(out)
    c = pd.concat(frames, ignore_index=True)
    c["kbd"] = c.m3 / days(c["date"]) / BBL / 1000
    return c


def bronze(mid, name, theme, s: pd.Series, unit, entity_id=None):
    df = pd.DataFrame({"metric_id": mid, "metric_name": name, "theme": theme, "source_id": "anp",
                       "freq": "monthly", "date": s.index, "value": s.round(3).values, "unit": unit})
    if entity_id:
        df["entity_id"] = entity_id
    return df


def ok(mid, s, unit, ent=""):
    print(f"[ok]   {mid:<28}{ent:<5} {len(s)} obs ({s.index.min():%Y-%m}..{s.index.max():%Y-%m}) "
          f"latest={s.iloc[-1]:,.1f} {unit}")


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    COMPANIES.mkdir(parents=True, exist_ok=True)

    # --- A: national oil & gas
    oil = load_state(URL_OIL_STATE, "anp_producao_petroleo_m3.csv")
    gas = load_state(URL_GAS_STATE, "anp_producao_gas_1000m3.csv")
    oil = oil[oil.index >= "2012-01-01"]
    gas = gas[gas.index >= "2012-01-01"]
    offshore = oil["MAR"] / oil["days"] / BBL / 1000
    national = (oil["MAR"] + oil["TERRA"]) / oil["days"] / BBL / 1000
    gas_mm3d = (gas["MAR"] + gas["TERRA"]) / gas["days"] / 1000
    write_bronze(bronze("oil_production_offshore_kbd", "Oil production, offshore (incl. condensate)",
                        "oil_gas", offshore, "kbd"), NATIVE / "oil_production_offshore_kbd.csv")
    ok("oil_production_offshore_kbd", offshore, "kbd")
    write_bronze(bronze("gas_production_mm3d", "Natural gas production, total (gross)",
                        "oil_gas", gas_mm3d, "mm3_day"), NATIVE / "gas_production_mm3d.csv")
    ok("gas_production_mm3d", gas_mm3d, "mm3_day")

    # cross-check vs IPEAData oil_production (ANP12_PDPET12 = crude + condensate
    # + LGN/NGL): ANP oil alone runs ~2-5% below; adding producao-lgn-m3.csv
    # reconciles to within ~0.02% (verified 2026-10-03, 175 months).
    ip = NATIVE / "oil_production.csv"
    if ip.exists():
        lg = pd.read_csv(cached(URL_LGN_STATE, "anp_producao_lgn_m3.csv", max_age_days=5, timeout=TIMEOUT),
                         sep=";", encoding="utf-8-sig", dtype=str)
        lg["date"] = pd.to_datetime(dict(year=lg["ANO"].astype(int), month=lg["MÊS"].map(MONTHS), day=1))
        lgn = num(lg["PRODUÇÃO"]).groupby(lg["date"]).sum()
        lgn = lgn[lgn > 0] / days(lgn[lgn > 0].index.to_series()) / BBL / 1000
        ipd = pd.read_csv(ip, parse_dates=["date"]).set_index("date")["value"]
        j = pd.concat([national.rename("anp"), lgn.rename("lgn"), ipd.rename("ipea")],
                      axis=1, sort=True).dropna()
        d_oil = (j.anp / j.ipea - 1) * 100
        d_all = ((j.anp + j.lgn) / j.ipea - 1) * 100
        print(f"[chk]  national oil vs IPEAData oil_production ({len(j)} months): oil-only median "
              f"{d_oil.median():+.2f}%; oil+LGN max |dev| {d_all.abs().max():.3f}% "
              f"(latest {j.index[-1]:%Y-%m}: {j.anp.iloc[-1]:,.0f}+{j.lgn.iloc[-1]:,.0f} vs {j.ipea.iloc[-1]:,.0f} kb/d)")

    # --- B: per-well 2016-2023 with operator + official pre-sal flag
    mar_b, pre_b = load_per_well()
    pre_b_m = pre_b.groupby("date")["kbd"].sum()
    mar_b_m = mar_b.groupby("date")["kbd"].sum()
    chk = (mar_b_m / offshore.reindex(mar_b_m.index) - 1) * 100
    print(f"[chk]  per-well Mar (B) vs state MAR (A) 2016-23: max |dev| {chk.abs().max():.2f}%")

    # --- C: producao-mar 2023+ (2023 only for validation)
    c = load_mar_files(LAST_B)
    def classify(cdf, upto_year):
        """Flag pre-salt wells in C using only B data up to `upto_year`."""
        pb = pre_b[pre_b.date.dt.year <= upto_year]
        mb = mar_b[mar_b.date.dt.year <= upto_year]
        wells = set(pb.well.str.strip())
        ref = mb[mb.date.dt.year == upto_year].assign(pre=lambda d: d.well.str.strip().isin(wells))
        fp = ref.groupby("field").apply(lambda g: g.loc[g.pre, "kbd"].sum() / max(g.kbd.sum(), 1e-9)) > 0.5
        seen = set(mb.well.str.strip())
        return cdf.well.isin(wells) | (~cdf.well.isin(seen) & cdf.field.map(fp).fillna(False).astype(bool))

    # out-of-sample validation: classify 2023 wells using only 2016-2022 B data
    c23 = c[c.date.dt.year == LAST_B]
    m23 = c23[classify(c23, LAST_B - 1)].groupby("date")["kbd"].sum()
    v = pd.concat([pre_b_m.rename("official"), m23.rename("method")], axis=1).dropna()
    print(f"[chk]  pre-sal 2023 out-of-sample (B<=2022 well list) vs official: max |dev| "
          f"{((v.method / v.official - 1) * 100).abs().max():.2f}% over {len(v)} months")
    c["pre"] = classify(c, LAST_B)
    pre_c_m = c[c.pre].groupby("date")["kbd"].sum()

    pre_all = pd.concat([pre_b_m, pre_c_m[pre_c_m.index.year > LAST_B]]).sort_index()
    share = (pre_all / national.reindex(pre_all.index) * 100).dropna()
    write_bronze(bronze("presalt_share", "Pre-salt share of national oil production", "oil_gas",
                        share, "pct"), NATIVE / "presalt_share.csv")
    ok("presalt_share", share, "pct")

    # --- operated volumes
    mar_b["ent"] = mar_b.operator.map(entity)
    op_b = mar_b.groupby(["date", "ent"])["kbd"].sum().unstack(fill_value=0)

    # 2024+ attribution. Field's dominant 2023 operator (by volume) vs current
    # register; a disagreement = operator change since 2023 -> register wins for
    # the whole field. Otherwise each well keeps its last B operator (a few wells
    # are booked under a neighbouring field, e.g. Albacora Leste well 7-ABL-13HP
    # under ALBACORA), and wells new since 2023 take the register operator.
    b23 = mar_b[mar_b.date.dt.year == LAST_B]
    dom23 = b23.groupby(["field", "operator"]).kbd.sum().reset_index() \
        .sort_values("kbd").drop_duplicates("field", keep="last").set_index("field").operator
    well_op = mar_b.sort_values("date").drop_duplicates("well", keep="last").set_index("well").operator
    reg = pd.read_csv(cached(URL_CAMPOS, "anp_extracao_campo.csv", max_age_days=7, timeout=TIMEOUT),
                      encoding="utf-8-sig", dtype=str)
    reg_op = reg.assign(k=reg.CAMPO.map(norm_field)).drop_duplicates("k").set_index("k").OPERADOR

    def register(f):
        k = norm_field(f)
        return reg_op.get(k, reg_op.get(k.split("_")[0]))

    c24 = c[c.date.dt.year > LAST_B].copy()
    field_ent, changes = {}, []
    for f in c24.field.unique():
        old, new = dom23.get(f), register(f)
        e_old = entity(old) if old is not None else None
        e_new = entity(new) if new is not None else None
        if e_old and e_new and e_old != e_new:
            changes.append(f"{f}: {old} -> {new}")
            field_ent[f] = ("force", e_new)
        else:
            field_ent[f] = ("keep", e_new or e_old)
            if not (e_old or e_new):
                print(f"[warn] no operator for field {f} -> OTHER")

    def attribute(row_field, row_well):
        mode, e = field_ent[row_field]
        if mode == "force":
            return e
        if row_well in well_op.index:
            return entity(well_op[row_well])
        return e or "OTHER"

    print(f"[info] operator changes 2023 -> current register (applied to all of 2024+): {changes or 'none'}")
    c24["ent"] = [attribute(f, w) for f, w in zip(c24.field, c24.well)]
    op_c = c24.groupby(["date", "ent"])["kbd"].sum().unstack(fill_value=0)
    op = pd.concat([op_b, op_c]).sort_index()

    frames = []
    for ent in ("PETR", "PRIO"):
        s = op[ent]
        s = s[s.index >= f"{START_B}-01-01"]
        frames.append(bronze("operated_oil_production_kbd",
                             "Operated offshore oil production (operated, gross — not equity)",
                             "companies", s, "kbd", entity_id=ent))
        ok("operated_oil_production_kbd", s, "kbd", ent)
        sh = (s / national.reindex(s.index) * 100).dropna()
        print(f"[chk]  {ent} operated share of national: latest {sh.iloc[-1]:.1f}% "
              f"(2016 avg {sh[sh.index.year == 2016].mean():.1f}%)")
    write_bronze(pd.concat(frames), COMPANIES / "operated_oil_production_kbd.csv", entity=True)


if __name__ == "__main__":
    main()
