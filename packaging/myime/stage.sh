#!/bin/sh
# Ubuntu 24.04 amd64, Swift >= 6, clang++, pkg-config, sqlite3/fcitx5core/json-c/enchant/glib development packages.
set -eu
project=$(cd "${1:?Specify the MyIME source checkout}" && pwd)
mkdir -p "${2:?Specify the staging directory}"
dest=$(cd "$2" && pwd)
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -r "$work"' EXIT
cp -R "$here/native/." "$work/"
mkdir -p "$work/IMEKit"
cp -R "$project/MyIME/IMEKit/Package.swift" "$project/MyIME/IMEKit/Sources" "$project/MyIME/IMEKit/Tests" "$work/IMEKit/"
swift build --package-path "$work" -c release --static-swift-stdlib -j 2
install -Dm755 "$work/.build/release/MyIMEHost" "$dest/usr/lib/myime/MyIMEHost"
strip "$dest/usr/lib/myime/MyIMEHost"
cp -R "$work/.build/release/IMEKit_IMEKit.resources" "$dest/usr/lib/myime/"
addon="$dest/usr/lib/x86_64-linux-gnu/fcitx5/libmyime.so"
mkdir -p "$(dirname "$addon")"
clang++ -std=c++17 -O2 -fPIC -shared "$here/native/addon.cpp" -o "$addon" $(pkg-config --cflags --libs Fcitx5Core json-c enchant-2 gio-2.0)
install -Dm644 "$here/myime.conf" "$dest/usr/share/fcitx5/inputmethod/myime.conf"
install -Dm644 "$here/addon.conf" "$dest/usr/share/fcitx5/addon/myime.conf"
install -Dm755 "$here/settings.py" "$dest/usr/bin/myime-settings"
install -Dm644 "$here/myime-settings.desktop" "$dest/usr/share/applications/myime-settings.desktop"
resources="$project/MyIME/MyIME/Resources"
install -Dm644 "$resources/system.sqlite" "$dest/usr/share/myime/system.sqlite"
for f in ThirdPartyNotices.txt GPL-3.0.txt; do install -Dm644 "$resources/$f" "$dest/usr/share/doc/myime/$f"; done
install -Dm644 "$project/LICENSING.md" "$dest/usr/share/doc/myime/LICENSING.md"
