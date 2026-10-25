"""Study 1 — Congress composition and president–Congress alignment, 1987–2027, with the foreign-policy angle.
Executes PART A of plan.md. numpy / pandas / duckdb / plotly only. seed = 0.
Run: /Users/zkid18/proj-personal/brazil-macro/.venv/bin/python congress_study.py
"""
import json, re, datetime as dt
import numpy as np, pandas as pd
from congress_core import *          # con, q, SQL, META, A, dlog, TOT/LTOT/DLTOT, estimators, event engine
import congress_core as CC

assert (OUT / "preregistration.txt").exists(), "preregistration.txt must exist before any analysis"
NUMS = []   # every emitted warehouse number: {value, series_id, source, last_date, sql}


def emit(name, value, sid, sqlname, note=""):
    m = META.get(sid, {})
    NUMS.append(dict(name=name, value=None if value is None or (isinstance(value, float) and np.isnan(value)) else round(float(value), 4),
                     series_id=sid, source=m.get("source"), last_date=m.get("last_date"), sql=sqlname, note=note))
    return value


# ============================================================================ 1. anchors
def anchors():
    a = {}
    a["political_terms"] = q("anchor_terms", "SELECT count(*) n, max(\"end\") last_end FROM political_terms").iloc[0].to_dict()
    a["political_events"] = q("anchor_events", "SELECT count(*) n, max(date) AS last_date FROM political_events").iloc[0].to_dict()
    a["congress_tables"] = q("anchor_tables", "SELECT table_name FROM information_schema.tables WHERE table_name ILIKE '%congress%' OR table_name ILIKE '%emend%'").table_name.tolist()
    assert int(a["political_terms"]["n"]) == 9 and str(a["political_terms"]["last_end"])[:10] == "2027-01-01"
    assert int(a["political_events"]["n"]) == 34 and str(a["political_events"]["last_date"])[:10] == "2026-10-04"
    assert a["congress_tables"] == []
    cov = q("anchor_coverage", """SELECT series_id, min(date) AS first_date, max(date) AS last_date FROM v_observations
        WHERE date <= current_date AND series_id IN ('primary_balance_gdp','gross_public_debt_gdp','embi_brazil','gov_real_yield_10y',
        'real_policy_rate','wb/GC.NFN.TOTL.GD.ZS.BR','ibovespa_usd','wb/FP.CPI.TOTL.ZG.BR') GROUP BY 1 ORDER BY 1""")
    a["coverage"] = {r.series_id: [str(r.first_date)[:10], str(r.last_date)[:10]] for r in cov.itertuples()}
    assert a["coverage"]["embi_brazil"][1] == "2024-07-30" and a["coverage"]["gov_real_yield_10y"][0] == "2015-01-02"
    assert "wb/FP.CPI.TOTL.ZG.BR" not in a["coverage"]
    # 0.5 prototypes: t-1 -> t+20 trading days
    protos = {"2016-04-17": -3.8, "2016-12-15": 13.0, "2017-07-13": 5.7, "2019-07-10": -6.1, "2019-10-22": -0.3, "2019-11-12": 4.9,
              "2021-02-24": -4.2, "2023-08-31": -3.6, "2023-12-20": -5.6, "2025-04-11": 15.4, "2025-11-27": -2.5, "2025-12-12": 4.8}
    x = DS["ibovespa_usd"]; got = {}
    for d, exp in protos.items():
        i = x.index.searchsorted(pd.Timestamp(d)); v = 100 * (x.iloc[i + 20] / x.iloc[i - 1] - 1)
        got[d] = round(v, 1); assert abs(v - exp) < 0.051, (d, v, exp)
    y = DS["gov_real_yield_10y"]; i = y.index.searchsorted(pd.Timestamp("2021-02-24"))
    assert (round(y.iloc[i - 1], 2), round(y.iloc[i + 20], 2)) == (3.31, 3.88)
    a["event_prototypes_ibov_usd_pct"] = got
    a["status"] = "all plan 0.1 / 0.4 / 0.5 anchors reproduced"
    return a


# ============================================================================ 2. legislatures / dyads
LEG = [(48, "1987-02-01", "1991-02-01", 1986), (49, "1991-02-01", "1995-02-01", 1990), (50, "1995-02-01", "1999-02-01", 1994),
       (51, "1999-02-01", "2003-02-01", 1998), (52, "2003-02-01", "2007-02-01", 2002), (53, "2007-02-01", "2011-02-01", 2006),
       (54, "2011-02-01", "2015-02-01", 2010), (55, "2015-02-01", "2019-02-01", 2014), (56, "2019-02-01", "2023-02-01", 2018),
       (57, "2023-02-01", "2027-02-01", 2022), (58, "2027-02-01", "2031-02-01", 2026)]
SHORTP = {"José Sarney": "Sarney", "Fernando Collor": "Collor", "Itamar Franco": "Itamar", "Fernando Henrique Cardoso": "FHC",
          "Luiz Inácio Lula da Silva": "Lula", "Dilma Rousseff": "Dilma", "Michel Temer": "Temer", "Jair Bolsonaro": "Bolsonaro"}
LEAN_A = {"Sarney": "centre", "Collor": "right", "Itamar": "centre", "FHC": "right", "Lula": "left", "Dilma": "left",
          "Temer": "right", "Bolsonaro": "right"}
DYAD_SQL = """
WITH leg AS (SELECT * FROM (VALUES
  (48, DATE '1987-02-01', DATE '1991-02-01'), (49, DATE '1991-02-01', DATE '1995-02-01'),
  (50, DATE '1995-02-01', DATE '1999-02-01'), (51, DATE '1999-02-01', DATE '2003-02-01'),
  (52, DATE '2003-02-01', DATE '2007-02-01'), (53, DATE '2007-02-01', DATE '2011-02-01'),
  (54, DATE '2011-02-01', DATE '2015-02-01'), (55, DATE '2015-02-01', DATE '2019-02-01'),
  (56, DATE '2019-02-01', DATE '2023-02-01'), (57, DATE '2023-02-01', DATE '2027-02-01'),
  (58, DATE '2027-02-01', DATE '2031-02-01')) AS t(leg_id, start, "end")),
dyad AS (
  SELECT l.leg_id, p.president, p.party, p.lean,
         greatest(l.start, p.start) AS start, least(l."end", p."end") AS "end"
  FROM leg l JOIN political_terms p ON p.start < l."end" AND p."end" > l.start)
SELECT row_number() OVER (ORDER BY start) AS dyad_id, *, date_diff('month', start, "end") AS months
FROM dyad WHERE date_diff('month', start, "end") >= 12 ORDER BY start"""


def legislatures():
    d = q("dyads", DYAD_SQL)
    d["start"] = pd.to_datetime(d.start); d["end"] = pd.to_datetime(d["end"])
    d["pres"] = d.president.map(SHORTP)
    d["dyad"] = d.pres + "×" + d.leg_id.astype(str)
    d["lean3"] = d.pres.map(LEAN_A)
    # Lula x57 runs to 2027-01-01 (political_terms end); its last months are the live 2026 data
    return d


DY = legislatures()
assert len(DY) == 12, DY   # plan says 13 historical but that count includes Collor×48 (10.5 m), which its own 12-month rule drops


def dyad_of_date(ts):
    ts = pd.Timestamp(ts)
    m = DY[(DY.start <= ts) & (DY["end"] > ts)]
    return None if m.empty else m.dyad.iloc[0]


ATTR = pd.DataFrame({"year": range(1987, 2027)}).set_index("year")
ATTR["c"] = [dyad_of_date(f"{y}-07-01") for y in ATTR.index]
ATTR["lag1"] = [dyad_of_date(f"{y - 1}-07-01") for y in ATTR.index]
first_year = {}
for y, d_ in ATTR.c.items():
    if d_ is not None and d_ not in first_year:
        first_year[d_] = y
ATTR["first"] = [first_year.get(d_) == y for y, d_ in ATTR.c.items()]

# ============================================================================ 3. external panel
FAMILY = {"PMDB": "MDB", "MDB": "MDB", "PFL": "União", "DEM": "União", "União": "União", "UNIÃO": "União", "União Brasil": "União",
          "PDS": "PP", "PPR": "PP", "PPB": "PP", "PP": "PP", "Progressistas": "PP", "PRB": "Republicanos", "Republicanos": "Republicanos",
          "PR": "PL", "PL": "PL", "PTN": "Podemos", "Podemos": "Podemos", "PODE": "Podemos", "PRN": "Agir", "PTC": "Agir", "Agir": "Agir",
          "PSDC": "DC", "DC": "DC", "PPS": "Cidadania", "Cidadania": "Cidadania", "PTdoB": "Avante", "Avante": "Avante",
          "SD": "Solidariedade", "Solidariedade": "Solidariedade", "PCdoB": "PCdoB", "PC do B": "PCdoB", "PT": "PT", "PSDB": "PSDB",
          "PSB": "PSB", "PDT": "PDT", "PTB": "PRD", "PEN": "PRD", "Patriota": "PRD", "PRD": "PRD", "PSOL": "PSOL", "REDE": "Rede",
          "Rede": "Rede", "NOVO": "Novo", "Novo": "Novo", "PV": "PV", "PSL": "União", "PSD": "PSD", "PSC": "Podemos", "PHS": "Podemos",
          "PROS": "Solidariedade", "PMN": "PMN", "PRP": "Patriota", "PRTB": "PRTB", "Missão": "Missão", "PCB": "PCB", "PMB": "PMB",
          "PSTU": "PSTU", "PCO": "PCO", "PPL": "PCdoB", "PRONA": "PL", "PSD_old": "PSD_old", "PST": "PL", "PSN": "Podemos", "PJ": "Agir"}
BLS_CODE = {"MDB": "MDB", "PMDB": "MDB", "PFL": "DEM", "DEM": "DEM", "PDS": "PP", "PPR": "PP", "PPB": "PP", "PP": "PP", "PRN": "PRN",
            "PL": "PL", "PR": "PL", "PPS": "CID", "Cidadania": "CID", "PCdoB": "PCDOB", "PRB": "REP", "Republicanos": "REP",
            "Podemos": "PODE", "PTN": "PODE", "SD": "SD", "Solidariedade": "SD", "PSL": "PSL", "PSDB": "PSDB", "PT": "PT", "PDT": "PDT",
            "PSB": "PSB", "PTB": "PTB", "PRD": "PTB", "PV": "PV", "PSOL": "PSOL", "Rede": "REDE", "REDE": "REDE", "Novo": "NOVO",
            "NOVO": "NOVO", "PSC": "PSC", "PROS": "PROS", "PDC": "PDC", "PSD": "PSD", "PSTU": "PSTU"}
BOLO_CODE = {"MDB": "MDB", "PMDB": "MDB", "PFL": "DEM", "DEM": "DEM", "PDS": "Progressistas", "PPR": "Progressistas", "PPB": "Progressistas",
             "PP": "Progressistas", "PRN": "PTC", "PTC": "PTC", "Agir": "PTC", "PL": "PR", "PR": "PR", "PPS": "PPS", "Cidadania": "PPS",
             "PCdoB": "PCdoB", "PRB": "PRB", "Republicanos": "PRB", "Podemos": "Podemos", "PTN": "Podemos", "SD": "SDD", "Solidariedade": "SDD",
             "PSL": "PSL", "PSDB": "PSDB", "PT": "PT", "PDT": "PDT", "PSB": "PSB", "PTB": "PTB", "PV": "PV", "PSOL": "PSOL", "Rede": "Rede",
             "Novo": "Novo", "PSC": "PSC", "PROS": "Pros", "Avante": "Avante", "PTdoB": "Avante", "PHS": "PHS", "PMN": "PMN", "DC": "DC",
             "PSDC": "DC", "Patriota": "Patriota", "PEN": "Patriota", "PRP": "PRP", "PRTB": "PRTB", "PMB": "PMB", "PSD": "PSD", "PSTU": "PSTU",
             "PCO": "PCO", "PCB": "PCB", "PPL": "PPL"}
PRES_PARTY = {"Sarney": ["PMDB"], "Collor": ["PRN"], "Itamar": [], "FHC": ["PSDB"], "Lula": ["PT"], "Dilma": ["PT"],
              "Temer": ["PMDB", "MDB"], "Bolsonaro": ["PSL"], "Lula IV": ["PT"], "Flávio": ["PL"]}
WAVES = [1990, 1993, 1997, 2001, 2005, 2009, 2013, 2017, 2021]


def norm_party(p):
    p = str(p).strip()
    return {"PC do B": "PCdoB", "PCDOB": "PCdoB", "UNIÃO": "União", "União Brasil": "União", "UNIAO": "União", "SOLIDARIEDADE": "Solidariedade",
            "PODEMOS": "Podemos", "PODE": "Podemos", "REPUBLICANOS": "Republicanos", "CIDADANIA": "Cidadania", "AVANTE": "Avante",
            "PATRIOTA": "Patriota", "PROGRESSISTAS": "PP", "MISSÃO": "Missão", "Missao": "Missão", "REDE": "Rede", "NOVO": "Novo"}.get(p, p)


def load_ideology():
    b = pd.read_csv(RES / "ideology_bls.csv")
    b = b[b.president_placement_flag == 0]
    bls = {(int(r.wave_year), r.party): (r.score + 1) * 5 for r in b.itertuples()}     # -1..1 -> 0..10
    bp = pd.read_csv(RES / "ideology_bls.csv"); bp = bp[bp.president_placement_flag == 1]
    pres = {}
    for r in bp.itertuples():
        pres.setdefault(r.party, []).append((int(r.wave_year), (r.score + 1) * 5, str(r.note)))
    g = pd.read_csv(RES / "ideology_bolognesi.csv")
    bolo = dict(zip(g.party, g.score))
    return bls, pres, bolo


BLS, BLS_PRES, BOLO = load_ideology()
# president placements on the BLS 0-10 scale: contemporaneous where available, else the 2013 retrospective wave
def pres_bls(pres):
    key = {"Sarney": "SARNEY", "Collor": "COLLOR", "Itamar": "ITAMAR", "FHC": "FHC", "Lula": "LULA", "Dilma": "DILMA",
           "Temer": "TEMER", "Bolsonaro": "BOLSONARO"}[pres]
    rows = BLS_PRES.get(key, [])
    contemp = [r for r in rows if "SITTING" in r[2]]
    pick = (contemp or [r for r in rows if r[0] == 2013] or rows)
    return float(np.mean([r[1] for r in pick])) if pick else np.nan


def bls_score(party, leg_start_year):
    code = BLS_CODE.get(party)
    if party == "União":
        return (0.66 + 1) * 5, "União = Zucco-Power 2023 DEM/PSL weighted average 0.66 (not a survey score)"
    if code is None:
        return np.nan, "no BLS score"
    avail = sorted([w for w in WAVES if (w, code) in BLS], key=lambda w: (abs(w - leg_start_year), w))
    if not avail:
        return np.nan, "no BLS score"
    w = avail[0]
    return BLS[(w, code)], f"BLS wave {w}"


def bolo_score(party):
    if party == "União":
        return (BOLO["DEM"] * 29 + BOLO["PSL"] * 52) / 81, "União = DEM/PSL seat-weighted (2018 seats 29/52)"
    if party == "PRD":
        return (BOLO["PTB"] + BOLO["Patriota"]) / 2, "PRD = mean(PTB, Patriota)"
    c = BOLO_CODE.get(party)
    return (BOLO.get(c, np.nan), "Bolognesi 2018") if c else (np.nan, "no Bolognesi score")


CENTRAO_NARROW = {"PP", "PDS", "PPR", "PPB", "PTB", "PRB", "Republicanos", "Solidariedade", "SD", "Avante", "PTdoB", "PROS", "PSC",
                  "Podemos", "PTN", "PRD"}


def centrao(party, leg_id):
    narrow = party in CENTRAO_NARROW or (party in ("PL", "PR") and leg_id <= 56) or (party == "PSD" and leg_id >= 54) or \
        (party == "União" and leg_id >= 57)
    broad = narrow or party in ("PMDB", "MDB", "PFL", "DEM") or (party == "PSDB" and leg_id >= 56)
    return int(narrow), int(broad)


def read_seats():
    c = pd.read_csv(RES / "chamber_seats.csv")
    c["party"] = c.party.map(norm_party)
    c.loc[(c.party == "PSD") & (c.election_year < 2010), "party"] = "PSD_old"   # old PSD (1987-2003) is a different party
    s = pd.read_csv(RES / "senate_seats.csv")
    s["party"] = s.party.map(norm_party)
    s.loc[(s.party == "PSD") & (s.leg_start_year < 2011), "party"] = "PSD_old"
    return c, s


def coalition_table():
    """coalition = parties holding ministries (Amorim Neto / Figueiredo convention). Bolsonaro 2019: no formal coalition;
    coded as the parties of his party-affiliated ministers (PSL, DEM, NOVO) and flagged."""
    c = pd.read_csv(RES / "coalitions.csv")
    out = {}
    for r in c.itertuples():
        m = re.match(r"(\w+) x (\d+)", str(r.dyad))
        if not m:
            continue
        dyad = f"{m.group(1)}×{m.group(2)}"
        if "pre-49" in str(r.dyad):
            continue
        txt = str(r.coalition_parties)
        if txt.lower() == "nan":
            continue
        txt = re.sub(r"\(PSB left 2013\)", "", txt)
        txt = txt.replace("none formal (ministers from ", "").replace(" ministers (centrao entry)", "").replace(")", "")
        parties = []
        for p_ in re.split(r"[;/]", txt):
            p_ = norm_party(p_.strip())
            if p_:
                parties.append(p_)
        if dyad == "Dilma×54" and r.timing == "mid":
            parties = [p_ for p_ in parties if p_ != "PSB"]
        sh = pd.to_numeric(r.coalition_share_cd, errors="coerce")
        out[(dyad, r.timing)] = dict(parties=parties, share_src=sh / 100 if sh == sh else np.nan, date=r.date, url=r.source_url,
                                     note=("NO FORMAL COALITION: ministers' parties" if "none formal" in str(r.coalition_parties) else r.note))
    return out


def coalition_key(dyad):
    return dyad


def build_seats():
    ch, se = read_seats()
    COAL = coalition_table()
    rows = []
    for leg_id, start, end, ey in LEG:
        for chamber, df, keycol, ycol in (("CD", ch, "seats_election", "election_year"), ("SF", se, "seats_start", "leg_start_year")):
            yy = ey if chamber == "CD" else int(start[:4])
            sub = df[(df[ycol] == yy)].copy()
            sub = sub[pd.to_numeric(sub[keycol], errors="coerce").fillna(0) > 0]
            if sub.empty:
                continue
            seats = sub[keycol].astype(float)
            if chamber == "CD" and "seats_inauguration" in sub and sub.seats_inauguration.notna().all() and sub.seats_inauguration.sum() > 0:
                seats = sub.seats_inauguration.astype(float); basis = "inauguration"
            else:
                basis = "election" if chamber == "CD" else "start of legislature"
            tot = seats.sum()
            for (r, st) in zip(sub.itertuples(), seats):
                p = r.party
                sb, nb = bls_score(p, int(start[:4]))
                sg, ng = bolo_score(p)
                cn, cbr = centrao(p, leg_id)
                rows.append(dict(leg_id=leg_id, start=start, chamber=chamber, party=p, party_family=FAMILY.get(p, p), seats_start=st,
                                 seats_share=st / tot, ideology_bls=sb, ideology_bolognesi=sg,
                                 bloc=None if np.isnan(sb) else ("left" if sb <= 4.0 else "right" if sb >= 6.0 else "centre"),
                                 bloc_bolognesi=None if np.isnan(sg) else ("left" if sg <= 4.0 else "right" if sg >= 6.0 else "centre"),
                                 centrao_narrow=cn, centrao_broad=cbr, seats_basis=basis,
                                 source_seats=getattr(r, "source_url", None), source_ideology=f"{nb}; {ng}",
                                 note=getattr(r, "note", None)))
    S = pd.DataFrame(rows)
    # coalition / president flags per dyad -> stored per (leg, party) for the dyad starting in that legislature
    S["president_party"] = 0; S["coalition_start"] = np.nan; S["coalition_mid"] = np.nan; S["source_coalition"] = None
    for d in DY.itertuples():
        m = (S.leg_id == d.leg_id)
        S.loc[m & S.party.isin(PRES_PARTY[d.pres]), "president_party"] = 1
        for timing, col in (("start", "coalition_start"), ("mid", "coalition_mid")):
            k = (d.dyad, timing)
            if k in COAL and COAL[k]["parties"]:
                S.loc[m, col] = S.loc[m, "party"].isin(COAL[k]["parties"]).astype(int).where(S.loc[m, col].isna(), S.loc[m, col])
                S.loc[m, "source_coalition"] = COAL[k]["url"]
    return S, COAL


def enpp(shares):
    s = np.asarray(shares, float)
    return 1 / np.sum(s ** 2)


def dyad_alignment(S, COAL, dyad, leg_id, pres, pres_ideo=None):
    cd = S[(S.leg_id == leg_id) & (S.chamber == "CD")]; sf = S[(S.leg_id == leg_id) & (S.chamber == "SF")]
    out = dict(chamber_size_cd=cd.seats_start.sum(), chamber_size_sf=sf.seats_start.sum() if len(sf) else np.nan)
    pp = PRES_PARTY[pres]
    out["pres_party_share_cd"] = cd[cd.party.isin(pp)].seats_share.sum() if pp else np.nan
    out["pres_party_share_sf"] = sf[sf.party.isin(pp)].seats_share.sum() if (pp and len(sf)) else np.nan
    for timing in ("start", "mid"):
        k = (dyad, timing)
        if k in COAL and COAL[k]["parties"]:
            comp = cd[cd.party.isin(COAL[k]["parties"])].seats_share.sum()
            rep_ = COAL[k]["share_src"]
            out[f"coalition_share_cd_{timing}_computed"] = comp
            out[f"coalition_share_cd_{timing}"] = rep_ if rep_ == rep_ else comp   # reported (Figueiredo 2007, seats at cabinet date) preferred
            out[f"coalition_share_sf_{timing}"] = sf[sf.party.isin(COAL[k]["parties"])].seats_share.sum() if len(sf) else np.nan
            out[f"coalition_share_cd_{timing}_src"] = COAL[k]["share_src"]
        else:
            out[f"coalition_share_cd_{timing}"] = np.nan; out[f"coalition_share_sf_{timing}"] = np.nan
    out["centrao_share_cd_narrow"] = cd[cd.centrao_narrow == 1].seats_share.sum()
    out["centrao_share_cd_broad"] = cd[cd.centrao_broad == 1].seats_share.sum()
    out["centrao_share_sf_narrow"] = sf[sf.centrao_narrow == 1].seats_share.sum() if len(sf) else np.nan
    out["left_share_cd"] = cd[cd.bloc == "left"].seats_share.sum(); out["right_share_cd"] = cd[cd.bloc == "right"].seats_share.sum()
    for ch, df in (("cd", cd), ("sf", sf)):
        ok = df.ideology_bls.notna()
        out[f"seat_weighted_ideology_{ch}"] = np.average(df.ideology_bls[ok], weights=df.seats_start[ok]) if ok.any() else np.nan
        out[f"ideology_coverage_{ch}"] = df.seats_share[ok].sum() if ok.any() else np.nan
        okg = df.ideology_bolognesi.notna()
        out[f"seat_weighted_bolognesi_{ch}"] = np.average(df.ideology_bolognesi[okg], weights=df.seats_start[okg]) if okg.any() else np.nan
    pi = pres_ideo if pres_ideo is not None else pres_bls(pres)
    out["pres_ideology_bls"] = pi
    out["pres_congress_distance"] = abs(pi - out["seat_weighted_ideology_cd"])
    pparty_bolo = {"Sarney": "MDB", "Collor": "PTC", "Itamar": None, "FHC": "PSDB", "Lula": "PT", "Dilma": "PT", "Temer": "MDB",
                   "Bolsonaro": "PSL", "Lula IV": "PT", "Flávio": "PR"}[pres]
    pb = BOLO.get(pparty_bolo, np.nan) if pparty_bolo else np.nan
    out["pres_ideology_bolognesi"] = pb
    out["pres_congress_distance_bolognesi"] = abs(pb - out["seat_weighted_bolognesi_cd"]) if not np.isnan(pb) else np.nan
    out["enpp_cd"] = enpp(cd.seats_share); out["enpp_sf"] = enpp(sf.seats_share) if len(sf) else np.nan
    out["frag_cd"] = 1 - np.sum(cd.seats_share ** 2)
    out["others_residual_cd"] = cd[cd.party.str.upper().str.startswith("OTHER")].seats_share.sum()
    return out


GOVMAP = {"Collor×49": "Collor", "Itamar×49": "Itamar", "FHC×51": "FHC (post-EC32)", "Lula×52": "Lula I", "Lula×53": "Lula II",
          "Dilma×54": "Dilma I", "Dilma×55": "Dilma II", "Temer×55": "Temer", "Bolsonaro×56": "Bolsonaro", "Lula×57": "Lula III"}
VETOMAP = {"FHC×50": "FHC I+II", "FHC×51": "FHC I+II", "Lula×52": "Lula I+II", "Lula×53": "Lula I+II", "Dilma×54": "Dilma I+II",
           "Dilma×55": "Dilma I+II", "Temer×55": "Temer", "Bolsonaro×56": "Bolsonaro", "Lula×57": "Lula III"}
FRMAP = {"Collor×49": ("Collor", 1989), "FHC×50": ("FHC", 1994), "FHC×51": ("FHC", 1998), "Lula×52": ("Lula", 2002), "Lula×53": ("Lula", 2006),
         "Dilma×54": ("Dilma", 2010), "Dilma×55": ("Dilma", 2014), "Bolsonaro×56": ("Bolsonaro", 2018), "Lula×57": ("Lula", 2022)}


def load_governability():
    g = pd.read_csv(RES / "governability.csv")
    g["president"] = g.president.astype(str).str.strip()
    return g


def gv(G, pres, metric, period=None):
    sub = G[(G.president == pres) & (G.metric == metric) & G.value.notna()]
    if period is not None:
        sub = sub[sub.period.astype(str) == str(period)]
    if sub.empty:
        return np.nan, None, None
    r = sub.iloc[0]
    return float(r.value), r.source_url, r.definition


def load_panel():
    S, COAL = build_seats()
    G = load_governability()
    rows = []
    for d in DY.itertuples():
        al = dyad_alignment(S, COAL, d.dyad, d.leg_id, d.pres)
        row = dict(dyad_id=d.dyad_id, dyad=d.dyad, leg_id=d.leg_id, president=d.pres, party=d.party, lean=d.lean3,
                   start=d.start.date(), end=d.end.date(), months=d.months, **al)
        gp = GOVMAP.get(d.dyad)
        v, url, df_ = gv(G, gp, "follow_rate") if gp else (np.nan, None, None)
        basom = df_ is not None and "Basometro" in str(df_)
        row["gov_success_rate"] = v if basom else np.nan
        row["gov_success_source"] = url if basom else None
        row["gov_success_def"] = "follow-rate (Estadão Basômetro governismo)" if basom else None
        if d.dyad == "Lula×57":
            a1, u1, _ = gv(G, "Lula III", "follow_rate", "2023-04"); a2, u2, _ = gv(G, "Lula III", "follow_rate", "2024-05")
            row["arko_follow_rate"] = np.nanmean([a1, a2]); row["arko_source"] = u2
        w, wu, wd = gv(G, gp, "win_rate") if gp else (np.nan, None, None)
        row["gov_win_rate"] = w; row["gov_win_source"] = wu
        for met_ in ("mp_converted", "mp_conv_rate", "mp_issued"):
            row[met_] = gv(G, gp, met_)[0] if gp else np.nan
        if d.dyad == "Lula×57":
            row["mp_issued"] = gv(G, "Lula III", "mp_issued", "2023..2026-04")[0]
        vp = VETOMAP.get(d.dyad)
        vt = gv(G, vp, "vetoes_total")[0] if vp else np.nan
        vo = gv(G, vp, "vetoes_overridden")[0] if vp else np.nan
        row["vetoes_appreciated_term"] = vt; row["vetoes_overridden_term"] = vo
        row["veto_override_share"] = vo / vt if (vt == vt and vo == vo and vt > 0) else np.nan
        fr = FRMAP.get(d.dyad)
        if fr:
            sub = G[(G.metric == "first_round_share") & (G.president == fr[0]) & (G.period.astype(str) == str(fr[1]))]
            row["first_round_vote_share_president"] = float(sub.value.iloc[0]) if len(sub) else np.nan
        else:
            row["first_round_vote_share_president"] = np.nan
        row["coalition_note"] = COAL.get((d.dyad, "start"), {}).get("note")
        rows.append(row)
    L = pd.DataFrame(rows)
    return S, COAL, G, L


# ============================================================================ 4. outcomes (annual, attributed to dyads)
def build_outcomes():
    O = {}
    O["pb"] = dict(name="Primary balance % GDP", sid="primary_balance_gdp", s=A("primary_balance_gdp", 2003), good=+1, hyp="G1")
    gd = A("gross_public_debt_gdp", 2006, col="year_end")
    O["ddebt"] = dict(name="Δ gross debt % GDP (pp/yr)", sid="gross_public_debt_gdp", s=gd.diff().dropna(), good=-1, hyp="G1")
    nd = A("net_public_debt_gdp", 2001, col="year_end")
    O["dnetdebt"] = dict(name="Δ net debt % GDP (pp/yr)", sid="net_public_debt_gdp", s=nd.diff().dropna(), good=-1, hyp="G1")
    O["interest"] = dict(name="Interest bill % GDP", sid="interest_bill_gdp", s=A("interest_bill_gdp", 2003), good=-1, hyp="G1")
    O["nld"] = dict(name="GG net lending % GDP (WB GFS)", sid="wb/GC.NLD.TOTL.GD.ZS.BR", s=A("wb/GC.NLD.TOTL.GD.ZS.BR"), good=+1, hyp="G1")
    O["gfcf"] = dict(name="GFCF % GDP", sid="wb/NE.GDI.FTOT.ZS.BR", s=A("wb/NE.GDI.FTOT.ZS.BR", 1987), good=+1, hyp="G1")
    O["realrate"] = dict(name="Real policy rate (ex-ante)", sid="real_policy_rate", s=A("real_policy_rate", 2002), good=-1, hyp="G2")
    O["embi"] = dict(name="EMBI+ Brazil (bp)", sid="embi_brazil", s=A("embi_brazil", 2000), good=-1, hyp="G2")
    O["ntnb"] = dict(name="NTN-B ~10y real yield", sid="gov_real_yield_10y", s=A("gov_real_yield_10y", 2015), good=-1, hyp="G2")
    O["riskprem"] = dict(name="Lending risk premium (WB)", sid="wb/FR.INR.RISK.BR", s=A("wb/FR.INR.RISK.BR", 1997), good=-1, hyp="G2")
    for k, v in O.items():
        v["s"] = v["s"][(v["s"].index >= 1987) & (v["s"].index <= 2026)].dropna()
    return O


OUTC = build_outcomes()
PRIMARY_OUT = {"G1": ["pb", "ddebt", "interest", "nld"], "G2": ["realrate", "embi", "ntnb", "riskprem"]}
XVARS = {"pres_party_share_cd": +1, "coalition_share_cd_start": +1, "coalition_share_cd_mid": +1, "pres_congress_distance": -1,
         "pres_congress_distance_bolognesi": -1, "enpp_cd": -1}
XMAIN = ["coalition_share_cd_start", "pres_party_share_cd", "enpp_cd", "pres_congress_distance"]


def annual_units(s, L, x, attr="c", y0=1987, adj="raw"):
    """returns DataFrame year, dyad, y, x."""
    ss = s[s.index >= y0]
    if adj in ("tot", "totlean"):
        lean = pd.Series({y: 1.0 if (ATTR.at[y, "c"] and L.set_index("dyad").lean.get(ATTR.at[y, "c"]) == "left") else 0.0
                          for y in ss.index if y in ATTR.index})
        ss = tot_adjust(ss, lean=lean if adj == "totlean" else None)
        if ss is None:
            return pd.DataFrame()
    xs = L.set_index("dyad")[x]
    rows = []
    for y, v in ss.items():
        if y not in ATTR.index:
            continue
        dd = ATTR.at[y, attr]
        if dd is None or dd not in xs.index or pd.isna(xs[dd]):
            continue
        if attr == "dropfirst":
            pass
        rows.append(dict(year=y, dyad=dd, y=v, x=xs[dd], first=ATTR.at[y, "first"]))
    return pd.DataFrame(rows)


def estimate(s, L, x, unit="dyad", attr="c", y0=1987, adj="raw", boot=False, rng=None):
    a = "c" if attr == "dropfirst" else attr
    U = annual_units(s, L, x, a, y0, adj)
    if U.empty:
        return None
    if attr == "dropfirst":
        U = U[~U["first"]]
    if unit == "dyad":
        D = U.groupby("dyad").agg(y=("y", "mean"), x=("x", "first"), n=("y", "size")).reset_index()
        if len(D) < 3 or D.x.nunique() < 3:
            return None
        res = dict(n_units=len(D), n_years=int(U.shape[0]), slope=slope(D.x, D.y), rho=spearman(D.x, D.y))
        if boot:
            bs = cluster_boot_slope(D.x.values, D.y.values, D.dyad.values, rng)
            res["ci80"] = [float(np.percentile(bs, 10)), float(np.percentile(bs, 90))] if len(bs) else [np.nan, np.nan]
            res["perm_p"], res["perm_floor"] = perm_p_slope(D.x.values, D.y.values, rng)
            res["units"] = D.round(4).to_dict("records")
        return res
    else:
        if U.dyad.nunique() < 3 or U.x.nunique() < 3:
            return None
        res = dict(n_units=int(U.dyad.nunique()), n_years=len(U), slope=slope(U.x, U.y), rho=spearman(U.x, U.y))
        if boot:
            bs = cluster_boot_slope(U.x.values, U.y.values, U.dyad.values, rng)
            res["ci80"] = [float(np.percentile(bs, 10)), float(np.percentile(bs, 90))]
        return res


def dyad_stats(L):
    rng = np.random.default_rng(SEED)
    out = {}
    for hyp, mets in PRIMARY_OUT.items():
        for m in mets + (["gfcf", "dnetdebt"] if hyp == "G1" else []):
            o = OUTC[m]
            for x in XMAIN:
                r = estimate(o["s"], L, x, boot=True, rng=rng)
                if r is None:
                    continue
                n1sign = XVARS[x] * o["good"]       # N1: better outcome with more alignment / less fragmentation
                r.update(hyp=hyp, metric=m, metric_name=o["name"], series_id=o["sid"], x=x, n1_expected_sign=n1sign,
                         sign_matches_n1=bool(np.sign(r["slope"]) == n1sign))
                rt = estimate(o["s"], L, x, adj="tot", boot=True, rng=rng)
                r["slope_tot"] = rt["slope"] if rt else None; r["ci80_tot"] = rt["ci80"] if rt else None
                out[f"{m}|{x}"] = r
    # BH / Holm over the primary family (G1+G2 primaries x coalition_share_cd_start)
    keys = [k for k in out if k.split("|")[1] == "coalition_share_cd_start" and k.split("|")[0] in sum(PRIMARY_OUT.values(), [])]
    ps = [out[k]["perm_p"] for k in keys]
    for k, qv, hv in zip(keys, bh(ps), holm(ps)):
        out[k]["bh_q"] = float(qv); out[k]["holm_p"] = float(hv)
    return out


def detrended_check(L):
    """POST-HOC (not pre-registered): partial Spearman of dyad means on x controlling for the dyad's mid-year
    (ENPP and alignment trend over time, as do rates and fiscal outcomes)."""
    out = {}
    mid = {d.dyad: (d.start + (d.end - d.start) / 2).year + (d.start + (d.end - d.start) / 2).month / 12 for d in DY.itertuples()}
    for m in sum(PRIMARY_OUT.values(), []) + ["gfcf"]:
        for x in XMAIN:
            U = annual_units(OUTC[m]["s"], L, x)
            if U.empty:
                continue
            D = U.groupby("dyad").agg(y=("y", "mean"), x=("x", "first")).reset_index()
            if len(D) < 5:
                continue
            t = D.dyad.map(mid).values
            ry = pd.Series(D.y).rank().values; rx = pd.Series(D.x).rank().values; rt = pd.Series(t).rank().values
            ey = ry - np.polyval(np.polyfit(rt, ry, 1), rt); ex = rx - np.polyval(np.polyfit(rt, rx, 1), rt)
            out[f"{m}|{x}"] = dict(n=len(D), rho_raw=spearman(D.x, D.y), rho_partial_time=float(np.corrcoef(ex, ey)[0, 1]) if ex.std() > 0 and ey.std() > 0 else None,
                                   rho_x_time=spearman(D.x, t), rho_y_time=spearman(D.y, t))
    # leave-one-dyad-out for the two N1-supporting cells
    for m in ("gfcf", "nld", "pb"):
        U = annual_units(OUTC[m]["s"], L, "coalition_share_cd_start")
        D = U.groupby("dyad").agg(y=("y", "mean"), x=("x", "first")).reset_index()
        loo = {d: spearman(D[D.dyad != d].x, D[D.dyad != d].y) for d in D.dyad}
        out[f"LOO|{m}|coalition_share_cd_start"] = dict(min=min(loo.values()), max=max(loo.values()),
                                                         argmin=min(loo, key=loo.get), loo=loo)
    return out


def robustness_grid(L):
    rows = []
    samples = {"1987+": 1987, "1995+": 1995, "2003+": 2003}
    for m in sum(PRIMARY_OUT.values(), []) + ["gfcf"]:
        o = OUTC[m]
        for sn, y0 in samples.items():
            for unit in ("dyad", "year"):
                for x, xs in XVARS.items():
                    for attr in ("c", "lag1", "dropfirst"):
                        for adj in ("raw", "tot", "totlean"):
                            r = estimate(o["s"], L, x, unit, attr, y0, adj)
                            if r is None or np.isnan(r["slope"]):
                                continue
                            n1 = xs * o["good"]
                            rows.append(dict(metric=m, sample=sn, unit=unit, x=x, attribution=attr, adjustment=adj,
                                             ideology_source="bolognesi" if "bolognesi" in x else "bls",
                                             n_units=r["n_units"], n_years=r["n_years"], slope=r["slope"], rho=r["rho"],
                                             n1_sign=n1, n1_consistent=int(np.sign(r["slope"]) == n1)))
        # centrão coding variants (exploratory; N1 sign = fragmentation-like, -1)
        for cod in ("centrao_share_cd_narrow", "centrao_share_cd_broad"):
            for unit in ("dyad", "year"):
                r = estimate(o["s"], L, cod, unit)
                if r is None or np.isnan(r["slope"]):
                    continue
                rows.append(dict(metric=m, sample="1987+", unit=unit, x=cod, attribution="c", adjustment="raw", ideology_source="-",
                                 n_units=r["n_units"], n_years=r["n_years"], slope=r["slope"], rho=r["rho"],
                                 n1_sign=-1 * o["good"], n1_consistent=int(np.sign(r["slope"]) == -1 * o["good"])))
    R = pd.DataFrame(rows)
    return R


def verdicts(DS_, R):
    V = {}
    for m in sum(PRIMARY_OUT.values(), []) + ["gfcf"]:
        sub = R[(R.metric == m) & ~R.x.str.startswith("centrao")]
        share = float(sub.n1_consistent.mean()) if len(sub) else np.nan
        b = DS_.get(f"{m}|coalition_share_cd_start")
        if b is None:
            V[m] = dict(verdict="not estimable", n1_share=share); continue
        ci = b["ci80"]; excl = ci[0] > 0 or ci[1] < 0
        if b["sign_matches_n1"] and share >= 0.8 and excl:
            v = "supports N1"
        elif (not b["sign_matches_n1"]) and (1 - share) >= 0.8 and excl:
            v = "robust association opposite to N1 (an N2-type 'Congress as check' pattern)"
        else:
            v = "no robust association (consistent with N2)"
        V[m] = dict(verdict=v, n1_share=share, baseline_slope=b["slope"], ci80=ci, rho=b["rho"], n_dyads=b["n_units"],
                    perm_p=b["perm_p"], bh_q=b.get("bh_q"), metric_name=OUTC[m]["name"], series_id=OUTC[m]["sid"], n_cells=len(sub))
    return V


# ============================================================================ 5. event study (G6 / G7 / foreign-policy votes)
# (date, label, group, stage). Dates verified in research/reforms.csv where available (see EVENT_SOURCES).
EVENTS_DEFAULT = [
    ("2016-10-10", "PEC 241 spending cap — Chamber 1st round", "G1 tightening", "primary"),
    ("2016-12-15", "EC 95 spending cap — promulgation", "G1 tightening", "secondary"),
    ("2017-04-26", "Labour reform — Chamber vote", "G1 tightening", "primary"),
    ("2017-07-13", "Labour reform — Lei 13.467 sanctioned", "G1 tightening", "secondary"),
    ("2019-07-10", "Pension reform — Chamber 1st round", "G1 tightening", "primary"),
    ("2019-10-22", "Pension reform — Senate final vote", "G1 tightening", "other"),
    ("2019-11-12", "EC 103 pension — promulgation", "G1 tightening", "secondary"),
    ("2021-02-10", "BCB autonomy — Chamber vote", "G1 tightening", "primary"),
    ("2021-02-24", "LC 179 BCB autonomy — sanctioned", "G1 tightening", "secondary"),
    ("2023-05-23", "Fiscal framework — Chamber vote", "G1 tightening", "primary"),
    ("2023-08-31", "LC 200 fiscal framework — sanctioned", "G1 tightening", "secondary"),
    ("2023-07-06", "PEC 45 tax reform — Chamber 1st round", "G1 tightening", "primary"),
    ("2023-12-20", "EC 132 tax reform — promulgation", "G1 tightening", "secondary"),
    ("2021-11-04", "PEC dos Precatórios — Chamber 1st round", "G2 loosening", "primary"),
    ("2021-12-08", "EC 113 precatórios — promulgation", "G2 loosening", "secondary"),
    ("2022-07-12", "PEC 'Kamikaze' — Chamber 1st round", "G2 loosening", "primary"),
    ("2022-07-14", "EC 123 'Kamikaze' — promulgation", "G2 loosening", "secondary"),
    ("2022-12-20", "PEC da Transição — Chamber 1st round", "G2 loosening", "primary"),
    ("2022-12-21", "EC 126 transition — promulgation", "G2 loosening", "secondary"),
    ("2024-11-28", "Fiscal package + IR exemption announcement (executive; flagged)", "G2 loosening", "flag"),
    ("2025-11-27", "Licensing-law veto override (52 of 63)", "G2 loosening", "primary"),
    ("2016-04-17", "Impeachment — Chamber vote", "G3 impeachment/institutional", "primary"),
    ("2016-05-12", "Impeachment — Senate admits, Temer acting", "G3 impeachment/institutional", "other"),
    ("2016-08-31", "Impeachment — Senate removal", "G3 impeachment/institutional", "secondary"),
    ("2023-01-08", "8 January 2023 riots (next trading day)", "G3 impeachment/institutional", "primary"),
    ("2025-04-01", "Reciprocity bill — Congress approval", "G4 foreign policy", "primary"),
    ("2025-04-11", "Lei 15.122 Reciprocity — sanctioned", "G4 foreign policy", "secondary"),
    ("2025-12-10", "Dosimetria PL 2162 — Chamber passage", "G4 foreign policy", "primary"),
    ("2025-12-12", "US lifts Magnitsky on Moraes", "G4 foreign policy", "other"),
    ("2026-01-08", "Dosimetria — full veto by Lula", "G4 foreign policy", "other"),
    ("2026-03-04", "EU–Mercosur — Senate approval", "G4 foreign policy", "primary"),
    ("2026-03-17", "EU–Mercosur — DL 14/2026 promulgated", "G4 foreign policy", "secondary"),
    ("2026-04-30", "Dosimetria veto overridden (Chamber 318–144, Senate 49–24)", "G4 foreign policy", "primary"),
]


def events_verified():
    notes = ["dates verified against the Câmara/Senado open-data APIs and Planalto (research/reforms.csv)",
             "fiscal framework Chamber vote: plan 2023-05-24 -> 2023-05-23 (base text 23:31; destaques/redação final 05-24)",
             "PEC 45 Chamber 1st round: plan 2023-07-07 -> 2023-07-06 21:49 (07-07 01:39 is the 2nd round)",
             "PEC Kamikaze Chamber 1st round: plan 2022-07-13 -> 2022-07-12 (07-13 is the 2nd round)",
             "precatórios Chamber 1st round 2021-11-04 01:49 (session opened 11-03); dosimetria Chamber 2025-12-10 02:58",
             "dosimetria veto was overridden on 2026-04-30 (Chamber 318-144, Senate 49-24; Senado Notícias) — the plan's 'veto awaits a joint session' is outdated; event added to G4"]
    return list(EVENTS_DEFAULT), notes


def event_section():
    events, notes = events_verified()
    EV, PL = run_event_study(events)
    # group comparison G1 vs G2, per stage, per series/window (exact permutation across events)
    rows = []
    for stage in ("primary", "secondary"):
        for sid in ES_SERIES:
            for wn in WINDOWS:
                e = EV[(EV.series_id == sid) & (EV.window == wn) & EV.car.notna() & (EV.stage == stage) &
                       EV.group.isin(["G1 tightening", "G2 loosening"])]
                n1, n2 = (e.group == "G1 tightening").sum(), (e.group == "G2 loosening").sum()
                r = dict(stage=stage, series_id=sid, window=wn, n_G1=int(n1), n_G2=int(n2))
                if n1 >= 2 and n2 >= 1:
                    vals = e.car.values.astype(float); lab = np.where(e.group == "G1 tightening", "left", "right")
                    p, pmin, nl = perm_test(vals, lab)
                    r.update(mean_G1=float(vals[lab == "left"].mean()), mean_G2=float(vals[lab == "right"].mean()),
                             diff=float(vals[lab == "left"].mean() - vals[lab == "right"].mean()), perm_p=p, p_min=pmin, n_labelings=nl,
                             placebo_sd=float(PL[(sid, wn)].std()))
                rows.append(r)
        # other groups: mean CAR and mean placebo p
    G = pd.DataFrame(rows)
    grp = (EV[EV.car.notna()].groupby(["group", "stage", "series_id", "window"])
           .agg(n=("car", "size"), mean_car=("car", "mean"), median_placebo_p=("placebo_p", "median")).reset_index())
    # 1992 descriptive (monthly)
    m92 = q("monthly_1992", """SELECT series_id, date, value FROM v_observations WHERE series_id IN ('wb/REER_M.BRA','wb/DPANUSSPB_M.BRA')
        AND date BETWEEN '1992-06-01' AND '1993-03-31' ORDER BY 1,2""")
    return EV, G, grp, m92, notes, events


# ============================================================================ 6. budget capture (G5)
def budget_capture():
    p = RES / "emendas.csv"
    E = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["year", "item", "value_brl_bn", "basis", "source_url"])
    E = E[pd.to_numeric(E.value_brl_bn, errors="coerce").notna()].copy(); E["value_brl_bn"] = E.value_brl_bn.astype(float)
    E["year"] = E.year.astype(int)

    def pick(item, prefer=("pago_incl_rap", "pago", "empenhado", "dotacao")):
        out = {}
        for y, g in E[E.item == item].groupby("year"):
            g = g[g.basis.isin(prefer)].copy()
            if g.empty:
                continue
            g["rk"] = g.basis.map({b: i for i, b in enumerate(prefer)})
            r = g.sort_values("rk").iloc[0]; out[y] = (r.value_brl_bn, r.basis, r.source_url)
        return out
    gdp = q("gdp_dec", """SELECT CAST(EXTRACT(year FROM date) AS INT) AS year, arg_max(value, date)/1000 AS gdp_brl_bn, max(date) AS d
        FROM v_observations WHERE series_id='gdp_nominal_12m_brl' AND date <= current_date GROUP BY 1 ORDER BY 1""").set_index("year")
    paid = pick("paid", ("pago_incl_rap",))   # cash incl. restos a pagar; Portal payment file incomplete for 2014-15 -> missing
    auth = pick("authorised", ("dotacao", "empenhado", "pago")); imp = pick("impositivas")
    rp9 = pick("rp9"); pix = pick("pix"); disc = pick("discretionary_total", ("pago", "pago_incl_rap", "empenhado", "dotacao"))
    rows = []
    for y in range(2014, 2027):
        r = dict(year=y)
        for nm, dct in (("emendas_paid_brl_bn", paid), ("emendas_authorized_brl_bn", auth), ("emendas_impositivas_brl_bn", imp),
                        ("emendas_rp9_brl_bn", rp9), ("emendas_pix_brl_bn", pix), ("discretionary_brl_bn", disc)):
            v = dct.get(y); r[nm] = v[0] if v else np.nan; r[nm + "_basis"] = v[1] if v else None; r[nm + "_src"] = v[2] if v else None
        g = gdp.gdp_brl_bn.get(y, np.nan)
        base = r["emendas_paid_brl_bn"]   # cash paid incl. restos a pagar only (no mixing of bases)
        r["emendas_pct_gdp"] = 100 * base / g if g == g and base == base else np.nan
        r["emendas_pct_gdp_basis"] = "paid" if not np.isnan(r["emendas_paid_brl_bn"]) else ("authorised" if base == base else None)
        r["emendas_share_discretionary"] = 100 * base / r["discretionary_brl_bn"] if base == base and r["discretionary_brl_bn"] == r["discretionary_brl_bn"] else np.nan
        r["gdp_nominal_brl_bn_dec"] = g
        rows.append(r)
    B = pd.DataFrame(rows).set_index("year")
    emit("gdp_nominal_2025_brl_bn", gdp.gdp_brl_bn.get(2025), "gdp_nominal_12m_brl", "gdp_dec")
    outs = {"wb/GC.NFN.TOTL.GD.ZS.BR": A("wb/GC.NFN.TOTL.GD.ZS.BR"), "wb/NE.GDI.FTOT.ZS.BR": A("wb/NE.GDI.FTOT.ZS.BR"),
            "gov_real_yield_10y": A("gov_real_yield_10y", 2015), "r_minus_g": A("r_minus_g", 2008)}
    for k, s in outs.items():
        B[k] = s.reindex(B.index)
    cors = {}
    for xv in ("emendas_pct_gdp", "emendas_share_discretionary"):
        for k in outs:
            d = B[[xv, k]].dropna(); d = d[d.index <= 2025]
            cors[f"{xv}~{k}"] = dict(rho=spearman(d[xv], d[k]) if len(d) >= 4 else None, n=len(d), years=f"{d.index.min()}–{d.index.max()}" if len(d) else None)
    return B, cors


# ============================================================================ 7. reform table (G4) and governability (G3)
def reform_table(L, S):
    p = RES / "reforms.csv"
    R = pd.read_csv(p) if p.exists() else pd.DataFrame()
    if R.empty:
        return R, {}
    R["date"] = pd.to_datetime(R.promulgation_date, errors="coerce")
    R["dyad"] = R.date.map(lambda d: dyad_of_date(d) if pd.notna(d) else None)
    Li = L.set_index("dyad")
    for c in ("coalition_share_cd_start", "pres_party_share_cd", "centrao_share_cd_narrow", "enpp_cd"):
        R[c] = R.dyad.map(Li[c])
    R = R[R.kind.isin(["EC", "LC", "law", "PEC"])]       # drop STF decisions (ADPF 854, Dino orders)
    econ = R[R.dyad.notna() & R.category.isin(["tightening", "loosening", "institutional"])]
    cnt = econ.groupby("dyad").size()
    bycat = econ.groupby(["dyad", "category"]).size().unstack(fill_value=0)
    D = L[["dyad", "months", "coalition_share_cd_start", "pres_party_share_cd", "enpp_cd", "pres_congress_distance"]].copy()
    D["n_econ_reforms"] = D.dyad.map(cnt).fillna(0)
    D["reforms_per_year"] = D.n_econ_reforms / (D.months / 12)
    for c in ("tightening", "loosening", "institutional"):
        D[c] = D.dyad.map(bycat[c] if c in bycat else {}).fillna(0)
    rng = np.random.default_rng(SEED)
    st = {}
    for x in ("coalition_share_cd_start", "pres_party_share_cd", "enpp_cd", "pres_congress_distance"):
        d = D[[x, "reforms_per_year"]].dropna()
        p_, fl = perm_p_slope(d[x].values, d.reforms_per_year.values, rng)
        st[x] = dict(rho=spearman(d[x], d.reforms_per_year), slope=slope(d[x], d.reforms_per_year), perm_p=p_, n=len(d))
    return R, dict(per_dyad=D.round(3).to_dict("records"), stats=st)


def governability_tests(L):
    rng = np.random.default_rng(SEED)
    out = {}
    for y in ("gov_success_rate", "gov_win_rate", "mp_conv_rate"):
        for x in ("coalition_share_cd_start", "pres_party_share_cd", "enpp_cd", "pres_congress_distance"):
            d = L[[x, y]].dropna()
            if len(d) < 4:
                out[f"{y}~{x}"] = dict(n=len(d)); continue
            p_, fl = perm_p_slope(d[x].values, d[y].values, rng)
            out[f"{y}~{x}"] = dict(n=len(d), rho=spearman(d[x], d[y]), slope=slope(d[x], d[y]), perm_p=p_,
                                  mean=float(d[y].mean()), sd=float(d[y].std()))
    # MP conversion pre/post 2019 (rule change: Ato Conjunto / EC 32 trancamento; STF on 'jabutis')
    m = L[["dyad", "mp_conv_rate"]].dropna()
    out["mp_pre2019_mean"] = float(m[~m.dyad.isin(["Bolsonaro×56", "Lula×57"])].mp_conv_rate.mean()) if len(m) else None
    out["mp_post2019"] = m[m.dyad.isin(["Bolsonaro×56", "Lula×57"])].to_dict("records")
    return out


def g8_fpa(L):
    p = RES / "fpa.csv"
    if not p.exists():
        return {}
    F = pd.read_csv(p)
    F = F[pd.to_numeric(F.deputies, errors="coerce").notna()]
    F["share_cd"] = F.deputies.astype(float) / 513
    pf = A("wb/AG.LND.PFLS.HA.BR") / 1e6
    rows = []
    for r in F.itertuples():
        y0 = int(r.legislature_start_year)
        yrs = [y for y in range(y0, y0 + 4) if y in pf.index]
        rows.append(dict(leg_start=y0, fpa_deputies=r.deputies, fpa_share_cd=r.share_cd, pfls_mha_mean=float(pf.reindex(yrs).mean()) if yrs else np.nan,
                         years=f"{yrs[0]}–{yrs[-1]}" if yrs else None, source=r.source_url))
    D = pd.DataFrame(rows)
    d = D.dropna(subset=["pfls_mha_mean"])
    eu = A("exports_to_eu", 2014)
    return dict(table=D.to_dict("records"), rho=spearman(d.fpa_share_cd, d.pfls_mha_mean) if len(d) >= 3 else None, n=len(d),
                exports_to_eu_annual={int(k): round(float(v), 3) for k, v in eu.items()})


def g9_coattails(L):
    d = L[["dyad", "first_round_vote_share_president", "pres_party_share_cd"]].dropna()
    d = d[~d.dyad.isin(["Itamar×49", "Temer×55", "Sarney×48"])]
    return dict(rho=spearman(d.first_round_vote_share_president, d.pres_party_share_cd) if len(d) >= 4 else None, n=len(d),
                rows=d.to_dict("records"))


def g10_treaties():
    p = RES / "treaties.csv"
    if not p.exists():
        return []
    T = pd.read_csv(p)
    for c in ("signed_date", "congress_approval_date", "promulgation_date"):
        T[c] = pd.to_datetime(T[c], errors="coerce")
    T["months_sign_to_congress"] = ((T.congress_approval_date - T.signed_date).dt.days / 30.44).round(1)
    T["months_sign_to_promulgation"] = ((T.promulgation_date - T.signed_date).dt.days / 30.44).round(1)
    T["dyad_at_signature"] = T.signed_date.map(lambda d: dyad_of_date(d) if pd.notna(d) else None)
    return T


def g11_lean_alignment(L):
    """politics deltas recomputed within aligned vs misaligned dyads (coalition_share_cd_start >= 0.5)."""
    gdp = A("wb/NY.GDP.MKTP.KD.ZG.BR", 1987); un = A("wb/SL.UEM.TOTL.ZS.BR", 1991)
    mw = A("ilostat/EAR_INEE_NOC_NB.BRA") / A("wb/FP.CPI.TOTL.BR")
    mets = {"A1 GDP growth": gdp, "C1 primary balance": OUTC["pb"]["s"], "B2 real policy rate": OUTC["realrate"]["s"],
            "E1 unemployment": un, "E3 real min-wage growth": dlog(mw).dropna()}
    Li = L.set_index("dyad")
    al = (Li.coalition_share_cd_start >= 0.5).map({True: "aligned", False: "misaligned"})
    al[Li.coalition_share_cd_start.isna()] = None
    out = {}
    for k, s in mets.items():
        rows = []
        for y, v in s.items():
            if y in ATTR.index and ATTR.at[y, "c"]:
                dd = ATTR.at[y, "c"]; rows.append(dict(dyad=dd, y=v))
        D = pd.DataFrame(rows).groupby("dyad").y.mean()
        res = {}
        for grp in ("aligned", "misaligned"):
            ds = [d for d in D.index if al.get(d) == grp]
            lv = [D[d] for d in ds if Li.lean[d] == "left"]; rv = [D[d] for d in ds if Li.lean[d] == "right"]
            res[grp] = dict(left_dyads=[d for d in ds if Li.lean[d] == "left"], right_dyads=[d for d in ds if Li.lean[d] == "right"],
                            delta_L_minus_R=float(np.mean(lv) - np.mean(rv)) if lv and rv else None)
        out[k] = res
    return dict(alignment=al.to_dict(), deltas=out)


# ============================================================================ 8. 2027 arithmetic
def arithmetic_2027(S):
    cd = S[(S.leg_id == 58) & (S.chamber == "CD")].set_index("party").seats_start
    sf = S[(S.leg_id == 58) & (S.chamber == "SF")].set_index("party").seats_start
    g = lambda ser, ps: float(sum(ser.get(p, 0) for p in ps))
    LEFT = ["PT", "PCdoB", "PV", "PSOL", "Rede", "PSB", "PDT"]
    RIGHTCORE = ["PL", "Novo", "Missão"]
    CENTRAO = ["PP", "Republicanos", "PSD", "União", "Podemos", "PRD", "Avante", "Solidariedade"]
    OTHERC = ["MDB", "PSDB", "Cidadania"]
    a = {}
    for ch, ser, pec, absmaj, n in (("CD", cd, 308, 257, 513), ("SF", sf, 49, 41, 81)):
        tot = float(ser.sum())
        L_, R_, C_, O_ = g(ser, LEFT), g(ser, RIGHTCORE), g(ser, CENTRAO), g(ser, OTHERC)
        rest = tot - L_ - R_ - C_ - O_
        a[ch] = dict(total=tot, left=L_, right_core=R_, centrao=C_, mdb_psdb_cid=O_, unclassified=rest, pec=pec, override=absmaj,
                     flavio_max_no_mdb=R_ + C_, flavio_max=R_ + C_ + O_, lula_max_no_pl=tot - R_,
                     lula_max_without_rightcore_and_centrao=L_ + O_ + rest,
                     lula_pec_needs_from_centrao=max(0, pec - (L_ + O_ + rest)),
                     flavio_pec_needs_from_mdb_left=max(0, pec - (R_ + C_)),
                     override_vs_lula_possible=R_ + C_ + O_ >= absmaj, override_vs_lula_needs_from_centrao=max(0, absmaj - R_ - O_),
                     override_vs_flavio_possible=L_ + O_ + C_ >= absmaj, left_blocks_pec=L_ >= n - pec + 1,
                     right_core_blocks_pec=R_ >= n - pec + 1, pec_blocking_minority=n - pec + 1)
        a[ch]["parties"] = {k: float(v) for k, v in ser.sort_values(ascending=False).items()}
    return a


# ============================================================================ 9. scenarios (A6) and exports-cell modifiers (A5)
DEBT_GRID = pd.read_csv(OUT.parent / "politics" / "debt_grid.csv")


def debt_row(rg, pb):
    r = DEBT_GRID[(DEBT_GRID.r_minus_g == rg) & (DEBT_GRID.primary_balance == pb)].iloc[0]
    return round(float(r.debt_2030), 1)


GOVERN = {"aligned": ("75–85", "60–80", "55–65 (no Arko history for an aligned base; Basômetro-type 75–79)"),
          "transactional": ("60–72", "25–50", "45–60 (Arko Lula III range; 46.5% May 2024)"),
          "opposed": ("45–60", "10–30", "< 47")}
PROB = {("Flávio", "aligned"): ("high", "PL is the largest bancada in both houses (121/513; 28/81); centrão migrates to winners; Flávio is a Senate operator"),
        ("Flávio", "transactional"): ("medium", "Bolsonaro 2019–20 analogue: no formal coalition until the centrão entered in 2020–21"),
        ("Flávio", "opposed"): ("low", "family-vs-centrão conflict analogue (2019–20); centrão has no seats to gain by opposing a PL president with 132 core votes"),
        ("Lula IV", "aligned"): ("low", "the right (PL+Novo+Missão 132) plus centrão (210) already carry an override majority; aligned centrão is unlikely after a PL-led election"),
        ("Lula IV", "transactional"): ("high", "Lula III pattern: ministries + record emendas (R$61.4bn LOA 2026) bought case-by-case support; MPs mostly failed (77%)"),
        ("Lula IV", "opposed"): ("medium", "PL 28 senators and 34/54 right Senate seats; dosimetria veto overridden 318–144 / 49–24 on 2026-04-30 shows the override majority exists")}
FISCAL = {("Flávio", "aligned"): ("+0.5 to +2.0 by 2029", (2, 1), (6, 2), "85–95", "2 to 4", "5.5–6.8", "+3% to +6%"),
          ("Flávio", "transactional"): ("−0.5 to +0.5", (4, 1), (6, 0), "93–104", "4 to 6", "6.5–7.8", "0% to +3%"),
          ("Flávio", "opposed"): ("−1.0 to 0 (rule-derived; not in plan)", (4, 0), (6, -1), "96–107", "4 to 6", "7.0–8.5 (extrapolated)", "−3% to +1%"),
          ("Lula IV", "aligned"): ("−0.5 to +0.5 (rule-derived; not in plan)", (4, 1), (6, 0), "93–104", "4 to 6", "6.5–7.8 (extrapolated)", "−2% to +2%"),
          ("Lula IV", "transactional"): ("−1.0 to 0 (emendas rigidity +0.3–0.5 pp/yr)", (4, 0), (6, -1), "98–107", "4 to 6", "7.0–8.5", "−4% to 0%"),
          ("Lula IV", "opposed"): ("−1.5 to −0.5 + veto overrides on spending bills", (4, -1), (6, -1), "100–112 (upper end extrapolates below the grid's pb = −1)", "5 to 7", "7.5–9.5", "−6% to −2%")}
REFORM = {("Flávio", "aligned"): "admin-reform PEC: medium–high; fiscal-framework revision: high; BCB financial-autonomy PEC 65/2023: high; privatisation programme: medium; state pension: medium; IR package follow-ups: medium",
          ("Flávio", "transactional"): "admin-reform PEC: low–medium; framework revision: medium; PEC 65/2023: medium; privatisation: low–medium; IR follow-ups: medium (emendas price per vote rises)",
          ("Flávio", "opposed"): "all PECs low; ordinary laws case-by-case; amnesty still passes (PL+centrão right wing ≥ 257)",
          ("Lula IV", "aligned"): "framework revision (toward spending): medium; IR follow-ups: high; PEC 65/2023: low; privatisation: very low; admin reform: low",
          ("Lula IV", "transactional"): "IR follow-ups: medium; framework tweaks: medium; government PECs need most of the centrão in both houses (see pec_feasibility): low; privatisation: very low",
          ("Lula IV", "opposed"): "PECs only from Congress's own agenda (emendas, amnesty, security); government PECs ≈ 0; MP conversion 10–30%"}
SUBBRANCH = {"Flávio": "centrão incumbents keep both chairs: aligned/transactional as listed; PL takes one chair: agenda control shifts to the presidency (raises 'aligned' toward high, admin-reform odds +1 step)",
             "Lula IV": "centrão incumbents keep both chairs: transactional most likely; PL takes one chair: agenda-setting, impeachment gatekeeping (Chamber) or joint-session/veto scheduling (Senate) pass to the opposition → shifts mass from transactional to opposed"}


def arithmetic_text(A_, cand, align):
    cd, sf = A_["CD"], A_["SF"]
    if cand == "Flávio":
        pec = (f"Chamber: right core {cd['right_core']:.0f} + centrão {cd['centrao']:.0f} = {cd['flavio_max_no_mdb']:.0f} vs 308; "
               f"Senate: {sf['flavio_max_no_mdb']:.0f} (+MDB/PSDB/Cid {sf['mdb_psdb_cid']:.0f}) vs 49")
        veto = (f"override needs 257/41: left {cd['left']:.0f} + MDB/PSDB/Cid {cd['mdb_psdb_cid']:.0f} = {cd['left'] + cd['mdb_psdb_cid']:.0f} deputies → ≥{max(0, 257 - cd['left'] - cd['mdb_psdb_cid'] - cd['unclassified']):.0f} centrão votes needed; "
                f"Senate {sf['left'] + sf['mdb_psdb_cid'] + sf['unclassified']:.0f} → ≥{max(0, 41 - sf['left'] - sf['mdb_psdb_cid'] - sf['unclassified']):.0f} of {sf['centrao']:.0f} centrão senators needed")
    else:
        pec = (f"Chamber: left {cd['left']:.0f} + MDB/PSDB/Cid {cd['mdb_psdb_cid']:.0f} + unclassified {cd['unclassified']:.0f} → needs ≥{cd['lula_pec_needs_from_centrao']:.0f} of the {cd['centrao']:.0f} centrão votes for 308; "
               f"Senate needs ≥{sf['lula_pec_needs_from_centrao']:.0f} of {sf['centrao']:.0f} centrão senators for 49 (PL+Novo hold {sf['right_core']:.0f})")
        veto = (f"override needs 257/41: PL+Novo+Missão {cd['right_core']:.0f} + centrão {cd['centrao']:.0f} = {cd['right_core'] + cd['centrao']:.0f} ≥ 257 (≥{cd['override_vs_lula_needs_from_centrao']:.0f} centrão votes suffice with MDB/PSDB); "
                f"Senate: PL+Novo {sf['right_core']:.0f} + MDB/PSDB {sf['mdb_psdb_cid']:.0f} = {sf['right_core'] + sf['mdb_psdb_cid']:.0f} ≥ 41 without any centrão senator; the left ({cd['left']:.0f} / {sf['left']:.0f}) cannot sustain a veto alone")
    feas = {("Flávio", "aligned"): "feasible", ("Flávio", "transactional"): "feasible at a price", ("Flávio", "opposed"): "blocked (centrão holds the 206-seat blocking minority)",
            ("Lula IV", "aligned"): "feasible only with near-unanimous centrão", ("Lula IV", "transactional"): "hard", ("Lula IV", "opposed"): "infeasible"}[(cand, align)]
    vs = {("Flávio", "aligned"): "strong", ("Flávio", "transactional"): "strong", ("Flávio", "opposed"): "moderate (an override needs ≥86 of 210 centrão deputies voting with the entire left, MDB and PSDB)",
          ("Lula IV", "aligned"): "moderate", ("Lula IV", "transactional"): "weak", ("Lula IV", "opposed"): "very weak"}[(cand, align)]
    return f"{vs} — {veto}", f"{feas} — {pec}"


def scenarios(A_, fp):
    rows = []
    for cand in ("Lula IV", "Flávio"):
        for align in ("aligned", "transactional", "opposed"):
            g = GOVERN[align]; p, why = PROB[(cand, align)]
            pb, lo, hi, debt_plan, rg, ntnb, fx = FISCAL[(cand, align)]
            veto, pec = arithmetic_text(A_, cand, align)
            d_lo, d_hi = debt_row(*lo), debt_row(*hi)
            f = fp[(cand, align)]
            rows.append(dict(candidate="Lula IV" if cand == "Lula IV" else "Flávio Bolsonaro", centrao_alignment=align, probability_qual=p,
                             probability_rationale=why, presidency_subbranch=SUBBRANCH[cand],
                             governability_success_rate_range=g[0], follow_rate_range=g[2], mp_conversion_range=g[1],
                             reform_odds_qual=REFORM[(cand, align)], veto_strength=veto, pec_feasibility=pec,
                             primary_balance_2027_30_range=pb, rminusg_range=rg,
                             debt_gdp_2030_range=debt_plan,
                             debt_grid_rows_cited=f"r−g={lo[0]}, pb={lo[1]:+d} → {d_lo}; r−g={hi[0]}, pb={hi[1]:+d} → {d_hi} (politics/debt_grid.csv, start 82.86 in 2026)",
                             ntnb_10y_range=ntnb, fx_modifier=fx, fp_us=f["US"], fp_china=f["China"], fp_eu=f["EU"],
                             fp_mercosur=f["Mercosur/LatAm"], fp_rest=f["Rest"],
                             commodity_state_note="ToT ±10% moves exports ±$14–22bn/yr (exports overlay) — larger than any Congress modifier",
                             rationale_fact_ids="G01;G02;G03;G09;G10;G11;G14;G15;G16;G17;G21;G24;A11;A12;A21;A25;A32;C30;C60;C61",
                             analogue_dyads={"aligned": "Temer×55 (2016–18), Bolsonaro×56 2021–22", "transactional": "Lula×57, Bolsonaro×56 2019–20",
                                             "opposed": "Dilma×55 (2015–16)"}[align]))
    return pd.DataFrame(rows)


# modifiers on the exports cells: (partner, candidate, case) x alignment -> (probability shift, USD bn/yr range, lever, rationale)
def fp_modifiers():
    X = pd.read_csv(OUT.parent / "exports" / "scenario_matrix.csv")
    X = X[X.partner.isin(["US", "China", "EU", "Mercosur/LatAm", "Rest"])]
    STEP = ["low", "low–medium", "medium", "medium–high", "high"]

    def shift(p, k):
        p = str(p).strip(); i = STEP.index(p) if p in STEP else 2
        return STEP[max(0, min(len(STEP) - 1, i + k))]
    RULES = {  # (candidate, case, partner): {align: (step shift, extra USD range text, lever, why)}
        ("Flávio Bolsonaro", "best", "US"): {"aligned": (+2, "0 (Section 301 is a trade finding; $ cell stays +2 to +6)", "amnesty / veto override",
                                                         "aligned Congress passes the broad amnesty (Amin PL) in the transition (A32) → political layer with Washington eases; Magnitsky lift precedent tied to Chamber vote (A11)"),
                                             "transactional": (+1, "0", "amnesty", "amnesty passes at a price; STF suspension of Lei 15.402 (G10) signals institutional conflict"),
                                             "opposed": (0, "0", "amnesty", "centrão withholds amnesty as leverage; US political layer unchanged")},
        ("Flávio Bolsonaro", "worst", "US"): {"aligned": (-1, "0", "—", "Congress removes a source of US conditionality (amnesty) — concessions demanded shift to ethanol/Pix (A19, B24)"),
                                              "transactional": (0, "0", "—", "no Congress lever on ethanol/digital concessions"), "opposed": (0, "0", "—", "same")},
        ("Lula IV", "best", "US"): {"aligned": (0, "0", "—", "Rubio's 'no good faith' (A25) keeps the 301 layer regardless of Congress"),
                                    "transactional": (0, "0 to +0.5", "veto override", "Congress already overrode the dosimetria veto (2026-04-30, G09) → political irritant partly removed without Lula; 301 unchanged"),
                                    "opposed": (+1, "0 to +0.5", "amnesty override", "an opposed Congress passes the broad amnesty over Lula's veto (257/41 available) → US political layer eases; STF reaction = conflict premium")},
        ("Lula IV", "worst", "US"): {"aligned": (+1, "−2 to −5 tail", "Reciprocity Law 15.122", "a Congress aligned with Lula lowers the political cost of using the Reciprocity Law (unused to date) → escalation tail"),
                                     "transactional": (0, "0", "Reciprocity Law", "law dormant; Camex decides; FPA opposes retaliation that invites agro counter-measures"),
                                     "opposed": (-1, "0", "Reciprocity Law", "hostile Congress raises the cost of retaliation; cannot force use")},
        ("Flávio Bolsonaro", "worst", "China"): {"aligned": (0, "0", "Senate FTO / anti-terror bill (flag)", "BRICS re-evaluation needs no Congress (A29); a PCC/CV FTO bill (A27) could touch correspondent banking (C14) — flag only"),
                                                 "transactional": (0, "0", "—", "no Congress role"), "opposed": (0, "0", "—", "no Congress role")},
        ("Flávio Bolsonaro", "worst", "EU"): {"aligned": (+2, "−2 to −5 (cell range unchanged)", "environmental law / veto-free rollbacks",
                                                         "FPA-dominant Congress + aligned executive: licensing-type rollbacks pass without vetoes (C30 precedent), EUDR from 2026-12-30 (C23) → high-risk / de-risking tail low → medium"),
                                              "transactional": (+1, "−2 to −5", "environmental law", "rollbacks pass case-by-case"),
                                              "opposed": (0, "−2 to −5", "environmental law", "centrão bargaining slows rollbacks; executive enforcement still decides PFLS")},
        ("Lula IV", "worst", "EU"): {"aligned": (0, "−2 to 0", "—", "executive enforcement continues; EU-side (EP/CJEU, C05/C06) dominates"),
                                     "transactional": (+1, "−2 to 0 (+ rollback tail)", "veto override on environmental law", "Congress-driven rollback path even with executive enforcement (52 of 63 licensing vetoes overridden, C30)"),
                                     "opposed": (+1, "−2 to 0 (+ rollback tail)", "veto override", "overrides become routine; EUDR reclassification tail rises from a low base")},
        ("Lula IV", "best", "EU"): {"aligned": (0, "0", "ratification done", "DL 14/2026 already promulgated (G05); Congress cannot undo provisional application"),
                                    "transactional": (0, "0", "ratification done", "same"), "opposed": (0, "0", "ratification done", "same")},
        ("Flávio Bolsonaro", "best", "EU"): {"aligned": (0, "0", "ratification done", "same; the EU side, not Brazil's Congress, is the binding constraint"),
                                             "transactional": (0, "0", "ratification done", "same"), "opposed": (0, "0", "ratification done", "same")},
        ("Lula IV", "best", "Mercosur/LatAm"): {"aligned": (0, "0 (EFTA DL 146/2026 and Singapore DL 147/2026 already ratified)", "treaty ratification (CF 49 I)", "the plan's pending EFTA item is done (in force for Brazil from 2026-10-01, G21); Congress's ratification role is spent for the current pipeline"),
                                                "transactional": (0, "0", "treaty ratification", "same; 2026 lags were 2–9 months from signature to DL"),
                                                "opposed": (0, "0", "treaty ratification", "same; future deals (UAE, Canada) not yet signed")},
        ("Flávio Bolsonaro", "best", "Mercosur/LatAm"): {"aligned": (0, "0", "treaty ratification", "EFTA/Singapore already ratified"), "transactional": (0, "0", "treaty ratification", "same"),
                                                         "opposed": (0, "0", "treaty ratification", "same")},
        ("Flávio Bolsonaro", "worst", "Mercosur/LatAm"): {"aligned": (+1, "−2 to −4", "CET / Mercosur protocol changes need Congress", "turning Mercosur into an FTA needs treaty changes Congress ratifies → aligned Congress makes the worst cell easier"),
                                                          "transactional": (0, "−2 to −4", "same", "industrial lobby (autos) in centrão slows it"), "opposed": (-1, "−2 to −4", "same", "blocked")},
        ("Flávio Bolsonaro", "best", "Rest"): {"aligned": (0, "+0.5 to +2 (critical minerals, strategic)", "Law 15.506 / Cimce (B51)", "Congress's role spent; Presidency approves deals → fast-track US minerals deals"),
                                               "transactional": (0, "+0.5 to +2", "Cimce", "same"), "opposed": (0, "+0.5 to +2", "Cimce", "same")},
        ("Lula IV", "best", "Rest"): {"aligned": (0, "0", "Senate: external credit (CF 52 V–VIII)", "NDB/CAF loans approved"),
                                      "transactional": (0, "0", "Senate", "delays to NDB/CAF loans for states; ≈0 export effect"),
                                      "opposed": (-1, "0", "Senate", "hostile Senate delays external credit and ambassador confirmations (US slot vacant, A38); ≈0 direct export $")},
    }
    rows = []
    for r in X.itertuples():
        for align in ("aligned", "transactional", "opposed"):
            k = (r.candidate, r.case, r.partner)
            rule = RULES.get(k, {}).get(align, (0, "0", "none", "no Congress lever on this cell"))
            rows.append(dict(candidate=r.candidate, case=r.case, partner=r.partner, centrao_alignment=align, exports_probability=r.probability_qual,
                             congress_adjusted_probability=shift(r.probability_qual, rule[0]), probability_shift_steps=rule[0],
                             exports_usd_bn_range=f"{r.impact_low_usd_bn_yr:+.1f} to {r.impact_high:+.1f}", congress_usd_modifier=rule[1],
                             lever=rule[2], rationale=rule[3], dominance_note="commodity/ToT state dominates (exports 6b: ToT ±10% ≈ ±$14–22bn/yr)",
                             exports_fact_ids=r.external_fact_ids))
    M = pd.DataFrame(rows)
    fp = {}
    for cand, c2 in (("Lula IV", "Lula IV"), ("Flávio", "Flávio Bolsonaro")):
        for align in ("aligned", "transactional", "opposed"):
            fp[(cand, align)] = {}
            for part in ("US", "China", "EU", "Mercosur/LatAm", "Rest"):
                s = M[(M.candidate == c2) & (M.partner == part) & (M.centrao_alignment == align)]
                txt = "; ".join(f"{t.case}: {t.exports_probability}→{t.congress_adjusted_probability}, $ {t.exports_usd_bn_range} (Congress: {t.congress_usd_modifier})"
                                for t in s.itertuples())
                fp[(cand, align)][part] = txt
    return M, fp


# ============================================================================ 10. charts
def charts(S, L, EV, B, A_, SC, R, RT):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    CH = OUT / "charts"; CH.mkdir(exist_ok=True)
    INK, MUTED, GRID = "#1f2933", "#7b8794", "#e4e7eb"
    LEFTC, RIGHTC, CENTC, OTHC = "#c0392b", "#1f4e9c", "#e0a526", "#9aa5b1"
    base = dict(template="plotly_white", font=dict(family="Inter, Arial", size=13, color=INK), margin=dict(l=60, r=30, t=70, b=50))
    paths = {}
    # 1 seats & ENPP timeline with president bands
    cd = S[S.chamber == "CD"].copy()
    yrs = sorted(cd.leg_id.unique()); legy = {l: int(s[:4]) for l, s, e, y in LEG}
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.06,
                        subplot_titles=("Chamber seat share by bloc at legislature start (BLS ideology; centrão narrow shown separately)", "Effective number of parties (Chamber)"))
    x = [legy[l] for l in yrs]
    for lab, col, f in (("Left (BLS ≤ 4)", LEFTC, lambda d: d[d.bloc == "left"].seats_share.sum()),
                        ("Centre (4–6)", CENTC, lambda d: d[d.bloc == "centre"].seats_share.sum()),
                        ("Right (≥ 6)", RIGHTC, lambda d: d[d.bloc == "right"].seats_share.sum()),
                        ("No ideology score", OTHC, lambda d: d[d.bloc.isna()].seats_share.sum())):
        fig.add_trace(go.Bar(x=x, y=[100 * f(cd[cd.leg_id == l]) for l in yrs], name=lab, marker_color=col), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=[100 * cd[(cd.leg_id == l) & (cd.centrao_narrow == 1)].seats_share.sum() for l in yrs], name="Centrão (narrow)",
                             mode="lines+markers", line=dict(color=INK, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=[enpp(cd[cd.leg_id == l].seats_share) for l in yrs], mode="lines+markers+text", name="ENPP",
                             text=[f"{enpp(cd[cd.leg_id == l].seats_share):.1f}" for l in yrs], textposition="top center", line=dict(color=INK)), row=2, col=1)
    for d in DY.itertuples():
        fig.add_vrect(x0=d.start.year + (d.start.month - 1) / 12, x1=d.end.year + (d.end.month - 1) / 12, fillcolor=LEFTC if d.lean3 == "left" else RIGHTC if d.lean3 == "right" else CENTC,
                      opacity=0.06, line_width=0, row=2, col=1)
    fig.update_layout(barmode="stack", title="Brazil's Chamber, 1987–2027: blocs, centrão and fragmentation", yaxis_title="% of seats", **base)
    p = CH / "1_seats_enpp_timeline.html"; fig.write_html(p, include_plotlyjs="cdn"); paths["1"] = str(p)
    # 2 alignment vs primary balance / real rate by dyad
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Primary balance % GDP (dyad mean)", "Real policy rate % (dyad mean)"))
    for j, m in enumerate(("pb", "realrate"), start=1):
        U = annual_units(OUTC[m]["s"], L, "coalition_share_cd_start")
        if U.empty:
            continue
        D = U.groupby("dyad").agg(y=("y", "mean"), x=("x", "first")).reset_index()
        D = D.merge(L[["dyad", "lean"]], on="dyad")
        fig.add_trace(go.Scatter(x=100 * D.x, y=D.y, mode="markers+text", text=D.dyad, textposition="top center", showlegend=False,
                                 marker=dict(size=11, color=[LEFTC if l == "left" else RIGHTC if l == "right" else CENTC for l in D.lean])), row=1, col=j)
        if len(D) >= 3:
            b = np.polyfit(100 * D.x, D.y, 1); xs = np.linspace(100 * D.x.min(), 100 * D.x.max(), 10)
            fig.add_trace(go.Scatter(x=xs, y=np.polyval(b, xs), mode="lines", line=dict(color=MUTED, dash="dash"), showlegend=False), row=1, col=j)
        fig.update_xaxes(title_text="Coalition share of Chamber seats at dyad start (%)", row=1, col=j)
    fig.update_layout(title="Alignment vs fiscal and rate outcomes, by president × legislature (n = dyads with data)", **base)
    p = CH / "2_alignment_scatter.html"; fig.write_html(p, include_plotlyjs="cdn"); paths["2"] = str(p)
    # 3 event study panels G1 vs G2
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Ibovespa USD (log %)", "BRL vs USD (log %, + = stronger BRL)", "NTN-B 10y real (bp)"))
    for j, sid in enumerate(("ibovespa_usd", "brl_usd", "gov_real_yield_10y"), start=1):
        for g, col in (("G1 tightening", RIGHTC), ("G2 loosening", LEFTC), ("G4 foreign policy", CENTC)):
            e = EV[(EV.series_id == sid) & (EV.window == "[-5,+5]") & (EV.group == g) & (EV.stage == "primary") & EV.car.notna()]
            fig.add_trace(go.Box(y=e.car, name=g.split(" ")[0], marker_color=col, boxpoints="all", text=e.event, showlegend=False), row=1, col=j)
    fig.update_layout(title="Abnormal change over [−5,+5] trading days — first Chamber floor vote (primary stage)", **base)
    p = CH / "3_event_study_groups.html"; fig.write_html(p, include_plotlyjs="cdn"); paths["3"] = str(p)
    # 4 emendas vs public investment and NTN-B
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    bb = B[B.index <= 2026]
    fig.add_trace(go.Bar(x=bb.index, y=bb.emendas_pct_gdp, name="Emendas % GDP (paid; authorised if no paid figure)", marker_color=CENTC), secondary_y=False)
    fig.add_trace(go.Scatter(x=bb.index, y=bb["wb/GC.NFN.TOTL.GD.ZS.BR"], name="Net investment in non-financial assets % GDP (WB GFS)", mode="lines+markers", line=dict(color=INK)), secondary_y=False)
    fig.add_trace(go.Scatter(x=bb.index, y=bb["gov_real_yield_10y"], name="NTN-B 10y real yield %", mode="lines+markers", line=dict(color=LEFTC)), secondary_y=True)
    for yv, lab in ((2015, "EC 86"), (2019, "EC 100/105"), (2022, "STF ADPF 854"), (2024, "LC 210")):
        fig.add_vline(x=yv, line=dict(color=MUTED, dash="dot")); fig.add_annotation(x=yv, y=1.04, yref="paper", text=lab, showarrow=False, font=dict(size=11, color=MUTED))
    fig.update_layout(title="Budget capture: emendas vs public investment and real yields, 2014–2026", **base)
    fig.update_yaxes(title_text="% GDP", secondary_y=False); fig.update_yaxes(title_text="% p.a.", secondary_y=True)
    p = CH / "4_emendas_investment_ntnb.html"; fig.write_html(p, include_plotlyjs="cdn"); paths["4"] = str(p)
    # 5 reform table heatmap
    if isinstance(RT, dict) and RT:
        D = pd.DataFrame(RT["per_dyad"])
        z = D[["coalition_share_cd_start", "pres_party_share_cd", "enpp_cd", "reforms_per_year"]].copy()
        zn = (z - z.mean()) / z.std()
        fig = go.Figure(go.Heatmap(z=zn.T.values, x=D.dyad, y=["Coalition share (start)", "President's party share", "ENPP", "Economic reforms / yr"],
                                   text=z.T.round(2).values, texttemplate="%{text}", colorscale="RdBu", zmid=0, showscale=False))
        fig.update_layout(title="What passed under what alignment: economic ECs/major laws per year vs Chamber arithmetic (z-colour, raw labels)", **base)
        p = CH / "5_reform_heatmap.html"; fig.write_html(p, include_plotlyjs="cdn"); paths["5"] = str(p)
    # 6 2027 arithmetic bars
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Chamber 2027 (513)", "Senate 2027 (81)"))
    for j, ch in enumerate(("CD", "SF"), start=1):
        a = A_[ch]
        for lab, v, col in (("Left", a["left"], LEFTC), ("MDB/PSDB/Cidadania", a["mdb_psdb_cid"], OTHC), ("Unclassified", a["unclassified"], "#cbd2d9"),
                            ("Centrão", a["centrao"], CENTC), ("PL+Novo+Missão", a["right_core"], RIGHTC)):
            fig.add_trace(go.Bar(x=[v], y=[ch], orientation="h", name=lab, marker_color=col, showlegend=(j == 1), text=[f"{v:.0f}"], textposition="inside"), row=1, col=j)
        for thr, lab in ((a["pec"], "PEC 3/5"), (a["override"], "override (abs. majority)")):
            fig.add_vline(x=thr, line=dict(color=INK, dash="dash"), row=1, col=j)
            fig.add_annotation(x=thr, y=0.5, text=f"{lab} {thr}", showarrow=False, yshift=40, font=dict(size=11), row=1, col=j)
    fig.update_layout(barmode="stack", title="2027 arithmetic: 308/49 for PECs, 257/41 for veto overrides", **base)
    p = CH / "6_arithmetic_2027.html"; fig.write_html(p, include_plotlyjs="cdn"); paths["6"] = str(p)
    # 7 scenario tornado (NTN-B and debt 2030 ranges)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("NTN-B 10y real yield range (%)", "Gross debt 2030 range (% GDP)"))
    labs = [f"{r.candidate.split(' ')[0]} · {r.centrao_alignment} ({r.probability_qual})" for r in SC.itertuples()]
    def rng_(s):
        nums = [float(v) for v in re.findall(r"\d+\.?\d*", s.split("(")[0])]
        return nums[0], nums[1]
    for j, col_ in enumerate(("ntnb_10y_range", "debt_gdp_2030_range"), start=1):
        lo = [rng_(v)[0] for v in SC[col_]]; hi = [rng_(v)[1] for v in SC[col_]]
        fig.add_trace(go.Bar(y=labs, x=np.array(hi) - np.array(lo), base=lo, orientation="h", showlegend=False,
                             marker_color=[RIGHTC if "Flávio" in l else LEFTC for l in labs], opacity=0.8), row=1, col=j)
    fig.update_layout(title="Scenario matrix: run-off winner × centrão alignment (ranges; probabilities qualitative)", **base, height=520)
    p = CH / "7_scenario_tornado.html"; fig.write_html(p, include_plotlyjs="cdn"); paths["7"] = str(p)
    # 8 robustness heatmap: share of grid cells with the N1 sign, metric x explanatory variable
    RR = R[~R.x.str.startswith("centrao")].groupby(["metric", "x"]).n1_consistent.mean().unstack()
    fig = go.Figure(go.Heatmap(z=RR.values, x=list(RR.columns), y=[OUTC[m]["name"] for m in RR.index], zmin=0, zmax=1, colorscale="RdBu",
                               text=np.round(RR.values, 2), texttemplate="%{text}", colorbar=dict(title="share N1-sign")))
    fig.update_layout(title="Robustness: share of grid cells with the N1-expected sign (1 = all cells say alignment helps; 0 = all say the opposite)", **base, height=520)
    p = CH / "8_robustness_heatmap.html"; fig.write_html(p, include_plotlyjs="cdn"); paths["8"] = str(p)
    return paths


# ============================================================================ 11. results
def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else round(float(o), 5)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (pd.Timestamp, dt.date)):
        return str(o)[:10]
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_results(res):
    (OUT / "results.json").write_text(json.dumps(_clean(res), indent=1, ensure_ascii=False, default=str))


def main():
    res = {"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    res["anchors"] = anchors()
    S, COAL, G, L = load_panel()
    S.to_csv(OUT / "congress_seats.csv", index=False)
    L.to_csv(OUT / "congress_legislatures.csv", index=False)
    A_ = arithmetic_2027(S)
    res["arithmetic_2027"] = A_
    # 2027 hypothetical dyads (not in the historical sample)
    res["dyad_2027"] = {c: dyad_alignment(S, COAL, "x", 58, c, pres_ideo=pres_bls("Lula") if c == "Lula IV" else (BLS[(2021, "PL")]))
                        for c in ("Lula IV", "Flávio")}
    DST = dyad_stats(L); res["dyad_stats"] = DST
    res["posthoc_detrended"] = detrended_check(L)
    R = robustness_grid(L); R.to_csv(OUT / "robustness_matrix.csv", index=False)
    V = verdicts(DST, R); res["verdicts_G1_G2"] = V
    res["robustness_sign_share"] = R[~R.x.str.startswith("centrao")].groupby("metric").n1_consistent.agg(["mean", "size"]).round(3).to_dict("index")
    res["robustness_centrao"] = R[R.x.str.startswith("centrao")][["metric", "x", "unit", "slope", "rho", "n_units"]].round(4).to_dict("records")
    res["G3"] = governability_tests(L)
    RTab, RT = reform_table(L, S); res["G4"] = RT
    if len(RTab):
        RTab.to_csv(OUT / "reform_table.csv", index=False)
    EV, EG, EGRP, M92, enotes, events = event_section()
    EV.to_csv(OUT / "event_study.csv", index=False)
    res["event_study"] = dict(notes=enotes, group_compare=EG.to_dict("records"), group_means=EGRP.to_dict("records"),
                              monthly_1992=M92.assign(date=M92.date.astype(str)).to_dict("records"), events=events)
    B, cors = budget_capture()
    for y in B.index:
        for sid in ("wb/GC.NFN.TOTL.GD.ZS.BR", "wb/NE.GDI.FTOT.ZS.BR", "gov_real_yield_10y", "r_minus_g"):
            if B.at[y, sid] == B.at[y, sid]:
                emit(f"annual|{sid}|{y}", B.at[y, sid], sid, "annual_panel")
    res["budget_capture"] = dict(table=B.reset_index().to_dict("records"), spearman=cors)
    res["G8"] = g8_fpa(L); res["G9"] = g9_coattails(L)
    T = g10_treaties(); res["G10"] = T.assign(**{c: T[c].astype(str) for c in ("signed_date", "congress_approval_date", "promulgation_date")}).to_dict("records") if len(T) else []
    res["G11"] = g11_lean_alignment(L)
    M, fp = fp_modifiers(); M.to_csv(OUT / "exports_cell_modifiers.csv", index=False)
    SC = scenarios(A_, fp); SC.to_csv(OUT / "scenario_matrix.csv", index=False)
    # annual congress table
    Ca = []
    for y in range(1987, 2027):
        d_ = ATTR.at[y, "c"]; lr = L.set_index("dyad").loc[d_] if d_ in set(L.dyad) else None
        b = B.loc[y] if y in B.index else None
        Ca.append(dict(year=y, leg_id=int(lr.leg_id) if lr is not None else None, dyad_id=int(lr.dyad_id) if lr is not None else None, dyad=d_,
                       gov_success_rate=lr.gov_success_rate if lr is not None else None,
                       emendas_authorized_brl_bn=b.emendas_authorized_brl_bn if b is not None else None, emendas_paid_brl_bn=b.emendas_paid_brl_bn if b is not None else None,
                       emendas_impositivas_brl_bn=b.emendas_impositivas_brl_bn if b is not None else None, emendas_rp9_brl_bn=b.emendas_rp9_brl_bn if b is not None else None,
                       emendas_pix_brl_bn=b.emendas_pix_brl_bn if b is not None else None, discretionary_brl_bn=b.discretionary_brl_bn if b is not None else None,
                       emendas_share_discretionary=b.emendas_share_discretionary if b is not None else None, emendas_pct_gdp=b.emendas_pct_gdp if b is not None else None,
                       source_ids="research/emendas.csv; research/governability.csv"))
    pd.DataFrame(Ca).to_csv(OUT / "congress_annual.csv", index=False)
    # joined panel: dyad x metric (raw dyad means)
    rows = []
    for m, o in OUTC.items():
        U = annual_units(o["s"], L, "coalition_share_cd_start")
        if U.empty:
            continue
        for dd, g in U.groupby("dyad"):
            rows.append(dict(dyad=dd, metric=m, series_id=o["sid"], value_mean=g.y.mean(), n_years=len(g), years=f"{g.year.min()}–{g.year.max()}"))
            emit(f"dyad_mean|{m}|{dd}", g.y.mean(), o["sid"], "annual_panel", note=f"years {g.year.min()}–{g.year.max()}, 1-July attribution")
    P = pd.DataFrame(rows).merge(L, on="dyad", how="left"); P.to_csv(OUT / "congress_panel.csv", index=False)
    res["charts"] = charts(S, L, EV, B, A_, SC, R, RT)
    res["sql"] = SQL; res["numbers"] = NUMS
    res["meta"] = {k: META[k] for k in META}
    write_results(res)
    return res, S, L, R, V, EV, EG, B, A_, SC, M


if __name__ == "__main__":
    out = main()
    print("done")
