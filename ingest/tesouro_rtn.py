"""tesouro_rtn.py — Tier-2 native adapter: Treasury monthly central-government results (RTN).

The Resultado do Tesouro Nacional is the Treasury's monthly, above-the-line account of the
central government (Treasury + central bank + social security): revenue by tax and
spending by category. It is where a fiscal package shows up first — whether an adjustment
lands on revenue or on spending — a month or so after the fact.

Source: the "Série Histórica" workbook, table 1.1 (monthly, R$ million, current prices,
cash basis, Jan-1997 onwards). Two places publish it:
  1. the monthly publication page
       https://www.tesourotransparente.gov.br/publicacoes/boletim-resultado-do-tesouro-nacional-rtn/<yyyy>/<m>
     (attachment serie_historica_<mmm><yy>.xlsx on cdn.tesouro.gov.br). Newest, but on
     2026-11-11 the page body failed to render ("Falha na integração THOT/3PRO") for
     scripted requests, so it is tried opportunistically;
  2. the open-data catalogue (CKAN) dataset `resultado-do-tesouro-nacional`, resource
     "... Série Histórica - Mensal" (XLSX). Stable, but lags: on 2026-11-11 it still held
     July 2026 (posted 2026-08-27) while August and September were already published.
The newest workbook of the two (by the month in its file name) wins.

Rows are matched by their line code AND a keyword, so a re-numbered table fails loudly
instead of loading the wrong line. Verification (2026-11-11, July-2026 workbook): total
revenue Jul-26 R$ 275.9 bn, net revenue 226.3 bn, total spending 215.5 bn, primary result
+10.8 bn (= net revenue - spending).

Writes warehouse/bronze/native/<metric_id>.csv (monthly flows, R$ million). The pipeline
derives 12-month sums as % of GDP (cg_*_gdp). Run:  python3 ingest/tesouro_rtn.py
"""
from __future__ import annotations
import sys, io, re, pathlib, datetime as dt, unicodedata
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_bytes, get_json, write_bronze, NATIVE  # noqa: E402
from _checks import check_gaps  # noqa: E402

CKAN = ("https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
        "?id=resultado-do-tesouro-nacional")
PUB = "https://www.tesourotransparente.gov.br/publicacoes/boletim-resultado-do-tesouro-nacional-rtn/{y}/{m}"
SHEET = "1.1"
MONTHS = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
          "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}

# metric_id -> (line code, keyword that must appear in the label, title)
LINES = {
    "cg_revenue_total_brl": ("1", "receita total", "Central government revenue, total"),
    "cg_revenue_rfb_brl": ("1.1", "administrada pela rfb",
                           "Central government revenue: taxes collected by the federal revenue service"),
    "cg_revenue_income_tax_brl": ("1.1.03", "imposto sobre a renda", "Central government revenue: income tax"),
    "cg_revenue_iof_brl": ("1.1.04", "iof", "Central government revenue: financial transactions tax (IOF)"),
    "cg_revenue_cofins_brl": ("1.1.05", "cofins", "Central government revenue: Cofins turnover tax"),
    "cg_revenue_csll_brl": ("1.1.07", "csll", "Central government revenue: social contribution on net profit"),
    "cg_revenue_rgps_brl": ("1.3", "rgps", "Central government revenue: social security contributions (net)"),
    "cg_revenue_nontax_brl": ("1.4", "nao administradas",
                              "Central government revenue: non-tax (dividends, royalties, concessions)"),
    "cg_transfers_subnational_brl": ("2", "transf", "Central government revenue shared with states and municipalities"),
    "cg_net_revenue_brl": ("3", "receita liquida", "Central government net revenue"),
    "cg_expense_total_brl": ("4", "despesa total", "Central government primary spending, total"),
    "cg_expense_pensions_brl": ("4.1", "previdenciarios", "Central government spending: social security pensions"),
    "cg_expense_payroll_brl": ("4.2", "pessoal", "Central government spending: payroll"),
    "cg_expense_other_mandatory_brl": ("4.3", "outras despesas obrigatorias",
                                       "Central government spending: other mandatory"),
    "cg_expense_discretionary_brl": ("4.4.2", "discricionarias", "Central government spending: discretionary"),
    "cg_primary_result_brl": ("5", "resultado primario", "Central government primary result (+=surplus)"),
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _month_of(url: str) -> tuple[int, int] | None:
    m = re.search(r"([a-z]{3})(\d{2})\.xlsx", url.lower())
    if m and m.group(1) in MONTHS:
        return 2000 + int(m.group(2)), MONTHS[m.group(1)]
    return None


def candidates() -> list[str]:
    urls = []
    today = dt.date.today()
    for back in range(0, 4):  # publication pages for the last few months
        y, m = today.year, today.month - back
        while m < 1:
            y, m = y - 1, m + 12
        try:
            html = get_bytes(PUB.format(y=y, m=m), timeout=60, retries=1).decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001 — missing month or broken page: try the next source
            continue
        urls += re.findall(r'https://cdn\.tesouro\.gov\.br/[^"\']*serie_historica[^"\']*\.xlsx', html)
    try:
        for r in get_json(CKAN, timeout=60)["result"]["resources"]:
            if "mensal" in _norm(r.get("name", "")) and str(r.get("format", "")).lower() == "xlsx":
                urls.append(r["url"])
    except Exception as e:  # noqa: BLE001
        print(f"[warn] CKAN lookup failed: {e}")
    return sorted(set(urls), key=lambda u: _month_of(u) or (0, 0), reverse=True)


def parse(raw: bytes) -> dict[str, pd.Series]:
    t = pd.read_excel(io.BytesIO(raw), sheet_name=SHEET, header=None)
    hdr = next(i for i in range(12) if _norm(t.iloc[i, 0]).startswith("discrimina"))
    dates = pd.to_datetime(t.iloc[hdr, 1:], errors="coerce")
    by_code = {}
    for i in range(hdr + 1, len(t)):
        lab = _norm(t.iloc[i, 0])
        m = re.match(r"^(\d+(?:\.\d+)*)", lab)
        if m and m.group(1) not in by_code:
            by_code[m.group(1)] = i
    out = {}
    for mid, (code, kw, _title) in LINES.items():
        i = by_code.get(code)
        if i is None or kw not in _norm(t.iloc[i, 0]):
            raise RuntimeError(f"{mid}: line {code} '{kw}' not found in table {SHEET} "
                               f"(got {t.iloc[i, 0] if i is not None else 'no such line'!r})")
        s = pd.Series(pd.to_numeric(t.iloc[i, 1:], errors="coerce").to_numpy(), index=dates)
        s = s[s.index.notna()].dropna()
        nz = s.ne(0)  # lines split out later (discretionary: 2008) carry 0 placeholders before
        out[mid] = s[nz.cummax()] if nz.any() else s
    return out


def main() -> int:
    NATIVE.mkdir(parents=True, exist_ok=True)
    urls = candidates()
    if not urls:
        print("[fail] no RTN workbook found (publication pages and CKAN)"); return 1
    series, used = None, None
    for u in urls:
        try:
            series, used = parse(get_bytes(u, timeout=180)), u
            break
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {u}: {e}")
    if series is None:
        print("[fail] every RTN workbook failed to parse"); return 1
    print(f"workbook: {used}")
    ok = True
    for mid, s in series.items():
        df = pd.DataFrame({"metric_id": mid, "metric_name": LINES[mid][2], "theme": "fiscal",
                           "source_id": "tesouro_rtn", "freq": "monthly",
                           "date": s.index.strftime("%Y-%m-01"), "value": s.values.round(3), "unit": "brl_mn"})
        n = write_bronze(df, NATIVE / f"{mid}.csv")
        if n:
            print(f"[ok]   {mid:<32} {n} obs ({df.date.min()}..{df.date.max()}), last {df.value.iloc[-1]:,.0f}")
            ok &= check_gaps(df, mid, "monthly")
    # identity check: primary result = net revenue - total spending (table line 5 = 3 - 4)
    chk = (series["cg_net_revenue_brl"] - series["cg_expense_total_brl"] - series["cg_primary_result_brl"]).abs().dropna()
    if chk.max() > 1.0:
        print(f"[FAIL] identity 5 = 3 - 4 broken by up to R$ {chk.max():,.1f} mn"); ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
