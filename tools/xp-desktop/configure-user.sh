#!/bin/sh
set -eu
assets="$HOME/.local/share/agentlinux-xp"
apps="$HOME/.local/share/applications"
menu="$HOME/.config/wintc/start-menu"
desktop=$(/usr/bin/python3 -c 'from gi.repository import GLib
print(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP) or "")')
mkdir -p "$apps" "$menu" "$desktop" "$HOME/.config/autostart"
if [ -x "$assets/peony-qt-desktop" ] && [ -x /usr/local/libexec/agentlinux-xp-desktop ] &&
   [ -r /usr/share/applications/agentlinux-xp-desktop.desktop ]; then
    # UKUI resolves required components from system desktop entries.
    cat > "$HOME/.config/autostart/peony-desktop.desktop" <<'ENTRY'
[Desktop Entry]
Type=Application
Name=Peony Desktop
Hidden=true
ENTRY
    gsettings set org.ukui.session.required-components filemanager agentlinux-xp-desktop
fi
chmod +x "$assets/lid-backlight.py"
cat > "$HOME/.config/autostart/agentlinux-xp-lid.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Internal display power
Name[zh_CN]=内屏电源管理
Exec="$assets/lid-backlight.py"
ENTRY
python3 - <<'PY'
from gi.repository import GLib
from pathlib import Path

path = Path(GLib.get_user_config_dir()) / "gtk-3.0/settings.ini"
path.parent.mkdir(parents=True, exist_ok=True)
settings = GLib.KeyFile()
if path.exists():
    settings.load_from_file(str(path), GLib.KeyFileFlags.KEEP_COMMENTS | GLib.KeyFileFlags.KEEP_TRANSLATIONS)
settings.set_string("Settings", "gtk-icon-theme-name", "luna")
settings.save_to_file(str(path))
PY
if [ -r "$assets/college-bliss.svg" ]; then
    mkdir -p "$assets/screensaver"
    gdk-pixbuf-thumbnailer -s 1920 "$assets/college-bliss.svg" "$assets/screensaver/bliss.png"
    python3 - "$assets" <<'PY'
from pathlib import Path
import sys
from gi.repository import Gio, GLib

assets = Path(sys.argv[1])
defaults = {
    "org.ukui.screensaver-default": {
        "background-path": str(assets / "screensaver"),
        "text-is-center": False,
        "mytext": "AgentLinux",
        "show-rest-time": False,
    },
    "org.ukui.screensaver": {
        "background": str(Path("/usr/local/share/agentlinux-xp/greeter/lock-background.svg")
                          if Path("/usr/local/share/agentlinux-xp/greeter/lock-background.svg").is_file()
                          else assets / "college-bliss.svg"),
        "mode": "default-ukui-custom",
    },
}
for schema, values in defaults.items():
    settings = Gio.Settings.new(schema)
    for key, value in values.items():
        if settings.get_user_value(key) is None:
            signature = settings.get_default_value(key).get_type_string()
            settings.set_value(key, GLib.Variant(signature, value))
Gio.Settings.sync()
PY
fi
python3 "$assets/ime-font.py"
python3 "$assets/localize-explorer.py"
python3 "$assets/localize-start-menu.py"
cc -Wall -Werror -shared -fPIC "$assets/task-manager-run.c" $(pkg-config --cflags --libs gio-unix-2.0 gtk+-3.0) -o "$assets/task-manager-run.new"
mv "$assets/task-manager-run.new" "$assets/task-manager-run.so"
python3 "$assets/localize-task-manager.py"
chmod +x "$assets/task-manager.sh"
cat > "$apps/agentlinux-xp-taskmgr.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Task Manager
Name[zh_CN]=任务管理器
Exec=$assets/task-manager.sh
Icon=utilities-system-monitor
Categories=System;Monitor;
ENTRY
cp "$apps/agentlinux-xp-taskmgr.desktop" "$menu/"

chmod +x "$assets/explorer-launch.sh" "$assets/shell-start.sh" "$assets/control-panel.py"
cc -Wall -Werror -shared -fPIC "$assets/explorer-newmenu.c" $(pkg-config --cflags --libs gio-2.0 wintc-shellext gtk+-3.0) -ldl -o "$assets/explorer-newmenu.new"
mv "$assets/explorer-newmenu.new" "$assets/explorer-newmenu.so"
cc -Wall -Werror -shared -fPIC "$assets/explorer-toolbar.c" $(pkg-config --cflags --libs gtk+-3.0) -o "$assets/explorer-toolbar.new"
mv "$assets/explorer-toolbar.new" "$assets/explorer-toolbar.so"
cc -Wall -Werror -shared -fPIC "$assets/clock-entry.c" $(pkg-config --cflags --libs gtk+-3.0 gio-unix-2.0) -o "$assets/clock-entry.new"
mv "$assets/clock-entry.new" "$assets/clock-entry.so"
chmod +x "$assets/control-command.sh" "$assets/taskbar.sh"
chmod +x "$assets/menu-open.sh"
mkdir -p "$assets/menu-commands"
chmod +x "$assets/session-dialog.py"
ln -sfn "$assets/session-dialog.py" "$assets/menu-commands/wintc-exitwin"
ln -sfn ../printers.py "$assets/menu-commands/system-config-printer"
ln -sfn "$assets/menu-open.sh" "$assets/menu-commands/exo-open"
ln -sfn "$assets/control-panel.py" "$assets/menu-commands/xfce4-settings-manager"
mkdir -p "$HOME/.local/bin"
cc -Wall -Werror -shared -fPIC "$assets/run-network.c" $(pkg-config --cflags --libs gio-2.0) -ldl -o "$assets/run-network.new"
mv "$assets/run-network.new" "$assets/run-network.so"
cc -Wall -Werror -shared -fPIC "$assets/display-language.c" $(pkg-config --cflags --libs gtk+-3.0 wintc-registry) -o "$assets/display-language.new"
mv "$assets/display-language.new" "$assets/display-language.so"
sed "s|^Exec=desk.cpl$|Exec=$HOME/.local/bin/desk.cpl|" /usr/share/applications/uk.co.oddmatics.wintc.cpl-desk.desktop > "$apps/uk.co.oddmatics.wintc.cpl-desk.desktop"
chmod +x "$assets/run-dialog.sh"
ln -sfn "$assets/run-dialog.sh" "$assets/menu-commands/run"
cat > "$apps/agentlinux-xp-run.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Run
Name[zh_CN]=运行
Exec=$assets/run-dialog.sh
NoDisplay=true
ENTRY
if [ ! -e "$HOME/.local/bin/taskmgr" ] && [ ! -L "$HOME/.local/bin/taskmgr" ]; then
    ln -s "$assets/task-manager.sh" "$HOME/.local/bin/taskmgr"
fi
for name in control control.exe calc calc.exe explorer.exe notepad.exe taskmgr.exe winver fsmgmt.msc diskmgmt.msc devmgmt.msc sysdm.cpl mmsys.cpl powercfg.cpl main.cpl ncpa.cpl timedate.cpl nusrmgr.cpl desk.cpl appwiz.cpl access.cpl intl.cpl; do
    target="$HOME/.local/bin/$name"
    if [ ! -e "$target" ] && [ ! -L "$target" ]; then
        ln -s "$assets/control-command.sh" "$target"
    fi
done
line='. "$HOME/.local/share/agentlinux-xp/session-env.sh"'
grep -qxF "$line" "$HOME/.xsessionrc" 2>/dev/null || printf '\n%s\n' "$line" >> "$HOME/.xsessionrc"
chmod +x "$assets/login-start.sh"
startup='case "${XDG_SESSION_DESKTOP:-}" in ukui|UKUI) "$HOME/.local/share/agentlinux-xp/login-start.sh" >>"$HOME/.local/share/agentlinux-xp/login-start.log" 2>&1 & ;; esac'
grep -qxF "$startup" "$HOME/.xsessionrc" || printf '%s\n' "$startup" >> "$HOME/.xsessionrc"
sh "$assets/install-panel-entries.sh"
cc -Wall -Werror "$assets/accesskeys.c" -lX11 -o "$assets/accesskeys.new"
mv "$assets/accesskeys.new" "$assets/accesskeys"
chmod +x "$assets/network-places.py" "$assets/connections.py" "$assets/programs.py" "$assets/printers.py" "$assets/accessibility.py" "$assets/fonts.py" "$assets/user-accounts.py" "$assets/date-properties.py" "$assets/power-properties.py" "$assets/system-properties.py" "$assets/input-properties.py" "$assets/sound-properties.py"
chmod +x "$assets/add-printer.py" "$assets/wireless.py"
cp "$apps/agentlinux-xp-wifi.desktop" "$menu/"
install_desktop_shortcut() {
    target="$desktop/$1.desktop"
    stored="${XDG_CONFIG_HOME:-$HOME/.config}/agentlinux-xp/hidden-shortcuts/$1.desktop"
    if [ ! -e "$target" ]; then
        if [ -f "$desktop/.$1.desktop" ] && [ ! -e "$stored" ]; then
            mkdir -p "$(dirname "$stored")"
            mv "$desktop/.$1.desktop" "$stored"
        fi
        if [ -f "$stored" ]; then target="$stored"; fi
    fi
    install -m 755 "$apps/${2:-$1}.desktop" "$target"
    gio set "$target" metadata::trusted true || true
}
install_desktop_shortcut agentlinux-xp-wifi
cp "$apps/agentlinux-xp-add-printer.desktop" "$menu/"
# Peony uses the vendor metadata when the desktop filename matches a system entry.
for folder in "$desktop" "${XDG_CONFIG_HOME:-$HOME/.config}/agentlinux-xp/hidden-shortcuts"; do
    for prefix in "" "."; do
        previous="$folder/${prefix}explorer.desktop"
        renamed="$folder/${prefix}agentlinux-xp-explorer.desktop"
        if [ -f "$previous" ] && [ ! -e "$renamed" ] && grep -Fqx "Exec=$assets/explorer-launch.sh %F" "$previous"; then
            mv "$previous" "$renamed"
        fi
    done
done
install_desktop_shortcut agentlinux-xp-explorer explorer
cp "$apps/explorer.desktop" "$menu/explorer.desktop"
for app in agentlinux-xp-control agentlinux-xp-places; do
    install_desktop_shortcut "$app"
    cp "$apps/$app.desktop" "$menu/$app.desktop"
done
ln -sfn "$apps/agentlinux-xp-admin.desktop" "$menu/agentlinux-xp-admin.desktop"
mkdir -p "$menu/Accessories"
notepad="$assets/notepad"
if [ ! -x "$notepad" ]; then
    notepad=/usr/bin/wintc-notepad
    sed -i 's|^Exec=.*|Exec=/usr/bin/wintc-notepad %F|' "$apps/notepad.desktop"
fi
ln -sfn "$apps/notepad.desktop" "$menu/Accessories/notepad.desktop"
ln -sfn "$apps/explorer.desktop" "$menu/Accessories/explorer.desktop"
if [ ! -e "$HOME/.local/bin/notepad" ] || [ "$(readlink "$HOME/.local/bin/notepad")" = /usr/bin/wintc-notepad ]; then
    ln -sfn "$notepad" "$HOME/.local/bin/notepad"
fi
xdg-mime default explorer.desktop inode/directory
if [ -x /usr/bin/ubuntu-kylin-software-center ]; then
    xdg-mime default agentlinux-xp-deb.desktop application/vnd.debian.binary-package application/x-deb
fi
show_desktop_key='/xfwm4/custom/<Super>d'
if ! xfconf-query -c xfce4-keyboard-shortcuts -p "$show_desktop_key" >/dev/null 2>&1; then
    xfconf-query -c xfce4-keyboard-shortcuts -p "$show_desktop_key" -n -t string -s show_desktop_key
fi
cc -Wall -Werror "$assets/run-shortcut.c" -lX11 -o "$assets/run-shortcut.new"
mv "$assets/run-shortcut.new" "$assets/run-shortcut"
cat > "$HOME/.config/autostart/agentlinux-xp-run.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=AgentLinux XP Run Shortcut
Exec=$assets/run-shortcut
TryExec=$assets/run-shortcut
ENTRY
cat > "$HOME/.config/autostart/agentlinux-xp-shell.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=AgentLinux XP Desktop
Exec=$assets/shell-start.sh
OnlyShowIn=UKUI;
ENTRY
