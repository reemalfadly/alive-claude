"""
طبقة نظام التشغيل — المكان الوحيد اللي يعرف إنك على ويندوز أو ماك أو لينكس.

ليش ملف لحاله:
    أول نسخه كانت تنادي `ctypes.windll` من جوّه كل حاسه. النتيجه إن
    المهاره **تنهار بالاستيراد** على ماك — قبل لا يوصل المستخدم لأي
    رساله مفيده، لأن `ctypes.windll` نفسه ما هو موجود إلا بويندوز.

    الحين كل نداء نظام يمرّ من هني. الحاسه تقول «بدّل لهالنافذه» وهذا
    الملف يقرر: ctypes بويندوز، AppleScript بماك، xdotool بلينكس.
    ولو ما فيه طريقه، يرجّع `None` — و`None` تعني **«ما أقدر»** مو خطأ.

الفرق بين الثلاثه:
    ويندوز  ← واجهة user32 مباشره، ما تحتاج شي منزّل
    ماك     ← osascript (جاي مع النظام)، بس **يحتاج إذن Accessibility**
    لينكس   ← xdotool و wmctrl، لازم تنزّلهم بنفسك

كل داله ترجّع `None` لو النظام ما يدعمها، عشان الحاسه تقول للمستخدم
جمله مفهومه بدل ما تطلّع تتبّعاً.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys

logger = logging.getLogger("alive.platform")

# ══════════ التعرّف على النظام ══════════
if sys.platform == "win32":
    OS = "windows"
elif sys.platform == "darwin":
    OS = "macos"
else:
    OS = "linux"

IS_WIN = OS == "windows"
IS_MAC = OS == "macos"
IS_LINUX = OS == "linux"

OS_NAME = {"windows": "ويندوز", "macos": "ماك", "linux": "لينكس"}[OS]

# مفتاح الاختصارات الأساسي — ماك يستخدم cmd واللي غيره ctrl.
# هذا يخلّي «احفظ» تشتغل بالثلاثه بلا ما تكتب الاختصار مرتين.
MOD = "cmd" if IS_MAC else "ctrl"


def _run(cmd: list[str], timeout: float = 8.0) -> str | None:
    """ينفّذ أمراً ويرجّع مخرَجه، أو None لو فشل."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8",
                           errors="replace")
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception as e:
        logger.debug("فشل %s: %s", cmd[0], e)
        return None


def _osa(script: str) -> str | None:
    """ينفّذ AppleScript. ماك فقط."""
    return _run(["osascript", "-e", script], timeout=12.0)


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def missing_tools() -> list[str]:
    """وش ناقص عشان التحكّم بالنوافذ يشتغل على هالنظام."""
    if IS_LINUX:
        return [t for t in ("xdotool", "wmctrl") if not have(t)]
    if IS_MAC:
        return [] if have("osascript") else ["osascript"]
    return []


def setup_hint() -> str:
    """جمله تقول للمستخدم وش ينقصه — بلغته مو بتتبّع."""
    miss = missing_tools()
    if not miss:
        return ""
    if IS_LINUX:
        return ("التحكّم بالنوافذ يحتاج: " + " و".join(miss) + "\n"
                "     sudo apt install " + " ".join(miss) +
                "   (أو dnf/pacman حسب توزيعتك)")
    return "ناقص: " + " و".join(miss)


MAC_PERMISSION = (
    "ماك يطلب إذناً أول مره: System Settings ← Privacy & Security ←\n"
    "     Accessibility ← فعّل الترمنال (أو البرنامج اللي تشغّل منه)."
)


# ══════════════════════════════════════════════════════════════════
#                          النوافذ
# ══════════════════════════════════════════════════════════════════
def active_window() -> dict | None:
    """النافذه الشغّاله: {left, top, width, height, title} أو None."""
    if IS_WIN:
        return _win_active()
    if IS_MAC:
        return _mac_active()
    return _linux_active()


def list_windows(contains: str = "") -> list[str]:
    """عناوين النوافذ المفتوحه."""
    if IS_WIN:
        titles = [t for _, t in _win_enum(contains)]
    elif IS_MAC:
        titles = _mac_list()
    else:
        titles = _linux_list()

    want = (contains or "").lower()
    return [t for t in titles if t and (not want or want in t.lower())]


def focus(name: str) -> str | None:
    """يبدّل للنافذه — يرجّع عنوانها، أو None لو ما قدر."""
    if IS_WIN:
        return _win_focus(name)
    if IS_MAC:
        return _mac_focus(name)
    return _linux_focus(name)


def window_action(action: str, name: str = "") -> bool | None:
    """كبّر · صغّر · سكّر · ارجع. True نجح، False ما لقى، None ما يدعم."""
    if IS_WIN:
        return _win_action(action, name)
    if IS_MAC:
        return _mac_action(action, name)
    return _linux_action(action, name)


# ══════════════════════════════════════════════════════════════════
#                       لوحة المفاتيح
# ══════════════════════════════════════════════════════════════════
def tap(combo: str) -> bool | None:
    """يضغط اختصاراً مثل `ctrl+s`. على ماك `ctrl` تنقلب `cmd` تلقائياً."""
    if IS_WIN:
        return _win_tap(combo)
    if IS_MAC:
        return _mac_tap(combo)
    return _linux_tap(combo)


def write(text: str) -> bool | None:
    """يكتب نصاً بمكان المؤشر — يدعم العربي."""
    if IS_WIN:
        return _win_write(text)
    if IS_MAC:
        return _mac_write(text)
    return _linux_write(text)


# ══════════════════════════════════════════════════════════════════
#                          ويندوز
# ══════════════════════════════════════════════════════════════════
def _win_u():
    import ctypes

    return ctypes.windll.user32


def _win_title(hwnd: int) -> str:
    import ctypes

    u = _win_u()
    n = u.GetWindowTextLengthW(hwnd)
    if not n:
        return ""
    b = ctypes.create_unicode_buffer(n + 1)
    u.GetWindowTextW(hwnd, b, n + 1)
    return b.value


def _win_enum(contains: str = "") -> list[tuple[int, str]]:
    import ctypes
    import ctypes.wintypes as wt

    u = _win_u()
    want = (contains or "").lower()
    found: list[tuple[int, str]] = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, _l):
        if u.IsWindowVisible(hwnd):
            t = _win_title(hwnd)
            if t and (not want or want in t.lower()):
                found.append((hwnd, t))
        return True

    u.EnumWindows(proc(cb), 0)
    return found


def _win_active() -> dict | None:
    import ctypes
    import ctypes.wintypes as wt

    try:
        u = _win_u()
        hwnd = u.GetForegroundWindow()
        if not hwnd:
            return None
        r = wt.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w < 120 or h < 120:
            return None
        return {"left": max(0, r.left), "top": max(0, r.top),
                "width": w, "height": h, "title": _win_title(hwnd)}
    except Exception:
        return None


def _win_focus(name: str) -> str | None:
    hits = _win_enum(name)
    if not hits:
        return None
    hwnd, title = hits[0]
    try:
        _win_u().ShowWindow(hwnd, 9)              # SW_RESTORE
        _win_u().SetForegroundWindow(hwnd)
        return title
    except Exception:
        return None


def _win_action(action: str, name: str = "") -> bool | None:
    u = _win_u()
    hits = _win_enum(name) if name else []
    if name and not hits:
        return False
    hwnd = hits[0][0] if hits else u.GetForegroundWindow()

    if action == "close":
        u.PostMessageW(hwnd, 0x0010, 0, 0)        # WM_CLOSE
        return True
    code = {"max": 3, "min": 6, "restore": 9}.get(action)
    if code is None:
        return False
    u.ShowWindow(hwnd, code)
    return True


_VK = {
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B, "cmd": 0x5B,
    "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
    "f11": 0x7A, "f12": 0x7B,
}
for _c in "abcdefghijklmnopqrstuvwxyz":
    _VK[_c] = ord(_c.upper())
for _d in "0123456789":
    _VK[_d] = ord(_d)

_KEYUP = 0x0002
_UNICODE = 0x0004


def _win_tap(combo: str) -> bool:
    import time

    parts = [p.strip().lower() for p in (combo or "").split("+") if p.strip()]
    codes = [_VK[p] for p in parts if p in _VK]
    if not codes or len(codes) != len(parts):
        return False

    u = _win_u()
    for c in codes[:-1]:
        u.keybd_event(c, 0, 0, 0)
    u.keybd_event(codes[-1], 0, 0, 0)
    time.sleep(0.012)
    u.keybd_event(codes[-1], 0, _KEYUP, 0)
    for c in reversed(codes[:-1]):
        u.keybd_event(c, 0, _KEYUP, 0)
    return True


def _win_write(text: str) -> bool:
    import time

    u = _win_u()
    for ch in text:
        code = ord(ch)
        u.keybd_event(0, code, _UNICODE, 0)
        u.keybd_event(0, code, _UNICODE | _KEYUP, 0)
        time.sleep(0.004)
    return True


# ══════════════════════════════════════════════════════════════════
#                           ماك
# ══════════════════════════════════════════════════════════════════
# نستخدم osascript لأنه جاي مع النظام. البديل (pyobjc) مكتبه ثقيله
# وتحتاج بناءً، وإحنا نبي المهاره تنزل بأمر واحد.
def _mac_active() -> dict | None:
    out = _osa('''
        tell application "System Events"
            set p to first application process whose frontmost is true
            try
                set w to first window of p
                set {x, y} to position of w
                set {ww, hh} to size of w
                set t to name of w
            on error
                return "none"
            end try
        end tell
        return (x as string) & "," & (y as string) & "," & ¬
               (ww as string) & "," & (hh as string) & "," & t
    ''')
    if not out or out == "none":
        return None
    try:
        parts = out.split(",", 4)
        x, y, w, h = (int(float(v)) for v in parts[:4])
        if w < 120 or h < 120:
            return None
        return {"left": max(0, x), "top": max(0, y), "width": w,
                "height": h, "title": parts[4] if len(parts) > 4 else ""}
    except Exception:
        return None


def _mac_list() -> list[str]:
    out = _osa('''
        set out to ""
        tell application "System Events"
            repeat with p in (every application process ¬
                              whose background only is false)
                repeat with w in (every window of p)
                    set out to out & (name of p) & " — " & (name of w) & linefeed
                end repeat
            end repeat
        end tell
        return out
    ''')
    if not out:
        # احتياط: أسماء البرامج بلا عناوين النوافذ (ما يحتاج إذناً كاملاً)
        out = _osa('tell application "System Events" to get name of '
                   '(every application process whose background only is false)')
        if not out:
            return []
        return [p.strip() for p in out.split(",") if p.strip()]
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _mac_focus(name: str) -> str | None:
    safe = (name or "").replace('"', "")
    # أول محاوله: اسم برنامج مطابق
    hit = _osa(f'''
        tell application "System Events"
            set ps to (every application process whose background only is false)
            repeat with p in ps
                if (name of p as string) contains "{safe}" then
                    set frontmost of p to true
                    return name of p
                end if
            end repeat
        end tell
        return "none"
    ''')
    if hit and hit != "none":
        return hit
    return None


def _mac_action(action: str, name: str = "") -> bool | None:
    if name and not _mac_focus(name):
        return False
    # ماك ما عنده «تكبير/تصغير» بنفس مفهوم ويندوز — نستخدم الاختصارات
    keys = {"close": "cmd+w", "min": "cmd+m", "max": "ctrl+cmd+f",
            "restore": "ctrl+cmd+f"}
    combo = keys.get(action)
    if not combo:
        return False
    return bool(_mac_tap(combo))


_MAC_MODS = {"cmd": "command down", "command": "command down",
             "ctrl": "control down", "control": "control down",
             "alt": "option down", "option": "option down",
             "shift": "shift down", "win": "command down"}

_MAC_KEYCODE = {"enter": 36, "return": 36, "tab": 48, "space": 49,
                "delete": 51, "backspace": 51, "esc": 53,
                "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96,
                "f11": 103, "f12": 111,
                "left": 123, "right": 124, "down": 125, "up": 126,
                "home": 115, "end": 119, "pageup": 116, "pagedown": 121}


def _mac_tap(combo: str) -> bool | None:
    """False = ما أعرف هالاختصار. None = أعرفه بس ما قدرت أنفّذه.

    الفرق مهم: الأولى غلط بالطلب، والثانيه غالباً إذن Accessibility
    ناقص — ورسالتين مختلفتين تماماً للمستخدم.
    """
    if not have("osascript"):
        return None

    parts = [p.strip().lower() for p in (combo or "").split("+") if p.strip()]
    if not parts:
        return False

    mods = [_MAC_MODS[p] for p in parts[:-1] if p in _MAC_MODS]
    if len(mods) != len(parts) - 1:
        return False
    key = parts[-1]

    using = (" using {" + ", ".join(mods) + "}") if mods else ""
    if key in _MAC_KEYCODE:
        script = f'tell application "System Events" to key code ' \
                 f'{_MAC_KEYCODE[key]}{using}'
    elif len(key) == 1:
        script = f'tell application "System Events" to keystroke "{key}"{using}'
    else:
        return False
    # وصلنا هني يعني الاختصار مفهوم — فالفشل تنفيذ مو معرفه
    return True if _osa(script) is not None else None


def _mac_write(text: str) -> bool | None:
    if not have("osascript"):
        return None
    # نقسّم النص: AppleScript يختنق بالنصوص الطويله جداً
    safe = text.replace("\\", "\\\\").replace('"', '\\"')
    for i in range(0, len(safe), 400):
        chunk = safe[i:i + 400]
        if _osa(f'tell application "System Events" to keystroke "{chunk}"') is None:
            return None
    return True


# ══════════════════════════════════════════════════════════════════
#                          لينكس
# ══════════════════════════════════════════════════════════════════
def _linux_active() -> dict | None:
    if not have("xdotool"):
        return None
    out = _run(["xdotool", "getactivewindow", "getwindowgeometry", "--shell"])
    if not out:
        return None
    vals: dict[str, int] = {}
    for ln in out.splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            try:
                vals[k.strip()] = int(v.strip())
            except ValueError:
                pass
    if not {"X", "Y", "WIDTH", "HEIGHT"} <= vals.keys():
        return None
    if vals["WIDTH"] < 120 or vals["HEIGHT"] < 120:
        return None
    title = _run(["xdotool", "getactivewindow", "getwindowname"]) or ""
    return {"left": max(0, vals["X"]), "top": max(0, vals["Y"]),
            "width": vals["WIDTH"], "height": vals["HEIGHT"], "title": title}


def _linux_list() -> list[str]:
    if have("wmctrl"):
        out = _run(["wmctrl", "-l"])
        if out:
            # التنسيق: id  desktop  host  title
            return [ln.split(None, 3)[3] for ln in out.splitlines()
                    if len(ln.split(None, 3)) > 3]
    if have("xdotool"):
        out = _run(["xdotool", "search", "--onlyvisible", "--name", "."])
        if out:
            titles = []
            for wid in out.splitlines()[:40]:
                t = _run(["xdotool", "getwindowname", wid.strip()])
                if t:
                    titles.append(t)
            return titles
    return []


def _linux_focus(name: str) -> str | None:
    if have("wmctrl"):
        if _run(["wmctrl", "-a", name]) is not None:
            for t in _linux_list():
                if name.lower() in t.lower():
                    return t
            return name
    if have("xdotool"):
        wid = _run(["xdotool", "search", "--onlyvisible", "--name", name])
        if wid:
            first = wid.splitlines()[0].strip()
            if _run(["xdotool", "windowactivate", first]) is not None:
                return _run(["xdotool", "getwindowname", first]) or name
    return None


def _linux_action(action: str, name: str = "") -> bool | None:
    if not have("wmctrl") and not have("xdotool"):
        return None
    target = name or ":ACTIVE:"

    if have("wmctrl"):
        flags = {"max": "add,maximized_vert,maximized_horz",
                 "restore": "remove,maximized_vert,maximized_horz"}
        if action == "close":
            return _run(["wmctrl", "-c", target]) is not None
        if action in flags:
            return _run(["wmctrl", "-r", target, "-b", flags[action]]) is not None
    if have("xdotool") and action == "min":
        wid = (_run(["xdotool", "search", "--name", name]) if name
               else _run(["xdotool", "getactivewindow"]))
        if wid:
            return _run(["xdotool", "windowminimize",
                         wid.splitlines()[0].strip()]) is not None
    return False


def _linux_tap(combo: str) -> bool | None:
    if not have("xdotool"):
        return None
    keys = (combo or "").replace("cmd", "super").replace("win", "super")
    return _run(["xdotool", "key", "--clearmodifiers", keys]) is not None


def _linux_write(text: str) -> bool | None:
    if not have("xdotool"):
        return None
    return _run(["xdotool", "type", "--clearmodifiers", "--delay", "6",
                 text], timeout=60.0) is not None


# ══════════════════════════════════════════════════════════════════
#                     كشف البرامج المتجمّده
# ══════════════════════════════════════════════════════════════════
def frozen_windows() -> list[str] | None:
    """أسماء النوافذ اللي ما ترد. None = النظام ما يوفّر طريقه موثوقه."""
    if not IS_WIN:
        # ماك ولينكس ما عندهم مقابل موثوق لـSendMessageTimeout.
        # نرجّع None بدل ما نخمّن ونطلّع إنذاراً كاذباً.
        return None

    import ctypes
    import ctypes.wintypes as wt

    try:
        u = _win_u()
        proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        stuck: list[str] = []

        def cb(hwnd, _l):
            if not u.IsWindowVisible(hwnd):
                return True
            if u.GetWindowTextLengthW(hwnd) < 3:
                return True
            result = wt.DWORD()
            # SMTO_ABORTIFHUNG = 2 — يرجّع صفراً لو النافذه ما ردّت
            if not u.SendMessageTimeoutW(hwnd, 0, 0, 0, 2, 1200,
                                         ctypes.byref(result)):
                t = _win_title(hwnd)
                if t:
                    stuck.append(t)
            return True

        u.EnumWindows(proc(cb), 0)
        return stuck
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════
#                        شفافية النافذه
# ══════════════════════════════════════════════════════════════════
def make_transparent(root, color: str = "#010203") -> bool:
    """يخلّي نافذة Tk شفافه. يرجّع False لو النظام ما يقدر.

    ويندوز  ← `-transparentcolor` يشيل لوناً محدداً تماماً
    ماك     ← `-transparent` مع خلفية systemTransparent
    لينكس   ← ما فيه طريقه موحّده (يعتمد على مدير النوافذ والتركيب)
    """
    try:
        if IS_WIN:
            root.attributes("-transparentcolor", color)
            return True
        if IS_MAC:
            root.attributes("-transparent", True)
            root.config(bg="systemTransparentColor")
            return True
    except Exception:
        pass
    return False


# ══════════════════════════════════════════════════════════════════
def report() -> str:
    lines = ["النظام      : " + OS_NAME + "  (" + sys.platform + ")",
             "مفتاح الأمر : " + MOD]
    miss = missing_tools()
    lines.append("التحكّم     : " + ("جاهز" if not miss
                                     else "ناقص " + " و".join(miss)))
    win = active_window()
    lines.append("النافذه     : " + (win["title"][:40] if win else "ما قدرت أقرأها"))
    fz = frozen_windows()
    lines.append("كشف التجمّد : " + ("مدعوم" if fz is not None else "ويندوز فقط"))
    return "\n  ".join(lines)


if __name__ == "__main__":
    print()
    print("  " + report())
    hint = setup_hint()
    if hint:
        print()
        print("  " + hint)
    if IS_MAC:
        print()
        print("  " + MAC_PERMISSION)
    print()


# ══════════════════════════════════════════════════════════════════
#                          الحافظه
# ══════════════════════════════════════════════════════════════════
def clipboard() -> str:
    """نص الحافظه. تُقرأ وتُرمى — ما تُخزَّن أبداً."""
    if IS_WIN:
        return _win_clipboard()
    if IS_MAC:
        return _run(["pbpaste"]) or ""
    for tool, args in (("xclip", ["xclip", "-selection", "clipboard", "-o"]),
                       ("xsel", ["xsel", "--clipboard", "--output"]),
                       ("wl-paste", ["wl-paste", "--no-newline"])):
        if have(tool):
            return _run(args) or ""
    return ""


def _win_clipboard() -> str:
    import ctypes

    CF_UNICODETEXT = 13
    try:
        u = ctypes.windll.user32
        k = ctypes.windll.kernel32

        # لازم نعلن الأنواع. بدونها ctypes تفترض أن المُرجَع `int` بـ٣٢ بت،
        # فيتقصّ المؤشر ٦٤ بت — وبايثون **يسقط بـSegmentation fault**، مو
        # يطلّع استثناءً نقدر نمسكه. جرّبناها وسقط الإنتربريتر كامل.
        u.GetClipboardData.argtypes = [ctypes.c_uint]
        u.GetClipboardData.restype = ctypes.c_void_p
        k.GlobalLock.argtypes = [ctypes.c_void_p]
        k.GlobalLock.restype = ctypes.c_void_p
        k.GlobalUnlock.argtypes = [ctypes.c_void_p]
        k.GlobalUnlock.restype = ctypes.c_int

        if not u.OpenClipboard(0):
            return ""
        try:
            handle = u.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            ptr = k.GlobalLock(handle)
            if not ptr:
                return ""
            try:
                return ctypes.c_wchar_p(ptr).value or ""
            finally:
                k.GlobalUnlock(handle)
        finally:
            u.CloseClipboard()
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════
#                     التقاط مخرَج الجهاز
# ══════════════════════════════════════════════════════════════════
# ويندوز عنده WASAPI loopback جاهز. لينكس عنده monitor sources من
# PulseAudio. ماك **ما عنده** طريقه أصليه — لازم سوّاقة صوت افتراضيه
# مثل BlackHole. نقولها بصراحه بدل ما نفشل بصمت.
LOOPBACK_HELP = {
    "macos": (
        "ماك ما يعطي أي برنامج مخرَج الصوت مباشره — يحتاج سوّاقه افتراضيه:\n"
        "     brew install blackhole-2ch\n"
        "     ثم: Audio MIDI Setup ← Multi-Output Device (سماعتك + BlackHole)\n"
        "     وخلّه المخرَج الافتراضي."
    ),
    "linux": (
        "يحتاج PulseAudio أو PipeWire (غالباً موجود):\n"
        "     pactl list short sources   ← لازم تشوف مصدراً ينتهي بـ.monitor"
    ),
    "windows": "",
}


def loopback_mic():
    """جهاز التقاط مخرَج الصوت، أو None. يحتاج soundcard منزّله."""
    try:
        import soundcard as sc
    except Exception:
        # مو ImportError بس: soundcard ينادي مكتبة النظام بالاستيراد،
        # وترجّع OSError لو CoreAudio/PulseAudio ناقصه.
        return None

    try:
        mics = sc.all_microphones(include_loopback=True)
    except Exception:
        return None

    loops = [m for m in mics if getattr(m, "isloopback", False)]

    # نفضّل اللي يطابق السمّاعه الشغّاله — عشان نلتقط اللي تسمعه فعلاً
    try:
        target = sc.default_speaker().name
        for m in loops:
            if m.name == target:
                return m
    except Exception:
        pass

    if loops:
        return loops[0]

    # لينكس: مصادر المراقبه أحياناً ما تتعلّم بـisloopback
    if IS_LINUX:
        for m in mics:
            if "monitor" in (m.name or "").lower():
                return m

    # ماك: BlackHole أو ما شابهه يظهر كميكروفون عادي
    if IS_MAC:
        for m in mics:
            n = (m.name or "").lower()
            if any(k in n for k in ("blackhole", "soundflower", "loopback",
                                    "multi-output")):
                return m
    return None
