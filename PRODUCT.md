# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
A curious economics graduate: interested in Brazil, comfortable with rates, inflation and correlation, but not a sell-side specialist. They open the report to understand what the data says about Brazil's resource economy and its biggest resource companies, and to check claims (Davidson's 2012 book, social-media charts) against numbers.

## Product Purpose
A registry-driven Brazil macro warehouse rendered as one static report. It states falsifiable hypotheses with pre-registered thresholds, tests them on public data, and shows the evidence. Success: a reader finds any verdict, its test and its source in seconds, and can trust the numbers.

## Positioning
Every claim is a test with a fixed threshold, computed from free public sources (BCB, IBGE, ComexStat, ANP, ONS, B3, CVM, Tesouro, IPEAData, World Bank via Dateno) and re-computed on each build, so verdicts can flip as data lands.

## Operating Context
Built by `python3 pipeline.py && python3 dashboard.py` into `warehouse/dashboard.html`; also published as a shareable claude.ai artifact link. Read on desktop and phone.

## Capabilities and Constraints
- Static single HTML file; Plotly from cdnjs; data embedded; no server.
- Company coverage: Petrobras, Vale, Axia (ex-Eletrobras), Suzano, PRIO, with Itaú as the non-resource control.
- Physical volumes are company-specific only where a public source exists (ANP operated oil, ONS generation); Vale and Suzano use national export tonnes as context, labelled as such.

## Brand Commitments
- Voice: neutral, data only. Verdicts state the statistic, the threshold and the result; no editorializing.
- Language: English; keep Portuguese source names (Selic, IPCA, CAGED, Focus) with short glosses.

## Evidence on Hand
All figures come from the warehouse (`warehouse/silver`, `warehouse/gold`). No testimonials, forecasts or investment advice; never fabricate numbers.

## Product Principles
1. The question leads; the verdict, the test and the source are always one glance apart.
2. Show the threshold next to the result so the reader judges distance, not just a label.
3. Say what a series is (and is not): proxies, snapshots and gaps are labelled where they appear.
4. Summary before detail; the library is there for checking, not for the first read.

## Accessibility & Inclusion
WCAG AA contrast in light and dark; identity never carried by color alone (labels, legends, tables); keyboard-reachable navigation; reduced motion respected.
