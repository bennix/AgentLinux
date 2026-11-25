#!/usr/bin/python3
import os
import re
import subprocess
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, GObject, Gtk, Pango

def tr(zh, en):
    return zh if os.getenv("LANGUAGE", os.getenv("LANG", "")).startswith("zh") else en

event_names = {
    "audio-volume-change": ("调整音量", "Volume change"),
    "battery-caution": ("电池电量警告", "Battery warning"),
    "battery-low": ("电池电量低", "Low battery"),
    "bell-terminal": ("终端响铃", "Terminal bell"),
    "bell-window-system": ("窗口系统响铃", "Window system bell"),
    "browser-navigate": ("开始导航", "Start navigation"),
    "complete-media-burn": ("光盘刻录完成", "Disc burning complete"),
    "complete-media-format": ("格式化完成", "Formatting complete"),
    "complete-media-rip": ("媒体提取完成", "Media extraction complete"),
    "desktop-login": ("登录系统", "System logon"),
    "desktop-logout": ("注销系统", "System logoff"),
    "device-added-media": ("连接设备", "Device connected"),
    "device-removed-media": ("断开设备", "Device disconnected"),
    "dialog-error": ("错误", "Error"),
    "dialog-information": ("信息提示", "Information"),
    "dialog-question": ("询问", "Question"),
    "dialog-warning": ("警告", "Warning"),
    "game-over-loser": ("游戏失败", "Game lost"),
    "game-over-winner": ("游戏胜利", "Game won"),
    "message-new-email": ("新邮件通知", "New mail notification"),
    "message-new-instant": ("新即时消息", "New instant message"),
    "phone-incoming-call": ("来电", "Incoming call"),
    "phone-outgoing-busy": ("电话占线", "Busy signal"),
    "phone-outgoing-calling": ("拨出电话", "Outgoing call"),
    "power-unplug-battery-low": ("低电量时拔下电源", "Power unplugged on low battery"),
    "theme-demo": ("声音主题示例", "Sound theme sample"),
    "trash-empty": ("清空回收站", "Empty Recycle Bin"),
}

def pactl(*args):
    return subprocess.run(["pactl", *args], env={**os.environ, "LC_ALL": "C"}, encoding="utf-8", capture_output=True, check=True, timeout=5).stdout.strip()

def device_label(description):
    # PulseAudio constructs these labels in the server's login language.
    for zh, en in (("内置音频 模拟立体声", "Built-in Audio Analog Stereo"),
                   ("监听设备：", "Monitor of "),
                   (" (回声消除参考：", " (echo cancelled with ")):
        description = description.replace(en, tr(zh, en)).replace(zh, tr(zh, en))
    return description


def devices(kind):
    found = {}
    for block in re.split(r"(?m)^\S+ #\d+\s*$", pactl("list", kind)):
        fields = dict(re.findall(r"(?m)^\t(Name|Description): (.+)$", block))
        if "Name" in fields:
            found[fields["Name"]] = device_label(fields.get("Description", fields["Name"]))
    return found

dialog = Gtk.Dialog(title=tr("声音和音频设备 属性", "Sounds and Audio Devices Properties"))
dialog.set_icon_name("audio-card")
dialog.set_default_size(445, 330)
for label, response in [(tr("确定", "OK"), Gtk.ResponseType.OK), (tr("取消", "Cancel"), Gtk.ResponseType.CANCEL), (tr("应用", "Apply"), Gtk.ResponseType.APPLY)]:
    dialog.add_button(label, response)
tabs = Gtk.Notebook(border_width=8)
dialog.get_content_area().pack_start(tabs, True, True, 0)

def page(title):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, border_width=12)
    scroll = Gtk.ScrolledWindow()
    scroll.set_propagate_natural_width(True)
    scroll.set_max_content_width(440)
    scroll.add(box)
    tabs.append_page(scroll, Gtk.Label(label=title))
    return box

def device_selector():
    combo = Gtk.ComboBoxText()
    renderer = combo.get_cells()[0]
    renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
    renderer.set_property("max-width-chars", 30)
    return combo

def group(box, title):
    frame = Gtk.Frame(label=title)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, border_width=10)
    frame.add(content)
    box.pack_start(frame, False, False, 0)
    return content

volume = page(tr("音量", "Volume"))
sound = page(tr("声音", "Sounds"))
audio = page(tr("音频", "Audio"))

voice = page(tr("语音", "Voice"))
hardware = page(tr("硬件", "Hardware"))
hardware_devices = device_selector()
hardware.pack_start(hardware_devices, False, False, 0)
hardware_grid = Gtk.Grid(column_spacing=12, row_spacing=8)
hardware.pack_start(hardware_grid, False, False, 0)
hardware_fields = {}
for row, (key, label) in enumerate((
    ("Driver", tr("驱动程序", "Driver")), ("Sample Specification", tr("采样格式", "Sample format")),
    ("Channel Map", tr("声道映射", "Channel map")), ("Active Port", tr("活动端口", "Active port")),
)):
    hardware_grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
    value = Gtk.Label(xalign=0, selectable=True, wrap=True)
    hardware_grid.attach(value, 1, row, 1, 1)
    hardware_fields[key] = value
hardware_info = {}


def show_hardware(_combo):
    fields = hardware_info.get(hardware_devices.get_active_id(), {})
    for key, field in hardware_fields.items():
        field.set_text(fields.get(key, "—"))


def reload_hardware(_tabs, selected_page, _index):
    if not hardware.is_ancestor(selected_page):
        return
    previous = hardware_devices.get_active_id()
    hardware_devices.remove_all()
    hardware_info.clear()
    for kind, role in (("sinks", tr("播放", "Playback")), ("sources", tr("录音", "Recording"))):
        try:
            listing = pactl("list", kind)
        except (OSError, subprocess.SubprocessError) as exc:
            hardware_devices.set_tooltip_text(str(exc))
            continue
        for block in re.split(r"(?m)^\S+ #\d+\s*$", listing):
            fields = dict(re.findall(r"(?m)^\t(Name|Description|Driver|Sample Specification|Channel Map|Active Port): (.+)$", block))
            name = fields.get("Name")
            if not name or (kind == "sources" and name.endswith(".monitor")):
                continue
            identifier = kind + "/" + name
            hardware_info[identifier] = fields
            hardware_devices.append(identifier, role + " · " + fields.get("Description", name))
    if not hardware_devices.set_active_id(previous or ""):
        hardware_devices.set_active(0)
    show_hardware(hardware_devices)


hardware_devices.connect("changed", show_hardware)
tabs.connect("switch-page", reload_hardware)

def configure():
    try:
        outputs = devices("sinks")
        sources = devices("sources")
    except (OSError, subprocess.SubprocessError):
        outputs, sources = {}, {}
    sink = pactl("get-default-sink") if outputs else None
    device_name = Gtk.Label(xalign=0)
    volume.pack_start(device_name, False, False, 0)
    master = group(volume, tr("设备音量", "Device volume"))
    slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    slider.get_accessible().set_name(tr("设备音量", "Device volume"))
    slider.set_digits(0)
    slider.connect("format-value", lambda _slider, value: f"{value:.0f}%")

    def mark_volume_range(adjustment):
        slider.clear_marks()
        slider.add_mark(0, Gtk.PositionType.BOTTOM, tr("低", "Low"))
        slider.add_mark(adjustment.get_upper(), Gtk.PositionType.BOTTOM, tr("高", "High"))

    slider.get_adjustment().connect("notify::upper", lambda adjustment, _: mark_volume_range(adjustment))
    mark_volume_range(slider.get_adjustment())
    master.add(slider)
    mute = Gtk.CheckButton(label=tr("静音", "Mute"))
    master.add(mute)

    def read_volume(device):
        value = max(map(int, re.findall(r"(\d+)%", pactl("get-sink-volume", device))))
        silent = pactl("get-sink-mute", device).endswith("yes")
        return value, silent

    def load_volume(device):
        value, silent = read_volume(device)
        device_name.set_text(outputs.get(device, device))
        slider.set_range(0, max(100, value))
        slider.set_value(value)
        mute.set_active(silent)
        return value, silent

    if sink:
        initial, muted = load_volume(sink)
    else:
        initial, muted = 0, False
        device_name.set_text(tr("没有可用的音频播放设备", "No audio playback device available"))
        master.set_sensitive(False)
    selectors = []
    for kind, names, title in [("sink", outputs, tr("声音播放", "Sound playback")), ("source", sources, tr("录音", "Sound recording"))]:
        combo = device_selector()
        default = pactl("get-default-" + kind) if names else None
        for identifier, description in names.items():
            if identifier == default or not identifier.endswith(".monitor"):
                combo.append(identifier, description)
        if default:
            combo.set_active_id(default)
        combo.set_sensitive(bool(names))
        combo.get_accessible().set_name(title)
        group(audio, title).add(combo)
        voice_title = tr("语音播放", "Voice playback") if kind == "sink" else tr("语音录制", "Voice recording")
        voice_combo = device_selector()
        voice_combo.set_model(combo.get_model())
        voice_combo.get_accessible().set_name(voice_title)
        voice_combo.set_sensitive(combo.get_sensitive())
        combo.bind_property("active", voice_combo, "active",
                            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        group(voice, voice_title).add(voice_combo)
        selectors.append([kind, combo, default])
    voice.pack_start(Gtk.Label(label=tr("语音与音频使用相同的系统默认设备。",
                                        "Voice and audio share the system default devices."),
                               xalign=0, wrap=True), False, False, 0)
    apply_button = dialog.get_widget_for_response(Gtk.ResponseType.APPLY)

    sound_backends = [Gio.Settings.new(schema) for schema in ("org.gnome.desktop.sound", "org.ukui.sound")]
    scheme = Gtk.ComboBoxText()
    current = sound_backends[0].get_string("theme-name")
    if current != "Windows XP Default":
        scheme.append(current, current)
    scheme.append("Windows XP Default", tr("Windows XP 默认", "Windows XP Default"))
    scheme.append("silent", tr("无声", "No sounds"))
    initial_scheme = current if sound_backends[0].get_boolean("event-sounds") else "silent"
    scheme.set_active_id(initial_scheme)
    scheme_group = group(sound, tr("声音方案", "Sound scheme"))
    scheme_group.add(scheme)
    session_sound = sound_backends[1]
    initial_login = session_sound.get_boolean("startup-music")
    login = Gtk.CheckButton(label=tr("登录时播放声音", "Play a sound at logon"))
    login.set_active(initial_login)
    scheme_group.add(login)
    scheme.set_sensitive(all(s.is_writable(k) for s in sound_backends for k in ("theme-name", "event-sounds")))

    def update_apply(*_):
        changed = round(slider.get_value()) != initial or mute.get_active() != muted
        changed |= any(combo.get_active_id() != previous for _, combo, previous in selectors)
        changed |= login.get_active() != initial_login
        apply_button.set_sensitive(changed or scheme.get_active_id() != initial_scheme)

    slider.connect("value-changed", update_apply)
    mute.connect("toggled", update_apply)
    for _, combo, _previous in selectors:
        combo.connect("changed", update_apply)
    update_apply()
    events = Gtk.ComboBoxText()
    for path in sorted(Path("/usr/share/sounds/Windows XP Default/stereo").glob("*")):
        if path.is_file() and path.suffix.lower() in (".wav", ".oga", ".ogg"):
            names = event_names.get(path.stem)
            events.append(str(path), tr(*names) if names else path.stem)
    events.set_active(0)
    event_group = group(sound, tr("程序事件声音", "Program event sounds"))
    event_group.add(events)
    play = Gtk.Button(label=tr("试听", "Preview"))
    play.set_sensitive(bool(events.get_active_id()))
    preview_process = None

    def stop_preview(*_):
        nonlocal preview_process
        if preview_process is not None:
            preview_process.force_exit()
            preview_process = None
        play.set_label(tr("试听", "Preview"))

    def preview_finished(process, result):
        nonlocal preview_process
        try:
            process.wait_finish(result)
        finally:
            if process is preview_process:
                preview_process = None
                play.set_label(tr("试听", "Preview"))

    def toggle_preview(_):
        nonlocal preview_process
        if preview_process is not None:
            stop_preview()
            return
        try:
            preview_process = Gio.Subprocess.new(["paplay", events.get_active_id()], Gio.SubprocessFlags.NONE)
        except GLib.Error as error:
            play.set_tooltip_text(error.message)
            return
        play.set_label(tr("停止试听", "Stop preview"))
        preview_process.wait_async(None, preview_finished)

    play.connect("clicked", toggle_preview)
    events.connect("changed", stop_preview)
    event_group.add(play)

    def scheme_changed(*_):
        stop_preview()
        if scheme.get_active_id() == "silent" and session_sound.is_writable("startup-music"):
            login.set_active(False)
        login.set_sensitive(scheme.get_active_id() != "silent" and session_sound.is_writable("startup-music"))
        event_group.set_sensitive(scheme.get_active_id() == "Windows XP Default")
        update_apply()

    scheme.connect("changed", scheme_changed)
    login.connect("toggled", update_apply)
    event_group.set_sensitive(initial_scheme == "Windows XP Default")
    login.set_sensitive(session_sound.is_writable("startup-music") and initial_scheme != "silent")
    def sync_volume(channel, condition):
        nonlocal initial, muted
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            return False
        event = channel.readline()
        if sink and "on sink #" in event:
            try:
                value, silent = read_volume(sink)
            except (OSError, subprocess.SubprocessError, ValueError):
                return True
            if round(slider.get_value()) == initial:
                slider.set_range(0, max(100, value))
                slider.set_value(value)
            if mute.get_active() == muted:
                mute.set_active(silent)
            initial, muted = value, silent
            update_apply()
        return True

    listener = None
    watch = None
    if outputs or sources:
        listener = subprocess.Popen(["pactl", "subscribe"], stdout=subprocess.PIPE, env={**os.environ, "LC_ALL": "C"})
        channel = GLib.IOChannel.unix_new(listener.stdout.fileno())
        watch = GLib.io_add_watch(channel, GLib.PRIORITY_DEFAULT, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, sync_volume)
    try:
        dialog.show_all()
        if len(sys.argv) == 2 and sys.argv[1] in ("0", "1", "2", "3", "4"):
            tabs.set_current_page(int(sys.argv[1]))
        while True:
            response = dialog.run()
            if response not in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK):
                break
            choice = scheme.get_active_id()
            if choice != initial_scheme:
                for backend in sound_backends:
                    if choice != "silent":
                        backend.set_string("theme-name", choice)
                    backend.set_boolean("event-sounds", choice != "silent")
                initial_scheme = choice
            if login.get_active() != initial_login:
                session_sound.set_boolean("startup-music", login.get_active())
                initial_login = session_sound.get_boolean("startup-music")
            value = round(slider.get_value())
            if value != initial:
                pactl("set-sink-volume", sink, str(value) + "%")
                initial = value
            if mute.get_active() != muted:
                pactl("set-sink-mute", sink, "1" if mute.get_active() else "0")
                muted = mute.get_active()
            for item in selectors:
                kind, combo, previous = item
                selection = combo.get_active_id()
                if selection and selection != previous:
                    pactl("set-default-" + kind, selection)
                    item[2] = selection
                    if kind == "sink":
                        sink = selection
                        initial, muted = load_volume(sink)
            update_apply()
            if response == Gtk.ResponseType.OK:
                break
    finally:
        stop_preview()
        if watch and GLib.MainContext.default().find_source_by_id(watch):
            GLib.source_remove(watch)
        if listener:
            listener.terminate()
            listener.wait()
            listener.stdout.close()


try:
    configure()
except (OSError, subprocess.SubprocessError, ValueError) as exc:
    error = Gtk.MessageDialog(transient_for=dialog, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text=tr("无法访问音频设备", "Cannot access audio device"))
    error.format_secondary_text(getattr(exc, "stderr", None) or str(exc))
    error.run()
    error.destroy()
dialog.destroy()
