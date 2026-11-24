#!/bin/sh
set -eu
src=${1:?supply WinTC windows/notepad/src}
assets="$HOME/.local/share/agentlinux-xp"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -R "$src/." "$work/"
cd "$work"
python3 - <<'PY'
from pathlib import Path
p = Path("window.c")
s = p.read_text()
start = s.index("    // FIXME: Double check this works with localization")
end = s.index("    gtk_window_set_title(", start)
s = s[:start] + '''    gboolean chinese = g_str_has_prefix(g_get_language_names()[0], "zh");
    GFile* file = wnd->file_uri ? g_file_new_for_uri(wnd->file_uri) : NULL;
    gchar* basename = file ? g_file_get_basename(file) : NULL;
    gchar* display = basename ? g_filename_display_name(basename) : NULL;
    gchar* title = g_strdup_printf("%s - %s",
        display ? display : (chinese ? "无标题" : _("Untitled")),
        chinese ? "记事本" : _("Notepad"));
    g_free(display);
    g_free(basename);
    g_clear_object(&file);

''' + s[end:]
p.write_text(s)
app = Path("application.c")
source = app.read_text().replace("        first_run = FALSE;", """
    const gchar* goto_keys[] = {"<Primary>g", NULL};
    const gchar* save_keys[] = {"<Primary>s", NULL};
    gtk_application_set_accels_for_action(GTK_APPLICATION(application), "win.go-to", goto_keys);
    gtk_application_set_accels_for_action(GTK_APPLICATION(application), "win.save", save_keys);
    first_run = FALSE;""")
app.write_text(source)
import xml.etree.ElementTree as ET

controls = dict(row.split("|") for row in """FILEMENU|文件(_F)
NEW|新建(_N)
OPEN|打开(_O)
SAVE|保存(_S)
SAVEAS|另存为(_A)
PAGESETUP|页面设置(_U)
PRINT|打印(_P)
EXIT|退出(_X)
EDITMENU|编辑(_E)
UNDO|撤销(_U)
CUT|剪切(_T)
COPY|复制(_C)
PASTE|粘贴(_P)
DELETE|删除(_L)
FIND|查找(_F)
FINDNEXT|查找下一个(_N)
REPLACE|替换(_R)
GOTO|转到(_G)
SELECTALL|全选(_A)
FORMATMENU|格式(_O)
WORDWRAP|自动换行(_W)
FONT|字体(_F)
VIEWMENU|查看(_V)
STATUSBAR|状态栏(_S)
HELPMENU|帮助(_H)
HELPTOPICS|帮助主题(_H)""".splitlines())
labels = {"Time/Date": "时间/日期", "About Notepad": "关于记事本",
          "Goto line": "转到指定行", "Line Number:": "行号：", "OK": "确定", "Cancel": "取消"}
manifest = ET.parse("res/resources.xml")
for stem, source in [("notepad", "window.c"), ("dlggoto", "dlggoto.c")]:
    filename = stem + ".ui"
    tree = ET.parse("res/" + filename)
    for field in tree.iter("property"):
        value = field.text or ""
        if value.endswith("%") and "%CTL_" in value:
            key = value.split("%CTL_")[1][:-1]
            field.text = controls[key] + ("…" if "%PUNC_MOREINPUT%" in value else "")
        elif value in labels:
            field.text = labels[value]
        else:
            continue
        field.attrib.pop("translatable", None)
    for widget in tree.iter("object"):
        label = widget.find("property[@name='label']")
        if label is not None and "(_" in (label.text or "") and widget.find("property[@name='use-underline']") is None:
            ET.SubElement(widget, "property", name="use-underline").text = "True"
    localized = stem + "-zh.ui"
    tree.write("res/" + localized, encoding="utf-8")
    ET.SubElement(manifest.getroot().find("gresource"), "file").text = localized
    path = Path(source)
    original = '"/uk/oddmatics/wintc/notepad/' + filename + '"'
    path.write_text(path.read_text().replace(original,
        'g_str_has_prefix(g_get_language_names()[0], "zh") ? '
        + original.replace(filename, localized) + ' : ' + original))
manifest.write("res/resources.xml", encoding="utf-8")
PY
echo '#define PKG_NAME "wintc-notepad"' > meta.h
glib-compile-resources --generate-source --sourcedir=res --target=resources.c res/resources.xml
cc -o notepad ./*.c "$assets/mount-compat.c" $(pkg-config --cflags --libs gio-unix-2.0 gtk+-3.0 wintc-comctl wintc-comgtk wintc-shcommon wintc-shell wintc-shellext wintc-shlang)
install -m 755 notepad "$assets/notepad.new"
mv "$assets/notepad.new" "$assets/notepad"
