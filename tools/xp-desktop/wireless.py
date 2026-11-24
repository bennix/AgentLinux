#!/usr/bin/python3
import os
import subprocess
from functools import lru_cache

import cairo

from network_details import address_fields
from dns_properties import dns_properties
from task_pane import add_task_pane, task_button

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("NM", "1.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, NM, Pango

AP_FLAGS = getattr(NM, "80211ApFlags")
SECURITY = getattr(NM, "80211ApSecurityFlags")

@lru_cache(maxsize=6)
def signal_bars(level):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 20, 16)
    brush = cairo.Context(surface)
    for bar in range(5):
        height = 3 + 3 * bar
        color = (0.13, 0.48, 0.12) if bar < level else (0.68, 0.68, 0.68)
        brush.set_source_rgb(*color)
        brush.rectangle(4 * bar, 16 - height, 3, height)
        brush.fill()
    return Gdk.pixbuf_get_from_surface(surface, 0, 0, 20, 16)


def render_signal(column, cell, model, row, data):
    strength = model[row][2]
    if isinstance(cell, Gtk.CellRendererPixbuf):
        cell.set_property("pixbuf", signal_bars((strength + 19) // 20))
    else:
        cell.set_property("text", f"{strength}%")


def tr(zh, en):
    return zh if os.getenv("LANGUAGE", os.getenv("LANG", "")).startswith("zh") else en

def ssid(ap):
    return NM.utils_ssid_to_utf8(ap.get_ssid().get_data()) if ap.get_ssid() else ""

def network_key(ap, dev):
    return (dev.get_path(), ap.get_ssid().get_data(), int(ap.get_flags()),
            int(ap.get_wpa_flags()), int(ap.get_rsn_flags()))

def security_label(ap):
    wpa, rsn = ap.get_wpa_flags(), ap.get_rsn_flags()
    modes = []
    if wpa & SECURITY.KEY_MGMT_PSK:
        modes.append("WPA")
    if rsn & SECURITY.KEY_MGMT_PSK:
        modes.append("WPA2")
    if rsn & SECURITY.KEY_MGMT_SAE:
        modes.append("WPA3")
    if (wpa | rsn) & SECURITY.KEY_MGMT_802_1X:
        enterprise = tr("企业", "Enterprise")
        if wpa & SECURITY.KEY_MGMT_802_1X:
            modes.append("WPA " + enterprise)
        if rsn & SECURITY.KEY_MGMT_802_1X:
            modes.append("802.1X " + enterprise)
    if rsn & SECURITY.KEY_MGMT_EAP_SUITE_B_192:
        modes.append("WPA3 " + tr("企业", "Enterprise") + " 192-bit")
    if rsn & (SECURITY.KEY_MGMT_OWE | SECURITY.KEY_MGMT_OWE_TM):
        modes.append(tr("增强型开放网络", "Enhanced Open") + " (OWE)")
    if modes:
        return " / ".join(modes)
    if wpa or rsn:
        return tr("已加密", "Secured")
    return "WEP" if ap.get_flags() & AP_FLAGS.PRIVACY else tr("开放", "Open")


def ask_network_key(parent, network, sae):
    dialog = Gtk.Dialog(title=tr("无线网络连接", "Wireless Network Connection"), transient_for=parent, modal=True)
    dialog.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    dialog.add_button(tr("连接", "Connect"), Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)
    box = dialog.get_content_area()
    box.set_border_width(12)
    box.set_spacing(8)
    box.add(Gtk.Label(label=tr("网络名称", "Network name") + " · " + network, xalign=0))
    entry = Gtk.Entry(visibility=False, activates_default=True, placeholder_text=tr("网络密钥", "Network key"))
    box.add(entry)
    reveal = Gtk.CheckButton(label=tr("显示网络密钥", "Show network key"))
    reveal.connect("toggled", lambda toggle: entry.set_visibility(toggle.get_active()))
    box.add(reveal)
    hint = Gtk.Label(xalign=0, wrap=True)
    box.add(hint)

    def validate(*_):
        text = entry.get_text()
        valid = bool(text) if sae else NM.utils_wpa_psk_valid(text)
        dialog.set_response_sensitive(Gtk.ResponseType.OK, valid)
        hint.set_text(tr("请输入 8 至 63 字节的密码，或 64 位十六进制密钥。",
                         "Enter an 8–63 byte passphrase or a 64-digit hexadecimal key.")
                      if text and not valid else "")

    entry.connect("changed", validate)
    validate()
    dialog.show_all()
    entry.grab_focus()
    response = dialog.run()
    password = entry.get_text() if response == Gtk.ResponseType.OK else None
    dialog.destroy()
    return password


class Wireless(Gtk.Application):
    def __init__(self):
        session = os.environ.get("XDG_SESSION_ID", "")
        app_id = "org.agentlinux.Wireless"
        if session.isascii() and session.isalnum():
            app_id += ".session" + session
        super().__init__(application_id=app_id, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.client = NM.Client.new(None)
        self.window = None
        self.busy = False
        self.pending = None
        self.scans = {}
        self.scan_error = ""

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        self.window = Gtk.ApplicationWindow(application=self, title=tr("无线网络连接", "Wireless Network Connection"))
        self.window.connect("destroy", lambda *_: self.quit())
        self.window.set_icon_name("network-wireless")
        display = self.window.get_display()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        area = monitor.get_workarea()
        self.window.set_default_size(min(650, area.width - 24), min(405, area.height - 64))
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=10)
        self.window.add(outer)
        panes = Gtk.Box(spacing=12)
        outer.pack_start(panes, True, True, 0)
        side = add_task_pane(panes, tr("网络任务", "Network Tasks"))
        for icon, label, callback in [
            ("view-refresh", tr("刷新网络列表", "Refresh network list"), self.scan),
            ("preferences-system-network", tr("更改高级设置", "Change advanced settings"), lambda *_: subprocess.Popen(["nm-connection-editor"])),
        ]:
            button = task_button(label)
            button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
            button.set_always_show_image(True)
            button.connect("clicked", callback)
            if callback == self.scan:
                self.refresh_button = button
                shortcuts = Gtk.AccelGroup()
                self.window.add_accel_group(shortcuts)
                button.add_accelerator("clicked", shortcuts, Gdk.KEY_F5, 0, Gtk.AccelFlags.VISIBLE)
                button.set_tooltip_text(label + " (F5)")
            side.pack_start(button, False, False, 0)
        self.status_button = task_button(tr("查看连接状态", "View connection status"))
        self.status_button.connect("clicked", self.show_status)
        side.pack_start(self.status_button, False, False, 0)
        self.ip_button = task_button(tr("TCP/IPv4 属性", "TCP/IPv4 Properties"))
        self.ip_button.connect("clicked", self.edit_selected_ip)
        side.pack_start(self.ip_button, False, False, 0)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panes.pack_start(right, True, True, 0)
        heading = Gtk.Label(xalign=0)
        heading.set_markup("<b>" + tr("选择无线网络", "Choose a wireless network") + "</b>")
        right.pack_start(heading, False, False, 0)
        scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        right.pack_start(scroll, True, True, 0)
        self.store = Gtk.ListStore(str, str, int, object, object, int, object)
        self.list = Gtk.TreeView(model=self.store)
        self.list.get_accessible().set_name(tr("可用无线网络", "Available wireless networks"))
        scroll.add(self.list)
        for i, name in enumerate([tr("无线网络", "Wireless network"), tr("安全性", "Security"), tr("信号", "Signal")]):
            cell = Gtk.CellRendererText()
            if i < 2:
                cell.set_property("ellipsize", Pango.EllipsizeMode.END)
                cell.set_property("width-chars", 10 if i == 0 else 8)
            col = Gtk.TreeViewColumn(name)
            if i == 1:
                col.set_min_width(110)
            if i == 0:
                icon = Gtk.CellRendererPixbuf()
                icon.set_property("icon-name", "network-wireless")
                col.pack_start(icon, False)
            if i == 2:
                bars = Gtk.CellRendererPixbuf()
                col.pack_start(bars, False)
                col.set_cell_data_func(bars, render_signal)
            col.pack_start(cell, True)
            if i == 2:
                col.set_cell_data_func(cell, render_signal)
            else:
                col.add_attribute(cell, "text", i)
            if i == 0:
                col.add_attribute(cell, "weight", 5)
            col.set_expand(i == 0)
            self.list.append_column(col)
        self.list.set_has_tooltip(True)
        self.list.connect("query-tooltip", self.network_tooltip)
        self.list.connect("row-activated", self.activate_network)
        self.preferred_network = None
        self.list.get_selection().connect("changed", self.selection_changed)
        self.scan_status = Gtk.Label(xalign=0, wrap=True)
        outer.pack_start(self.scan_status, False, False, 0)
        self.message = Gtk.Label(xalign=0)
        self.message.set_line_wrap(True)
        outer.pack_start(self.message, False, False, 0)
        self.button = Gtk.Button()
        self.button.set_halign(Gtk.Align.END)
        self.button.set_size_request(92, -1)
        self.button.connect("clicked", lambda *_: self.connect_selected())
        outer.pack_end(self.button, False, False, 0)
        self.populate()
        self.window.show_all()
        GLib.timeout_add_seconds(4, self.populate)
        self.scan()

    def devices(self):
        return [d for d in self.client.get_devices() if isinstance(d, NM.DeviceWifi)]

    def network_tooltip(self, view, x, y, keyboard, tooltip):
        found, _, _, model, path, item = view.get_tooltip_context(x, y, keyboard)
        if not found:
            return False
        tooltip.set_text(model[item][0] + "\n" + model[item][1])
        view.set_tooltip_row(tooltip, path)
        return True

    def selected(self):
        model, it = self.list.get_selection().get_selected()
        return (model[it][3], model[it][4]) if it else (None, None)

    def selection_changed(self, *_):
        ap, device = self.selected()
        if ap and ap.get_ssid():
            self.preferred_network = network_key(ap, device)
        self.update_button()

    def populate(self):
        old = self.preferred_network
        rows = {}
        devices = self.devices()
        for dev in devices:
            active = dev.get_active_access_point()
            for ap in dev.get_access_points():
                if ssid(ap):
                    key = network_key(ap, dev)
                    row = (ap == active, ap.get_strength(), ap, dev)
                    if key not in rows or row[:2] > rows[key][:2]:
                        rows[key] = row
        active_iter = selected_iter = None
        existing = {row[6]: row.iter for row in self.store}
        for key in existing.keys() - rows.keys():
            self.store.remove(existing[key])
        ordered = sorted(rows, key=lambda k: rows[k][:2], reverse=True)
        for key in ordered:
            current, strength, ap, dev = rows[key]
            name = ssid(ap) + (tr("（已连接）", " (Connected)") if current else "")
            values = [name, security_label(ap), strength, ap, dev,
                      Pango.Weight.BOLD if current else Pango.Weight.NORMAL]
            it = existing.get(key)
            if it is None:
                it = self.store.append([*values, key])
            else:
                for column, value in enumerate(values):
                    if self.store.get_value(it, column) != value:
                        self.store.set_value(it, column, value)
            if current:
                active_iter = it
            if key == old:
                selected_iter = it
        positions = {row[6]: i for i, row in enumerate(self.store)}
        if ordered != list(positions):
            self.store.reorder([positions[key] for key in ordered])
        it = selected_iter if old is not None else (active_iter or self.store.get_iter_first())
        if it:
            self.list.get_selection().select_iter(it)
        now = GLib.get_monotonic_time()
        for dev, (previous, start) in list(self.scans.items()):
            if dev not in devices or dev.get_last_scan() > previous:
                del self.scans[dev]
            elif now - start >= 30_000_000:
                del self.scans[dev]
                self.scan_error = tr("等待无线扫描结果超时。", "Timed out waiting for Wi-Fi scan results.")
        if not devices:
            summary = tr("未检测到无线网卡。", "No wireless adapter found.")
        elif not self.client.wireless_get_enabled():
            summary = tr("Wi-Fi 已关闭。", "Wi-Fi is turned off.")
        elif self.scans:
            summary = tr("正在扫描无线网络…", "Scanning for wireless networks…")
        elif self.scan_error:
            summary = self.scan_error
            if rows:
                summary += tr("（显示已有网络：", " (cached networks: ") + str(len(rows)) + tr("）", ")")
        elif rows:
            summary = tr("发现的无线网络", "Wireless networks found") + f" · {len(rows)}"
        else:
            summary = tr("尚未发现无线网络。", "No wireless networks found.")
        self.scan_status.set_text(summary)
        self.refresh_button.set_sensitive(bool(devices) and self.client.wireless_get_enabled() and not self.scans)
        if self.pending:
            state = self.pending.get_state()
            if state in (NM.ActiveConnectionState.ACTIVATED, NM.ActiveConnectionState.DEACTIVATED):
                self.message.set_text(tr("已连接。", "Connected.") if state == NM.ActiveConnectionState.ACTIVATED else tr("连接已结束，请检查密码和信号。", "Connection ended. Check the password and signal."))
                self.pending = None
                self.busy = False
        self.update_button()
        return True

    def activate_network(self, view, path, _column):
        view.get_selection().select_path(path)
        ap, dev = self.selected()
        if ap and ap == dev.get_active_access_point():
            self.show_status()
        else:
            self.connect_selected()

    def update_button(self):
        ap, dev = self.selected()
        self.button.set_label(tr("断开连接", "Disconnect") if ap and ap == dev.get_active_access_point() else tr("连接", "Connect"))
        self.button.set_sensitive(bool(ap) and not self.busy)

        self.status_button.set_sensitive(bool(ap and ap == dev.get_active_access_point()))

        self.ip_button.set_sensitive(self.selected_ip_profile() is not None)

    def selected_ip_profile(self):
        ap, dev = self.selected()
        if not ap or ap != dev.get_active_access_point():
            return None
        active = dev.get_active_connection()
        profile = active.get_connection() if active else None
        ipv4 = profile.get_setting_ip4_config() if profile else None
        return profile if ipv4 and ipv4.get_method() in ("auto", "manual") else None

    def edit_selected_ip(self, *_):
        profile = self.selected_ip_profile()
        if profile:
            dns_properties(self.window, profile, tr)

    def show_status(self, *_):
        ap, dev = self.selected()
        if not ap or ap != dev.get_active_access_point():
            return
        dialog = Gtk.Dialog(title=tr("无线网络连接 状态", "Wireless Network Connection Status"),
                            transient_for=self.window, modal=True)
        dialog.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
        tabs = Gtk.Notebook(border_width=8)
        dialog.set_default_size(460, 340)
        dialog.get_content_area().pack_start(tabs, True, True, 0)

        def fill_grid(grid, fields):
            for row, (label, value) in enumerate(fields):
                grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
                field = value if isinstance(value, Gtk.Widget) else Gtk.Label(label=value, selectable=True, xalign=0)
                if isinstance(field, Gtk.Label):
                    field.set_line_wrap(True)
                    field.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                    field.set_max_width_chars(40)
                grid.attach(field, 1, row, 1, 1)
        def page(title, fields, footer=None):
            grid = Gtk.Grid(row_spacing=8, column_spacing=16, border_width=12)
            fill_grid(grid, fields)
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scroll.add(grid)
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            content.pack_start(scroll, True, True, 0)
            if footer is not None:
                footer.set_halign(Gtk.Align.END)
                footer.set_margin_end(8)
                footer.set_margin_bottom(4)
                content.pack_end(footer, False, False, 0)
            tabs.append_page(content, Gtk.Label(label=title))
            return grid

        speed = Gtk.Label(selectable=True, xalign=0)
        signal = Gtk.Box(spacing=6)
        bars = Gtk.Image()
        percentage = Gtk.Label(selectable=True, xalign=0)
        signal.pack_start(bars, False, False, 0)
        signal.pack_start(percentage, False, False, 0)

        def update_speed(*_):
            bitrate = dev.get_bitrate()
            speed.set_text(f"{bitrate / 1000:g} Mbps" if bitrate else tr("未知", "Unknown"))

        connection = dev.get_active_connection()
        bssid = Gtk.Label(selectable=True, xalign=0)
        frequency = Gtk.Label(selectable=True, xalign=0)
        security = Gtk.Label(selectable=True, xalign=0)
        name = Gtk.Label(selectable=True, xalign=0)

        def update_access_point(*_):
            current = dev.get_active_access_point()
            if dev.get_active_connection() != connection:
                dialog.destroy()
                return
            unknown = tr("未知", "Unknown")
            name.set_text(ssid(current) if current else ssid(ap))
            bssid.set_text((current.get_bssid() if current else None) or unknown)
            mhz = current.get_frequency() if current else 0
            frequency.set_text(f"{mhz} MHz" if mhz else unknown)
            security.set_text(security_label(current) if current else unknown)
            strength = current.get_strength() if current else 0
            bars.set_from_pixbuf(signal_bars((strength + 19) // 20))
            percentage.set_text(f"{strength}%" if current else unknown)

        update_speed()
        update_access_point()
        handlers = [(dev, dev.connect("notify::bitrate", update_speed)),
                    (dev, dev.connect("notify::active-access-point", update_access_point)),
                    (dev, dev.connect("notify::active-connection", update_access_point))]
        properties = Gtk.Button(label=tr("TCP/IPv4 属性", "TCP/IPv4 Properties"))
        profile = connection.get_connection() if connection else None
        ipv4 = profile.get_setting_ip4_config() if profile else None
        properties.set_sensitive(bool(ipv4 and ipv4.get_method() in ("auto", "manual")))
        properties.connect("clicked", lambda _: dns_properties(dialog, profile, tr))
        page(tr("常规", "General"), [
            (tr("网络名称", "Network name"), name),
            (tr("接入点地址", "Access point address"), bssid),
            (tr("无线频率", "Radio frequency"), frequency),
            (tr("安全性", "Security"), security),
            (tr("状态", "Status"), tr("已连接", "Connected")),
            (tr("连接速度", "Link speed"), speed),
            (tr("信号强度", "Signal strength"), signal),
        ], properties)
        copy = Gtk.Button(label=tr("复制网络详情", "Copy network details"))
        support = page(tr("支持", "Support"), [], copy)
        displayed = None

        def copy_addresses(_button):
            if displayed:
                text = "\n".join(f"{label}: {value}" for label, value in displayed)
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                clipboard.set_text(text, -1)
                clipboard.store()

        copy.connect("clicked", copy_addresses)

        def refresh_addresses():
            nonlocal displayed
            update_access_point()
            fields = address_fields(dev, tr)
            if fields != displayed:
                for child in support.get_children():
                    child.destroy()
                fill_grid(support, fields or [(tr("网络地址", "Network address"),
                                               tr("等待分配", "Awaiting assignment"))])
                copy.set_sensitive(bool(fields))
                support.show_all()
                displayed = fields
            return GLib.SOURCE_CONTINUE

        refresh_addresses()
        timer = GLib.timeout_add_seconds(2, refresh_addresses)
        def stop_updates(*_):
            GLib.source_remove(timer)
            for obj, handler in handlers:
                GObject.signal_handler_disconnect(obj, handler)

        dialog.set_destroy_with_parent(True)
        dialog.connect("destroy", stop_updates)
        dialog.connect("response", lambda widget, _response: widget.destroy())
        dialog.show_all()

    def scan(self, *_):
        if self.scans or not self.client.wireless_get_enabled():
            return
        self.scan_error = ""
        for dev in self.devices():
            self.scans[dev] = (dev.get_last_scan(), GLib.get_monotonic_time())
            dev.request_scan_async(None, self.scanned)
        self.populate()

    def scanned(self, dev, result):
        try:
            dev.request_scan_finish(result)
        except GLib.Error as exc:
            self.scans.pop(dev, None)
            if "not authorized" in exc.message.casefold():
                self.scan_error = tr("当前会话无权刷新网络列表。", "This session cannot request a Wi-Fi scan.")
            else:
                self.scan_error = exc.message
        self.populate()

    def connect_selected(self):
        ap, dev = self.selected()
        if not ap or self.busy:
            return
        if ap == dev.get_active_access_point():
            dev.disconnect_async(None, self.disconnected)
        else:
            profile = next((p for p in dev.get_available_connections() if ap.connection_valid(p)), None)
            if profile:
                self.client.activate_connection_async(profile, dev, ap.get_path(), None, self.activated)
            else:
                flags = ap.get_rsn_flags() | ap.get_wpa_flags()
                security = NM.SettingWirelessSecurity.new()
                if flags & (SECURITY.KEY_MGMT_802_1X | SECURITY.KEY_MGMT_EAP_SUITE_B_192):
                    subprocess.Popen(["nm-connection-editor", "--create", "--type=wifi"])
                    return
                connection = NM.SimpleConnection.new()
                if flags & (SECURITY.KEY_MGMT_PSK | SECURITY.KEY_MGMT_SAE):
                    password = ask_network_key(self.window, ssid(ap), bool(flags & SECURITY.KEY_MGMT_SAE))
                    if password is None:
                        return
                    security.props.key_mgmt = "sae" if flags & SECURITY.KEY_MGMT_SAE else "wpa-psk"
                    security.props.psk = password
                    connection.add_setting(security)
                elif flags & (SECURITY.KEY_MGMT_OWE | SECURITY.KEY_MGMT_OWE_TM):
                    security.props.key_mgmt = "owe"
                    connection.add_setting(security)
                elif flags or ap.get_flags() & AP_FLAGS.PRIVACY:
                    subprocess.Popen(["nm-connection-editor", "--create", "--type=wifi"])
                    return
                self.client.add_and_activate_connection_async(connection, dev, ap.get_path(), None, self.created)
        self.busy = True
        self.update_button()

    def activated(self, client, result):
        self.finished(client.activate_connection_finish, result)

    def created(self, client, result):
        self.finished(client.add_and_activate_connection_finish, result)

    def disconnected(self, dev, result):
        self.finished(dev.disconnect_finish, result)

    def finished(self, finish, result):
        try:
            value = finish(result)
            if isinstance(value, NM.ActiveConnection):
                self.pending = value
                self.message.set_text(tr("正在连接…", "Connecting…"))
            else:
                self.message.set_text(tr("已断开。", "Disconnected."))
        except GLib.Error as exc:
            self.message.set_text(exc.message)
        self.busy = self.pending is not None
        self.populate()

Wireless().run()
