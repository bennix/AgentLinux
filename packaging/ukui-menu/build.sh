#!/bin/sh
# Run on Noble amd64 with the ukui-menu build dependencies installed.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
curl -fLsS --retry 3 https://archive.ubuntu.com/ubuntu/pool/universe/u/ukui-menu/ukui-menu_3.0.3.orig.tar.gz -o menu.tar.gz
echo "5b0ef863bc06eb2ac4b0c78b99249cc6a1f1dc8e807ce7801c12132c0f58eadb  menu.tar.gz" | sha256sum -c -
tar xzf menu.tar.gz
cd ukui-menu
patch -p1 < "$here/layout-ownership.patch"
/usr/lib/qt5/bin/qmake ukui-menu.pro
make -j"${JOBS:-2}"
strip -o "$work/ukui-menu.stripped" ukui-menu
install -m755 "$work/ukui-menu.stripped" "$here/ukui-menu"
