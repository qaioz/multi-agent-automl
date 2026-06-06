#!/usr/bin/env bash
# stop-nag.sh — stop a running nag.sh, no matter who launched it.
set -uo pipefail

PIDFILE="${TMPDIR:-/tmp}/nag.pid"

if [ ! -f "$PIDFILE" ]; then
  echo "No nag running (no $PIDFILE). Trying pattern match as a fallback..."
  pkill -f "nag.sh" 2>/dev/null && echo "Killed stray nag.sh process(es)." || echo "Nothing to stop."
  exit 0
fi

PID="$(cat "$PIDFILE")"

pkill -P "$PID" 2>/dev/null || true   # kill children first (sleep/say/afplay)
if kill "$PID" 2>/dev/null; then
  echo "Sent stop to nag.sh (PID $PID)."
else
  echo "PID $PID not alive; cleaning up stale pidfile."
fi
rm -f "$PIDFILE"
