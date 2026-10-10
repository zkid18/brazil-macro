import pickle, json, pandas as pd, numpy as np, sys
sys.path.insert(0, '.')
import pt_liberalism_study as S
pd.set_option('display.width', 260); pd.set_option('display.max_columns', 60); pd.set_option('display.max_rows', 200)
o = pickle.load(open('cache/o.pkl', 'rb'))
b = o['base']
print('=== BASE DELTAS')
rows = []
for c, d in b.items():
    if c == 'FPminusELI': print('FPminusELI', d); continue
    rows.append(dict(sub=c, delta=d['delta'], ci80=d.get('ci80'), ci95=d.get('ci95'), perm=d.get('perm_p'), floor=d.get('perm_floor'), npt=d.get('n_pt'), nnon=d.get('n_non'),
                     withR6=d.get('delta_with_R6'), yearw=d.get('delta_yearweighted'), tot=d.get('delta_tot'), tot80=d.get('ci80_tot'), totstart=d.get('delta_tot_start'),
                     start_raw=d.get('delta_start_raw'), crisis=d.get('delta_crisis_out'), drop0203=d.get('delta_drop_2002_03'), term=d.get('delta_term'), pterm=d.get('perm_p_term'), q=d.get('bh_q')))
print(pd.DataFrame(rows).round(3).to_string())
print('=== SCORES (sc_r6)'); print(o['sc_r6'][[c for c in ['a','b','c','d','e','f','g','ELI','n_ELI_subs'] if c in o['sc_r6']]].round(3))
print(o['sc'][[c for c in ['FP','fraser_summary','heritage_overall'] if c in o['sc']]].round(3))
print('=== TERM'); print(o['scTerm'][[c for c in ['a','b','c','d','e','f','g','ELI','FP','pt'] if c in o['scTerm']]].round(3))
print('=== TOT adj'); print(o['scT'][['a','b','c','d','e','f','g','ELI']].round(3))
print('=== pairs'); 
for k, v in o['pairs'].items():
    print(k, {c: (round(x['delta'],3) if x['delta'] is not None else None, tuple(round(y,2) for y in x['ci80'])) for c, x in v.items()})
print('=== decomp b'); print(pd.DataFrame(o['dec_b']).round(3))
print('=== H2', o['h2'])
print('=== H0', o['h0'])
print('=== H7', o['h7'])
print('=== sens', o['sens'])
print('=== share'); print(pd.DataFrame(o['share']).T)
print('=== fam2'); print(pd.DataFrame({k: dict(delta=v['delta'], p=v['perm_p'], q=v['bh_q']) for k, v in o['fam2'].items()}).T.round(3))
print('=== fam2 regime scores'); print(pd.DataFrame({k: v['regime_scores'] for k, v in o['fam2'].items()}).T.round(2))
print('=== gaps'); [print(g) for g in o['gaps']]
print('=== fpq', json.dumps({k: {kk: (round(vv,3) if isinstance(vv,float) else vv) for kk, vv in v.items()} if isinstance(v, dict) else v for k, v in o['fpq'].items()}, default=str))
print('=== vp', o['vp'])
print('=== exact'); print(o['exact'].round(2))
print('=== FP matrix'); print(o['FPm'])
print('=== Sub annual'); print(o['Sub'].round(2))
