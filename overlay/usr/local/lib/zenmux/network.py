#!/usr/bin/python3
import json
import os
import signal
import subprocess
import threading
from pathlib import Path

from gi.repository import Gio, GLib
import backend

snapshot = backend.SETTINGS.parent / "desktop-proxy-backup.json"
base = "org.gnome.system.proxy"
stop = threading.Event()


def keys():
    yield base, "mode"
    for protocol in ("http", "https", "socks"):
        for key in ("host", "port"):
            yield base + "." + protocol, key
    yield base + ".http", "use-authentication"


def restore():
    if not snapshot.exists():
        return
    values = json.loads(snapshot.read_text())
    for schema, key in reversed(list(keys())):
        item = Gio.Settings.new(schema)
        value = values[schema + "/" + key]
        if value is None:
            item.reset(key)
        else:
            item.set_value(key, GLib.Variant.parse(item.get_value(key).get_type(), value, None, None))
    Gio.Settings.sync()
    snapshot.unlink()


def main():
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    restore()
    cfg = backend.load()
    if not cfg.get("desktop_proxy"):
        subprocess.run(["systemd-notify", "--ready"], check=True)
        return
    with backend.proxy(cfg["data"], cfg["node"], desktop=True) as (_, port, token, controller):
        values = {}
        for schema, key in keys():
            v = Gio.Settings.new(schema).get_user_value(key)
            values[schema + "/" + key] = v.print_(True) if v is not None else None
        tmp = snapshot.with_suffix(".tmp")
        tmp.write_text(json.dumps(values))
        os.replace(tmp, snapshot)
        try:
            for proto in ("http", "https", "socks"):
                item = Gio.Settings.new(base + "." + proto)
                item.set_string("host", "127.0.0.1")
                item.set_int("port", port)
            Gio.Settings.new(base + ".http").set_boolean("use-authentication", False)
            Gio.Settings.new(base).set_string("mode", "manual")
            Gio.Settings.sync()
            subprocess.run(["systemd-notify", "--ready"], check=True)
            while not stop.wait(5):
                import socket
                with socket.create_connection(("127.0.0.1", controller), timeout=2):
                    pass
        finally:
            restore()


if __name__ == "__main__":
    main()
