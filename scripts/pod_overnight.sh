#!/usr/bin/env bash
# Overnight v2 collection. Runs detached, survives SSH drops, stops the pod when finished.
#
#   nohup setsid bash /workspace/pod_overnight.sh > /workspace/overnight.log 2>&1 &
#
# WHY IT SELF-TERMINATES: RunPod bills while idle. If the run finishes at 03:00 and nobody
# is awake until 09:00, that is six hours of a GPU doing nothing. `runpodctl stop pod` at the
# end caps that at zero. Results live on /workspace (the network volume), which SURVIVES the
# stop — only the container disk is wiped — so nothing is lost by stopping.
#
# WHY setsid AND nohup: nohup alone detaches from the terminal but the process stays in the
# SSH session's process group, so some sshd configurations still signal it on disconnect.
# setsid puts it in a new session entirely. A network blip must not kill a 3-hour run.

set -u   # NOT -e: a single model failing must not abort the roster. Checkpointing means a
         # rerun skips completed models, so partial progress is always kept.

cd /workspace/mft
source /workspace/env.sh

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
echo "=== v2 overnight run started $STAMP ==="
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "roster: $(grep -c '^  - id:' config/models.yaml) entries"
echo

# ---------------------------------------------------------------------------------------
# 1. The roster. --purge-weights deletes each model after scoring it: the runnable subset is
#    ~291 GiB against a 200 GB volume, so they cannot all be resident.
# ---------------------------------------------------------------------------------------
python -u scripts/run_experiment.py --all --harness v2 --cloze --suffix _v2 --purge-weights
RC=$?
echo
echo "=== run_experiment exit=$RC ==="

# ---------------------------------------------------------------------------------------
# 2. Inventory. Written to its own file so the morning check is one `cat`, not log archaeology.
# ---------------------------------------------------------------------------------------
{
  echo "=== v2 collection summary  ($(date -u +%FT%TZ)) ==="
  echo "run_experiment exit code: $RC"
  echo
  echo "CSVs written:"
  ls -1 results/raw/*_v2.csv 2>/dev/null | wc -l
  echo
  printf '%-46s %8s %8s\n' MODEL ROWS BYTES
  for f in results/raw/*_v2.csv; do
    [ -e "$f" ] || continue
    printf '%-46s %8s %8s\n' "$(basename "$f" _v2.csv)" "$(($(wc -l < "$f") - 1))" "$(stat -c%s "$f")"
  done
  echo
  echo "models SKIPPED by the memory planner (expected on a 32 GiB card):"
  grep -E "WILL NOT FIT" /workspace/overnight.log | sed 's/^/  /' | head -20
} > /workspace/v2_summary.txt 2>&1

cat /workspace/v2_summary.txt

# ---------------------------------------------------------------------------------------
# 3. Stop the pod. Guarded: if RUNPOD_POD_ID cannot be read we must NOT silently keep
#    running, so say so loudly in the log — that is the case where money leaks.
# ---------------------------------------------------------------------------------------
POD_ID=$(tr '\0' '\n' < /proc/1/environ 2>/dev/null | grep '^RUNPOD_POD_ID=' | cut -d= -f2-)
echo
if [ -n "${POD_ID:-}" ] && command -v runpodctl >/dev/null 2>&1; then
  echo "=== stopping pod $POD_ID at $(date -u +%FT%TZ) ==="
  sync
  sleep 5
  runpodctl stop pod "$POD_ID"
else
  echo "!!! COULD NOT STOP POD — RUNPOD_POD_ID='${POD_ID:-}' runpodctl=$(command -v runpodctl || echo missing)"
  echo "!!! THE POD IS STILL BILLING. Stop it from the RunPod console."
fi
