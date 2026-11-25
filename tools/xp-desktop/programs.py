#!/usr/bin/python3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango
from task_pane import fit_window, add_task_pane, task_button


def tr(zh, en):
    return zh if GLib.get_language_names()[0].startswith("zh") else en


window = Gtk.Window(title=tr("添加或删除程序", "Add or Remove Programs"))
fit_window(window, 650, 420)
window.set_icon_name("system-software-install")
window.connect("destroy", Gtk.main_quit)
layout = Gtk.Box(spacing=12, border_width=12)
window.add(layout)
side = add_task_pane(layout, tr("程序任务", "Program Tasks"))
def installed_entry(desktop):
    try:
        return Gio.DesktopAppInfo.new(desktop)
    except TypeError:
        return None


store = installed_entry("ubuntu-kylin-software-center.desktop")
manage = task_button(tr("添加或删除软件…", "Add or remove software…"))
manage.set_sensitive(store is not None)
if store:
    manage.connect("clicked", lambda _: store.launch([], None))
side.add(manage)

installer = installed_entry("agentlinux-xp-deb.desktop")


def choose_package(_):
    chooser = Gtk.FileChooserDialog(title=tr("选择安装包", "Select an installation package"),
                                    transient_for=window, action=Gtk.FileChooserAction.OPEN)
    chooser.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    chooser.add_button(tr("打开", "Open"), Gtk.ResponseType.OK)
    chooser.set_default_response(Gtk.ResponseType.OK)
    chooser.set_local_only(True)
    packages = Gtk.FileFilter()
    packages.set_name(tr("Debian 软件包 (*.deb)", "Debian packages (*.deb)"))
    packages.add_pattern("*.[dD][eE][bB]")
    chooser.add_filter(packages)
    downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
    if downloads:
        chooser.set_current_folder(downloads)
    chosen = chooser.get_file() if chooser.run() == Gtk.ResponseType.OK else None
    chooser.destroy()
    if chosen:
        try:
            info = subprocess.run(
                ["dpkg-deb", "--show", "--showformat=" + r"${Package}\n${Version}\n${Architecture}", chosen.get_path()],
                capture_output=True, text=True, errors="replace", check=True, timeout=5,
            ).stdout.splitlines()
        except (OSError, subprocess.SubprocessError):
            detail.set_text(tr("无法读取 Debian 安装包信息。", "Could not read the Debian package information."))
            return
        preview = Gtk.Dialog(title=tr("安装包属性", "Package Properties"), transient_for=window, modal=True)
        preview.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
        preview.add_button(tr("打开安装器", "Open installer"), Gtk.ResponseType.OK)
        preview.set_default_response(Gtk.ResponseType.CANCEL)
        grid = Gtk.Grid(border_width=12, row_spacing=6, column_spacing=12)
        fit_window(preview, 420, 220)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(grid)
        preview.get_content_area().pack_start(scroll, True, True, 0)
        labels = [tr("软件包", "Package"), tr("版本", "Version"), tr("架构", "Architecture")]
        for row, (label, value) in enumerate(zip(labels, info)):
            grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
            field = Gtk.Label(label=value, xalign=0, selectable=True, wrap=True)
            field.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            field.set_max_width_chars(36)
            field.set_hexpand(True)
            grid.attach(field, 1, row, 1, 1)
        preview.show_all()
        proceed = preview.run() == Gtk.ResponseType.OK
        preview.destroy()
        if not proceed:
            return
        try:
            installer.launch([chosen], None)
        except GLib.Error as exc:
            detail.set_text(exc.message)


local_package = task_button(tr("从文件安装…", "Install from file…"))
local_package.set_sensitive(installer is not None)
local_package.connect("clicked", choose_package)
side.add(local_package)
main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
layout.pack_start(main, True, True, 0)
main.add(Gtk.Label(label=tr("当前安装的桌面程序", "Currently installed desktop programs"), xalign=0))
find = task_button(tr("查找已安装的程序", "Find an installed program"))
side.add(find)
search = Gtk.SearchEntry(placeholder_text=tr("搜索程序、软件包或 .deb 文件名", "Search programs, packages or .deb filenames"))
main.add(search)
def focus_search(_button):
    search.grab_focus()
    search.select_region(0, -1)


shortcuts = Gtk.AccelGroup()
window.add_accel_group(shortcuts)
find.connect("clicked", focus_search)
find.add_accelerator("clicked", shortcuts, Gdk.KEY_f, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
find.set_tooltip_text(find.get_label() + " (Ctrl+F)")
order = Gtk.ComboBoxText()
order.append("name", tr("名称", "Name"))
order.append("size", tr("软件包大小（从大到小）", "Package size (largest first)"))
order.set_active_id("name")
sort_bar = Gtk.Box(spacing=6)
sort_bar.add(Gtk.Label(label=tr("排序方式", "Sort by")))
sort_bar.add(order)
main.add(sort_bar)
rows = Gtk.ListStore(str, str, str, Gio.Icon, GObject.TYPE_INT64, str)
worker = ThreadPoolExecutor(max_workers=1)
pending = None

def sort_rows(*_):
    if order.get_active_id() == "size":
        rows.set_sort_column_id(4, Gtk.SortType.DESCENDING)
    else:
        rows.set_sort_column_id(0, Gtk.SortType.ASCENDING)

order.connect("changed", sort_rows)
sort_rows()

def reload_apps(*_):
    global pending
    if pending:
        pending.cancel()
    selection = table.get_selection()
    model, item = selection.get_selected()
    previous = model[item][1] if item is not None else None
    rows.clear()
    for app in sorted(Gio.AppInfo.get_all(), key=lambda a: a.get_display_name().casefold()):
        if isinstance(app, Gio.DesktopAppInfo) and app.should_show():
            filename = app.get_filename()
            display_name = app.get_display_name()
            name = app.get_string("Name") or ""
            generic = app.get_string("GenericName") or ""
            if generic and display_name == f"{name} {generic}":
                display_name = f"{app.get_name()} {app.get_locale_string('GenericName') or generic}"
            names = [display_name, app.get_display_name(), name]
            translations = GLib.KeyFile()
            try:
                translations.load_from_file(filename, GLib.KeyFileFlags.KEEP_TRANSLATIONS)
                translation_keys, _ = translations.get_keys("Desktop Entry")
                for language in ("zh_CN", "en_US"):
                    for key in ("Name", "GenericName", "X-GNOME-FullName"):
                        if key in translation_keys:
                            names.append(translations.get_locale_string("Desktop Entry", key, language))
            except GLib.Error:
                pass
            cached = packages.get(filename)
            size = cached[2] if cached else -1
            if cached:
                names.append(cached[0])
            rows.append([display_name, filename, "\n".join(names).casefold(),
                         app.get_icon() or Gio.ThemedIcon.new("application-x-executable"), size,
                         size_label(size) if cached else "—"])
    if previous:
        for row in filtered:
            if row[1] == previous:
                table.set_cursor(row.path)
                break

    pending = worker.submit(package_index)
    pending.add_done_callback(lambda job: GLib.idle_add(load_sizes, job))
    selected(selection)


filtered = rows.filter_new()
search_package = None
archive_job = None
requested_result = None
last_query = None


def matches_program(model, item, _data):
    if search_package is not None:
        info = packages.get(model[item][1])
        return bool(info and info[0].partition(":")[0].casefold() == search_package)
    return search.get_text().strip().casefold() in model[item][2]


def read_package_name(path):
    result = subprocess.run(["dpkg-deb", "--field", str(path), "Package"], capture_output=True,
                            text=True, check=True, timeout=5)
    return result.stdout.strip().casefold()


def use_package_name(job, original):
    global search_package, archive_job
    if job is archive_job and search.get_text().strip() == original:
        archive_job = None
        try:
            search_package = job.result()
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        filtered.refilter()
        selected(table.get_selection())
        select_requested_result()
    return False


def update_search(_entry, *, refresh=False):
    global search_package, archive_job, last_query
    original = search.get_text().strip()
    if not refresh and original == last_query:
        return
    last_query = original
    if archive_job:
        archive_job.cancel()
        archive_job = None
    search_package = None
    if original.lower().endswith(".deb"):
        path = Path(original)
        search_package = path.stem.partition("_")[0].casefold()
        if path.parent == Path(".") and downloads_folder:
            path = Path(downloads_folder) / path
        if path.is_absolute() and path.is_file():
            archive_job = worker.submit(read_package_name, path)
            archive_job.add_done_callback(lambda done: GLib.idle_add(use_package_name, done, original))
    filtered.refilter()
    selected(table.get_selection())


downloads_folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
filtered.set_visible_func(matches_program)
search.connect("search-changed", update_search)
table = Gtk.TreeView(model=filtered)
column = Gtk.TreeViewColumn(tr("名称", "Name"))
icon = Gtk.CellRendererPixbuf()
column.pack_start(icon, False)
column.add_attribute(icon, "gicon", 3)
caption = Gtk.CellRendererText()
caption.set_property("ellipsize", Pango.EllipsizeMode.END)
column.set_expand(True)
column.pack_start(caption, True)
column.add_attribute(caption, "text", 0)
table.append_column(column)
table.append_column(Gtk.TreeViewColumn(tr("软件包大小", "Package size"), Gtk.CellRendererText(), text=5))
scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
scroll.add(table)
main.pack_start(scroll, True, True, 0)
detail = Gtk.Label(xalign=0, selectable=True, wrap=True)
main.add(detail)


packages = {}


def package_index():
    owners = subprocess.run(["dpkg-query", "-S", "*/applications/*.desktop"], capture_output=True, text=True)
    result = subprocess.run(["dpkg-query", "-W", "-f=" + r"${binary:Package}\t${Version}\t${Installed-Size}\n"],
                            capture_output=True, text=True, check=True)
    stats = {}
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) == 3:
            size = int(fields[2]) if fields[2].isdigit() else -1
            stats[fields[0]] = (fields[0], fields[1], size)
    indexed = {}
    for line in owners.stdout.splitlines():
        package, sep, filename = line.partition(": ")
        if sep and package in stats:
            indexed[filename] = stats[package]
    return indexed


def size_label(size):
    return f"{size:,} KiB" if size >= 0 else tr("未提供", "Not provided")


def load_sizes(job):
    global packages, pending
    if job is not pending:
        return False
    pending = None
    try:
        packages = job.result()
    except (OSError, subprocess.SubprocessError) as exc:
        detail.set_text(str(exc))
        return False
    # Updating a sorted column can move a row during iteration.
    items = [(row.iter, packages[row[1]]) for row in rows if row[1] in packages]
    for item, (package, _, size) in items:
        terms = rows[item][2].splitlines()
        if package.casefold() not in terms:
            terms.append(package.casefold())
        rows.set(item, 2, "\n".join(terms), 4, size, 5, size_label(size))
    selected(table.get_selection())
    select_requested_result()
    return False


def selected(selection):
    model, item = selection.get_selected()
    if item is None:
        message = ""
        if search.get_text().strip() and model.get_iter_first() is None:
            if pending or archive_job:
                message = tr("正在读取软件包信息…", "Reading package information…")
            else:
                message = tr("没有匹配的已安装程序。", "No matching installed programs.")
        detail.set_text(message)
        return
    name, filename = model[item][0], model[item][1]
    info = packages.get(filename)
    if info:
        package, version, size = info
        detail.set_text("\n".join((name, tr("软件包", "Package") + " · " + package,
                                   tr("已安装版本", "Installed version") + " · " + version,
                                   tr("软件包大小", "Package size") + " · " + size_label(size))))
    else:
        detail.set_text(name)


def select_requested_result():
    global requested_result
    if requested_result is None or archive_job is not None:
        return
    if requested_result != search.get_text() or window.get_focus() != search:
        requested_result = None
        return
    first = filtered.get_iter_first()
    if first is None and pending is not None:
        return
    requested_result = None
    if first is not None:
        table.set_cursor(filtered.get_path(first))
        table.grab_focus()


def focus_first_result(entry):
    global requested_result
    update_search(entry, refresh=True)
    requested_result = entry.get_text()
    select_requested_result()


search.connect("activate", focus_first_result)
table.get_selection().connect("changed", selected)
refresh = task_button(tr("刷新列表", "Refresh list"))
refresh.connect("clicked", reload_apps)
refresh.add_accelerator("clicked", shortcuts, Gdk.KEY_F5, 0, Gtk.AccelFlags.VISIBLE)
refresh.set_tooltip_text(refresh.get_label() + " (F5)")
side.add(refresh)
monitor = Gio.AppInfoMonitor.get()
monitor.connect("changed", reload_apps)
reload_apps()
window.show_all()
Gtk.main()
worker.shutdown(wait=False, cancel_futures=True)
