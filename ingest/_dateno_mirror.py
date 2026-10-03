"""_dateno_mirror.py — shared writer for the Dateno-mirror adapters.

Dateno's statsdb has two namespaces, `wb` (World Bank) and `ilostat` (ILO), and
both mirror public upstreams. Our Dateno key is capped at 200 requests/day, so
`worldbank_bulk.py` and `ilostat_bulk.py` pull the SAME data straight from the
upstreams and land it here in exactly the schema `dateno_bulk.py` writes:

    warehouse/bronze/dateno/observations.parquet   (OBS_COLS)
    warehouse/bronze/dateno/catalog.parquet        (CAT_COLS)

so the platform treats Dateno-native and upstream-mirrored rows as one source family.

Merge rules (`merge_into_dateno`):
  * Dateno-native rows (pulled through the Dateno API, e.g. the 22 tier-1 wb series)
    always win: dedupe key is (ns, ts_id, date, classif1, classif2), native first.
    Mirror rows only add dates/dims the native series lacks.
  * A series is "mirror-produced" when its catalog `source` contains MIRROR_TAG.
    On rerun, all previous mirror rows for that namespace are dropped and replaced
    (idempotent). Native catalog rows keep `source`, but empty metadata fields
    (name, topic, unit, definition, database, ...) are filled from the mirror.
  * Catalog stats (freq, first/last_date, n_obs, n_dims, last_value) are recomputed
    from the merged observations for every touched series.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import BRONZE  # noqa: E402

OUT = BRONZE / "dateno"
MIRROR_TAG = "mirrored in Dateno"
OBS_COLS = ["ns", "ts_id", "indicator_id", "date", "freq", "value", "unit", "obs_status",
            "classif1", "classif2", "obs_source"]
CAT_COLS = ["ns", "ts_id", "indicator_id", "table", "name", "indicator_name", "source_id",
            "database", "source", "topic", "unit", "definition", "periodicity", "license",
            "last_update", "freq", "first_date", "last_date", "n_obs", "n_dims", "last_value"]
CAT_STR = CAT_COLS[:16]
OBS_STR = ["ns", "ts_id", "indicator_id", "freq", "unit", "obs_status", "classif1", "classif2",
           "obs_source"]
STATS = ["freq", "first_date", "last_date", "n_obs", "n_dims", "last_value"]

# ILO "total" codes: SEX_T, AGE_YTHADULT_YGE15, ECO_SECTOR_TOTAL, AGE_AGGREGATE_TOTAL, ...
_TOTAL = re.compile(r"(_T|TOTAL|_TOT|AGE_YTHADULT_YGE15|AGE_10YRBANDS_TOTAL|AGE_5YRBANDS_TOTAL)$")


def _is_total(code) -> bool:
    if code is None or (isinstance(code, float) and pd.isna(code)) or code == "":
        return True
    return all(bool(_TOTAL.search(p)) for p in str(code).split("|"))


def headline_mask(obs: pd.DataFrame) -> pd.Series:
    """True for the headline row(s) of each series: no disaggregation (wb) or every
    ILO dimension at its total (SEX_T, *_TOTAL, AGE_YTHADULT_YGE15). Series with no
    all-total combination fall back to their first (classif1, classif2) combination."""
    c1 = obs["classif1"].astype(object).where(obs["classif1"].notna(), "")
    c2 = obs["classif2"].astype(object).where(obs["classif2"].notna(), "")
    tot = pd.Series([_is_total(a) and _is_total(b) for a, b in zip(c1, c2)], index=obs.index)
    has_tot = tot.groupby(obs["ts_id"]).transform("any")
    key = c1 + "\x00" + c2
    first_key = key.groupby(obs["ts_id"]).transform("min")
    return tot | (~has_tot & (key == first_key))


def series_stats(obs: pd.DataFrame) -> pd.DataFrame:
    """Per (ns, ts_id): freq, first/last date, n_obs, n_dims, last_value (headline)."""
    if obs.empty:
        return pd.DataFrame(columns=["ns", "ts_id"] + STATS)
    g = obs.groupby(["ns", "ts_id"], sort=False)
    st = pd.DataFrame({
        "freq": g["freq"].agg(lambda s: s.mode().iloc[0]),
        "first_date": g["date"].min(),
        "last_date": g["date"].max(),
        "n_obs": g.size(),
    })
    dims = obs[["ns", "ts_id", "classif1", "classif2"]].fillna("").drop_duplicates()
    st["n_dims"] = dims.groupby(["ns", "ts_id"]).size()
    h = obs[headline_mask(obs)].sort_values("date")
    st["last_value"] = h.groupby(["ns", "ts_id"])["value"].last()
    return st.reset_index()


def _norm_obs(obs: pd.DataFrame) -> pd.DataFrame:
    obs = obs[OBS_COLS].copy()
    for c in OBS_STR:
        obs[c] = obs[c].astype(object).where(obs[c].notna() & (obs[c].astype(str) != ""), None)
    obs["value"] = pd.to_numeric(obs["value"], errors="coerce").astype(float)
    obs["date"] = pd.to_datetime(obs["date"]).dt.date
    return obs[obs["value"].notna()]


def _schema(cols, types):
    import pyarrow as pa
    return pa.schema([(c, types.get(c, pa.large_string())) for c in cols])


def _types():
    import pyarrow as pa
    return {"date": pa.date32(), "first_date": pa.date32(), "last_date": pa.date32(),
            "value": pa.float64(), "last_value": pa.float64(), "n_obs": pa.int64(),
            "n_dims": pa.int64()}


def _write(df: pd.DataFrame, path: Path, cols: list[str]) -> None:
    """Write with the exact Arrow types dateno_bulk.py produces (large_string, date32,
    float64, int64) -- pandas would otherwise emit `string` or `null` for all-None columns."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    sch = _schema(cols, _types())
    data = {}
    for f in sch:
        v = df[f.name]
        if pa.types.is_large_string(f.type):
            v = v.astype(object).where(v.notna(), None)
        data[f.name] = pa.array(v.tolist() if f.type != pa.float64() else v.to_numpy(), type=f.type)
    pq.write_table(pa.table(data, schema=sch), path, compression="zstd")


def merge_into_dateno(ns: str, obs_new: pd.DataFrame, cat_new: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge one namespace's mirror pull into the two Dateno parquets (see module doc)."""
    obs_new, cat_new = _norm_obs(obs_new), cat_new.copy()
    op, cp = OUT / "observations.parquet", OUT / "catalog.parquet"
    obs_old = pd.read_parquet(op) if op.exists() else pd.DataFrame(columns=OBS_COLS)
    cat_old = pd.read_parquet(cp) if cp.exists() else pd.DataFrame(columns=CAT_COLS)
    obs_old = _norm_obs(obs_old) if len(obs_old) else obs_old

    # previous mirror output for this ns -> drop (rerun is a full replace)
    src = cat_old["source"].astype(object).fillna("")
    old_mirror = cat_old[(cat_old["ns"] == ns) & src.str.contains(MIRROR_TAG, regex=False)]
    mirror_ids = set(old_mirror["ts_id"])
    native_cat = cat_old[~cat_old["ts_id"].isin(mirror_ids) | (cat_old["ns"] != ns)]
    keep = ~((obs_old["ns"] == ns) & obs_old["ts_id"].isin(mirror_ids))
    # mirror rows that were appended to native series (e.g. 2024-25 for tier-1)
    osrc = obs_old["obs_source"].astype(object).fillna("")
    keep &= ~((obs_old["ns"] == ns) & osrc.str.contains(MIRROR_TAG, regex=False))
    obs_native = obs_old[keep]

    key = ["ns", "ts_id", "date", "classif1", "classif2"]
    obs = pd.concat([obs_native.assign(_p=0), obs_new.assign(_p=1)], ignore_index=True)
    k = obs[key].astype(str)
    obs = obs[~k.duplicated(keep="first")].drop(columns="_p")
    obs = obs.sort_values(["ns", "ts_id", "classif1", "classif2", "date"], na_position="first",
                          ignore_index=True)

    # catalog: native rows keep identity/source, fill gaps from mirror metadata
    native_ids = set(zip(native_cat["ns"], native_cat["ts_id"]))
    cn = cat_new.set_index(["ns", "ts_id"])
    nat = native_cat.copy()
    for i, r in nat.iterrows():
        kk = (r["ns"], r["ts_id"])
        if kk in cn.index:
            m = cn.loc[kk]
            for c in CAT_STR:
                if c in ("ns", "ts_id", "source") or c in STATS:
                    continue
                if pd.isna(r[c]) or r[c] == "":
                    nat.at[i, c] = m.get(c)
            if pd.isna(r["source"]):
                nat.at[i, "source"] = f"Dateno statsdb API ({ns}); metadata filled from upstream mirror"
    new_only = cat_new[[(a, b) not in native_ids for a, b in zip(cat_new["ns"], cat_new["ts_id"])]]
    cat = pd.concat([nat, new_only], ignore_index=True)

    st = series_stats(obs).set_index(["ns", "ts_id"])
    cat = cat.set_index(["ns", "ts_id"])
    cat = cat[cat.index.isin(st.index)]  # drop all-null series
    for c in STATS:
        cat[c] = st.loc[cat.index, c].values
    cat = cat.reset_index()[CAT_COLS]
    for c in CAT_STR:
        cat[c] = cat[c].astype(object).where(cat[c].notna(), None).astype("string")
    cat["n_obs"] = cat["n_obs"].astype("int64")
    cat["n_dims"] = cat["n_dims"].astype("int64")
    cat["last_value"] = cat["last_value"].astype(float)
    cat = cat.sort_values(["ns", "ts_id"], ignore_index=True)

    OUT.mkdir(parents=True, exist_ok=True)
    tmp_o, tmp_c = op.with_suffix(".tmp"), cp.with_suffix(".tmp")
    _write(obs, tmp_o, OBS_COLS)
    _write(cat, tmp_c, CAT_COLS)
    tmp_o.replace(op)
    tmp_c.replace(cp)
    return obs, cat


def summary(obs: pd.DataFrame, cat: pd.DataFrame, ns: str, t0: float) -> None:
    import time
    o, c = obs[obs.ns == ns], cat[cat.ns == ns]
    print(f"\n================ {ns} summary (whole namespace after merge) ================")
    print(f"series: {len(c):,}   observations: {len(o):,}")
    print("by freq (series):", c["freq"].value_counts().to_dict())
    print("by freq (obs):   ", o["freq"].value_counts().to_dict())
    db = c.groupby(c["database"].fillna("?")).agg(series=("ts_id", "size"), obs=("n_obs", "sum"))
    print("by database:\n" + db.sort_values("obs", ascending=False).head(40).to_string())
    top = c["topic"].fillna("?").str.split(":").str[0].str.strip()
    print("top topics (series):", top.value_counts().head(15).to_dict())
    for f in ("observations.parquet", "catalog.parquet"):
        print(f"{f}: {(OUT / f).stat().st_size / 1e6:.2f} MB (all namespaces)")
    print(f"totals all ns: series {len(cat):,}, obs {len(obs):,}")
    print(f"runtime: {time.time() - t0:.1f}s")


def tier1_check(obs: pd.DataFrame) -> None:
    """The 22 tier-1 series must equal warehouse/bronze/<ts_id>.csv on every CSV date."""
    import yaml
    from _http import ROOT
    t1 = yaml.safe_load((ROOT / "registry" / "source_map.yml").read_text()).get("tier1", {})
    ok, extra = 0, 0
    for metric, v in t1.items():
        ts = v["ts_id"]
        ref = pd.read_csv(BRONZE / f"{ts}.csv").dropna(subset=["value"])
        ref = dict(zip(ref["date"].astype(str).str[:4], ref["value"].astype(float)))
        got = obs[obs.ts_id == ts]
        mine = dict(zip([str(d.year) for d in got["date"]], got["value"]))
        diff = [y for y in ref if y not in mine or abs(ref[y] - mine[y]) > 1e-9 * max(1, abs(ref[y]))]
        extra += len(set(mine) - set(ref))
        if diff:
            print(f"  [DIFF] {metric} {ts}: {len(diff)} dates differ")
        else:
            ok += 1
    print(f"  tier-1: {ok}/{len(t1)} identical to bronze CSVs on all their dates "
          f"(+{extra} newer obs appended from the mirror)")
