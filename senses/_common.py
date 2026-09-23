"""
الأساس المشترك بين الحواس — الإعدادات ونداء النموذج.

كل حاسه تستورد من هني بدل ما تكرّر الكود، وبدل ما تعرف مفتاحك من مكان
ثابت. كله يقرأ من `config.json` اللي أنشأه `setup.py`.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger("alive")

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"

API = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = (8, 45)

# نماذج **مفحوصه فعلياً** — أرسلنا لها صوره وتأكّدنا إنها تقبلها.
# مهم: النماذج النصيه والصوتيه ترفض الصور بـ400، وبعض الأسماء الشائعه
# (مثل gemini-2.5-flash) ترجع 404 على مفاتيح الطبقه المجانيه.
# لو تغيّرت القائمه، شغّل: python senses/_common.py --probe
VISION_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
]

TEXT_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]


# ══════════ المكتبات ══════════
# غالب الأعطال اللي يشوفها اللي ينزّل المهاره أول مره هي `ImportError`
# بشكل تتبّع طويل ما يفهمه. بدال ما نرميه عليه، نشوف الناقص وننزّله.
PIP = {
    "PIL": "Pillow",
    "mss": "mss",
    "requests": "requests",
    "numpy": "numpy",
    "psutil": "psutil",
    "sounddevice": "sounddevice",
    "soundcard": "soundcard",
    "faster_whisper": "faster-whisper",
}


def ensure(*modules: str, quiet: bool = False) -> bool:
    """يتأكد إن المكتبات موجوده، وينزّل الناقص مره وحده.

    غالب أعطال أول تشغيل هي `ImportError` بتتبّع طويل ما يفهمه أحد.
    بدال ما نرميه على المستخدم، نشوف الناقص وننزّله. ولو فشل التنزيل
    نطبع أمر pip الصحيح — سطر واحد واضح.
    """
    import importlib
    import subprocess
    import sys

    missing = []
    for mod in modules:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(PIP.get(mod, mod))

    if not missing:
        return True

    if not quiet:
        print("  أنزّل " + ", ".join(missing) + "… (مره وحده بس)")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing],
                       check=True, timeout=900)
    except Exception:
        print()
        print("  ما قدرت أنزّلها. شغّل بنفسك:")
        print("  " + sys.executable + " -m pip install " + " ".join(missing))
        print()
        return False

    importlib.invalidate_caches()
    for mod in modules:
        try:
            importlib.import_module(mod)
        except ImportError:
            print()
            print("  " + mod + " ما زال ناقصاً. جرّب:")
            print("  " + sys.executable + " -m pip install " + PIP.get(mod, mod))
            print()
            return False
    return True


def windows_only(what: str) -> bool:
    """بعض الحواس تستخدم واجهات ويندوز مباشره. نقولها بوضوح بدل الانهيار."""
    import sys

    if sys.platform == "win32":
        return True
    print()
    print("  «" + what + "» تشتغل على ويندوز بس — تستخدم واجهات ويندوز مباشره.")
    print("  باقي الحواس تشتغل عندك عادي.")
    print()
    return False


_cfg: dict | None = None


def config() -> dict:
    global _cfg
    if _cfg is None:
        try:
            _cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            _cfg = {}
    return _cfg


def user_name() -> str:
    """اسم المستخدم من إعداداته — ما نفترض أي اسم أبداً."""
    return (config().get("name") or "").strip() or "صديقي"


def api_key() -> str:
    key = (config().get("gemini_key") or "").strip()
    if key:
        return key
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        return os.environ.get("GEMINI_API_KEY", "").strip()
    except Exception:
        return ""


def persona() -> str:
    """شخصية كلود — تُبنى من اسم المستخدم مو من اسم ثابت."""
    return (
        f"أنت كلود، مساعد {user_name()} على جهازه. "
        f"ناديه «{user_name()}». "
        "جاوب بجمل قصيره وطبيعيه، ولا تعدّد نقاطاً إلا لو طلب. "
        "لا تقل «تم» إلا بعد ما تنفّذ فعلاً."
    )


def hide_key(text: str) -> str:
    """يشيل المفتاح من رسائل الخطأ — الروابط تحمله بالكامل."""
    return re.sub(r"key=[\w\-]+", "key=***", str(text))


def call(parts: list[dict], max_tokens: int = 800,
         models: list[str] | None = None) -> str:
    """ينادي النماذج بالترتيب لين واحد يرد."""
    if not ensure("requests"):
        raise RuntimeError("requests ناقصه")
    import requests

    key = api_key()
    if not key:
        raise RuntimeError("ما فيه مفتاح — شغّل setup.py")

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    last = ""
    for model in (models or VISION_MODELS):
        try:
            r = requests.post(f"{API}/{model}:generateContent?key={key}",
                              json=payload, timeout=TIMEOUT)
            if r.status_code in (429, 500, 503):
                last = f"{model} مزدحم ({r.status_code})"
                continue
            r.raise_for_status()
            text = "".join(
                p.get("text", "")
                for c in r.json().get("candidates", [])
                for p in c.get("content", {}).get("parts", [])
            ).strip()
            if text:
                return text
            last = f"{model} رجّع رداً فاضياً"
        except Exception as e:
            last = f"{model}: {hide_key(e)}"
            continue
    raise RuntimeError(hide_key(last) or "ما فيه نموذج متاح")


def ask(prompt: str, max_tokens: int = 600) -> str:
    """سؤال نصي بسيط."""
    try:
        return call([{"text": f"{persona()}\n\n{prompt}"}], max_tokens,
                    TEXT_MODELS)
    except Exception as e:
        return f"ما قدرت أجاوب: {e}"


def line(ch: str = "─", n: int = 50) -> None:
    print("  " + ch * n)


# ══════════ فحص النماذج ══════════
def probe() -> None:
    """يرسل صوره صغيره لكل نموذج ويطبع اللي يقبلها فعلاً.

    الأسماء تتغيّر بين الحين والثاني، والتخمين يكسر الرؤيه بصمت.
    شغّل هذا لو صارت الرؤيه ترجع 400 أو 404.
    """
    import base64
    import io as _io

    import requests
    from PIL import Image

    key = api_key()
    if not key:
        print("  ما فيه مفتاح — شغّل setup.py")
        return

    img = Image.new("RGB", (64, 64), (200, 90, 60))
    buf = _io.BytesIO()
    img.save(buf, "JPEG")
    enc = base64.b64encode(buf.getvalue()).decode()

    try:
        data = requests.get(f"{API}?key={key}&pageSize=300", timeout=25).json()
    except Exception as e:
        print(f"  تعذّر جلب القائمه: {hide_key(e)}")
        return

    names = [m["name"].split("/")[-1] for m in data.get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])
             and not any(x in m["name"] for x in
                         ("tts", "embedding", "imagen", "veo", "image"))]

    print(f"\nأفحص {len(names)} نموذجاً…\n")
    good = []
    for name in names:
        body = {
            "contents": [{"parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": enc}},
                {"text": "وش لون الصوره؟"},
            ]}],
            "generationConfig": {"maxOutputTokens": 40,
                                 "thinkingConfig": {"thinkingBudget": 0}},
        }
        try:
            r = requests.post(f"{API}/{name}:generateContent?key={key}",
                              json=body, timeout=40)
            if r.status_code == 200:
                good.append(name)
                print(f"  ✅ {name}")
            elif r.status_code == 429:
                print(f"  ⏸ {name}  (حصه)")
        except Exception:
            continue

    print(f"\nضع هذي بـVISION_MODELS:\n{good}\n")


if __name__ == "__main__":
    import sys

    if "--probe" in sys.argv:
        probe()
    else:
        print(f"\nالاسم : {user_name()}")
        print(f"  المفتاح: {'محفوظ' if api_key() else 'ناقص'}")
        print(f"  الرؤيه : {VISION_MODELS[0]}\n")
