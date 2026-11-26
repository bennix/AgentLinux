#!/usr/bin/python3
import fnmatch
import locale
import os
import re
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from queue import Empty, Full, Queue

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango

from task_pane import add_task_pane, fit_window

zh = GLib.get_language_names()[0].startswith("zh")


def tr(chinese, english):
    return chinese if zh else english


def type_description(content_type):
    labels = {
        "inode/directory": tr("文件夹", "File Folder"),
        "text/plain": tr("文本文档", "Text Document"),
        "application/octet-stream": tr("文件", "File"),
    }
    return labels.get(content_type) or Gio.content_type_get_description(content_type)


window = Gtk.Window(title=tr("搜索结果", "Search Results"))
window.set_icon_name("system-search")
fit_window(window, 800, 540)
layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
window.add(layout)
panes = Gtk.Paned()
layout.pack_start(panes, True, True, 0)
panel = Gtk.Box()
panes.pack1(panel, False, False)
tasks = add_task_pane(panel, tr("搜索助理", "Search Companion"))
sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=8)
tasks.add(sidebar)
name_label = Gtk.Label(label=tr("全部或部分文件名(_N)", "All or part of the file _name"), use_underline=True, xalign=0)
sidebar.add(name_label)
query = Gtk.Entry()
name_label.set_mnemonic_widget(query)
sidebar.add(query)
folder_label = Gtk.Label(label=tr("寻找范围(_L)", "_Look in"), use_underline=True, xalign=0)
sidebar.add(folder_label)
folder = Gtk.FileChooserButton(title=tr("选择文件夹", "Choose Folder"),
                               action=Gtk.FileChooserAction.SELECT_FOLDER)
folder.set_current_folder(str(Path.home()))
folder.set_filename(str(Path.home()))
folder_label.set_mnemonic_widget(folder)
sidebar.add(folder)
date_section = Gtk.Expander(label=tr("什么时候修改的？", "When was it modified?"))
date_choices = Gtk.ComboBoxText()
for label in [tr("不限", "Any time"), tr("最近 7 天", "Last 7 days"),
              tr("最近 30 天", "Last 30 days"), tr("最近 365 天", "Last 365 days")]:
    date_choices.append_text(label)
date_choices.set_active(0)
date_section.add(date_choices)
sidebar.add(date_section)
size_section = Gtk.Expander(label=tr("文件大小是多少？", "What size is it?"))
size_choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, margin_start=6)
size_section.add(size_choices)
sidebar.add(size_section)
size_filters = []
for label, lower, upper in [
    (tr("不限", "Don't remember"), None, None),
    (tr("小（小于 100 KB）", "Small (less than 100 KB)"), 0, 100 * 1024 - 1),
    (tr("中（100 KB 至 1 MB）", "Medium (100 KB to 1 MB)"), 100 * 1024, 1024 ** 2),
    (tr("大（大于 1 MB）", "Large (more than 1 MB)"), 1024 ** 2 + 1, None),
]:
    group = size_filters[0][0] if size_filters else None
    option = Gtk.RadioButton.new_with_label_from_widget(group, label)
    size_choices.add(option)
    size_filters.append((option, lower, upper))
advanced_section = Gtk.Expander(label=tr("更多高级选项", "More advanced options"))
subfolders = Gtk.CheckButton(label=tr("搜索子文件夹", "Search subfolders"))
subfolders.set_active(True)
advanced_choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
advanced_section.add(advanced_choices)
hidden_files = Gtk.CheckButton(label=tr("搜索隐藏文件和文件夹", "Search hidden files and folders"))
hidden_files.set_active(Gio.Settings.new("org.ukui.peony.settings").get_boolean("show-hidden-file"))
advanced_choices.add(hidden_files)
advanced_choices.add(subfolders)
match_case = Gtk.CheckButton(label=tr("区分大小写", "Case sensitive"))
advanced_choices.add(match_case)
sidebar.add(advanced_section)
buttons = Gtk.ButtonBox()
start = Gtk.Button.new_with_mnemonic(tr("搜索(_S)", "_Search"))
stop = Gtk.Button.new_with_mnemonic(tr("停止(_T)", "S_top"))
stop.set_sensitive(False)
shortcuts = Gtk.AccelGroup()
window.add_accel_group(shortcuts)
stop.add_accelerator("clicked", shortcuts, Gdk.KEY_Escape, 0, Gtk.AccelFlags.VISIBLE)
stop.set_tooltip_text(tr("停止当前搜索 (Esc)", "Stop the current search (Esc)"))
buttons.add(start)
buttons.add(stop)
sidebar.add(buttons)
model = Gtk.ListStore(str, str, Gio.Icon, GObject.TYPE_INT64, str, float, str, str)
def filename_key(name):
    # Compare digit runs by length and digits, including very long numeric names.
    parts = re.split(r"([0-9]+)", name.casefold())
    return tuple(locale.strxfrm(part) if index % 2 == 0 else
                 (len(part.lstrip("0")), part.lstrip("0"), len(part))
                 for index, part in enumerate(parts))


def compare_names(data, first, second, _unused):
    left = filename_key(data.get_value(first, 0))
    right = filename_key(data.get_value(second, 0))
    return (left > right) - (left < right)


model.set_sort_func(0, compare_names, None)
model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
results = Gtk.TreeView(model=model)
for i, title in enumerate([tr("名称", "Name"), tr("所在文件夹", "In Folder")]):
    column = Gtk.TreeViewColumn(title)
    if i == 0:
        icon = Gtk.CellRendererPixbuf()
        column.pack_start(icon, False)
        column.add_attribute(icon, "gicon", 2)
    text = Gtk.CellRendererText()
    text.set_property("ellipsize", Pango.EllipsizeMode.MIDDLE)
    column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
    column.set_fixed_width(135 if i == 0 else 120)
    column.pack_start(text, True)
    column.add_attribute(text, "text", i)
    column.set_resizable(True)
    column.set_sort_column_id(i)
    results.append_column(column)
def result_tooltip(tree, x, y, keyboard, tooltip):
    found, _, _, data, path, row = tree.get_tooltip_context(x, y, keyboard)
    if not found:
        return False
    tooltip.set_text(os.path.join(data[row][1], data[row][0]))
    tree.set_tooltip_row(tooltip, path)
    return True


results.set_has_tooltip(True)
results.connect("query-tooltip", result_tooltip)
size_cell = Gtk.CellRendererText(xalign=1)
size_column = Gtk.TreeViewColumn(tr("大小", "Size"), size_cell, text=4)
size_column.set_sort_column_id(3)
size_column.set_resizable(True)
results.append_column(size_column)
type_column = Gtk.TreeViewColumn(tr("类型", "Type"), Gtk.CellRendererText(), text=7)
type_column.set_sort_column_id(7)
type_column.set_resizable(True)
results.append_column(type_column)
modified_column = Gtk.TreeViewColumn(tr("修改日期", "Date Modified"), Gtk.CellRendererText(), text=6)
modified_column.set_sort_column_id(5)
modified_column.set_resizable(True)
results.append_column(modified_column)
scroll = Gtk.ScrolledWindow()
scroll.add(results)
panes.pack2(scroll, True, False)
status = Gtk.Label(xalign=0, margin=5)
layout.pack_end(status, False, False, 0)
active = None


def search(_widget):
    global active
    if active is not None:
        return
    root = folder.get_filename()
    if not root:
        return
    days = (0, 7, 30, 365)[date_choices.get_active()]
    today = date.today()
    midnight = datetime.min.time()
    first_day = datetime.combine(today - timedelta(days=days - 1), midnight).timestamp() if days else None
    tomorrow = datetime.combine(today + timedelta(days=1), midnight).timestamp()
    minimum, maximum = next((low, high) for option, low, high in size_filters if option.get_active())
    recursive = subfolders.get_active()
    include_hidden = hidden_files.get_active()
    case_sensitive = match_case.get_active()
    term = query.get_text()
    if not case_sensitive:
        term = term.casefold()
    pattern = term if any(c in term for c in "*?[") else "*" + term + "*"
    # Explorer treats *.* as all names, including names without an extension.
    if pattern == "*.*":
        pattern = "*"
    cancel = threading.Event()
    active = cancel
    batches = Queue(maxsize=4)
    model.clear()
    start.set_sensitive(False)
    stop.set_sensitive(True)
    status.set_text(tr("正在搜索…", "Searching…"))

    def send(batch):
        while not cancel.is_set():
            try:
                batches.put(batch, timeout=0.1)
                return
            except Full:
                pass

    def scan():
        batch = []
        for directory, folders, files in os.walk(root):
            if cancel.is_set():
                return
            if not include_hidden:
                folders[:] = [name for name in folders if not name.startswith(".")]
                files = [name for name in files if not name.startswith(".")]
            folder_names = set(folders)
            for name in folders + files:
                if cancel.is_set():
                    return
                if fnmatch.fnmatchcase(name if case_sensitive else name.casefold(), pattern):
                    content_type = "inode/directory" if name in folder_names else Gio.content_type_guess(name, None)[0]
                    size = -1
                    modified = float("-inf")
                    modified_text = ""
                    try:
                        info = os.stat(os.path.join(directory, name), follow_symlinks=False)
                        if name not in folder_names:
                            size = info.st_size
                        modified = info.st_mtime
                        modified_text = time.strftime("%x %H:%M", time.localtime(modified))
                    except (OSError, OverflowError, ValueError):
                        pass
                    if first_day is not None and not first_day <= modified < tomorrow:
                        continue
                    if minimum is not None and size < minimum:
                        continue
                    if maximum is not None and size > maximum:
                        continue
                    size_text = (f"{(size + 1023) // 1024:,} KB" if size >= 0 else "")
                    batch.append((name, directory, Gio.content_type_get_icon(content_type), size, size_text,
                                  modified, modified_text, type_description(content_type)))
                    if len(batch) == 100:
                        send(batch)
                        batch = []
            if not recursive:
                break
        if batch:
            send(batch)
        send(None)

    def poll():
        global active
        if not cancel.is_set():
            try:
                batch = batches.get_nowait()
            except Empty:
                return True
            if batch is not None:
                for row in batch:
                    model.append(row)
                return True
        active = None
        start.set_sensitive(True)
        stop.set_sensitive(False)
        count = len(model)
        english_count = "1 result" if count == 1 else f"{count} results"
        status.set_text((tr("已停止", "Stopped") if cancel.is_set() else tr("搜索完成", "Search complete"))
                        + tr(f" · {count} 个结果", f" · {english_count}"))
        return False

    threading.Thread(target=scan, daemon=True).start()
    GLib.timeout_add(25, poll)


def open_result(_tree, path, _column):
    name, directory, *_ = model[path]
    launch_path(Path(directory, name))


def launch_path(target):
    try:
        Gio.AppInfo.launch_default_for_uri(target.as_uri(), None)
    except GLib.Error as exc:
        dialog = Gtk.MessageDialog(transient_for=window, modal=True, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE, text=exc.message)
        dialog.run()
        dialog.destroy()


def file_manager_action(target, method):
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call_sync("org.freedesktop.FileManager1", "/org/freedesktop/FileManager1",
                      "org.freedesktop.FileManager1", method,
                      GLib.Variant("(ass)", ([target.as_uri()], "")), None,
                      Gio.DBusCallFlags.NONE, 5000, None)
    except GLib.Error as exc:
        if method == "ShowItems":
            launch_path(target.parent)
            return
        dialog = Gtk.MessageDialog(transient_for=window, modal=True, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE, text=exc.message)
        dialog.run()
        dialog.destroy()


def result_key(tree, event):
    modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
    if modifiers != Gdk.ModifierType.MOD1_MASK or event.keyval not in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
        return False
    selected_model, row = tree.get_selection().get_selected()
    if row is None:
        return False
    name, directory, *_ = selected_model[row]
    file_manager_action(Path(directory, name), "ShowItemProperties")
    return True


def result_menu(event=None):
    selected_model, row = results.get_selection().get_selected()
    if row is None:
        return False
    name, directory, *_ = selected_model[row]
    menu = Gtk.Menu()
    menu.attach_to_widget(results, None)
    target = Path(directory, name)
    open_item = Gtk.MenuItem(label=tr("打开", "Open"))
    open_item.connect("activate", lambda _: launch_path(target))
    menu.append(open_item)
    reveal = Gtk.MenuItem(label=tr("打开所在文件夹", "Open Containing Folder"))
    reveal.connect("activate", lambda _: file_manager_action(target, "ShowItems"))
    menu.append(reveal)
    menu.append(Gtk.SeparatorMenuItem())
    properties = Gtk.MenuItem(label=tr("属性", "Properties"))
    properties.connect("activate", lambda _: file_manager_action(Path(directory, name), "ShowItemProperties"))
    menu.append(properties)
    menu.connect("selection-done", lambda widget: widget.destroy())
    menu.show_all()
    if event is not None:
        menu.popup_at_pointer(event)
    else:
        path = selected_model.get_path(row)
        rect = results.get_cell_area(path, results.get_column(0))
        menu.popup_at_rect(results.get_bin_window(), rect, Gdk.Gravity.SOUTH_WEST,
                           Gdk.Gravity.NORTH_WEST, None)
        menu.select_first(True)
    return True


def result_click(tree, event):
    if event.button != 3:
        return False
    hit = tree.get_path_at_pos(int(event.x), int(event.y))
    if hit is None:
        return False
    tree.grab_focus()
    tree.set_cursor(hit[0])
    return result_menu(event)


results.connect("button-press-event", result_click)
results.connect("key-press-event", result_key)
results.connect("popup-menu", lambda _: result_menu())
start.connect("clicked", search)
query.connect("activate", search)
stop.connect("clicked", lambda _: active and active.set())
results.connect("row-activated", open_result)
window.connect("destroy", Gtk.main_quit)
window.show_all()
query.grab_focus()
Gtk.main()
