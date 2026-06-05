"""tesouro_bonds.py — Tier-2 native adapter: Brazilian government bond yields.

Source: Tesouro Transparente (Tesouro Direto) daily prices & rates CSV (free, public).
Builds CONSTANT-MATURITY daily yield series — for each business day, pick the bond
whose maturity is closest to the target tenor:
  gov_real_yield_10y    Tesouro IPCA+ (NTN-B)   ~10y  -> real sovereign yield
  gov_nominal_yield_5y  Tesouro Prefixado (LTN) ~5y   -> nominal sovereign yield

These are the core "gov bonds" gauges for the market_repricing theme (carry, term
premium, real-rate level) and complement the Selic policy rate.

Writes canonical bronze to bronze/native/. Run:  python3 ingest/tesouro_bonds.py
"""
from __future__ import annotations
import ssl, io, pathlib, urllib.request
import pandas as pd
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "warehouse" / "bronze" / "native"
CSV_URL = ("https://www.tesourotransparente.gov.br/ckan/dataset/"
           "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
           "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
HDR = {"User-Agent": "brazil-macro-pipeline/1.0"}

# metric_id -> (Tipo Titulo, target tenor years, name)
TARGETS = {
    "gov_real_yield_10y": ("Tesouro IPCA+", 10.0, "Gov real yield ~10y (NTN-B)"),
    "gov_nominal_yield_5y": ("Tesouro Prefixado", 5.0, "Gov nominal yield ~5y (LTN)"),
}
START = "2015-01-01"  # keep recent ~decade


def load() -> pd.DataFrame:
    req = urllib.request.Request(CSV_URL, headers=HDR)
    with urllib.request.urlopen(req, timeout=120, context=_CTX) as r:
        raw = r.read()
    for enc in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(raw), sep=";", decimal=",", encoding=enc)
            break
        except Exception:  # noqa: BLE001
            continue
    df.columns = [c.strip() for c in df.columns]
    df["base"] = pd.to_datetime(df["Data Base"], format="%d/%m/%Y", errors="coerce")
    df["mat"] = pd.to_datetime(df["Data Vencimento"], format="%d/%m/%Y", errors="coerce")
    df["yield"] = pd.to_numeric(df["Taxa Compra Manha"], errors="coerce")
    return df.dropna(subset=["base", "mat", "yield"])


def constant_maturity(df, tipo, tenor):
    s = df[(df["Tipo Titulo"] == tipo) & (df["base"] >= START)].copy()
    s["tenor"] = (s["mat"] - s["base"]).dt.days / 365.25
    s["gap"] = (s["tenor"] - tenor).abs()
    s = s[s["gap"] <= 3.5]                       # only accept bonds near the target tenor
    s = s.sort_values(["base", "gap"]).groupby("base", as_index=False).first()
    return s[["base", "yield"]]


def write(metric_id, name, s):
    lines = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
    for _, r in s.sort_values("base").iterrows():
        lines.append(f'{metric_id},"{name}",market_repricing,tesouro_direto,daily,'
                     f'{r.base.strftime("%Y-%m-%d")},{r["yield"]:.4f},pct_pa')
    (NATIVE / f"{metric_id}.csv").write_text("\n".join(lines) + "\n")
    print(f"[ok]   {metric_id:<20} {len(s)} obs ({s.base.min().date()}..{s.base.max().date()})")


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    df = load()
    print(f"loaded {len(df):,} bond price rows; titles: {sorted(df['Tipo Titulo'].unique())}")
    for mid, (tipo, tenor, name) in TARGETS.items():
        cm = constant_maturity(df, tipo, tenor)
        if cm.empty:
            print(f"[warn] {mid}: no bonds within tenor band"); continue
        write(mid, name, cm)


if __name__ == "__main__":
    main()
