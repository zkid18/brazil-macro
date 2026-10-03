"""dateno_bulk.py — pull EVERY Brazil time series Dateno's statsdb carries (wb + ilostat).

Backbone ingest for the Brazil macro platform. Lands two compact parquets:

    warehouse/bronze/dateno/observations.parquet   long: one row per (series, dims, date)
    warehouse/bronze/dateno/catalog.parquet        one row per Brazil series + indicator metadata

Run
---
    set -a; source .env; set +a
    .venv/bin/python ingest/dateno_bulk.py                      # enumerate -> meta -> values -> build
    .venv/bin/python ingest/dateno_bulk.py --budget 180         # stop after 180 API calls (daily quota)
    .venv/bin/python ingest/dateno_bulk.py --mode probe         # low-request enumeration (see below)
    .venv/bin/python ingest/dateno_bulk.py --build-only         # no network: rebuild parquets from cache
    .venv/bin/python ingest/dateno_bulk.py --seed-tier1 --build-only   # reuse the 22 tier-1 CSVs as cache

Every stage is resumable: pages, metadata and exports are cached one file per
request under warehouse/bronze/raw/dateno/ (gitignored) and skipped on rerun.

API (base https://api.dateno.io/statsdb/0.1, header `apikey: $DATENO_API_KEY`)
--------------------------------------------------------------------------
    GET /ns                                   -> namespaces: wb, ilostat (only these two)
    GET /ns/{ns}/indicators?start=&limit=     -> {totals, items:[{id, table, name, metadata:[]}]}
                                                 totals: wb 18,001 / ilostat 1,057
    GET /ns/{ns}/ts?start=&limit=             -> {totals, items:[{id, indicator, table, name}]}
                                                 totals: wb 3,812,383 / ilostat 135,609
    GET /ns/{ns}/indicators/{ind}             -> indicator metadata as [{name, value}] pairs
    GET /ns/{ns}/ts/{ts_id}                   -> same metadata, per series (not needed)
    GET /ns/{ns}/ts/{ts_id}/export.csv|.json  -> values

Paging: `limit` max is 1000 (>1000 returns 422). No server-side filters: country=,
q=, search=, indicator=, table=, id=, name= are all silently ignored, so finding
Brazil means paging the whole namespace (3,813 wb pages + 136 ilostat pages,
~2-4 s each, deeper offsets slower; ~2 pages/s at 8 workers) -- or `--mode probe`.

Brazil filter / ids:
  * list items: `indicator` is a literal placeholder ("indicator_id"/"indicator"),
    so indicator_id = ts_id.rsplit(".", 1)[0]. `table` == indicator for wb; for
    ilostat table = indicator + "_A" (annual collection).
  * wb country suffix is ISO-2 for WDI-family sources (NY.GDP.MKTP.KD.ZG.BR) and
    ISO-3 for others (LAC Equity Lab 1.0.HCount.1.90usd.BRA); ilostat is ISO-3.
    The reliable discriminator is name.endswith(" - Brazil"); `pages` mode uses
    the name AND reports id-suffix mismatches.
  * `--mode probe` skips the 3.8M enumeration: list indicators (19+2 pages), then
    try {ind}.BR then {ind}.BRA export directly (404 = no Brazil series). Fewer
    requests total, but it trusts the suffix convention instead of the name.

Export formats differ by namespace:
  wb:      indicator_id,indicator_name,country_id,country_name,countryiso3code,date,value,unit,obs_status,decimal
  ilostat: ref_area,indicator,source,classif1[,classif2],time,obs_value[,obs_status],note_*...
           -> ILO series are disaggregated (sex/age/...): several rows per date, kept
              as classif1/classif2 columns. wb rows include null values (gaps); dropped.
  Periods: "2023" -> 2023-12-31 (A); "2023Q1" -> quarter end (Q); "2023M01" -> month end (M).

Metadata fields:
  wb:      IndicatorName, Source, Topic, Periodicity, Unitofmeasure, Longdefinition/
           Shortdefinition, source_id (WB database id -> name via keyless
           api.worldbank.org/v2/sources, cached), License_Type. Pairs repeat; first non-empty wins.
  ilostat: indicator.label, database.label, subject.label, freq.label, description (HTML),
           data.start/end, last.update.

Gotchas:
  * 403 for the default Python-urllib User-Agent; we send _http.UA.
  * QUOTA: the key in .env is a free tier -- RateLimit-Limit 200/day, 500/month
    (headers X-RateLimit-Limit-Day / -Month, Retry-After in seconds). A full Brazil
    pull needs ~35k requests (pages ~3.9k + metadata ~17k + exports ~16k), so it
    needs a paid/bulk key. On a 429 with a long Retry-After this script stops
    cleanly (all progress is cached) instead of retrying -- _http.get_bytes would
    burn the remaining quota on blind retries, which is why requests go through
    `_call` here (still using _http's certifi CTX and UA).

Runtime: dominated by quota, not bandwidth. Without a quota, ~30 min for
enumeration at 8 workers + ~15-20k exports at ~10/s. --build-only takes seconds.
"""
from __future__ import annotations

import argparse, json, os, random, re, shutil, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import BRONZE, CTX, RAW_CACHE, ROOT, UA, get_json  # noqa: E402

BASE = os.environ.get("DATENO_API_BASE", "https://api.dateno.io").rstrip("/") + "/statsdb/0.1"
API_KEY = os.environ.get("DATENO_API_KEY")
CACHE = RAW_CACHE / "dateno"
OUT = BRONZE / "dateno"
PAGE = 1000  # API max
NAMESPACES = ("wb", "ilostat")
SUFFIX = " - Brazil"


# ---------------------------------------------------------------- transport
class QuotaExhausted(RuntimeError):
    pass


class Client:
    """Thread-safe, quota-aware GET. Never logs the key (header only, not in URLs)."""

    def __init__(self, budget: int | None):
        self.budget, self.used = budget, 0
        self.lock = threading.Lock()
        self.stopped: str | None = None
        self.remaining_day: str | None = None

    def get(self, path: str, accept: str = "application/json") -> bytes | None:
        """Return body, None on 404. Raises QuotaExhausted / RuntimeError."""
        for attempt in range(5):
            with self.lock:
                if self.stopped:
                    raise QuotaExhausted(self.stopped)
                if self.budget is not None and self.used >= self.budget:
                    self.stopped = f"request budget {self.budget} reached"
                    raise QuotaExhausted(self.stopped)
                self.used += 1
            req = urllib.request.Request(BASE + path, headers={
                "apikey": API_KEY or "", "User-Agent": UA, "Accept": accept})
            try:
                with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
                    self.remaining_day = r.headers.get("X-RateLimit-Remaining-Day", self.remaining_day)
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code == 429:
                    wait = int(e.headers.get("Retry-After") or 60)
                    if wait > 120:
                        with self.lock:
                            self.stopped = (f"429 quota exhausted (day limit "
                                            f"{e.headers.get('X-RateLimit-Limit-Day')}, month remaining "
                                            f"{e.headers.get('X-RateLimit-Remaining-Month')}); "
                                            f"resets in {wait/3600:.1f} h")
                        raise QuotaExhausted(self.stopped)
                    time.sleep(wait + random.random())
                    continue
                if e.code in (500, 502, 503, 504):
                    time.sleep(2 ** attempt + random.random())
                    continue
                raise RuntimeError(f"HTTP {e.code} {path}")
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                time.sleep(2 ** attempt + random.random())
                last = e
        raise RuntimeError(f"gave up {path}: {locals().get('last', 'retries')}")


def _atomic_write(p: Path, data: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(p)


def _pool(fn, jobs, workers: int, label: str):
    """Run fn over jobs; returns (n_ok, failures list). Stops early on quota."""
    ok, fails, t0 = 0, [], time.time()
    if not jobs:
        return 0, []
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fn, j): j for j in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
                ok += 1
            except QuotaExhausted:
                pass
            except Exception as e:  # noqa: BLE001
                fails.append({"stage": label, "job": str(futs[f]), "error": str(e)[:300]})
            if i % 200 == 0:
                print(f"  [{label}] {i}/{len(jobs)} ok={ok} fail={len(fails)} {time.time()-t0:.0f}s")
    return ok, fails


# ---------------------------------------------------------------- stage a: enumerate
def is_brazil(item: dict) -> bool:
    return str(item.get("name", "")).endswith(SUFFIX)


def enumerate_pages(cli: Client, ns: str, workers: int) -> None:
    d = CACHE / "enum" / ns
    first = json.loads(cli.get(f"/ns/{ns}/ts?start=0&limit=1"))
    total = first["totals"]
    todo = [s for s in range(0, total, PAGE) if not (d / f"{s:08d}.json").exists()]
    print(f"[enum:{ns}] {total:,} series, {total // PAGE + 1} pages, {len(todo)} to fetch")

    def one(start: int):
        body = json.loads(cli.get(f"/ns/{ns}/ts?start={start}&limit={PAGE}"))
        items = body["items"]
        br = [{"id": i["id"], "table": i.get("table"), "name": i["name"]} for i in items
              if is_brazil(i) or i["id"].endswith((".BR", ".BRA"))]
        _atomic_write(d / f"{start:08d}.json", json.dumps({"n": len(items), "brazil": br}).encode())

    _pool(one, todo, workers, f"enum:{ns}")


def enumerate_probe(cli: Client, ns: str, workers: int) -> None:
    """List indicators, then probe {ind}.BR / {ind}.BRA exports (export doubles as values fetch)."""
    ind_file = CACHE / "indicators" / f"{ns}.json"
    if not ind_file.exists():
        first = json.loads(cli.get(f"/ns/{ns}/indicators?start=0&limit={PAGE}"))
        items = first["items"]
        for s in range(PAGE, first["totals"], PAGE):
            items += json.loads(cli.get(f"/ns/{ns}/indicators?start={s}&limit={PAGE}"))["items"]
        _atomic_write(ind_file, json.dumps(items).encode())
    inds = json.loads(ind_file.read_text())
    d = CACHE / "probe" / ns
    suffixes = (".BRA",) if ns == "ilostat" else (".BR", ".BRA")
    todo = [i for i in inds if not (d / f"{_safe(i['id'])}.json").exists()]
    print(f"[probe:{ns}] {len(inds)} indicators, {len(todo)} to probe")

    def one(ind: dict):
        found = None
        for suf in suffixes:
            ts = ind["id"] + suf
            vp = _values_path(ns, ts)
            if vp.exists():
                found = ts
                break
            body = cli.get(f"/ns/{ns}/ts/{ts}/export.csv", accept="text/csv")
            if body is not None:
                _atomic_write(vp, body)
                found = ts
                break
        name = (ind.get("name") or ind["id"]) + SUFFIX if found else None
        _atomic_write(d / f"{_safe(ind['id'])}.json",
                      json.dumps({"id": found, "table": ind.get("table"), "name": name}).encode())

    _pool(one, todo, workers, f"probe:{ns}")


def load_enumeration() -> pd.DataFrame:
    rows, mism = [], 0
    for ns in NAMESPACES:
        for p in sorted((CACHE / "enum" / ns).glob("*.json")):
            for it in json.loads(p.read_text())["brazil"]:
                if not is_brazil(it):
                    mism += 1  # id suffix matched, name didn't (e.g. another country coded BR?)
                    continue
                rows.append({"ns": ns, **it})
        for p in sorted((CACHE / "probe" / ns).glob("*.json")):
            it = json.loads(p.read_text())
            if it["id"]:
                rows.append({"ns": ns, **it})
    if mism:
        print(f"[enum] {mism} items with .BR/.BRA suffix but name not '{SUFFIX}' -> excluded")
    df = pd.DataFrame(rows, columns=["ns", "id", "table", "name"]).drop_duplicates(["ns", "id"])
    return df.rename(columns={"id": "ts_id"})


# ---------------------------------------------------------------- stage b: metadata
def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


def _meta_path(ns: str, ind: str) -> Path:
    return CACHE / "meta" / ns / f"{_safe(ind)}.json"


def _values_path(ns: str, ts: str) -> Path:
    return CACHE / "values" / ns / f"{_safe(ts)}.csv"


def fetch_meta(cli: Client, series: pd.DataFrame, workers: int) -> list:
    jobs = sorted({(r.ns, r.indicator_id) for r in series.itertuples()
                   if not _meta_path(r.ns, r.indicator_id).exists()})
    print(f"[meta] {series.indicator_id.nunique()} indicators, {len(jobs)} to fetch")

    def one(job):
        ns, ind = job
        body = cli.get(f"/ns/{ns}/indicators/{ind}")
        _atomic_write(_meta_path(ns, ind), body if body is not None else b'{"metadata": []}')

    return _pool(one, jobs, workers, "meta")[1]


# ---------------------------------------------------------------- stage c: values
def fetch_values(cli: Client, series: pd.DataFrame, workers: int, tier1: set) -> list:
    todo = series[[not _values_path(r.ns, r.ts_id).exists() and
                   not _values_path(r.ns, r.ts_id).with_suffix(".404").exists()
                   for r in series.itertuples()]].copy()
    # priority: tier-1 ids, then ILO, then wb ISO-2 (WDI family), then the rest
    todo["prio"] = [0 if t in tier1 else 1 if ns == "ilostat" else 2 if t.endswith(".BR") else 3
                    for ns, t in zip(todo.ns, todo.ts_id)]
    todo = todo.sort_values(["prio", "ts_id"])
    print(f"[values] {len(series)} series, {len(todo)} to fetch")

    def one(job):
        ns, ts = job
        body = cli.get(f"/ns/{ns}/ts/{ts}/export.csv", accept="text/csv")
        if body is None:
            _atomic_write(_values_path(ns, ts).with_suffix(".404"), b"")
            raise RuntimeError("404 on export")
        _atomic_write(_values_path(ns, ts), body)

    return _pool(one, list(zip(todo.ns, todo.ts_id)), workers, "values")[1]


# ---------------------------------------------------------------- stage d: build
_Q_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}


def parse_period(s: str) -> tuple[str | None, str]:
    s = str(s).strip()
    if re.fullmatch(r"\d{4}", s):
        return f"{s}-12-31", "A"
    m = re.fullmatch(r"(\d{4})-?Q([1-4])", s)
    if m:
        return f"{m[1]}-{_Q_END[m[2]]}", "Q"
    m = re.fullmatch(r"(\d{4})-?M?(\d{2})", s)
    if m:
        return (pd.Timestamp(f"{m[1]}-{m[2]}-01") + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d"), "M"
    try:
        return pd.Timestamp(s).strftime("%Y-%m-%d"), "D"
    except Exception:  # noqa: BLE001
        return None, "?"


def read_export(ns: str, ts: str, path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if df.empty:
        return df
    if ns == "wb" or "value" in df.columns:
        out = pd.DataFrame({"period": df["date"], "value": df["value"],
                            "unit": df.get("unit", ""), "obs_status": df.get("obs_status", ""),
                            "classif1": "", "classif2": "", "obs_source": "",
                            "export_name": df.get("indicator_name", "")})
    else:  # ilostat
        out = pd.DataFrame({"period": df["time"], "value": df["obs_value"],
                            "unit": "", "obs_status": df.get("obs_status", ""),
                            "classif1": df.get("classif1", ""), "classif2": df.get("classif2", ""),
                            "obs_source": df.get("source", ""), "export_name": ""})
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out[out["value"].notna()]
    parsed = out["period"].map(parse_period)
    out["date"] = [p[0] for p in parsed]
    out["freq"] = [p[1] for p in parsed]
    out = out[out["date"].notna()]
    out.insert(0, "ts_id", ts)
    out.insert(0, "ns", ns)
    return out.drop(columns="period")


def _meta_dict(ns: str, ind: str) -> dict:
    p = _meta_path(ns, ind)
    if not p.exists():
        return {}
    md: dict = {}
    for kv in json.loads(p.read_text()).get("metadata", []):
        if kv.get("value") not in (None, "") and kv["name"] not in md:
            md[kv["name"]] = kv["value"]
    md["_name"] = json.loads(p.read_text()).get("name")
    return md


def _wb_sources() -> dict:
    p = CACHE / "wb_sources.json"
    if not p.exists():
        try:
            r = get_json("https://api.worldbank.org/v2/sources?format=json&per_page=500")
            _atomic_write(p, json.dumps({s["id"]: s["name"].strip() for s in r[1]}).encode())
        except Exception as e:  # noqa: BLE001
            print(f"[warn] WB sources lookup failed: {e}")
            return {}
    return json.loads(p.read_text())


def _strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip() if isinstance(s, str) else s


def catalog_fields(ns: str, ind: str, wb_src: dict) -> dict:
    m = _meta_dict(ns, ind)
    if ns == "wb":
        return {"indicator_name": m.get("IndicatorName"), "source_id": m.get("source_id"),
                "database": wb_src.get(m.get("source_id"), None), "source": m.get("Source"),
                "topic": m.get("Topic"), "unit": m.get("Unitofmeasure"),
                "definition": m.get("Longdefinition") or m.get("Shortdefinition"),
                "periodicity": m.get("Periodicity"), "license": m.get("License_Type"),
                "last_update": None}
    return {"indicator_name": m.get("indicator.label") or m.get("_name"), "source_id": m.get("database"),
            "database": m.get("database.label"), "source": "ILOSTAT",
            "topic": m.get("subject.label"), "unit": None,
            "definition": _strip_html(m.get("description")), "periodicity": m.get("freq.label"),
            "license": None, "last_update": m.get("last.update")}


def _headline(g: pd.DataFrame) -> pd.DataFrame:
    """ILO: pick the total/aggregate disaggregation for last_value."""
    if (g["classif1"] == "").all():
        return g
    tot = g[g["classif1"].str.contains(r"_T$|TOTAL|_TOTAL", regex=True) &
            ((g["classif2"] == "") | g["classif2"].str.contains(r"_T$|TOTAL|AGE_YTHADULT_YGE15", regex=True))]
    if not tot.empty:
        return tot
    first = g.sort_values(["classif1", "classif2"]).iloc[0]
    return g[(g.classif1 == first.classif1) & (g.classif2 == first.classif2)]


def build(series: pd.DataFrame, t0: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    # include cached exports even if enumeration is partial (e.g. seeded tier-1)
    known = set(zip(series.ns, series.ts_id))
    extra = []
    for ns in NAMESPACES:
        for p in (CACHE / "values" / ns).glob("*.csv"):
            if (ns, p.stem) not in known:
                extra.append({"ns": ns, "ts_id": p.stem, "table": None, "name": None,
                              "indicator_id": p.stem.rsplit(".", 1)[0]})
    if extra:
        series = pd.concat([series, pd.DataFrame(extra)], ignore_index=True)

    frames, empty, missing, export_names = [], [], 0, {}
    for r in series.itertuples():
        p = _values_path(r.ns, r.ts_id)
        if not p.exists():
            missing += 1
            continue
        df = read_export(r.ns, r.ts_id, p)
        if df.empty:
            empty.append(r.ts_id)
            continue
        df["indicator_id"] = r.indicator_id
        export_names[(r.ns, r.ts_id)] = next((x for x in df.pop("export_name") if x), None)
        frames.append(df)
    obs = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["ns", "ts_id", "indicator_id", "date", "freq", "value", "unit", "obs_status",
                 "classif1", "classif2", "obs_source"])
    obs = obs[["ns", "ts_id", "indicator_id", "date", "freq", "value", "unit", "obs_status",
               "classif1", "classif2", "obs_source"]]
    for c in ("unit", "obs_status", "classif1", "classif2", "obs_source"):
        obs[c] = obs[c].replace("", None)
    obs["date"] = pd.to_datetime(obs["date"]).dt.date
    obs = obs.sort_values(["ns", "ts_id", "classif1", "classif2", "date"], na_position="first",
                          ignore_index=True)

    wb_src = _wb_sources()
    rows = []
    obs_g = {k: g for k, g in obs.groupby(["ns", "ts_id"], sort=False)}
    for r in series.itertuples():
        g = obs_g.get((r.ns, r.ts_id))
        if g is None:
            continue
        f = catalog_fields(r.ns, r.indicator_id, wb_src)
        h = _headline(g.fillna({"classif1": "", "classif2": ""}))
        last = h.sort_values("date").iloc[-1]
        name = r.name if isinstance(r.name, str) else None
        if name and name.endswith(SUFFIX):
            name = name[: -len(SUFFIX)]
        rows.append({"ns": r.ns, "ts_id": r.ts_id, "indicator_id": r.indicator_id,
                     "table": r.table, "name": name or f["indicator_name"] or export_names.get((r.ns, r.ts_id)),
                     **f,
                     "unit": f["unit"] or (g["unit"].dropna().iloc[0] if g["unit"].notna().any() else None),
                     "freq": g["freq"].mode().iloc[0], "first_date": g["date"].min(),
                     "last_date": g["date"].max(), "n_obs": len(g),
                     "n_dims": len(g[["classif1", "classif2"]].drop_duplicates()),
                     "last_value": float(last["value"])})
    cat = pd.DataFrame(rows)
    STR = ["ns", "ts_id", "indicator_id", "table", "name", "indicator_name", "source_id", "database",
           "source", "topic", "unit", "definition", "periodicity", "license", "last_update", "freq"]
    for c in STR:
        if c in cat:
            cat[c] = cat[c].astype("string")
    OUT.mkdir(parents=True, exist_ok=True)
    obs.to_parquet(OUT / "observations.parquet", compression="zstd", index=False)
    cat.to_parquet(OUT / "catalog.parquet", compression="zstd", index=False)

    print("\n================ dateno_bulk summary ================")
    print(f"series found (enumerated + cached): {len(series):,}")
    print(f"  fetched with data: {len(cat):,}   empty (dropped): {len(empty):,}   "
          f"not yet fetched: {missing:,}")
    print(f"observations: {len(obs):,}   ->  {OUT/'observations.parquet'} "
          f"({(OUT/'observations.parquet').stat().st_size/1e6:.2f} MB)")
    print(f"catalog rows: {len(cat):,}   ->  {OUT/'catalog.parquet'}")
    if len(obs):
        yrs = pd.Series([d.year for d in obs["date"]])
        dec = (yrs // 10 * 10).value_counts().sort_index()
        print("coverage by decade (obs):", ", ".join(f"{k}s:{v:,}" for k, v in dec.items()))
        last = cat["last_date"].map(lambda d: d.year).value_counts().sort_index().tail(8)
        print("series by last year:", ", ".join(f"{k}:{v}" for k, v in last.items()))
        print("freq:", obs["freq"].value_counts().to_dict(), " ns:", cat["ns"].value_counts().to_dict())
        print("top databases:", cat["database"].fillna("?").value_counts().head(15).to_dict())
        top = cat["topic"].fillna("?").str.split(":").str[0].str.strip()
        print("top topics:", top.value_counts().head(15).to_dict())
    print(f"run time: {time.time()-t0:.1f}s")
    return obs, cat


# ---------------------------------------------------------------- sanity
def sanity(obs: pd.DataFrame, cat: pd.DataFrame, tier1: dict, seeded: bool) -> None:
    print("\n---- sanity: tier-1 vs warehouse/bronze/<ts_id>.csv ----")
    bad = 0
    for metric, ts in tier1.items():
        ref_p = BRONZE / f"{ts}.csv"
        got = obs[obs.ts_id == ts]
        if got.empty:
            print(f"  [MISSING] {metric} {ts}")
            bad += 1
            continue
        ref = pd.read_csv(ref_p).dropna(subset=["value"])
        ref = dict(zip(ref["date"].astype(str).str[:4], ref["value"].astype(float)))
        mine = dict(zip([str(d.year) for d in got["date"]], got["value"]))
        diff = [y for y in ref if y not in mine or abs(ref[y] - mine[y]) > 1e-9 * max(1, abs(ref[y]))]
        if diff or len(mine) != len(ref):
            bad += 1
            print(f"  [DIFF] {ts}: {len(diff)} years differ, n {len(mine)} vs {len(ref)}")
    print(f"  tier-1: {len(tier1) - bad}/{len(tier1)} identical"
          + ("  (NB: seeded from those same CSVs -> checks parsing only)" if seeded else ""))
    if len(cat):
        print("---- spot check (5 random series, last value) ----")
        for r in cat.sample(min(5, len(cat)), random_state=7).itertuples():
            print(f"  {r.ts_id:<28} {str(r.name)[:60]:<60} {r.last_date} = {r.last_value:,.4g}")


def load_tier1() -> dict:
    import yaml
    t1 = yaml.safe_load((ROOT / "registry" / "source_map.yml").read_text()).get("tier1", {})
    return {k: v["ts_id"] for k, v in t1.items()}


def seed_tier1(tier1: dict) -> None:
    """The 22 tier-1 CSVs are verbatim Dateno wb exports -- reuse them, saving quota."""
    for ts in tier1.values():
        src, dst = BRONZE / f"{ts}.csv", _values_path("wb", ts)
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ns", default="wb,ilostat")
    ap.add_argument("--mode", choices=["pages", "probe"], default="pages")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--budget", type=int, default=None, help="max API calls this run")
    ap.add_argument("--skip-meta", action="store_true")
    ap.add_argument("--build-only", action="store_true", help="no network; rebuild from cache")
    ap.add_argument("--seed-tier1", action="store_true", help="copy tier-1 bronze CSVs into cache")
    a = ap.parse_args()
    t0 = time.time()
    tier1 = load_tier1()
    if a.seed_tier1:
        seed_tier1(tier1)

    fails: list = []
    cli = Client(a.budget)
    if not a.build_only:
        if not API_KEY:
            print("DATENO_API_KEY not set: `set -a; source .env; set +a`", file=sys.stderr)
            return 2
        try:
            for ns in a.ns.split(","):
                (enumerate_probe if a.mode == "probe" else enumerate_pages)(cli, ns, a.workers)
        except QuotaExhausted:
            pass
    series = load_enumeration()
    series["indicator_id"] = series["ts_id"].str.rsplit(".", n=1).str[0]
    if not a.build_only and not cli.stopped:
        if not a.skip_meta:
            fails += fetch_meta(cli, series, a.workers)
        if not cli.stopped:
            fails += fetch_values(cli, series, a.workers, set(tier1.values()))
    if fails:
        CACHE.mkdir(parents=True, exist_ok=True)
        with open(CACHE / "failures.jsonl", "a") as fh:
            for f in fails:
                fh.write(json.dumps(f) + "\n")
    if cli.stopped:
        print(f"\n[STOPPED] {cli.stopped}. {cli.used} calls made this run; progress cached, rerun to resume.")
    print(f"API calls this run: {cli.used}, failures logged: {len(fails)}")

    obs, cat = build(series, t0)
    sanity(obs, cat, tier1, seeded=a.seed_tier1)
    print("\nrun: set -a; source .env; set +a; .venv/bin/python ingest/dateno_bulk.py [--budget N] [--mode probe]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
