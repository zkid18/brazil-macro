"""Writes report.md from the study module's objects (re-runs the study; deterministic, seed 0)."""
import numpy as np, pandas as pd, json
import politics_lean_study as S

OUT = S.OUT
plan = (OUT / "plan.md").read_text().splitlines()
R, MET = S.RESULTS, S.MET


def f(x, nd=2, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return (f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}")


def ci(c, nd=2):
    return "–" if not c else f"[{c[0]:+.{nd}f}, {c[1]:+.{nd}f}]"


def md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r.values) + " |")
    return "\n".join(out)


def mrow(mid, nd=2):
    r = R[mid]; m = MET[mid]
    return dict(id=mid, metric=m["name"], unit=m["unit"], series=r["series_ids"], last=r["last_date"],
                **{"n L/R": f"{r.get('n_left', 0)}/{r.get('n_right', 0)}", "mean L": f(r.get("mean_left"), nd), "mean R": f(r.get("mean_right"), nd),
                   "Δ L−R": f(r.get("diff"), nd, True), "80% CI": ci(r.get("ci80"), nd), "95% CI": ci(r.get("ci95"), nd),
                   "perm p (floor)": f"{f(r.get('perm_p'))} ({f(r.get('p_min_attainable'), 3)})" if "perm_p" in r else "–",
                   "BH q": f(r.get("bh_q")), "sign-cons.": f"{r['sign_consistency_share']:.0%}" if r.get("sign_consistency_share") is not None else "–",
                   "ToT-adj Δ": f(r.get("diff_tot"), nd, True), "ToT-adj 80% CI": ci(r.get("ci80_tot"), nd), "verdict": r["verdict"]})


def bucket_table(bucket, primary=True):
    ids = [k for k in MET if MET[k]["bucket"] == bucket and MET[k]["primary"] == primary and k in R and k != "D3r"]
    if not ids:
        return "_none_"
    df = pd.DataFrame([mrow(k) for k in ids])
    if primary:
        df = df[["id", "metric", "unit", "n L/R", "mean L", "mean R", "Δ L−R", "80% CI", "perm p (floor)", "BH q", "sign-cons.", "ToT-adj Δ", "ToT-adj 80% CI", "verdict"]]
    else:
        df = df[["id", "metric", "unit", "n L/R", "Δ L−R", "80% CI", "perm p (floor)", "ToT-adj Δ"]]
    return md_table(df)


def term_values_table(ids):
    rows = []
    for mid in ids:
        tv = R[mid].get("term_values", {})
        rows.append({"metric": f"{mid} {MET[mid]['name']} ({MET[mid]['unit']})", **{t: f(tv.get(t), 2) for t in S.TERM_ORDER}})
    return md_table(pd.DataFrame(rows))


# ---------------------------------------------------------------- key numbers
Q = S.Q0S
qt = Q[Q.level == "term"]; qy = Q[Q.level == "year"]
H0 = {m: (Q[(Q.metric_id == m) & (Q.level == "term")].iloc[0], Q[(Q.metric_id == m) & (Q.level == "year")].iloc[0]) for m in ("A1", "D1", "D2", "C2")}
comp = S.COMP_RES
EVG = S.EVG.set_index(["series_id", "window"])
EV = S.EV


def evg(sid, w, k):
    try:
        return EVG.loc[(sid, w), k]
    except KeyError:
        return np.nan


# brent-adjusted group comparison
evb = EV[EV.group.isin(["left win", "right transition"]) & EV.car_brent_adj.notna()]
EVB = evb.groupby(["series_id", "window", "group"]).car_brent_adj.mean().unstack()

PRE = S.PRE.set_index(["series_id", "window"])
SC = S.SCEN
DB = S.DEBT_BRANCH
ST = S.START
MK = S.MKT


def scen(mid, br):
    r = SC[(SC.metric_id == mid) & (SC.branch.str.startswith(br))]
    return None if not len(r) else r.iloc[0]


def scen_cell(mid, br, nd=1):
    r = scen(mid, br)
    if r is None or pd.isna(r.get("hist_median")):
        return "n<2"
    mods = [r[f"model {p}"] for p in S.TOT_PATHS]
    return (f"hist {r.hist_p25:.{nd}f} to {r.hist_p75:.{nd}f} (med {r.hist_median:.{nd}f}); "
            f"model {min(mods):.{nd}f} to {max(mods):.{nd}f}")


def debt_cell(br):
    d = DB[DB.branch.str.startswith(br)]
    return f"{d.debt_2030.min():.0f}–{d.debt_2030.max():.0f} (median-pb, r−g {ST['r_minus_g']['value']:.2f}: {d[(d.pb_case == 'pb median') & (d.r_minus_g.round(2) == round(ST['r_minus_g']['value'], 2))].debt_2030.iloc[0]:.0f}; " + (
        f"Lula III run-rate {S.debt_path(S.D0, ST['r_minus_g']['value'], S.PB_HIST['Lula III'][1])[-1]:.0f})" if br == "S-L" else
        f"Bolsonaro ex-2020 run-rate {S.debt_path(S.D0, ST['r_minus_g']['value'], S.BOLSO_EX2020)[-1]:.0f})")


power = "\n".join(plan[187:188])  # verbatim power statement line
assert power.startswith("**Power statement"), power[:40]
constraints = "\n".join(plan[4:58])

# ---------------------------------------------------------------- report text
L = []
A = L.append
A("# Brazil: political lean vs economic, social and market outcomes, 1985–2026 — with conditional 2027–2030 scenarios\n")
A(f"_Generated {pd.Timestamp.now('UTC'):%Y-%m-%d %H:%M} UTC from `{S.DB}` (read-only). Pre-registration: `preregistration.md` (written before results). "
  "Code: `politics_lean_study.py`, `make_charts.py`, `make_report.py`. Every warehouse number below carries its series_id; latest dates are in the Appendix._\n")

A("## 0. External fact (NOT in the warehouse — fenced)\n")
A("```text\nEXTERNAL, user-supplied, not in brazil_macro.duckdb (political_events ends with the 2026-10-04 'first round' row and no result):\n"
  "  First round 2026-10-04: Flávio Bolsonaro (PL, right) 47.0% · Lula (PT, left) 44.9%. Run-off 2026-10-25.\n"
  "  Sources: CNN https://www.cnn.com/2026/10/04/americas/brazil-president-elections-2026-latam-intl\n"
  "           Washington Post https://www.washingtonpost.com/world/2026/10/04/bolsonaro-lula-head-runoff-5-takeaways-brazils-election/\n"
  "Use in this report: only to choose which scenario branches are presented as primary (Lula IV vs Flávio Bolsonaro).\n"
  "It does not enter any estimate. Market data in the warehouse end 2026-10-01/02, so the market reaction to the\n"
  "first-round result is NOT observable here.\n```\n")

# ---- Summary
A("## 1. Summary\n")
A("**Q0 — how much of the between-term variation is lean, and how much is the terms-of-trade (ToT) cycle?** "
  f"Across the 23 primary metrics, a Shapley split of between-term R² gives lean a median share of **{qt.shap_lean.median():.2f}** vs ToT **{qt.shap_tot.median():.2f}**; "
  f"ToT matches or beats lean in **{int(qt.tot_ge_lean.sum())}/{len(qt)}** metrics at term level (year level: lean {qy.shap_lean.median():.2f} vs ToT {qy.shap_tot.median():.2f}, "
  f"ToT ≥ lean in {int(qy.tot_ge_lean.sum())}/{len(qy)}). The pre-registered H0-primary (ToT explains at least as much as lean for A1, D1, D2, C2) **holds at term level for all four** "
  f"(A1 GDP growth lean {H0['A1'][0].shap_lean:.2f} vs ToT {H0['A1'][0].shap_tot:.2f}; D1 USD equity {H0['D1'][0].shap_lean:.2f} vs {H0['D1'][0].shap_tot:.2f}; "
  f"D2 BRL {H0['D2'][0].shap_lean:.2f} vs {H0['D2'][0].shap_tot:.2f}; C2 Δdebt {H0['C2'][0].shap_lean:.2f} vs {H0['C2'][0].shap_tot:.2f}), "
  f"but at year level GDP growth tilts the other way (lean {H0['A1'][1].shap_lean:.2f} vs ToT {H0['A1'][1].shap_tot:.2f}). "
  "Where lean does carry more weight it is in **policy instruments** — real policy rate, primary balance, interest bill, real minimum wage — and, at year level, in **labour and distribution** (unemployment lean 0.31 vs ToT 0.02; Δ Gini 0.26 vs 0.10); not in markets, the external accounts or debt. "
  "Neither factor explains most of the variance in most outcomes; the bulk is term-specific shocks (2002 confidence crisis, GFC, 2015–16 recession and impeachment, COVID, 2026 oil shock).\n")
A(power + "\n")
A("Consequently **nothing clears Benjamini–Hochberg at q = 0.10 and no composite clears Holm at α = 0.10**; the results below are effect sizes with honest bands. "
  "The 80% cluster-bootstrap CIs (3–4 terms per side) are narrower than the permutation test implies; read 'robust-by-CI' as 'consistent direction', not 'significant'.\n")

def line(mid, txt):
    r = R[mid]
    return (f"- **{mid} {MET[mid]['name']}** — Δ L−R {f(r.get('diff'), 2, True)} {MET[mid]['unit']} (80% CI {ci(r.get('ci80'))}; perm p {f(r.get('perm_p'))}, floor {f(r.get('p_min_attainable'), 3)}; "
            f"sign-consistent in {r.get('sign_consistency_share', 0):.0%} of {r.get('n_cells', 0)} cells; ToT-adjusted {f(r.get('diff_tot'), 2, True)}). {txt}")

A("### Per-bucket findings (Δ = mean of left terms − mean of right/centre-right terms, coding A)\n")
A("Buckets E (labour & distribution) and F (health, education, safety) are given the same space as fiscal and markets: the user's framing — that "
  "institutional quality is better read through health, social policy, poverty, inequality and education than through corruption indices — is adopted here. WGI is reported last among the social buckets for that reason.\n")
A("**A. Growth.**")
A(line("A1", "Left terms grew faster, and the gap **widens** after ToT adjustment — but Collor (−1.3%) and Temer (−0.1%) sit on the right, and Dilma (1.2%) on the left; 2003+ only has Temer/Bolsonaro as 'right'."))
A(line("A2", ""))
A(line("A3", "Investment shows no robust lean pattern raw; after ToT adjustment the left edge is +1.6 pts but the permutation test is uninformative."))
A(f"- Composite COMP-G: Δ {comp[('COMP-G Growth','raw')]['diff']:+.2f} z (80% CI {ci(comp[('COMP-G Growth','raw')]['ci80'])}, perm p {comp[('COMP-G Growth','raw')]['perm_p']:.2f}, Holm {comp[('COMP-G Growth','raw')]['holm_p']:.2f}); ToT-adj {comp[('COMP-G Growth','tot')]['diff']:+.2f}.\n")
A("**B. Prices and rates.**")
A(line("B1", "The raw gap is entirely Collor's hyperinflation (coded right); post-1995 and rank versions flip sign or vanish. No lean signal in inflation."))
A(line("B2", "Real policy rates were **higher** under PT terms (Lula I–II 9.7, Lula III 8.9 vs Temer 5.3, Bolsonaro 2.3 — `real_policy_rate`), the right narrative's sign. But only 2 right terms exist post-2001, and both started after the 2015–16 recession; the start-level-adjusted gap is +1.0 pt."))
A("**C. Fiscal.**")
A(line("C1", "Left terms ran larger primary surpluses (Lula I–II +3.2% vs Temer −2.1%, Bolsonaro −2.3% incl. COVID). This contradicts the right narrative's expectation; but FHC's 1999–2002 surpluses are outside `primary_balance_gdp` coverage (starts 2002-11), and Lula III (−0.8) breaks the pattern."))
A(line("C2", "Gross-debt change has **no** lean pattern (sign-consistency below 50%). Only 4 terms observed (series starts 2006-12)."))
A(line("C4", "Higher interest bill under left terms — mechanically tied to the higher real rate (B2)."))
A(f"- Composite COMP-S 'orthodox stability': Δ {comp[('COMP-S Orthodox stability','raw')]['diff']:+.2f} z (80% CI {ci(comp[('COMP-S Orthodox stability','raw')]['ci80'])}, perm p {comp[('COMP-S Orthodox stability','raw')]['perm_p']:.2f}) — no difference.\n")
A("**D. Markets and external.**")
A(line("D1", "USD equity returns: no lean pattern; ToT explains ~0.9 of between-term variance."))
A(line("D2", "BRL: left terms saw a stronger BRL on average (driven by Lula I–II's commodity boom and FHC II's 1999/2002 devaluations — the 2002 'Lula panic' is booked to FHC under July-1 attribution); ToT explains ~0.8."))
A(line("D3", ""))
A(f"- Composite COMP-M: Δ {comp[('COMP-M Markets','raw')]['diff']:+.2f} z (80% CI {ci(comp[('COMP-M Markets','raw')]['ci80'])}, perm p {comp[('COMP-M Markets','raw')]['perm_p']:.2f}) — no difference over full terms. The lean signal in markets is in **event windows**, not in term averages (section 6).\n")
A("**E. Labour and distribution (equal prominence).**")
A(line("E1", "Unemployment was lower in left terms in **every** specification cell; start-level-adjusted change still favours left (−0.66 pt/yr). Temer/Bolsonaro inherited the 2015–16 recession (start 8.5% / 12.3%)."))
A(line("E3", "Real minimum wage grew ~3 pts/yr faster under left terms (Lula I–II +5.5%/yr, Lula III +3.3%, Dilma +2.2% vs Bolsonaro +0.1%, FHC +0.4%) — the one result both narratives predicted; its 'employment cost' (informality up, E2) is **not** visible: informality fell faster under left terms (E2 Δ −1.7 pts/yr, secondary)."))
A(line("E5", "Gini change: the baseline sign is **misleading** — it is driven by Collor's 1990–92 'fall' (−3.4 pts/yr), which straddles the PNAD 1992 redesign (no 1991 survey). In 1995+ samples left terms reduce Gini faster in 87% of cells (Lula III −0.8/yr, Lula I–II −0.6 vs Temer +0.7, FHC −0.2). Start-level-adjusted Δ = −0.38 pts/yr. Pre-registered verdict stays 'no robust association'."))
A(line("E6", "Extreme poverty ($3.00/day) fell faster under left terms in 96–100% of cells; ToT adjustment enlarges it (−1.15 pts/yr); 80% CI just touches zero raw. The $8.30 line (secondary) shows the same: Δ −2.1 pts/yr."))
A(f"- Composite **COMP-D Distribution**: Δ **{comp[('COMP-D Distribution','raw')]['diff']:+.2f} z** (80% CI {ci(comp[('COMP-D Distribution','raw')]['ci80'])}, perm p **{comp[('COMP-D Distribution','raw')]['perm_p']:.3f} = the design floor**, Holm {comp[('COMP-D Distribution','raw')]['holm_p']:.2f}); ToT-adjusted {comp[('COMP-D Distribution','tot')]['diff']:+.2f} z (p {comp[('COMP-D Distribution','tot')]['perm_p']:.3f}). "
  "Every left term scores above every right term on this composite — the most extreme labeling possible. It is the strongest lean association in the study and it **survives** the ToT control, but it still misses Holm at 0.10 (0.114) because of the 35-labeling floor.\n")
A("**F. Health, education, safety (equal prominence).**")
A(line("F1", "Infant mortality fell at ~3.3–3.4%/yr under both; the decline slowed after 2015 regardless of lean (Dilma −3.1, Temer −1.5, Bolsonaro −1.0, Lula III −1.2). In the 2003+ sample left terms are faster in every cell, but that is Lula I–II vs post-2016."))
A(line("F5", "Homicide rate: no lean pattern; the biggest falls came under Bolsonaro (−1.5/100k/yr) and Lula III (−1.5, DATASUS 2024–25 preliminary)."))
A(f"- Secondary (descriptive, no inference): life-expectancy gain Δ {f(R['F2'].get('diff'),2,True)} yrs/yr; govt health spending Δ {f(R['F3'].get('diff'),2,True)} % GDP (WB, 2000–2023: right terms slightly higher — Bolsonaro's COVID years); education spending Δ {f(R['F4'].get('diff'),2,True)} % GDP (to 2022); safety-net coverage Δ {f(R['F6'].get('diff'),1,True)} pts (WB ASPIRE, 2006–2022, sparse).\n")
A("**G. Institutions (WGI).**")
A(line("GCC", "Control of Corruption deteriorated slightly more in left terms in 90–100% of cells, but by 0.01 units/yr — invisible against the WGI's own standard errors (~0.1–0.2)."))
A(line("GGE", ""))
A(line("GRL", ""))
A("- Read with the user's framing: on the outcome measures of state capacity that matter to households (E, F), left terms score better on distribution and the same on health and safety; the perception-based WGI shows no lean signal.\n")
A("**H. Environment.**")
A(line("H1", "Primary-forest loss was lower in left terms in ~92% of cells (Lula I–II/Dilma/Lula III vs Temer/Bolsonaro, 2002+ only), CI touches zero; fire years (2016, 2024) and only 2 right terms limit it."))
A("")

# event study summary
A("### Event study (daily; abnormal = raw change minus own-trend over [−250,−121])\n")
A(f"- Six left wins/continuity events vs three right/centre-right transitions (2016 impeachment vote, 2018 run-off, 2019 inauguration). Over [0,+60] trading days, Ibovespa-USD abnormal return averaged **{evg('ibovespa_usd','[0,+60]','mean_left_win'):+.1f}%** after left wins vs **{evg('ibovespa_usd','[0,+60]','mean_right_transition'):+.1f}%** after right transitions "
  f"(Δ {evg('ibovespa_usd','[0,+60]','diff'):+.1f}, permutation p {evg('ibovespa_usd','[0,+60]','perm_p'):.3f}, floor {evg('ibovespa_usd','[0,+60]','p_min'):.3f}); BRL {evg('brl_usd','[0,+60]','mean_left_win'):+.1f}% vs {evg('brl_usd','[0,+60]','mean_right_transition'):+.1f}% (p {evg('brl_usd','[0,+60]','perm_p'):.2f}); "
  f"10y real yield (only 2016+) {evg('gov_real_yield_10y','[0,+60]','mean_left_win'):+.0f} bp vs {evg('gov_real_yield_10y','[0,+60]','mean_right_transition'):+.0f} bp. Around the event itself ([−1,+1]) the difference is small and insignificant (Ibov USD {evg('ibovespa_usd','[-1,+1]','diff'):+.1f}, p {evg('ibovespa_usd','[-1,+1]','perm_p'):.2f}).")
A("- Caveats: the three right events are one episode (2016–2019, all from a post-recession trough with impeachment-era repricing), 2018 run-off and 2019 inauguration windows overlap, and 2022 run-off/2023 inauguration overlap. Brent-adjusted versions keep the sign and size (Ibov USD [0,+60]: −2.7% vs +17.7%). EMBI shows **no** lean difference at any window. Focus Selic/FX 'reactions' at 1 January inaugurations are mechanical (the 12-month-ahead horizon rolls at year start) and are ignored.\n- First-round analogues: the largest single first-round moves in the data are 2014 (Ibov USD +10.1% [−1,+1], placebo p 0.03), 2018 (BRL +4.5%, NTN-B 10y −42 bp, p ≤ 0.02) and 2022 (Ibov USD +12.0%, BRL +4.4%, p ≤ 0.02) — all first rounds in which the right-of-centre candidate finished stronger than prices had implied (judged from the price action itself). Whether 2026 belongs to that group cannot be checked here.")
A("- **2026**: the first-round reaction (Oct 5 onward) is not in the warehouse (`ibovespa_usd` ends 2026-10-01, `brl_usd` / NTN-B 2026-10-02). Pre-election pricing: all 2026 moves over [Jul 1→t−1], [Sep 1→t−1], [t−5→t−1] in BRL, Ibov USD and Ibov BRL sit inside the six-election interquartile range ⇒ by the pre-registered rule, **no unusual election premium was priced** before the vote. YTD the 2026 tape is unusually *strong* (Ibov USD +20.5% vs a historical IQR of −6.3 to +7.5; BRL +5.2% vs −13.3 to +3.4), the opposite of 2002's pre-election panic. Focus IPCA 12m rose more than usual Jul→t−1 (+0.52 vs IQR −0.18 to +0.44) — the oil shock, not obviously the election. The 10y real yield fell 42 bp Jul→t−1 (z −2.9 vs n=2 history; confounded by the Sep 17 Selic cut to 13.75).\n")

# scenarios summary
A("### 2027–2030 scenarios — primary branches: Lula IV (left) vs Flávio Bolsonaro (right); centre secondary\n")
A("History ranges are the post-1995 4-year mandates (inflation: 1996+, dropping the Real-plan transition year) of each lean (left: Lula I, Lula II, Dilma I, Lula III; right: FHC I, FHC II, Temer, Bolsonaro; Dilma II has <2 years). "
  f"'Model' = α_lean + β·ΔToT fitted on all 8 mandates, evaluated at ToT paths p25/p50/p75 of historical 4-year ToT changes ({S.TOT_PATHS['ToT falls (p25)']:+.1f}, {S.TOT_PATHS['ToT flat-ish (p50)']:+.1f}, {S.TOT_PATHS['ToT rises (p75)']:+.1f} log-pts/yr). "
  f"ToT in 2025 sits at the {S.LTOT_PCTL:.0%} percentile of 1991–2025, so mean reversion (the p25 path) is a live risk. n ≤ 8 ⇒ illustrative ranges, never forecasts.\n")
rows = []
for mid, lab in [("A1", "GDP growth, %/yr"), ("B1", "Inflation (deflator, log %)"), ("B2", "Real policy rate, %"), ("C1", "Primary balance, % GDP"),
                 ("D2", "BRL vs USD, %/yr (+ stronger)"), ("D1", "Ibovespa USD, %/yr"), ("E5", "Δ Gini, pts/yr"), ("E6", "Δ poverty $3.00, pts/yr"),
                 ("E1c", "Δ unemployment, pts/yr"), ("E3", "Real min wage, %/yr"), ("F1", "Infant mortality, %/yr")]:
    rows.append({"outcome": lab, "Lula IV (left)": scen_cell(mid, "S-L"), "Flávio Bolsonaro (right)": scen_cell(mid, "S-R"), "centre (secondary)": scen_cell(mid, "S-C")})
rows.append({"outcome": "Gross debt/GDP 2030, %", "Lula IV (left)": debt_cell("S-L"), "Flávio Bolsonaro (right)": debt_cell("S-R"), "centre (secondary)": "use grid"})
A(md_table(pd.DataFrame(rows)) + "\n")
A("Read the market rows with care: the right branch's BRL/equity history is dominated by FHC II (1999 float, 2001 energy crisis, 2002 pre-Lula panic booked to FHC), and the left branch's by Lula I–II's commodity boom; the event study points the other way for the first 60 days after a right win (Ibov USD +19% vs −4% abnormal). The fiscal rows are equally context-bound (Lula I–II surpluses vs COVID 2020). Gini/poverty/unemployment/min-wage rows are where the lean gap is most stable across specifications.\n")
A(f"**Market-implied (as of 2026-09-25 Focus / 2026-10-02 curve; a probability-weighted mix of both outcomes, pre-first-round):** GDP 2027 {ST['focus_gdp_growth']['value']:.2f}% (`focus_gdp_growth`), IPCA 12m {ST['focus_ipca_12m']['value']:.2f}% (`focus_ipca_12m`), "
  f"Selic 12m ahead {ST['focus_selic_12m']['value']:.2f}% (`focus_selic_12m`) ⇒ real ≈ {MK['implied_real_policy_12m']:.1f}%; NTN-B 10y real {ST['gov_real_yield_10y']['value']:.2f}% (`gov_real_yield_10y`); "
  f"LTN 5y {ST['gov_nominal_yield_5y']['value']:.2f}% (`gov_nominal_yield_5y`) ⇒ rough real 5y ≈ {MK['rough_real_5y']:.1f}%; BRL {ST['focus_fx']['value']:.2f} (`focus_fx`). "
  f"Markets price growth near the **right-branch** history (≈1–2%) and a real rate near the **left-branch** history (≈7–9%) — i.e. they price neither narrative's best case. "
  f"The marginal funding cost implies r−g ≈ {MK['implied_r_minus_g_ltn']:.1f} pts (LTN 5y minus Focus nominal growth) vs {ST['r_minus_g']['value']:.2f} on the stock (`r_minus_g`, {ST['r_minus_g']['date']}).\n")
A(f"**Debt arithmetic is the one deterministic piece.** From {S.D0:.1f}% (`gross_public_debt_gdp`, {ST['gross_public_debt_gdp']['date']}), stabilising debt needs a primary surplus of ≈{S.debt_stab_pb[ST['r_minus_g']['value']]:.1f}% GDP at today's r−g; the current 12m primary is {ST['primary_balance_gdp']['value']:+.2f}%. "
  f"The 4×3 grid spans {S.DEBT_GRID.debt_2030.min():.0f}–{S.DEBT_GRID.debt_2030.max():.0f}% of GDP in 2030. Lean-conditional primary-balance history spans −2.0 to +3.5 — wider than any lean difference, and each side's history is dominated by its context "
  f"(left median is lifted by Lula I–II's commodity boom; right median is dragged by COVID 2020 — Bolsonaro ex-2020 averaged {S.BOLSO_EX2020:+.2f}%, Lula III {S.PB_HIST['Lula III'][1]:+.2f}%). With r−g = {ST['r_minus_g']['value']:.2f}: "
  f"Lula III run-rate ⇒ {S.debt_path(S.D0, ST['r_minus_g']['value'], S.PB_HIST['Lula III'][1])[-1]:.0f}% in 2030; Bolsonaro ex-2020 run-rate ⇒ {S.debt_path(S.D0, ST['r_minus_g']['value'], S.BOLSO_EX2020)[-1]:.0f}%. Both branches see debt rise unless r−g falls or pb exceeds ~+4%.\n")
A("**Swing variables (ranked by in-sample explanatory power from Q0):** (1) the commodity/ToT path — Brent at $114 (`brent_usd`, 2026-09-29) helps an oil exporter (pre-salt share and oil exports below), but ToT is near a cycle high; "
  "(2) the fiscal–monetary mix: r−g and the credibility of the fiscal rule (2016 spending cap and 2023 framework both moved real yields on announcement); (3) the real-rate path set by an autonomous BCB (2021 law), which history shows does not order by lean; "
  "(4) external shocks — the 2025 US tariff (`exports_to_us` vs `exports_to_china`). Lean itself ranks behind (1) for markets and debt, and ahead of it only for distribution and policy instruments.\n")

A("### Caveats\n")
A("- Association, not causation: 9 terms, 3 left vs 4 right (coding A); terms are confounded with the commodity super-cycle (Lula I–II), GFC, Lava Jato and the 2015–16 recession (Dilma II/Temer), COVID (Bolsonaro), and the 2026 oil shock (Lula III, incomplete).\n"
  "- No Congress composition data in the warehouse → coalition effects untested; no peer countries, US rates, dollar index, VIX or world GDP → the only global control is Brazil's own ToT (+Brent from 2000).\n"
  "- Survey breaks (PNAD 1992, PNAD-C 2012), WB interpolation of forest area, preliminary DATASUS 2024–26, biennial WGI before 2002, and 2026 partial-year values (IBC-Br Jan–Jul, unemployment Jan–Aug) are documented below.\n"
  "- July-1 attribution books 2002's pre-Lula market panic to FHC and 2016's recovery to Temer; lag-1 and drop-first-year cells exist to test this (see robustness).\n")

# ---- Data constraints
A("## 2. Data constraints (plan §0.1–0.8, verbatim, then executor updates)\n")
A(constraints + "\n")
A("**Executor updates (2026-10-05):** 0.1 re-checked — `political_events` still has no 2026 result and `git log -- registry/` shows nothing newer (latest b79840b). The first-round result is supplied externally (section 0) and is used only to order the scenario branches. "
  f"All §0.9 anchors reproduced exactly (Ibovespa USD 2026 YTD +22.8% vs +22.7% — rounding). ToT splice: UVI ratio rescaled to TT.PRI (k = {S.TOT_INFO['rescale_k']:.3f}, ρ = {S.TOT_INFO['rho_overlap']:.5f} over {S.TOT_INFO['n_overlap']} overlapping years); 2025 extended with `wb/TOT.BRA`. "
  "2026 GDP = IBC-Br Jan–Jul 2026 vs Jan–Jul 2025; 2026 unemployment = native `unemployment_rate` Jan–Aug mean, level-matched to the WB ILO-modelled 2025 value. Interpolated gaps: Gini, poverty, income shares, WGI 1997/1999/2001, education spending, informality.\n")

# ---- Terms
A("## 3. Term table and lean coding\n")
tt = S.T[["term_id", "short", "start", "end", "party", "lean"]].copy()
tt["start"] = tt.start.dt.date; tt["end"] = tt.end.dt.date
tt["years attributed (1 Jul rule)"] = [f"{S.ATTR.index[S.ATTR.term_c == t].min()}–{S.ATTR.index[S.ATTR.term_c == t].max()}" for t in tt.short]
for c in "ABCD":
    tt[f"coding {c}"] = [S.CODINGS[c][t] or "dropped" for t in tt.short]
tt["mean ΔlogToT /yr"] = [f"{S.DLTOT.reindex(S.ATTR.index[S.ATTR.term_c == t]).mean():+.1f}" for t in tt.short]
A(md_table(tt) + "\n")
A("Coding E = coding A with Dilma II's 2015–16 years dropped. Mandate unit splits FHC (1999), Lula (2007), Dilma (2015). Lula III is incomplete (data to 2026-08/10).\n")
A("Term-attribution SQL (prepended to every term query; 1 July majority rule for annual data):\n```sql\n" + S.TERM_SQL.strip() + "\n```\n")

# ---- Prereg
A("## 4. Pre-registered hypotheses\n")
A("See `preregistration.md` (timestamped before any result). Families: (1) four composites, Holm at α = 0.10; (2) 23 primary metrics, BH at q = 0.10 (the plan said '~26'; the verified primary list has 23 metrics — composites are tested separately in family 1); (3) secondary metrics, descriptive. "
  "Support for a narrative requires: baseline sign matches AND ≥ 80% of robustness cells share it AND the 80% cluster-bootstrap CI excludes zero.\n")
exp = pd.DataFrame([dict(id=k, metric=MET[k]["name"], left_expects=MET[k]["expL"][1], right_expects=MET[k]["expR"][1]) for k in S.PRIMARY])
A(md_table(exp) + "\n")

# ---- Results
A("## 5. Results\n")
A("### 5.1 Q0 — variance decomposition (Shapley R²; term level: term mean on left dummy vs term-mean ΔlogToT; year level: lean dummies vs [ΔlogToT, logToT])\n")
qq = Q.copy(); qq = qq.round(2)
A(md_table(qq[["metric_id", "name", "level", "n", "r2_lean", "r2_tot", "r2_both", "shap_lean", "shap_tot", "tot_ge_lean"]]) + "\n")
A("### 5.2 Family 1 — composites (Holm across 4)\n")
crow = []
for (n, adj), v in comp.items():
    crow.append(dict(composite=n, adjustment=adj, **{"n L/R": f"{v['n_left']}/{v['n_right']}", "Δ (z)": f"{v['diff']:+.2f}", "80% CI": ci(v["ci80"]), "95% CI": ci(v["ci95"]),
                     "perm p": f"{v['perm_p']:.3f}", "floor": f"{v['p_min']:.3f}", "Holm p": f"{v['holm_p']:.3f}"}))
A(md_table(pd.DataFrame(crow)) + "\n")
A("Composite values by term (z-mean, raw):\n")
A(md_table(pd.DataFrame([{**{"composite": n}, **{t: f(comp[(n, 'raw')]['by_term'].get(t), 2) for t in S.TERM_ORDER}} for n in S.COMPOSITES])) + "\n")
A("### 5.3 Family 2 — primary metrics, by bucket (BH q across 23)\n")
for b in ["A Growth", "B Prices & rates", "C Fiscal", "D Markets & external", "E Labour & distribution", "F Health, education, safety", "G Institutions (WGI)", "H Environment"]:
    A(f"#### {b}\n")
    A(bucket_table(b, True) + "\n")
    A("Secondary (descriptive):\n\n" + bucket_table(b, False) + "\n")
A("### 5.4 Term values (term mean of annual values) for the primary metrics\n")
A(term_values_table(S.PRIMARY) + "\n")
A("### 5.5 Inherited conditions — starting-point-adjusted change (term change regressed on start level)\n")
sa = pd.DataFrame([dict(metric=k, n_terms=v["n"], raw_diff=f"{v['raw']:+.2f}", start_adjusted_diff=f"{v['adj']:+.2f}", slope_on_start=f"{v['slope']:+.3f}") for k, v in S.START_ADJ.items() if v])
A(md_table(sa) + "\n")
A("### 5.6 Within-president contrasts (descriptive; mandate means)\n")
wm = pd.DataFrame(S.WITHIN).T
want = ["FHC I", "FHC II", "Lula I", "Lula II", "Lula III", "Dilma I", "Dilma II", "Temer", "Bolsonaro"]
wm = wm.reindex(columns=[c for c in want if c in wm.columns]).round(2)
wm.insert(0, "metric", [f"{k} {MET[k]['name']}" for k in wm.index])
A(md_table(wm) + "\n")
A("Mandate ToT backdrop (mean ΔlogToT, log-pts/yr): " + ", ".join(f"{k} {v['dltot']:+.1f}" for k, v in S.MAND_TOT.items()) + ". "
  "Same-person, same-lean mandates differ as much as opposite-lean ones: Lula II vs Lula III growth, FHC I vs FHC II BRL — the cycle moves with ToT, not with the person.\n")
A("SQL behind the annual panel (catalog `agg` applied: last for stocks like debt/primary 12m, sum for counts, mean otherwise):\n```sql\n" + S.SQL["annual_panel"].replace("$1", "$ids") + "\n```\n"
  "Year-end panel for returns:\n```sql\n" + S.SQL["year_end_panel"] + "\n```\n")

# ---- Event study
A("## 6. Event study\n")
A("Daily changes; abnormal = raw cumulative change − (window length × mean daily change over [−250,−121]); Brent-adjusted variant = market model on Brent daily log change, estimated on the same window. "
  "Significance by placebo: 2,000 random non-event dates ≥ 90 days from any listed event. Coverage guard: a window is used only if the series has the full estimation and event window with no >2× calendar gap.\n")
A("```sql\n" + S.SQL["daily_panel"] + "\n```\n")
g = S.EVG.copy()
g = g[g.series_id.isin(["ibovespa_usd", "brl_usd", "embi_brazil", "gov_real_yield_10y", "focus_selic_12m"])].round(2)
A("**Left wins vs right/centre-right transitions (6 vs 3 events; permutation across events, floor 1/84 = 0.012):**\n")
A(md_table(g[["series_id", "window", "n_left", "n_right", "mean_left_win", "mean_right_transition", "diff", "perm_p", "p_min"]]) + "\n")
if len(EVB):
    eb = EVB.reset_index().round(2)
    A("Brent-adjusted group means (ibovespa_usd, brl_usd; 2001+ events):\n\n" + md_table(eb) + "\n")
key = EV[EV.window.isin(["[-1,+1]", "[0,+60]", "pre [-120,-1]"]) & EV.series_id.isin(["ibovespa_usd", "brl_usd", "embi_brazil", "gov_real_yield_10y"])]
piv = key.pivot_table(index=["event_date", "event", "group"], columns=["series_id", "window"], values="car").round(1)
piv.columns = [f"{a} {b}" for a, b in piv.columns]
A("Per-event abnormal changes (log % for prices, + = stronger BRL; bp for spreads/yields):\n\n" + md_table(piv.reset_index()) + "\n")
sig = EV[(EV.placebo_p < 0.05) & EV.window.isin(["[-1,+1]", "[-5,+5]", "[0,+60]"]) & EV.group.isin(["left win", "right transition", "first round"])]
A("Events individually outside the placebo 95% band (two-sided p < 0.05), windows [−1,+1], [−5,+5], [0,+60]:\n\n" +
  md_table(sig[["event", "series_id", "window", "car", "raw_change", "placebo_p", "z"]].round(2)) + "\n")
A("1994 and 1998 (monthly only — descriptive): " + "; ".join(
    f"{sid} {str(d)[:7]}: {v:,.2f}" for sid, d, v in S.M9498.itertuples(index=False) if str(d)[5:7] in ("09", "11")) + "\n")
A("**Constant-mean caveat:** the abnormal model subtracts the estimation-window drift; for 2026 that window (Oct 2025–Apr 2026) was a strong rally, so the 2026 pre-run-up 'abnormal' Ibov-USD figure (−41.8%) is mostly the removed drift — the raw change is in `event_study.csv` (`raw_change`).\n")

# ---- robustness
A("## 7. Robustness\n")
A("Grid per primary metric: sample (1985+/1995+/2003+) × unit (term / 4-year mandate / year-weighted) × lean coding (A–E) × attribution (contemporaneous / lag-1 / drop first year) × adjustment (raw / ToT / ToT+Brent, 2001+) × transform (mean / rank). "
  "Cells with < 2 units per side are blank. Full grid: `robustness_matrix.csv`; heatmap: `charts/robustness_heatmap.html`.\n")
rb = S.ROB[S.ROB["diff"].notna()]
rows = []
for m in S.PRIMARY:
    x = rb[rb.metric_id == m]
    rows.append({"id": m, "metric": MET[m]["name"], "cells": len(x), "share Δ>0": f"{(x.sign > 0).mean():.0%}",
                 **{f"Δ>0 {s}": f"{(x[x['sample'] == s].sign > 0).mean():.0%}" for s in ["1985+", "1995+", "2003+"]},
                 **{f"Δ>0 coding {c}": (f"{(x[x.coding == c].sign > 0).mean():.0%}" if len(x[x.coding == c]) else "–") for c in "ABCDE"},
                 "Δ>0 lag1": f"{(x[x.attribution == 'lag1'].sign > 0).mean():.0%}", "Δ>0 ToT": f"{(x[x.adjustment == 'tot'].sign > 0).mean():.0%}"})
A(md_table(pd.DataFrame(rows)) + "\n")
A("Reading: E1 unemployment (0% positive → always lower under left), E6 poverty, E3 minimum wage, C1 primary balance, D2 BRL, A1/A2 growth are directionally stable; "
  "B1 inflation, C2 debt change, F5 homicides, D6/D7 flip with sample or coding. E5 Gini flips between the 1985+ baseline (Collor artifact) and 1995+ (left better).\n")

# ---- multiple comparisons
A("## 8. Multiple comparisons\n")
mc = pd.DataFrame([dict(id=m, metric=MET[m]["name"], perm_p=f(R[m].get("perm_p")), floor=f(R[m].get("p_min_attainable"), 3), bh_q=f(R[m].get("bh_q")),
                        perm_p_tot=f(R[m].get("perm_p_tot")), bh_q_tot=f(R[m].get("bh_q_tot"))) for m in S.PRIMARY])
A(md_table(mc) + "\n")
A("No primary metric clears BH at q = 0.10 (smallest q ≈ 0.86); no composite clears Holm at 0.10 (smallest 0.114, COMP-D). This was expected from the power floor and is reported, not hidden.\n")

# ---- scenarios
A("## 9. Scenarios 2027–2030 (full detail)\n")
A("Branches: **S-L Lula IV (left)** and **S-R Flávio Bolsonaro (right)** are primary (external first-round result, section 0); **S-C centre** is secondary and uses coding B (FHC and Temer as 'centre') because Sarney/Itamar are hyperinflation-era. "
  "Fits use post-1995 mandates only. 'lo/hi' = model ± 1.28 × residual SD (≈80% band).\n")
sc = S.SCEN.copy()
keep = ["metric_id", "outcome", "unit", "branch", "n_hist", "hist_mandates", "hist_min", "hist_p25", "hist_median", "hist_p75", "hist_max", "beta_tot", "r2", "n_fit"] + \
       [c for c in sc.columns if c.startswith("model ")]
sc = sc[[c for c in keep if c in sc.columns]].round(2)
A(md_table(sc) + "\n")
A("Debt/GDP 2030 grid (`gross_public_debt_gdp` start, nominal g = `nominal_gdp_growth` " + f"{ST['nominal_gdp_growth']['value']:.2f}%):\n\n" + md_table(S.DEBT_GRID.round(1)) + "\n")
A("Debt by branch (pb from each lean's post-2002 mandate history):\n\n" + md_table(S.DEBT_BRANCH.round(2)) + "\n")
A("Reference paths: " + "; ".join(f"{k} → {v:.1f}%" for k, v in S.DEBT_REF.items()) + f". Debt-stabilising primary: " +
  ", ".join(f"r−g {k if isinstance(k, (int, float)) else k}: {v:.2f}%" for k, v in S.debt_stab_pb.items()) +
  ". Warehouse gold `derived_metrics.debt_stabilizing_primary_surplus_gap` (2026) = 6.9 pts, computed with r−g 7.69 (real policy rate − Focus growth) — a harsher marginal-rate view; `hypothesis_tests` L3 confirms r−g = +5.06 on the stock (Aug 2026).\n")
A("Starting conditions used (series_id, value, date, source):\n")
A(md_table(pd.DataFrame([dict(series_id=k, value=f"{v['value']:,.2f}", date=v["date"], source=v["source"]) for k, v in ST.items()])) + "\n")
A("Note vs the original brief: the warehouse has Selic **13.75** (cut on 2026-09-17), not 14.5. Brent is $114 (126.7 in Mar 2026): a 2026 oil shock is in the data, which flatters an oil exporter's ToT and fiscal take but raises inflation expectations (Focus IPCA 12m 4.02 → 4.65 YTD).\n")

# ---- pre-election
A("## 10. 2026 pre-election market-pricing check\n")
A("Change from window start to the last observation before 2026-10-04 (log % for prices, + = stronger BRL; bp for yields; level for Focus), vs the same windows before the 2002–2022 first rounds. "
  "Rule fixed in advance: inside the historical IQR ⇒ 'no unusual election premium'; outside ⇒ report direction without attributing it to a candidate.\n")
pe = S.PRE.round(2)
A(md_table(pe[["series_id", "window", "change_2026", "n_hist", "hist_mean", "hist_p25", "hist_p75", "z", "inside_iqr", "hist_values"]]) + "\n")
A("Confounds inside the 2026 window: Selic cut to 13.75 on 2026-09-17, Brent 61 → 114 over 2026, the 2025 US tariff. `embi_brazil` ends 2024-07-30 and cannot be used. Reading: BRL, Ibovespa (USD and BRL) and Focus Selic moves over the 3-month, 1-month and 1-week windows are inside the historical IQR; Focus IPCA rose more than usual Jul→t−1 (oil); "
  "YTD equity and BRL strength and the Jul→t−1 fall in 10y real yields are outside it (direction: easier financial conditions, not an election premium). The market reaction to Flávio Bolsonaro's first-round lead is not observable in this warehouse.\n")

# ---- conclusions
A("## 11. What can and cannot be concluded\n")
A("**Can:** (i) Over 1985–2026, the commodity/ToT cycle explains more of the between-term variation in markets, the BRL, the current account and debt dynamics than presidential lean does. "
  "(ii) Left (PT) terms are consistently associated with lower unemployment, faster real minimum-wage growth, faster poverty reduction and (post-1995) faster Gini decline — the distribution composite separates the two sides completely — and this survives the ToT control. "
  "(iii) Left terms also had higher real policy rates and higher interest bills, and — against the right narrative — larger primary surpluses on average (driven by Lula I–II). "
  "(iv) Markets reacted better in the 60 days after the three right/centre-right transitions than after six left wins; the event-day reaction itself does not differ. "
  "(v) Health and safety outcomes (infant mortality, homicides) and WGI scores show no lean pattern.\n")
A("**Cannot:** causal effects of lean; anything at conventional significance (term-level permutation floor 0.029; 0.10 for post-2001 series); coalition/Congress effects (no data); separation of lean from the specific shocks each term met; "
  "the 2026 first-round market reaction; any point forecast for 2027–2030.\n")

# ---- appendix
A("## Appendix — every series used (source, coverage, latest observation)\n")
ap = pd.DataFrame([dict(series_id=k, source=v["source"], freq=v["freq"], role=v["role"], first=v["first_date"], last=v["last_date"], n=v["n"]) for k, v in sorted(S.META.items())])
A(md_table(ap) + "\n")
A("Files: `results.json` (all numbers with series_ids and SQL), `metric_table.csv`, `term_table.csv`, `term_table_exact_monthly.csv`, `q0_variance_decomposition.csv`, `robustness_matrix.csv`, `event_study.csv`, `event_study_groups.csv`, "
  "`pre_election_2026.csv`, `scenarios.csv`, `debt_grid.csv`, `debt_by_branch.csv`; charts in `charts/` (timeline, forest, robustness_heatmap, event_study, campaign_2026, debt_fan, composites). Charts are light-mode plotly HTML (CDN plotly.js).\n")

(OUT / "report.md").write_text("\n".join(L))
print("report.md", len("\n".join(L)))
