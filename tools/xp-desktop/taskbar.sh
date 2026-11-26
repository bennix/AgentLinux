#!/bin/sh
assets="$HOME/.local/share/agentlinux-xp"
. "$assets/session-env.sh"
case "${LC_ALL:-${LANGUAGE:-${LC_MESSAGES:-${LANG:-}}}}" in
    zh_CN*|zh:*) layout=taskbar-zh ;;
    *) layout=taskbar-en ;;
esac
export G_RESOURCE_OVERLAYS="/uk/oddmatics/wintc/taskband=$assets/$layout${G_RESOURCE_OVERLAYS:+:$G_RESOURCE_OVERLAYS}"
export GTK_MODULES="$assets/clock-entry.so${GTK_MODULES:+:$GTK_MODULES}"
export PATH="$assets/menu-commands:$PATH"
export LD_PRELOAD="$assets/start-actions.so:$assets/mount-compat.so${LD_PRELOAD:+:$LD_PRELOAD}"
exec /usr/bin/wintc-taskband
