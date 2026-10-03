"""ipeadata.py — Tier-2 native adapter: IPEAData OData (open macro series).

embi_brazil : EMBI+ Brazil country-risk spread (J.P. Morgan), daily, in bps.
Series code JPM366_EMBI366. Used as the open substitute for sovereign CDS.
              DISCONTINUED: IPEA marks it "EMBI + Risco-Brasil - INATIVA" (SERSTATUS=I,
              "série interrompida por descontinuidade de fornecimento"), last obs
              2024-07-30. Checked 2026-10-03: full Metadados catalog (3,606 series)
              has no other EMBI / country-risk / CDS / JP Morgan series -> no IPEA
              replacement exists; a current spread needs another source.
brent_usd   : Brent spot (EIA via IPEA), EIA366_PBRENT366, daily US$/bbl since 2000.
              Verified 2026-10-03: last obs 2026-09-29; weekends/holidays are
              null in the feed and dropped.
gas_production : ANP12_PDGASN12, monthly. IPEA labels the unit "Barril/dia" x
              "milhões" — it is MILLION BARRELS OF OIL EQUIVALENT per day using
              ANP's 1 m³ oil = 1,000 m³ gas convention. Reconciled 2026-10-03
              against ANP producao-gas-natural-1000m3.csv: Jul-26 IPEA 1.352 x
              158.987 = 215.0 MMm³/d vs ANP (190.75 mar + 24.21 terra) = 215.0
              MMm³/d. We store it converted: value x 158.987 -> million m³/day.

The IPEAData OData endpoint ignores $top/$orderby, so we fetch the full series
and keep the most recent window in pandas. Writes canonical bronze to bronze/native/.
Run:  python3 ingest/ipeadata.py
"""
from __future__ import annotations
import sys, json, ssl, time, pathlib, urllib.request
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _checks import check_gaps  # noqa: E402
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "warehouse" / "bronze" / "native"
HDR = {"User-Agent": "brazil-macro-pipeline/1.0"}
START = "2000-01-01"

# Verified via IPEAData catalog + magnitude check. Oil is thousand-barrels/day.
# Optional 6th tuple element = multiplier applied to VALVALOR (default 1).
SERIES = {
    "embi_brazil": ("JPM366_EMBI366", "EMBI+ Brazil country risk", "market_repricing", "bps", "daily"),
    "ibovespa_level": ("GM366_IBVSP366", "Ibovespa index level", "market_repricing", "points", "daily"),
    "oil_production": ("ANP12_PDPET12", "Oil production (avg/day)", "oil_gas", "kbbl_day", "monthly"),
    "brent_usd": ("EIA366_PBRENT366", "Brent crude spot price", "oil_gas", "usd_per_bbl", "daily"),
    "gas_production": ("ANP12_PDGASN12", "Natural gas production (avg/day)", "oil_gas",
                       "mm3_day", "monthly", 158.987),
}


def fetch(code):
    url = f"http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{code}')"
    last = None
    for attempt in range(1, 5):  # IPEA occasionally resets / returns empty bodies
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=180, context=_CTX) as r:
                return json.loads(r.read())["value"]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * attempt)
    raise RuntimeError(f"{code}: {last}")


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    gap_fail = []
    for mid, (code, name, theme, unit, freq, *opt) in SERIES.items():
        mult = opt[0] if opt else 1
        try:
            rows = fetch(code)
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {mid}: {e}")
            continue
        df = pd.DataFrame(rows)
        df = df[df.VALVALOR.notna()].copy()
        df["VALVALOR"] = df.VALVALOR.astype(float) * mult
        df["date"] = df.VALDATA.str[:10]
        df = df[df.date >= START].sort_values("date")
        out = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
        for _, r in df.iterrows():
            out.append(f'{mid},"{name}",{theme},ipeadata,{freq},{r.date},{float(r.VALVALOR):.4f},{unit}')
        (NATIVE / f"{mid}.csv").write_text("\n".join(out) + "\n")
        print(f"[ok]   {mid:<14} {len(df)} obs ({df.date.min()}..{df.date.max()}) "
              f"latest={float(df.iloc[-1].VALVALOR):.2f} {unit}")
        if not check_gaps(df, mid, freq, quiet=True):
            gap_fail.append(mid)
    if gap_fail:
        sys.exit(f"[FAIL] internal gaps in: {gap_fail}")


if __name__ == "__main__":
    main()
