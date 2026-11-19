#!/usr/bin/python3
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
        super().__init__(title="ZenMux 桌面助手")
        self.set_default_size(680, 610)
        self.cfg = backend.load()
        self.history = [{"role": "system", "content": "使用中文回答。用户要求桌面操作时可调用可用工具。"}]
        self.book = Gtk.Notebook()
        self.add(self.book)
        self.chatbox, self.settings = column(), column()
        settings_scroll = Gtk.ScrolledWindow()
        settings_scroll.add(self.settings)
        for page, name in [(self.chatbox, "助手"), (settings_scroll, "设置")]:
            self.book.append_page(page, Gtk.Label(label=name))
        self.log = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.log)
        self.chatbox.pack_start(scroll, True, True, 0)
        self.form = Gtk.Entry(placeholder_text="输入问题，或描述桌面操作")
        self.form.connect("activate", self.send)
        self.chatbox.add(self.form)
        self.tools = Gtk.CheckButton(label="允许模型提议桌面操作（执行前询问）")
        self.chatbox.add(self.tools)
        self.chatbox.add(button("发送", self.send))
        self.chatbox.add(button("打开 Agent 工作台与微信配对", lambda _: subprocess.Popen(["/opt/ZenCode/zcode"])))

        def field(label, widget):
            self.settings.add(Gtk.Label(label=label, xalign=0))
            self.settings.add(widget)
            return widget

        self.profiles = self.cfg.get("providers", {"ZenMux": {
            "base_url": backend.BASE_URL, "key": self.cfg.get("key", ""),
            "model": self.cfg.get("model", ""), "models": self.cfg.get("models", [])}})
        self.provider = field("AI 供应商（选择或输入新名称）", Gtk.ComboBoxText.new_with_entry())
        for name in self.profiles:
            self.provider.append_text(name)
        self.url = field("Base URL", Gtk.Entry())
        self.key = field("API Key", Gtk.Entry(visibility=False))
        self.invite = button("没有 ZenMux API Key？通过邀请链接注册", lambda _: webbrowser.open(backend.INVITE))
        self.settings.add(self.invite)
        self.model = field("模型名称（可输入新名称）", Gtk.ComboBoxText.new_with_entry())
        self.provider.get_child().connect("changed", self.select_profile)
        self.url.connect("changed", lambda _: self.key.set_text(""))
        self.provider.get_child().set_text(self.cfg.get("provider", "ZenMux"))
        self.proxied = Gtk.CheckButton(label="AI 请求使用代理")
        self.proxied.set_active(self.cfg.get("proxied", False))
        self.settings.add(self.proxied)
        self.desktop_proxy = Gtk.CheckButton(label="桌面网络使用代理（遵循系统代理的应用）")
        self.desktop_proxy.set_active(self.cfg.get("desktop_proxy", False))
        self.settings.add(self.desktop_proxy)
        self.source = field("VLESS 链接或 HTTPS 机场订阅", Gtk.Entry(visibility=False))
        self.source.set_text(self.cfg.get("source", ""))
        self.settings.add(button("导入 / 刷新节点", self.refresh))
        self.node = field("代理节点", Gtk.ComboBoxText())
        self.settings.add(button("测速并选择最佳节点", self.measure))
        self.draft = {k: self.cfg.get(k) for k in ("source", "data", "names")}
        self.populate(self.cfg.get("names", []), self.cfg.get("node"))
        self.settings.add(button("保存设置", self.store))
        self.status = Gtk.Label(xalign=0, wrap=True)
        self.settings.add(self.status)
        self.settings.add(Gtk.LinkButton.new_with_label("https://cs.fudan.edu.cn/", "出品方：复旦大学计算与智能创新学院"))
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
        self.status.set_text("正在读取节点…")
        def loaded(result):
            data, names = result
            self.draft = dict(source=source, data=data, names=names)
            self.populate(names, self.cfg.get("node"))
            self.status.set_text(f"已读取 {len(names)} 个节点，请选择后保存")
        self.work(lambda: backend.nodes(source), loaded, self.status.set_text)

    def measure(self, _):
        if not self.draft.get("data") or self.source.get_text().strip() != self.draft.get("source"):
            return self.status.set_text("请先导入要测速的节点")
        previous = self.node.get_active_id()
        self.status.set_text("正在测试 ZenMux 与 Google，每个目标各 3 次…")
        def progress(done, total):
            GLib.idle_add(self.status.set_text, f"测速中：已完成 {done}/{total} 项测试")
        def measured(rows):
            self.node.remove_all()
            def metric(label, result):
                count, delay = result
                latency = f"{delay} ms" if count else "不可达"
                return f"{label} {count}/3 {latency}"
            for name, zenmux, google in rows:
                self.node.append(name, "　".join((name, metric("ZenMux", zenmux), metric("Google", google))))
            if rows and rows[0][1][0]:
                self.node.set_active(0)
                self.status.set_text("已优先按 ZenMux 成功次数和延迟排序。可手动改选，保存后生效。")
            else:
                self.node.set_active_id(previous) if previous else self.node.set_active(0)
                self.status.set_text("本轮所有节点均未连通 ZenMux，请检查网络或刷新订阅。")
        self.work(lambda: backend.benchmark(self.draft["data"], progress), measured, self.status.set_text)

    def store(self, _):
        model = self.model.get_child().get_text().strip()
        source = self.source.get_text().strip()
        if source and source != self.draft.get("source"):
            return self.status.set_text("请先导入新地址，再保存")
        if (self.proxied.get_active() or self.desktop_proxy.get_active()) and not (source and self.node.get_active_id()):
            return self.status.set_text("请先导入并选择节点")
        provider = self.provider.get_child().get_text().strip()
        base_url = self.url.get_text().strip().rstrip("/")
        if not provider:
            return self.status.set_text("请输入供应商名称")
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
        self.status.set_text("设置已保存至本机" if restart.returncode == 0 else "设置已保存；桌面代理服务启动失败")

    def write(self, line):
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), line + "\n\n")
        self.log.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 1)

    def send(self, _):
        prompt = self.form.get_text().strip()
        profile = self.profiles.get(self.cfg.get("provider", "ZenMux"), {})
        if not profile.get("key") or not profile.get("model"):
            self.book.set_current_page(1)
            return self.status.set_text("请填写并保存 API Key 和模型名称")
        if not prompt:
            return
        self.form.set_text("")
        self.write("我　" + prompt)
        self.history.append({"role": "user", "content": prompt})
        allowed = self.tools.get_active()
        self.work(lambda: backend.chat(self.cfg, self.history, allowed),
                  lambda msg: self.answer(msg, allowed), self.write)

    def answer(self, msg, allowed):
        content = msg.get("content") or ""
        if content:
            self.write("助手　" + content)
        self.history.append({"role": "assistant", "content": content or "收到操作请求。"})
        for call in msg.get("tool_calls", []) if allowed else []:
            try:
                fn = call["function"]
                args = json.loads(fn["arguments"])
                labels = {"open_home": "打开主目录", "create_folder": "在主目录创建文件夹",
                          "system_info": "查看系统信息"}
                dialog = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.OK_CANCEL,
                                           text=labels[fn["name"]])
                dialog.format_secondary_text(json.dumps(args, ensure_ascii=False))
                ok = dialog.run() == Gtk.ResponseType.OK
                dialog.destroy()
                result = backend.action(fn["name"], args) if ok else "已取消"
            except Exception as exc:
                result = str(exc)
            self.write(result)
            self.history[-1]["content"] += "\n操作结果：" + result


if __name__ == "__main__":
    Window()
    Gtk.main()
