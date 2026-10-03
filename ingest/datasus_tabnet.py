"""datasus_tabnet.py — native adapter: DATASUS TabNet SIM (Sistema de Informações sobre
Mortalidade), monthly deaths by place of residence, Brazil, 1996 → latest preliminary month.

Endpoint (free, no key; form POST, latin-1 HTML with a <PRE> CSV block when formato=prn):
  POST http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/obt10uf.def
  Linha=Ano/mês_do_Óbito  Coluna=--Não-Ativa--  Incremento=Óbitos_p/Residênc
  Arquivos=obtuf96.dbf … obtuf26.dbf (one per year)   formato=prn
  every S<dimension> select must be sent (TODAS_AS_CATEGORIAS__ = no filter); the body
  must be urlencoded as latin-1 (field names carry accents).

Series (filters on the form's own option codes, verified against tn_form.html 2026-10-03):
  deaths_total        no filter                                      (all causes)
  homicide_deaths     SGrupo_CID-10=246  "Agressões"                  X85–Y09
  suicide_deaths      SGrupo_CID-10=245  "Lesões autoprovocadas int." X60–X84
  traffic_deaths      SGrupo_CID-10=220..228 (pedestre … outros terrestres) V01–V89
  deaths_respiratory  SCapítulo_CID-10=10  chapter X                  J00–J99
  deaths_circulatory  SCapítulo_CID-10=9   chapter IX                 I00–I99

Gotchas:
  * SIM data are FINAL only through 2024 (as of extraction 02/12/2025); 2025–2026 are
    preliminary and the latest months are badly incomplete (Aug-2026 total = 51k vs ~125k
    normal). Rule: per series, walk back from the latest month and drop it while
    value < 85% of the mean of the 12 months before it. Earlier preliminary months are
    kept but may still be revised up (homicides especially, as police investigations
    re-code 'undetermined intent' deaths).
  * Rows are "Janeiro/1996" (or "..Janeiro/1996"), interleaved with year subtotal rows
    "1996" and a final "Total" row — both skipped. "-" means zero.
  * One POST for all 31 yearly files takes ~15 s.

Sanity (2026-10-03): homicides 1996 = 38,894; 2024 = 39,9xx (≈39,946 expected);
deaths_total 2024 = 1,532,015 — WHO MDB 2023 total is 1,465,610.
Cross-check vs WHO MDB homicides is printed by ingest/who_mortality.py.

Writes bronze/native/<metric_id>.csv, theme=health, source_id=datasus_sim, unit=deaths.
Run:  .venv/bin/python ingest/datasus_tabnet.py
"""
from __future__ import annotations
import re, sys, html, pathlib, datetime, urllib.parse
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_bytes, write_bronze, NATIVE  # noqa: E402

URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/obt10uf.def"
FIRST_YEAR = 1996
SELECTS = ["SRegião", "SUnidade_da_Federação", "SCapítulo_CID-10", "SGrupo_CID-10",
           "SCategoria_CID-10", "SCausa_-_CID-BR-10", "SCausa_mal_definidas", "SFaixa_Etária",
           "SFaixa_Etária_OPS", "SFaixa_Etária_det", "SFx.Etária_Menor_1A", "SSexo", "SCor/raça",
           "SEscolaridade", "SEstado_civil", "SLocal_ocorrência"]
MONTHS = {m: i + 1 for i, m in enumerate(
    ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
     "Setembro", "Outubro", "Novembro", "Dezembro"])}
COMPLETE_SHARE = 0.85  # latest month must reach 85% of trailing-12m mean to be kept

# metric_id -> (filters, name)
SERIES = {
    "deaths_total": ({}, "Deaths, all causes (SIM, by residence)"),
    "homicide_deaths": ({"SGrupo_CID-10": ["246"]}, "Homicide deaths (ICD-10 X85-Y09)"),
    "suicide_deaths": ({"SGrupo_CID-10": ["245"]}, "Suicide deaths (ICD-10 X60-X84)"),
    "traffic_deaths": ({"SGrupo_CID-10": [str(g) for g in range(220, 229)]},
                       "Land-transport accident deaths (ICD-10 V01-V89)"),
    "deaths_respiratory": ({"SCapítulo_CID-10": ["10"]}, "Respiratory-disease deaths (ICD-10 J00-J99)"),
    "deaths_circulatory": ({"SCapítulo_CID-10": ["9"]}, "Circulatory-disease deaths (ICD-10 I00-I99)"),
}


def query(filters: dict, years) -> str:
    p = [("Linha", "Ano/mês_do_Óbito"), ("Coluna", "--Não-Ativa--"), ("Incremento", "Óbitos_p/Residênc")]
    p += [("Arquivos", f"obtuf{y % 100:02d}.dbf") for y in years]
    for s in SELECTS:
        p += [(s, v) for v in filters.get(s, ["TODAS_AS_CATEGORIAS__"])]
    p += [("formato", "prn"), ("mostre", "Mostra")]
    body = urllib.parse.urlencode(p, encoding="latin-1").encode()
    raw = get_bytes(URL, data=body, method="POST", timeout=240,
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    return raw.decode("latin-1")


def parse(page: str) -> pd.DataFrame:
    m = re.search(r"<PRE>(.*?)</PRE>", page, re.S | re.I)
    if not m:
        raise RuntimeError("TabNet response has no <PRE> block: " + page[-500:])
    recs = []
    for line in html.unescape(m.group(1)).splitlines():
        mm = re.match(r'^"\.*([A-Za-zçÇ]+)/(\d{4})";(.+)$', line.strip())
        if not mm or mm.group(1) not in MONTHS:
            continue  # header, year subtotal, Total
        v = mm.group(3).strip()
        recs.append(dict(date=f"{mm.group(2)}-{MONTHS[mm.group(1)]:02d}-01",
                         value=0.0 if v == "-" else float(v)))
    return pd.DataFrame(recs).sort_values("date").reset_index(drop=True)


def drop_incomplete(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    dropped = []
    while len(df) > 13:
        last, base = df.value.iloc[-1], df.value.iloc[-13:-1].mean()
        if last >= COMPLETE_SHARE * base:
            break
        dropped.append(df.date.iloc[-1])
        df = df.iloc[:-1]
    return df, dropped


def main():
    years = range(FIRST_YEAR, datetime.date.today().year + 1)
    for mid, (filters, name) in SERIES.items():
        df, dropped = drop_incomplete(parse(query(filters, years)))
        df = df.assign(metric_id=mid, metric_name=name, theme="health", source_id="datasus_sim",
                       freq="monthly", unit="deaths")
        n = write_bronze(df, NATIVE / f"{mid}.csv")
        if n:
            ann = df.assign(y=df.date.str[:4]).groupby("y").value.sum()
            print(f"[ok]   {mid:<20} {n} obs ({df.date.min()}..{df.date.max()}) "
                  f"latest={df.value.iloc[-1]:.0f}  2024={ann.get('2024', float('nan')):.0f}  "
                  f"dropped_incomplete={dropped}")


if __name__ == "__main__":
    main()
