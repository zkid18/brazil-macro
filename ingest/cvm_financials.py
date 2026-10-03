"""cvm_financials.py — company adapter: CVM ITR/DFP open data (quarterly financials).

Source: CVM "Dados Abertos" — Companhias Abertas, structured statements
  https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{YYYY}.zip  (Q1–Q3, 2012→2026)
  https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{YYYY}.zip  (full year, 2012→2025)
Each zip holds `;`-separated latin-1 CSVs, one per statement × consolidated/individual.
We read the CONSOLIDATED files only: DRE (income), BPA/BPP (balance sheet), DFC_MI
(cash flow, indirect method). Zips are cached in warehouse/bronze/raw/ (gitignored).

Entities are keyed by CNPJ (verified in cad_cia_aberta.csv / statement files 2026-10-03):
  PETR 33.000.167/0001-01  PETROLEO BRASILEIRO S.A. PETROBRAS
  VALE 33.592.510/0001-54  VALE S.A.
  AXIA 00.001.180/0001-26  CENTRAIS ELET BRAS S.A. - ELETROBRAS → renamed "AXIA ENERGIA S.A." (same CNPJ)
  SUZB 16.404.287/0001-55  SUZANO S.A. (ex-Suzano Papel e Celulose; same CNPJ)
  PRIO 10.629.105/0001-68  PRIO S.A. (ex-HRT Participações / PetroRio; same CNPJ, files since 2012)
  ITUB 60.872.504/0001-23  ITAU UNIBANCO HOLDING S.A.

Rules / gotchas
- ORDEM_EXERC == 'ÚLTIMO' only (the current period of each filing). 'PENÚLTIMO' rows are the
  prior-period comparatives re-presented in later filings; we do NOT overwrite with them
  (that would mix restated and original bases and break the Q4 = FY − 9M derivation).
  Re-filings of the same period (VERSAO 2, 3 …) supersede earlier versions: we keep the
  highest VERSAO per (company, DT_REFER) → "most recent filing for each period".
  main() prints how many FY figures were later restated by >0.5 % (PENÚLTIMO vs ÚLTIMO).
- ESCALA_MOEDA: MIL → ×1 000, UNIDADE → ×1. Output unit brl_bn (BRL billions).
- DRE flows: ITR carries both quarter-only rows (DT_INI_EXERC = quarter start) and YTD rows
  (DT_INI_EXERC = Jan 1). We use quarter-only rows for Q1–Q3; Q4 = DFP full year − ITR 9M YTD.
- DFC is YTD only in both ITR and DFP → quarterly flows by differencing YTD.
- Account codes are verified by description (DS_CONTA) on every row, not trusted blindly:
    revenue_brl     3.01 "Receita de Venda de Bens e/ou Serviços"  (ITUB: 3.01 "Receitas da
                    Intermediação Financeira" — gross interest income, NOT comparable; flagged in
                    metric_name)
    ebit_brl        3.05 "Resultado Antes do Resultado Financeiro e dos Tributos" (not ITUB: its 3.05
                    is pre-tax income)
    net_income_brl  "Atribuído a Sócios da Empresa Controladora" = 3.11.01 (non-banks), 3.09.01
                    (ITUB, bank layout) — NI attributable to controlling shareholders.
    gross_debt_brl  2.01.04 + 2.02.01 "Empréstimos e Financiamentos" (includes debentures and lease
                    liabilities sub-accounts 2.0x.0x.03 "Financiamento por Arrendamento"; IFRS-16 leases
                    are large for PETR since 2019). Not ITUB (its 2.02.01 = derivatives).
    cash_brl        1.01.01 "Caixa e Equivalentes de Caixa" + 1.01.02 "Aplicações Financeiras". Not ITUB.
    capex_brl       DFC 6.02.xx lines matched by description (CAPEX_INC / CAPEX_EXC regexes): additions to
                    PP&E + intangibles; also SUZB biological assets (forest formation, part of Suzano's
                    own capex definition), AXIA concession/transmission assets ("Aquisição de ativos de
                    concessão" 2012-17, "Infraestrutura da transmissão - ativo contratual" 2022+), PETR
                    2012-13 segment "Investimentos em …" lines. Excludes M&A (PRIO "(Aquisição) de ativos de
                    óleo e gás", subsidiaries), PETR 2019 Transfer-of-Rights surplus bonus, disposals.
                    Positive = cash out. Not ITUB. Caveats: AXIA 2022 intangibles include the ~R$30 bn
                    privatization concession grant (one-off, not separable in the data); AXIA 2018-21 misses
                    transmission contract-asset spend (not shown as an investing line then); PRIO uses net
                    "(Compra) venda" lines in some years → a few small negative quarters.
    dividends_paid_brl  DFC 6.03.xx lines for dividends/JCP paid to the company's own shareholders
                    (AXIA: "Pagamento de remuneração aos acionistas"); excludes payments to non-controlling
                    interests. A filed DFC with no such line = 0 (PRIO returns cash mostly via buybacks).
                    Positive = cash out; a handful of tiny negative quarters are YTD reclassifications.
- Restatement policy (flagged): ÚLTIMO + highest VERSAO = the period's own latest filing. Later
  re-presentations (PENÚLTIMO) are NOT applied — e.g. PETR FY2018 revenue 349.8 original vs 310.3
  re-presented in 2019 (BR Distribuidora → discontinued ops). Intra-year restatements make
  Q1+Q2+Q3 ≠ 9M YTD in a few company-years (PETR 2019, AXIA 2018/2022, ITUB 2013-22 revenue …);
  Q4 is FY − 9M YTD (same basis as FY) unless the 9M YTD row is missing/blank, then FY − ΣQ1..Q3.
- Filing errors handled: AXIA ITR Q3-2024/Q3-2025 and SUZB Q1-2024 left 3.11.01 blank (0) → we use
  3.11 (consolidated) for those rows. ITUB ITR 2012 has only Q1 (Q2/Q3-2012 missing → no Q4-2012).
- Sanity (verified 2026-10-03 vs probe, BRL bn): FY2025 revenue / consolidated NI — PETR 497.55 / 110.61
  (to controlling 110.13), VALE 213.59 / 11.81 (to controlling 13.81: NCI −2.0), SUZB 50.12 / 13.44,
  AXIA 41.28 / 6.56; PETR Q2-2026 169.53 / 52.49 (to controlling 52.45).
  main() re-checks these and asserts Σ quarters 2025 == DFP FY (±0.5 %) for every flow.

Run:  .venv/bin/python ingest/cvm_financials.py
"""
from __future__ import annotations
import sys, pathlib, re, zipfile, datetime as dt
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _http import cached, write_bronze, COMPANIES  # noqa: E402

BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
FIRST_YEAR = 2012
SOURCE, THEME, FREQ, UNIT = "cvm_itr_dfp", "companies", "quarterly", "brl_bn"

CNPJ = {
    "33.000.167/0001-01": "PETR",
    "33.592.510/0001-54": "VALE",
    "00.001.180/0001-26": "AXIA",
    "16.404.287/0001-55": "SUZB",
    "10.629.105/0001-68": "PRIO",
    "60.872.504/0001-23": "ITUB",
}
BANKS = {"ITUB"}

# metric_id -> (metric_name, kind) ; kind: flow (DRE quarter rows) | ytd (DFC) | stock (balance)
SERIES = {
    "revenue_brl":        ("Revenue (net sales)", "flow"),
    "ebit_brl":           ("EBIT (result before financial result and taxes)", "flow"),
    "net_income_brl":     ("Net income attributable to controlling shareholders", "flow"),
    "gross_debt_brl":     ("Gross debt (loans, financing, debentures, leases)", "stock"),
    "cash_brl":           ("Cash, equivalents and financial investments", "stock"),
    "capex_brl":          ("Capex (additions to PP&E and intangibles, cash)", "ytd"),
    "dividends_paid_brl": ("Dividends and JCP paid to shareholders (cash)", "ytd"),
}
BANK_NAME = {"revenue_brl": "Revenue (bank: financial intermediation income)"}
BANK_METRICS = {"revenue_brl", "net_income_brl"}

# (statement, code, description regex) — every selected row must match its description
ACCOUNTS = {
    "revenue_brl":    [("DRE", "3.01", r"^Receita")],
    "ebit_brl":       [("DRE", "3.05", r"^Resultado Antes do Resultado Financeiro e dos Tributos")],
    "net_income_brl": [("DRE", ("3.11.01", "3.09.01"), r"^Atribu.do a S.cios da Empresa Controladora")],
    "gross_debt_brl": [("BPP", "2.01.04", r"^Empr.stimos e Financiamentos$"),
                       ("BPP", "2.02.01", r"^Empr.stimos e Financiamentos$")],
    "cash_brl":       [("BPA", "1.01.01", r"^Caixa e Equivalentes de Caixa$"),
                       ("BPA", "1.01.02", r"^Aplica..es Financeiras$")],
}
NI_PARENT = r"^Lucro/Preju.zo Consolidado do Per.odo"

CAPEX_INC = re.compile(
    r"imobiliz|intang|ativos? biol|ativos? de concess|ativo financeiro - transmiss"
    r"|infraestrutura da transmiss|^investimentos em (?:explora|refino|abastec|g.s e energia|distribui|biocomb)", re.I)
CAPEX_EXC = re.compile(r"alien|recebiment|recursos|baixa|mantido para venda|adiantamento"
                       r"|investimentos em t.tulos|subsidi|controlad", re.I)
DIV_INC = re.compile(r"dividend|juros s(?:obre|/) ?(?:o )?capital|jcp|remunera..o aos acionistas", re.I)
DIV_EXC = re.compile(r"n.o controlador|recebid", re.I)

CSV_COLS = ["CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA", "ESCALA_MOEDA", "ORDEM_EXERC",
            "DT_INI_EXERC", "DT_FIM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA"]


def _zip(kind: str, year: int) -> pathlib.Path:
    K = kind.upper()
    cur = dt.date.today().year
    # current-year ITR and last DFP keep receiving filings/re-filings → refresh weekly
    age = 7 if year >= cur - 1 else None
    return cached(f"{BASE}/{K}/DADOS/{kind}_cia_aberta_{year}.zip", f"cvm_{kind}_{year}.zip",
                  max_age_days=age, timeout=300)


def load_rows() -> pd.DataFrame:
    """All consolidated DRE/BPA/BPP/DFC_MI rows for our CNPJs, every ITR/DFP year."""
    frames = []
    last = dt.date.today().year
    for year in range(FIRST_YEAR, last + 1):
        for kind in ("itr", "dfp"):
            try:
                z = zipfile.ZipFile(_zip(kind, year))
            except Exception as e:  # noqa: BLE001 — DFP for the current year doesn't exist yet
                if year == last:
                    continue
                raise RuntimeError(f"{kind} {year}: {e}") from e
            for st in ("DRE", "BPA", "BPP", "DFC_MI"):
                df = pd.read_csv(z.open(f"{kind}_cia_aberta_{st}_con_{year}.csv"), sep=";",
                                 encoding="latin-1", dtype=str, usecols=lambda c: c in CSV_COLS)
                df = df.reindex(columns=CSV_COLS)  # BPA/BPP have no DT_INI_EXERC (stocks)
                df = df[df.CNPJ_CIA.isin(CNPJ)].copy()
                df["entity_id"], df["kind"], df["st"] = df.CNPJ_CIA.map(CNPJ), kind, st
                frames.append(df)
    d = pd.concat(frames, ignore_index=True)
    mult = d.ESCALA_MOEDA.map({"MIL": 1e3, "UNIDADE": 1.0})
    if mult.isna().any():
        raise ValueError(f"unknown ESCALA_MOEDA {d.ESCALA_MOEDA[mult.isna()].unique()}")
    d["v"] = d.VL_CONTA.astype(float) * mult / 1e9
    d["VERSAO"] = d.VERSAO.astype(int)
    for c in ("DT_REFER", "DT_INI_EXERC", "DT_FIM_EXERC"):
        d[c] = pd.to_datetime(d[c])
    return d


def latest_version(d: pd.DataFrame) -> pd.DataFrame:
    d = d[d.ORDEM_EXERC == "ÚLTIMO"]
    vmax = d.groupby(["entity_id", "kind", "DT_REFER"]).VERSAO.transform("max")
    return d[d.VERSAO == vmax]


def _qstart(ts: pd.Series) -> pd.Series:
    return ts.dt.to_period("Q").dt.start_time


def pick_accounts(d: pd.DataFrame, mid: str) -> pd.DataFrame:
    """Rows for a coded metric, description-checked; summed per (entity, kind, period)."""
    parts = []
    for st, code, rx in ACCOUNTS[mid]:
        codes = code if isinstance(code, tuple) else (code,)
        x = d[(d.st == st) & d.CD_CONTA.isin(codes)]
        ok = x.DS_CONTA.str.contains(rx, regex=True)
        bad = x[~ok & ~x.entity_id.isin(BANKS)]
        if not bad.empty:
            print(f"[warn] {mid}: {len(bad)} rows with unexpected description, e.g. "
                  f"{bad.entity_id.iloc[0]} {bad.CD_CONTA.iloc[0]} '{bad.DS_CONTA.iloc[0]}' — dropped")
        x = x[ok]
        if mid == "net_income_brl":
            x = _ni_with_fallback(d, x)
        parts.append(x.assign(acct=f"{st}:{codes[0]}"))
    x = pd.concat(parts)
    g = x.groupby(["entity_id", "kind", "DT_REFER", "DT_INI_EXERC", "DT_FIM_EXERC"], dropna=False)
    out = g.agg(v=("v", "sum"), n=("acct", "nunique")).reset_index()
    return out[out.n == len(ACCOUNTS[mid])]  # stocks need every component present


def _ni_with_fallback(d: pd.DataFrame, child: pd.DataFrame) -> pd.DataFrame:
    """NI attributable to controlling holders (child of 'Lucro/Prejuízo Consolidado do Período').
    Some filings leave the split blank (=0) while the consolidated line is filled (e.g. AXIA
    ITR Q3-2025: 3.11.01 = 0, 3.11 = −5.45 bn) → fall back to the consolidated line there."""
    k = ["entity_id", "kind", "DT_REFER", "DT_INI_EXERC", "DT_FIM_EXERC"]
    par = d[(d.st == "DRE") & d.DS_CONTA.str.contains(NI_PARENT, regex=True)]
    child = child.assign(pcode=child.CD_CONTA.str.rsplit(".", n=1).str[0])
    j = child.merge(par[k + ["CD_CONTA", "v"]].rename(columns={"CD_CONTA": "pcode", "v": "pv"}),
                    on=k + ["pcode"], how="inner")  # child must sit under the consolidated line
    fb = (j.v == 0) & (j.pv != 0)
    if fb.any():
        print(f"[info] net_income_brl: {fb.sum()} rows with blank controlling-holder split → used "
              f"consolidated line: " + ", ".join(sorted({f"{e} {r:%Y-%m}" for e, r in
                                                          zip(j.entity_id[fb], j.DT_REFER[fb])})))
    j.loc[fb, "v"] = j.loc[fb, "pv"]
    return j.drop(columns=["pcode", "pv"])


def pick_dfc(d: pd.DataFrame, mid: str) -> pd.DataFrame:
    x = d[(d.st == "DFC_MI") & ~d.entity_id.isin(BANKS)]
    if mid == "capex_brl":
        x = x[x.CD_CONTA.str.fullmatch(r"6\.02\.\d+")]
        x = x[x.DS_CONTA.str.contains(CAPEX_INC) & ~x.DS_CONTA.str.contains(CAPEX_EXC)]
    else:
        x = x[x.CD_CONTA.str.fullmatch(r"6\.03\.\d+")]
        x = x[x.DS_CONTA.str.contains(DIV_INC) & ~x.DS_CONTA.str.contains(DIV_EXC)]
    k = ["entity_id", "kind", "DT_REFER", "DT_INI_EXERC", "DT_FIM_EXERC"]
    out = x.groupby(k).v.sum()
    if mid == "dividends_paid_brl":
        # no dividend line in a filed DFC = nothing paid that YTD (e.g. PRIO, which pays via buybacks)
        filed = d[(d.st == "DFC_MI") & ~d.entity_id.isin(BANKS)].drop_duplicates(k).set_index(k).index
        out = out.reindex(filed, fill_value=0.0)
    out = out.reset_index()
    out["v"] = -out.v  # cash out → positive
    return out, x


def quarterly_flow(x: pd.DataFrame) -> pd.DataFrame:
    """DRE: Q1–Q3 from quarter-only ITR rows; Q4 = DFP FY − ITR 9M YTD."""
    itr = x[x.kind == "itr"]
    q = itr[itr.DT_INI_EXERC == _qstart(itr.DT_FIM_EXERC)][["entity_id", "DT_FIM_EXERC", "v"]]
    ytd9 = itr[(itr.DT_FIM_EXERC.dt.month == 9) & (itr.DT_INI_EXERC.dt.month == 1)]
    ytd9 = ytd9.set_index(["entity_id", ytd9.DT_FIM_EXERC.dt.year.rename("y")]).v
    q13 = q[q.DT_FIM_EXERC.dt.month <= 9]
    q13 = q13.groupby(["entity_id", q13.DT_FIM_EXERC.dt.year.rename("y")]).v.agg(["sum", "count"])
    q13 = q13[q13["count"] == 3]["sum"]
    # 9M base: the 9M YTD row (same basis as FY after intra-year restatements); fall back to
    # Q1+Q2+Q3 when the YTD row is missing or blank (0) while the quarters are not.
    base = ytd9.reindex(ytd9.index.union(q13.index))
    bad = base.isna() | ((base == 0) & q13.reindex(base.index).fillna(0).ne(0))
    base[bad] = q13.reindex(base.index)[bad]
    fy = x[(x.kind == "dfp") & (x.DT_INI_EXERC.dt.month == 1) & (x.DT_FIM_EXERC.dt.month == 12)]
    q4 = fy.assign(y=fy.DT_FIM_EXERC.dt.year).join(base.rename("v_9m"), on=["entity_id", "y"])
    q4 = q4.dropna(subset=["v_9m"])
    q4 = q4.assign(v=q4.v - q4.v_9m)[["entity_id", "DT_FIM_EXERC", "v"]]
    return pd.concat([q, q4]).rename(columns={"DT_FIM_EXERC": "date"})


def quarterly_from_ytd(x: pd.DataFrame) -> pd.DataFrame:
    """DFC: YTD (Jan 1 → quarter end) from ITR Q1–Q3 + DFP FY; difference within each year."""
    x = x[x.DT_INI_EXERC.dt.month == 1].copy()
    x["date"], x["y"] = x.DT_FIM_EXERC, x.DT_FIM_EXERC.dt.year
    x = x.drop_duplicates(["entity_id", "date"], keep="last").sort_values(["entity_id", "date"])
    x["prev_date"] = x.groupby(["entity_id", "y"]).date.shift()
    x["prev"] = x.groupby(["entity_id", "y"]).v.shift()
    q1 = x.date.dt.month == 3
    contiguous = q1 | ((x.date.dt.month - x.prev_date.dt.month) == 3)  # no gap in the YTD chain
    x = x[contiguous]
    x["v"] = x.v - x.prev.where(~q1, 0.0)
    return x[["entity_id", "date", "v"]]


def stock(x: pd.DataFrame) -> pd.DataFrame:
    return x[x.DT_FIM_EXERC == x.DT_REFER][["entity_id", "DT_FIM_EXERC", "v"]].rename(
        columns={"DT_FIM_EXERC": "date"})


def restatement_report(raw: pd.DataFrame) -> None:
    """FY revenue/NI: original (DFP y ÚLTIMO) vs re-presented next year (DFP y+1 PENÚLTIMO)."""
    d = raw[(raw.kind == "dfp") & (raw.st == "DRE") & raw.CD_CONTA.isin(["3.01", "3.11.01", "3.09.01"])]
    vmax = d.groupby(["entity_id", "DT_REFER"]).VERSAO.transform("max")
    d = d[d.VERSAO == vmax]
    u = d[d.ORDEM_EXERC == "ÚLTIMO"].set_index(["entity_id", "CD_CONTA", "DT_FIM_EXERC"]).v
    p = d[d.ORDEM_EXERC == "PENÚLTIMO"].set_index(["entity_id", "CD_CONTA", "DT_FIM_EXERC"]).v
    j = pd.concat([u.rename("orig"), p.rename("restated")], axis=1).dropna()
    j = j[(j.orig - j.restated).abs() > 0.005 * j.orig.abs().clip(lower=1e-9)]
    print(f"[info] restatements: {len(j)} FY revenue/NI figures re-presented >0.5% in the next DFP "
          f"(kept ORIGINAL ÚLTIMO values): "
          + ", ".join(f"{e} {c} {d.year}: {r.orig:.1f}→{r.restated:.1f}" for (e, c, d), r in j.iterrows()))


def main():
    raw = load_rows()
    d = latest_version(raw)
    print(f"[info] {len(raw):,} raw rows; names: "
          + "; ".join(f"{e}={'/'.join(sorted(g.unique()))}" for e, g in
                      raw.assign(n=raw.DENOM_CIA).groupby("entity_id").n))
    series, checks = {}, {}
    for mid, (name, kind) in SERIES.items():
        if kind == "ytd":
            x, lines = pick_dfc(d, mid)
            q = quarterly_from_ytd(x)
            used = lines.groupby(["entity_id"]).DS_CONTA.unique()
            for e, descs in used.items():
                print(f"[acct] {mid} {e}: {sorted(set(descs))[:8]}{' …' if len(set(descs)) > 8 else ''}")
            fy = x[(x.kind == "dfp") & (x.DT_INI_EXERC.dt.month == 1)]
        else:
            x = pick_accounts(d, mid)
            q = quarterly_flow(x) if kind == "flow" else stock(x)
            fy = x[(x.kind == "dfp") & (x.DT_INI_EXERC.dt.month == 1)] if kind == "flow" else None
        if kind != "stock":
            # 2025: Σ quarters == DFP FY (±0.5 %) — and Q1–Q3 quarter rows vs 9M YTD for DRE
            for e, fv in fy[fy.DT_FIM_EXERC.dt.year == 2025].set_index("entity_id").v.items():
                s = q[(q.entity_id == e) & (q.date.dt.year == 2025)]
                assert len(s) == 4, f"{mid} {e}: {len(s)} quarters in 2025"
                assert abs(s.v.sum() - fv) <= 0.005 * max(abs(fv), 1e-6) + 1e-6, \
                    f"{mid} {e} 2025: Σq={s.v.sum():.3f} vs FY={fv:.3f}"
            checks[mid] = fy
            if kind == "flow":
                itr = x[x.kind == "itr"]
                qq = itr[itr.DT_INI_EXERC == _qstart(itr.DT_FIM_EXERC)]
                q13 = qq[qq.DT_FIM_EXERC.dt.month <= 9].groupby(
                    ["entity_id", qq.DT_FIM_EXERC.dt.year]).v.agg(["sum", "count"])
                y9 = itr[(itr.DT_FIM_EXERC.dt.month == 9) & (itr.DT_INI_EXERC.dt.month == 1)]
                y9 = y9.groupby(["entity_id", y9.DT_FIM_EXERC.dt.year]).v.sum()
                j = q13[q13["count"] == 3].join(y9.rename("ytd"), how="inner")
                j["gap"] = (j["sum"] - j.ytd).abs() / j.ytd.abs().clip(lower=0.05)
                off = j[j.gap > 0.005]
                print(f"[chk]  {mid}: Q1+Q2+Q3 vs 9M YTD differ >0.5% in {len(off)}/{len(j)} company-years "
                      "(intra-year restatements; Q4 uses the 9M YTD basis): "
                      + ", ".join(f"{e} {y}" for e, y in off.index))
        if mid not in BANK_METRICS:
            q = q[~q.entity_id.isin(BANKS)]
        q = q.sort_values(["entity_id", "date"])
        q = q.assign(metric_id=mid, theme=THEME, source_id=SOURCE, freq=FREQ, unit=UNIT,
                     value=q.v.round(4),
                     metric_name=[BANK_NAME.get(mid, name) if e in BANKS else name for e in q.entity_id])
        n = write_bronze(q, COMPANIES / f"{mid}.csv", entity=True)
        series[mid] = q
        last = q.groupby("entity_id").tail(1)
        print(f"[ok]   {mid:<19} {n} obs ({q.date.min():%Y-%m-%d}..{q.date.max():%Y-%m-%d}) latest: "
              + ", ".join(f"{r.entity_id} {r.date.year}Q{(r.date.month - 1) // 3 + 1}={r.value:.2f}"
                          for r in last.itertuples()))

    # sanity vs the probe (BRL bn). The probe's NI was the CONSOLIDATED line (3.11, incl.
    # non-controlling interests); our net_income_brl is the controlling-holder share (3.11.01).
    cons = d[(d.st == "DRE") & (d.CD_CONTA == "3.11") & d.DS_CONTA.str.contains(NI_PARENT, regex=True)]
    probe = {("PETR", 2025): (497.5, 110.6), ("VALE", 2025): (213.6, 11.8),
             ("SUZB", 2025): (50.1, 13.4), ("AXIA", 2025): (41.3, 6.6), ("PETR", "2026Q2"): (169.5, 52.5)}
    bad = []
    for (e, per), (rev_w, ni_w) in probe.items():
        if per == 2025:
            rv = checks["revenue_brl"]; rv = rv[(rv.entity_id == e) & (rv.DT_FIM_EXERC.dt.year == 2025)].v.iloc[0]
            na = checks["net_income_brl"]
            na = na[(na.entity_id == e) & (na.DT_FIM_EXERC.dt.year == 2025)].v.iloc[0]
            c = cons[(cons.entity_id == e) & (cons.kind == "dfp") & (cons.DT_FIM_EXERC.dt.year == 2025)]
        else:
            sr, sn = series["revenue_brl"], series["net_income_brl"]
            rv = sr[(sr.entity_id == e) & (sr.date == "2026-06-30")].value.iloc[0]
            na = sn[(sn.entity_id == e) & (sn.date == "2026-06-30")].value.iloc[0]
            c = cons[(cons.entity_id == e) & (cons.DT_FIM_EXERC == "2026-06-30")
                     & (cons.DT_INI_EXERC == "2026-04-01")]
        nc = c.v.iloc[0]
        ok = all(abs(g - w) <= 0.06 + 0.005 * abs(w) for g, w in ((rv, rev_w), (nc, ni_w)))
        bad += [] if ok else [(e, per)]
        print(f"[sanity] {e} {per}: revenue {rv:.2f} (probe {rev_w}) | NI consolidated {nc:.2f} "
              f"(probe {ni_w}) | NI to controlling (emitted) {na:.2f}  {'ok' if ok else 'MISMATCH'}")
    assert not bad, f"sanity mismatches: {bad}"
    restatement_report(raw)


if __name__ == "__main__":
    main()
