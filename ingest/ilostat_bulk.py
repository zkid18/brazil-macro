"""ilostat_bulk.py — every ILOSTAT Brazil series, straight from the ILO, written in the
exact Dateno `ilostat` format (no Dateno API calls at all).

Dateno's `ilostat` namespace mirrors ILOSTAT (annual collection only). Our Dateno key
is capped at 200 requests/day, so this adapter pulls the same data — plus the
quarterly and monthly collections Dateno doesn't carry — from ILO's free rplumber API
and merges it into warehouse/bronze/dateno/{observations,catalog}.parquet via
_dateno_mirror.merge_into_dateno.

Run
---
    .venv/bin/python ingest/ilostat_bulk.py                  # fetch (resumable) + build + merge
    .venv/bin/python ingest/ilostat_bulk.py --build-only     # no network: rebuild from cache
    .venv/bin/python ingest/ilostat_bulk.py --headline-only  # keep only the total disaggregation
    .venv/bin/python ingest/ilostat_bulk.py --refresh        # re-fetch every dataset

Endpoints (cached under warehouse/bronze/raw/ilostat/, gitignored)
---------
    TOC      https://rplumber.ilo.org/metadata/toc/indicator/?lang=en&format=.csv
             1 row per dataset id = <INDICATOR>_<FREQ> (A ~1.2k, Q ~590, M ~170): label,
             freq, subject, database, classif.labels, last.update
    data     https://rplumber.ilo.org/data/indicator/?id=<ID>&ref_area=BRA&format=.csv
             server-side BRA filter, ~1 s/request, no paging (whole series in one CSV):
             ref_area,source,indicator,sex,classif1[,classif2],time,obs_value,obs_status,note_*
    defs     https://sdmx.ilo.org/rest/dataflow/ILO  (one 7 MB SDMX structure message:
             DF_<INDICATOR> -> English Name + HTML Description -> catalog.definition)
The all-country bulk files (rplumber .../data/indicator?id=<ID>&format=.csv.gz) would
be ~100x more bytes for the same Brazil rows, so the per-dataset BRA filter is used.

Dateno ID convention (reproduced)
---------------------------------
    annual:     ts_id = <INDICATOR>.BRA       indicator_id = <INDICATOR>     table = <INDICATOR>_A
    quarterly:  ts_id = <INDICATOR>_Q.BRA     indicator_id = <INDICATOR>_Q   table = <INDICATOR>_Q
    monthly:    ts_id = <INDICATOR>_M.BRA     indicator_id = <INDICATOR>_M   table = <INDICATOR>_M
Annual ids are exactly Dateno's (Dateno: table = indicator + "_A", ISO-3 suffix). Dateno
has no Q/M ILO series; the _Q/_M suffix keeps one freq per ts_id (Dateno invariant
indicator_id = ts_id.rsplit(".", 1)[0] still holds).

Disaggregations
---------------
ILO rows carry up to three dimensions (sex, classif1, classif2). Dateno's export has
two, so:  classif1 = sex (or the first dimension when there is no sex),
          classif2 = the remaining dimension codes joined with "|"   (None if none).
e.g. SEX_T / AGE_YTHADULT_YGE15|ECO_SECTOR_TOTAL. n_dims in the catalog = number of
distinct (classif1, classif2) combinations.
HEADLINE: the "total" series is the rows where every code is a total — SEX_T,
*_TOTAL, *_T, AGE_YTHADULT_YGE15 (15+), *_AGGREGATE_TOTAL — see
_dateno_mirror.headline_mask(obs). catalog.last_value is the headline's last value.
`obs_source` = ILO's survey/source code (e.g. "BX:6355" = PNAD Contínua), exactly as
in Dateno's ilostat exports; catalog `source` names the upstream route.

Gotchas
-------
* rplumber answers HTTP 200 with a header-only CSV when a dataset has no Brazil data
  (cached as-is, counted as "no BRA"), and HTTP 200 + JSON {"error": "deprecated ..."}
  for retired ids (cached as .err, skipped).
* Default Python-urllib and curl UAs get an empty body; _http.UA works.
* Some datasets are huge for Brazil (e.g. EMP_TEMP_SEX_AGE_ECO_NB_Q); the committed
  parquet size is reported at the end — use --headline-only if it gets too big.

Runtime: 1,964 requests ≈ 16 min cold at 8 workers (~0.5 s/request/worker; a few 429s,
retried on rerun); --build-only ≈ 1-2 min.
"""
from __future__ import annotations

import argparse, io, json, re, sys, time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import RAW_CACHE, get_bytes  # noqa: E402
from _dateno_mirror import CAT_COLS, headline_mask, merge_into_dateno, summary  # noqa: E402
from dateno_bulk import parse_period  # noqa: E402

CACHE = RAW_CACHE / "ilostat"
NS = "ilostat"
TOC_URL = "https://rplumber.ilo.org/metadata/toc/indicator/?lang=en&format=.csv"
DATA_URL = "https://rplumber.ilo.org/data/indicator/?id={id}&ref_area=BRA&format=.csv"
DF_URL = "https://sdmx.ilo.org/rest/dataflow/ILO"
SOURCE = "ILOSTAT rplumber API (mirrored in Dateno ilostat)"


def _w(p: Path, b: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_bytes(b)
    tmp.replace(p)


def _cached(url: str, p: Path, offline: bool, refresh: bool = False) -> Path | None:
    if p.exists() and not refresh:
        return p
    if offline:
        return None
    _w(p, get_bytes(url, timeout=180, retries=5))
    return p


def toc(offline: bool) -> pd.DataFrame:
    p = _cached(TOC_URL, CACHE / "toc_en.csv", offline)
    return pd.read_csv(p, dtype=str, encoding="utf-8-sig", keep_default_na=False)


def definitions(offline: bool) -> dict:
    """DF_<INDICATOR> -> (name, description text) from the SDMX dataflow list."""
    try:
        p = _cached(DF_URL, CACHE / "dataflows.xml", offline)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] SDMX dataflows: {e}")
        return {}
    if p is None:
        return {}
    ns = {"s": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
          "c": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common"}
    XL = "{http://www.w3.org/XML/1998/namespace}lang"
    out = {}
    for df in ET.parse(p).getroot().iter(f"{{{ns['s']}}}Dataflow"):
        ind = df.get("id", "").removeprefix("DF_")
        name = next((e.text for e in df.findall("c:Name", ns) if e.get(XL) == "en"), None)
        desc = next((e.text for e in df.findall("c:Description", ns) if e.get(XL) == "en"), None)
        if desc:
            desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", desc)).strip()
        out[ind] = (name, desc)
    return out


def _data_path(i: str) -> Path:
    return CACHE / "data" / f"{i}.csv"


def fetch(ids: list[str], workers: int, refresh: bool) -> int:
    todo = [i for i in ids if refresh or not (_data_path(i).exists() or
                                              _data_path(i).with_suffix(".err").exists())]
    print(f"[ilo] {len(ids)} datasets, {len(todo)} to fetch")
    fails, t0 = 0, time.time()

    def one(i):
        b = get_bytes(DATA_URL.format(id=i), timeout=180, retries=5)
        if b.lstrip().startswith(b"{"):
            _w(_data_path(i).with_suffix(".err"), b)
        else:
            _w(_data_path(i), b)

    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(one, i): i for i in todo}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                fails += 1
                with open(CACHE / "failures.jsonl", "a") as fh:
                    fh.write(json.dumps({"t": time.strftime("%F %T"), "id": futs[f],
                                         "error": str(e)[:300]}) + "\n")
            if n % 200 == 0:
                print(f"  {n}/{len(todo)} fail={fails} {time.time()-t0:.0f}s")
    return fails


def read_one(i: str, freq: str) -> pd.DataFrame | None:
    p = _data_path(i)
    if not p.exists() or p.stat().st_size < 10:
        return None
    df = pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if df.empty:
        return None
    dims = [c for c in ("sex", "classif1", "classif2") if c in df.columns]
    d = df[dims].replace("", None) if dims else pd.DataFrame(index=df.index)
    if dims:
        c1 = d[dims[0]]
        rest = d[dims[1:]]
        c2 = rest.apply(lambda r: "|".join(x for x in r if x), axis=1) if len(dims) > 1 else None
    else:
        c1, c2 = None, None
    ind = df["indicator"].iloc[0]
    iid = ind if freq == "A" else f"{ind}_{freq}"
    out = pd.DataFrame({"ns": NS, "ts_id": f"{iid}.BRA", "indicator_id": iid,
                        "period": df["time"], "value": pd.to_numeric(df["obs_value"], errors="coerce"),
                        "unit": None, "obs_status": df.get("obs_status"),
                        "classif1": c1, "classif2": c2, "obs_source": df.get("source")})
    return out[out["value"].notna()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--headline-only", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    t0 = time.time()
    t = toc(a.build_only)
    defs = definitions(a.build_only)
    fails = 0 if a.build_only else fetch(list(t["id"]), a.workers, a.refresh)

    frames, nobra, err = [], 0, 0
    for r in t.itertuples():
        if _data_path(r.id).with_suffix(".err").exists():
            err += 1
            continue
        df = read_one(r.id, r.freq)
        if df is None:
            nobra += 1
            continue
        df["table"] = r.id
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    pp = {p: parse_period(p) for p in raw["period"].unique()}
    raw["date"] = raw["period"].map(lambda p: pp[p][0])
    raw["freq"] = raw["period"].map(lambda p: pp[p][1])
    raw = raw[raw["date"].notna()].drop(columns="period")
    if a.headline_only:
        raw = raw[headline_mask(raw)]

    meta = t.set_index("id")
    cats = []
    for (ts, iid, tab) in raw[["ts_id", "indicator_id", "table"]].drop_duplicates().itertuples(index=False):
        m = meta.loc[tab]
        label = m["indicator.label"] or None
        unit = re.search(r"\(([^()]*)\)\s*$", label or "")
        name_df, desc = defs.get(m["indicator"], (None, None))
        cats.append({"ns": NS, "ts_id": ts, "indicator_id": iid, "table": tab,
                     "name": label, "indicator_name": label or name_df,
                     "source_id": m["database"] or None, "database": m["database.label"] or None,
                     "source": SOURCE, "topic": m["subject.label"] or None,
                     "unit": unit.group(1) if unit else None, "definition": desc,
                     "periodicity": m["freq.label"] or None, "license": "CC BY 4.0",
                     "last_update": m["last.update"] or None})
    cat = pd.DataFrame(cats)
    for c in CAT_COLS:
        if c not in cat:
            cat[c] = None
    print(f"[ilo] datasets: {len(t)}  with BRA data: {len(frames)}  no BRA: {nobra}  "
          f"deprecated: {err}  fetch failures: {fails}")
    print(f"[ilo] built {len(cat):,} series, {len(raw):,} obs"
          + ("  (headline-only)" if a.headline_only else ""))

    obs_all, cat_all = merge_into_dateno(NS, raw.drop(columns="table"), cat)
    summary(obs_all, cat_all, NS, t0)
    spot(obs_all)
    print("\nrun: .venv/bin/python ingest/ilostat_bulk.py [--build-only] [--headline-only]")
    return 0


SPOT = [("UNE_DEAP_SEX_AGE_RT.BRA", 2023, 7.0, 8.5, "unemployment rate 15+ %"),
        ("UNE_DEAP_SEX_AGE_RT_Q.BRA", 2023, 7.0, 9.5, "unemployment rate 15+ % (Q4)"),
        ("EAP_DWAP_SEX_AGE_RT.BRA", 2023, 60, 65, "labour force participation 15+ %")]


def spot(obs: pd.DataFrame) -> None:
    print("---- sanity ----")
    for ts, yr, lo, hi, lab in SPOT:
        g = obs[(obs.ts_id == ts)]
        g = g[headline_mask(g)] if len(g) else g
        g = g[[d.year == yr for d in g["date"]]].sort_values("date")
        v = g["value"].iloc[-1] if len(g) else None
        ok = v is not None and lo <= v <= hi
        print(f"  [{'OK ' if ok else 'BAD'}] {lab:<34} {ts:<28} {yr}: {v}  (expect {lo}..{hi})"
              + (f"  dims={g.iloc[-1].classif1}/{g.iloc[-1].classif2} src={g.iloc[-1].obs_source}" if len(g) else ""))


if __name__ == "__main__":
    raise SystemExit(main())
