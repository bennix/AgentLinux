#!/usr/bin/python3
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

directory = Path.home() / ".local/share/agentlinux-xp/taskbar-zh"
directory.mkdir(parents=True, exist_ok=True)
resource = "/uk/oddmatics/wintc/taskband/personal-menu.ui"
root = ET.fromstring(subprocess.check_output(["gresource", "extract", "/usr/bin/wintc-taskband", resource]))
folders = {
    "%PLACE_DOCUMENTS%": ("我的文档", "打开用于存放文档的文件夹。"),
    "%PLACE_PICTURES%": ("图片收藏", "打开用于存放照片和图片的文件夹。"),
    "%PLACE_MUSIC%": ("我的音乐", "打开用于存放音乐和音频文件的文件夹。"),
}
for widget in root.iter("object"):
    label = widget.find("property[@name='label']")
    if label is not None and label.text in folders:
        label.text, help_text = folders[label.text]
        tooltip = widget.find("property[@name='tooltip-text']")
        if tooltip is not None:
            tooltip.text = help_text
            tooltip.set("translatable", "no")
ET.ElementTree(root).write(directory / "personal-menu.ui", encoding="UTF-8")
