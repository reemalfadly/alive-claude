"""
الرفيق العايم — أيقونة كلود على سطح مكتبك، تقفز لما تشتغل حواسه.

    python companion.py

الحالات:
    نايم   رمادي · عيون مغمضه · zzz
    يسمع   أخضر · يقفز مع كل جمله
    يشوف   سماوي · حلقة مسح تدور
    يفكر   برتقالي · نقاط تدور

التحكّم:
    نقره      ⇦ لوح المحادثه
    سحب       ⇦ يتحرك، ويتذكر مكانه
    نقره يمين ⇦ قائمه

الخصوصيه:
    · المايك يسمع، بس **ما ينكتب شي قبل كلمة السر**
    · اللي قبلها يُفرَّغ محلياً ثم **يُرمى فوراً**
    · الصوت الخام ينمسح بعد التفريغ
    · التفريغ كله محلي — صوتك ما يطلع من جهازك
"""

from __future__ import annotations

import json
import logging
import math
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "senses"))

import _platform as plat  # noqa: E402
from _common import ask, config, line, user_name  # noqa: E402

HEARD = BASE / "heard.md"
POS = BASE / ".pet_pos.json"
LOG = BASE / "companion.log"

logging.basicConfig(filename=str(LOG), level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("companion")

RATE = 16_000
BLOCK = 1600
START_RMS = 0.012
KEEP_RMS = 0.006
SILENCE_TO_END = 1.2
MIN_SPEECH = 0.6
MAX_SPEECH = 45.0
WINDOW_SEC = 90.0

_wake = (config().get("wake_phrase") or "كلود اسمعني").strip()
WAKE_PHRASES = tuple({_wake, "كلود", "كلاود", "claude"})

# ── وضع السكوت ──
# «كلود اسكت» يسكّته تماماً: ما يرد، ما ينطق، وما يكتب شيئاً.
# ولا يرجع إلا بكلمة التنبيه **كامله** — مو بـ«كلود» وحدها، عشان
# ما يصحى لأن أحداً ذكر اسمه بالصدفه وانتِ مسكّتته عمداً.
HUSH_WITH_NAME = ("اسكت", "وقف", "بس", "اصمت", "خلاص", "stop", "quiet",
                  "shut up")
HUSH_ALONE = ("اسكت", "اصمت", "بس خلاص", "stop", "shut up")

PET = 96
CHROMA = "#0b0c10"
BODY = "#d9775a"
EYE = "#1a1410"
ACCENT = {"sleep": "#6b5a52", "listen": "#34d399",
          "see": "#38bdf8", "think": "#f0b27a"}

SPRITE = [
    "...........",
    "..#######..",
    "..#######..",
    "..#o###o#..",
    "..#o###o#..",
    "#.#######.#",
    "#.#######.#",
    "..#######..",
    "..#.#.#.#..",
    "..#.#.#.#..",
    "...........",
]

_events: queue.Queue = queue.Queue()
_voice = None

# مسكّت؟ Event مو bool عادي — الحلقه بخيط والواجهه بخيط ثاني.
_hushed = threading.Event()


def hush() -> None:
    """يسكّته فوراً — يقطع نطقه الحالي ويوقف كل رد."""
    _hushed.set()
    if _voice is not None:
        try:
            _voice.interrupt()      # يقطع اللي بنصّه ويفضّي الطابور
        except Exception:
            pass
    log.info("سكتّ — ما أرد لين تقول «%s»", _wake)


def unhush() -> None:
    _hushed.clear()
    log.info("رجعت أسمع")


# ══════════ كلمة السر ══════════
def _norm(t: str) -> str:
    import re

    t = re.sub(r"[ً-ْـ]", "", (t or "").lower())
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return re.sub(r"\s+", " ", t.replace("ة", "ه").replace("ى", "ي")).strip(" ،.؟!")


def _wake_match(text: str, strict: bool = False) -> tuple[bool, str]:
    """هل ناداني؟ يرجّع (نعم، باقي الكلام).

    `strict` يعني: كلمة التنبيه **كامله** بس. نستخدمه وهو مسكّت، عشان
    «كلود» العابره بحديث عادي ما تصحّيه وانتِ مسكّتته عمداً.
    """
    low = _norm(text)
    if not low:
        return False, ""
    words = low.split()
    phrases = (_wake,) if strict else WAKE_PHRASES
    for n in (4, 3, 2, 1):
        if len(words) < n:
            continue
        head = " ".join(words[:n])
        for phrase in phrases:
            p = _norm(phrase)
            if len(p.split()) == n and (
                    head == p or SequenceMatcher(None, head, p).ratio() >= 0.85):
                return True, " ".join(words[n:]).strip()
    return False, ""


def _hush_match(text: str) -> bool:
    """هل قالت لي «اسكت»؟

    نقبلها بصورتين:
      · باسمي   — «كلود اسكت» · «اسكت يا كلود» (بأي مكان بالجمله)
      · لحالها  — «اسكت» جمله كامله بكلمتين أو أقل

    ليش الشرط الثاني مقيّد: «اسكت» تجي داخل كلام عادي («قلت له اسكت»)،
    وما نبي نسكّته بالغلط. لو هي كل الجمله، فهي موجّهه لي.
    """
    low = _norm(text)
    if not low:
        return False

    words = low.split()
    has_name = any(SequenceMatcher(None, w, "كلود").ratio() >= 0.85
                   or w in ("claude", "كلاود") for w in words)
    if has_name and any(h in low for h in HUSH_WITH_NAME):
        return True
    if len(words) <= 2 and any(low == h or low.startswith(h + " ")
                               for h in HUSH_ALONE):
        return True
    return False


def _append(text: str) -> None:
    try:
        if not HEARD.exists():
            HEARD.write_text(f"# اللي سمعته — {datetime.now():%Y-%m-%d}\n\n",
                             encoding="utf-8")
        with HEARD.open("a", encoding="utf-8") as f:
            f.write(f"- **{datetime.now():%H:%M}** — {text}\n")
    except OSError:
        pass


# ══════════ الصوت والعقل ══════════
def _say(text: str) -> None:
    global _voice
    if not text or _hushed.is_set():
        return
    try:
        from voice import Voice

        if _voice is None:
            _voice = Voice()
        log.info("أنطق: %s", text[:70])
        _voice.say(text)
    except Exception as e:
        log.warning("تعذّر النطق: %s", e)


def speaking() -> bool:
    return bool(_voice and _voice.speaking)


SEE_HINTS = ("شوف", "شف", "انظر", "شاشتي", "على الشاشه")
TEXT_HINTS = ("اقرا", "اقرأ", "وش مكتوب", "شنو مكتوب")
CLIP_HINTS = ("تابع معاي", "تابع معي", "هالمقطع", "هذا المقطع")
DIFF_HINTS = ("وش تغير", "شنو تغير", "قارن", "شوف الفرق")
SMELL_HINTS = ("شم", "كل شي تمام", "فيه مشكله")
HEAR_HINTS = ("وش مشغل", "شنو مشغل", "وش الصوت")


def _think(text: str) -> str:
    """يرد — حاسه مناسبه، أو جواب من النموذج."""
    low = _norm(text)

    try:
        if any(h in low for h in CLIP_HINTS):
            _events.put(("state", "see"))
            from see import watch_clip

            return watch_clip(8.0, text)

        if any(h in low for h in TEXT_HINTS):
            _events.put(("state", "see"))
            from see import read_text

            return read_text(text)

        if any(h in low for h in DIFF_HINTS):
            _events.put(("state", "see"))
            from see import what_changed

            return what_changed(text)

        if any(h in low for h in SEE_HINTS):
            _events.put(("state", "see"))
            from see import describe

            return describe(text)

        if any(h in low for h in SMELL_HINTS):
            from smell import sniff

            alerts = sniff(force=True)
            return " ".join(alerts[:3]) if alerts else "كل شي تمام — ما أشمّ أي مشكله."

        if any(h in low for h in HEAR_HINTS):
            _events.put(("state", "listen"))
            from hear import record, transcribe

            audio = record(10.0)
            out = transcribe(audio)
            return f"اللي سمعته: {out}" if out else "ما فيه كلام واضح."
    except Exception as e:
        log.warning("تعذّرت الحاسه: %s", e)
        return f"ما قدرت أسويها: {e}"

    now = datetime.now()
    return ask(f"الوقت الحين {now:%H:%M} ليوم {now:%A}.\n\n{text}", 400)


def _respond(text: str) -> None:
    if _hushed.is_set():
        return

    def go() -> None:
        if _hushed.is_set():
            return
        _events.put(("state", "think"))
        log.info("أفكر بـ: %s", text[:60])
        reply = _think(text)
        log.info("ردي: %s", reply[:80])
        _events.put(("reply", reply))
        _say(reply)

    threading.Thread(target=go, daemon=True).start()


# ══════════ خيط السمع ══════════
def listen_forever() -> None:
    try:
        _listen_loop()
    except Exception as e:
        log.exception("انهار خيط السمع: %s", e)
        _events.put(("status", f"تعطّل السمع: {e}"))


def _listen_loop() -> None:
    import numpy as np
    import sounddevice as sd
    from faster_whisper import WhisperModel

    _events.put(("status", "أجهّز…"))
    model = WhisperModel("small", device="auto", compute_type="auto")
    _events.put(("ready", None))

    frames: list = []
    talking, silence = False, 0.0
    frame_sec = BLOCK / RATE
    awake_until = 0.0

    with sd.InputStream(samplerate=RATE, blocksize=BLOCK, channels=1,
                        dtype="float32") as stream:
        while True:
            data, _ = stream.read(BLOCK)
            chunk = data[:, 0].copy()
            level = float(np.sqrt(np.mean(chunk ** 2)))

            now = time.time()
            if awake_until and now > awake_until:
                awake_until = 0.0
                _events.put(("sleep", None))

            # ما نسجّل وإحنا نتكلم — وإلا سمعنا صوتنا وردّينا على أنفسنا
            if speaking():
                frames, talking, silence = [], False, 0.0
                continue

            if not talking:
                if level >= START_RMS:
                    talking, frames, silence = True, [chunk], 0.0
                continue

            frames.append(chunk)
            silence = silence + frame_sec if level < KEEP_RMS else 0.0
            spoken = len(frames) * frame_sec
            if silence < SILENCE_TO_END and spoken < MAX_SPEECH:
                continue

            audio = np.concatenate(frames)
            frames, talking, silence = [], False, 0.0
            if len(audio) / RATE < MIN_SPEECH:
                continue

            segments, _info = model.transcribe(audio, language="ar", beam_size=3)
            text = " ".join(s.text.strip() for s in segments).strip()
            del audio                       # ما نحتفظ بالصوت الخام

            if not text:
                continue

            # ── «اسكت» أولاً: تسبق كل شي، وتشتغل حتى وهو يرد ──
            if _hush_match(text):
                if not _hushed.is_set():
                    hush()
                    awake_until = 0.0
                    _events.put(("hush", None))
                continue

            # وهو مسكّت، ما يصحّيه إلا كلمة التنبيه كامله
            called, rest = _wake_match(text, strict=_hushed.is_set())
            if called:
                if _hushed.is_set():
                    unhush()
                awake_until = time.time() + WINDOW_SEC
                _events.put(("wake", None))
                if rest:
                    _events.put(("line", rest))
                    _append(rest)
                    _respond(rest)
                else:
                    _say(f"أسمعك يا {user_name()}.")
            elif _hushed.is_set():
                continue                # مسكّت — الكلام يُرمى بلا أثر
            elif awake_until:
                _events.put(("line", text))
                _append(text)
                _respond(text)
            # ما ناديتني؟ الكلام يُرمى — ما ينكتب ولا ينحفظ


# ══════════ الأيقونه ══════════
# لو النظام ما يدعم الشفافيه، نرسم على خلفيه داكنه بدل مربّع أخضر
FALLBACK_BG = "#0b1016"


class Pet:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Claude")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=CHROMA)

        # الشفافيه تختلف بين الأنظمه:
        #   ويندوز ← `-transparentcolor` يشيل لوناً محدداً بالضبط
        #   ماك    ← `-transparent` مع خلفية systemTransparent
        #   لينكس  ← ما فيه طريقه موحّده (يعتمد على مدير النوافذ)
        # لو ما نجحت، نخلّي خلفيه داكنه بدل مربّع ملوّن غريب.
        if not plat.make_transparent(self.root, CHROMA):
            self.root.configure(bg=FALLBACK_BG)
            try:
                self.root.attributes("-alpha", 0.92)
            except tk.TclError:
                pass

        self.canvas = tk.Canvas(self.root, width=PET, height=PET,
                                bg=self.root["bg"], highlightthickness=0)
        self.canvas.pack()

        self._place()
        self.state = "sleep"
        self.t = 0.0
        self.bounce = 0.0
        self._drag = None
        self._moved = False

        self.canvas.bind("<Button-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._menu)

        self.panel = Panel(self.root)
        self.root.after(33, self._tick)
        self.root.after(80, self._pump)

    def _place(self) -> None:
        x, y = 40, 40
        try:
            if POS.exists():
                d = json.loads(POS.read_text(encoding="utf-8"))
                x, y = int(d["x"]), int(d["y"])
        except Exception:
            pass
        self.root.geometry(f"{PET}x{PET}+{x}+{y}")

    def _save_pos(self) -> None:
        try:
            POS.write_text(json.dumps({"x": self.root.winfo_x(),
                                       "y": self.root.winfo_y()}),
                           encoding="utf-8")
        except OSError:
            pass

    def _press(self, e) -> None:
        self._drag = (e.x_root - self.root.winfo_x(),
                      e.y_root - self.root.winfo_y())
        self._moved = False

    def _move(self, e) -> None:
        if not self._drag:
            return
        self._moved = True
        self.root.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _release(self, _e) -> None:
        if self._drag and not self._moved:
            self.panel.toggle()
        elif self._drag:
            self._save_pos()
        self._drag = None

    def _menu(self, e) -> None:
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="إظهار / إخفاء اللوح", command=self.panel.toggle)
        m.add_separator()
        m.add_command(label="خروج", command=self.root.destroy)
        m.tk_popup(e.x_root, e.y_root)

    def set_state(self, state: str, jump: bool = False) -> None:
        self.state = state
        if jump:
            self.bounce = 1.0

    def _tick(self) -> None:
        self.t += 0.033
        self.bounce *= 0.90
        self._draw()
        self.root.after(33, self._tick)

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")
        accent = ACCENT[self.state]

        cols, rows = len(SPRITE[0]), len(SPRITE)
        cell = PET / cols
        breathe = math.sin(self.t * (3.6 if self.state != "sleep" else 1.2))
        hop = self.bounce * 12 + (breathe * 1.2 if self.state != "sleep" else 0)
        squash = 1.0 - self.bounce * 0.12

        off_x = (PET - cols * cell) / 2
        off_y = (PET - rows * cell) / 2 - hop
        blink = self.state == "sleep" or math.sin(self.t * 0.9) > 0.985

        for ry, row in enumerate(SPRITE):
            for rx, ch in enumerate(row):
                if ch == ".":
                    continue
                x0 = off_x + rx * cell
                y0 = off_y + ry * cell * squash
                x1, y1 = x0 + cell + 0.6, y0 + cell * squash + 0.6

                if ch == "#":
                    c.create_rectangle(x0, y0, x1, y1, fill=BODY, outline="")
                elif ch == "o":
                    if blink:
                        mid = (y0 + y1) / 2
                        c.create_rectangle(x0, mid - 1, x1, mid + 1,
                                           fill=EYE, outline="")
                    else:
                        eye = accent if self.state in ("see", "listen") else EYE
                        c.create_rectangle(x0, y0, x1, y1, fill=eye, outline="")

        cx, cy = PET / 2, PET / 2 - hop

        if self.state == "listen":
            for i in range(3):
                a = 9 + i * 7 + abs(breathe) * 4
                for sign in (-1, 1):
                    c.create_arc(cx + sign * 30 - a, cy - a,
                                 cx + sign * 30 + a, cy + a,
                                 start=(0 if sign > 0 else 180) - 32, extent=64,
                                 style="arc", outline=accent, width=2)
        elif self.state == "see":
            c.create_arc(cx - 37, cy - 37, cx + 37, cy + 37,
                         start=(self.t * 160) % 360, extent=72,
                         style="arc", outline=accent, width=3)
        elif self.state == "think":
            for i in range(3):
                a = self.t * 3.0 + i * 2.1
                dx, dy = math.cos(a) * 36, math.sin(a) * 36
                c.create_oval(cx + dx - 3, cy + dy - 3, cx + dx + 3, cy + dy + 3,
                              fill=accent, outline="")
        elif self.state == "sleep":
            for i, (dx, dy, sz) in enumerate(((22, -24, 10), (30, -33, 8))):
                if math.sin(self.t * 1.2 + i * 1.4) > 0:
                    c.create_text(cx + dx, cy + dy, text="z",
                                  fill=accent, font=("Segoe UI", sz, "bold"))

    def _pump(self) -> None:
        try:
            while True:
                kind, payload = _events.get_nowait()

                if kind == "status":
                    self.panel.head(str(payload), "#9aa7c2")
                elif kind == "ready":
                    self.panel.log(f"جاهز. قل «{_wake}».")
                elif kind == "hush":
                    self.pet.set_state("sleep")
                    self.panel.head(f"مسكّت — قل «{_wake}»", "#8b5a52")
                    self.panel.log("سكتّ. ما أرد لين تناديني.")
                elif kind == "wake":
                    self.set_state("listen", jump=True)
                    self.panel.show()
                    self.panel.head(f"أسمعك يا {user_name()} 🎤", "#34d399")
                    self.panel.log("— أسمعك —")
                elif kind == "line":
                    self.set_state("listen", jump=True)
                    self.panel.log(str(payload))
                elif kind == "reply":
                    self.set_state("listen")
                    self.panel.log(f"كلود: {payload}")
                elif kind == "state":
                    self.set_state(str(payload), jump=True)
                elif kind == "sleep":
                    self.set_state("sleep")
                    self.panel.head(f"نايم — قل «{_wake}»", "#6b5a52")
                    self.panel.log("— رجعت أنام —")
                    self.root.after(1600, self.panel.hide)
        except queue.Empty:
            pass
        self.root.after(80, self._pump)

    def run(self) -> None:
        self.root.mainloop()


class Panel:
    def __init__(self, master: tk.Tk) -> None:
        self.win = tk.Toplevel(master)
        self.win.title("كلود")
        self.win.configure(bg="#080e16")
        self.win.geometry("430x270")
        self.win.attributes("-topmost", True)
        self.win.protocol("WM_DELETE_WINDOW", self.hide)

        self.title = tk.Label(self.win, text=f"نايم — قل «{_wake}»",
                              bg="#080e16", fg="#6b5a52",
                              font=("Segoe UI", 12), pady=10)
        self.title.pack(fill="x")

        self.box = tk.Text(self.win, bg="#04070b", fg="#d8f3fb",
                           font=("Segoe UI", 11), wrap="word",
                           relief="flat", padx=12, pady=8)
        self.box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.box.tag_configure("rtl", justify="right")
        self.box.configure(state="disabled")
        self.win.withdraw()
        self._shown = False

    def head(self, text: str, color: str) -> None:
        self.title.configure(text=text, fg=color)

    def log(self, text: str) -> None:
        self.box.configure(state="normal")
        self.box.insert("end", f"{datetime.now():%H:%M}  {text}\n", "rtl")
        self.box.see("end")
        self.box.configure(state="disabled")

    def show(self) -> None:
        self.win.deiconify()
        self.win.lift()
        self._shown = True

    def hide(self) -> None:
        self.win.withdraw()
        self._shown = False

    def toggle(self) -> None:
        self.hide() if self._shown else self.show()


def main() -> None:
    if not (config().get("name") or "").strip():
        print("\n  شغّل setup.py أول عشان أعرف اسمك.\n")
        return
    threading.Thread(target=listen_forever, daemon=True).start()
    Pet().run()


if __name__ == "__main__":
    main()
