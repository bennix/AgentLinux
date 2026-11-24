#!/bin/sh
# Build the Chinese variant from the matching WinTC taskmgr source directory.
set -eu
src=${1:?supply the WinTC windows/taskmgr/src directory}
assets="$HOME/.local/share/agentlinux-xp"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -R "$src/." "$work/"
cd "$work"
sed -i 's/"Windows Task Manager"/"任务管理器"/g' window.c
sed -i '/gtk_container_add(GTK_CONTAINER(self), main_box);/a\    gtk_window_set_default_size(GTK_WINDOW(self), 630, 440);' window.c
sed -i 's/"Image Name"/"映像名称"/g; s/"User Name"/"用户名"/g; s/"Mem Usage"/"内存使用"/g' pageproc.c
echo '#define PKG_NAME "wintc-taskmgr"' > meta.h
glib-compile-resources --generate-source --sourcedir=res --target=resources.c res/resources.xml
cc -o taskmgr-zh ./*.c "$assets/mount-compat.c" $(pkg-config --cflags --libs gio-unix-2.0 gtk+-3.0 wintc-comctl wintc-comgtk wintc-shcommon wintc-shell wintc-shellext wintc-shlang)
install -m 755 taskmgr-zh "$assets/taskmgr-localized.new"
mv "$assets/taskmgr-localized.new" "$assets/taskmgr-localized"
