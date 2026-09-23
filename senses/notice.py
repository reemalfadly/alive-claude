"""
حواس إضافيه — الملفات · الوقت والعاده · الانتباه · الحافظه · الشبكه.

كلها تشترك بمبدأ واحد: **تلاحظ بلا ما تزعج**. تشتغل بالخلفيه، تجمع
إشارات صغيره، وما تتكلم إلا لما يصير الشي يستاهل.

  📁 الملفات   يراقب مجلداتك ويعرف لما ينضاف أو ينحذف شي
  ⏰ الوقت     يتعلّم إيقاع يومك: متى تشتغل ومتى ترتاح
  🎯 الانتباه  يعرف متى تكون مركّزاً ومتى تائهاً بين النوافذ
  📋 الحافظه   يشوف اللي تنسخه (نصوص فقط، وما يحفظ الأسرار)
  🌐 الشبكه    يعرف إذا النت وقف أو التحميل خلص

الخصوصيه:
  · كل شي محلي — ولا حاسه ترسل شي لأي خدمه
  · الحافظه ما تحفظ أي شي يشبه كلمة سر أو بطاقه
  · تقدر توقف أي حاسه لحالها
"""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("alive.notice")

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = BASE_DIR / ".state"
STATE_DIR.mkdir(exist_ok=True)

_announce = None


def bind(announce=None) -> None:
    global _announce
    _announce = announce


def _say(message: str) -> None:
    if _announce:
        try:
            _announce(message)
        except Exception as e:
            logger.debug("تعذّر التنبيه: %s", e)
    else:
        logger.info(message)


# ══════════════════════════════════════════════════════
# 📁 حاسة الملفات
# ══════════════════════════════════════════════════════
class FileSense:
    """يراقب مجلدات ويعرف لما ينضاف ملف جديد.

    ما نستخدم مكتبة مراقبه خارجيه: مسح دوري بسيط أخف وأوثق على ويندوز،
    وما يحتاج تبعيات. المجلدات تُضبط من الإعدادات.
    """

    def __init__(self, folders: list[Path], patterns: tuple[str, ...] = ("*",),
                 every: float = 20.0) -> None:
        self.folders = [Path(f) for f in folders]
        self.patterns = patterns
        self.every = every
        self._seen: dict[str, set[str]] = {}
        self._running = threading.Event()
        self._on_new = None

    def on_new(self, fn) -> None:
        self._on_new = fn

    def _scan(self, folder: Path) -> set[str]:
        out: set[str] = set()
        if not folder.is_dir():
            return out
        try:
            for pat in self.patterns:
                for p in folder.glob(pat):
                    if p.is_file():
                        out.add(str(p))
        except OSError:
            pass
        return out

    def _loop(self) -> None:
        for f in self.folders:                  # أول مسح: نتعرّف بلا تنبيه
            self._seen[str(f)] = self._scan(f)

        while self._running.is_set():
            time.sleep(self.every)
            if not self._running.is_set():
                break
            for f in self.folders:
                key = str(f)
                now = self._scan(f)
                fresh = now - self._seen.get(key, set())
                self._seen[key] = now
                for path in sorted(fresh):
                    self._notify(Path(path))

    def _notify(self, path: Path) -> None:
        try:
            size_mb = path.stat().st_size / 2**20
        except OSError:
            return
        if size_mb < 0.02:                      # ملف مؤقت أو نصف مكتوب
            return
        logger.info("ملف جديد: %s (%.0f ميقا)", path.name, size_mb)
        if self._on_new:
            try:
                self._on_new(path, size_mb)
            except Exception as e:
                logger.debug("تعذّر إشعار الملف: %s", e)

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("حاسة الملفات شغّاله على %d مجلد", len(self.folders))

    def stop(self) -> None:
        self._running.clear()


# ══════════════════════════════════════════════════════
# ⏰ حاسة الوقت والعاده
# ══════════════════════════════════════════════════════
class HabitSense:
    """يتعلّم إيقاع يومك: أي ساعه تشتغل، وعلى أي برنامج.

    ما نحفظ محتوى — بس (اليوم، الساعه، اسم البرنامج). من هذا يعرف:
      «عادةً تبدأ المونتاج هالوقت» · «هذي أول مره تشتغل بهالساعه»
    """

    PATH = STATE_DIR / "habits.json"
    MIN_SAMPLES = 12                # قبلها ما نستنتج شي

    def __init__(self, every: float = 300.0) -> None:
        self.every = every
        self._running = threading.Event()

    def _load(self) -> dict:
        import json

        if not self.PATH.exists():
            return {"slots": {}}
        try:
            return json.loads(self.PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"slots": {}}

    def _save(self, data: dict) -> None:
        import json

        try:
            self.PATH.write_text(json.dumps(data, ensure_ascii=False),
                                 encoding="utf-8")
        except OSError:
            pass

    def _active_app(self) -> str:
        import ctypes

        try:
            u = ctypes.windll.user32
            hwnd = u.GetForegroundWindow()
            n = u.GetWindowTextLengthW(hwnd)
            if not n:
                return ""
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, b, n + 1)
            title = b.value
            # آخر جزء بعد الشرطه عادةً اسم البرنامج
            for sep in (" - ", " — ", " | "):
                if sep in title:
                    return title.rsplit(sep, 1)[-1].strip()[:40]
            return title[:40]
        except Exception:
            return ""

    def record(self) -> None:
        app = self._active_app()
        if not app:
            return
        now = datetime.now()
        slot = f"{now.weekday()}-{now.hour}"
        data = self._load()
        slots = data.setdefault("slots", {})
        bucket = slots.setdefault(slot, {})
        bucket[app] = bucket.get(app, 0) + 1
        self._save(data)

    def usual_now(self) -> str:
        """وش عادةً تسوي بهالوقت؟"""
        now = datetime.now()
        slot = f"{now.weekday()}-{now.hour}"
        data = self._load()
        bucket = data.get("slots", {}).get(slot, {})
        total = sum(bucket.values())
        if total < self.MIN_SAMPLES:
            return ""
        top = Counter(bucket).most_common(1)[0]
        if top[1] / total < 0.4:
            return ""
        return top[0]

    def summary(self) -> str:
        data = self._load()
        slots = data.get("slots", {})
        if not slots:
            return "لسه ما تعلّمت إيقاع يومك."

        total = sum(sum(b.values()) for b in slots.values())
        apps = Counter()
        hours = Counter()
        for slot, bucket in slots.items():
            hour = int(slot.split("-")[1])
            for app, n in bucket.items():
                apps[app] += n
                hours[hour] += n

        top_app = apps.most_common(1)[0][0] if apps else "—"
        busy = hours.most_common(3)
        times = "، و".join(f"{h}" for h, _ in busy)
        return (f"من {total} ملاحظه: أكثر شي تستخدم {top_app}، "
                f"وأنشط ساعاتك {times}.")

    def _loop(self) -> None:
        while self._running.is_set():
            time.sleep(self.every)
            if self._running.is_set():
                self.record()

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("حاسة الوقت شغّاله")

    def stop(self) -> None:
        self._running.clear()


# ══════════════════════════════════════════════════════
# 🎯 حاسة الانتباه
# ══════════════════════════════════════════════════════
class AttentionSense:
    """يعرف متى تكون مركّزاً ومتى تائهاً.

    الإشاره: كم مره تبدّل نافذه بالدقيقه.
      · نافذه وحده فتره طويله   ⇦ مركّز — لا تقاطعه
      · تبديل كثير بوقت قصير    ⇦ تائه — يمكن يحتاج مساعده
    """

    FOCUS_MIN = 90.0            # ثانيه بنفس النافذه = تركيز
    SCATTER_SWITCHES = 8        # تبديلات بالدقيقتين = تشتّت

    def __init__(self, every: float = 10.0) -> None:
        self.every = every
        self._switches: deque = deque(maxlen=60)
        self._last_title = ""
        self._since = time.time()
        self._running = threading.Event()

    def _title(self) -> str:
        import ctypes

        try:
            u = ctypes.windll.user32
            hwnd = u.GetForegroundWindow()
            n = u.GetWindowTextLengthW(hwnd)
            if not n:
                return ""
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, b, n + 1)
            return b.value
        except Exception:
            return ""

    def _loop(self) -> None:
        while self._running.is_set():
            time.sleep(self.every)
            if not self._running.is_set():
                break
            title = self._title()
            if title and title != self._last_title:
                self._switches.append(time.time())
                self._last_title = title
                self._since = time.time()

    def state(self) -> str:
        """يرجع: focused · scattered · normal"""
        now = time.time()
        recent = [t for t in self._switches if now - t < 120]
        if len(recent) >= self.SCATTER_SWITCHES:
            return "scattered"
        if now - self._since >= self.FOCUS_MIN:
            return "focused"
        return "normal"

    def describe(self) -> str:
        s = self.state()
        mins = int((time.time() - self._since) / 60)
        if s == "focused":
            return f"مركّز — صار لك {max(1, mins)} دقيقه بنفس الشغل."
        if s == "scattered":
            return "تبدّل بين النوافذ كثير — تبي أساعدك بشي؟"
        return "شغل عادي."

    def should_interrupt(self) -> bool:
        """هل يصح أقاطعه الحين؟ لا نقاطع المركّز."""
        return self.state() != "focused"

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("حاسة الانتباه شغّاله")

    def stop(self) -> None:
        self._running.clear()


# ══════════════════════════════════════════════════════
# 📋 حاسة الحافظه
# ══════════════════════════════════════════════════════
class ClipboardSense:
    """يشوف اللي تنسخه — نصوص فقط، وما يحفظ الأسرار.

    مفيده لأشياء مثل: «نسخت رابطاً، أفتحه؟» أو «هذا كود، أشرحه؟»
    وما تُخزَّن الحافظه إطلاقاً — نقرأها ونقرر ونرميها.
    """

    SECRET_HINTS = ("password", "كلمة السر", "كلمه السر", "api_key",
                    "secret", "token", "bearer ", "-----BEGIN")

    def __init__(self, every: float = 3.0) -> None:
        self.every = every
        self._last = ""
        self._running = threading.Event()
        self._on_copy = None

    def on_copy(self, fn) -> None:
        self._on_copy = fn

    def _read(self) -> str:
        import ctypes

        CF_UNICODETEXT = 13
        try:
            u = ctypes.windll.user32
            k = ctypes.windll.kernel32
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

    def _is_secret(self, text: str) -> bool:
        low = text.lower()
        if any(h in low for h in self.SECRET_HINTS):
            return True
        import re

        t = text.strip()
        # مفتاح أو رمز: سلسله طويله بلا مسافات فيها حروف وأرقام
        if 20 <= len(t) <= 200 and " " not in t:
            if re.search(r"[A-Za-z]", t) and re.search(r"\d", t):
                return True
        return False

    def kind(self, text: str) -> str:
        import re

        t = text.strip()
        if re.match(r"^https?://", t):
            return "رابط"
        if re.search(r"^\s*(def |class |import |function |const |<\w+)", t, re.M):
            return "كود"
        if len(t) > 400:
            return "نص طويل"
        return "نص"

    def _loop(self) -> None:
        self._last = self._read()               # أول قراءه بلا تنبيه
        while self._running.is_set():
            time.sleep(self.every)
            if not self._running.is_set():
                break
            text = self._read()
            if not text or text == self._last:
                continue
            self._last = text
            if self._is_secret(text):
                logger.info("تجاهلت نسخه تشبه سراً")
                continue
            if self._on_copy:
                try:
                    self._on_copy(text, self.kind(text))
                except Exception as e:
                    logger.debug("تعذّر إشعار الحافظه: %s", e)

    def current(self) -> str:
        text = self._read()
        if not text:
            return "الحافظه فاضيه."
        if self._is_secret(text):
            return "فيه شي بالحافظه بس يبان سراً — ما أقراه."
        kind = self.kind(text)
        preview = text.strip()[:160]
        return f"بالحافظه {kind}: {preview}"

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("حاسة الحافظه شغّاله")

    def stop(self) -> None:
        self._running.clear()


# ══════════════════════════════════════════════════════
# 🌐 حاسة الشبكه
# ══════════════════════════════════════════════════════
class NetworkSense:
    """يعرف إذا النت وقف أو رجع، وكم السرعه الحاليه."""

    def __init__(self, every: float = 30.0) -> None:
        self.every = every
        self._online = True
        self._running = threading.Event()
        self._on_change = None

    def on_change(self, fn) -> None:
        self._on_change = fn

    def _check(self) -> bool:
        import socket

        for host in ("1.1.1.1", "8.8.8.8"):
            try:
                socket.setdefaulttimeout(4)
                socket.create_connection((host, 53)).close()
                return True
            except OSError:
                continue
        return False

    def speed(self) -> str:
        """معدّل النقل الحالي من عدّادات النظام."""
        import psutil

        a = psutil.net_io_counters()
        time.sleep(1.0)
        b = psutil.net_io_counters()
        down = (b.bytes_recv - a.bytes_recv) / 1024
        up = (b.bytes_sent - a.bytes_sent) / 1024
        if down > 1024:
            return f"التحميل {down / 1024:.1f} ميقا/ث والرفع {up / 1024:.1f}"
        return f"التحميل {down:.0f} كيلو/ث والرفع {up:.0f}"

    def status(self) -> str:
        if not self._check():
            return "ما فيه نت."
        return f"النت شغّال. {self.speed()}"

    def _loop(self) -> None:
        while self._running.is_set():
            time.sleep(self.every)
            if not self._running.is_set():
                break
            online = self._check()
            if online == self._online:
                continue
            self._online = online
            if self._on_change:
                try:
                    self._on_change(online)
                except Exception:
                    pass

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("حاسة الشبكه شغّاله")

    def stop(self) -> None:
        self._running.clear()


# ══════════ تشغيل مباشر ══════════
if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _common import line, user_name

    args = sys.argv[1:]
    print()
    print("  حواس الملاحظه")
    line("═")

    if "--habits" in args or not args:
        h = HabitSense()
        print("  ⏰ العادات :", h.summary())
        usual = h.usual_now()
        if usual:
            print(f"     عادةً بهالوقت: {usual}")

    if "--clip" in args or not args:
        c = ClipboardSense()
        print("  📋 الحافظه:", c.current()[:120])

    if "--net" in args or not args:
        n = NetworkSense()
        print("  🌐 الشبكه :", n.status())

    if "--watch" in args:
        import time

        senses = [HabitSense(), AttentionSense(), ClipboardSense(), NetworkSense()]
        for s in senses:
            s.start()
        print(f"\nأراقب يا {user_name()}. (Ctrl+C يوقف)\n")
        try:
            while True:
                time.sleep(30)
                print(f"  🎯 {senses[1].describe()}")
        except KeyboardInterrupt:
            print("\nوقفت.\n")
    print()
