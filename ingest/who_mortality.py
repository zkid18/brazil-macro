"""who_mortality.py — native adapter: WHO Mortality Database (ICD-10 raw files), Brazil,
annual 1996–2023, plus mortality rates using IBGE population projections.

Endpoints (free, no key; listed on https://www.who.int/data/data-collection-tools/who-mortality-database):
  https://cdn.who.int/media/docs/default-source/world-health-data-platform/mortality-raw-data/morticd10_part{1..6}.zip
  (~7–12 MB each, CSV with header Country,Admin1,SubDiv,Year,List,Cause,Sex,Frmat,IM_Frmat,
   Deaths1..Deaths26,IM_Frmat..IM_Deaths4). Cached in bronze/raw/who_morticd10_part*.zip via cached();
  only Brazil rows are parsed, only the derived annual series are written.
  Population: IBGE SIDRA t7358 v606 (Projeção da população, revisão 2018), c2 sex
  (6794 total / 4 men / 5 women), c287/100362 (all ages), c1933 = projection year 2000–2060.

Codes / layout:
  Country 2070 = Brazil. List 104 = ICD-10 detailed list with mixed 3-char ("A00") and 4-char
  ("A001") cause codes; Cause "AAA" = all causes (national total). Ranges below are matched on the
  first 3 characters (detail codes never duplicate a 3-char code within list 104 — verified:
  sum of non-AAA causes == AAA for every year).
  Sex 1 = male, 2 = female, 9 = unknown (included in totals, excluded from sex-specific rates).
  Frmat 00 for every Brazil row: Deaths1 = all ages, Deaths2 = <1 year, Deaths19..25 = 65-69 … 95+,
  Deaths26 = age unknown.

Gotchas:
  * 1996–2002 also carry sub-national rows (Admin1 901/902) → keep Admin1 empty only.
  * IBGE projection starts in 2000 and the WHO pop file has no national Brazil population for
    1996–1999 → rates are 2000–2023; counts/shares are 1996–2023.
  * traffic = V01–V89 (all land transport) to match the TabNet traffic_deaths definition, not
    WHO's narrower road-traffic subset.

Series (theme=health, source_id=who_mdb):
  deaths_total_who, infant_deaths (deaths); homicide_rate (X85–Y09), suicide_rate (X60–X84),
  traffic_death_rate (V01–V89), lung_cancer_rate_male/female (C33–C34)  (per 100k, crude);
  ncd_death_share (C00–D48 + E00–E90 + I00–I99 + J00–J99, % of all deaths); deaths_65plus_share (%).

Sanity (verified 2026-10-03): total deaths 2023 = 1,465,610; homicides 52,260 (2010),
63,748 (2017), 43,443 (2023); suicides 2019 ≈ 13.5k → 2023 ≈ 17.0k; lung cancer (C33–C34) 2023 ≈ 31.2k.
Cross-check: annual sums of bronze homicide_deaths.csv (DATASUS TabNet) vs WHO homicide counts
2010–2023 printed at the end (run ingest/datasus_tabnet.py first).

Run:  .venv/bin/python ingest/who_mortality.py
"""
from __future__ import annotations
import sys, pathlib, zipfile
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import cached, get_json, write_bronze, NATIVE  # noqa: E402

BASE = "https://cdn.who.int/media/docs/default-source/world-health-data-platform/mortality-raw-data"
PARTS = range(1, 7)
BRAZIL = 2070
POP_URL = ("https://apisidra.ibge.gov.br/values/t/7358/n1/all/v/606/p/all"
           "/c2/6794,4,5/c287/100362/c1933/all")

GROUPS = {  # name -> list of (lo, hi) 3-char ICD ranges, inclusive
    "homicide": [("X85", "Y09")],
    "suicide": [("X60", "X84")],
    "traffic": [("V01", "V89")],
    "lung": [("C33", "C34")],
    "ncd": [("C00", "D48"), ("E00", "E90"), ("I00", "I99"), ("J00", "J99")],
}

META = {  # metric_id -> (name, unit)
    "deaths_total_who": ("Deaths, all causes (WHO MDB)", "deaths"),
    "infant_deaths": ("Infant deaths (age <1, WHO MDB)", "deaths"),
    "homicide_rate": ("Homicide rate (X85-Y09)", "per_100k"),
    "suicide_rate": ("Suicide rate (X60-X84)", "per_100k"),
    "traffic_death_rate": ("Land-transport death rate (V01-V89)", "per_100k"),
    "lung_cancer_rate_male": ("Lung cancer death rate, male (C33-C34)", "per_100k"),
    "lung_cancer_rate_female": ("Lung cancer death rate, female (C33-C34)", "per_100k"),
    "ncd_death_share": ("NCD share of deaths (C00-D48, E00-E90, I00-I99, J00-J99)", "pct"),
    "deaths_65plus_share": ("Share of deaths at age 65+", "pct"),
}


def load_brazil() -> pd.DataFrame:
    frames = []
    for i in PARTS:
        p = cached(f"{BASE}/morticd10_part{i}.zip", f"who_morticd10_part{i}.zip", max_age_days=90)
        with zipfile.ZipFile(p) as z:
            with z.open(z.namelist()[0]) as f:
                for ch in pd.read_csv(f, dtype=str, chunksize=500_000):
                    ch = ch[ch.Country == str(BRAZIL)]
                    if len(ch):
                        frames.append(ch)
    df = pd.concat(frames, ignore_index=True)
    df = df[df.Admin1.isna() & df.SubDiv.isna()]  # national rows only
    dcols = [f"Deaths{k}" for k in range(1, 27)]
    df[dcols] = df[dcols].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["Year"] = df.Year.astype(int)
    df["c3"] = df.Cause.str[:3]
    return df


def in_group(c3: pd.Series, name: str) -> pd.Series:
    m = pd.Series(False, index=c3.index)
    for lo, hi in GROUPS[name]:
        m |= (c3 >= lo) & (c3 <= hi)
    return m


def population() -> pd.DataFrame:
    rows = get_json(POP_URL)[1:]
    sex = {"6794": "total", "4": "male", "5": "female"}
    recs = [dict(year=int(r["D6N"]), sex=sex[r["D4C"]], pop=float(r["V"])) for r in rows]
    return pd.DataFrame(recs).pivot(index="year", columns="sex", values="pop")


def main():
    df = load_brazil()
    tot = df[df.Cause == "AAA"].groupby("Year")
    allc = tot.Deaths1.sum()
    detail = df[df.Cause != "AAA"].groupby("Year").Deaths1.sum()
    gap = (detail - allc).abs().max()
    print(f"[chk]  WHO Brazil national rows: {len(df)}; years {allc.index.min()}..{allc.index.max()}; "
          f"max |sum(detail)-AAA| = {gap:.0f}")
    det = df[df.Cause != "AAA"]

    def count(name, sexes=None):
        d = det[in_group(det.c3, name)]
        if sexes:
            d = d[d.Sex.isin(sexes)]
        return d.groupby("Year").Deaths1.sum().reindex(allc.index, fill_value=0)

    pop = population().reindex(allc.index)
    out = {
        "deaths_total_who": allc,
        "infant_deaths": tot.Deaths2.sum(),
        "homicide_rate": count("homicide") / pop.total * 1e5,
        "suicide_rate": count("suicide") / pop.total * 1e5,
        "traffic_death_rate": count("traffic") / pop.total * 1e5,
        "lung_cancer_rate_male": count("lung", ["1"]) / pop.male * 1e5,
        "lung_cancer_rate_female": count("lung", ["2"]) / pop.female * 1e5,
        "ncd_death_share": count("ncd") / allc * 100,
        "deaths_65plus_share": tot[[f"Deaths{k}" for k in range(19, 26)]].sum().sum(axis=1) / allc * 100,
    }
    for mid, s in out.items():
        name, unit = META[mid]
        s = s.dropna().round(4 if unit != "deaths" else 0)
        b = pd.DataFrame({"date": [f"{y}-01-01" for y in s.index], "value": s.values}).assign(
            metric_id=mid, metric_name=name, theme="health", source_id="who_mdb", freq="annual", unit=unit)
        n = write_bronze(b, NATIVE / f"{mid}.csv")
        if n:
            print(f"[ok]   {mid:<24} {n} obs ({b.date.min()}..{b.date.max()}) latest={b.value.iloc[-1]}")

    hom = count("homicide")
    print("[chk]  counts: total2023={:.0f} homicides 2010/2017/2023={:.0f}/{:.0f}/{:.0f} "
          "suicides 2019/2023={:.0f}/{:.0f} lung(C33-34) 2023={:.0f}".format(
              allc.get(2023), hom.get(2010), hom.get(2017), hom.get(2023),
              count("suicide").get(2019), count("suicide").get(2023), count("lung").get(2023)))

    tn = NATIVE / "homicide_deaths.csv"
    if tn.exists():
        t = pd.read_csv(tn)
        t = t.assign(y=t.date.str[:4].astype(int)).groupby("y").value.sum()
        yrs = [y for y in range(2010, 2024) if y in t.index and y in hom.index]
        rel = ((t[yrs] - hom[yrs]).abs() / hom[yrs])
        print(f"[chk]  homicides WHO vs TabNet 2010-2023: max rel diff = {rel.max():.4%} "
              f"(year {rel.idxmax()}: WHO {hom[rel.idxmax()]:.0f} vs TabNet {t[rel.idxmax()]:.0f})")


if __name__ == "__main__":
    main()
