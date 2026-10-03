"""ibge_sidra.py — Tier-2 native adapter: IBGE SIDRA (PNAD Contínua, PMC).

National monthly series:
  real_average_income   t6390 v5933            (R$, real)            PNAD, rolling quarter
  employed_population   t6320 v4090            (thousand persons)    PNAD, rolling quarter
  unemployment_rate     t6381 v4099            (% of labor force)    PNAD, rolling quarter
  retail_sales_volume   t8880 v7170 c11046/56734 (index 2022=100, s.a.) PMC, monthly
-> enables derived real_wage_bill = employed * real income.

National annual series (theme health):
  adult_smoking_prevalence  t4173 v4163 c1/6795 c2/6794  (% of adults 18+ current tobacco smokers) PNS 2013, 2019
  population                t7358 v606 c2/6794 c287/100362 c1933/all  (persons) IBGE projection, 2018 revision
Verified 2026-10-03: smoking 14.7% (2013) -> 12.6% (2019); population 2010 = 194.9M, 2023 = 216.3M.
Gotcha (t7358): the SIDRA *period* is the projection revision (2018); the calendar year is
classification c1933 (D6), 2000-2060 — years after the current year are dropped (pure projection).
Note the 2018 projection runs ~6% above the 2022 Census count (203.1M).

Verified 2026-10-03: unemployment 5.4% (abr-jun 2026) / 5.3% (mai-jul) — matches the
"record-low 5.3%" headline; PMC metadata via servicodados.ibge.gov.br/api/v3/agregados/8880.

SIDRA period code is YYYYMM (for PNAD: ending month of the rolling quarter).
Writes canonical bronze to bronze/native/. Run:  python3 ingest/ibge_sidra.py
"""
from __future__ import annotations
import sys, pathlib, datetime
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_json, write_bronze, NATIVE  # noqa: E402

# metric_id -> (table, variable, classification filter, name, theme, unit[, freq, year_dim])
# freq defaults to monthly (period YYYYMM); annual reads the year from period D3C or `year_dim`.
SERIES = {
    "real_average_income": (6390, 5933, "", "Real average labor income", "labor", "brl_real"),
    "employed_population": (6320, 4090, "", "Employed population", "labor", "thousand_persons"),
    "unemployment_rate": (6381, 4099, "", "Unemployment rate (PNAD)", "labor", "pct"),
    "retail_sales_volume": (8880, 7170, "/c11046/56734",
                            "Retail sales volume (PMC, s.a.)", "domestic_demand", "index_2022_100"),
    "adult_smoking_prevalence": (4173, 4163, "/c1/6795/c2/6794",
                                 "Adult (18+) current tobacco smokers (PNS)", "health", "pct", "annual"),
    "population": (7358, 606, "/c2/6794/c287/100362/c1933/all",
                   "Resident population (IBGE projection, 2018 rev.)", "health", "persons", "annual", "D6N"),
}


def fetch(table, var, cls):
    url = f"https://apisidra.ibge.gov.br/values/t/{table}/n1/all/v/{var}/p/all{cls}"
    return get_json(url)[1:]  # drop header row


def main():
    for mid, (table, var, cls, name, theme, unit, *opt) in SERIES.items():
        freq = opt[0] if opt else "monthly"
        year_dim = opt[1] if len(opt) > 1 else "D3C"
        recs = []
        for r in fetch(table, var, cls):
            code, v = r.get("D3C", ""), r.get("V")
            try:
                val = float(v)
            except (TypeError, ValueError):
                continue  # '...', '-' etc.
            if freq == "annual":
                y = r.get(year_dim, "")
                if len(y) == 4 and int(y) < datetime.date.today().year:   # projections for the current year onward are not data
                    recs.append(dict(date=f"{y}-12-31", value=val))  # annual convention: year end
            elif len(code) == 6:
                recs.append(dict(date=f"{code[:4]}-{code[4:6]}-01", value=val))
        df = pd.DataFrame(recs).assign(metric_id=mid, metric_name=name, theme=theme,
                                       source_id="ibge_sidra", freq=freq, unit=unit)
        n = write_bronze(df, NATIVE / f"{mid}.csv")
        if n:
            print(f"[ok]   {mid:<22} {n} obs ({df.date.min()}..{df.date.max()}) "
                  f"latest={df.sort_values('date').value.iloc[-1]}")


if __name__ == "__main__":
    main()
