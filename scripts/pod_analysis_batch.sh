#!/usr/bin/env bash
# All Bayesian work in one pod session, then verified self-stop.
#
#   nohup setsid bash /workspace/pod_analysis_batch.sh > /workspace/analysis_batch.log 2>&1 &
#
# These are the only pod-bound steps left: bambi/pymc need a C++ toolchain and the Windows dev
# box has none (PyTensor falls back to pure Python, minutes per fit). Everything else in the
# analysis runs locally.

set -u   # NOT -e: one failing job must not cancel the rest. Each writes its own CSV.

export PATH=/workspace/venv-analysis/bin:$PATH
cd /workspace/mft

V2=results/derived/analysis_long_v2.csv
echo "=== analysis batch started $(date -u +%FT%TZ) ==="
echo "vCPU: $(nproc)   data: $V2 ($(wc -l < $V2) rows)"
python -c "import bambi,pymc;print('bambi',bambi.__version__,'pymc',pymc.__version__)"
echo

# ---------------------------------------------------------------------------------------
# 1. PRIMARY: variance ratio on v2 at N=31. 7 foundations x 2 exclusion settings x 2
#    residual specs = 28 fits. Uses cores=chains, so it parallelises within each fit.
# ---------------------------------------------------------------------------------------
echo "### [1/3] primary variance ratio (v2, N=31) ###"
python -u scripts/analyse_variance_ratio.py --data "$V2" 2>&1 | grep -vE "Sampling|Progress|NUTS|jitter|Multiprocess|^\s*$"
echo "  exit=$?"
echo

# ---------------------------------------------------------------------------------------
# 2. SEED AUDIT: what did the randomised-hash seed (C11) actually cost? 7 foundations x 5
#    explicit seeds = 35 fits. Measures Monte-Carlo error rather than assuming it negligible.
#    A verdict that flips across seeds means the bands are unstable at this draw count.
# ---------------------------------------------------------------------------------------
echo "### [2/3] seed audit — 7 foundations x 5 seeds ###"
python -u scripts/analyse_variance_ratio.py --data "$V2" --seed-audit 5 2>&1 | grep -vE "Sampling|Progress|NUTS|jitter|Multiprocess|^\s*$"
echo "  exit=$?"
echo

# ---------------------------------------------------------------------------------------
# 3. F9 — the full-MCMC permutation null. 7 x 100 = 700 fits, each cores=1 with parallelism
#    across worker processes (nested pools deadlock; see the module docstring). Clears the
#    moment-estimator deviation from the write-up.
# ---------------------------------------------------------------------------------------
echo "### [3/3] MCMC permutation null — 700 fits ###"
python -u scripts/mcmc_permutation_null.py --data "$V2" --n-perm 100 --workers 24 2>&1 | tail -40
echo "  exit=$?"
echo

# ---------------------------------------------------------------------------------------
# Inventory, so the morning check is one `cat`.
# ---------------------------------------------------------------------------------------
{
  echo "=== analysis batch summary  ($(date -u +%FT%TZ)) ==="
  for f in variance_ratio_v2.csv variance_ratio_seed_audit.csv mcmc_permutation_null.csv; do
    p="results/derived/$f"
    if [ -e "$p" ]; then
      echo "  $f  rows=$(( $(wc -l < "$p") - 1 ))  bytes=$(stat -c%s "$p")"
    else
      echo "  $f  MISSING"
    fi
  done
} > /workspace/analysis_summary.txt 2>&1
cat /workspace/analysis_summary.txt

# ---------------------------------------------------------------------------------------
# Stop the pod. Same verified teardown as pod_overnight.sh: check the exit code of the stop
# call, not merely that the binary exists. That distinction cost ~1h44m of idle billing on
# 2026-08-08 and is recorded as C9.
# ---------------------------------------------------------------------------------------
POD_ID=$(tr '\0' '\n' < /proc/1/environ 2>/dev/null | grep '^RUNPOD_POD_ID='   | cut -d= -f2-)
API_KEY=$(tr '\0' '\n' < /proc/1/environ 2>/dev/null | grep '^RUNPOD_API_KEY=' | cut -d= -f2-)

stop_pod() {
  [ -n "${POD_ID:-}" ] || { echo "no RUNPOD_POD_ID"; return 1; }
  command -v runpodctl >/dev/null 2>&1 || { echo "runpodctl not installed"; return 1; }
  # `config` also tries to sync an SSH key and can print Unauthorized for that side-quest
  # while the key is fine, so its exit code is deliberately ignored. Only the stop matters.
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
