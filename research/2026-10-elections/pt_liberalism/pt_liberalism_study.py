"""PT economic-liberalism regime study. Executes plan.md (same dir). Read-only on the warehouse.

Run: /Users/zkid18/proj-personal/brazil-macro/.venv/bin/python pt_liberalism_study.py
"""
import os, sys, csv, json, math, itertools, re, glob, datetime as dt
import numpy as np
import pandas as pd
import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
DB = '/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb'
EXT = os.path.join(HERE, 'ext')
CACHE = os.path.join(HERE, 'cache')
CHARTS = os.path.join(HERE, 'charts')
assert os.path.exists(os.path.join(HERE, 'preregistration.txt')), 'preregistration.txt must exist before computing'
RNG = np.random.default_rng(0)
NBOOT = int(os.environ.get('NBOOT', 5000))
YEARS = list(range(1995, 2027))
ZYEARS = list(range(1995, 2026))
RESULTS = {}   # name -> dict(value, series_id/fact_id, source, last_date, sql)
SQL_LOG = {}


def rec(name, value, sid='', source='', last_date='', sql=''):
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        value = None
    RESULTS[name] = dict(value=value, series_id=sid, source=source, last_date=str(last_date), sql=sql)


# ----------------------------------------------------------------------------------------------
# 1. regimes
# ----------------------------------------------------------------------------------------------
BASE_REG = [
    # rid, label, party, PT?, start, end
    ('R1', 'FHC I', 'PSDB', 0, '1995-01-01', '1999-01-15'),
    ('R2', 'FHC II', 'PSDB', 0, '1999-01-15', '2003-01-01'),
    ('R3', 'Lula-Palocci', 'PT', 1, '2003-01-01', '2006-03-28'),
    ('R4', 'Lula-Mantega', 'PT', 1, '2006-03-28', '2011-01-01'),
    ('R5', 'Dilma NME', 'PT', 1, '2011-01-01', '2015-01-01'),
    ('R6', 'Levy/Barbosa', 'PT', 1, '2015-01-01', '2016-05-12'),
    ('R7', 'Temer', 'MDB', 0, '2016-05-12', '2019-01-01'),
    ('R8', 'Bolsonaro', 'PL', 0, '2019-01-01', '2023-01-01'),
    ('R9', 'Lula III', 'PT', 1, '2023-01-01', '2027-01-01'),
]
DATA_END = '2026-08-31'


def regimes(variant='baseline'):
    R = [list(r) for r in BASE_REG]
    d = {r[0]: r for r in R}
    if variant == 'lula_split_2007':
        d['R3'][5] = '2007-01-01'; d['R4'][4] = '2007-01-01'
    elif variant == 'lula_split_gfc':
        d['R3'][5] = '2008-09-15'; d['R4'][4] = '2008-09-15'
    elif variant == 'nme_from_2011_08':
        d['R4'][5] = '2011-08-31'; d['R5'][4] = '2011-08-31'
    elif variant == 'levy_only':
        d['R6'][5] = '2015-12-18'   # Barbosa months dropped (gap until Temer)
    elif variant == 'r9_split_2025':
        r9 = d['R9']
        R.remove(r9)
        R.append(['R9a', 'Lula III (Campos Neto)', 'PT', 1, '2023-01-01', '2025-01-01'])
        R.append(['R9b', 'Lula III (Galipolo)', 'PT', 1, '2025-01-01', '2027-01-01'])
    df = pd.DataFrame(R, columns=['rid', 'label', 'party', 'pt', 'start', 'end'])
    df['start'] = pd.to_datetime(df.start); df['end'] = pd.to_datetime(df.end)
    return df.reset_index(drop=True)


def year_regime(reg):
    """1-July rule: year -> rid."""
    out = {}
    for y in YEARS:
        d = pd.Timestamp(y, 7, 1)
        m = reg[(reg.start <= d) & (reg.end > d)]
        out[y] = m.rid.iloc[0] if len(m) else None
    return out


TERMS = {'T_FHC': ('FHC', 0, range(1995, 2003)), 'T_LULA12': ('Lula I-II', 1, range(2003, 2011)),
         'T_DILMA': ('Dilma', 1, range(2011, 2016)), 'T_TEMER': ('Temer', 0, range(2016, 2019)),
         'T_BOLSO': ('Bolsonaro', 0, range(2019, 2023)), 'T_LULA3': ('Lula III', 1, range(2023, 2027))}

# ----------------------------------------------------------------------------------------------
# 2. panels
# ----------------------------------------------------------------------------------------------
CON = duckdb.connect(DB, read_only=True)
MONTHLY_IDS = ['selic_target', 'real_policy_rate', 'ipca_12m', 'ipca_monthly', 'ipca_administered_prices', 'focus_ipca_12m',
               'focus_selic_12m', 'primary_balance_gdp', 'nominal_deficit_gdp', 'interest_bill_gdp', 'gross_public_debt_gdp',
               'net_public_debt_gdp', 'credit_gdp', 'fx_reserves', 'brl_usd', 'brent_usd', 'embi_brazil', 'gov_real_yield_10y',
               'wb/TOT.BRA', 'wb/REER_M.BRA', 'gdp_nominal_12m_brl', 'unemployment_rate']
ANNUAL_IDS = ['wb/TM.TAX.MRCH.WM.AR.ZS.BR', 'wb/TM.TAX.MRCH.SM.AR.ZS.BR', 'wb/TM.TAX.MANF.WM.AR.ZS.BR', 'wb/NE.TRD.GNFS.ZS.BR',
              'wb/NE.IMP.GNFS.ZS.BR', 'wb/GC.TAX.INTT.RV.ZS.BR', 'wb/GC.TAX.TOTL.GD.ZS.BR', 'wb/GC.REV.XGRT.GD.ZS.BR',
              'wb/GC.XPN.TRFT.ZS.BR', 'wb/GC.XPN.TOTL.GD.ZS.BR', 'wb/NE.CON.GOVT.KD.ZG.BR', 'wb/NY.GDP.MKTP.KD.ZG.BR',
              'wb/NY.GDP.MKTP.CN.BR', 'wb/NY.GDP.MKTP.CD.BR', 'wb/FS.AST.PRVT.GD.ZS.BR', 'wb/GFDD.EI.08.BR', 'wb/GFDD.OI.20a.BR',
              'wb/FI.RES.TOTL.MO.BR', 'wb/PX.REX.REER.BR', 'wb/TT.PRI.MRCH.XD.WD.BR', 'ilostat/EAR_INEE_NOC_NB.BRA',
              'wb/FP.CPI.TOTL.BR', 'wb/per_sa_cc.cov_pop_tot.BRA', 'wb/GOV_WGI_RQ_EST.BR', 'wb/TX.VAL.MRCH.HI.ZS.BR',
              'wb/TX.VAL.MRCH.R1.ZS.BR', 'wb/TX.VAL.MRCH.R3.ZS.BR', 'wb/TX.VAL.MRCH.R6.ZS.BR', 'wb/TX.VAL.MRCH.AL.ZS.BR',
              'wb/AG.LND.PFLS.HA.BR', 'wb/TOT.BRA', 'wb/SI.POV.GINI.BR', 'brent_usd']

SQL_MONTHLY = """SELECT series_id, date_trunc('month', date) AS ym,
       CASE WHEN series_id IN ('fx_reserves','brl_usd','brent_usd') THEN arg_max(value, date) ELSE avg(value) END AS v,
       max(date) AS last_date
FROM v_observations WHERE date <= current_date AND series_id IN ({ids}) GROUP BY 1,2"""
SQL_ANNUAL = """SELECT series_id, year, value, is_complete, agg FROM v_annual
WHERE year BETWEEN 1995 AND 2026 AND series_id IN ({ids})"""


def _ids(lst):
    return ','.join("'" + s + "'" for s in lst)


def monthly_panel():
    q = SQL_MONTHLY.format(ids=_ids(MONTHLY_IDS))
    SQL_LOG['monthly_panel'] = q
    df = CON.sql(q).df()
    W = df.pivot(index='ym', columns='series_id', values='v').sort_index()
    W.index = pd.to_datetime(W.index)
    last = df.groupby('series_id').last_date.max()
    return W, last


def annual_panel():
    q = SQL_ANNUAL.format(ids=_ids(ANNUAL_IDS))
    SQL_LOG['annual_panel'] = q
    df = CON.sql(q).df()
    W = df.pivot(index='year', columns='series_id', values='value').sort_index()
    return W


import functools


@functools.lru_cache(maxsize=None)
def pull_sgs(code, start='01/01/1995'):
    """CSV cache in executor dir only."""
    fn = os.path.join(CACHE, f'sgs_{code}.csv')
    if not os.path.exists(fn):
        sys.path.insert(0, '/Users/zkid18/proj-personal/brazil-macro/ingest'); import bcb_sgs
        rows = []
        y0 = int(start[-4:])
        for y in range(y0, 2027, 10):
            s = start if y == y0 else f'01/01/{y}'
            rows += bcb_sgs.fetch_values([code], s, f'31/12/{min(y + 9, 2026)}').get(code, [])
        with open(fn, 'w', newline='') as f:
            w = csv.writer(f); w.writerow(['date', 'value']); w.writerows(sorted(set(rows)))
    s = pd.read_csv(fn, parse_dates=['date']).set_index('date').value
    return s[s.index <= pd.Timestamp('2026-10-05')]


# ----------------------------------------------------------------------------------------------
# 3. external data
# ----------------------------------------------------------------------------------------------
def _read(fn):
    p = os.path.join(EXT, fn)
    return pd.read_csv(p) if os.path.exists(p) else None


def load_external():
    E = {}
    ser = []
    for fn in ['series_B.csv', 'series_C.csv']:
        d = _read(fn)
        if d is not None:
            d['file'] = fn
            ser.append(d)
    S = pd.concat(ser, ignore_index=True) if ser else pd.DataFrame(columns=['series_key', 'date', 'value'])
    S['value'] = pd.to_numeric(S.value, errors='coerce')
    S['year'] = pd.to_datetime(S.date, errors='coerce').dt.year
    E['series'] = S
    E['targets'] = _read('cmn_targets.csv')
    E['rstar'] = _read('neutral_rate.csv')
    E['fp'] = _read('fp_coding.csv')
    E['local_content'] = _read('local_content.csv')
    E['agreements'] = _read('trade_agreements_sice.csv') if _read('trade_agreements_sice.csv') is not None else _read('trade_agreements.csv')
    facts = []
    for fn in sorted(glob.glob(os.path.join(EXT, 'facts_*.csv'))):
        d = pd.read_csv(fn); d['file'] = os.path.basename(fn); facts.append(d)
    E['facts'] = pd.concat(facts, ignore_index=True) if facts else pd.DataFrame()
    return E


def ext_series(E, key):
    S = E['series']
    d = S[S.series_key == key].dropna(subset=['value', 'year'])
    if not len(d):
        return pd.Series(dtype=float)
    return d.groupby('year').value.last().sort_index()


# ----------------------------------------------------------------------------------------------
# 4. coded tables (each row cites a fact id in external_facts.csv; 'RM' facts are logged by the main executor)
# ----------------------------------------------------------------------------------------------
# M6 BCB autonomy: de jure (LC 179 from 2021-02-24) + de facto (2 retained/protected, 1 replaced at transition, 0 public presidential pressure)
M6_CODE = {**{y: (0, 1, 'FHC appointees; no formal autonomy') for y in range(1995, 2003)},
           **{y: (0, 2, 'Meirelles given minister status / no presidential pressure (plan codes as protected)') for y in range(2003, 2011)},
           2011: (0, 0, 'Dilma public pressure; Aug-2011 surprise cut'), 2012: (0, 0, 'Dilma public pressure on rates/banks'),
           2013: (0, 1, 'Tombini hiking cycle'), 2014: (0, 1, ''), 2015: (0, 1, ''),
           2016: (0, 1, 'Goldfajn replaced Tombini at transition'), 2017: (0, 1, ''), 2018: (0, 1, ''),
           2019: (0, 1, 'Campos Neto replaced Goldfajn at transition'), 2020: (0, 1, ''),
           2021: (1, 1, 'LC 179 de jure autonomy'), 2022: (1, 1, ''),
           2023: (1, 0, 'Lula public attacks on Campos Neto (retained across transition)'), 2024: (1, 0, 'Lula attacks continue'),
           2025: (1, 1, 'Galipolo (Lula appointee) takes over, hikes to 15%'), 2026: (1, 1, '')}

# S4 sectoral intervention events per year (+1 intervention enacted, -1 liberalising measure enacted); sign in ELI is negative
S4_EVENTS = [
    (1995, -1, 'EC 9/1995 ends Petrobras oil monopoly'),
    (1997, -1, 'Petroleum Law 9,478 creates ANP, opens upstream'),
    (2010, 1, 'Pre-salt production-sharing Law 12,351: Petrobras sole operator, min 30%'),
    (2011, 1, 'Plano Brasil Maior / IPI +30pp on cars with low local content (Decree 7,567)'),
    (2012, 1, 'MP 579 electricity concession renewal/tariff cut'),
    (2012, 1, 'Inovar-Auto regime'),
    (2016, -1, 'Petrobras import-parity pricing policy (Oct 2016)'),
    (2016, -1, 'Law 13,365 ends Petrobras mandatory sole-operator role in pre-salt'),
    (2018, 1, "Diesel price subsidy after truckers' strike"),
    (2021, 1, 'Bolsonaro removes Petrobras CEO over fuel prices'),
    (2022, 1, 'EC 123 / LC 194 fuel-tax cuts and caps in election year'),
    (2022, 1, 'Further Petrobras CEO dismissals over fuel prices'),
    (2023, 1, 'Petrobras abandons import-parity pricing (May 2023)'),
    (2024, 1, 'Extraordinary-dividend retention fight; Prates fired'),
    (2024, 1, 'Nova Industria Brasil industrial policy'),
    (2026, 1, 'Federal diesel subsidies with Petrobras participation (MPs 1,340/1,363/1,391)'),
]
# L4 labour/pension regulation events (+ = more redistributive/pro-labour)
L4_EVENTS = [
    (1998, -1, 'EC 20/1998 pension reform (FHC)'),
    (2003, -1, 'EC 41/2003 civil-service pension reform (Lula)'),
    (2011, 1, 'Law 12,382/2011 enacts minimum-wage valorisation rule'),
    (2015, -1, 'MPs 664/665 tighten unemployment insurance and survivor pensions (Levy)'),
    (2017, -1, 'Labour reform Law 13,467/2017'),
    (2019, -1, 'EC 103/2019 pension reform'),
    (2023, 1, 'Law 14,663/2023 restores minimum-wage valorisation rule'),
    (2024, -1, 'Dec-2024 fiscal package caps minimum-wage real gain at 2.5% (arcabouco limit)'),
]
# IOF on foreign portfolio fixed-income inflows (% rate, effective dates); filled from facts_A where verified
IOF_STEPS = None   # set in components() from ext/iof_steps.csv if present, else from facts below
IOF_DEFAULT = [('1999-01-01', 0.0), ('2008-03-17', 1.5), ('2008-10-23', 0.0), ('2009-10-20', 2.0), ('2010-10-05', 4.0),
               ('2010-10-19', 6.0), ('2013-06-05', 0.0)]


def _annual_from_steps(steps, years):
    """time-weighted annual mean of a step function given [(date, rate)]."""
    s = pd.Series([r for _, r in steps], index=pd.to_datetime([d for d, _ in steps])).sort_index()
    days = pd.date_range(f'{years[0]}-01-01', f'{years[-1]}-12-31', freq='D')
    v = s.reindex(days.union(s.index)).ffill().reindex(days)
    return v.groupby(v.index.year).mean()


def cmn_targets(E, t2003=4.0):
    T = E.get('targets')
    base = {1999: (8.0, 2.0), 2000: (6.0, 2.0), 2001: (4.0, 2.0), 2002: (3.5, 2.0), 2003: (4.0, 2.5), 2004: (5.5, 2.5),
            2005: (4.5, 2.5), **{y: (4.5, 2.0) for y in range(2006, 2017)}, 2017: (4.5, 1.5), 2018: (4.5, 1.5),
            2019: (4.25, 1.5), 2020: (4.0, 1.5), 2021: (3.75, 1.5), 2022: (3.5, 1.5), 2023: (3.25, 1.5), 2024: (3.0, 1.5),
            2025: (3.0, 1.5), 2026: (3.0, 1.5), 2027: (3.0, 1.5)}
    src = 'plan hard-code'
    if T is not None and len(T):
        T = T.copy(); T['year'] = pd.to_numeric(T.year, errors='coerce'); T['target'] = pd.to_numeric(T.target, errors='coerce')
        T['tolerance'] = pd.to_numeric(T.tolerance, errors='coerce')
        diffs = []
        for _, r in T.dropna(subset=['year', 'target']).iterrows():
            y = int(r.year)
            if y in base and abs(base[y][0] - r.target) > 1e-9:
                diffs.append((y, base[y][0], r.target))
            base[y] = (r.target, r.tolerance if not pd.isna(r.tolerance) else base.get(y, (0, 1.5))[1])
        # in-force (revised) targets for 2003/2004 per plan and RA09 / file notes: 2003 4.0 (CMN 2,972), 2004 5.5 (CMN 3,108); tol 2.5
        base[2003] = (t2003, 2.5); base[2004] = (5.5, 2.5)
        src = 'ext/cmn_targets.csv (BCB historico de metas); 2003/2004 revised in-force targets'
        RESULTS['cmn_target_diffs_vs_plan'] = dict(value=diffs, series_id='cmn_targets', source=src, last_date='', sql='')
    base[2027] = base.get(2027, (3.0, 1.5))
    return base, src


# ----------------------------------------------------------------------------------------------
# 5. components
# ----------------------------------------------------------------------------------------------
COMP = {}   # id -> dict(sub, s (raw annual series, natural units), sign, weight, src, sids, transform, monthly(optional))
GAPS = []
SUBS = {'a': 'Fiscal discipline', 'b': 'Monetary orthodoxy', 'c': 'State role in credit (+ = smaller)',
        'd': 'Trade openness', 'e': 'SOE / market intervention (+ = less)', 'f': 'Left / social (+ = more redistributive)',
        'g': 'External & FX'}
ELI_SUBS = ['a', 'b', 'c', 'd', 'e', 'g']


def add(cid, sub, s, sign, src, sids, transform, weight=1.0, monthly=None, descriptive=False, note=''):
    s = pd.Series(s, dtype=float).dropna()
    s = s[(s.index >= 1995) & (s.index <= 2026)]
    if len(s) < 3:
        GAPS.append((cid, f'insufficient data ({len(s)} obs): {note or src}'))
        return
    COMP[cid] = dict(sub=sub, s=s, sign=sign, weight=weight, src=src, sids=sids, transform=transform,
                     monthly=monthly, descriptive=descriptive, note=note)


def compound_12m(m):
    """monthly % changes -> 12m % (rolling compounding)."""
    return 100 * (np.exp(np.log1p(m / 100).rolling(12).sum()) - 1)


def interp_rstar(E, mp):
    """BCB neutral-rate estimates, linearly interpolated, flat beyond ends; plus fallback 10y trailing median."""
    idx = mp.index
    R = E.get('rstar')
    bcb = None
    if R is not None and len(R):
        R = R.copy(); R['date'] = pd.to_datetime(R.date, errors='coerce')
        R['pt'] = pd.to_numeric(R.rstar_point, errors='coerce')
        lo = pd.to_numeric(R.rstar_low, errors='coerce'); hi = pd.to_numeric(R.rstar_high, errors='coerce')
        R['pt'] = R.pt.fillna((lo + hi) / 2)
        R = R.dropna(subset=['date', 'pt']).sort_values('date').groupby('date').pt.mean()
        if len(R) >= 2:
            s = R.reindex(idx.union(R.index)).interpolate(method='time', limit_area='inside')
            s = s.ffill()            # hold last estimate forward
            s = s.reindex(idx)       # NaN before first published estimate (no backward extrapolation)
            bcb = s
    rr = mp['real_policy_rate']
    fb = rr.rolling(120, min_periods=36).median()
    fb = fb.bfill()
    return bcb, fb


def components(E, mp, an, rstar_mode='bcb', f3=True, net_debt_mode='warehouse', t2003=4.0):
    COMP.clear(); GAPS.clear()
    yrs = pd.Index(YEARS)
    ann_m = lambda s: s.groupby(s.index.year).mean()
    dec = lambda s: s[s.index.month == 12].groupby(s[s.index.month == 12].index.year).last()

    # ---------------- (a) fiscal
    pb = dec(mp['primary_balance_gdp'].dropna())
    last_pb = mp['primary_balance_gdp'].dropna()
    pb.loc[2026] = last_pb.iloc[-1]   # latest 12m (Aug-2026), flagged partial
    ext_pb = ext_series(E, 'primary_balance_gdp_bcb')
    pb_full = pd.concat([ext_pb[ext_pb.index < 2002], pb[pb.index >= 2002]]) if len(ext_pb) else pb
    if not len(ext_pb):
        GAPS.append(('F1', 'pre-2002 primary balance (BCB NFSP annual) not obtained; F1 starts 2002'))
    add('F1', 'a', pb_full, +1, 'BCB via warehouse primary_balance_gdp (Dec, 12m) 2002+; ext primary_balance_gdp_bcb 1995-2001',
        'primary_balance_gdp; ext:primary_balance_gdp_bcb', 'annual level (Dec 12m)')
    sp = ext_series(E, 'central_govt_primary_spend_brl_bn')
    if len(sp) >= 10:
        cpi = an['wb/FP.CPI.TOTL.BR']
        real = sp / cpi.reindex(sp.index)
        g = 100 * real.pct_change()
        f2 = g - an['wb/NY.GDP.MKTP.KD.ZG.BR'].reindex(g.index)
        add('F2', 'a', f2, -1, 'Tesouro RTN primary spending deflated by CPI minus real GDP growth', 'ext:central_govt_primary_spend_brl_bn; wb/FP.CPI.TOTL.BR; wb/NY.GDP.MKTP.KD.ZG.BR', 'pts/yr')
    else:
        f2 = an['wb/NE.CON.GOVT.KD.ZG.BR'] - an['wb/NY.GDP.MKTP.KD.ZG.BR']
        GAPS.append(('F2', 'Tesouro primary-spending series not obtained; fallback WB real gov consumption growth - real GDP growth (plan fallback)'))
        add('F2', 'a', f2, -1, 'WB fallback: real gov consumption growth - real GDP growth', 'wb/NE.CON.GOVT.KD.ZG.BR; wb/NY.GDP.MKTP.KD.ZG.BR', 'pts/yr')
    if f3:
        tb = ext_series(E, 'tax_burden_gdp')
        if len(tb) >= 10:
            stn = ext_series(E, 'tax_burden_gdp_stn')
            d3 = tb.diff()
            d3.loc[2005] = np.nan                      # GDP-revision break 2004/05 (Receita series)
            if len(stn) >= 5:
                ds = stn.diff().dropna()
                for y in ds.index:
                    if y >= 2011: d3.loc[y] = ds.loc[y]   # STN general-govt series (one method) replaces Receita from 2011 (2020 FGTS/S-system break)
            else:
                d3.loc[2020] = np.nan
            add('F3', 'a', d3.sort_index(), -1, 'Receita Federal CTB % GDP change 1996-2010 (2005 break dropped); Tesouro STN general-govt CTB change 2011-2025',
                'ext:tax_burden_gdp; ext:tax_burden_gdp_stn', 'delta pts/yr')
        else:
            tbw = an['wb/GC.TAX.TOTL.GD.ZS.BR'].dropna()
            GAPS.append(('F3', 'Receita Federal tax-burden series not obtained; WB central-govt tax revenue 2010+ used'))
            add('F3', 'a', tbw.diff(), -1, 'WB central-govt tax revenue % GDP change (2010+)', 'wb/GC.TAX.TOTL.GD.ZS.BR', 'delta pts/yr')
    gross = dec(mp['gross_public_debt_gdp'].dropna())
    if net_debt_mode == 'warehouse':
        net = dec(mp['net_public_debt_gdp'].dropna()); nsrc = 'net_public_debt_gdp (warehouse)'
    else:
        s4513 = pull_sgs(4513); net = dec(s4513); nsrc = 'SGS 4513 DLSP consolidated'
    ext_nd = ext_series(E, 'net_public_debt_gdp_bcb')
    dnet = net.diff()
    if len(ext_nd) and net_debt_mode != 'warehouse':
        nd = pd.concat([ext_nd[ext_nd.index < net.index.min()], net]).sort_index(); dnet = nd.diff()
    elif len(ext_nd):
        # warehouse concept differs from consolidated DLSP; do not splice levels, only use ext changes pre-2002
        dnet = pd.concat([ext_nd.diff()[ext_nd.index <= 2001], net.diff()[net.index >= 2002]]).sort_index()
    gross.loc[2026] = mp['gross_public_debt_gdp'].dropna().iloc[-1]
    net_last = (mp['net_public_debt_gdp'] if net_debt_mode == 'warehouse' else pull_sgs(4513)).dropna().iloc[-1]
    dnet.loc[2026] = net_last - net.loc[2025]
    f4 = pd.concat([gross.diff(), dnet], axis=1).mean(axis=1)
    add('F4', 'a', f4, -1, f'mean of change in gross (2007+) and net debt % GDP; net={nsrc}; ext pre-2002 net debt changes',
        'gross_public_debt_gdp; ' + nsrc + '; ext:net_public_debt_gdp_bcb', 'delta pts/yr (Dec-Dec; 2026 = Aug vs Dec-2025)')

    # ---------------- (b) monetary
    targets, tsrc = cmn_targets(E, t2003)
    tgt_m = pd.Series({d: targets.get(d.year, (np.nan, np.nan))[0] for d in mp.index})
    tol_m = pd.Series({d: (2.0 if d.year <= 2002 else 2.5 if d.year <= 2005 else 2.0 if d.year <= 2016 else 1.5) for d in mp.index})
    # 12m-ahead target blend for expectations
    tgt_ahead = pd.Series({d: targets.get(d.year, (np.nan,))[0] * (12 - d.month) / 12 + targets.get(d.year + 1, (np.nan,))[0] * d.month / 12
                           for d in mp.index})
    bcb_rs, fb_rs = interp_rstar(E, mp)
    rs = bcb_rs.fillna(fb_rs) if (rstar_mode == 'bcb' and bcb_rs is not None) else fb_rs
    if bcb_rs is None:
        GAPS.append(('M1', 'BCB neutral-rate table not obtained; 10y trailing median fallback used'))
    rr = mp['real_policy_rate']
    gap = (rr - rs).dropna()
    add('M1', 'b', ann_m(gap), +1, f'real_policy_rate minus r* ({"BCB/Copom r* interpolated from 2016-01, 10y trailing median before" if rstar_mode == "bcb" else "10y trailing median throughout"})',
        'real_policy_rate; ext:neutral_rate', 'annual mean of gap', monthly=gap)
    ipca = mp['ipca_12m']
    d_ipca = dec(ipca.dropna()); d_ipca.loc[2026] = ipca.dropna().iloc[-1]
    m2 = -(d_ipca - pd.Series({y: targets.get(y, (np.nan,))[0] for y in d_ipca.index})).abs()
    add('M2', 'b', m2.dropna(), +1, f'-|Dec IPCA 12m - CMN target| ({tsrc})', 'ipca_12m; cmn_targets', '-|dev|')
    inband = ((ipca - tgt_m).abs() <= tol_m).astype(float).where(ipca.notna() & tgt_m.notna())
    add('M3', 'b', ann_m(inband.dropna()), +1, 'share of months IPCA 12m inside CMN band', 'ipca_12m; cmn_targets', 'share', monthly=inband.dropna())
    fe = mp['focus_ipca_12m']
    egap = (fe - tgt_ahead).dropna()
    add('M4a', 'b', -ann_m(egap), +1, 'Focus 12m-ahead IPCA expectation minus target (blend)', 'focus_ipca_12m; cmn_targets', '-mean gap', weight=0.5, monthly=-egap)
    # within-year SD from daily
    fd = CON.sql("SELECT date, value FROM v_observations WHERE series_id='focus_ipca_12m' AND date<=current_date").df()
    fd['y'] = pd.to_datetime(fd.date).dt.year
    sd = fd.groupby('y').value.std()
    add('M4b', 'b', -sd, +1, 'within-year SD of Focus 12m IPCA expectations (daily)', 'focus_ipca_12m', '-SD', weight=0.5)
    taylor = (mp['selic_target'] - (rs + fe + 1.5 * (fe - tgt_ahead))).dropna()
    add('M5', 'b', ann_m(taylor), +1, 'Selic - [r* + pi_e + 1.5(pi_e - pi*)]', 'selic_target; focus_ipca_12m; neutral_rate; cmn_targets',
        'annual mean residual', monthly=taylor)
    m6 = pd.Series({y: v[0] + v[1] for y, v in M6_CODE.items()})
    add('M6', 'b', m6, +1, 'coded: de jure LC179 (0/1) + de facto (0 pressure /1 replaced /2 protected)', 'coded; facts RA*/RM*', 'ordinal 0-3')

    # ---------------- (c) credit
    earm = pull_sgs(20593) / pull_sgs(20539) * 100
    add('C1', 'c', ann_m(earm.dropna()), -1, 'SGS 20593/20539 earmarked share of credit (2007-03+)', 'sgs:20593; sgs:20539', 'annual mean %', monthly=earm.dropna())
    GAPS.append(('C1', 'pre-2007 earmarked share (old methodology) not pulled; C1 starts 2007'))
    bd = ext_series(E, 'bndes_disbursements_brl_bn')
    if len(bd) >= 10:
        gdp_bn = an['wb/NY.GDP.MKTP.CN.BR'] / 1e9
        c2 = 100 * bd / gdp_bn.reindex(bd.index)
        if 2026 in c2.index: c2 = c2.drop(2026)
        add('C2', 'c', c2.dropna(), -1, 'BNDES disbursements / nominal GDP', 'ext:bndes_disbursements_brl_bn; wb/NY.GDP.MKTP.CN.BR', '% GDP', weight=0.5)
        tl = ext_series(E, 'bndes_treasury_debt_gdp')
        if len(tl) >= 10:
            add('C2b', 'c', tl, -1, 'Treasury credits to BNDES, stock % GDP (BCB net-debt table)', 'ext:bndes_treasury_debt_gdp', '% GDP', weight=0.5)
    else:
        GAPS.append(('C2', 'BNDES disbursement series not obtained'))
    tj = pull_sgs(256)
    selic_m = pull_sgs(4189)   # Selic accumulated in month, annualised (1995+), consistent across 1995-2026
    tlp_real = pull_sgs(27572)
    ipca12_m = compound_12m(pull_sgs(433))
    tlp_nom = 100 * ((1 + tlp_real / 100) * (1 + ipca12_m.reindex(tlp_real.index) / 100) - 1)
    lend = tj.copy()
    lend[lend.index >= '2018-01-01'] = tlp_nom.reindex(lend[lend.index >= '2018-01-01'].index)
    c3 = (lend - selic_m.reindex(lend.index)).dropna()
    c3 = c3[c3.index <= '2026-08-01']
    c3 = c3[c3.index >= '1995-07-01'] if False else c3
    add('C3', 'c', ann_m(c3), +1, 'TJLP (to 2017) / TLP nominal = (1+Jm)(1+IPCA12m) (2018+) minus Selic (SGS 4189)',
        'sgs:256; sgs:27572; sgs:433; sgs:4189', 'annual mean pp', monthly=c3)
    pub = pull_sgs(2007) / (pull_sgs(2007) + pull_sgs(2043)) * 100
    add('C4', 'c', ann_m(pub.dropna()), -1, 'public-control banks share of credit SGS 2007/(2007+2043)', 'sgs:2007; sgs:2043', 'annual mean %', monthly=pub.dropna())
    add('C5', 'c', an['wb/GFDD.EI.08.BR'], -1, 'WB credit to govt & SOEs % GDP', 'wb/GFDD.EI.08.BR', 'level', descriptive=True)

    # ---------------- (d) trade
    tw = an['wb/TM.TAX.MRCH.WM.AR.ZS.BR'].dropna(); ts = an['wb/TM.TAX.MRCH.SM.AR.ZS.BR'].dropna()
    wto = ext_series(E, 'wto_mfn_simple_avg')
    ts2 = ts.copy()
    if len(wto):
        # splice WTO MFN simple average after 2022 by ratio in overlap year
        ov = [y for y in wto.index if y in ts.index]
        k = (ts.loc[ov] / wto.loc[ov]).mean() if ov else 1.0
        for y in wto.index:
            if y > ts.index.max(): ts2.loc[y] = wto.loc[y] * k
        RESULTS['T1_wto_splice_ratio'] = dict(value=float(k), series_id='wto_mfn_simple_avg', source='WTO tariff profiles', last_date=str(wto.index.max()), sql='')
    else:
        GAPS.append(('T1', 'WTO 2023-25 MFN averages not obtained; T1 ends 2022'))
    t1 = pd.concat([(tw - tw.loc[ZYEARS[0]:2025].mean()) / tw.loc[:2025].std(), (ts2 - ts2.loc[:2025].mean()) / ts2.loc[:2025].std()], axis=1).mean(axis=1)
    add('T1', 'd', t1, -1, 'WB applied tariff weighted & simple (z-avg); WTO MFN simple spliced 2023+', 'wb/TM.TAX.MRCH.WM.AR.ZS.BR; wb/TM.TAX.MRCH.SM.AR.ZS.BR; ext:wto_mfn_simple_avg', 'z-mean of levels')
    tr = an['wb/NE.TRD.GNFS.ZS.BR']; tot = an['wb/TOT.BRA']; reer = an['wb/PX.REX.REER.BR']
    d = pd.concat([tr, np.log(tot), np.log(reer)], axis=1).dropna(); d = d[d.index >= 1995]
    X = np.column_stack([np.ones(len(d)), d.iloc[:, 1], d.iloc[:, 2]])
    beta, *_ = np.linalg.lstsq(X, d.iloc[:, 0].values, rcond=None)
    add('T2', 'd', pd.Series(d.iloc[:, 0].values - X @ beta, index=d.index), +1, 'trade % GDP residual on log ToT, log REER (OLS 1995-2025)',
        'wb/NE.TRD.GNFS.ZS.BR; wb/TOT.BRA; wb/PX.REX.REER.BR', 'OLS residual', weight=0.5)
    A = E.get('agreements')
    if A is not None and len(A):
        cnt = pd.Series(0.0, index=yrs)
        A = A[~A.name.astype(str).str.contains('unverified', case=False)]
        for col in ['signed', 'in_force']:
            yy = A[col].astype(str).str.extract(r'((?:19|20)\d{2})')[0].dropna().astype(int)
            for y in yy:
                if y in cnt.index: cnt[y] += 1
        add('T3', 'd', cnt[cnt.index <= 2026], +1, 'count of trade agreements signed or entering into force per year (OAS SICE Brazil index + Mercosur-Palestine)', 'ext:trade_agreements_sice.csv', 'count/yr')
    else:
        GAPS.append(('T3', 'trade agreement list not obtained'))
    LC = E.get('local_content')
    if LC is not None and len(LC):
        reg = regimes(); yr = year_regime(reg)
        mp_lc = dict(zip(LC.regime_id, pd.to_numeric(LC.score, errors='coerce')))
        add('T4', 'd', pd.Series({y: mp_lc.get(r, np.nan) for y, r in yr.items()}).dropna(), +1,
            'coded local-content stance per regime (+ = lower)', 'ext:local_content.csv', 'coded -1/0/+1')
    else:
        GAPS.append(('T4', 'local-content coding not obtained'))
    ad = ext_series(E, 'ad_initiations_brazil')
    if len(ad) >= 10:
        add('T5', 'd', ad, -1, 'WTO AD initiations by Brazil', 'ext:ad_initiations_brazil', 'count/yr')
    else:
        GAPS.append(('T5', 'WTO AD initiations not obtained'))
    add('T6', 'd', an['wb/GC.TAX.INTT.RV.ZS.BR'], -1, 'WB taxes on international trade % revenue', 'wb/GC.TAX.INTT.RV.ZS.BR', 'level')

    # ---------------- (e) SOE / intervention
    pq = CON.sql("""SELECT year(CAST(quarter_end AS DATE)) y, sum(revenue_usd_bn) rev FROM company_metrics WHERE entity_id='PETR'
                    GROUP BY 1 HAVING count(*)=4 ORDER BY 1""").df().set_index('y').rev
    br = mp['brent_usd'].groupby(mp.index.year).mean()
    dd = pd.concat([np.log(pq), np.log(br.reindex(pq.index))], axis=1).dropna()
    Xb = np.column_stack([np.ones(len(dd)), dd.iloc[:, 1]])
    bb, *_ = np.linalg.lstsq(Xb, dd.iloc[:, 0].values, rcond=None)
    add('S1', 'e', pd.Series(dd.iloc[:, 0].values - Xb @ bb, index=dd.index), +1,
        'FALLBACK: residual of log Petrobras USD revenue on log Brent (2012+); no ANP/Abicom parity series', 'revenue_usd_bn@PETR; brent_usd', 'OLS residual')
    GAPS.append(('S1', 'No pump-price / import-parity gap series (ANP/Abicom) obtained; warehouse fallback used (2012+ only)'))
    free12 = compound_12m(pull_sgs(11428)); adm12 = compound_12m(pull_sgs(4449))
    rep = -(free12 - adm12).clip(lower=0)
    rep = rep.dropna(); rep = rep[rep.index >= '1995-12-01']
    add('S2', 'e', ann_m(rep), +1, '-max(0, free 12m - administered 12m) IPCA (SGS 11428, 4449)', 'sgs:11428; sgs:4449', 'annual mean', monthly=rep)
    pv = ext_series(E, 'privatisation_proceeds_usd_bn')
    if len(pv) >= 10:
        gdp_usd = an['wb/NY.GDP.MKTP.CD.BR'] / 1e9
        add('S3', 'e', 100 * pv / gdp_usd.reindex(pv.index), +1, 'privatisation/concession proceeds % GDP', 'ext:privatisation_proceeds_usd_bn; wb/NY.GDP.MKTP.CD.BR', '% GDP')
    else:
        pc = ext_series(E, 'privatisation_count')
        if len(pc) >= 10:
            add('S3', 'e', pc, +1, 'privatisation/concession count per year', 'ext:privatisation_count', 'count')
        else:
            GAPS.append(('S3', 'privatisation proceeds/count series not obtained'))
    s4 = pd.Series(0.0, index=yrs)
    for y, v, _ in S4_EVENTS: s4[y] += v
    add('S4', 'e', s4, -1, 'coded sectoral-intervention events (+1 intervention, -1 liberalisation)', 'coded; facts RA*/RM*', 'net count/yr')
    petr = CON.sql("""SELECT year(CAST(quarter_end AS DATE)) y, sum(dividends_paid_brl) dv, sum(capex_brl) cx FROM company_metrics
                      WHERE entity_id='PETR' GROUP BY 1 ORDER BY 1""").df().set_index('y')
    add('S5', 'e', 100 * petr.dv / (petr.dv + petr.cx), +1, 'Petrobras dividends/(dividends+capex)', 'dividends_paid_brl@PETR; capex_brl@PETR', '%', descriptive=True)

    # ---------------- (f) left / social (+ = more redistributive)
    mw = an['ilostat/EAR_INEE_NOC_NB.BRA'].copy()
    mw_ext = ext_series(E, 'min_wage_brl')
    for y in mw_ext.index:
        if y not in mw.dropna().index: mw.loc[y] = mw_ext.loc[y]
    cpi = an['wb/FP.CPI.TOTL.BR'].copy()
    ipca_ann = pull_sgs(433)
    ia = (np.exp(np.log1p(ipca_ann / 100).groupby(ipca_ann.index.year).mean()) - 1)  # not used
    # extend CPI to 2026 with IPCA annual-average index if needed
    ix = (1 + pull_sgs(433) / 100).cumprod(); ixa = ix.groupby(ix.index.year).mean()
    for y in [2025, 2026]:
        if y not in cpi.dropna().index and (y - 1) in cpi.index:
            cpi.loc[y] = cpi.loc[y - 1] * ixa.loc[y] / ixa.loc[y - 1]
    mw = mw.sort_index(); cpi = cpi.sort_index()
    l1 = 100 * (mw / cpi.reindex(mw.index)).pct_change()
    add('L1', 'f', l1.dropna(), +1, 'real minimum-wage growth (ILO nominal / WB CPI; 2025-26 decree values, CPI extended with IPCA)',
        'ilostat/EAR_INEE_NOC_NB.BRA; wb/FP.CPI.TOTL.BR; ext:min_wage_brl; sgs:433', '% y/y')
    l2 = an['wb/GC.XPN.TRFT.ZS.BR'] * an['wb/GC.XPN.TOTL.GD.ZS.BR'] / 100
    add('L2a', 'f', l2.dropna(), +1, 'WB subsidies & transfers % GDP (central govt)', 'wb/GC.XPN.TRFT.ZS.BR; wb/GC.XPN.TOTL.GD.ZS.BR', '% GDP', weight=0.5)
    bf = ext_series(E, 'bolsa_familia_spend_brl_bn')
    bfx = ext_series(E, 'bolsa_familia_extraordinary_credits_brl_bn')
    if len(bfx): bf = bf.add(bfx.reindex(bf.index).fillna(0), fill_value=0)
    if len(bf) >= 8:
        gdp_bn = an['wb/NY.GDP.MKTP.CN.BR'] / 1e9
        add('L2b', 'f', (100 * bf / gdp_bn.reindex(bf.index)).dropna(), +1, 'Bolsa Familia/Auxilio Brasil spending % GDP',
            'ext:bolsa_familia_spend_brl_bn; wb/NY.GDP.MKTP.CN.BR', '% GDP', weight=0.5)
    else:
        GAPS.append(('L2b', 'Bolsa Familia spending series not obtained'))
    add('L3', 'f', an['wb/per_sa_cc.cov_pop_tot.BRA'], +1, 'WB CCT coverage (sparse; 2020 anomaly)', 'wb/per_sa_cc.cov_pop_tot.BRA', '%', descriptive=True)
    l4 = pd.Series(0.0, index=yrs)
    for y, v, _ in L4_EVENTS: l4[y] += v
    add('L4', 'f', l4, +1, 'coded labour/pension regulation events', 'coded; facts', 'net count/yr')

    # ---------------- (g) external
    fx = mp['fx_reserves'].dropna(); fxd = fx.groupby(fx.index.year).last()
    gdp_usd_m = an['wb/NY.GDP.MKTP.CD.BR'] / 1e6
    x1 = 100 * fxd.diff() / gdp_usd_m.reindex(fxd.index)
    if 2026 in x1.index and pd.isna(x1.loc[2026]):
        x1.loc[2026] = 100 * fxd.diff().loc[2026] / gdp_usd_m.loc[2025]
    add('X1', 'g', x1.dropna(), +1, 'change in year-end FX reserves % GDP (USD)', 'fx_reserves; wb/NY.GDP.MKTP.CD.BR', 'pp of GDP', weight=0.5)
    ka = ext_series(E, 'kaopen')
    if len(ka) >= 10:
        add('X2', 'g', ka, +1, 'Chinn-Ito KAOPEN (higher = more open)', 'ext:kaopen', 'index')
    else:
        GAPS.append(('X2', 'Chinn-Ito KAOPEN not obtained'))
    iof = _annual_from_steps(IOF_DEFAULT, list(range(1999, 2027)))
    add('X2b', 'g', iof, -1, 'IOF on foreign portfolio fixed-income inflows, time-weighted annual mean (Decrees 6,391/6,613/6,983/7,323/7,330/8,023)',
        'coded; facts RA*/RM*', '% rate', descriptive=True, note='pre-2008 rates (1990s controls) not verified -> descriptive only')
    sw = ext_series(E, 'fx_swap_stock_usd_bn')
    if len(sw) >= 5:
        add('X3', 'g', 100 * sw / (an['wb/NY.GDP.MKTP.CD.BR'] / 1e9).reindex(sw.index), -1, 'BCB FX swap stock % GDP', 'ext:fx_swap_stock_usd_bn', '% GDP', descriptive=True)
    return COMP


# ----------------------------------------------------------------------------------------------
# 6. index construction
# ----------------------------------------------------------------------------------------------
CODED = {'M6', 'S4', 'L4', 'T3', 'T4'}


def tot_regressors(an, mp):
    tot = an['wb/TOT.BRA'].copy()
    lt = np.log(tot)
    return pd.DataFrame({'dl': lt.diff(), 'l': lt})


def zscore_pool(comp, tot_adj=False, an=None, mp=None, drop=()):
    Z = {}
    params = {}
    TR = tot_regressors(an, mp) if tot_adj else None
    for cid, c in comp.items():
        if c['descriptive'] or cid in drop:
            continue
        v = c['s'] * c['sign']
        if tot_adj and cid not in CODED:
            d = pd.concat([v.rename('y'), TR], axis=1).dropna()
            d = d[(d.index >= 1995) & (d.index <= 2025)]
            if len(d) >= 8:
                X = np.column_stack([np.ones(len(d)), d.dl, d.l])
                b, *_ = np.linalg.lstsq(X, d.y.values, rcond=None)
                full = pd.concat([v.rename('y'), TR], axis=1).dropna()
                v = pd.Series(full.y.values - np.column_stack([np.ones(len(full)), full.dl, full.l]) @ b, index=full.index)
        base = v[(v.index >= 1995) & (v.index <= 2025)]
        mu, sd = base.mean(), base.std()
        if not sd or np.isnan(sd):
            continue
        Z[cid] = (v - mu) / sd
        params[cid] = (mu, sd)
    Z = pd.DataFrame(Z).reindex(YEARS)
    return Z, params


def subindex(Z, comp):
    out, ncomp = {}, {}
    for s in SUBS:
        cols = [c for c in Z.columns if comp[c]['sub'] == s]
        if not cols:
            continue
        w = np.array([comp[c]['weight'] for c in cols])
        M = Z[cols]
        avail = M.notna()
        num = (M.fillna(0) * w).sum(axis=1)
        den = (avail * w).sum(axis=1)
        v = num / den.replace(0, np.nan)
        n = avail.sum(axis=1)
        v[n < 2] = np.nan
        out[s] = v; ncomp[s] = n
    return pd.DataFrame(out), pd.DataFrame(ncomp)


def unit_map(unit, variant='baseline'):
    """returns (year->unit id, unit table with pt flag)."""
    if unit == 'term':
        ym = {}
        for k, (lab, pt, rg) in TERMS.items():
            for y in rg: ym[y] = k
        tab = pd.DataFrame([(k, v[0], v[1]) for k, v in TERMS.items()], columns=['rid', 'label', 'pt'])
        return ym, tab
    reg = regimes(variant)
    return year_regime(reg), reg


def regime_scores(Sub, ym, tab, drop_years=(), min_years=2, ncomp=None):
    rows = {}
    for _, r in tab.iterrows():
        ys = [y for y, k in ym.items() if k == r.rid and y not in drop_years]
        d = {}
        for s in Sub.columns:
            vals = Sub.loc[ys, s].dropna() if ys else pd.Series(dtype=float)
            d[s] = vals.mean() if len(vals) >= min_years else np.nan
            d['n_' + s] = len(vals)
        rows[r.rid] = d
    df = pd.DataFrame(rows).T
    elis = [s for s in ELI_SUBS if s in Sub.columns]
    df['ELI'] = df[elis].mean(axis=1, skipna=True).where(df[elis].notna().sum(axis=1) >= 3)
    df['n_ELI_subs'] = df[elis].notna().sum(axis=1)
    df['pt'] = tab.set_index('rid').pt.reindex(df.index).astype(int)
    return df


def delta(scores, col, pt=None):
    d = scores[[col, 'pt']].dropna()
    if pt is not None:
        d = d.assign(pt=pt.reindex(d.index))
    a = d[d.pt == 1][col]; b = d[d.pt == 0][col]
    if len(a) == 0 or len(b) == 0:
        return np.nan
    return a.mean() - b.mean()


def perm_test(scores, col):
    d = scores[[col, 'pt']].dropna()
    n, k = len(d), int(d.pt.sum())
    if k == 0 or k == n:
        return np.nan, np.nan, 0
    obs = d[d.pt == 1][col].mean() - d[d.pt == 0][col].mean()
    vals = d[col].values
    cnt, tot = 0, 0
    for c in itertools.combinations(range(n), k):
        m = np.zeros(n, bool); m[list(c)] = True
        dd = vals[m].mean() - vals[~m].mean()
        cnt += abs(dd) >= abs(obs) - 1e-12; tot += 1
    return cnt / tot, 1 / tot * 2 if tot else np.nan, tot


def cluster_bootstrap(Sub, ym, tab, drop_years=(), fp_draws=None, cols=None, nboot=NBOOT, seed=0, pairs=()):
    """two-stage: resample units within PT / non-PT, then years within unit. Returns dict col -> array of deltas;
    pairs: list of (rid_a, rid_b) for pairwise contrasts (years resampled within each)."""
    rng = np.random.default_rng(seed)
    cols = cols or list(Sub.columns)
    elis = [s for s in ELI_SUBS if s in Sub.columns]
    units = {}
    for _, r in tab.iterrows():
        ys = [y for y, k in ym.items() if k == r.rid and y not in drop_years]
        M = Sub.loc[ys, :].values if ys else np.zeros((0, Sub.shape[1]))
        units[r.rid] = (int(r.pt), M)
    sidx = {s: i for i, s in enumerate(Sub.columns)}
    base = regime_scores(Sub, ym, tab, drop_years)
    elig = [u for u in units if not np.isnan(base.loc[u, 'ELI']) or any(not np.isnan(base.loc[u, s]) for s in Sub.columns)]
    pt_u = [u for u in elig if units[u][0] == 1]; np_u = [u for u in elig if units[u][0] == 0]
    out = {c: np.full(nboot, np.nan) for c in cols + ['ELI', 'FP', 'FPminusELI']}
    pout = {p: {c: np.full(nboot, np.nan) for c in cols + ['ELI']} for p in pairs}

    def unit_val(M, idx):
        R = M[idx]
        with np.errstate(all='ignore'):
            cnt = np.sum(~np.isnan(R), axis=0)
            v = np.where(cnt >= min(2, len(idx)), np.nanmean(np.where(np.isnan(R), np.nan, R), axis=0), np.nan) if len(idx) else np.full(M.shape[1], np.nan)
        e = [v[sidx[s]] for s in elis]
        e = [x for x in e if not np.isnan(x)]
        return v, (np.mean(e) if len(e) >= 3 else np.nan)

    for b in range(nboot):
        vals = {1: [], 0: []}
        for grp, lst in [(1, pt_u), (0, np_u)]:
            pick = rng.choice(lst, size=len(lst), replace=True)
            for u in pick:
                M = units[u][1]
                idx = rng.integers(0, len(M), len(M)) if len(M) else np.array([], int)
                v, e = unit_val(M, idx)
                fp = fp_draws[u][rng.integers(0, len(fp_draws[u]))] if fp_draws is not None and u in fp_draws else np.nan
                vals[grp].append((v, e, fp))
        for c in cols + ['ELI', 'FP']:
            g = {}
            for grp in (1, 0):
                if c == 'ELI': xs = [t[1] for t in vals[grp]]
                elif c == 'FP': xs = [t[2] for t in vals[grp]]
                else: xs = [t[0][sidx[c]] for t in vals[grp]]
                xs = [x for x in xs if not np.isnan(x)]
                g[grp] = np.mean(xs) if xs else np.nan
            out[c][b] = g[1] - g[0]
        out['FPminusELI'][b] = abs(out['FP'][b]) - abs(out['ELI'][b])
        for p in pairs:
            va = []; 
            for u in p:
                M = units[u][1]
                idx = rng.integers(0, len(M), len(M)) if len(M) else np.array([], int)
                va.append(unit_val(M, idx))
            for c in cols:
                pout[p][c][b] = va[0][0][sidx[c]] - va[1][0][sidx[c]]
            pout[p]['ELI'][b] = va[0][1] - va[1][1]
    return out, pout


def ci(a, lvl=0.80):
    a = a[~np.isnan(a)]
    if not len(a):
        return (np.nan, np.nan)
    lo = (1 - lvl) / 2
    return (float(np.quantile(a, lo)), float(np.quantile(a, 1 - lo)))


def start_adjust(scores, tab, col):
    """regress unit scores on standardized start-month IPCA 12m and Selic; return residual-based delta."""
    ip, se = _start_series()
    X = []
    for rid in scores.index:
        st = pd.Timestamp(tab.set_index('rid').loc[rid, 'start']) if 'start' in tab.columns else pd.Timestamp(min(TERMS[rid][2]), 1, 1)
        m = (st - pd.offsets.MonthBegin(1)).normalize().replace(day=1)
        X.append([ip.asof(m), se.asof(m)])
    X = np.array(X, float)
    X = (X - X.mean(0)) / X.std(0)
    d = scores[[col, 'pt']].copy(); d['x1'] = X[:, 0]; d['x2'] = X[:, 1]
    d = d.dropna()
    if len(d) < 5:
        return np.nan, None
    A = np.column_stack([np.ones(len(d)), d.x1, d.x2])
    b, *_ = np.linalg.lstsq(A, d[col].values, rcond=None)
    res = d[col].values - A @ b
    r = pd.Series(res, index=d.index)
    return r[d.pt == 1].mean() - r[d.pt == 0].mean(), r


@functools.lru_cache(maxsize=None)
def _start_series():
    return compound_12m(pull_sgs(433)), pull_sgs(4189)


def bh(pvals):
    p = np.array([np.nan if v is None else v for v in pvals], float)
    ok = ~np.isnan(p); q = np.full_like(p, np.nan)
    pv = p[ok]; n = len(pv)
    if n == 0:
        return q
    o = np.argsort(pv); r = np.empty(n); r[o] = np.arange(1, n + 1)
    qq = pv * n / r
    qs = np.minimum.accumulate(qq[o][::-1])[::-1]
    out = np.empty(n); out[o] = np.minimum(qs, 1)
    q[ok] = out
    return q


# ----------------------------------------------------------------------------------------------
# 7. FP axis
# ----------------------------------------------------------------------------------------------
FP_DIMS = ['FP1', 'FP2', 'FP3', 'FP4', 'FP5']


def fp_axis(E, with_fp4=True, ndraw=2000, seed=0):
    F = E.get('fp')
    if F is None or not len(F):
        GAPS.append(('FP', 'fp_coding.csv not obtained'))
        return None, None, None
    F = F.copy(); F['score'] = pd.to_numeric(F.score, errors='coerce')
    P = F.pivot_table(index='regime_id', columns='dimension', values='score', aggfunc='mean').reindex(columns=FP_DIMS)
    dims = [d for d in FP_DIMS if with_fp4 or d != 'FP4']

    def comp(M):
        Zs = (M - M.mean()) / M.std(ddof=1).replace(0, np.nan)
        return Zs[dims].mean(axis=1)
    fp = comp(P)
    rng = np.random.default_rng(seed)
    draws = {r: [] for r in P.index}
    for _ in range(ndraw):
        M = P + rng.integers(-1, 2, size=P.shape)
        f = comp(M)
        for r in P.index: draws[r].append(f[r])
    draws = {r: np.array(v) for r, v in draws.items()}
    return fp, P, draws


def fp_for_variant(fp, draws, variant):
    """map FP regime scores onto variant/term units."""
    if variant == 'r9_split_2025' and fp is not None and 'R9' in fp.index:
        fp = pd.concat([fp, pd.Series({'R9a': fp['R9'], 'R9b': fp['R9']})])
        draws = {**draws, 'R9a': draws['R9'], 'R9b': draws['R9']}
    return fp, draws


def fp_terms(fp, draws):
    mapping = {'T_FHC': ['R1', 'R2'], 'T_LULA12': ['R3', 'R4'], 'T_DILMA': ['R5', 'R6'], 'T_TEMER': ['R7'], 'T_BOLSO': ['R8'], 'T_LULA3': ['R9']}
    f = pd.Series({k: np.mean([fp[r] for r in v if r in fp.index]) for k, v in mapping.items()})
    d = {k: np.mean([draws[r] for r in v if r in draws], axis=0) for k, v in mapping.items()}
    return f, d


# ----------------------------------------------------------------------------------------------
# 8. rhetoric
# ----------------------------------------------------------------------------------------------
DICT_PT = {
    'LIBERAL': ['responsabilidade fiscal', 'superávit primário', 'superavit primario', 'equilíbrio fiscal', 'equilibrio fiscal', 'estabilidade',
                'metas de inflação', 'meta de inflação', 'autonomia do banco central', 'abertura comercial', 'livre comércio', 'concessão', 'concessões',
                'privatização', 'privatizações', 'competitividade', 'produtividade', 'ajuste', 'reforma tributária', 'investimento privado',
                'investimentos privados'],
    'LEFT': ['desenvolvimentismo', 'desenvolvimentista', 'bndes', 'indústria nacional', 'conteúdo local', 'papel do estado', 'estatal', 'estatais',
             'petrobras', 'salário mínimo', 'distribuição de renda', 'bolsa família', 'justiça social', 'trabalhadores', 'trabalhadoras', 'soberania',
             'neoliberal', 'neoliberalismo', 'juros altos'],
    'FP_SOUTH': ['sul-sul', 'brics', 'áfrica', 'países em desenvolvimento', 'multilateral', 'multilateralismo', 'onu', 'mercosul',
                 'integração regional', 'soberania', 'amazônia', 'clima'],
    'FP_WEST': ['estados unidos', 'ocde', 'aliança', 'israel', 'ocidente', 'segurança'],
}
DICT_EN = {
    'LIBERAL': ['fiscal responsibility', 'primary surplus', 'fiscal balance', 'stability', 'inflation target', 'central bank independence',
                'central bank autonomy', 'trade liberali', 'free trade', 'concession', 'privati', 'competitiveness', 'productivity', 'adjustment',
                'tax reform', 'private investment'],
    'LEFT': ['developmentalis', 'national industry', 'local content', 'role of the state', 'state-owned', 'petrobras', 'minimum wage',
             'income distribution', 'bolsa familia', 'social justice', 'workers', 'sovereignty', 'neoliberal', 'high interest rates'],
    'FP_SOUTH': ['south-south', 'brics', 'africa', 'developing countries', 'multilateral', 'united nations', 'mercosur', 'regional integration',
                 'sovereignty', 'amazon', 'climate', 'global south'],
    'FP_WEST': ['united states', 'oecd', 'alliance', 'israel', 'west', 'security'],
}


def _norm(t):
    return re.sub(r'\s+', ' ', t.lower())


def rhetoric(seed=0):
    man_fn = os.path.join(EXT, 'corpus', 'manifest.csv')
    if not os.path.exists(man_fn):
        GAPS.append(('RHET', 'corpus manifest not found'))
        return None, []
    man = pd.read_csv(man_fn)
    rows, audit = [], []
    rng = np.random.default_rng(seed)
    for _, m in man.iterrows():
        fn = os.path.join(EXT, 'corpus', f'{m.doc_id}.txt')
        if not os.path.exists(fn):
            continue
        t = _norm(open(fn, encoding='utf-8', errors='ignore').read())
        toks = re.findall(r'\w+', t)
        n = len(toks)
        if n < 300:
            continue
        D = DICT_EN if str(m.language).lower().startswith('en') else DICT_PT
        cnt = {}
        for k, terms in D.items():
            cnt[k] = sum(len(re.findall(r'\b' + re.escape(w), t)) for w in terms)
        # sentence bootstrap for CI on score
        sents = [s for s in re.split(r'(?<=[.!?;])\s+', t) if len(s) > 20]
        sc = []
        for _ in range(300):
            pick = rng.integers(0, len(sents), len(sents))
            L = sum(sum(len(re.findall(r'\b' + re.escape(w), sents[i])) for w in D['LIBERAL']) for i in pick[:400])
            Lf = sum(sum(len(re.findall(r'\b' + re.escape(w), sents[i])) for w in D['LEFT']) for i in pick[:400])
            sc.append((L - Lf) / (L + Lf) if L + Lf else np.nan)
        lib, left = cnt['LIBERAL'], cnt['LEFT']
        rows.append(dict(doc_id=m.doc_id, corpus=m.corpus, regime_id=m.regime_id, party=m.party, date=m.date, tokens=n,
                         lib_per1k=1000 * lib / n, left_per1k=1000 * left / n, south_per1k=1000 * cnt['FP_SOUTH'] / n,
                         west_per1k=1000 * cnt['FP_WEST'] / n,
                         rhet_score=(lib - left) / (lib + left) if lib + left else np.nan,
                         fp_rhet=(cnt['FP_SOUTH'] - cnt['FP_WEST']) / (cnt['FP_SOUTH'] + cnt['FP_WEST']) if cnt['FP_SOUTH'] + cnt['FP_WEST'] else np.nan,
                         score_lo=np.nanquantile(sc, 0.1) if len(sc) else np.nan, score_hi=np.nanquantile(sc, 0.9) if len(sc) else np.nan,
                         source_url=m.source_url))
        hits = [s for s in sents if any(re.search(r'\b' + re.escape(w), s) for w in D['LIBERAL'] + D['LEFT'])]
        for s in rng.choice(hits, size=min(2, len(hits)), replace=False) if hits else []:
            audit.append(dict(doc_id=m.doc_id, sentence=s[:400]))
    R = pd.DataFrame(rows)
    if len(audit) > 20:
        audit = [audit[i] for i in rng.choice(len(audit), 20, replace=False)]
    return R, audit


# ----------------------------------------------------------------------------------------------
# 9. helpers for tests
# ----------------------------------------------------------------------------------------------
def spearman(x, y):
    d = pd.concat([pd.Series(x), pd.Series(y)], axis=1).dropna()
    if len(d) < 4:
        return np.nan, np.nan, len(d)
    rx, ry = d.iloc[:, 0].rank().values, d.iloc[:, 1].rank().values
    rho = np.corrcoef(rx, ry)[0, 1]
    rng = np.random.default_rng(0)
    perm = np.array([np.corrcoef(rx, rng.permutation(ry))[0, 1] for _ in range(5000)])
    p = (np.sum(np.abs(perm) >= abs(rho) - 1e-12) + 1) / (len(perm) + 1)
    return float(rho), float(p), len(d)


def year_level_delta(Sub, ym, tab, col_vals):
    pt = tab.set_index('rid').pt
    d = pd.DataFrame({'v': col_vals, 'u': pd.Series(ym)}).dropna()
    d['pt'] = d.u.map(pt)
    return d[d.pt == 1].v.mean() - d[d.pt == 0].v.mean()


def annual_eli(Sub):
    e = [s for s in ELI_SUBS if s in Sub.columns]
    return Sub[e].mean(axis=1).where(Sub[e].notna().sum(axis=1) >= 3)


def cell_eval(Sub, unit, variant, adj, crisis_out, fp, fp_draws, min_years=2):
    ym, tab = unit_map(unit, variant)
    drop = {2009, 2015, 2016, 2020} if crisis_out else set()
    if unit == 'year':
        ym, tab = unit_map('regime', variant)
    sc = regime_scores(Sub, ym, tab, drop, min_years=min_years)
    # FP
    if fp is not None:
        if unit == 'term':
            f, _ = fp_terms(fp, fp_draws)
        else:
            f, _ = fp_for_variant(fp, fp_draws, variant)
        sc['FP'] = f.reindex(sc.index)
    out = {}
    cols = [c for c in list(SUBS) + ['ELI', 'FP'] if c in sc.columns]
    for c in cols:
        if unit == 'year':
            if c == 'FP':
                vals = pd.Series({y: sc.loc[k, 'FP'] if k in sc.index else np.nan for y, k in ym.items() if y not in drop})
            elif c == 'ELI':
                vals = annual_eli(Sub).drop(list(drop), errors='ignore')
            else:
                vals = Sub[c].drop(list(drop), errors='ignore')
            out[c] = year_level_delta(Sub, {y: k for y, k in ym.items() if y not in drop}, tab, vals)
        elif adj == 'tot+start' and c not in ('FP',):
            t2 = tab if unit != 'term' else tab
            out[c] = start_adjust(sc, t2, c)[0] if unit == 'regime' else _term_start_adjust(sc, c)
        else:
            out[c] = delta(sc, c)
    return out, sc


def _term_start_adjust(sc, col):
    tab = pd.DataFrame([(k, pd.Timestamp(min(v[2]), 1, 1)) for k, v in TERMS.items()], columns=['rid', 'start']).set_index('rid')
    t = tab.reindex(sc.index); t.index.name = 'rid'
    return start_adjust(sc, t.reset_index(), col)[0]


# ----------------------------------------------------------------------------------------------
# 10. robustness grid
# ----------------------------------------------------------------------------------------------
VARIANTS = ['baseline', 'lula_split_2007', 'lula_split_gfc', 'nme_from_2011_08', 'levy_only', 'r9_split_2025']


def h_flags(o, sc, unit, variant):
    f = {}
    f['H1'] = (o.get('a', np.nan) >= -0.3) and (o.get('b', np.nan) >= -0.3)
    f['H1_comp'] = (o.get('a', np.nan) <= -0.5) and (o.get('b', np.nan) <= -0.5)
    f['H4'] = (o.get('f', np.nan) >= 0.8) and (o.get('c', np.nan) <= -0.5) and (abs(o.get('ELI', np.nan)) < 0.5)
    f['H4_partial_c'] = o.get('c', np.nan) < 0
    f['H4_partial_f'] = o.get('f', np.nan) > 0
    f['H4_comp'] = (o.get('ELI', np.nan) <= -0.8)
    f['H5'] = abs(o.get('d', np.nan)) < 0.5
    f['H5_comp'] = o.get('d', np.nan) <= -0.5
    f['H6'] = abs(o.get('FP', np.nan)) > abs(o.get('ELI', np.nan)) + 0.5
    if unit == 'regime' and 'R5' in sc.index:
        pt = sc[sc.pt == 1]['ELI'].dropna()
        if 'R5' in pt.index and len(pt) >= 3:
            sd = pt.std(); med = pt.median()
            f['H2'] = bool(pt.idxmin() == 'R5' and (med - pt['R5']) > sd)
            f['H2_rank_min'] = bool(pt.idxmin() == 'R5')
        r3 = 'R3'; r9s = [r for r in ['R9', 'R9a', 'R9b'] if r in sc.index]
        if r3 in sc.index and r9s:
            a9 = sc.loc[r9s, 'a'].mean(); b9 = sc.loc[r9s, 'b'].mean()
            f['H3'] = bool((a9 - sc.loc[r3, 'a'] < -0.5) and (b9 - sc.loc[r3, 'b'] >= 0))
            f['H3_comp'] = bool(b9 - sc.loc[r3, 'b'] < -0.5)
    return f


def robustness_grid(Zs, comp, fp_by, draws_by):
    rows = []
    for variant in VARIANTS:
        for unit in ['regime', 'term', 'year']:
            for adj in ['raw', 'tot', 'tot+start']:
                for crisis_out in [False, True]:
                    for f3 in [True, False]:
                        for fp4 in [True, False]:
                            Z = Zs[(adj != 'raw', f3)]
                            Sub, _ = subindex(Z, comp)
                            if unit == 'year' and adj == 'tot+start':
                                continue
                            o, sc = cell_eval(Sub, unit, variant, adj, crisis_out, fp_by[fp4], draws_by[fp4])
                            fl = h_flags(o, sc, unit, variant)
                            rows.append(dict(variant=variant, unit=unit, adj=adj, crisis_out=crisis_out, f3=f3, fp4=fp4,
                                             **{f'd_{k}': v for k, v in o.items()}, **fl))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------
# 11. main
# ----------------------------------------------------------------------------------------------
def external_index_by_unit(E, ym, tab, key, shift=0):
    s = ext_series(E, key)
    if not len(s):
        return pd.Series(dtype=float)
    s.index = s.index + shift
    out = {}
    for rid in tab.rid:
        ys = [y for y, k in ym.items() if k == rid and y in s.index]
        out[rid] = s.loc[ys].mean() if ys else np.nan
    return pd.Series(out)


def main():
    E = load_external()
    mp, last = monthly_panel()
    an = annual_panel()
    comp = components(E, mp, an)
    gaps0 = list(GAPS)
    # z variants
    Zs = {}
    for tot in (False, True):
        for f3 in (True, False):
            Zs[(tot, f3)] = zscore_pool(comp, tot_adj=tot, an=an, mp=mp, drop=() if f3 else ('F3',))[0]
    Z = Zs[(False, True)]
    Sub, ncomp = subindex(Z, comp)
    ym, tab = unit_map('regime')
    sc = regime_scores(Sub, ym, tab)
    sc_r6 = regime_scores(Sub, ym, tab, min_years=1)
    # exact-month attribution (descriptive): monthly components averaged within exact regime dates, z'd with annual params
    exact = {}
    for cid, c in comp.items():
        mmn = c.get('monthly')
        if mmn is None or c['descriptive'] or cid not in Z.columns:
            continue
        ann = (c['s'] * c['sign']); base_ = ann[(ann.index >= 1995) & (ann.index <= 2025)]
        mu_, sd_ = base_.mean(), base_.std()
        for _, r in tab.iterrows():
            v = mmn[(mmn.index >= r.start) & (mmn.index < r.end)]
            exact.setdefault(cid, {})[r.rid] = ((v.mean() * c['sign']) - mu_) / sd_ if len(v) else np.nan
    exact = pd.DataFrame(exact)
    # FP
    fp, FPm, draws = fp_axis(E, True)
    fp_nofp4, _, draws_nofp4 = fp_axis(E, False)
    if fp is not None:
        sc['FP'] = fp.reindex(sc.index); sc_r6['FP'] = fp.reindex(sc_r6.index)
    # external indices
    for key, shift in [('fraser_summary', 0), ('heritage_overall', -1)] + [(f'fraser_area{i}', 0) for i in range(1, 6)] + \
                      [(k, -1) for k in ['heritage_trade', 'heritage_monetary', 'heritage_govspend', 'heritage_taxburden',
                                         'heritage_fiscalhealth', 'heritage_investment', 'heritage_financial']]:
        v = external_index_by_unit(E, ym, tab, key, shift)
        if len(v): sc[key] = v.reindex(sc.index)

    # ---------- pre-specified measurement sensitivities (recompute components, then restore baseline)
    sens = {}
    for nm, kw in [('rstar_trailing_median', dict(rstar_mode='fallback')), ('target_2003_adjusted_8.5', dict(t2003=8.5)),
                   ('net_debt_sgs4513', dict(net_debt_mode='sgs4513'))]:
        cs = {k: dict(v) for k, v in components(E, mp, an, **kw).items()}
        Zx, _ = zscore_pool(cs); Sx, _ = subindex(Zx, cs); sx = regime_scores(Sx, ym, tab)
        sens[nm] = {c: delta(sx, c) for c in ['a', 'b', 'ELI']}
        sens[nm]['R9-R3_b'] = sx.loc['R9', 'b'] - sx.loc['R3', 'b']; sens[nm]['R9-R3_a'] = sx.loc['R9', 'a'] - sx.loc['R3', 'a']
        sens[nm]['scores'] = sx[['a', 'b', 'ELI']].round(3).to_dict()
    comp = components(E, mp, an)
    # ---------- deltas, permutation, bootstrap (baseline)
    cols = [c for c in SUBS if c in Sub.columns]
    base = {}
    for c in cols + ['ELI'] + (['FP'] if fp is not None else []):
        p, floor, nlab = perm_test(sc, c)
        base[c] = dict(delta=delta(sc, c), perm_p=p, perm_floor=floor, n_labelings=nlab,
                       n_pt=int(sc[[c, 'pt']].dropna().pt.sum()), n_non=int((sc[[c, 'pt']].dropna().pt == 0).sum()),
                       delta_with_R6=delta(sc_r6, c))
    # length-weighted variant (= year-level)
    for c in cols:
        base[c]['delta_yearweighted'] = year_level_delta(Sub, ym, tab, Sub[c])
    base['ELI']['delta_yearweighted'] = year_level_delta(Sub, ym, tab, annual_eli(Sub))
    boot, pboot = cluster_bootstrap(Sub, ym, tab, fp_draws=draws, cols=cols, pairs=[('R9', 'R3'), ('R5', 'R4'), ('R5', 'R9')])
    for c in cols + ['ELI', 'FP']:
        if c in base:
            base[c]['ci80'] = ci(boot[c], 0.8); base[c]['ci90'] = ci(boot[c], 0.9); base[c]['ci95'] = ci(boot[c], 0.95)
    base['FPminusELI'] = dict(delta=(abs(base['FP']['delta']) - abs(base['ELI']['delta'])) if 'FP' in base else np.nan,
                              ci80=ci(boot['FPminusELI'], 0.8), ci95=ci(boot['FPminusELI'], 0.95))
    # ToT-adjusted and start-adjusted
    SubT, _ = subindex(Zs[(True, True)], comp)
    scT = regime_scores(SubT, ym, tab)
    bootT, _ = cluster_bootstrap(SubT, ym, tab, cols=cols, nboot=2000, seed=1)
    for c in cols + ['ELI']:
        base[c]['delta_tot'] = delta(scT, c); base[c]['ci80_tot'] = ci(bootT[c], 0.8)
        base[c]['delta_tot_start'] = start_adjust(scT, tab, c)[0]
        base[c]['delta_start_raw'] = start_adjust(sc, tab, c)[0]
    # crisis exclusion
    scC = regime_scores(Sub, ym, tab, drop_years={2009, 2015, 2016, 2020})
    scC2 = regime_scores(Sub, ym, tab, drop_years={2002, 2003})
    for c in cols + ['ELI']:
        base[c]['delta_crisis_out'] = delta(scC, c); base[c]['delta_drop_2002_03'] = delta(scC2, c)
    # term level
    ymT, tabT = unit_map('term')
    scTerm = regime_scores(Sub, ymT, tabT)
    if fp is not None:
        fT, dT = fp_terms(fp, draws); scTerm['FP'] = fT.reindex(scTerm.index)
    for c in cols + ['ELI'] + (['FP'] if fp is not None else []):
        p, floor, nlab = perm_test(scTerm, c)
        base[c]['delta_term'] = delta(scTerm, c); base[c]['perm_p_term'] = p; base[c]['perm_floor_term'] = floor
    # sub-index decomposition of (b) for H3
    bcb_out = [k for k in ['M1', 'M2', 'M3', 'M4a', 'M4b', 'M5'] if k in Z.columns]
    Zb = Z[bcb_out]; wb = np.array([comp[k]['weight'] for k in bcb_out])
    b_out = (Zb.fillna(0) * wb).sum(axis=1) / (Zb.notna() * wb).sum(axis=1).replace(0, np.nan)
    b_gov = Z['M6']
    dec_b = {}
    for rid in ['R3', 'R4', 'R5', 'R7', 'R8', 'R9']:
        ys = [y for y, k in ym.items() if k == rid]
        dec_b[rid] = dict(bcb_outcome=b_out.loc[ys].mean(), gov_stance_M6=b_gov.loc[ys].mean(),
                          **{k: Z.loc[ys, k].mean() for k in bcb_out + ['M6']})
    # pairwise contrasts
    pairs = {}
    for p, d in pboot.items():
        nm = f'{p[0]}-{p[1]}'
        pairs[nm] = {c: dict(delta=float(sc.loc[p[0], c] - sc.loc[p[1], c]) if not (pd.isna(sc.loc[p[0], c]) or pd.isna(sc.loc[p[1], c])) else None,
                             ci80=ci(d[c], 0.8), ci95=ci(d[c], 0.95)) for c in cols + ['ELI']}
    # within PT (H2)
    ptE = sc[sc.pt == 1]['ELI'].dropna()
    h2 = dict(pt_eli=ptE.round(3).to_dict(), rank_R5=int(ptE.rank().get('R5', np.nan)) if 'R5' in ptE else None,
              median=ptE.median(), sd=ptE.std(), gap_R5_median=(ptE.get('R5', np.nan) - ptE.median()),
              gap_R5_R4=(ptE.get('R5', np.nan) - ptE.get('R4', np.nan)), gap_R5_R9=(ptE.get('R5', np.nan) - ptE.get('R9', np.nan)),
              delta_eli_ex_R5=delta(sc.drop('R5'), 'ELI'), floor_p=1 / len(ptE) if len(ptE) else None)
    ptE6 = sc_r6[sc_r6.pt == 1]['ELI'].dropna()
    h2['with_R6'] = dict(pt_eli=ptE6.round(3).to_dict(), sd=ptE6.std(), median=ptE6.median(),
                         delta_eli_ex_R5=delta(sc_r6.drop('R5'), 'ELI'))
    # rhetoric
    R, audit = rhetoric()
    h0 = {}
    if R is not None and len(R):
        A = R[R.corpus == 'A'].copy()
        A['ELI'] = A.regime_id.map(sc['ELI'])
        A['ELI_r6'] = A.regime_id.map(sc_r6['ELI'])
        rho, p, n = spearman(A.rhet_score, A.ELI_r6)
        h0['rho_rhet_ELI_corpusA'] = rho; h0['perm_p'] = p; h0['n_docs'] = n
        Ad = A.dropna(subset=['rhet_score', 'ELI_r6'])
        if len(Ad) >= 3:
            Ad = Ad.assign(rz=(Ad.rhet_score - Ad.rhet_score.mean()) / Ad.rhet_score.std(),
                           ez=(Ad.ELI_r6 - Ad.ELI_r6.mean()) / Ad.ELI_r6.std())
            ispt = Ad.party.astype(str).str.upper().str.contains('PT') & ~Ad.party.astype(str).str.upper().str.contains('PTB')
            h0['pt_mean_rhet_z'] = Ad[ispt].rz.mean(); h0['pt_mean_action_z'] = Ad[ispt].ez.mean()
            h0['non_mean_rhet_z'] = Ad[~ispt].rz.mean(); h0['non_mean_action_z'] = Ad[~ispt].ez.mean()
            h0['pt_gap_rhet_minus_action'] = h0['pt_mean_rhet_z'] - h0['pt_mean_action_z']
            # pt vs non-pt programmes raw scores
            h0['pt_mean_score'] = Ad[ispt].rhet_score.mean(); h0['non_mean_score'] = Ad[~ispt].rhet_score.mean()
        B = R[R.corpus == 'B'].copy()
        if len(B):
            B['FP'] = B.regime_id.map(sc.get('FP', pd.Series(dtype=float)))
            B['ELI'] = B.regime_id.map(sc_r6['ELI'])
            h0['rho_UN_fp_rhet_vs_FPaxis'] = spearman(B.fp_rhet, B.FP)[0]
            h0['rho_UN_econ_rhet_vs_ELI'] = spearman(B.rhet_score, B.ELI)[0]
            h0['UN_by_regime'] = B.groupby('regime_id')[['rhet_score', 'fp_rhet', 'south_per1k', 'west_per1k']].mean().round(3).to_dict()
        R.to_csv(os.path.join(HERE, 'rhetoric_scores.csv'), index=False)
    # H7 external indices
    h7 = {}
    for key in ['fraser_summary', 'heritage_overall']:
        if key in sc.columns:
            h7[key] = dict(zip(['rho', 'perm_p', 'n'], spearman(sc[key], sc['ELI'])))
            h7[key + '_delta_pt'] = delta(sc, key)
    area_map = {'fraser_area1': 'a', 'fraser_area3': 'b', 'fraser_area4': 'd', 'fraser_area5': 'c', 'heritage_trade': 'd',
                'heritage_monetary': 'b', 'heritage_govspend': 'a', 'heritage_fiscalhealth': 'a', 'heritage_financial': 'c',
                'heritage_investment': 'e'}
    for k, s in area_map.items():
        if k in sc.columns:
            h7[f'{k}~{s}'] = spearman(sc[k], sc[s])[0]
    # annual concordance (more obs)
    eli_ann = annual_eli(Sub)
    for key, sh in [('fraser_summary', 0), ('heritage_overall', -1)]:
        s = ext_series(E, key)
        if len(s):
            s.index = s.index + sh
            h7[key + '_annual_rho'] = spearman(s, eli_ann)[0]
    # FP quantitative anchors (descriptive, outcomes not policy)
    fpq = {}
    for key in ['unga_distance_bra_usa', 'unga_idealpoint_brazil']:
        v = external_index_by_unit(E, ym, tab, key, 0)
        if len(v): fpq[key] = v.round(3).to_dict()
    for key in ['wb/TX.VAL.MRCH.HI.ZS.BR', 'wb/TX.VAL.MRCH.R1.ZS.BR', 'wb/AG.LND.PFLS.HA.BR']:
        s_ = an[key]; fpq[key] = {r: (s_.loc[[y for y, k in ym.items() if k == r and y in s_.dropna().index]].mean()) for r in tab.rid}
    pr = ext_series(E, 'prodes_amazon_km2')
    if len(pr): fpq['prodes_amazon_km2'] = {r: pr.loc[[y for y, k in ym.items() if k == r and y in pr.index]].mean() for r in tab.rid}
    if fp is not None and 'unga_distance_bra_usa' in fpq:
        fpq['rho_FP_vs_unga_distance'] = spearman(sc['FP'], pd.Series(fpq['unga_distance_bra_usa']))[0]
    vp = {k.replace('vparty_v2pariglef_', ''): ext_series(E, k).round(3).to_dict() for k in E['series'].series_key.unique() if str(k).startswith('vparty_v2pariglef')}
    # robustness
    fp_by = {True: fp, False: fp_nofp4}; draws_by = {True: draws, False: draws_nofp4}
    rob = robustness_grid(Zs, comp, fp_by, draws_by)
    rob.to_csv(os.path.join(HERE, 'robustness_matrix.csv'), index=False)
    share = {}
    for h in ['H1', 'H1_comp', 'H2', 'H2_rank_min', 'H3', 'H3_comp', 'H4', 'H4_partial_c', 'H4_partial_f', 'H4_comp', 'H5', 'H5_comp', 'H6']:
        if h in rob.columns:
            v = rob[h].dropna().astype(bool)
            share[h] = dict(share=float(v.mean()) if len(v) else None, n_cells=int(len(v)))
    for c in cols + ['ELI', 'FP']:
        k = f'd_{c}'
        if k in rob.columns:
            v = rob[k].dropna(); bs = np.sign(base[c]['delta']) if c in base else 0
            share[f'sign_{c}'] = dict(share_same_sign=float((np.sign(v) == bs).mean()), n_cells=int(len(v)), median=float(v.median()),
                                      p10=float(v.quantile(.1)), p90=float(v.quantile(.9)))
    # BH families
    fam1 = [base[c]['perm_p'] for c in cols]
    q1 = bh(fam1)
    for c, q in zip(cols, q1): base[c]['bh_q'] = q
    fam2 = {}
    for cid in Z.columns:
        s = regime_scores(Z[[cid]].rename(columns={cid: 'x'}), ym, tab, min_years=2)
        s = s[['x', 'pt']]
        if s.x.notna().sum() >= 4 and s.dropna().pt.nunique() == 2:
            fam2[cid] = dict(delta=delta(s, 'x'), perm_p=perm_test(s, 'x')[0], regime_scores=s.x.round(3).to_dict())
    qs = bh([v['perm_p'] for v in fam2.values()])
    for (k, v), q in zip(fam2.items(), qs): v['bh_q'] = q
    return dict(E=E, mp=mp, an=an, comp=comp, Z=Z, Zs=Zs, Sub=Sub, ncomp=ncomp, sc=sc, sc_r6=sc_r6, scT=scT, scC=scC, scTerm=scTerm,
                fp=fp, FPm=FPm, draws=draws, base=base, boot=boot, pairs=pairs, dec_b=dec_b, h2=h2, R=R, audit=audit, h0=h0, h7=h7,
                rob=rob, share=share, fam2=fam2, last=last, sens=sens, exact=exact, fpq=fpq, vp=vp, gaps=gaps0 + [g for g in GAPS if g not in gaps0])


# ----------------------------------------------------------------------------------------------
# 12. charts (plotly; PT = orange slot, non-PT = blue slot of the validated reference palette)
# ----------------------------------------------------------------------------------------------
C_PT, C_NON, C_GRAY, C_INK, C_MUTED = '#eb6834', '#2a78d6', '#8a8984', '#0b0b0b', '#52514e'
DIVERGING = [[0, '#eb6834'], [0.5, '#f0efec'], [1, '#2a78d6']]


def _layout(fig, title, h=600):
    fig.update_layout(template='plotly_white', title=dict(text=title, font=dict(size=16, color=C_INK)), height=h,
                      font=dict(family='Inter, Helvetica, Arial', size=12, color=C_MUTED), hovermode='closest',
                      margin=dict(l=60, r=30, t=70, b=50))
    return fig


def charts(o):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    os.makedirs(CHARTS, exist_ok=True)
    reg = regimes(); Sub = o['Sub']; sc = o['sc']
    paths = []
    # 1 sub-index timeline
    subs = [s for s in SUBS if s in Sub.columns]
    fig = make_subplots(rows=len(subs), cols=1, shared_xaxes=True, subplot_titles=[f'({s}) {SUBS[s]}' for s in subs], vertical_spacing=0.03)
    for i, s in enumerate(subs, 1):
        for _, r in reg.iterrows():
            fig.add_vrect(x0=r.start.year + r.start.dayofyear / 365, x1=min(r.end.year + r.end.dayofyear / 365, 2026.7),
                          fillcolor=C_PT if r.pt else C_NON, opacity=0.08, line_width=0, row=i, col=1)
        fig.add_trace(go.Scatter(x=Sub.index, y=Sub[s], mode='lines+markers', line=dict(color=C_INK, width=2), marker=dict(size=6),
                                 name=s, showlegend=False, hovertemplate='%{x}: %{y:.2f} z<extra>' + s + '</extra>'), row=i, col=1)
        fig.add_hline(y=0, line=dict(color=C_GRAY, width=1), row=i, col=1)
    for d, lab in [(2000.34, 'LRF'), (2016.95, 'EC 95'), (2021.15, 'LC 179'), (2023.66, 'LC 200'), (2008.7, 'GFC'), (2011.66, 'Aug-11 cut')]:
        fig.add_vline(x=d, line=dict(color=C_GRAY, width=1, dash='dot'))
    _layout(fig, 'Sub-indices by year (+ = more liberal; f: + = more redistributive). Orange bands = PT regimes, blue = non-PT', h=1500)
    p = os.path.join(CHARTS, '1_subindex_timeline.html'); fig.write_html(p, include_plotlyjs='cdn'); paths.append(p)
    # 2 trajectory
    if 'FP' in sc.columns:
        boot_e = {}
        rng = np.random.default_rng(3)
        ym, tab = unit_map('regime')
        for rid in sc.index:
            ys = [y for y, k in ym.items() if k == rid]
            elis = annual_eli(Sub).loc[ys].dropna().values
            if len(elis) >= 1:
                bs = [np.mean(rng.choice(elis, len(elis))) for _ in range(1000)]
                boot_e[rid] = (np.quantile(bs, .1), np.quantile(bs, .9))
        scr = o['sc_r6']
        d = pd.DataFrame({'ELI': scr['ELI'], 'FP': sc['FP'], 'pt': scr['pt']}).dropna()
        fig = go.Figure()
        order = [r for r in reg.rid if r in d.index]
        for a, b in zip(order[:-1], order[1:]):
            fig.add_annotation(x=d.loc[b, 'ELI'], y=d.loc[b, 'FP'], ax=d.loc[a, 'ELI'], ay=d.loc[a, 'FP'], xref='x', yref='y', axref='x', ayref='y',
                               showarrow=True, arrowhead=2, arrowwidth=1.5, arrowcolor=C_GRAY, opacity=0.8)
        for grp, col, nm in [(1, C_PT, 'PT regimes'), (0, C_NON, 'non-PT regimes')]:
            dd = d[d.pt == grp]
            ex_lo = [dd.loc[r, 'ELI'] - boot_e.get(r, (np.nan,))[0] for r in dd.index]
            ex_hi = [boot_e.get(r, (0, np.nan))[1] - dd.loc[r, 'ELI'] for r in dd.index]
            fy = [np.quantile(o['draws'][r], .1) for r in dd.index]; fy2 = [np.quantile(o['draws'][r], .9) for r in dd.index]
            fig.add_trace(go.Scatter(x=dd.ELI, y=dd.FP, mode='markers+text', name=nm, text=[reg.set_index('rid').label[r] for r in dd.index],
                                     textposition='top center', marker=dict(size=13, color=col, line=dict(color='white', width=2)),
                                     error_x=dict(type='data', symmetric=False, array=ex_hi, arrayminus=ex_lo, color=col, thickness=1),
                                     error_y=dict(type='data', symmetric=False, array=[b - v for b, v in zip(fy2, dd.FP)],
                                                  arrayminus=[v - a for a, v in zip(fy, dd.FP)], color=col, thickness=1),
                                     hovertemplate='%{text}<br>ELI %{x:.2f}<br>FP %{y:.2f}<extra></extra>'))
        fig.add_hline(y=0, line=dict(color=C_GRAY, width=1)); fig.add_vline(x=0, line=dict(color=C_GRAY, width=1))
        fig.update_xaxes(title='Economic Liberalism Index (z; + = more liberal/orthodox)')
        fig.update_yaxes(title='Foreign-policy progressivism (z; + = South-South / multilateral / climate)')
        _layout(fig, '2-D trajectory: economic liberalism vs foreign-policy progressivism (arrows chronological; bars = 10-90% year-bootstrap / coding Monte Carlo). Levy/Barbosa shown with relaxed coverage', h=700)
        p = os.path.join(CHARTS, '2_trajectory_2d.html'); fig.write_html(p, include_plotlyjs='cdn'); paths.append(p)
    # 3 scorecard
    cols = [c for c in list(SUBS) + ['ELI', 'FP'] if c in sc.columns]
    ext_cols = [c for c in ['fraser_summary', 'heritage_overall'] if c in sc.columns]
    M = o['sc_r6'][[c for c in cols if c in o['sc_r6'].columns]].copy()
    if 'FP' in sc.columns: M['FP'] = sc['FP']
    for c in ext_cols:
        v = sc[c]; M[c + ' (z)'] = (v - v.mean()) / v.std()
    labels = [f"{reg.set_index('rid').label[r]} ({'PT' if reg.set_index('rid').pt[r] else 'non-PT'})" for r in M.index]
    fig = go.Figure(go.Heatmap(z=M.values.astype(float), x=list(M.columns), y=labels, colorscale=DIVERGING, zmid=0, zmin=-1.6, zmax=1.6,
                               text=np.round(M.values.astype(float), 2), texttemplate='%{text}', hovertemplate='%{y}<br>%{x}: %{z:.2f}<extra></extra>'))
    fig.update_yaxes(autorange='reversed')
    _layout(fig, 'Regime scorecard (z; blue = more liberal / more progressive FP / more redistributive for f). Levy/Barbosa (16 months) shown for reference only', h=600)
    p = os.path.join(CHARTS, '3_regime_scorecard.html'); fig.write_html(p, include_plotlyjs='cdn'); paths.append(p)
    # 4 rhetoric vs action
    R = o['R']
    if R is not None and len(R):
        A = R[R.corpus == 'A'].copy(); A['ELI'] = A.regime_id.map(o['sc_r6']['ELI'])
        fig = go.Figure()
        for grp, col, nm in [(True, C_PT, 'PT documents'), (False, C_NON, 'non-PT documents')]:
            ispt = A.party.astype(str).str.upper().eq('PT')
            dd = A[ispt == grp]
            fig.add_trace(go.Scatter(x=dd.rhet_score, y=dd.ELI, mode='markers+text', text=dd.doc_id.str.replace('A_', ''), textposition='top center',
                                     marker=dict(size=11, color=col, line=dict(color='white', width=2)), name=nm,
                                     error_x=dict(type='data', symmetric=False, array=dd.score_hi - dd.rhet_score, arrayminus=dd.rhet_score - dd.score_lo, color=col, thickness=1),
                                     hovertemplate='%{text}<br>rhetoric %{x:.2f}<br>ELI of following regime %{y:.2f}<extra></extra>'))
        fig.update_xaxes(title='Rhetoric score (LIBERAL - LEFT)/(LIBERAL + LEFT), campaign programme')
        fig.update_yaxes(title='ELI of the regime the programme preceded')
        _layout(fig, 'Rhetoric vs action: campaign programmes vs realised ELI', h=650)
        p = os.path.join(CHARTS, '4_rhetoric_vs_action.html'); fig.write_html(p, include_plotlyjs='cdn'); paths.append(p)
    # 5 external crosscheck
    E = o['E']; eli = annual_eli(Sub)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=['ELI (annual, z)', 'Fraser EFW summary (0-10)', 'Heritage IEF overall (0-100; edition year - 1)'])
    fig.add_trace(go.Scatter(x=eli.index, y=eli, mode='lines+markers', line=dict(color=C_INK, width=2), name='ELI'), row=1, col=1)
    for i, (k, sh) in enumerate([('fraser_summary', 0), ('heritage_overall', -1)], 2):
        s = ext_series(E, k)
        if len(s):
            fig.add_trace(go.Scatter(x=s.index + sh, y=s.values, mode='lines+markers', line=dict(color=C_NON, width=2), name=k), row=i, col=1)
    for _, r in reg.iterrows():
        for i in (1, 2, 3):
            fig.add_vrect(x0=r.start.year + r.start.dayofyear / 365, x1=min(r.end.year + r.end.dayofyear / 365, 2026.7), fillcolor=C_PT if r.pt else C_NON,
                          opacity=0.07, line_width=0, row=i, col=1)
    _layout(fig, 'External cross-check: ELI vs Fraser and Heritage (orange bands = PT)', h=850)
    p = os.path.join(CHARTS, '5_external_crosscheck.html'); fig.write_html(p, include_plotlyjs='cdn'); paths.append(p)
    # 6 robustness heatmap
    rob = o['rob']
    hs = [h for h in ['H1', 'H2', 'H3', 'H4', 'H4_partial_c', 'H4_partial_f', 'H5', 'H6'] if h in rob.columns]
    G = rob.groupby(['variant', 'unit'])[hs].agg(lambda v: np.nanmean(v.astype(float)) if v.notna().any() else np.nan)
    fig = go.Figure(go.Heatmap(z=G.values.astype(float), x=hs, y=[f'{a} / {b}' for a, b in G.index], zmin=0, zmax=1,
                               colorscale=[[0, '#f0efec'], [1, '#2a78d6']], text=np.round(G.values.astype(float), 2), texttemplate='%{text}',
                               hovertemplate='%{y}<br>%{x}: share of cells where prediction holds %{z:.2f}<extra></extra>'))
    fig.update_yaxes(autorange='reversed')
    _layout(fig, 'Robustness: share of grid cells (adjustment x crisis x F3 x FP4) in which each user prediction holds', h=800)
    p = os.path.join(CHARTS, '6_robustness_heatmap.html'); fig.write_html(p, include_plotlyjs='cdn'); paths.append(p)
    # 7 components small multiples
    comp = o['comp']
    panels = [('S2', 'Admin-price repression: -max(0, free - admin IPCA 12m), pp'), ('C1', 'Earmarked share of credit, %'), ('C4', 'Public-bank share of credit, %'),
              ('C3', 'TJLP/TLP minus Selic, pp'), ('T1', 'Tariff level (z-avg of weighted & simple)'), ('F1', 'Primary balance, % GDP'),
              ('M5', 'Taylor-rule residual (Selic minus rule), pp'), ('S5', 'Petrobras dividends / (dividends + capex), %')]
    panels = [p_ for p_ in panels if p_[0] in comp]
    fig = make_subplots(rows=4, cols=2, subplot_titles=[t for _, t in panels], vertical_spacing=0.08)
    for i, (cid, t) in enumerate(panels):
        r_, c_ = i // 2 + 1, i % 2 + 1
        mm = comp[cid].get('monthly')
        s = mm if mm is not None else comp[cid]['s']
        x = s.index
        fig.add_trace(go.Scatter(x=x, y=s.values, mode='lines' if mm is not None else 'lines+markers', line=dict(color=C_INK, width=2), name=cid, showlegend=False,
                                 hovertemplate='%{x}: %{y:.2f}<extra>' + cid + '</extra>'), row=r_, col=c_)
        for _, rg in reg.iterrows():
            if mm is not None:
                x0, x1 = rg.start, min(rg.end, pd.Timestamp('2026-09-01'))
            else:
                x0, x1 = rg.start.year + rg.start.dayofyear / 365, min(rg.end.year + rg.end.dayofyear / 365, 2026.7)
            fig.add_vrect(x0=x0, x1=x1, fillcolor=C_PT if rg.pt else C_NON, opacity=0.07, line_width=0, row=r_, col=c_)
    _layout(fig, 'Key components (natural units). Orange bands = PT regimes, blue = non-PT', h=1200)
    p = os.path.join(CHARTS, '7_components_small_multiples.html'); fig.write_html(p, include_plotlyjs='cdn'); paths.append(p)
    return paths


# ----------------------------------------------------------------------------------------------
# 13. outputs
# ----------------------------------------------------------------------------------------------
OWN_FACTS = [
    ('RM01', 'EC 9 of 9 Nov 1995 rewrote art. 177, ending the Petrobras oil monopoly (S4 liberalising event, 1995)', '1995-11-09', 'https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc09.htm', 'Planalto', 'S4;R1', 'high', 'soe'),
    ('RM02', 'Law 9,478 of 6 Aug 1997 (Petroleum Law) created the ANP and opened upstream to private operators (S4 liberalising, 1997)', '1997-08-06', 'https://www.planalto.gov.br/ccivil_03/leis/l9478.htm', 'Planalto', 'S4;R1', 'high', 'soe'),
    ('RM03', 'EC 20 of 15 Dec 1998 reformed the pension system (L4 -1, 1998)', '1998-12-15', 'https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc20.htm', 'Planalto', 'L4;R1', 'high', 'labour'),
    ('RM04', 'Law 12,351 of 22 Dec 2010 (pre-salt production sharing) made Petrobras operator of all blocks with a minimum 30% stake (S4 intervention, 2010)', '2010-12-22', 'https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12351.htm', 'Planalto', 'S4;R4', 'high', 'soe'),
    ('RM05', 'Decree 7,567 of 15 Sep 2011 (Plano Brasil Maior) raised IPI on vehicles failing local-content/regional requirements (S4 intervention, 2011)', '2011-09-15', 'https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/decreto/d7567.htm', 'Planalto', 'S4;R5', 'high', 'soe'),
    ('RM06', 'Law 13,365 of 29 Nov 2016 made Petrobras operatorship of pre-salt blocks a right of preference rather than mandatory (S4 liberalising, 2016)', '2016-11-29', 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/lei/l13365.htm', 'Planalto', 'S4;R7', 'high', 'soe'),
    ('RM07', 'Law 12,382 of 25 Feb 2011 set the minimum-wage valuation rule for 2011-2015 (L4 +1, 2011)', '2011-02-25', 'https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12382.htm', 'Planalto', 'L4;R5', 'high', 'labour'),
    ('RM08', 'Decree 6,391 of 12 Mar 2008 set IOF at 1.5% on foreign-investor FX inflows into financial/capital markets from 17 Mar 2008', '2008-03-17', 'https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2008/decreto/d6391.htm', 'Planalto', 'X2b;R4', 'high', 'fx'),
    ('RM09', 'Decree 6,613 of 22 Oct 2008 cut IOF on foreign-investor inflows into financial/capital markets to zero', '2008-10-22', 'https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2008/decreto/d6613.htm', 'Planalto', 'X2b;R4', 'high', 'fx'),
    ('RM10', 'MPs 664 and 665 of 30 Dec 2014 (converted into Laws 13,135 and 13,134 of 2015) tightened survivor pensions, sickness benefit, unemployment insurance and abono (L4 -1, coded 2015, Levy package)', '2014-12-30', 'https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/mpv/mpv665.htm', 'Planalto', 'L4;R6', 'high', 'labour'),
    ('RM11', "MP 838 of 30 May 2018 created a diesel price subsidy after the truckers' strike (S4 intervention, 2018)", '2018-05-30', 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/mpv/mpv838.htm', 'Planalto', 'S4;R7', 'high', 'soe'),
    ('RM12', 'In Feb 2021 Bolsonaro removed Petrobras CEO Roberto Castello Branco and named Gen. Joaquim Silva e Luna (S4 intervention, 2021); Silva e Luna served 2021-2022', '2021-02-19', 'https://en.wikipedia.org/wiki/Joaquim_Silva_e_Luna', 'Wikipedia (cites UOL/Estadao)', 'S4;R8', 'medium', 'soe'),
    ('RM13', 'EC 123 of 14 Jul 2022 declared a fuel-price emergency enabling election-year transfers; LC 194 of 23 Jun 2022 capped ICMS on fuels/energy (S4 intervention, 2022)', '2022-07-14', 'https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc123.htm', 'Planalto', 'S4;R8', 'high', 'soe'),
    ('RM14', 'LC 194 of 23 Jun 2022 treats fuels, electricity, communications and transport as essential goods, capping ICMS rates', '2022-06-23', 'https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp194.htm', 'Planalto', 'S4;R8', 'high', 'soe'),
    ('RM16', 'OAS SICE Brazil trade-agreement index: 20 agreements signed 1996-2026 with signature/entry-into-force dates (Mercosur-Chile ACE35 1996, Bolivia ACE36 1996, ... EU 2026-01-17/2026-05-01, EFTA 2025-09-16)', '2026-10-05', 'http://www.sice.oas.org/ctyindex/BRZ/BRZagreements_e.asp', 'OAS SICE', 'T3', 'high', 'trade'),
    ('RM15', 'BCB SGS series pulled 2026-10-05 via SOAP (FachadaWSSGS): 20593, 20539, 20542, 20625, 2007, 2043, 256, 27572, 11428, 4449, 4513, 433, 4189', '2026-10-05', 'https://www3.bcb.gov.br/sgspub/', 'Banco Central do Brasil', 'C1;C3;C4;S2;F4', 'high', 'credit'),
]


def write_outputs(o, chart_paths):
    # results.json
    base = o['base']
    for c, d in base.items():
        for k, v in d.items():
            rec(f'delta.{c}.{k}', v if not isinstance(v, tuple) else list(v), sid=c, source='computed (regime-level Δ PT - non-PT)')
    for k, v in o['h2'].items(): rec(f'H2.{k}', v, source='computed')
    for k, v in o['sens'].items(): rec(f'sensitivity.{k}', v, source='computed')
    for k, v in o['fpq'].items(): rec(f'FP_anchor.{k}', v, source='UNGA ideal points / WB / INPE (descriptive)')
    rec('vparty_v2pariglef', o['vp'], source='V-Party (ext/series_C.csv)')
    rec('exact_month_component_z', o['exact'].round(3).to_dict(), source='monthly components, exact regime dates')
    for k, v in o['h0'].items(): rec(f'H0.{k}', v, source='rhetoric dictionary coding')
    for k, v in o['h7'].items(): rec(f'H7.{k}', list(v) if isinstance(v, tuple) else v, source='Fraser/Heritage vs ELI')
    for k, v in o['pairs'].items(): rec(f'pair.{k}', v, source='computed pairwise contrast')
    for k, v in o['dec_b'].items(): rec(f'H3.decomp_b.{k}', v, source='computed')
    for k, v in o['share'].items(): rec(f'robustness.{k}', v, source='robustness_matrix.csv')
    for k, v in o['fam2'].items(): rec(f'component_delta.{k}', v, sid=o['comp'][k]['sids'], source=o['comp'][k]['src'])
    for sid, d in o['last'].items(): rec(f'last_date.{sid}', str(d), sid=sid, source='warehouse v_observations')
    rec('gaps', o['gaps'], source='executor')
    rec('rhetoric_audit_sample', o['audit'], source='random 20-sentence audit sample')
    rec('sql.monthly_panel', SQL_LOG.get('monthly_panel'), sql=SQL_LOG.get('monthly_panel'))
    rec('sql.annual_panel', SQL_LOG.get('annual_panel'), sql=SQL_LOG.get('annual_panel'))

    def clean(x):
        if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)): return [clean(v) for v in x]
        if isinstance(x, (np.floating, float)):
            return None if (x is None or np.isnan(x) or np.isinf(x)) else round(float(x), 5)
        if isinstance(x, (np.integer,)): return int(x)
        if isinstance(x, (np.bool_,)): return bool(x)
        return x
    json.dump(clean(RESULTS), open(os.path.join(HERE, 'results.json'), 'w'), indent=1, ensure_ascii=False)
    # regime table
    reg = regimes().set_index('rid')
    sc = o['sc_r6'].copy()
    T = pd.DataFrame(index=reg.index)
    T['label'] = reg.label; T['party'] = reg.party; T['start'] = reg.start.dt.date
    T['end'] = [min(e, pd.Timestamp(DATA_END)).date() for e in reg.end]
    T['months'] = [round((min(e, pd.Timestamp(DATA_END)) - s).days / 30.44, 1) for s, e in zip(reg.start, reg.end)]
    T['eligible_baseline'] = [bool(o['sc'].loc[r, 'n_ELI_subs'] >= 3 and not pd.isna(o['sc'].loc[r, 'ELI'])) for r in T.index]
    for c in list(SUBS) + ['ELI']:
        if c in sc.columns: T[c] = sc[c].round(3)
        if 'n_' + c in sc.columns: T['nyears_' + c] = sc['n_' + c]
    for c in ['FP', 'fraser_summary', 'heritage_overall']:
        if c in o['sc'].columns: T[c] = o['sc'][c].round(3)
    T['ELI_tot_adj'] = o['scT']['ELI'].round(3)
    if o['R'] is not None and len(o['R']):
        A = o['R'][o['R'].corpus == 'A']
        T['rhetoric_A'] = A.groupby('regime_id').rhet_score.mean().reindex(T.index).round(3)
        B = o['R'][o['R'].corpus == 'B']
        T['rhetoric_UN_econ'] = B.groupby('regime_id').rhet_score.mean().reindex(T.index).round(3)
        T['rhetoric_UN_fp'] = B.groupby('regime_id').fp_rhet.mean().reindex(T.index).round(3)
    T['n_components_used'] = [sum(1 for cid in o['Z'].columns if o['Z'].loc[[y for y, k in year_regime(regimes()).items() if k == r], cid].notna().any()) for r in T.index]
    T.index.name = 'rid'
    T.to_csv(os.path.join(HERE, 'regime_table.csv'))
    # components long
    rows = []
    for cid, c in o['comp'].items():
        for y, v in c['s'].items():
            rows.append(dict(component_id=cid, sub_index=c['sub'], series_ids=c['sids'], source=c['src'], transform=c['transform'],
                             sign=c['sign'], weight=c['weight'], descriptive=c['descriptive'], coverage=f"{int(c['s'].index.min())}-{int(c['s'].index.max())}",
                             year=int(y), value=round(float(v), 5), z=(round(float(o['Z'].loc[y, cid]), 4) if cid in o['Z'].columns and y in o['Z'].index and not pd.isna(o['Z'].loc[y, cid]) else None),
                             partial_year=bool(y == 2026)))
    pd.DataFrame(rows).to_csv(os.path.join(HERE, 'index_components.csv'), index=False)
    # facts
    F = o['E']['facts'].copy()
    own = pd.DataFrame(OWN_FACTS, columns=['fact_id', 'claim', 'date', 'source_url', 'publisher', 'used_in', 'confidence', 'channel'])
    own['accessed'] = '2026-10-05'; own['file'] = 'executor'
    ex = pd.read_csv('/private/tmp/claude-501/-Users-zkid18-proj-personal-brazil-macro/e568729e-c40b-484d-9883-0299d5b637e0/scratchpad/exports/external_facts.csv')
    ex = ex[ex.fact_id.isin(['C04', 'C07', 'C47', 'C63', 'C28', 'C34', 'B01', 'B31', 'C62'])].rename(columns={'used_in_scenario_ids': 'used_in'})
    ex['used_in'] = 'reused from exports study'; ex['file'] = 'exports/external_facts.csv'
    allf = pd.concat([F, own, ex], ignore_index=True)
    cols = ['fact_id', 'claim', 'date', 'source_url', 'publisher', 'accessed', 'used_in', 'confidence', 'channel', 'file']
    allf = allf[[c for c in cols if c in allf.columns]]
    allf.to_csv(os.path.join(HERE, 'external_facts.csv'), index=False)
    # external series (long)
    srows = []
    for fn in sorted(glob.glob(os.path.join(CACHE, 'sgs_*.csv'))):
        code = re.findall(r'sgs_(\d+)', fn)[0]
        d = pd.read_csv(fn)
        for _, r in d.iterrows():
            srows.append(dict(series_key=f'sgs:{code}', date=r.date, value=r.value, source_url='https://www3.bcb.gov.br/sgspub/ (SOAP FachadaWSSGS)', accessed='2026-10-05'))
    S = o['E']['series']
    for _, r in S.iterrows():
        srows.append(dict(series_key=r.series_key, date=r.date, value=r.value, source_url=r.get('source_url', ''), accessed=r.get('accessed', '2026-10-05')))
    pd.DataFrame(srows).to_csv(os.path.join(HERE, 'external_series.csv'), index=False)


if __name__ == '__main__':
    o = main()
    paths = charts(o)
    write_outputs(o, paths)
    import pickle
    pickle.dump({k: v for k, v in o.items() if k not in ('E',)}, open(os.path.join(CACHE, 'o.pkl'), 'wb'))
    print('done', paths)
