"""Apply the AgentLinux UI fixes to the pinned Ubuntu Kylin store for the ISO."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request

root = Path(sys.argv[1])
relative = Path("usr/share/ubuntu-kylin-software-center")
with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    if len(sys.argv) > 2:
        deb = Path(sys.argv[2])
    else:
        deb = work / "store.deb"
        url = "https://archive.ubuntu.com/ubuntu/pool/universe/u/ubuntu-kylin-software-center/ubuntu-kylin-software-center_3.3.4_amd64.deb"
        urllib.request.urlretrieve(url, deb)
    if hashlib.sha256(deb.read_bytes()).hexdigest() != "e046bb9e099d86f936f1fc105580c5807429a1ae2871ecd3191006328308a824":
        raise ValueError("Unexpected UKUI Software Center package")
    subprocess.run(["dpkg-deb", "-x", deb, work], check=True)
    store = work / relative
    patch = Path(__file__).resolve().with_name("local-deb-and-shutdown.patch")
    subprocess.run(["patch", "-p1", "-i", patch], cwd=store, check=True)
    for file in ("ubuntu-kylin-software-center.py", "models/enums.py", "ui/detailscrollwidget.py"):
        dest = root / relative / file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(store / file, dest)
