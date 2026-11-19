#!/usr/bin/python3
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

host = "/usr/lib/myime/MyIMEHost"
config = Path(os.getenv("XDG_CONFIG_HOME") or Path.home()/".config")/"myime/preferences.json"
data = Path(os.getenv("XDG_DATA_HOME") or Path.home()/".local/share")/"myime"
defaults = json.loads(subprocess.check_output([host, "defaults"]))
prefs = dict(defaults)
if config.is_file():
    prefs.update(json.loads(config.read_text()))
def save():
    config.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=config.parent, delete=False) as f:
        json.dump(prefs, f)
    os.replace(f.name, config)
win = Gtk.Window(title="MyIME 设置")
win.set_default_size(500, 560)
win.connect("destroy", Gtk.main_quit)
tabs = Gtk.Notebook()
win.add(tabs)
def page(title):
    item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)
    tabs.append_page(item, Gtk.Label(label=title))
    return item
def toggle(box, label, value, change):
    widget = Gtk.CheckButton(label=label)
    widget.set_active(value)
    widget.connect("toggled", lambda w: (change(w.get_active()), save()))
    box.pack_start(widget, False, False, 0)
def number(box, label, key, low, high, step):
    row = Gtk.Box(spacing=10)
    row.pack_start(Gtk.Label(label=label), False, False, 0)
    spin = Gtk.SpinButton.new_with_range(low, high, step)
    spin.set_value(prefs[key])
    spin.connect("value-changed", lambda w: (prefs.update({key:w.get_value_as_int() if step==1 else w.get_value()}), save()))
    row.pack_end(spin, False, False, 0)
    box.pack_start(row, False, False, 0)
main = page("候选")
number(main, "每页候选数", "pageSize", 3, 9, 1)
for key,label in [("outputTraditional","输出繁体"),("showEnglishGloss","显示英文释义")]:
    toggle(main,label,prefs[key],lambda value,k=key:prefs.update({k:value}))
toggle(main,"纵向排列",prefs["orientation"]=="vertical",lambda v:prefs.update(orientation="vertical" if v else "horizontal"))
weights = page("候选排序")
for k,label in [("frequencyWeight","系统词频"),("userWeight","个人词频"),("lengthWeight","词长"),
                ("contextWeight","上下文"),("fuzzyPenalty","模糊音惩罚"),("partialPenalty","简拼惩罚")]:
    number(weights,label,k,0,5,0.01)
fuzzy = page("模糊音")
for key,label in zip(["zZh","cCh","sSh","nL","fH","rL","anAng","enEng","inIng","ianIang","uanUang"],
                     ["z / zh","c / ch","s / sh","n / l","f / h","r / l","an / ang","en / eng","in / ing","ian / iang","uan / uang"]):
    toggle(fuzzy,label,prefs["fuzzy"][key],lambda v,k=key:prefs["fuzzy"].update({k:v}))
sources = page("词库")
for bit,label in [(0,"雾凇拼音"),(2,"中文维基"),(3,"景行词库"),(5,"搜狗分类整理"),(10,"清华开放中文词库"),(14,"青简词库与语料短语")]:
    toggle(sources,label,not prefs["disabledSourceMask"] & (1<<bit),
           lambda v,b=bit:prefs.update(disabledSourceMask=prefs["disabledSourceMask"] & ~(1<<b) if v else prefs["disabledSourceMask"] | (1<<b)))
status = Gtk.Label(wrap=True)
def manage(button, op):
    try:
        if op=="clear-learning":
            dlg=Gtk.MessageDialog(transient_for=win,modal=True,message_type=Gtk.MessageType.QUESTION,
                                  buttons=Gtk.ButtonsType.YES_NO,text="清空本机的 MyIME 学习记录？")
            result=dlg.run()
            dlg.destroy()
            if result!=Gtk.ResponseType.YES: return
            subprocess.run([host,op],check=True)
        else:
            dlg=Gtk.FileChooserDialog(title=button.get_label(),transient_for=win,
                 action=Gtk.FileChooserAction.SAVE if op=="export" else Gtk.FileChooserAction.OPEN)
            dlg.add_buttons("取消",Gtk.ResponseType.CANCEL,"确定",Gtk.ResponseType.OK)
            dlg.set_do_overwrite_confirmation(True)
            result=dlg.run()
            path=dlg.get_filename()
            dlg.destroy()
            if result!=Gtk.ResponseType.OK: return
            if op=="replace":
                data.mkdir(mode=0o700,parents=True,exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=data) as f:
                    with open(path,"rb") as source: shutil.copyfileobj(source,f)
                    f.flush()
                    subprocess.run([host,"validate"],env=dict(os.environ,MYIME_SYSTEM_DATABASE=f.name),check=True)
                    os.link(f.name, f.name+".valid")
                    os.replace(f.name+".valid", data/"system.sqlite")
            else:
                result=subprocess.run([host,op,path],check=True,capture_output=True,text=True)
                if result.stdout: status.set_text(result.stdout.strip())
        if op!="export": (data/"reload").touch()
        if op!="import": status.set_text("已完成")
    except (OSError,subprocess.SubprocessError) as exc: status.set_text(str(exc))
for op,label in [("import","导入用户词组 TSV"),("export","导出用户词组 TSV"),("replace","校验并替换系统词库"),("clear-learning","清空学习记录")]:
    btn=Gtk.Button(label=label)
    btn.connect("clicked",manage,op)
    sources.pack_start(btn,False,False,0)
sources.pack_start(status,False,False,0)
win.show_all()
Gtk.main()
