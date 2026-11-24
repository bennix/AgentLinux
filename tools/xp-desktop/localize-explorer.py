"""Generate a Chinese GResource overlay from the installed Explorer version."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

labels = dict(line.split("|") for line in """%CTL_FILEMENU%|文件
%CTL_EDITMENU%|编辑
%CTL_VIEWMENU%|查看
%CTL_TOOLSMENU%|工具
%CTL_HELPMENU%|帮助
%CTL_COPY%|复制
%CTL_CUT%|剪切
%CTL_PASTE%|粘贴
%CTL_UNDO%|撤销
%CTL_GOTO%|转到
%PUNC_MOREINPUT%%CTL_CUSTOMIZE%|自定义…
Search Companion|搜索助理
Paste Shortcut|粘贴快捷方式
Copy To Folder...|复制到文件夹…
Move To Folder...|移动到文件夹…
Select All|全部选定
Invert Selection|反向选择
Toolbars|工具栏
Standard Buttons|标准按钮
Address Bar|地址栏
Links|链接
Lock the Toolbars|锁定工具栏
Status Bar|状态栏
Explorer Bar|浏览器栏
Thumbnails|缩略图
Tiles|平铺
Icons|图标
List|列表
Details|详细信息
Arrange Icons by|排列图标
Name|名称
Size|大小
Type|类型
Modified|修改时间
Show in Groups|按组排列
Auto Arrange|自动排列
Align to Grid|对齐到网格
Choose Details...|选择详细信息…
Refresh|刷新
Favorites|收藏夹
Add to Favorites...|添加到收藏夹…
Organize Favorites...|整理收藏夹…
Map Network Drive...|映射网络驱动器…
Disconnect Network Drive...|断开网络驱动器…
Synchronize...|同步…
Folder Options...|文件夹选项…
Help and Support Center|帮助和支持中心
Is this copy of Windows legal?|此 Windows 副本是否合法？
About Windows|关于 Windows
Folders|文件夹
Address|地址
Go|转到""".splitlines())
dest = Path.home() / ".local/share/agentlinux-xp/explorer-zh"
dest.mkdir(parents=True, exist_ok=True)
binary = "/usr/bin/explorer"
for name in subprocess.check_output(["gresource", "list", binary], text=True).splitlines():
    if not name.endswith(".ui"):
        continue
    root = ET.fromstring(subprocess.check_output(["gresource", "extract", binary, name]))
    changed = False
    for prop in root.iter("property"):
        if prop.get("name") in {"label", "title", "tooltip-text"} and prop.text in labels:
            prop.text = labels[prop.text]
            prop.set("translatable", "no")
            changed = True
    if changed:
        ET.ElementTree(root).write(dest / Path(name).name, encoding="UTF-8")
