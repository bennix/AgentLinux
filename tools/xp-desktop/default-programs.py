#!/usr/bin/python3
from gi.repository import GLib
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk

zh = GLib.get_language_names()[0].startswith("zh")
window = Gtk.Dialog(title="设置程序访问和默认值" if zh else "Set Program Access and Defaults")
window.set_icon_name("preferences-desktop-default-applications")
grid = Gtk.Grid(column_spacing=16, row_spacing=10, border_width=16)
window.get_content_area().add(grid)
window.add_button("关闭(_C)" if zh else "_Close", Gtk.ResponseType.CLOSE)


def choose(combo, content_type):
    app = combo.get_app_info()
    if app:
        try:
            app.set_as_default_for_type(content_type)
        except GLib.Error as error:
            dialog = Gtk.MessageDialog(transient_for=window, modal=True, message_type=Gtk.MessageType.ERROR,
                                       buttons=Gtk.ButtonsType.CLOSE, text=error.message)
            dialog.run()
            dialog.destroy()
            combo.refresh()


for row, (cn, en, mime) in enumerate([
    ("网页链接（HTTP_S）", "Web links (HTTP_S)", "x-scheme-handler/https"),
    ("网页链接（_HTTP）", "Web links (_HTTP)", "x-scheme-handler/http"),
    ("电子邮件(_E)", "_Email", "x-scheme-handler/mailto"),
    ("文本文档(_T)", "_Text documents", "text/plain"),
    ("_PDF 文档", "_PDF documents", "application/pdf"),
]):
    label = cn if zh else en
    caption = Gtk.Label(label=label, use_underline=True, xalign=0)
    grid.attach(caption, 0, row, 1, 1)
    choice = Gtk.AppChooserButton.new(mime)
    choice.set_show_default_item(True)
    choice.set_show_dialog_item(True)
    caption.set_mnemonic_widget(choice)
    choice.get_accessible().set_name(caption.get_text())
    choice.set_hexpand(True)
    grid.attach(choice, 1, row, 1, 1)
    choice.connect("changed", choose, mime)

window.connect("response", lambda dialog, _response: dialog.destroy())
window.connect("destroy", Gtk.main_quit)
window.show_all()
Gtk.main()
