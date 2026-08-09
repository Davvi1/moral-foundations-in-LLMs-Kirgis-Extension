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
# 3. Stop the pod.
#
# THIS BLOCK FAILED IN PRODUCTION ON 2026-08-08 AND COST ~1h44m OF IDLE BILLING.
# The bug is worth stating precisely because it is a general one: the old guard tested
# `command -v runpodctl` — i.e. DOES THE BINARY EXIST — and then ran the stop command
# without ever checking whether it WORKED. runpodctl had never been configured with an
# API key on that pod, so the call failed with "API key not found", the `else` branch
# never fired because the binary did exist, and the script exited reporting success.
#
# A guard that checks a precondition instead of the outcome is not a guard. Check the
# exit code of the thing you actually care about.
#
# The API key is available the same way HF_TOKEN is: RunPod injects it into PID 1's
# environment, and sshd-spawned shells do not inherit it. See env.sh for the same trick.
# ---------------------------------------------------------------------------------------
POD_ID=$(tr '\0' '\n' < /proc/1/environ 2>/dev/null | grep '^RUNPOD_POD_ID='   | cut -d= -f2-)
API_KEY=$(tr '\0' '\n' < /proc/1/environ 2>/dev/null | grep '^RUNPOD_API_KEY=' | cut -d= -f2-)
echo

stop_pod() {
  [ -n "${POD_ID:-}" ] || { echo "no RUNPOD_POD_ID"; return 1; }
  command -v runpodctl >/dev/null 2>&1 || { echo "runpodctl not installed"; return 1; }
  # Configure if we have a key. `config` also tries to sync an SSH key to the RunPod cloud
  # and can print an "Unauthorized" error for that side-quest even when the key is fine —
  # so its exit code is NOT a reliable signal and is deliberately ignored here. The only
  # thing that matters is whether `stop pod` succeeds.
  if [ -n "${API_KEY:-}" ]; then
    runpodctl config --apiKey "$API_KEY" >/dev/null 2>&1 || true
  fi
  runpodctl stop pod "$POD_ID"
}

sync
sleep 5
STOPPED=0
for attempt in 1 2 3; do
  echo "=== stopping pod ${POD_ID:-<unknown>} (attempt $attempt) at $(date -u +%FT%TZ) ==="
  if stop_pod; then STOPPED=1; break; fi
  echo "    attempt $attempt failed; retrying in 20s"
  sleep 20
done

if [ "$STOPPED" -eq 1 ]; then
  echo "=== pod stop command succeeded at $(date -u +%FT%TZ) ==="
else
  # Leave a marker OUTSIDE the log too. A failure buried in 200k lines of vLLM progress
  # bars is a failure nobody sees — which is exactly how the 2026-08-08 leak went unnoticed
  # until a scheduled check-in happened to look.
  {
    echo "POD STOP FAILED at $(date -u +%FT%TZ)"
    echo "POD_ID='${POD_ID:-}'  api_key_present=$([ -n "${API_KEY:-}" ] && echo yes || echo no)"
    echo "THE POD IS STILL RUNNING AND BILLING. Stop it from the RunPod console."
  } | tee /workspace/POD_STOP_FAILED.txt
fi
