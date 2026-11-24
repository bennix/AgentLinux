"""Apply the Song-style candidate font without changing other Fcitx settings."""
import configparser
import os
import tempfile
from pathlib import Path

path = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "fcitx5/conf/classicui.conf"
path.parent.mkdir(parents=True, exist_ok=True)
config = configparser.RawConfigParser()
config.optionxform = str
section = "ClassicUI"
# Fcitx stores top-level options before its named sections.
config.read_string(f"[{section}]\n" + (path.read_text() if path.exists() else ""))
config.set(section, "Font", "Noto Serif CJK SC 12")
with tempfile.NamedTemporaryFile(mode="w+", dir=path.parent, delete=False) as tmp:
    config.write(tmp, space_around_delimiters=False)
    tmp.seek(0)
    body = tmp.read().split("\n", 1)[1]
    tmp.seek(0)
    tmp.write(body)
    tmp.truncate()
os.replace(tmp.name, path)
