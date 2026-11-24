#!/usr/bin/python3
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk

zh = GLib.get_language_names()[0].startswith("zh")
window = Gtk.Window(title="搜索文件和文件夹" if zh else "Search for Files and Folders")
window.set_icon_name("system-search")
monitor = window.get_display().get_primary_monitor() or window.get_display().get_monitor(0)
area = monitor.get_workarea()
window.set_default_size(min(760, area.width - 24), min(520, area.height - 64))
chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN)
chooser.set_current_folder(str(Path.home()))
window.add(chooser)


def open_result(widget):
    uri = widget.get_uri()
    if uri:
        try:
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except GLib.Error as exc:
            dialog = Gtk.MessageDialog(transient_for=window, modal=True, message_type=Gtk.MessageType.ERROR,
                                       buttons=Gtk.ButtonsType.CLOSE, text=exc.message)
            dialog.run()
            dialog.destroy()


chooser.connect("file-activated", open_result)
window.connect("destroy", Gtk.main_quit)
window.show_all()
chooser.set_property("search-mode", True)
Gtk.main()
