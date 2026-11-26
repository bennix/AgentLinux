#!/usr/bin/python3
import locale
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

language = os.getenv("LANGUAGE", os.getenv("LANG", "en_US"))
os.environ["LC_TIME"] = "zh_CN.UTF-8" if language.startswith("zh") else "en_US.UTF-8"
locale.setlocale(locale.LC_TIME, os.environ["LC_TIME"])

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, GObject, Gtk

from task_pane import cycle_property_pages

def tr(zh, en):
    return zh if os.getenv("LANGUAGE", os.getenv("LANG", "")).startswith("zh") else en

def status():
    result = subprocess.check_output(["timedatectl", "show", "-p", "Timezone", "-p", "CanNTP", "-p", "NTP", "-p", "NTPSynchronized"], text=True, timeout=4)
    return dict(line.split("=", 1) for line in result.splitlines())

def draw_clock(_, ctx):
    now = datetime.now()
    ctx.translate(76, 76)
    ctx.set_source_rgb(.99, .99, .96)
    ctx.arc(0, 0, 67, 0, math.tau)
    ctx.fill_preserve()
    ctx.set_source_rgb(.24, .32, .43)
    ctx.set_line_width(2)
    ctx.stroke()
    for tick in range(60):
        ctx.save()
        ctx.rotate(tick * math.tau / 60)
        ctx.move_to(0, -62)
        ctx.line_to(0, -55 if tick % 5 == 0 else -60)
        ctx.stroke()
        ctx.restore()
    ctx.select_font_face("Sans")
    ctx.set_font_size(11)
    for hour in range(1, 13):
        angle = hour * math.tau / 12
        label = str(hour)
        left, top, width, height, _, _ = ctx.text_extents(label)
        ctx.move_to(46 * math.sin(angle) - left - width / 2,
                    -46 * math.cos(angle) - top - height / 2)
        ctx.show_text(label)
    for fraction, length, width in [((now.hour + now.minute / 60) / 12, 34, 5), (now.minute / 60, 49, 3), (now.second / 60, 54, 1)]:
        ctx.save()
        ctx.rotate(fraction * math.tau)
        if width == 1:
            ctx.set_source_rgb(.69, .15, .12)
        ctx.set_line_width(width)
        ctx.move_to(0, 5)
        ctx.line_to(0, -length)
        ctx.stroke()
        ctx.restore()
    ctx.arc(0, 0, 3, 0, math.tau)
    ctx.fill()

window = Gtk.Dialog(title=tr("日期和时间 属性", "Date and Time Properties"))
window.set_icon_name("appointment-new")
window.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
tabs = Gtk.Notebook(border_width=8)
window.connect("key-press-event", cycle_property_pages, tabs)
window.get_content_area().pack_start(tabs, True, True, 0)
def page(label):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=12)
    tabs.append_page(box, Gtk.Label(label=label))
    return box

general = page(tr("日期和时间", "Date and Time"))
row = Gtk.Box(spacing=12)
general.add(row)
date_frame = Gtk.Frame(label=tr("日期", "Date"))
row.pack_start(date_frame, True, True, 0)
date_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, border_width=6)
date_frame.add(date_box)
calendar = Gtk.Calendar()
date_box.add(calendar)
selected_date = Gtk.Label(selectable=True)
selected_date.get_accessible().set_name(tr("所选日期", "Selected date"))
date_box.add(selected_date)


def update_selected_date(*_):
    year, month, day = calendar.get_date()
    try:
        value = datetime(year, month + 1, day)
    except ValueError:
        selected_date.set_text("")
        return
    selected_date.set_text(value.strftime(tr("%Y年%m月%d日 %A", "%A, %B %d, %Y")))


calendar.connect("day-selected", update_selected_date)
calendar.connect("month-changed", update_selected_date)
update_selected_date()
today_button = Gtk.Button(label=tr("今天", "Today"))
date_box.add(today_button)


def go_to_today(_button):
    now = datetime.now()
    calendar.select_month(now.month - 1, now.year)
    calendar.select_day(now.day)
    calendar.grab_focus()


today_button.connect("clicked", go_to_today)
time_frame = Gtk.Frame(label=tr("时间", "Time"))
row.pack_start(time_frame, False, False, 0)
clock_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, border_width=6)
time_frame.add(clock_box)
clock = Gtk.DrawingArea()
clock.set_size_request(152, 152)
clock.connect("draw", draw_clock)
clock_box.add(clock)
digital = Gtk.Label(selectable=True)
digital.get_accessible().set_name(tr("当前时间", "Current time"))
clock_box.add(digital)
zone = page(tr("时区", "Time Zone"))
internet = page(tr("Internet 时间", "Internet Time"))
zone_name = Gtk.Label(xalign=0)
zone_row = Gtk.Box(spacing=6)
general.add(zone_row)
zone_row.add(Gtk.Label(label=tr("当前时区", "Current time zone"), xalign=0))
clock_zone = Gtk.Label(xalign=0, selectable=True)
zone_row.add(clock_zone)
zone_name.bind_property("label", clock_zone, "label", GObject.BindingFlags.SYNC_CREATE)
sync = Gtk.Label(xalign=0)
zone.add(zone_name)
internet.add(sync)
switch_sync = Gtk.Button()
internet.add(switch_sync)
sync_feedback = Gtk.Label(xalign=0, wrap=True)
internet.add(sync_feedback)
ntp_enabled = None
ntp_pending = False


def change_sync(button):
    global ntp_pending
    if ntp_enabled is None or ntp_pending or not button.get_sensitive():
        return
    try:
        process = Gio.Subprocess.new(["timedatectl", "set-ntp", "false" if ntp_enabled else "true"],
                                     Gio.SubprocessFlags.STDERR_PIPE)
    except GLib.Error as error:
        sync_feedback.set_text(error.message)
        return
    ntp_pending = True
    button.set_sensitive(False)
    sync_feedback.set_text(tr("正在应用设置…", "Applying settings…"))

    def finished(process, result):
        global ntp_pending
        try:
            _, _, stderr = process.communicate_utf8_finish(result)
            message = "" if process.get_successful() else stderr.strip() or tr("设置失败", "Could not change setting")
        except GLib.Error as error:
            message = error.message
        ntp_pending = False
        sync_feedback.set_text(message)
        refresh_status()
        read_sync_details()

    process.communicate_utf8_async(None, None, finished)


switch_sync.connect("clicked", change_sync)
sync_details = Gtk.Label(xalign=0, selectable=True, wrap=True)
internet.add(sync_details)
refresh_sync = Gtk.Button(label=tr("刷新校时详情", "Refresh synchronization details"))
internet.add(refresh_sync)


def read_sync_details(*_):
    if not refresh_sync.get_sensitive():
        return
    refresh_sync.set_sensitive(False)
    launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    launcher.setenv("LC_ALL", "C", True)

    def finished(process, result):
        try:
            _, output, _ = process.communicate_utf8_finish(result)
            fields = dict(line.strip().split(": ", 1) for line in output.splitlines() if ": " in line)
            names = [("Server", tr("服务器", "Server")), ("Stratum", tr("时钟层级", "Stratum")),
                     ("Offset", tr("时钟偏差", "Clock offset")), ("Delay", tr("网络延迟", "Network delay"))]
            lines = [f"{label}   {fields[key]}" for key, label in names if fields.get(key)]
            interval = fields.get("Poll interval", "").partition(" (")[0]
            if interval:
                lines.append(tr("校时间隔", "Polling interval") + "   " + interval)
            sync_details.set_text("\n".join(lines) if process.get_successful() and lines else
                                  tr("暂无校时详情", "Synchronization details unavailable"))
        except GLib.Error as error:
            sync_details.set_text(error.message)
        refresh_sync.set_sensitive(True)

    try:
        process = launcher.spawnv(["timedatectl", "timesync-status"])
        process.communicate_utf8_async(None, None, finished)
    except GLib.Error as error:
        sync_details.set_text(error.message)
        refresh_sync.set_sensitive(True)


def refresh_internet_time(*_):
    refresh_status()
    read_sync_details()


refresh_sync.connect("clicked", refresh_internet_time)
internet.connect("map", read_sync_details)
zones = sorted(available_timezones())
zone_picker = Gtk.ComboBoxText.new_with_entry()
zone_picker.get_child().set_placeholder_text(tr("输入城市或时区", "Enter a city or time zone"))
for name in zones:
    zone_picker.append(name, name)
completion = Gtk.EntryCompletion()
suggestions = Gtk.ListStore(str, str)
try:
    from babel.dates import get_timezone_location
except ImportError:
    get_timezone_location = None
# Localized city names can be identical for a zone and its historical aliases.
try:
    zone_table = Path("/usr/share/zoneinfo/zone.tab").read_text().splitlines()
    locations = {line.split()[2] for line in zone_table if line and not line.startswith("#")}
except OSError:
    locations = set()
for name in sorted(zones, key=lambda zone: zone not in locations):
    city = ""
    if get_timezone_location and "/" in name:
        try:
            city = get_timezone_location(ZoneInfo(name), locale=tr("zh_CN", "en_US"), return_city=True)
        except (KeyError, ValueError, ZoneInfoNotFoundError):
            pass
    suggestions.append((name, city))
completion.set_model(suggestions)
completion.set_text_column(0)
city_cell = Gtk.CellRendererText()
completion.pack_start(city_cell, False)
completion.add_attribute(city_cell, "text", 1)
completion.set_match_func(lambda comp, key, it, _: any(key.casefold() in text.casefold()
                          for text in comp.get_model()[it]), None)
zone_picker.get_child().set_completion(completion)
zone.add(zone_picker)
zone_preview = Gtk.Label(xalign=0, selectable=True)
zone.add(zone_preview)
preview_zone = None
apply_zone = Gtk.Button(label=tr("应用时区", "Apply time zone"))
zone_actions = Gtk.Box(spacing=6)
zone.add(zone_actions)
zone_actions.add(apply_zone)
reset_zone = Gtk.Button(label=tr("返回当前时区", "Return to current time zone"))
zone_actions.add(reset_zone)
zone_feedback = Gtk.Label(xalign=0, wrap=True)
zone.add(zone_feedback)
current_zone = None
zone_request = None


def update_preview():
    if not preview_zone:
        zone_preview.set_text("")
        return
    now = datetime.now(preview_zone)
    offset = now.strftime("%z")
    label = tr("所选时区时间", "Time in selected zone")
    zone_preview.set_text(f"{label}  {now:%x %H:%M:%S}  (UTC{offset[:3]}:{offset[3:5]})")


def update_zone_button(*_):
    global preview_zone
    name = zone_picker.get_child().get_text().strip()
    preview_zone = ZoneInfo(name) if name in zones else None
    update_preview()
    reset_zone.set_sensitive(zone_request is None and current_zone is not None and name != current_zone)
    apply_zone.set_sensitive(zone_request is None and current_zone is not None and name in zones and name != current_zone)


def zone_finished(process, result):
    global zone_request
    try:
        _, _, stderr = process.communicate_utf8_finish(result)
        feedback = "" if process.get_successful() else stderr.strip() or tr("时区设置失败", "Could not set time zone")
    except GLib.Error as error:
        feedback = error.message
    zone_request = None
    zone_picker.set_sensitive(True)
    zone_feedback.set_text(feedback)
    refresh_status()
    update_zone_button()


def change_zone(_):
    global zone_request
    name = zone_picker.get_child().get_text().strip()
    if zone_request is not None or name not in zones or name == current_zone:
        return
    try:
        zone_request = Gio.Subprocess.new(["timedatectl", "set-timezone", name], Gio.SubprocessFlags.STDERR_PIPE)
    except GLib.Error as error:
        zone_feedback.set_text(error.message)
        return
    zone_picker.set_sensitive(False)
    update_zone_button()
    zone_feedback.set_text(tr("正在应用时区…", "Applying time zone…"))
    zone_request.communicate_utf8_async(None, None, zone_finished)


zone_picker.get_child().connect("changed", update_zone_button)
apply_zone.connect("clicked", change_zone)
reset_zone.connect("clicked", lambda _: zone_picker.get_child().set_text(current_zone))
for box, label in [(general, tr("更改日期和时间…", "Change date and time…")), (internet, tr("更改校时设置…", "Change synchronization settings…"))]:
    button = Gtk.Button(label=label)
    button.connect("clicked", lambda _: subprocess.Popen(["/usr/bin/ukui-control-center", "-p", "datetime"]))
    box.pack_end(button, False, False, 0)
def refresh_status(*_):
    global current_zone, ntp_enabled
    try:
        data = status()
        timezone = data["Timezone"]
        entry = zone_picker.get_child()
        if current_zone is None or entry.get_text() == current_zone:
            entry.set_text(timezone)
        current_zone = timezone
        update_zone_button()
        try:
            offset = datetime.now(ZoneInfo(timezone)).strftime("%z")
            zone_name.set_text(f"(UTC{offset[:3]}:{offset[3:5]}) {timezone}")
        except (ZoneInfoNotFoundError, ValueError):
            zone_name.set_text(timezone)
        ntp_enabled = data["NTP"] == "yes"
        switch_sync.set_label(tr("关闭自动校时", "Turn off automatic synchronization") if ntp_enabled else
                              tr("启用自动校时", "Turn on automatic synchronization"))
        switch_sync.set_sensitive(data.get("CanNTP") == "yes" and not ntp_pending)
        sync.set_text(tr("自动校时已关闭", "Automatic synchronization is off") if data["NTP"] != "yes" else (tr("已与网络时间同步", "Synchronized with network time") if data["NTPSynchronized"] == "yes" else tr("正在等待网络校时", "Waiting for network synchronization")))
    except (OSError, subprocess.SubprocessError, KeyError):
        ntp_enabled = None
        switch_sync.set_label(tr("自动校时", "Automatic synchronization"))
        switch_sync.set_sensitive(False)
        for label in (zone_name, sync):
            label.set_text(tr("无法读取系统时间配置", "Time settings are unavailable"))
    return False
def tick():
    update_preview()
    digital.set_text(datetime.now().strftime("%H:%M:%S"))
    clock.queue_draw()
    return True
window.connect("focus-in-event", refresh_status)
refresh_status()
tick()
timer = GLib.timeout_add_seconds(1, tick)
window.show_all()
if len(sys.argv) == 2 and sys.argv[1] in ("0", "1", "2"):
    tabs.set_current_page(int(sys.argv[1]))
window.run()
GLib.source_remove(timer)
window.destroy()
