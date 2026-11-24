#!/usr/bin/python3
import configparser
import ipaddress
import pwd
import grp
import stat
import os
import re
import sqlite3
import socket
import threading
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote, unquote_to_bytes, urlsplit

from network_details import lan_addresses, smb_uri, windows_location
from task_pane import add_task_pane, task_button

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango


def tr(zh, en):
    return zh if GLib.get_language_names()[0].startswith("zh") else en


def samba(*args):
    proc = subprocess.run(["net", "usershare", *args], text=True, capture_output=True)
    if proc.returncode:
        raise ValueError(proc.stderr.strip() or tr("共享设置失败", "Share operation failed"))
    return proc.stdout


def shares():
    # Every Samba section represents a share, including one named DEFAULT.
    info = configparser.ConfigParser(interpolation=None, default_section="/")
    info.read_string(samba("info"))
    return info


def permission_labels(share):
    acl = share.get("usershare_acl", "").strip().rstrip(",").casefold()
    access = {"everyone:r": tr("只读", "Read only"),
              "everyone:f": tr("读写", "Read and write")}.get(acl, tr("自定义", "Custom"))
    login = {"y": tr("允许访客", "Guests allowed"),
             "n": tr("需要登录", "Sign-in required")}.get(share.get("guest_ok", "").lower(), tr("未知", "Unknown"))
    return access, login


def refresh(*_, select_name=None):
    try:
        entries = shares()
        current = selected()
        current_name = select_name or (current[0] if current is not None else None)
        rows.clear()
        for name in entries.sections():
            share = entries[name]
            access, login = permission_labels(share)
            item = rows.append([name, share["path"], network_path(name), access, login, share.get("comment", "")])
            if current_name and name.casefold() == current_name.casefold():
                table.get_selection().select_iter(item)
                table.scroll_to_cell(rows.get_path(item))
        status.set_text("" if len(rows) else tr("尚未共享文件夹。", "No folders are shared."))
    except (OSError, ValueError, configparser.Error) as exc:
        status.set_text(str(exc))


def network_path(name):
    return rf"\\{socket.gethostname()}\{name}"


def mac_address(name):
    host = socket.gethostname().split(".")[0]
    return f"smb://{host}.local/{quote(name, safe='')}"


def share_name_error(name, existing, accounts):
    if not name or name.startswith("-") or re.search(r'[\x00-\x1f%+=;,/\\:*?"<>|\[\]]', name):
        return tr("请移除共享名中不支持的符号。", "Remove unsupported characters from the share name.")
    if name.casefold() in existing:
        return tr("共享名称已存在。", "This share name already exists.")
    if name.casefold() in accounts:
        return tr("此名称已用于系统账号。请为共享文件夹另取名称。",
                  "This name belongs to a system account. Choose another share name.")
    return ""


def add_share(name, path, writable, comment=""):
    problem = share_name_error(name, {n.casefold() for n in shares().sections()},
                               {user.pw_name.casefold() for user in pwd.getpwall()})
    if problem:
        raise ValueError(problem)
    if not path or not Path(path).is_dir():
        raise ValueError(tr("请选择文件夹。", "Choose a folder."))
    samba("add", name, os.path.abspath(path), comment, "Everyone:F" if writable else "Everyone:R", "guest_ok=n")


def add_detail(grid, row, label, value, copy_caption=None):
    grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1)
    field = Gtk.Label(label=value, xalign=0, selectable=True, wrap=True)
    field.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    field.set_max_width_chars(44)
    grid.attach(field, 1, row, 1, 1)
    if copy_caption:
        button = Gtk.Button(label=tr("复制", "Copy"))
        button.get_accessible().set_name(copy_caption)
        button.set_tooltip_text(copy_caption)
        button.connect("clicked", lambda _: copy_text(value))
        grid.attach(button, 2, row, 1, 1)


def add_addresses(grid, row, name):
    add_detail(grid, row, tr("Windows 路径", "Windows path"), network_path(name),
               tr("复制 Windows 路径", "Copy Windows path"))
    add_detail(grid, row + 1, tr("Mac 连接地址", "Mac connection address"), mac_address(name),
               tr("复制 Mac 连接地址", "Copy Mac connection address"))


def add_lan_addresses(grid, row, name):
    for interface, host in lan_addresses():
        authority = f"[{host}]" if ":" in host else host
        uri = f"smb://{authority}/{quote(name, safe='')}"
        unc = windows_location(uri)
        if unc:
            add_detail(grid, row, f"Windows · {interface}", unc,
                       tr("复制 Windows IP 路径", "Copy Windows IP path"))
            row += 1
        add_detail(grid, row, f"Mac · {interface}", uri,
                   tr("复制 Mac IP 地址", "Copy Mac IP address"))
        row += 1


def scroll_share_details(dialog, widget):
    display = dialog.get_display()
    parent_window = window.get_window()
    monitor = display.get_monitor_at_window(parent_window) if parent_window else display.get_monitor(0)
    area = monitor.get_workarea()
    scroll = Gtk.ScrolledWindow()
    scroll.set_max_content_width(max(240, area.width - 80))
    scroll.set_max_content_height(max(140, area.height - 140))
    scroll.set_propagate_natural_width(True)
    scroll.set_propagate_natural_height(True)
    scroll.add(widget)
    dialog.get_content_area().pack_start(scroll, True, True, 0)


def show_created(row):
    dialog = Gtk.Dialog(title=tr("文件夹已共享", "Folder shared"), transient_for=window, modal=True)
    dialog.add_button(tr("设置共享密码…", "Set sharing password…"), Gtk.ResponseType.APPLY)
    dialog.add_button(tr("完成", "Finish"), Gtk.ResponseType.CLOSE)
    dialog.set_default_response(Gtk.ResponseType.CLOSE)
    grid = Gtk.Grid(column_spacing=12, row_spacing=8, border_width=12)
    add_addresses(grid, 0, row[0])
    add_detail(grid, 2, tr("共享权限", "Share permissions"), row[3])
    add_detail(grid, 3, tr("访问方式", "Access"), row[4])
    add_detail(grid, 4, tr("本机共享账号", "Local sharing account"), pwd.getpwuid(os.getuid()).pw_name)
    add_lan_addresses(grid, 5, row[0])
    scroll_share_details(dialog, grid)
    dialog.show_all()
    response = dialog.run()
    dialog.destroy()
    if response == Gtk.ResponseType.APPLY:
        set_share_password(buttons[set_share_password])


def create(_=None, initial=None):
    dlg = Gtk.Dialog(title=tr("共享文件夹", "Share a Folder"), transient_for=window, modal=True)
    dlg.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    dlg.add_button(tr("共享", "Share"), Gtk.ResponseType.OK)
    box = dlg.get_content_area()
    box.set_border_width(12)
    box.set_spacing(8)
    folder = Gtk.FileChooserButton(title=tr("选择文件夹", "Select a folder"), action=Gtk.FileChooserAction.SELECT_FOLDER)
    name = Gtk.Entry(placeholder_text=tr("共享名", "Share name"))
    folder.connect("file-set", lambda button: name.set_text(Path(button.get_filename()).name))
    if initial and Path(initial).is_dir():
        folder.set_filename(initial)
        name.set_text(Path(initial).name)
    write = Gtk.CheckButton(label=tr("允许已登录的网络用户更改文件", "Allow signed-in network users to change files"))
    comment = Gtk.Entry(placeholder_text=tr("共享备注（可选）", "Share comment (optional)"))
    error = Gtk.Label(xalign=0, wrap=True)
    preview = Gtk.Label(xalign=0, selectable=True, wrap=True)
    existing = {row[0].casefold() for row in rows}
    accounts = {user.pw_name.casefold() for user in pwd.getpwall()}

    def update_preview(*_):
        share_name = name.get_text().strip()
        problem = share_name_error(share_name, existing, accounts) if share_name else ""
        error.set_text(problem)
        preview.set_text(network_path(share_name) if share_name and not problem else "")
        dlg.set_response_sensitive(Gtk.ResponseType.OK, bool(folder.get_filename() and share_name and not problem))

    name.connect("changed", update_preview)
    folder.connect("selection-changed", update_preview)
    update_preview()
    for widget in (Gtk.Label(label=tr("本机文件夹", "Local folder"), xalign=0), folder,
                   Gtk.Label(label=tr("共享名", "Share name"), xalign=0), name,
                   Gtk.Label(label=tr("Windows 网络路径", "Windows network path"), xalign=0),
                   preview, comment, write, error):
        box.add(widget)
    dlg.show_all()
    created = None
    while dlg.run() == Gtk.ResponseType.OK:
        try:
            share_name = name.get_text().strip()
            add_share(share_name, folder.get_filename(), write.get_active(), comment.get_text())
            created = share_name
            break
        except (OSError, ValueError, configparser.Error) as exc:
            error.set_text(str(exc))
    dlg.destroy()
    if created:
        notebook.set_current_page(0)
        refresh(select_name=created)
        row = selected()
        if row is not None and row[0].casefold() == created.casefold():
            status.set_text(tr("已共享", "Shared") + " · " + row[2])
            show_created(row)


def open_folder_sharing(path):
    folder = os.path.realpath(path) if path else None
    matches = [row for row in rows if os.path.realpath(row[1]) == folder]
    if not matches:
        create(initial=path)
        return
    row = matches[0]
    table.get_selection().select_path(row.path)
    table.scroll_to_cell(row.path)
    if len(matches) == 1:
        properties()
    else:
        status.set_text(tr("此文件夹使用多个共享名，请选择要查看的共享。", "This folder has multiple share names. Select the share to inspect."))


def selected():
    model, it = table.get_selection().get_selected()
    return model[it] if it is not None else None


def local_permissions(folder):
    grid = Gtk.Grid(column_spacing=12, row_spacing=8, border_width=10)
    try:
        info = os.stat(folder)
    except OSError as error:
        grid.add(Gtk.Label(label=str(error), wrap=True, xalign=0))
        return grid
    try:
        owner = pwd.getpwuid(info.st_uid).pw_name
    except KeyError:
        owner = str(info.st_uid)
    try:
        group = grp.getgrgid(info.st_gid).gr_name
    except KeyError:
        group = str(info.st_gid)
    add_detail(grid, 0, tr("所有者", "Owner"), owner)
    add_detail(grid, 1, tr("所属组", "Group"), group)
    add_detail(grid, 2, tr("Unix 权限", "Unix mode"), stat.filemode(info.st_mode))
    account = pwd.getpwuid(os.getuid()).pw_name
    if os.access(folder, os.W_OK | os.X_OK):
        access = tr("可以创建文件", "Can create files")
    else:
        access = tr("无法创建文件", "Cannot create files")
    add_detail(grid, 3, account, access)
    note = Gtk.Label(label=tr("网络用户写入文件需要共享权限和其本机帐户权限同时允许。",
                              "Network users need both share permission and local account permission to write files."),
                     xalign=0, wrap=True)
    note.set_max_width_chars(45)
    grid.attach(note, 0, 4, 2, 1)
    return grid


def properties(_=None):
    row = selected()
    if row is None:
        return
    name = row[0]
    try:
        original = dict(shares()[name])
    except (KeyError, ValueError, OSError, configparser.Error):
        refresh()
        return
    acl = original.get("usershare_acl", "").rstrip(",").casefold()
    editable = acl in ("everyone:r", "everyone:f") and original.get("guest_ok") == "n"
    dlg = Gtk.Dialog(title=name + tr(" 属性", " Properties"), transient_for=window, modal=True)
    dlg.add_button(tr("停止共享…", "Stop sharing…"), Gtk.ResponseType.REJECT)
    dlg.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
    if editable:
        dlg.add_button(tr("确定", "OK"), Gtk.ResponseType.OK)
    tabs = Gtk.Notebook(border_width=8)
    scroll_share_details(dlg, tabs)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    tabs.append_page(box, Gtk.Label(label=tr("共享", "Sharing")))
    tabs.append_page(local_permissions(original["path"]), Gtk.Label(label=tr("本机权限", "Local Permissions")))
    box.set_border_width(12)
    box.set_spacing(8)
    access, login = permission_labels(original)
    details = Gtk.Grid(column_spacing=12, row_spacing=6)
    box.add(details)
    add_detail(details, 0, tr("本机文件夹", "Local folder"), original["path"])
    add_addresses(details, 1, name)
    add_detail(details, 3, tr("共享权限", "Share permissions"), access)
    add_detail(details, 4, tr("访问方式", "Access"), login)
    write = Gtk.CheckButton(label=tr("允许已登录的网络用户更改文件", "Allow signed-in network users to change files"))
    original_comment = original.get("comment", "")
    comment = Gtk.Entry(text=original_comment, editable=editable)
    details.attach(Gtk.Label(label=tr("备注", "Comment"), xalign=0), 0, 5, 1, 1)
    details.attach(comment, 1, 5, 1, 1)
    add_lan_addresses(details, 6, name)
    if editable:
        write.set_active(acl == "everyone:f")
        access_label = details.get_child_at(1, 3)
        write.connect("toggled", lambda check: access_label.set_text(
            tr("读写", "Read and write") if check.get_active() else tr("只读", "Read only")))
        box.add(write)
    dlg.show_all()
    response = dlg.run()
    writable = write.get_active()
    updated_comment = comment.get_text()
    dlg.destroy()
    if response == Gtk.ResponseType.REJECT:
        confirm_stop(name, original["path"])
        return
    if response != Gtk.ResponseType.OK or not editable or (writable == (acl == "everyone:f") and updated_comment == original_comment):
        return
    try:
        if dict(shares()[name]) != original:
            raise ValueError(tr("共享已更改，请刷新后重试。", "The share has changed. Refresh and try again."))
        samba("add", name, original["path"], updated_comment,
              "Everyone:F" if writable else "Everyone:R", "guest_ok=n")
        refresh(select_name=name)
        saved = selected()
        if saved is not None and saved[0] == name and saved[1] == original["path"]:
            status.set_text(tr("当前共享权限：{}", "Current share permissions: {}").format(saved[3]))
    except (ValueError, OSError, KeyError, configparser.Error) as exc:
        status.set_text(str(exc))


def set_share_password(button):
    account = pwd.getpwuid(os.getuid()).pw_name
    dlg = Gtk.Dialog(title=tr("设置共享密码", "Set sharing password"), transient_for=window, modal=True)
    dlg.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    save = dlg.add_button(tr("保存", "Save"), Gtk.ResponseType.OK)
    dlg.set_default_response(Gtk.ResponseType.OK)
    box = dlg.get_content_area()
    box.set_border_width(12)
    box.set_spacing(6)
    box.add(Gtk.Label(label=tr("网络共享账号", "Network sharing account") + " · " + account, xalign=0))
    entries = []
    for caption in (tr("新的共享密码", "New sharing password"), tr("确认共享密码", "Confirm sharing password")):
        label = Gtk.Label(label=caption, xalign=0)
        entry = Gtk.Entry(visibility=False, activates_default=True)
        entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        label.set_mnemonic_widget(entry)
        box.add(label)
        box.add(entry)
        entries.append(entry)
    first, confirm = entries

    def validate(*_):
        password = first.get_text()
        save.set_sensitive(bool(password) and password == confirm.get_text()
                           and not any(char in password for char in "\r\n"))

    for entry in entries:
        entry.connect("changed", validate)
    validate()
    dlg.show_all()
    first.grab_focus()
    response = dlg.run()
    password = first.get_text() if response == Gtk.ResponseType.OK and save.get_sensitive() else ""
    for entry in entries:
        entry.set_text("")
    dlg.destroy()
    if not password:
        return

    def finished(process, result):
        try:
            process.communicate_finish(result)
            code = process.get_exit_status() if process.get_if_exited() else None
        except GLib.Error:
            code = None
        button.set_sensitive(True)
        if code == 0:
            message = tr("共享密码已保存。", "Sharing password saved.")
        elif code == 126:
            message = tr("已取消授权，共享密码未更改。", "Authorization was cancelled. The sharing password was not changed.")
        elif code == 127:
            message = tr("未获得管理员授权，请重新打开设置共享密码。", "Administrator authorization was unavailable. Open Set sharing password to retry.")
        else:
            message = tr("无法保存共享密码，请检查 Samba 账号设置后重试。", "Could not save the sharing password. Check the Samba account settings and try again.")
        status.set_text(message)

    try:
        process = Gio.Subprocess.new(["/usr/bin/pkexec", "--disable-internal-agent", "/usr/bin/smbpasswd", "-s", "-a", account],
                                     Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_SILENCE |
                                     Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error as exc:
        status.set_text(exc.message)
        return
    button.set_sensitive(False)
    status.set_text(tr("正在设置共享密码…", "Setting sharing password…"))
    process.communicate_async(GLib.Bytes.new((password + "\n" + password + "\n").encode()), None, finished)


def stop(_):
    row = selected()
    if row is None:
        return
    confirm_stop(row[0], row[1])


def confirm_stop(name, folder):
    dlg = Gtk.MessageDialog(transient_for=window, modal=True, message_type=Gtk.MessageType.QUESTION,
                            buttons=Gtk.ButtonsType.NONE,
                            text=tr("停止共享“{}”？", "Stop sharing “{}”?").format(name))
    dlg.format_secondary_text(tr("本机文件将保留在 {}。", "Local files will remain in {}.").format(folder))
    dlg.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
    dlg.add_button(tr("停止共享", "Stop sharing"), Gtk.ResponseType.YES)
    dlg.set_default_response(Gtk.ResponseType.CANCEL)
    response = dlg.run()
    dlg.destroy()
    if response == Gtk.ResponseType.YES:
        try:
            current = shares()
            if name not in current or current[name].get("path") != folder:
                refresh()
                status.set_text(tr("共享位置已更改，请重新选择。", "The share location has changed. Select it again."))
                return
            samba("delete", name)
            refresh()
            status.set_text(tr("已停止共享“{}”。", "Stopped sharing “{}”.").format(name))
        except (OSError, ValueError, configparser.Error) as exc:
            status.set_text(str(exc))


def share_uri(text):
    return smb_uri(text, tr)


def place_key_for_uri(uri):
    """Compare bookmark destinations without changing the address stored for launch."""
    try:
        parts = urlsplit(uri)
        path = parts.path.removesuffix("/")
        return (parts.scheme, parts.username, parts.hostname, parts.port if parts.port is not None else 445,
                tuple(unquote_to_bytes(segment) for segment in path.split("/")), parts.query, parts.fragment)
    except ValueError:
        return (uri,)


def place_caption(uri):
    try:
        parts = urlsplit(uri)
        host = parts.hostname
        if not host:
            return uri
        leaf = parts.path.rstrip("/").rsplit("/", 1)[-1]
        if leaf:
            return tr("{}（位于 {}）", "{} on {}").format(unquote(leaf), host)
        return host
    except ValueError:
        return uri


class ShareMountOperation(Gtk.MountOperation):
    def __init__(self, parent, parts):
        super().__init__(parent=parent)
        self.host = parts.hostname
        self.share = unquote(parts.path.lstrip("/").split("/", 1)[0])

    def do_ask_password(self, message, default_user, default_domain, flags):
        # GVfs can keep the previous desktop language until the next login.
        prompt = tr("请输入“{host}”上共享“{share}”的登录信息。",
                    "Enter the sign-in details for “{share}” on {host}.")
        message = tr("需要认证", "Authentication Required") + "\n" + prompt.format(host=self.host, share=self.share)
        Gtk.MountOperation.do_ask_password(self, message, default_user, default_domain, flags)


def browse_share(target, parent=None):
    parts = urlsplit(target)
    if parts.scheme == "smb" and parts.path.strip("/"):
        location = Gio.File.new_for_uri(target)
        operation = ShareMountOperation(parent, parts)
        loop = GLib.MainLoop()
        errors = []

        def mounted(source, result):
            try:
                source.mount_enclosing_volume_finish(result)
            except GLib.Error as exc:
                if not exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.ALREADY_MOUNTED):
                    errors.append(exc)
            finally:
                loop.quit()

        location.mount_enclosing_volume(Gio.MountMountFlags.NONE, operation, None, mounted)
        loop.run()
        if errors:
            error = errors[0]
            if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.FAILED_HANDLED) or error.matches(
                    Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                return
            raise OSError(error.message)
    env = os.environ.copy()
    assets = str(Path(__file__).resolve().parent)
    for key in ("GTK_MODULES", "LD_PRELOAD", "G_RESOURCE_OVERLAYS"):
        entries = [value for value in env.get(key, "").split(":") if value and assets not in value
                   and "/agentlinux-xp/" not in value]
        if entries:
            env[key] = ":".join(entries)
        else:
            env.pop(key, None)
    subprocess.Popen(["peony", "--show-folders", target], env=env)


def connect(_):
    try:
        target = share_uri(address.get_text())
        browse_share(target, window)
    except (OSError, ValueError) as exc:
        status.set_text(str(exc))


def location_column(title, icon, caption=None):
    column = Gtk.TreeViewColumn(title)
    renderer = Gtk.CellRendererPixbuf()
    path = Path("/usr/share/icons/luna/res/16x16") / (icon + ".png")
    if path.is_file():
        renderer.set_property("pixbuf", GdkPixbuf.Pixbuf.new_from_file(str(path)))
    else:
        renderer.set_property("icon-name", "folder-remote")
    column.pack_start(renderer, False)
    if caption is None:
        caption = Gtk.CellRendererText()
    column.pack_start(caption, True)
    column.add_attribute(caption, "text", 0)
    return column


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--connect":
        try:
            target = share_uri(sys.argv[2])
            browse_share(target)
            sys.exit(0)
        except (ValueError, OSError) as exc:
            notice = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR,
                                       buttons=Gtk.ButtonsType.CLOSE, text=str(exc))
            notice.run()
            notice.destroy()
            sys.exit(1)
    local_shares = sys.argv[1:] == ["--local-shares"]
    title = tr("共享文件夹", "Shared Folders") if local_shares else tr("网上邻居", "My Network Places")
    window = Gtk.Window(title=title)
    window.set_icon_name("folder-publicshare" if local_shares else "network-workgroup")
    display = window.get_display()
    monitor = display.get_primary_monitor() or display.get_monitor(0)
    area = monitor.get_workarea()
    window.set_default_size(min(730, area.width - 24), min(360, area.height - 64))
    window.connect("destroy", Gtk.main_quit)
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, border_width=10, spacing=8)
    window.add(root)
    bar = Gtk.Box(spacing=6)
    root.add(bar)
    bookmarks = Gtk.ListStore(str, str)
    address_list = Gtk.ComboBox.new_with_model_and_entry(bookmarks)
    address_list.set_entry_text_column(1)
    address_list.get_accessible().set_name(tr("已保存的共享地址", "Saved share addresses"))
    address = address_list.get_child()
    address.set_placeholder_text(r"\\server\share   ·   smb://server/share")
    address.get_accessible().set_name(tr("网络共享地址", "Network share address"))
    address.set_tooltip_text(tr("输入计算机名、IP 地址或共享路径，例如 NAS/公共文档。",
                                "Enter a computer name, IP address or share path, such as NAS/Documents."))
    bar.pack_start(address_list, True, True, 0)
    go = Gtk.Button(label=tr("连接", "Connect"))
    go.connect("clicked", connect)
    address.connect("activate", connect)
    bar.add(go)
    body = Gtk.Box(spacing=10)
    root.pack_start(body, True, True, 0)
    tasks = add_task_pane(body, tr("网络任务", "Network Tasks"))
    rows = Gtk.ListStore(str, str, str, str, str, str)
    table = Gtk.TreeView(model=rows)
    table.get_accessible().set_name(tr("本机共享", "Local shares"))
    for i, title in [(0, tr("共享名", "Share name")), (3, tr("共享权限", "Share permissions")),
                     (4, tr("访问方式", "Access")), (5, tr("备注", "Comment")), (1, tr("本机文件夹", "Local folder"))]:
        column = location_column(title, "folder_shared") if i == 0 else Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)
        if i == 5:
            column.get_cells()[0].set_property("ellipsize", Pango.EllipsizeMode.END)
            column.set_max_width(180)
        column.set_resizable(True)
        column.set_sort_column_id(i)
        table.append_column(column)
    def open_local_folder(path):
        try:
            browse_share(Path(path).as_uri())
        except (OSError, ValueError) as exc:
            status.set_text(str(exc))

    table.connect("row-activated", lambda view, path, column: open_local_folder(rows[path][1]))
    scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
    scroll.add(table)
    notebook = Gtk.Notebook()
    notebook.set_scrollable(True)
    body.pack_start(notebook, True, True, 0)
    notebook.append_page(scroll, Gtk.Label(label=tr("本机共享", "Local shares")))
    directory = Path(GLib.get_user_data_dir()) / "agentlinux-xp"
    directory.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(directory / "network-places.sqlite3")
    db.execute("CREATE TABLE IF NOT EXISTS places (uri TEXT PRIMARY KEY)")
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("CREATE TABLE IF NOT EXISTS place_names (uri TEXT PRIMARY KEY REFERENCES places(uri) ON DELETE CASCADE, name TEXT NOT NULL)")
    completion = Gtk.EntryCompletion()
    completion.set_model(bookmarks)
    completion.set_text_column(0)
    uri_cell = Gtk.CellRendererText()
    completion.pack_start(uri_cell, False)
    completion.add_attribute(uri_cell, "text", 1)

    def match_location(widget, key, item, _data):
        name, uri = widget.get_model()[item]
        return any(key.casefold() in value.casefold() for value in
                   (name, unquote(uri), windows_location(uri) or ""))

    def choose_location(_widget, model, item):
        address.set_text(model[item][1])
        address.set_position(-1)
        return True

    completion.set_match_func(match_location, None)
    completion.connect("match-selected", choose_location)
    address.set_completion(completion)
    places = Gtk.TreeView(model=bookmarks)
    places.get_accessible().set_name(tr("常用网络位置", "My network places"))
    place_name = Gtk.CellRendererText()
    name_column = location_column(tr("名称", "Name"), "folder_network", place_name)
    places.append_column(name_column)
    places.append_column(Gtk.TreeViewColumn(tr("网络地址", "Network address"), Gtk.CellRendererText(), text=1))
    saved = Gtk.ScrolledWindow()
    saved.add(places)
    saved_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    saved_page.pack_end(saved, True, True, 0)
    notebook.append_page(saved_page, Gtk.Label(label=tr("常用网络位置", "My network places")))

    discovered = Gtk.ListStore(str, str)
    discovered.set_sort_column_id(0, Gtk.SortType.ASCENDING)
    computers = Gtk.TreeView(model=discovered)
    computers.get_accessible().set_name(tr("网络计算机", "Network computers"))
    computers.append_column(location_column(tr("计算机名称", "Computer name"), "folder_network"))
    computers.append_column(Gtk.TreeViewColumn(tr("网络地址", "Network address"), Gtk.CellRendererText(), text=1))

    def search_location(model, _column, key, item, _data):
        name, uri = model[item]
        # GtkTreeView expects False for a match.
        return not any(key.casefold() in value.casefold() for value in
                       (name, unquote(uri), windows_location(uri) or ""))

    for view in (places, computers):
        view.set_search_column(0)
        view.set_search_equal_func(search_location, None)
        for index, column in enumerate(view.get_columns()):
            column.set_sort_column_id(index)
    discovery_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    searches = {}
    def open_search_result(entry, view):
        key = entry.get_text().strip()
        model, item = view.get_selection().get_selected()
        if key and item is not None and not search_location(model, 0, key, item, None):
            view.row_activated(model.get_path(item), view.get_column(0))

    for view, page in ((places, saved_page), (computers, discovery_page)):
        search = Gtk.SearchEntry(placeholder_text=tr("查找名称或网络地址", "Find a name or network address"))
        view.set_search_entry(search)
        search.connect("activate", open_search_result, view)
        page.pack_start(search, False, False, 0)
        searches[view] = search
    listing = Gtk.ScrolledWindow()
    listing.add(computers)
    discovery_page.pack_start(listing, True, True, 0)
    discovery_status = Gtk.Label(xalign=0, wrap=True)
    discovery_page.add(discovery_status)
    notebook.append_page(discovery_page, Gtk.Label(label=tr("网络计算机", "Network computers")))
    discovering = False

    def show_computers(entries, error):
        global discovering
        discovering = False
        if error:
            discovery_status.set_text(error)
            return False
        model, selected = computers.get_selection().get_selected()
        selected_uri = model[selected][1] if selected is not None else None
        incoming = {uri: name for name, uri in entries}
        existing = {row[1]: row.iter for row in discovered}
        for uri, item in existing.items():
            if uri not in incoming:
                discovered.remove(item)
            elif discovered[item][0] != incoming[uri]:
                discovered[item][0] = incoming[uri]
        for uri, name in incoming.items():
            if uri not in existing:
                discovered.append((name, uri))
        if selected_uri and selected_uri not in incoming:
            computers.get_selection().unselect_all()
        discovery_status.set_text("" if entries else tr(
            "尚未发现 SMB 计算机。也可以在地址栏输入共享路径。",
            "No SMB computers found. You can enter a share path in the address bar."))
        return False

    def discover_computers(_, *, background=False):
        global discovering
        if discovering:
            return
        discovering = True
        if not background:
            discovery_status.set_text(tr("正在查找网络计算机…", "Looking for network computers…"))

        def enumerate_network():
            entries = {}
            errors = []
            for location in ("network:///", "wsdd:///"):
                try:
                    network = Gio.File.new_for_uri(location)
                    files = network.enumerate_children("standard::display-name,standard::target-uri",
                                                       Gio.FileQueryInfoFlags.NONE, None)
                    try:
                        for info in files:
                            uri = info.get_attribute_string("standard::target-uri")
                            if uri and uri.lower().startswith("smb://"):
                                entries.setdefault(uri, info.get_display_name())
                    finally:
                        files.close(None)
                except GLib.Error as exc:
                    errors.append(exc.message)
            result = [(name, uri) for uri, name in entries.items()]
            GLib.idle_add(show_computers, result, errors[0] if len(errors) == 2 else None)

        threading.Thread(target=enumerate_network, daemon=True).start()

    discovery_timer = 0

    def refresh_visible_computers():
        discover_computers(None, background=True)
        return GLib.SOURCE_CONTINUE

    def start_discovery(page):
        global discovery_timer
        discover_computers(page)
        if not discovery_timer:
            discovery_timer = GLib.timeout_add_seconds(8, refresh_visible_computers)

    def stop_discovery(_page):
        global discovery_timer
        if discovery_timer:
            GLib.source_remove(discovery_timer)
            discovery_timer = 0

    discovery_page.connect("map", start_discovery)
    discovery_page.connect("unmap", stop_discovery)

    def reload_places(select_uri=None):
        bookmarks.clear()
        locations = db.execute("SELECT name, places.uri FROM places LEFT JOIN place_names USING (uri)")
        items = [(name or place_caption(uri), uri) for name, uri in locations]
        for caption, uri in sorted(items, key=lambda item: (item[0].casefold(), item[1])):
            item = bookmarks.append((caption, uri))
            if uri == select_uri:
                path = bookmarks.get_path(item)
                places.set_cursor(path)
                places.scroll_to_cell(path)

    def saved_destination(target):
        key = place_key_for_uri(target)
        for (saved,) in db.execute("SELECT uri FROM places ORDER BY (uri = ?) DESC, uri", (target,)):
            if place_key_for_uri(saved) == key:
                return saved
        return None

    def bookmark(_, initial_uri=None, initial_name=""):
        if initial_uri is None and notebook.get_current_page() == 3:
            model, item = mounted_view.get_selection().get_selected()
            if item is not None:
                initial_uri = model[item][1]
        dialog = Gtk.Dialog(title=tr("添加网络位置", "Add a network place"), transient_for=window, modal=True)
        dialog.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(tr("完成", "Finish"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_border_width(12)
        box.set_spacing(8)
        box.add(Gtk.Label(label=tr("输入共享文件夹的网络地址", "Enter the address of the shared folder"), xalign=0))
        entry = Gtk.Entry(text=address.get_text() if initial_uri is None else initial_uri, placeholder_text=address.get_placeholder_text(), width_chars=44)
        entry.set_activates_default(True)
        box.add(entry)
        box.add(Gtk.Label(label=tr("快捷方式名称（可选）", "Shortcut name (optional)"), xalign=0))
        entry.get_accessible().set_name(tr("网络共享地址", "Network share address"))
        name_entry = Gtk.Entry(text=initial_name)
        name_entry.get_accessible().set_name(tr("快捷方式名称", "Shortcut name"))
        name_entry.set_activates_default(True)
        box.add(name_entry)
        feedback = Gtk.Label(xalign=0, wrap=True)
        box.add(feedback)
        dialog.show_all()
        entry.grab_focus()
        try:
            while dialog.run() == Gtk.ResponseType.OK:
                try:
                    uri = share_uri(entry.get_text())
                    break
                except ValueError as exc:
                    feedback.set_text(str(exc))
                    entry.grab_focus()
            else:
                return
            with db:
                db.execute("BEGIN IMMEDIATE")
                uri = saved_destination(uri) or uri
                db.execute("INSERT OR IGNORE INTO places VALUES (?)", (uri,))
                name = name_entry.get_text().strip()
                if name:
                    db.execute("INSERT OR REPLACE INTO place_names (uri, name) VALUES (?, ?)", (uri, name))
            address.set_text(uri)
            notebook.set_current_page(1)
            reload_places(uri)
            places.grab_focus()
            status.set_text(tr("网络位置已保存。", "Network place saved."))
        except sqlite3.Error as exc:
            status.set_text(str(exc))
        finally:
            dialog.destroy()

    last_removed = None

    def remove_place(_):
        global last_removed
        model, it = places.get_selection().get_selected()
        if it is None:
            return
        uri = model[it][1]
        try:
            with db:
                alias = db.execute("SELECT name FROM place_names WHERE uri = ?", (uri,)).fetchone()
                removed = db.execute("DELETE FROM places WHERE uri = ?", (uri,)).rowcount
            if removed:
                last_removed = (uri, alias[0] if alias else None)
                undo.show()
                status.set_text(tr("已移除快捷方式。", "Shortcut removed."))
            reload_places()
        except sqlite3.Error as exc:
            status.set_text(str(exc))

    def undo_remove(_):
        global last_removed
        if last_removed is None:
            return
        uri, alias = last_removed
        try:
            with db:
                added = db.execute("INSERT OR IGNORE INTO places VALUES (?)", (uri,)).rowcount
                if added and alias:
                    db.execute("INSERT INTO place_names VALUES (?, ?)", (uri, alias))
            notebook.set_current_page(1)
            reload_places(uri)
            last_removed = None
            undo.hide()
            status.set_text(tr("快捷方式已恢复。", "Shortcut restored.") if added else
                            tr("此网络位置已存在。", "This network place already exists."))
        except sqlite3.Error as exc:
            status.set_text(str(exc))

    def open_place(view, path, column):
        address.set_text(view.get_model()[path][1])
        connect(None)

    mounts = Gio.VolumeMonitor.get()
    mounted_rows = Gtk.ListStore(str, str, object)
    mounted_view = Gtk.TreeView(model=mounted_rows)
    mounted_view.get_accessible().set_name(tr("已连接共享", "Connected shares"))
    mounted_view.append_column(location_column(tr("共享名", "Share name"), "folder-remote"))
    mounted_view.append_column(Gtk.TreeViewColumn(tr("网络地址", "Network address"), Gtk.CellRendererText(), text=1))
    mounted_view.connect("row-activated", open_place)
    mounted_scroll = Gtk.ScrolledWindow()
    mounted_scroll.add(mounted_view)
    mounted_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    mounted_page.pack_start(mounted_scroll, True, True, 0)
    disconnect = Gtk.Button(label=tr("断开所选共享", "Disconnect selected share"))
    mount_actions = Gtk.Box(spacing=6)
    map_button = Gtk.Button(label=tr("连接共享…", "Connect to share…"))
    mount_actions.pack_start(map_button, True, True, 0)
    cancel_map = Gtk.Button(label=tr("取消连接", "Cancel connection"))
    cancel_map.set_no_show_all(True)
    mount_actions.pack_start(cancel_map, True, True, 0)
    mount_actions.pack_start(disconnect, True, True, 0)
    mounted_page.add(mount_actions)
    notebook.append_page(mounted_page, Gtk.Label(label=tr("已连接共享", "Connected shares")))
    disconnecting = set()

    def update_disconnect(*_):
        model, item = mounted_view.get_selection().get_selected()
        disconnect.set_sensitive(item is not None and model[item][1] not in disconnecting and model[item][2].can_unmount())

    pending_mount_selection = None

    def refresh_mounts(*_):
        global pending_mount_selection
        model, item = mounted_view.get_selection().get_selected()
        selected_uri = model[item][1] if item is not None else None
        mounted_rows.clear()
        target_row = None
        for mount in mounts.get_mounts():
            root = mount.get_root()
            if root.has_uri_scheme("smb"):
                uri = root.get_uri()
                row = mounted_rows.append((mount.get_name(), uri, mount))
                if pending_mount_selection and (pending_mount_selection.equal(root) or
                                                pending_mount_selection.has_prefix(root)):
                    target_row = row
                if uri == selected_uri:
                    mounted_view.get_selection().select_iter(row)
        if target_row is not None:
            path = mounted_rows.get_path(target_row)
            mounted_view.set_cursor(path)
            mounted_view.scroll_to_cell(path)
            pending_mount_selection = None
        update_disconnect()

    def map_share(*_):
        if not map_button.get_sensitive():
            return False
        dialog = Gtk.Dialog(title=tr("映射网络驱动器", "Map Network Drive"), transient_for=window, modal=True)
        dialog.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(tr("连接", "Connect"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_border_width(12)
        box.set_spacing(8)
        box.add(Gtk.Label(label=tr("共享文件夹的网络路径", "Network path of the shared folder"), xalign=0))
        entry = Gtk.Entry(text=address.get_text(), placeholder_text=r"\\server\share", width_chars=40,
                          activates_default=True)
        box.add(entry)
        feedback = Gtk.Label(xalign=0, wrap=True)
        box.add(feedback)
        dialog.show_all()
        try:
            while dialog.run() == Gtk.ResponseType.OK:
                try:
                    uri = share_uri(entry.get_text())
                    if not urlsplit(uri).path.strip("/"):
                        raise ValueError(tr("请输入共享文件夹名称。", "Include the shared folder name."))
                    break
                except ValueError as error:
                    feedback.set_text(str(error))
            else:
                return False
        finally:
            dialog.destroy()
        address.set_text(uri)
        request = Gio.Cancellable()
        cancel_handler = cancel_map.connect("clicked", lambda _: request.cancel())
        map_button.set_sensitive(False)
        map_button.hide()
        cancel_map.show()
        status.set_text(tr("正在连接共享…", "Connecting to share…"))

        def finished(file, result):
            global pending_mount_selection
            cancel_map.disconnect(cancel_handler)
            cancel_map.hide()
            map_button.show()
            map_button.set_sensitive(True)
            try:
                file.mount_enclosing_volume_finish(result)
            except GLib.Error as error:
                if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                    status.set_text(tr("已取消连接。", "Connection cancelled."))
                    return
                if not error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.ALREADY_MOUNTED):
                    status.set_text(error.message)
                    return
            pending_mount_selection = file
            refresh_mounts()
            status.set_text(tr("共享已连接。", "Share connected."))

        Gio.File.new_for_uri(uri).mount_enclosing_volume(Gio.MountMountFlags.NONE, Gtk.MountOperation.new(window),
                                                         request, finished)
        return False

    def disconnect_share(_button):
        model, item = mounted_view.get_selection().get_selected()
        if item is None:
            return
        _, uri, mount = model[item]
        if uri in disconnecting or not mount.can_unmount():
            return
        disconnecting.add(uri)
        update_disconnect()

        def finished(source, result):
            disconnecting.discard(uri)
            try:
                source.unmount_with_operation_finish(result)
                status.set_text(tr("共享连接已断开。", "Share disconnected."))
            except GLib.Error as error:
                status.set_text(error.message)
            refresh_mounts()

        mount.unmount_with_operation(Gio.MountUnmountFlags.NONE, Gtk.MountOperation.new(window), None, finished)

    mounted_view.get_selection().connect("changed", update_disconnect)
    map_button.connect("clicked", map_share)
    disconnect.connect("clicked", disconnect_share)
    for signal in ("mount-added", "mount-removed", "mount-changed"):
        mounts.connect(signal, refresh_mounts)
    refresh_mounts()

    def rename_place(_):
        model, item = places.get_selection().get_selected()
        if item is None:
            return
        place_name.set_property("editable", True)
        places.grab_focus()
        places.set_cursor_on_cell(model.get_path(item), name_column, place_name, True)

    def finish_rename(renderer, path, text):
        renderer.set_property("editable", False)
        uri = bookmarks[path][1]
        name = text.strip()
        try:
            with db:
                if name:
                    db.execute("INSERT OR REPLACE INTO place_names VALUES (?, ?)", (uri, name))
                else:
                    db.execute("DELETE FROM place_names WHERE uri = ?", (uri,))
            reload_places(uri)
        except sqlite3.Error as exc:
            status.set_text(str(exc))

    place_name.connect("edited", finish_rename)
    place_name.connect("editing-canceled", lambda renderer: renderer.set_property("editable", False))

    def place_key(view, event):
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        if Gdk.keyval_to_lower(event.keyval) == Gdk.KEY_z and modifiers == Gdk.ModifierType.CONTROL_MASK and last_removed:
            undo_remove(view)
            return True
        if modifiers or not view.get_selection().count_selected_rows():
            return False
        if event.keyval in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete):
            remove_place(view)
            return True
        if event.keyval == Gdk.KEY_F2:
            rename_place(view)
            return True
        return False

    places.connect("key-press-event", place_key)
    places.connect("row-activated", open_place)
    computers.connect("row-activated", open_place)
    reload_places()
    def copy_text(text):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    def copy_mac_address(_):
        row = selected()
        if row is not None:
            copy_text(mac_address(row[0]))

    def copy_path(_):
        row = selected()
        if row is not None:
            copy_text(row[2])

    def selection_key(view, event):
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        model, item = view.get_selection().get_selected()
        if item is None:
            return False
        if Gdk.keyval_to_lower(event.keyval) == Gdk.KEY_c and modifiers == Gdk.ModifierType.CONTROL_MASK:
            copy_text(model[item][2 if view == table else 1])
            return True
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and modifiers == Gdk.ModifierType.MOD1_MASK:
            if view == table:
                properties()
            else:
                location_properties(model[item][0], model[item][1])
            return True
        return False

    for view in (table, places, computers, mounted_view):
        view.connect("key-press-event", selection_key)

    def refresh_page(_):
        if notebook.get_current_page() == 3:
            refresh_mounts()
        elif notebook.get_current_page() == 2:
            discover_computers(None)
        elif notebook.get_current_page() == 1:
            model, item = places.get_selection().get_selected()
            reload_places(model[item][1] if item is not None else None)
        else:
            refresh()

    def window_key(widget, event):
        modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
        key = Gdk.keyval_to_lower(event.keyval)
        if key == Gdk.KEY_f and modifiers == Gdk.ModifierType.CONTROL_MASK:
            page = notebook.get_current_page()
            if page in (1, 2):
                view = places if page == 1 else computers
                searches[view].grab_focus()
                searches[view].select_region(0, -1)
                return True
        if ((key == Gdk.KEY_d and modifiers == Gdk.ModifierType.MOD1_MASK) or
                (key == Gdk.KEY_l and modifiers == Gdk.ModifierType.CONTROL_MASK)):
            address.grab_focus()
            address.select_region(0, -1)
            return True
        if key == Gdk.KEY_F4 and not modifiers:
            address.grab_focus()
            if len(bookmarks):
                address_list.popup_for_device(event.get_device())
            return True
        if key == Gdk.KEY_F5 and not modifiers:
            refresh_page(widget)
            return True
        return False

    window.connect("key-press-event", window_key)
    buttons = {}
    for label, action in [
        (tr("添加网络位置", "Add a network place"), bookmark),
        (tr("重命名快捷方式", "Rename shortcut"), rename_place),
        (tr("移除快捷方式", "Remove shortcut"), remove_place),
        (tr("浏览网络", "Browse network"), lambda _: browse_share("network:///")),
        (tr("共享文件夹…", "Share a folder…"), create), (tr("复制 Windows 路径", "Copy Windows path"), copy_path),
        (tr("复制 Mac 地址", "Copy Mac address"), copy_mac_address),
        (tr("属性", "Properties"), properties), (tr("停止共享", "Stop sharing"), stop),
        (tr("设置共享密码…", "Set sharing password…"), set_share_password),
        (tr("刷新", "Refresh"), refresh_page)
    ]:
        b = task_button(label)
        b.connect("clicked", action)
        tasks.add(b)
        buttons[action] = b

    def sync_actions(*_):
        page = notebook.get_current_page()
        local = page == 0
        for action in (create, copy_path, copy_mac_address, properties, stop, set_share_password):
            buttons[action].set_visible(local)
        for action in (rename_place, remove_place):
            buttons[action].set_visible(page == 1)
        for action in (properties, stop, copy_path, copy_mac_address):
            buttons[action].set_sensitive(local and selected() is not None)
        for action in (rename_place, remove_place):
            buttons[action].set_sensitive(notebook.get_current_page() == 1 and places.get_selection().count_selected_rows() > 0)

    table.get_selection().connect("changed", sync_actions)
    def pointer_menu(view, event):
        if event.button != 3:
            return False
        hit = view.get_path_at_pos(int(event.x), int(event.y))
        if not hit or event.window != view.get_bin_window():
            return False
        path, column = hit[:2]
        view.grab_focus()
        view.set_cursor(path)
        return show_menu(view, path, column, event)

    def keyboard_menu(view):
        model, row = view.get_selection().get_selected()
        if row is None:
            return False
        return show_menu(view, model.get_path(row), view.get_column(0))

    def change_target(uri):
        dlg = Gtk.Dialog(title=tr("更改目标地址", "Change target address"), transient_for=window, modal=True)
        dlg.add_button(tr("取消", "Cancel"), Gtk.ResponseType.CANCEL)
        dlg.add_button(tr("保存", "Save"), Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        box = dlg.get_content_area()
        box.set_border_width(12)
        entry = Gtk.Entry(text=uri, width_chars=44, activates_default=True)
        box.add(entry)
        feedback = Gtk.Label(xalign=0, wrap=True)
        box.add(feedback)
        dlg.show_all()
        try:
            while dlg.run() == Gtk.ResponseType.OK:
                try:
                    target = share_uri(entry.get_text())
                    if target == uri:
                        return
                    with db:
                        db.execute("BEGIN IMMEDIATE")
                        existing = saved_destination(target)
                        if existing == uri:
                            return
                        if existing is not None:
                            raise ValueError(tr("目标地址已存在。", "This target address already exists."))
                        if not db.execute("INSERT INTO places SELECT ? FROM places WHERE uri = ?", (target, uri)).rowcount:
                            raise ValueError(tr("原快捷方式已移除。", "The original shortcut was removed."))
                        db.execute("UPDATE place_names SET uri = ? WHERE uri = ?", (target, uri))
                        db.execute("DELETE FROM places WHERE uri = ?", (uri,))
                    reload_places(target)
                    if address.get_text() == uri:
                        address.set_text(target)
                    return
                except sqlite3.IntegrityError:
                    feedback.set_text(tr("目标地址已存在。", "This target address already exists."))
                except (sqlite3.Error, ValueError) as exc:
                    feedback.set_text(str(exc))
        finally:
            dlg.destroy()

    def location_properties(name, uri):
        dialog = Gtk.Dialog(title=tr("{} 属性", "{} Properties").format(name), transient_for=window, modal=True)
        dialog.add_button(tr("关闭", "Close"), Gtk.ResponseType.CLOSE)
        grid = Gtk.Grid(column_spacing=12, row_spacing=8, border_width=12)
        dialog.get_content_area().add(grid)
        add_detail(grid, 0, tr("名称", "Name"), name)
        add_detail(grid, 1, tr("网络地址", "Network address"), uri, tr("复制网络地址", "Copy network address"))
        unc = windows_location(uri)
        if unc:
            add_detail(grid, 2, tr("Windows 路径", "Windows path"), unc, tr("复制 Windows 路径", "Copy Windows path"))
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def show_menu(view, path, column, event=None):
        menu = Gtk.Menu()
        if view == table:
            folder = rows[path][1]
            actions = [(tr("打开", "Open"), lambda _: open_local_folder(folder))]
            actions.extend((buttons[action].get_label(), action) for action in
                           (properties, copy_path, copy_mac_address, stop))
        else:
            row = view.get_model()[path]
            name, uri = row[0], row[1]
            def open_target(_):
                address.set_text(uri)
                connect(None)
            actions = [(tr("打开", "Open"), open_target),
                       (tr("复制网络地址", "Copy network address"), lambda _: copy_text(uri))]
            unc = windows_location(uri)
            if unc:
                actions.append((tr("复制 Windows 路径", "Copy Windows path"), lambda _: copy_text(unc)))
            if view == mounted_view:
                actions.append((buttons[bookmark].get_label(), lambda _: bookmark(None, uri)))
            elif view == computers:
                actions.append((buttons[bookmark].get_label(), lambda _: bookmark(None, uri, name)))
            else:
                actions.extend([(tr("更改目标地址…", "Change target address…"), lambda _: change_target(uri)),
                                (buttons[rename_place].get_label(), rename_place),
                                (buttons[remove_place].get_label(), remove_place)])
            actions.append((tr("属性", "Properties"), lambda _: location_properties(name, uri)))
        for label, callback in actions:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", callback)
            menu.append(item)
        menu.attach_to_widget(view, None)
        menu.connect("selection-done", lambda widget: widget.destroy())
        menu.show_all()
        if event is None:
            menu.popup_at_rect(view.get_bin_window(), view.get_cell_area(path, column),
                               Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, Gtk.get_current_event())
            menu.select_first(True)
        else:
            menu.popup_at_pointer(event)
        return True

    for view in (table, places, computers, mounted_view):
        view.connect("button-press-event", pointer_menu)
        view.connect("popup-menu", keyboard_menu)
    places.get_selection().connect("changed", sync_actions)
    notebook.connect_after("switch-page", sync_actions)
    status = Gtk.Label(xalign=0, wrap=True)
    footer = Gtk.Box(spacing=8)
    footer.pack_start(status, True, True, 0)
    undo = Gtk.Button(label=tr("撤销移除", "Undo removal"))
    undo.set_no_show_all(True)
    undo.connect("clicked", undo_remove)
    footer.pack_end(undo, False, False, 0)
    root.add(footer)
    refresh()
    window.show_all()
    if sys.argv[1:] in (["--connected"], ["--map-share"]):
        notebook.set_current_page(3)
        mounted_view.grab_focus()
    elif not sys.argv[1:]:
        notebook.set_current_page(2)
    elif sys.argv[1:] == ["--add-place"]:
        notebook.set_current_page(1)
    sync_actions()
    if len(sys.argv) == 3 and sys.argv[1] == "--share":
        GLib.idle_add(open_folder_sharing, sys.argv[2])
    if sys.argv[1:] == ["--add-place"]:
        GLib.idle_add(bookmark, None)
    if sys.argv[1:] == ["--map-share"]:
        GLib.idle_add(map_share)
    Gtk.main()
