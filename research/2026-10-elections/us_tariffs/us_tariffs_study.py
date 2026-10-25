"""US tariffs on Brazil under Lula III: what they did (product x destination x month), and what escalation would do.

Sections follow plan.md: 0 anchors, 1 pulls, 3 timeline/coverage, 4 exposure, 5 effects, 6 escalation matrix, 7 charts.
Run:  .venv/bin/python us_tariffs_study.py <step> [<step> ...]   steps: anchors pulls_comex pulls_fr pulls_hts pulls_bls
      pulls_cotahist pulls_sidra pulls_comtrade timeline exposure effects matrix charts all

Pitfalls (plan §7, copied):
- ComexStat dates are first-of-month (year, monthNumber); the warehouse stops at 2026-08, the live API at 2026-09.
- Comtrade primaryValue is CIF for imports (use fobvalue against ComexStat FOB) and lags shipments by 1-2 months.
- HS6 mapping is many-to-one (record partials).
- Crude is exempt but fell ~30% for non-tariff reasons: excluded from the control group in the main spec; both reported.
- Coffee and beef prices roughly doubled in 2025: use unit-value ratios, not levels.
- The Nov-2025 relief (EO 14361) and the Nov-14 all-country agricultural EO overlap (two tau changes).
- Section 122 applied to everyone (R4 wedge vs competitors ~ 0).
- The forced-labour 12.5% applies to many economies (relative wedge, not absolute, for the mirror).
- 2026 BRL appreciation (6.10 -> 4.98) and the Brent shock confound 2026 levels.
- The aircraft-232 clock (~2027-01-05) and the Graham Act list date (2026-10-18) are inside the forecast horizon.
- Placebo windows: exclude Mar 2020-Jun 2021 in a robustness cell.
- v_annual 2026 is incomplete; never write to the warehouse; sleep 11 s (ComexStat) and 2.5 s (Comtrade).
- numpy-only estimators: OLS by np.linalg.lstsq, cluster bootstrap, permutation/placebo p-values, seed 0. Plotly HTML only.
"""
import json, os, sys, time, ssl, zipfile, io, re, glob, subprocess, urllib.request, urllib.error, urllib.parse
from pathlib import Path
import duckdb, numpy as np, pandas as pd

OUT = Path(__file__).resolve().parent
CACHE = OUT / "cache"
CH = OUT / "charts"
for d in [CACHE, CH, CACHE / "comexstat", CACHE / "comtrade", CACHE / "fr", CACHE / "hts", CACHE / "bls",
          CACHE / "cotahist", CACHE / "sidra"]:
    d.mkdir(parents=True, exist_ok=True)
WH = "/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb"
REVIEW_CH = OUT.parent / "review" / "charts"
SEED = 0
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa
    CTX = ssl.create_default_context()

RES_PATH = OUT / "results.json"
R = json.loads(RES_PATH.read_text()) if RES_PATH.exists() else {}
_R0 = json.dumps(R, sort_keys=True, default=str)
_R0 = json.loads(_R0)
SQLLOG = R.get("_sqllog", {})
APILOG = OUT / "api_calls.csv"


def save_results():
    """merge with the on-disk file: keys changed by this process overwrite, others are kept (parallel steps)."""
    R["_sqllog"] = SQLLOG
    disk = json.loads(RES_PATH.read_text()) if RES_PATH.exists() else {}
    for k, v in R.items():
        if k == "_sqllog":
            disk.setdefault("_sqllog", {}).update(v)
        elif k not in _R0 or json.dumps(_R0[k], sort_keys=True, default=str) != json.dumps(v, sort_keys=True, default=str):
            disk[k] = v
    R.update({k: v for k, v in disk.items() if k not in R})

    def conv(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, (pd.Timestamp,)):
            return str(o)[:10]
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)
    RES_PATH.write_text(json.dumps(disk, indent=1, default=conv, ensure_ascii=False))


# ---------------------------------------------------------------- warehouse (read-only)
_WCON = None


def wcon():
    global _WCON
    if _WCON is None:
        _WCON = duckdb.connect(WH, read_only=True)
    return _WCON


_CAT = None


def cat():
    global _CAT
    if _CAT is None:
        _CAT = wcon().sql("""SELECT c.series_id, c.source, max(o.date) last_date
                 FROM catalog c LEFT JOIN observations o USING(series_id) GROUP BY ALL""").df().set_index("series_id")
    return _CAT


def wq(sql, name=None):
    if name:
        SQLLOG[name] = sql.strip()
    return wcon().sql(sql).df()


def rec(key, value, series_id=None, sql=None, source=None, last_date=None, note=None, call=None):
    """every number: {value, series_id, source, last_date, sql} or the cache file / API call."""
    sids = [] if series_id is None else (series_id if isinstance(series_id, (list, tuple)) else [series_id])
    c = cat() if sids else None
    src = source or "; ".join(sorted({str(c.loc[s, "source"]) for s in sids if c is not None and s in c.index}))
    last = last_date or max([str(c.loc[s, "last_date"])[:10] for s in sids if c is not None and s in c.index] or [""])
    if isinstance(value, (np.floating, np.integer)):
        value = float(value)
    R[key] = {"value": value, "series_id": series_id, "source": src, "last_date": last, "sql": sql}
    if note:
        R[key]["note"] = note
    if call:
        R[key]["call"] = call
    return value


def log_call(endpoint, body, rows, nbytes, secs, cached):
    new = not APILOG.exists()
    with open(APILOG, "a") as f:
        if new:
            f.write("endpoint,body_or_url,rows,bytes,seconds,cached_file,ts\n")
        b = json.dumps(body) if not isinstance(body, str) else body
        f.write(",".join(['"' + str(x).replace('"', '""') + '"' for x in
                          [endpoint, b, rows, nbytes, round(secs, 1), cached, time.strftime("%Y-%m-%d %H:%M:%S")]]) + "\n")


def http(url, data=None, headers=None, timeout=120, method=None):
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()


# ---------------------------------------------------------------- 1.1 ComexStat
COMEX = "https://api-comexstat.mdic.gov.br/general"
COMEX_HDR = {"User-Agent": "brazil-macro-pipeline/1.0", "Content-Type": "application/json"}
_last_comex = [0.0]


def comex(name, body, force=False):
    fj = CACHE / "comexstat" / f"{name}.json"
    fp = CACHE / "comexstat" / f"{name}.parquet"
    if fp.exists() and not force:
        return pd.read_parquet(fp)
    data = json.dumps(body).encode()
    for attempt in range(1, 8):
        wait = 11 - (time.time() - _last_comex[0])
        if wait > 0:
            time.sleep(wait)
        t0 = time.time()
        try:
            req = urllib.request.Request(COMEX, data=data, headers=COMEX_HDR, method="POST")
            with urllib.request.urlopen(req, timeout=300, context=CTX) as r:
                raw = r.read()
            _last_comex[0] = time.time()
            rows = json.loads(raw)["data"]["list"]
            fj.write_bytes(raw)
            df = pd.DataFrame(rows)
            df.to_parquet(fp)
            log_call(COMEX, body, len(df), len(raw), time.time() - t0, str(fp.relative_to(OUT)))
            print(f"  comex {name}: {len(df)} rows, {len(raw)/1e6:.1f} MB, {time.time()-t0:.0f}s", flush=True)
            return df
        except urllib.error.HTTPError as e:
            _last_comex[0] = time.time()
            if e.code == 429:
                time.sleep(15 + 5 * attempt); continue
            print("  comex HTTP", e.code, name, e.read()[:200]); time.sleep(15)
        except Exception as e:  # noqa
            _last_comex[0] = time.time()
            print("  comex error", name, repr(e)[:200]); time.sleep(15)
    raise RuntimeError(f"comex {name} failed")


def comex_get(path):
    fp = CACHE / "comexstat" / ("tables_" + path.strip("/").replace("/", "_") + ".json")
    if fp.exists():
        return json.loads(fp.read_text())
    wait = 11 - (time.time() - _last_comex[0])
    if wait > 0:
        time.sleep(wait)
    t0 = time.time()
    raw = http("https://api-comexstat.mdic.gov.br" + path, headers={"User-Agent": "brazil-macro-pipeline/1.0"})
    _last_comex[0] = time.time()
    fp.write_bytes(raw)
    j = json.loads(raw)
    log_call("GET " + path, "", len(j["data"]) if isinstance(j.get("data"), list) else "", len(raw), time.time() - t0, str(fp.relative_to(OUT)))
    return j


PERIOD = {"from": "2023-01", "to": "2026-12"}


def body_us(details, monthly=True, flow="export", extra_filters=None, metrics=("metricFOB", "metricKG")):
    f = [{"filter": "country", "values": ["249"]}] + (extra_filters or [])
    return {"flow": flow, "monthDetail": monthly, "period": PERIOD, "filters": f, "details": details,
            "metrics": list(metrics)}


def load_us_ncm():
    df = comex("us_ncm_m", body_us(["ncm"]))
    d = pd.DataFrame({"ncm": df.coNcm.astype(str).str.zfill(8),
                      "ym": pd.to_datetime(dict(year=df.year.astype(int), month=df.monthNumber.astype(int), day=1)),
                      "fob": df.metricFOB.astype(float), "kg": df.metricKG.astype(float)})
    d["hs4"] = d.ncm.str[:4]; d["hs6"] = d.ncm.str[:6]
    if "ncm" in df.columns:
        d["desc"] = df["ncm"].values
    return d


# ---------------------------------------------------------------- 0. anchors
ANCH = {"exports_to_us": {2023: 36.915, 2024: 40.369, 2025: 37.682},
        "monthly": [3.347, 3.829, 2.845, 2.666, 2.307, 2.592, 3.412, 2.374, 2.530, 2.859, 3.158, 2.986, 3.424, 3.584, 3.190]}


def anchors():
    mism = []
    sql = """SELECT year, value FROM v_annual WHERE series_id='exports_to_us' AND year BETWEEN 2023 AND 2026 ORDER BY year"""
    a = wq(sql, "anchor_annual")
    for y, v in zip(a.year, a.value):
        rec(f"anchors.exports_to_us.{y}_bn", round(v / 1e9, 3), "exports_to_us", sql)
        if y in ANCH["exports_to_us"] and abs(v / 1e9 - ANCH["exports_to_us"][y]) > 0.002:
            mism.append(("annual", y, v / 1e9))
    sql2 = """SELECT date, value FROM v_observations WHERE series_id='exports_to_us' AND date BETWEEN '2025-06-01' AND '2026-08-01' ORDER BY date"""
    m = wq(sql2, "anchor_monthly")
    for (d, v), e in zip(m.itertuples(index=False), ANCH["monthly"]):
        if abs(v / 1e9 - e) > 0.002:
            mism.append(("monthly", str(d)[:10], v / 1e9))
    ytd = m[m.date >= pd.Timestamp("2026-01-01")].value.sum() / 1e9
    rec("anchors.exports_to_us.2026_janaug_bn", round(ytd, 3), "exports_to_us", sql2)
    if abs(ytd - 24.105) > 0.002:
        mism.append(("ytd", 2026, ytd))
    ev = wq("SELECT * FROM political_events WHERE event ILIKE '%tarif%' OR kind ILIKE '%tarif%'", "anchor_political_events")
    rec("anchors.political_events_tariff_rows", len(ev), "political_events", SQLLOG["anchor_political_events"],
        note=ev.to_dict("records").__repr__()[:500])
    mk = wq("""SELECT series_id, max(date) AS last FROM v_observations WHERE series_id IN ('brl_usd','ibovespa_usd','gov_real_yield_10y',
               'gov_nominal_yield_5y','focus_fx','focus_selic_12m','fx_reserves','brent_usd','embi_brazil','caged_net_hires') GROUP BY 1""", "anchor_market_last")
    R["anchors.market_last_dates"] = {r.series_id: str(r.last)[:10] for r in mk.itertuples()}
    # ComexStat live
    d = load_us_ncm()
    yy = d.groupby(d.ym.dt.year).fob.sum() / 1e9
    for y in [2023, 2024, 2025, 2026]:
        rec(f"anchors.comexstat_live.us_{y}_bn", round(float(yy[y]), 3), source="ComexStat API (live)",
            last_date=str(d.ym.max())[:10], call="cache/comexstat/us_ncm_m.parquet")
    R["anchors.comexstat_live.rows"] = len(d); R["anchors.comexstat_live.n_ncm"] = d.ncm.nunique()
    R["anchors.comexstat_live.last_month"] = str(d.ym.max())[:10]
    for y in [2024, 2025]:
        if abs(yy[y] - ANCH["exports_to_us"][y]) > 0.002:
            mism.append(("comexstat_live", y, yy[y]))
    top = d[d.ym.dt.year == 2024].groupby("ncm").fob.sum().sort_values(ascending=False) / 1e9
    R["anchors.top_ncm_2024"] = {k: round(v, 3) for k, v in top.head(45).items()}
    R["anchors.top45_share_2024"] = round(float(top.head(45).sum() / top.sum() * 100), 1)
    R["anchors.mismatches"] = mism
    print("anchor mismatches:", mism)
    print("top45 share", R["anchors.top45_share_2024"], "rows", len(d), "ncm", d.ncm.nunique(), "last", d.ym.max())
    save_results()
    return mism


STEPS = {}


def step(f):
    STEPS[f.__name__] = f
    return f


step(anchors)


# ---------------------------------------------------------------- 1.1 ComexStat pulls
TOP40 = ['2709', '7207', '8802', '0901', '2710', '4703', '7201', '8429', '2009', '0202', '7224', '6802', '1701', '8504',
         '2818', '4409', '8409', '4418', '1602', '2601', '7202', '4011', '8411', '8708', '8807', '4412', '1502', '3301',
         '8501', '4407', '2401', '8704', '2804', '9403', '8483', '7304', '7108', '2101', '2207', '8481']
EXTRA_HS4 = ['0409', '0304', '0306', '6403', '6402', '7325', '9306', '9303', '3504', '4107']
HS4_SET = TOP40 + EXTRA_HS4
FIRM_NCM = ['88024090', '88023039', '88073000', '09011110', '02023000', '72011000', '72071200', '47032900',
            '20091200', '20091100', '20091900', '17011400', '72029300', '85042300', '85042100', '64039990', '04090000',
            '03046200', '24012030', '22071010', '73251000', '84099190', '28182010', '15021012', '68029390', '68029990',
            '26011210', '84291190', '84295199', '33011290', '21011110', '16025000']


@step
def pulls_comex():
    comex("us_heading_m", body_us(["heading"]))
    comex("us_state_m", body_us(["state"]))
    comex("us_state_heading_y", body_us(["state", "heading"], monthly=False))
    comex("us_state_heading_m_top", body_us(["state", "heading"], extra_filters=[{"filter": "heading", "values": TOP40}]))
    comex("world_heading_m", {"flow": "export", "monthDetail": True, "period": PERIOD, "filters": [],
                              "details": ["heading"], "metrics": ["metricFOB", "metricKG"]})
    for k in range(0, len(HS4_SET), 10):
        comex(f"div_heading_country_m_{k//10}", {"flow": "export", "monthDetail": True, "period": PERIOD,
              "filters": [{"filter": "heading", "values": HS4_SET[k:k+10]}], "details": ["heading", "country"],
              "metrics": ["metricFOB", "metricKG"]})
    comex("div_ncm_country_m", {"flow": "export", "monthDetail": True, "period": PERIOD,
          "filters": [{"filter": "ncm", "values": FIRM_NCM}], "details": ["ncm", "country"], "metrics": ["metricFOB", "metricKG"]})
    comex("imp_us_heading_y", body_us(["heading"], monthly=False, flow="import", metrics=("metricFOB",)))
    comex("imp_us_heading_m", body_us(["heading"], flow="import", metrics=("metricFOB",)))
    comex("world_state_m", {"flow": "export", "monthDetail": True, "period": PERIOD, "filters": [],
                            "details": ["state"], "metrics": ["metricFOB"]})
    for p in ["/tables/countries", "/tables/uf", "/tables/ncm", "/tables/economic-blocks"]:
        try:
            comex_get(p)
        except Exception as e:  # noqa
            print("  table", p, e)
    try:
        comex("world_ncm_m", {"flow": "export", "monthDetail": True, "period": PERIOD, "filters": [],
                              "details": ["ncm"], "metrics": ["metricFOB", "metricKG"]})
    except Exception as e:  # noqa
        print("  world_ncm_m failed", e); R["gaps.world_ncm_m"] = str(e); save_results()



# ---------------------------------------------------------------- 1.4 HTS lists (USITC Chapter 99, current release)
CODE_RE = re.compile(r"(?<![\d.])(\d{4}\.\d{2}(?:\.\d{4}|\.\d{2}(?:\.\d{2})?)?)(?![\d])")
TOKEN_RE = re.compile(r"\d{4}(?:\.\d{2}(?:\.\d{4}|\.\d{2}(?:\.\d{2})?)?)?")
HEAD4_RE = re.compile(r"(?<![\d.])(\d{4})(?![\d.])")
LISTS = {  # name: (start marker (regex), end marker (regex), kind)
    "ieepa_a_amended": (r"As provided in heading 9903\.01\.81, the additional duties", r"As provided in heading 9903\.01\.90, the additional duty", "full"),
    "ieepa_b_particular": (r"As provided in heading 9903\.01\.90, the additional duty", r"As provided in heading 9903\.01\.82, the additional duties", "particular"),
    "ieepa_aircraft": (r"As provided in heading 9903\.01\.82, the additional duties", r"shall not apply to products of iron or steel provided for in", "full"),
    "recip_annex_ii": (r"As provided for in heading 9903\.01\.32", r"As provided in heading 9903\.02\.78", "full"),
    "ag_eo14360": (r"As provided in heading 9903\.02\.78", r"As provided in 9903\.01\.26", "full"),
    "s122_a": (r"As provided in heading 9903\.03\.03, the additional duty", r"As provided in heading 9903\.03\.04", "full"),
    "s122_b": (r"As provided in heading 9903\.03\.04", r"As provided in heading 9903\.03\.05", "particular"),
    "s122_aircraft": (r"As provided in heading 9903\.03\.05", r"As provided in heading 9903\.03\.06", "full"),
    "s122_c": (r"As provided in heading 9903\.03\.06", r"As provided in heading 9903\.03\.07", "particular"),
    "s232_metals": (r"Headings 9903\.82\.02.9903\.82\.26 apply to the full customs value", r"Heading 9903\.82\.19 applies to limited quantities", "full"),
    "s232_autos": (r"^33\. \(a\)", r"^35\. ", "full"),
    "s232_wood": (r"^37\.\s*$", r"^38\.\s*$", "full"),
    "s232_mhdv": (r"^38\.\s*$", r"^39\.\s*$", "full"),
    "s232_semis": (r"^39\.\s*$", r"^40\.\s*$", "full"),
    "s232_pharma": (r"^40\.\s*$", r"^41\.\s*$", "full"),
    "s301_a_ii": (r"As provided in heading 9903\.05\.03, the additional duty", r"As provided in heading 9903\.05\.04, the additional duty", "full"),
    "s301_a_iii": (r"As provided in heading 9903\.05\.04, the additional duty", r"As provided in heading 9903\.05\.05, the additional duty", "particular"),
    "s301_aircraft": (r"As provided in heading 9903\.05\.05, the additional duty", r"As provided in heading 9903\.05\.06, the additional duty", "full"),
    "s301_pharma": (r"As provided in heading 9903\.05\.06, the additional duty", r"As provided in heading 9903\.05\.07, the additional duty", "particular"),
    "s301_a_vi": (r"As provided in heading 9903\.05\.07, the additional duty", r"^51\.\s*$", "particular"),
    "fl_b": (r"As provided in heading 9903\.05\.86, the duties", r"As provided in heading 9903\.05\.87, the duties", "full"),
    "fl_c": (r"As provided in heading 9903\.05\.87, the duties", r"As provided in heading 9903\.05\.88, the additional", "particular"),
    "fl_aircraft": (r"As provided in heading 9903\.05\.88, the additional", r"As provided in heading 9903\.05\.89, the additional", "full"),
    "fl_pharma": (r"As provided in heading 9903\.05\.89, the additional", r"As provided in heading 9903\.05\.90, the additional", "particular"),
    "fl_f": (r"As provided in heading 9903\.05\.90, the additional", r"As provided in heading 9903\.05\.93, the additional", "particular"),
}
HDR_RE = re.compile(r"Harmonized Tariff Schedule of the United States|Annotated for Statistical|^\s*XXII\s*$|99 - [IVX]+ - \d+|U\.S\. Notes \(con\.\)")


def hts_universe():
    j = json.loads((CACHE / "hts" / "hts_full.json").read_text())
    rows = []
    for r in j:
        c = (r.get("htsno") or "").replace(".", "")
        if len(c) >= 8 and c[:2] != "99" and c[:2] != "98":
            rows.append((c[:8], c[:6], r.get("general") or "", r.get("description") or ""))
    u = pd.DataFrame(rows, columns=["hts8", "hs6", "mfn", "desc"]).drop_duplicates("hts8")
    return u


def extract_lists():
    lines = (CACHE / "hts" / "chapter99.txt").read_text(errors="ignore").split("\n")
    out = {}
    for name, (a, b, kind) in LISTS.items():
        ra, rb = re.compile(a), re.compile(b)
        i0 = next((i for i, l in enumerate(lines) if ra.search(l)), None)
        if i0 is None:
            print("  marker not found", name); out[name] = (set(), kind, None, None); continue
        i1 = next((i for i in range(i0 + 1, len(lines)) if rb.search(lines[i])), None)
        seg = [l for l in lines[i0 + 1:i1] if not HDR_RE.search(l)]
        codes = set()
        for l in seg:
            toks = [t.strip(";,") for t in l.split()]
            if toks and all(TOKEN_RE.fullmatch(t) for t in toks):   # pure list line: keep 4-digit headings too
                codes |= {t.replace(".", "") for t in toks}
            else:
                codes |= {m.replace(".", "") for m in CODE_RE.findall(l)}
        codes = {c for c in codes if not c.startswith("99") and not c.startswith("98")}
        out[name] = (codes, kind, i0 + 1, i1 + 1 if i1 else None)
        print(f"  {name}: {len(codes)} codes, lines {i0+1}-{i1+1 if i1 else None}")
    # original EO 14323 Annex I (govinfo PDF via pdftotext)
    t = (CACHE / "fr" / "2025-14896.pdf.txt").read_text(errors="ignore")
    k = t.find("Annex I")
    codes = set(m.replace(".", "") for m in CODE_RE.findall(t[k:] if k > 0 else t))
    codes = {c for c in codes if not c.startswith("99") and not c.startswith("98")}
    out["eo14323_annex_i_orig"] = (codes, "full", None, None)
    print(f"  eo14323_annex_i_orig: {len(codes)} codes")
    rows = []
    for n, (cs, kind, a, b) in out.items():
        for c in sorted(cs):
            rows.append(dict(list=n, code=c, kind=kind, src_line_from=a, src_line_to=b))
    pd.DataFrame(rows).to_csv(CACHE / "hts" / "lists_long.csv", index=False)
    return out


def hs6_share(codes, kind, U):
    """HS6 -> share of the HS6 covered by a list. full list: share of HTS-8 lines under the HS6 that are listed
    (codes at 6/4 digits cover every line under them); 'particular' lists name an article inside a subheading -> 0.5."""
    if not codes:
        return {}
    U8 = U.groupby("hs6").hts8.apply(set).to_dict()
    sh = {}
    for hs6, s8 in U8.items():
        if kind == "particular":
            hit = any(c[:8] in s8 or (len(c) == 6 and c == hs6) for c in codes if c[:6] == hs6)
            if hit:
                sh[hs6] = 0.5
            continue
        n = 0
        for h8 in s8:
            if h8 in codes or h8[:6] in codes or h8[:4] in codes or any(c.startswith(h8) for c in codes if len(c) == 10 and c[:6] == hs6):
                n += 1
        if n:
            sh[hs6] = n / len(s8)
    return sh


@step
def pulls_hts():
    L = extract_lists()
    U = hts_universe()
    print("  HTS universe", len(U), "HTS-8 lines,", U.hs6.nunique(), "HS6")
    rows = []
    for n, (cs, kind, a, b) in L.items():
        for h, s in hs6_share(cs, kind, U).items():
            rows.append(dict(list=n, hs6=h, share=s))
    df = pd.DataFrame(rows)
    df.to_csv(CACHE / "hts" / "lists_hs6.csv", index=False)
    R["hts.list_sizes"] = {n: len(v[0]) for n, v in L.items()}
    R["hts.list_lines"] = {n: [v[2], v[3]] for n, v in L.items()}
    save_results()


# ---------------------------------------------------------------- 3. timeline + coverage (stop rule)
def list_shares():
    df = pd.read_csv(CACHE / "hts" / "lists_hs6.csv", dtype={"hs6": str})
    S = {n: g.set_index("hs6").share.to_dict() for n, g in df.groupby("list")}
    L = pd.read_csv(CACHE / "hts" / "lists_long.csv", dtype=str)
    # inferred lists (annexes that are images in the FR)
    U = hts_universe()
    orig = set(L[L.list == "eo14323_annex_i_orig"].code)
    amend = set(L[L.list == "ieepa_a_amended"].code)
    relief = {c for c in amend - orig if not any(c.startswith(o) or o.startswith(c) for o in orig)}
    S["relief_eo14361"] = hs6_share(relief, "full", U)
    for h, s in S.get("ieepa_b_particular", {}).items():
        S["relief_eo14361"][h] = max(S["relief_eo14361"].get(h, 0), s)
    rec_ = set(L[L.list == "recip_annex_ii"].code)
    ag = {c for c in rec_ if int(c[:2]) <= 24}
    S["ag_eo14360_inferred"] = hs6_share(ag, "full", U)
    S["recip_annex_ii_orig_inferred"] = hs6_share(rec_ - ag, "full", U)
    R["hts.inferred"] = {"relief_eo14361_codes": len(relief), "ag_eo14360_codes": len(ag),
                         "note": "EO 14361 and EO 14360 annexes are images in the FR; relief = HTS 2(x)(iii)(a) as amended minus "
                                 "EO 14323 Annex I (pdftotext of the govinfo PDF) plus 2(x)(iii)(b); EO 14360 additions = "
                                 "chapter 01-24 codes in the current EO 14257 Annex II (9903.01.32)."}
    return S


def g(S, n, h):
    return S.get(n, {}).get(h, 0.0)


def status_fracs(S, hs6, regime, partial_mode="any"):
    """fractions of an HS6 in each status + added ad valorem rate per status, for Brazil."""
    def sh(n):
        v = g(S, n, hs6)
        if partial_mode == "half":
            return 0.5 if 0 < v < 1 else v
        if partial_mode == "any":      # any listed HTS-8 under the HS6 -> the whole HS6 (MDIC maps NCM-8 -> HTS-8)
            return 1.0 if v > 0 else 0.0
        return v
    metals, autos = sh("s232_metals"), sh("s232_autos")
    wood, mhdv, pharma = sh("s232_wood"), sh("s232_mhdv"), sh("s232_pharma")
    chap = hs6[:2]
    if regime == "R0":
        return {"mfn": 1.0}, {"mfn": 0.0}
    if regime == "R1":
        f232 = max(metals, autos)
        rx = (1 - f232) * sh("recip_annex_ii_orig_inferred")
        r232 = 50.0 if chap in ("72", "73", "76", "74") else 25.0
        return {"232": f232, "exempt": rx, "full": 1 - f232 - rx}, {"232": r232, "exempt": 0.0, "full": 10.0}
    if regime == "R2":
        f232 = max(metals, autos)
        ex = (1 - f232) * max(sh("eo14323_annex_i_orig"), sh("ieepa_aircraft"))
        rx = sh("recip_annex_ii_orig_inferred")
        r232 = 50.0 if chap in ("72", "73", "76", "74") else 25.0
        return ({"232": f232, "exempt": ex, "full": max(0.0, 1 - f232 - ex)},
                {"232": r232, "exempt": 10.0 * (1 - rx), "full": 40.0 + 10.0 * (1 - rx)})
    if regime == "R3":
        f232 = max(metals, autos, wood, mhdv)
        ex = (1 - f232) * max(sh("ieepa_a_amended"), sh("relief_eo14361"), sh("ieepa_aircraft"), sh("eo14323_annex_i_orig"))
        rx = max(sh("recip_annex_ii_orig_inferred"), sh("ag_eo14360_inferred"))
        r232 = 50.0 if chap in ("72", "73", "76", "74") else 25.0
        return ({"232": f232, "exempt": ex, "full": max(0.0, 1 - f232 - ex)},
                {"232": r232, "exempt": 10.0 * (1 - rx), "full": 40.0 + 10.0 * (1 - rx)})
    if regime == "R4":
        f232 = max(metals, autos, wood, mhdv, pharma)
        ex = (1 - f232) * max(sh("s122_a"), sh("s122_b"), sh("s122_aircraft"))
        r232 = 50.0 if chap in ("72", "73", "76", "74") else 25.0
        return {"232": f232, "exempt": ex, "full": max(0.0, 1 - f232 - ex)}, {"232": r232, "exempt": 0.0, "full": 10.0}
    if regime == "R5":
        f232 = max(metals, autos, wood, mhdv, pharma)
        ex = (1 - f232) * max(sh("s301_a_ii"), sh("s301_a_iii"), sh("s301_aircraft"), sh("s301_pharma"))
        e301 = max(sh("s301_a_ii"), sh("s301_a_iii"), sh("s301_aircraft"), sh("s301_pharma"))
        efl = max(sh("fl_b"), sh("fl_c"), sh("fl_aircraft"), sh("fl_pharma"))
        r232 = 50.0 if chap in ("72", "73", "76", "74") else 25.0
        r = 1 - f232   # exemptions treated as nested within the HS6
        return ({"232": f232, "exempt": r * min(e301, efl), "fl_only": r * max(0.0, e301 - efl),
                 "s301_only": r * max(0.0, efl - e301), "full": r * (1 - max(e301, efl))},
                {"232": r232, "exempt": 0.0, "fl_only": 12.5, "s301_only": 25.0, "full": 37.5})
    raise ValueError(regime)


REGIMES = [("R0", "2023-01-01", "2025-03-11"), ("R1", "2025-03-12", "2025-08-05"), ("R2", "2025-08-06", "2025-11-12"),
           ("R3", "2025-11-13", "2026-02-23"), ("R4", "2026-02-24", "2026-07-21"), ("R5", "2026-07-22", "2026-12-31")]


def regime_of(ym):
    """monthly regime: a month belongs to the regime in force for most of it."""
    mid = pd.Timestamp(ym) + pd.Timedelta(days=14)
    for r, a, b in REGIMES:
        if pd.Timestamp(a) <= mid <= pd.Timestamp(b):
            return r
    return "R5"


def status_table(S, partial_mode="any"):
    d = load_us_ncm()
    hs6s = sorted(d.hs6.unique())
    rows = []
    for h in hs6s:
        for r, *_ in REGIMES:
            fr_, rt = status_fracs(S, h, r, partial_mode)
            for k, v in fr_.items():
                rows.append(dict(hs6=h, regime=r, status=k, frac=v, rate=rt[k]))
    return pd.DataFrame(rows)


ANCHOR_COV = {"R5": {"full": (16.5, 3), "exempt": (52.7, 5), "232": (24.2, 5)},
              "R2": {"full": (35.9, 4), "232": (19.5, 4)},
              "R3": {"full": (22.0, 4)},
              "R4": {"exempt": (46.0, 5)}}


def coverage(S, partial_mode="any", verbose=True):
    d = load_us_ncm()
    v24 = d[d.ym.dt.year == 2024].groupby("hs6").fob.sum()
    v25 = d[d.ym.dt.year == 2025].groupby("hs6").fob.sum()
    st = status_table(S, partial_mode)
    out, miss = {}, []
    for r, *_ in REGIMES:
        s = st[st.regime == r]
        for yr, v in (("2024", v24), ("2025", v25)):
            m = s.merge(v.rename("fob"), left_on="hs6", right_index=True)
            tot = v.sum()
            pct = (m.frac * m.fob).groupby(m.status).sum() / tot * 100
            out[(r, yr)] = pct.round(2).to_dict()
            if yr == "2024":
                eff = float((m.frac * m.fob * m.rate).sum() / tot)
                out[(r, "eff_rate_2024w")] = round(eff, 2)
        for k, (tgt, tol) in ANCHOR_COV.get(r, {}).items():
            got = out[(r, "2024")].get(k, 0.0)
            ok = abs(got - tgt) <= tol
            if not ok:
                miss.append((r, k, round(got, 1), tgt, tol))
            if verbose:
                print(f"  {r} {k}: {got:.1f}% vs {tgt} +/- {tol} -> {'OK' if ok else 'MISS'}")
    return out, miss, st


# ---------------------------------------------------------------- 1.2 UN Comtrade public preview (US imports)
CT = "https://comtradeapi.un.org/public/v1/preview/C/M/HS"
MIRROR_HS4 = ["0901", "0202", "2009", "7201", "7207", "4703", "8802", "7202", "2709", "1701", "4407", "6802"]
_ct_calls = [0]


def ct_get(period, cmds, partner=None, budget=450):
    cmd = ",".join(cmds)
    tag = (cmd if len(cmds) <= 4 else f"{len(cmds)}codes_{abs(hash(cmd)) % 10**6}")
    fp = CACHE / "comtrade" / f"842_{period}_{tag}_{partner or 'all'}.json"
    if fp.exists():
        return json.loads(fp.read_text())
    if _ct_calls[0] >= budget:
        raise RuntimeError("comtrade budget reached")
    url = f"{CT}?reporterCode=842&period={period}&flowCode=M&cmdCode={cmd}&partner2Code=0&motCode=0&customsCode=C00"
    if partner:
        url += f"&partnerCode={partner}"
    for attempt in range(6):
        time.sleep(2.6)
        t0 = time.time()
        try:
            raw = http(url, timeout=90)
            _ct_calls[0] += 1
            j = json.loads(raw)
            fp.write_bytes(raw)
            log_call("comtrade preview", url, len(j.get("data") or []), len(raw), time.time() - t0, str(fp.relative_to(OUT)))
            return j
        except urllib.error.HTTPError as e:
            _ct_calls[0] += 1
            if e.code == 429:
                print("  429, sleeping", 20 * (attempt + 1)); time.sleep(20 * (attempt + 1)); continue
            if e.code == 403:
                raise RuntimeError("comtrade HTTP 403 (public preview cap) at " + url)
            print("  comtrade HTTP", e.code, url); time.sleep(5)
        except Exception as e:  # noqa
            print("  comtrade err", repr(e)[:120]); time.sleep(10)
    raise RuntimeError("comtrade sustained failure at " + url)


def months(a, b):
    return [p.strftime("%Y%m") for p in pd.period_range(a, b, freq="M").to_timestamp()]


@step
def pulls_comtrade():
    done = []
    try:
        # bilateral by HS4 (top-40 + extras), US imports from Brazil
        if R.get("gaps.comtrade", "").startswith("stopped") and not os.environ.get("CT_RETRY"):
            raise RuntimeError("skipped (cap hit earlier; set CT_RETRY=1 to retry): " + R["gaps.comtrade"])
        for p in months("2023-01", "2026-07"):
            ct_get(p, HS4_SET, partner="76")
        done.append("bilateral 2023-01..2026-07")
        # competitor mirror: batch HS4 so each call stays < 500 rows; split on truncation
        groups = [["0901"], ["0202", "7201", "7202"], ["2009", "7207", "4703"], ["8802", "2709"], ["1701", "4407"], ["6802"]]
        for p in months("2023-01", "2026-07")[::-1]:
            for grp in groups:
                j = ct_get(p, grp)
                if len(j.get("data") or []) >= 500 and len(grp) > 1:
                    print("  truncated, splitting", p, grp)
                    for c in grp:
                        ct_get(p, [c])
            done.append(p)
    except RuntimeError as e:
        print("  stopped:", e)
        R["gaps.comtrade"] = f"stopped: {e}; done through {done[-1] if done else None}"
    R["comtrade.calls_this_run"] = _ct_calls[0]
    R["comtrade.done"] = done[:3] + ["..."] + done[-3:]
    save_results()


# ---------------------------------------------------------------- 1.6 B3 COTAHIST (parse_cotahist / BDI-TPMERC filter copied from ingest/b3_market.py)
SERHIST = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/"
COT_TICKERS = {"EMBR3", "GGBR4", "CSNA3", "JBSS3", "MRFG3", "BEEF3", "BRFS3", "WEGE3", "TUPY3", "SUZB3", "KLBN11", "DXCO3",
               "ALPA4", "GRND3", "VULC3", "SMTO3", "CMIN3", "USIM5", "CBAV3", "SLCE3", "MBRF3", "JBSS32", "EMBJ3"}


def parse_cotahist(zpath, tickers=COT_TICKERS):
    rows = []
    with zipfile.ZipFile(zpath) as z, z.open(z.namelist()[0]) as fh:
        for raw in fh:
            if raw[:2] != b"01" or raw[12:24].decode("latin-1").strip() not in tickers:
                continue
            l = raw.decode("latin-1")
            rows.append(dict(date=l[2:10], bdi=l[10:12], ticker=l[12:24].strip(), tpmerc=l[24:27],
                             close=int(l[108:121]) / 100, qty=int(l[152:170]), fatcot=int(l[210:217])))
    return pd.DataFrame(rows, columns=["date", "bdi", "ticker", "tpmerc", "close", "qty", "fatcot"])


def cotahist_file(kind, tag):
    out = CACHE / "cotahist" / f"{kind}{tag}.csv"
    if out.exists():
        return pd.read_csv(out, dtype={"date": str, "bdi": str, "tpmerc": str})
    name = f"COTAHIST_{kind}{tag}.ZIP"
    z = CACHE / "cotahist" / name
    t0 = time.time()
    try:
        raw = http(SERHIST + name, timeout=900)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    z.write_bytes(raw)
    df = parse_cotahist(z)
    os.remove(z)
    df.to_csv(out, index=False)
    log_call("B3 COTAHIST", SERHIST + name, len(df), len(raw), time.time() - t0, str(out.relative_to(OUT)))
    print(f"  {name}: {len(raw)/1e6:.0f} MB -> {len(df)} rows", flush=True)
    return df.astype({"date": str})


@step
def pulls_cotahist():
    frames = []
    for y in (2021, 2022, 2023, 2024, 2025, 2026):   # 2021-23 added for placebo depth (events crowd 2025-26)
        df = cotahist_file("A", str(y))
        if df is not None:
            frames.append(df)
    allr = pd.concat(frames, ignore_index=True)
    last = pd.to_datetime(allr.date).max()
    for d in pd.bdate_range(last + pd.Timedelta(days=1), pd.Timestamp("2026-10-06")):
        df = cotahist_file("D", d.strftime("%d%m%Y"))
        if df is not None and len(df):
            frames.append(df)
    allr = pd.concat(frames, ignore_index=True)
    allr["date"] = pd.to_datetime(allr.date)
    bdi = allr.bdi.astype(str).str.zfill(2)
    R["cotahist.bdi_by_ticker"] = {t: sorted(set(b)) for t, b in bdi.groupby(allr.ticker)}
    allr = allr[(allr.tpmerc.astype(str).str.zfill(3) == "010") & ((bdi == "02") | ((allr.ticker == "JBSS32") & (bdi != "96")))]
    allr = allr.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"])
    allr.to_parquet(CACHE / "cotahist" / "closes.parquet")
    R["cotahist.tickers"] = {t: [str(g.date.min())[:10], str(g.date.max())[:10], len(g)] for t, g in allr.groupby("ticker")}
    R["cotahist.fatcot_not1"] = int((allr.fatcot != 1).sum())
    print(R["cotahist.tickers"])
    save_results()


@step
def pulls_comex_world_ncm():
    for y in (2023, 2024, 2025, 2026):
        try:
            comex(f"world_ncm_m_{y}", {"flow": "export", "monthDetail": True, "period": {"from": f"{y}-01", "to": f"{y}-12"},
                                       "filters": [], "details": ["ncm"], "metrics": ["metricFOB", "metricKG"]})
        except Exception as e:  # noqa
            print("  world_ncm", y, "failed", e)
            R[f"gaps.world_ncm_m_{y}"] = str(e)
    save_results()


# ================================================================ DATA LAYER (in-memory; never the warehouse)
def _ym(df):
    return pd.to_datetime(dict(year=df.year.astype(int), month=df.monthNumber.astype(int), day=1))


_CACHE_D = {}


def D(name):
    if name in _CACHE_D:
        return _CACHE_D[name]
    cx = CACHE / "comexstat"
    if name == "us_ncm":
        out = load_us_ncm()
    elif name == "world_ncm":
        fr_ = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(cx / "world_ncm_m_20*.parquet")))])
        out = pd.DataFrame({"ncm": fr_.coNcm.astype(str).str.zfill(8), "ym": _ym(fr_), "fob": fr_.metricFOB.astype(float),
                            "kg": fr_.metricKG.astype(float)})
    elif name == "world_hs4":
        fr_ = pd.read_parquet(cx / "world_heading_m.parquet")
        out = pd.DataFrame({"hs4": fr_.headingCode.astype(str).str.zfill(4), "ym": _ym(fr_),
                            "fob": fr_.metricFOB.astype(float), "kg": fr_.metricKG.astype(float)})
    elif name == "div":
        fr_ = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(cx / "div_heading_country_m_*.parquet")))])
        out = pd.DataFrame({"hs4": fr_.headingCode.astype(str).str.zfill(4), "country": fr_.country, "ym": _ym(fr_),
                            "fob": fr_.metricFOB.astype(float), "kg": fr_.metricKG.astype(float)})
    elif name == "div_ncm":
        fr_ = pd.read_parquet(cx / "div_ncm_country_m.parquet")
        out = pd.DataFrame({"ncm": fr_.coNcm.astype(str).str.zfill(8), "country": fr_.country, "ym": _ym(fr_),
                            "fob": fr_.metricFOB.astype(float), "kg": fr_.metricKG.astype(float)})
    elif name == "state_hs4_y":
        fr_ = pd.read_parquet(cx / "us_state_heading_y.parquet")
        out = pd.DataFrame({"uf": fr_.state, "hs4": fr_.headingCode.astype(str).str.zfill(4), "year": fr_.year.astype(int),
                            "fob": fr_.metricFOB.astype(float)})
    elif name == "state_m":
        fr_ = pd.read_parquet(cx / "us_state_m.parquet")
        out = pd.DataFrame({"uf": fr_.state, "ym": _ym(fr_), "fob": fr_.metricFOB.astype(float)})
    elif name == "world_state_m":
        fr_ = pd.read_parquet(cx / "world_state_m.parquet")
        out = pd.DataFrame({"uf": fr_.state, "ym": _ym(fr_), "fob": fr_.metricFOB.astype(float)})
    elif name == "state_hs4_m":
        fr_ = pd.read_parquet(cx / "us_state_heading_m_top.parquet")
        out = pd.DataFrame({"uf": fr_.state, "hs4": fr_.headingCode.astype(str).str.zfill(4), "ym": _ym(fr_),
                            "fob": fr_.metricFOB.astype(float)})
    elif name == "imp_us_y":
        fr_ = pd.read_parquet(cx / "imp_us_heading_y.parquet")
        out = pd.DataFrame({"hs4": fr_.headingCode.astype(str).str.zfill(4), "desc": fr_.heading, "year": fr_.year.astype(int),
                            "fob": fr_.metricFOB.astype(float)})
    elif name == "hs4_desc":
        fr_ = pd.read_parquet(cx / "world_heading_m.parquet")
        out = fr_.drop_duplicates("headingCode").set_index(fr_.drop_duplicates("headingCode").headingCode.astype(str).str.zfill(4)).heading
    else:
        raise KeyError(name)
    _CACHE_D[name] = out
    return out


COMMODITY_HS4 = {"0901", "0202", "1602", "7201", "7207", "7224", "4703", "1701", "1502", "2401", "2818", "2709"}
MANUF_HS4 = {"8802", "8807", "8429", "8504", "6403", "6402", "9403", "4409", "4418", "4412", "4407", "4011", "6802", "9306", "7304"}


def hs4_class(h):
    if h in COMMODITY_HS4:
        return "commodity"
    if h in MANUF_HS4:
        return "manufactured"
    c = int(h[:2])
    if c <= 27 or c in (41, 47, 71) or h in ("7202", "7203", "7206", "2601", "2804", "2818", "7108", "4401", "4403"):
        return "commodity"
    return "manufactured"


def hs4_status(partial_mode="any"):
    """HS4 x regime: value-weighted (2024 US) status fractions and added Brazil rate; group labels."""
    S = list_shares()
    st = status_table(S, partial_mode)
    us = D("us_ncm")
    v6 = us[us.ym.dt.year == 2024].groupby("hs6").fob.sum().rename("v")
    st = st.merge(v6, left_on="hs6", right_index=True, how="left").fillna({"v": 0.0})
    st["hs4"] = st.hs6.str[:4]
    st["fv"] = st.frac * st.v
    agg = st.groupby(["hs4", "regime", "status"]).agg(fv=("fv", "sum")).reset_index()
    tot = st.drop_duplicates(["hs6", "regime"]).groupby(["hs4", "regime"]).v.sum().rename("tv")
    agg = agg.merge(tot, left_on=["hs4", "regime"], right_index=True)
    agg["share"] = np.where(agg.tv > 0, agg.fv / agg.tv, np.nan)
    # unweighted fallback for HS4 with zero 2024 value
    uw = st.groupby(["hs4", "regime", "status"]).frac.mean().rename("share_uw").reset_index()
    agg = agg.merge(uw, on=["hs4", "regime", "status"], how="outer")
    agg["share"] = agg.share.fillna(agg.share_uw)
    piv = agg.pivot_table(index="hs4", columns=["regime", "status"], values="share", aggfunc="sum").fillna(0.0)
    st["rv"] = st.frac * st.rate * st.v
    st["ru"] = st.frac * st.rate
    rate = (st.groupby(["hs4", "regime"]).rv.sum() / st.drop_duplicates(["hs6", "regime"]).groupby(["hs4", "regime"]).v.sum())
    rate_u = st.groupby(["hs4", "regime"]).ru.sum() / st.drop_duplicates(["hs6", "regime"]).groupby(["hs4", "regime"]).hs6.count()
    rate = rate.where(np.isfinite(rate), rate_u).unstack().fillna(0.0)
    g = pd.DataFrame(index=piv.index)
    f = lambda r, s: piv[(r, s)] if (r, s) in piv.columns else 0.0
    g["f232"] = np.maximum(f("R2", "232"), f("R5", "232"))
    g["full_R2"], g["full_R3"], g["full_R5"] = f("R2", "full"), f("R3", "full"), f("R5", "full")
    g["fl_only_R5"] = f("R5", "fl_only")
    grp = np.where(g.f232 >= 0.5, "232", np.where(g.full_R2 < 0.5, "exempt",
                   np.where(g.full_R3 >= 0.5, "covered", "relief")))
    g["group"] = grp
    g.loc[g.index == "2709", "group"] = "crude"
    g["class"] = [hs4_class(h) for h in g.index]
    for r in ["R0", "R1", "R2", "R3", "R4", "R5"]:
        g[f"rate_{r}"] = rate[r] if r in rate.columns else 0.0
    return g


@step
def exposure():
    """section 4: product exposure map (top-40 HS4 + firm HS4)."""
    g = hs4_status()
    us = D("us_ncm"); wh = D("world_hs4"); dv = D("div"); desc = D("hs4_desc")
    usy = us.groupby([us.hs4, us.ym.dt.year]).fob.sum().unstack().fillna(0) / 1e9
    wy = wh.groupby([wh.hs4, wh.ym.dt.year]).fob.sum().unstack().fillna(0) / 1e9
    ytd_m = us.ym.max().month
    usy26 = us[(us.ym.dt.year == 2026)].groupby("hs4").fob.sum() / 1e9
    st_y = D("state_hs4_y")
    st24 = st_y[st_y.year == 2024]
    ct = mirror_annual()   # Comtrade 2024 annual from monthly pulls
    rows = []
    for h in HS4_SET:
        s = st24[st24.hs4 == h].groupby("uf").fob.sum().sort_values(ascending=False)
        sh = (s / s.sum()) if s.sum() > 0 else s
        m = ct.get(h, {})
        row = dict(hs4=h, description=str(desc.get(h, ""))[:90],
                   value_us_2024_bn=round(usy.loc[h, 2024], 3) if h in usy.index else 0.0,
                   value_us_2025_bn=round(usy.loc[h, 2025], 3) if h in usy.index else 0.0,
                   value_us_2026ytd_bn=round(float(usy26.get(h, 0.0)), 3), ytd_months=ytd_m,
                   us_share_of_brazil_exports_2024=round(100 * usy.loc[h, 2024] / wy.loc[h, 2024], 1) if h in usy.index and h in wy.index and wy.loc[h, 2024] > 0 else None,
                   brazil_share_of_us_imports_2024=m.get("br_share"), n_suppliers_gt5pct=m.get("n_gt5"), supplier_hhi=m.get("hhi"),
                   top3_competitors=m.get("top3"), states_top3="; ".join(f"{k} {100*v:.0f}%" for k, v in sh.head(3).items()),
                   state_share_top3=round(100 * sh.head(3).sum(), 1) if len(sh) else None,
                   unit_value_available=bool((us[(us.hs4 == h)].kg > 0).any()), **{"class": hs4_class(h)},
                   group=g.group.get(h), full_rate_now_pct=round(float(g.rate_R5.get(h, np.nan)), 1))
        for r in ["R1", "R2", "R3", "R4", "R5"]:
            row[f"status_{r}_rate_pct"] = round(float(g[f"rate_{r}"].get(h, np.nan)), 1)
        bs = m.get("br_share")
        row["substitutability_class"] = ("low" if (bs is not None and bs > 30 and (m.get("hhi") or 0) > 2500) or h in ("8802", "7202")
                                         else "n/a (no mirror)" if bs is None else "med" if bs > 10 else "high")
        row["firms"], row["firm_states_source"] = FIRMS.get(h, ("", ""))
        rows.append(row)
    pe = pd.DataFrame(rows).sort_values("value_us_2024_bn", ascending=False)
    pe.to_csv(OUT / "product_exposure.csv", index=False)
    R["exposure.n_rows"] = len(pe)
    R["exposure.top40_share_2024"] = round(float(pe.value_us_2024_bn.sum() / usy[2024].sum() * 100), 1)
    print(pe.head(15)[["hs4", "value_us_2024_bn", "group", "full_rate_now_pct", "brazil_share_of_us_imports_2024", "states_top3"]].to_string())
    save_results()
    return pe


FIRMS = {  # static firm/state mapping; sources: company filings / MDIC state data (fact ids in external_facts.csv)
    "8802": ("Embraer (SP: São José dos Campos, Gavião Peixoto)", "Embraer 20-F; D-series"),
    "8807": ("Embraer; aerostructure suppliers (SP)", "Embraer 20-F"),
    "4703": ("Suzano, Klabin, Eldorado (BA, MA, SP, MS, ES)", "company filings"),
    "8504": ("WEG (SC Jaraguá do Sul), Siemens Energy, Hitachi Energy", "WEG annual report"),
    "8501": ("WEG (SC)", "WEG annual report"),
    "0202": ("JBS, Marfrig/MBRF, Minerva (SP, MS, GO, MT)", "company filings"),
    "1602": ("JBS, MBRF, Minerva (SP, MS, GO, MT, RS)", "company filings"),
    "7207": ("ArcelorMittal Tubarão (ES), CSN (RJ), Gerdau, Usiminas, Ternium (RJ)", "company filings"),
    "7224": ("Gerdau, Villares/Aperam (SP, MG)", "company filings"),
    "8409": ("Tupy (SC Joinville, MG Betim), MWM", "Tupy annual report"),
    "7325": ("Tupy (SC)", "Tupy annual report"),
    "2009": ("Cutrale, Citrosuco, LDC (SP)", "CitrusBR"),
    "3301": ("Cutrale, Citrosuco (orange oil, SP)", "CitrusBR"),
    "7201": ("independent guseiros (MG, PA, MA, ES)", "Sindifer"),
    "7202": ("CBMM (MG Araxá) ferroniobium", "CBMM"),
    "0901": ("Cooxupé, exporters (MG, ES, SP)", "Cecafé"),
    "2101": ("Cacique, Iguaçu (PR, SP) instant coffee", "ABICS"),
    "6403": ("Alpargatas, Grendene, Vulcabras (RS, CE, BA)", "Abicalçados"),
    "6402": ("Grendene, Alpargatas (CE, PB)", "Abicalçados"),
    "9403": ("furniture clusters (SC São Bento, RS Bento Gonçalves)", "Abimóvel"),
    "0409": ("honey (PI, CE, PR)", "ABEMEL"),
    "0304": ("tilapia (PR)", "Peixe BR"),
    "8429": ("Caterpillar Piracicaba, Komatsu Suzano, CNH Contagem (SP, MG)", "company sites"),
    "2401": ("tobacco (RS, SC, PR)", "SindiTabaco"),
    "6802": ("granite/stone (ES Cachoeiro, Serra)", "Centrorochas"),
    "2818": ("Hydro Alunorte (PA) alumina", "Hydro"),
    "1502": ("tallow (SP, MT)", "ABRA"),
    "2709": ("Petrobras, Shell, PRIO, Equinor (RJ, SP offshore)", "ANP"),
    "2710": ("Petrobras refineries", "ANP"),
    "4409": ("pine mouldings (PR, SC)", "Abimci"),
    "4418": ("doors, mouldings (PR, SC)", "Abimci"),
    "4412": ("plywood (PR, SC)", "Abimci"),
    "4407": ("sawn pine (PR, SC)", "Abimci"),
    "4011": ("Pirelli, Goodyear, Bridgestone, Michelin (SP, BA, RJ)", "ANIP"),
    "9306": ("CBC (SP Ribeirão Pires)", "CBC"),
    "9303": ("Taurus (RS São Leopoldo)", "Taurus filings"),
    "1701": ("Raízen, São Martinho, Cosan (SP)", "UNICA"),
    "2207": ("Raízen, São Martinho (SP)", "UNICA"),
    "7108": ("gold miners (MG, PA, MT)", "ANM"),
    "2601": ("Vale, CSN Mineração (MG, PA)", "company filings"),
    "8708": ("auto-parts suppliers (SP, MG, PR)", "Sindipeças"),
}



def comtrade_df():
    if "ct" in _CACHE_D:
        return _CACHE_D["ct"]
    rows = []
    for f in glob.glob(str(CACHE / "comtrade" / "842_*.json")):
        j = json.loads(Path(f).read_text())
        for x in j.get("data") or []:
            rows.append(dict(period=str(x["period"]), hs4=str(x["cmdCode"]), partner=int(x["partnerCode"]),
                             pdesc=x.get("partnerDesc"), cif=x.get("primaryValue") or 0.0, fob=x.get("fobvalue"),
                             kg=x.get("netWgt"), file=os.path.basename(f), allp=f.endswith("_all.json")))
    df = pd.DataFrame(rows)
    if len(df):
        df["ym"] = pd.to_datetime(df.period + "01", format="%Y%m%d")
        # prefer the all-partner calls; drop duplicate (period, hs4, partner)
        df = df.sort_values("allp", ascending=False).drop_duplicates(["period", "hs4", "partner"])
    _CACHE_D["ct"] = df
    return df


M49 = {76: "Brazil", 170: "Colombia", 704: "Vietnam", 604: "Peru", 484: "Mexico", 124: "Canada", 699: "India", 360: "Indonesia",
       757: "Switzerland", 320: "Guatemala", 340: "Honduras", 558: "Nicaragua", 231: "Ethiopia", 800: "Uganda", 188: "Costa Rica",
       218: "Ecuador", 36: "Australia", 32: "Argentina", 858: "Uruguay", 600: "Paraguay", 152: "Chile", 554: "New Zealand", 156: "China",
       392: "Japan", 410: "Korea", 251: "France", 276: "Germany", 528: "Netherlands", 380: "Italy", 381: "Italy", 724: "Spain", 752: "Sweden",
       246: "Finland", 56: "Belgium", 826: "UK", 643: "Russia", 710: "South Africa", 792: "Turkey", 804: "Ukraine", 398: "Kazakhstan",
       682: "Saudi Arabia", 579: "Norway", 368: "Iraq", 328: "Guyana", 862: "Venezuela", 214: "Dominican Rep.", 40: "Austria", 620: "Portugal",
       764: "Thailand", 458: "Malaysia", 616: "Poland", 372: "Ireland", 842: "USA"}


def mirror_annual(a0="2024-01-01", a1="2024-12-01"):
    """calendar-2024 base (needs 12 months of all-partner calls)."""
    ct = comtrade_df()
    out = {}
    if not len(ct):
        return out
    a = ct[(ct.ym >= a0) & (ct.ym <= a1) & ct.allp]
    for h, g in a.groupby("hs4"):
        w = g[g.partner == 0].cif.sum()
        p = g[g.partner != 0].groupby("partner").cif.sum().sort_values(ascending=False)
        if w <= 0 or g.ym.nunique() < 12:
            continue
        sh = p / w * 100
        br = float(sh.get(76, 0.0))
        comp = sh[sh.index != 76]
        out[h] = dict(br_share=round(br, 1), hhi=round(float((sh ** 2).sum()), 0), n_gt5=int((sh > 5).sum()),
                      top3="; ".join(f"{M49.get(c, c)} {v:.0f}%" for c, v in comp.head(3).items()), us_imports_bn=round(w / 1e9, 3))
    return out



# ================================================================ 5. measured effects
MONTHS = pd.date_range("2023-01-01", "2026-09-01", freq="MS")
POST_REG = ["ann", "R2", "R3", "R4", "R5"]


def month_regime(t):
    if t == pd.Timestamp("2025-07-01"):
        return "ann"
    if t <= pd.Timestamp("2025-06-01"):
        return "pre"
    return regime_of(t)


def build_panel(unit="hs4", min_v24=5e6):
    """balanced unit x month panel: US, world, ROW (FOB US$), plus 2024 US value."""
    us = D("us_ncm")
    if unit == "hs4":
        u = us.groupby(["hs4", "ym"]).fob.sum().rename("us")
        w = D("world_hs4").groupby(["hs4", "ym"]).fob.sum().rename("world")
        key = "hs4"
    else:
        u = us.groupby(["ncm", "ym"]).fob.sum().rename("us")
        w = D("world_ncm").groupby(["ncm", "ym"]).fob.sum().rename("world")
        key = "ncm"
    v24 = u[u.index.get_level_values(1).year == 2024].groupby(level=0).sum()
    keep = v24[v24 >= min_v24].index
    idx = pd.MultiIndex.from_product([keep, MONTHS], names=[key, "ym"])
    p = pd.DataFrame(index=idx).join(u).join(w).fillna(0.0)
    p["world"] = np.maximum(p.world, p.us)
    p["row"] = p.world - p.us
    p["v24"] = v24.reindex(p.index.get_level_values(0)).values
    return p.reset_index()


def twfe(Y, X, W=None):
    """Y: N x T, X: K x N x T. Two-way within transformation (balanced), optional unit weights W (N)."""
    def dm(A):
        if W is None:
            return A - A.mean(axis=1, keepdims=True) - A.mean(axis=0, keepdims=True) + A.mean()
        w = W / W.sum()
        ai = A.mean(axis=1, keepdims=True)
        at = (w[:, None] * A).sum(axis=0, keepdims=True)
        return A - ai - at + (w[:, None] * ai).sum()
    y = dm(Y).ravel()
    Xs = np.column_stack([dm(x).ravel() for x in X])
    if W is not None:
        sw = np.sqrt(np.repeat(W / W.mean(), Y.shape[1]))
        b, *_ = np.linalg.lstsq(Xs * sw[:, None], y * sw, rcond=None)
    else:
        b, *_ = np.linalg.lstsq(Xs, y, rcond=None)
    return b


def make_design(p, g, key, outcome="triple", groups=("covered", "relief", "232"), include_crude=False,
                include_232=True, pre_start="2023-01-01", drop=(), weighted=False, seasonal=False):
    """event-time design: D[g, r] = 1[group g] x 1[month in regime r]; reference = exempt (excl. crude unless included)."""
    p = p.copy()
    p["hs4"] = p[key].str[:4]
    p["group"] = p.hs4.map(g.group).fillna("exempt")
    if not include_crude:
        p = p[p.group != "crude"]
    if not include_232:
        p = p[p.group != "232"]
    p = p[~p.hs4.isin(drop)]
    # log offset k_i = 1% of the unit's 2024 mean monthly value (log1p on US$ sends a zero month ~13 log points down)
    k_us = p.groupby(key).us.transform(lambda s: 0.01 * max(s[p.loc[s.index, "ym"].dt.year == 2024].mean(), 1.0))
    k_row = p.groupby(key).row.transform(lambda s: 0.01 * max(s[p.loc[s.index, "ym"].dt.year == 2024].mean(), 1.0))
    if outcome == "triple":
        p["y"] = np.log(p.us + k_us) - np.log(p.row + k_row)
    elif outcome == "level":
        p["y"] = np.log(p.us + k_us)
    elif outcome == "share":
        p["y"] = np.where(p.world > 0, p.us / p.world, 0.0)
    elif outcome == "row":
        p["y"] = np.log(p.row + k_row)
    units = sorted(p[key].unique())
    Y = p.pivot(index=key, columns="ym", values="y").loc[units]
    if seasonal:
        Y = Y - Y.shift(12, axis=1)
    Y = Y.loc[:, Y.columns >= pd.Timestamp(pre_start) if not seasonal else Y.columns >= max(pd.Timestamp(pre_start), pd.Timestamp("2024-01-01"))]
    cols = list(Y.columns)
    reg = [month_regime(t) for t in cols]
    grp_u = p.drop_duplicates(key).set_index(key).group.loc[units].values
    gl = [x for x in groups if x in set(grp_u)] + (["crude"] if include_crude and "crude" in set(grp_u) else [])
    names, X = [], []
    for gg in gl:
        for r in POST_REG:
            if gg == "crude" and r == "ann":
                pass
            m = np.outer(grp_u == gg, np.array([x == r for x in reg])).astype(float)
            if m.sum() == 0:
                continue
            names.append(f"{gg}:{r}"); X.append(m)
    W = p.drop_duplicates(key).set_index(key).v24.loc[units].values if weighted else None
    return Y.values, np.array(X), names, grp_u, units, W, cols


def cluster_boot(Y, X, grp_u, W=None, nboot=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    N = Y.shape[0]
    out = np.empty((nboot, X.shape[0]))
    for b in range(nboot):
        ii = rng.integers(0, N, N)
        out[b] = twfe(Y[ii], X[:, ii, :], None if W is None else W[ii])
    return out


def placebo_perm(p, g, key, names_base, nperm=2000, seed=SEED, **kw):
    """permute group labels across HS4 (keeping group sizes) and re-estimate."""
    rng = np.random.default_rng(seed)
    Y, X, names, grp_u, units, W, cols = make_design(p, g, key, **kw)
    hs4u = np.array([u[:4] for u in units])
    reg = np.array([month_regime(t) for t in cols])
    out = np.full((nperm, len(names)), np.nan)
    for b in range(nperm):
        perm = rng.permutation(grp_u)
        Xp = []
        for nm in names:
            gg, r = nm.split(":")
            Xp.append(np.outer(perm == gg, reg == r).astype(float))
        out[b] = twfe(Y, np.array(Xp), W)
    return names, out


@step
def effects():
    g = hs4_status()
    g.to_csv(CACHE / "hs4_status.csv")
    res_rows = []
    p4 = build_panel("hs4")
    R["did.panel_hs4"] = {"units": int(p4.hs4.nunique()), "months": len(MONTHS), "min_v24_usd": 5e6,
                          "groups": g.loc[g.index.isin(p4.hs4.unique())].group.value_counts().to_dict()}
    # ---- baseline: HS4, triple-diff, excl crude, incl 232, pre 2023-01, unweighted
    Y, X, names, grp_u, units, W, cols = make_design(p4, g, "hs4")
    b0 = twfe(Y, X, W)
    bs = cluster_boot(Y, X, grp_u, W)
    pn, pl = placebo_perm(p4, g, "hs4", names)
    base = {}
    for j, nm in enumerate(names):
        ci80 = np.percentile(bs[:, j], [10, 90]); ci90 = np.percentile(bs[:, j], [5, 95])
        pp = float(np.mean(np.abs(pl[:, j]) >= abs(b0[j])))
        base[nm] = dict(coef=float(b0[j]), pct=float(100 * (np.exp(b0[j]) - 1)), ci80=ci80.tolist(), ci90=ci90.tolist(),
                        placebo_p=pp)
        res_rows.append(dict(estimator="event_time_twfe", unit="hs4", outcome="triple", window=nm.split(":")[1],
                             group=nm.split(":")[0], cell="baseline", coef=b0[j], pct=100 * (np.exp(b0[j]) - 1),
                             ci80_lo=ci80[0], ci80_hi=ci80[1], ci90_lo=ci90[0], ci90_hi=ci90[1], placebo_p=pp,
                             n_units=len(units), n_months=len(cols)))
    R["did.baseline"] = base
    print("baseline:"); [print(f"  {k}: {v['pct']:+.1f}%  CI80 {100*(np.exp(v['ci80'][0])-1):+.1f}..{100*(np.exp(v['ci80'][1])-1):+.1f}  p={v['placebo_p']:.3f}") for k, v in base.items()]
    # ---- level & ROW outcomes (baseline cell) for diversion
    for oc in ["level", "row"]:
        Y2, X2, n2, gu2, u2, W2, c2 = make_design(p4, g, "hs4", outcome=oc)
        b2 = twfe(Y2, X2, W2); bs2 = cluster_boot(Y2, X2, gu2, W2, nboot=1000)
        for j, nm in enumerate(n2):
            res_rows.append(dict(estimator="event_time_twfe", unit="hs4", outcome=oc, window=nm.split(":")[1],
                                 group=nm.split(":")[0], cell="baseline", coef=b2[j], pct=100 * (np.exp(b2[j]) - 1),
                                 ci80_lo=np.percentile(bs2[:, j], 10), ci80_hi=np.percentile(bs2[:, j], 90),
                                 ci90_lo=np.percentile(bs2[:, j], 5), ci90_hi=np.percentile(bs2[:, j], 95),
                                 n_units=len(u2), n_months=len(c2)))
        R[f"did.baseline_{oc}"] = {nm: float(100 * (np.exp(b2[j]) - 1)) for j, nm in enumerate(n2)}
    # ---- robustness grid (point estimates)
    import itertools
    pn_ = build_panel("ncm", min_v24=1e6)
    grid = []
    for unit, oc, crude, inc232, pre, dropcb, wtd, seas in itertools.product(
            ["hs4", "ncm"], ["triple", "level", "share"], [False, True], [True, False], ["2023-01-01", "2024-01-01"],
            [False, True], [False, True], [False, True]):
        if seas and pre == "2024-01-01":
            continue
        pp_ = p4 if unit == "hs4" else pn_
        try:
            Yr, Xr, nr, gur, ur, Wr, cr = make_design(pp_, g, unit, outcome=oc, include_crude=crude, include_232=inc232,
                                                     pre_start=pre, drop=("0901", "0202", "1602") if dropcb else (),
                                                     weighted=wtd, seasonal=seas)
            br = twfe(Yr, Xr, Wr)
        except Exception as e:  # noqa
            print("  grid cell failed", unit, oc, e); continue
        cell = f"{unit}|{oc}|crude={int(crude)}|232={int(inc232)}|pre={pre[:4]}|dropCB={int(dropcb)}|w={int(wtd)}|seas={int(seas)}"
        for j, nm in enumerate(nr):
            grid.append(dict(estimator="event_time_twfe", unit=unit, outcome=oc, window=nm.split(":")[1],
                             group=nm.split(":")[0], cell=cell, coef=br[j],
                             pct=100 * (np.exp(br[j]) - 1) if oc != "share" else np.nan, n_units=len(ur), n_months=len(cr)))
    G = pd.DataFrame(grid)
    res_rows += grid
    sign = {}
    for (gg, w), s in G.groupby(["group", "window"]):
        bsign = np.sign(base.get(f"{gg}:{w}", {}).get("coef", np.nan))
        sign[f"{gg}:{w}"] = dict(n_cells=len(s), share_same_sign=float(np.mean(np.sign(s.coef) == bsign)),
                                 median_pct=float(np.nanmedian(s.pct)))
    R["did.robustness_sign_share"] = sign
    # ---- intensity spec: elasticity on ln(1 + tau) by class
    el = intensity_elasticity(p4, g)
    R["did.elasticity"] = el
    pd.DataFrame(res_rows).to_csv(OUT / "did_results.csv", index=False)
    save_results()
    return base


def tau_matrix(units, cols, g, key="hs4"):
    T = np.zeros((len(units), len(cols)))
    for i, u in enumerate(units):
        h = u[:4]
        for j, t in enumerate(cols):
            r = regime_of(t) if t >= pd.Timestamp("2023-01-01") else "R0"
            if t < pd.Timestamp("2025-03-01"):
                r = "R0"
            T[i, j] = g[f"rate_{r}"].get(h, 0.0) / 100.0
    return T


def intensity_elasticity(p, g, nboot=2000):
    """y = a_i + g_t + sum_class e_class * ln(1+tau_it); triple-diff outcome; cluster bootstrap by HS4."""
    p = p.copy(); p["group"] = p.hs4.map(g.group).fillna("exempt")
    p = p[p.group != "crude"]
    k_us = p.groupby("hs4").us.transform(lambda s: 0.01 * max(s[p.loc[s.index, "ym"].dt.year == 2024].mean(), 1.0))
    k_row = p.groupby("hs4").row.transform(lambda s: 0.01 * max(s[p.loc[s.index, "ym"].dt.year == 2024].mean(), 1.0))
    p["y"] = np.log(p.us + k_us) - np.log(p.row + k_row)
    units = sorted(p.hs4.unique())
    Y = p.pivot(index="hs4", columns="ym", values="y").loc[units]
    cols = list(Y.columns); Y = Y.values
    T = tau_matrix(units, cols, g)
    cls = np.array([hs4_class(u) for u in units])
    X = np.array([np.log1p(T) * (cls == c)[:, None] for c in ("commodity", "manufactured")])
    b = twfe(Y, X)
    bs = cluster_boot(Y, X, cls, nboot=nboot)
    out = {}
    for j, c in enumerate(("commodity", "manufactured")):
        out[c] = dict(eps=float(b[j]), ci80=np.percentile(bs[:, j], [10, 90]).tolist(), ci90=np.percentile(bs[:, j], [5, 95]).tolist())
    # pooled
    Xp = np.array([np.log1p(T)]); bp = twfe(Y, Xp); bsp = cluster_boot(Y, Xp, cls, nboot=nboot)
    out["pooled"] = dict(eps=float(bp[0]), ci80=np.percentile(bsp[:, 0], [10, 90]).tolist(), ci90=np.percentile(bsp[:, 0], [5, 95]).tolist())
    print("elasticity:", {k: round(v["eps"], 2) for k, v in out.items()})
    return out



WINDOWS_P = {"W40": ("2025-08-01", "2026-02-01"), "R2": ("2025-08-01", "2025-10-01"), "R3": ("2025-11-01", "2026-02-01"),
             "R4": ("2026-03-01", "2026-07-01"), "R5": ("2026-08-01", "2026-09-01"), "EP": ("2025-08-01", "2026-09-01"),
             "PRE": ("2025-01-01", "2025-06-01")}
TREAT_WIN = {"covered": "W40", "relief": "R2", "232": "EP", "crude": "EP", "exempt": "W40"}


def _wsum(s, a, b):
    """sum over window [a, b] and over the same calendar months of 2024 (base)."""
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    m = (s.index >= a) & (s.index <= b)
    months_ = s.index[m].month
    base = s[(s.index.year == 2024) & s.index.month.isin(months_)]
    # count multiplicity (a window may span >12 months: EP has Aug-Sep twice)
    mult = pd.Series(months_).value_counts()
    bsum = sum(base[base.index.month == mo].sum() * c for mo, c in mult.items())
    return float(s[m].sum()), float(bsum), int(m.sum())


def product_did(g=None, p=None, kgp=None):
    """additive US$ gaps per HS4 and window (no log-to-$ asymmetry).
    DD: cf_US = US_2024(same months) x C_US(window)/C_US(2024 same months), C = exempt-group aggregate (excl. crude).
    TD: cf_US = US_2024(same months) x ROW_i(window)/ROW_i(2024 same months) (product's own ROW as control).
    ROW (diversion): cf_ROW = ROW_2024 x C_ROW(window)/C_ROW(2024); in tonnes when kg is reported, valued at window UV."""
    g = hs4_status() if g is None else g
    p = build_panel("hs4") if p is None else p
    p = p.copy(); p["group"] = p.hs4.map(g.group).fillna("exempt")
    kg = D("us_ncm").groupby(["hs4", "ym"]).kg.sum().rename("us_kg")
    wkg = D("world_hs4").groupby(["hs4", "ym"]).kg.sum().rename("w_kg")
    p = p.merge(kg, left_on=["hs4", "ym"], right_index=True, how="left").merge(wkg, left_on=["hs4", "ym"], right_index=True, how="left").fillna(0.0)
    p["row_kg"] = np.maximum(p.w_kg - p.us_kg, 0.0)
    C = p[p.group == "exempt"].groupby("ym")[["us", "row", "us_kg", "row_kg"]].sum()
    rows = []
    for h, d in p.groupby("hs4"):
        d = d.set_index("ym").sort_index()
        grp = g.group.get(h, "exempt")
        out = dict(hs4=h, group=grp, **{"class": hs4_class(h)}, v24_us=float(d.us[d.index.year == 2024].sum()),
                   v24_row=float(d.row[d.index.year == 2024].sum()))
        for wn, (a, b) in WINDOWS_P.items():
            ua, ub, n = _wsum(d.us, a, b); ra, rb, _ = _wsum(d.row, a, b)
            ca, cb, _ = _wsum(C.us, a, b); cra, crb, _ = _wsum(C.row, a, b)
            f = 12.0 / n
            cf_dd = ub * ca / cb
            cf_td = ub * (ra / rb) if rb > 0 else np.nan
            out[f"dus_dd_{wn}"] = (ua - cf_dd) * f          # US$/yr; negative = loss
            out[f"dus_td_{wn}"] = (ua - cf_td) * f if rb > 0 else np.nan
            # ROW change vs control, in tonnes valued at window unit value when kg exists
            ka, kb, _ = _wsum(d.row_kg, a, b); cka, ckb, _ = _wsum(C.row_kg, a, b)
            if kb > 0 and ka > 0 and ckb > 0:
                uv = ra / ka
                out[f"drow_{wn}"] = (ka - kb * cka / ckb) * uv * f
                out[f"drow_basis_{wn}"] = "kg"
            else:
                out[f"drow_{wn}"] = (ra - rb * cra / crb) * f if crb > 0 else np.nan
                out[f"drow_basis_{wn}"] = "usd"
            out[f"us_pct_dd_{wn}"] = 100 * (ua / cf_dd - 1) if cf_dd > 0 else np.nan
        rows.append(out)
    pdid = pd.DataFrame(rows)
    tw = pdid.group.map(TREAT_WIN)
    pick = lambda col: np.array([pdid.loc[i, f"{col}_{w}"] for i, w in zip(pdid.index, tw)])
    pdid["treat_window"] = tw
    pdid["dus_dd"] = pick("dus_dd"); pdid["dus_td"] = pick("dus_td"); pdid["drow"] = pick("drow")
    pdid["gross_loss_bn_yr"] = -pdid.dus_dd / 1e9
    pdid["gross_loss_td_bn_yr"] = -pdid.dus_td / 1e9
    pdid["drow_bn_yr"] = pdid.drow / 1e9
    pdid["dus_bn_yr"] = pdid.dus_dd / 1e9
    pdid["d_div"] = np.where(pdid.dus_bn_yr < 0, np.clip(pdid.drow_bn_yr / np.abs(pdid.dus_bn_yr), 0, 1), np.nan)
    pdid["net_loss_bn_yr"] = np.where(pdid.dus_bn_yr < 0, pdid.gross_loss_bn_yr * (1 - pdid.d_div), pdid.gross_loss_bn_yr)
    return pdid


def group_div(pdid, mask, rng, nboot=2000):
    s = pdid[mask & (pdid.dus_bn_yr < 0)]
    if not len(s):
        return dict(d=np.nan, ci80=[np.nan, np.nan], n=0)
    w = np.abs(s.dus_bn_yr.values); d = s.d_div.values
    est = float(np.sum(w * d) / np.sum(w))
    bs = []
    for _ in range(nboot):
        ii = rng.integers(0, len(s), len(s))
        bs.append(np.sum(w[ii] * d[ii]) / np.sum(w[ii]))
    return dict(d=est, ci80=np.percentile(bs, [10, 90]).tolist(), ci90=np.percentile(bs, [5, 95]).tolist(), n=int(len(s)),
                gross_bn=float(s.gross_loss_bn_yr.sum()), drow_bn=float(s.drow_bn_yr.clip(lower=0).sum()))


@step
def losses():
    g = hs4_status(); p = build_panel("hs4", min_v24=1e6)
    pdid = product_did(g, p)
    pdid.to_csv(CACHE / "product_did.csv", index=False)
    rng = np.random.default_rng(SEED)
    tr = pdid.group.isin(["covered", "relief", "232"])
    R["loss.by_group"] = {gg: dict(gross_bn_yr=round(float(s.gross_loss_bn_yr.sum()), 3), net_bn_yr=round(float(s.net_loss_bn_yr.sum()), 3),
                                   v24_bn=round(float(s.v24_us.sum() / 1e9), 3),
                                   pct_of_v24=round(float(100 * s.gross_loss_bn_yr.sum() / (s.v24_us.sum() / 1e9)), 1) if s.v24_us.sum() else None,
                                            gross_td_bn_yr=round(float(s.gross_loss_td_bn_yr.sum()), 3),
                                   episode_gap_us_bn=round(float(s.dus_dd_EP.sum() / 1e9 * 14 / 12), 3),
                                   episode_gap_row_bn=round(float(s.drow_EP.sum() / 1e9 * 14 / 12), 3), n=int(len(s)))
                          for gg, s in pdid.groupby("group")}
    gross = float(pdid[tr].gross_loss_bn_yr.sum()); net = float(pdid[tr].net_loss_bn_yr.sum())
    R["loss.treated_gross_bn_yr"] = gross; R["loss.treated_net_bn_yr"] = net
    gdp = float(wq("SELECT value FROM v_annual WHERE series_id='wb/NY.GDP.MKTP.CD.BR' AND year=2025", "gdp_2025").value.iloc[0]) / 1e9
    rec("loss.gdp_2025_bn", gdp, "wb/NY.GDP.MKTP.CD.BR", SQLLOG["gdp_2025"])
    R["loss.net_pct_gdp"] = 100 * net / gdp
    top = pdid[tr].sort_values("gross_loss_bn_yr", ascending=False)
    R["loss.top10_treated_hs4"] = top.head(15)[["hs4", "group", "gross_loss_bn_yr", "gross_loss_td_bn_yr", "net_loss_bn_yr", "d_div", "drow_bn_yr", "v24_us"]].round(3).to_dict("records")
    pos = top[top.gross_loss_bn_yr > 0]
    R["loss.top10_share_of_gross"] = float(pos.head(10).gross_loss_bn_yr.sum() / pos.gross_loss_bn_yr.sum() * 100)
    R["loss.max_single_hs4_bn"] = float(pos.gross_loss_bn_yr.max())
    cov = pdid[pdid.group == "covered"]
    R["loss.covered_pct_fall"] = float(100 * cov.gross_loss_bn_yr.sum() / (cov.v24_us.sum() / 1e9))
    # diversion (H2) by class among treated lines; plan's named lists as a second cut
    R["div.by_class"] = {c: group_div(pdid, tr & (pdid["class"] == c), rng) for c in ("commodity", "manufactured")}
    R["div.plan_lists"] = {"commodity": group_div(pdid, pdid.hs4.isin(COMMODITY_HS4 - {"2709"}) & tr, rng),
                           "manufactured": group_div(pdid, pdid.hs4.isin(MANUF_HS4) & tr, rng)}
    R["div.by_group"] = {gg: group_div(pdid, pdid.group == gg, rng) for gg in ("covered", "relief", "232")}
    # windows for covered lines: the 40% period, the Section 122 period, the 301 period; pre-period placebo
    for wn in ["W40", "R2", "R3", "R4", "R5", "PRE"]:
        s = pdid[pdid.group == "covered"]
        R[f"loss.covered_{wn}_gross_bn_yr"] = float(-s[f"dus_dd_{wn}"].sum() / 1e9)
        R[f"loss.covered_{wn}_pct"] = float(100 * s[f"dus_dd_{wn}"].sum() / (s.v24_us.sum()))
        s = pdid[pdid.group == "relief"]
        R[f"loss.relief_{wn}_gross_bn_yr"] = float(-s[f"dus_dd_{wn}"].sum() / 1e9)
        s = pdid[pdid.group == "232"]
        R[f"loss.232_{wn}_gross_bn_yr"] = float(-s[f"dus_dd_{wn}"].sum() / 1e9)
    print(json.dumps({k: R[k] for k in ["loss.by_group", "loss.treated_gross_bn_yr", "loss.treated_net_bn_yr", "loss.net_pct_gdp",
                                        "loss.top10_share_of_gross", "loss.max_single_hs4_bn", "div.by_class", "div.plan_lists", "div.by_group",
                                        "loss.covered_W40_pct", "loss.covered_R4_pct", "loss.covered_R5_pct", "loss.covered_PRE_pct"]}, indent=0, default=str)[:4000])
    # cluster bootstrap over HS4 for the national totals and the H2 class difference
    T = pdid[tr].reset_index(drop=True)
    bs_g, bs_n, bs_dd = [], [], []
    for _ in range(2000):
        ii = rng.integers(0, len(T), len(T)); s = T.iloc[ii]
        bs_g.append(s.gross_loss_bn_yr.sum()); bs_n.append(s.net_loss_bn_yr.sum())
        def dcls(c):
            q_ = s[(s["class"] == c) & (s.dus_bn_yr < 0)]
            w = np.abs(q_.dus_bn_yr.values)
            return np.sum(w * q_.d_div.values) / np.sum(w) if w.sum() > 0 else np.nan
        bs_dd.append(dcls("commodity") - dcls("manufactured"))
    R["loss.treated_gross_ci80"] = np.percentile(bs_g, [10, 90]).tolist()
    R["loss.treated_net_ci80"] = np.percentile(bs_n, [10, 90]).tolist()
    R["loss.treated_net_ci90"] = np.percentile(bs_n, [5, 95]).tolist()
    R["div.class_diff"] = dict(d=R["div.by_class"]["commodity"]["d"] - R["div.by_class"]["manufactured"]["d"],
                               ci80=np.nanpercentile(bs_dd, [10, 90]).tolist(), ci90=np.nanpercentile(bs_dd, [5, 95]).tolist())
    # pre-trend adjusted covered fall
    a, b = R["loss.covered_W40_pct"], R["loss.covered_PRE_pct"]
    R["loss.covered_W40_pct_pretrend_adj"] = 100 * ((1 + a / 100) / (1 + b / 100) - 1)
    print("CIs", R["loss.treated_gross_ci80"], R["loss.treated_net_ci80"], R["div.class_diff"], R["loss.covered_W40_pct_pretrend_adj"])
    h7()
    save_results()
    return pdid


def h7():
    """decomposition of the y/y change in US-bound exports, Aug-2025..Jul-2026 vs Aug-2024..Jul-2025, by R2 status (HS6 fractions)."""
    S = list_shares()
    st = status_table(S)
    us = D("us_ncm")
    a = us[(us.ym >= "2025-08-01") & (us.ym <= "2026-07-01")].groupby("hs6").fob.sum()
    b = us[(us.ym >= "2024-08-01") & (us.ym <= "2025-07-01")].groupby("hs6").fob.sum()
    dlt = a.subtract(b, fill_value=0.0).rename("d")
    r2 = st[st.regime == "R2"].pivot_table(index="hs6", columns="status", values="frac", aggfunc="sum").fillna(0)
    r3 = st[st.regime == "R3"].pivot_table(index="hs6", columns="status", values="frac", aggfunc="sum").fillna(0)
    m = r2.join(dlt, how="right").fillna(0.0)
    m["full_r3"] = r3.full.reindex(m.index).fillna(0.0)
    crude = m.index.str[:4] == "2709"
    out = {}
    out["crude"] = float(m.d[crude].sum())
    mm = m[~crude]
    out["232"] = float((mm["232"] * mm.d).sum())
    out["full_persistent"] = float((np.minimum(mm.full, mm.full_r3) * mm.d).sum())
    out["full_relieved"] = float(((mm.full - np.minimum(mm.full, mm.full_r3)) * mm.d).sum())
    out["exempt_other"] = float((mm.exempt * mm.d).sum())
    tot = float(m.d.sum())
    R["h7.decomp_bn"] = {k: round(v / 1e9, 3) for k, v in out.items()}
    R["h7.total_change_bn"] = round(tot / 1e9, 3)
    neg = {k: v for k, v in out.items()}
    R["h7.share_crude_plus_232"] = 100 * (out["crude"] + out["232"]) / tot if tot < 0 else None
    R["h7.share_full"] = 100 * (out["full_persistent"] + out["full_relieved"]) / tot if tot < 0 else None
    print("H7:", R["h7.decomp_bn"], "total", R["h7.total_change_bn"], "crude+232 share", R["h7.share_crude_plus_232"], "full share", R["h7.share_full"])



# ---------------------------------------------------------------- 5.3 unit values
UV_NCM = {"09011110": "green coffee", "02023000": "frozen boneless beef", "72011000": "pig iron", "72071200": "steel slabs",
          "47032900": "eucalyptus pulp", "20091200": "OJ not-from-concentrate", "20091100": "FCOJ", "17011400": "raw cane sugar"}
REG_LIST = ["pre", "R2", "R3", "R4", "R5"]


def uv_ratio_table(df, key):
    us = df[df.country == "Estados Unidos"].groupby([key, "ym"])[["fob", "kg"]].sum()
    row = df[df.country != "Estados Unidos"].groupby([key, "ym"])[["fob", "kg"]].sum()
    t = us.join(row, lsuffix="_us", rsuffix="_row").reset_index()
    t = t[(t.kg_us > 0) & (t.kg_row > 0)]
    t["uv_us"] = t.fob_us / t.kg_us; t["uv_row"] = t.fob_row / t.kg_row
    t["lr"] = np.log(t.uv_us / t.uv_row)
    t["reg"] = [("pre" if (pd.Timestamp("2024-01-01") <= x <= pd.Timestamp("2025-07-01")) else
                 (regime_of(x) if x >= pd.Timestamp("2025-08-01") else "early")) for x in t.ym]
    return t


@step
def unit_values():
    g = hs4_status()
    t = uv_ratio_table(D("div"), "hs4")
    # value-weighted (US fob) mean log ratio by regime
    agg = t.groupby(["hs4", "reg"]).apply(lambda s: np.average(s.lr, weights=s.fob_us)).unstack()
    ch = agg[[r for r in REG_LIST if r in agg.columns]].sub(agg["pre"], axis=0).drop(columns="pre")
    ch["group"] = ch.index.map(g.group)
    ch.to_csv(CACHE / "uv_ratio_change_hs4.csv")
    R["uv.hs4_change_pct"] = {h: {r: round(100 * (np.exp(v) - 1), 1) for r, v in row.drop("group").items() if pd.notna(v)}
                              for h, row in ch.iterrows() if h in TOP40}
    # DiD covered vs exempt on the log ratio (R2), cluster bootstrap over HS4
    rng = np.random.default_rng(SEED)
    for grp in ("covered", "relief", "232"):
        for r in ("R2", "R3", "R4", "R5"):
            a = ch[ch.group == grp][r].dropna().values; b = ch[ch.group == "exempt"][r].dropna().values
            if len(a) < 2 or len(b) < 2:
                continue
            est = a.mean() - b.mean()
            bs = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(2000)]
            R[f"uv.did_{grp}_{r}"] = dict(pct=100 * (np.exp(est) - 1), ci80=[100 * (np.exp(x) - 1) for x in np.percentile(bs, [10, 90])], n=len(a))
    # NCM detail for the seven lines
    tn = uv_ratio_table(D("div_ncm"), "ncm")
    tn = tn[tn.ncm.isin(UV_NCM)]
    tn.to_csv(CACHE / "uv_ratio_ncm.csv", index=False)
    an = tn.groupby(["ncm", "reg"]).apply(lambda s: np.average(s.lr, weights=s.fob_us)).unstack()
    chn = an[[r for r in REG_LIST if r in an.columns]].sub(an["pre"], axis=0).drop(columns="pre")
    R["uv.ncm_change_pct"] = {f"{n} {UV_NCM[n]}": {r: round(100 * (np.exp(v) - 1), 1) for r, v in row.items() if pd.notna(v)}
                              for n, row in chn.iterrows()}
    R["uv.ncm_level_pre"] = {f"{n} {UV_NCM[n]}": round(float(np.exp(v)), 3) for n, v in an["pre"].items()}
    print(json.dumps(R["uv.ncm_change_pct"], indent=0)); print({k: v for k, v in R.items() if k.startswith("uv.did")})
    save_results()


# ---------------------------------------------------------------- 5.5 states and employment
UF_ABBR = {"Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF",
           "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
           "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI",
           "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR",
           "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"}


def sidra(tab):
    j = json.loads((CACHE / "sidra" / f"t{tab}.json").read_text())
    df = pd.DataFrame(j[1:])
    df["V"] = pd.to_numeric(df.V, errors="coerce")
    return df


@step
def states():
    pdid = pd.read_csv(CACHE / "product_did.csv", dtype={"hs4": str})
    sy = D("state_hs4_y")
    s24 = sy[sy.year == 2024].groupby(["uf", "hs4"]).fob.sum()
    sh = (s24 / s24.groupby(level="hs4").transform("sum")).rename("sh").reset_index()
    m = sh.merge(pdid[["hs4", "group", "gross_loss_bn_yr", "net_loss_bn_yr"]], on="hs4")
    tr = m.group.isin(["covered", "relief", "232"])
    uf_loss = m[tr].assign(gl=m.sh * m.gross_loss_bn_yr, nl=m.sh * m.net_loss_bn_yr).groupby("uf")[["gl", "nl"]].sum()
    uf_loss = uf_loss.sort_values("gl", ascending=False)
    pos = uf_loss.gl.clip(lower=0)
    R["states.loss_bn_yr"] = uf_loss.round(3).to_dict("index")
    R["states.top5_share_gross"] = float(pos.head(5).sum() / pos.sum() * 100)
    R["states.top5"] = list(pos.head(5).index)
    # exposure: covered-line US exports 2024 / UF total exports 2024
    g = hs4_status()
    cov24 = s24.reset_index().assign(f=lambda x: x.hs4.map(g.full_R2).fillna(0.0) * (x.hs4 != "2709"))
    cov24 = (cov24.fob * cov24.f).groupby(cov24.uf).sum()
    ws = D("world_state_m"); tot24 = ws[ws.ym.dt.year == 2024].groupby("uf").fob.sum()
    us_st = D("state_m"); us24 = us_st[us_st.ym.dt.year == 2024].groupby("uf").fob.sum()
    expo = pd.DataFrame({"covered_us_2024_bn": cov24 / 1e9, "us_2024_bn": us24 / 1e9, "total_2024_bn": tot24 / 1e9})
    expo["exposure_pct"] = 100 * expo.covered_us_2024_bn / expo.total_2024_bn
    expo = expo[expo.index.isin(UF_ABBR)]
    expo["uf2"] = expo.index.map(UF_ABBR)
    # UF DiD on monthly US-bound exports: log(us_uf,t) on exposure x post, UF and month FE, cluster bootstrap by UF
    p = us_st[us_st.uf.isin(UF_ABBR)].pivot_table(index="uf", columns="ym", values="fob", aggfunc="sum").reindex(columns=MONTHS).fillna(0.0)
    p = p.loc[expo.index]
    k = 0.01 * p.loc[:, p.columns.year == 2024].mean(axis=1).values[:, None]
    Y = np.log(p.values + k)
    post = np.array([(t >= pd.Timestamp("2025-08-01")) & (t <= pd.Timestamp("2026-02-01")) for t in p.columns], float)
    post2 = np.array([t >= pd.Timestamp("2026-03-01") for t in p.columns], float)
    e = expo.exposure_pct.values / 10.0   # per 10 pp of exports in covered US lines
    X = np.array([np.outer(e, post), np.outer(e, post2)])
    b = twfe(Y, X); rng = np.random.default_rng(SEED); N = len(e)
    bs = np.array([twfe(Y[ii], X[:, ii, :]) for ii in (rng.integers(0, N, N) for _ in range(2000))])
    R["states.did_us_exports"] = dict(per10pp_W40_pct=100 * (np.exp(b[0]) - 1), ci80_W40=[100 * (np.exp(x) - 1) for x in np.percentile(bs[:, 0], [10, 90])],
                                      per10pp_post_pct=100 * (np.exp(b[1]) - 1), ci80_post=[100 * (np.exp(x) - 1) for x in np.percentile(bs[:, 1], [10, 90])], n_uf=N)
    # employment proxies: PIM-PF (14 locations, index 2022=100, variable 12606) and PNAD unemployment (27 UF)
    pim = sidra(8888)
    pim = pim[(pim.D2C == "12606")]
    pim["ym"] = pd.to_datetime(pim.D3C, format="%Y%m"); pim = pim.dropna(subset=["V"])
    pv = pim.pivot_table(index="D1N", columns="ym", values="V")
    pv = pv.loc[:, pv.columns >= "2024-01-01"]
    yy = np.log(pv).sub(np.log(pv).shift(12, axis=1)).dropna(axis=1, how="all")    # y/y log change (NSA index)
    pre_ = yy.loc[:, (yy.columns >= "2025-01-01") & (yy.columns <= "2025-07-01")].mean(axis=1)
    pst_ = yy.loc[:, yy.columns >= "2025-08-01"].mean(axis=1)
    dd = (pst_ - pre_).rename("d_pim")
    ex = expo.set_index(expo.index).exposure_pct
    J = pd.concat([dd, ex], axis=1, join="inner")
    R["states.pim"] = dict(n=len(J), slope_per10pp=float(np.polyfit(J.exposure_pct / 10, J.d_pim * 100, 1)[0]) if len(J) > 2 else None,
                           corr=float(np.corrcoef(J.exposure_pct, J.d_pim)[0, 1]) if len(J) > 2 else None,
                           sd_cross_state_pp=float(J.d_pim.std() * 100), last=str(pv.columns.max())[:10],
                           by_uf={k: round(100 * v, 2) for k, v in dd.items()})
    if len(J) > 2:
        hi = J[J.exposure_pct >= J.exposure_pct.median()].d_pim.mean(); lo = J[J.exposure_pct < J.exposure_pct.median()].d_pim.mean()
        R["states.pim"]["exposed_minus_unexposed_pp"] = float(100 * (hi - lo))
        R["states.pim"]["gap_in_sd"] = float((hi - lo) / J.d_pim.std())
        R["states.pim"]["perm_p_slope"] = perm_slope(J.exposure_pct.values, J.d_pim.values)
    un = sidra(4099); un["q"] = un.D3C
    uv_ = un.pivot_table(index="D1N", columns="q", values="V")
    qs = sorted(uv_.columns)
    def qd(q):
        return uv_[q] - uv_[str(int(q[:4]) - 1) + q[4:]]
    pre_q = [q for q in qs if q in ("202501", "202502")]; post_q = [q for q in qs if q >= "202503"]
    du = (pd.concat([qd(q) for q in post_q], axis=1).mean(axis=1) - pd.concat([qd(q) for q in pre_q], axis=1).mean(axis=1)).rename("d_un")
    J2 = pd.concat([du, ex], axis=1, join="inner")
    R["states.unemp"] = dict(n=len(J2), slope_per10pp=float(np.polyfit(J2.exposure_pct / 10, J2.d_un, 1)[0]), corr=float(np.corrcoef(J2.exposure_pct, J2.d_un)[0, 1]),
                             sd_cross_state_pp=float(J2.d_un.std()), last=qs[-1], perm_p_slope=perm_slope(J2.exposure_pct.values, J2.d_un.values))
    hi = J2[J2.exposure_pct >= J2.exposure_pct.median()].d_un.mean(); lo = J2[J2.exposure_pct < J2.exposure_pct.median()].d_un.mean()
    R["states.unemp"]["exposed_minus_unexposed_pp"] = float(hi - lo); R["states.unemp"]["gap_in_sd"] = float((hi - lo) / J2.d_un.std())
    expo = expo.join(uf_loss, how="left").join(dd, how="left").join(du, how="left")
    expo.to_csv(CACHE / "state_exposure.csv")
    R["states.exposure_top"] = expo.sort_values("exposure_pct", ascending=False).head(8)[["uf2", "exposure_pct", "covered_us_2024_bn", "gl"]].round(3).to_dict("records")
    print(json.dumps({k: R[k] for k in ["states.top5_share_gross", "states.top5", "states.did_us_exports", "states.exposure_top"]}, default=str, indent=0)[:3000])
    print({k: v for k, v in R["states.pim"].items() if k != "by_uf"}); print(R["states.unemp"])
    save_results()


def perm_slope(x, y, n=5000, seed=SEED):
    rng = np.random.default_rng(seed); obs = abs(np.polyfit(x, y, 1)[0])
    vals = np.array([abs(np.polyfit(rng.permutation(x), y, 1)[0]) for _ in range(n)])
    return float((np.sum(vals >= obs) + 1) / (n + 1))



# ---------------------------------------------------------------- 5.4 US-side mirror (Comtrade) + competitor rate table
FL10 = {32, 50, 116, 124, 218, 222, 320, 340, 699, 360, 400, 458, 484, 586, 144, 826, 780}   # 10% forced-labour tier (memo 2026-15274 s.1(a)(i))
FL_NET10 = {"EU", 490}                       # 10% net of MFN (EU, Taiwan)
FL_NET125 = {392, 410, 757}                  # 12.5% net of MFN (Japan, Korea, Switzerland)
FL_INVEST = {12, 24, 32, 36, 44, 48, 50, 76, 116, 124, 152, 156, 170, 188, 214, 218, 818, 222, "EU", 320, 328, 340, 344, 699, 360, 368,
             376, 392, 400, 398, 414, 434, 458, 484, 504, 554, 558, 566, 578, 512, 586, 604, 608, 634, 643, 682, 702, 710, 410, 144, 757,
             490, 764, 780, 792, 784, 826, 858, 862, 704}
EU = {40, 56, 100, 191, 196, 203, 208, 233, 246, 251, 276, 300, 348, 372, 381, 428, 440, 442, 470, 528, 616, 620, 642, 703, 705, 724, 752}
RECIP_R2 = {188: 15, 218: 15, 699: 25, 360: 19, 392: 15, 458: 19, 558: 18, 710: 30, 410: 15, 757: 39, 764: 19, 792: 15, 800: 15, 704: 20}


def comp_rate(c, hs4, reg, S_h4):
    """added US rate on a competitor's good (pp), by regime. S_h4: dict list -> HS4 exempt share (value-weighted HS6)."""
    cc = "EU" if c in EU else c
    usmca = c in (484, 124)
    if S_h4.get("232", 0) >= 0.5:
        return 0.0          # Section 232 applies to all origins: no relative wedge (UK/EU/Japan deal rates ignored)
    if reg in ("R1", "R2", "R3"):
        if usmca or c == 643:
            return 0.0       # USMCA-compliant goods / Russia outside the reciprocal regime
        ex = S_h4.get("recip_ii", 0) if reg != "R3" else max(S_h4.get("recip_ii", 0), S_h4.get("ag", 0))
        base = 10.0 if reg == "R1" else (50.0 if c == 699 else 15.0 if cc == "EU" else 30.0 if c == 156 else RECIP_R2.get(c, 10.0))
        if reg == "R3" and c == 156:
            base = 20.0
        return base * (1 - ex)
    if reg == "R4":
        return 0.0 if usmca else 10.0 * (1 - S_h4.get("s122", 0))
    if reg == "R5":
        if cc not in FL_INVEST and c not in FL_INVEST:
            return 0.0
        r = 10.0 if (c in FL10 or cc in FL_NET10 or c in FL_NET10) else 12.5
        return r * (1 - S_h4.get("fl", 0))
    return 0.0


def hs4_list_shares():
    S = list_shares()
    us = D("us_ncm"); v6 = us[us.ym.dt.year == 2024].groupby("hs6").fob.sum()
    out = {}
    for h in MIRROR_HS4:
        hs6 = v6[v6.index.str[:4] == h]
        w = hs6 / hs6.sum() if hs6.sum() > 0 else None
        def ws(names):
            if w is None:
                return 0.0
            return float(sum(w[h6] * max(1.0 if S.get(n, {}).get(h6, 0) > 0 else 0.0 for n in names) for h6 in w.index))
        out[h] = {"232": ws(["s232_metals", "s232_autos", "s232_wood", "s232_mhdv"]), "recip_ii": ws(["recip_annex_ii_orig_inferred"]),
                  "ag": ws(["ag_eo14360_inferred"]), "s122": ws(["s122_a", "s122_b", "s122_aircraft"]),
                  "fl": ws(["fl_b", "fl_c", "fl_aircraft", "fl_pharma"])}
    return out


@step
def mirror():
    ct = comtrade_df()
    if not len(ct):
        R["gaps.mirror"] = "no Comtrade data"; save_results(); return
    g = hs4_status(); SL = hs4_list_shares()
    a = ct[ct.allp & ct.hs4.isin(MIRROR_HS4)].copy()
    a["reg"] = [("base" if pd.Timestamp("2024-01-01") <= t <= pd.Timestamp("2025-03-01") else regime_of(t) if t >= pd.Timestamp("2025-08-01")
                 else "R1" if t >= pd.Timestamp("2025-04-01") else "early") for t in a.ym]
    world = a[a.partner == 0].groupby(["hs4", "ym"]).cif.sum().rename("world")
    a = a[a.partner != 0].merge(world, left_on=["hs4", "ym"], right_index=True)
    a["share"] = 100 * a.cif / a.world
    a["uv"] = np.where(a.kg > 0, a.cif / a.kg, np.nan)
    rows, wedge_rows = [], []
    for h, d in a.groupby("hs4"):
        base = d[d.reg == "base"]
        bw = base.groupby("partner").cif.sum(); bw = bw / bw.sum()
        comps = [c for c in bw.sort_values(ascending=False).index if c != 76][:8]
        cw = bw.reindex(comps); cw = cw / cw.sum()
        br = d[d.partner == 76]
        for reg in ["base", "R1", "R2", "R3", "R4", "R5"]:
            dr = d[d.reg == reg]
            if not len(dr):
                continue
            tot = dr.groupby("ym").world.first().sum()
            sh_br = 100 * dr[dr.partner == 76].cif.sum() / tot
            comp = dr[dr.partner.isin(comps)]
            uv_br = dr[dr.partner == 76].cif.sum() / dr[dr.partner == 76].kg.sum() if dr[dr.partner == 76].kg.sum() > 0 else np.nan
            uv_c = comp.cif.sum() / comp.kg.sum() if comp.kg.sum() > 0 else np.nan
            t_br = g[f"rate_{reg}"].get(h, 0.0) if reg != "base" else 0.0
            t_c = float(sum(cw[c] * comp_rate(c, h, reg, SL[h]) for c in comps)) if reg != "base" else 0.0
            if SL[h]["232"] >= 0.5 and reg != "base":
                t_c = t_br     # Section 232 applies to every origin at the same rate: no relative wedge
            rows.append(dict(hs4=h, reg=reg, br_share=sh_br, uv_br=uv_br, uv_comp=uv_c, tau_br=t_br, tau_comp=t_c, wedge=t_br - t_c,
                             months=dr.ym.nunique(), top_comps="; ".join(str(M49.get(c, c)) for c in comps[:4])))
    M = pd.DataFrame(rows)
    b = M[M.reg == "base"].set_index("hs4")
    M["d_share"] = M.br_share - M.hs4.map(b.br_share)
    M["d_luv_cif"] = 100 * (np.log(M.uv_br / M.uv_comp) - M.hs4.map(np.log(b.uv_br / b.uv_comp)))
    M["d_luv_duty"] = M.d_luv_cif + 100 * (np.log1p(M.tau_br / 100) - np.log1p(M.tau_comp / 100))
    M.to_csv(OUT / "us_mirror.csv", index=False)
    P = M[M.reg.isin(["R2", "R3", "R4", "R5"])].dropna(subset=["d_share"])
    P = P[P.hs4 != "2709"]
    sl = np.polyfit(P.wedge, P.d_share, 1)[0]
    rng = np.random.default_rng(SEED)
    perm = []
    for _ in range(5000):
        q_ = P.copy(); q_["w"] = q_.groupby("reg").wedge.transform(lambda s: rng.permutation(s.values))
        perm.append(np.polyfit(q_.w, q_.d_share, 1)[0])
    R["mirror.slope_dshare_per_pp_wedge"] = dict(slope=float(sl), perm_p=float(np.mean(np.abs(perm) >= abs(sl))), n=len(P))
    R["mirror.base_window"] = "2024-01..2025-03 (US import months; Comtrade CIF)"
    R["mirror.table"] = M[["hs4", "reg", "br_share", "d_share", "wedge", "tau_br", "tau_comp", "d_luv_cif", "d_luv_duty", "top_comps"]].round(2).to_dict("records")
    R["mirror.base_shares"] = {h: dict(br_share=round(float(b.br_share.get(h, np.nan)), 1), comps=b.top_comps.get(h)) for h in b.index}
    R["mirror.annual_2024"] = mirror_annual()
    print(M[M.reg.isin(["base", "R2", "R3", "R5"])][["hs4", "reg", "br_share", "d_share", "wedge", "d_luv_cif", "d_luv_duty"]].round(1).to_string())
    print(R["mirror.slope_dshare_per_pp_wedge"])
    save_results()



# ---------------------------------------------------------------- BLS CPI/PPI + H8 (revealed preference of the relief)
BLS_NAMES = {"CUUR0000SEFP01": "CPI coffee", "CUUR0000SEFC": "CPI beef and veal", "CUUR0000SEFC01": "CPI uncooked ground beef",
             "CUUR0000SEFN02": "CPI frozen noncarbonated juices and drinks", "CUUR0000SEFN03": "CPI nonfrozen noncarbonated juices and drinks",
             "CUUR0000SAF11": "CPI food at home", "CUUR0000SA0": "CPI all items",
             "WPU026301": "PPI coffee (wp.item 026301 per plan §0.5)", "WPU024203": "PPI frozen juices incl. OJ (024203)",
             "WPU101702": "PPI semifinished steel mill products (101702)", "WPU101712": "PPI ferroalloys (101712)", "WPU0121": "PPI 0121 (name unverified: wp.item blocked)"}


def bls():
    out = {}
    for f in ("bls_q1.json", "bls_q2.json"):
        j = json.loads((CACHE / "bls" / f).read_text())
        for s in j["Results"]["series"]:
            d = pd.DataFrame(s["data"])
            d = d[d.period.str.startswith("M") & (d.period != "M13")]
            d["date"] = pd.to_datetime(d.year + "-" + d.period.str[1:] + "-01")
            out[s["seriesID"]] = pd.to_numeric(d.set_index("date").value, errors="coerce").sort_index()
    return out


@step
def cpi_relief():
    B = bls()
    yy = {k: (100 * (s / s.shift(12) - 1)) for k, s in B.items()}
    for k, s in yy.items():
        s = s.dropna()
        if len(s):
            R[f"bls.{k}"] = dict(name=BLS_NAMES.get(k, k), last=str(s.index.max())[:10], yoy_last=round(float(s.iloc[-1]), 1),
                                 yoy_2025_10=(round(float(s.get(pd.Timestamp("2025-10-01"))), 1) if pd.Timestamp("2025-10-01") in s.index else None),
                                 yoy_2025_09=round(float(s.get(pd.Timestamp("2025-09-01"), np.nan)), 1) if pd.Timestamp("2025-09-01") in s.index else None,
                                 yoy_2025_07=round(float(s.get(pd.Timestamp("2025-07-01"), np.nan)), 1) if pd.Timestamp("2025-07-01") in s.index else None,
                                 peak_yoy=round(float(s.max()), 1), peak_date=str(s.idxmax())[:10],
                                 level_vs_2024avg_pct=round(float(100 * (B[k].iloc[-1] / B[k][B[k].index.year == 2024].mean() - 1)), 1))
    # 2x2: food/ag HS4 lines covered in R2 (full >= 0.5, US exports >= $10m in 2024): relieved in R3 vs not, x CPI salience
    g = hs4_status()
    us = D("us_ncm"); v24 = us[us.ym.dt.year == 2024].groupby("hs4").fob.sum()
    cand = g[(g.full_R2 >= 0.5) & (g.index.str[:2].astype(int) <= 24)].copy()
    cand = cand[cand.index.isin(v24[v24 >= 1e7].index)]
    cand["relieved"] = cand.full_R3 < 0.5
    # salience: line maps to a BLS CPI item with y/y >= 2x CPI-all in Oct 2025 (coffee 0901, beef 0201/0202/1602, juices 2009);
    # other staples without a pulled CPI item are coded low (judgement, listed in the CSV)
    sal_map = {"0901": "CUUR0000SEFP01", "2101": "CUUR0000SEFP01", "0201": "CUUR0000SEFC", "0202": "CUUR0000SEFC", "1602": "CUUR0000SEFC",
               "2009": "CUUR0000SEFN03"}
    all10 = R["bls.CUUR0000SA0"]["yoy_2025_10"] or R["bls.CUUR0000SA0"]["yoy_2025_09"]
    def sal(h):
        k = sal_map.get(h)
        if not k:
            return False
        v = R[f"bls.{k}"]["yoy_2025_10"] or R[f"bls.{k}"]["yoy_2025_09"]
        return v is not None and v >= 2 * all10
    cand["cpi_salient"] = [sal(h) for h in cand.index]
    cand["v24_bn"] = (v24.reindex(cand.index) / 1e9).round(3)
    cand["desc"] = [str(D("hs4_desc").get(h, ""))[:60] for h in cand.index]
    cand[["desc", "v24_bn", "relieved", "cpi_salient", "full_R2", "full_R3"]].to_csv(CACHE / "h8_relief_2x2.csv")
    tab = pd.crosstab(cand.relieved, cand.cpi_salient)
    vt = cand.groupby(["relieved", "cpi_salient"]).v24_bn.sum().unstack().fillna(0)
    # permutation p for the association (relieved share among salient minus non-salient)
    rng = np.random.default_rng(SEED)
    x = cand.cpi_salient.values; y = cand.relieved.values.astype(float)
    obs = y[x].mean() - y[~x].mean() if x.any() and (~x).any() else np.nan
    perm = [(lambda p_: y[p_].mean() - y[~p_].mean())(rng.permutation(x)) for _ in range(5000)]
    R["h8.table_counts"] = {str(k): v for k, v in tab.to_dict().items()}
    R["h8.table_value_bn"] = {str(k): v for k, v in vt.to_dict().items()}
    R["h8.relieved_share_salient_minus_other"] = float(obs)
    R["h8.perm_p"] = float(np.mean(np.abs(perm) >= abs(obs) - 1e-12))
    R["h8.n_lines"] = len(cand)
    R["h8.relieved_lines"] = cand[cand.relieved].index.tolist()
    R["h8.salient_not_relieved"] = cand[cand.cpi_salient & ~cand.relieved].index.tolist()
    R["h8.dates"] = {"call": "2025-10-06", "kuala_lumpur": "2025-10-26", "all_country_ag_eo14360_signed": "2025-11-14",
                     "eo14361_signed": "2025-11-20", "effective_retro": "2025-11-13",
                     "cpi_sep2025_release": "2025-10-24 (delayed by the shutdown; per BLS schedule — not verified here)"}
    print(tab); print(vt); print("obs", obs, "p", R["h8.perm_p"], R["h8.relieved_lines"])
    print({k: v for k, v in R.items() if k.startswith("bls.")})
    save_results()



# ---------------------------------------------------------------- 5.6 market event study (engine imported from congress_core)
EVENTS = [("2025-07-10", "Trump letter 50% (07-09 evening)", "E"), ("2025-07-30", "EO 14323 + Magnitsky on Moraes", "E"),
          ("2025-08-06", "40% effective", "E"), ("2025-09-23", "UNGA chemistry", "D"), ("2025-10-06", "Lula-Trump call", "D"),
          ("2025-10-27", "Kuala Lumpur meeting (Sun 26)", "D"), ("2025-11-20", "EO 14361 food relief", "D"),
          ("2025-12-12", "Magnitsky lifted", "D"), ("2026-02-20", "SCOTUS voids IEEPA", "D"), ("2026-05-07", "White House meeting", "D"),
          ("2026-06-01", "301 determination", "E"), ("2026-07-15", "301 final action", "E"), ("2026-07-22", "301 effective", "E"),
          ("2026-08-17", "FT: Magnitsky re-imposition discussed (Sun 16)", "E"), ("2026-10-01", "consular suspension", "E"),
          ("2025-04-02", "Liberation Day (Brazil at 10% floor)", "C"), ("2025-04-11", "Reciprocity Law", "C"),
          ("2026-10-05", "first-round result", "C")]
BASKET = ["EMBR", "GGBR4", "CSNA3", "JBS", "SUZB3", "WEGE3", "TUPY3", "ALPA4", "GRND3", "DXCO3"]


def firm_returns():
    """daily USD log returns (x100) per firm from COTAHIST closes / brl_usd; tickers spliced on returns (splice day dropped)."""
    c = pd.read_parquet(CACHE / "cotahist" / "closes.parquet")
    fx = wq("SELECT date, value FROM v_observations WHERE series_id='brl_usd' AND date >= '2020-06-01' ORDER BY date", "brl_usd_daily")
    fx = fx.set_index(pd.to_datetime(fx.date)).value
    out = {}
    lines = {"EMBR": [("EMBR3", None, "2025-10-31"), ("EMBJ3", "2025-11-03", None)],
             "JBS": [("JBSS3", None, "2025-06-06"), ("JBSS32", "2025-06-09", None)]}
    for t in set(c.ticker):
        if t in ("EMBR3", "EMBJ3", "JBSS3", "JBSS32"):
            continue
        lines[t] = [(t, None, None)]
    jumps = {}
    for e, parts in lines.items():
        rs = []
        for tk, a, b in parts:
            s = c[c.ticker == tk].set_index("date").close.sort_index()
            if a: s = s[s.index >= a]
            if b: s = s[s.index <= b]
            usd = s / fx.reindex(s.index).ffill()
            rs.append(100 * np.log(usd).diff().dropna())
        if len(parts) > 1:
            s0 = c[c.ticker == parts[0][0]].set_index("date").close.sort_index(); s1 = c[c.ticker == parts[1][0]].set_index("date").close.sort_index()
            jumps[e] = float(s1.iloc[0] / s0.iloc[-1]) if len(s0) and len(s1) else None
        out[e] = pd.concat(rs).sort_index()
    R["markets.splice_price_ratio"] = jumps
    return out


@step
def markets():
    sys.path.insert(0, str(OUT.parent / "congress"))
    import congress_core as cc   # noqa: E402  (attaches the warehouse read-only)
    R["markets.engine"] = "congress_core.car / perm_test / WINDOWS (estimation [-250,-121], Brent market model for BRL & Ibovespa)"
    raw = wq("""SELECT series_id, date, value FROM v_observations WHERE date <= current_date AND date >= '2015-01-01' AND series_id IN
        ('brl_usd','ibovespa_usd','gov_real_yield_10y','gov_nominal_yield_5y','brent_usd') ORDER BY 1,2""", "daily_market_panel")
    raw["date"] = pd.to_datetime(raw.date)
    S = {k: g_.set_index("date").value for k, g_ in raw.groupby("series_id")}
    ch = {"brl_usd": -100 * np.log(S["brl_usd"]).diff().dropna(),            # + = BRL stronger
          "ibovespa_usd": 100 * np.log(S["ibovespa_usd"]).diff().dropna(),
          "gov_real_yield_10y": 100 * S["gov_real_yield_10y"].diff().dropna(),   # bp
          "gov_nominal_yield_5y": 100 * S["gov_nominal_yield_5y"].diff().dropna()}
    brent = (100 * np.log(S["brent_usd"]).diff()).dropna()
    fr_ = firm_returns()
    ch["embraer_usd"] = fr_["EMBR"]
    bk = pd.concat([fr_[k] for k in BASKET if k in fr_], axis=1).dropna(how="all")
    ch["exposed_basket_usd"] = bk.mean(axis=1, skipna=True)
    ib = ch["ibovespa_usd"]
    ch["embraer_minus_ibov"] = (fr_["EMBR"] - ib.reindex(fr_["EMBR"].index)).dropna()
    ch["basket_minus_ibov"] = (ch["exposed_basket_usd"] - ib.reindex(ch["exposed_basket_usd"].index)).dropna()
    for k in ["SUZB3", "WEGE3", "GGBR4", "JBS", "TUPY3"]:
        ch[f"{k}_usd"] = fr_[k]
    rows = []
    edates = [pd.Timestamp(d) for d, *_ in EVENTS]
    PL, PLm = {}, {}
    rng = np.random.default_rng(SEED)
    for sid, d in ch.items():
        d = d[~d.index.duplicated()].sort_index()
        for date, label, grp in EVENTS:
            t0 = d.index.searchsorted(pd.Timestamp(date))
            for wn, (a, b) in cc.WINDOWS.items():
                v = cc.car(d, t0, a, b) if t0 < len(d) else None
                vb = cc.car(d, t0, a, b, brent=brent) if (t0 < len(d) and sid in ("brl_usd", "ibovespa_usd")) else None
                rows.append(dict(series=sid, date=date, event=label, group=grp, window=wn, car=v, car_brent=vb,
                                 raw=cc.car(d, t0, a, b, raw=True) if t0 < len(d) else None))
        ok = np.ones(len(d), bool)
        for e in edates:
            ok &= np.abs((d.index - e).days) > 90
        cand = np.where(ok)[0]; cand = cand[(cand > 260) & (cand < len(d) - 70)]
        for excl_covid in (False, True):
            cd = cand
            if excl_covid:
                cd = cand[~((d.index[cand] >= "2020-01-15") & (d.index[cand] <= "2021-07-15"))]
            draws = rng.choice(cd, size=2000, replace=len(cd) < 2000)
            for wn, (a, b) in cc.WINDOWS.items():
                vals = np.array([v for v in (cc.car(d, t, a, b) for t in draws) if v is not None], float)
                PL[(sid, wn, excl_covid)] = vals
        R[f"markets.placebo_pool.{sid}"] = dict(n_candidates=int(len(cand)), first=str(d.index[cand].min())[:10] if len(cand) else None)
    ev = pd.DataFrame(rows)
    def pz(r):
        pl = PL[(r.series, r.window, False)]
        if r.car is None or pd.isna(r.car) or not len(pl):
            return pd.Series({"placebo_p": np.nan, "pctile": np.nan})
        return pd.Series({"placebo_p": float(np.mean(np.abs(pl) >= abs(r.car))), "pctile": float(np.mean(pl <= r.car))})
    ev[["placebo_p", "pctile"]] = ev.apply(pz, axis=1)
    ev.to_csv(OUT / "event_study.csv", index=False)
    # H5: group-mean CAR vs placebo distribution of means of k random dates; E vs D exact permutation
    summ = {}
    for sid in ch:
        for wn in ("[-1,+1]", "[-5,+5]", "[-20,+20]"):
            s = ev[(ev.series == sid) & (ev.window == wn)].dropna(subset=["car"])
            E = s[s.group == "E"].car.values; Dd = s[s.group == "D"].car.values
            out = {}
            for excl in (False, True):
                pl = PL[(sid, wn, excl)]
                if not len(pl) or not len(E):
                    continue
                mE = np.array([pl[rng.integers(0, len(pl), len(E))].mean() for _ in range(4000)])
                mD = np.array([pl[rng.integers(0, len(pl), len(Dd))].mean() for _ in range(4000)]) if len(Dd) else np.array([np.nan])
                out[f"exclcovid={int(excl)}"] = dict(mean_E=float(E.mean()), band_E_5_95=np.percentile(mE, [5, 95]).tolist(),
                    pctile_E=float(np.mean(mE <= E.mean())), mean_D=float(Dd.mean()) if len(Dd) else None,
                    band_D_5_95=np.nanpercentile(mD, [5, 95]).tolist(), pctile_D=float(np.mean(mD <= Dd.mean())) if len(Dd) else None)
            if len(E) and len(Dd):
                vals = np.concatenate([E, Dd]); lab = np.array(["left"] * len(E) + ["right"] * len(Dd))
                p, pmin, ncomb = cc.perm_test(vals, lab)
                out["perm_E_vs_D"] = dict(diff=float(E.mean() - Dd.mean()), p=p, p_floor=pmin, n_comb=ncomb, nE=len(E), nD=len(Dd))
            summ[f"{sid}|{wn}"] = out
    R["markets.h5"] = summ
    # Embraer alone, per event, [-5,+5] and [-1,+1]
    R["markets.embraer_events"] = ev[(ev.series.isin(["embraer_usd", "embraer_minus_ibov"])) & (ev.window.isin(["[-1,+1]", "[-5,+5]"]))][
        ["series", "date", "event", "group", "window", "car", "raw", "placebo_p"]].round(3).to_dict("records")
    for sid in ["brl_usd", "ibovespa_usd", "gov_real_yield_10y", "embraer_usd", "exposed_basket_usd", "embraer_minus_ibov"]:
        print(sid, {k: (round(v["exclcovid=0"]["mean_E"], 2), [round(x, 2) for x in v["exclcovid=0"]["band_E_5_95"]], round(v["exclcovid=0"]["mean_D"], 2),
                        round(v.get("perm_E_vs_D", {}).get("p", np.nan), 3)) for k, v in summ.items() if k.startswith(sid + "|") and "exclcovid=0" in v})
    save_results()



# ---------------------------------------------------------------- 3. timeline table
TIMELINE = [
 # measure_id, regime, signed, effective, end, authority, instrument, fr_doc, citation, rate, stacking, scope, exemption_source, status, url, fact_ids, conf
 ("M01", "R1", "2025-02-10", "2025-03-12", "", "Sec. 232 (TEA 1962)", "Proclamation 10895/10896", "2025-02832; 2025-02833", "90 FR 9807; 90 FR 9817", "25", "replaces IEEPA on 232 goods", "steel, aluminium + derivatives, all countries", "HTS 9903.81/.85 (now 9903.82)", "in force (50% since 2025-06-04)", "https://www.federalregister.gov/d/2025-02833", "D01", "high"),
 ("M02", "R1", "2025-06-03", "2025-06-04", "", "Sec. 232", "Proclamation 10947", "2025-10524", "90 FR 24199", "50", "", "steel/aluminium raised to 50%", "", "in force; restructured 2026-04-09 (11021) and 2026-06-04 (11032): metals 50%, derivatives 25/15%", "https://www.federalregister.gov/d/2025-10524", "D01", "high"),
 ("M03", "R1", "2025-03-26", "2025-04-03", "", "Sec. 232", "Proclamation 10908", "2025-05930", "90 FR 14705", "25", "", "autos and parts", "HTS note 33", "in force", "https://www.federalregister.gov/d/2025-05930", "D01", "high"),
 ("M04", "R1", "2025-04-02", "2025-04-05", "2026-02-20", "IEEPA", "EO 14257", "2025-06063", "90 FR 15041", "10", "Brazil at the 10% floor", "all goods ex Annex II (energy, pharma, minerals...)", "9903.01.32 (Annex II)", "voided by SCOTUS 2026-02-20", "https://www.federalregister.gov/d/2025-06063", "D02;A16", "high"),
 ("M05", "R1", "2025-07-30", "2025-08-01", "", "Sec. 232", "Proclamation 10962", "2025-14893", "90 FR 37727", "50", "", "semi-finished copper", "9903.78.01", "in force", "https://www.federalregister.gov/d/2025-14893", "D01", "high"),
 ("M06", "R2", "2025-07-30", "2025-08-06", "2026-02-20", "IEEPA (national emergency w.r.t. Brazil)", "EO 14323", "2025-14896", "90 FR 37739", "40", "+10 reciprocal = 50; not on 232 goods", "all Brazilian goods ex Annex I (694 products; civil aircraft 9903.01.82; 232 goods 9903.01.83)", "9903.01.77-.83; Annex I from govinfo PDF (702 HTS tokens)", "tariff voided 2026-02-20; emergency continued 2026-07-28", "https://www.federalregister.gov/d/2025-14896", "A02;A03;D03", "high"),
 ("M07", "R2", "2025-09-29", "2025-10-14", "", "Sec. 232", "Proclamation 10976", "2025-19482", "90 FR 48127", "10-25", "", "softwood lumber 10%, upholstered furniture/cabinets 25%", "HTS note 37", "in force (amended 2026-01-09)", "https://www.federalregister.gov/d/2025-19482", "D01", "high"),
 ("M08", "R3", "2025-11-14", "2025-11-13", "2026-02-20", "IEEPA", "EO 14360", "2025-21203", "90 FR 54091", "0", "all countries", "reciprocal removed from certain agricultural products (coffee, beef, fruit...) for every country; rationale cites 'current domestic demand'", "Annex II updated (image); inferred = ch.01-24 codes in 9903.01.32", "voided with IEEPA", "https://www.federalregister.gov/d/2025-21203", "D04", "high"),
 ("M09", "R3", "2025-11-20", "2025-11-13", "2026-02-20", "IEEPA", "EO 14361", "2025-21417", "90 FR 54467", "0 (relief)", "retroactive; refunds", "removes the 40% from 238 HTS codes + ag categories (beef, coffee, fruit, juices); rationale cites 'initial progress in negotiations'", "9903.01.81 as amended + 9903.01.90 (11 particular articles)", "voided with IEEPA", "https://www.federalregister.gov/d/2025-21417", "A09;D05", "high"),
 ("M10", "R3", "2025-07-30", "2025-07-30", "2025-12-12", "IEEPA/GloMag (EO 13818)", "OFAC SDN", "", "", "", "", "Moraes designated; lifted 2025-12-12", "", "lifted; re-imposition discussed Aug-2026", "https://home.treasury.gov/news/press-releases/sb0257", "A05;A11;A12", "high"),
 ("M11", "R4", "2026-02-20", "2026-02-24", "2026-07-24", "Trade Act s.122", "Proclamation 11012", "2026-03824", "91 FR 9339", "10", "all countries; not on 232 goods", "all goods ex Annex I/II (energy, minerals, certain ag incl. beef/oranges, pharma, aerospace)", "9903.03.01-.11", "expired 2026-07-24", "https://www.federalregister.gov/d/2026-03824", "A17;D06", "high"),
 ("M12", "R4", "2026-02-20", "2026-02-20", "", "", "EO 14389 Ending Certain Tariff Actions", "2026-03832", "91 FR 9437", "", "", "terminates IEEPA tariffs after Learning Resources v. Trump", "", "done", "https://www.federalregister.gov/d/2026-03832", "A16", "high"),
 ("M13", "R4", "2026-02-06", "2026-02-13", "", "", "Proclamation 11010 Ensuring Affordable Beef", "2026-03050", "91 FR 7107", "", "", "+80,000 t to the beef TRQ, allocated in its entirety to Argentina", "", "in force", "https://www.federalregister.gov/d/2026-03050", "D07", "high"),
 ("M14", "R5", "2026-07-15", "2026-07-22", "", "Trade Act s.301 (Brazil investigation USTR-2025-0043)", "Presidential memo + USTR notice", "2026-14654; 2026-14542", "91 FR 45619; 91 FR 45516", "25", "not on 232 goods; stacks with forced-labour 301", "all Brazilian goods ex annex (raw materials, ag that cannot be grown, aircraft, pharma uses); dissolving pulp removed from exemptions", "9903.05.01-.09 (note 50)", "in force", "https://www.federalregister.gov/d/2026-14542", "A20;A21;D08", "high"),
 ("M15", "R5", "2026-07-23", "2026-07-24", "", "Trade Act s.301 (forced labour, 60 economies)", "Presidential memo + USTR notice", "2026-15274; 2026-15181", "91 FR 47717; 91 FR 47318", "12.5", "Brazil in the 12.5% tier; 10% tier incl. Argentina, Canada, Mexico, India, Indonesia; EU/Taiwan 10% net of MFN", "general exemption annex", "9903.05.20-.84; exemptions 9903.05.86-.90 (note 52)", "in force", "https://www.federalregister.gov/d/2026-15274", "A22;D09", "high"),
 ("M16", "R5", "2026-07-09", "", "", "Sec. 232", "Proclamation 11040 (aircraft, engines, parts)", "2026-14334", "91 FR 43507", "0 now", "", "no tariff; negotiations; President may act if no agreement within 180 days (~2027-01-05)", "", "clock running", "https://www.federalregister.gov/d/2026-14334", "D10", "high"),
 ("M17", "R5", "2026-07-28", "", "", "IEEPA/NEA", "Notice: Continuation of the National Emergency w.r.t. Brazil", "2026-15389", "91 FR 47929", "", "", "emergency of EO 14323 continued one year (cites STF 'censorship')", "", "live sanctions basis", "https://www.federalregister.gov/d/2026-15389", "D11", "high"),
 ("M18", "R5", "2026-03-11", "", "", "Trade Act s.301 (structural excess capacity)", "USTR notice", "2026-05214", "91 FR 12886", "", "", "16 economies; Brazil NOT a respondent (mentioned only re BYD plants)", "", "pending", "https://www.federalregister.gov/d/2026-05214", "D12", "high"),
]
TL_COLS = ["measure_id", "regime", "date_signed", "date_effective", "date_end", "authority", "instrument", "fr_document_number",
           "fr_citation", "rate_pct", "stacking_rule", "scope", "exemption_source", "status_2026_10_06", "primary_url", "fact_ids", "confidence"]


@step
def timeline():
    S = list_shares()
    out, miss, st = coverage(S, "any")
    out_c, miss_c, _ = coverage(S, "count", verbose=False)
    R["coverage.any"] = {f"{k[0]}|{k[1]}": v for k, v in out.items()}
    R["coverage.count"] = {f"{k[0]}|{k[1]}": v for k, v in out_c.items()}
    R["coverage.anchor_misses_any"] = miss; R["coverage.anchor_misses_count"] = miss_c
    R["coverage.note"] = ("Primary HS6 rule 'any': an HS6 with any listed HTS-8 counts as listed (MDIC maps NCM-8 to HTS-8). "
                          "The plan's count/partial rule misses the R5 37.5% anchor (20.4% vs 16.5 +/- 3) but is close to GTA's 21.5% (A24); "
                          "kept as a robustness cell.")
    tl = pd.DataFrame(TIMELINE, columns=TL_COLS)
    def share(reg, yr):
        d = out.get((reg, yr), {})
        return "; ".join(f"{k} {v:.1f}" for k, v in d.items())
    tl["share_us_bound_2024_pct"] = [share(r, "2024") for r in tl.regime]
    tl["share_us_bound_2025_pct"] = [share(r, "2025") for r in tl.regime]
    tl["ncm_list_file"] = "cache/hts/lists_long.csv; cache/hts/lists_hs6.csv"
    tl.to_csv(OUT / "tariff_timeline.csv", index=False)
    save_results()



# ---------------------------------------------------------------- 6. escalation matrix
AIRCRAFT_HS4 = {"8802", "8807", "8411", "8803"}
ENERGY_HS4 = {"2709", "2710", "2711", "2701"}


def rung_rates(st5, hs6, rung, case):
    """added Brazil rate (%) by status fraction for an HS6 under rung x case. st5: dict status -> frac (R5)."""
    h4 = hs6[:4]; air = h4 in AIRCRAFT_HS4; en = h4 in ENERGY_HS4
    r232 = 50.0 if hs6[:2] in ("72", "73", "76", "74") else 25.0
    f = st5
    if rung == "a":
        return {"232": r232, "exempt": 0.0, "fl_only": 12.5, "s301_only": 25.0, "full": 37.5}
    if rung == "b":
        t301 = {"low": 37.5, "central": 50.0, "high": 100.0}[case]
        return {"232": r232, "exempt": 0.0, "fl_only": 12.5, "s301_only": t301, "full": t301 + 12.5}
    if rung == "c":
        ex = {"low": 25.0, "central": 37.5, "high": 62.5}[case]
        if en and case == "low":
            ex = 0.0
        if air:
            ex = {"low": 25.0, "central": 25.0, "high": 50.0}[case]   # aircraft-232 tariff at the 180-day mark
        full = {"low": 37.5, "central": 37.5, "high": 62.5}[case]
        return {"232": r232, "exempt": ex, "fl_only": max(ex, 12.5), "s301_only": max(ex, 25.0), "full": full}
    if rung == "d":
        t = {"low": 100.0, "central": 100.0, "high": 500.0}[case]
        e_ = 0.0 if (en and case == "low") else t
        return {"232": max(r232, t), "exempt": e_, "fl_only": t, "s301_only": t, "full": t}
    if rung == "e":
        t_air = 0.0
        return {"232": r232, "exempt": 0.0, "fl_only": 12.5, "s301_only": 12.5, "full": 12.5}   # 301 suspended, FL stays, 232 stays
    raise ValueError(rung)


EPS = {"low": {"commodity": -0.5, "manufactured": -0.5}, "central": {"commodity": -1.4, "manufactured": -1.0},
       "high": {"commodity": -2.5, "manufactured": -2.5}}
DIV = {"low": {"commodity": 0.75, "manufactured": 0.28}, "central": {"commodity": 0.55, "manufactured": 0.22},
       "high": {"commodity": 0.32, "manufactured": 0.17}}
RUNG_DEF = {
    "a": ("status quo R5: s301 25% + forced-labour 12.5% on ~16% of US-bound trade; s232 on ~25%; exemption annex; aircraft-232 clock running", "as now", "none (baseline)"),
    "b": ("s301 raised to 50-100% on current coverage", "USTR modification, Trade Act s.307 (19 USC 2417), notice and comment ~30 days",
          "no Pix/digital deal; STF action vs Bolsonaro family; election-interference dispute (A38)"),
    "c": ("coverage widened: exemption annex removed (coffee, beef, OJ, pig iron, pulp, ore pellets, alumina, stone), energy included, aircraft tariffed (s232 at the 180-day mark or s301), s232 steel 50% no TRQ",
          "USTR modification of the s301 annex; Proclamation under s232(c)(3)(A) for aircraft", "aircraft-232 clock ~2027-01-05; failed negotiation; amnesty blocked by the STF"),
    "d": ("'total' regime: >=100% (to 500%) across the board via s301 or a Graham-Act-type secondary tariff + financial sanctions (SDN of officials, state banks/Petrobras analogues, secondary sanctions)",
          "s301; IEEPA sanctions under the still-live national emergency (2026-15389); Graham Act only if Brazil enters the top-5 Russian crude/gas list",
          "open confrontation (e.g. arrest of Eduardo Bolsonaro, re-imprisonment of Jair, election-fraud claims); Russian oil list (2026-10-18) — Brazil not a top-5 crude/gas buyer"),
    "e": ("negotiated de-escalation: s301 suspended/monitored agreement (Pix/digital, ethanol TRQ, deforestation); forced-labour 12.5% and s232 stay; aircraft deal",
          "USTR termination/suspension under s.307; s232(c)(3)(A) agreement", "amnesty in the transition (Flávio, A32) or Congress override; Pix/ethanol concessions"),
}
PROB = {  # judgement (low <25, medium 25-60, high >60), modal state through 2027 conditional on the run-off winner
    "a": ("medium (40%)", "medium (35%)"), "b": ("low (20%)", "low (5%)"), "c": ("low (15%)", "low (3%)"),
    "d": ("low (5%)", "low (1%)"), "e": ("low (20%)", "medium-high (56%)")}
PROB_RATIONALE = {
    "a": "Section 301 is a trade finding (A19-A21) that survives a change of government; 232 is multilateral. Default under both.",
    "b": "Lula IV: Rubio blames Lula personally (A25), Magnitsky re-imposition discussed (A12), consular suspension (A38). Flávio: aligned, received at the White House (A27).",
    "c": "Aircraft-232 clock (2026-14334) falls on ~2027-01-05, four days after the inauguration; a Lula IV government without a deal is the main path. USTR kept aircraft, coffee, beef and OJ exempt for US-supply reasons (2026-14542) — revealed US cost limits the rung.",
    "d": "Requires abandoning the US-supply logic of the exemption annex; the emergency (2026-15389) keeps the legal route open. Graham Act list unlikely to include Brazil (A45).",
    "e": "Flávio pledges amnesty in the transition (A32) and frames the tariff as Lula's (A28); Pix/ethanol concessions still needed (A19). Lula IV: 3 meetings produced only the Nov-2025 relief (A06-A09, A26).",
}


def stress_analogue():
    """warehouse: worst 63-trading-day moves since 2015 (BRL, Ibovespa USD, NTN-B 10y real) as the (d) market analogue."""
    x = wq("""SELECT series_id, date, value FROM v_observations WHERE date >= '2015-01-01' AND date <= current_date
              AND series_id IN ('brl_usd','ibovespa_usd','gov_real_yield_10y') ORDER BY 1,2""", "stress_analogue")
    out = {}
    for s, g_ in x.groupby("series_id"):
        v = g_.set_index(pd.to_datetime(g_.date)).value
        if s == "gov_real_yield_10y":
            ch = 100 * (v - v.shift(63)); worst = ch.max(); when = ch.idxmax()
        elif s == "brl_usd":
            ch = 100 * (v / v.shift(63) - 1); worst = ch.max(); when = ch.idxmax()   # BRL weakening
        else:
            ch = 100 * (v / v.shift(63) - 1); worst = ch.min(); when = ch.idxmin()
        out[s] = dict(worst_63d=round(float(worst), 1), date=str(when)[:10], p95=round(float(ch.quantile(0.95 if s != "ibovespa_usd" else 0.05)), 1))
    return out


@step
def matrix():
    g = hs4_status()
    S = list_shares(); st = status_table(S)
    us = D("us_ncm"); v6 = us[us.ym.dt.year == 2024].groupby("hs6").fob.sum()
    s5 = st[st.regime == "R5"].pivot_table(index="hs6", columns="status", values="frac", aggfunc="sum").fillna(0.0)
    s5 = s5.reindex(v6.index).fillna(0.0)
    gdp = R.get("loss.gdp_2025_bn", {}).get("value") if isinstance(R.get("loss.gdp_2025_bn"), dict) else None
    if gdp is None:
        gdp = float(wq("SELECT value FROM v_annual WHERE series_id='wb/NY.GDP.MKTP.CD.BR' AND year=2025", "gdp_2025").value.iloc[0]) / 1e9
    exports_2025 = float(wq("SELECT value FROM v_annual WHERE series_id='exports_total' AND year=2025", "exports_2025").value.iloc[0]) / 1e9
    tot24 = v6.sum() / 1e9
    stress = stress_analogue(); R["matrix.stress_analogue"] = stress
    ct = R.get("mirror.annual_2024") or mirror_annual()
    rows = []
    res = {}
    for rung in "abcde":
        rr = {}
        for case in ("low", "central", "high"):
            eps, dv = EPS[case], DIV[case]
            if rung == "d":
                dv = {k: v * 0.5 for k, v in dv.items()}     # secondary sanctions deter third-country buyers
            gross = net = duty = 0.0; cov = 0.0; byh4 = {}
            for h6, x in v6.items():
                cls = hs4_class(h6[:4]); fr_ = s5.loc[h6].to_dict()
                ra, rb = rung_rates(fr_, h6, "a", case), rung_rates(fr_, h6, rung, case)
                xa = sum(fr_.get(k, 0) * x * (1 + ra[k] / 100) ** eps[cls] for k in ra)
                xr = sum(fr_.get(k, 0) * x * (1 + rb[k] / 100) ** eps[cls] for k in rb)
                l0 = x - xr      # level loss vs no tariff
                inc = xa - xr    # incremental vs (a)
                gross += inc; net += inc * (1 - dv[cls]) if inc > 0 else inc
                duty += sum(fr_.get(k, 0) * x * (1 + rb[k] / 100) ** eps[cls] * rb[k] / 100 for k in rb)
                cov += x * sum(fr_.get(k, 0) for k in rb if rb[k] > 0)
                byh4[h6[:4]] = byh4.get(h6[:4], 0.0) + inc
            rr[case] = dict(gross=gross / 1e9, net=net / 1e9, duty=duty / 1e9, cov=100 * cov / 1e9 / tot24,
                            top5=sorted(byh4.items(), key=lambda z: -z[1])[:5])
        res[rung] = rr
        m_lo, m_hi, k_lo, k_hi = 0.10, 0.20, 1.0, 1.5
        c = rr["central"]
        gdp_dir = lambda xbn, m, k: 100 * xbn / gdp * (1 - m) * k
        fin = {"a": (0, 0, 0), "b": (0, 0, 0), "c": (0, 0, 0), "d": (1.0, 2.0, 4.0), "e": (0, 0, 0)}[rung]   # % GDP, judgement
        mk = {"a": ("0", "0", "0", "0"), "b": ("-0.5 to -2", "-1 to -4", "+0 to +15", "0 to -3 (aircraft exempt)"),
              "c": ("-1 to -4", "-3 to -8", "+10 to +40", "-10 to -25 (Jul-2025 letter: -11.7% in 3 days)"),
              "d": (f"-10 to {-stress['brl_usd']['worst_63d']:.0f}", f"-20 to {stress['ibovespa_usd']['worst_63d']:.0f}",
                    f"+100 to +{stress['gov_real_yield_10y']['worst_63d']:.0f}", "-30 to -50"),
              "e": ("+1 to +3", "+2 to +6", "-5 to -20", "+5 to +19 (EO 14323 exemption: +18.7% in 3 days)")}[rung]
        top5 = "; ".join(f"{h} {v/1e9:.2f}" for h, v in c["top5"])
        rows.append(dict(rung=rung, definition=RUNG_DEF[rung][0], legal_route=RUNG_DEF[rung][1], triggers=RUNG_DEF[rung][2],
                         covered_share_us_bound_pct=round(c["cov"], 1),
                         export_loss_gross_low_bn=round(rr["low"]["gross"], 2), export_loss_gross_central_bn=round(c["gross"], 2),
                         export_loss_gross_high_bn=round(rr["high"]["gross"], 2),
                         diversion_rate_used="comm/manuf " + "/".join(f"{DIV['central'][k]*(0.5 if rung=='d' else 1):.2f}" for k in ("commodity", "manufactured")),
                         export_loss_net_low_bn=round(rr["low"]["net"], 2), export_loss_net_central_bn=round(c["net"], 2),
                         export_loss_net_high_bn=round(rr["high"]["net"], 2),
                         pct_exports_central=round(100 * c["net"] / exports_2025, 2),
                         pct_gdp_direct_low=round(gdp_dir(rr["low"]["net"], m_hi, k_lo), 2), pct_gdp_direct_central=round(gdp_dir(c["net"], 0.15, 1.25), 2),
                         pct_gdp_direct_high=round(gdp_dir(rr["high"]["net"], m_lo, k_hi), 2),
                         financial_block_pct_gdp_low_central_high="/".join(str(x) for x in fin),
                         total_pct_gdp_central=round(gdp_dir(c["net"], 0.15, 1.25) + fin[1], 2),
                         top5_hs4_losses_bn=top5, brl_pct=mk[0], ibov_usd_pct=mk[1], ntnb_bp=mk[2], embraer_pct=mk[3],
                         source_of_market_numbers=("event study (event_study.csv) scaled by severity; (d) = worst 63-day move since 2015 in the warehouse "
                                                   f"(BRL {stress['brl_usd']['worst_63d']}% on {stress['brl_usd']['date']}; Ibov USD {stress['ibovespa_usd']['worst_63d']}%; NTN-B +{stress['gov_real_yield_10y']['worst_63d']} bp)"),
                         us_duty_paid_bn_central=round(c["duty"], 2), prob_lula_iv=PROB[rung][0], prob_flavio=PROB[rung][1],
                         prob_rationale=PROB_RATIONALE[rung]))
    M = pd.DataFrame(rows)
    # US-side block
    imp = D("imp_us_y"); i25 = imp[imp.year == 2025].groupby(["hs4", "desc"]).fob.sum().sort_values(ascending=False) / 1e9
    R["matrix.us_exporter_exposure_2025_top"] = [(h, d[:50], round(v, 2)) for (h, d), v in i25.head(12).items()]
    R["matrix.us_exports_to_brazil_2025_bn_comex"] = round(float(i25.sum()), 2)
    nosub = {"8411", "8803", "3004", "3002", "3808", "3105", "2701", "2711"}
    R["matrix.retaliation_no_substitute_bn"] = round(float(i25[[h in nosub for h, _ in i25.index]].sum()), 2)
    R["matrix.retaliation_substitutable_bn"] = round(float(i25.sum() - R["matrix.retaliation_no_substitute_bn"]), 2)
    us_cost = []
    for h, label, share_src in [("0901", "coffee", "mirror"), ("0202", "frozen beef", "mirror"), ("2009", "orange juice", "mirror"),
                                ("7201", "pig iron (EAF input)", "mirror"), ("7207", "steel slabs", "mirror"), ("4703", "chemical pulp", "mirror"),
                                ("7202", "ferroalloys (ferroniobium 7202.93: Brazil 66% of US imports, USGS)", "mirror"), ("8802", "aircraft (E175)", "mirror")]:
        m = ct.get(h, {})
        x24 = float(us[(us.ym.dt.year == 2024) & (us.hs4 == h)].fob.sum() / 1e9)
        sh = m.get("br_share")
        for rung, tau in (("c", 37.5), ("d", 100.0)):
            # import-price effect if competitors do not cut prices: Brazil share x tau x pass-through 0.9 (ARD 2019: complete pass-through)
            imp_px = (sh or 0) / 100 * tau * 0.9
            us_cost.append(dict(hs4=h, item=label, rung=rung, tau=tau, br_share_us_imports=sh, us_imports_bn=m.get("us_imports_bn"),
                                brazil_fob_2024_bn=round(x24, 3), import_price_effect_pct=round(imp_px, 1),
                                retail_effect_pct=round(imp_px * 0.4, 1) if h == "0901" else None,
                                duty_on_brazil_bn=round(x24 * (1 + tau / 100) ** -1.4 * tau / 100, 2)))
    UC = pd.DataFrame(us_cost); UC.to_csv(CACHE / "us_cost_block.csv", index=False)
    R["matrix.us_cost_block"] = UC.to_dict("records")
    def uc(rung):
        s = UC[UC.rung == rung]
        return "; ".join(f"{r.item.split(' (')[0]} +{r.import_price_effect_pct}% import px" for r in s.itertuples() if r.import_price_effect_pct)
    M["us_consumer_cost_bn"] = M.us_duty_paid_bn_central
    M["us_cpi_items"] = ["0 incremental", "none (coffee/beef/OJ stay exempt)", uc("c") + "; coffee retail ~ +" + str(UC[(UC.rung=='c')&(UC.hs4=='0901')].retail_effect_pct.iloc[0]) + "%", uc("d"), "0"]
    M["us_input_shortages"] = ["none", "none", "pig iron (US imports ~70% Brazil), slabs (~76%), ferroniobium (66%), pulp (~41%); E175 supply", "same, plus all", "none"]
    M["us_exporter_exposure_bn"] = [0, 0, f"retaliation menu: {R['matrix.us_exports_to_brazil_2025_bn_comex']} goods (ComexStat 2025) + 34.4 services (USTR)"] + [f"{R['matrix.us_exports_to_brazil_2025_bn_comex']} + 34.4 services"] + [0]
    M["us_fdi_exposure_bn"] = "gap (BEA not reachable without a key/search); Brazil holds US Treasuries $168.0bn (TIC Jul-2026)"
    M["retaliation_option"] = ["none", "Reciprocity Law 15.122 art. 3: goods/services duties", "duties on substitutable US goods; IP suspension (Lei 12.270)",
                               "full menu incl. IP/services; Camex", "none"]
    M["retaliation_cost_to_brazil_bn"] = ["0", f"~0.25 x {R['matrix.retaliation_substitutable_bn']} x 0.5 pass-through = {0.125*R['matrix.retaliation_substitutable_bn']:.1f} (judgement)",
                                          f"{0.125*R['matrix.retaliation_substitutable_bn']:.1f}-{0.25*R['matrix.retaliation_substitutable_bn']:.1f}; avoid {R['matrix.retaliation_no_substitute_bn']} of no-substitute inputs (jet engines, LNG, coal, medicines, agrochemicals, fertilisers)",
                                          "large; inputs for Embraer/airlines and agriculture", "0"]
    M["analogue"] = ["2026 R5 (this study)", "R2 Aug-Nov 2025 (covered lines -44% at 50%)", "R2 relief lines; US-China 2018-19 (complete pass-through, ARD 2019)",
                     "India Aug-2025 50% (A43); Venezuela 2019 PDVSA SDN (not verified this session)", "Nov-2025 relief; Dec-2025 Magnitsky lift"]
    M["fact_ids"] = ["A21;A22;A23;D08;D09;D10", "A19;A25;A38;D08", "D08;D10;E04;E05;E06;F01", "A12;A43;A44;A45;D11", "A09;A11;A28;A32"]
    M["uncertainty_note"] = ["elasticities: low (-0.5) / central (comm -1.4, manuf -1.0, this study) / high (-2.5, US-China HS10 literature); diversion from s5.2"] * 5
    M.to_csv(OUT / "escalation_matrix.csv", index=False)
    R["matrix.summary"] = M[["rung", "covered_share_us_bound_pct", "export_loss_gross_central_bn", "export_loss_net_low_bn", "export_loss_net_central_bn",
                             "export_loss_net_high_bn", "pct_gdp_direct_central", "total_pct_gdp_central", "us_duty_paid_bn_central", "prob_lula_iv", "prob_flavio"]].to_dict("records")
    R["matrix.gdp_bn"] = gdp; R["matrix.exports_2025_bn"] = exports_2025
    c_ = M.set_index("rung")
    R["h4.rung_c_net_central_bn"] = float(c_.loc["c", "export_loss_net_central_bn"])
    R["h4.rung_c_net_high_bn"] = float(c_.loc["c", "export_loss_net_high_bn"])
    R["h4.rung_d_trade_only_net_central_bn"] = float(c_.loc["d", "export_loss_net_central_bn"])
    R["h4.threshold_bn"] = 0.01 * gdp
    print(M[["rung", "covered_share_us_bound_pct", "export_loss_gross_low_bn", "export_loss_gross_central_bn", "export_loss_gross_high_bn",
             "export_loss_net_central_bn", "pct_gdp_direct_central", "total_pct_gdp_central", "us_duty_paid_bn_central"]].to_string())
    print(stress); print(R["matrix.us_exporter_exposure_2025_top"][:6], R["matrix.retaliation_no_substitute_bn"])
    save_results()



# ---------------------------------------------------------------- 7. charts (Plotly HTML)
REG_SHADE = [("R1", "2025-03-12", "2025-08-05", "rgba(150,150,150,0.10)"), ("R2", "2025-08-06", "2025-11-12", "rgba(214,39,40,0.15)"),
             ("R3", "2025-11-13", "2026-02-23", "rgba(255,127,14,0.12)"), ("R4", "2026-02-24", "2026-07-21", "rgba(44,160,44,0.10)"),
             ("R5", "2026-07-22", "2026-10-06", "rgba(148,103,189,0.15)")]


@step
def charts():
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import shutil
    def shade(fig, row=None, col=None):
        for r, a, b, c in REG_SHADE:
            kw = dict(row=row, col=col) if row else {}
            fig.add_vrect(x0=a, x1=b, fillcolor=c, line_width=0, annotation_text=r, annotation_position="top left", **kw)
    def save(fig, name, title):
        fig.update_layout(title=title, template="plotly_white", font=dict(size=12))
        p = CH / f"{name}.html"; fig.write_html(p, include_plotlyjs="cdn")
        REVIEW_CH.mkdir(parents=True, exist_ok=True); shutil.copy(p, REVIEW_CH / f"07_us_tariffs__{name}.html")
    S = list_shares(); st = status_table(S); us = D("us_ncm")
    # 01 coverage by regime
    m = us.groupby(["hs6", "ym"]).fob.sum().reset_index()
    m["regime"] = [("R0" if t < pd.Timestamp("2025-03-01") else regime_of(t)) for t in m.ym]
    mm = m.merge(st, on=["hs6", "regime"])
    mm["v"] = mm.fob * mm.frac
    mm.loc[mm.hs6.str[:4] == "2709", "status"] = "crude (exempt)"
    a = mm.groupby(["ym", "status"]).v.sum().unstack().fillna(0) / 1e9
    fig = go.Figure()
    for c in ["mfn", "exempt", "crude (exempt)", "fl_only", "s301_only", "232", "full"]:
        if c in a.columns:
            fig.add_trace(go.Scatter(x=a.index, y=a[c], stackgroup="one", name={"mfn": "pre-2025 (MFN only)", "full": "full added rate",
                                     "fl_only": "12.5% only", "s301_only": "25% only"}.get(c, c)))
    shade(fig); fig.update_yaxes(title="US$bn per month (ComexStat FOB)")
    save(fig, "01_coverage_by_regime", "Brazil to US exports by tariff status in force (R0-R5), monthly to 2026-09")
    # 02 treemap
    pe = pd.read_csv(OUT / "product_exposure.csv", dtype={"hs4": str})
    pe = pe[pe.value_us_2024_bn > 0]
    fig = go.Figure(go.Treemap(labels=[f"{h} {d[:30]}" for h, d in zip(pe.hs4, pe.description.fillna(""))], parents=[""] * len(pe),
                               values=pe.value_us_2024_bn, marker=dict(colors=pe.full_rate_now_pct, colorscale="Reds", showscale=True,
                               colorbar=dict(title="added rate now %")),
                               customdata=np.stack([pe.brazil_share_of_us_imports_2024.fillna(-1), pe.firms.fillna(""), pe.states_top3.fillna(""), pe.group], axis=1),
                               hovertemplate="%{label}<br>US$%{value:.2f}bn (2024)<br>Brazil share of US imports %{customdata[0]}%<br>%{customdata[1]}<br>%{customdata[2]}<br>group %{customdata[3]}<extra></extra>"))
    save(fig, "02_exposure_treemap", "Top-40 HS4 (+firm lines) to the US, 2024 value; colour = added US rate in R5")
    # 03 event-time coefficients
    did = pd.read_csv(OUT / "did_results.csv")
    b = did[(did.cell == "baseline") & (did.outcome == "triple") & did.ci80_lo.notna()]
    fig = go.Figure(); order = POST_REG
    for i, gg in enumerate(["covered", "relief", "232"]):
        s = b[b.group == gg].set_index("window").reindex(order)
        x = [j + (i - 1) * 0.2 for j in range(len(order))]
        pct = lambda v: 100 * (np.exp(v) - 1)
        fig.add_trace(go.Scatter(x=x, y=pct(s.coef), mode="markers", name=gg,
                                 error_y=dict(type="data", symmetric=False, array=pct(s.ci90_hi) - pct(s.coef), arrayminus=pct(s.coef) - pct(s.ci90_lo))))
    fig.update_xaxes(tickvals=list(range(len(order))), ticktext=["Jul-25 (letter)", "R2 40%", "R3 relief", "R4 s122", "R5 s301"])
    fig.add_hline(y=0, line_dash="dot"); fig.update_yaxes(title="% vs exempt lines (log US - log ROW), 90% cluster-bootstrap CI")
    save(fig, "03_did_event_time", "Triple-difference event-time effects by group (HS4, ref. = exempt excl. crude)")
    # 04 diversion
    pdid = pd.read_csv(CACHE / "product_did.csv", dtype={"hs4": str})
    t = pdid[pdid.group.isin(["covered", "relief", "232"]) & (pdid.dus_bn_yr < 0)]
    fig = go.Figure()
    for c_ in ("commodity", "manufactured"):
        s = t[t["class"] == c_]
        fig.add_trace(go.Scatter(x=s.dus_bn_yr, y=s.drow_bn_yr, mode="markers", name=c_, text=s.hs4,
                                 marker=dict(size=np.clip(np.sqrt(s.v24_us / 1e6), 4, 30)), hovertemplate="%{text}: dUS %{x:.2f}, dROW %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[-0.8, 0], y=[0.8, 0], mode="lines", name="full diversion (d=1)", line=dict(dash="dash")))
    fig.update_xaxes(title="change in US-bound exports vs control, US$bn/yr (treated window)"); fig.update_yaxes(title="change in non-US exports vs control, US$bn/yr")
    save(fig, "04_diversion_by_product", "Diversion by product: lost US sales vs gained rest-of-world sales (treated HS4)")
    # 05 unit value ratios
    tn = pd.read_csv(CACHE / "uv_ratio_ncm.csv", dtype={"ncm": str}, parse_dates=["ym"])
    fig = go.Figure()
    for n, s in tn.groupby("ncm"):
        fig.add_trace(go.Scatter(x=s.ym, y=s.uv_us / s.uv_row, name=f"{n} {UV_NCM.get(n, '')}"))
    shade(fig); fig.add_hline(y=1, line_dash="dot"); fig.update_yaxes(title="FOB unit value to US / to rest of world")
    save(fig, "05_unit_value_ratios", "Brazil's US-bound vs rest-of-world FOB unit values (ComexStat NCM)")
    # 06 mirror shares
    ct = comtrade_df(); a6 = ct[ct.allp & ct.hs4.isin(MIRROR_HS4)]
    w = a6[a6.partner == 0].groupby(["hs4", "ym"]).cif.sum()
    fig = make_subplots(rows=3, cols=4, subplot_titles=MIRROR_HS4)
    for k, h in enumerate(MIRROR_HS4):
        s = a6[(a6.hs4 == h) & (a6.partner != 0)]
        tot = w.xs(h, level=0) if h in w.index.get_level_values(0) else None
        if tot is None:
            continue
        top = s.groupby("partner").cif.sum().sort_values(ascending=False).head(4).index
        for p_ in top:
            q_ = s[s.partner == p_].set_index("ym").cif.reindex(tot.index).fillna(0) / tot * 100
            fig.add_trace(go.Scatter(x=q_.index, y=q_, name=str(p_), line=dict(width=3 if p_ == 76 else 1), showlegend=False,
                                     hovertemplate=f"partner {p_}: %{{y:.1f}}%<extra></extra>"), row=k // 4 + 1, col=k % 4 + 1)
    save(fig, "06_us_mirror_shares", "US import shares by supplier (Comtrade, CIF); thick line = Brazil (76); M49 codes")
    # 07 states
    se = pd.read_csv(CACHE / "state_exposure.csv", index_col=0).sort_values("exposure_pct", ascending=False)
    fig = make_subplots(rows=1, cols=3, subplot_titles=["exposure: covered US exports, % of UF exports (2024)", "gross loss US$bn/yr", "unemployment change vs pre (pp)"])
    fig.add_trace(go.Bar(x=se.uf2, y=se.exposure_pct, showlegend=False), 1, 1)
    fig.add_trace(go.Bar(x=se.uf2, y=se.gl, showlegend=False), 1, 2)
    fig.add_trace(go.Bar(x=se.uf2, y=se.d_un, showlegend=False), 1, 3)
    save(fig, "07_state_exposure", "States: exposure, loss and labour-market divergence (exploratory, n=27)")
    # 08 event study
    ev = pd.read_csv(OUT / "event_study.csv")
    sers = ["brl_usd", "ibovespa_usd", "gov_real_yield_10y", "exposed_basket_usd", "embraer_usd", "embraer_minus_ibov"]
    fig = make_subplots(rows=2, cols=3, subplot_titles=sers)
    for k, sid in enumerate(sers):
        s = ev[(ev.series == sid) & (ev.window == "[-5,+5]")].dropna(subset=["car"])
        col = s.group.map({"E": "firebrick", "D": "seagreen", "C": "gray"})
        fig.add_trace(go.Bar(x=s.date, y=s.car, marker_color=col, text=s.event, showlegend=False, hovertemplate="%{text}<br>%{y:.2f}<extra></extra>"), k // 3 + 1, k % 3 + 1)
    save(fig, "08_event_study", "CAR [-5,+5] by event (red = escalation, green = de-escalation, grey = control); % or bp")
    # 09 tornado
    em = pd.read_csv(OUT / "escalation_matrix.csv")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=em.rung, x=em.export_loss_net_central_bn, orientation="h", name="Brazil net export loss vs (a), central",
                         error_x=dict(type="data", symmetric=False, array=em.export_loss_net_high_bn - em.export_loss_net_central_bn,
                                      arrayminus=em.export_loss_net_central_bn - em.export_loss_net_low_bn)))
    fig.add_trace(go.Bar(y=em.rung, x=-em.us_duty_paid_bn_central, orientation="h", name="duty paid by US importers (central, negative axis)"))
    fig.update_layout(barmode="overlay"); fig.update_xaxes(title="US$bn per year")
    save(fig, "09_escalation_tornado", "Escalation ladder (a)-(e): Brazil net export loss and US importer duty bill")
    # 10 CPI
    B = bls(); fig = go.Figure()
    for k_ in ["CUUR0000SEFP01", "CUUR0000SEFC", "CUUR0000SEFN02", "CUUR0000SA0"]:
        s = (100 * (B[k_] / B[k_].shift(12) - 1)).dropna(); s = s[s.index >= "2023-01-01"]
        fig.add_trace(go.Scatter(x=s.index, y=s, name=BLS_NAMES[k_]))
    shade(fig); fig.add_vline(x="2025-11-20", line_dash="dash", annotation_text="EO 14361 relief")
    fig.add_vline(x="2025-11-14", line_dash="dot", annotation_text="EO 14360 all-country ag")
    fig.update_yaxes(title="% y/y (NSA; Oct-2025 missing)")
    save(fig, "10_us_cpi_and_relief", "US CPI coffee, beef, juices vs all items, with the Nov-2025 relief")
    R["charts"] = sorted(str(p.name) for p in CH.glob("*.html")); save_results()


@step
def run_all():
    for s in ["anchors", "pulls_hts", "pulls_cotahist", "timeline", "exposure", "effects", "losses", "unit_values", "mirror",
              "states", "cpi_relief", "markets", "matrix", "charts"]:
        print("==", s, flush=True); STEPS[s]()

if __name__ == "__main__":
    for s in sys.argv[1:]:
        print("==", s, flush=True)
        STEPS[s]()
