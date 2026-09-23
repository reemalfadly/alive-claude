"""
حاسة السمع — يسمع اللي طالع من سمّاعاتك.

    python hear.py          ١٥ ثانيه
    python hear.py 30       ٣٠ ثانيه

يلتقط **مخرَج الصوت نفسه** مو المايك — يعني يسمع الفيديو أو الأغنيه
بنقاء المصدر، بلا ضجة الغرفه وبلا ما يلتقط صوتك.

التفريغ محلي بالكامل — الصوت ما يطلع من جهازك إطلاقاً.
الصوت الخام ينمسح بعد التفريغ مباشره.

**ما يشتغل إلا لما تشغّله.** ما فيه تسجيل خلفي.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _platform as plat  # noqa: E402
from _common import ensure, line  # noqa: E402

RATE = 16_000
DEFAULT_SECONDS = 15.0
SILENCE_RMS = 0.0015


def _loopback():
    """جهاز التقاط مخرَج الصوت — يختلف بين الأنظمه.

    ويندوز ← WASAPI loopback، جاهز بلا شي
    لينكس  ← مصدر `.monitor` من PulseAudio أو PipeWire
    ماك    ← **ما عنده طريقه أصليه**، يحتاج BlackHole أو ما شابهه
    """
    mic = plat.loopback_mic()
    if mic is None:
        hint = plat.LOOPBACK_HELP.get(plat.OS, "")
        msg = "ما لقيت جهازاً ألتقط منه مخرَج الصوت."
        if hint:
            msg += "\n" + hint
        raise RuntimeError(msg)
    return mic, mic.name


def record(seconds: float = DEFAULT_SECONDS):
    import numpy as np

    mic, name = _loopback()
    print(f"  أسمع من: {name}")
    print(f"  المده  : {seconds:.0f} ثانيه\n")

    chunk = int(RATE * 0.5)
    frames = []
    start = time.time()

    with mic.recorder(samplerate=RATE, channels=1, blocksize=chunk) as rec:
        while time.time() - start < seconds:
            frames.append(rec.record(numframes=chunk))
            done = time.time() - start
            bar = "#" * int(done / seconds * 28)
            print("\r  [%-28s] %4.1fs" % (bar, done), end="", flush=True)
    print()

    if not frames:
        return np.zeros(0, dtype="float32")

    audio = np.concatenate(frames, axis=0)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype("float32")


def transcribe(audio) -> str:
    """تفريغ محلي على كرت الشاشه — الصوت ما يطلع من الجهاز."""
    from faster_whisper import WhisperModel

    model = WhisperModel("small", device="auto", compute_type="auto")
    segments, _info = model.transcribe(audio, language="ar", beam_size=3)
    return " ".join(s.text.strip() for s in segments).strip()


def main() -> None:
    if not ensure("soundcard", "numpy"):
        return
    seconds = DEFAULT_SECONDS
    if len(sys.argv) > 1:
        try:
            seconds = max(3.0, min(180.0, float(sys.argv[1])))
        except ValueError:
            pass

    import numpy as np

    print()
    print("  أسمع اللي طالع من جهازك")
    line("═")

    try:
        audio = record(seconds)
    except Exception as e:
        print(f"\n  ما قدرت أسمع: {e}")
        print("  جرّب: pip install soundcard")
        return

    if len(audio) == 0:
        print("  ما وصلني صوت.")
        return

    level = float(np.sqrt(np.mean(audio ** 2)))
    if level < SILENCE_RMS:
        print(f"  ما فيه صوت طالع (المستوى {level:.4f}).")
        print("  تأكد إن المقطع شغّال والصوت مو مكتوم.")
        return

    print(f"  المستوى: {level:.3f} — أفرّغه…\n")
    try:
        text = transcribe(audio)
    except ImportError:
        print("  التفريغ يحتاج: pip install faster-whisper")
        return
    del audio                       # ما نحتفظ بالصوت الخام

    if not text:
        print("  سمعت صوتاً بلا كلام واضح (موسيقى أو مؤثرات).")
        return

    line()
    print("  اللي سمعته:\n")
    print("  " + text.replace("\n", "\n  "))
    print()


if __name__ == "__main__":
    main()
