#!/usr/bin/python3
import subprocess
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from task_pane import cycle_property_pages

def tr(zh, en):
    return zh if GLib.get_language_names()[0].startswith("zh") else en

helper = Path(__file__).with_name("accesskeys")
saved = Path.home() / ".config/agentlinux-xp/accesskeys"
state = int(subprocess.check_output([helper]))
dialog = Gtk.Dialog(title=tr("辅助功能选项", "Accessibility Options"))
dialog.set_icon_name("preferences-desktop-accessibility")
dialog.set_default_size(420, 290)
for label, code in [(tr("确定", "OK"), Gtk.ResponseType.OK),
                    (tr("取消", "Cancel"), Gtk.ResponseType.CANCEL),
                    (tr("应用", "Apply"), Gtk.ResponseType.APPLY)]:
    dialog.add_button(label, code)
tabs = Gtk.Notebook(border_width=8)
dialog.connect("key-press-event", cycle_property_pages, tabs)
dialog.get_content_area().add(tabs)
options = {}
for label, rows in [
    (tr("键盘", "Keyboard"), [(8, tr("使用粘滞键", "Use StickyKeys")),
                              (2, tr("使用慢速键", "Use SlowKeys")),
                              (4, tr("忽略快速重复按键", "Use BounceKeys"))]),
    (tr("鼠标", "Mouse"), [(16, tr("使用数字键盘移动鼠标指针", "Use the numeric keypad to move the mouse pointer"))])
]:
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, border_width=16)
    tabs.append_page(page, Gtk.Label(label=label))
    for bit, title in rows:
        button = Gtk.CheckButton(label=title)
        button.set_active(bool(state & bit))
        page.add(button)
        options[bit] = button
feedback = Gtk.Label(xalign=0, wrap=True)
dialog.get_content_area().add(feedback)
apply_button = dialog.get_widget_for_response(Gtk.ResponseType.APPLY)


def requested():
    return sum(bit for bit, button in options.items() if button.get_active())


def update_pending(*_):
    apply_button.set_sensitive(requested() != state)


for button in options.values():
    button.connect("toggled", update_pending)
update_pending()
dialog.show_all()
if sys.argv[1:] == ["3"]:
    tabs.set_current_page(1)
while True:
    response = dialog.run()
    if response not in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK):
        break
    value = requested()
    if value != state:
        try:
            actual = int(subprocess.check_output([helper, str(value)]))
            if actual != value:
                raise ValueError(tr("无法应用键盘设置", "Could not apply keyboard settings"))
            saved.parent.mkdir(parents=True, exist_ok=True)
            GLib.file_set_contents(str(saved), str(actual).encode())
        except (OSError, ValueError, GLib.Error, subprocess.SubprocessError) as error:
            feedback.set_text(str(error))
            continue
        state = actual
        feedback.set_text("")
        update_pending()
    if response == Gtk.ResponseType.OK:
        break
dialog.destroy()
