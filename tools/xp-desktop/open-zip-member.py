#!/usr/bin/python3
"""Open one ZIP member with its desktop application using a private runtime copy."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
from zipfile import ZipFile

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk


def open_member(archive, member):
    name = member.rsplit("/", 1)[-1]
    if name in ("", ".", ".."):
        raise ValueError(member)
    with ZipFile(archive) as source, source.open(member) as stream:
        directory = Path(tempfile.mkdtemp(prefix="agentlinux-zip-", dir=GLib.get_user_runtime_dir()))
        target = directory / name
        try:
            with target.open("xb") as output:
                shutil.copyfileobj(stream, output)
            os.chmod(target, 0o400)
            Gio.AppInfo.launch_default_for_uri(target.as_uri(), None)
        except Exception:
            shutil.rmtree(directory)
            raise


if __name__ == "__main__":
    try:
        open_member(*sys.argv[1:])
    except Exception as error:
        chinese = GLib.get_language_names()[0].startswith("zh")
        dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                   text="无法打开压缩包中的文件" if chinese else "Cannot open the archived file")
        dialog.format_secondary_text(str(error))
        dialog.run()
        dialog.destroy()
        sys.exit(1)
