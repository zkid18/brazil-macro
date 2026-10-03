"""bcb_olinda.py — BCB Olinda OData: Pix monthly transactions (count and value).

Service: https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata/
Resource (from $metadata): function EstatisticasTransacoesPix(Database='yyyyMM')
    -> rows AnoMes, PAG_PFPJ, REC_PFPJ, regions, ages, FORMAINICIACAO, NATUREZA,
       FINALIDADE, VALOR (R$), QUANTIDADE (count)
Monthly totals = sum of VALOR / QUANTIDADE over all breakdown rows of a month.

Gotchas:
  * `Database` is a START month — it returns every month from it onward (~13k
    rows/month), so each month is requested with Database=M & $filter=AnoMes eq M
    and $select=QUANTIDADE,VALOR (~7-15 s per month on the server).
  * `$apply` aggregation is silently ignored.
  * Pix launched Nov-2020. Month totals are cached in the gitignored raw cache
    (warehouse/bronze/raw/pix_monthly_totals.csv); the last 3 months are always
    re-fetched to catch revisions.

Verification (2026-10-03): Jan-2021 totals identical across two independent
resources (EstatisticasTransacoesPix and TransacoesPixPorMunicipio payer side:
169.77 mn tx, R$ 137.9 bn); Aug-2026 = 7,367 mn tx, R$ 3,174 bn; Sep-2026 = 7,170 mn
tx, R$ 3,225 bn — consistent with Pix running ~7 bn tx/month in 2026.

Run:  python3 ingest/bcb_olinda.py
"""
from __future__ import annotations
import sys, pathlib, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_json, write_bronze, NATIVE, RAW_CACHE  # noqa: E402

BASE = "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata"
CACHE = RAW_CACHE / "pix_monthly_totals.csv"
FIRST = (2020, 11)
SERIES = {
    "pix_transactions_count": dict(col="qty", scale=1e6, unit="million_tx",
                                   metric_name="Pix transactions, monthly count (mn)"),
    "pix_transactions_value": dict(col="value", scale=1e9, unit="brl_bn",
                                   metric_name="Pix transactions, monthly value (R$ bn)"),
}
for _s in SERIES.values():
    _s.update(theme="domestic_demand", source_id="bcb_olinda_pix", freq="monthly")


def month_totals(ym: int) -> tuple[int, float, float, int]:
    url = (f"{BASE}/EstatisticasTransacoesPix(Database=@Database)?@Database='{ym}'"
           f"&$format=json&$select=QUANTIDADE,VALOR&$filter=AnoMes%20eq%20{ym}")
    rows = get_json(url, timeout=180, retries=5)["value"]
    return ym, sum(r["QUANTIDADE"] or 0 for r in rows), sum(r["VALOR"] or 0 for r in rows), len(rows)


def main():
    today = dt.date.today()
    months, (y, m) = [], FIRST
    while (y, m) <= (today.year, today.month):
        months.append(y * 100 + m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    have = pd.read_csv(CACHE) if CACHE.exists() else pd.DataFrame(columns=["ym", "qty", "value"])
    have = have[have.ym < months[-3]] if len(have) else have  # always refresh last 3 months
    todo = [ym for ym in months if ym not in set(have.ym)]
    print(f"Pix: {len(todo)} months to fetch ({len(have)} cached)")
    got = []
    with ThreadPoolExecutor(4) as ex:
        for ym, q, v, n in ex.map(month_totals, todo):
            if n:
                got.append(dict(ym=ym, qty=q, value=v))
    tot = pd.concat([have, pd.DataFrame(got)]).sort_values("ym").drop_duplicates("ym", keep="last")
    RAW_CACHE.mkdir(parents=True, exist_ok=True)
    tot.to_csv(CACHE, index=False)
    date = pd.to_datetime(tot.ym.astype(int).astype(str), format="%Y%m")
    for metric_id, s in SERIES.items():
        df = pd.DataFrame({"date": date, "value": (tot[s["col"]] / s["scale"]).round(3)})
        for k in ("metric_name", "theme", "source_id", "freq", "unit"):
            df[k] = s[k]
        df["metric_id"] = metric_id
        n = write_bronze(df, NATIVE / f"{metric_id}.csv")
        print(f"[ok]   {metric_id:<24} {n} obs  {date.min():%Y-%m} .. {date.max():%Y-%m}  "
              f"latest={df.value.iloc[-1]:,.1f} {s['unit']}")


if __name__ == "__main__":
    main()
