#!/usr/bin/python3
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

labels = dict(line.split("|") for line in """_File|文件(_F)
%CTL_VIEWMENU%|查看
%CTL_HELPMENU%|帮助
Processes|进程
Show processes from all users|显示所有用户的进程
End Process|结束进程
_New Task (Run...)|新建任务（运行…）(_N)
E_xit Task Manager|退出任务管理器(_X)
Options|选项
Always On Top|置于顶层
Minimize On Use|使用时最小化
Hide When Minimized|最小化时隐藏
Show 16-bit tasks|显示 16 位任务
Refresh Now|立即刷新
Update Speed|更新速度
Select Columns|选择列
Shut Down|关机
Stand By|待机
Hibernate|休眠
Turn Off|关闭
Restart|重新启动
Log Off %s|注销 %s
Switch User|切换用户
Task Manager Help Topics|任务管理器帮助主题
About Task Manager|关于任务管理器
Processes: %d|当前用户的进程
Task Manager Warning|任务管理器警告""".splitlines())
directory = Path.home() / ".local/share/agentlinux-xp/taskmgr-zh"
directory.mkdir(parents=True, exist_ok=True)
for filename in ("taskmgr.ui", "page-processes.ui", "dlgkill.ui"):
    xml = subprocess.check_output(["gresource", "extract", "/usr/bin/taskmgr", "/uk/oddmatics/wintc/taskmgr/" + filename])
    root = ET.fromstring(xml)
    if filename == "taskmgr.ui":
        mnemonics = {"%CTL_FILEMENU%": "_File", "New Task (Run...)": "_New Task (Run...)",
                     "Exit Task Manager": "E_xit Task Manager"}
        for item in root.iter("object"):
            label = item.find("property[@name='label']")
            if label is None or label.text not in mnemonics:
                continue
            if label.text == "New Task (Run...)":
                item.find("property[@name='action-name']").text = "win.new-task"
            label.text = mnemonics[label.text]
            underline = item.find("property[@name='use-underline']")
            if underline is None:
                underline = ET.Element("property", name="use-underline")
                underline.tail = "\n            "
                item.insert(list(item).index(label), underline)
            underline.text = "True"
        english = directory.with_name("taskmgr-en")
        english.mkdir(exist_ok=True)
        ET.ElementTree(root).write(english / filename, encoding="UTF-8")
    for field in root.iter("property"):
        if field.text in labels:
            field.text = labels[field.text]
            field.set("translatable", "no")
        elif field.text and field.text.startswith("WARNING: Terminating a process"):
            field.text = "强行结束进程可能导致数据丢失或系统不稳定。进程将无法保存数据。确实要结束该进程吗？"
            field.set("translatable", "no")
    ET.ElementTree(root).write(directory / filename, encoding="UTF-8")
