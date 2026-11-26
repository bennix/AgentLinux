#!/usr/bin/python3
"""XP-style welcome page for Ubuntu's CUPS printer installation wizard."""
import grp
import locale
import os
import subprocess
import sys
import threading
from urllib.parse import urlsplit
from network_details import smb_uri
from printer_test_page import submit_test_page

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

sys.path.insert(0, "/usr/share/system-config-printer")
import newprinter
import ppdippstr

locale.setlocale(locale.LC_ALL, "")
ppdippstr.init()
zh = os.environ.get("LANGUAGE", locale.getlocale()[0] or "").startswith("zh")
title = "添加打印机向导" if zh else "Add Printer Wizard"
window = Gtk.Window(title=title)
window.set_icon_name("printer")
window.set_default_size(530, 355)
window.connect("destroy", Gtk.main_quit)
layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
window.add(layout)
page = Gtk.Box()
page.set_name("welcome")
layout.pack_start(page, True, True, 0)
stripe = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
stripe.set_name("stripe")
stripe.set_size_request(140, -1)
icon = Gtk.Image.new_from_icon_name("printer", Gtk.IconSize.DIALOG)
stripe.pack_start(icon, False, False, 24)
page.pack_start(stripe, False, False, 0)
body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
body.set_border_width(22)
page.pack_start(body, True, True, 0)
for string, heading in [
    ("欢迎使用添加打印机向导" if zh else "Welcome to the Add Printer Wizard", True),
    ("此向导可帮助您安装本地打印机或连接网络打印机。" if zh else "This wizard helps you install a local printer or connect to a network printer.", False),
    ("要继续，请单击“下一步”。" if zh else "To continue, click Next.", False),
]:
    label = Gtk.Label(xalign=0)
    label.set_line_wrap(True)
    label.set_size_request(300, -1)
    label.set_max_width_chars(35)
    label.set_markup(f'<span size="x-large" weight="bold">{string}</span>' if heading else string)
    body.pack_start(label, False, False, 0)
known_address = Gtk.CheckButton.new_with_mnemonic("使用网络打印机地址(_U)" if zh else "_Use a network printer address")
body.pack_start(known_address, False, False, 0)
address = Gtk.Entry(placeholder_text="ipp://server/printers/name")
address.get_accessible().set_name("网络打印机地址" if zh else "Network printer address")
address_row = Gtk.Box(spacing=4)
address_row.set_no_show_all(True)
address.set_activates_default(True)
address_row.pack_start(address, True, True, 0)
find = Gtk.Button.new_with_mnemonic("查找(_F)…" if zh else "_Find…")
address_row.pack_end(find, False, False, 0)
body.pack_start(address_row, False, False, 0)
driverless = Gtk.CheckButton(label="使用 IPP Everywhere 免驱打印" if zh else "Use IPP Everywhere driverless printing")
driverless.set_active(True)
driverless.set_no_show_all(True)
body.pack_start(driverless, False, False, 0)


def update_driverless(*_):
    driverless.set_visible(known_address.get_active() and
                           address.get_text().strip().strip('"').lower().startswith(("ipp://", "ipps://")))


address.connect("changed", update_driverless)
address.show()
find.show()
error = Gtk.Label(xalign=0, wrap=True)
body.pack_start(error, False, False, 0)


def toggle_address(button):
    address_row.set_visible(button.get_active())
    update_driverless()
    error.set_text("")
    if button.get_active():
        address.grab_focus()


def finish_search(results, message):
    find.set_sensitive(True)
    if not window.get_visible() or not known_address.get_active():
        return False
    if results:
        count = len(results)
        message = (f"找到 {count} 个网络打印地址。请选择地址，然后继续安装。" if zh else
                   f"Network printer addresses found: {count}. Select an address to continue setup.")
    error.set_text(message)
    if results:
        menu = Gtk.Menu()
        for name, uri in results:
            item = Gtk.MenuItem(label=f"{name}  ({urlsplit(uri).netloc})")
            item.set_tooltip_text(uri)
            item.get_accessible().set_description(uri)
            item.connect("activate", lambda _, value=uri: address.set_text(value))
            menu.append(item)
        menu.attach_to_widget(find, None)
        menu.connect("selection-done", lambda widget: widget.destroy())
        menu.show_all()
        menu.popup_at_widget(find, Gdk.Gravity.SOUTH_EAST, Gdk.Gravity.NORTH_EAST, None)
    return False


def find_printers(_button):
    find.set_sensitive(False)
    error.set_text("正在查找网络打印机…" if zh else "Searching for network printers…")

    def browse():
        results = []
        try:
            proc = subprocess.run(["ippfind", "-T", "3", "_ipp._tcp", "_ipps._tcp", "--print-name", "--print"],
                                  capture_output=True, text=True, errors="replace", timeout=8)
            lines = proc.stdout.splitlines()
            if proc.returncode not in (0, 1):
                raise OSError
            results = sorted(set((name, uri) for name, uri in zip(lines[::2], lines[1::2])
                                 if uri.startswith(("ipp://", "ipps://"))))
            message = "" if results else ("未发现打印机，可手动输入地址。" if zh else
                                          "No printers found. You can enter an address.")
        except (OSError, subprocess.TimeoutExpired):
            message = "无法搜索打印机，可手动输入地址。" if zh else "Search unavailable. You can enter an address."
        GLib.idle_add(finish_search, results, message)

    threading.Thread(target=browse, daemon=True).start()


find.connect("clicked", find_printers)
known_address.connect("toggled", toggle_address)
style = Gtk.CssProvider()
style.load_from_data(b"#welcome { background: white; color: black; } #stripe { background-image: linear-gradient(to bottom, #08358a, #377bbd); }")
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
layout.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
actions = Gtk.ButtonBox()
actions.set_layout(Gtk.ButtonBoxStyle.END)
actions.set_border_width(8)
actions.set_spacing(6)
layout.pack_start(actions, False, False, 0)
wizard = None


class PrinterWizard(newprinter.NewPrinterGUI):
    back_to_welcome = False
    returning = False

    def on_entNPName_changed(self, widget):
        super().on_entNPName_changed(widget)
        self.update_queue_name(widget)

    def update_queue_name(self, widget):
        if self.dialog_mode not in ("printer", "printer_with_uri"):
            return
        name = widget.get_text()
        message = ""
        if not name:
            message = "请输入打印队列名称。" if zh else "Enter a print queue name."
        elif len(name.encode("utf-8")) > 127:
            message = "队列名称最多可用 127 个 UTF-8 字节。" if zh else "Use at most 127 UTF-8 bytes for the queue name."
        elif any(ord(c) <= 32 or ord(c) == 127 or c in "/#" for c in name):
            message = "名称不能包含控制字符、空格、/ 或 #。" if zh else "Names cannot contain control characters, spaces, / or #."
        elif not newprinter.checkNPName(self.printers, name):
            message = "此队列名称已被使用。" if zh else "This queue name is already in use."
        self.btnNPApply.set_sensitive(not message)
        position = Gtk.EntryIconPosition.SECONDARY
        widget.set_icon_from_icon_name(position, "dialog-warning" if message else None)
        widget.set_icon_tooltip_text(position, message or None)
        widget.get_accessible().set_description(message)

    def on_btnNPApply_clicked(self, widget):
        # On Ubuntu local print administrators can authenticate to cupsd over
        # its Unix socket even in sessions without a graphical PolicyKit agent.
        try:
            local_admin = grp.getgrnam("lpadmin").gr_gid in os.getgroups()
        except KeyError:
            local_admin = False
        if local_admin and self._host.startswith("/"):
            self.cups._connect(allow_pk=False)
        super().on_btnNPApply_clicked(widget)

    def device_key(self, _window, event):
        if event.keyval == Gdk.KEY_Escape and not (event.state & Gtk.accelerator_get_default_mod_mask()):
            self.on_NPCancel(self.NewPrinterWindow)
            return True
        return False

    def setNPButtons(self):
        super().setNPButtons()
        if self.ntbkNewPrinter.get_current_page() == self.PAGE_DESCRIBE_PRINTER:
            self.update_queue_name(self.entNPName)
        # CUPS hides Back on its first page, which follows our welcome page.
        self.back_to_welcome = not self.btnNPBack.get_visible()
        self.btnNPBack.show()

    def on_btnNPBack_clicked(self, widget):
        if self.back_to_welcome:
            self.returning = True
            self.on_NPCancel(widget)
        else:
            super().on_btnNPBack_clicked(widget)

    def _initialisePrinterWithURIMode(self):
        if not (driverless.get_visible() and driverless.get_active()):
            return super()._initialisePrinterWithURIMode()
        self._initialiseDeviceFromURI()
        self._initialiseWidgetsForMode("IPP-Printer")
        self.ppd = "everywhere"
        self.exactdrivermatch = True
        self.installable_options = False
        self.ntbkNewPrinter.set_current_page(self.PAGE_DESCRIBE_PRINTER)

    def getWidgets(self, widgets, domain=None):
        super().getWidgets(widgets, domain or "system-config-printer")


def printer_added(_wizard, name):
    if "--report-queue" in sys.argv[1:]:
        print("agentlinux-printer-added=" + name, flush=True)
    for child in body.get_children():
        child.destroy()
    heading = Gtk.Label(xalign=0, wrap=True)
    heading.set_markup('<span size="x-large" weight="bold">' +
                       ("添加打印机向导已完成" if zh else "Completing the Add Printer Wizard") + "</span>")
    body.pack_start(heading, False, False, 0)
    summary = Gtk.Label(xalign=0, wrap=True)
    summary.set_text(("已添加打印队列：%s" if zh else "Added print queue: %s") % name)
    body.pack_start(summary, False, False, 0)
    test_page = Gtk.Button.new_with_mnemonic("打印测试页(_T)" if zh else "Print _test page")
    test_page.set_halign(Gtk.Align.START)
    feedback = Gtk.Label(xalign=0, wrap=True, selectable=True)
    default_button = Gtk.Button.new_with_mnemonic("设为我的默认打印机(_D)" if zh else "Set as my _default printer")
    default_button.set_halign(Gtk.Align.START)

    def choose_default(button):
        result = subprocess.run(["lpoptions", "-d", name], capture_output=True, text=True)
        if result.returncode:
            feedback.set_text(("设置失败：" if zh else "Could not set default: ") + result.stderr.strip())
            return
        button.set_sensitive(False)
        feedback.set_text(("我的默认打印机：" if zh else "My default printer: ") + name)

    default_button.connect("clicked", choose_default)
    body.pack_start(default_button, False, False, 0)
    test_page.connect("clicked", lambda _: feedback.set_text(submit_test_page(name)))
    body.pack_start(test_page, False, False, 0)
    body.pack_start(feedback, False, False, 0)
    back.destroy()
    forward.destroy()
    cancel.destroy()
    finish = Gtk.Button.new_with_mnemonic("完成(_F)" if zh else "_Finish")
    finish.set_can_default(True)
    finish.connect("clicked", lambda _: window.destroy())
    actions.add(finish)
    window.show_all()
    finish.grab_default()
    finish.grab_focus()
    window.present()


def leave_device_wizard(current):
    if current.returning:
        current.NewPrinterWindow.destroy()
        window.present()
        (address if known_address.get_active() else forward).grab_focus()
    else:
        window.destroy()


def advance(_button):
    global wizard
    uri = None
    if known_address.get_active():
        uri = address.get_text().strip()
        try:
            if len(uri) >= 2 and uri[0] == uri[-1] == '"':
                uri = uri[1:-1]
            if uri.startswith("\\\\") or uri.lower().startswith("smb://"):
                uri = smb_uri(uri, lambda cn, en: cn if zh else en)
            parsed = urlsplit(uri)
            port = parsed.port
            if (parsed.scheme not in {"ipp", "ipps", "smb", "socket", "lpd"} or
                    not parsed.hostname or parsed.password is not None or port == 0 or
                    any(c.isspace() for c in uri) or
                    (parsed.scheme == "smb" and not parsed.path.strip("/"))):
                raise ValueError
        except ValueError:
            error.set_text("请输入有效的网络打印机地址。" if zh else "Enter a valid network printer address.")
            address.grab_focus()
            return
    wizard = PrinterWizard()
    wizard.connect("dialog-canceled", leave_device_wizard)
    wizard.connect("printer-added", printer_added)
    if zh:
        translations = {"Select Device": "选择打印机", "Enter device URI": "输入打印机地址",
                        "For example:": "例如：", "Cancel": "取消", "Forward": "下一步",
                        "Back": "上一步", "Apply": "完成"}
        for builder in wizard._bld:
            for widget in builder.get_objects():
                if isinstance(widget, Gtk.Label):
                    label = widget.get_label()
                    for source, target in translations.items():
                        label = label.replace(source, target)
                    widget.set_label(label)
    if wizard.init("printer_with_uri" if uri else "printer", device_uri=uri, parent=window):
        wizard.btnNPBack.set_label("< 上一步(_B)" if zh else "< _Back")
        wizard.btnNPBack.set_use_underline(True)
        wizard.btnNPApply.set_label("完成(_F)" if zh else "_Finish")
        wizard.btnNPApply.set_use_underline(True)
        wizard.NewPrinterWindow.connect("key-press-event", wizard.device_key)
        wizard.NewPrinterWindow.set_title(title)
        wizard.NewPrinterWindow.set_icon_name("printer")
        display = window.get_display()
        monitor = display.get_monitor_at_window(window.get_window())
        area = monitor.get_workarea()
        if wizard.NewPrinterWindow.get_preferred_height()[0] + 40 > area.height:
            pages = wizard.ntbkNewPrinter
            container = pages.get_parent()
            container.remove(pages)
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scroll.add(pages)
            container.pack_start(scroll, True, True, 0)
            container.reorder_child(scroll, 0)
            scroll.show()
            wizard.NewPrinterWindow.resize(min(640, area.width - 16), area.height - 48)
        wizard.NewPrinterWindow.present()
        window.hide()


back = Gtk.Button.new_with_mnemonic("< 上一步(_B)" if zh else "< _Back")
back.set_sensitive(False)
actions.add(back)
forward = Gtk.Button.new_with_mnemonic("下一步(_N) >" if zh else "_Next >")
forward.connect("clicked", advance)
forward.set_can_default(True)
actions.add(forward)
cancel = Gtk.Button(label="取消" if zh else "Cancel")
cancel.connect("clicked", lambda _: window.destroy())
actions.add(cancel)


def welcome_key(_window, event):
    if event.keyval == Gdk.KEY_Escape and not (event.state & Gtk.accelerator_get_default_mod_mask()):
        window.destroy()
        return True
    return False


window.connect("key-press-event", welcome_key)
window.show_all()
forward.grab_default()
forward.grab_focus()
Gtk.main()
