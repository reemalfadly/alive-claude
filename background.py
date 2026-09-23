"""
تشغيل «كلود حي» بالخلفيه — يشتغل مع الجهاز ويضل شغّالاً.

    python background.py --on      يشتغل تلقائياً مع كل إقلاع
    python background.py --off     يوقف التشغيل التلقائي
    python background.py           يقول لك الحاله الحاليه
    python background.py --now     يشغّله الحين بلا تسجيل تلقائي

وش يشتغل بالخلفيه:
    الرفيق العايم (`companion.py`) — أيقونة صغيره على سطح المكتب،
    تصغى لكلمة التنبيه، وتشمّ المشاكل وتنبّهك قبل ما تنكسر.

كل نظام وطريقته — ما فيه خدمه ولا صلاحيات إداريه، وكلها قابله للتراجع:
    ويندوز ← اختصار بمجلد Startup
    ماك    ← LaunchAgent بـ~/Library/LaunchAgents
    لينكس  ← ملف .desktop بـ~/.config/autostart

ما ينزّل شيئاً ولا يعدّل أي إعداد نظام. ملف واحد بمجلدك، تمسحه بـ`--off`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "companion.py"
LABEL = "alive-claude"

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


def _py() -> str:
    """مفسّر بايثون بلا نافذة كونسول على ويندوز."""
    if IS_WIN:
        w = Path(sys.executable).with_name("pythonw.exe")
        if w.exists():
            return str(w)
    return sys.executable


# ══════════════════════════════════════════════════════════════════
#                          ويندوز
# ══════════════════════════════════════════════════════════════════
def _win_startup() -> Path:
    return (Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows"
            / "Start Menu" / "Programs" / "Startup" / f"{LABEL}.bat")


def _win_on() -> str:
    f = _win_startup()
    f.parent.mkdir(parents=True, exist_ok=True)
    # `start ""` يطلق العمليه ويرجع فوراً، فالإقلاع ما ينتظرها
    f.write_text(
        "@echo off\r\n"
        f'cd /d "{HERE}"\r\n'
        f'start "" "{_py()}" "{TARGET}"\r\n',
        encoding="utf-8")
    return str(f)


def _win_off() -> bool:
    f = _win_startup()
    if f.exists():
        f.unlink()
        return True
    return False


def _win_is_on() -> bool:
    return _win_startup().exists()


# ══════════════════════════════════════════════════════════════════
#                            ماك
# ══════════════════════════════════════════════════════════════════
def _mac_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"com.{LABEL}.plist"


def _mac_on() -> str:
    f = _mac_plist()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{TARGET}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{HERE}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
''', encoding="utf-8")
    # `load` يخلّيه يشتغل الحين بلا ما تعيد تشغيل الجهاز
    subprocess.run(["launchctl", "load", "-w", str(f)],
                   capture_output=True, timeout=20)
    return str(f)


def _mac_off() -> bool:
    f = _mac_plist()
    if not f.exists():
        return False
    subprocess.run(["launchctl", "unload", "-w", str(f)],
                   capture_output=True, timeout=20)
    f.unlink()
    return True


def _mac_is_on() -> bool:
    return _mac_plist().exists()


# ══════════════════════════════════════════════════════════════════
#                           لينكس
# ══════════════════════════════════════════════════════════════════
def _linux_desktop() -> Path:
    return Path.home() / ".config" / "autostart" / f"{LABEL}.desktop"


def _linux_on() -> str:
    f = _linux_desktop()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f'''[Desktop Entry]
Type=Application
Name=Alive Claude
Comment=كلود حي — حواس على جهازك
Exec={sys.executable} "{TARGET}"
Path={HERE}
Terminal=false
X-GNOME-Autostart-enabled=true
''', encoding="utf-8")
    return str(f)


def _linux_off() -> bool:
    f = _linux_desktop()
    if f.exists():
        f.unlink()
        return True
    return False


def _linux_is_on() -> bool:
    return _linux_desktop().exists()


# ══════════════════════════════════════════════════════════════════
ON = _win_on if IS_WIN else (_mac_on if IS_MAC else _linux_on)
OFF = _win_off if IS_WIN else (_mac_off if IS_MAC else _linux_off)
IS_ON = _win_is_on if IS_WIN else (_mac_is_on if IS_MAC else _linux_is_on)
OS_NAME = "ويندوز" if IS_WIN else ("ماك" if IS_MAC else "لينكس")


def run_now() -> str:
    """يشغّل الرفيق الحين بلا انتظار إقلاع."""
    try:
        kw = {}
        if IS_WIN:
            kw["creationflags"] = 0x00000008     # DETACHED_PROCESS
        else:
            kw["start_new_session"] = True
        subprocess.Popen([_py(), str(TARGET)], cwd=str(HERE), **kw)
        return "شغّلته."
    except Exception as e:
        return f"ما قدرت أشغّله: {e}"


def main() -> None:
    args = sys.argv[1:]
    print()
    print("  كلود حي — التشغيل بالخلفيه")
    print("  " + "─" * 50)

    if not TARGET.exists():
        print(f"  ما لقيت {TARGET.name} — تأكد إنك بمجلد المهاره.")
        print()
        return

    if "--on" in args:
        where = ON()
        print(f"  ✅ بيشتغل تلقائياً مع كل إقلاع ({OS_NAME})")
        print(f"     {where}")
        print()
        print("  " + run_now())
    elif "--off" in args:
        print("  ✅ وقّفت التشغيل التلقائي" if OFF()
              else "  ⬜ ما كان مفعّلاً أصلاً")
    elif "--now" in args:
        print("  " + run_now())
    else:
        print(f"  النظام        : {OS_NAME}")
        print(f"  تلقائي بالإقلاع: {'مفعّل ✅' if IS_ON() else 'مو مفعّل ⬜'}")
        print()
        print("  --on   يشتغل مع كل إقلاع")
        print("  --off  يوقفه")
        print("  --now  يشغّله الحين بس")
    print()


if __name__ == "__main__":
    main()
