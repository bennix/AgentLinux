#!/usr/bin/python3
from pathlib import Path
import subprocess
from task_pane import fit_window
from xml.etree import ElementTree

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk


def activate(app):
    if app.get_active_window():
        app.get_active_window().present()
        return
    chinese = GLib.get_language_names()[0].startswith("zh")
    roots = [GLib.get_user_data_dir(), *GLib.get_system_data_dirs()]
    locales = ["zh_CN", "C"] if chinese else ["C"]
    page = next(Path(root, "help", lang, "agentlinux-xp/index.page")
                for lang in locales for root in roots
                if Path(root, "help", lang, "agentlinux-xp/index.page").is_file())
    doc = ElementTree.parse(page).getroot()
    title = doc.findtext("{*}title")
    window = Gtk.ApplicationWindow(application=app, title=title)
    fit_window(window, 700, 440)
    window.set_icon_name("help-browser")
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    window.add(box)
    header = Gtk.Label(label=title, xalign=0)
    header.set_name("help-banner")
    box.pack_start(header, False, False, 0)
    area = Gtk.Box()
    box.pack_start(area, True, True, 0)
    sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    sidebar.set_name("help-navigation")
    area.pack_start(sidebar, False, False, 0)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    content.set_border_width(18)
    area.pack_start(content, True, True, 0)
    heading = Gtk.Label(xalign=0)
    heading.set_name("help-heading")
    body = Gtk.Label(xalign=0, yalign=0)
    body.set_line_wrap(True)
    body.set_selectable(True)
    content.pack_start(heading, False, False, 0)
    reading = Gtk.ScrolledWindow()
    reading.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    reading.add(body)
    content.pack_start(reading, True, True, 0)
    more = doc.find("{*}section[@id='more']/{*}p/{*}link")
    link = Gtk.Button(label=more.text)
    link.connect("clicked", lambda *_: subprocess.Popen(["/usr/bin/yelp", "help-list:"]))
    content.pack_end(link, False, False, 0)
    topic_targets = {"desktop": "search", "programs": "programs", "fonts": "fonts", "printers": "printers",
                     "input": "keyboard", "network": "connections"}
    target = None
    open_topic = Gtk.Button()
    open_topic.set_no_show_all(True)
    content.pack_end(open_topic, False, False, 0)

    def launch_topic(_button):
        if target:
            try:
                target.launch([], window.get_display().get_app_launch_context())
            except GLib.Error as error:
                notice = Gtk.MessageDialog(transient_for=window, modal=True,
                                           message_type=Gtk.MessageType.ERROR,
                                           buttons=Gtk.ButtonsType.CLOSE, text=error.message)
                notice.run()
                notice.destroy()

    open_topic.connect("clicked", launch_topic)
    group = None
    for section in doc.findall("{*}section"):
        if section.get("id") == "more":
            continue
        name = section.findtext("{*}title")
        paragraph = section.findtext("{*}p")
        button = Gtk.RadioButton.new_with_label_from_widget(group, name)
        button.set_mode(False)
        sidebar.pack_start(button, False, False, 0)

        def select(widget, topic=name, text=paragraph, component=topic_targets.get(section.get("id"))):
            nonlocal target
            if widget.get_active():
                target = None
                if component:
                    try:
                        target = Gio.DesktopAppInfo.new(f"agentlinux-xp-{component}.desktop")
                    except TypeError:
                        pass
                if target:
                    label = target.get_display_name()
                    open_topic.set_label(f"打开“{label}”" if chinese else f"Open {label}")
                open_topic.set_visible(target is not None)
                heading.set_text(topic)
                body.set_text(text)
                reading.get_vadjustment().set_value(0)

        button.connect("toggled", select)
        if group is None:
            group = button
            select(button)
    css = Gtk.CssProvider()
    css.load_from_data(b"""
        #help-banner { background-image: linear-gradient(to right,#17479a,#517dd0);
            color: white; padding: 16px; font-size: 23px; font-weight: bold; }
        #help-navigation { background-color: #dce7f9; padding: 12px; }
        #help-navigation button:checked { background-image: none; background-color: #315fa6; color: white; }
        #help-heading { color: #204c91; font-size: 18px; font-weight: bold; }
    """)
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window.show_all()


app = Gtk.Application(application_id="org.agentlinux.HelpCenter", flags=Gio.ApplicationFlags.FLAGS_NONE)
app.connect("activate", activate)
app.run()
