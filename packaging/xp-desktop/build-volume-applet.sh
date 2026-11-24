#!/bin/sh
# Build on Ubuntu amd64 with the ukui-media build dependencies installed.
set -eu
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 UKUI_MEDIA_3.1.1.2_SOURCE COMPONENT_DIRECTORY" >&2
    exit 2
fi
test "$(dpkg --print-architecture)" = amd64
patch_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$2"
output=$(CDPATH= cd -- "$2" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -R "$1/ukui-volume-control-applet-qt" "$work/"
cd "$work"
patch -p1 < "$patch_dir/ukui-media-module-query.patch"
cd ukui-volume-control-applet-qt
qmake 'QMAKE_CXXFLAGS+=-Werror=return-type'
make -j"${JOBS:-2}"
strip -o "$work/agentlinux-volume-control" ukui-volume-control-applet-qt
install -m755 "$work/agentlinux-volume-control" "$output/agentlinux-volume-control"

# Preserve the distro package's other payloads, maintainer scripts and conffiles.
cd "$work"
apt-get download ukui-media:amd64=3.1.1.2-1
dpkg-deb -R ukui-media_3.1.1.2-1_amd64.deb package
binary=usr/bin/ukui-volume-control-applet-qt
install -m755 agentlinux-volume-control "package/$binary"
sed -i 's/^Version: .*/Version: 3.1.1.2-1+agentlinux1/' package/DEBIAN/control
(
    cd package
    sed -i '\|  usr/bin/ukui-volume-control-applet-qt$|d' DEBIAN/md5sums
    md5sum "$binary" >> DEBIAN/md5sums
)
dpkg-deb --root-owner-group -b package "$output/ukui-media_3.1.1.2-1+agentlinux1_amd64.deb"
