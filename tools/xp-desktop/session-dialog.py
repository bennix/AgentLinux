#!/usr/bin/python3
import os
import subprocess
import sys
from ctypes.util import find_library
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

user = "--user-options" in sys.argv
zh = os.getenv("LANGUAGE", os.getenv("LANG", "")).startswith("zh")
translations = {"Turn off computer": "关闭计算机", "Log Off Windows": "注销 AgentLinux",
                "Stand By": "待机", "Turn Off": "关闭", "Restart": "重新启动",
                "Switch User": "切换用户", "Log Off": "注销", "Cancel": "取消"}
prefix = "/uk/oddmatics/wintc/msgina/"
library = Path("/usr/lib/x86_64-linux-gnu") / find_library("wintc-msgina")
def resource(name):
    return subprocess.check_output(["gresource", "extract", str(library), prefix + name])
builder = Gtk.Builder.new_from_string(resource("usropts.ui" if user else "pwropts.ui").decode(), -1)
style = Gtk.CssProvider()
style.load_from_data(resource("exitwnd.css"))
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style, Gtk.STYLE_PROVIDER_PRIORITY_FALLBACK)
emblem = Path(__file__).resolve().with_name("college-emblem.png")
if emblem.is_file():
    branding = Gtk.CssProvider()
    branding.load_from_data((
        '.wintc-exitwnd box.title { background-image: url("' + emblem.as_uri() + '"); '
        'background-size: 28px 28px; background-position: 98% 50%; min-height: 32px; }'
    ).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), branding, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
window = Gtk.Window()
window.set_title(("注销" if user else "关闭计算机") if zh else ("Log Off" if user else "Turn off computer"))
window.set_decorated(False)
window.set_resizable(False)
window.set_position(Gtk.WindowPosition.CENTER)
window.get_style_context().add_class("wintc-exitwnd")
window.add(builder.get_object("main-box"))
window.connect("destroy", Gtk.main_quit)
window.connect("key-press-event", lambda _, event: window.destroy() if event.keyval == Gdk.KEY_Escape else False)
for widget in builder.get_objects():
    if isinstance(widget, Gtk.Label) and zh:
        widget.set_text(translations.get(widget.get_text(), widget.get_text()))
    elif isinstance(widget, Gtk.Label) and widget.get_text() == "Log Off Windows":
        widget.set_text("Log Off AgentLinux")

iface = "org.gnome.SessionManager"
path = "/org/gnome/SessionManager"
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
actions = {"switch-user": ("canSwitch", "switchUser"), "log-off": ("canLogout", "logout")} if user else {
    "stand-by": ("canSuspend", "suspend"), "turn-off": ("canPowerOff", "powerOff"), "restart": ("canReboot", "reboot")}
def invoke(_, method):
    msg = Gio.DBusMessage.new_method_call(iface, path, iface, method)
    msg.set_flags(Gio.DBusMessageFlags.NO_REPLY_EXPECTED)
    bus.send_message(msg, Gio.DBusSendMessageFlags.NONE)
    bus.flush_sync(None)
    window.destroy()

for name, (check, method) in actions.items():
    button = builder.get_object("button-" + name)
    if zh:
        button.set_label(translations.get(button.get_label(), button.get_label()))
    try:
        enabled, = bus.call_sync(iface, path, iface, check, None, GLib.VariantType.new("(b)"), Gio.DBusCallFlags.NONE, 1000, None).unpack()
    except GLib.Error:
        enabled = False
    button.set_sensitive(enabled)
    button.connect("clicked", invoke, method)
cancel = builder.get_object("button-cancel")
if zh:
    cancel.set_label("取消")
cancel.connect("clicked", lambda _: window.destroy())
window.show_all()
cancel.grab_focus()
Gtk.main()
