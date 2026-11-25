#!/usr/bin/python3
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from subprocess import Popen, run

import cups
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango
from printer_test_page import submit_test_page
from task_pane import add_task_pane, cycle_property_pages, task_button


def tr(zh, en):
    return zh if GLib.get_language_names()[0].startswith("zh") else en


window = Gtk.Window(title=tr("打印机和传真", "Printers and Faxes"))
window.set_icon_name("printer")
window.set_default_size(620, 350)
window.connect("destroy", Gtk.main_quit)
layout = Gtk.Box(spacing=6)
content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
window.add(content)
menu_bar = Gtk.MenuBar()
content.pack_start(menu_bar, False, False, 0)
file_item = Gtk.MenuItem.new_with_mnemonic(tr("文件(_F)", "_File"))
file_menu = Gtk.Menu()
file_item.set_submenu(file_menu)
menu_bar.append(file_item)
content.pack_start(layout, True, True, 0)
tasks = add_task_pane(layout, tr("打印机任务", "Printer Tasks"))
right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
layout.pack_start(right, True, True, 0)
rows = Gtk.ListStore(str, str, str, str)
table = Gtk.TreeView(model=rows)
name_column = Gtk.TreeViewColumn(tr("名称", "Name"))
icon = Gtk.CellRendererPixbuf()
icon.set_property("icon-name", "printer")
icon.set_property("stock-size", Gtk.IconSize.LARGE_TOOLBAR)
name_column.pack_start(icon, False)
caption = Gtk.CellRendererText()
name_column.pack_start(caption, True)
name_column.add_attribute(caption, "text", 2)
table.append_column(name_column)
table.append_column(Gtk.TreeViewColumn(tr("状态", "Status"), Gtk.CellRendererText(), text=1))
table.append_column(Gtk.TreeViewColumn(tr("文档数", "Documents"), Gtk.CellRendererText(), text=3))
scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
scroll.add(table)
right.pack_start(scroll, True, True, 0)
message = Gtk.Label(xalign=0)
message.set_line_wrap(True)
right.add(message)


last_queue_status = ""


def refresh(*_, select_name=None, background=False):
    global last_queue_status
    model, selected = table.get_selection().get_selected()
    previous = model[selected][0] if selected is not None else None
    try:
        server = cups.Connection()
        printers = server.getPrinters()
        destination = server.getDests().get((None, None))
        default = destination.name if destination else server.getDefault()
    except RuntimeError as error:
        rows.clear()
        last_queue_status = tr("无法读取打印队列", "Could not read print queues") + " · " + str(error)
        message.set_text(last_queue_status)
        return
    updated = []
    states = {3: tr("就绪", "Ready"), 4: tr("正在打印", "Printing"), 5: tr("已停止", "Stopped")}
    for name, attrs in sorted(printers.items()):
        caption = name + tr("（默认）", " (default)") if name == default else name
        count = attrs.get("queued-job-count")
        if count is None:
            try:
                details = server.getPrinterAttributes(name, requested_attributes=["queued-job-count"])
                count = details.get("queued-job-count")
            except RuntimeError:
                pass
        updated.append([name, states.get(attrs.get("printer-state"), tr("未知", "Unknown")),
                        caption, str(count) if count is not None else "—"])
    if updated != [list(row) for row in rows]:
        rows.clear()
        for values in updated:
            rows.append(values)
    for row in rows:
        if row[0] == (select_name or previous):
            item = row.iter
            table.get_selection().select_iter(item)
            if select_name:
                table.scroll_to_cell(rows.get_path(item))
    status = "" if printers else tr("尚未安装打印机。", "No printers are installed.")
    if not background or status or message.get_text() == last_queue_status:
        message.set_text(status)
    last_queue_status = status


queue_windows = {}


def open_queue(*_):
    model, item = table.get_selection().get_selected()
    if item is None:
        return
    name = model[item][0]
    if name in queue_windows:
        queue_windows[name].present()
        return
    queue = Gtk.Window(title=name, transient_for=window, destroy_with_parent=True)
    queue.set_icon_name("printer")
    monitor = window.get_display().get_monitor_at_window(window.get_window())
    workarea = monitor.get_workarea()
    queue.set_default_size(min(720, workarea.width - 24), min(300, workarea.height - 64))
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    queue.add(box)
    bar = Gtk.MenuBar()
    box.pack_start(bar, False, False, 0)
    printer_menu_item = Gtk.MenuItem.new_with_mnemonic(tr("打印机(_P)", "_Printer"))
    bar.append(printer_menu_item)
    printer_actions = Gtk.Menu()
    printer_menu_item.set_submenu(printer_actions)
    pause_printing = Gtk.MenuItem()
    printer_actions.append(pause_printing)
    properties = Gtk.MenuItem(label=tr("属性", "Properties"))
    properties.connect("activate", lambda _: printer_properties(name, queue, status))
    printer_actions.append(properties)
    printer_actions.append(Gtk.SeparatorMenuItem())
    close_queue = Gtk.MenuItem.new_with_mnemonic(tr("关闭(_C)", "_Close"))
    close_queue.connect("activate", lambda _: queue.close())
    printer_actions.append(close_queue)
    stopped = False
    document = Gtk.MenuItem.new_with_mnemonic(tr("文档(_D)", "_Document"))
    bar.append(document)
    menu = Gtk.Menu()
    document.set_submenu(menu)
    jobs = Gtk.ListStore(int, str, str, str, int, str, str, str, int, GObject.TYPE_INT64, GObject.TYPE_INT64)
    view = Gtk.TreeView(model=jobs)
    for index, title in [(1, tr("文档名", "Document Name")), (2, tr("状态", "Status")),
                         (3, tr("所有者", "Owner")), (5, tr("页数", "Pages")),
                         (6, tr("大小", "Size")), (7, tr("提交时间", "Submitted"))]:
        cell = Gtk.CellRendererText()
        if index == 1:
            cell.set_property("ellipsize", Pango.EllipsizeMode.END)
            cell.set_property("width-chars", 16)
        column = Gtk.TreeViewColumn(title, cell, text=index)
        column.set_resizable(True)
        column.set_sort_column_id({2: 4, 5: 8, 6: 9, 7: 10}.get(index, index))
        column.set_expand(index == 1)
        view.append_column(column)
    def document_tooltip(tree, x, y, keyboard, tooltip):
        found, _, _, model, path, item = tree.get_tooltip_context(x, y, keyboard)
        if not found:
            return False
        tooltip.set_text(model[item][1])
        tree.set_tooltip_row(tooltip, path)
        return True

    view.set_has_tooltip(True)
    view.connect("query-tooltip", document_tooltip)
    area = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
    area.add(view)
    box.pack_start(area, True, True, 0)
    status = Gtk.Label(xalign=0, margin=4)
    box.pack_end(status, False, False, 0)
    states = {3: tr("等待", "Pending"), 4: tr("已暂停", "Paused"),
              5: tr("正在打印", "Printing"), 6: tr("已停止", "Stopped")}

    def reload_jobs():
        nonlocal stopped
        _, selected = view.get_selection().get_selected()
        previous = jobs[selected][0] if selected is not None else None
        try:
            attrs = ["job-id", "job-printer-uri", "job-state", "job-name", "job-originating-user-name",
                     "job-impressions", "job-k-octets", "time-at-creation"]
            server = cups.Connection()
            state = server.getPrinterAttributes(name, requested_attributes=["printer-state"]).get("printer-state")
            stopped = state == 5
            pause_printing.set_sensitive(state in (3, 4, 5))
            pause_printing.set_label(tr("恢复打印", "Resume Printing") if stopped else tr("暂停打印", "Pause Printing"))
            listing = server.getJobs(requested_attributes=attrs)
            # CUPS can omit private titles from the all-users listing even for
            # the caller's own jobs. Request only the missing owner metadata.
            if any("job-name" not in job or "job-originating-user-name" not in job
                   for job in listing.values()):
                try:
                    owned = server.getJobs(my_jobs=True, requested_attributes=[
                        "job-id", "job-name", "job-originating-user-name"])
                except (RuntimeError, cups.IPPError):
                    owned = {}
                for job_id in listing.keys() & owned.keys():
                    listing[job_id].update(owned[job_id])
            updated = []
            for job_id, job in sorted(listing.items()):
                destination = unquote(urlsplit(job.get("job-printer-uri", "")).path.split("/")[-1])
                if destination != name:
                    continue
                state = job.get("job-state", 0)
                pages = job.get("job-impressions", 0)
                size = job.get("job-k-octets")
                submitted = job.get("time-at-creation", 0)
                updated.append([job_id, job.get("job-name", str(job_id)), states.get(state, str(state)),
                                job.get("job-originating-user-name", "—"), state, str(pages) if pages > 0 else "—",
                                f"{size} KiB" if size is not None else "—",
                                datetime.fromtimestamp(submitted).strftime("%x %H:%M") if submitted > 0 else "—",
                                pages, size if size is not None else -1, submitted])
            if updated != sorted((list(row) for row in jobs), key=lambda row: row[0]):
                jobs.clear()
                for values in updated:
                    row = jobs.append(values)
                    if values[0] == previous:
                        view.get_selection().select_iter(row)
            status.set_text(tr("队列中的文档数", "Documents in queue") + f" · {len(jobs)}")
        except (RuntimeError, cups.IPPError) as error:
            pause_printing.set_sensitive(False)
            jobs.clear()
            status.set_text(str(error))
        return True

    def change_printer_state(_item):
        try:
            server = cups.Connection()
            if stopped:
                server.enablePrinter(name)
            else:
                server.disablePrinter(name)
        except (RuntimeError, cups.IPPError) as error:
            status.set_text(str(error))
            return
        reload_jobs()
        refresh(background=True)

    pause_printing.connect("activate", change_printer_state)

    def change_job(_, operation, target=None):
        _, selected = view.get_selection().get_selected()
        if target is None:
            if selected is None:
                return
            target = jobs[selected][0], jobs[selected][1]
        job_id, title = target
        if operation == "cancel":
            confirm = Gtk.MessageDialog(transient_for=queue, modal=True, message_type=Gtk.MessageType.QUESTION,
                                        buttons=Gtk.ButtonsType.YES_NO,
                                        text=tr("取消打印此文档？", "Cancel printing this document?"))
            confirm.format_secondary_text(title)
            answer = confirm.run()
            confirm.destroy()
            if answer != Gtk.ResponseType.YES:
                return
        try:
            server = cups.Connection()
            if operation == "cancel":
                server.cancelJob(job_id)
            else:
                server.setJobHoldUntil(job_id, operation)
            reload_jobs()
        except (RuntimeError, cups.IPPError) as error:
            notice = Gtk.MessageDialog(transient_for=queue, modal=True, message_type=Gtk.MessageType.ERROR,
                                       buttons=Gtk.ButtonsType.CLOSE, text=str(error))
            notice.run()
            notice.destroy()

    actions = []
    for label, operation in [(tr("暂停", "Pause"), "indefinite"), (tr("继续", "Resume"), "no-hold"),
                             (tr("取消打印", "Cancel printing"), "cancel")]:
        action = Gtk.MenuItem(label=label)
        action.connect("activate", change_job, operation)
        menu.append(action)
        actions.append(action)

    def update_actions(*_):
        _, selected = view.get_selection().get_selected()
        state = jobs[selected][4] if selected is not None else None
        for action, enabled in zip(actions, (state in (3, 5), state == 4, state is not None)):
            action.set_sensitive(enabled)

    def job_menu(tree, event=None):
        if event is not None:
            if event.button != 3 or event.window != tree.get_bin_window():
                return False
            hit = tree.get_path_at_pos(int(event.x), int(event.y))
            if not hit:
                return False
            tree.grab_focus()
            tree.set_cursor(hit[0])
        _, selected = tree.get_selection().get_selected()
        if selected is None:
            return False
        target = jobs[selected][0], jobs[selected][1]
        popup = Gtk.Menu()
        for action, operation in zip(actions, ("indefinite", "no-hold", "cancel")):
            entry = Gtk.MenuItem(label=action.get_label())
            entry.set_sensitive(action.get_sensitive())
            entry.connect("activate", change_job, operation, target)
            popup.append(entry)
        popup.attach_to_widget(tree, None)
        popup.connect("selection-done", lambda widget: widget.destroy())
        popup.show_all()
        if event is None:
            rect = tree.get_cell_area(jobs.get_path(selected), tree.get_column(0))
            popup.popup_at_rect(tree.get_bin_window(), rect, Gdk.Gravity.SOUTH_WEST,
                                Gdk.Gravity.NORTH_WEST, Gtk.get_current_event())
            popup.select_first(True)
        else:
            popup.popup_at_pointer(event)
        return True

    def job_key(tree, event):
        if event.keyval not in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete) or event.state & Gtk.accelerator_get_default_mod_mask():
            return False
        change_job(tree, "cancel")
        return True

    view_item = Gtk.MenuItem.new_with_mnemonic(tr("查看(_V)", "_View"))
    view_menu = Gtk.Menu()
    view_item.set_submenu(view_menu)
    bar.append(view_item)
    refresh_jobs = Gtk.MenuItem.new_with_mnemonic(tr("刷新(_R)", "_Refresh"))
    refresh_jobs.connect("activate", lambda _: reload_jobs())
    view_menu.append(refresh_jobs)
    accelerators = Gtk.AccelGroup()
    queue.add_accel_group(accelerators)
    refresh_jobs.add_accelerator("activate", accelerators, Gdk.KEY_F5, 0, Gtk.AccelFlags.VISIBLE)

    view.connect("key-press-event", job_key)
    view.connect("button-press-event", job_menu)
    view.connect("popup-menu", job_menu)
    view.get_selection().connect("changed", update_actions)
    reload_jobs()
    update_actions()
    timer = GLib.timeout_add_seconds(3, reload_jobs)
    def queue_closed(*_):
        GLib.source_remove(timer)
        del queue_windows[name]

    queue_windows[name] = queue
    queue.connect("destroy", queue_closed)
    queue.show_all()


queue_button = task_button(tr("查看正在打印的文档", "See what's printing"))
queue_button.set_sensitive(False)
queue_button.connect("clicked", open_queue)
tasks.pack_start(queue_button, False, False, 0)


def print_test_page(_button):
    model, item = table.get_selection().get_selected()
    if item is not None:
        message.set_text(submit_test_page(model[item][0]))


test_button = task_button(tr("打印测试页", "Print test page"))
test_button.set_sensitive(False)
test_button.connect("clicked", print_test_page)
tasks.pack_start(test_button, False, False, 0)


def set_default(_button):
    model, item = table.get_selection().get_selected()
    if item is None:
        return
    try:
        result = run(["lpoptions", "-d", model[item][0]], capture_output=True, text=True)
    except OSError as error:
        message.set_text(str(error))
        return
    if result.returncode:
        message.set_text(tr("设置默认打印机失败", "Could not set default printer") + " · " + result.stderr.strip())
        return
    refresh()


default_button = task_button(tr("设为默认打印机", "Set as default printer"))
default_button.set_sensitive(False)
default_button.connect("clicked", set_default)
tasks.pack_start(default_button, False, False, 0)


def show_properties(*_):
    model, item = table.get_selection().get_selected()
    if item is None:
        return
    printer_properties(model[item][0], window, message)


def printer_properties(name, parent, feedback_label):
    fields = [(tr("型号", "Model"), "printer-make-and-model"),
              (tr("位置", "Location"), "printer-location"),
              (tr("说明", "Description"), "printer-info"),
              (tr("队列中的文档", "Queued documents"), "queued-job-count")]
    try:
        attrs = cups.Connection().getPrinterAttributes(name, requested_attributes=[key for _, key in fields] + ["device-uri", "printer-is-shared"])
    except (RuntimeError, OSError) as error:
        feedback_label.set_text(tr("无法读取打印机属性", "Could not read printer properties") + " · " + str(error))
        return
    dialog = Gtk.Dialog(title=tr("{} 属性", "{} Properties").format(name), transient_for=parent, modal=True)
    dialog.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
    dialog.set_default_response(Gtk.ResponseType.CLOSE)
    tabs = Gtk.Notebook()
    dialog.connect("key-press-event", cycle_property_pages, tabs)
    dialog.get_content_area().add(tabs)

    def page(title, details):
        grid = Gtk.Grid(column_spacing=14, row_spacing=8, border_width=12)
        tabs.append_page(grid, Gtk.Label(label=title))
        for i, (label, value) in enumerate(details):
            grid.attach(Gtk.Label(label=label, xalign=0), 0, i, 1, 1)
            field = Gtk.Label(label=str(value) if value is not None and value != "" else "—",
                              xalign=0, selectable=True, wrap=True)
            field.set_max_width_chars(48)
            grid.attach(field, 1, i, 1, 1)

        return grid

    details = [(tr("名称", "Name"), name)] + [(label, attrs.get(key)) for label, key in fields]
    general = page(tr("常规", "General"), details)
    test_page = Gtk.Button(label=tr("打印测试页", "Print test page"))
    feedback = Gtk.Label(xalign=0, wrap=True)
    test_page.connect("clicked", lambda _: feedback.set_text(submit_test_page(name)))
    general.attach(test_page, 0, len(details), 1, 1)
    general.attach(feedback, 1, len(details), 1, 1)
    edits = {}
    save = Gtk.Button(label=tr("应用", "Apply"))
    save.set_sensitive(False)

    def update_save(*_):
        save.set_sensitive(any(entry.get_text() != (attrs.get(key) or "") for key, entry in edits.items()))

    for row, (label, key) in enumerate(fields, start=1):
        if key in ("printer-location", "printer-info"):
            general.get_child_at(1, row).destroy()
            entry = Gtk.Entry(text=attrs.get(key) or "")
            entry.get_accessible().set_name(label)
            general.attach(entry, 1, row, 1, 1)
            edits[key] = entry
            entry.connect("changed", update_save)

    def save_details(_):
        args = ["lpadmin", "-p", name]
        for key, flag in (("printer-location", "-L"), ("printer-info", "-D")):
            value = edits[key].get_text()
            if value != (attrs.get(key) or ""):
                args.extend((flag, value))
        try:
            result = run(args, capture_output=True, text=True)
            if result.returncode:
                feedback.set_text(result.stderr.strip() or tr("保存失败。", "Could not save changes."))
                return
            for key, entry in edits.items():
                attrs[key] = entry.get_text()
            update_save()
            feedback.set_text(tr("打印机信息已保存。", "Printer information saved."))
        except OSError as exc:
            feedback.set_text(str(exc))

    save.connect("clicked", save_details)
    general.attach(save, 0, len(details) + 1, 1, 1)
    shared = attrs.get("printer-is-shared")
    sharing = page(tr("共享", "Sharing"), [(tr("共享名", "Share name"), name)])
    try:
        setting = cups.Connection().adminGetServerSettings().get(cups.CUPS_SERVER_SHARE_PRINTERS)
    except (RuntimeError, OSError):
        setting = None
    server_state = {"0": tr("已关闭", "Off"), "1": tr("已开启", "On")}.get(setting, tr("未知", "Unknown"))
    sharing.attach(Gtk.Label(label=tr("打印服务器共享", "Print server sharing"), xalign=0), 0, 1, 1, 1)
    sharing.attach(Gtk.Label(label=server_state, xalign=0), 1, 1, 1, 1)
    toggle = Gtk.CheckButton(label=tr("共享这台打印机", "Share this printer"))
    toggle.set_active(bool(shared))
    toggle.set_sensitive(shared is not None)
    sharing.attach(toggle, 0, 2, 2, 1)
    hint = Gtk.Label(label=tr("局域网访问还需要打印服务器开启共享。", "Network access also requires sharing on the print server."),
                     xalign=0, wrap=True)
    sharing.attach(hint, 0, 3, 2, 1)
    apply = Gtk.Button(label=tr("应用", "Apply"))
    apply.set_sensitive(False)
    sharing.attach(apply, 0, 4, 1, 1)

    def save_sharing(_):
        nonlocal shared
        try:
            server = cups.Connection()
            server.setPrinterShared(name, toggle.get_active())
            shared = server.getPrinterAttributes(name, requested_attributes=["printer-is-shared"])["printer-is-shared"]
            toggle.set_active(shared)
            apply.set_sensitive(False)
            hint.set_text(tr("打印队列共享已开启。", "Queue sharing is enabled.") if shared else
                          tr("打印队列共享已关闭。", "Queue sharing is disabled."))
        except (RuntimeError, OSError, KeyError) as exc:
            hint.set_text(str(exc))

    toggle.connect("toggled", lambda button: apply.set_sensitive(button.get_active() != shared))
    apply.connect("clicked", save_sharing)
    try:
        device = urlsplit(attrs.get("device-uri") or "")
        protocol, host, port = device.scheme.upper(), device.hostname, device.port
        if host and port is None:
            port = {"ipp": 631, "ipps": 631, "socket": 9100, "lpd": 515,
                    "http": 80, "https": 443}.get(device.scheme)
    except ValueError:
        protocol, host, port = None, None, None
    page(tr("端口", "Ports"), [(tr("连接方式", "Connection type"), protocol),
                             (tr("设备主机", "Device host"), host),
                             (tr("端口号", "Port number"), port)])
    dialog.show_all()
    dialog.run()
    dialog.destroy()


properties_button = task_button(tr("属性", "Properties"))
properties_button.set_sensitive(False)
properties_button.connect("clicked", show_properties)
tasks.pack_start(properties_button, False, False, 0)


def selection_changed(selection):
    for action_button in (queue_button, test_button, default_button, properties_button):
        action_button.set_sensitive(selection.count_selected_rows() > 0)


table.get_selection().connect("changed", selection_changed)
def activate_queue(view, path, _column):
    view.get_selection().select_path(path)
    open_queue()


table.connect("row-activated", activate_queue)

def printer_menu(view, event=None):
    if event is not None:
        if event.button != 3 or event.window != view.get_bin_window():
            return False
        hit = view.get_path_at_pos(int(event.x), int(event.y))
        view.grab_focus()
        if hit:
            view.set_cursor(hit[0])
        else:
            view.get_selection().unselect_all()
    model, item = view.get_selection().get_selected()
    menu = Gtk.Menu()
    buttons = (add_button, refresh_button) if item is None else (
        queue_button, default_button, test_button, properties_button)
    for button in buttons:
        entry = Gtk.MenuItem(label=button.get_label())
        entry.set_sensitive(button.get_sensitive())
        entry.connect("activate", lambda _entry, target=button: target.clicked())
        menu.append(entry)
    menu.attach_to_widget(view, None)
    menu.connect("selection-done", lambda widget: widget.destroy())
    menu.show_all()
    if event is None:
        rect = (view.get_cell_area(model.get_path(item), name_column) if item is not None
                else Gdk.Rectangle())
        menu.popup_at_rect(view.get_bin_window(), rect, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST,
                           Gtk.get_current_event())
        menu.select_first(True)
    else:
        menu.popup_at_pointer(event)
    return True


table.connect("button-press-event", printer_menu)
table.connect("popup-menu", printer_menu)

def add_printer(button):
    def finished(process, result):
        button.set_sensitive(True)
        try:
            _, output, _ = process.communicate_utf8_finish(result)
            if not process.get_successful():
                message.set_text(tr("添加打印机向导已异常退出。", "The Add Printer Wizard exited unexpectedly."))
                return
            prefix = "agentlinux-printer-added="
            added = next((line[len(prefix):] for line in reversed(output.splitlines())
                          if line.startswith(prefix)), None)
            refresh(select_name=added)
            if added:
                table.grab_focus()
        except GLib.Error as error:
            message.set_text(error.message)

    try:
        process = Gio.Subprocess.new([str(Path(__file__).with_name("add-printer.py")), "--report-queue"],
                                     Gio.SubprocessFlags.STDOUT_PIPE)
    except GLib.Error as error:
        message.set_text(error.message)
        return
    button.set_sensitive(False)
    process.communicate_utf8_async(None, None, finished)


def add_task(label, action):
    button = task_button(label)
    button.connect("clicked", action)
    tasks.pack_start(button, False, False, 0)
    return button


add_button = add_task(tr("添加打印机", "Add a printer"), add_printer)
refresh_button = add_task(tr("刷新", "Refresh"), refresh)
add_task(tr("管理打印队列", "Manage print queues"), lambda *_: Popen(["/usr/bin/system-config-printer"]))


# Reuse the task pane actions so both entry points follow queue selection.
for label, target in (
    (tr("添加打印机(_A)…", "_Add Printer…"), add_button),
    (tr("打开(_O)", "_Open"), queue_button),
    (tr("设为默认打印机(_D)", "Set as _Default Printer"), default_button),
    (tr("属性(_R)", "P_roperties"), properties_button),
):
    item = Gtk.MenuItem.new_with_mnemonic(label)
    target.bind_property("sensitive", item, "sensitive", GObject.BindingFlags.SYNC_CREATE)
    item.connect("activate", lambda _item, button=target: button.clicked())
    file_menu.append(item)
file_menu.append(Gtk.SeparatorMenuItem())
close_item = Gtk.MenuItem.new_with_mnemonic(tr("关闭(_C)", "_Close"))
close_item.connect("activate", lambda *_: window.close())
file_menu.append(close_item)


def window_key(_window, event):
    modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
    if event.keyval == Gdk.KEY_F5 and not modifiers:
        refresh()
        return True
    if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and modifiers == Gdk.ModifierType.MOD1_MASK:
        if properties_button.get_sensitive():
            show_properties()
            return True
    return False


window.connect("key-press-event", window_key)


def poll_queues():
    if table.get_mapped():
        refresh(background=True)
    return True


window.connect("focus-in-event", lambda *_: refresh())
GLib.timeout_add_seconds(5, poll_queues)
refresh()
window.show_all()
Gtk.main()
