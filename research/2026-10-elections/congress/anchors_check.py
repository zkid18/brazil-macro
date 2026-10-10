import duckdb, pandas as pd
pd.set_option('display.width',250); pd.set_option('display.max_columns',30); pd.set_option('display.max_rows',200)
c=duckdb.connect('/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb',read_only=True)
print(c.sql("select count(*) from political_terms").fetchall(), c.sql("select max(start), max(\"end\") from political_terms").fetchall())
print(c.sql("select count(*), max(date) from political_events").fetchall())
print(c.sql("select date,label from political_events order by date desc limit 3").df() if 'label' in [r[0] for r in c.sql("describe political_events").fetchall()] else c.sql("select * from political_events order by 1 desc limit 3").df())
print(c.sql("select table_name from information_schema.tables where table_name ilike '%congress%' or table_name ilike '%emend%' or table_name ilike '%legisl%'").df())
print(c.sql("select series_id,title from v_search where title ilike '%emenda%' or title ilike '%congress%' or title ilike '%parliament%' or series_id ilike '%emend%' limit 20").df())
ids=['primary_balance_gdp','gross_public_debt_gdp','net_public_debt_gdp','interest_bill_gdp','implicit_interest_rate','r_minus_g','nominal_gdp_growth','wb/GC.XPN.TOTL.GD.ZS.BR','wb/GC.REV.XGRT.GD.ZS.BR','wb/GC.TAX.TOTL.GD.ZS.BR','wb/GC.NLD.TOTL.GD.ZS.BR','wb/GC.XPN.INTP.RV.ZS.BR','wb/GC.XPN.TRFT.ZS.BR','wb/GC.NFN.TOTL.GD.ZS.BR','wb/NE.CON.GOVT.ZS.BR','wb/NE.GDI.FTOT.ZS.BR','wb/NE.GDI.FTOT.KD.ZG.BR','real_policy_rate','selic_target','embi_brazil','gov_real_yield_10y','gov_nominal_yield_5y','wb/FR.INR.RINR.BR','wb/FR.INR.RISK.BR','focus_selic_12m','ibovespa_usd','brl_usd','wb/DSTKMKTXD_M.BRA','wb/DPANUSSPB_M.BRA','wb/REER_M.BRA','wb/GOV_WGI_CC_EST.BR','wb/NY.GDP.MKTP.KD.ZG.BR','wb/NYGDPMKTPSAKD_Q.BRA','ibc_br','wb/AG.LND.PFLS.HA.BR','wb/AG.LND.FRLS.HA.BR','exports_to_eu','wb/FP.CPI.TOTL.ZG.BR','wb/GC.BAL.CASH.GD.ZS.BR','wb/NE.GDI.FPUB.ZS.BR','gdp_nominal_12m_brl','wb/NY.GDP.DEFL.KD.ZG.BR','brent_usd','focus_ipca_12m']
df=c.sql(f"""select series_id, min(date) first_date, max(date) last_date, count(*) n from v_observations where date<=current_date and series_id in ({','.join("'"+i+"'" for i in ids)}) group by 1""").df().set_index('series_id').reindex(ids)
print(df)
print(c.sql("select * from catalog where series_id in ('gdp_nominal_12m_brl','embi_brazil','gov_real_yield_10y')").df() if True else '')
# event prototypes
d=c.sql("""select series_id,date,value from v_observations where series_id in ('ibovespa_usd','gov_real_yield_10y','embi_brazil','brl_usd') and date<=current_date order by 1,2""").df()
d['date']=pd.to_datetime(d.date); S={k:g.set_index('date').value for k,g in d.groupby('series_id')}
evs=['2016-04-17','2016-12-15','2017-07-13','2019-07-10','2019-10-22','2019-11-12','2021-02-24','2023-08-31','2023-12-20','2025-04-11','2025-11-27','2025-12-12']
rows=[]
for e in evs:
    r={'event':e}
    for k,x in S.items():
        i=x.index.searchsorted(pd.Timestamp(e))
        if i-1<0 or i+20>=len(x): r[k]=None; continue
        a,b=x.iloc[i-1],x.iloc[i+20]
        r[k]=f"{(b/a-1)*100:+.1f}%" if k=='ibovespa_usd' else f"{a:.3f}->{b:.3f}"
    rows.append(r)
print(pd.DataFrame(rows))
