#!/bin/sh
set -eu
src=$(dirname "$0")
install -D -m 0755 "$src/start-desktop-manager.sh" /usr/local/libexec/agentlinux-xp-desktop
install -D -m 0644 "$src/agentlinux-xp-desktop.desktop" /usr/share/applications/agentlinux-xp-desktop.desktop
