"""
حاسة الشمّ — يحسّ بالمشكله قبل ما تنكسر.

    python smell.py            فحص فوري
    python smell.py --watch    مراقبه مستمره

الفرق عن باقي الحواس:
  الباقيات ترد لما تسأل. **هذي تنبّهك من نفسها** — تشمّ المشكله وهي
  جايه وتقول لك قبل ما تتعطّل.

وش تشمّ:
  · القرص يمتلئ       · الذاكره تتسرّب      · برنامج علّق
  · تصدير ناقص         · النت وقف            · كرت الشاشه مخنوق

المبدأ: **ما تزعجك**.
  · نفس الإنذار ما يتكرر قبل ٤٥ دقيقه
  · البرنامج المشغول ما يُعتبر معلّقاً إلا لو تكرر مرتين
  · كل شي محلي — قراءات من نظام التشغيل مباشره
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import ROOT, config, ensure, line, user_name  # noqa: E402

REPORT = ROOT / "alerts.md"

CHECK_EVERY = 90.0
QUIET_AFTER = 45 * 60

DISK_WARN_GB = 25
DISK_BAD_GB = 10
MEM_WARN = 88
GPU_WARN = 92
HOG_GB = 10
TINY_EXPORT_MB = 8
GAP_SECONDS = 900

_last: dict[str, float] = {}
_frozen_seen: dict[str, int] = {}
FROZEN_STREAK = 2


# ══════════ الفحوصات ══════════
def _disk():
    import shutil

    for drive in ("D:\\", "C:\\"):
        try:
            free = shutil.disk_usage(drive).free / 2**30
        except OSError:
            continue
        if free < DISK_BAD_GB:
            return (f"disk-{drive}",
                    f"القرص {drive[0]} باقي {free:.0f} قيقا بس — "
                    "التصدير والحفظ بيوقفون.")
        if free < DISK_WARN_GB:
            return (f"disk-{drive}",
                    f"القرص {drive[0]} باقي {free:.0f} قيقا.")
    return None


def _memory():
    import psutil

    mem = psutil.virtual_memory()
    if mem.percent < MEM_WARN:
        return None
    try:
        top = max(psutil.process_iter(["name", "memory_info"]),
                  key=lambda p: (p.info["memory_info"].rss
                                 if p.info.get("memory_info") else 0))
        gb = top.info["memory_info"].rss / 2**30
        name = (top.info["name"] or "برنامج").replace(".exe", "")
        if gb >= HOG_GB:
            return ("mem-hog",
                    f"{name} أكل {gb:.0f} قيقا والجهاز صار "
                    f"{mem.percent:.0f} بالميه.")
    except Exception:
        pass
    return ("mem", f"الذاكره {mem.percent:.0f} بالميه — الجهاز بيثقل.")


def _gpu():
    import subprocess

    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout.strip().splitlines()[0]
        used, total = (int(x.strip()) for x in out.split(","))
        pct = used / total * 100
        if pct >= GPU_WARN:
            return ("gpu", f"ذاكرة كرت الشاشه {pct:.0f} بالميه.")
    except Exception:
        pass
    return None


def _frozen():
    """نافذه ما تستجيب. برامج المونتاج تنشغل دقايق وهي بخير،
    فما ننبّه إلا لو تكرر مرتين."""
    import ctypes
    import ctypes.wintypes as wt

    try:
        u = ctypes.windll.user32
        proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        stuck: list[str] = []

        def cb(hwnd, _l):
            if not u.IsWindowVisible(hwnd):
                return True
            n = u.GetWindowTextLengthW(hwnd)
            if n < 3:
                return True
            result = wt.DWORD()
            if not u.SendMessageTimeoutW(hwnd, 0, 0, 0, 2, 1200,
                                         ctypes.byref(result)):
                b = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(hwnd, b, n + 1)
                stuck.append(b.value[:45])
            return True

        u.EnumWindows(proc(cb), 0)

        for title in list(_frozen_seen):
            if title not in stuck:
                _frozen_seen.pop(title, None)

        for title in stuck:
            _frozen_seen[title] = _frozen_seen.get(title, 0) + 1
            if _frozen_seen[title] >= FROZEN_STREAK:
                return ("frozen", f"«{title}» ما يستجيب من فتره.")
    except Exception:
        pass
    return None


def _bad_export():
    """ملف جديد بمجلداتك المراقبه طلع حجمه صفر أو صغيراً جداً."""
    folders = [Path(f) for f in config().get("watch_folders", [])]
    for folder in folders:
        if not folder.is_dir():
            continue
        try:
            files = [p for p in folder.iterdir()
                     if p.is_file()
                     and p.suffix.lower() in {".mp4", ".mov", ".mkv", ".zip",
                                              ".pdf", ".psd"}]
            if not files:
                continue
            newest = max(files, key=lambda p: p.stat().st_mtime)
            if time.time() - newest.stat().st_mtime > GAP_SECONDS:
                continue
            mb = newest.stat().st_size / 2**20
            if mb < 0.05:
                return ("export-empty", f"«{newest.name}» حجمه صفر.")
            if mb < TINY_EXPORT_MB and newest.suffix.lower() in {".mp4", ".mov", ".mkv"}:
                return ("export-tiny",
                        f"«{newest.name}» طلع {mb:.0f} ميقا بس — "
                        "يمكن التصدير انقطع.")
        except OSError:
            continue
    return None


def _network():
    import socket

    try:
        socket.setdefaulttimeout(4)
        socket.create_connection(("1.1.1.1", 53)).close()
        return None
    except OSError:
        return ("net", "انقطع النت.")


CHECKS = (_disk, _memory, _gpu, _frozen, _bad_export, _network)


# ══════════ الشمّ ══════════
def sniff(force: bool = False) -> list[str]:
    now = time.time()
    fresh = []
    for check in CHECKS:
        try:
            hit = check()
        except Exception:
            continue
        if not hit:
            continue
        key, message = hit
        if not force and now - _last.get(key, 0) < QUIET_AFTER:
            continue
        _last[key] = now
        fresh.append(message)
        _log(message)
    return fresh


def _log(message: str) -> None:
    try:
        if not REPORT.exists():
            REPORT.write_text("# تنبيهات كلود\n\n", encoding="utf-8")
        with REPORT.open("a", encoding="utf-8") as f:
            f.write(f"- **{datetime.now():%Y-%m-%d %H:%M}** — {message}\n")
    except OSError:
        pass


def main() -> None:
    if not ensure("psutil"):
        return
    watch = "--watch" in sys.argv
    print()
    print("  حاسة الشمّ" + ("  (مراقبه مستمره)" if watch else ""))
    line("═")

    alerts = sniff(force=True)
    if alerts:
        for a in alerts:
            print(f"  ⚠ {a}")
    else:
        print(f"  ✅ كل شي تمام يا {user_name()} — ما أشمّ أي مشكله.")

    if not watch:
        print()
        return

    print(f"\n  أراقب كل {CHECK_EVERY:.0f} ثانيه. (Ctrl+C يوقف)\n")
    try:
        while True:
            time.sleep(CHECK_EVERY)
            for a in sniff():
                print(f"  [{datetime.now():%H:%M}] ⚠ {a}")
    except KeyboardInterrupt:
        print("\n  وقفت.\n")


if __name__ == "__main__":
    main()
