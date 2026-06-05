"""bcb_sgs.py — Tier-2 native adapter: Banco Central do Brasil SGS time-series API.

This is the high-frequency path Dateno does NOT carry. BCB SGS is public, free,
no key. Endpoint:
    https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{n}?formato=json
returns [{"data":"dd/MM/yyyy","valor":"x.xx"}, ...].

Writes canonical bronze CSV to warehouse/bronze/native/<metric_id>.csv with columns:
    metric_id,metric_name,theme,source_id,freq,date,value,unit
(date is ISO yyyy-mm-dd). The pipeline's silver step reads this schema directly.

Run:  python3 ingest/bcb_sgs.py
"""
from __future__ import annotations
import json, ssl, time, pathlib, urllib.request, urllib.error
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _CTX = ssl.create_default_context()

# BCB SGS is notoriously flaky: identical requests return 200/400/406 at random
# under load. Retry with backoff and tolerate intermittent rejections.
RETRIES = 6
# 10-year window for daily series (BCB caps daily ranges at ~10y); long window
# for monthly. End date matches the pipeline's reproducible RUN_TS (2026-06-01).
DAILY_START, MONTHLY_START, END = "01/06/2016", "01/01/2000", "01/06/2026"

ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "warehouse" / "bronze" / "native"

# registry metric_id -> SGS series spec. `n` = how many most-recent obs to pull.
# All codes below were verified against known current reality before inclusion
# (see README "BCB SGS code verification"). NFSP series follow BCB convention:
# positive = financing need = deficit; the pipeline flips sign where a *balance*
# is wanted. `_internal` series are inputs to derived series, not headline metrics.
SERIES = {
    # --- policy & market (daily) ---
    "selic_target": dict(code=432, freq="daily", unit="pct_pa",
                         metric_name="Selic target rate", theme="macro_policy"),
    "brl_usd": dict(code=1, freq="daily", unit="brl_per_usd",
                    metric_name="BRL/USD official exchange rate", theme="market_repricing"),
    # --- inflation (monthly) ---
    "ipca_monthly": dict(code=433, freq="monthly", unit="pct_mom",
                         metric_name="IPCA monthly change", theme="inflation"),
    "ipca_12m": dict(code=13522, freq="monthly", unit="pct_yoy",
                     metric_name="IPCA accumulated 12 months", theme="inflation"),
    # --- activity & credit (monthly) ---
    "ibc_br": dict(code=24363, freq="monthly", unit="index",
                   metric_name="IBC-Br monthly activity index", theme="domestic_demand"),
    "credit_gdp": dict(code=20622, freq="monthly", unit="pct_gdp",
                       metric_name="Credit to GDP", theme="domestic_demand"),
    "delinquency_rate": dict(code=21082, freq="monthly", unit="pct",
                             metric_name="Delinquency rate (credit)", theme="domestic_demand"),
    "household_debt_income": dict(code=29037, freq="monthly", unit="pct_income",
                                  metric_name="Household debt-to-income", theme="domestic_demand"),
    "household_credit_balance": dict(code=20570, freq="monthly", unit="brl_mn",
                                     metric_name="Household credit balance", theme="domestic_demand",
                                     internal=True),
    "corporate_credit_balance": dict(code=20571, freq="monthly", unit="brl_mn",
                                     metric_name="Corporate credit balance", theme="domestic_demand",
                                     internal=True),
    # --- fiscal (monthly) ---
    "gross_public_debt_gdp": dict(code=13762, freq="monthly", unit="pct_gdp",
                                  metric_name="Gross general govt debt / GDP", theme="fiscal"),
    "net_public_debt_gdp": dict(code=4503, freq="monthly", unit="pct_gdp",
                                metric_name="Net public debt / GDP", theme="fiscal"),
    "nominal_deficit_gdp": dict(code=5727, freq="monthly", unit="pct_gdp_nfsp",
                                metric_name="Nominal deficit / GDP (NFSP, +=deficit)", theme="fiscal"),
    "primary_result_nfsp": dict(code=5793, freq="monthly", unit="pct_gdp_nfsp",
                                metric_name="Primary result / GDP (NFSP, +=deficit)", theme="fiscal",
                                internal=True),
    # --- external (daily) ---
    "fx_reserves": dict(code=13621, freq="daily", unit="usd_mn",
                        metric_name="International reserves", theme="external_sector"),
}
for _s in SERIES.values():
    _s.setdefault("source_id", "bcb_sgs")
    _s.setdefault("internal", False)


def fetch(code: int, freq: str):
    start = DAILY_START if freq == "daily" else MONTHLY_START
    url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
           f"?formato=json&dataInicial={start}&dataFinal={END}")
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "brazil-macro-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=40, context=_CTX) as resp:
                body = resp.read().decode("utf-8", "replace").strip()
            if not body:  # BCB sometimes 200s with an empty body — treat as transient
                raise ValueError("empty body")
            return json.loads(body)
        except (urllib.error.HTTPError, urllib.error.URLError,
                json.JSONDecodeError, ValueError) as e:
            last = e
            transient = (not isinstance(e, urllib.error.HTTPError)
                         or e.code in (400, 406, 429, 500, 502, 503, 504))
            if transient and attempt < RETRIES:
                time.sleep(1.5 * attempt)
                continue
            raise
    raise last  # pragma: no cover


def iso(d: str) -> str:  # dd/MM/yyyy -> yyyy-mm-dd
    dd, mm, yyyy = d.split("/")
    return f"{yyyy}-{mm}-{dd}"


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    ok = 0
    for metric_id, s in SERIES.items():
        try:
            data = fetch(s["code"], s["freq"])
            lines = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
            for row in data:
                if row.get("valor") in (None, ""):
                    continue
                lines.append(f'{metric_id},"{s["metric_name"]}",{s["theme"]},'
                             f'{s["source_id"]},{s["freq"]},{iso(row["data"])},'
                             f'{row["valor"]},{s["unit"]}')
            (NATIVE / f"{metric_id}.csv").write_text("\n".join(lines) + "\n")
            print(f"[ok]   {metric_id:<16} SGS {s['code']:<6} {s['freq']:<7} {len(data)} obs")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {metric_id:<16} SGS {s['code']} :: {e}")
    print(f"\nPulled {ok}/{len(SERIES)} native series -> {NATIVE}")


if __name__ == "__main__":
    main()
