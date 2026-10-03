"""_http.py — shared HTTP + bronze-writing helpers for the ingest adapters.

One place for the SSL context (certifi on python.org macOS), the User-Agent
(several Brazilian portals 403 the default Python-urllib UA), retries, and the
canonical bronze contract:

    metric_id,metric_name,theme,source_id,freq,date,value,unit[,entity_id]

`entity_id` is optional: blank/absent means the series is about Brazil ("BR").
Company series carry the company key (e.g. "PETR") and land in bronze/companies/.
"""
from __future__ import annotations
import json, ssl, time, pathlib, urllib.request, urllib.error
import pandas as pd

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001 — fall back to system default context
    CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRONZE = ROOT / "warehouse" / "bronze"
NATIVE = BRONZE / "native"
COMPANIES = BRONZE / "companies"
RAW_CACHE = BRONZE / "raw"  # gitignored download cache (large zips/parquets)
UA = "brazil-macro-pipeline/1.0"
BRONZE_COLS = ["metric_id", "metric_name", "theme", "source_id", "freq", "date", "value", "unit"]


def get_bytes(url: str, *, headers: dict | None = None, data: bytes | None = None,
              method: str | None = None, timeout: int = 90, retries: int = 4,
              backoff: float = 3.0) -> bytes:
    """GET/POST with retries on network errors, 429 and 5xx."""
    h = {"User-Agent": UA, **(headers or {})}
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=h, method=method)
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
        time.sleep(backoff * attempt)
    raise RuntimeError(f"{url} failed after {retries} attempts: {last}")


def get_json(url: str, **kw):
    return json.loads(get_bytes(url, headers={"Accept": "application/json", **kw.pop("headers", {})}, **kw))


def post_json(url: str, body: dict, **kw):
    data = json.dumps(body).encode()
    return json.loads(get_bytes(url, data=data, method="POST",
                                headers={"Content-Type": "application/json", **kw.pop("headers", {})}, **kw))


def cached(url: str, name: str, *, max_age_days: float | None = None, **kw) -> pathlib.Path:
    """Download `url` into the raw cache once; reuse unless older than max_age_days."""
    RAW_CACHE.mkdir(parents=True, exist_ok=True)
    p = RAW_CACHE / name
    if p.exists() and p.stat().st_size > 0:
        if max_age_days is None or (time.time() - p.stat().st_mtime) < max_age_days * 86400:
            return p
    p.write_bytes(get_bytes(url, **kw))
    return p


def write_bronze(df: pd.DataFrame, path: pathlib.Path, *, entity: bool = False) -> int:
    """Validate and write one bronze CSV. Refuses to write an empty series
    (an empty file would silently replace a good snapshot)."""
    cols = BRONZE_COLS + (["entity_id"] if entity else [])
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing bronze columns {missing}")
    out = df[cols].copy()
    out = out[out["value"].notna()]
    if out.empty:
        print(f"[skip] {path.name}: no rows — keeping existing file")
        return 0
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out = out.sort_values((["entity_id"] if entity else []) + ["date"])
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    return len(out)
