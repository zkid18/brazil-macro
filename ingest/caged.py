"""caged.py — Novo CAGED monthly net formal job creation (saldo) via IPEAData.

Source: IPEAData OData v4, series CAGED12_SALDON12
    "Empregados - saldo - sem ajuste - novo Caged" (Mensal, unit Pessoa,
    fonte Min. Economia/SEPRT/Novo Caged), Jan-2020 onward.
    http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='CAGED12_SALDON12')

Why not BCB SGS: SGS 28763 ("New Caged - Total") is the formal-employment STOCK
(48.2 mn, Aug-26), and 28784 is the same stock seasonally adjusted — levels, not
the saldo concept. The MTE PDET microdata (FTP 7z per month) is far heavier.

Gotchas: IPEAData resets connections intermittently (retries in _http); the
`contains()` catalog filter is unreliable — the code was found via direct
Metadados('CAGED12_SALDON12') lookup. Not seasonally adjusted (December is
always strongly negative).

Verification (2026-10-03): calendar-year sums 2022 = 2,011,366, 2023 = 1,478,340,
2024 = 1,676,514 — consistent with MTE headline annual saldos; Aug-26 = +165,827.

Run:  python3 ingest/caged.py
"""
from __future__ import annotations
import sys, pathlib
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_json, write_bronze, NATIVE  # noqa: E402

BASE = "http://www.ipeadata.gov.br/api/odata4"
SERIES = {
    "caged_net_hires": dict(code="CAGED12_SALDON12", freq="monthly", unit="jobs", theme="labor",
                            metric_name="Novo CAGED net formal job creation (saldo, NSA)",
                            source_id="ipeadata"),
}


def main():
    ok = 0
    for metric_id, s in SERIES.items():
        try:
            rows = get_json(f"{BASE}/ValoresSerie(SERCODIGO='{s['code']}')",
                            timeout=120, retries=6)["value"]
            df = pd.DataFrame({"date": pd.to_datetime([r["VALDATA"][:10] for r in rows]),
                               "value": [r["VALVALOR"] for r in rows]})
            df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()
            for k in ("metric_name", "theme", "source_id", "freq", "unit"):
                df[k] = s[k]
            df["metric_id"] = metric_id
            n = write_bronze(df, NATIVE / f"{metric_id}.csv")
            if n:
                ok += 1
                last = df.dropna().iloc[-1]
                print(f"[ok]   {metric_id:<18} {s['code']} {n} obs  {df.date.min():%Y-%m} .. "
                      f"{df.date.max():%Y-%m}  latest={last.value:,.0f}")
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {metric_id} {s['code']} :: {e}")
    print(f"\nPulled {ok}/{len(SERIES)} -> {NATIVE}")


if __name__ == "__main__":
    main()
