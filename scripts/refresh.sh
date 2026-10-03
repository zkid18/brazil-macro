#!/usr/bin/env bash
# refresh.sh — Brazil Monitoring ETL: ingest -> checks -> build (staged) -> sanity gate -> swap.
#
#   ./scripts/refresh.sh            daily   : Brazilian native sources (fast, keyless)
#   ./scripts/refresh.sh --weekly   weekly  : daily + World Bank and ILO full Brazil pull
#   ./scripts/refresh.sh --monthly  monthly : full refresh — every adapter, bulk caches
#                                             re-downloaded, ILO labels, Dateno tier-1 pull and
#                                             discovery (needs DATENO_API_KEY in .env)
#
# Safety: one run at a time (lock); a failed adapter is logged and skipped (the build uses the
# last good bronze snapshot); the warehouse and the site are built into staging paths and only
# swapped in if the build succeeds AND the catalogue did not shrink by more than 10%.
# Summary of every run: logs/last_run.json (+ logs/<adapter>.log). Cron on the droplet:
#   30 9 2-31 * 1-6  daily · 30 9 * * 0  --weekly · 0 5 1 * *  --monthly   (/etc/cron.d/brazil-monitoring)
set -u
cd "$(dirname "$0")/.."
ROOT=$(pwd)
PY=.venv/bin/python
MODE=daily; [ "${1:-}" = "--weekly" ] && MODE=weekly; [ "${1:-}" = "--monthly" ] && MODE=monthly
mkdir -p logs
log(){ echo "[$(date -u +%FT%TZ)] [$MODE] $*"; }

# ---- lock (mkdir is atomic on every OS; flock is not on macOS)
LOCK=/tmp/brazil-monitoring.lock
if ! mkdir "$LOCK" 2>/dev/null; then log "another run is in progress ($LOCK) — exiting"; exit 0; fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

START=$(date -u +%FT%TZ); FAILED=()
run(){  # run <adapter> [args...] — logged, time-limited, never fatal
  local a=$1; shift
  log "run $a $*"
  if ! timeout 3600 $PY "ingest/$a.py" "$@" > "logs/$a.log" 2>&1; then FAILED+=("$a"); log "FAILED $a (logs/$a.log)"; fi
}
[ -f .env ] && { set -a; . ./.env; set +a; }

# ---- 1. ingest (SKIP_INGEST=1 rebuilds from the current bronze only — for testing the build/swap)
if [ "${SKIP_INGEST:-0}" != 1 ]; then
NATIVE=(bcb_sgs bcb_focus bcb_olinda caged ibge_sidra ipeadata comexstat tesouro_bonds ons_energy ons_plants
        anp_production b3_market cvm_financials datasus_tabnet who_mortality)
for a in "${NATIVE[@]}"; do run "$a"; done
if [ "$MODE" != daily ]; then
  if [ "$MODE" = monthly ]; then run worldbank_bulk --max-age 25; run ilostat_bulk --refresh
  else run worldbank_bulk; run ilostat_bulk; fi
fi
if [ "$MODE" = monthly ]; then
  run ilo_codelists
  if [ -n "${DATENO_API_KEY:-}" ]; then run dateno_pull; run dateno_discover; else log "skip Dateno (no DATENO_API_KEY)"; fi
fi
fi

# ---- 2. checks (report only: a gap in one source must not block the rest)
$PY ingest/_checks.py > logs/checks.log 2>&1 && log "gap check: clean" || log "gap check: issues (logs/checks.log)"

# ---- 3. build into staging
STAGE_DB="$ROOT/warehouse/brazil_macro.duckdb.staging"; STAGE_SITE="$ROOT/warehouse/portal.staging"
rm -rf "$STAGE_DB" "$STAGE_SITE"
log "build (staged)"
if BRAZIL_MACRO_DB="$STAGE_DB" $PY pipeline.py > logs/pipeline.log 2>&1 \
   && BRAZIL_MACRO_DB="$STAGE_DB" BRAZIL_MACRO_PORTAL="$STAGE_SITE" $PY portal.py > logs/portal.log 2>&1; then
  # ---- 4. sanity gate: the catalogue must not shrink by more than 10%
  OK=$($PY - "$ROOT/warehouse/portal/data/meta.json" "$STAGE_SITE/data/meta.json" <<'EOF'
import json, sys, pathlib
old, new = (pathlib.Path(p) for p in sys.argv[1:3])
n = json.loads(new.read_text())
o = json.loads(old.read_text()) if old.exists() else {"n_series": 0, "n_obs": 0}
ok = n["n_series"] >= 0.9 * o["n_series"] and n["n_obs"] >= 0.9 * o["n_obs"]
print(f"{'ok' if ok else 'shrink'} series {o['n_series']}->{n['n_series']} obs {o['n_obs']}->{n['n_obs']}")
EOF
)
  log "sanity: $OK"
  if [[ "$OK" == ok* ]]; then
    # ---- 5. swap (each mv is atomic)
    mv -f "$STAGE_DB" "$ROOT/warehouse/brazil_macro.duckdb"
    rm -rf "$ROOT/warehouse/portal.old"; [ -d "$ROOT/warehouse/portal" ] && mv "$ROOT/warehouse/portal" "$ROOT/warehouse/portal.old"
    mv "$STAGE_SITE" "$ROOT/warehouse/portal" && rm -rf "$ROOT/warehouse/portal.old"
    STATUS=published; log "published"
  else STATUS=blocked_by_sanity_gate; log "NOT published: $OK (live site unchanged)"; fi
else STATUS=build_failed; log "BUILD FAILED (live site unchanged; logs/pipeline.log, logs/portal.log)"; fi

# ---- 6. run summary
$PY - "$MODE" "$START" "$STATUS" "${FAILED[@]:-}" > logs/last_run.json <<'EOF'
import json, sys, datetime
mode, start, status, *failed = sys.argv[1:]
print(json.dumps({"mode": mode, "started": start, "finished": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "status": status, "failed_adapters": [f for f in failed if f]}, indent=1))
EOF
log "done: $STATUS; failed adapters: ${FAILED[*]:-none}"
[ "$STATUS" = published ]
