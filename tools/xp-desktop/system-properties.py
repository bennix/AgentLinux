#!/usr/bin/python3
import os
import platform
import subprocess
import sys
from pathlib import Path

from network_details import lan_addresses, windows_location

from task_pane import cycle_property_pages, fit_window

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

def tr(zh, en):
    return zh if os.getenv("LANGUAGE", os.getenv("LANG", "")).startswith("zh") else en

def read(path, fallback=""):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return fallback

if sys.argv[1:] == ["--version"]:
    about = Gtk.Dialog(title=tr("关于 AgentLinux", "About AgentLinux"))
    about.set_icon_name("computer")
    about.set_default_size(440, -1)
    about.add_button(tr("确定", "OK"), Gtk.ResponseType.OK)
    about.set_default_response(Gtk.ResponseType.OK)
    body = about.get_content_area()
    banner = Gtk.Box(spacing=14)
    banner.set_name("version-banner")
    style = Gtk.CssProvider()
    style.load_from_data(b"#version-banner { padding: 12px 18px; color: white; "
                         b"background-image: linear-gradient(to right, #123780, #417ac1); }")
    banner.get_style_context().add_provider(style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    emblem = Path(__file__).with_name("college-emblem.png")
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(emblem), 64, 64, True)
    banner.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)
    brand = Gtk.Label(xalign=0)
    brand.set_markup('<span size="xx-large" foreground="white"><b>AgentLinux</b></span>')
    banner.pack_start(brand, True, True, 0)
    body.pack_start(banner, False, False, 0)
    info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, border_width=16)
    body.pack_start(info, True, True, 0)
    info.add(Gtk.Label(label=platform.freedesktop_os_release()["PRETTY_NAME"], xalign=0))
    info.add(Gtk.Label(label=tr("内核版本", "Kernel version") + "  " + platform.release(), xalign=0))
    info.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
    info.add(Gtk.Label(label=tr("系统架构", "System architecture") + "  " + platform.machine(), xalign=0))
    about.show_all()
    about.run()
    about.destroy()
    sys.exit(0)

dialog = Gtk.Dialog(title=tr("系统属性", "System Properties"))
dialog.set_icon_name("computer")
dialog.set_default_size(475, 320)
dialog.add_button(tr("确定", "OK"), Gtk.ResponseType.OK)
dialog.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
dialog.set_default_response(Gtk.ResponseType.OK)
tabs = Gtk.Notebook(border_width=8)
dialog.connect("key-press-event", cycle_property_pages, tabs)
dialog.get_content_area().pack_start(tabs, True, True, 0)

def page(zh, en):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, border_width=16)
    tabs.append_page(box, Gtk.Label(label=tr(zh, en)))
    return box

def line(box, value):
    label = Gtk.Label(label=value, xalign=0, selectable=True)
    label.set_line_wrap(True)
    box.pack_start(label, False, False, 0)

def action(box, title, desktop):
    try:
        app = Gio.DesktopAppInfo.new(desktop)
    except TypeError:
        return
    if app:
        button = Gtk.Button(label=title)
        button.connect("clicked", lambda _: app.launch([], None))
        box.pack_start(button, False, False, 0)

general = page("常规", "General")
row = Gtk.Box(spacing=22)
general.pack_start(row, True, True, 0)
row.pack_start(Gtk.Image.new_from_file(str(Path(__file__).with_name("college-emblem.png"))), False, False, 0)
details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
row.pack_start(details, True, True, 0)
def detail_group(title):
    heading = Gtk.Label(xalign=0)
    heading.set_markup("<b>" + title + "</b>")
    details.pack_start(heading, False, False, 0)
    group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, margin_start=12)
    details.pack_start(group, False, False, 0)
    return group


system_info = detail_group(tr("系统", "System"))
line(system_info, "AgentLinux")
line(system_info, platform.freedesktop_os_release()["PRETTY_NAME"])
line(system_info, "Linux " + platform.release())
computer_info = detail_group(tr("计算机", "Computer"))
cpu = next((v.split(":", 1)[1].strip() for v in read("/proc/cpuinfo").splitlines() if v.startswith("model name")), platform.machine())
line(computer_info, cpu)
ram = next(int(v.split()[1]) for v in read("/proc/meminfo").splitlines() if v.startswith("MemTotal:"))
line(computer_info, tr("{:.1f} GiB 内存", "{:.1f} GiB RAM").format(ram / 1048576))
computer = page("计算机名", "Computer Name")
line(computer, tr("计算机全名", "Full computer name"))
line(computer, platform.node())
def samba_setting(parameter):
    try:
        return subprocess.run(["testparm", "-s", "--parameter-name=" + parameter],
                              capture_output=True, text=True, check=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


workgroup = samba_setting("workgroup")
if workgroup:
    line(computer, tr("SMB 工作组", "SMB workgroup") + " · " + workgroup)
server = samba_setting("netbios name")
if server:
    def copy_address(_button, address):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(address, -1)
        clipboard.store()

    addresses = Gtk.Grid(column_spacing=8, row_spacing=6)
    address_scroll = Gtk.ScrolledWindow()
    address_scroll.set_min_content_height(100)
    address_scroll.add(addresses)
    computer.pack_start(address_scroll, True, True, 0)
    def refresh_addresses(_tabs, selected, _index):
        if selected != computer:
            return
        for child in addresses.get_children():
            child.destroy()
        paths = [("Windows", '\\\\' + server),
                 ("macOS", "smb://" + platform.node().split(".")[0] + ".local")]
        for interface, host in lan_addresses():
            uri = "smb://" + (f"[{host}]" if ":" in host else host)
            if unc := windows_location(uri):
                paths.append((f"Windows · {interface}", unc))
            paths.append((f"macOS · {interface}", uri))
        for i, (label, address) in enumerate(paths):
            addresses.attach(Gtk.Label(label=label, xalign=0), 0, i, 1, 1)
            addresses.attach(Gtk.Label(label=address, selectable=True, xalign=0), 1, i, 1, 1)
            button = Gtk.Button(label=tr("复制", "Copy"))
            button.get_accessible().set_name(tr("复制 {} 地址", "Copy {} address").format(label))
            button.connect("clicked", copy_address, address)
            addresses.attach(button, 2, i, 1, 1)
        addresses.show_all()

    tabs.connect("switch-page", refresh_addresses)
action(computer, tr("网上邻居", "My Network Places"), "agentlinux-xp-places.desktop")
hardware = page("硬件", "Hardware")
line(hardware, " ".join(filter(None, [read("/sys/class/dmi/id/sys_vendor"), read("/sys/class/dmi/id/product_name")])))


def show_devices(_button):
    viewer = Gtk.Dialog(title=tr("设备管理器", "Device Manager"), transient_for=dialog, modal=True)
    fit_window(viewer, 690, 380)
    viewer.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
    area = viewer.get_content_area()
    model = Gtk.TreeStore(str, str, str)
    machine = model.append(None, [platform.node(), "", ""])
    categories = {
        "01": tr("存储控制器", "Storage controllers"),
        "02": tr("网络适配器", "Network adapters"),
        "03": tr("显示适配器", "Display adapters"),
        "04": tr("声音、视频和游戏控制器", "Sound, video and game controllers"),
        "0c03": tr("通用串行总线控制器", "Universal Serial Bus controllers"),
    }
    groups = {}
    pci_rows = {}
    pci_error = Gtk.Label(xalign=0, wrap=True, no_show_all=True)
    area.pack_start(pci_error, False, False, 0)

    def refresh_pci():
        try:
            inventory = subprocess.run(["lspci", "-D", "-vmmk"], capture_output=True, text=True,
                                       check=True, timeout=4, env={**os.environ, "LC_ALL": "C"}).stdout
        except (OSError, subprocess.SubprocessError) as error:
            pci_error.set_text(tr("无法读取 PCI 设备", "Could not read PCI devices") + " · " + str(error))
            pci_error.show()
            return
        pci_error.hide()
        present = set()
        for record in inventory.strip().split("\n\n"):
            fields = dict(line.split(":\t", 1) for line in record.splitlines() if ":\t" in line)
            if "Slot" in fields:
                slot = fields["Slot"]
                code = read(f"/sys/bus/pci/devices/{slot}/class").removeprefix("0x")
                category = categories.get(code[:4]) or categories.get(code[:2], tr("系统设备", "System devices"))
                if category not in groups:
                    groups[category] = model.append(machine, [category, "", ""])
                present.add(slot)
                values = [fields.get("Device", slot), slot, fields.get("Driver", tr("未绑定", "Unbound"))]
                if slot in pci_rows:
                    model.set(pci_rows[slot], [0, 1, 2], values)
                else:
                    pci_rows[slot] = model.append(groups[category], values)
        for slot in pci_rows.keys() - present:
            row = pci_rows.pop(slot)
            parent = model.iter_parent(row)
            model.remove(row)
            if not model.iter_has_child(parent):
                model.remove(groups.pop(model.get_value(parent, 0)))

    refresh_pci()
    usb = Path("/sys/bus/usb/devices")
    usb_rows = {}
    category = tr("USB 设备", "USB devices")

    def refresh_usb(*_):
        present = set()
        for device in sorted(usb.glob("*")):
            vendor = read(device / "idVendor")
            if not vendor:
                continue
            product = read(device / "product") or f"{vendor}:{read(device / 'idProduct')}"
            port = device.name
            prefix = port if not port.startswith("usb") else f"{port[3:]}-0"
            drivers = sorted({link.resolve().name for link in usb.glob(f"{prefix}:*/driver") if link.is_symlink()})
            present.add(port)
            values = [product, port, ", ".join(drivers) or tr("未绑定", "Unbound")]
            if port in usb_rows:
                item = usb_rows[port]
                if list(model[item]) != values:
                    model.set(item, [0, 1, 2], values)
            else:
                if category not in groups:
                    groups[category] = model.append(machine, [category, "", ""])
                usb_rows[port] = model.append(groups[category], values)
        for port in usb_rows.keys() - present:
            model.remove(usb_rows.pop(port))
        if not present and category in groups:
            model.remove(groups.pop(category))

        return True

    input_rows = {}
    def refresh_inputs(client):
        present = set()
        for item in client.query_by_subsystem("input"):
            node = item.get_device_file()
            if not node or not node.startswith("/dev/input/event"):
                continue
            if item.get_property_as_boolean("ID_INPUT_KEYBOARD"):
                group = tr("键盘", "Keyboards")
            elif any(item.get_property_as_boolean(flag) for flag in
                     ("ID_INPUT_MOUSE", "ID_INPUT_TOUCHPAD", "ID_INPUT_POINTINGSTICK")):
                group = tr("鼠标和其他指针设备", "Mice and other pointing devices")
            else:
                continue
            parent = item.get_parent()
            ancestor = parent
            while ancestor and not ancestor.get_driver():
                ancestor = ancestor.get_parent()
            name = parent.get_sysfs_attr("name") if parent else None
            values = [name or item.get_name(), node, ancestor.get_driver() if ancestor else "—"]
            key = (group, node)
            present.add(key)
            if key in input_rows:
                model.set(input_rows[key], [0, 1, 2], values)
            else:
                if group not in groups:
                    groups[group] = model.append(machine, [group, "", ""])
                input_rows[key] = model.append(groups[group], values)
        for key in input_rows.keys() - present:
            model.remove(input_rows.pop(key))
            if not model.iter_has_child(groups[key[0]]):
                model.remove(groups.pop(key[0]))

    def refresh_devices(client, _action, item):
        if item.get_subsystem() == "input":
            refresh_inputs(client)
        else:
            refresh_usb()

    try:
        gi.require_version("GUdev", "1.0")
        from gi.repository import GUdev
        monitor = GUdev.Client.new(["usb", "input"])
        handler = monitor.connect("uevent", refresh_devices)
        refresh_inputs(monitor)
    except (ValueError, ImportError):
        monitor = None
        timer = GLib.timeout_add_seconds(2, refresh_usb)
    refresh_usb()
    view = Gtk.TreeView(model=model)
    icon_names = dict(zip((categories[key] for key in ("01", "02", "03", "04", "0c03")),
                          ("drive_disk", "net_lan", "monitor", "hardware_mm", "hardware_pcb")))
    icon_names[tr("USB 设备", "USB devices")] = "hardware"
    icon_names[tr("键盘", "Keyboards")] = "keyboard"
    icon_names[tr("鼠标和其他指针设备", "Mice and other pointing devices")] = "mouse"
    icons = {}
    for icon_name in set(icon_names.values()) | {"hardware_pcb", "computer"}:
        filename = Path("/usr/share/icons/luna/res/16x16") / (icon_name + ".png")
        if filename.is_file():
            icons[icon_name] = GdkPixbuf.Pixbuf.new_from_file(str(filename))

    def draw_icon(_column, renderer, model, item, _data):
        parent = model.iter_parent(item)
        if parent is None:
            icon_name = "computer"
        else:
            category = parent if model.get_value(item, 1) else item
            icon_name = icon_names.get(model.get_value(category, 0), "hardware_pcb")
        renderer.set_property("pixbuf", icons.get(icon_name))

    for index, title in enumerate([tr("设备", "Device"), tr("位置", "Location"), tr("驱动程序", "Driver")]):
        column = Gtk.TreeViewColumn(title)
        if index == 0:
            icon = Gtk.CellRendererPixbuf()
            column.pack_start(icon, False)
            column.set_cell_data_func(icon, draw_icon)
        text = Gtk.CellRendererText()
        column.pack_start(text, True)
        column.add_attribute(text, "text", index)
        column.set_sort_column_id(index)
        view.append_column(column)
    def device_properties(tree, path, _column):
        name, location, driver = model[path]
        if not location:
            if tree.row_expanded(path):
                tree.collapse_row(path)
            else:
                tree.expand_row(path, False)
            return
        is_usb = location in usb_rows
        bus = "usb" if is_usb else "pci"
        device = Path("/sys/bus") / bus / "devices" / location
        vendor = read(device / ("idVendor" if is_usb else "vendor")).removeprefix("0x")
        product = read(device / ("idProduct" if is_usb else "device")).removeprefix("0x")
        is_input = location.startswith("/dev/input/")
        if is_input:
            device = Path("/sys/class/input") / Path(location).name / "device"
            bus = "input"
            vendor = read(device / "id/vendor")
            product = read(device / "id/product")
        properties = Gtk.Dialog(title=tr("设备属性", "Device Properties"), transient_for=viewer, modal=True)
        properties.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
        grid = Gtk.Grid(row_spacing=8, column_spacing=12, border_width=12)
        pages = Gtk.Notebook()
        properties.connect("key-press-event", cycle_property_pages, pages)
        properties.get_content_area().add(pages)
        pages.append_page(grid, Gtk.Label(label=tr("常规", "General")))
        fields = [(tr("设备", "Device"), name), (tr("总线", "Bus"), bus.upper()),
                  (tr("位置", "Location"), location), (tr("驱动程序", "Driver"), driver),
                  (tr("硬件 ID", "Hardware ID"), f"{vendor}:{product}" if vendor and product else "—")]
        interfaces = sorted(device.glob("net/*"))
        if is_usb:
            interfaces.extend(sorted(device.glob("*:*/net/*")))
        for interface in interfaces:
            wireless = (interface / "wireless").exists() or (interface / "phy80211").exists()
            fields.append((tr("无线网络接口", "Wireless interface") if wireless else
                           tr("网络接口", "Network interface"), interface.name))
            address = read(interface / "address")
            if address:
                fields.append((tr("物理地址", "Physical address"), address.upper()))
        for index, (label, value) in enumerate(fields):
            grid.attach(Gtk.Label(label=label, xalign=0), 0, index, 1, 1)
            field = Gtk.Label(label=value, selectable=True, xalign=0, wrap=True)
            field.set_max_width_chars(45)
            grid.attach(field, 1, index, 1, 1)
        drivers = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=12)
        pages.append_page(drivers, Gtk.Label(label=tr("驱动程序", "Driver")))
        line(drivers, tr("绑定的驱动程序", "Bound driver") + " · " + driver)
        links = [device / "driver/module"]
        if is_usb:
            links.extend(device.glob("*:*/driver/module"))
        for module in sorted({link.resolve().name for link in links if link.is_symlink()}):
            line(drivers, tr("内核模块", "Kernel module") + " · " + module)
            try:
                filename = subprocess.run(["modinfo", "-F", "filename", module], capture_output=True,
                                          text=True, timeout=2, check=True).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                filename = ""
            if filename:
                line(drivers, filename)
        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=12)
        pages.append_page(details, Gtk.Label(label=tr("详细信息", "Details")))
        selector = Gtk.ComboBoxText()
        details.add(selector)
        values = {}
        if is_input:
            # Linux input uevents expose bus/vendor/product/version as PRODUCT.
            for entry in read(device / "uevent").splitlines():
                if entry.startswith("PRODUCT="):
                    values[tr("硬件 ID", "Hardware IDs")] = entry.removeprefix("PRODUCT=")
                    break
            values[tr("设备节点", "Device node")] = location
        elif vendor and product:
            prefix, vendor_key, product_key = ("USB", "VID", "PID") if is_usb else ("PCI", "VEN", "DEV")
            hardware_id = f"{prefix}\\{vendor_key}_{vendor.upper()}&{product_key}_{product.upper()}"
            values[tr("硬件 ID", "Hardware IDs")] = hardware_id
        aliases = [device / "modalias"]
        if is_usb:
            aliases.extend(sorted(device.glob("*:*/modalias")))
        modalias = "\n".join(dict.fromkeys(value for alias in aliases if (value := read(alias))))
        if modalias:
            values[tr("内核模块别名", "Kernel module aliases")] = modalias
        values[tr("系统设备路径", "System device path")] = str(device.resolve())
        value_label = Gtk.Label(xalign=0, yalign=0, selectable=True, wrap=True)
        value_label.set_max_width_chars(55)
        viewport = Gtk.ScrolledWindow()
        viewport.set_min_content_height(80)
        viewport.add(value_label)
        details.pack_start(viewport, True, True, 0)
        for label in values:
            selector.append_text(label)
        selector.connect("changed", lambda widget: value_label.set_text(values[widget.get_active_text()]))
        selector.set_active(0)
        copy = Gtk.Button(label=tr("复制", "Copy"))
        copy.set_halign(Gtk.Align.END)
        copy.connect("clicked", lambda _: Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(value_label.get_text(), -1))
        details.add(copy)
        properties.show_all()
        properties.run()
        properties.destroy()

    def scan_devices(_item):
        refresh_pci()
        refresh_usb()
        if monitor is not None:
            refresh_inputs(monitor)
        view.grab_focus()

    menu_bar = Gtk.MenuBar()
    actions = Gtk.MenuItem.new_with_mnemonic(tr("操作(_A)", "_Action"))
    action_menu = Gtk.Menu()
    scan = Gtk.MenuItem.new_with_mnemonic(tr("扫描检测硬件改动(_S)", "_Scan for hardware changes"))
    scan.connect("activate", scan_devices)
    action_menu.append(scan)
    actions.set_submenu(action_menu)
    menu_bar.append(actions)
    area.pack_start(menu_bar, False, False, 0)

    def device_key(tree, event):
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        if not modifiers and event.keyval == Gdk.KEY_F5:
            scan_devices(None)
            return True
        if modifiers != Gdk.ModifierType.MOD1_MASK or event.keyval not in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            return False
        path, column = tree.get_cursor()
        if path is None or not model[path][1]:
            return False
        device_properties(tree, path, column)
        return True

    def device_menu(tree, event=None):
        if event is not None:
            if event.button != 3:
                return False
            hit = tree.get_path_at_pos(int(event.x), int(event.y))
            if hit is None:
                return False
            tree.set_cursor(hit[0], hit[1], False)
        path, column = tree.get_cursor()
        if path is None or not model[path][1]:
            return False
        reference = Gtk.TreeRowReference.new(model, path)
        menu = Gtk.Menu()
        entry = Gtk.MenuItem(label=tr("属性", "Properties"))

        def open_properties(_entry):
            if reference.valid():
                device_properties(tree, reference.get_path(), column)

        entry.connect("activate", open_properties)
        menu.append(entry)
        menu.attach_to_widget(tree, None)
        menu.connect("selection-done", lambda widget: widget.detach())
        menu.show_all()
        if event is None:
            menu.popup_at_widget(tree, Gdk.Gravity.CENTER, Gdk.Gravity.NORTH_WEST, None)
        else:
            menu.popup_at_pointer(event)
        return True

    view.connect("button-press-event", device_menu)
    view.connect("popup-menu", device_menu)
    view.connect("key-press-event", device_key)
    view.connect("row-activated", device_properties)
    model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
    scroll = Gtk.ScrolledWindow()
    scroll.add(view)
    area.pack_start(scroll, True, True, 0)
    view.expand_row(model.get_path(machine), False)
    viewer.show_all()
    viewer.run()
    if monitor is not None:
        monitor.disconnect(handler)
    else:
        GLib.source_remove(timer)
    viewer.destroy()


devices = Gtk.Button(label=tr("设备管理器", "Device Manager"))
devices.connect("clicked", show_devices)
hardware.pack_start(devices, False, False, 0)
action(hardware, tr("附加驱动程序", "Additional Drivers"), "software-properties-drivers.desktop")
action(hardware, tr("磁盘管理", "Disk Management"), "org.gnome.DiskUtility.desktop")
action(hardware, tr("任务管理器", "Task Manager"), "agentlinux-xp-taskmgr.desktop")
advanced = page("高级", "Advanced")
for heading, description, caption, entry in [
    (tr("性能", "Performance"), tr("查看处理器、内存和交换空间的使用情况。", "View processor, memory and swap usage."),
     tr("系统监视器", "System Monitor"), "mate-system-monitor.desktop"),
    (tr("用户配置文件", "User Profiles"), tr("管理此计算机上的用户账户。", "Manage user accounts on this computer."),
     tr("用户账户", "User Accounts"), "agentlinux-xp-userinfo.desktop"),
    (tr("启动", "Startup"), tr("选择登录后自动启动的程序。", "Choose which applications start at sign-in."),
     tr("启动程序", "Startup Applications"), "gnome-session-properties.desktop"),
]:
    frame = Gtk.Frame(label=heading)
    row = Gtk.Box(spacing=10, border_width=8)
    description_label = Gtk.Label(label=description, xalign=0)
    description_label.set_line_wrap(True)
    row.pack_start(description_label, True, True, 0)
    action(row, caption, entry)
    frame.add(row)
    advanced.pack_start(frame, False, False, 0)

if sys.argv[1:] == ["--devices"]:
    show_devices(None)
else:
    dialog.show_all()
    pages = {"--computer-name": computer, "--hardware": hardware, "--advanced": advanced}
    if len(sys.argv) == 2 and sys.argv[1] in pages:
        tabs.set_current_page(tabs.page_num(pages[sys.argv[1]]))
    dialog.run()
dialog.destroy()
