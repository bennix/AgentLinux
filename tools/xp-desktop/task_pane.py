import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk


def cycle_property_pages(_dialog, event, tabs):
    modifiers = event.state & Gtk.accelerator_get_default_mod_mask()
    ctrl = Gdk.ModifierType.CONTROL_MASK
    shift = Gdk.ModifierType.SHIFT_MASK
    if event.keyval not in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab) or modifiers not in (ctrl, ctrl | shift):
        return False
    step = -1 if modifiers & shift else 1
    tabs.set_current_page((tabs.get_current_page() + step) % tabs.get_n_pages())
    tabs.grab_focus()
    return True

def fit_window(window, width, height):
    display = window.get_display()
    monitor = display.get_primary_monitor() or display.get_monitor(0)
    work = monitor.get_workarea()
    window.set_default_size(min(width, work.width - 24), min(height, work.height - 64))


def task_button(label):
    button = Gtk.Button(label=label)
    button.set_relief(Gtk.ReliefStyle.NONE)
    button.get_child().set_xalign(0)
    return button


def add_task_pane(layout, title):
    sidebar = Gtk.ScrolledWindow()
    sidebar.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    sidebar.set_propagate_natural_width(True)
    layout.pack_start(sidebar, False, False, 0)
    pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    pane.set_name("xp-task-pane")
    sidebar.add(pane)
    group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    group.set_margin_start(8)
    group.set_margin_end(8)
    group.set_margin_top(10)
    pane.pack_start(group, False, False, 0)
    heading = Gtk.ToggleButton()
    heading.set_name("xp-task-heading")
    heading.get_accessible().set_name(title)
    heading.set_active(True)
    caption = Gtk.Box(spacing=6)
    caption.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
    arrow = Gtk.Image.new_from_icon_name("pan-up-symbolic", Gtk.IconSize.MENU)
    caption.pack_end(arrow, False, False, 0)
    heading.add(caption)
    group.pack_start(heading, False, False, 0)
    reveal = Gtk.Revealer()
    reveal.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
    reveal.set_reveal_child(True)
    group.pack_start(reveal, False, False, 0)
    tasks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    tasks.set_name("xp-task-tasks")
    reveal.add(tasks)

    def toggle(button):
        expanded = button.get_active()
        reveal.set_reveal_child(expanded)
        arrow.set_from_icon_name("pan-up-symbolic" if expanded else "pan-down-symbolic", Gtk.IconSize.MENU)

    heading.connect("toggled", toggle)
    style = Gtk.CssProvider()
    style.load_from_data(b"""
        #xp-task-pane { background-image: linear-gradient(to bottom, #7698e7, #647ed4); }
        #xp-task-tasks { background-color: #d7dff5; padding-bottom: 5px; }
        #xp-task-heading { background-color: #eff3ff; color: #174481; font-weight: bold; padding: 6px; }
        #xp-task-tasks button { padding: 4px 6px; }
        #xp-task-tasks button:not(:disabled) label { color: #16458b; }
        #xp-task-tasks button:hover:not(:disabled) label { text-decoration-line: underline; }
    """)
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    return tasks
