#!/bin/sh
assets="$HOME/.local/share/agentlinux-xp"
. "$assets/session-env.sh"
program=/usr/bin/taskmgr
export GTK_MODULES="$assets/task-manager-run.so${GTK_MODULES:+:$GTK_MODULES}"
case "${LANGUAGE:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in
    zh_CN*|zh:*)
        if [ -x "$assets/taskmgr-localized" ]; then program="$assets/taskmgr-localized"; fi
        export G_RESOURCE_OVERLAYS="/uk/oddmatics/wintc/taskmgr=$assets/taskmgr-zh${G_RESOURCE_OVERLAYS:+:$G_RESOURCE_OVERLAYS}" ;;
    *) export G_RESOURCE_OVERLAYS="/uk/oddmatics/wintc/taskmgr=$assets/taskmgr-en${G_RESOURCE_OVERLAYS:+:$G_RESOURCE_OVERLAYS}" ;;
esac
export LD_PRELOAD="$assets/mount-compat.so${LD_PRELOAD:+:$LD_PRELOAD}"
exec "$program" "$@"
