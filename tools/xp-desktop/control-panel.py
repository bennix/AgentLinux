#!/usr/bin/python3
import configparser
import os
import sys
import tempfile
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from task_pane import cycle_property_pages

home = Path.home()
config = home / ".config/agentlinux-xp"
chinese = GLib.get_language_names()[0].startswith("zh")


def tr(zh, en):
    return zh if chinese else en


def write_setting(path, writer):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as tmp:
        writer(tmp)
    os.replace(tmp.name, path)


def folder_options(_button):
    settings = Gio.Settings.new("org.ukui.peony.settings")
    settings.delay()
    dialog = Gtk.Dialog(title=tr("文件夹选项", "Folder Options"), transient_for=window, modal=True)
    dialog.add_button(tr("确定", "OK"), Gtk.ResponseType.OK)
    dialog.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    apply = dialog.add_button(tr("应用(_A)", "_Apply"), Gtk.ResponseType.APPLY)
    apply.set_use_underline(True)
    notebook = Gtk.Notebook(border_width=8)
    dialog.connect("key-press-event", cycle_property_pages, notebook)
    click_file = Path(GLib.get_user_config_dir()) / "agentlinux-xp/explorer-single-click"
    click_available = Path(__file__).with_name("explorer-lib").joinpath("libwintc-comctl.so.1").is_file()
    if click_available:
        general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=12)
        notebook.append_page(general, Gtk.Label(label=tr("常规", "General")))
        click_scope = tr("新打开的 XP 资源管理器窗口", "New XP Explorer windows")
        if Path(__file__).with_name("peony-qt-desktop").is_file():
            click_scope = tr("桌面图标及新打开的 XP 资源管理器窗口", "Desktop icons and new XP Explorer windows")
        frame = Gtk.Frame(label=tr("打开项目的方式", "Click items as follows"))
        choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, border_width=8)
        general.add(frame)
        frame.add(choices)
        choices.set_tooltip_text(click_scope)
        single = Gtk.RadioButton.new_with_label_from_widget(None, tr("单击打开项目", "Single-click to open an item"))
        double = Gtk.RadioButton.new_with_label_from_widget(single, tr("双击打开项目", "Double-click to open an item"))
        choices.add(single)
        choices.add(double)
        reset_click = Gtk.Button(label=tr("还原默认值", "Restore Defaults"))
        reset_click.set_halign(Gtk.Align.END)
        reset_click.connect("clicked", lambda _button: double.set_active(True))
        general.pack_end(reset_click, False, False, 0)
        (single if click_file.exists() else double).set_active(True)
    panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, border_width=12)
    notebook.append_page(panel, Gtk.Label(label=tr("查看", "View")))
    dialog.get_content_area().add(notebook)
    panel.add(Gtk.Label(label=tr("高级设置", "Advanced settings"), xalign=0))
    hidden_group = Gtk.Frame(label=tr("隐藏文件和文件夹", "Hidden files and folders"))
    hidden_choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, border_width=6)
    hidden_group.add(hidden_choices)
    hide = Gtk.RadioButton.new_with_mnemonic_from_widget(None, tr("不显示隐藏文件和文件夹(_D)", "_Do not show hidden files and folders"))
    show_hidden = Gtk.RadioButton.new_with_mnemonic_from_widget(hide, tr("显示隐藏文件和文件夹(_S)", "_Show hidden files and folders"))
    hidden_choices.add(hide)
    hidden_choices.add(show_hidden)
    panel.add(hidden_group)
    settings.bind("show-hidden-file", show_hidden, "active", Gio.SettingsBindFlags.DEFAULT)
    settings.bind_writable("show-hidden-file", hidden_group, "sensitive", False)
    options = [
        ("show-file-extension", tr("隐藏文件扩展名", "Hide file extensions"), True),
        ("do-not-thumbnail", tr("显示缩略图", "Show thumbnails"), True),
        ("show-trash-dialog", tr("移入回收站前显示确认对话框", "Ask before moving items to the Recycle Bin"), False),
        ("folder-first", tr("文件夹排在文件前面", "List folders before files"), False),
    ]
    for key, label, inverted in options:
        check = Gtk.CheckButton(label=label)
        flags = Gio.SettingsBindFlags.DEFAULT
        if inverted:
            flags |= Gio.SettingsBindFlags.INVERT_BOOLEAN
        settings.bind(key, check, "active", flags)
        panel.add(check)
    def restore_defaults(_button):
        if settings.is_writable("show-hidden-file"):
            settings.reset("show-hidden-file")
        for key, _, _ in options:
            if settings.is_writable(key):
                settings.reset(key)

    restore = Gtk.Button(label=tr("还原默认值", "Restore Defaults"))
    restore.set_halign(Gtk.Align.END)
    restore.connect("clicked", restore_defaults)
    panel.pack_end(restore, False, False, 0)
    apply.set_sensitive(False)
    def update_apply(*_):
        apply.set_sensitive(settings.get_has_unapplied() or
                            (click_available and single.get_active() != click_file.exists()))

    if click_available:
        single.connect("toggled", update_apply)
    settings.connect("notify::has-unapplied", update_apply)
    dialog.set_default_size(370, 250)
    dialog.show_all()
    while True:
        response = dialog.run()
        if response in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK):
            if click_available and single.get_active() != click_file.exists():
                try:
                    if single.get_active():
                        click_file.parent.mkdir(parents=True, exist_ok=True)
                        click_file.touch()
                    else:
                        click_file.unlink(missing_ok=True)
                except OSError as error:
                    notice = Gtk.MessageDialog(transient_for=dialog, modal=True, message_type=Gtk.MessageType.ERROR,
                                               buttons=Gtk.ButtonsType.CLOSE, text=str(error))
                    notice.run()
                    notice.destroy()
                    continue
            settings.apply()
            update_apply()
        if response != Gtk.ResponseType.APPLY:
            break
    settings.revert()
    dialog.destroy()


def language(_button):
    dialog = Gtk.Dialog(title=tr("界面语言 / Display Language", "Display Language / 界面语言"),
                        transient_for=window, modal=True)
    dialog.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    dialog.add_button(tr("确定(_O)", "_OK"), Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)
    box = dialog.get_content_area()
    box.set_border_width(14)
    box.set_spacing(10)
    current = "zh_CN.UTF-8" if chinese else "en_US.UTF-8"
    box.add(Gtk.Label(label=tr("当前界面语言：简体中文", "Current display language: English"), xalign=0))
    caption = Gtk.Label.new_with_mnemonic(tr("此账户的桌面语言(_L)", "_Language for this account"))
    caption.set_xalign(0)
    box.add(caption)
    choice = Gtk.ComboBoxText()
    caption.set_mnemonic_widget(choice)
    choice.append("zh_CN.UTF-8", "简体中文")
    choice.append("en_US.UTF-8", "English")
    selected = config / "language"
    try:
        saved = selected.read_text().strip()
    except (OSError, UnicodeError):
        saved = current
    choice.set_active_id(saved if saved in ("zh_CN.UTF-8", "en_US.UTF-8") else current)
    box.add(choice)
    hint = Gtk.Label(xalign=0, wrap=True)
    def update_hint(*_):
        zh_hint = "下次登录后，桌面将使用所选语言。"
        en_hint = "Your desktop will use this language the next time you sign in."
        message = tr(zh_hint + "\n" + en_hint, en_hint + "\n" + zh_hint)
        hint.set_text(message if choice.get_active_id() != current else "")
    choice.connect("changed", update_hint)
    update_hint()
    box.add(hint)
    dialog.show_all()
    if dialog.run() == Gtk.ResponseType.OK:
        locale = choice.get_active_id()
        if locale in ("zh_CN.UTF-8", "en_US.UTF-8"):
            config.mkdir(parents=True, exist_ok=True)
            dmrc = configparser.RawConfigParser()
            dmrc.optionxform = str
            dmrc.read(home / ".dmrc")
            if not dmrc.has_section("Desktop"):
                dmrc.add_section("Desktop")
            dmrc.set("Desktop", "Language", locale)
            write_setting(home / ".dmrc", dmrc.write)
            write_setting(selected, lambda file: file.write(locale + "\n"))
    dialog.destroy()


window = Gtk.Window(title=tr("控制面板", "Control Panel"))
window.set_icon_name("preferences-system")
window.set_name("xp-control")
grid = Gtk.FlowBox(column_spacing=8, row_spacing=6, homogeneous=True)
grid.set_selection_mode(Gtk.SelectionMode.NONE)
grid.set_min_children_per_line(1)
grid.set_valign(Gtk.Align.START)
scroll = Gtk.ScrolledWindow()
scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
scroll.add(grid)
layout = Gtk.Box()
window.add(layout)
nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=10)
nav.set_name("xp-nav")
layout.pack_start(nav, False, False, 0)
section = Gtk.Label(label=tr("控制面板", "Control Panel"), xalign=0)
section.set_name("xp-task-title")
nav.pack_start(section, False, False, 0)
content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=12)
layout.pack_start(content, True, True, 0)
heading = Gtk.Label(xalign=0)
content.pack_start(heading, False, False, 0)
back = Gtk.Button(label=tr("返回分类首页", "Back to categories"))
switch = Gtk.Button()
nav.pack_start(switch, False, False, 0)
nav.pack_start(back, False, False, 0)
content.pack_start(scroll, True, True, 0)
display = window.get_display()
monitor = display.get_primary_monitor() or display.get_monitor(0)
workarea = monitor.get_workarea()
window.set_default_size(min(800, workarea.width - 24), min(500, workarea.height - 64))
provider = Gtk.CssProvider()
provider.load_from_data(b"""
#xp-control { background-color: #f2f5fc; }
#xp-control.classic-view { background-color: white; }
#xp-control.classic-view #xp-icon {
    background: transparent; border-color: transparent; box-shadow: none;
}
#xp-control.classic-view #xp-icon:focus label {
    color: white; background-color: #316ac5;
    outline: 1px dotted #182b4a; outline-offset: 0;
}
#xp-nav { background-image: linear-gradient(to bottom, #7698e7, #647ed4); }
#xp-task-title { background-color: #e5ecfb; color: #174481; font-weight: bold; padding: 7px; }
#xp-nav button { color: #183e82; }
#xp-category, #xp-category:hover, #xp-category:active,
#xp-control:not(.classic-view) #xp-icon {
    background: transparent; border-color: transparent; box-shadow: none;
}
#xp-category label, #xp-control:not(.classic-view) #xp-icon label { color: #174481; }
#xp-category:hover label, #xp-control:not(.classic-view) #xp-icon:hover label { text-decoration: underline; }
#xp-category:focus label, #xp-control:not(.classic-view) #xp-icon:focus label {
    outline: 1px dotted #174481; outline-offset: 1px;
}
""")
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
entries = [
    ("添加或删除程序", "Add or Remove Programs", "system-software-install", "agentlinux-xp-programs.desktop"),
    ("鼠标", "Mouse", "input-mouse", "agentlinux-xp-mouse.desktop"),
    ("键盘", "Keyboard", "input-keyboard", "agentlinux-xp-keyboard.desktop"),
    ("声音和音频设备", "Sounds and Audio Devices", "audio-card", "agentlinux-xp-audio.desktop"),
    ("日期和时间", "Date and Time", "appointment-new", "agentlinux-xp-datetime.desktop"),
    ("电源选项", "Power Options", "battery", "agentlinux-xp-power.desktop"),
    ("用户帐户", "User Accounts", "preferences-desktop-personal", "agentlinux-xp-userinfo.desktop"),
    ("文件夹选项", "Folder Options", "folder", None),
    ("字体", "Fonts", "preferences-desktop-font", "agentlinux-xp-fonts.desktop"),
    ("辅助功能选项", "Accessibility Options", "preferences-desktop-accessibility", "agentlinux-xp-access.desktop"),
    ("显示属性", "Display Properties", "preferences-desktop-display", "agentlinux-xp-display.desktop"),
    ("无线网络连接", "Wireless Network Connection", "network-wireless", "agentlinux-xp-wifi.desktop"),
    ("管理工具", "Administrative Tools", "preferences-system", "agentlinux-xp-admin.desktop"),
    ("网上邻居", "My Network Places", "network-workgroup", "agentlinux-xp-places.desktop"),
    ("共享文件夹", "Shared Folders", "folder-publicshare", "agentlinux-xp-shares.desktop"),
    ("网络连接", "Network Connections", "preferences-system-network", "agentlinux-xp-connections.desktop"),
    ("系统网络", "System Network", "network-wired", "agentlinux-system-network.desktop"),
    ("输入法", "Input Method", "preferences-desktop-keyboard", "myime-settings.desktop"),
    ("添加打印机", "Add Printer", "gnome-dev-printer-new", "agentlinux-xp-add-printer.desktop"),
    ("打印机和传真", "Printers and Faxes", "printer", "agentlinux-xp-printers.desktop"),
    ("系统设置", "System Settings", "preferences-system", "agentlinux-xp-settings.desktop"),
    ("系统", "System", "computer", "agentlinux-xp-system.desktop"),
    ("任务管理器", "Task Manager", "utilities-system-monitor", "agentlinux-xp-taskmgr.desktop"),
    ("界面语言 / Language", "Language / 界面语言", "preferences-desktop-locale", None),
]
categories = [
    ("外观和主题", "Appearance and Themes", ["Display Properties", "Folder Options", "Fonts"], "control_appearance"),
    ("打印机和其他硬件", "Printers and Other Hardware", ["Printers and Faxes", "Add Printer", "Mouse", "Keyboard"], "hardware"),
    ("网络和 Internet 连接", "Network and Internet Connections", ["Wireless Network Connection", "Network Connections", "My Network Places", "Shared Folders", "System Network"], "net_internet"),
    ("用户帐户", "User Accounts", ["User Accounts"], "people"),
    ("添加或删除程序", "Add or Remove Programs", ["Add or Remove Programs"], "file_generic_installer"),
    ("日期、时间、语言和区域设置", "Date, Time, Language, and Regional Options", ["Date and Time", "Language / 界面语言", "Input Method"], "calendar"),
    ("声音和音频设备", "Sounds and Audio Devices", ["Sounds and Audio Devices"], "volume_on"),
    ("辅助功能选项", "Accessibility Options", ["Accessibility Options"], "accessibility"),
    ("性能和维护", "Performance and Maintenance", ["System", "Power Options", "Administrative Tools", "Task Manager", "System Settings"], "settings"),
]
by_name = {entry[1]: entry for entry in entries}
preference = Path(GLib.get_user_config_dir()) / "agentlinux-xp/control-panel-view"
classic = preference.exists() and preference.read_text().strip() == "classic"


luna_icons = {
    "system-software-install": "file_generic_installer", "preferences-desktop-display": "control_display",
    "network-wireless": "net_wireless", "audio-card": "volume_on", "printer": "printer",
    "gnome-dev-printer-new": "printer",
    "computer": "laptop", "preferences-desktop-personal": "people", "appointment-new": "calendar",
    "preferences-desktop-accessibility": "accessibility", "input-mouse": "mouse",
    "preferences-desktop-font": "file_ttf", "preferences-system-network": "net_lan",
    "input-keyboard": "keyboard", "preferences-desktop-keyboard": "keyboard_shortcuts",
    "battery": "ac_power", "utilities-system-monitor": "monitor",
    "preferences-desktop-locale": "net_internet",
    "folder": "folder", "folder-publicshare": "folder_shared",
    "network-wired": "net_connections", "network-workgroup": "net_places", "preferences-system": "settings",
}


def tile(label, icon, resource=None):
    button = Gtk.Button()
    button.get_accessible().set_name(label)
    button.set_tooltip_text(label)
    caption = Gtk.Label(label=label, xalign=0)
    caption.set_halign(Gtk.Align.START)
    caption.set_line_wrap(True)
    caption.set_max_width_chars(16 if classic else 22)
    button.set_relief(Gtk.ReliefStyle.NONE)
    resource = resource or luna_icons.get(icon)
    image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
    for size in ("48x48", "32x32"):
        path = Path("/usr/share/icons/luna/res") / size / f"{resource}.png"
        if path.is_file():
            image.set_from_file(str(path))
            if icon == "gnome-dev-printer-new":
                badge = path.parents[1] / "16x16/add.png"
                if badge.is_file():
                    overlay = Gtk.Overlay()
                    overlay.add(image)
                    plus = Gtk.Image.new_from_file(str(badge))
                    plus.set_halign(Gtk.Align.END)
                    plus.set_valign(Gtk.Align.END)
                    overlay.add_overlay(plus)
                    image = overlay
            break
    image.set_size_request(48, 48)
    contents = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if classic else Gtk.Orientation.HORIZONTAL, spacing=6)
    image.set_halign(Gtk.Align.START)
    contents.pack_start(image, False, False, 0)
    contents.pack_start(caption, False, False, 0)
    button.add(contents)
    button.set_size_request(120, 76)
    button.connect("key-press-event", navigation_key)
    grid.add(button)
    button.get_parent().set_can_focus(False)
    return button


current_category = None
forward_category = None


def show(category=None):
    global current_category, forward_category
    style = window.get_style_context()
    if classic:
        style.add_class("classic-view")
    else:
        style.remove_class("classic-view")
    previous = current_category
    forward_category = previous if category is None and not classic else None
    current_category = category
    focus = None
    grid.set_max_children_per_line(4 if classic else 2)
    for child in grid.get_children():
        child.destroy()
    title = tr("选择一个类别", "Pick a category")
    if classic:
        title = tr("经典视图", "Classic View")
    elif category:
        title = tr(*category[:2])
    heading.set_markup("<big><b>" + title + "</b></big>")
    switch.set_label(tr("切换到分类视图", "Switch to Category View") if classic else tr("切换到经典视图", "Switch to Classic View"))
    back.set_visible(category is not None)
    if not classic and category is None:
        for item in categories:
            button = tile(tr(*item[:2]), by_name[item[2][0]][2], item[3])
            button.set_name("xp-category")
            button.connect("clicked", lambda _, item=item: show(item))
            if item == previous:
                focus = button
    else:
        if classic:
            items = sorted(entries, key=lambda item: GLib.utf8_collate_key(tr(*item[:2]), -1))
        else:
            items = [by_name[name] for name in category[2]]
        for zh, en, icon, desktop in items:
            button = tile(tr(zh, en), icon)
            button.set_name("xp-icon")
            if desktop:
                try:
                    app = Gio.DesktopAppInfo.new(desktop)
                except TypeError:
                    app = None
                button.set_sensitive(app is not None)
                if app:
                    button.connect("clicked", lambda _, target=app: target.launch([], None))
            else:
                dialog = folder_options if en == "Folder Options" else language
                # Let assistive clients finish the activation before entering a modal loop.
                button.connect("clicked", lambda widget, open_dialog=dialog: GLib.idle_add(open_dialog, widget))
    grid.show_all()
    adjustment = scroll.get_vadjustment()
    if focus is not None:
        # The category tiles get their new positions on the next allocation.
        def reveal_category(button):
            if window.get_focus() == button:
                _, top = button.translate_coordinates(grid, 0, 0)
                adjustment.clamp_page(top, top + button.get_allocated_height())
            return GLib.SOURCE_REMOVE

        def allocated(button, _allocation):
            button.disconnect(on_allocate)
            GLib.idle_add(reveal_category, button)

        on_allocate = focus.connect_after("size-allocate", allocated)
        focus.grab_focus()
    else:
        adjustment.set_value(0)
        if classic or category:
            for row in grid.get_children():
                button = row.get_child()
                if button.get_sensitive():
                    button.grab_focus()
                    break


def change_view(_button):
    global classic
    classic = not classic
    preference.parent.mkdir(parents=True, exist_ok=True)
    write_setting(preference, lambda f: f.write("classic" if classic else "category"))
    show()


def navigation_key(_window, event):
    modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
    if not modifiers and event.keyval in (Gdk.KEY_Home, Gdk.KEY_End):
        buttons = [row.get_child() for row in grid.get_children() if row.get_child().get_sensitive()]
        if buttons:
            target = buttons[0] if event.keyval == Gdk.KEY_Home else buttons[-1]
            target.grab_focus()
            adjustment = scroll.get_vadjustment()
            adjustment.set_value(adjustment.get_lower() if event.keyval == Gdk.KEY_Home else
                                 adjustment.get_upper() - adjustment.get_page_size())
            return True
    if modifiers in (0, Gdk.ModifierType.SHIFT_MASK):
        initial = chr(Gdk.keyval_to_unicode(event.keyval)).casefold()
        if initial.isalnum():
            buttons = [row.get_child() for row in grid.get_children() if row.get_child().get_sensitive()]
            focus = window.get_focus()
            start = buttons.index(focus) + 1 if focus in buttons else 0
            visible_items = entries if classic or current_category else categories
            english_names = {tr(zh, en): en for zh, en, _, _ in visible_items}
            for button in buttons[start:] + buttons[:start]:
                label = button.get_accessible().get_name()
                if label.casefold().startswith(initial) or english_names[label].casefold().startswith(initial):
                    button.grab_focus()
                    return True
    if current_category and ((event.keyval == Gdk.KEY_Left and modifiers == Gdk.ModifierType.MOD1_MASK)
                             or (event.keyval == Gdk.KEY_BackSpace and not modifiers)):
        show()
        return True
    if forward_category and event.keyval == Gdk.KEY_Right and modifiers == Gdk.ModifierType.MOD1_MASK:
        show(forward_category)
        return True
    return False


window.connect("key-press-event", navigation_key)
back.connect("clicked", lambda _: show())
switch.connect("clicked", change_view)
window.connect("destroy", Gtk.main_quit)
if sys.argv[1:] in (["--admin-tools"], ["--settings"]):
    classic = True
    if sys.argv[1:] == ["--settings"]:
        entries = [by_name[name] for name in (
            "Display Properties", "Sounds and Audio Devices", "Network Connections",
            "Input Method", "User Accounts", "Date and Time", "Power Options",
            "Printers and Faxes", "System",
        )]
        entries.append(("其他系统设置", "Additional System Settings", "preferences-system",
                        "ukui-control-center.desktop"))
        window.set_title(tr("系统设置", "System Settings"))
    else:
        entries = [
            ("设备管理器", "Device Manager", "computer", "agentlinux-xp-devices.desktop"),
            ("磁盘管理", "Disk Management", "drive-harddisk", "org.gnome.DiskUtility.desktop"),
            by_name["Shared Folders"],
        ]
        window.set_title(tr("管理工具", "Administrative Tools"))
    window.show_all()
    show()
    nav.hide()
    heading.set_markup("<big><b>" + window.get_title() + "</b></big>")
    Gtk.main()
elif sys.argv[1:] == ["--folder-options"]:
    folder_options(None)
elif sys.argv[1:] == ["--language"]:
    language(None)
else:
    window.show_all()
    show()
    Gtk.main()
