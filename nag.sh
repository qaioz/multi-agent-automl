#!/usr/bin/env bash
# nag.sh — repeatedly play a sound + speak a message until you stop it (Ctrl-C).
# Usage:   ./nag.sh "your message here"
#          ./nag.sh -i 10 "your message"      # custom interval (seconds) between repeats
#          ./nag.sh -s Glass "your message"   # custom system sound name
#          ./nag.sh -n 3 "your message"       # play 3 times then exit (0 = forever)

set -euo pipefail

INTERVAL=5
SOUND="Ping"
REPEAT=0   # 0 = repeat forever (until stopped); >0 = play that many times then exit

while getopts "i:s:n:h" opt; do
  case "$opt" in
    i) INTERVAL="$OPTARG" ;;
    s) SOUND="$OPTARG" ;;
    n) REPEAT="$OPTARG" ;;
    h)
      echo "Usage: $0 [-i interval_secs] [-s sound_name] [-n repeat_count] \"message\""
      echo "Sounds live in /System/Library/Sounds (e.g. Ping, Glass, Hero, Sosumi)."
      echo "-n 0 (default) repeats forever until stopped; -n 3 plays 3 times then exits."
      exit 0
      ;;
    *) echo "Try '$0 -h'"; exit 1 ;;
  esac
done
shift $((OPTIND - 1))

MESSAGE="${*:-Hey. This is your reminder.}"
SOUND_FILE="/System/Library/Sounds/${SOUND}.aiff"
PIDFILE="${TMPDIR:-/tmp}/nag.pid"

echo "$$" > "$PIDFILE"

if [ "$REPEAT" -gt 0 ]; then
  echo "Nagging with: \"$MESSAGE\"  (sound: $SOUND, ${REPEAT}x every ${INTERVAL}s)"
else
  echo "Nagging with: \"$MESSAGE\"  (sound: $SOUND, every ${INTERVAL}s, until stopped)"
fi
echo "PID $$ written to $PIDFILE"
echo "Stop with: ./stop-nag.sh   (or Ctrl-C if running in foreground)"

cleanup() {
  pkill -P "$$" 2>/dev/null || true   # kill any in-flight say/afplay/sleep child
  rm -f "$PIDFILE"
  echo; echo "Stopped."
  exit 0
}
trap cleanup INT TERM

count=0
while true; do
  [ -f "$SOUND_FILE" ] && afplay "$SOUND_FILE"
  say "$MESSAGE"
  count=$((count + 1))
  if [ "$REPEAT" -gt 0 ] && [ "$count" -ge "$REPEAT" ]; then
    break
  fi
  sleep "$INTERVAL"
done

rm -f "$PIDFILE"
