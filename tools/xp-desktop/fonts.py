#!/usr/bin/python3

import os
from pathlib import Path

from task_pane import fit_window

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango

chinese = GLib.get_language_names()[0].startswith("zh")
window = Gtk.Window(title="字体" if chinese else "Fonts")
window.set_icon_name("preferences-desktop-font")
fit_window(window, 600, 480)
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=10)
window.add(box)
chooser = Gtk.FontChooserWidget()
chooser.set_font("Noto Serif CJK SC 16")
chooser.set_preview_text("春风又绿江南岸　AaBbCc　0123456789")
scroll = Gtk.ScrolledWindow()
scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
scroll.set_propagate_natural_height(True)
scroll.add(chooser)
box.pack_start(scroll, True, True, 0)
def preview_candidates(_button):
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    font = "Noto Serif CJK SC 12"
    try:
        for line in (config / "fcitx5/conf/classicui.conf").read_text().splitlines():
            if line.strip().startswith("["):
                break
            key, _, value = line.partition("=")
            if key.strip() == "Font" and value.strip():
                font = value.strip()
    except OSError:
        pass
    chooser.set_font(font)
    chooser.set_preview_text("1 你好　2 拟好　3 你号")


def show_sample(*_):
    font = chooser.get_font_desc()
    if font is None:
        return
    dialog = Gtk.Dialog(title=font.get_family(), transient_for=window, modal=True)
    dialog.add_button("关闭" if chinese else "Close", Gtk.ResponseType.CLOSE)
    dialog.set_default_size(560, 320)
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    dialog.get_content_area().pack_start(scroll, True, True, 0)
    sheet = Gtk.Grid(row_spacing=8, column_spacing=12, border_width=12)
    sheet.set_name("font-sample-sheet")
    style = Gtk.CssProvider()
    style.load_from_data(b"#font-sample-sheet { background-color: white; } #font-sample-sheet label { color: #181818; }")
    Gtk.StyleContext.add_provider_for_screen(window.get_screen(), style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    scroll.add(sheet)
    face = chooser.get_font_face()
    header = Gtk.Label(xalign=0, selectable=True)
    family = GLib.markup_escape_text(font.get_family())
    style_name = GLib.markup_escape_text(face.get_face_name()) if face else ""
    header.set_markup(f"<big><b>{family}</b></big>  {style_name}")
    sheet.attach(header, 0, 0, 2, 1)
    sheet.attach(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), 0, 1, 2, 1)
    characters = Gtk.Label(
        label="abcdefghijklmnopqrstuvwxyz\nABCDEFGHIJKLMNOPQRSTUVWXYZ\n0123456789.:,;!?",
        xalign=0, selectable=True,
    )
    alphabet_font = font.copy()
    alphabet_font.set_size(14 * Pango.SCALE)
    alphabet_attrs = Pango.AttrList()
    alphabet_attrs.insert(Pango.attr_font_desc_new(alphabet_font))
    characters.set_attributes(alphabet_attrs)
    sheet.attach(characters, 0, 2, 2, 1)
    for row, size in enumerate((10, 12, 16, 18, 24, 32, 36, 48, 60, 72), start=3):
        sheet.attach(Gtk.Label(label=f"{size} pt", xalign=1), 0, row, 1, 1)
        sample = Gtk.Label(label=chooser.get_preview_text(), xalign=0, selectable=True)
        sample.set_line_wrap(True)
        sample.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        sample.set_hexpand(True)
        desc = font.copy()
        desc.set_size(size * Pango.SCALE)
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_font_desc_new(desc))
        sample.set_attributes(attrs)
        sheet.attach(sample, 1, row, 1, 1)
    dialog.set_destroy_with_parent(True)
    dialog.connect("response", lambda widget, _response: widget.destroy())
    dialog.connect("destroy", lambda widget: Gtk.StyleContext.remove_provider_for_screen(widget.get_screen(), style))
    dialog.show_all()


chooser.connect("font-activated", show_sample)
actions = Gtk.Box(spacing=8)
box.pack_end(actions, False, False, 0)
candidate = Gtk.Button(label="预览输入法候选字体（默认宋体）" if chinese else "Preview input method font (Song style by default)")
candidate.connect("clicked", preview_candidates)
actions.pack_start(candidate, False, False, 0)
preview = Gtk.Button(label="字体样张…" if chinese else "Font sample…")
preview.connect("clicked", show_sample)
actions.pack_start(preview, False, False, 0)
close = Gtk.Button.new_with_mnemonic("关闭(_C)" if chinese else "_Close")
close.set_halign(Gtk.Align.END)
close.connect("clicked", lambda _: window.close())
actions.pack_end(close, False, False, 0)
window.connect("destroy", Gtk.main_quit)
window.show_all()
Gtk.main()
