#!/bin/sh
set -eu
assets="$HOME/.local/share/agentlinux-xp"
preference="${XDG_CONFIG_HOME:-$HOME/.config}/agentlinux-xp/desktop-theme"

theme() {
    if [ "$(cat "$preference" 2>/dev/null || true)" = studio ]; then
        printf studio
    else
        printf xp
    fi
}

child=
trap '[ -z "$child" ] || kill "$child" 2>/dev/null || true' EXIT
trap 'exit 0' HUP INT TERM
while :; do
    selected=$(theme)
    /usr/bin/python3 "$assets/window-appearance.py" "$selected" ||
        echo "Could not apply desktop window appearance: $selected" >&2
    case "$selected" in
        studio) GTK_THEME=Adwaita QT_STYLE_OVERRIDE=Fusion /usr/bin/python3 "$assets/studio-panel.py" & ;;
        xp) "$assets/taskbar.sh" & ;;
    esac
    child=$!
    while kill -0 "$child" 2>/dev/null; do
        if [ "$(theme)" != "$selected" ]; then
            kill "$child" 2>/dev/null || true
            wait "$child" || true
            child=
            break
        fi
        sleep 0.5
    done
    if [ -n "$child" ]; then
        wait "$child" || true
        child=
        if [ "$selected" = studio ]; then
            # Leave a functional panel available if the theme cannot start.
            /usr/local/bin/agentlinux-desktop-theme xp
        else
            exit 1
        fi
    fi
done
