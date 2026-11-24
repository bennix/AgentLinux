"""Stage the rebuilt amd64 desktop components into a live/install image layer."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("components", type=Path, help="output of build-click-components.sh")
parser.add_argument("overlay", type=Path)
parser.add_argument("--debs", type=Path, default=Path(__file__).resolve().parents[2] / "build/xp/debs",
                    help="directory containing WinTC theme packages")
args = parser.parse_args()
assets = Path(__file__).resolve().parents[2] / "tools/xp-desktop"
user_assets = Path("etc/skel/.local/share/agentlinux-xp")
installer_assets = Path("usr/share/desktop-provision")
files = [
    (args.components / "gtk30-zh_CN.mo", Path("usr/share/locale-langpack/zh_CN/LC_MESSAGES/gtk30.mo"), 0o644),
    (args.components / "libpeony.so.3.2.2", Path("usr/lib/x86_64-linux-gnu/libpeony.so.3.2.2"), 0o644),
    (args.components / "agentlinux-volume-control", Path("usr/local/libexec/ukui-volume-control-applet-qt"), 0o755),
    (Path(__file__).with_name("volume-applet"), Path("usr/local/libexec/agentlinux-volume-applet"), 0o755),
    (Path(__file__).with_name("ukui-volume-control-applet.desktop"), Path("etc/skel/.config/autostart/ukui-volume-control-applet.desktop"), 0o644),
    (Path(__file__).with_name("ukui-volume-control-applet.desktop"), Path("etc/xdg/autostart/ukui-volume-control-applet.desktop"), 0o644),
    (assets.parents[1] / "packaging/portable/install-entry.desktop", Path("usr/local/share/agentlinux/agentlinux-install-to-disk.desktop"), 0o644),
    (assets.parents[1] / "packaging/portable/install-to-disk", Path("usr/local/bin/agentlinux-install-to-disk"), 0o755),
    (assets.parents[1] / "packaging/portable/42_agentlinux_installer", Path("etc/grub.d/42_agentlinux_installer"), 0o755),
    (Path(__file__).with_name("installer") / "launch-ui", Path("usr/local/libexec/agentlinux-xp-install-ui"), 0o755),
    (args.components.parent / "installer-artifacts/libapp.so", Path("usr/local/share/agentlinux-xp/installer/libapp.so"), 0o644),
    (Path(__file__).with_name("whitelabel.yml"), installer_assets / "whitelabel.yml", 0o644),
    (assets.parents[1] / "packaging/branding/greeter-logo.png", installer_assets / "images/college-emblem.png", 0o644),
]
slides = Path(__file__).with_name("installer") / "slides"
for category in ("ADDRESS", "COLLATE", "CTYPE", "IDENTIFICATION", "MEASUREMENT",
                 "MESSAGES/SYS_LC_MESSAGES", "MONETARY", "NAME", "NUMERIC", "PAPER",
                 "TELEPHONE", "TIME"):
    relative = Path("en_US.utf8") / ("LC_" + category)
    files.append((args.components / relative, Path("usr/lib/locale") / relative, 0o644))
for slide in sorted(slides.glob("*/*.html")):
    files.append((slide, installer_assets / "slides" / slide.relative_to(slides), 0o644))
for relative in ("accesskeys", "clock-entry.so", "start-actions.so", "task-manager-run.so", "taskmgr-localized", "notepad", "mount-compat.so", "run-shortcut",
                 "explorer-toolbar.so", "explorer-newmenu.so", "run-network.so", "display-language.so",
                 "peony-qt-desktop", "explorer-lib/libwintc-comctl.so.1"):
    source = args.components / relative
    with source.open("rb") as binary:
        header = binary.read(20)
    if header[:6] != b"\x7fELF\x02\x01" or header[18:20] != b"\x3e\x00":
        parser.error(f"{source} must be an x86-64 Linux ELF file")
    files.append((source, user_assets / relative, 0o755))
for name in (
    "install-panel-entries.sh", "control-panel.py", "system-properties.py", "input-properties.py",
    "cursor-settings.py", "sound-properties.py", "date-properties.py", "power-properties.py",
    "programs.py", "fonts.py", "accessibility.py", "user-accounts.py", "network-places.py",
    "connections.py", "wireless.py", "search-files.py", "default-programs.py", "printers.py", "add-printer.py", "dns_properties.py",
    "login-start.sh", "shell-start.sh", "session-env.sh", "taskbar.sh", "task-manager.sh", "display-mode.py",
    "session-dialog.py", "menu-open.sh", "explorer-launch.sh", "run-dialog.sh", "control-command.sh",
    "network_details.py", "task_pane.py", "cursor_preview.py",
):
    files.append((assets / name, user_assets / name, 0o755))
files.extend([
    (Path(__file__).with_name("org.kde.kscreen.service"), Path("usr/local/share/dbus-1/services/org.kde.kscreen.service"), 0o644),
    (Path(__file__).with_name("kscreen-theme.conf"), Path("etc/systemd/user/plasma-kscreen.service.d/theme.conf"), 0o644),
    (assets / "lid-backlight.py", Path("usr/local/libexec/agentlinux-xp-lid"), 0o755),
    (Path(__file__).with_name("lid.desktop"), Path("etc/xdg/autostart/agentlinux-xp-lid.desktop"), 0o644),
    (assets.parents[1] / "packaging/branding/greeter-logo.png", user_assets / "college-emblem.png", 0o644),
    (Path(__file__).with_name("xsessionrc"), Path("etc/skel/.xsessionrc"), 0o644),
    (Path(__file__).with_name("xfwm4.xml"), Path("etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml"), 0o644),
    (Path(__file__).with_name("xsettings.xml"), Path("etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml"), 0o644),
    (Path(__file__).with_name("classicui.conf"), Path("etc/skel/.config/fcitx5/conf/classicui.conf"), 0o644),
    (Path(__file__).with_name("gtk-settings.ini"), Path("etc/skel/.config/gtk-3.0/settings.ini"), 0o644),
    (Path(__file__).with_name("peony-desktop.desktop"), Path("etc/skel/.config/autostart/peony-desktop.desktop"), 0o644),
    (Path(__file__).with_name("panel-entries.desktop"), Path("etc/skel/.config/autostart/agentlinux-xp-panel-entries.desktop"), 0o644),
    (assets / "install-panel-entries.sh", Path("usr/local/libexec/agentlinux-xp-panel-setup"), 0o755),
    (assets / "start-desktop-manager.sh", Path("usr/local/libexec/agentlinux-xp-desktop"), 0o755),
    (assets / "agentlinux-xp-desktop.desktop", Path("usr/share/applications/agentlinux-xp-desktop.desktop"), 0o644),
])
for name in ("AgentLinux.jpg", "AgentLinux-Nodes.jpg", "AgentLinux-Studio.jpg", "college-bliss.svg"):
    files.append((assets.parents[1] / "packaging/branding" / name, Path("usr/share/backgrounds") / name, 0o644))
greeter = Path(__file__).with_name("greeter")
resource_dir = Path("usr/local/share/agentlinux-xp/greeter")
files.extend([
    (assets / "screensaver-defaults.py", Path("usr/local/libexec/agentlinux-xp-screensaver-defaults"), 0o755),
    (greeter / "lock-background.svg", resource_dir / "lock-background.svg", 0o644),
    (greeter / "bliss.png", Path("usr/local/share/agentlinux-xp/screensaver/bliss.png"), 0o644),
    (assets.parents[1] / "overlay/usr/local/bin/agentlinux-components", Path("usr/local/bin/agentlinux-components"), 0o755),
    (assets / "login-greeter.sh", Path("usr/local/libexec/agentlinux-xp-greeter"), 0o755),
    (greeter / "agentlinux-xp.desktop", Path("usr/share/xgreeters/agentlinux-xp.desktop"), 0o644),
    (Path(__file__).with_name("lightdm-locale.conf"), Path("etc/systemd/system/lightdm.service.d/locale.conf"), 0o644),
    (greeter / "99-agentlinux-xp.conf", Path("etc/lightdm/lightdm.conf.d/99-agentlinux-xp.conf"), 0o644),
])
for name in ("logo.png", "mini-logo.png", "userpic.png"):
    files.append((assets.parents[1] / "packaging/branding/greeter-logo.png", resource_dir / "branding" / name, 0o644))
for resource in (*greeter.glob("*/*.ui"), *greeter.glob("*/*.css")):
    files.append((resource, resource_dir / resource.relative_to(greeter), 0o644))

for directory in ("taskbar-zh", "explorer-zh", "taskmgr-zh", "taskmgr-en"):
    for resource in Path(__file__).with_name(directory).glob("*.ui"):
        files.append((resource, user_assets / directory / resource.name, 0o644))

boot_theme = Path("usr/share/plymouth/themes/agentlinux-xp")
for resource in Path(__file__).with_name("boot").joinpath("theme").iterdir():
    files.append((resource, boot_theme / resource.name, 0o644))

archives = []
for package in ("python3-packaging", "xfwm4", "xfconf", "libxfconf-0-3", "libgarcon-common", "libgarcon-1-0", "libgarcon-gtk3-1-0",
                "libxfce4ui-2-0", "libxfce4ui-common", "libxfce4util7", "libxfce4util-common"):
    archive = args.debs.parent / "ubuntu-debs" / (package + ".deb")
    archives.append(archive)

for package in ("wintc-taskband", "wintc-notepad", "wintc-taskmgr", "wintc-explorer", "wintc-shell-run", "wintc-cpl-desk",
                "wintc-sound-theme-xp", "wintc-cursor-theme-standard-with-shadow", "wintc-cursor-theme-standard-no-shadow",
                "libwintc-exec", "libwintc-shelldpa", "libwintc-shellext", "libwintc-sndapi",
                "libwintc-syscfg", "libwintc-registry", "libwintc-shell", "wintc-regsvc", "wintc-icon-theme-luna", "wintc-theme-luna-blue", "wintc-logonui",
                "libwintc-comctl", "libwintc-comgtk", "libwintc-msgina", "libwintc-shlang",
                "libwintc-shcommon", "libwintc-winbrand"):
    archives.append(args.debs / (package + ".deb"))

archives.append(args.components / "ukui-media_3.1.1.2-1+agentlinux1_amd64.deb")

for archive in archives:
    subprocess.run(["dpkg-deb", "--extract", archive, args.overlay], check=True)
    files.append((archive, Path("usr/local/share/agentlinux-xp/packages") / archive.name, 0o644))
files.extend([
    (Path(__file__).with_name("register-packages"), Path("usr/local/libexec/agentlinux-xp-register-packages"), 0o755),
    (Path(__file__).with_name("register-packages.service"), Path("etc/systemd/system/agentlinux-xp-packages.service"), 0o644),
])

# The Ubuntu base aliases /lib to /usr/lib. A real /lib directory in the
# upper SquashFS would hide that link, including the display-manager unit.
legacy_lib = args.overlay / "lib"
if legacy_lib.is_dir() and not legacy_lib.is_symlink():
    shutil.copytree(legacy_lib, args.overlay / "usr/lib", symlinks=True, dirs_exist_ok=True)
    shutil.rmtree(legacy_lib)

# WinTC references GTK touch handles and slider images supplied by the Kylin base.
theme_assets = args.overlay / "usr/share/themes/Windows XP style (Blue)/gtk-3.0/assets"
if not theme_assets.exists() and not theme_assets.is_symlink():
    theme_assets.symlink_to("../../ukui/gtk-3.0/assets", target_is_directory=True)

for source, relative, mode in files:
    target = args.overlay / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    target.chmod(mode)

# Keep dpkg's record for the rebuilt library consistent in Live and installed systems.
library = Path("usr/lib/x86_64-linux-gnu/libpeony.so.3.2.2")
manifest = "libpeony3t64.md5sums"
entries = (args.components / manifest).read_text().splitlines()
matching = [i for i, line in enumerate(entries) if line.split(maxsplit=1)[-1] == str(library)]
if len(matching) != 1:
    parser.error(f"{manifest} must contain exactly one entry for {library}")
checksum = hashlib.md5((args.overlay / library).read_bytes()).hexdigest()
entries[matching[0]] = f"{checksum}  {library}"
record = args.overlay / "var/lib/dpkg/info" / manifest
record.parent.mkdir(parents=True, exist_ok=True)
record.write_text("\n".join(entries) + "\n")

commands = {"run": "run-dialog.sh", "exo-open": "menu-open.sh", "system-config-printer": "printers.py", "wintc-exitwin": "session-dialog.py",
            "xfce4-settings-manager": "control-panel.py"}
links = {user_assets / "menu-commands" / name: "../" + script for name, script in commands.items()}
for name in ("control", "control.exe", "calc", "calc.exe", "winver", "fsmgmt.msc", "diskmgmt.msc", "devmgmt.msc", "sysdm.cpl",
             "mmsys.cpl", "powercfg.cpl", "main.cpl", "ncpa.cpl", "timedate.cpl", "nusrmgr.cpl",
             "desk.cpl", "appwiz.cpl", "access.cpl", "intl.cpl"):
    links[Path("etc/skel/.local/bin") / name] = "../share/agentlinux-xp/control-command.sh"
links[Path("etc/skel/.local/bin/taskmgr")] = "../share/agentlinux-xp/task-manager.sh"
links[Path("etc/skel/.local/bin/notepad")] = "../share/agentlinux-xp/notepad"
links[Path("etc/systemd/system/multi-user.target.wants/agentlinux-xp-packages.service")] = "../agentlinux-xp-packages.service"
links[Path("etc/alternatives/default.plymouth")] = "/" + str(boot_theme / "agentlinux-xp.plymouth")
for relative, destination in links.items():
    link = args.overlay / relative
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        link.unlink()
    link.symlink_to(destination)
