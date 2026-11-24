#!/bin/sh
assets="$HOME/.local/share/agentlinux-xp"
. "$assets/session-env.sh"
if [ -f "$assets/explorer-newmenu.so" ]; then
    export LD_PRELOAD="$assets/explorer-newmenu.so${LD_PRELOAD:+:$LD_PRELOAD}"
fi
export GTK_MODULES="${GTK_MODULES:+$GTK_MODULES:}$assets/explorer-toolbar.so"
case "${LANGUAGE:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in
    zh_CN*|zh:*)
        export G_RESOURCE_OVERLAYS="/uk/oddmatics/wintc/explorer=$assets/explorer-zh${G_RESOURCE_OVERLAYS:+:$G_RESOURCE_OVERLAYS}" ;;
esac
export LD_PRELOAD="$assets/mount-compat.so${LD_PRELOAD:+:$LD_PRELOAD}"
if [ -f "${XDG_CONFIG_HOME:-$HOME/.config}/agentlinux-xp/explorer-single-click" ]; then
    export AGENTLINUX_EXPLORER_SINGLE_CLICK=1
fi
if [ -f "$assets/explorer-lib/libwintc-comctl.so.1" ]; then
    export LD_LIBRARY_PATH="$assets/explorer-lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
exec /usr/bin/explorer "$@"
