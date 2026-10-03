"""worldbank_bulk.py — every World Bank Brazil series, straight from the World Bank,
written in the exact Dateno `wb` format (no Dateno API calls at all).

Dateno's `wb` namespace is a mirror of the public World Bank API v2 (its export
columns are literally the API's JSON fields). Our Dateno key is capped at 200
requests/day, so this adapter pulls the same data from the free upstream and merges
it into warehouse/bronze/dateno/{observations,catalog}.parquet via
_dateno_mirror.merge_into_dateno (the 22 Dateno-native tier-1 rows always win).

Run
---
    .venv/bin/python ingest/worldbank_bulk.py                 # download/refresh + build + merge
    .venv/bin/python ingest/worldbank_bulk.py --build-only    # no network: rebuild from cache
    .venv/bin/python ingest/worldbank_bulk.py --skip-api      # bulk zips only
    .venv/bin/python ingest/worldbank_bulk.py --max-age 30    # re-download bulk zips older than N days

Routes (both cached under warehouse/bronze/raw/worldbank/, gitignored, resumable)
------
1. DataBank bulk CSV zips (primary; measured ~13 MB/s, WDI 283 MB in 22 s):
     https://databank.worldbank.org/data/download/<NAME>_CSV.zip  (302 -> databankfiles...)
   One all-country wide file per database ("Country Name, Country Code, Indicator Name,
   Indicator Code, 1960, 1961, ..." or "...,1995Q1, ..."), plus a *Series* metadata file
   whose columns (Topic, Unit of measure, Periodicity, Long definition, Source, License
   Type) are exactly the metadata Dateno exposes. We line-filter on "BRA" before
   parsing, so even the 200 MB WDI CSV parses in a few seconds.
   IDS is 4-dimensional (counterpart area): we keep Counterpart-Area = WLD, which is
   what the API (and Dateno) return by default.
2. API v2 for sources without a bulk zip (QEDS, Findex, JEDH, GEM monthly, ...):
     indicator list   https://api.worldbank.org/v2/indicator?format=json&per_page=30000
                      (29.5k ids, each attributed to ONE "home" source -> one series
                       per indicator, like Dateno's 18k-indicator wb namespace)
     data             https://api.worldbank.org/v2/country/BRA/indicator/A;B;...(<=60)
                      ?source=<sid>&format=json&per_page=20000   (all dates when no date=)
   One JSON per 60-indicator chunk; per_page=20000 means no paging in practice
   (pages>1 is still followed). Without date= the API returns ANNUAL data only, so GEM
   (source 15) is also queried with date=1960M01:<Y>M12 and date=1960Q1:<Y>Q4.
   Fallback when that route fails (QEDS 22/23 and JEDH 54 answer 400 "Invalid value"):
     https://api.worldbank.org/v2/sources/<sid>/country/BRA/series/all/time/all
     ?format=json&per_page=50000&page=N     (~45 s per 50k-cell page, mostly nulls)
   4-dimension sources (PEFA, ICP, DSSI, FPN) return "Data not found" on both routes
   for Brazil and are logged, not fatal.

Dateno ID convention (reproduced)
---------------------------------
    ts_id = <INDICATOR>.<country.id as the WB API returns it>, indicator_id = <INDICATOR>,
    table = <INDICATOR>.
The API's country.id is ISO-2 ("BR") for most databases (WDI, Gender, IDS, ...) and
ISO-3 ("BRA") for a few (e.g. LAC Equity Lab) — this is exactly Dateno's ".BR" vs ".BRA"
split. For API routes we use country.id from the payload; for bulk routes we probe one
API call per database (`country/all/indicator/<id>?source=<sid>&per_page=1`, cached
in id_style.json) and default to ISO-2 if the probe fails.
When the same indicator code appears in several databases (WDI codes are repeated
in Gender/HNP/EdStats/...), the series comes from its home source per the API list;
if the home source has no Brazil data, WDI first, then the order of BULK below.

Gotchas
-------
* 2026-10: api.worldbank.org data calls return 502 for most uncached URLs (CDN-cached
  URLs still answer). Hence the bulk-first design; API calls retry 6x with backoff
  and failures are logged to failures.jsonl — a rerun picks up only what is missing.
* GEM's bulk zip (GemDataEXTR.zip) is xlsx-only and frozen at 2024-03; GEM comes
  from the API (source 15, monthly/quarterly) instead.
* `obs_source` = "World Bank <route>: <database> (mirrored in Dateno wb)"; catalog
  `source` = "World Bank <route> (mirrored in Dateno wb)"; the original data
  provider (e.g. "IMF, IFS") is appended to `definition` as "Source: ...".
* Skipped sources: subnational / other-country (5, 11, 38, 41, 45, 50), WDI Database
  Archives (57, vintages of WDI), internal survey copy (73).
* An indicator with several frequencies (GEM) is split: annual keeps <IND>.<cc>
  (Dateno's id), quarterly/monthly become <IND>_Q.<cc> / <IND>_M.<cc>.
* Expected-empty for Brazil: QEDS GDDS (23; Brazil reports SDDS), GPE (34), PEFA,
  ICP, DSSI, GDLD, FPN — their API calls fail/return nothing and are logged.
* Bulk zips have no obs_status; empty strings and ".." are gaps and are dropped.

Runtime: ~2-3 min cold (≈1.1 GB of zips), ~40 s --build-only.
"""
from __future__ import annotations

import argparse, csv, hashlib, io, json, re, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import RAW_CACHE, get_bytes, get_json  # noqa: E402
from _dateno_mirror import CAT_COLS, merge_into_dateno, summary, tier1_check  # noqa: E402
from dateno_bulk import parse_period  # noqa: E402

CACHE = RAW_CACHE / "worldbank"
API = "https://api.worldbank.org/v2"
DL = "https://databank.worldbank.org/data/download/"
NS = "wb"
TAG = "(mirrored in Dateno wb)"

# source id -> bulk zip (DataBank). Order = fallback priority after the home source.
BULK = {
    "2": "WDI_CSV.zip", "6": "IDS_CSV.zip", "14": "Gender_Stats_CSV.zip",
    "16": "HNP_Stats_CSV.zip", "12": "EdStats_CSV.zip", "25": "Jobs_CSV.zip",
    "32": "GFDD_CSV.zip", "3": "WGI_CSV.zip", "83": "SPI_CSV.zip", "1": "DB_CSV.zip",
    "20": "QPSD_CSV.zip", "29": "ASPIRE_CSV.zip", "40": "Population-Estimates_CSV.zip",
    "75": "ESG_CSV.zip", "86": "JOIN_CSV.zip", "87": "CCDR_CSV.zip", "46": "SDG_CSV.zip",
    "19": "MDG_CSV.zip", "39": "HNPQ_CSV.zip", "65": "HEFPI_CSV.zip", "31": "CPIA_CSV.zip",
    "13": "ES_CSV.zip", "66": "LPI_CSV.zip", "35": "SE4ALL_CSV.zip", "63": "HCI_CSV.zip",
    "58": "UHC_CSV.zip", "18": "IDA_CSV.zip", "27": "GEP_CSV.zip", "60": "Economic_Fitness_CSV.zip",
    "89": "ID4D_CSV.zip", "37": "LAC_CSV.zip",
    "povstats": "PovStats_CSV.zip",  # Poverty & Equity: DataBank-only (not an API v2 source)
}
EXTRA_DB = {"povstats": "Poverty and Equity"}
SKIP = {"5", "11", "38", "41", "45", "50", "57", "73"}
_PERIOD = re.compile(r"^(\d{4}(?:Q[1-4]|M\d{2})?)(?: \[.*\])?$")
_UNIT_IN_NAME = re.compile(r"\(([^()]*)\)\s*$")


def _w(p: Path, b: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_bytes(b)
    tmp.replace(p)


def _log_fail(stage: str, job: str, err: Exception) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(CACHE / "failures.jsonl", "a") as fh:
        fh.write(json.dumps({"t": time.strftime("%F %T"), "stage": stage, "job": job,
                             "error": str(err)[:300]}) + "\n")


# ---------------------------------------------------------------- reference lists
def sources(offline: bool) -> dict:
    p = CACHE / "sources.json"
    if not p.exists() and not offline:
        r = get_json(f"{API}/sources?format=json&per_page=200", retries=6)
        _w(p, json.dumps(r[1]).encode())
    return {s["id"]: s for s in json.loads(p.read_text())} if p.exists() else {}


def indicator_list(offline: bool) -> dict:
    """id -> {name, unit, source.id, sourceNote, sourceOrganization, topics}."""
    p = CACHE / "indicators.json"
    if not p.exists() and not offline:
        r = get_json(f"{API}/indicator?format=json&per_page=30000", retries=6)
        _w(p, json.dumps(r[1]).encode())
    return {i["id"]: i for i in json.loads(p.read_text())} if p.exists() else {}


def id_style(sids: list[str], inds: dict, offline: bool) -> dict:
    """sid -> 'BR' or 'BRA' (the API's country.id convention = Dateno's ts suffix)."""
    p = CACHE / "id_style.json"
    st = json.loads(p.read_text()) if p.exists() else {}
    todo = [s for s in sids if s not in st and s.isdigit()]
    if todo and not offline:
        first = {}
        for i in inds.values():
            first.setdefault(i["source"]["id"], i["id"])

        def probe(sid):
            ind = first.get(sid)
            if not ind:
                return sid, None
            url = f"{API}/country/BR;BRA/indicator/{ind}?source={sid}&format=json&per_page=5"
            try:
                r = get_json(url, retries=5, backoff=2)
            except Exception:  # noqa: BLE001
                try:
                    r = get_json(f"{API}/country/all/indicator/{ind}?source={sid}&format=json&per_page=1",
                                 retries=5, backoff=2)
                except Exception as e:  # noqa: BLE001
                    _log_fail("id_style", sid, e)
                    return sid, None
            rows = r[1] if len(r) > 1 and r[1] else []
            if not rows:
                return sid, None
            return sid, "BRA" if len(rows[0]["country"]["id"]) == 3 else "BR"

        with ThreadPoolExecutor(6) as ex:
            for sid, s in ex.map(probe, todo):
                if s:
                    st[sid] = s
        _w(p, json.dumps(st, indent=1, sort_keys=True).encode())
    return st


# ---------------------------------------------------------------- route 1: bulk zips
def download_bulk(max_age: float | None, workers: int) -> None:
    d = CACHE / "bulk"
    d.mkdir(parents=True, exist_ok=True)

    def one(name):
        p = d / name
        if p.exists() and p.stat().st_size > 0 and (
                max_age is None or time.time() - p.stat().st_mtime < max_age * 86400):
            return name, "cached"
        t = time.time()
        b = get_bytes(DL + name, timeout=300, retries=4)
        if not b.startswith(b"PK"):
            raise RuntimeError("not a zip")
        _w(p, b)
        return name, f"{len(b)/1e6:.0f} MB in {time.time()-t:.0f}s"

    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(one, n): n for n in BULK.values()}
        for f in as_completed(futs):
            try:
                n, msg = f.result()
                if msg != "cached":
                    print(f"  [bulk] {n}: {msg}")
            except Exception as e:  # noqa: BLE001
                print(f"  [bulk FAIL] {futs[f]}: {e}")
                _log_fail("bulk", futs[f], e)


def _members(z: zipfile.ZipFile) -> tuple[str | None, str | None]:
    """(data csv, series-metadata csv) inside a DataBank zip."""
    data, series = None, None
    for zi in sorted(z.infolist(), key=lambda x: -x.file_size):
        n = zi.filename.lower()
        if not n.endswith(".csv"):
            continue
        if series is None and "series" in n and "country" not in n and "time" not in n \
                and "footnote" not in n:
            series = zi.filename
            continue
        if data is None and not any(k in n for k in ("country", "series", "footnote", "foot")):
            data = zi.filename
    return data, series


def parse_bulk(sid: str, path: Path) -> tuple[pd.DataFrame, dict]:
    """-> long BRA rows [indicator_id, name, period, value], {code: series-metadata}."""
    z = zipfile.ZipFile(path)
    data, series = _members(z)
    if data is None:
        raise RuntimeError(f"no data csv in {path.name}: {z.namelist()}")
    with z.open(data) as fh:
        txt = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace")
        header = txt.readline()
        lines = [header] + [ln for ln in txt if "BRA" in ln]
    df = pd.read_csv(io.StringIO("".join(lines)), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    df = df[df["Country Code"].str.strip() == "BRA"]
    if "Counterpart-Area Code" in df.columns:
        df = df[df["Counterpart-Area Code"].str.strip() == "WLD"]
    code = "Indicator Code" if "Indicator Code" in df.columns else "Series Code"
    name = "Indicator Name" if "Indicator Name" in df.columns else "Series Name"
    pcols = [c for c in df.columns if _PERIOD.match(c)]
    long = df[[code, name] + pcols].melt([code, name], var_name="period", value_name="value")
    long["value"] = pd.to_numeric(long["value"].str.strip().replace({"..": ""}), errors="coerce")
    long = long[long["value"].notna()]
    long["period"] = long["period"].str.extract(_PERIOD)[0]
    long = long.rename(columns={code: "indicator_id", name: "name"})
    long["indicator_id"] = long["indicator_id"].str.strip()

    meta = {}
    if series:
        with z.open(series) as fh:
            sm = pd.read_csv(fh, dtype=str, keep_default_na=False, encoding="utf-8-sig",
                             encoding_errors="replace")
        sm.columns = [c.strip() for c in sm.columns]
        kc = "Series Code" if "Series Code" in sm.columns else "Code" if "Code" in sm.columns else sm.columns[0]
        for r in sm.to_dict("records"):
            meta[r[kc].strip()] = {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
    return long, meta


# ---------------------------------------------------------------- route 2: API v2
Y = time.gmtime().tm_year
# sources whose API defaults to annual only: also ask for monthly and quarterly ranges
DATE_VARIANTS = {"15": ["", f"&date=1960M01:{Y}M12", f"&date=1960Q1:{Y}Q4"]}


def _api_path(sid: str, chunk: list[str], variant: str = "") -> Path:
    h = hashlib.md5((";".join(chunk) + variant).encode()).hexdigest()[:12]
    return CACHE / "api" / sid / f"{h}.json"


def fetch_api(sid: str, ids: list[str], workers: int, offline: bool) -> tuple[list, int]:
    """Indicator route: country/BRA/indicator/<=60 ids. Returns (rows, missing jobs)."""
    chunks = [ids[i:i + 60] for i in range(0, len(ids), 60)]
    jobs = [(c, v) for c in chunks for v in DATE_VARIANTS.get(sid, [""])]
    todo = [j for j in jobs if not _api_path(sid, *j).exists()]

    def one(job):
        chunk, variant = job
        rows, page, pages = [], 1, 1
        while page <= pages:
            url = (f"{API}/country/BRA/indicator/{';'.join(chunk)}?source={sid}"
                   f"&format=json&per_page=20000&page={page}{variant}")
            r = get_json(url, retries=6, backoff=2, timeout=120)
            if not isinstance(r, list) or len(r) < 2:
                raise RuntimeError(f"API message: {str(r)[:200]}")
            pages = int(r[0].get("pages") or 1)
            rows += [x for x in (r[1] or []) if x.get("value") is not None]
            page += 1
        _w(_api_path(sid, chunk, variant), json.dumps(rows).encode())

    if todo and not offline:
        with ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(one, j): j for j in todo}
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:  # noqa: BLE001
                    _log_fail(f"api:{sid}", ";".join(futs[f][0])[:120], e)
    rows = []
    for j in jobs:
        p = _api_path(sid, *j)
        if p.exists():
            rows += json.loads(p.read_text())
    return rows, sum(not _api_path(sid, *j).exists() for j in jobs)


def fetch_advanced(sid: str, workers: int, offline: bool) -> list:
    """Fallback for sources whose indicator route 400s (QEDS 22/23, JEDH 54, ...):
    sources/<sid>/country/BRA/series/all/time/all, 50k cells/page (~45 s/page, mostly
    null cells). Rows are converted to the indicator-route shape. 4-concept sources
    (PEFA, ICP, DSSI) answer 'Data not found' here and are skipped."""
    d = CACHE / "api_adv" / sid
    url = f"{API}/sources/{sid}/country/BRA/series/all/time/all?format=json&per_page=50000&page={{}}"

    def page(n):
        p = d / f"p{n:04d}.json"
        if p.exists():
            return json.loads(p.read_text())
        if offline:
            raise RuntimeError("offline")
        r = get_json(url.format(n), retries=6, backoff=3, timeout=300)
        rows = []
        for x in r["source"]["data"]:
            if x.get("value") is None:
                continue
            v = {c["concept"].lower(): c for c in x["variable"]}
            if set(v) - {"country", "series", "time"}:
                continue
            rows.append({"indicator": {"id": v["series"]["id"], "value": v["series"]["value"]},
                         "country": {"id": None}, "date": v["time"]["value"], "value": x["value"]})
        out = {"pages": int(r["pages"]), "rows": rows}
        _w(p, json.dumps(out).encode())
        return out

    try:
        first = page(1)
    except Exception as e:  # noqa: BLE001
        if str(e) != "offline":
            _log_fail(f"api_adv:{sid}", "page1", e)
        return []
    rows = list(first["rows"])
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(page, n): n for n in range(2, first["pages"] + 1)}
        for f in as_completed(futs):
            try:
                rows += f.result()["rows"]
            except Exception as e:  # noqa: BLE001
                if str(e) != "offline":
                    _log_fail(f"api_adv:{sid}", f"page{futs[f]}", e)
    return rows


# ---------------------------------------------------------------- build
def _clean(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s or None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--skip-api", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-age", type=float, default=None, help="re-download zips older than N days")
    a = ap.parse_args()
    t0 = time.time()
    off = a.build_only

    srcs = sources(off)
    inds = indicator_list(off)
    db_name = {sid: s["name"].strip() for sid, s in srcs.items()} | EXTRA_DB
    last_upd = {sid: s.get("lastupdated") for sid, s in srcs.items()}

    # ---- route 1
    if not off:
        download_bulk(a.max_age, a.workers)
    cand = []  # (sid, route, long df with ts-less rows)
    bulk_meta: dict[str, dict] = {}
    for sid, zname in BULK.items():
        p = CACHE / "bulk" / zname
        if not p.exists():
            continue
        try:
            long, meta = parse_bulk(sid, p)
        except Exception as e:  # noqa: BLE001
            print(f"  [parse FAIL] {zname}: {e}")
            _log_fail("parse", zname, e)
            continue
        long["sid"], long["route"] = sid, "DataBank bulk CSV"
        long["cid"] = None
        bulk_meta[sid] = meta
        cand.append(long)
        print(f"  [bulk] {zname:<30} BRA series {long.indicator_id.nunique():>6,}  obs {len(long):>8,}")

    # ---- route 2
    api_sids = [sid for sid in srcs if sid not in BULK and sid not in SKIP]
    home_ids: dict[str, list] = {}
    for i in inds.values():
        home_ids.setdefault(i["source"]["id"], []).append(i["id"])
    api_fail = 0
    if not a.skip_api:
        for sid in api_sids:
            ids = sorted(home_ids.get(sid, []))
            if not ids:
                continue
            rows, nf = fetch_api(sid, ids, a.workers, off)
            if nf:  # indicator route incomplete -> whole-source advanced query
                adv = fetch_advanced(sid, a.workers, off)
                if adv:
                    have = {(r["indicator"]["id"], r["date"]) for r in rows}
                    rows += [r for r in adv if (r["indicator"]["id"], r["date"]) not in have]
                    nf = 0
            api_fail += nf
            if rows:
                df = pd.DataFrame({
                    "indicator_id": [r["indicator"]["id"] for r in rows],
                    "name": [r["indicator"]["value"] for r in rows],
                    "period": [r["date"] for r in rows],
                    "value": [float(r["value"]) for r in rows],
                    "cid": [r["country"].get("id") for r in rows],
                    "unit_obs": [r.get("unit") or None for r in rows],
                    "obs_status": [r.get("obs_status") or None for r in rows]})
                df["sid"], df["route"] = sid, "API v2"
                cand.append(df)
            print(f"  [api] {sid:>3} {db_name.get(sid, '?')[:45]:<45} ids {len(ids):>5}  "
                  f"BRA obs {len(rows):>7,}  missing chunks {nf}")

    allc = pd.concat(cand, ignore_index=True)
    for c in ("unit_obs", "obs_status"):
        if c not in allc:
            allc[c] = None

    # ---- one series per indicator: home source, else WDI, else BULK order
    order = {sid: i for i, sid in enumerate(BULK)}
    home = {k: v["source"]["id"] for k, v in inds.items()}
    pairs = allc[["indicator_id", "sid"]].drop_duplicates()
    pairs["rank"] = [0 if home.get(i) == s else 1 + order.get(s, 99) for i, s in
                     zip(pairs.indicator_id, pairs.sid)]
    chosen = pairs.sort_values("rank").drop_duplicates("indicator_id")
    allc = allc.merge(chosen[["indicator_id", "sid"]], on=["indicator_id", "sid"])
    print(f"  indicators with Brazil data: {len(chosen):,} "
          f"(home source {int((chosen['rank'] == 0).sum()):,}, fallback {int((chosen['rank'] > 0).sum()):,})")

    # ---- ids
    styles = id_style(sorted(set(allc.sid)), inds, off)
    pp = {p: parse_period(p) for p in allc["period"].unique()}
    allc["date"] = allc["period"].map(lambda p: pp[p][0])
    allc["freq"] = allc["period"].map(lambda p: pp[p][1])
    allc = allc[allc["date"].notna()].copy()
    # one freq per series: an indicator carrying several (GEM: A+Q+M) keeps the plain
    # (Dateno) id for annual and gets <IND>_Q / <IND>_M for the others.
    multi = allc.groupby("indicator_id")["freq"].transform("nunique") > 1
    split = multi & (allc["freq"] != "A")
    allc.loc[split, "indicator_id"] = allc.loc[split, "indicator_id"] + "_" + allc.loc[split, "freq"]
    suffix = allc["cid"].where(allc["cid"].notna(), allc["sid"].map(lambda s: styles.get(s, "BR")))
    allc["ts_id"] = allc["indicator_id"] + "." + suffix

    obs = pd.DataFrame({
        "ns": NS, "ts_id": allc["ts_id"], "indicator_id": allc["indicator_id"],
        "date": allc["date"], "freq": allc["freq"], "value": allc["value"],
        "unit": allc["unit_obs"], "obs_status": allc["obs_status"], "classif1": None,
        "classif2": None,
        "obs_source": "World Bank " + allc["route"] + ": " + allc["sid"].map(db_name).fillna("?") + " " + TAG})

    # ---- catalog
    cat_rows = []
    first = allc.drop_duplicates("ts_id")
    for r in first.itertuples():
        base = re.sub(r"_[QM]$", "", r.indicator_id) if r.indicator_id not in inds else r.indicator_id
        m = bulk_meta.get(r.sid, {}).get(base, {})
        api = inds.get(base, {})
        name = _clean(m.get("Indicator Name")) or _clean(api.get("name")) or _clean(r.name)
        org = _clean(m.get("Source")) or _clean(api.get("sourceOrganization"))
        defin = (_clean(m.get("Long definition")) or _clean(m.get("Short definition"))
                 or _clean(api.get("sourceNote")))
        if org:
            defin = f"{defin} Source: {org}" if defin else f"Source: {org}"
        topic = _clean(m.get("Topic")) or "; ".join(t.get("value", "").strip() for t in api.get("topics", [])
                                                   if t.get("value")) or db_name.get(r.sid)
        unit = _clean(m.get("Unit of measure")) or _clean(api.get("unit"))
        if not unit and name and _UNIT_IN_NAME.search(name):
            unit = _UNIT_IN_NAME.search(name).group(1)
        cat_rows.append({
            "ns": NS, "ts_id": r.ts_id, "indicator_id": r.indicator_id, "table": r.indicator_id,
            "name": name, "indicator_name": name, "source_id": r.sid,
            "database": db_name.get(r.sid), "source": f"World Bank {r.route} {TAG}",
            "topic": topic, "unit": unit, "definition": defin,
            "periodicity": _clean(m.get("Periodicity")) or {"A": "Annual", "Q": "Quarterly",
                                                            "M": "Monthly"}.get(r.freq),
            "license": _clean(m.get("License Type")) or "CC BY-4.0",
            "last_update": last_upd.get(r.sid)})
    cat = pd.DataFrame(cat_rows)
    for c in CAT_COLS:
        if c not in cat:
            cat[c] = None
    print(f"  built: {cat.shape[0]:,} series, {len(obs):,} obs")

    obs_all, cat_all = merge_into_dateno(NS, obs, cat)
    summary(obs_all, cat_all, NS, t0)
    print("---- sanity ----")
    tier1_check(obs_all)
    spot(cat_all)
    if api_fail:
        print(f"[warn] {api_fail} API jobs missing (mostly sources with no Brazil coverage, see Gotchas; transient 502s fill on rerun); see {CACHE/'failures.jsonl'}")
    print("\nrun: .venv/bin/python ingest/worldbank_bulk.py [--build-only] [--skip-api]")
    return 0


SPOT = [("NY.GDP.MKTP.KD.ZG.BR", 2023, 2.9, 3.3, "GDP growth %"),
        ("SP.POP.TOTL.BR", 2023, 205e6, 217e6, "population"),
        ("FP.CPI.TOTL.ZG.BR", 2023, 4.4, 4.8, "CPI inflation %"),
        ("SP.DYN.LE00.IN.BR", 2023, 73, 77, "life expectancy"),
        ("EG.ELC.ACCS.ZS.BR", 2022, 99, 100.01, "electricity access %"),
        ("SL.UEM.TOTL.ZS.BR", 2023, 7.5, 8.5, "unemployment (ILO modeled) %"),
        ("DT.DOD.DECT.CD.BR", 2023, 5e11, 7.5e11, "external debt stocks US$"),
        ("EN.GHG.CO2.MT.CE.AR5.BR", 2023, 350, 600, "CO2 excl. LULUCF Mt")]


def spot(cat: pd.DataFrame) -> None:
    from pandas import read_parquet
    from _dateno_mirror import OUT
    obs = read_parquet(OUT / "observations.parquet", filters=[("ts_id", "in", [s[0] for s in SPOT])])
    for ts, yr, lo, hi, lab in SPOT:
        g = obs[(obs.ts_id == ts) & (pd.to_datetime(obs.date).dt.year == yr)]
        v = g["value"].iloc[0] if len(g) else None
        ok = v is not None and lo <= v <= hi
        print(f"  [{'OK ' if ok else 'BAD'}] {lab:<30} {ts:<26} {yr}: {v if v is None else f'{v:,.4g}'}"
              f"  (expect {lo:,.4g}..{hi:,.4g})")


if __name__ == "__main__":
    raise SystemExit(main())
