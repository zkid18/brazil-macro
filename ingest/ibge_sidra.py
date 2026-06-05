"""ibge_sidra.py — Tier-2 native adapter: IBGE SIDRA (PNAD Contínua).

Rolling-quarter (monthly cadence) labor series, national:
  real_average_income  t6390 v5933  (R$, real)
  employed_population   t6320 v4090  (thousand persons)
-> enables derived real_wage_bill = employed * real income.

SIDRA period code is YYYYMM (ending month of the rolling quarter).
Writes canonical bronze to bronze/native/. Run:  python3 ingest/ibge_sidra.py
"""
from __future__ import annotations
import json, ssl, pathlib, urllib.request
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "warehouse" / "bronze" / "native"
HDR = {"User-Agent": "brazil-macro-pipeline/1.0"}

# metric_id -> (table, variable, name, theme, unit)
SERIES = {
    "real_average_income": (6390, 5933, "Real average labor income", "labor", "brl_real"),
    "employed_population": (6320, 4090, "Employed population", "labor", "thousand_persons"),
}


def fetch(table, var):
    url = f"https://apisidra.ibge.gov.br/values/t/{table}/n1/all/v/{var}/p/all"
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=90, context=_CTX) as r:
        return json.loads(r.read())[1:]  # drop header row


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    for mid, (table, var, name, theme, unit) in SERIES.items():
        rows = fetch(table, var)
        out = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
        n = 0
        for r in rows:
            code, v = r.get("D3C", ""), r.get("V")
            try:
                val = float(v)
            except (TypeError, ValueError):
                continue  # '...', '-' etc.
            if len(code) == 6:
                date = f"{code[:4]}-{code[4:6]}-01"
                out.append(f'{mid},"{name}",{theme},ibge_sidra,monthly,{date},{val},{unit}')
                n += 1
        (NATIVE / f"{mid}.csv").write_text("\n".join(out) + "\n")
        print(f"[ok]   {mid:<22} {n} obs")


if __name__ == "__main__":
    main()
