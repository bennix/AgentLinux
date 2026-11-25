from ipaddress import IPv4Address, IPv4Network
import subprocess

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk


def dns_properties(parent, profile, tr, device):
    active = device.get_active_connection()
    if not active or active.get_uuid() != profile.get_uuid():
        return
    ipv4 = profile.get_setting_ip4_config()
    servers = [ipv4.get_dns(i) for i in range(ipv4.get_num_dns())]
    automatic = not ipv4.get_ignore_auto_dns() and not servers
    dialog = Gtk.Dialog(title=tr("Internet 协议 (TCP/IPv4) 属性", "Internet Protocol (TCP/IPv4) Properties"), transient_for=parent, modal=True)
    dialog.set_destroy_with_parent(True)
    dialog.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    dialog.add_button(tr("确定", "OK"), Gtk.ResponseType.OK)
    grid = Gtk.Grid(border_width=14, column_spacing=12, row_spacing=8)
    dialog.get_content_area().add(grid)
    grid.attach(Gtk.Label(label=profile.get_id(), xalign=0), 0, 0, 2, 1)
    count = ipv4.get_num_addresses()
    first = ipv4.get_address(0) if count else None
    dhcp = ipv4.get_method() == "auto"
    simple = count <= 1 and not (dhcp and count) and not (first and first.get_attribute_names())
    ip_auto = Gtk.RadioButton.new_with_label_from_widget(None, tr("自动获取 IP 地址", "Obtain an IP address automatically"))
    ip_manual = Gtk.RadioButton.new_with_label_from_widget(ip_auto, tr("使用下面的 IP 地址", "Use the following IP address"))
    grid.attach(ip_auto, 0, 1, 2, 1)
    grid.attach(ip_manual, 0, 2, 2, 1)
    ip_values = [first.get_address() if first else "",
                 str(IPv4Network((0, first.get_prefix())).netmask) if first else "",
                 ipv4.get_gateway() or ""]
    def address_entry(label, value, row):
        entry = Gtk.Entry(text=value)
        caption = Gtk.Label(label=label, xalign=0, use_underline=True)
        caption.set_mnemonic_widget(entry)
        entry.get_accessible().set_name(caption.get_text())
        grid.attach(caption, 0, row, 1, 1)
        grid.attach(entry, 1, row, 1, 1)
        return entry

    ip_entries = []
    for row, label in enumerate((tr("IP 地址(_I)", "_IP address"), tr("子网掩码(_M)", "Subnet _mask"),
                                 tr("默认网关(_G)", "Default _gateway"))):
        ip_entries.append(address_entry(label, ip_values[row], row + 3))
    ip_manual.set_active(not dhcp)
    for radio in (ip_auto, ip_manual):
        radio.set_sensitive(simple)
    def address_sensitivity(*_):
        for entry in ip_entries:
            entry.set_sensitive(simple and ip_manual.get_active())
    ip_manual.connect("toggled", address_sensitivity)
    address_sensitivity()
    auto = Gtk.RadioButton.new_with_label_from_widget(None, tr("自动获取 DNS 服务器地址", "Obtain DNS server address automatically"))
    manual = Gtk.RadioButton.new_with_label_from_widget(auto, tr("使用下面的 DNS 服务器地址", "Use the following DNS server addresses"))
    grid.attach(auto, 0, 6, 2, 1)
    grid.attach(manual, 0, 7, 2, 1)
    entries = []
    for i, label in enumerate((tr("首选 DNS 服务器(_P)", "_Preferred DNS server"),
                               tr("备用 DNS 服务器(_A)", "_Alternate DNS server"))):
        entries.append(address_entry(label, servers[i] if i < len(servers) else "", i + 8))
    note = Gtk.Label(label=tr("更改将在下次连接时生效。", "Changes take effect on the next connection."), xalign=0, wrap=True)
    grid.attach(note, 0, 10, 2, 1)
    def sensitivity(*_):
        for entry in entries:
            entry.set_sensitive(manual.get_active())
    manual.connect("toggled", sensitivity)
    manual.set_active(not automatic)
    sensitivity()
    def connection_changed(*_):
        if device.get_active_connection() != active:
            dialog.destroy()

    handler = device.connect("notify::active-connection", connection_changed)
    dialog.show_all()
    try:
        while dialog.run() == Gtk.ResponseType.OK:
            values = [entry.get_text().strip() for entry in entries]
            changes = []
            ip = [entry.get_text().strip() for entry in ip_entries]
            if simple and (ip_auto.get_active() != dhcp or (ip_manual.get_active() and ip != ip_values)):
                if ip_manual.get_active():
                    try:
                        address = IPv4Address(ip[0])
                        network = IPv4Network("0.0.0.0/" + ip[1])
                        if str(network.netmask) != ip[1]:
                            raise ValueError
                        gateway = str(IPv4Address(ip[2])) if ip[2] else ""
                    except ValueError:
                        note.set_text(tr("请检查 IP 地址、子网掩码和网关。", "Check the IP address, subnet mask and gateway."))
                        continue
                    changes.extend(["ipv4.method", "manual", "ipv4.addresses", f"{address}/{network.prefixlen}",
                                    "ipv4.gateway", gateway])
                else:
                    changes.extend(["ipv4.method", "auto", "ipv4.gateway", "", "ipv4.addresses", ""])
            dns_changed = auto.get_active() != automatic or values != (servers + ["", ""])[:2]
            if dns_changed and manual.get_active():
                try:
                    selected = [str(IPv4Address(values[0]))]
                    if values[1]:
                        selected.append(str(IPv4Address(values[1])))
                except ValueError:
                    note.set_text(tr("请输入有效的 IPv4 DNS 地址。", "Enter a valid IPv4 DNS address."))
                    continue
                selected.extend(servers[2:])
            else:
                selected = []
            if dns_changed:
                changes.extend(["ipv4.ignore-auto-dns", "yes" if selected else "no", "ipv4.dns", ",".join(selected)])
            if not changes:
                break
            result = subprocess.run(["nmcli", "connection", "modify", "uuid", profile.get_uuid(), *changes],
                                    text=True, capture_output=True)
            if result.returncode == 0:
                break
            note.set_text(result.stderr.strip())
    finally:
        GObject.signal_handler_disconnect(device, handler)
        dialog.destroy()
