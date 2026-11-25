#!/usr/bin/python3
import os
import sys
import subprocess
from pathlib import Path
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GUdev", "1.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GUdev, GdkPixbuf, Gio, GLib, GObject, Gtk, Pango

from task_pane import cycle_property_pages

def tr(zh, en):
    return zh if os.getenv("LANGUAGE", os.getenv("LANG", "")).startswith("zh") else en

device = sys.argv[1]
if device not in ("mouse", "keyboard"):
    raise SystemExit(2)
settings = Gio.Settings.new("org.ukui.peripherals-" + device)
settings.delay()
backends = [settings]
dialog = Gtk.Dialog(title=tr("鼠标 属性", "Mouse Properties") if device == "mouse" else tr("键盘 属性", "Keyboard Properties"))
dialog.set_icon_name("input-" + device)
dialog.set_default_size(425, 320)
for label, response in [(tr("确定", "OK"), Gtk.ResponseType.OK), (tr("取消", "Cancel"), Gtk.ResponseType.CANCEL), (tr("应用", "Apply"), Gtk.ResponseType.APPLY)]:
    dialog.add_button(label, response)
tabs = Gtk.Notebook(border_width=8)
dialog.connect("key-press-event", cycle_property_pages, tabs)
dialog.get_content_area().pack_start(tabs, True, True, 0)

def tab(zh, en):
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, border_width=14)
    tabs.append_page(page, Gtk.Label(label=tr(zh, en)))
    return page

def toggle(page, key, zh, en, backend=settings):
    widget = Gtk.CheckButton(label=tr(zh, en))
    widget.set_active(backend.get_boolean(key))
    widget.connect("toggled", lambda button: backend.set_boolean(key, button.get_active()))
    page.pack_start(widget, False, False, 0)
    return widget

def scale(page, key, zh, en, low, high, backend=settings):
    floating = backend.get_value(key).get_type_string() == "d"
    value = backend.get_double(key) if floating else backend.get_int(key)
    slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min(low, value), max(high, value), 0.1 if floating else 1)
    title = tr(zh, en)
    slider.get_accessible().set_name(title)
    slider.set_value(value)
    def changed(widget):
        if floating:
            backend.set_double(key, widget.get_value())
        else:
            backend.set_int(key, round(widget.get_value()))
    slider.connect("value-changed", changed)
    page.pack_start(Gtk.Label(label=title, xalign=0), False, False, 0)
    page.pack_start(slider, False, False, 0)
    return slider

if device == "mouse":
    buttons = tab("鼠标键", "Buttons")
    configuration = Gtk.Frame(label=tr("鼠标键配置", "Button configuration"))
    primary = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, border_width=8)
    configuration.add(primary)
    buttons.pack_start(configuration, False, False, 0)
    toggle(primary, "left-handed", "切换主要和次要的按钮", "Switch primary and secondary buttons")
    double_click = Gtk.Frame(label=tr("双击速度", "Double-click speed"))
    controls = Gtk.Box(spacing=12, border_width=8)
    double_click.add(controls)
    buttons.pack_start(double_click, False, False, 0)
    interval_controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    controls.pack_start(interval_controls, True, True, 0)
    speed = scale(interval_controls, "double-click", "速度", "Speed", 100, 900)
    speed.get_accessible().set_name(tr("双击速度", "Double-click speed"))
    speed.set_inverted(True)
    speed.set_draw_value(False)
    speed.add_mark(speed.get_adjustment().get_upper(), Gtk.PositionType.BOTTOM, tr("慢", "Slow"))
    speed.add_mark(speed.get_adjustment().get_lower(), Gtk.PositionType.BOTTOM, tr("快", "Fast"))
    def describe_speed(slider):
        interval = tr("双击间隔：{} 毫秒", "Double-click interval: {} ms").format(round(slider.get_value()))
        slider.set_tooltip_text(interval)
        slider.get_accessible().set_description(interval)

    speed.connect("value-changed", describe_speed)
    describe_speed(speed)
    instruction = Gtk.Label(label=tr("双击右侧文件夹以测试设置。", "Double-click the folder on the right to test your setting."), xalign=0, wrap=True)
    instruction.set_max_width_chars(38)
    interval_controls.pack_start(instruction, False, False, 0)
    interval_controls.reorder_child(instruction, 0)
    test_folder = Gtk.Button(valign=Gtk.Align.CENTER)
    test_folder.set_tooltip_text(instruction.get_text())
    test_folder.get_accessible().set_name(tr("测试双击", "Test double-click"))
    folder_icon = Gtk.Image.new_from_icon_name("folder", Gtk.IconSize.LARGE_TOOLBAR)
    test_folder.set_image(folder_icon)
    test_folder.set_always_show_image(True)
    last_click = None
    folder_open = False

    def test_double_click(_button):
        global last_click, folder_open
        now = GLib.get_monotonic_time()
        if last_click is not None and now - last_click <= settings.get_int("double-click") * 1000:
            folder_open = not folder_open
            folder_icon.set_from_icon_name("folder-open" if folder_open else "folder", Gtk.IconSize.LARGE_TOOLBAR)
            last_click = None
        else:
            last_click = now

    test_folder.connect("clicked", test_double_click)
    controls.pack_end(test_folder, False, False, 0)
    pointers = tab("指针", "Pointers")
    scheme_label = Gtk.Label(label=tr("指针方案", "Pointer scheme"), xalign=0)
    schemes = Gtk.ComboBoxText()
    scheme_label.set_mnemonic_widget(schemes)
    pointers.pack_start(scheme_label, False, False, 0)
    pointers.pack_start(schemes, False, False, 0)
    current_scheme = settings.get_string("cursor-theme")
    available = {current_scheme}
    roots = [Path.home() / ".icons", Path(GLib.get_user_data_dir()) / "icons"]
    roots.extend(Path(directory) / "icons" for directory in GLib.get_system_data_dirs())
    for root in roots:
        available.update(folder.parent.name for folder in root.glob("*/cursors") if folder.is_dir())
    for name in sorted(available, key=str.casefold):
        schemes.append(name, name or tr("系统默认", "System default"))
    schemes.set_active_id(current_scheme)
    schemes.connect("changed", lambda combo: settings.set_string("cursor-theme", combo.get_active_id()))
    size = scale(pointers, "cursor-size", "指针大小（像素）", "Pointer size (pixels)", 16, 64)
    from cursor_preview import cursor_pixbuf

    samples = Gtk.ListStore(str, str, GdkPixbuf.Pixbuf)
    for name, zh, en in (
        ("left_ptr", "正常选择", "Normal Select"), ("question_arrow", "帮助选择", "Help Select"),
        ("left_ptr_watch", "后台运行", "Working in Background"), ("watch", "忙", "Busy"),
        ("crosshair", "精确选择", "Precision Select"), ("xterm", "文本选择", "Text Select"),
        ("pencil", "手写", "Handwriting"), ("not-allowed", "不可用", "Unavailable"),
        ("size_ver", "垂直调整", "Vertical Resize"), ("size_hor", "水平调整", "Horizontal Resize"),
        ("size_fdiag", "沿对角线调整 1", "Diagonal Resize 1"),
        ("size_bdiag", "沿对角线调整 2", "Diagonal Resize 2"),
        ("fleur", "移动", "Move"), ("hand2", "链接选择", "Link Select"),
    ):
        samples.append((name, tr(zh, en), None))
    roles = Gtk.TreeView(model=samples, headers_visible=False)
    roles.append_column(Gtk.TreeViewColumn("", Gtk.CellRendererPixbuf(), pixbuf=2))
    roles.append_column(Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=1))
    scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_min_content_height(96)
    scroll.add(roles)
    pointers.pack_start(scroll, True, True, 0)

    def refresh_samples(*_):
        for row in samples:
            row[2] = cursor_pixbuf(schemes.get_active_id(), row[0], round(size.get_value()))

    schemes.connect("changed", refresh_samples)
    size.connect("value-changed", refresh_samples)
    refresh_samples()
    pointer = tab("指针选项", "Pointer Options")
    scale(pointer, "motion-acceleration", "指针移动速度", "Pointer speed", 1, 10)
    toggle(pointer, "locate-pointer", "按 Ctrl 键时显示指针的位置", "Show location of pointer when I press CTRL")
    wheel = tab("滑轮", "Wheel")
    scale(wheel, "wheel-speed", "滚动速度", "Scrolling speed", 1, 10)
else:
    speed = tab("速度", "Speed")
    scroll_settings = Gtk.ScrolledWindow()
    scroll_settings.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    speed.pack_start(scroll_settings, True, True, 0)
    groups = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    scroll_settings.add(groups)

    def keyboard_group(zh, en):
        frame = Gtk.Frame(label=tr(zh, en))
        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, border_width=6)
        frame.add(controls)
        groups.pack_start(frame, False, False, 0)
        return controls

    characters = keyboard_group("字符重复", "Character repeat")
    repeat = toggle(characters, "repeat", "按住键时重复输入", "Repeat characters when a key is held down")
    delay = scale(characters, "delay", "重复延迟", "Repeat delay", 150, 1000)
    rate = scale(characters, "rate", "重复速度", "Repeat rate", 10, 250)
    delay.set_inverted(True)
    for slider, low, high in ((delay, tr("短", "Short"), tr("长", "Long")),
                              (rate, tr("慢", "Slow"), tr("快", "Fast"))):
        slider.set_flippable(False)
        slider.set_draw_value(False)
        slider.add_mark(slider.get_adjustment().get_lower(), Gtk.PositionType.BOTTOM, low)
        slider.add_mark(slider.get_adjustment().get_upper(), Gtk.PositionType.BOTTOM, high)
        repeat.bind_property("active", slider, "sensitive", GObject.BindingFlags.SYNC_CREATE)
    def describe_repeat(slider):
        units = (tr("重复延迟：{} 毫秒", "Repeat delay: {} ms") if slider == delay else
                 tr("重复速度：每秒 {} 次", "Repeat rate: {} repeats per second"))
        description = units.format(round(slider.get_value()))
        slider.set_tooltip_text(description)
        slider.get_accessible().set_description(description)

    for slider in (delay, rate):
        slider.connect("value-changed", describe_repeat)
        describe_repeat(slider)
    test = Gtk.Entry(placeholder_text=tr("在此测试键盘重复速度", "Click here and hold down a key to test repeat rate"))
    characters.pack_start(test, False, False, 0)
    cursor = keyboard_group("光标闪烁频率", "Cursor blink rate")
    dialog.set_default_size(425, 440)
    style = Gio.Settings.new("org.ukui.style")
    style.delay()
    backends.append(style)
    blink = toggle(cursor, "cursor-blink", "文字光标闪烁", "Blink the text cursor", style)
    period = scale(cursor, "cursor-blink-time", "闪烁周期（毫秒，向右更快）",
                   "Blink period (ms, faster to the right)", 100, 2500, style)
    period.set_inverted(True)
    preview = Gtk.Entry(placeholder_text=tr("点击此处预览光标", "Click here to preview the cursor"))
    cursor.pack_start(preview, False, False, 0)

    def preview_cursor(*_):
        period.set_sensitive(blink.get_active())
        local = Gtk.Settings.get_default()
        local.set_property("gtk-cursor-blink", blink.get_active())
        local.set_property("gtk-cursor-blink-time", round(period.get_value()))

    blink.connect("toggled", preview_cursor)
    period.connect("value-changed", preview_cursor)
    preview_cursor()

hardware = tab("硬件", "Hardware")
device_rows = Gtk.ListStore(str, str, str, str)
device_view = Gtk.TreeView(model=device_rows)
for column, caption in enumerate((tr("设备名称", "Device name"), tr("设备节点", "Device node"))):
    device_view.append_column(Gtk.TreeViewColumn(caption, Gtk.CellRendererText(), text=column))
device_scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
device_scroll.add(device_view)
hardware.pack_start(device_scroll, True, True, 0)
details = Gtk.Grid(column_spacing=8, row_spacing=4)
hardware.pack_start(details, False, False, 0)
detail_values = []
for row, label in enumerate((tr("驱动程序", "Driver"), tr("连接位置", "Location"))):
    details.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
    value = Gtk.Label(xalign=0, selectable=True, wrap=True)
    value.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    value.set_max_width_chars(40)
    details.attach(value, 1, row, 1, 1)
    detail_values.append(value)


def device_selected(selection):
    model, item = selection.get_selected()
    for column, value in enumerate(detail_values, 2):
        value.set_text(model[item][column] if item is not None else "—")


device_view.get_selection().connect("changed", device_selected)
client = GUdev.Client.new(["input"])


def refresh_hardware(*_):
    flags = ("ID_INPUT_KEYBOARD",) if device == "keyboard" else ("ID_INPUT_MOUSE", "ID_INPUT_TOUCHPAD", "ID_INPUT_POINTINGSTICK")
    found = []
    for item in client.query_by_subsystem("input"):
        node = item.get_device_file()
        if node and node.startswith("/dev/input/event") and any(item.get_property_as_boolean(flag) for flag in flags):
            parent = item.get_parent()
            name = parent.get_sysfs_attr("name") if parent else None
            ancestor = parent
            while ancestor and not ancestor.get_driver():
                ancestor = ancestor.get_parent()
            driver = ancestor.get_driver() if ancestor else "—"
            found.append((name or item.get_name(), node, driver, item.get_property("ID_PATH") or item.get_sysfs_path()))
    found.sort()
    if found != [tuple(row) for row in device_rows]:
        selection = device_view.get_selection()
        model, item = selection.get_selected()
        previous = tuple(model[item]) if item is not None else None
        device_rows.clear()
        for record in found:
            row = device_rows.append(record)
            if record == previous or (previous is None and record == found[0]):
                selection.select_iter(row)
        device_selected(selection)


client.connect("uevent", refresh_hardware)
refresh_hardware()

apply_button = dialog.get_widget_for_response(Gtk.ResponseType.APPLY)


def sync_pending(*_):
    dirty = any(backend.get_has_unapplied() for backend in backends)
    apply_button.set_sensitive(dirty)
    if device == "keyboard":
        test.set_placeholder_text(tr("点击“应用”后可试打新设置", "Click Apply to test the new settings") if settings.get_has_unapplied()
                                  else tr("在此按住一个键测试重复速度", "Hold down a key here to test the repeat rate"))


for backend in backends:
    backend.connect("notify::has-unapplied", sync_pending)
sync_pending()
dialog.show_all()
if sys.argv[2:] == ["--hardware"]:
    tabs.set_current_page(tabs.page_num(hardware))
elif device == "mouse" and len(sys.argv) == 3 and sys.argv[2] in ("0", "1", "2", "3"):
    tabs.set_current_page(int(sys.argv[2]))
while True:
    response = dialog.run()
    if response in (Gtk.ResponseType.OK, Gtk.ResponseType.APPLY):
        cursor_changed = device == "mouse" and any(
            settings.get_value(key) != Gio.Settings.new("org.ukui.peripherals-mouse").get_value(key)
            for key in ("cursor-theme", "cursor-size"))
        for backend in backends:
            backend.apply()
        if cursor_changed:
            interface = Gio.Settings.new("org.gnome.desktop.interface")
            for key in ("cursor-theme", "cursor-size"):
                interface.set_value(key, settings.get_value(key))
        Gio.Settings.sync()
        if cursor_changed:
            subprocess.run([sys.executable, str(Path(__file__).with_name("cursor-settings.py"))], check=True)
    if response != Gtk.ResponseType.APPLY:
        break
for backend in backends:
    backend.revert()
dialog.destroy()
