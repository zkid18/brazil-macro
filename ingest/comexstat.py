"""comexstat.py — Tier-2 native adapter: MDIC ComexStat trade API.

POST https://api-comexstat.mdic.gov.br/general with a JSON body. Returns monthly
FOB (US$). The API rate-limits aggressively (~1 req / 10s) so we space calls.

Series (monthly, US$ FOB):
  exports_total, imports_total  (no filter)
  soy/oil/iron_ore/beef/coffee/sugar _exports  (export flow, NCM groups)
  fertilizer_imports            (import flow, NCM chapter 31 codes)

NCM groups were validated against known magnitudes before inclusion (e.g. soy
~US$5-7bn in harvest months). Writes canonical bronze to bronze/native/.
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

# metric_id -> (flow, [NCM 8-digit codes] or None for total, name, theme)
SERIES = {
    "exports_total":     ("export", None, "Total exports (FOB)", "external_trade"),
    "imports_total":     ("import", None, "Total imports (FOB)", "external_trade"),
    "soy_exports":       ("export", ["12019000", "12010010"], "Soybean exports", "agriculture_trade"),
    "oil_exports":       ("export", ["27090010", "27090090"], "Crude oil exports", "energy_trade"),
    "iron_ore_exports":  ("export", ["26011100", "26011200"], "Iron ore exports", "minerals_trade"),
    "beef_exports":      ("export", ["02013000", "02023000"], "Beef exports", "agriculture_trade"),
    "coffee_exports":    ("export", ["09011110", "09011190", "09012100"], "Coffee exports", "agriculture_trade"),
    "sugar_exports":     ("export", ["17011400", "17019900"], "Sugar exports", "agriculture_trade"),
    "fertilizer_imports": ("import", ["31021010", "31042090", "31052000", "31053000"],
                           "Fertilizer imports", "agriculture_risk"),
    "niobium_exports":   ("export", ["72029300"], "Niobium (ferroniobium) exports", "minerals_trade"),
    "potash_imports":    ("import", ["31042010", "31042090"], "Potash imports", "agriculture_risk"),
}


def fetch(flow, ncms):
    body = {"flow": flow, "monthDetail": True, "period": PERIOD,
            "filters": ([{"filter": "ncm", "values": ncms}] if ncms else []),
            "details": [], "metrics": ["metricFOB"]}
    data = json.dumps(body).encode()
    for attempt in range(1, 6):
        try:
            req = urllib.request.Request(URL, data=data, headers=HDR, method="POST")
            with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
                payload = json.loads(r.read())
            return payload["data"]["list"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 5:
                time.sleep(PAUSE + 3 * attempt); continue
            raise
        except (urllib.error.URLError, KeyError, TypeError):
            if attempt < 5:
                time.sleep(PAUSE); continue
            raise
    return []


def write(metric_id, name, theme, rows):
    lines = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
    for r in sorted(rows, key=lambda x: (x["year"], x["monthNumber"])):
        date = f'{r["year"]}-{int(r["monthNumber"]):02d}-01'
        lines.append(f'{metric_id},"{name}",{theme},comexstat,monthly,{date},{r["metricFOB"]},usd_fob')
    (NATIVE / f"{metric_id}.csv").write_text("\n".join(lines) + "\n")
    print(f"[ok]   {metric_id:<18} {len(rows)} months")


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
            rows = fetch(flow, ncms)
            if rows:
                write(mid, name, theme, rows)
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
