import cups
from gi.repository import GLib


def tr(zh, en):
    return zh if GLib.get_language_names()[0].startswith("zh") else en


def submit_test_page(name):
    try:
        job = cups.Connection().printFile(name, "/usr/share/cups/data/default-testpage.pdf",
                                          tr("测试页", "Test page"), {})
        return tr("已提交测试页", "Test page submitted") + f" · {name} #{job}"
    except (RuntimeError, OSError) as exc:
        return tr("测试页提交失败", "Could not submit test page") + " · " + str(exc)
