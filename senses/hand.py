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
  · كل فعل ينسجّل

تشتغل على الثلاثه:
  ويندوز ← مباشره، ما تحتاج شي منزّل
  ماك    ← osascript (مع النظام)، **يبي إذن Accessibility**
  لينكس  ← xdotool و wmctrl

الاختصارات مكتوبه مره وحده بـ`ctrl`، وتنقلب `cmd` تلقائياً على ماك.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _platform as plat  # noqa: E402

logger = logging.getLogger("alive.hand")

# ── نصوص نرفض كتابتها مهما كان ──
SECRET_HINTS = (
    "كلمة السر", "كلمه السر", "كلمة المرور", "باسورد", "password",
    "pin", "الرقم السري", "بطاقة", "credit", "cvv", "otp", "رمز التحقق",
)

NO_CONTROL = (
    "ما أقدر أتحكّم بالنوافذ على " + plat.OS_NAME + " بلا أدوات ناقصه."
)


def _mod(combo: str) -> str:
    """يحوّل `ctrl` لـ`cmd` على ماك. نكتب الاختصار مره وحده بس."""
    if plat.IS_MAC:
        return re.sub(r"\bctrl\b", "cmd", combo)
    return combo


# ══════════ لوحة المفاتيح ══════════
def press(combo: str) -> str:
    """يضغط اختصاراً: ctrl+s · alt+tab · enter"""
    combo = (combo or "").strip()
    if not combo:
        return "قوليلي أي اختصار."

    ok = plat.tap(_mod(combo))
    if ok is None:
        return NO_CONTROL + " " + plat.setup_hint()
    if not ok:
        return f"ما أعرف الاختصار «{combo}»."

    logger.info("ضغطت %s", combo)
    return f"ضغطت {_mod(combo)}."


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
    """يكتب نصاً بالمكان اللي المؤشر فيه — يدعم العربي."""
    text = (text or "").strip()
    if not text:
        return "قوليلي شنو أكتب."

    if _looks_secret(text):
        logger.warning("رفضت كتابة نص يشبه كلمة سر")
        return ("ما أكتب كلمات سر ولا أرقام بطاقات — اكتبيها بنفسج. "
                "هذي قاعده ثابته عندي.")

    if len(text) > 2000:
        return "النص طويل زياده. قصّيه أو خلّيني أكتبه بملف."

    ok = plat.write(text)
    if ok is None:
        return NO_CONTROL + " " + plat.setup_hint()
    if not ok:
        return "ما قدرت أكتب. " + (plat.MAC_PERMISSION if plat.IS_MAC else "")

    logger.info("كتبت %d حرف", len(text))
    return f"كتبته لج ({len(text)} حرف)."


# ══════════ النوافذ ══════════
def switch_to(name: str) -> str:
    """يبدّل للنافذه اللي اسمها يطابق."""
    name = (name or "").strip()
    if not name:
        return "قوليلي أي نافذه."

    title = plat.focus(name)
    if title is None:
        miss = plat.missing_tools()
        if miss:
            return NO_CONTROL + "\n  " + plat.setup_hint()
        return f"ما لقيت نافذه فيها «{name}»."

    logger.info("بدّلت لـ%s", title[:40])
    return f"بدّلت لـ{title[:45]}."


def window_action(action: str, name: str = "") -> str:
    """تكبير · تصغير · إغلاق نافذه."""
    acts = {"كبر": "max", "تكبير": "max", "صغر": "min", "تصغير": "min",
            "ارجع": "restore", "استعاده": "restore",
            "سكر": "close", "اغلق": "close", "اقفل": "close"}
    act = acts.get((action or "").strip())
    if act is None:
        return "أقدر أكبّر أو أصغّر أو أسكّر أو أرجّع النافذه."

    res = plat.window_action(act, name)
    if res is None:
        return NO_CONTROL + "\n  " + plat.setup_hint()
    if res is False:
        return f"ما لقيت نافذه فيها «{name}»." if name else "ما قدرت."

    word = {"max": "كبّرت", "min": "صغّرت", "close": "سكّرت",
            "restore": "رجّعت"}[act]
    win = plat.active_window()
    where = (" " + win["title"][:40]) if (win and not name) else (" " + name if name else "")
    logger.info("%s %s", word, where.strip())
    return f"{word}{where}."


def show_desktop() -> str:
    """يصغّر كل شي ويبيّن سطح المكتب."""
    combo = {"windows": "win+d", "macos": "f11", "linux": "super+d"}[plat.OS]
    ok = plat.tap(combo)
    if not ok:
        return NO_CONTROL + " " + plat.setup_hint()
    return "بيّنت سطح المكتب."


def list_windows() -> str:
    wins = [t for t in plat.list_windows() if len(t) > 3]
    if not wins:
        miss = plat.missing_tools()
        if miss:
            return NO_CONTROL + "\n  " + plat.setup_hint()
        return "ما فيه نوافذ مفتوحه."
    names = "، و".join(w[:35] for w in wins[:8])
    more = f" وغيرها {len(wins) - 8}" if len(wins) > 8 else ""
    return f"المفتوح عندج ({len(wins)}): {names}{more}."


# ══════════ اختصارات جاهزه ══════════
# مكتوبه بـ`ctrl` وتنقلب `cmd` على ماك تلقائياً عبر `_mod`.
SHORTCUTS = {
    "احفظ": ("ctrl+s", "حفظت الملف."),
    "انسخ": ("ctrl+c", "نسخت."),
    "الصق": ("ctrl+v", "لصقت."),
    "قص": ("ctrl+x", "قصّيت."),
    "تراجع": ("ctrl+z", "تراجعت."),
    "اعد": ("ctrl+shift+z" if plat.IS_MAC else "ctrl+y", "أعدت."),
    "حدد الكل": ("ctrl+a", "حدّدت الكل."),
    "بحث": ("ctrl+f", "فتحت البحث."),
    "تبويب جديد": ("ctrl+t", "فتحت تبويباً."),
    "سكر التبويب": ("ctrl+w", "سكّرت التبويب."),
    "بدل": ("cmd+tab" if plat.IS_MAC else "alt+tab", "بدّلت."),
    "ملء الشاشه": ("ctrl+cmd+f" if plat.IS_MAC else "f11", "ملء الشاشه."),
    "حدث": ("ctrl+r" if plat.IS_MAC else "f5", "حدّثت الصفحه."),
}


def shortcut(name: str) -> str:
    """ينفّذ اختصاراً معروفاً بالاسم العربي."""
    key = (name or "").strip()
    for label, (combo, msg) in SHORTCUTS.items():
        if label in key or key in label:
            ok = plat.tap(_mod(combo))
            if ok is None:
                return NO_CONTROL + " " + plat.setup_hint()
            if not ok:
                return f"ما قدرت أنفّذ «{label}»."
            logger.info("اختصار: %s", label)
            return msg
    names = "، و".join(list(SHORTCUTS)[:8])
    return f"أعرف: {names}… أي واحد؟"


def shortcuts_list() -> str:
    return "الاختصارات اللي أعرفها: " + "، و".join(SHORTCUTS) + "."


# ══════════ تشغيل مباشر ══════════
if __name__ == "__main__":
    args = sys.argv[1:]
    print()

    hint = plat.setup_hint()
    if hint:
        print("  ⚠ " + hint)
        print()

    if not args:
        print("  النظام: " + plat.OS_NAME)
        print("  " + list_windows())
        print()
        print("  " + shortcuts_list())
        if plat.IS_MAC:
            print()
            print("  " + plat.MAC_PERMISSION)
    elif args[0] == "--type":
        print("  " + type_text(" ".join(args[1:])))
    elif args[0] == "--switch":
        print("  " + switch_to(" ".join(args[1:])))
    elif args[0] == "--key":
        print("  " + press(" ".join(args[1:])))
    elif args[0] == "--desktop":
        print("  " + show_desktop())
    else:
        print("  " + shortcut(" ".join(args)))
    print()
