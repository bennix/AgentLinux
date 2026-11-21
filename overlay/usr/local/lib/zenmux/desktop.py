#!/usr/bin/python3
from gettext import dgettext
from functools import partial
tr = partial(dgettext, 'agentlinux')
import json
import threading
import subprocess
import webbrowser

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk
import backend


def column():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_border_width(16)
    return box


def button(label, callback):
    item = Gtk.Button(label=label)
    item.connect("clicked", callback)
    return item


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title=tr('ZenMux Desktop Assistant'))
        self.set_default_size(680, 610)
        self.cfg = backend.load()
        self.history = [{"role": "system", "content": tr('Respond in English. Use the available tools when the user requests desktop actions.')}]
        self.book = Gtk.Notebook()
        self.add(self.book)
        self.chatbox, self.settings = column(), column()
        settings_scroll = Gtk.ScrolledWindow()
        settings_scroll.add(self.settings)
        for page, name in [(self.chatbox, tr('Assistant')), (settings_scroll, tr('Settings'))]:
            self.book.append_page(page, Gtk.Label(label=name))
        self.log = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.log)
        self.chatbox.pack_start(scroll, True, True, 0)
        self.form = Gtk.Entry(placeholder_text=tr('Ask a question or describe a desktop action'))
        self.form.connect("activate", self.send)
        self.chatbox.add(self.form)
        self.tools = Gtk.CheckButton(label=tr('Allow proposed desktop actions (confirm before running)'))
        self.chatbox.add(self.tools)
        self.chatbox.add(button(tr('Send'), self.send))
        self.chatbox.add(button(tr('Open the agent workbench and WeChat pairing'), lambda _: subprocess.Popen(["/opt/ZenCode/zcode"])))

        def field(label, widget):
            self.settings.add(Gtk.Label(label=label, xalign=0))
            self.settings.add(widget)
            return widget

        self.profiles = self.cfg.get("providers", {"ZenMux": {
            "base_url": backend.BASE_URL, "key": self.cfg.get("key", ""),
            "model": self.cfg.get("model", ""), "models": self.cfg.get("models", [])}})
        self.provider = field(tr('AI provider (select or enter a name)'), Gtk.ComboBoxText.new_with_entry())
        for name in self.profiles:
            self.provider.append_text(name)
        self.url = field("Base URL", Gtk.Entry())
        self.key = field("API Key", Gtk.Entry(visibility=False))
        self.invite = button(tr('Get a ZenMux API key via invitation'), lambda _: webbrowser.open(backend.INVITE))
        self.settings.add(self.invite)
        self.model = field(tr('Model name (select or enter a name)'), Gtk.ComboBoxText.new_with_entry())
        self.provider.get_child().connect("changed", self.select_profile)
        self.url.connect("changed", lambda _: self.key.set_text(""))
        self.provider.get_child().set_text(self.cfg.get("provider", "ZenMux"))
        self.proxied = Gtk.CheckButton(label=tr('Proxy AI requests'))
        self.proxied.set_active(self.cfg.get("proxied", False))
        self.settings.add(self.proxied)
        self.desktop_proxy = Gtk.CheckButton(label=tr('Use the desktop proxy for supported applications'))
        self.desktop_proxy.set_active(self.cfg.get("desktop_proxy", False))
        self.settings.add(self.desktop_proxy)
        self.source = field(tr('VLESS link or HTTPS subscription'), Gtk.Entry(visibility=False))
        self.source.set_text(self.cfg.get("source", ""))
        self.settings.add(button(tr('Import / refresh nodes'), self.refresh))
        self.node = field(tr('Proxy node'), Gtk.ComboBoxText())
        self.settings.add(button(tr('Benchmark and select a node'), self.measure))
        self.draft = {k: self.cfg.get(k) for k in ("source", "data", "names")}
        self.populate(self.cfg.get("names", []), self.cfg.get("node"))
        self.settings.add(button(tr('Save settings'), self.store))
        self.status = Gtk.Label(xalign=0, wrap=True)
        self.settings.add(self.status)
        self.settings.add(Gtk.LinkButton.new_with_label("https://cs.fudan.edu.cn/", tr('Publisher: Fudan University School of Computer Science and Artificial Intelligence')))
        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        self.select_profile(self.provider.get_child())
        if not self.key.get_text():
            self.book.set_current_page(1)

    def select_profile(self, entry):
        name = entry.get_text().strip()
        profile = self.profiles.get(name, {})
        self.url.set_text(profile.get("base_url", backend.BASE_URL if name == "ZenMux" else ""))
        self.key.set_text(profile.get("key", ""))
        self.model.remove_all()
        for model in profile.get("models", []):
            self.model.append_text(model)
        self.model.get_child().set_text(profile.get("model", ""))
        self.invite.set_visible(name == "ZenMux")

    def populate(self, names, selected):
        self.node.remove_all()
        for name in names:
            self.node.append(name, name)
        self.node.set_active(names.index(selected) if selected in names else 0)

    def work(self, operation, success, failure):
        self.book.set_sensitive(False)
        def finish(callback, value):
            self.book.set_sensitive(True)
            callback(value)
            return False
        def worker():
            try:
                result = operation()
            except Exception as exc:
                GLib.idle_add(finish, failure, str(exc))
            else:
                GLib.idle_add(finish, success, result)
        threading.Thread(target=worker, daemon=True).start()

    def refresh(self, _):
        source = self.source.get_text().strip()
        self.status.set_text(tr('Reading nodes…'))
        def loaded(result):
            data, names = result
            self.draft = dict(source=source, data=data, names=names)
            self.populate(names, self.cfg.get("node"))
            self.status.set_text(tr('Loaded {} nodes. Select one and save.').format(len(names)))
        self.work(lambda: backend.nodes(source), loaded, self.status.set_text)

    def measure(self, _):
        if not self.draft.get("data") or self.source.get_text().strip() != self.draft.get("source"):
            return self.status.set_text(tr('Import nodes before testing'))
        previous = self.node.get_active_id()
        self.status.set_text(tr('Testing ZenMux and Google three times per destination…'))
        def progress(done, total):
            GLib.idle_add(self.status.set_text, tr('Benchmark: {}/{} tests complete').format(done, total))
        def measured(rows):
            self.node.remove_all()
            def metric(label, result):
                count, delay = result
                latency = f"{delay} ms" if count else tr('Unreachable')
                return f"{label} {count}/3 {latency}"
            for name, zenmux, google in rows:
                self.node.append(name, "　".join((name, metric("ZenMux", zenmux), metric("Google", google))))
            if rows and rows[0][1][0]:
                self.node.set_active(0)
                self.status.set_text(tr('Sorted by ZenMux successes and latency. Select a node and save to apply.'))
            else:
                self.node.set_active_id(previous) if previous else self.node.set_active(0)
                self.status.set_text(tr('No nodes reached ZenMux. Check the network or refresh the subscription.'))
        self.work(lambda: backend.benchmark(self.draft["data"], progress), measured, self.status.set_text)

    def store(self, _):
        model = self.model.get_child().get_text().strip()
        source = self.source.get_text().strip()
        if source and source != self.draft.get("source"):
            return self.status.set_text(tr('Import the new URL before saving'))
        if (self.proxied.get_active() or self.desktop_proxy.get_active()) and not (source and self.node.get_active_id()):
            return self.status.set_text(tr('Import and select a node first'))
        provider = self.provider.get_child().get_text().strip()
        base_url = self.url.get_text().strip().rstrip("/")
        if not provider:
            return self.status.set_text(tr('Enter a provider name'))
        try:
            backend.endpoint(base_url)
        except ValueError as exc:
            return self.status.set_text(str(exc))
        names = list(self.profiles.get(provider, {}).get("models", []))
        added = bool(model and model not in names)
        if added:
            names.append(model)
        profile = dict(base_url=base_url, key=self.key.get_text().strip(), model=model, models=names)
        profiles = dict(self.profiles, **{provider: profile})
        cfg = dict(self.draft if source else {}, providers=profiles, provider=provider,
                   proxied=self.proxied.get_active(), desktop_proxy=self.desktop_proxy.get_active(), node=self.node.get_active_id() if source else None)
        try:
            backend.save(cfg)
        except OSError as exc:
            return self.status.set_text(str(exc))
        previous = self.cfg.get("provider", "ZenMux")
        if provider != previous or self.profiles.get(previous, {}).get("base_url") != base_url:
            self.history = self.history[:1]
            self.log.get_buffer().set_text("")
        if provider not in self.profiles:
            self.provider.append_text(provider)
        self.profiles = profiles
        self.cfg = cfg
        if added:
            self.model.append_text(model)
        restart = subprocess.run(["systemctl", "--user", "restart", "zenmux-network.service"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.status.set_text(tr('Settings saved locally') if restart.returncode == 0 else tr('Settings saved. The desktop proxy service failed to start.'))

    def write(self, line):
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), line + "\n\n")
        self.log.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 1)

    def send(self, _):
        prompt = self.form.get_text().strip()
        profile = self.profiles.get(self.cfg.get("provider", "ZenMux"), {})
        if not profile.get("key") or not profile.get("model"):
            self.book.set_current_page(1)
            return self.status.set_text(tr('Enter and save an API key and model name first'))
        if not prompt:
            return
        self.form.set_text("")
        self.write(tr('You: ') + prompt)
        self.history.append({"role": "user", "content": prompt})
        allowed = self.tools.get_active()
        self.work(lambda: backend.chat(self.cfg, self.history, allowed),
                  lambda msg: self.answer(msg, allowed), self.write)

    def answer(self, msg, allowed, rounds=0):
        content = msg.get("content") or ""
        if content:
            self.write(tr('Assistant: ') + content)
        calls = msg.get("tool_calls") if allowed else None
        if not calls:
            self.history.append({"role": "assistant", "content": content})
            return
        if not all(isinstance(call, dict) and isinstance(call.get("id"), str)
                   and isinstance(call.get("function"), dict) for call in calls):
            self.write(tr('Invalid tool response'))
            return
        self.history.append({"role": "assistant", "content": content or None, "tool_calls": calls})
        stopped = False
        for call in calls:
            if stopped:
                self.history.append({"role": "tool", "tool_call_id": call["id"], "content": tr('Cancelled')})
                continue
            try:
                fn = call["function"]
                args = json.loads(fn["arguments"])
                labels = {"open_home": tr('Open home folder'), "create_folder": tr('Create a folder in your home directory'),
                          "system_info": tr('View system information'),
                          "network_status": tr('Inspect active NetworkManager connections and the system tunnel'),
                          "disk_usage": tr('Inspect available space on local filesystems'),
                          "failed_services": tr('List failed system and user services'),
                          "list_controls": tr('List visible buttons in a selected window'),
                          "activate_control": tr('Activate a named control in a selected window'),
                          "list_apps": tr('List installed desktop applications'),
                          "launch_app": tr('Launch an installed application by its desktop ID'),
                          "list_windows": tr('List open desktop windows and titles'),
                          "focus_window": tr('Activate a listed desktop window')}
                dialog = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.OK_CANCEL,
                                           text=labels[fn["name"]])
                dialog.format_secondary_text(json.dumps(args, ensure_ascii=False) + "\n" + tr("The result will be sent to your selected AI provider."))
                ok = dialog.run() == Gtk.ResponseType.OK
                dialog.destroy()
                stopped = not ok
                result = backend.action(fn["name"], args) if ok else tr('Cancelled')
            except Exception as exc:
                result = str(exc)
            self.write(result)
            self.history.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        if stopped:
            return
        more_tools = rounds < 7 and self.tools.get_active()
        self.work(lambda: backend.chat(self.cfg, self.history, more_tools),
                  lambda reply: self.answer(reply, more_tools, rounds + 1), self.write)


if __name__ == "__main__":
    Window()
    Gtk.main()
