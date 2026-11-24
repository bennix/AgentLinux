#!/usr/bin/python3
from pathlib import Path

from gi.repository import Gio, GLib

background = Path("/usr/local/share/agentlinux-xp/greeter/lock-background.svg")
slides = Path("/usr/local/share/agentlinux-xp/screensaver")
if background.is_file() and (slides / "bliss.png").is_file():
    defaults = {
        "org.ukui.screensaver": {"background": str(background), "mode": "default-ukui-custom"},
        "org.ukui.screensaver-default": {
            "background-path": str(slides), "text-is-center": False,
            "mytext": "AgentLinux", "show-rest-time": False,
        },
    }
    for schema, values in defaults.items():
        settings = Gio.Settings.new(schema)
        for key, value in values.items():
            if settings.get_user_value(key) is None:
                signature = settings.get_default_value(key).get_type_string()
                settings.set_value(key, GLib.Variant(signature, value))
    Gio.Settings.sync()
