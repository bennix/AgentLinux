from gettext import dgettext
from functools import partial
tr = partial(dgettext, 'agentlinux')
import base64
import concurrent.futures
import contextlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import statistics
import sys
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

CORE = Path(__file__).with_name("mihomo")
SETTINGS = Path.home() / ".config/zenmux-agent/settings.json"
INVITE = "https://zenmux.ai/invite/GBQMC5"
BASE_URL = "https://zenmux.ai/api/v1"


def load():
    if SETTINGS.exists():
        return json.loads(SETTINGS.read_text())
    return {}


def save(config):
    SETTINGS.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=SETTINGS.parent, mode="w", delete=False) as f:
        json.dump(config, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(f.name, SETTINGS)


class SecureRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        if urllib.parse.urlsplit(url).scheme != "https":
            raise ValueError(tr('Subscription redirects require HTTPS'))
        return super().redirect_request(req, fp, code, msg, headers, url)


def provider_data(source):
    if source.startswith("vless://"):
        return source
    if not source.startswith("https://"):
        raise ValueError(tr('Enter a VLESS link or HTTPS subscription URL'))
    req = urllib.request.Request(source, headers={"User-Agent": "clash.meta"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), SecureRedirect())
    with opener.open(req, timeout=25) as resp:
        data = resp.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError(tr('Subscription exceeds 8 MiB'))
    return data.decode("utf-8-sig")


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def proxy(data, selection=None, desktop=False):
    with tempfile.TemporaryDirectory(prefix="zenmux-") as tmp:
        root = Path(tmp)
        (root / "nodes").write_text(data)
        listen, control = port(), port()
        while control == listen:
            control = port()
        token = secrets.token_hex(24)
        config = {"mixed-port": listen, "bind-address": "127.0.0.1", "allow-lan": False,
                  "external-controller": f"127.0.0.1:{control}", "secret": token,
                  "authentication": [] if desktop else ["agent:" + token], "mode": "rule", "log-level": "silent",
                  "profile": {"store-selected": False}, "ipv6": True,
                  "proxy-providers": {"nodes": {"type": "file", "path": "./nodes"}},
                  "proxy-groups": [{"name": "ZenMux Route", "type": "select", "use": ["nodes"]}],
                  "rules": ["MATCH,ZenMux Route"]}
        if selection:
            from smart_routing import configure
            configure(config, root, "ZenMux Route")
        (root / "config.yaml").write_text(json.dumps(config))
        proc = subprocess.Popen([str(CORE), "-d", tmp], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        try:
            client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            url = f"http://127.0.0.1:{control}/proxies/ZenMux%20Route"
            headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline and proc.poll() is None:
                try:
                    with client.open(urllib.request.Request(url, headers=headers), timeout=1) as r:
                        names = json.load(r)["all"]
                    if names and names != ["COMPATIBLE"]:
                        break
                except (OSError, KeyError):
                    pass
                time.sleep(0.15)
            else:
                raise ValueError(tr('Proxy startup failed. Check the node format or import again.'))
            if selection:
                if selection not in names:
                    raise ValueError(tr('The selected node is unavailable. Select another.'))
                request = urllib.request.Request(url, data=json.dumps({"name": selection}).encode(),
                                                 headers=headers, method="PUT")
                client.open(request, timeout=3).close()
            yield names, listen, token, control
        finally:
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def nodes(source):
    data = provider_data(source)
    with proxy(data) as (names, _, __, ___):
        return data, names


def benchmark(data, progress):
    """Probe each individual proxy via the local Mihomo controller."""
    with proxy(data) as (names, _, token, control):
        def probe(name, target):
            endpoint = urllib.parse.quote(name, safe="")
            query = urllib.parse.urlencode({"timeout": 4500, "url": target})
            req = urllib.request.Request(f"http://127.0.0.1:{control}/providers/proxies/nodes/{endpoint}/healthcheck?{query}",
                                         headers={"Authorization": "Bearer " + token})
            client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            delays = []
            for _ in range(3):
                try:
                    with client.open(req, timeout=6) as resp:
                        delay = json.load(resp)["delay"]
                    if isinstance(delay, int) and delay > 0:
                        delays.append(delay)
                except (OSError, ValueError, KeyError):
                    continue
            return len(delays), int(statistics.median(delays)) if delays else None

        targets = ("https://zenmux.ai/", "https://www.google.com/generate_204")
        results = {name: {} for name in names}
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(probe, name, url): (name, index)
                       for name in names for index, url in enumerate(targets)}
            for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
                name, index = futures[future]
                results[name][index] = future.result()
                progress(done, len(futures))
        rows = [(name, values[0], values[1]) for name, values in results.items()]
        return sorted(rows, key=lambda row: (-row[1][0], row[1][1] or float("inf"),
                                              -row[2][0], row[2][1] or float("inf"), row[0]))


TOOLS = [{"type": "function", "function": {
    "name": name, "description": desc,
    "parameters": {"type": "object", "properties": props, "required": list(props),
                   "additionalProperties": False}}}
    for name, desc, props in [
        ("list_components", tr("Discover installed apps and system components by stable ID"), {}),
        ("inspect_component", tr("Read system status or inspect an installed app and its launch interface"),
         {"component": {"type": "string"}}),
        ("create_office_file", tr("Create a LibreOffice document, spreadsheet (cell A1), or presentation with the supplied text"),
         {"kind": {"type": "string", "enum": ["writer", "calc", "impress"]}, "text": {"type": "string"}}),
        ("network_status", tr('Inspect active NetworkManager connections and the system tunnel'), {}),
        ("disk_usage", tr('Inspect available space on local filesystems'), {}),
        ("failed_services", tr('List failed system and user services'), {}),
        ("list_apps", tr('List installed desktop applications'), {}),
        ("launch_app", tr('Launch an installed application by its desktop ID'), {"desktop_id": {"type": "string"}}),
        ("list_windows", tr('List open desktop windows and titles'), {}),
        ("focus_window", tr('Activate a listed desktop window'), {"window_id": {"type": "string"}}),
        ("list_controls", tr('List visible controls and slider values in a selected window'), {"window_id": {"type": "string"}}),
        ("activate_control", tr('Activate a named control in a selected window'),
         {key: {"type": "string"} for key in ("window_id", "path", "role", "label")}),
        ("set_slider_value", tr('Set a named slider in a selected window'),
         {**{key: {"type": "string"} for key in ("window_id", "path", "role", "label")}, "value": {"type": "number"}}),
        ("open_home", tr('Open the home directory in the file manager'), {}),
        ("create_folder", tr('Create a folder in the home directory'), {"name": {"type": "string"}}),
        ("system_info", tr('Show the system name, kernel version and architecture'), {})]]


def endpoint(url):
    parsed = urllib.parse.urlsplit(url)
    local = parsed.hostname in ("127.0.0.1", "localhost", "::1")
    if (not parsed.hostname or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or any(c.isspace() for c in url)
            or not (parsed.scheme == "https" or (parsed.scheme == "http" and local))):
        raise ValueError(tr('Enter a valid HTTPS base URL. Local endpoints also support HTTP.'))
    if parsed.port == 0:
        raise ValueError(tr('Invalid base URL port'))
    return parsed


def chat(cfg, messages, use_tools):
    profile = cfg.get("providers", {}).get(cfg.get("provider"), cfg)
    target = endpoint(profile.get("base_url", BASE_URL))
    if cfg.get("proxied") and target.scheme != "https":
        raise ValueError(tr('Use direct access for local HTTP endpoints'))
    payload = {"model": profile["model"], "messages": messages}
    if use_tools:
        payload["tools"] = TOOLS
    if cfg.get("proxied") and not (cfg.get("data") and cfg.get("node")):
        raise ValueError(tr('Import and select a proxy node first'))
    route = proxy(cfg["data"], cfg["node"]) if cfg.get("proxied") else contextlib.nullcontext()
    with route as active:
        if active:
            _, listen, token, _ = active
            conn = http.client.HTTPSConnection("127.0.0.1", listen, timeout=90)
            auth = base64.b64encode(("agent:" + token).encode()).decode()
            conn.set_tunnel(target.hostname, target.port or 443, {"Proxy-Authorization": "Basic " + auth})
        else:
            connection = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
            conn = connection(target.hostname, target.port, timeout=90)
        try:
            conn.request("POST", target.path.rstrip("/") + "/chat/completions", json.dumps(payload).encode(),
                         {"Authorization": "Bearer " + profile["key"], "Content-Type": "application/json"})
            response = conn.getresponse()
            if response.status != 200:
                raise ValueError(tr('Provider returned HTTP {}. Check the key, balance, model and tool support.').format(response.status))
            return json.load(response)["choices"][0]["message"]
        finally:
            conn.close()


def action(name, args):
    if name == "create_office_file" and set(args) == {"kind", "text"}:
        from office import create_file
        return str(create_file(**args))
    if name == "list_components" and not args:
        from components import catalog
        return json.dumps(catalog(), ensure_ascii=False)
    if name == "inspect_component" and set(args) == {"component"} and isinstance(args["component"], str):
        from components import describe
        return json.dumps(describe(args["component"]), ensure_ascii=False)
    if not args and name == "network_status":
        return subprocess.check_output(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
                                       text=True, timeout=5)
    if not args and name == "disk_usage":
        return subprocess.check_output(["df", "-lh", "-x", "tmpfs", "-x", "devtmpfs"], text=True, timeout=5)
    if not args and name == "failed_services":
        return "\n".join(subprocess.check_output(["systemctl", scope, "--failed", "--no-pager",
                                                  "--plain", "--no-legend"], text=True, timeout=5)
                         for scope in ("--system", "--user")).strip() or tr('No failed services')
    if name in ("list_apps", "launch_app"):
        from gi.repository import Gio
        apps = {a.get_id(): a for a in Gio.AppInfo.get_all() if a.get_id() and a.should_show()}
        if name == "list_apps" and not args:
            return json.dumps({key: apps[key].get_display_name() for key in sorted(apps)}, ensure_ascii=False)
        if name == "launch_app" and set(args) == {"desktop_id"} and args["desktop_id"] in apps:
            app = apps[args["desktop_id"]]
            app.launch([], None)
            return app.get_display_name()
    if name in ("list_windows", "focus_window", "list_controls", "activate_control", "set_slider_value"):
        import re
        listing = subprocess.check_output(["xprop", "-root", "_NET_CLIENT_LIST_STACKING"], text=True, timeout=3)
        ids = re.findall(r"0x[0-9a-fA-F]+", listing)
        if not ids:
            listing = subprocess.check_output(["xprop", "-root", "_NET_CLIENT_LIST"], text=True, timeout=3)
            ids = re.findall(r"0x[0-9a-fA-F]+", listing)
        if name == "list_windows" and not args:
            windows = {}
            for wid in ids:
                title = subprocess.run(["xdotool", "getwindowname", wid], capture_output=True, text=True, timeout=3)
                if title.returncode == 0:
                    windows[wid] = title.stdout.strip()[:250]
            return json.dumps(windows, ensure_ascii=False)
        if name in ("list_controls", "activate_control", "set_slider_value") and args.get("window_id") in ids:
            keys = {"window_id"} if name == "list_controls" else {"window_id", "path", "role", "label"}
            expected = keys | {"value"} if name == "set_slider_value" else keys
            if name == "set_slider_value" and type(args.get("value")) not in (int, float):
                raise ValueError(tr('Unsupported action'))
            if set(args) == expected and all(isinstance(args[k], str) for k in keys):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name("accessible.py"))],
                                        input=json.dumps([name, args]), capture_output=True, text=True, timeout=10)
                if result.returncode:
                    raise ValueError(tr('The window or control is unavailable. Inspect it again.'))
                return result.stdout.strip()
        if name == "focus_window" and set(args) == {"window_id"} and args["window_id"] in ids:
            wid = args["window_id"]
            subprocess.run(["xdotool", "windowactivate", "--sync", wid], check=True, timeout=3)
            return subprocess.check_output(["xdotool", "getwindowname", wid], text=True, timeout=3).strip()
    if name == "open_home" and not args:
        subprocess.run(["xdg-open", str(Path.home())], check=True)
        return tr('Opened home directory')
    if name == "system_info" and not args:
        import platform
        return " ".join(platform.uname()[i] for i in (0, 2, 4))
    if name == "create_folder" and set(args) == {"name"}:
        folder = args["name"]
        if not isinstance(folder, str) or not folder.strip() or folder in (".", "..") or "/" in folder:
            raise ValueError(tr('Enter a single valid directory name'))
        (Path.home() / folder).mkdir(mode=0o700)
        return tr('Created folder {}').format(folder)
    raise ValueError(tr('Unsupported action'))
