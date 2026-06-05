"""ipeadata.py — Tier-2 native adapter: IPEAData OData (open macro series).

embi_brazil : EMBI+ Brazil country-risk spread (J.P. Morgan), daily, in bps.
Series code JPM366_EMBI366. Used as the open substitute for sovereign CDS.

The IPEAData OData endpoint ignores $top/$orderby, so we fetch the full series
and keep the most recent window in pandas. Writes canonical bronze to bronze/native/.
Run:  python3 ingest/ipeadata.py
"""
from __future__ import annotations
import json, ssl, pathlib, urllib.request
import pandas as pd
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    _CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "warehouse" / "bronze" / "native"
HDR = {"User-Agent": "brazil-macro-pipeline/1.0"}
START = "2000-01-01"

# Verified via IPEAData catalog + magnitude check. Gas (ANP12_PDGASN12) skipped:
# its m³ scale was ambiguous on probe. Oil is thousand-barrels/day.
SERIES = {
    "embi_brazil": ("JPM366_EMBI366", "EMBI+ Brazil country risk", "market_repricing", "bps", "daily"),
    "ibovespa_level": ("GM366_IBVSP366", "Ibovespa index level", "market_repricing", "points", "daily"),
    "oil_production": ("ANP12_PDPET12", "Oil production (avg/day)", "oil_gas", "kbbl_day", "monthly"),
}


def fetch(code):
    url = f"http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{code}')"
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=90, context=_CTX) as r:
        return json.loads(r.read())["value"]


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    for mid, (code, name, theme, unit, freq) in SERIES.items():
        rows = fetch(code)
        df = pd.DataFrame(rows)
        df = df[df.VALVALOR.notna()].copy()
        df["date"] = df.VALDATA.str[:10]
        df = df[df.date >= START].sort_values("date")
        out = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
        for _, r in df.iterrows():
            out.append(f'{mid},"{name}",{theme},ipeadata,{freq},{r.date},{float(r.VALVALOR):.4f},{unit}')
        (NATIVE / f"{mid}.csv").write_text("\n".join(out) + "\n")
        print(f"[ok]   {mid:<14} {len(df)} obs ({df.date.min()}..{df.date.max()}) "
              f"latest={float(df.iloc[-1].VALVALOR):.0f}{unit}")


if __name__ == "__main__":
    main()
