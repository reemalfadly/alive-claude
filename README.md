<div align="center">

# 🫀 كلود حي · Alive Claude

**مهارة تعطي [Claude Code](https://claude.com/claude-code) حواسّاً على جهازك.**

يشوف شاشتك · يسمع اللي تشغّله · يسمعك من المايك · يشمّ المشاكل قبل ما تنكسر · يتحكّم بنوافذك · يلاحظ إيقاع يومك

مجاني بالكامل · مفتوح المصدر · كل شي يشتغل على جهازك

[التنزيل](#-التنزيل-بأمر-واحد) · [الحواس](#-الحواس-العشر) · [الخصوصيه](#-الخصوصيه-مبنيه-بالكود-مو-وعداً) · [English](#-english)

</div>

---

## 🤔 ليش؟

كلود كود يقرأ ملفاتك ويكتب كوداً — وهذا ممتاز. بس هو **أعمى وأطرش**.

تقول له «ليش هالزر ما يشتغل؟» فيسألك تلصق الكود. تقول له «الشاشه فيها خطأ
أحمر» فيسألك تكتبه بيدك. وأنت تشوفه قدامك.

هالمهاره تحلّ هذا: **تقول «شوف شاشتي» فيشوفها فعلاً.**

---

## ⚡ التنزيل بأمر واحد

```bash
git clone https://github.com/reemalfadly/alive-claude.git
cd alive-claude
python install.py
```

وبس. السكربت يسوي كل شي:

1. ينسخ المهاره لـ`~/.claude/skills/alive-claude/`
2. ينزّل المكتبات المطلوبه
3. يسألك عن **اسمك** ومفتاحك وكلمة التنبيه

بعدها **سكّر جلسة كلود كود وافتح وحده جديده**، وقل:

> **«شوف شاشتي»**

### ما عندك git؟

نزّل [ZIP](https://github.com/reemalfadly/alive-claude/archive/refs/heads/main.zip)،
فكّه، وشغّل `python install.py` جوّه المجلد.

### المفتاح

من [Google AI Studio](https://aistudio.google.com/apikey) — **مجاني وبلا بطاقه**.

بلا مفتاح: البصر والصوت الطبيعي يتعطّلون، و**باقي الحواس تشتغل عادي**.

---

## 🧠 الحواس العشر

| | الحاسه | تقول له | وش يسوي |
|---|---|---|---|
| 👁 | **البصر** | «شوف شاشتي» | يلتقط الشاشه ويحلّلها |
| 📖 | **القراءه الدقيقه** | «وش مكتوب» | يقرأ النص الصغير حرفياً — كود · ترجمه · أرقام |
| 🎬 | **المتابعه** | «تابع معاي هالمقطع» | عدة إطارات متتاليه ⇦ يفهم الحركه مو لقطه جامده |
| 🔍 | **المقارنه** | «احفظ قبل» ثم «وش تغيّر» | يقارن الشاشه بوقتين |
| 🎯 | **المنطقه** | «شوف الزاويه اليمنى» | جزء محدد بس — **ما يشوف بقية شاشتك** |
| 👂 | **السمع** | «وش مشغّل الحين» | يسمع مخرَج جهازك ويفرّغه نصاً |
| 🎤 | **الإصغاء** | «كلود اسمعني» | يسمعك من المايك ويرد بصوت طبيعي |
| 👃 | **الشمّ** | «شم لي» · «كل شي تمام؟» | **ينبّهك من نفسه** — ذاكره ممتلئه · قرص يخلص · برنامج متجمّد |
| ✋ | **اليد** | «احفظ» · «بدّل للكروم» | يتحكّم بالنوافذ والاختصارات |
| 🧠 | **الملاحظه** | «وش عاداتي» · «أنا مركّز؟» | يتعلّم إيقاع يومك ويسكت لما تكون مركّزاً |

### أمثله حقيقيه

```
أنت: شوف شاشتي، ليش هالخطأ؟
كلود: عندك ImportError بالسطر ٤٢ — ناقصك `pip install requests`.

أنت: تابع معاي المقطع ١٠ ثواني
كلود: شريط التحميل وصل ٦٠٪ ثم وقف، والرساله تغيّرت لـ"connection reset".

أنت: وش مشغّل الحين؟
كلود: بودكاست عن تصميم الواجهات — المتحدث يتكلم عن نظام الشبكه الثماني.

أنت: شم لي
كلود: ⚠ الذاكره ٩٤٪ والقرص D باقي ٣ قيقا. VS Code ما استجاب من ٤ دقايق.
```

---

## 🛡 الخصوصيه — مبنيه بالكود مو وعداً

| القاعده | كيف تُفرض |
|---|---|
| **ولا كلمه تنكتب قبل كلمة التنبيه** | اللي قبل «كلود اسمعني» يُفرَّغ محلياً ثم **يُرمى بلا حفظ** |
| **الصوت الخام ينمسح** | بعد التفريغ مباشره — ولا ثانيه تنحفظ |
| **التفريغ محلي بالكامل** | صوتك ما يطلع من جهازك أبداً |
| **ما تنحفظ لقطات** | إلا لقطة المقارنه الواحده، وتقدر تمسحها |
| **الحافظه ما تُخزَّن** | تُقرأ وتُرمى |
| **ما يكتب كلمات سر** | أي نص يشبه سراً يُرفض قبل ما ينكتب |
| **يتوقّف بالنوافذ الخاصه** | بنك · كلمة سر · تصفّح متخفٍّ |
| **ما يقاطعك وأنت مركّز** | يفحص انتباهك قبل أي تنبيه تلقائي |

**النداء الوحيد اللي يطلع من جهازك** هو البصر والصوت الطبيعي، ويروح لـ
Google AI Studio **بمفتاحك أنت**. ما فيه خادم وسيط، ولا تتبّع، ولا حساب.

إعداداتك — اسمك ومفتاحك — تنحفظ بـ`config.json` **عندك**، وهو مستثنى
من git أصلاً.

---

## 🖥 المتطلبات

| | |
|---|---|
| **النظام** | ويندوز ١٠ / ١١ — السمع واليد والرفيق يحتاجون ويندوز، والباقي يشتغل بكل مكان |
| **بايثون** | ٣.١٠ فأعلى |
| **المفتاح** | [Google AI Studio](https://aistudio.google.com/apikey) — مجاني |
| **اختياري** | كرت NVIDIA — يسرّع تفريغ الصوت |
| **اختياري** | `pip install faster-whisper` — تفريغ صوتي محلي (~١ قيقا أول مره) |

---

## 🔧 الاستخدام المباشر

المهاره تشتغل من داخل كلود كود بالكلام العادي، وتقدر تشغّلها يدوياً:

```bash
python senses/see.py                    # لقطه ووصف
python senses/see.py "ليش هالخطأ؟"      # سؤال محدد
python senses/see.py --text             # يقرأ النص حرفياً
python senses/see.py --clip 8           # يتابع ٨ ثواني
python senses/see.py --region يمين      # منطقه محدده
python senses/see.py --mark             # يحفظ «قبل»
python senses/see.py --diff             # وش تغيّر

python senses/hear.py 15                # يسمع مخرَج جهازك ١٥ ثانيه
python senses/mic.py                    # يسمعك
python senses/smell.py                  # فحص فوري
python senses/smell.py --watch          # مراقبه مستمره
python senses/voice.py "أهلاً"          # يتكلم

python companion.py                     # الرفيق العايم على سطح المكتب
```

---

## 🐛 لو صار عطل

| العطل | الحل |
|---|---|
| كلود ما يعرف المهاره | سكّر الجلسه وافتح وحده جديده |
| «ما فيه مفتاح» | `python setup.py` |
| الرؤيه ترجع 400 أو 404 | `python senses/_common.py --probe` — يفحص أي نموذج يقبل الصور بمفتاحك |
| ما يسمع المايك | تأكد إن ويندوز معطي بايثون إذن المايك |
| ما يسمع مخرَج الجهاز | `pip install soundcard` |
| ملف بايثون انكسر | `python guard.py --fix` |
| `python` يفتح متجر مايكروسوفت | استخدم `py` بدالها: `py install.py` |

> **`--probe` ليش مهم:** أسماء نماذج Google تتغيّر، والتخمين يكسر الرؤيه
> بصمت. هالأمر يرسل صوره تجريبيه لكل نموذج بمفتاحك ويقول لك أيّها يقبلها
> فعلاً — فالمهاره ما تنكسر لو تغيّرت الأسماء بعد سنه.

---

## 📁 الملفات

```
alive-claude/
├── SKILL.md              تعريف المهاره لكلود كود
├── README.md             هذا الملف
├── install.py            التنزيل بأمر واحد
├── setup.py              الإعداد — يسأل عن اسمك ومفتاحك
├── guard.py              حارس الصياغه — يمسك الملف المكسور ويصلّحه
├── companion.py          الرفيق العايم (أيقونة بكسل تقفز مع الحواس)
├── requirements.txt
├── docs/
│   └── guide.html        شرح مصوّر — افتحه بالمتصفح
└── senses/
    ├── _common.py        الأساس المشترك + فاحص النماذج
    ├── see.py            البصر — خمس قدرات
    ├── hear.py           يسمع مخرَج الجهاز (WASAPI loopback)
    ├── mic.py            يسمعك
    ├── voice.py          صوته
    ├── smell.py          يشمّ المشاكل
    ├── hand.py           يتحكّم بالنوافذ
    └── notice.py         يلاحظ عاداتك
```

---

## 🇬🇧 English

**Alive Claude** gives [Claude Code](https://claude.com/claude-code) senses on
your machine: it sees your screen, hears what you're playing, listens to your
microphone, senses problems before they break, controls your windows, and
learns your daily rhythm.

Free, open source, and everything runs locally — the only outbound call is
vision and natural voice, which goes to Google AI Studio with **your own** key.

### Install

```bash
git clone https://github.com/reemalfadly/alive-claude.git
cd alive-claude
python install.py
```

The installer copies the skill into `~/.claude/skills/alive-claude/`, installs
the dependencies, and asks for **your name**, your free
[Google AI Studio key](https://aistudio.google.com/apikey), and a wake phrase.

Restart Claude Code, then just say **"look at my screen"** — or use your own
language. The skill never assumes a name; it asks you and stores it in a local
`config.json` that is git-ignored.

### The ten senses

Sight · precise text reading · motion over several frames · before/after diff ·
region-only capture · system-audio hearing · microphone listening with a wake
phrase · anomaly sensing · window control · habit noticing.

### Privacy

Nothing is written before the wake phrase. Raw audio is deleted right after
local transcription. Transcription is fully local — your voice never leaves the
machine. No screenshots are kept except the one comparison reference.
Clipboard is read and discarded. Anything resembling a secret is refused.
It pauses on banking, password, and incognito windows.

### Requirements

Windows 10/11 (hearing, hand, and companion need Windows; the rest is portable),
Python 3.10+, and a free Google AI Studio key. Without a key, vision and natural
voice are disabled and every other sense still works.

---

<div align="center">

**صُنعت بواسطة م. ريم الفضلي**

[@iconReem](https://instagram.com/iconreem) · رخصة MIT

</div>
