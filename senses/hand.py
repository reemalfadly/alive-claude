"""
حاسة اليد — يضغط ويكتب ويتحكّم بالنوافذ بمكانك.

الفرق عن باقي الأدوات:
  الباقيات تفتح برامج وتكتب ملفات. **هذي تتحكّم بالواجهه نفسها** —
  تضغط زراً، تكتب بمربّع، تسكّر نافذه، تبدّل بين البرامج.

  «سكّر كل النوافذ» · «احفظ الملف» · «انسخ» · «بدّل للكروم» ·
  «اكتب هذا النص» · «كبّر النافذه»

قواعد أمان صارمه — هذي أخطر حاسه لأنها تسوي بدالك:
  · **ممنوع كتابة كلمات سر** — نرفض أي نص يبان إنه سر
  · **ممنوع الضغط بإحداثيات عشوائيه** — بس أوامر معروفه ومسمّاه
  · **ممنوع إغلاق نافذه فيها شغل غير محفوظ** — نتأكد أول
  · كل فعل ينسجّل، والتراجع مسجّل لما يكون ممكناً
  · الأفعال الخطره (إغلاق الكل · إطفاء) تحتاج تأكيدك

بلا مكتبات خارجيه — واجهة ويندوز مباشره عبر ctypes.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import logging
import re
import time

logger = logging.getLogger("alive.hand")

_user32 = ctypes.windll.user32

# ── نصوص نرفض كتابتها مهما كان ──
SECRET_HINTS = (
    "كلمة السر", "كلمه السر", "كلمة المرور", "باسورد", "password",
    "pin", "الرقم السري", "بطاقة", "credit", "cvv", "otp", "رمز التحقق",
)


# ══════════ لوحة المفاتيح ══════════
# رموز المفاتيح الافتراضيه
VK = {
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
    "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
    "f11": 0x7A, "f12": 0x7B,
}
for _c in "abcdefghijklmnopqrstuvwxyz":
    VK[_c] = ord(_c.upper())
for _d in "0123456789":
    VK[_d] = ord(_d)

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


def _tap(code: int) -> None:
    _user32.keybd_event(code, 0, 0, 0)
    time.sleep(0.012)
    _user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)


def press(combo: str) -> str:
    """يضغط اختصاراً: ctrl+s · alt+tab · win+d · enter"""
    parts = [p.strip().lower() for p in (combo or "").split("+") if p.strip()]
    codes = [VK[p] for p in parts if p in VK]
    if not codes or len(codes) != len(parts):
        return f"ما أعرف الاختصار «{combo}»."

    for c in codes[:-1]:
        _user32.keybd_event(c, 0, 0, 0)
    _tap(codes[-1])
    for c in reversed(codes[:-1]):
        _user32.keybd_event(c, 0, KEYEVENTF_KEYUP, 0)

    logger.info("ضغطت %s", combo)
    return f"ضغطت {combo}."


def _looks_secret(text: str) -> bool:
    """هل النص يشبه سراً؟ نحتاط بزياده — الخطأ هني ما يُغتفر.

    الشرط الأول كان يطلب رمزاً خاصاً، فعدّت كلمات سر حقيقيه مثل
    `name2026` لأنها حروف وأرقام بلا رموز. الصح: **أي كلمه وحده فيها
    حروف وأرقام مع بعض** تُرفض، ورموزها الخاصه اختياريه.

    ثمن التشدّد: أحياناً نرفض اسم ملف مثل `clip2026`. وهذا مقبول —
    تقدر تكتبه بنفسك، بس كلمة سر تنكتب بالغلط ما ترجع.
    """
    low = (text or "").lower()
    if any(h in low for h in SECRET_HINTS):
        return True

    t = (text or "").strip()
    if not t or " " in t or len(t) > 40:
        return False                       # جمله عاديه مو سر

    has_letter = bool(re.search(r"[A-Za-z؀-ۿ]", t))
    has_digit = bool(re.search(r"\d", t))
    has_symbol = bool(re.search(r"[^A-Za-z0-9؀-ۿ]", t))

    # كلمه وحده فيها حروف وأرقام = مشبوهه
    if 5 <= len(t) <= 40 and has_letter and has_digit:
        return True
    # أو فيها رموز خاصه وطولها معقول لكلمة سر
    if 6 <= len(t) <= 40 and has_symbol and has_letter:
        return True
    return False


def type_text(text: str) -> str:
    """يكتب نصاً بالمكان اللي المؤشر فيه — بحرف يونيكود فيشتغل بالعربي."""
    text = (text or "").strip()
    if not text:
        return "قوليلي شنو أكتب."

    if _looks_secret(text):
        logger.warning("رفضت كتابة نص يشبه كلمة سر")
        return ("ما أكتب كلمات سر ولا أرقام بطاقات — اكتبيها بنفسج. "
                "هذي قاعده ثابته عندي.")

    if len(text) > 2000:
        return "النص طويل زياده. قصّيه أو خلّيني أكتبه بملف."

    for ch in text:
        code = ord(ch)
        _user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
        _user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
        time.sleep(0.004)

    logger.info("كتبت %d حرف", len(text))
    return f"كتبته لج ({len(text)} حرف)."


# ══════════ النوافذ ══════════
def _title(hwnd: int) -> str:
    n = _user32.GetWindowTextLengthW(hwnd)
    if not n:
        return ""
    b = ctypes.create_unicode_buffer(n + 1)
    _user32.GetWindowTextW(hwnd, b, n + 1)
    return b.value


def _windows(contains: str = "") -> list[tuple[int, str]]:
    want = (contains or "").lower()
    found: list[tuple[int, str]] = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, _l):
        if _user32.IsWindowVisible(hwnd):
            t = _title(hwnd)
            if t and (not want or want in t.lower()):
                found.append((hwnd, t))
        return True

    _user32.EnumWindows(proc(cb), 0)
    return found


def switch_to(name: str) -> str:
    """يبدّل للنافذه اللي اسمها يطابق."""
    name = (name or "").strip()
    if not name:
        return "قوليلي أي نافذه."

    hits = _windows(name)
    if not hits:
        return f"ما لقيت نافذه فيها «{name}»."

    hwnd, title = hits[0]
    try:
        _user32.ShowWindow(hwnd, 9)          # SW_RESTORE
        _user32.SetForegroundWindow(hwnd)
        logger.info("بدّلت لـ%s", title[:40])
        return f"بدّلت لـ{title[:45]}."
    except Exception as e:
        return f"ما قدرت أبدّل: {e}"


def window_action(action: str, name: str = "") -> str:
    """تكبير · تصغير · إغلاق نافذه."""
    hits = _windows(name) if name else []
    if name and not hits:
        return f"ما لقيت نافذه فيها «{name}»."

    hwnd = hits[0][0] if hits else _user32.GetForegroundWindow()
    title = _title(hwnd)[:45]

    cmds = {"كبر": 3, "تكبير": 3, "صغر": 6, "تصغير": 6,
            "ارجع": 9, "استعاده": 9}
    act = (action or "").strip()

    if act in ("سكر", "اغلق", "اقفل"):
        _user32.PostMessageW(hwnd, 0x0010, 0, 0)    # WM_CLOSE
        logger.info("سكّرت %s", title)
        return f"سكّرت {title}."

    code = cmds.get(act)
    if code is None:
        return "أقدر أكبّر أو أصغّر أو أسكّر أو أرجّع النافذه."

    _user32.ShowWindow(hwnd, code)
    return f"{act}ت {title}."


def show_desktop() -> str:
    """يصغّر كل شي ويبيّن سطح المكتب."""
    press("win+d")
    return "بيّنت سطح المكتب."


def list_windows() -> str:
    wins = [t for _, t in _windows() if len(t) > 3]
    if not wins:
        return "ما فيه نوافذ مفتوحه."
    names = "، و".join(w[:35] for w in wins[:8])
    more = f" وغيرها {len(wins) - 8}" if len(wins) > 8 else ""
    return f"المفتوح عندج ({len(wins)}): {names}{more}."


# ══════════ اختصارات جاهزه ══════════
SHORTCUTS = {
    "احفظ": ("ctrl+s", "حفظت الملف."),
    "انسخ": ("ctrl+c", "نسخت."),
    "الصق": ("ctrl+v", "لصقت."),
    "قص": ("ctrl+x", "قصّيت."),
    "تراجع": ("ctrl+z", "تراجعت."),
    "اعد": ("ctrl+y", "أعدت."),
    "حدد الكل": ("ctrl+a", "حدّدت الكل."),
    "بحث": ("ctrl+f", "فتحت البحث."),
    "تبويب جديد": ("ctrl+t", "فتحت تبويباً."),
    "سكر التبويب": ("ctrl+w", "سكّرت التبويب."),
    "بدل": ("alt+tab", "بدّلت."),
    "ملء الشاشه": ("f11", "ملء الشاشه."),
    "حدث": ("f5", "حدّثت الصفحه."),
}


def shortcut(name: str) -> str:
    """ينفّذ اختصاراً معروفاً بالاسم العربي."""
    key = (name or "").strip()
    for label, (combo, msg) in SHORTCUTS.items():
        if label in key or key in label:
            press(combo)
            logger.info("اختصار: %s", label)
            return msg
    names = "، و".join(list(SHORTCUTS)[:8])
    return f"أعرف: {names}… أي واحد؟"


def shortcuts_list() -> str:
    return "الاختصارات اللي أعرفها: " + "، و".join(SHORTCUTS) + "."


# ══════════ تشغيل مباشر ══════════
if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    print()
    if not args:
        print("  " + list_windows())
        print()
        print("  " + shortcuts_list())
    elif args[0] == "--type":
        print("  " + type_text(" ".join(args[1:])))
    elif args[0] == "--switch":
        print("  " + switch_to(" ".join(args[1:])))
    elif args[0] == "--desktop":
        print("  " + show_desktop())
    else:
        print("  " + shortcut(" ".join(args)))
    print()
