#!/usr/bin/env bash
# Runs the Studio01 research-digest job with Claude Code as a bounded,
# non-interactive job. Tools are restricted to WebFetch (read the source
# pages) and Write (save the digest + log) — nothing else is allowed.
#
# Note: this must be run from a plain terminal, not from inside another
# active Claude Code session — a nested `claude` subprocess spawned from
# within a running session fails with a 401 (the OAuth token does not
# carry over to the child process). This run's actual output was produced
# by the outer interactive session directly for that reason; this script
# is the reproducible standalone form of the same job.

set -euo pipefail
cd "$(dirname "$0")/../../.."   # repo root

RUN_DATE="$(TZ=America/New_York date +%d-%m-%Y)"
OUT_DIR="studio/ceydat709/outputs"

claude -p "$(cat studio/ceydat709/code/run-prompt.txt)" \
  --allowedTools "WebFetch,Write" \
  --permission-mode acceptEdits \
  --output-format stream-json \
  --verbose \
  > "$OUT_DIR/run-trace-$RUN_DATE.jsonl"

echo "Trace written to $OUT_DIR/run-trace-$RUN_DATE.jsonl"
