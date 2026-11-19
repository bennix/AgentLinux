#!/bin/sh
# Stage the official amd64 desktop client into the release filesystem.
set -eu
package=${1:?Expected Tencent WeChat .deb}
dest=${2:?Expected release overlay}
[ "$(dpkg-deb -f "$package" Package)" = wechat ]
[ "$(dpkg-deb -f "$package" Architecture)" = amd64 ]
mkdir -p "$dest"
dpkg-deb -x "$package" "$dest"
mkdir -p "$dest/usr/bin"
ln -snf /opt/wechat/wechat "$dest/usr/bin/wechat"
test -x "$dest/opt/wechat/wechat"
test -f "$dest/usr/share/applications/wechat.desktop"
