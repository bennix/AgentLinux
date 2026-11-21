"""Stage AgentLinux desktop artwork and the Noble UKUI About plugin in an image layer."""
import argparse
import base64
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
from xml.etree import ElementTree as ET

assets = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root", type=Path)
parser.add_argument("--ukcc-deb", type=Path)
args = parser.parse_args()
share = args.root / "usr/share"
greeter_images = share / "ukui-greeter/images"
greeter_images.mkdir(parents=True, exist_ok=True)
shutil.copyfile(assets / "greeter-logo.png", greeter_images / "logo.png")
# UKUI draws the selected account's portrait above the password field.
skel = args.root / "etc/skel"
skel.mkdir(parents=True, exist_ok=True)
shutil.copyfile(assets / "greeter-logo.png", skel / ".face")

backgrounds = share / "backgrounds"
backgrounds.mkdir(parents=True, exist_ok=True)
catalogs = share / "ukui-background-properties"
catalogs.mkdir(parents=True, exist_ok=True)
for catalog, themes in [
    ("ubuntukylin-wallpapers", [("AgentLinux", "AgentLinux", "AgentLinux · Plan / Act / Verify")]),
    ("noble-ubuntukylin-wallpapers", [("AgentLinux-Nodes", "AgentLinux-Nodes", "AgentLinux · Agent Network"),
                                      ("AgentLinux-Studio", "AgentLinux-Studio", "AgentLinux · Reasoning Studio")]),
]:
    collection = ET.Element("wallpapers")
    for source, filename, title in themes:
        shutil.copyfile(assets / (source + ".jpg"), backgrounds / (filename + ".jpg"))
        entry = ET.SubElement(collection, "wallpaper")
        for key, value in [("name", title), ("filename", "/usr/share/backgrounds/" + filename + ".jpg"),
                           ("options", "zoom"), ("pcolor", "#000000"), ("scolor", "#000000"), ("shade_type", "solid")]:
            ET.SubElement(entry, key).text = value
    # UKUI's catalog parser dereferences the DTD metadata when refreshing previews.
    header = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE wallpapers SYSTEM "gnome-wp-list.dtd">\n'
    (catalogs / (catalog + ".xml")).write_bytes(header.encode() + ET.tostring(collection, encoding="utf-8"))

shutil.copyfile(backgrounds / "AgentLinux.jpg", backgrounds / "warty-final-ubuntukylin.jpg")

# UKUI 3.22 passes these three built-in resource names directly to QSvgRenderer.
# Keep the string lengths and ELF offsets intact, including for literal-length Qt calls.
svg_path = "/usr/share/agentlinux/seal.svg"
dest = args.root / svg_path.lstrip("/")
dest.parent.mkdir(parents=True, exist_ok=True)
logo = base64.b64encode((assets / "emblem.jpg").read_bytes()).decode()
dest.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="130" height="50" viewBox="0 0 130 50"><image x="40" y="0" width="50" height="50" xlink:href="data:image/jpeg;base64,{logo}"/></svg>')
plugin = Path("usr/lib/x86_64-linux-gnu/ukui-control-center/libabout.so")
with tempfile.TemporaryDirectory() as temp:
    work = Path(temp)
    deb = args.ukcc_deb
    if deb is None:
        deb = work / "ukcc.deb"
        urllib.request.urlretrieve("https://archive.ubuntu.com/ubuntu/pool/universe/u/ukui-control-center/ukui-control-center_3.22.1.28-1_amd64.deb", deb)
    if hashlib.sha256(deb.read_bytes()).hexdigest() != "49ac14caed5554c87cdd220f96a6cf1dec487a866341ce30f62ce3a0e5cd0918":
        raise ValueError("Unexpected UKUI control center package")
    subprocess.run(["dpkg-deb", "-x", deb, work / "pkg"], check=True)
    data = (work / "pkg" / plugin).read_bytes()
    for filename in ("logo-dark.svg", "logo-light.svg", "logoukui.svg"):
        old = ("://img/plugins/about/" + filename).encode()
        if data.count(old + b"\0") != 1:
            raise ValueError("Unexpected About plugin resource table")
        new = svg_path.replace("/seal", "/" * (1 + len(old) - len(svg_path)) + "seal").encode()
        assert len(old) == len(new)
        data = data.replace(old + b"\0", new + b"\0")
    (args.root / plugin).parent.mkdir(parents=True, exist_ok=True)
    (args.root / plugin).write_bytes(data)
