"""imf_fiscal_monitor.py — Tier-2 adapter: IMF Fiscal Monitor, Brazil's general government.

General government = federal + states + municipalities. This is the basis of the usual
"Brazil collects ~40% of GDP" figure. The other fiscal series in the warehouse measure
something narrower or different:
  * primary_balance_gdp / nominal_deficit_gdp (central bank, NFSP): consolidated public
    sector incl. state-owned firms, monthly, below-the-line;
  * wb/GC.* (World Bank): central government only (~26% of GDP revenue);
  * cg_* (tesouro_rtn.py): central government, monthly, above-the-line.

Also writes emerging-market PEER MEDIANS for revenue and expenditure so "is Brazil's tax
take high?" can be answered from the warehouse. Peer panel = the emerging-market G20
members other than Brazil (fixed, not hand-picked): Argentina, China, India, Indonesia,
Mexico, Russia, Saudi Arabia, South Africa, Türkiye. The median is taken over the peers
with a value in that year (n is logged).

Source: IMF DataMapper API, dataset FM (Fiscal Monitor; new vintage each April and
October), keyless JSON:
    GET https://www.imf.org/external/datamapper/api/v1/<indicator>
    -> {"values": {"<indicator>": {"<ISO3>": {"<year>": value}}}, "api": {...}}
Gotchas (checked 2026-11-11 against the October 2026 vintage):
  * Country path filters (/<indicator>/BRA) are ignored for FM indicators: the server
    returns every country (~250 KB), so we fetch once and filter locally.
  * A browser User-Agent gets 403 from the CDN; the pipeline UA works.
  * Values run to the end of the forecast horizon (+5 years). Only years up to the
    current one are kept; the current year is the IMF's estimate, not an outturn.
  * The cyclically adjusted primary balance is in % of POTENTIAL GDP.
Magnitude check (Oct-2026 vintage): Brazil revenue 39.4% of GDP (2024), 40.5% (2026e);
primary balance -0.3% (2024) vs central bank NFSP -0.4% (Dec-2024) — consistent.

Writes warehouse/bronze/native/<metric_id>.csv. Run:  python3 ingest/imf_fiscal_monitor.py
"""
from __future__ import annotations
import sys, pathlib, datetime as dt, statistics
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_json, write_bronze, NATIVE  # noqa: E402
from _checks import check_gaps  # noqa: E402

API = "https://www.imf.org/external/datamapper/api/v1/"
COUNTRY = "BRA"
PEERS = ["ARG", "CHN", "IND", "IDN", "MEX", "RUS", "SAU", "ZAF", "TUR"]
START, END = 2000, dt.date.today().year

# metric_id -> (IMF indicator, title, unit, write peer median?)
SERIES = {
    "gg_revenue_gdp": ("GGR_G01_GDP_PT", "General government revenue / GDP (IMF)", "pct_gdp", True),
    "gg_expenditure_gdp": ("G_X_G01_GDP_PT", "General government expenditure / GDP (IMF)", "pct_gdp", True),
    "gg_primary_balance_gdp": ("GGXONLB_G01_GDP_PT",
                               "General government primary balance / GDP (IMF, +=surplus)", "pct_gdp", False),
    "gg_overall_balance_gdp": ("GGXCNL_G01_GDP_PT",
                               "General government overall balance / GDP (IMF, +=surplus)", "pct_gdp", False),
    "gg_cyc_adj_primary_balance_gdp": ("GGCBP_G01_PGDP_PT",
                                       "General government cyclically adjusted primary balance (IMF, % potential GDP)",
                                       "pct_potential_gdp", False),
}
PEER_TITLE = {"gg_revenue_gdp": "General government revenue / GDP, emerging G20 median ex-Brazil (IMF)",
              "gg_expenditure_gdp": "General government expenditure / GDP, emerging G20 median ex-Brazil (IMF)"}


def fetch(indicator: str) -> dict:
    d = get_json(API + indicator, timeout=120)
    vals = d.get("values", {}).get(indicator)
    if not vals:
        raise RuntimeError(f"{indicator}: no 'values' in response (keys: {list(d)[:5]})")
    return vals


def frame(metric_id, title, unit, points: dict[int, float]) -> pd.DataFrame:
    rows = [(f"{y}-12-31", v) for y, v in sorted(points.items()) if START <= y <= END and v is not None]
    return pd.DataFrame({"metric_id": metric_id, "metric_name": title, "theme": "fiscal",
                         "source_id": "imf_fm", "freq": "annual",
                         "date": [r[0] for r in rows], "value": [r[1] for r in rows], "unit": unit})


def main() -> int:
    ok = True
    for mid, (ind, title, unit, peer) in SERIES.items():
        try:
            vals = fetch(ind)
        except Exception as e:  # noqa: BLE001 — one failed indicator must not stop the rest
            print(f"[fail] {mid}: {e}"); ok = False; continue
        br = {int(y): float(v) for y, v in vals.get(COUNTRY, {}).items()}
        df = frame(mid, title, unit, br)
        n = write_bronze(df, NATIVE / f"{mid}.csv")
        if n:
            print(f"[ok]   {mid:<32} {n} obs ({df.date.min()}..{df.date.max()}), last {df.value.iloc[-1]:.1f}")
            ok &= check_gaps(df, mid, "annual")
        if peer:
            by_year: dict[int, list[float]] = {}
            for c in PEERS:
                for y, v in vals.get(c, {}).items():
                    by_year.setdefault(int(y), []).append(float(v))
            med = {y: statistics.median(v) for y, v in by_year.items() if len(v) >= 6}
            pid = f"{mid}_em_peers"
            pdf = frame(pid, PEER_TITLE[mid], unit, med)
            n = write_bronze(pdf, NATIVE / f"{pid}.csv")
            if n:
                last = max(y for y in med if y <= END)
                print(f"[ok]   {pid:<32} {n} obs, last {med[last]:.1f} (n={len(by_year[last])} peers in {last})")
                ok &= check_gaps(pdf, pid, "annual")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
