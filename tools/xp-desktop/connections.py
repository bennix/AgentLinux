#!/usr/bin/python3
import subprocess
from pathlib import Path
from network_details import address_fields, connection_duration, connection_status
from dns_properties import dns_properties

from task_pane import cycle_property_pages, fit_window, add_task_pane, task_button

import gi
gi.require_version("NM", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk, NM, Pango


def tr(zh, en):
    return zh if GLib.get_language_names()[0].startswith("zh") else en


client = NM.Client.new(None)
window = Gtk.Window(title=tr("网络连接", "Network Connections"))
fit_window(window, 690, 365)
window.set_icon_name("preferences-system-network")
window.connect("destroy", Gtk.main_quit)
layout = Gtk.Box(spacing=12, border_width=10)
window.add(layout)
tasks = add_task_pane(layout, tr("网络任务", "Network Tasks"))
store = Gtk.ListStore(str, str, str, str, object)
table = Gtk.TreeView(model=store)
table.get_accessible().set_name(tr("网络适配器", "Network adapters"))
for i, label in enumerate([tr("名称", "Name"), tr("状态", "Status"), tr("设备", "Device")]):
    column = Gtk.TreeViewColumn(label)
    if i == 0:
        icon = Gtk.CellRendererPixbuf()
        column.pack_start(icon, False)
        column.add_attribute(icon, "icon-name", 3)
    cell = Gtk.CellRendererText()
    if i == 1:
        cell.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.set_expand(True)
    column.pack_start(cell, True)
    column.add_attribute(cell, "text", i)
    table.append_column(column)
scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
scroll.add(table)
layout.pack_start(scroll, True, True, 0)


def selected():
    model, it = table.get_selection().get_selected()
    return model[it][4] if it is not None else None


def properties(*_):
    show_properties(window, selected())


def show_properties(parent, device):
    if not device:
        return
    profile = active_profile(device)
    dialog = Gtk.Dialog(title=tr("连接属性", "Connection Properties"), transient_for=parent, modal=True)
    dialog.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
    pages = Gtk.Notebook(border_width=8)
    dialog.connect("key-press-event", cycle_property_pages, pages)
    dialog.get_content_area().add(pages)
    general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=12)
    pages.append_page(general, Gtk.Label(label=tr("常规", "General")))
    general.add(Gtk.Label(label=tr("连接时使用", "Connect using"), xalign=0))
    general.add(Gtk.Label(label=device.get_description() or device.get_iface(), xalign=0, wrap=True))
    if profile:
        general.add(Gtk.Label(label=profile.get_id(), xalign=0, selectable=True))
    ipv4 = Gtk.Button(label=tr("Internet 协议 (TCP/IPv4) 属性…", "Internet Protocol (TCP/IPv4) Properties…"))
    config = profile.get_setting_ip4_config() if profile else None
    ipv4.set_sensitive(bool(config and config.get_method() in ("auto", "manual")))
    ipv4.connect("clicked", lambda _: dns_properties(dialog, profile, tr, device))
    general.add(ipv4)
    advanced = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=12)
    pages.append_page(advanced, Gtk.Label(label=tr("高级", "Advanced")))
    editor = Gtk.Button(label=tr("编辑网络配置…", "Edit network configuration…"))
    def open_editor(_button):
        args = ["nm-connection-editor"]
        if profile:
            args.extend(["--edit", profile.get_uuid()])
        subprocess.Popen(args)
        dialog.response(Gtk.ResponseType.CLOSE)
    editor.connect("clicked", open_editor)
    advanced.add(editor)
    dialog.show_all()
    dialog.run()
    dialog.destroy()


def active_profile(device):
    active = device.get_active_connection() if device else None
    return active.get_connection() if active else None


def edit_dns(*_):
    device = selected()
    profile = active_profile(device)
    if profile and profile.get_setting_ip4_config():
        dns_properties(window, profile, tr, device)


def wireless(*_):
    subprocess.Popen(["gtk-launch", "agentlinux-xp-wifi"])

def show_status(*_):
    device = selected()
    if not device or device.get_state() != NM.DeviceState.ACTIVATED:
        return
    title = (tr("无线网络连接 状态", "Wireless Network Connection Status") if isinstance(device, NM.DeviceWifi)
             else tr("本地连接 状态", "Local Area Connection Status"))
    dialog = Gtk.Dialog(title=title, transient_for=window, modal=True)
    dialog.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
    edit = Gtk.Button(label=tr("属性", "Properties"))
    dialog.get_action_area().pack_start(edit, False, False, 0)
    dialog.get_action_area().reorder_child(edit, 0)
    edit.connect("clicked", lambda _: show_properties(dialog, device) if device in client.get_devices() else None)
    notebook = Gtk.Notebook(border_width=6)
    dialog.connect("key-press-event", cycle_property_pages, notebook)
    dialog.set_default_size(460, 340)
    dialog.get_content_area().pack_start(notebook, True, True, 0)
    pages = []
    copy = Gtk.Button(label=tr("复制网络详情", "Copy network details"))
    copy.set_halign(Gtk.Align.END)
    for title in (tr("常规", "General"), tr("支持", "Support")):
        grid = Gtk.Grid(row_spacing=8, column_spacing=16, border_width=14)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(grid)
        page = scroll
        if pages:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            page.pack_start(scroll, True, True, 0)
            page.pack_end(copy, False, False, 4)
        notebook.append_page(page, Gtk.Label(label=title))
        pages.append((grid, {}))

    def copy_details(_button):
        text = "\n".join(f"{label}: {field.get_text()}" for label, field in pages[1][1].items())
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    copy.connect("clicked", copy_details)

    def update():
        present = device in client.get_devices()
        edit.set_sensitive(present)
        state = device.get_state() if present else NM.DeviceState.UNAVAILABLE
        connected = state == NM.DeviceState.ACTIVATED
        status = connection_status(state, tr)
        general = [(tr("状态", "Status"), status), (tr("设备", "Device"), device.get_iface())]
        if connected:
            active = device.get_active_connection()
            if active:
                general.append((tr("连接名称", "Connection name"), active.get_id()))
                if duration := connection_duration(device):
                    general.append((tr("持续时间", "Duration"), duration))
            if isinstance(device, NM.DeviceWifi):
                speed = device.get_bitrate() / 1000
                ap = device.get_active_access_point()
                if ap:
                    ssid = ap.get_ssid()
                    if ssid and ssid.get_size():
                        general.append((tr("网络名称（SSID）", "Network name (SSID)"),
                                        NM.utils_ssid_to_utf8(ssid.get_data())))
                    general.append((tr("信号强度", "Signal strength"), f"{ap.get_strength()}%"))
            else:
                speed = device.get_speed()
            if speed:
                general.append((tr("连接速度", "Link speed"), f"{speed:g} Mbps"))
            stats = Path("/sys/class/net") / device.get_iface() / "statistics"
            for counter, label in (("tx_packets", tr("发送的数据包", "Packets sent")),
                                   ("rx_packets", tr("收到的数据包", "Packets received")),
                                   ("tx_bytes", tr("已发送（字节）", "Bytes sent")),
                                   ("rx_bytes", tr("已接收（字节）", "Bytes received"))):
                try:
                    total = int((stats / counter).read_text())
                except (OSError, ValueError):
                    continue
                general.append((label, f"{total:,}"))
        support = address_fields(device, tr) if connected else []
        copy.set_sensitive(bool(support))
        if not support:
            support = [(tr("网络地址", "Network address"), tr("暂无地址", "No address available"))]
        for (grid, widgets), fields in zip(pages, (general, support)):
            if list(widgets) != [label for label, _ in fields]:
                for child in grid.get_children():
                    child.destroy()
                widgets.clear()
                for row, (label, _) in enumerate(fields):
                    grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
                    field = Gtk.Label(xalign=0, selectable=True, wrap=True)
                    field.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                    field.set_max_width_chars(44)
                    grid.attach(field, 1, row, 1, 1)
                    widgets[label] = field
                grid.show_all()
            for label, value in fields:
                if widgets[label].get_text() != value:
                    widgets[label].set_text(value)
        return True

    update()
    timer = GLib.timeout_add_seconds(2, update)
    dialog.show_all()
    try:
        dialog.run()
    finally:
        GLib.source_remove(timer)
        dialog.destroy()


def button(label, action):
    widget = task_button(label)
    widget.connect("clicked", action)
    tasks.add(widget)
    return widget


wifi = button(tr("查看可用的无线网络", "View available wireless networks"), wireless)
status_button = button(tr("查看连接状态", "View connection status"), show_status)
dns_button = button(tr("TCP/IPv4 属性", "TCP/IPv4 Properties"), edit_dns)
props = button(tr("更改连接设置", "Change connection settings"), properties)


def selection_changed(*_):
    device = selected()
    profile = active_profile(device)
    dns_button.set_sensitive(bool(profile and profile.get_setting_ip4_config() and
                                  profile.get_setting_ip4_config().get_method() in ("auto", "manual")))
    wifi.set_sensitive(isinstance(device, NM.DeviceWifi))
    props.set_sensitive(device is not None)
    status_button.set_sensitive(bool(device and device.get_state() == NM.DeviceState.ACTIVATED))


table.get_selection().connect("changed", selection_changed)
def activate_device(view, path, _column):
    view.get_selection().select_path(path)
    device = selected()
    if device.get_state() == NM.DeviceState.ACTIVATED:
        show_status()
    elif isinstance(device, NM.DeviceWifi):
        wireless()
    else:
        properties()


table.connect("row-activated", activate_device)


def device_menu(view, event=None):
    if event is not None:
        if event.button != 3 or event.window != view.get_bin_window():
            return False
        hit = view.get_path_at_pos(int(event.x), int(event.y))
        if not hit:
            return False
        view.grab_focus()
        view.set_cursor(hit[0])
    model, item = view.get_selection().get_selected()
    if item is None:
        return False
    path = model.get_path(item)
    target = model[item][4].get_path()

    def activate(_entry, callback):
        for row in model:
            if row[4].get_path() == target:
                view.get_selection().select_path(row.path)
                callback()
                break

    menu = Gtk.Menu()
    for label, source, callback in [(tr("状态", "Status"), status_button, show_status),
                                    (wifi.get_label(), wifi, wireless),
                                    (tr("属性", "Properties"), props, properties)]:
        entry = Gtk.MenuItem(label=label)
        entry.set_sensitive(source.get_sensitive())
        entry.connect("activate", activate, callback)
        menu.append(entry)
    menu.attach_to_widget(view, None)
    menu.connect("selection-done", lambda widget: widget.destroy())
    menu.show_all()
    if event is None:
        menu.popup_at_rect(view.get_bin_window(), view.get_cell_area(path, view.get_column(0)),
                           Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, Gtk.get_current_event())
        menu.select_first(True)
    else:
        menu.popup_at_pointer(event)
    return True


table.connect("button-press-event", device_menu)
table.connect("popup-menu", device_menu)


def refresh(*_):
    device = selected()
    old = device.get_path() if device else None
    rows = []
    preferred = None
    best_rank = (False, False, False)
    for dev in client.get_devices():
        if not isinstance(dev, (NM.DeviceEthernet, NM.DeviceWifi)):
            continue
        is_wifi = isinstance(dev, NM.DeviceWifi)
        state = dev.get_state()
        active = dev.get_active_connection()
        status = connection_status(state, tr)
        if state == NM.DeviceState.ACTIVATED and active:
            status += " · " + active.get_id()
        rows.append([tr("无线网络连接", "Wireless Network Connection") if is_wifi else tr("本地连接", "Local Area Connection"),
                           status, dev.get_iface(), "network-wireless" if is_wifi else "network-wired", dev])
        rank = (dev.get_path() == old, state == NM.DeviceState.ACTIVATED, is_wifi)
        if preferred is None or rank > best_rank:
            preferred, best_rank = len(rows) - 1, rank
    if [row[4].get_path() for row in store] == [row[4].get_path() for row in rows]:
        for current, updated in zip(store, rows):
            for column, value in enumerate(updated):
                if current[column] != value:
                    current[column] = value
    else:
        store.clear()
        for row in rows:
            store.append(row)
    if preferred is not None:
        table.get_selection().select_path(preferred)
    selection_changed()


def window_key(_window, event):
    modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
    if not modifiers and event.keyval == Gdk.KEY_F5:
        refresh()
        return True
    if (modifiers == Gdk.ModifierType.MOD1_MASK and
            event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and selected() is not None):
        properties()
        return True
    return False


window.connect("key-press-event", window_key)
button(tr("刷新", "Refresh"), refresh)
def watch_device(_client, device):
    if isinstance(device, (NM.DeviceWifi, NM.DeviceEthernet)):
        device.connect("notify::state", refresh)
    refresh()


for device in client.get_devices():
    if isinstance(device, (NM.DeviceWifi, NM.DeviceEthernet)):
        device.connect("notify::state", refresh)
client.connect("device-added", watch_device)
client.connect("device-removed", refresh)
client.connect("notify::active-connections", refresh)
window.connect("focus-in-event", refresh)
refresh()
window.show_all()
model, initial = table.get_selection().get_selected()
if initial is not None:
    table.set_cursor(model.get_path(initial))
    table.grab_focus()
Gtk.main()
