import duckdb, pandas as pd
DB='/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb'
c=duckdb.connect(DB,read_only=True)
REG="""WITH reg(rid,label,s,e) AS (VALUES (2,'FHC II',DATE '1999-01-15',DATE '2003-01-01'),(3,'Lula-Palocci',DATE '2003-01-01',DATE '2006-04-01'),
(4,'Lula-Mantega',DATE '2006-04-01',DATE '2011-01-01'),(5,'Dilma NME',DATE '2011-01-01',DATE '2015-01-01'),(6,'Levy',DATE '2015-01-01',DATE '2016-05-12'),
(7,'Temer',DATE '2016-05-12',DATE '2019-01-01'),(8,'Bolsonaro',DATE '2019-01-01',DATE '2023-01-01'),(9,'Lula III',DATE '2023-01-01',DATE '2027-01-01'))"""
q=REG+"""
SELECT r.rid,r.label,o.series_id, round(avg(value),2) mean_v, round(arg_min(value,date),1) first_v, round(arg_max(value,date),1) last_v, min(date) d0, max(date) d1
FROM v_observations o JOIN reg r ON o.date>=r.s AND o.date<r.e
WHERE o.date<=current_date AND series_id IN ('real_policy_rate','primary_balance_gdp','ipca_12m','selic_target','embi_brazil','credit_gdp','gross_public_debt_gdp','net_public_debt_gdp')
GROUP BY ALL ORDER BY series_id, rid"""
df=c.sql(q).df()
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
print(df)
print(c.sql("select year(date) y, round(avg(value),2) from v_observations where series_id='real_policy_rate' and year(date) in (2003,2012,2013,2020,2021,2025,2026) and date<=current_date group by 1 order by 1").fetchall())
print(c.sql("select year(date) y, round(stddev_samp(value),2) from v_observations where series_id='focus_ipca_12m' and year(date) in (2002,2003,2015,2016,2021,2023,2025,2026) group by 1 order by 1").fetchall())
print(c.sql("select year(date) y, round(100*(exp(sum(ln(1+value/100)))-1),2) from v_observations where series_id='ipca_administered_prices' and year(date) in (2012,2013,2014,2015,2017,2021,2022,2023,2025) group by 1 order by 1").fetchall())
print(c.sql("select year(date) y, round(100*(exp(sum(ln(1+value/100)))-1),2) from v_observations where series_id='ipca_monthly' and year(date) in (2012,2013,2014,2015,2017,2021,2022,2023,2025) group by 1 order by 1").fetchall())
print(c.sql("""with s as (select date,value,lag(value) over (order by date) p from v_observations where series_id='selic_target')
select year(date),count(*) filter (where value<>p), count(*) filter (where value<p), min(value),max(value) from s where year(date) in (2011,2012,2017,2025,2026) group by 1 order by 1""").fetchall())
print(c.sql("select date,value from v_observations where series_id='selic_target' and date between '2011-08-25' and '2011-09-05' order by date").fetchall())
for sid,yrs in [('wb/TM.TAX.MRCH.WM.AR.ZS.BR',(1995,2003,2008,2012,2013,2019,2022)),('wb/TM.TAX.MRCH.SM.AR.ZS.BR',(1995,2003,2008,2012,2013,2019,2022)),('wb/NE.TRD.GNFS.ZS.BR',(2003,2010,2019,2022,2025)),('wb/TX.VAL.MRCH.HI.ZS.BR',(1995,2010,2023)),('wb/TX.VAL.MRCH.R1.ZS.BR',(1995,2010,2023))]:
    print(sid, c.sql(f"select year,round(value,2) from v_annual where series_id='{sid}' and year in {yrs} order by 1").fetchall())
print(c.sql("select year(cast(quarter_end as date)) y, round(sum(dividends_paid_brl)/1e9,1) d, round(sum(net_income_brl)/1e9,1) ni, round(arg_max(net_debt_brl_bn, cast(quarter_end as date)),0) nd from company_metrics where entity_id='PETR' group by 1 order by 1").fetchall())
print(c.sql("select year(date), round(arg_max(value,date),1) from v_observations where series_id='total_return_usd@PETR' and year(date) in (2014,2015,2022,2023,2026) group by 1 order by 1").fetchall())
print(c.sql("select year(date), round(arg_max(value,date)/1000,1), max(date) from v_observations where series_id='fx_reserves' and year(date) in (2002,2006,2008,2011,2019,2022,2026) group by 1 order by 1").fetchall())
