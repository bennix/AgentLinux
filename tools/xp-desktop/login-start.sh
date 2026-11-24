#!/bin/sh
set -eu
assets="$HOME/.local/share/agentlinux-xp"
# UKUI starts its required panel and window manager before the XP replacements.
for attempt in $(seq 1 60); do
    if xdotool search --onlyvisible --name '^UKUI Panel$' >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
saved="$HOME/.config/agentlinux-xp/accesskeys"
if [ -r "$saved" ]; then
    "$assets/accesskeys" "$(cat "$saved")" || echo "Could not restore accessibility settings" >&2
fi
"$assets/run-shortcut" &
exec "$assets/shell-start.sh"
