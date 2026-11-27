#!/usr/bin/python3
"""Repair the X11 keyboard focus if the locker releases it without a target."""
import os
import re
import subprocess

from gi.repository import Gio, GLib


SCREENSAVER = "org.ukui.ScreenSaver"


def x11(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL,
                                   env={**os.environ, "LC_ALL": "C"}, timeout=1)


def restore_focus(bus, attempts):
    locked, = bus.call_sync(SCREENSAVER, "/", SCREENSAVER, "GetLockState", None,
                            GLib.VariantType.new("(b)"), Gio.DBusCallFlags.NONE, 1000, None).unpack()
    if locked:
        if attempts:
            GLib.timeout_add(300, retry, bus, attempts - 1)
        return
    if x11("xdotool", "getwindowfocus", "-f").strip() != "0":
        return
    active = re.search(r"0x[0-9a-fA-F]+", x11("xprop", "-root", "_NET_ACTIVE_WINDOW"))
    if not active or int(active[0], 16) == 0:
        if attempts:
            GLib.timeout_add(300, retry, bus, attempts - 1)
        return
    window = active[0]
    properties = x11("xprop", "-id", window, "WM_CLASS", "_NET_WM_WINDOW_TYPE")
    if any(kind in properties.lower() for kind in ("screensaver", "window_type_desktop",
                                                    "window_type_dock", "window_type_notification")):
        return
    if "IsViewable" in x11("xwininfo", "-id", window):
        # A normal application or the user may have received focus during the checks.
        if x11("xdotool", "getwindowfocus", "-f").strip() == "0":
            x11("xdotool", "windowfocus", window)


def retry(bus, attempts):
    try:
        restore_focus(bus, attempts)
    except (GLib.Error, OSError, subprocess.SubprocessError):
        pass  # The session or the candidate window may have closed.
    return GLib.SOURCE_REMOVE


def unlocked(bus, *_signal):
    GLib.timeout_add(350, retry, bus, 3)


if os.environ.get("DISPLAY") and os.environ.get("XDG_SESSION_TYPE") == "x11":
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    subscription = bus.signal_subscribe(
        SCREENSAVER, SCREENSAVER, "unlock", "/", None,
        Gio.DBusSignalFlags.NONE, unlocked,
    )
    try:
        GLib.MainLoop().run()
    finally:
        bus.signal_unsubscribe(subscription)
