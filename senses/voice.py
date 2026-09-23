"""
صوت كلود — نطق طبيعي عبر Gemini.

    python voice.py "أي نص تبي أقوله"

ليش Gemini مو المحرك المجاني العادي:
  المحركات المجانيه صوتها آلي وتقطّع وتقرأ اللهجات بالفصحى. نطق Gemini
  صوت بشري ومقطع واحد متصل. عيبه الوحيد حصه يوميه — ولو خلصت ما نسكت،
  نرجع للمجاني تلقائياً.

قصّ الضجه:
  نماذج النطق أحياناً تختم بطقّه («تششش») بعد آخر كلمه. قِسنا الصوت
  فطلع: [كلام] … [صمت] … [انفجار قصير]. نلقى الفجوه ونقص من عندها.
"""

from __future__ import annotations

import base64
import logging
import queue
import sys
import threading
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import API, TIMEOUT, api_key, config  # noqa: E402

logger = logging.getLogger("alive.voice")

OUT_RATE = 24_000
MAX_CHARS = 900

# بالترتيب: الأسرع أولاً، ولو ازدحم أو خلصت حصته ننتقل للي بعده
MODELS = [
    "gemini-3.8-flash-lite-tts",
    "gemini-3.8-flash-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-preview-tts",
]

FRAME_MS = 20
GAP_FRAMES = 6            # صمت ١٢٠ مث = فاصل حقيقي
BURST_MAX_FRAMES = 20     # انفجار أقصر من ٤٠٠ مث = ضجه مو كلام

_quota_until = 0.0
_lock = threading.Lock()


def voice_name() -> str:
    return (config().get("voice") or "Puck").strip()


def _trim_tail(audio):
    """يقصّ الضجه اللي تجي بعد آخر كلمه.

    ندوّر **فجوة صمت قرب النهايه**، ولو بعدها مقطع قصير نعتبره ضجه
    ونقص من بداية الفجوه. ولو ما فيه فجوه نقص الصمت العادي بس.
    """
    import numpy as np

    if len(audio) < OUT_RATE // 10:
        return audio

    win = int(OUT_RATE * FRAME_MS / 1000)
    n = len(audio) // win
    if n < 8:
        return audio

    energy = np.sqrt(np.mean(audio[: n * win].reshape(n, win) ** 2, axis=1))
    floor = float(np.max(energy)) * 0.06
    loud = energy > floor
    if not loud.any():
        return audio

    end_frame = int(np.where(loud)[0][-1]) + 1

    silent = np.where(~loud[:end_frame])[0]
    if len(silent):
        run_end = int(silent[-1])
        run_start = run_end
        while run_start > 0 and not loud[run_start - 1]:
            run_start -= 1
        gap = run_end - run_start + 1
        tail = end_frame - run_end - 1
        if gap >= GAP_FRAMES and 0 < tail <= BURST_MAX_FRAMES:
            end_frame = run_start

    end = min(len(audio), max(int(end_frame * win) + win, OUT_RATE // 5))
    cut = audio[:end].copy()

    fade = min(len(cut), OUT_RATE // 25)
    if fade > 8:
        cut[-fade:] *= np.linspace(1.0, 0.0, fade, dtype="float32")
    return cut


def synth(text: str):
    """يرجع الصوت كـfloat32، أو None لو ما نفع."""
    global _quota_until
    import numpy as np
    import requests

    with _lock:
        if time.time() < _quota_until:
            return None

    key = api_key()
    if not key:
        return None

    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name()}}
            },
        },
    }

    for model in MODELS:
        try:
            r = requests.post(f"{API}/{model}:generateContent?key={key}",
                              json=payload, timeout=TIMEOUT)
            if r.status_code in (429, 500, 503):
                continue
            r.raise_for_status()
            data = (r.json()["candidates"][0]["content"]["parts"][0]
                    ["inlineData"]["data"])
            pcm = base64.b64decode(data)
            audio = np.frombuffer(pcm, dtype=np.int16).astype("float32") / 32768.0
            return _trim_tail(audio)
        except Exception as e:
            logger.debug("تعذّر %s: %s", model, e)
            continue

    with _lock:
        _quota_until = time.time() + 3600
    logger.info("نطق Gemini مو متاح — أرجع للمجاني ساعه")
    return None


def _split(text: str) -> list[str]:
    import re

    text = (text or "").strip()
    if len(text) <= MAX_CHARS:
        return [text] if text else []
    parts, buf = [], ""
    for piece in re.split(r"(?<=[.!؟?،])\s+", text):
        if len(buf) + len(piece) > MAX_CHARS and buf:
            parts.append(buf.strip())
            buf = piece
        else:
            buf = f"{buf} {piece}".strip()
    if buf:
        parts.append(buf.strip())
    return parts


class Voice:
    """مشغّل صوت — يتكلم بالترتيب ويسكت فوراً لو قاطعته."""

    def __init__(self) -> None:
        self._q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._speaking = False
        self._last = 0.0
        threading.Thread(target=self._loop, daemon=True).start()

    @property
    def speaking(self) -> bool:
        return self._speaking or (time.time() - self._last) < 0.35

    def say(self, text: str) -> None:
        for part in _split(text):
            self._q.put(part)

    def interrupt(self) -> None:
        self._stop.set()
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break

    def _speak_free(self, text: str) -> None:
        """الاحتياطي المجاني بلا حدود."""
        try:
            import asyncio
            import tempfile

            import edge_tts

            fallback = config().get("fallback_voice") or "ar-SA-HamedNeural"
            path = Path(tempfile.gettempdir()) / "alive_tts.mp3"

            async def go() -> None:
                await edge_tts.Communicate(text, fallback).save(str(path))

            asyncio.run(go())
            self._play_file(path)
        except Exception as e:
            logger.warning("تعذّر النطق الاحتياطي: %s", e)

    def _play_file(self, path: Path) -> None:
        import subprocess

        try:
            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError:
            import os

            os.startfile(str(path))

    def _loop(self) -> None:
        while True:
            text = self._q.get()
            self._stop.clear()
            self._speaking = True
            try:
                audio = synth(text)
                if audio is not None and len(audio):
                    self._play(audio)
                else:
                    self._speak_free(text)
            except Exception as e:
                logger.warning("تعذّر النطق: %s", e)
            self._last = time.time()
            self._speaking = False

    def _play(self, audio) -> None:
        import sounddevice as sd

        chunk = 2048
        with sd.OutputStream(samplerate=OUT_RATE, channels=1,
                             dtype="float32") as out:
            for i in range(0, len(audio), chunk):
                if self._stop.is_set():
                    break
                out.write(audio[i:i + chunk])


def save_wav(audio, path: str) -> None:
    import numpy as np

    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(OUT_RATE)
        w.writeframes(pcm)


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or "أهلاً! أنا كلود، وهذا صوتي."
    print(f"\n  الصوت: {voice_name()}")
    v = Voice()
    v.say(text)
    time.sleep(0.5)
    while v.speaking:
        time.sleep(0.2)
    print("  خلصت.\n")
