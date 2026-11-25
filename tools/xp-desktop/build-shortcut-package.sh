#!/bin/sh
set -eu
src=${1:?WinTC appwiz source directory required}
original=${2:?original wintc-cpl-appwiz package required}
output=${3:?output package required}
assets=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
dpkg-deb -R "$original" "$work/package"
cp -R "$src" "$work/src"
cp -R "$src/../../../../shared/comgtk" "$work/comgtk"
(cd "$work/comgtk" && patch -p1 < "$assets/shortcut-message-buttons.patch")
(
    cd "$work/src"
    patch -p1 < "$assets/shortcut-translations.patch"
    echo '#define PKG_NAME "wintc-cpl-appwiz"' > meta.h
    glib-compile-resources --generate-source --sourcedir=res --target=resources.c res/resources.xml
    cc -O2 -o "$work/package/usr/bin/appwiz.cpl" ./*.c "$work/comgtk/src/msgbox.c" $(pkg-config --cflags --libs gtk+-3.0 gio-unix-2.0 wintc-comctl wintc-comgtk wintc-shcommon wintc-shlang wintc-wizard97)
)
locale="$work/package/usr/share/locale/zh_CN/LC_MESSAGES"
mkdir -p "$locale"
msgfmt --check-format "$assets/shortcut-zh_CN.po" -o "$locale/wintc-cpl-appwiz.mo"
sed -i '/^Version:/s/$/+agentlinux2/' "$work/package/DEBIAN/control"
(cd "$work/package" && find usr -type f -exec md5sum {} + >DEBIAN/md5sums)
dpkg-deb --root-owner-group -b "$work/package" "$output"
