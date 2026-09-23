"""
حارس الصياغه — يمسك الملف المكسور قبل ما تحاول تشغّله.

المشكله اللي يحلها:
  لما أعدّل ملفاً بسكربت، أحياناً تنكسر سلاسل النصوص: `"\\n"` تنقلب
  لسطر جديد حقيقي داخل السلسله، فيصير:

      print(f"  المده: {n} ثانيه
      ")

  الملف يصير مكسوراً نحوياً، والعطل ما ينكشف إلا لما يحاول بايثون
  يستورده — يعني بعد ما يتعطّل. هذا العطل تحديداً تكرّر **ست مرات
  بيوم واحد** أثناء بناء هالمهاره، فصار له حارس.

ثلاث طبقات:
  ١. **فحص**  — يفحص كل ملفات بايثون بالمشروع بثانيه واحده
  ٢. **تشخيص** — يميّز هذا العطل بالذات عن أي خطأ نحوي ثاني
  ٣. **إصلاح** — يلحم السطر المكسور تلقائياً ويحوّله لـ`\\n` صح

والتتبّع: كل كسر يُسجّل بالحارس (`sentinel`) فنعرف أي ملف يتكرر كسره.

التشغيل:
    venv\\Scripts\\python.exe -m tools.syntax_guard           فحص
    venv\\Scripts\\python.exe -m tools.syntax_guard --fix     فحص وإصلاح
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

logger = logging.getLogger("alive.guard")

BASE_DIR = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"venv", "__pycache__", ".git", "models", "node_modules"}

# توقيع العطل: سلسله تُفتح وما تُغلق بنفس السطر
_UNTERMINATED = "unterminated string literal"


def python_files(root: Path | None = None) -> list[Path]:
    root = root or BASE_DIR
    out = []
    for p in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def check(path: Path) -> tuple[bool, str, int]:
    """يفحص ملفاً. يرجع (سليم؟، الرساله، رقم السطر)."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"تعذّرت القراءه: {e}", 0
    try:
        ast.parse(source)
        return True, "", 0
    except SyntaxError as e:
        return False, str(e.msg), int(e.lineno or 0)


def is_broken_string(message: str) -> bool:
    """هل هذا عطل الهروب بالذات؟"""
    return _UNTERMINATED in (message or "").lower()


def repair(path: Path) -> tuple[bool, str]:
    """يلحم السلسله المكسوره: السطر اللي انفتحت فيه + اللي بعده.

    القاعده: لو السطر فيه عدد فردي من علامات الاقتباس (غير مهرَّبه)،
    فهو مفتوح — نلحمه باللي بعده ونحط `\\n` بدل السطر الحقيقي.
    نكرّر لين يمر الفحص أو نستسلم بأمان بلا ما نخرّب أكثر.
    """
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"تعذّرت القراءه: {e}"

    lines = original.split("\n")

    for _round in range(40):
        ok, msg, lineno = check(path)
        if ok:
            return True, "سليم"
        if not is_broken_string(msg):
            return False, f"عطل ثاني مو الهروب: {msg}"

        i = max(0, lineno - 1)
        if i >= len(lines) - 1:
            break

        quote = _open_quote(lines[i])
        if not quote:
            break

        # نلحم لين نلقى إغلاق السلسله
        merged = lines[i]
        j = i + 1
        while j < len(lines):
            merged += "\\n" + lines[j].lstrip()
            if quote in lines[j]:
                break
            j += 1

        lines[i:j + 1] = [merged]
        path.write_text("\n".join(lines), encoding="utf-8")

    path.write_text(original, encoding="utf-8")      # نرجّعه لو ما نفع
    return False, "ما قدرت أصلحه — رجّعت الأصل"


def _open_quote(line: str) -> str:
    """أي علامة اقتباس بقيت مفتوحه بآخر السطر؟"""
    for q in ('"', "'"):
        # نعدّ غير المهرَّبه، ونتجاهل الثلاثيه
        if '"""' in line or "'''" in line:
            continue
        count = len(re.findall(rf"(?<!\\){q}", line))
        if count % 2 == 1:
            return q
    return ""


# ══════════ الواجهه ══════════
def scan(fix: bool = False, verbose: bool = True) -> list[tuple[Path, str, int]]:
    broken: list[tuple[Path, str, int]] = []

    for path in python_files():
        ok, msg, lineno = check(path)
        if ok:
            continue

        rel = path.relative_to(BASE_DIR)
        kind = "هروب مكسور" if is_broken_string(msg) else "خطأ نحوي"

        if fix and is_broken_string(msg):
            fixed, note = repair(path)
            if fixed:
                if verbose:
                    print(f"  🔧 صلّحت {rel}  (كان: {msg} · سطر {lineno})")
                _track(rel, msg, repaired=True)
                continue
            msg = note

        broken.append((path, msg, lineno))
        _track(rel, msg, repaired=False)
        if verbose:
            print(f"  ❌ {rel}  [{kind}] سطر {lineno}: {msg}")

    return broken


def _track(rel: Path, msg: str, repaired: bool) -> None:
    """يسجّل الكسر بالحارس عشان نعرف أي ملف يتكرر كسره."""
    logger.info("%s %s: %s", "صلّحت" if repaired else "مكسور", rel, msg[:90])


def guard() -> bool:
    """يُنادى عند الإقلاع. يرجع True لو كل شي سليم."""
    broken = scan(fix=False, verbose=False)
    if not broken:
        logger.info("فحص الصياغه: كل الملفات سليمه")
        return True
    for path, msg, lineno in broken:
        logger.error("ملف مكسور: %s سطر %d — %s",
                     path.relative_to(BASE_DIR), lineno, msg)
    return False


def _cli() -> None:
    import sys

    sys.path.insert(0, str(BASE_DIR))
    fix = "--fix" in sys.argv

    print()
    print("  حارس الصياغه" + ("  (مع الإصلاح)" if fix else ""))
    print("  " + "─" * 46)

    files = python_files()
    broken = scan(fix=fix)

    print()
    print(f"  فحصت  : {len(files)} ملف")
    if broken:
        print(f"  مكسور : {len(broken)}")
        if not fix:
            print("\n  شغّليها بـ --fix عشان أصلّح أعطال الهروب تلقائياً.")
    else:
        print("  النتيجه: كلها سليمه ✅")
    print()


if __name__ == "__main__":
    _cli()
