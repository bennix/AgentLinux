#!/bin/sh
if [ "$#" -ge 3 ] && [ "$1" = --launch ] && [ "$2" = FileManager ]; then
    shift 2
    if [ "$#" -eq 1 ] && [ "$1" = / ]; then
        # WinTC sends / for the My Computer start-menu item.
        set -- "::{170f6110-d099-4fca-9307-fc1dc43eb71b}"
    fi
    # The taskbar sends one directory without quoting spaces.
    if [ "$#" -gt 1 ] && [ -d "$*" ]; then
        set -- "$*"
    fi
    exec "$HOME/.local/share/agentlinux-xp/explorer-launch.sh" "$@"
fi
exec /usr/bin/exo-open "$@"
