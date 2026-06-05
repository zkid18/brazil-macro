"""dashboard.py — build a single self-contained dashboard.html from the warehouse.

Reads the silver/gold/dq outputs and emits one static HTML file (Plotly via CDN).
No server: just open warehouse/dashboard.html in a browser.

Run:  python3 dashboard.py
"""
from __future__ import annotations
import pathlib, html
import pandas as pd
import plotly.graph_objects as go

ROOT = pathlib.Path(__file__).resolve().parent
SILVER = ROOT / "warehouse" / "silver" / "fact_time_series.parquet"
GOLD = ROOT / "warehouse" / "gold"
DQ = ROOT / "dq" / "dq_report.csv"
OUT = ROOT / "warehouse" / "dashboard.html"
BOOK_YEAR = 2012  # Davidson published 2012; marker for before/after feel

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.32.0.min.js"

THEME_ORDER = [
    "macro_policy", "market_repricing", "domestic_demand",  # daily/monthly natives first
    "macro_activity", "inflation", "fiscal", "external_sector", "external_trade",
    "investment_productivity", "labor", "demography", "structural_energy",
    "environment_risk", "unknown",
]


def fig_html(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"displayModeBar": False})


def line_chart(df_metric: pd.DataFrame) -> str:
    m = df_metric.copy()
    m["dt"] = pd.to_datetime(m["date"])
    m = m.sort_values("dt")
    name = m["metric_name"].iloc[0]
    unit = m["unit"].iloc[0]
    freq = m["freq"].iloc[0]
    # markers only for sparse annual; lines-only for dense daily/monthly
    mode = "lines+markers" if freq == "annual" else "lines"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m["dt"], y=m["value"], mode=mode,
                             line=dict(width=1.6), marker=dict(size=3),
                             hovertemplate="%{x|%Y-%m-%d}: %{y:.2f}<extra></extra>"))
    fig.add_vline(x=f"{BOOK_YEAR}-01-01", line_width=1, line_dash="dot", line_color="#c0392b")
    fig.update_layout(
        title=dict(text=f"{name}<br><span style='font-size:11px;color:#888'>"
                        f"{m['metric_id'].iloc[0]} · {unit} · {freq}</span>", font=dict(size=13)),
        margin=dict(l=40, r=12, t=46, b=28), height=240,
        template="plotly_white", showlegend=False)
    return fig_html(fig)


def table_html(df: pd.DataFrame) -> str:
    return df.to_html(index=False, border=0, classes="tbl", justify="left")


def main():
    silver = pd.read_parquet(SILVER)
    scorecard = pd.read_parquet(GOLD / "book_scorecard.parquet")
    derived = pd.read_parquet(GOLD / "derived_metrics.parquet")
    dq = pd.read_csv(DQ)

    n_metrics = silver.metric_id.nunique()
    n_rows = len(silver)
    yr_min, yr_max = int(silver.year.min()), int(silver.year.max())
    freq_counts = silver.groupby("freq").metric_id.nunique().to_dict()
    freq_str = " · ".join(f"{v} {k}" for k, v in sorted(freq_counts.items()))

    # scorecard cards
    cards = []
    for _, r in scorecard.iterrows():
        cards.append(
            f"<div class='card'><div class='card-h'>{html.escape(r.thread)}"
            f"<span class='tag'>{html.escape(r.theme)}</span></div>"
            f"<div class='ev'>{html.escape(r.evidence)}</div>"
            f"<div class='rd'>{html.escape(r.reading)}</div></div>")

    # charts grouped by theme
    themes = sorted(silver.theme.unique(),
                    key=lambda t: THEME_ORDER.index(t) if t in THEME_ORDER else 99)
    sections = []
    for theme in themes:
        sub = silver[silver.theme == theme]
        charts = "".join(
            f"<div class='chart'>{line_chart(sub[sub.metric_id == mid])}</div>"
            for mid in sorted(sub.metric_id.unique()))
        sections.append(f"<h2>{html.escape(theme)}</h2><div class='grid'>{charts}</div>")

    page = f"""<!doctype html><html><head><meta charset='utf-8'>
<title>Brazil Macro Registry — dashboard</title>
<script src="{PLOTLY_CDN}"></script>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#fafafa;color:#222}}
 header{{background:#1a2332;color:#fff;padding:18px 28px}}
 header h1{{margin:0;font-size:20px}} header p{{margin:4px 0 0;color:#9fb0c8;font-size:13px}}
 .wrap{{max-width:1280px;margin:0 auto;padding:22px 28px}}
 h2{{margin:30px 0 8px;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:#555;border-bottom:1px solid #e2e2e2;padding-bottom:5px}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:12px}}
 .chart{{background:#fff;border:1px solid #ececec;border-radius:6px}}
 .cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:12px}}
 .card{{background:#fff;border:1px solid #e6e6e6;border-left:3px solid #c0392b;border-radius:6px;padding:12px 14px}}
 .card-h{{font-weight:600;font-size:14px;display:flex;justify-content:space-between;gap:8px}}
 .tag{{background:#eef1f5;color:#566;font-size:10px;padding:2px 7px;border-radius:10px;font-weight:500;white-space:nowrap}}
 .ev{{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#1a2332;margin:7px 0}}
 .rd{{font-size:12px;color:#666}}
 .tbl{{border-collapse:collapse;font-size:12px;background:#fff;width:100%}}
 .tbl th,.tbl td{{border:1px solid #ededed;padding:4px 8px;text-align:left}}
 .tbl th{{background:#f3f5f8}}
 .meta{{font-size:12px;color:#888;margin:6px 0 0}}
 .note{{font-size:11px;color:#999}}
</style></head><body>
<header><h1>Brazil Macro Data Registry — dashboard</h1>
<p>{n_metrics} metrics ({freq_str}) · {n_rows:,} observations · {yr_min}–{yr_max} · sources: Dateno/World Bank (annual) + BCB SGS (daily/monthly) · dotted red line = 2012 (book published)</p></header>
<div class='wrap'>
 <h2>Book scorecard — computed evidence vs Davidson's 2012 bets</h2>
 <div class='cards'>{''.join(cards)}</div>
 <h2>Derived metrics</h2>{table_html(derived)}
 <h2>Coverage &amp; freshness (DQ)</h2>{table_html(dq)}
 {''.join(sections)}
 <p class='note'>Generated by dashboard.py from warehouse/silver + gold. Static file — no server.</p>
</div></body></html>"""

    OUT.write_text(page)
    print(f"Wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
    print(f"Open: file://{OUT}")


if __name__ == "__main__":
    main()
