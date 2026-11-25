#!/usr/bin/python3
import fnmatch
import os
import threading
import time
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
buttons = Gtk.ButtonBox()
start = Gtk.Button.new_with_mnemonic(tr("搜索(_S)", "_Search"))
stop = Gtk.Button.new_with_mnemonic(tr("停止(_T)", "S_top"))
stop.set_sensitive(False)
buttons.add(start)
buttons.add(stop)
sidebar.add(buttons)
model = Gtk.ListStore(str, str, Gio.Icon, GObject.TYPE_INT64, str, float, str, str)
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
    term = query.get_text().casefold()
    pattern = term if any(c in term for c in "*?[") else "*" + term + "*"
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
            folder_names = set(folders)
            for name in folders + files:
                if cancel.is_set():
                    return
                if fnmatch.fnmatchcase(name.casefold(), pattern):
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
                    size_text = (f"{(size + 1023) // 1024:,} KB" if size >= 0 else "")
                    batch.append((name, directory, Gio.content_type_get_icon(content_type), size, size_text,
                                  modified, modified_text, type_description(content_type)))
                    if len(batch) == 100:
                        send(batch)
                        batch = []
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
        status.set_text((tr("已停止", "Stopped") if cancel.is_set() else tr("搜索完成", "Search complete"))
                        + tr(f" · {count} 个结果", f" · {count} results"))
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


def show_properties(target):
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call_sync("org.freedesktop.FileManager1", "/org/freedesktop/FileManager1",
                      "org.freedesktop.FileManager1", "ShowItemProperties",
                      GLib.Variant("(ass)", ([target.as_uri()], "")), None,
                      Gio.DBusCallFlags.NONE, 5000, None)
    except GLib.Error as exc:
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
    show_properties(Path(directory, name))
    return True


def result_menu(event=None):
    selected_model, row = results.get_selection().get_selected()
    if row is None:
        return False
    name, directory, *_ = selected_model[row]
    menu = Gtk.Menu()
    menu.attach_to_widget(results, None)
    for label, target in [(tr("打开", "Open"), Path(directory, name)),
                          (tr("打开所在文件夹", "Open Containing Folder"), Path(directory))]:
        item = Gtk.MenuItem(label=label)
        item.connect("activate", lambda _, path=target: launch_path(path))
        menu.append(item)
    menu.append(Gtk.SeparatorMenuItem())
    properties = Gtk.MenuItem(label=tr("属性", "Properties"))
    properties.connect("activate", lambda _: show_properties(Path(directory, name)))
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
