"""Append the XP Plymouth resources to an original Ubuntu Kylin Live initrd."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("original", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
if args.original.resolve() == args.output.resolve():
    parser.error("choose a separate output file")
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    themes = Path("usr/share/plymouth/themes")
    target = root / themes
    target.mkdir(parents=True)
    shutil.copytree(Path(__file__).with_name("theme"), target / "agentlinux-xp")
    (target / "default.plymouth").symlink_to("agentlinux-xp/agentlinux-xp.plymouth")
    archive = subprocess.check_output(
        ["bsdtar", "--format", "newc", "--uid", "0", "--gid", "0", "-cf", "-",
         themes / "agentlinux-xp", themes / "default.plymouth"], cwd=root)
    with args.original.open("rb") as source, args.output.open("wb") as output:
        shutil.copyfileobj(source, output)
        output.write(bytes(-output.tell() % 4))
        output.write(archive)
