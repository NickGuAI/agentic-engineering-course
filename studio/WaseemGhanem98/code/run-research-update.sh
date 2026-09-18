#!/usr/bin/env bash
set -euo pipefail

agent_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_dir="$(cd -- "$agent_dir/.." && pwd)"
card="$workspace_dir/delegation-card.md"
dry_run=false
if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=true
  shift
fi
if (( $# > 1 )) || [[ ! "${1:-30}" =~ ^[1-9][0-9]{0,3}$ ]]; then
  echo "Usage: bash run-research-update.sh [--dry-run] [days: 1-9999]" >&2
  exit 2
fi
days="${1:-30}"
for input in "$agent_dir/research-update.md" "$card"; do
  if [[ ! -f "$input" || ! -r "$input" ]]; then
    echo "Missing readable input: $input" >&2
    exit 2
  fi
done

make_prompt() {
  cat "$agent_dir/research-update.md"
  printf '\n## Original delegation card\n\n'
  cat "$card"
  printf '\n## Run input\nToday (UTC): %s\nRecent window: %s days\n' "$(date -u +%F)" "$days"
}

if "$dry_run"; then
  make_prompt
  exit 0
fi
if ! command -v codex >/dev/null 2>&1; then
  echo "Codex CLI is required. Install it and sign in with your own account." >&2
  exit 127
fi

mkdir -p "$workspace_dir/outputs"
run_dir="$(mktemp -d "$workspace_dir/outputs/run-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
make_prompt > "$run_dir/prompt.md"
echo "Saving prompt, output, and execution trace to $run_dir" >&2
if codex --search --ask-for-approval never exec --sandbox read-only \
  --cd "$agent_dir" --json --output-last-message "$run_dir/output.md" - \
  < "$run_dir/prompt.md" > "$run_dir/trace.jsonl" 2> "$run_dir/stderr.log"; then
  if [[ ! -s "$run_dir/output.md" ]]; then
    printf 'failed (no report produced)\n' > "$run_dir/status.txt"
    echo "Codex produced no report; inspect $run_dir/trace.jsonl." >&2
    exit 1
  fi
  printf 'completed\n' > "$run_dir/status.txt"
  cat "$run_dir/output.md"
else
  result=$?
  printf 'failed (exit %s)\n' "$result" > "$run_dir/status.txt"
  echo "Agent execution failed; see $run_dir/stderr.log and trace.jsonl." >&2
  exit "$result"
fi
