#!/bin/sh
set -eu
assets="$HOME/.local/share/agentlinux-xp"
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$apps"
cat > "$apps/agentlinux-xp-deb.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Install Debian Package
Name[zh_CN]=安装 Debian 软件包
Path=/usr/share/ubuntu-kylin-software-center
Exec=/usr/share/ubuntu-kylin-software-center/ubuntu-kylin-software-center.py %f
TryExec=/usr/share/ubuntu-kylin-software-center/ubuntu-kylin-software-center.py
MimeType=application/vnd.debian.binary-package;application/x-deb;
Icon=system-software-install
NoDisplay=true
Terminal=false
DESKTOP
cat > "$apps/agentlinux-xp-control.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Control Panel
Name[zh_CN]=控制面板
Exec=/usr/bin/python3 "$assets/control-panel.py"
Icon=/usr/share/icons/luna/res/32x32/control_panel.png
Categories=Settings;
ENTRY
while IFS='|' read -r key en zh icon; do
    case "$key" in
        keyboard|mouse) command="/usr/bin/python3 \"$assets/input-properties.py\" $key" ;;
        admin) command="/usr/bin/python3 \"$assets/control-panel.py\" --admin-tools" ;;
        devices) command="/usr/bin/python3 \"$assets/system-properties.py\" --devices" ;;
        system) command="/usr/bin/python3 \"$assets/system-properties.py\"" ;;
        programs) command="/usr/bin/python3 \"$assets/programs.py\"" ;;
        places) command="/usr/bin/python3 \"$assets/network-places.py\"" ;;
        shares) command="/usr/bin/python3 \"$assets/network-places.py\" --local-shares" ;;
        connections) command="/usr/bin/python3 \"$assets/connections.py\"" ;;
        printers) command="/usr/bin/python3 \"$assets/printers.py\"" ;;
        access) command="/usr/bin/python3 \"$assets/accessibility.py\"" ;;
        fonts) command="/usr/bin/python3 \"$assets/fonts.py\"" ;;
        userinfo) command="/usr/bin/python3 \"$assets/user-accounts.py\"" ;;
        datetime) command="/usr/bin/python3 \"$assets/date-properties.py\"" ;;
        power) command="/usr/bin/python3 \"$assets/power-properties.py\"" ;;
        audio) command="/usr/bin/python3 \"$assets/sound-properties.py\"" ;;
        *) command="/usr/bin/ukui-control-center -p $key" ;;
    esac
    cat > "$apps/agentlinux-xp-$key.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=$en
Name[zh_CN]=$zh
Exec=$command
Icon=$icon
Categories=Settings;
ENTRY
done <<'ITEMS'
mouse|Mouse|鼠标|input-mouse
keyboard|Keyboard|键盘|input-keyboard
admin|Administrative Tools|管理工具|preferences-system
devices|Device Manager|设备管理器|computer
system|System|系统|computer
audio|Sounds and Audio Devices|声音和音频设备|audio-card
datetime|Date and Time|日期和时间|appointment-new
power|Power Options|电源选项|battery
programs|Add or Remove Programs|添加或删除程序|system-software-install
shares|Shared Folders|共享文件夹|folder-publicshare
places|My Network Places|网上邻居|/usr/share/icons/luna/32x32/places/network-workgroup.png
connections|Network Connections|网络连接|preferences-system-network
printers|Printers and Faxes|打印机和传真|printer
access|Accessibility Options|辅助功能选项|preferences-desktop-accessibility
fonts|Fonts|字体|preferences-desktop-font
userinfo|User Accounts|用户帐户|preferences-desktop-personal
ITEMS
cat > "$apps/agentlinux-xp-search.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Search for Files and Folders
Name[zh_CN]=搜索文件和文件夹
Exec=/usr/bin/python3 "$assets/search-files.py"
Icon=system-search
NoDisplay=true
ENTRY
cat > "$apps/agentlinux-xp-wifi.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Wireless Network Connection
Name[zh_CN]=无线网络连接
Exec=/usr/bin/python3 "$assets/wireless.py"
Icon=/usr/share/icons/luna/32x32/devices/network-wireless.png
Categories=Settings;Network;
ENTRY
cat > "$apps/agentlinux-xp-add-printer.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Add Printer Wizard
Name[zh_CN]=添加打印机向导
Exec=/usr/bin/python3 "$assets/add-printer.py"
Icon=printer
Categories=Settings;HardwareSettings;
ENTRY
cat > "$apps/agentlinux-xp-taskmgr.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Task Manager
Name[zh_CN]=任务管理器
Exec="$assets/task-manager.sh"
Icon=utilities-system-monitor
Categories=System;Monitor;
ENTRY
cat > "$apps/agentlinux-xp-run.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Run
Name[zh_CN]=运行
Exec="$assets/run-dialog.sh"
Icon=system-run
Categories=System;
ENTRY
cat > "$apps/notepad.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Notepad
Name[zh_CN]=记事本
Exec="$assets/notepad" %F
Icon=notepad
Categories=Utility;TextEditor;GTK;
MimeType=text/plain;
ENTRY
accessories="${XDG_CONFIG_HOME:-$HOME/.config}/wintc/start-menu/Accessories"
mkdir -p "$accessories"
ln -sfn "$apps/agentlinux-xp-printers.desktop" "$(dirname "$accessories")/agentlinux-xp-printers.desktop"
for entry in zcode.desktop zenmux-agent.desktop; do
    launcher="/usr/share/applications/$entry"
    destination="$(dirname "$accessories")/$entry"
    if [ -f "$launcher" ] && [ ! -e "$destination" ] && [ ! -L "$destination" ]; then
        ln -s "$launcher" "$destination"
    fi
done
ln -sfn "$apps/notepad.desktop" "$accessories/notepad.desktop"
cat > "$apps/explorer.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Windows Explorer
Name[zh_CN]=资源管理器
Exec="$assets/explorer-launch.sh" %F
Icon=explorer
Categories=System;FileManager;
MimeType=inode/directory;
ENTRY
ln -sfn "$apps/explorer.desktop" "$accessories/explorer.desktop"
for utility in mate-calc gucharmap; do
    entry="/usr/share/applications/$utility.desktop"
    if [ -f "$entry" ]; then
        ln -sfn "$entry" "$accessories/$utility.desktop"
    fi
done
cat > "$apps/agentlinux-xp-computer.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=My Computer
Name[zh_CN]=我的电脑
Exec="$assets/menu-open.sh" --launch FileManager /
Icon=computer
Categories=System;FileManager;
ENTRY

# Seed the XP desktop once, after XDG has selected its localized directory.
desktop=$(/usr/bin/python3 -c 'from gi.repository import GLib
print(GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP) or "")')
settings="${XDG_CONFIG_HOME:-$HOME/.config}/agentlinux-xp"
if [ -n "$desktop" ] && [ "$desktop" != "$HOME" ] && [ ! -e "$settings/desktop-shortcuts-initialized" ]; then
    mkdir -p "$desktop" "$settings"
    for item in control places explorer wifi; do
        name="agentlinux-xp-$item.desktop"
        source="$apps/$name"
        if [ "$item" = explorer ]; then source="$apps/explorer.desktop"; fi
        if [ ! -e "$desktop/$name" ] && [ ! -L "$desktop/$name" ] &&
           [ ! -e "$desktop/.$name" ] && [ ! -e "$settings/hidden-shortcuts/$name" ]; then
            install -m 755 "$source" "$desktop/$name"
            gio set "$desktop/$name" metadata::trusted true 2>/dev/null || true
        fi
    done
    touch "$settings/desktop-shortcuts-initialized"
fi

# Add My Documents once for existing desktops as well as fresh accounts.
if [ -n "$desktop" ] && [ "$desktop" != "$HOME" ] && [ ! -e "$settings/documents-shortcut-initialized" ]; then
    mkdir -p "$desktop" "$settings"
    name=agentlinux-xp-documents.desktop
    if [ ! -e "$desktop/$name" ] && [ ! -L "$desktop/$name" ] &&
       [ ! -e "$desktop/.$name" ] && [ ! -e "$settings/hidden-shortcuts/$name" ]; then
        cat > "$apps/$name" <<ENTRY
[Desktop Entry]
Type=Application
Name=My Documents
Name[zh_CN]=我的文档
Exec="$assets/explorer-launch.sh" --my-documents
Icon=/usr/share/icons/luna/res/48x48/folder_documents.png
Categories=System;FileManager;
ENTRY
        install -m 755 "$apps/$name" "$desktop/$name"
        gio set "$desktop/$name" metadata::trusted true 2>/dev/null || true
    fi
    touch "$settings/documents-shortcut-initialized"
fi

# Register the generated launchers with GIO and the XP recent-documents menu.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$apps"
fi
