#!/bin/sh
desktop="$HOME/.local/share/agentlinux-xp/peony-qt-desktop"
[ -x "$desktop" ] || desktop=/usr/bin/peony-qt-desktop

"$desktop" -w -d &
child=$!
trap 'kill -TERM "$child" 2>/dev/null; wait "$child"; exit' HUP INT TERM

# The Live session can start Peony before the display backend is ready.
# Only retry our own process if it never mapped a desktop on this display.
for attempt in $(seq 1 60); do
    kill -0 "$child" 2>/dev/null || { wait "$child"; exit $?; }
    for window in $(xdotool search --onlyvisible --pid "$child" 2>/dev/null); do
        if xprop -id "$window" _NET_WM_WINDOW_TYPE 2>/dev/null | grep -qw _NET_WM_WINDOW_TYPE_DESKTOP; then
            wait "$child"
            exit $?
        fi
    done
    sleep 2
done
kill -TERM "$child" 2>/dev/null
wait "$child"
exec "$desktop" -w -d
