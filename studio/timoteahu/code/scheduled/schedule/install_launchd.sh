#!/usr/bin/env bash
# Install or remove the weekly launchd job. Nothing runs until you call this yourself.
#   bash install_launchd.sh install [claude|codex]
#   bash install_launchd.sh uninstall
#   bash install_launchd.sh run-now      # trigger once, same environment as the schedule
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LABEL=com.timoteahu.research-digest
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
RUNNER="$(cd "$HERE/.." && pwd)/run_digest.py"
LOGDIR="$(cd "$HERE/../../.." && pwd)/work/scheduled"

case "${1:-}" in
  install)
    AGENT="${2:-claude}"
    command -v "$AGENT" >/dev/null || { echo "$AGENT not on PATH" >&2; exit 1; }
    mkdir -p "$LOGDIR" "$(dirname "$PLIST")"
    # launchd starts with a bare PATH; bake in the current one so the agent CLI is found.
    sed -e "s|__RUNNER__|$RUNNER|" -e "s|__AGENT__|$AGENT|" \
        -e "s|__PATH__|$PATH|" -e "s|__LOGDIR__|$LOGDIR|" \
        "$HERE/$LABEL.plist.template" > "$PLIST"
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "installed $PLIST (agent: $AGENT, Mondays 09:00)"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "removed $LABEL"
    ;;
  run-now)
    launchctl kickstart "gui/$(id -u)/$LABEL"
    ;;
  *)
    sed -n '2,5p' "$0"; exit 1
    ;;
esac
