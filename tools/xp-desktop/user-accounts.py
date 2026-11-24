#!/usr/bin/python3
import os
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, Gio, GLib, Gtk

def tr(zh, en):
    return zh if os.getenv("LANGUAGE", os.getenv("LANG", "")).startswith("zh") else en

def call(path, interface, method, params=None):
    return bus.call_sync("org.freedesktop.Accounts", path, interface, method, params,
                         None, Gio.DBusCallFlags.NONE, 3000, None).unpack()[0]

window = Gtk.Window(title=tr("用户帐户", "User Accounts"), border_width=18)
window.set_icon_name("preferences-desktop-personal")
window.set_default_size(550, 290)
window.connect("destroy", Gtk.main_quit)
page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
window.add(page)
heading = Gtk.Label(xalign=0)
heading.set_markup("<span size='x-large' foreground='#274596'><b>" +
                   tr("选择一个帐户", "Pick an account") + "</b></span>")
page.pack_start(heading, False, False, 0)
scroll = Gtk.ScrolledWindow()
scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
cards = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
scroll.add(cards)
page.pack_start(scroll, True, True, 0)

def manage(_button):
    subprocess.Popen(["/usr/bin/ukui-control-center", "-p", "userinfo"])

def change_picture(path, image):
    chooser = Gtk.FileChooserDialog(title=tr("选择帐户图片", "Choose an account picture"),
                                    transient_for=window, action=Gtk.FileChooserAction.OPEN)
    chooser.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    chooser.add_button(tr("使用此图片", "Use this picture"), Gtk.ResponseType.OK)
    formats = Gtk.FileFilter()
    formats.set_name(tr("图片", "Pictures"))
    formats.add_pixbuf_formats()
    chooser.add_filter(formats)
    thumbnail = Gtk.Image()
    chooser.set_preview_widget(thumbnail)
    chooser.set_use_preview_label(False)
    feedback = Gtk.Label(xalign=0, wrap=True)
    chooser.set_extra_widget(feedback)
    feedback.show()

    def update_preview(widget):
        filename = widget.get_preview_filename()
        thumbnail.clear()
        feedback.set_text("")
        if filename and Path(filename).is_file():
            try:
                thumbnail.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(filename, 128, 128, True))
            except GLib.Error:
                feedback.set_text(tr("无法读取这张图片，请选择其他文件。", "Cannot read this picture. Choose another file."))
        widget.set_preview_widget_active(thumbnail.get_pixbuf() is not None)

    chooser.connect("update-preview", update_preview)
    try:
        while chooser.run() == Gtk.ResponseType.OK:
            filename = chooser.get_filename()
            if filename:
                try:
                    preview = GdkPixbuf.Pixbuf.new_from_file_at_scale(filename, 64, 64, True)
                    break
                except GLib.Error:
                    feedback.set_text(tr("无法读取这张图片，请选择其他文件。", "Cannot read this picture. Choose another file."))
        else:
            return
    finally:
        chooser.destroy()
    try:
        bus.call_sync("org.freedesktop.Accounts", path, "org.freedesktop.Accounts.User", "SetIconFile",
                      GLib.Variant("(s)", (filename,)), None,
                      Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION, 30000, None)
        image.set_from_pixbuf(preview)
    except GLib.Error as error:
        notice = Gtk.MessageDialog(transient_for=window, modal=True, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE, text=tr("无法更改帐户图片", "Could not change the account picture"))
        notice.format_secondary_text(error.message)
        notice.run()
        notice.destroy()


def change_name(card, user, path, label, caption):
    dialog = Gtk.Dialog(title=tr("更改帐户名称", "Change account name"), transient_for=window, modal=True)
    dialog.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    save = dialog.add_button(tr("更改名称", "Change name"), Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)
    box = dialog.get_content_area()
    box.set_border_width(12)
    box.set_spacing(8)
    box.add(Gtk.Label(label=tr("输入要显示在登录界面的名称。", "Enter the name to display on the logon screen."), xalign=0))
    original = user.get("RealName") or user["UserName"]
    entry = Gtk.Entry(text=original, activates_default=True)
    box.add(entry)
    feedback = Gtk.Label(xalign=0, wrap=True)
    box.add(feedback)
    entry.connect("changed", lambda field: save.set_sensitive(field.get_text().strip() not in ("", original)))
    save.set_sensitive(False)
    dialog.show_all()
    entry.grab_focus()
    entry.select_region(0, -1)
    try:
        while dialog.run() == Gtk.ResponseType.OK:
            name = entry.get_text().strip()
            if not name or name == original:
                continue
            try:
                bus.call_sync("org.freedesktop.Accounts", path, "org.freedesktop.Accounts.User", "SetRealName",
                              GLib.Variant("(s)", (name,)), None,
                              Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION, 30000, None)
            except GLib.Error as error:
                feedback.set_text(error.message)
                continue
            user["RealName"] = caption[0] = name
            label.set_text("\n".join(caption))
            card.get_accessible().set_name(" · ".join(caption))
            break
    finally:
        dialog.destroy()


def show_details(card, user, role, path, image, label, caption):
    detail = Gtk.MessageDialog(transient_for=window, modal=True,
                               text=user.get("RealName") or user["UserName"], buttons=Gtk.ButtonsType.CLOSE)
    fields = [(tr("登录名", "Login name"), user["UserName"]),
              (tr("帐户类型", "Account type"), role),
              (tr("主文件夹", "Home folder"), user["HomeDirectory"])]
    if user.get("Locked"):
        fields.append((tr("帐户状态", "Account status"), tr("已锁定", "Locked")))
    detail.format_secondary_text("\n".join(label + " · " + value for label, value in fields))
    if user["Uid"] == os.getuid():
        detail.add_button(tr("更改名称…", "Change name…"), 2)
        detail.add_button(tr("更改图片…", "Change picture…"), 1)
        detail.add_button(tr("管理帐户…", "Manage account…"), Gtk.ResponseType.APPLY)
    response = detail.run()
    detail.destroy()
    if response == 1:
        change_picture(path, image)
    elif response == 2:
        change_name(card, user, path, label, caption)
    elif response == Gtk.ResponseType.APPLY:
        manage(None)

try:
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    for path in call("/org/freedesktop/Accounts", "org.freedesktop.Accounts", "ListCachedUsers"):
        user = call(path, "org.freedesktop.DBus.Properties", "GetAll",
                    GLib.Variant("(s)", ("org.freedesktop.Accounts.User",)))
        if user["SystemAccount"]:
            continue
        role = tr("计算机管理员", "Computer administrator") if user["AccountType"] == 1 else tr("标准用户", "Standard user")
        card = Gtk.Button()
        row = Gtk.Box(spacing=14, border_width=8)
        card.add(row)
        image = Gtk.Image.new_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
        picture = Path(user["IconFile"] or "/nonexistent")
        if not picture.is_file() and user["Uid"] == os.getuid():
            picture = Path.home() / ".face"
        if picture.is_file():
            try:
                image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(picture), 64, 64, True))
            except GLib.Error:
                pass
        row.add(image)
        name = user.get("RealName") or user["UserName"]
        caption = [name, role]
        if user["Uid"] == os.getuid():
            caption.append(tr("当前帐户", "Current account"))
        if user.get("Locked"):
            caption.append(tr("已锁定", "Locked"))
        label = Gtk.Label(label="\n".join(caption), xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        row.add(label)
        card.get_accessible().set_name(" · ".join(caption))
        card.connect("clicked", show_details, user, role, path, image, label, caption)
        cards.pack_start(card, False, False, 0)
except GLib.Error as error:
    cards.add(Gtk.Label(label=error.message, xalign=0, wrap=True))
settings = Gtk.Button(label=tr("管理用户帐户…", "Manage user accounts…"))
settings.connect("clicked", manage)
page.pack_end(settings, False, False, 0)
window.show_all()
Gtk.main()
