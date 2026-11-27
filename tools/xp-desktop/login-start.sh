#!/bin/sh
set -eu
# The desktop starts before im-config initializes the X session environment.
export GTK_IM_MODULE="${GTK_IM_MODULE:-fcitx}" QT_IM_MODULE="${QT_IM_MODULE:-fcitx}"
export XMODIFIERS="${XMODIFIERS:-@im=fcitx}" SDL_IM_MODULE="${SDL_IM_MODULE:-fcitx}"
assets="$HOME/.local/share/agentlinux-xp"
saved="$HOME/.config/agentlinux-xp/accesskeys"
if [ -r "$saved" ]; then
    "$assets/accesskeys" "$(cat "$saved")" || echo "Could not restore accessibility settings" >&2
fi
"$assets/run-shortcut" &
exec "$assets/shell-start.sh" --login
