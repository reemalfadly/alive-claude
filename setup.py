"""
إعداد «كلود حي» — يسأل عن اسمك ومفتاحك ويجهّز كل شي.

شغّله مره وحده:
    python setup.py

ما يرسل أي شي لأي مكان. كل الإعدادات تنحفظ بملف `config.json` عندك.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"

REQUIRED = [
    ("requests", "requests"),
    ("numpy", "numpy"),
    ("Pillow", "PIL"),
    ("mss", "mss"),
    ("sounddevice", "sounddevice"),
    ("soundcard", "soundcard"),        # التقاط مخرَج الجهاز — الثلاثه
    ("psutil", "psutil"),
    ("python-dotenv", "dotenv"),
]

OPTIONAL = [
    ("faster-whisper", "faster_whisper", "تفريغ الصوت محلياً (يحتاج تنزيل ~١ قيقا)"),
]

DEFAULTS = {
    "name": "",
    "language": "ar",
    "wake_phrase": "كلود اسمعني",
    "voice": "Puck",
    "gemini_key": "",
    "watch_folders": [],
    "privacy": {
        "record_before_wake": False,
        "save_screenshots": False,
        "read_clipboard": True,
    },
}


def _line(ch: str = "─", n: int = 54) -> None:
    print("  " + ch * n)


def load() -> dict:
    if CONFIG.exists():
        try:
            data = json.loads(CONFIG.read_text(encoding="utf-8"))
            merged = dict(DEFAULTS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                      encoding="utf-8")


def check_packages() -> list[str]:
    missing = []
    for pip_name, import_name in REQUIRED:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    return missing


def install(packages: list[str]) -> bool:
    print(f"\n  أنزّل {len(packages)} مكتبه…")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *packages],
                       check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def main() -> None:
    print()
    print("  كلود حي — الإعداد")
    _line("═")
    print("""
  هذي المهاره تعطي كلود كود حواس على جهازك:
  يشوف شاشتك · يسمع اللي تشغّله · يسمعك · يشمّ المشاكل · يتحكّم بالنوافذ

  كل شي محلي عدا نداءات البصر والصوت الطبيعي (Google AI Studio المجاني).
""")

    cfg = load()

    # ── ١) الاسم ──
    _line()
    print("  ١) وش أناديك؟")
    current = cfg.get("name", "")
    prompt = f"     [{current}] " if current else "     "
    name = input(prompt).strip()
    if name:
        cfg["name"] = name
    elif not current:
        print("     تمام، بناديك «صديقي» لين تقول لي اسمك.")
        cfg["name"] = "صديقي"
    print(f"     ✅ {cfg['name']}")

    # ── ٢) المفتاح ──
    print()
    _line()
    print("  ٢) مفتاح Google AI Studio (مجاني)")
    print("     من: https://aistudio.google.com/apikey")
    print("     بلا مفتاح: البصر والصوت الطبيعي يتعطّلون، والباقي يشتغل.")
    has = bool(cfg.get("gemini_key"))
    key = input(f"     [{'محفوظ' if has else 'فاضي'}] ").strip()
    if key:
        cfg["gemini_key"] = key
        print("     ✅ انحفظ")
    elif has:
        print("     ✅ نستخدم المحفوظ")
    else:
        print("     ⬜ بلا مفتاح — تقدر تضيفه بعدين")

    # ── ٣) كلمة التنبيه ──
    print()
    _line()
    print("  ٣) وش تقول عشان أسمعك؟")
    wake = input(f"     [{cfg['wake_phrase']}] ").strip()
    if wake:
        cfg["wake_phrase"] = wake
    print(f"     ✅ «{cfg['wake_phrase']}»")

    # ── ٤) مجلدات المراقبه ──
    print()
    _line()
    print("  ٤) مجلدات تبيني أراقبها؟ (اختياري — افصل بفاصله)")
    print("     مثال: D:\\Videos, C:\\Users\\me\\Downloads")
    folders = input("     ").strip()
    if folders:
        cfg["watch_folders"] = [f.strip() for f in folders.split(",") if f.strip()]
        print(f"     ✅ {len(cfg['watch_folders'])} مجلد")

    save(cfg)

    # ── ٥) المكتبات ──
    print()
    _line()
    print("  ٥) المكتبات")
    missing = check_packages()
    if not missing:
        print("     ✅ كلها موجوده")
    else:
        print(f"     ناقص: {', '.join(missing)}")
        # الافتراضي «نعم»: اللي ينزّل المهاره يبيها تشتغل، مو يبي سؤالاً.
        ans = input("     أنزّلها؟ [Y/n] ").strip().lower()
        if ans in ("", "y", "yes", "ن", "نعم"):
            print("     ✅ خلصت" if install(missing) else "     ❌ فشل — نزّلها يدوياً")
        else:
            print("     ⬜ تخطّيت — بعض الحواس بتتعطّل")

    print()
    for pip_name, import_name, why in OPTIONAL:
        try:
            __import__(import_name)
        except ImportError:
            print(f"     ⬜ {pip_name} — {why}")
            print(f"        pip install {pip_name}")

    # ── خلصنا ──
    print()
    _line("═")
    print(f"""
  جاهز يا {cfg['name']}!

  جرّب:
     python senses/see.py              يشوف شاشتك
     python senses/smell.py            يفحص جهازك
     python companion.py               الرفيق العايم

  وبكلود كود قل: «شوف شاشتي» أو «شم لي»
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  وقفت الإعداد.")
