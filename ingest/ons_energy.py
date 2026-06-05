"""ons_energy.py — Tier-2 native adapter: ONS (grid operator) open data.

Two CKAN datasets, per-year parquet, national (SIN) daily aggregates:
  balanco-energia-subsistema  -> generation by source (hydro/thermal/wind/solar) + load
  ear-diario-por-subsistema   -> stored hydro energy (EAR) % of max

Emits daily series (national):
  electricity_generation_by_source (total MWmed), hydro/wind_solar/thermal_generation_share,
  thermal_dispatch_mwh, electricity_load, stored_energy_ear.
hydro_stress_index is derived downstream (low EAR + high thermal share).

Run:  python3 ingest/ons_energy.py
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
BAL = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/balanco_energia_subsistema_ho/BALANCO_ENERGIA_SUBSISTEMA_{y}.parquet"
EAR = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/ear_subsistema_di/EAR_DIARIO_SUBSISTEMA_{y}.parquet"
YEARS = range(2015, 2027)
HDR = {"User-Agent": "brazil-macro-pipeline/1.0"}


def get_parquet(url):
    req = urllib.request.Request(url, headers=HDR)
    return pd.read_parquet(io.BytesIO(urllib.request.urlopen(req, timeout=120, context=_CTX).read()))


def num(col):  # year files vary: some store numbers as strings w/ comma decimals
    return pd.to_numeric(col.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def load_years(tmpl):
    frames = []
    for y in YEARS:
        try:
            frames.append(get_parquet(tmpl.format(y=y)))
        except Exception as e:  # noqa: BLE001 — skip missing/failed years
            print(f"  [skip] {y}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def write(metric_id, name, theme, unit, s):
    s = s.dropna().sort_index()
    lines = ["metric_id,metric_name,theme,source_id,freq,date,value,unit"]
    for d, v in s.items():
        lines.append(f'{metric_id},"{name}",{theme},ons_open_data,daily,{d},{v:.4f},{unit}')
    (NATIVE / f"{metric_id}.csv").write_text("\n".join(lines) + "\n")
    print(f"[ok]   {metric_id:<32} {len(s)} obs ({s.index.min()}..{s.index.max()})")


def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    print("downloading ONS balanco (generation)…")
    bal = load_years(BAL)
    sin = bal[bal.id_subsistema == "SIN"].copy()
    sin["date"] = pd.to_datetime(sin.din_instante).dt.strftime("%Y-%m-%d")
    for c in ["val_gerhidraulica", "val_gertermica", "val_gereolica", "val_gersolar", "val_carga"]:
        sin[c] = num(sin[c])
    g = sin.groupby("date").agg(
        h=("val_gerhidraulica", "mean"), t=("val_gertermica", "mean"),
        e=("val_gereolica", "mean"), s=("val_gersolar", "mean"),
        load=("val_carga", "mean")).dropna(how="all")
    tot = (g.h + g.t + g.e + g.s)
    write("electricity_generation_by_source", "Electricity generation, total (SIN)",
          "energy_water", "mwmed", tot)
    write("hydro_generation_share", "Hydro generation share", "energy_water", "pct", g.h / tot * 100)
    write("wind_solar_generation_share", "Wind + solar generation share", "energy_water",
          "pct", (g.e + g.s) / tot * 100)
    write("thermal_generation_share", "Thermal generation share", "energy_water",
          "pct", g.t / tot * 100)
    write("thermal_dispatch_mwh", "Thermal dispatch (generation)", "energy_water", "mwmed", g.t)
    write("electricity_load", "Electricity load (SIN)", "energy_water", "mwmed", g.load)

    print("downloading ONS EAR (stored energy)…")
    ear = load_years(EAR)
    ear["mwmes"] = num(ear.ear_verif_subsistema_mwmes)
    ear["maxv"] = num(ear.ear_max_subsistema)
    # national EAR% = sum(verified MWmes) / sum(max) across subsystems, per day
    ed = ear.groupby("ear_data").apply(
        lambda x: x.mwmes.sum() / x.maxv.sum() * 100 if x.maxv.sum() else None,
        include_groups=False)
    ed.index = pd.to_datetime(ed.index).strftime("%Y-%m-%d")
    write("stored_energy_ear", "Stored energy / EAR (national %)", "energy_water", "pct", ed)


if __name__ == "__main__":
    main()
