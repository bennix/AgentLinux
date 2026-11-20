import json
import os
import shutil
from pathlib import Path

def configure(config, directory, outbound):
    rules = json.loads(Path(__file__).with_name("smart-routing.json").read_text())
    resources = Path("/usr/lib/Clash Verge/resources")
    for name in ("Country.mmdb", "geosite.dat"):
        dest = directory / name
        if not dest.exists():
            try:
                os.link(resources / name, dest)
            except OSError:
                shutil.copyfile(resources / name, dest)
    config.update({"mode": "rule", "find-process-mode": "strict",
                   "rules": rules + ["MATCH," + outbound]})
