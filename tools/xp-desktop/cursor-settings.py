"""Apply the saved XP pointer scheme to X11 clients."""
import os
import subprocess

from gi.repository import Gio

if os.environ.get("DISPLAY"):
    mouse = Gio.Settings.new("org.ukui.peripherals-mouse")
    theme = mouse.get_string("cursor-theme") or "default"
    size = mouse.get_int("cursor-size")
    if not set("\r\n\\").intersection(theme):
        subprocess.run(["xrdb", "-nocpp", "-merge"], check=True, text=True,
                       input=f"Xcursor.theme: {theme}\nXcursor.size: {size}\n")
