"""Remember confirmed X11 modes for each active monitor configuration."""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def monitors():
    listing = subprocess.check_output(["xrandr", "--props"], text=True, env={**os.environ, "LC_ALL": "C"})
    active = {}
    for block in re.split(r"\n(?=\S)", listing):
        header, _, properties = block.partition("\n")
        match = re.match(r"(\S+) connected (?:primary )?\d+x\d+[+-]\d+[+-]\d+", header)
        if not match:
            continue
        edid = re.search(r"^\s*EDID:[ \t]*\n((?:[ \t]+[\da-fA-F]{32}\s*\n)+)", properties, re.M)
        modes = dict(re.findall(r"^ +([0-9]+x[0-9]+)\s+([^\n]+)", properties, re.M))
        active[match[1]] = ("".join(edid[1].split()) if edid else "", modes)
    return active


def main(args):
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "agentlinux-xp" / "display-modes.json"
    if not args and not config.exists():
        return
    active = monitors()
    identity = json.dumps(sorted((name, info[0]) for name, info in active.items()))
    profiles = json.loads(config.read_text()) if config.exists() else {}
    if args:
        output, mode = args
        if output not in active or "*" not in active[output][1].get(mode, ""):
            raise ValueError("Display mode changed before it could be saved")
        profiles.setdefault(identity, {})[output] = mode
        config.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", dir=config.parent, delete=False) as draft:
            json.dump(profiles, draft)
        os.replace(draft.name, config)
        return
    changes = []
    for output, mode in profiles.get(identity, {}).items():
        rates = active[output][1].get(mode)
        if rates and "*" not in rates:
            changes.extend(["--output", output, "--mode", mode])
    if changes:
        subprocess.run(["xrandr", *changes], check=True)


if __name__ == "__main__":
    main(sys.argv[1:])
