#!/usr/bin/python3
import fnmatch
import os
import threading
from pathlib import Path
from queue import Empty, Full, Queue

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk

from task_pane import add_task_pane, fit_window

zh = GLib.get_language_names()[0].startswith("zh")


def tr(chinese, english):
    return chinese if zh else english


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
model = Gtk.ListStore(str, str, Gio.Icon)
results = Gtk.TreeView(model=model)
for i, title in enumerate([tr("名称", "Name"), tr("所在文件夹", "In Folder")]):
    column = Gtk.TreeViewColumn(title)
    if i == 0:
        icon = Gtk.CellRendererPixbuf()
        column.pack_start(icon, False)
        column.add_attribute(icon, "gicon", 2)
    text = Gtk.CellRendererText()
    column.pack_start(text, True)
    column.add_attribute(text, "text", i)
    column.set_resizable(True)
    column.set_sort_column_id(i)
    results.append_column(column)
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
                    batch.append((name, directory, Gio.content_type_get_icon(content_type)))
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
    name, directory, _icon = model[path]
    try:
        Gio.AppInfo.launch_default_for_uri(Path(directory, name).as_uri(), None)
    except GLib.Error as exc:
        dialog = Gtk.MessageDialog(transient_for=window, modal=True, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE, text=exc.message)
        dialog.run()
        dialog.destroy()


start.connect("clicked", search)
query.connect("activate", search)
stop.connect("clicked", lambda _: active and active.set())
results.connect("row-activated", open_result)
window.connect("destroy", Gtk.main_quit)
window.show_all()
query.grab_focus()
Gtk.main()
