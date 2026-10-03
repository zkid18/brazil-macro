"""b3_market.py — company market data from B3 (Ibovespa portfolio, COTAHIST closes,
corporate actions, cash dividends/JCP).

Series written
--------------
bronze/companies/ (entity_id column):
  ibov_weight            daily  pct            b3_ibov_portfolio  entity_id = B3 ticker (all ~76
                                                                  constituents); metric_name carries the
                                                                  company name ("Ibovespa weight — VALE").
                                                                  Snapshot appended per run, de-duped on
                                                                  (entity_id, date) — B3 exposes only the
                                                                  current portfolio, so history = our runs.
  share_close_brl        daily  brl            b3_cotahist        unadjusted close of the main ticker
  share_close_adj_brl    daily  brl            b3_cotahist        back-adjusted for splits / reverse splits /
                                                                  bonus shares ONLY (latest = raw close)
  dividend_per_share_brl event  brl_per_share  b3_dividends       cash dividends + JCP + "RENDIMENTO"
                                                                  (monetary update paid with installments),
                                                                  dated by ex-date, on the adjusted share basis
bronze/native/:
  ibov_resource_energy_weight daily pct        b3_ibov_portfolio  sum of Ibovespa weights in B3 sectors
                                                                  Petróleo/Gás/Biocomb + Mineração + Siderurgia/
                                                                  Metalurgia + Madeira e Papel + Energia Elétrica

Sources (all verified 2026-10-03)
---------------------------------
* Ibovespa portfolio: indexProxy/indexCall/GetPortfolioDay/{b64 {"language":"pt-br","pageNumber":1,
  "pageSize":120,"index":"IBOV","segment":"2"}}. segment "1" returns segment=null; segment "2" groups by
  B3 sector ("Petróleo, Gás e Biocombustíveis", "Mats Básicos / Mineração", ...). `part` uses comma
  decimals and sums to 100. Header date (e.g. 05/10/26) is the session the theoretical portfolio applies
  to; we date the snapshot by the run date. 2026-10-03: 76 names, VALE3 9.877, ITUB4 8.890, PETR4 8.385,
  PETR3 5.136, AXIA3 4.817; resource/energy block 46.8 % (Fable's report quoted ≈39 % on a narrower set).
* COTAHIST fixed-width (latin-1, 245 cols): bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{YYYY}.ZIP
  (2012–2026; the current-year file is updated through the previous session — A2026 already holds
  2026-10-02) and COTAHIST_D{DDMMYYYY}.ZIP for any later sessions. Filter TIPREG 01, CODBDI "02" (lote
  padrão; the probe's "010" is TPMERC = mercado à vista), TPMERC 010; prices ÷100; FATCOT = 1 for every
  row used. HRTP3 traded under CODBDI 58 for 15 sessions in Feb–Mar 2014 (special listing) → we fall back
  to BDI 58 only where no BDI-02 row exists. Zips are deleted after parsing; the filtered rows are kept in
  warehouse/bronze/raw/cotahist_parsed/ (gitignored) so reruns don't re-download closed years.
  Check vs B3 2026-10-02: PETR4 51.17, VALE3 72.10, AXIA3 56.90, SUZB3 44.35, PRIO3 63.01 (exact).
* Ticker splices (one continuous line per entity; dates from COTAHIST):
    AXIA: ELET3 → AXIA3 on 2025-11-10 (Eletrobras renamed Axia Energia; last ELET3 2025-11-07, no gap jump)
    PRIO: HRTP3 → PRIO3 on 2015-06-26 (HRT Participações renamed PetroRio; same ISIN family)
    SUZB: SUZB5 (PNA) → SUZB3 on 2017-11-10 (Novo Mercado migration, PNA converted 1:1 into ON;
          SUZB3 has no lote-padrão trades before that date). Fibria merger (Jan-2019) issued new shares to
          Fibria holders — no factor for Suzano holders.
* Corporate actions: listedCompaniesProxy/CompanyCall/GetListedSupplementCompany/{b64 {"issuingCompany":
  "ITUB","language":"pt-br"}} → JSON *string* holding a list; `stockDividends` has label DESDOBRAMENTO /
  GRUPAMENTO / BONIFICACAO, `factor` (% new shares for split/bonus, ratio for grouping) and
  `lastDatePrior` (last "com" date → ex = next session). This list is INCOMPLETE: it omits Itaú's 10 %
  bonuses of 2013/2015/2016/Mar-2025 and HRT/PetroRio's 2012 split, 2014 grouping and 2019 split. Those
  are in EXTRA_EVENTS below, each verified from COTAHIST as a price gap that matches 1/ratio while the
  Ibovespa and the sister share class moved normally (e.g. ITUB4 −9.0 % / ITUB3 −9.2 % vs IBOV +0.2 % on
  2015-07-14). Not adjusted (by design — splits/bonus only): Itaú's Oct-2021 XP spin-off ("CIS RED CAP",
  ex 2021-10-04, ITUB4 −18 % vs IBOV −2 %), so ITUB's price+dividend total return understates by ~16 %
  around that date.
* Cash dividends: listedCompaniesProxy/CompanyCall/GetListedCashDividends/{b64 {"language":"pt-br",
  "pageNumber":N,"pageSize":120,"tradingName":...}} (paginated, back to 1996). Trading names: PETROBRAS,
  VALE, AXIA ENERGIA (covers the Eletrobras history), SUZANO S.A., PRIO, ITAUUNIBANCO. `valueCash` is
  R$ per share at the time; `lastDatePriorEx` is the last "com" date, ex-date = next session.
  Identical rows (same date/type/value) are genuine installments (cross-checked against
  GetListedSupplementCompany cashDividends, which shows distinct paymentDates) — so they are summed, not
  de-duplicated. Share class: PN for PETR/ITUB, ON otherwise.

Sanity (2026-10-03 run): closes 2026-10-02 match the probe exactly. Adjusted |daily return| > 40 % only:
AXIA 2017-08-22 +49 % (government announced Eletrobras privatisation on 08-21) and PRIO 2016-03-24 +84 %
(PRIO3 1.96 → 3.60 on ~20× volume, not a clean split ratio, no B3 stock event — penny-stock rerating;
plus HRTP3 2015-01-22 +42 %, a speculative spike reversed within days). TTM dividend yield on the
adjusted basis: PETR 7.1 %, VALE 7.8 %, ITUB 6.9 %, AXIA 2.6 %, SUZB 2.5 %, PRIO 0 % (one dividend ever,
Dec-2023 — PRIO returns cash via buybacks).

Run:  .venv/bin/python ingest/b3_market.py
"""
from __future__ import annotations
import base64, datetime as dt, json, os, sys, pathlib, zipfile, urllib.error
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import get_json, cached, write_bronze, NATIVE, COMPANIES, RAW_CACHE  # noqa: E402

LISTED = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/"
PORTFOLIO = "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/"
SERHIST = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/"
PARSED = RAW_CACHE / "cotahist_parsed"
START = pd.Timestamp("2012-01-02")
TODAY = pd.Timestamp(dt.date.today())
FIRST_COM = pd.Timestamp("2011-12-29")  # last session of 2011: a "com" date on/after it has ex >= START

# entity -> ticker history [(ticker, first_date)], B3 issuer code, cash-dividend trading name, share class
TARGETS = {
    "PETR": dict(line=[("PETR4", "2012-01-01")], code="PETR", trading="PETROBRAS", cls="PN"),
    "VALE": dict(line=[("VALE3", "2012-01-01")], code="VALE", trading="VALE", cls="ON"),
    "AXIA": dict(line=[("ELET3", "2012-01-01"), ("AXIA3", "2025-11-10")], code="AXIA",
                 trading="AXIA ENERGIA", cls="ON"),
    "SUZB": dict(line=[("SUZB5", "2012-01-01"), ("SUZB3", "2017-11-10")], code="SUZB",
                 trading="SUZANO S.A.", cls="ON"),
    "PRIO": dict(line=[("HRTP3", "2012-01-01"), ("PRIO3", "2015-06-26")], code="PRIO",
                 trading="PRIO", cls="ON"),
    "ITUB": dict(line=[("ITUB4", "2012-01-01")], code="ITUB", trading="ITAUUNIBANCO", cls="PN"),
}
TICKERS = {t for v in TARGETS.values() for t, _ in v["line"]}
PROBE_2026_10_02 = {"PETR": 51.17, "VALE": 72.10, "AXIA": 56.90, "SUZB": 44.35, "PRIO": 63.01}

# Stock events missing from B3's stockDividends list. ratio = new shares per old share; ex = first ex session.
EXTRA_EVENTS = [
    ("PRIO", "2012-05-29", 50.0, "HRT split 1:50 (HRTP3 375.00 → 7.75; volume ×51)"),
    ("PRIO", "2014-08-04", 0.1, "HRT grouping 10:1 (HRTP3 1.40 → 14.50)"),
    ("PRIO", "2019-03-06", 10.0, "PetroRio split 1:10 (PRIO3 168.00 → 17.03)"),
    ("ITUB", "2013-05-21", 1.10, "Itaú 10% bonus (ITUB4 −7.7% vs IBOV +1.0%)"),
    ("ITUB", "2015-07-14", 1.10, "Itaú 10% bonus (ITUB4 −9.0% vs IBOV +0.2%)"),
    ("ITUB", "2016-10-18", 1.10, "Itaú 10% bonus (ITUB4 −7.8% vs IBOV +1.7%)"),
    ("ITUB", "2025-03-18", 1.10, "Itaú 10% bonus (ITUB4 −8.6% vs IBOV +0.5%)"),
]
RESOURCE_SECTORS = ("Petróleo", "Mats Básicos / Mineração", "Mats Básicos / Sid Metalurgia",
                    "Mats Básicos / Madeira e Papel", "Utilidade Públ / Energ Elétrica")


def b64(d: dict) -> str:
    return base64.b64encode(json.dumps(d, separators=(",", ":")).encode()).decode()


def br_num(s) -> float:
    return float(str(s).replace(".", "").replace(",", "."))


def load_json(url):
    j = get_json(url)
    return json.loads(j) if isinstance(j, str) else j


def bronze_frame(metric_id, name, theme, source, freq, unit, rows):
    df = pd.DataFrame(rows)
    df.insert(0, "metric_id", metric_id)
    df.insert(1, "metric_name", df.pop("metric_name") if "metric_name" in df else name)
    for k, v in dict(theme=theme, source_id=source, freq=freq, unit=unit).items():
        df[k] = v
    return df


def append_snapshot(df, path, keys):
    if path.exists():
        old = pd.read_csv(path, dtype=str)
        old["value"] = pd.to_numeric(old["value"])
        df = pd.concat([old, df.astype({"date": str})], ignore_index=True)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df = df.drop_duplicates(keys, keep="last")
    return df


def report(metric_id, df, entity=True):
    for e, g in (df.groupby("entity_id") if entity else [("BR", df)]):
        g = g.sort_values("date")
        print(f"[ok]   {metric_id:<28} {e:<6} {len(g):>5} obs ({str(g.date.iloc[0])[:10]}.."
              f"{str(g.date.iloc[-1])[:10]}) latest {g.value.iloc[-1]:.4f}")


# ---------------------------------------------------------------- 1. Ibovespa portfolio
def ibov_portfolio():
    j = load_json(PORTFOLIO + b64({"language": "pt-br", "pageNumber": 1, "pageSize": 120,
                                   "index": "IBOV", "segment": "2"}))
    res = pd.DataFrame(j["results"])
    res["w"] = res["part"].map(br_num)
    assert abs(res.w.sum() - 100) < 0.5, res.w.sum()
    date = TODAY.strftime("%Y-%m-%d")
    print(f"  Ibovespa portfolio header date {j['header']['date']}: {len(res)} names, sum {res.w.sum():.3f}")
    w = bronze_frame("ibov_weight", None, "companies", "b3_ibov_portfolio", "daily", "pct",
                     dict(metric_name=["Ibovespa weight — " + a.strip() for a in res.asset],
                          date=date, value=res.w.values, entity_id=res.cod.str.strip().values))
    w = append_snapshot(w, COMPANIES / "ibov_weight.csv", ["entity_id", "date"])
    write_bronze(w, COMPANIES / "ibov_weight.csv", entity=True)
    print(f"[ok]   ibov_weight                  {len(res)} constituents on {date}; top: " +
          ", ".join(f"{c} {v:.2f}" for c, v in res.sort_values("w", ascending=False)[["cod", "w"]].head(5).values))
    mask = res.segment.fillna("").str.startswith(RESOURCE_SECTORS)
    share = res.loc[mask, "w"].sum()
    by = res[mask].groupby("segment").w.sum().round(2).to_dict()
    n = bronze_frame("ibov_resource_energy_weight", "Ibovespa weight of resource & energy sectors",
                     "companies", "b3_ibov_portfolio", "daily", "pct", dict(date=[date], value=[round(share, 3)]))
    n = append_snapshot(n, NATIVE / "ibov_resource_energy_weight.csv", ["date"])
    write_bronze(n, NATIVE / "ibov_resource_energy_weight.csv")
    print(f"[ok]   ibov_resource_energy_weight  {share:.2f}% on {date}  {by}")


# ---------------------------------------------------------------- 2. COTAHIST
def parse_cotahist(zpath: pathlib.Path) -> pd.DataFrame:
    rows = []
    with zipfile.ZipFile(zpath) as z, z.open(z.namelist()[0]) as fh:
        for raw in fh:
            if raw[:2] != b"01" or raw[12:24].decode("latin-1").strip() not in TICKERS:
                continue
            l = raw.decode("latin-1")
            rows.append(dict(date=l[2:10], bdi=l[10:12], ticker=l[12:24].strip(), tpmerc=l[24:27],
                             close=int(l[108:121]) / 100, qty=int(l[152:170]), fatcot=int(l[210:217])))
    return pd.DataFrame(rows, columns=["date", "bdi", "ticker", "tpmerc", "close", "qty", "fatcot"])


def cotahist_file(kind: str, tag: str, refresh_days: float | None) -> pd.DataFrame | None:
    """kind A (annual, tag=YYYY) or D (daily, tag=DDMMYYYY). Parsed rows cached as CSV; zip deleted."""
    PARSED.mkdir(parents=True, exist_ok=True)
    out = PARSED / f"{kind}{tag}.csv"
    if out.exists() and (refresh_days is None or
                         (dt.datetime.now().timestamp() - out.stat().st_mtime) < refresh_days * 86400):
        return pd.read_csv(out, dtype={"date": str, "bdi": str, "tpmerc": str})
    name = f"COTAHIST_{kind}{tag}.ZIP"
    try:
        z = cached(SERHIST + name, name, timeout=600, max_age_days=0)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    df = parse_cotahist(z)
    os.remove(z)
    df.to_csv(out, index=False)
    return df.astype({"date": str})


def load_cotahist() -> pd.DataFrame:
    frames = []
    for y in range(START.year, TODAY.year + 1):
        df = cotahist_file("A", str(y), None if y < TODAY.year else 1)
        if df is not None:
            frames.append(df)
            print(f"  COTAHIST_A{y}: {len(df)} rows")
    allr = pd.concat(frames, ignore_index=True)
    last = pd.to_datetime(allr.date).max()
    for d in pd.bdate_range(last + pd.Timedelta(days=1), TODAY):  # sessions after the annual file
        df = cotahist_file("D", d.strftime("%d%m%Y"), None)
        if df is not None and len(df):
            frames.append(df)
            print(f"  COTAHIST_D{d:%d%m%Y}: {len(df)} rows")
    allr = pd.concat(frames, ignore_index=True)
    allr["date"] = pd.to_datetime(allr.date)
    allr = allr[(allr.tpmerc.astype(str).str.zfill(3) == "010") & allr.bdi.astype(str).str.zfill(2).isin(["02", "58"])]
    assert (allr.fatcot == 1).all(), "unexpected FATCOT != 1"
    allr["pri"] = (allr.bdi.astype(str).str.zfill(2) != "02").astype(int)  # prefer BDI 02
    return allr.sort_values(["ticker", "date", "pri"]).drop_duplicates(["ticker", "date"])


def entity_closes(cot: pd.DataFrame) -> dict[str, pd.Series]:
    out = {}
    for e, cfg in TARGETS.items():
        parts = []
        bounds = [pd.Timestamp(d) for _, d in cfg["line"]] + [pd.Timestamp("2100-01-01")]
        for i, (tk, _) in enumerate(cfg["line"]):
            s = cot[(cot.ticker == tk) & (cot.date >= max(bounds[i], START)) & (cot.date < bounds[i + 1])]
            parts.append(s.set_index("date").close)
        out[e] = pd.concat(parts).sort_index()
    return out


# ---------------------------------------------------------------- 3. corporate actions
def stock_events(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    def next_session(d):
        i = sessions.searchsorted(d, side="right")
        return sessions[i] if i < len(sessions) else d + pd.offsets.BDay(1)

    rows = []
    for e, cfg in TARGETS.items():
        j = load_json(LISTED + "GetListedSupplementCompany/" + b64({"issuingCompany": cfg["code"], "language": "pt-br"}))
        isin_cls = "ACNOR" if cfg["cls"] == "ON" else "ACNPR"
        for s in (j[0].get("stockDividends") or []):
            lab, f = s["label"].strip(), br_num(s["factor"])
            if lab not in ("DESDOBRAMENTO", "GRUPAMENTO", "BONIFICACAO") or isin_cls not in s["isinCode"]:
                continue
            ratio = f if lab == "GRUPAMENTO" else 1 + f / 100
            com = pd.to_datetime(s["lastDatePrior"], dayfirst=True)
            if com < FIRST_COM:  # pre-window event: already embedded in every price we hold
                continue
            ex = next_session(com)
            rows.append(dict(entity=e, ex=ex, ratio=ratio, note=f"B3 {lab} {s['factor']}"))
    for e, ex, ratio, note in EXTRA_EVENTS:
        rows.append(dict(entity=e, ex=pd.Timestamp(ex), ratio=ratio, note="static: " + note))
    ev = pd.DataFrame(rows)
    return ev[ev.ex >= START].drop_duplicates(["entity", "ex"]).sort_values(["entity", "ex"])


def cum_factor(dates: pd.DatetimeIndex, ev: pd.DataFrame, inclusive: bool = False) -> pd.Series:
    """Number of today's shares per share held at each date (product of ratios of events after it)."""
    f = pd.Series(1.0, index=dates)
    for ex, r in zip(ev.ex, ev.ratio):
        f[(dates <= ex) if inclusive else (dates < ex)] *= r
    return f


# ---------------------------------------------------------------- 4. dividends
def cash_dividends(cfg) -> pd.DataFrame:
    rows, n = [], 1
    while True:
        j = load_json(LISTED + "GetListedCashDividends/" + b64(
            {"language": "pt-br", "pageNumber": n, "pageSize": 120, "tradingName": cfg["trading"]}))
        rows += j.get("results") or []
        if n >= j["page"]["totalPages"]:
            break
        n += 1
    df = pd.DataFrame(rows)
    df = df[df.typeStock.str.strip() == cfg["cls"]].copy()
    df["com"] = pd.to_datetime(df.lastDatePriorEx, dayfirst=True)
    df["v"] = df.valueCash.map(br_num)
    return df[df.corporateAction.str.strip().isin(["DIVIDENDO", "JRS CAP PROPRIO", "RENDIMENTO"])]


def main():
    COMPANIES.mkdir(parents=True, exist_ok=True)
    ibov_portfolio()

    print("COTAHIST …")
    cot = load_cotahist()
    closes = entity_closes(cot)
    sessions = pd.DatetimeIndex(sorted(cot.date.unique()))
    ev = stock_events(sessions)
    print("stock events applied (ratio = new shares per old share):")
    for r in ev.itertuples():
        print(f"  {r.entity} ex {r.ex.date()} ratio {r.ratio:g}  {r.note}")

    raw_rows, adj_rows, div_rows, adj = [], [], [], {}
    for e, s in closes.items():
        f = cum_factor(s.index, ev[ev.entity == e])
        a = s / f
        adj[e] = a
        raw_rows.append(pd.DataFrame(dict(date=s.index, value=s.values, entity_id=e)))
        adj_rows.append(pd.DataFrame(dict(date=a.index, value=a.round(6).values, entity_id=e)))
        d = cash_dividends(TARGETS[e])
        sess = pd.DatetimeIndex(s.index)
        d["ex"] = [sess[i] if (i := sess.searchsorted(c, side="right")) < len(sess) else c + pd.offsets.BDay(1)
                   for c in d.com]
        d = d[d.com >= FIRST_COM]
        d["adj"] = d.v / cum_factor(pd.DatetimeIndex(d.ex), ev[ev.entity == e], inclusive=True).values
        g = d.groupby("ex").adj.sum()
        div_rows.append(pd.DataFrame(dict(date=g.index, value=g.round(8).values, entity_id=e)))

    def mk(mid, name, freq, unit, src, rows):
        return bronze_frame(mid, name, "companies", src, freq, unit, pd.concat(rows, ignore_index=True))

    close_df = mk("share_close_brl", "Share close, main ticker (unadjusted)", "daily", "brl", "b3_cotahist", raw_rows)
    adj_df = mk("share_close_adj_brl", "Share close, main ticker (split/bonus-adjusted)", "daily", "brl",
                "b3_cotahist", adj_rows)
    div_df = mk("dividend_per_share_brl", "Cash dividends + JCP per share (ex-date, adjusted basis)", "event",
                "brl_per_share", "b3_dividends", div_rows)
    for mid, df in [("share_close_brl", close_df), ("share_close_adj_brl", adj_df), ("dividend_per_share_brl", div_df)]:
        write_bronze(df, COMPANIES / f"{mid}.csv", entity=True)
        report(mid, df)

    # ---------------- sanity checks
    print("sanity: close on 2026-10-02 vs probe")
    for e, v in PROBE_2026_10_02.items():
        got = closes[e].get(pd.Timestamp("2026-10-02"))
        print(f"  {e}: {got} vs {v} {'OK' if got == v else 'MISMATCH'}")
    print("sanity: adjusted daily |return| > 20% (all must be < 40% or explained)")
    for e, a in adj.items():
        r = a.pct_change().dropna()
        for d, x in r[r.abs() > 0.20].items():
            i = closes[e].index.get_loc(d)
            print(f"  {e} {d.date()} {x:+.1%}  raw {closes[e].iloc[i - 1]} -> {closes[e].iloc[i]}")
    print("sanity: trailing-12m dividend yield (adjusted DPS / adjusted close)")
    for e, a in adj.items():
        g = div_df[div_df.entity_id == e]
        last = a.index[-1]
        ttm = g[pd.to_datetime(g.date) > last - pd.Timedelta(days=365)].value.sum()
        print(f"  {e}: TTM DPS {ttm:.4f} / close {a.iloc[-1]:.2f} = {ttm / a.iloc[-1]:.1%}")


if __name__ == "__main__":
    main()
