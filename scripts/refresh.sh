#!/usr/bin/env bash
# refresh.sh — re-ingest, rebuild the warehouse and the Brazil Monitoring portal.
#   daily  : Brazilian native sources (fast, keyless)
#   weekly : World Bank + ILO full Brazil pull (Dateno ids), when called with --weekly
# Each adapter failure is logged and skipped; the build always runs on the latest
# good bronze snapshots. Cron (droplet): see README "Deployment".
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
log(){ echo "[$(date -u +%FT%TZ)] $*"; }
run(){ log "run $1"; timeout 1800 $PY "ingest/$1.py" > "logs/$1.log" 2>&1 || log "FAILED $1 (see logs/$1.log)"; }
mkdir -p logs
for a in bcb_sgs bcb_focus bcb_olinda caged ibge_sidra ipeadata comexstat tesouro_bonds ons_energy ons_plants \
         anp_production b3_market cvm_financials datasus_tabnet who_mortality; do run "$a"; done
if [ "${1:-}" = "--weekly" ]; then run worldbank_bulk; run ilostat_bulk; fi
log "build"; $PY pipeline.py > logs/pipeline.log 2>&1 && $PY portal.py > logs/portal.log 2>&1 && log "done" || log "BUILD FAILED"
