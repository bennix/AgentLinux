#!/usr/bin/python3
"""Apply Studio appearance and restore the user's previous desktop settings."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

STUDIO = {
    "/general/theme": "AgentLinux Studio",
    "/general/title_alignment": "center",
    "/general/title_font": "Sans Bold 10",
    "picture-filename": "/usr/local/share/agentlinux/studio-wallpaper.jpg",
    "picture-options": "stretched",
    "panelposition": 1,
}


def xfconf(path, *args):
    return subprocess.run(["xfconf-query", "-c", "xfwm4", "-p", path, *args],
                          capture_output=True, text=True, timeout=3)


def settings(action, key, *value):
    schema = "org.ukui.panel.settings" if key == "panelposition" else "org.mate.background"
    return subprocess.run(["gsettings", action, schema, key, *value],
                          capture_output=True, text=True, timeout=3)


def read(path):
    if not path.startswith("/"):
        result = settings("get", path)
        if result.returncode == 0:
            return ast.literal_eval(result.stdout)
        return None
    result = xfconf(path)
    return result.stdout.rstrip("\n") if result.returncode == 0 else None


def write(path, value):
    if not path.startswith("/"):
        if value is None:
            settings("reset", path).check_returncode()
        else:
            settings("set", path, json.dumps(value)).check_returncode()
    elif value is None:
        xfconf(path, "-r").check_returncode()
    else:
        xfconf(path, "-n", "-t", "string", "-s", value).check_returncode()


def apply(theme, snapshot):
    if theme == "studio":
        previous = json.loads(snapshot.read_text()) if snapshot.exists() else {}
        current = {path: read(path) for path in STUDIO}
        pending = STUDIO.keys() - previous.keys()
        # Peony is optional in standalone X11 sessions.
        if current["panelposition"] is None:
            pending.discard("panelposition")
        if pending:
            for path in pending:
                previous[path] = current[path]
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", dir=snapshot.parent, delete=False) as file:
                json.dump(previous, file)
            os.replace(file.name, snapshot)
        for path, value in STUDIO.items():
            if path in previous and current[path] != value:
                write(path, value)
    elif snapshot.exists():
        previous = json.loads(snapshot.read_text())
        for path, value in STUDIO.items():
            # Preserve edits made by the user while Studio was active.
            if path in previous and read(path) == value and previous[path] != value:
                write(path, previous[path])
        snapshot.unlink()


if __name__ == "__main__":
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    apply(sys.argv[1], config / "agentlinux-xp" / "studio-window-settings.json")
