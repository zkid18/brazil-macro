"""comexstat.py — Tier-2 native adapter: MDIC ComexStat trade API.

POST https://api-comexstat.mdic.gov.br/general with a JSON body. Returns monthly
FOB (US$) and, on request, net weight (`metricKG`). The API rate-limits
aggressively (~1 req / 10s) so we space calls by PAUSE.

Series (monthly, 2014-01 -> latest month published):
  exports_total, imports_total  (no filter)                          usd_fob
  soy/oil/iron_ore/beef/coffee/sugar _exports  (export flow, NCM groups) usd_fob
  fertilizer_imports, potash_imports, niobium_exports                usd_fob
  pulp_exports                  chemical wood pulp, SH4 headings 4702+4703+4704
  oil_exports_kg, iron_ore_exports_kg, pulp_exports_kg               thousand_tonnes
      (same request as the FOB series, `"metrics":["metricFOB","metricKG"]`;
       value = metricKG / 1e6)
  exports_to_china              all-goods FOB, `details:["country"]` row "China"
  exports_to_us                 all-goods FOB, filter country 249 (Estados Unidos)
  exports_to_eu                 all-goods FOB, filter economicBlock 22 ("União
                                Europeia - UE") — ComexStat applies CURRENT EU-27
                                membership retroactively (2019 query returns no UK,
                                but does include French overseas departments,
                                Åland, Andorra, San Marino), so the series is a
                                consistent EU-27 aggregate across 2014-2026.
  beef_exports_to_china         beef NCMs (as beef_exports) x filter country 160

Verification (2026-10-03, live requests):
  * Pulp: 2025 exports by NCM within headings 4702-4705: 47032900 (bleached
    eucalyptus kraft) US$8.94bn/20.4 Mt (~88%), 47020000 (dissolving) US$0.99bn,
    47032110/47032190 (bleached conifer) US$0.21bn, 47031900 US$23M, 4704xx ~0,
    4705 ~0. We filter by heading (4702/4703/4704 = all chemical wood pulp) so
    NCM re-codings (e.g. 47032100 -> 47032110/90) cannot drop rows.
    Aug-26 47032900 alone = 1.41 Mt / US$748M (report.md H6).
  * Oil KG: Nov-25 8.40 Mt / US$3.48bn (≈ 1.98 mb/d at 7.33 bbl/t) — plausible
    vs ~4.4 mb/d production. Iron ore KG Aug-26 34.4 Mt / US$2.05bn (~US$60/t FOB).
  * Beef to China: 2025 = US$8.84bn, essentially all NCM 02023000 (frozen
    boneless); 02013000 to China ~0. Uses the same NCM pair as beef_exports.
  * Country codes from GET /tables/countries (China 160, Estados Unidos 249);
    block id from GET /tables/economic-blocks.

NB: existing series keep their original requests byte-for-byte; adding
metricKG to a request does not change metricFOB.
Writes canonical bronze to bronze/native/.
Run:  python3 ingest/comexstat.py
"""
from __future__ import annotations
import json, ssl, time, pathlib, urllib.request, urllib.error
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "warehouse" / "bronze" / "native"
URL = "https://api-comexstat.mdic.gov.br/general"
HDR = {"User-Agent": "brazil-macro-pipeline/1.0", "Content-Type": "application/json"}
# NB: ComexStat treats period as a year-range x month-range GRID, so the month
# bound must be 01..12 to get every month (not a month-of-year window).
PERIOD = {"from": "2014-01", "to": "2026-12"}
PAUSE = 11  # seconds between calls (rate-limit safety)

BEEF_NCMS = ["02013000", "02023000"]
CHINA, USA, EU_BLOCK = "160", "249", "22"

# metric_id -> (flow, [NCM 8-digit codes] or None for total, name, theme)
SERIES = {
    "exports_total":     ("export", None, "Total exports (FOB)", "external_trade"),
    "imports_total":     ("import", None, "Total imports (FOB)", "external_trade"),
    "soy_exports":       ("export", ["12019000", "12010010"], "Soybean exports", "agriculture_trade"),
    "oil_exports":       ("export", ["27090010", "27090090"], "Crude oil exports", "energy_trade"),
    "iron_ore_exports":  ("export", ["26011100", "26011200"], "Iron ore exports", "minerals_trade"),
    "beef_exports":      ("export", BEEF_NCMS, "Beef exports", "agriculture_trade"),
    "coffee_exports":    ("export", ["09011110", "09011190", "09012100"], "Coffee exports", "agriculture_trade"),
    "sugar_exports":     ("export", ["17011400", "17019900"], "Sugar exports", "agriculture_trade"),
    "fertilizer_imports": ("import", ["31021010", "31042090", "31052000", "31053000"],
                           "Fertilizer imports", "agriculture_risk"),
    "niobium_exports":   ("export", ["72029300"], "Niobium (ferroniobium) exports", "minerals_trade"),
    "potash_imports":    ("import", ["31042010", "31042090"], "Potash imports", "agriculture_risk"),
}

# FOB series that also get a net-weight companion from the SAME request.
# fob metric_id -> (kg metric_id, kg metric_name)
KG_COMPANION = {
    "oil_exports":      ("oil_exports_kg", "Crude oil exports (net weight)"),
    "iron_ore_exports": ("iron_ore_exports_kg", "Iron ore exports (net weight)"),
    "pulp_exports":     ("pulp_exports_kg", "Chemical wood pulp exports (net weight)"),
}

# Series needing filters beyond a plain NCM list.
# metric_id -> (flow, filters, name, theme)
EXTRA = {
    "pulp_exports": ("export", [{"filter": "heading", "values": ["4702", "4703", "4704"]}],
                     "Chemical wood pulp exports (FOB, SH 4702-4704)", "forestry_trade"),
    "exports_to_us": ("export", [{"filter": "country", "values": [USA]}],
                      "Exports to the United States (FOB)", "external_trade"),
    "exports_to_eu": ("export", [{"filter": "economicBlock", "values": [EU_BLOCK]}],
                      "Exports to the European Union, EU-27 (FOB)", "external_trade"),
    "beef_exports_to_china": ("export", [{"filter": "ncm", "values": BEEF_NCMS},
                                         {"filter": "country", "values": [CHINA]}],
                              "Beef exports to China (FOB)", "agriculture_trade"),
}


def _post(body, timeout=60):
    data = json.dumps(body).encode()
    for attempt in range(1, 6):
        try:
            req = urllib.request.Request(URL, data=data, headers=HDR, method="POST")
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                payload = json.loads(r.read())
            return payload["data"]["list"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 5:
                time.sleep(PAUSE + 3 * attempt); continue
            raise
        except (urllib.error.URLError, KeyError, TypeError, TimeoutError):
            if attempt < 5:
                time.sleep(PAUSE); continue
            raise
    return []


def fetch(flow, ncms, metrics=("metricFOB",)):
    body = {"flow": flow, "monthDetail": True, "period": PERIOD,
            "filters": ([{"filter": "ncm", "values": ncms}] if ncms else []),
            "details": [], "metrics": list(metrics)}
    return _post(body)


def fetch_filtered(flow, filters, metrics=("metricFOB",)):
    body = {"flow": flow, "monthDetail": True, "period": PERIOD,
            "filters": filters, "details": [], "metrics": list(metrics)}
    return _post(body, timeout=90)


def write(metric_id, name, theme, rows, field="metricFOB", unit="usd_fob", scale=None):
    lines = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
    for r in sorted(rows, key=lambda x: (x["year"], x["monthNumber"])):
        date = f'{r["year"]}-{int(r["monthNumber"]):02d}-01'
        v = r[field] if scale is None else f"{float(r[field]) / scale:.3f}"
        lines.append(f'{metric_id},"{name}",{theme},comexstat,monthly,{date},{v},{unit}')
    (NATIVE / f"{metric_id}.csv").write_text("\n".join(lines) + "\n")
    last = max(rows, key=lambda x: (x["year"], x["monthNumber"]))
    lv = float(last[field]) / (scale or 1)
    print(f"[ok]   {metric_id:<22} {len(rows)} months "
          f"(..{last['year']}-{last['monthNumber']}) latest={lv:,.1f} {unit}")


def write_with_kg(mid, name, theme, rows):
    write(mid, name, theme, rows)
    if mid in KG_COMPANION:
        kid, kname = KG_COMPANION[mid]
        write(kid, kname, theme, rows, field="metricKG", unit="thousand_tonnes", scale=1e6)


def fetch_by_country(flow):
    body = {"flow": flow, "monthDetail": True, "period": PERIOD,
            "filters": [], "details": ["country"], "metrics": ["metricFOB"]}
    data = json.dumps(body).encode()
    for attempt in range(1, 6):
        try:
            req = urllib.request.Request(URL, data=data, headers=HDR, method="POST")
            with urllib.request.urlopen(req, timeout=90, context=_CTX) as r:
                return json.loads(r.read())["data"]["list"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 5:
                time.sleep(PAUSE + 3 * attempt); continue
            raise
    return []


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    for i, (mid, (flow, ncms, name, theme)) in enumerate(SERIES.items()):
        if i:
            time.sleep(PAUSE)
        try:
            if mid in KG_COMPANION:
                rows = fetch(flow, ncms, metrics=("metricFOB", "metricKG"))
            else:
                rows = fetch(flow, ncms)
            if rows:
                write_with_kg(mid, name, theme, rows)
            else:
                print(f"[warn] {mid}: empty")
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {mid}: {e}")
    for mid, (flow, filters, name, theme) in EXTRA.items():
        time.sleep(PAUSE)
        try:
            metrics = ("metricFOB", "metricKG") if mid in KG_COMPANION else ("metricFOB",)
            rows = fetch_filtered(flow, filters, metrics)
            if rows:
                write_with_kg(mid, name, theme, rows)
            else:
                print(f"[warn] {mid}: empty")
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {mid}: {e}")
    # exports_by_destination: keep China (the book's demand-engine partner)
    time.sleep(PAUSE)
    try:
        rows = fetch_by_country("export")
        cn = [r for r in rows if (r.get("country") or r.get("noPaispt")) == "China"]
        if cn:
            write("exports_to_china", "Exports to China (FOB)", "external_trade", cn)
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] exports_to_china: {e}")


if __name__ == "__main__":
    main()
