"""fetch.py — external pulls for the Petrobras study (cached in ./cache; nothing written to the warehouse).

1. B3 COTAHIST annual files 2000-2011 and daily files after the warehouse cut-off (2026-10-05..09)
   -> cache/cotahist_<tag>.csv (selected tickers only)
2. B3 listed-companies API: PETROBRAS cash dividends (back to 1996) and stock events (splits/bonus)
   -> cache/petr_cash_div.json, cache/petr_supplement.json
3. FRED DCOILBRENTEU (Brent, to extend past the warehouse's 2026-09-29) -> cache/fred_brent.csv
"""
import base64, io, json, pathlib, ssl, sys, urllib.request, zipfile
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
UA = "Mozilla/5.0 (research; brazil-macro)"
try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    CTX = ssl.create_default_context()

TICKERS = {"PETR4", "PETR3", "VALE5", "VALE3", "ITUB4", "ITAU4", "ELET3", "ELET6", "AXIA3", "BOVA11",
           "PRIO3", "SUZB3", "BBAS3", "BBDC4"}
SERHIST = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/"
LISTED = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/"


def get(url, timeout=600):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()


def parse_cotahist(blob: bytes) -> pd.DataFrame:
    rows = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z, z.open(z.namelist()[0]) as fh:
        for raw in fh:
            if raw[:2] != b"01":
                continue
            tk = raw[12:24].decode("latin-1").strip()
            if tk not in TICKERS:
                continue
            l = raw.decode("latin-1")
            rows.append(dict(date=l[2:10], bdi=l[10:12], ticker=tk, tpmerc=l[24:27],
                             close=int(l[108:121]) / 100, qty=int(l[152:170]), fatcot=int(l[210:217])))
    return pd.DataFrame(rows, columns=["date", "bdi", "ticker", "tpmerc", "close", "qty", "fatcot"])


def cotahist(kind, tag):
    out = CACHE / f"cotahist_{kind}{tag}.csv"
    if out.exists():
        return
    try:
        blob = get(f"{SERHIST}COTAHIST_{kind}{tag}.ZIP")
    except Exception as e:
        print("  miss", kind, tag, e)
        return
    df = parse_cotahist(blob)
    df.to_csv(out, index=False)
    print(f"  COTAHIST_{kind}{tag}: {len(df)} rows")


def b64(d):
    return base64.b64encode(json.dumps(d).encode()).decode()


def b3_dividends():
    out = CACHE / "petr_cash_div.json"
    if not out.exists():
        rows, n = [], 1
        while True:
            j = json.loads(get(LISTED + "GetListedCashDividends/" + b64(
                {"language": "pt-br", "pageNumber": n, "pageSize": 120, "tradingName": "PETROBRAS"})))
            rows += j.get("results") or []
            if n >= j["page"]["totalPages"]:
                break
            n += 1
        out.write_text(json.dumps(rows))
        print("  dividends rows", len(rows))
    out2 = CACHE / "petr_supplement.json"
    if not out2.exists():
        j = get(LISTED + "GetListedSupplementCompany/" + b64({"issuingCompany": "PETR", "language": "pt-br"}))
        out2.write_bytes(j)
        print("  supplement saved")


def fred():
    out = CACHE / "fred_brent.csv"
    out.write_bytes(get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU&cosd=2000-01-01"))
    print("  FRED brent saved")


if __name__ == "__main__":
    for y in range(2000, 2012):
        cotahist("A", str(y))
    for d in ["05102026", "06102026", "07102026", "08102026", "09102026",
              "29092026", "30092026", "01102026", "02102026"]:
        cotahist("D", d)
    b3_dividends()
    fred()
