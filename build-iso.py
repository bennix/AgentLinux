"""Build the amd64 remix from the verified Ubuntu Kylin 24.04.5 desktop ISO."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
base = root / "build/base.iso"
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=root / "AgentLinux-24.04.5-network-amd64.iso")
out = parser.parse_args().output.resolve()
overlay = root / "overlay"


def digest(path, algorithm):
    with path.open("rb") as f:
        checksum = hashlib.new(algorithm)
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            checksum.update(chunk)
        return checksum.hexdigest()


required_payloads = (
    "opt/ZenCode/zcode",
    "opt/obscura-firefox/firefox",
    "opt/claude-cage-package/Cage-0.1.8-linux-amd64.deb",
    "usr/local/lib/zenmux/mihomo",
    "usr/bin/xdotool",
    "opt/wechat/wechat",
    "usr/share/applications/wechat.desktop",
    "usr/share/fcitx5/inputmethod/myime.conf",
    "usr/share/fcitx5/addon/myime.conf",
    "usr/lib/x86_64-linux-gnu/fcitx5/libmyime.so",
    "usr/lib/myime/MyIMEHost",
    "usr/lib/myime/IMEKit_IMEKit.resources/emoji-map.txt",
    "usr/share/myime/system.sqlite",
    "usr/bin/myime-settings",
    "usr/share/doc/myime/ThirdPartyNotices.txt",
)
if any(not (overlay / name).is_file() for name in required_payloads):
    raise SystemExit("Restore the complete release overlay first. See README.md.")

if digest(base, "sha256") != "8c3c89a59b50d3fc9d1affd087d19a3a670ecc5b34cc1e3ab05137bd7ec1b553":
    raise SystemExit("Base ISO checksum mismatch")
with tempfile.TemporaryDirectory(dir=out.parent) as work:
    tmp = Path(work)
    paths = ["boot/grub/grub.cfg", "boot/grub/loopback.cfg", "casper/install-sources.yaml", "md5sum.txt"]
    cmd = ["xorriso", "-indev", base, "-osirrox", "on"]
    for path in paths:
        cmd += ["-extract", "/" + path, tmp / Path(path).name]
    subprocess.run(cmd, check=True)
    layer = tmp / "agent.squashfs"
    subprocess.run(["mksquashfs", overlay, layer, "-all-root", "-no-xattrs", "-noappend", "-comp", "xz",
                    "-action", "chmod(0600)@name(agentlinux-proxy.nmconnection)"], check=True)
    updates = {}
    for path in paths[:-1]:
        f = tmp / Path(path).name
        f.chmod(0o644)
        value = f.read_text()
        if path.endswith(".cfg"):
            value = value.replace("quiet splash", "layerfs-path=minimal.standard.live.agent.squashfs quiet splash").replace("set timeout=30", "set timeout=5")
        else:
            value = value.replace(".squashfs", ".agent.squashfs")
            import re
            size = sum(p.stat().st_size for p in overlay.rglob("*") if p.is_file())
            value = re.sub(r"(?m)^(  size: )(\d+)$", lambda m: m[1] + str(int(m[2]) + size), value)
        f.write_text(value)
        updates[path] = f
    layers = ["casper/" + name + ".agent.squashfs" for name in ("minimal", "minimal.standard", "minimal.standard.live")]
    checks = {p: digest(f, "md5") for p, f in updates.items()}
    checks.update(dict.fromkeys(layers, digest(layer, "md5")))
    md5 = tmp / "md5sum.txt"
    lines = [line for line in md5.read_text().splitlines() if line[32:].strip().lstrip("*").removeprefix("./") not in checks]
    md5.chmod(0o644)
    md5.write_text("\n".join(lines + [f"{v}  ./{p}" for p, v in checks.items()]) + "\n")
    updates["md5sum.txt"] = md5
    updates[layers[0]] = layer
    image = tmp / "result.iso"
    cmd = ["xorriso", "-indev", base, "-outdev", image]
    for path, f in updates.items():
        cmd += ["-map", f, "/" + path]
    for path in layers[1:]:
        cmd += ["-clone", "/" + layers[0], "/" + path]
    subprocess.run(cmd + ["-publisher", "College of Computer Science and Artificial Intelligence, Fudan University", "-boot_image", "any", "replay", "-commit", "-end"], check=True)
    image.replace(out)
out.with_suffix(".iso.sha256").write_text(digest(out, "sha256") + "  " + out.name + "\n")
