"""dateno_discover.py — find candidate datasets in Dateno for registry metrics we
have not ingested yet.

Dateno's search index (1.5M+ datasets) returns metadata and links, not values. For
every registry metric that coverage.py marks as pending, query Dateno's Brazil
open-data catalog with the metric name and keep the top hits. The portal lists them
under "Not yet in the warehouse" so a reader can follow the link to the source.

    GET https://api.dateno.io/search/0.2/query?q=..&filters=source.countries.name="Brazil"
        &filters=source.catalog_type="Open data portal"&limit=5&apikey=$DATENO_API_KEY

Without `catalog_type`, Portuguese queries drown in geoportal map layers.
Writes registry/dateno_candidates.json.  Run:  python3 ingest/dateno_discover.py
"""
from __future__ import annotations
import json, os, sys, time, pathlib, urllib.parse
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_json, ROOT  # noqa: E402

API = os.environ.get("DATENO_API_BASE", "https://api.dateno.io").rstrip("/")
KEY = os.environ.get("DATENO_API_KEY")
OUT = ROOT / "registry" / "dateno_candidates.json"


def search(q: str, limit: int = 5) -> list[dict]:
    params = [("q", q), ("filters", 'source.countries.name="Brazil"'),
              ("filters", 'source.catalog_type="Open data portal"'), ("limit", limit), ("apikey", KEY)]
    d = get_json(f"{API}/search/0.2/query?" + urllib.parse.urlencode(params), timeout=60)
    out = []
    for h in d.get("hits", {}).get("hits", []):
        src = h.get("_source", {})
        ds, so = src.get("dataset", {}), src.get("source", {})
        out.append(dict(title=ds.get("title"), url=ds.get("url") or so.get("uid"),
                        publisher=so.get("name") or (ds.get("responsible") or {}).get("title"),
                        formats=ds.get("formats", []), changed=(ds.get("date_changed") or "")[:10],
                        dateno_id=src.get("id")))
    return out


def main():
    if not KEY:
        raise SystemExit("DATENO_API_KEY not set. `set -a; source .env; set +a` first.")
    reg = pd.read_csv(ROOT / "registry" / "brazil_macro_data_allocation_metrics.csv")
    cov = pd.read_csv(ROOT / "registry_coverage.csv")
    pending = cov[cov.status.str.startswith("pending")].merge(
        reg[["metric_id", "metric_name"]], on="metric_id", how="left")
    res = {}
    for r in pending.itertuples():
        q = str(r.metric_name).replace("_", " ")
        try:
            hits = search(q)
        except Exception as e:  # noqa: BLE001 — one failed query must not stop the sweep
            print(f"[fail] {r.metric_id}: {e}")
            continue
        res[r.metric_id] = dict(query=q, status=r.status, hits=hits)
        print(f"[ok]   {r.metric_id:<36} {len(hits)} hits  {hits[0]['title'][:60] if hits else ''}")
        time.sleep(0.3)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"Wrote {OUT} ({len(res)} metrics)")


if __name__ == "__main__":
    main()
