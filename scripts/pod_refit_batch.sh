#!/usr/bin/env bash
# Refit the variance ratio after the 2026-08-10 corrections, then verified self-stop.
#
#   nohup setsid bash /workspace/pod_refit_batch.sh > /workspace/refit_batch.log 2>&1 &
#
# WHY A REFIT. variance_ratio_v2.csv was fitted at N=31 with Social Norms treated as a seventh
# foundation. Two things changed:
#   - SmolLM2-1.7B is excluded by the discrimination threshold, so N=30 (LIMITATIONS 22)
#   - Social Norms is Clifford's designed NON-MORAL CONTROL, now labelled `is_control` in the
#     output so it can never be averaged into a foundation-level statistic (LIMITATIONS 5)
#
# Plus the two sensitivities that were named as debts and never run:
#   - scan-excluded, pre-specified at ANALYSIS_PLAN.md:192, never executed (LIMITATIONS 1)
#   - (1|family), because eight Qwens are not eight independent draws (F3)
#
# 3 runs x 7 levels x 2 exclusion settings x 2 residual specs = 84 fits.
#
# DELIBERATELY NOT RE-RUN, so this is a decision and not an oversight:
#   - SEED AUDIT (35 fits). Measures Monte-Carlo error from the C11 randomised seed. Ran at
#     N=31: spread 0.005-0.033, i.e. 0.8-2.2% of interval width, no verdict flips. Dropping one
#     model of 31 does not change what that measures.
#   - PERMUTATION NULL (700 fits, ~3h, and the dominant cost of the last session). Its job is
#     to calibrate the estimator: destroy the interaction and confirm R reports none. It
#     collapsed to 0.0006-0.0021 against an observed 0.34-1.08 -- a margin of two to three
#     orders of magnitude. One model in thirty cannot close that. Re-running it would roughly
#     nine-fold the bill to move a number that is already three orders of magnitude clear.
#   Both are recorded in FINDINGS.md as fitted at N=31, with this reasoning.

set -u   # NOT -e: one failing job must not cancel the rest. Each writes its own CSV.

export PATH=/workspace/venv-analysis/bin:$PATH
cd /workspace/mft || { echo "FATAL: /workspace/mft missing"; exit 1; }

V2=results/derived/analysis_long_v2.csv
echo "=== refit batch started $(date -u +%FT%TZ) ==="
echo "vCPU: $(nproc)"
git log --oneline -1
python -c "import bambi,pymc;print('bambi',bambi.__version__,'pymc',pymc.__version__)"

# Fail loudly and early if the data is not the corrected version. Running 84 fits against the
# wrong dataset would produce a full set of plausible numbers -- the failure mode that makes
# this project's whole argument.
python - <<'PY' || exit 1
import pandas as pd, sys
df = pd.read_csv("results/derived/analysis_long_v2.csv")
ok = df[df["excluded"].astype(str) != "True"]
n = ok["model"].nunique()
print(f"precheck: {n} models analysable, {len(ok)} usable rows")
if n != 30:
    print(f"FATAL: expected 30 models after exclusions, got {n}. Wrong dataset -- rebuild.")
    sys.exit(1)
if "family" not in df.columns:
    print("FATAL: no `family` column; --family-effect would fail")
    sys.exit(1)
print("precheck OK")
PY
echo

FILTER='Sampling|Progress|NUTS|jitter|Multiprocess|^\s*$'

# THE THREE JOBS RUN CONCURRENTLY, not in sequence. Each fit sets cores=chains=4, so one job
# saturates only 4 vCPU; on a 16-vCPU box three jobs use 12 and the wall clock drops from
# ~2h to ~40min. Since the pod is billed by the hour that is a direct saving, and the jobs are
# independent -- separate processes, separate output files, no shared state.
#
# Do NOT raise this to four-plus jobs without adding vCPU: oversubscribing cores makes each
# chain slower and the arithmetic stops working.
run_job() {
  local tag="$1"; shift
  echo "### START $tag  $(date -u +%TZ) ###"
  python -u scripts/analyse_variance_ratio.py --data "$V2" "$@" > "/workspace/${tag}.log" 2>&1
  echo "### DONE  $tag exit=$? $(date -u +%TZ) ###"
}

run_job primary                       &
run_job noscan  --exclude-scan        &
run_job family  --family-effect       &
wait
echo "all three jobs finished at $(date -u +%FT%TZ)"
echo

for t in primary noscan family; do
  echo "--- $t ---"
  grep -vE "$FILTER" "/workspace/${t}.log" | grep -E "R=|FIT FAILED|FATAL|exclude-scan" | tail -32
  echo
done

{
  echo "=== refit batch summary  ($(date -u +%FT%TZ)) ==="
  for f in variance_ratio_v2.csv variance_ratio_v2_noscan.csv variance_ratio_v2_family.csv; do
    p="results/derived/$f"
    if [ -e "$p" ]; then
      echo "  $f  rows=$(( $(wc -l < "$p") - 1 ))  bytes=$(stat -c%s "$p")"
    else
      echo "  $f  MISSING"
    fi
  done
  echo
  echo "--- R by foundation, all three runs ---"
  python - <<'PY'
import pandas as pd, pathlib
for f in ["variance_ratio_v2.csv","variance_ratio_v2_noscan.csv","variance_ratio_v2_family.csv"]:
    p = pathlib.Path("results/derived")/f
    if not p.exists():
        print(f"{f}: MISSING"); continue
    d = pd.read_csv(p)
    d = d[(d.exclusions.astype(str)=="True") & (d.residual=="method-specific")]
    print(f"\n{f}  (n_models={d.n_models.iloc[0] if len(d) else '?'})")
    for _, r in d.sort_values("R_median").iterrows():
        ctl = "  [CONTROL]" if r.get("is_control", False) else ""
        print(f"   {r.foundation:<14} R={r.R_median:.3f} "
              f"[{r['R_q2.5']:.3f}, {r['R_q97.5']:.3f}]  {r.verdict}"
              f"  rhat={r.max_rhat:.3f}{ctl}")
PY
} > /workspace/refit_summary.txt 2>&1
cat /workspace/refit_summary.txt

# ---------------------------------------------------------------------------------------
# DO NOT STOP UNTIL THE RESULTS HAVE BEEN COLLECTED.
#
# This cost a run on 2026-08-10. The pod was created with `volumeInGb: 0` -- no persistent
# storage -- while this script still carried the stop-on-completion teardown inherited from
# `pod_analysis_batch.sh`, which was written for a pod backed by a network volume. RunPod wipes
# the CONTAINER disk on stop. The batch completed, wrote all three CSVs, stopped the pod, and
# destroyed its own output. 38 minutes of compute for nothing.
#
# The two safety properties are in tension and both are required:
#   - never leave a pod billing after the work is done (2026-08-08, ~1h44m leaked)
#   - never destroy results that have not been retrieved (2026-08-10, one run lost)
#
# Resolution: signal completion, then WAIT for the collector to acknowledge, with a hard
# timeout so a dropped connection still cannot leave the pod running indefinitely. The pod
# stops when results are safe, or when the timeout says nobody is coming.
touch /workspace/DONE
echo "=== DONE marker written $(date -u +%FT%TZ); waiting for /workspace/PULLED ==="
IDLE_TIMEOUT_S=${IDLE_TIMEOUT_S:-3600}
waited=0
while [ ! -f /workspace/PULLED ] && [ "$waited" -lt "$IDLE_TIMEOUT_S" ]; do
  sleep 20; waited=$((waited + 20))
done
if [ -f /workspace/PULLED ]; then
  echo "=== results acknowledged after ${waited}s; stopping ==="
else
  echo "=== TIMEOUT after ${waited}s with no acknowledgement; stopping anyway ==="
  echo "=== RESULTS WERE NOT COLLECTED — they are about to be destroyed with the disk ==="
fi

# ---------------------------------------------------------------------------------------
# Verified teardown. Check the EXIT CODE of the stop call, not merely that the binary
# exists — that distinction cost ~1h44m of idle billing on 2026-08-08.
# ---------------------------------------------------------------------------------------
POD_ID=$(tr '\0' '\n' < /proc/1/environ 2>/dev/null | grep '^RUNPOD_POD_ID='   | cut -d= -f2-)
API_KEY=$(tr '\0' '\n' < /proc/1/environ 2>/dev/null | grep '^RUNPOD_API_KEY=' | cut -d= -f2-)

stop_pod() {
  [ -n "${POD_ID:-}" ] || { echo "no RUNPOD_POD_ID"; return 1; }
  command -v runpodctl >/dev/null 2>&1 || { echo "runpodctl not installed"; return 1; }
  [ -n "${API_KEY:-}" ] && runpodctl config --apiKey "$API_KEY" >/dev/null 2>&1 || true
  runpodctl stop pod "$POD_ID"
}

sync; sleep 5
STOPPED=0
for attempt in 1 2 3; do
  echo "=== stopping pod ${POD_ID:-<unknown>} (attempt $attempt) at $(date -u +%FT%TZ) ==="
  if stop_pod; then STOPPED=1; break; fi
  echo "    attempt $attempt failed; retrying in 20s"
  sleep 20
done
if [ "$STOPPED" -eq 1 ]; then
  echo "=== pod stop succeeded at $(date -u +%FT%TZ) ==="
else
  { echo "POD STOP FAILED at $(date -u +%FT%TZ)"
    echo "POD_ID='${POD_ID:-}' api_key_present=$([ -n "${API_KEY:-}" ] && echo yes || echo no)"
    echo "THE POD IS STILL RUNNING AND BILLING. Stop it from the RunPod console."
  } | tee /workspace/POD_STOP_FAILED.txt
fi
