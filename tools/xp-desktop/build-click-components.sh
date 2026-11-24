#!/bin/sh
# Build against the target distribution's Qt, Peony and WinTC development packages.
set -eu
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 WINTC_SOURCE PEONY_SOURCE DESTINATION" >&2
    exit 2
fi
assets=$(cd "$(dirname "$0")" && pwd)
wintc=$(cd "$1" && pwd)
peony=$(cd "$2" && pwd)
mkdir -p "$3"
dest=$(cd "$3" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -R "$wintc/shared/comctl" "$work/comctl"
(
    cd "$work/comctl"
    patch --batch --forward -p1 < "$assets/explorer-single-click.patch"
    (cd src/res && glib-compile-resources --target=../resources.c --generate resources.xml)
    cc -O2 -fPIC -shared -Wl,-soname,libwintc-comctl.so.1 src/*.c \
        $(pkg-config --cflags --libs gtk+-3.0 wintc-comgtk wintc-shcommon wintc-shlang) \
        -lm -o "$work/libwintc-comctl.so.1"
)
cp -R "$peony" "$work/peony"
(
    cd "$work/peony"
    patch --batch --forward -p1 < "$assets/peony-standard-icons.patch"
    patch --batch --forward -p1 < "$assets/peony-single-click.patch"
    patch --batch --forward -p1 < "$assets/peony-display-properties.patch"
    patch --batch --forward -p1 < "$assets/peony-open-computer.patch"
    patch --batch --forward -p1 < "$assets/peony-open-folders.patch"
    patch --batch --forward -p1 < "$assets/peony-sidebar-cleanup.patch"
    (cd libpeony-qt && qmake libpeony-qt.pro && make -j"${JOBS:-2}")
    cd peony-qt-desktop
    qmake peony-qt-desktop.pro
    make -j"${JOBS:-2}"
)
cc -Wall -Werror "$assets/accesskeys.c" -lX11 -o "$work/accesskeys"
cc -Wall -Werror -shared -fPIC "$assets/start-actions.c" $(pkg-config --cflags --libs gtk+-3.0) -ldl -o "$work/start-actions.so"
install -m755 "$work/start-actions.so" "$dest/start-actions.so"
mkdir -p "$dest/explorer-lib"
for file in "$work/accesskeys" "$work/libwintc-comctl.so.1" "$work/peony/libpeony-qt/libpeony.so.3.2.2" "$work/peony/peony-qt-desktop/peony-qt-desktop"; do
    case "$file" in
        */accesskeys) output="$dest/accesskeys" ;;
        */libpeony.so.3.2.2) output="$dest/libpeony.so.3.2.2" ;;
        *.so.1) output="$dest/explorer-lib/libwintc-comctl.so.1" ;;
        *) output="$dest/peony-qt-desktop" ;;
    esac
    stage=$(mktemp "$output.XXXXXX")
    install -m755 "$file" "$stage"
    mv "$stage" "$output"
done
install -m644 /var/lib/dpkg/info/libpeony3t64.md5sums "$dest/libpeony3t64.md5sums"
install -m644 /usr/share/locale-langpack/zh_CN/LC_MESSAGES/gtk30.mo "$dest/gtk30-zh_CN.mo"
