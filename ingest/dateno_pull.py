"""dateno_pull.py — reproducible Tier-1 extractor.

Reads registry/source_map.yml, pulls each Tier-1 series from Dateno's structured
timeseries API, and lands raw CSV into warehouse/bronze/<ts_id>.csv.

Endpoint (observed via the Dateno MCP server):
    GET {DATENO_API_BASE}/statsdb/0.1/ns/{ns}/ts/{ts_id}/export.csv
Returns tidy CSV: indicator_id,indicator_name,country_id,country_name,
                  countryiso3code,date,value,unit,obs_status,decimal

Two transport modes:
  * REST  — set DATENO_API_BASE (e.g. https://api.dateno.io) and optionally
            DATENO_API_KEY. Used when the API is network-reachable.
  * MCP   — in the Claude Code session the same call is made via the
            mcp__claude_ai_Dateno__export_timeseries_file tool; the base64
            payload is decoded to the same bronze path. (The MCP host's REST
            endpoint at 127.0.0.1:8100 is NOT reachable from a normal shell,
            which is why this script exists for out-of-sandbox runs.)

Idempotent: re-running overwrites bronze CSVs in place.
"""
from __future__ import annotations
import os, sys, ssl, pathlib, urllib.request, urllib.error
import yaml
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001 — fall back to system default context
    _SSL_CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRONZE = ROOT / "warehouse" / "bronze"
SOURCE_MAP = ROOT / "registry" / "source_map.yml"
API_BASE = os.environ.get("DATENO_API_BASE", "https://api.dateno.io").rstrip("/")
API_KEY = os.environ.get("DATENO_API_KEY")  # never hard-code; export before running


def load_tier1() -> dict:
    with open(SOURCE_MAP) as fh:
        return yaml.safe_load(fh).get("tier1", {})


def pull_rest(ns: str, ts_id: str) -> bytes:
    if not API_KEY:
        raise RuntimeError("DATENO_API_KEY not set. `export DATENO_API_KEY=...` first.")
    url = f"{API_BASE}/statsdb/0.1/ns/{ns}/ts/{ts_id}/export.csv"
    # NB: the API rejects the default Python-urllib User-Agent with 403; send a normal one.
    req = urllib.request.Request(url, headers={
        "apikey": API_KEY, "Accept": "text/csv", "User-Agent": "brazil-macro-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        return resp.read()


def main() -> int:
    BRONZE.mkdir(parents=True, exist_ok=True)
    tier1 = load_tier1()
    ok, fail = 0, 0
    for metric_id, spec in tier1.items():
        ns, ts_id = spec["ns"], spec["ts_id"]
        try:
            data = pull_rest(ns, ts_id)
            (BRONZE / f"{ts_id}.csv").write_bytes(data)
            print(f"[ok]   {metric_id:<34} {ns}/{ts_id}")
            ok += 1
        except Exception as e:  # noqa: BLE001 — report and continue
            print(f"[FAIL] {metric_id:<34} {ns}/{ts_id} :: {e}", file=sys.stderr)
            fail += 1
    print(f"\nPulled {ok} series, {fail} failed. Bronze: {BRONZE}")
    return 1 if fail and not ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
