"""Inspect or activate named controls in an explicitly selected X11 window."""
import json
import subprocess
import sys
from collections import deque

import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

ROLES = {Atspi.Role.PUSH_BUTTON, Atspi.Role.CHECK_BOX, Atspi.Role.RADIO_BUTTON,
         Atspi.Role.TOGGLE_BUTTON, Atspi.Role.PAGE_TAB, Atspi.Role.MENU_ITEM}


def selected_window(wid):
    pid = int(subprocess.check_output(["xdotool", "getwindowpid", wid], timeout=2))
    title = subprocess.check_output(["xdotool", "getwindowname", wid], text=True, timeout=2).rstrip("\n")
    desktop = Atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app and app.get_process_id() == pid:
            windows = [app.get_child_at_index(j) for j in range(app.get_child_count())]
            matches = [w for w in windows if w and w.get_name() == title]
            if len(matches) == 1:
                return matches[0]
    raise ValueError("Window unavailable or ambiguous")


def controls(window):
    queue = deque([(window, "")])
    visited = 0
    while queue and visited < 1200:
        obj, path = queue.popleft()
        visited += 1
        states = obj.get_state_set()
        if obj.get_role() in ROLES and states.contains(Atspi.StateType.SHOWING) and states.contains(Atspi.StateType.ENABLED):
            label = obj.get_name()
            if label and obj.get_n_actions() == 1:
                yield obj, {"path": path, "role": obj.get_role_name(), "label": label[:200]}
        for i in range(min(obj.get_child_count(), 1200 - visited - len(queue))):
            child = obj.get_child_at_index(i)
            if child:
                queue.append((child, f"{path}/{i}"))


def main():
    operation, args = json.load(sys.stdin)
    items = controls(selected_window(args["window_id"]))
    if operation == "list_controls":
        print(json.dumps([info for _, info in items], ensure_ascii=False))
        return
    for obj, info in items:
        if all(info[k] == args[k] for k in ("path", "role", "label")):
            if obj.do_action(0):
                print(json.dumps(info, ensure_ascii=False))
                return
            break
    raise ValueError("Control changed or is unavailable")


if __name__ == "__main__":
    main()
