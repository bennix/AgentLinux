"""Discover desktop entries and inspect supported system components as the current user."""
import shutil
import subprocess
from pathlib import Path

from gi.repository import Gio, GLib

# Each probe is read-only and returns a native machine-readable inventory.
PROBES = {
    "network": ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"],
    "printers": ["lpstat", "-e"],
    "shares": ["net", "usershare", "list"],
    "input-method": ["fcitx5-remote", "-n"],
    "storage": ["lsblk", "-J", "-o", "NAME,TYPE,SIZE,RO"],
    "power": ["upower", "-e"],
    "audio": ["pactl", "-f", "json", "list", "short", "sinks"],
    "display": ["xrandr", "--query"],
    "services": ["systemctl", "--failed", "--plain", "--no-legend", "--no-pager"],
}


def entries():
    return {app.get_id(): app for app in Gio.AppInfo.get_all() if app.get_id() and app.should_show()}


def power_readings():
    batteries = []
    supplies = []
    for path in sorted(Path("/sys/class/power_supply").glob("*/uevent")):
        try:
            properties = dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
        except OSError:
            continue
        if properties.get("POWER_SUPPLY_SCOPE") == "Device":
            continue
        kind = properties.get("POWER_SUPPLY_TYPE", "")
        if kind == "Battery" and properties.get("POWER_SUPPLY_PRESENT") != "0":
            capacity = properties.get("POWER_SUPPLY_CAPACITY", "")
            batteries.append({"name": path.parent.name, "state": properties.get("POWER_SUPPLY_STATUS"),
                              "percent": int(capacity) if capacity.isdecimal() else None})
        elif kind in ("Mains", "Wireless") or kind.startswith("USB"):
            online = properties.get("POWER_SUPPLY_ONLINE")
            if online in ("0", "1"):
                supplies.append(online == "1")
    return {"external_power_online": any(supplies) if supplies else None, "batteries": batteries}


def describe(component):
    if component.startswith("system/") and component[7:] in PROBES:
        key = component[7:]
        result = subprocess.run(PROBES[key], text=True, capture_output=True, timeout=8)
        info = {"component": component, "ok": result.returncode == 0, "status": result.stdout.strip(),
                "error": result.stderr.strip() if result.returncode else ""}
        if key == "power":
            info.update(power_readings())
        return info
    app = entries().get(component.removeprefix("app/")) if component.startswith("app/") else None
    if not app:
        raise ValueError("Unknown component")
    executable = app.get_executable()
    if app.get_commandline():
        try:
            _, argv = GLib.shell_parse_argv(app.get_commandline())
            executable = argv[0]
        except GLib.Error:
            pass
    return {"component": component, "name": app.get_display_name(), "executable": executable,
            "available": bool(executable and shutil.which(executable)),
            "actions": ["launch_app"], "desktop_id": app.get_id()}


def catalog():
    return {"system": ["system/" + key for key in sorted(PROBES)],
            "apps": {"app/" + key: app.get_display_name() for key, app in sorted(entries().items())}}
