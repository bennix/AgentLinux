#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
dest=$(mktemp -d)
trap 'rm -rf "$dest"' EXIT
chmod 755 "$dest"
cp -a packaging/network/DEBIAN "$dest/"
for item in etc/NetworkManager etc/claude-code usr/local/lib/agentlinux-network usr/share/applications/agentlinux-system-network.desktop etc/systemd/system/agentlinux-tunnel.service; do
    mkdir -p "$dest/$(dirname "$item")"
    cp -a "overlay/$item" "$dest/$item"
done
chmod 600 "$dest/etc/NetworkManager/system-connections/agentlinux-proxy.nmconnection"
mkdir -p build/networkqa
dpkg-deb --root-owner-group -Zgzip --build "$dest" build/networkqa/agentlinux-system-network.deb
