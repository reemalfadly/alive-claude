"""
حاسة الإصغاء — يسمعك من المايك ويفرّغ كلامك.

    python mic.py           ينتظرك تتكلم ويوقف لما تسكت
    python mic.py 30        حد أقصى ٣٠ ثانيه

كيف يشتغل:
  · ينتظر لين تبدأ تتكلم — ما يسجّل الصمت
  · يوقف تلقائياً بعد ثانيه ونص سكوت
  · التفريغ **محلي بالكامل** — صوتك ما يطلع من جهازك

**ما يسجّل إلا لما تشغّله.** ما فيه استماع خلفي، والصوت الخام ينمسح
بعد التفريغ مباشره.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import ensure, line, user_name  # noqa: E402

RATE = 16_000
BLOCK = 1600
WAIT_FOR_SPEECH = 20.0
SILENCE_TO_STOP = 1.5
MAX_SECONDS = 60.0
START_RMS = 0.012
KEEP_RMS = 0.006


def listen(max_seconds: float = MAX_SECONDS):
    import numpy as np
    import sounddevice as sd

    print("  تكلم… (أسجّل أول ما أسمعك، وأوقف لما تسكت)\n")

    frames = []
    started = False
    silence = waited = 0.0
    frame_sec = BLOCK / RATE

    with sd.InputStream(samplerate=RATE, blocksize=BLOCK, channels=1,
                        dtype="float32") as stream:
        while True:
            data, _ = stream.read(BLOCK)
            chunk = data[:, 0].copy()
            level = float(np.sqrt(np.mean(chunk ** 2)))

            if not started:
                waited += frame_sec
                if level >= START_RMS:
                    started = True
                    frames.append(chunk)
                elif waited >= WAIT_FOR_SPEECH:
                    print("  ما سمعت شي.")
                    return np.zeros(0, dtype="float32")
                continue

            frames.append(chunk)
            silence = silence + frame_sec if level < KEEP_RMS else 0.0
            spoken = len(frames) * frame_sec
            print(f"\r  🔴 أسمعك… {spoken:4.1f}s", end="", flush=True)

            if silence >= SILENCE_TO_STOP or spoken >= max_seconds:
                break

    print()
    return np.concatenate(frames) if frames else np.zeros(0, dtype="float32")


def transcribe(audio) -> str:
    from faster_whisper import WhisperModel

    model = WhisperModel("small", device="auto", compute_type="auto")
    segments, _info = model.transcribe(audio, language="ar", beam_size=3)
    return " ".join(s.text.strip() for s in segments).strip()


def main() -> None:
    if not ensure("sounddevice", "numpy"):
        return
    limit = MAX_SECONDS
    if len(sys.argv) > 1:
        try:
            limit = max(3.0, min(180.0, float(sys.argv[1])))
        except ValueError:
            pass

    print()
    print(f"  أسمعك يا {user_name()}")
    line("═")

    try:
        audio = listen(limit)
    except Exception as e:
        print(f"\n  ما قدرت أفتح المايك: {e}")
        return

    if len(audio) < RATE * 0.4:
        print("  ما وصلني كلام كافٍ.")
        return

    print("  أفرّغ…\n")
    try:
        text = transcribe(audio)
    except ImportError:
        print("  التفريغ يحتاج: pip install faster-whisper")
        return
    del audio

    if not text:
        print("  سمعت صوتاً بس ما قدرت أفهم الكلام.")
        return

    line()
    print("  قلت:\n")
    print("  " + text.replace("\n", "\n  "))
    print()


if __name__ == "__main__":
    main()
