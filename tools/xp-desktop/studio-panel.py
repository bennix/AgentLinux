#!/usr/bin/python3
"""AgentLinux Studio panels for the existing X11 desktop session."""
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import gi
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkX11, Gio, GLib, Gtk


def tr(zh, en):
    return zh if GLib.get_language_names()[0].startswith("zh") else en


def launch(app):
    try:
        app.launch([], None)
    except GLib.Error as error:
        dialog = Gtk.MessageDialog(transient_for=header, buttons=Gtk.ButtonsType.CLOSE,
                                   text=tr("无法打开应用", "Could not open the application"))
        dialog.format_secondary_text(app.get_display_name())
        dialog.connect("response", lambda widget, _: widget.destroy())
        dialog.show()
        print(error.message, flush=True)


def x11(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=1,
                            env={**os.environ, "LC_ALL": "C"})
    return result.stdout if result.returncode == 0 else ""


def activate_running(classes, executable_root=None):
    if not classes:
        return False
    try:
        pattern = "^(" + "|".join(re.escape(name) for name in classes) + ")$"
        matches = set(map(int, x11("xdotool", "search", "--class", pattern).split()))
        stack = x11("xprop", "-root", "_NET_CLIENT_LIST_STACKING")
        for window in reversed(re.findall(r"0x[0-9a-fA-F]+", stack)):
            if int(window, 16) not in matches:
                continue
            if executable_root:
                try:
                    pid = int(x11("xdotool", "getwindowpid", window))
                    executable = Path(f"/proc/{pid}/exe").readlink()
                except (OSError, ValueError):
                    continue
                if not executable.is_relative_to(executable_root):
                    continue
            if subprocess.run(["xdotool", "windowactivate", window],
                              stderr=subprocess.DEVNULL, timeout=1).returncode == 0:
                return True
    except (OSError, subprocess.SubprocessError):
        pass
    return False


def app_button(desktop, icon, label, classes=(), executable_root=None):
    button = Gtk.Button()
    button.set_tooltip_text(label)
    button.get_accessible().set_name(label)
    try:
        app = Gio.DesktopAppInfo.new(desktop)
    except TypeError:
        app = None
    image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
    image.set_pixel_size(24)
    button.set_name(icon)
    button.set_image(image)
    button.set_sensitive(app is not None)
    if app:
        def clicked(_):
            if not activate_running(classes, executable_root):
                launch(app)
        button.connect("clicked", clicked)
    return button


def keep_titles_visible(boundary):
    try:
        clients = x11("xprop", "-root", "_NET_CLIENT_LIST")
        windows = re.findall(r"0x[0-9a-fA-F]+", clients)
        if not windows:
            windows = x11("xdotool", "search", "--onlyvisible", "--name", ".").split()
        for xid in windows:
            metadata = x11("xprop", "-id", xid, "_NET_WM_WINDOW_TYPE", "_NET_WM_STATE",
                           "_NET_FRAME_EXTENTS", "WM_STATE")
            if any(flag in metadata for flag in ("_TYPE_DOCK", "_TYPE_DESKTOP", "_TYPE_NOTIFICATION",
                                                 "_STATE_FULLSCREEN", "_STATE_MAXIMIZED_VERT", "_STATE_HIDDEN")):
                continue
            if "WM_STATE(WM_STATE)" not in metadata:
                continue
            geometry = x11("xwininfo", "-id", xid)
            coordinates = re.findall(r"Absolute upper-left [XY]:\s+(-?\d+)", geometry)
            width = re.search(r"^\s*Width:\s+(\d+)", geometry, re.MULTILINE)
            if "IsViewable" not in geometry or len(coordinates) != 2 or width is None:
                continue
            x, y = map(int, coordinates)
            right = x + int(width[1])
            extents = re.search(r"_NET_FRAME_EXTENTS\(CARDINAL\) = (\d+), \d+, (\d+), \d+", metadata)
            if extents:
                x -= int(extents[1])
                y -= int(extents[2])
            if x < boundary.x + boundary.width and right > boundary.x and y < boundary.y + boundary.height:
                x11("xdotool", "windowmove", xid, "x", str(boundary.y + boundary.height))
    except (OSError, subprocess.SubprocessError):
        pass
    return GLib.SOURCE_REMOVE


def panel(name, box, height, bottom=False):
    window = Gtk.Window(title=name)
    window.set_wmclass("agentlinux-studio", "Agentlinux-studio")
    window.set_name("studio-dock" if bottom else "studio-bar")
    window.set_decorated(False)
    window.set_resizable(False)
    window.set_accept_focus(False)
    window.set_type_hint(Gdk.WindowTypeHint.DOCK)
    window.stick()
    if bottom and window.get_screen().is_composited():
        visual = window.get_screen().get_rgba_visual()
        if visual is not None:
            window.set_visual(visual)
            window.get_style_context().add_class("composited")
    window.add(box)
    display = window.get_display()

    def position(*_):
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if not monitor:
            return
        area = monitor.get_geometry()
        width = min(area.width, 352) if bottom else area.width
        left = area.x + (area.width - width) // 2
        gap = 12 if bottom else 0
        top = area.y + area.height - height - gap if bottom else area.y
        window.set_size_request(width, height)
        window.move(left, top)
        screen = window.get_screen()
        if (bottom and top + height + gap == screen.get_height()) or (not bottom and top == 0):
            strut = [0] * 12
            offset = 3 if bottom else 2
            strut[offset] = height + gap
            edge = 10 if bottom else 8
            strut[edge:edge + 2] = [left, left + width - 1]
            subprocess.run(["xprop", "-id", hex(window.get_window().get_xid()),
                            "-f", "_NET_WM_STRUT_PARTIAL", "32c", "-set", "_NET_WM_STRUT_PARTIAL",
                            ", ".join(map(str, strut))], check=False)
        if not bottom:
            area.height = height
            GLib.timeout_add(400, keep_titles_visible, area)

    window.connect("map", position)
    window.get_screen().connect("monitors-changed", position)
    window.show_all()
    return window


style = Gtk.CssProvider()
style.load_from_data(b"""
#studio-bar {
    background: linear-gradient(to bottom, #fbfcff, #ecf1fa);
    color: #182342;
    border-bottom: 1px solid #d3ddec;
}
#studio-dock {
    background: linear-gradient(to bottom, #f6f9ff, #dbe5f5);
    color: #182342;
    border: 1px solid #a7b9d7;
}
#studio-dock.composited {
    background: linear-gradient(to bottom, rgba(246, 249, 255, 0.96), rgba(219, 229, 245, 0.88));
    border-radius: 18px;
}
#studio-bar button, #studio-dock button {
    background: none; box-shadow: none; border: 0;
    border-radius: 9px; padding: 4px 10px;
}
#studio-bar button { color: #182342; font-weight: 600; }
#studio-bar button:hover { background: #dce6f8; }
#studio-dock button {
    padding: 9px; margin: 0 4px; color: white; border-radius: 12px;
    box-shadow: inset 0 1px rgba(255, 255, 255, 0.35), 0 2px 3px rgba(22, 39, 72, 0.3);
}
#studio-dock #folder-symbolic { background: linear-gradient(to bottom, #559ee8, #245aa6); }
#studio-dock #web-browser-symbolic { background: linear-gradient(to bottom, #28a5a2, #176477); }
#studio-dock #document-edit-symbolic { background: linear-gradient(to bottom, #9776d3, #5b408a); }
#studio-dock #x-office-document-symbolic { background: linear-gradient(to bottom, #4aa779, #246353); }
#studio-dock #utilities-terminal-symbolic { background: linear-gradient(to bottom, #607299, #303e59); }
#studio-dock button:hover, #studio-dock button:focus {
    box-shadow: inset 0 0 0 2px #ffffff, 0 2px 4px rgba(22, 39, 72, 0.35);
}
""")
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

bar = Gtk.Box(spacing=8, margin_start=10, margin_end=10)
applications = Gtk.MenuButton(label="AgentLinux")
menu = Gtk.Menu()
switch = Gtk.MenuItem(label=tr("切换到 XP 主题", "Switch to XP theme"))
switch.connect("activate", lambda _: subprocess.Popen(["/usr/local/bin/agentlinux-desktop-theme", "xp"]))
menu.append(switch)
menu.append(Gtk.SeparatorMenuItem())
for app in sorted(Gio.AppInfo.get_all(), key=lambda item: item.get_display_name().casefold()):
    if app.should_show():
        item = Gtk.MenuItem(label=app.get_display_name())
        item.connect("activate", lambda _, application=app: launch(application))
        menu.append(item)
menu.show_all()
applications.set_popup(menu)
bar.pack_start(applications, False, False, 0)
clock = Gtk.Label()
bar.pack_end(clock, False, False, 6)


def update_clock():
    clock.set_text(datetime.now().strftime("%H:%M"))
    return GLib.SOURCE_CONTINUE


update_clock()
GLib.timeout_add_seconds(10, update_clock)
settings = Gtk.MenuButton()
settings.set_image(Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.LARGE_TOOLBAR))
settings.set_tooltip_text(tr("系统设置", "System settings"))
settings.get_accessible().set_name(tr("系统设置", "System settings"))
settings_menu = Gtk.Menu()
for desktop, zh, en in [
    ("agentlinux-xp-control.desktop", "控制面板", "Control Panel"),
    ("agentlinux-xp-connections.desktop", "网络连接", "Network Connections"),
    ("agentlinux-xp-audio.desktop", "声音和音频设备", "Sounds and Audio Devices"),
    ("agentlinux-xp-power.desktop", "电源选项", "Power Options"),
    ("agentlinux-xp-printers.desktop", "打印机和传真", "Printers and Faxes"),
]:
    try:
        app = Gio.DesktopAppInfo.new(desktop)
    except TypeError:
        continue
    if app:
        item = Gtk.MenuItem(label=tr(zh, en))
        item.connect("activate", lambda _, application=app: launch(application))
        settings_menu.append(item)
settings_menu.show_all()
settings.set_popup(settings_menu)
bar.pack_end(settings, False, False, 0)
header = panel("AgentLinux Studio", bar, 34)

dock = Gtk.Box(spacing=5, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
for desktop, icon, zh, en, classes, executable in [
    ("explorer.desktop", "folder-symbolic", "资源管理器", "File Manager", ("explorer",), None),
    ("obscura-firefox.desktop", "web-browser-symbolic", "浏览器", "Browser", ("firefox", "obscura-firefox"), "/opt/obscura-firefox"),
    ("zcode.desktop", "document-edit-symbolic", "ZenCode", "ZenCode", ("zencode", "zcode"), None),
    ("genoffice.desktop", "x-office-document-symbolic", "ZenOffice", "ZenOffice", ("genoffice", "zenoffice"), None),
    ("mate-terminal.desktop", "utilities-terminal-symbolic", "终端", "Terminal", ("mate-terminal",), None),
]:
    dock.pack_start(app_button(desktop, icon, tr(zh, en), classes, executable), False, False, 0)
panel(tr("应用停靠栏", "Application Dock"), dock, 54, bottom=True)
Gtk.main()
