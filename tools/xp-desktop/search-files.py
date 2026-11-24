#!/usr/bin/python3
import fnmatch
import os
import threading
from pathlib import Path
from queue import Empty, Full, Queue

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk

zh = GLib.get_language_names()[0].startswith("zh")


def tr(chinese, english):
    return chinese if zh else english


window = Gtk.Window(title=tr("搜索结果", "Search Results"))
window.set_icon_name("system-search")
display = window.get_display()
area = (display.get_primary_monitor() or display.get_monitor(0)).get_workarea()
window.set_default_size(min(800, area.width - 24), min(540, area.height - 64))
layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
window.add(layout)
panes = Gtk.Paned()
layout.pack_start(panes, True, True, 0)
sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=12)
panes.pack1(sidebar, False, False)
header = Gtk.Label(xalign=0)
header.set_markup("<b>" + tr("搜索助理", "Search Companion") + "</b>")
sidebar.add(header)
sidebar.add(Gtk.Label(label=tr("全部或部分文件名", "All or part of the file name"), xalign=0))
query = Gtk.Entry()
sidebar.add(query)
sidebar.add(Gtk.Label(label=tr("寻找范围", "Look in"), xalign=0))
folder = Gtk.FileChooserButton(title=tr("选择文件夹", "Choose Folder"),
                               action=Gtk.FileChooserAction.SELECT_FOLDER)
folder.set_current_folder(str(Path.home()))
folder.set_filename(str(Path.home()))
sidebar.add(folder)
buttons = Gtk.ButtonBox()
start = Gtk.Button(label=tr("搜索", "Search"))
stop = Gtk.Button(label=tr("停止", "Stop"))
stop.set_sensitive(False)
buttons.add(start)
buttons.add(stop)
sidebar.add(buttons)
model = Gtk.ListStore(str, str)
results = Gtk.TreeView(model=model)
for i, title in enumerate([tr("名称", "Name"), tr("所在文件夹", "In Folder")]):
    column = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)
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
            for name in folders + files:
                if cancel.is_set():
                    return
                if fnmatch.fnmatchcase(name.casefold(), pattern):
                    batch.append((name, directory))
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
    name, directory = model[path]
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
