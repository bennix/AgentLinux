"""Add the verified native ZenOffice package to an AgentLinux MyIME/WeChat ISO."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("base", type=Path)
parser.add_argument("deb", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--clash-verge", type=Path, help="Clash Verge Rev 2.5.10 official amd64 deb")
parser.add_argument("--obscura-firefox", type=Path, required=True, help="Official Obscura Firefox 0.3.14 Linux amd64 deb")
parser.add_argument("--claude-cage", required=True, type=Path, help="Official Claude Cage 0.2.0-rc amd64 deb")
parser.add_argument("--ukcc-deb", type=Path, help="Use a cached UKUI control center package")
parser.add_argument("--store-deb", type=Path, help="Use a cached UKUI software center package")
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

if checksum(args.deb, "sha256") != "30522732743fe43ea56b4e0f603ea35dd0f5551467269e6b8c71ffe09e5314c8":
    raise SystemExit("Unexpected ZenOffice package checksum (expected upstream v0.6.108 amd64)")
with tempfile.TemporaryDirectory(dir=args.output.parent) as directory:
    work = Path(directory)
    root = work / "root"
    run("dpkg-deb", "-x", args.deb, root)
    (root / "usr/bin").mkdir(exist_ok=True)
    (root / "usr/bin/genoffice").symlink_to("/opt/ZenOffice/genoffice")
    profiles = root / "etc/apparmor.d"
    profiles.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "opt/ZenOffice/resources/apparmor-profile", profiles / "genoffice")
    shutil.copyfile(Path(__file__).with_name("claude-cage-desktop.apparmor"), profiles / "claude-cage-desktop")
    # Casper skips apparmor.service when the read-only live root has profiles.
    units = root / "etc/systemd/system"
    wants = units / "multi-user.target.wants"
    wants.mkdir(parents=True)
    service = "zenoffice-live-apparmor.service"
    (units / service).write_text("""[Unit]
Description=Load application AppArmor profiles for the live desktop
ConditionPathExists=/rofs/etc/apparmor.d
ConditionSecurity=apparmor
After=apparmor.service
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=/usr/sbin/apparmor_parser --replace /etc/apparmor.d/genoffice /etc/apparmor.d/claude-cage-desktop
RemainAfterExit=yes
""")
    (wants / service).symlink_to("../" + service)
    run("python3", Path(__file__).resolve().parents[1] / "branding/install.py", root, *(["--ukcc-deb", args.ukcc_deb] if args.ukcc_deb else []))
    overlay = Path(__file__).resolve().parents[2] / "overlay"
    if checksum(args.claude_cage, "sha256") != "ec6ca1844f717af1bd6b604dd4709a8d21665ef0b22a774c123614d73c6c005a":
        raise SystemExit("Unexpected Claude Cage 0.2.0-rc amd64 package checksum")
    cage_package = root / "opt/claude-cage-package/Cage-0.2.0-rc-linux-amd64.deb"
    cage_package.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.claude_cage, cage_package)
    if checksum(args.obscura_firefox, "sha256") != "9328c21c84f00ae7fc9d013b88448ca51b648d9e77b451f7a4b41c9767c1e143":
        raise SystemExit("Unexpected Obscura Firefox 0.3.14 amd64 package checksum")
    run("dpkg-deb", "-x", args.obscura_firefox, root)
    shutil.copy2(overlay / "usr/share/applications/obscura-firefox.desktop",
                 root / "usr/share/applications/obscura-firefox.desktop")
    for rel in ("usr/local/bin/agentlinux-obscura", "etc/systemd/logind.conf.d/90-agentlinux-lid.conf", "etc/dconf/profile/user",
                "etc/dconf/db/agentlinux", "etc/dconf/db/agentlinux.d/10-laptop-lid",
                "etc/NetworkManager/dispatcher.d/84-agentlinux-proxy", "usr/local/lib/zenmux/cage-terminal", "usr/local/lib/agentlinux-network/settings", "usr/local/lib/agentlinux-network/engine", "usr/local/lib/agentlinux-network/configure", "etc/xdg/autostart/zenmux-workbench.desktop", "etc/firefox/policies/policies.json", "opt/obscura-firefox/distribution/policies.json"):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / rel, dest)
    shutil.copyfile(Path(__file__).resolve().parents[1] / "browser/distribution.ini",
                    root / "opt/obscura-firefox/distribution/distribution.ini")
    smart = Path(__file__).resolve().parents[1] / "smart-routing"
    if args.clash_verge:
        target = root / "usr/local/lib/zenmux"
        shutil.copy2(overlay / "usr/local/lib/zenmux/accessible.py", target / "accessible.py")
        shutil.copy2(overlay / "usr/local/lib/zenmux/backend.py", target / "backend.py")
        shutil.copy2(smart / "smart_routing.py", target / "smart_routing.py")
        shutil.copy2(smart / "rules.json", target / "smart-routing.json")
        dest = root / "etc/skel/.local/share/io.github.clash-verge-rev.clash-verge-rev/profiles"
        dest.mkdir(parents=True)
        rules = json.loads((smart / "rules.json").read_text())
        # Register global enhancements so the first subscription import keeps
        # the distributor script instead of creating a fresh upstream template.
        (dest.parent / "profiles.yaml").write_text(json.dumps({"current": None, "items": [
            {"uid": "Merge", "type": "merge", "file": "Merge.yaml", "updated": 0},
            {"uid": "Script", "type": "script", "file": "Script.js", "updated": 0}
        ]}))
        (dest / "Merge.yaml").write_text("profile:\n  store-selected: true\n")
        (dest / "Script.js").write_text((smart / "script-template.js").read_text().replace("__DIRECT_RULES__", json.dumps(rules)))
    packaging = Path(__file__).resolve().parents[1]
    run("python3", packaging / "software-center/stage.py", root, *([args.store_deb] if args.store_deb else []))
    shutil.copy2(packaging / "ukui-menu/ukui-menu", root / "usr/bin/ukui-menu")
    user_units = root / "usr/lib/systemd/user"
    user_units.mkdir(parents=True, exist_ok=True)
    shutil.copy2(packaging / "input-tray/agentlinux-input.service", user_units)
    shutil.copy2(packaging / "input-tray/agentlinux-input.desktop", root / "etc/xdg/autostart")
    for name, directory in (
        ("notificationitem.conf", "usr/local/share/fcitx5/addon"),
        ("libagentlinuxnotificationitem.so", "usr/lib/x86_64-linux-gnu/fcitx5"),
    ):
        target = root / directory
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(packaging / "input-tray" / name, target)
    catalog = root / "usr/share/locale/zh_CN/LC_MESSAGES/agentlinux.mo"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    run("msgfmt", "-o", catalog, packaging / "i18n/zh_CN.po")
    for rel in ("usr/local/lib/zenmux/desktop.py", "usr/local/bin/zenmux-cage",
                "usr/share/applications/zenmux-agent.desktop", "usr/share/applications/zenmux-cage.desktop",
                "usr/share/applications/agentlinux-system-network.desktop"):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / rel, dest)
    shutil.copy2(packaging / "myime/settings.py", root / "usr/bin/myime-settings")
    wifi = Path(__file__).resolve().parents[1] / "wifi"
    (root / "usr/local/bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(wifi / "ukui-control-center", root / "usr/local/bin/ukui-control-center")
    shutil.copy2(packaging / "power-tray/ukui-power-manager-tray", root / "usr/local/bin/ukui-power-manager-tray")
    shutil.copy2(wifi / "properties", root / "usr/local/lib/agentlinux-network/properties")
    portable = packaging / "portable"
    for source, dest in (
        (wifi / "kylin-nm.desktop", "etc/xdg/autostart/kylin-nm.desktop"),
        (portable / "install-entry.desktop", "usr/local/share/agentlinux/agentlinux-install-to-disk.desktop"),
        (portable / "install-shortcuts.desktop", "etc/xdg/autostart/agentlinux-install-shortcuts.desktop"),
        (portable / "install-shortcuts", "usr/local/lib/agentlinux/install-shortcuts"),
        (portable / "reboot-to-installer", "usr/local/lib/agentlinux/reboot-to-installer"),
        (portable / "install-to-disk", "usr/local/bin/agentlinux-install-to-disk"),
        (portable / "prepare-installer", "usr/local/lib/agentlinux/prepare-installer"),
        (portable / "42_agentlinux_installer", "etc/grub.d/42_agentlinux_installer"),
    ):
        target = root / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    cage = Path(__file__).resolve().parents[1] / "cage"
    shutil.copy2(cage / "proxy-setup", root / "usr/local/lib/zenmux/cage-proxy-setup")
    shutil.copy2(cage / "proxy-setup.desktop", root / "usr/share/applications/cage-proxy-setup.desktop")
    shutil.copy2(cage / "host-terminal.desktop", root / "usr/share/applications/agentlinux-host-terminal.desktop")
    suffix = ".agent.zenoffice.squashfs"
    if args.clash_verge:
        if checksum(args.clash_verge, "sha256") != "add8564811ba4d2305da443288d23a26c5ed19674b676a0bb58b99ec4f7d13cf":
            raise SystemExit("Unexpected Clash Verge Rev 2.5.10 amd64 package checksum")
        run("dpkg-deb", "-x", args.clash_verge, root)
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
    replacing = suffix in updates["casper/install-sources.yaml"].read_text()
    old_size = 0
    if replacing:
        # Rebuild the top app layer directly from the current release.
        previous_layer = work / "previous.squashfs"
        run("xorriso", "-indev", args.base, "-osirrox", "on", "-extract",
            "/casper/minimal" + suffix, previous_layer)
        listing = subprocess.check_output(["unsquashfs", "-lln", previous_layer], text=True)
        old_size = sum(int(line.split(None, 3)[2]) for line in listing.splitlines()
                       if line.startswith("-"))
    for path in paths[:-1]:
        f = updates[path]
        data = f.read_text()
        if (suffix if replacing else ".agent.squashfs") not in data:
            raise ValueError(f"Expected layered AgentLinux source in {path}")
        if not replacing:
            data = data.replace(".agent.squashfs", suffix)
        if path.endswith(".yaml"):
            data = re.sub(r"(?m)^(  size: )(\d+)$", lambda m: m[1] + str(int(m[2]) + size - old_size), data)
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
        if replacing:
            write.extend(["-rm", "/" + path, "--"])
        write.extend(["-clone", "/" + layers[0], "/" + path])
    run(*write, "-boot_image", "any", "replay", "-commit", "-end")
    image.rename(args.output)
args.output.with_suffix(".iso.sha256").write_text(checksum(args.output, "sha256") + "  " + args.output.name + "\n")
