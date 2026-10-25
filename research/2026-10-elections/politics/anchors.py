import duckdb, pandas as pd
pd.set_option('display.width',250); pd.set_option('display.max_columns',20)
c=duckdb.connect('/Users/zkid18/proj-personal/brazil-macro/warehouse/brazil_macro.duckdb',read_only=True)
T="""WITH terms AS (SELECT row_number() OVER (ORDER BY start) AS term_id,
 president||' '||strftime(start,'%Y') AS term_label, start, "end", lean FROM political_terms)"""
q=T+"""
SELECT a.series_id, t.term_label, round(avg(a.value),2) v, count(*) n FROM v_annual a
JOIN terms t ON make_date(a.year,7,1)>=t.start AND make_date(a.year,7,1)<t."end"
WHERE a.series_id IN ('wb/NY.GDP.MKTP.KD.ZG.BR','wb/NE.GDI.FTOT.ZS.BR','wb/SI.POV.GINI.BR','wb/GOV_WGI_CC_EST.BR') AND a.year BETWEEN 1985 AND 2025
GROUP BY 1,2,t.term_id ORDER BY 1,t.term_id"""
print(c.sql(q).df().pivot(index='term_label',columns='series_id',values='v'))
q=T+"""
SELECT o.series_id, t.term_label, round(avg(o.value),2) v, count(*) n FROM v_observations o
JOIN terms t ON o.date>=t.start AND o.date<t."end"
WHERE o.series_id IN ('real_policy_rate','primary_balance_gdp','ipca_12m','gross_public_debt_gdp') AND o.date<=current_date
GROUP BY 1,2,t.term_id ORDER BY 1,t.term_id"""
print(c.sql(q).df().pivot(index='term_label',columns='series_id',values='v'))
q=T+""", qq AS (SELECT o.date, o.value, t.term_label, t.term_id FROM v_observations o JOIN terms t ON o.date - INTERVAL 45 DAY>=t.start AND o.date - INTERVAL 45 DAY<t."end" WHERE series_id='wb/NYGDPMKTPSAKD_Q.BRA')
SELECT term_label, round(100*(power(arg_max(value,date)/arg_min(value,date), 4.0/(count(*)-1))-1),2) ann, count(*) n FROM qq GROUP BY term_label, term_id ORDER BY term_id"""
print(c.sql(q).df())
q="""SELECT year(date) y, arg_max(value,date) v FROM v_observations WHERE series_id='ibovespa_usd' GROUP BY 1 ORDER BY 1"""
d=c.sql(q).df().set_index('y').v; r=(d/d.shift()-1)*100
print(r.loc[[2002,2003,2008,2015,2016,2024,2025,2026]].round(1))
