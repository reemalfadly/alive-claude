"""
تنزيل «كلود حي» بأمر واحد.

    python install.py

وش يسوي بالترتيب:
  ١. ينسخ المهاره لـ`~/.claude/skills/alive-claude/`  (مكان مهارات كلود كود)
  ٢. ينزّل المكتبات المطلوبه
  ٣. يشغّل الإعداد — يسألك عن اسمك ومفتاحك

لو المهاره أصلاً بمكانها، يتخطّى النسخ ويكمّل على الإعداد.
ما يرسل أي شي لأي مكان. الإعدادات تنحفظ عندك بـ`config.json`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = Path.home() / ".claude" / "skills"
DEST = SKILLS / "alive-claude"

# اللي ننسخه. نتجاهل الكاش والإعدادات الشخصيه ومجلد git.
SKIP = {"__pycache__", ".git", ".github", "config.json", ".env",
        ".vision_ref.jpg", "docs"}

REQUIRED = ["requests", "numpy", "Pillow", "mss", "psutil", "python-dotenv"]
AUDIO = ["sounddevice", "soundcard"]        # الثلاثه يدعمونها

# أدوات النظام اللي ما تنزّل بـpip
SYSTEM_TOOLS = {
    "linux": ("التحكّم بالنوافذ يحتاج أدوات من توزيعتك:",
              "sudo apt install xdotool wmctrl     (أو dnf/pacman)"),
    "darwin": ("ماك يطلب إذناً أول مره تتحكّم بالنوافذ:",
               "System Settings ← Privacy & Security ← Accessibility"),
    "win32": ("", ""),
}


def line(ch: str = "─", n: int = 54) -> None:
    print("  " + ch * n)


def copy_skill() -> Path:
    """ينسخ المهاره لمجلد مهارات كلود كود."""
    if HERE.resolve() == DEST.resolve():
        print("  ✅ المهاره أصلاً بمكانها الصح")
        return DEST

    SKILLS.mkdir(parents=True, exist_ok=True)

    if DEST.exists():
        # نحافظ على إعداداته القديمه — الاسم والمفتاح ما يضيعون بالتحديث
        keep = DEST / "config.json"
        saved = keep.read_bytes() if keep.exists() else None
        shutil.rmtree(DEST, ignore_errors=True)
        DEST.mkdir(parents=True, exist_ok=True)
        if saved:
            (DEST / "config.json").write_bytes(saved)
            print("  ↻ حدّثت المهاره وحافظت على إعداداتك")
    else:
        DEST.mkdir(parents=True, exist_ok=True)

    for item in HERE.iterdir():
        if item.name in SKIP:
            continue
        target = DEST / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(item, target)

    print("  ✅ نسخت المهاره إلى:")
    print("     " + str(DEST))
    return DEST


def install_packages() -> None:
    # الصوت يشتغل بالثلاثه: WASAPI بويندوز، CoreAudio بماك،
    # PulseAudio بلينكس. ما نستثني أي نظام.
    packages = list(REQUIRED) + AUDIO

    print()
    print("  أنزّل " + str(len(packages)) + " مكتبه…")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *packages],
                       check=True, timeout=1200)
        print("  ✅ خلصت")
    except Exception:
        print("  ⚠ ما قدرت أنزّلها كلها. شغّل بنفسك:")
        print("     " + sys.executable + " -m pip install " + " ".join(packages))


HELP = """
  كلود حي — التنزيل

    python install.py          ينسخ المهاره + ينزّل المكتبات + يسأل عن اسمك
    python install.py --auto   نفس الشي **بلا أي أسئله** (لكلود كود)
    python install.py --help   هذا الشرح

  ينسخ إلى: ~/.claude/skills/alive-claude/
  يشتغل على ويندوز وماك ولينكس.
"""


def _stamp_config(dest: Path) -> None:
    """يكتب قالب إعدادات فاضياً — بلا اسم، عشان كلود يسأل عنه.

    ما ندوس على إعداد موجود: لو المستخدم محدّث المهاره، اسمه ومفتاحه
    يضلّون مكانهم.
    """
    import json

    f = dest / "config.json"
    if f.exists():
        return
    f.write_text(json.dumps({
        "name": "",
        "language": "ar",
        "wake_phrase": "كلود اسمعني",
        "voice": "Puck",
        "gemini_key": "",
        "watch_folders": [],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(HELP)
        return

    print()
    print("  كلود حي — التنزيل")
    line("═")
    print()

    if sys.version_info < (3, 10):
        print("  ⚠ تحتاج بايثون ٣.١٠ أو أحدث. عندك " +
              ".".join(str(x) for x in sys.version_info[:3]))
        return

    auto = "--auto" in sys.argv

    dest = copy_skill()
    install_packages()

    head, cmd = SYSTEM_TOOLS.get(sys.platform, SYSTEM_TOOLS["linux"])
    if head:
        print()
        print("  " + head)
        print("     " + cmd)

    if auto:
        # كلود كود يشغّلها بلا طرفيه تفاعليه — `input()` هني يرمي EOFError.
        # فنتخطّى الإعداد، وكلود يسأل المستخدم بالمحادثه ويكتب config.json.
        print()
        line()
        print("  ✅ نزّلت المهاره. باقي الاسم والمفتاح.")
        print("     " + str(dest / "config.json"))
        _stamp_config(dest)
    else:
        print()
        line()
        print("  الإعداد — بيسألك عن اسمك ومفتاحك")
        line()
        try:
            subprocess.run([sys.executable, str(dest / "setup.py")], check=False)
        except KeyboardInterrupt:
            print()
            print("  وقفت الإعداد. تقدر تشغّله بعدين:")
            print("     python " + str(dest / "setup.py"))
            return

    print()
    line("═")
    print()
    print("  النظام: " + {"win32": "ويندوز", "darwin": "ماك"}
          .get(sys.platform, "لينكس"))
    print()
    print("  خلصنا. افتح كلود كود وقل:")
    print()
    print("     «شوف شاشتي»       ← يلتقط الشاشه ويوصفها")
    print("     «شم لي»           ← يفحص جهازك")
    print("     «وش مشغّل الحين»  ← يسمع مخرَج جهازك")
    print()
    print("  ولو ما لقى كلود المهاره، سكّر الجلسه وافتح وحده جديده.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("  وقفت التنزيل.")
