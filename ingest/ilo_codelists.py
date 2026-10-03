"""ilo_codelists.py — readable labels for ILO breakdown codes (sex, age, occupation, ...).

observations_dims stores ILO classification codes such as SEX_F, AGE_YTHADULT_YGE15 or
ECO_ISIC4_C. ILO's SDMX service publishes one codelist per classification:
    GET https://sdmx.ilo.org/rest/codelist/ILO/CL_<DIM>_<SCHEME>   (e.g. CL_ECO_ISIC4, CL_SEX)
Code ids in the codelist equal ours, so a code maps to its English <common:Name>.
(Asking for all codelists at once returns "Response is too large".)

Writes registry/ilo_labels.csv (code, dimension, label), committed.
Run:  python3 ingest/ilo_codelists.py   (after ilostat_bulk.py)
"""
from __future__ import annotations
import pathlib, sys, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_bytes, ROOT  # noqa: E402

S = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"
C = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}"
LANG = "{http://www.w3.org/XML/1998/namespace}lang"
DIM_NAME = {"SEX": "Sex", "AGE": "Age", "ECO": "Economic activity", "OCU": "Occupation", "EDU": "Education",
            "GEO": "Rural / urban", "STE": "Status in employment", "IFL": "Informality", "IND": "Industry",
            "EST": "Establishment", "INS": "Institutional sector", "CUR": "Currency", "MTS": "Marital status",
            "CBR": "Place of birth", "HHT": "Household type", "DSB": "Disability", "NOC": "Number of children",
            "LMS": "Labour market status", "NAT": "Nationality", "MJH": "Multiple jobs", "WKT": "Working time"}


def fetch(cl: str) -> list[tuple]:
    try:
        root = ET.fromstring(get_bytes(f"https://sdmx.ilo.org/rest/codelist/ILO/{cl}", timeout=60, retries=2))
    except Exception:  # noqa: BLE001 — unknown codelist id: try the next candidate
        return []
    out = []
    for code in root.iter(f"{S}Code"):
        name = next((n.text for n in code.findall(f"{C}Name") if n.get(LANG) == "en"), None)
        if name:
            out.append((code.get("id"), name))
    return out


def main():
    import duckdb
    db = ROOT / "warehouse" / "brazil_macro.duckdb"
    con = duckdb.connect(str(db), read_only=True)
    codes = {r[0] for r in con.sql(
        "SELECT DISTINCT unnest(string_split(coalesce(classif1,'') || '|' || coalesce(classif2,''), '|')) "
        "FROM observations_dims").fetchall() if r[0]}
    con.close()
    # candidate codelists: CL_<first two tokens>, then CL_<first token>
    cands = set()
    for c in codes:
        p = c.split("_")
        if len(p) >= 3:
            cands.add("CL_" + "_".join(p[:2]))
        cands.add("CL_" + p[0])
    with ThreadPoolExecutor(6) as ex:
        res = dict(zip(sorted(cands), ex.map(fetch, sorted(cands))))
    lab = {}
    for cl, pairs in res.items():
        for cid, name in pairs:
            lab.setdefault(cid, name)
    rows = [(c, DIM_NAME.get(c.split("_")[0], c.split("_")[0].title()), lab.get(c, c)) for c in sorted(codes)]
    df = pd.DataFrame(rows, columns=["code", "dimension", "label"])
    df.to_csv(ROOT / "registry" / "ilo_labels.csv", index=False)
    print(f"ilo labels: {len(df)} codes, {sum(df.code != df.label)} labelled from "
          f"{sum(1 for v in res.values() if v)} codelists")


if __name__ == "__main__":
    main()
