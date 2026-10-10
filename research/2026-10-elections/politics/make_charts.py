"""Charts for the lean study (plotly HTML). Imports the study module (re-runs it, ~10s)."""
import numpy as np, pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import politics_lean_study as S

CH = S.OUT / "charts"; CH.mkdir(exist_ok=True)
LEAN_COL = {"left": "#e34948", "right": "#2a78d6", "centre": "#eda100"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
RAW_COL, ADJ_COL = "#52514e", "#1baf7a"
FONT = dict(family="Inter, -apple-system, Segoe UI, Roboto, sans-serif", size=13, color=INK)


def style(fig, title, h=520):
    fig.update_layout(title=dict(text=title, font=dict(size=16)), template="plotly_white", font=FONT, height=h,
                      paper_bgcolor=SURF, plot_bgcolor=SURF, margin=dict(l=70, r=30, t=70, b=50),
                      hoverlabel=dict(bgcolor="white", font=dict(color=INK)))
    fig.update_xaxes(gridcolor=GRID, linecolor=INK2, zerolinecolor=INK2)
    fig.update_yaxes(gridcolor=GRID, linecolor=INK2, zerolinecolor=INK2)
    return fig


def save(fig, name):
    fig.write_html(CH / name, include_plotlyjs="cdn", full_html=True)
    return str(CH / name)


paths = {}
# 1 timeline -------------------------------------------------------------------
gdp = S.MET["A1"]["s"]; tot = S.TOT
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                    subplot_titles=("Real GDP growth, % y/y (wb/NY.GDP.MKTP.KD.ZG.BR; 2026 = IBC-Br YTD)",
                                    "Terms of trade, index (TT.PRI / UVI ratio, 2000 = 100 scale)"))
lean_by_year = {y: S.LEAN_A[S.ATTR.at[y, "term_c"]] for y in gdp.index}
fig.add_bar(x=gdp.index, y=gdp.values, marker_color=[LEAN_COL[lean_by_year[y]] for y in gdp.index], marker_line_width=0,
            name="GDP growth", showlegend=False, hovertemplate="%{x}: %{y:.1f}%<extra></extra>", row=1, col=1)
fig.add_scatter(x=tot.loc[1985:].index, y=tot.loc[1985:].values, mode="lines", line=dict(color=INK, width=2), name="ToT",
                showlegend=False, hovertemplate="%{x}: %{y:.0f}<extra></extra>", row=2, col=1)
for t in S.T.itertuples():
    l = S.LEAN_A[t.short]
    x0 = max(t.start.year + t.start.dayofyear / 366, 1985) - 0.5; x1 = min(t.end.year + t.end.dayofyear / 366, 2026.8) - 0.5
    for r in (1, 2):
        fig.add_vrect(x0=x0, x1=x1, fillcolor=LEAN_COL[l], opacity=0.08, line_width=0, row=r, col=1)
    fig.add_annotation(x=(x0 + x1) / 2, y=1.0, yref="paper", text=t.short, showarrow=False, font=dict(size=10, color=INK2), yshift=-28)
for l in ("left", "right", "centre"):
    fig.add_bar(x=[None], y=[None], marker_color=LEAN_COL[l], name={"left": "left (PT)", "right": "right / centre-right", "centre": "centre"}[l])
fig.update_layout(legend=dict(orientation="h", y=-0.08), bargap=0.15)
paths["timeline"] = save(style(fig, "Lean bands over growth and the terms-of-trade cycle, 1985–2026", 640), "timeline.html")

# 2 forest: standardized Δ raw vs ToT-adjusted -----------------------------------
rows = []
for mid in S.PRIMARY:
    r = S.RESULTS[mid]
    if "diff" not in r:
        continue
    sd = pd.Series(r["term_values"]).std()
    rows.append(dict(mid=mid, label=f"{mid} {S.MET[mid]['name']}", bucket=S.MET[mid]["bucket"], d=r["diff"] / sd, lo=r["ci80"][0] / sd, hi=r["ci80"][1] / sd,
                     dt=r.get("diff_tot", np.nan) / sd, lot=r.get("ci80_tot", [np.nan, np.nan])[0] / sd, hit=r.get("ci80_tot", [np.nan, np.nan])[1] / sd,
                     share=r.get("sign_consistency_share"), p=r["perm_p"], raw=r["diff"], unit=S.MET[mid]["unit"]))
F = pd.DataFrame(rows).iloc[::-1].reset_index(drop=True); F["yy"] = np.arange(len(F))
fig = go.Figure()
fig.add_scatter(x=F.d, y=F.yy + 0.17, mode="markers", marker=dict(size=10, color=RAW_COL, line=dict(color=SURF, width=2)), name="raw Δ (80% cluster-bootstrap CI)",
                error_x=dict(type="data", symmetric=False, array=F.hi - F.d, arrayminus=F.d - F.lo, color=RAW_COL, thickness=2, width=0),
                customdata=np.c_[F.raw, F.unit, F.p, F.share],
                hovertemplate="Δ left−right = %{customdata[0]:.2f} %{customdata[1]}<br>= %{x:.2f} SD of term values<br>perm p = %{customdata[2]:.2f}<br>sign-consistency %{customdata[3]:.0%}<extra>raw</extra>")
fig.add_scatter(x=F.dt, y=F.yy - 0.17, mode="markers", marker=dict(size=10, color=ADJ_COL, symbol="diamond", line=dict(color=SURF, width=2)), name="ToT-adjusted Δ (80% CI)",
                error_x=dict(type="data", symmetric=False, array=F.hit - F.dt, arrayminus=F.dt - F.lot, color=ADJ_COL, thickness=2, width=0),
                hovertemplate="ToT-adjusted Δ = %{x:.2f} SD<extra>ToT-adj</extra>")
fig.add_vline(x=0, line_color=INK2, line_width=1)
fig.update_xaxes(title="Δ (left − right), in SD of term-level values · + = higher under left terms")
fig.update_layout(legend=dict(orientation="h", y=1.04, x=0), yaxis=dict(tickfont=dict(size=11), tickmode="array", tickvals=F.yy, ticktext=F.label, range=[-0.6, len(F) - 0.4], zeroline=False))
paths["forest"] = save(style(fig, "Left − right difference per primary metric, raw vs terms-of-trade adjusted", 820), "forest.html")

# 3 robustness heatmap -----------------------------------------------------------
R = S.ROB[S.ROB["diff"].notna()]
cols, mat = [], []
dims = [("sample", ["1985+", "1995+", "2003+"]), ("unit", ["term", "mandate", "year"]), ("coding", list("ABCDE")),
        ("attribution", ["c", "lag1", "dropfirst"]), ("adjustment", ["raw", "tot", "totbrent"]), ("transform", ["mean", "rank"])]
for dim, levels in dims:
    for lv in levels:
        cols.append(f"{dim}:{lv}")
labels = [f"{m} {S.MET[m]['name']}" for m in S.PRIMARY]
Z = np.full((len(S.PRIMARY), len(cols)), np.nan)
for i, m in enumerate(S.PRIMARY):
    rm = R[R.metric_id == m]
    j = 0
    for dim, levels in dims:
        for lv in levels:
            x = rm[rm[dim] == lv]
            if len(x):
                Z[i, j] = (x.sign > 0).mean()
            j += 1
fig = go.Figure(go.Heatmap(z=Z[::-1], x=cols, y=labels[::-1], zmin=0, zmax=1, xgap=2, ygap=2,
                           colorscale=[[0, "#2a78d6"], [0.5, "#f0efec"], [1, "#e34948"]],
                           colorbar=dict(title="share of cells<br>with Δ>0"),
                           hovertemplate="%{y}<br>%{x}<br>share Δ(left−right) > 0: %{z:.0%}<extra></extra>"))
fig.update_xaxes(tickangle=-45, tickfont=dict(size=10)); fig.update_yaxes(tickfont=dict(size=11))
paths["robustness"] = save(style(fig, "Robustness: share of specification cells where left terms score higher (red) or lower (blue)", 820), "robustness_heatmap.html")

# 4 event-study paths --------------------------------------------------------------
ser = [("ibovespa_usd", "Ibovespa in USD, cum. abnormal log %"), ("brl_usd", "BRL vs USD, cum. abnormal log % (+ = stronger BRL)"),
       ("embi_brazil", "EMBI spread, cum. abnormal bp"), ("gov_real_yield_10y", "NTN-B 10y real yield, cum. abnormal bp")]
fig = make_subplots(rows=2, cols=2, subplot_titles=[s[1] for s in ser], vertical_spacing=0.14, horizontal_spacing=0.08)
shown = set()
for k, (sid, ttl) in enumerate(ser):
    d = S.daily_changes(sid)
    r, c = k // 2 + 1, k % 2 + 1
    for date, label, grp in S.EVENTS:
        if grp not in ("left win", "right transition"):
            continue
        t0 = S.event_index(d, date)
        if t0 - 250 < 0 or t0 + 60 >= len(d):
            continue
        mu = d.iloc[t0 - 250: t0 - 120].mean()
        seg = d.iloc[t0 - 60: t0 + 61] - mu
        path = seg.cumsum() - seg.iloc[:60].sum()   # zero at t-1
        col = LEAN_COL["left" if grp == "left win" else "right"]
        fig.add_scatter(x=np.arange(-60, 61), y=path.values, mode="lines", line=dict(color=col, width=2), opacity=0.85,
                        name=grp, legendgroup=grp, showlegend=grp not in shown,
                        hovertemplate=f"{label}<br>day %{{x}}: %{{y:.1f}}<extra></extra>", row=r, col=c)
        shown.add(grp)
    fig.add_vline(x=0, line_color=INK2, line_width=1, row=r, col=c)
fig.update_xaxes(title="trading days from event (0 = first session on/after)")
fig.update_layout(legend=dict(orientation="h", y=-0.1))
paths["event_study"] = save(style(fig, "Market paths around left wins (red) vs right/centre-right transitions (blue); zero at t−1", 760), "event_study.html")

# 5 campaign tape 2026 vs prior election years ------------------------------------
fig = make_subplots(rows=1, cols=3, subplot_titles=("Ibovespa USD, log % from t−120", "BRL vs USD, log % (+ = stronger) from t−120",
                                                    "NTN-B 10y real, bp from t−120"), horizontal_spacing=0.07)
for k, (sid, sign, mult) in enumerate([("ibovespa_usd", 1, "log"), ("brl_usd", -1, "log"), ("gov_real_yield_10y", 1, "bp")]):
    x = S.DS[sid]
    for yr, d1 in S.R1.items():
        pre = x[x.index < pd.Timestamp(d1)]
        if len(pre) < 121 or (pd.Timestamp(d1) - pre.index[-1]).days > 7:
            continue
        seg = pre.iloc[-120:]
        y = sign * 100 * np.log(seg / seg.iloc[0]) if mult == "log" else 100 * (seg - seg.iloc[0])
        is26 = yr == 2026
        fig.add_scatter(x=np.arange(-120, 0), y=y.values, mode="lines", name=str(yr), legendgroup=str(yr), showlegend=(k == 0),
                        line=dict(color=INK if is26 else "#a8a79f", width=3 if is26 else 1.5),
                        hovertemplate=f"{yr}: day %{{x}} %{{y:.1f}}<extra></extra>", row=1, col=k + 1)
        fig.add_annotation(x=-1, y=float(y.iloc[-1]), text=str(yr), showarrow=False, xanchor="left", font=dict(size=10, color=INK if is26 else INK2),
                           row=1, col=k + 1)
fig.update_xaxes(title="trading days before first round")
paths["campaign_2026"] = save(style(fig, "2026 campaign tape (black) vs the six prior first-round run-ups — data end 2026-10-02", 520), "campaign_2026.html")

# 6 debt fan ------------------------------------------------------------------------
fig = go.Figure()
yrs = list(range(2026, 2031))
for r in S.DEBT_GRID.itertuples():
    path = [getattr(r, f"debt_{y}") for y in yrs]
    fig.add_scatter(x=yrs, y=path, mode="lines", line=dict(color="#c9c8c1", width=1.2), showlegend=False,
                    hovertemplate=f"grid r−g={r.r_minus_g}, pb={r.primary_balance}: %{{y:.1f}}<extra></extra>")
    fig.add_annotation(x=2030, y=path[-1], text=f"r−g {r.r_minus_g}, pb {r.primary_balance:+d}", showarrow=False, xanchor="left", font=dict(size=9, color=INK2))
rg = S.START["r_minus_g"]["value"]
for br, lean in (("Lula IV — left pb median", "left"), ("Flávio Bolsonaro — right pb median", "right")):
    pb = S.DEBT_BRANCH[(S.DEBT_BRANCH.branch.str.contains("left" if lean == "left" else "right")) & (S.DEBT_BRANCH.pb_case == "pb median")].primary_balance.iloc[0]
    p = S.debt_path(S.D0, rg, pb)
    fig.add_scatter(x=yrs, y=p, mode="lines+markers", line=dict(color=LEAN_COL[lean], width=3), marker=dict(size=8),
                    name=f"{br} ({pb:+.2f}% GDP), r−g {rg:.2f}", hovertemplate="%{x}: %{y:.1f}% GDP<extra></extra>")
for lab, pbv, lean in (("Lula III mandate mean pb", S.PB_HIST["Lula III"][1], "left"), ("Bolsonaro ex-2020 mean pb", S.BOLSO_EX2020, "right")):
    p = S.debt_path(S.D0, rg, pbv)
    fig.add_scatter(x=yrs, y=p, mode="lines", line=dict(color=LEAN_COL[lean], width=2, dash="dot"), name=f"{lab} ({pbv:+.2f}), r−g {rg:.2f}",
                    hovertemplate="%{x}: %{y:.1f}% GDP<extra></extra>")
p = S.debt_path(S.D0, rg, S.START["primary_balance_gdp"]["value"])
fig.add_scatter(x=yrs, y=p, mode="lines", line=dict(color=INK, width=2, dash="dash"), name=f"current run-rate pb {S.START['primary_balance_gdp']['value']:+.2f}, r−g {rg:.2f}")
fig.update_yaxes(title="gross general-government debt, % GDP"); fig.update_xaxes(dtick=1, range=[2025.8, 2031.2])
fig.update_layout(legend=dict(orientation="v", y=-0.1, yanchor="top", x=0))
paths["debt_fan"] = save(style(fig, f"Gross debt/GDP 2027–2030: d(t+1) = d·(1+r)/(1+g) − pb, from {S.D0:.1f}% (Aug 2026)", 760).update_layout(margin=dict(b=200)), "debt_fan.html")

# 7 composites by term ----------------------------------------------------------------
fig = make_subplots(rows=2, cols=2, subplot_titles=list(S.COMPOSITES), vertical_spacing=0.18)
for k, name in enumerate(S.COMPOSITES):
    c = pd.Series(S.COMP_RES[(name, "raw")]["by_term"]).reindex([t for t in S.TERM_ORDER]).dropna()
    fig.add_bar(x=c.index, y=c.values, marker_color=[LEAN_COL[S.LEAN_A[t]] for t in c.index], marker_line_width=0, showlegend=False,
                hovertemplate="%{x}: %{y:.2f} z<extra></extra>", row=k // 2 + 1, col=k % 2 + 1)
for l in ("left", "right", "centre"):
    fig.add_bar(x=[None], y=[None], marker_color=LEAN_COL[l], name=l)
fig.update_yaxes(title="mean z-score")
fig.update_layout(legend=dict(orientation="h", y=-0.08), bargap=0.25)
paths["composites"] = save(style(fig, "Pre-registered composites by term (z-mean of components; higher = better on that composite's terms)", 700), "composites.html")

if __name__ == "__main__":
    for k, v in paths.items():
        print(k, v)
