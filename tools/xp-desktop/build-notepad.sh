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
# Register only successful opens and saves with the GTK recent-documents menu.
import re
s, count = re.subn(r"(?m)^( +)wnd->file_uri = g_strdup\(uri\);$",
                   r"\g<0>\n\1gtk_recent_manager_add_item(gtk_recent_manager_get_default(), wnd->file_uri);", s)
if count != 2:
    raise RuntimeError("Unexpected Notepad open/save implementation")
# GVfs supplies smb:// URIs when a shared document is opened from Peony.
unsupported = '    else\n    {\n        wintc_messagebox_show(\n            GTK_WINDOW(wnd),\n            "Sorry, only local files'
branches = ["""
        g_autoptr(GFile) file = g_file_new_for_uri(uri);
        g_autofree gchar* text = NULL;
        gsize length;
        GError* error = NULL;
        if (g_file_load_contents(file, NULL, &text, &length, NULL, &error)) {
            if (length > G_MAXINT || !g_utf8_validate(text, length, NULL))
                g_set_error_literal(&error, G_IO_ERROR, G_IO_ERROR_INVALID_DATA,
                    g_str_has_prefix(g_get_language_names()[0], "zh") ?
                    "无法打开此 UTF-8 文本文档。" : "Cannot open this document as UTF-8 text.");
            else {
                gtk_text_buffer_set_text(wnd->text_buffer, text, length);
                gtk_text_buffer_set_modified(wnd->text_buffer, FALSE);
                g_free(wnd->file_uri);
                wnd->file_uri = g_strdup(uri);
                gtk_recent_manager_add_item(gtk_recent_manager_get_default(), uri);
                wintc_notepad_window_update_title(wnd);
            }
        }
        if (error) wintc_display_error_and_clear(&error, GTK_WINDOW(wnd));
""", """
        g_autoptr(GFile) file = g_file_new_for_uri(uri);
        GtkTextIter start, end;
        gtk_text_buffer_get_bounds(wnd->text_buffer, &start, &end);
        g_autofree gchar* text = gtk_text_buffer_get_text(wnd->text_buffer, &start, &end, FALSE);
        GError* error = NULL;
        if (g_file_replace_contents(file, text, strlen(text), NULL, FALSE,
                                    G_FILE_CREATE_NONE, NULL, NULL, &error)) {
            g_free(wnd->file_uri);
            wnd->file_uri = g_strdup(uri);
            gtk_recent_manager_add_item(gtk_recent_manager_get_default(), uri);
            gtk_text_buffer_set_modified(wnd->text_buffer, FALSE);
            wintc_notepad_window_update_title(wnd);
        } else wintc_display_error_and_clear(&error, GTK_WINDOW(wnd));
"""]
pieces = s.split(unsupported)
if len(pieces) != 3:
    raise RuntimeError("Unexpected Notepad URI handlers")
s = pieces[0] + "".join('    else if (g_strcmp0(uri_scheme, "smb") == 0)\n    {' + branch +
                        '    }\n' + unsupported + tail for branch, tail in zip(branches, pieces[1:]))
# GTK's saved chooser dimensions can exceed the work area on compact displays.
anchor = "    return dlg;"
if s.count(anchor) != 1:
    raise RuntimeError("Unexpected Notepad file chooser")
s = s.replace(anchor, """    if (g_str_has_prefix(g_get_language_names()[0], "zh")) {
        gboolean saving = action == GTK_FILE_CHOOSER_ACTION_SAVE;
        gtk_window_set_title(GTK_WINDOW(dlg), saving ? "另存为" : "打开");
        gtk_button_set_label(GTK_BUTTON(gtk_dialog_get_widget_for_response(
            GTK_DIALOG(dlg), GTK_RESPONSE_CANCEL)), "取消");
        gtk_button_set_label(GTK_BUTTON(gtk_dialog_get_widget_for_response(
            GTK_DIALOG(dlg), GTK_RESPONSE_ACCEPT)), saving ? "保存" : "打开");
    }
    GdkMonitor* monitor = gdk_display_get_monitor_at_window(
        gtk_widget_get_display(GTK_WIDGET(wnd)), gtk_widget_get_window(GTK_WIDGET(wnd)));
    GdkRectangle area;
    gdk_monitor_get_workarea(monitor, &area);
    if (area.width <= 1280 || area.height <= 800)
        gtk_window_maximize(GTK_WINDOW(dlg));

""" + anchor)
# The text view implements these action signals for keyboard editing as well.
clipboard_actions = {key: key.lower() + "-clipboard" for key in ("CUT", "COPY", "PASTE")}
declaration = "static void action_clipboard(GSimpleAction* action, GVariant* parameter, gpointer user_data)"
s = s.replace("static GActionEntry s_window_actions[] = {",
              declaration + ";\n\nstatic GActionEntry s_window_actions[] = {\n" +
              "\n".join('    { .name = "%s", .activate = action_clipboard },' % signal
                        for signal in clipboard_actions.values()))
s += "\n" + declaration + """
{
    WinTCNotepadWindow* wnd = WINTC_NOTEPAD_WINDOW(user_data);
    (void)parameter;
    g_signal_emit_by_name(wnd->text_view, g_action_get_name(G_ACTION(action)));
}
"""
# Restore menu mnemonics after WinTC rewrites GtkLabel text during localization.
anchor = "    wintc_lc_builder_preprocess_widget_text(builder);"
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + """
    gboolean zh = g_str_has_prefix(g_get_language_names()[0], "zh");
    const gchar* ids[] = {"file-menu", "edit-menu", "format-menu", "view-menu", "help-menu"};
    const gchar* en_labels[] = {"_File", "_Edit", "F_ormat", "_View", "_Help"};
    const gchar* zh_labels[] = {"文件(_F)", "编辑(_E)", "格式(_O)", "查看(_V)", "帮助(_H)"};
    for (guint i = 0; i < G_N_ELEMENTS(ids); i++) {
        GtkMenuItem* item = GTK_MENU_ITEM(gtk_builder_get_object(builder, ids[i]));
        gtk_menu_item_set_use_underline(item, TRUE);
        gtk_menu_item_set_label(item, zh ? zh_labels[i] : en_labels[i]);
    }
""")
p.write_text(s)
app = Path("application.c")
source = app.read_text().replace("        first_run = FALSE;", """
    const gchar* goto_keys[] = {"<Primary>g", NULL};
    const gchar* new_keys[] = {"<Primary>n", NULL};
    const gchar* open_keys[] = {"<Primary>o", NULL};
    const gchar* save_keys[] = {"<Primary>s", NULL};
    gtk_application_set_accels_for_action(GTK_APPLICATION(application), "win.go-to", goto_keys);
    gtk_application_set_accels_for_action(GTK_APPLICATION(application), "win.new", new_keys);
    gtk_application_set_accels_for_action(GTK_APPLICATION(application), "win.open('')", open_keys);
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
    if stem == "notepad":
        for item in tree.iter("object"):
            label = item.find("property[@name='label']")
            if item.find("child[@type='submenu']") is not None and label is not None:
                item.set("id", label.text.removeprefix("%CTL_").removesuffix("MENU%").lower() + "-menu")
            for key, signal in clipboard_actions.items():
                if label is not None and label.text == "%CTL_" + key + "%":
                    item.find("property[@name='action-name']").text = "win." + signal
        tree.write("res/" + filename, encoding="utf-8")
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
