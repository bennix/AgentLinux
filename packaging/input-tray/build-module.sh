#!/bin/sh
# Build on Ubuntu noble amd64 with the Fcitx 5.1.7 and fmt development headers.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
echo '8a67003d0370dbeaef1c6a171044c6c8da0c24006bfd1c15b7c44ba488f0d3f2  src.tar.xz' | sha256sum -c -
tar xf src.tar.xz
cd fcitx5-5.1.7
patch -p1 < "$here/menu.patch"
inc=${DEVROOT:-}/usr/include
echo "#define HAVE_PIPE2 1" > config.h
g++ -shared -fPIC -O2 -std=c++17 '-DFCITX_GETTEXT_DOMAIN="fcitx5"' -DFMT_HEADER_ONLY -I. -I"$inc" -I"$inc/Fcitx5/Core" -I"$inc/Fcitx5/Config" -I"$inc/Fcitx5/Utils" -Isrc/lib -Isrc/ui/classic -Isrc/modules/dbus src/modules/notificationitem/*.cpp -Wl,-z,defs -l:libFcitx5Core.so.7 -l:libFcitx5Config.so.6 -l:libFcitx5Utils.so.2 -o ../libagentlinuxnotificationitem.so
