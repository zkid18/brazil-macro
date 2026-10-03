"""bcb_sgs.py — Tier-2 native adapter: Banco Central do Brasil SGS time series.

Transport: the legacy SGS SOAP service (the JSON API host `api.bcb.gov.br` is
gone — NXDOMAIN at the authoritative DNS since 2026):
    POST https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS
    WSDL https://www3.bcb.gov.br/sgspub/JSP/sgsgeral/FachadaWSSGS.wsdl
Operations used:
    getValoresSeriesXML(in0=long[] codes, in1="dd/MM/yyyy", in2="dd/MM/yyyy")
        -> escaped XML string <SERIES><SERIE ID='code'><ITEM><DATA>..</DATA><VALOR>..</VALOR>
    getUltimoValorVO(in0=long code) -> metadata (name, unit, periodicity, source, last value)

Gotchas:
  * SOAP 1.1 rpc/encoded (Apache Axis 1.2). A `SOAPAction` header MUST be present
    (empty string is fine) or the server returns the WSDL / a fault.
  * The series payload is an XML document escaped inside <getValoresSeriesXMLReturn>
    (ISO-8859-1 declared); parse the outer envelope, then parse the inner string.
  * Dates are UNPADDED: daily `d/M/yyyy`, monthly `M/yyyy` (monthly -> 1st of month).
  * Empty <VALOR/> rows (weekends for daily series) are dropped.
  * Many codes per call work; a single bad code faults the whole batch, so main()
    falls back to one-call-per-code if a batch fails.
  * Daily ranges are capped at ~10 years by BCB; monthly from 2000.

Verification (2026-10-03, every code checked with getUltimoValorVO name/unit/
periodicity + magnitude vs known reality; see `python3 ingest/bcb_sgs.py --meta`):
  432 Selic target 13.75 % a.a. (2026-10-02) · 1 BRL/USD ~5.1 · 13621 reserves US$ mn
  10844 IPCA Services (% m/m) · 4449 IPCA Administered prices (% m/m)
  21379 IPCA diffusion index (%, ~50-70) · 22701 Current account (US$ mn, monthly flow)
  22708/22709 BoP goods exports/imports (US$ mn, monthly ~25-30k / ~20-25k)
  1373 Anfavea vehicle production (units ~200-250k/month; 246,015 Jun-26)
  29034 household debt service ratio SA (% income, 28.72 Jul-26)
  7384-7387 Fenabrave dealer sales by segment (summed; 279,578 Jul-26)
  4382 nominal GDP 12m sum (R$ mn, 13.34 trn Aug-26)
  Rejected: 28763 = Novo CAGED formal-employment STOCK (48.2 mn), not net hires
  (see ingest/caged.py); 29039 = IC-Br energy index, not household debt.
NFSP series follow BCB convention (positive = financing need = deficit); the
pipeline flips the sign where a *balance* is wanted. `internal` series are inputs
to derived series, not headline metrics.

Writes warehouse/bronze/native/<metric_id>.csv via _http.write_bronze.

Run:  python3 ingest/bcb_sgs.py            (pull all)
      python3 ingest/bcb_sgs.py --meta 432 1373 ...   (print metadata for codes)
"""
from __future__ import annotations
import sys, pathlib, datetime as dt, html, re
import xml.etree.ElementTree as ET
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_bytes, write_bronze, NATIVE  # noqa: E402

URL = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS"
NS = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS"
TODAY = dt.date.today()
END = TODAY.strftime("%d/%m/%Y")
# Daily history back to 2010 so "since the book (2012)" USD conversions have FX coverage.
DAILY_START = "04/01/2010"
MONTHLY_START = "01/01/2000"

# registry metric_id -> SGS series spec.
SERIES = {
    # --- policy & market (daily) ---
    "selic_target": dict(code=432, freq="daily", unit="pct_pa",
                         metric_name="Selic target rate", theme="macro_policy"),
    "brl_usd": dict(code=1, freq="daily", unit="brl_per_usd",
                    metric_name="BRL/USD official exchange rate", theme="market_repricing"),
    # --- inflation (monthly) ---
    "ipca_monthly": dict(code=433, freq="monthly", unit="pct_mom",
                         metric_name="IPCA monthly change", theme="inflation"),
    "ipca_12m": dict(code=13522, freq="monthly", unit="pct_yoy",
                     metric_name="IPCA accumulated 12 months", theme="inflation"),
    "ipca_services": dict(code=10844, freq="monthly", unit="pct_mom",
                          metric_name="IPCA services monthly change", theme="inflation"),
    "ipca_administered_prices": dict(code=4449, freq="monthly", unit="pct_mom",
                                     metric_name="IPCA administered prices monthly change",
                                     theme="inflation"),
    "inflation_diffusion": dict(code=21379, freq="monthly", unit="pct",
                                metric_name="IPCA diffusion index", theme="inflation"),
    # --- activity & credit (monthly) ---
    "ibc_br": dict(code=24363, freq="monthly", unit="index",
                   metric_name="IBC-Br monthly activity index", theme="domestic_demand"),
    "credit_gdp": dict(code=20622, freq="monthly", unit="pct_gdp",
                       metric_name="Credit to GDP", theme="domestic_demand"),
    "delinquency_rate": dict(code=21082, freq="monthly", unit="pct",
                             metric_name="Delinquency rate (credit)", theme="domestic_demand"),
    "household_debt_income": dict(code=29037, freq="monthly", unit="pct_income",
                                  metric_name="Household debt-to-income", theme="domestic_demand"),
    "household_credit_balance": dict(code=20570, freq="monthly", unit="brl_mn",
                                     metric_name="Household credit balance", theme="domestic_demand",
                                     internal=True),
    "corporate_credit_balance": dict(code=20571, freq="monthly", unit="brl_mn",
                                     metric_name="Corporate credit balance", theme="domestic_demand",
                                     internal=True),
    # 29034 = debt service / disposable income, SA, total (incl. mortgages); 28.7% Jul-26.
    # (29265 = same, NSA; 29035 ex-mortgage; 29036 principal only.)
    "household_debt_service_ratio": dict(code=29034, freq="monthly", unit="pct_income",
                                         metric_name="Household debt service ratio (SA)",
                                         theme="domestic_demand"),
    "vehicle_production": dict(code=1373, freq="monthly", unit="units",
                               metric_name="Vehicle production (Anfavea)", theme="domestic_demand"),
    # Fenabrave dealer sales = domestic registrations, fresher than Anfavea (Jul vs Jun).
    # No single total code: sum 7384 cars + 7385 light comm. + 7386 trucks + 7387 buses
    # (Jul-26 = 279,578). 1378 (Anfavea "total") includes exports — not domestic demand.
    "vehicle_sales": dict(code=(7384, 7385, 7386, 7387), freq="monthly", unit="units",
                          metric_name="Vehicle sales, dealers (Fenabrave, all segments)",
                          theme="domestic_demand"),
    # --- fiscal (monthly) ---
    "gdp_nominal_12m_brl": dict(code=4382, freq="monthly", unit="brl_mn",
                                metric_name="Nominal GDP, 12-month sum (R$ mn)", theme="fiscal"),
    "gross_public_debt_gdp": dict(code=13762, freq="monthly", unit="pct_gdp",
                                  metric_name="Gross general govt debt / GDP", theme="fiscal"),
    "net_public_debt_gdp": dict(code=4503, freq="monthly", unit="pct_gdp",
                                metric_name="Net public debt / GDP", theme="fiscal"),
    "nominal_deficit_gdp": dict(code=5727, freq="monthly", unit="pct_gdp_nfsp",
                                metric_name="Nominal deficit / GDP (NFSP, +=deficit)", theme="fiscal"),
    "primary_result_nfsp": dict(code=5793, freq="monthly", unit="pct_gdp_nfsp",
                                metric_name="Primary result / GDP (NFSP, +=deficit)", theme="fiscal",
                                internal=True),
    # --- external ---
    "fx_reserves": dict(code=13621, freq="daily", unit="usd_mn",
                        metric_name="International reserves", theme="external_sector"),
    "current_account_usd": dict(code=22701, freq="monthly", unit="usd_mn",
                                metric_name="Current account balance (monthly, US$ mn)",
                                theme="external_sector"),
    "bop_goods_exports": dict(code=22708, freq="monthly", unit="usd_mn",
                              metric_name="BoP goods exports (US$ mn)", theme="external_sector"),
    "bop_goods_imports": dict(code=22709, freq="monthly", unit="usd_mn",
                              metric_name="BoP goods imports (US$ mn)", theme="external_sector"),
}
for _s in SERIES.values():
    _s.setdefault("source_id", "bcb_sgs")
    _s.setdefault("internal", False)

_ENV = ('<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"><soapenv:Body>'
        '<ns:{op} soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" '
        'xmlns:ns="' + NS + '">{args}</ns:{op}></soapenv:Body></soapenv:Envelope>')


def _call(op: str, args: str, timeout: int = 120) -> bytes:
    body = _ENV.format(op=op, args=args).encode()
    return get_bytes(URL, data=body, method="POST", timeout=timeout,
                     headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '""'})


def _iso(d: str) -> str:
    """'d/M/yyyy' -> 'yyyy-mm-dd'; 'M/yyyy' -> 'yyyy-mm-01'."""
    p = [int(x) for x in d.strip().split("/")]
    if len(p) == 3:
        return f"{p[2]:04d}-{p[1]:02d}-{p[0]:02d}"
    return f"{p[1]:04d}-{p[0]:02d}-01"


def fetch_values(codes: list[int], start: str, end: str = END) -> dict[int, list[tuple[str, float]]]:
    """Return {code: [(iso_date, value), ...]} for a batch of codes."""
    items = "".join(f'<item xsi:type="xsd:long">{c}</item>' for c in codes)
    args = (f'<in0 xsi:type="soapenc:Array" soapenc:arrayType="xsd:long[{len(codes)}]">{items}</in0>'
            f'<in1 xsi:type="xsd:string">{start}</in1><in2 xsi:type="xsd:string">{end}</in2>')
    raw = _call("getValoresSeriesXML", args)
    outer = ET.fromstring(raw)
    fault = outer.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Fault")
    if fault is not None:
        raise RuntimeError("SOAP fault: " + " ".join(fault.itertext())[:300])
    ret = next((e.text for e in outer.iter() if e.tag.endswith("getValoresSeriesXMLReturn")), None)
    if not ret:
        raise RuntimeError("empty getValoresSeriesXMLReturn")
    inner = ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", ret.strip()))
    out: dict[int, list[tuple[str, float]]] = {}
    for serie in inner.iter("SERIE"):
        rows = []
        for it in serie.iter("ITEM"):
            v = (it.findtext("VALOR") or "").strip()
            if v:
                rows.append((_iso(it.findtext("DATA")), float(v)))
        out[int(serie.get("ID"))] = rows
    return out


def meta(code: int) -> dict:
    """getUltimoValorVO metadata, flattened (multiRef hrefs resolved)."""
    raw = _call("getUltimoValorVO", f'<in0 xsi:type="xsd:long">{code}</in0>', timeout=60)
    root = ET.fromstring(raw)
    refs = {e.get("id"): e for e in root.iter() if e.get("id")}
    vo = refs.get("id0")
    if vo is None:
        raise RuntimeError(" ".join(root.itertext())[:300])

    def val(node, name):
        e = node.find(name)
        if e is None:
            return None
        if e.get("href"):
            e = refs[e.get("href")[1:]]
        return html.unescape(e.text or "")

    last = refs[vo.find("ultimoValor").get("href")[1:]]
    return dict(code=code, name=val(vo, "nomeCompleto"), short=val(vo, "shortName"),
                unit=val(vo, "unidadePadrao"), periodicity=val(vo, "periodicidadeSigla"),
                source=val(vo, "fonte"), last=val(last, "svalor"),
                last_date=f"{val(last, 'ano')}-{int(val(last, 'mes')):02d}-{int(val(last, 'dia')):02d}")


def _pull(codes: list[int], start: str) -> dict[int, list]:
    try:
        return fetch_values(codes, start)
    except Exception as e:  # noqa: BLE001 — one bad code faults the batch
        print(f"[warn] batch {codes} failed ({e}); retrying one code per call")
        out = {}
        for c in codes:
            try:
                out.update(fetch_values([c], start))
            except Exception as e2:  # noqa: BLE001
                print(f"[FAIL] SGS {c} :: {e2}")
        return out


def _codes(s: dict) -> tuple:
    return s["code"] if isinstance(s["code"], tuple) else (s["code"],)


def main():
    if "--meta" in sys.argv:
        for c in sys.argv[sys.argv.index("--meta") + 1:]:
            try:
                print(meta(int(c)))
            except Exception as e:  # noqa: BLE001
                print({"code": c, "error": str(e)[:200]})
        return
    NATIVE.mkdir(parents=True, exist_ok=True)
    data: dict[int, list] = {}
    for freq, start in (("daily", DAILY_START), ("monthly", MONTHLY_START)):
        codes = [c for s in SERIES.values() if s["freq"] == freq for c in _codes(s)]
        for i in range(0, len(codes), 8):
            data.update(_pull(codes[i:i + 8], start))
    ok = 0
    for metric_id, s in SERIES.items():
        parts = [pd.DataFrame(data.get(c) or [], columns=["date", "value"]).set_index("date")["value"]
                 for c in _codes(s)]
        # multi-code series = sum of components; keep only dates where ALL are present
        df = (pd.concat(parts, axis=1).dropna().sum(axis=1).rename("value").reset_index()
              if len(parts) > 1 else parts[0].reset_index())
        for k in ("metric_name", "theme", "source_id", "freq", "unit"):
            df[k] = s[k]
        df["metric_id"] = metric_id
        n = write_bronze(df, NATIVE / f"{metric_id}.csv")
        if n:
            ok += 1
            print(f"[ok]   {metric_id:<28} SGS {'+'.join(map(str, _codes(s))):<6} {s['freq']:<7} {n:>5} obs  "
                  f"{df.date.min()} .. {df.date.max()}  latest={df.value.iloc[-1]:g}")
        else:
            print(f"[FAIL] {metric_id:<28} SGS {s['code']} :: no data")
    print(f"\nPulled {ok}/{len(SERIES)} native series -> {NATIVE}  (end={END})")


if __name__ == "__main__":
    main()
