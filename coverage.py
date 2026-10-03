"""coverage.py — classify every registry metric_id by materialization status.

Joins the 112-row registry against what the warehouse actually contains
(silver series + derived metrics), plus the source_map tiers, and writes
registry_coverage.csv + prints a summary. Answers: "how far through the
registry are we, and via which source?"
"""
from __future__ import annotations
import pathlib
import pandas as pd, yaml

ROOT = pathlib.Path(__file__).resolve().parent
REG = pd.read_csv(ROOT / "registry" / "brazil_macro_data_allocation_metrics.csv")
SILVER = pd.read_parquet(ROOT / "warehouse" / "silver" / "fact_time_series.parquet")
DERIVED = pd.read_parquet(ROOT / "warehouse" / "gold" / "derived_metrics.parquet")
smap = yaml.safe_load(open(ROOT / "registry" / "source_map.yml"))

# country-level series only; company (entity) series are outside the macro registry
BR = SILVER[SILVER.entity_id == "BR"]
native_ids = set(BR[~BR.resolved_source.str.startswith("dateno")].metric_id)
wb_ids = set(BR[BR.resolved_source.str.startswith("dateno")].metric_id)
derived_ids = set(DERIVED[DERIVED.status.str.startswith("computed")].derived_metric)
tier3 = set(smap.get("tier3", {}).get("metric_ids", []))

# registry metric -> proxy/related series we DID materialize (different id/concept)
PROXY = {
    "gdp_by_sector": "gdp_agriculture/industry/services_share (WB)",
    "grain_harvest_total": "cereal_production (WB annual)",
    "gfcf": "investment_rate_gdp (WB)",
    "exports_by_product": "soy/oil/iron_ore/beef/coffee/sugar + concentration index",
    "exports_by_destination": "exports_to_china + china_export_share",
}


def classify(mid: str) -> tuple[str, str]:
    if mid in native_ids:
        src = BR.loc[BR.metric_id == mid, "resolved_source"].iloc[0]
        return "native_ingested", f"{src} (native)"
    if mid in derived_ids:
        return "derived_computed", "pipeline"
    if mid in wb_ids:
        return "dateno_ingested", "Dateno/World Bank (annual)"
    if mid in PROXY and PROXY[mid]:
        return "proxy", PROXY[mid]
    if mid in tier3:
        return "pending_tier3", "manual/geospatial/paid"
    return "pending_tier2", "native adapter not built yet"


rows = [dict(metric_id=m.metric_id, theme=m.theme, priority=m.priority,
             status=(c := classify(m.metric_id))[0], via=c[1])
        for m in REG.itertuples()]
cov = pd.DataFrame(rows)
cov.to_csv(ROOT / "registry_coverage.csv", index=False)

done = {"native_ingested", "derived_computed", "dateno_ingested", "proxy"}
n_done = cov.status.isin(done).sum()
print(f"Registry coverage: {n_done}/{len(cov)} metrics materialized "
      f"({n_done/len(cov)*100:.0f}%)\n")
print(cov.status.value_counts().to_string())
print("\nBy theme (materialized / total):")
g = cov.assign(done=cov.status.isin(done)).groupby("theme").agg(
    done=("done", "sum"), total=("done", "size"))
print(g.to_string())
print("\nStill pending (Tier-2 native adapters to build next):")
print(", ".join(sorted(cov[cov.status == "pending_tier2"].metric_id)))
