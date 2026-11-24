#!/bin/sh
set -eu
assets="$HOME/.local/share/agentlinux-xp"
saved="$HOME/.config/agentlinux-xp/accesskeys"
if [ -r "$saved" ]; then
    "$assets/accesskeys" "$(cat "$saved")" || echo "Could not restore accessibility settings" >&2
fi
"$assets/run-shortcut" &
exec "$assets/shell-start.sh" --login
