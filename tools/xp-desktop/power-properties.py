#!/usr/bin/python3
import os
import sys
from pathlib import Path
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GUdev", "1.0")
from gi.repository import Gio, GLib, GObject, Gtk, GUdev

from task_pane import cycle_property_pages

def tr(zh, en):
    return zh if os.getenv("LANGUAGE", os.getenv("LANG", "")).startswith("zh") else en

settings = Gio.Settings.new("org.ukui.power-manager")
settings.delay()
window = Gtk.Dialog(title=tr("电源选项 属性", "Power Options Properties"))
window.set_default_size(470, 285)
window.set_icon_name("battery")
for label, response in [(tr("确定", "OK"), Gtk.ResponseType.OK), (tr("取消", "Cancel"), Gtk.ResponseType.CANCEL), (tr("应用", "Apply"), Gtk.ResponseType.APPLY)]:
    window.add_button(label, response)
tabs = Gtk.Notebook(border_width=8)
window.connect("key-press-event", cycle_property_pages, tabs)
window.get_content_area().pack_start(tabs, True, True, 0)
grid = Gtk.Grid(column_spacing=12, row_spacing=14, border_width=12)
tabs.append_page(grid, Gtk.Label(label=tr("电源使用方案", "Power Schemes")))
for col, (suffix, title) in enumerate([("ac", tr("使用交流电源", "Plugged in")), ("battery", tr("使用电池", "Running on batteries"))], 1):
    grid.attach(Gtk.Label(label=title), col, 0, 1, 1)
    for row, (key, title) in enumerate([("sleep-display-", tr("关闭显示器", "Turn off monitor")), ("sleep-computer-", tr("系统待机", "System standby"))], 1):
        if col == 1:
            grid.attach(Gtk.Label(label=title, xalign=0), 0, row, 1, 1)
        name = key + suffix
        current = settings.get_int(name)
        combo = Gtk.ComboBoxText()
        for sec in sorted({0, 60, 180, 300, 600, 900, 1200, 1800, 3600, current}):
            text = tr("从不", "Never") if sec == 0 else (tr(f"{sec//60} 分钟", f"{sec//60} min") if sec % 60 == 0 else tr(f"{sec} 秒", f"{sec} s"))
            combo.append(str(sec), text)
        combo.set_active_id(str(current))
        settings.bind_writable(name, combo, "sensitive", False)
        combo.connect("changed", lambda w, k=name: settings.set_int(k, int(w.get_active_id())))
        grid.attach(combo, col, row, 1, 1)
meter = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=16)
tabs.append_page(meter, Gtk.Label(label=tr("电表", "Power Meter")))
advanced = Gtk.Grid(column_spacing=12, row_spacing=12, border_width=14)
tabs.append_page(advanced, Gtk.Label(label=tr("高级", "Advanced")))
advanced.attach(Gtk.Label(label=tr("合上笔记本盖时", "When I close the lid"), xalign=0), 0, 0, 2, 1)
lid_actions = {
    "blank": tr("关闭屏幕", "Turn off the screen"), "nothing": tr("不执行操作", "Do nothing"),
    "suspend": tr("待机", "Stand by"), "hibernate": tr("休眠", "Hibernate"),
    "shutdown": tr("关机", "Shut down"), "interactive": tr("询问操作", "Ask what to do"),
    "notify": tr("显示通知", "Show a notification"),
}
for row, (suffix, title) in enumerate([("ac", tr("使用交流电源", "Plugged in")),
                                       ("battery", tr("使用电池", "Running on batteries"))], 1):
    key = "button-lid-" + suffix
    advanced.attach(Gtk.Label(label=title, xalign=0), 0, row, 1, 1)
    choices = Gtk.ComboBoxText()
    for value in settings.props.settings_schema.get_key(key).get_range().unpack()[1]:
        choices.append(value, lid_actions.get(value, value))
    choices.set_active_id(settings.get_string(key))
    settings.bind_writable(key, choices, "sensitive", False)
    choices.connect("changed", lambda widget, k=key: settings.set_string(k, widget.get_active_id()))
    advanced.attach(choices, 1, row, 1, 1)

def battery_capacity_details(device):
    for metric, unit in (("energy", "Wh"), ("charge", "Ah")):
        try:
            full = int((device / (metric + "_full")).read_text())
            design = int((device / (metric + "_full_design")).read_text())
        except (OSError, ValueError):
            continue
        if full > 0 and design > 0:
            return tr("满充容量", "Full charge capacity") + f"  {full / 1e6:.2f} {unit}  ·  " + tr(
                "设计容量", "Design capacity") + f"  {design / 1e6:.2f} {unit}  ({full / design:.0%})"
    return ""


def battery_time(device, state):
    if state not in ("Charging", "Discharging"):
        return ""
    charging = state == "Charging"
    key = "time_to_full_now" if charging else "time_to_empty_now"
    try:
        seconds = int((device / key).read_text())
    except (ValueError, OSError):
        seconds = 0
    if seconds <= 0:
        for metric, rate in (("energy", "power_now"), ("charge", "current_now")):
            try:
                amount = int((device / (metric + "_now")).read_text())
                if charging:
                    amount = int((device / (metric + "_full")).read_text()) - amount
                speed = abs(int((device / rate).read_text()))
            except (ValueError, OSError):
                continue
            if amount > 0 and speed:
                seconds = round(3600 * amount / speed)
                break
    if seconds <= 0:
        return ""
    hours, minutes = divmod(max(1, round(seconds / 60)), 60)
    label = tr("预计充满时间", "Estimated time to full") if charging else tr("预计剩余时间", "Estimated time remaining")
    return label + "  " + tr(f"{hours} 小时 {minutes:02d} 分钟", f"{hours} h {minutes:02d} min")


def refresh():
    for child in meter.get_children():
        child.destroy()
    supplies = []
    batteries = 0
    for device in sorted(Path("/sys/class/power_supply").glob("*")):
        try:
            try:
                if (device / "scope").read_text().strip() == "Device":
                    continue
            except FileNotFoundError:
                pass
            kind = (device / "type").read_text().strip()
            if kind != "Battery":
                if kind in ("Mains", "Wireless") or kind.startswith("USB"):
                    supplies.append(int((device / "online").read_text()))
                continue
            capacity = int((device / "capacity").read_text())
            try:
                state = (device / "status").read_text().strip()
            except OSError:
                state = "Unknown"
            state_label = {"Charging": tr("正在充电", "Charging"), "Discharging": tr("正在放电", "Discharging"),
                           "Not charging": tr("未在充电", "Not charging"), "Full": tr("已充满", "Full")}.get(
                               state, tr("充电状态未知", "Charge status unknown"))
            summary = f"{device.name}   {capacity}%   ·   {state_label}"
            meter.pack_start(Gtk.Label(label=summary, xalign=0), False, False, 0)
            bar = Gtk.ProgressBar()
            bar.get_accessible().set_name(summary)
            bar.set_fraction(min(1, max(0, capacity / 100)))
            meter.pack_start(bar, False, False, 0)
            details = battery_capacity_details(device)
            if details:
                meter.pack_start(Gtk.Label(label=details, xalign=0, wrap=True), False, False, 0)
            readings = []
            for key, title, unit in (("voltage_now", tr("电池电压", "Battery voltage"), "V"),
                                     ("current_now", tr("电池电流", "Battery current"), "A"),
                                     ("power_now", tr("电池功率", "Battery power"), "W")):
                try:
                    value = int((device / key).read_text()) / 1e6
                except (OSError, ValueError):
                    continue
                readings.append(f"{title}  {value:.2f} {unit}")
            if readings:
                meter.pack_start(Gtk.Label(label="  ·  ".join(readings), xalign=0, wrap=True), False, False, 0)
            estimate = battery_time(device, state)
            if estimate:
                meter.pack_start(Gtk.Label(label=estimate, xalign=0), False, False, 0)
            batteries += 1
        except (OSError, ValueError):
            continue
    window.set_icon_name("ac-adapter" if any(supplies) else "battery")
    if supplies:
        source = tr("外部电源已连接", "External power connected") if any(supplies) else tr("外部电源未连接", "External power disconnected")
        label = Gtk.Label(label=source, xalign=0)
        source_row = Gtk.Box(spacing=8)
        source_row.pack_start(Gtk.Image.new_from_icon_name(window.get_icon_name(), Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
        source_row.pack_start(label, False, False, 0)
        meter.pack_start(source_row, False, False, 0)
        meter.reorder_child(source_row, 0)
    if not batteries:
        meter.add(Gtk.Label(label=tr("未检测到电池", "No battery detected")))
    meter.show_all()
    return True
power_devices = GUdev.Client.new(["power_supply"])
power_handler = power_devices.connect("uevent", lambda *_: refresh())
refresh()
timer = GLib.timeout_add_seconds(15, refresh)
apply_button = window.get_widget_for_response(Gtk.ResponseType.APPLY)
settings.bind_property("has-unapplied", apply_button, "sensitive", GObject.BindingFlags.SYNC_CREATE)
window.show_all()
if sys.argv[1:] == ["--meter"]:
    tabs.set_current_page(tabs.page_num(meter))
elif len(sys.argv) == 2 and sys.argv[1] in ("0", "1", "2"):
    tabs.set_current_page(int(sys.argv[1]))
while True:
    response = window.run()
    if response in (Gtk.ResponseType.OK, Gtk.ResponseType.APPLY):
        settings.apply()
        Gio.Settings.sync()
    if response != Gtk.ResponseType.APPLY:
        break
power_devices.disconnect(power_handler)
GLib.source_remove(timer)
settings.revert()
window.destroy()
