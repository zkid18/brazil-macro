"""bcb_focus.py — Tier-2 native adapter: BCB Focus market expectations (Olinda OData).

- focus_ipca_12m : ExpectativasMercadoInflacao12Meses (IPCA, smoothed) — true 12m-ahead.
- focus_selic_12m / focus_gdp_growth / focus_fx : ExpectativasMercadoAnuais, taking for
  each survey date the expectation for the NEXT calendar year (reference = year+1),
  the conventional Focus forward reading.

Writes canonical bronze to warehouse/bronze/native/<metric_id>.csv. Uses median.
Run:  python3 ingest/bcb_focus.py
"""
from __future__ import annotations
import json, ssl, time, pathlib, urllib.request, urllib.error, urllib.parse
import pandas as pd
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "warehouse" / "bronze" / "native"
BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"
HDR = {"User-Agent": "brazil-macro-pipeline/1.0", "Accept": "application/json"}


def odata(resource: str, params: str) -> list:
    url = f"{BASE}/{resource}?" + urllib.parse.quote(params + "&$format=json", safe="$&=,")
    for attempt in range(1, 5):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
                return json.loads(r.read())["value"]
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as e:
            if attempt == 4:
                raise
            time.sleep(2 * attempt)
    return []


def write(metric_id, name, theme, freq, unit, df):
    df = df.dropna().sort_values("date")
    lines = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
    for _, r in df.iterrows():
        lines.append(f'{metric_id},"{name}",{theme},bcb_focus,{freq},{r.date},{r.value},{unit}')
    (NATIVE / f"{metric_id}.csv").write_text("\n".join(lines) + "\n")
    print(f"[ok]   {metric_id:<16} {len(df)} obs ({df.date.min()}..{df.date.max()})")


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    # 1) IPCA 12m-ahead (smoothed, base 0)
    v = odata("ExpectativasMercadoInflacao12Meses",
              "$filter=Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0"
              "&$select=Data,Mediana&$orderby=Data&$top=20000")
    df = pd.DataFrame(v).rename(columns={"Data": "date", "Mediana": "value"})
    write("focus_ipca_12m", "Focus expected IPCA 12m", "expectations", "daily", "pct_yoy", df)

    # 2) Selic / GDP / FX next-year expectation (reference = survey_year + 1)
    plan = [("focus_selic_12m", "Selic", "Focus expected Selic (next yr)", "pct_pa"),
            ("focus_gdp_growth", "PIB Total", "Focus expected GDP growth (next yr)", "pct_yoy"),
            ("focus_fx", "Câmbio", "Focus expected BRL/USD (next yr)", "brl_per_usd")]
    for metric_id, indic, name, unit in plan:
        v = odata("ExpectativasMercadoAnuais",
                  f"$filter=Indicador eq '{indic}' and baseCalculo eq 0"
                  "&$select=Data,DataReferencia,Mediana&$orderby=Data&$top=60000")
        d = pd.DataFrame(v)
        if d.empty:
            print(f"[skip] {metric_id}: no rows"); continue
        d["yr"] = d["Data"].str[:4].astype(int)
        d["ref"] = d["DataReferencia"].astype(int)
        d = d[d.ref == d.yr + 1]  # next-year forward expectation
        write(metric_id, name, "expectations", "daily", unit,
              d.rename(columns={"Data": "date", "Mediana": "value"})[["date", "value"]])


if __name__ == "__main__":
    main()
