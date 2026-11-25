#!/usr/bin/python3
"""Apply the desktop lid-blank setting to the internal panel backlight."""
import fcntl
import os
from pathlib import Path
import signal
import sys

from gi.repository import Gio, GLib

def internal_backlights(drm, backlights):
    devices = {device.resolve() for device in backlights.glob("*")}
    panels = set()
    for connector_type in ("eDP", "LVDS", "DSI"):
        for connector in drm.glob(f"card*-{connector_type}-*"):
            for entry in (*connector.glob("*"), *connector.glob("backlight/*")):
                if entry.resolve() in devices and (entry / "brightness").is_file():
                    panels.add(entry.resolve())
    return sorted(panels)


panels = internal_backlights(Path("/sys/class/drm"), Path("/sys/class/backlight"))
if not panels or not os.environ.get("XDG_SESSION_ID"):
    sys.exit(0)
panel = panels[0]
runtime = Path(GLib.get_user_runtime_dir())
lock = (runtime / "agentlinux-lid.lock").open("a")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(0)

saved = runtime / "agentlinux-lid-brightness"
settings = Gio.Settings.new("org.ukui.power-manager")
bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
power = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None, "org.freedesktop.UPower",
                               "/org/freedesktop/UPower", "org.freedesktop.UPower", None)
session = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None, "org.freedesktop.login1",
                                 "/org/freedesktop/login1/session/self", "org.freedesktop.login1.Session", None)

def brightness(value):
    session.call_sync("SetBrightness", GLib.Variant("(ssu)", ("backlight", panel.name, value)),
                      Gio.DBusCallFlags.NONE, 2000, None)

def restore():
    if saved.exists():
        brightness(int(saved.read_text()))
        saved.unlink()

def update(*_):
    try:
        closed = power.get_cached_property("LidIsClosed")
        battery = power.get_cached_property("OnBattery")
        if closed is None or battery is None:
            return
        key = "button-lid-battery" if battery.unpack() else "button-lid-ac"
        if closed.unpack() and settings.get_string(key) == "blank":
            current = int((panel / "brightness").read_text())
            if current:
                if not saved.exists():
                    tmp = saved.with_suffix(".tmp")
                    tmp.write_text(str(current))
                    tmp.replace(saved)
                brightness(0)
        else:
            restore()
    except (OSError, ValueError, GLib.Error) as exc:
        print(exc, file=sys.stderr)

loop = GLib.MainLoop()
power.connect("g-properties-changed", update)
settings.connect("changed", update)
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: loop.quit())
update()
try:
    loop.run()
finally:
    restore()
