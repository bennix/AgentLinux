#!/usr/bin/python3
"""Localize the installed WinTC greeter's GTK resources for Chinese sessions."""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

binary, destination = map(Path, sys.argv[1:3])
english = sys.argv[3:] == ["en"]
destination.mkdir(parents=True, exist_ok=True)
labels = {
    "Please wait...": "请稍候…",
    "To begin, click your user name": "请单击用户名开始登录",
    "Turn off computer": "关闭计算机",
    "Type your password": "请输入密码",
    "welcome": "欢迎使用",
    "After you log on, you can add or change accounts. Just go to Control Panel and click User Accounts.": "登录后，可以在控制面板的“用户帐户”中添加或更改帐户。",
}
if english:
    labels = {"To begin, click your user name": "Click your user name"}
for filename in ("welcphs1.ui", "welcphs2.ui", "welcphs3.ui", "welcome.ui", "useritem.ui"):
    if english and filename != "welcphs2.ui":
        continue
    path = "/uk/oddmatics/wintc/logonui/" + filename
    root = ET.fromstring(subprocess.check_output(["gresource", "extract", binary, path]))
    for prop in root.iter("property"):
        if prop.get("name") == "label" and prop.text:
            source = " ".join(prop.text.split())
            if source in labels:
                prop.text = labels[source]
                prop.set("translatable", "no")
    ET.ElementTree(root).write(destination / filename, encoding="UTF-8")

if not english:
    css = subprocess.check_output(["gresource", "extract", binary,
                                   "/uk/oddmatics/wintc/logonui/welcome-ui.css"])
    # Allow for the taller CJK text metrics inside the fixed-height account tile.
    (destination / "welcome-ui.css").write_bytes(css + b"\n.wintc-welcome .user-label { margin-top: 3px; }\n")
