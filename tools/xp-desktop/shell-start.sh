#!/bin/sh
set -eu
. "$HOME/.local/share/agentlinux-xp/session-env.sh"

# Serialize concurrent autostart requests on this X display only.
display_name=$(printf '%s' "$DISPLAY" | tr -c 'A-Za-z0-9_-' '_')
exec 9>"${XDG_RUNTIME_DIR:?}/agentlinux-xp-shell-$display_name.lock"
flock -n 9 || exit 0

# Create per-user launchers before the control panel checks their desktop IDs.
if [ -x /usr/local/libexec/agentlinux-xp-panel-setup ]; then
    /usr/local/libexec/agentlinux-xp-panel-setup || echo "XP launcher setup failed" >&2
fi

/usr/bin/python3 "$HOME/.local/share/agentlinux-xp/cursor-settings.py" || true
/usr/bin/python3 "$HOME/.local/share/agentlinux-xp/display-mode.py" || true

xfwm_ready() {
    wm_window=$(xprop -root _NET_SUPPORTING_WM_CHECK | awk '/window id/ {print $NF}')
    [ -n "$wm_window" ] && xprop -id "$wm_window" _NET_WM_NAME 2>/dev/null | grep -q '"Xfwm4"'
}
if ! xfwm_ready; then
    xfwm4 --replace --compositor=on 9>&- &
    wm_pid=$!
    # Wait for Xfwm to take ownership before WinTC measures the desktop.
    for attempt in $(seq 1 60); do
        xfwm_ready && break
        kill -0 "$wm_pid" 2>/dev/null || break
        sleep 0.5
    done
fi
taskbar_visible() {
    xdotool search --onlyvisible --class '^Wintc-taskband$' >/dev/null 2>&1
}
if ! taskbar_visible; then
    # Keep the XP panel available if its primary process exits during login.
    (
        delay=1
        while :; do
            started=$(date +%s)
            "$HOME/.local/share/agentlinux-xp/taskbar.sh" || true
            # X closes at logout. A second instance may also own the panel.
            xprop -root _NET_CLIENT_LIST >/dev/null 2>&1 || exit 0
            taskbar_visible && exit 0
            if [ "$(($(date +%s) - started))" -ge 30 ]; then delay=1; fi
            sleep "$delay"
            if [ "$delay" -lt 16 ]; then delay=$((delay * 2)); fi
        done
    ) 9>&- &
fi
# Start the mixer with the XP shell even when UKUI skips its autostart entry.
# The applet enforces one instance and the launcher waits for panel geometry.
if [ -x /usr/local/libexec/agentlinux-volume-applet ]; then
    /usr/local/libexec/agentlinux-volume-applet 9>&- &
fi
# On slow Live boots the replacement panel can take longer than seven seconds.
# Wait for its mapped window before hiding the session's required UKUI panel.
# Either panel can be mapped again while the session manager finishes startup.
# Recheck on window-list changes, including the initial value reported by xprop.
(
    xprop -spy -root _NET_CLIENT_LIST | while IFS= read -r event; do
        if taskbar_visible; then
            xdotool search --onlyvisible --name '^UKUI Panel$' windowunmap %@ || true
        fi
    done
) 9>&- &
# Xfwm creates its custom shortcut table on first startup.
shortcut='/xfwm4/custom/<Super>d'
settings="${XDG_CONFIG_HOME:-$HOME/.config}/agentlinux-xp"
if [ ! -e "$settings/show-desktop-key-initialized" ] &&
   xfconf-query -c xfce4-keyboard-shortcuts -p /xfwm4/custom/override >/dev/null 2>&1; then
    if xfconf-query -c xfce4-keyboard-shortcuts -p "$shortcut" >/dev/null 2>&1 ||
       xfconf-query -c xfce4-keyboard-shortcuts -p "$shortcut" -n -t string -s show_desktop_key; then
        mkdir -p "$settings" && touch "$settings/show-desktop-key-initialized"
    fi
fi
wait
