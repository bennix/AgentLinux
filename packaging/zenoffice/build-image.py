"""Add the verified native ZenOffice package to an AgentLinux MyIME/WeChat ISO."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("base", type=Path)
parser.add_argument("deb", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--clash-verge", type=Path, help="Original Clash Verge 1.3.8 amd64 AppImage")
parser.add_argument("--libfuse2", type=Path, help="Ubuntu 24.04 libfuse2t64 amd64 package for the AppImage runtime")
args = parser.parse_args()
if args.output.exists():
    parser.error("Select a new output file")

def checksum(path, algorithm):
    with path.open("rb") as stream:
        result = hashlib.new(algorithm)
        for block in iter(lambda: stream.read(1 << 20), b""):
            result.update(block)
        return result.hexdigest()

def run(*args):
    subprocess.run(args, check=True)

if checksum(args.deb, "sha256") != "b0612de5180c10ea5d5903cf35c531034ce3742bad796efdd4822a1923ac207a":
    raise SystemExit("Unexpected ZenOffice package checksum (expected upstream v0.6.107 amd64)")
with tempfile.TemporaryDirectory(dir=args.output.parent) as directory:
    work = Path(directory)
    root = work / "root"
    run("dpkg-deb", "-x", args.deb, root)
    (root / "usr/bin").mkdir(exist_ok=True)
    (root / "usr/bin/genoffice").symlink_to("/opt/ZenOffice/genoffice")
    profiles = root / "etc/apparmor.d"
    profiles.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "opt/ZenOffice/resources/apparmor-profile", profiles / "genoffice")
    # Casper skips apparmor.service when the read-only live root has profiles.
    units = root / "etc/systemd/system"
    wants = units / "multi-user.target.wants"
    wants.mkdir(parents=True)
    service = "zenoffice-live-apparmor.service"
    (units / service).write_text("""[Unit]
Description=Load the ZenOffice AppArmor profile for the live desktop
ConditionPathExists=/rofs/etc/apparmor.d
ConditionSecurity=apparmor
After=apparmor.service
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=/usr/sbin/apparmor_parser --replace /etc/apparmor.d/genoffice
RemainAfterExit=yes
""")
    (wants / service).symlink_to("../" + service)
    overlay = Path(__file__).resolve().parents[2] / "overlay"
    for rel in ("etc/xdg/autostart/zenmux-workbench.desktop", "etc/firefox/policies/policies.json", "opt/obscura-firefox/distribution/policies.json"):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(overlay / rel, dest)
    shutil.copyfile(Path(__file__).resolve().parents[1] / "browser/distribution.ini",
                    root / "opt/obscura-firefox/distribution/distribution.ini")
    suffix = ".agent.zenoffice.squashfs"
    if args.clash_verge:
        if checksum(args.clash_verge, "sha256") != "7efe8f198689f2913ec094c0c7ba9759d54b52883aea7d7e91e307c7a77f6048":
            raise SystemExit("Unexpected Clash Verge v1.3.8 amd64 AppImage checksum")
        app = root / "opt/clash-verge"
        if not args.libfuse2 or checksum(args.libfuse2, "sha256") != "42919b326576c6c5cde85f4748092351c13b1b365c8793adb926b9c11cd5b22d":
            raise SystemExit("Expected Ubuntu Noble libfuse2t64 2.9.9-8.1build1 amd64")
        # The Noble runtime uses a merged /usr; a top-level lib directory in
        # a squashfs overlay would mask /lib -> usr/lib and the kernel modules.
        fuse = work / "fuse"
        run("dpkg-deb", "-x", args.libfuse2, fuse)
        shutil.copytree(fuse / "usr", root / "usr", symlinks=True, dirs_exist_ok=True)
        shutil.copytree(fuse / "lib", root / "usr/lib", symlinks=True, dirs_exist_ok=True)
        app.mkdir()
        binary = app / "Clash-Verge.AppImage"
        shutil.copyfile(args.clash_verge, binary)
        binary.chmod(0o755)
        (root / "usr/bin/clash-verge").symlink_to("/opt/clash-verge/Clash-Verge.AppImage")
        assets = work / "verge-assets"
        icon_path = "usr/share/icons/hicolor/256x256@2/apps/clash-verge.png"
        run("unsquashfs", "-o", "189632", "-d", assets, args.clash_verge, "clash-verge.desktop", icon_path)
        desktop = root / "usr/share/applications/clash-verge.desktop"
        desktop.write_text((assets / "clash-verge.desktop").read_text().replace("Development;", "Network;"))
        icon = root / "usr/share/icons/hicolor/256x256/apps/clash-verge.png"
        icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(assets / icon_path, icon)
        suffix = ".agent.apps.squashfs"
    layer = work / "office.squashfs"
    run("mksquashfs", root, layer, "-all-root", "-no-xattrs", "-noappend", "-comp", "xz")
    size = sum(p.stat().st_size for p in root.rglob("*") if not p.is_symlink() and p.is_file())
    paths = ["boot/grub/grub.cfg", "boot/grub/loopback.cfg", "casper/install-sources.yaml", "md5sum.txt"]
    read = ["xorriso", "-indev", args.base, "-osirrox", "on"]
    updates = {}
    for path in paths:
        updates[path] = work / Path(path).name
        read.extend(["-extract", "/" + path, updates[path]])
    run(*read)
    for path in paths[:-1]:
        f = updates[path]
        data = f.read_text()
        if ".agent.squashfs" not in data:
            raise ValueError(f"Expected layered AgentLinux source in {path}")
        data = data.replace(".agent.squashfs", suffix)
        if path.endswith(".yaml"):
            data = re.sub(r"(?m)^(  size: )(\d+)$", lambda m: m[1] + str(int(m[2]) + size), data)
        f.chmod(0o644)
        f.write_text(data)
    layers = ["casper/" + n + suffix for n in ("minimal","minimal.standard","minimal.standard.live")]
    checks = {p: checksum(updates[p], "md5") for p in paths[:-1]}
    checks.update(dict.fromkeys(layers, checksum(layer, "md5")))
    md5 = updates["md5sum.txt"]
    lines = [s for s in md5.read_text().splitlines() if s[32:].strip().lstrip("*").removeprefix("./") not in checks]
    md5.chmod(0o644)
    md5.write_text("\n".join(lines + [f"{v}  ./{k}" for k,v in checks.items()]) + "\n")
    updates[layers[0]] = layer
    image = work / "image.iso"
    write = ["xorriso", "-indev", args.base, "-outdev", image]
    for path, src in updates.items():
        write.extend(["-map", src, "/" + path])
    for path in layers[1:]:
        write.extend(["-clone", "/" + layers[0], "/" + path])
    run(*write, "-boot_image", "any", "replay", "-commit", "-end")
    image.rename(args.output)
args.output.with_suffix(".iso.sha256").write_text(checksum(args.output, "sha256") + "  " + args.output.name + "\n")
