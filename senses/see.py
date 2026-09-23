"""
حاسة البصر — خمس قدرات.

    python see.py                     لقطه ووصف
    python see.py "وش هذا الخطأ؟"     سؤال محدد
    python see.py --text              قراءة النص حرفياً (كود · ترجمه · أرقام)
    python see.py --clip 8            متابعة ٨ ثواني ⇦ يفهم الحركه
    python see.py --region يمين       منطقه محدده بس
    python see.py --mark              يحفظ لقطة «قبل»
    python see.py --diff              وش تغيّر من «قبل»

ليش خمس مو وحده:
  · اللقطه الواحده تكفي لسؤال بسيط، وتعجز عن الحركه
  · التصغير للعرض يضيّع الحروف الصغيره ⇦ `--text` بدقّه كامله
  · «وش تغيّر؟» يحتاج صورتين مو وحده ⇦ `--mark` ثم `--diff`
  · `--region` أدق وأرخص، **وما يشوف بقية شاشتك**

الصور تُرسل وتُرمى. ما ينحفظ إلا مرجع المقارنه، وتقدر تمسحه.
"""

from __future__ import annotations

import base64
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import ROOT, call, ensure, line, persona, user_name  # noqa: E402

REF = ROOT / ".vision_ref.jpg"

CLIP_WIDTH = 880
TEXT_WIDTH = 1600
NORMAL_WIDTH = 1280

REGIONS = {
    "يمين": (0.5, 0.0, 1.0, 1.0),
    "يسار": (0.0, 0.0, 0.5, 1.0),
    "فوق": (0.0, 0.0, 1.0, 0.5),
    "تحت": (0.0, 0.5, 1.0, 1.0),
    "وسط": (0.25, 0.25, 0.75, 0.75),
    "زاويه يمين فوق": (0.55, 0.0, 1.0, 0.45),
    "زاويه يسار فوق": (0.0, 0.0, 0.45, 0.45),
    "زاويه يمين تحت": (0.55, 0.55, 1.0, 1.0),
    "زاويه يسار تحت": (0.0, 0.55, 0.45, 1.0),
    "right": (0.5, 0.0, 1.0, 1.0),
    "left": (0.0, 0.0, 0.5, 1.0),
    "top": (0.0, 0.0, 1.0, 0.5),
    "bottom": (0.0, 0.5, 1.0, 1.0),
    "center": (0.25, 0.25, 0.75, 0.75),
}


def _active_rect() -> dict | None:
    """إحداثيات النافذه الشغّاله."""
    import ctypes
    import ctypes.wintypes as wt

    try:
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        if not hwnd:
            return None
        r = wt.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w < 120 or h < 120:
            return None
        return {"left": max(0, r.left), "top": max(0, r.top),
                "width": w, "height": h}
    except Exception:
        return None


def grab(window_only: bool = False, region: tuple | None = None,
         max_width: int = NORMAL_WIDTH, fmt: str = "JPEG") -> bytes:
    # `mss.mss()` هو المصنع الصحيح. جرّبت `mss.MSS` لأنه يطلّع تحذير
    # إهمال، فانكسر بـBitBlt — الصنف الأساس مو مصنعاً. نكتم التحذير بدالها.
    import warnings

    import mss
    from PIL import Image

    # `mss.mss()` هو المصنع الصحيح لكنه يطلّع تحذير إهمال. جرّبنا `mss.MSS`
    # فانكسر الالتقاط بـBitBlt — الصنف الأساس مو مصنعاً. نكتم التحذير
    # بـcatch_warnings مو filterwarnings(module=...): التحذير يُنسب لهذا
    # الملف مو لـmss، فالفلتر بالاسم ما يمسكه.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        sct = mss.mss()

    with sct:
        area = dict(sct.monitors[1])
        if window_only:
            win = _active_rect()
            if win:
                area = win

        if region:
            x0, y0, x1, y1 = region
            w, h = area["width"], area["height"]
            area = {
                "left": area["left"] + int(w * x0),
                "top": area["top"] + int(h * y0),
                "width": max(40, int(w * (x1 - x0))),
                "height": max(40, int(h * (y1 - y0))),
            }

        raw = sct.grab(area)
        img = Image.frombytes("RGB", raw.size, raw.rgb)

    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    if fmt == "PNG":
        img.save(buf, format="PNG", optimize=True)
    else:
        img.save(buf, format="JPEG", quality=84)
    return buf.getvalue()


def _ask(images: list[tuple[bytes, str]], prompt: str,
         max_tokens: int = 900) -> str:
    parts = [{"inline_data": {"mime_type": mime,
                              "data": base64.b64encode(data).decode()}}
             for data, mime in images]
    parts.append({"text": f"{persona()}\n\n{prompt}"})
    return call(parts, max_tokens)


# ══════════ القدرات ══════════
def describe(question: str = "") -> str:
    ask = question.strip() or "وش اللي على الشاشه؟ اختصر بجملتين."
    return _ask([(grab(), "image/jpeg")], ask)


def read_text(question: str = "") -> str:
    """يقرأ النص الصغير بدقّه — النافذه الشغّاله بدقّتها الكامله."""
    png = grab(window_only=True, max_width=TEXT_WIDTH, fmt="PNG")
    prompt = ("اقرأ النص الظاهر **حرفياً وبدقّه**. حافظ على الأسطر "
              "والمسافات لو كان كوداً أو جدولاً. لا تلخّص.")
    if question.strip():
        prompt += f"\n\nوبعدها جاوب: {question}"
    return _ask([(png, "image/png")], prompt, 1400)


def watch_clip(seconds: float = 8.0, question: str = "",
               frames: int = 5) -> str:
    """عدة إطارات ⇦ يفهم الحركه مو لقطه جامده."""
    frames = max(3, min(8, frames))
    gap = max(0.4, seconds / frames)

    shots = []
    for i in range(frames):
        shots.append((grab(max_width=CLIP_WIDTH), "image/jpeg"))
        print(f"\r  إطار {i + 1}/{frames}", end="", flush=True)
        if i < frames - 1:
            time.sleep(gap)
    print()

    ask = question.strip() or "وش صار بهالمقطع؟"
    prompt = (f"هذي {frames} لقطات متتاليه على مدى {seconds:.0f} ثواني "
              f"بالترتيب (الأولى أقدم).\n\n"
              f"اقرأها كتسلسل زمني وقل وش **يتغيّر** بينها — الحركه "
              f"والتقدّم، مو وصف كل صوره لحالها.\n\nالسؤال: {ask}")
    return _ask(shots, prompt)


def look_region(where: str, question: str = "") -> str:
    key = where.strip().lower()
    box = None
    best_len = 0
    for name, rect in REGIONS.items():
        if name.lower() in key and len(name) > best_len:
            box, best_len = rect, len(name)

    if box is None:
        names = "، و".join(n for n in REGIONS if not n.isascii())
        return f"أي منطقه؟ عندي: {names}."

    img = grab(region=box, max_width=1500, fmt="PNG")
    ask = question.strip() or "وش فيها؟"
    return _ask([(img, "image/png")],
                f"هذي منطقة «{where}» من الشاشه فقط.\n\n{ask}")


def mark_before() -> str:
    REF.write_bytes(grab())
    return "حفظت لقطة «قبل». سوِّ تعديلاتك وشغّل --diff."


def what_changed(question: str = "") -> str:
    if not REF.exists():
        return "ما عندي لقطة «قبل». شغّل --mark أول."

    ask = question.strip() or "وش تغيّر بالضبط؟"
    prompt = ("الصوره الأولى **قبل** والثانيه **بعد** — نفس الشاشه "
              "بوقتين.\n\nقل وش تغيّر: شنو انضاف، شنو انحذف، شنو انتقل. "
              f"تجاهل الساعه ومؤشرات النظام.\n\n{ask}")
    return _ask([(REF.read_bytes(), "image/jpeg"), (grab(), "image/jpeg")],
                prompt)


def _cli() -> None:
    if not ensure("mss", "PIL", "requests"):
        return
    args = sys.argv[1:]
    print()

    try:
        if "--text" in args:
            rest = " ".join(a for a in args if a != "--text")
            print("  أقرأ النص بدقّه…\n")
            out = read_text(rest)
        elif "--clip" in args:
            i = args.index("--clip")
            secs = float(args[i + 1]) if len(args) > i + 1 and args[i + 1].replace(".", "").isdigit() else 8.0
            rest = " ".join(a for j, a in enumerate(args)
                            if j not in (i, i + 1) or not a.replace(".", "").isdigit())
            rest = rest.replace("--clip", "").strip()
            print(f"  أتابع {secs:.0f} ثواني…")
            out = watch_clip(secs, rest)
        elif "--region" in args:
            i = args.index("--region")
            where = args[i + 1] if len(args) > i + 1 else ""
            rest = " ".join(args[i + 2:])
            out = look_region(where, rest)
        elif "--mark" in args:
            out = mark_before()
        elif "--diff" in args:
            rest = " ".join(a for a in args if a != "--diff")
            print("  أقارن…\n")
            out = what_changed(rest)
        else:
            out = describe(" ".join(args))
    except Exception as e:
        out = f"تعذّر: {e}"

    line()
    print("  " + out.replace("\n", "\n  "))
    print()


if __name__ == "__main__":
    _cli()
