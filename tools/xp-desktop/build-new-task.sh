#!/bin/sh
set -eu
src=${1:?supply WinTC shell/run/src}
dest=${2:-"$HOME/.local/share/agentlinux-xp"}
mkdir -p "$dest"
dest=$(cd "$dest" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$src"/*.c "$src"/*.h "$work/"
cd "$work"
python3 - <<'PY'
from pathlib import Path
for name, old, new in (
    ("application.c", '"uk.co.oddmatics.wintc.run"', '"org.agentlinux.NewTask"'),
    ("dialog.c", '_("Run")', '(g_str_has_prefix(g_get_language_names()[0], "zh") ? "创建新任务" : "Create New Task")'),
):
    path = Path(name)
    source = path.read_text()
    if source.count(old) != 1:
        raise ValueError(f"Unexpected WinTC source in {name}")
    path.write_text(source.replace(old, new))
PY
echo '#define PKG_NAME "wintc-shell-run"' > meta.h
cc -o new-task ./*.c $(pkg-config --cflags --libs gtk+-3.0 wintc-comctl wintc-comgtk wintc-exec wintc-shlang)
stage=$(mktemp "$dest/new-task.XXXXXX")
trap 'rm -f "$stage"; rm -rf "$work"' EXIT
install -m 755 new-task "$stage"
mv "$stage" "$dest/new-task"
