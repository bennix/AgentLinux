#!/bin/sh
set -eu
name=${0##*/}
if [ "$name" = control ] || [ "$name" = control.exe ]; then
    name=$(printf '%s' "${1:-panel}" | LC_ALL=C tr '[:upper:]' '[:lower:]')
fi
case "$name" in
    explorer.exe) exec "$HOME/.local/share/agentlinux-xp/explorer-launch.sh" "$@" ;;
    notepad.exe) exec "$HOME/.local/share/agentlinux-xp/notepad" "$@" ;;
    taskmgr.exe) exec "$HOME/.local/share/agentlinux-xp/task-manager.sh" "$@" ;;
    cmd|cmd.exe) exec /usr/bin/x-terminal-emulator "$@" ;;
    calc|calc.exe) exec /usr/bin/mate-calc "$@" ;;
    access.cpl|accessibility) app=access ;;
    intl.cpl|international) exec "$HOME/.local/share/agentlinux-xp/control-panel.py" --language ;;
    appwiz.cpl) app=programs ;;
    panel) app=control ;;
    winver) exec "$HOME/.local/share/agentlinux-xp/system-properties.py" --version ;;
    timedate.cpl,,[0-2]) exec "$HOME/.local/share/agentlinux-xp/date-properties.py" "${name##*,}" ;;
    timedate.cpl|date/time) app=datetime ;;
    nusrmgr.cpl|userpasswords) app=userinfo ;;
    folders) exec "$HOME/.local/share/agentlinux-xp/control-panel.py" --folder-options ;;
    fonts) app=fonts ;;
    desk.cpl|desktop|desk.cpl,,[0-4])
        case "$name:${1:-}" in
            desk.cpl,,[0-4]:*) export AGENTLINUX_DISPLAY_PAGE=${name##*,} ;;
            *:--desktop) export AGENTLINUX_DISPLAY_PAGE=1 ;;
            *:--settings) export AGENTLINUX_DISPLAY_PAGE=4 ;;
        esac
        if [ -n "${AGENTLINUX_DISPLAY_PAGE:-}" ] &&
           gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
               --method org.freedesktop.DBus.NameHasOwner uk.co.oddmatics.wintc.cpl-desk | grep -Fq true; then
            gapplication action uk.co.oddmatics.wintc.cpl-desk select-page "$AGENTLINUX_DISPLAY_PAGE" && exit 0
        fi
        export GTK_MODULES="$HOME/.local/share/agentlinux-xp/display-language.so${GTK_MODULES:+:$GTK_MODULES}"
        exec /usr/bin/desk.cpl ;;
    admintools) app=admin ;;
    diskmgmt.msc) exec gtk-launch org.gnome.DiskUtility ;;
    fsmgmt.msc) app=shares ;;
    devmgmt.msc) exec "$HOME/.local/share/agentlinux-xp/system-properties.py" --devices ;;
    sysdm.cpl,,1) exec "$HOME/.local/share/agentlinux-xp/system-properties.py" --computer-name ;;
    sysdm.cpl,,3) exec "$HOME/.local/share/agentlinux-xp/system-properties.py" --advanced ;;
    sysdm.cpl,,2) exec "$HOME/.local/share/agentlinux-xp/system-properties.py" --hardware ;;
    sysdm.cpl|sysdm.cpl,,0|system) app=system ;;
    mmsys.cpl) app=audio ;;
    mmsys.cpl,,[0-4])
        exec "$HOME/.local/share/agentlinux-xp/sound-properties.py" "${name##*,}" ;;
    powercfg.cpl) app=power ;;
    main.cpl,,[0-3]|main.cpl,@0,[0-3])
        exec "$HOME/.local/share/agentlinux-xp/input-properties.py" mouse "${name##*,}" ;;
    main.cpl,,4|main.cpl,@0,4) exec "$HOME/.local/share/agentlinux-xp/input-properties.py" mouse --hardware ;;
    main.cpl,@1,1) exec "$HOME/.local/share/agentlinux-xp/input-properties.py" keyboard --hardware ;;
    main.cpl,@1|main.cpl,@1,0) app=keyboard ;;
    main.cpl|main.cpl,@0|mouse) app=mouse ;;
    keyboard) app=keyboard ;;
    ncpa.cpl|netconnections) app=connections ;;
    printers) app=printers ;;
    *) exit 2 ;;
esac
exec gtk-launch "agentlinux-xp-$app"
