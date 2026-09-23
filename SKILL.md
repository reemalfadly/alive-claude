---
name: alive-claude
description: كلود حي — يعطي كلود كود حواسّاً على جهاز المستخدم، Alive Claude gives Claude Code senses on the user's machine. ALWAYS use this skill when the user asks Claude to see, look at, read, or watch their screen; to hear what is playing on their machine; to listen to their microphone; to sense or check whether anything is wrong; to control their windows; or to notice their habits. Arabic triggers "كلود حي"، "شوف شاشتي"، "وش على الشاشه"، "وش مكتوب"، "وش تغيّر"، "تابع معاي هالمقطع"، "شوف الزاويه اليمنى"، "وش مشغّل"، "اسمع اللي مشغّله"، "كلود اسمعني"، "شم لي"، "كل شي تمام؟"، "وش عاداتي"، "أنا مركّز؟"، "نزّل كلود حي"، "فعّل الحواس". English triggers "look at my screen", "what's on my screen", "read my screen", "what changed on screen", "watch my screen", "what am I playing", "listen to my mic", "sense my machine", "is anything wrong with my computer", "install alive claude". Works on Windows with a free Google AI Studio key; everything runs locally except the vision and natural-voice calls.
---

# كلود حي — حواس على جهاز المستخدم

كلود كود يقرأ الملفات ويكتب كوداً، بس هو **أعمى وأطرش**. هالمهاره
تعطيه عشر حواس تشتغل على جهاز المستخدم نفسه.

**مكان المهاره:** `~/.claude/skills/alive-claude/`
شغّل كل الأوامر من داخل هالمجلد.

---

## ⚡ أول شي — اسأل عن اسمه

**قبل أي حاسه، افحص الإعدادات:**

```bash
python senses/_common.py
```

لو طبع `الاسم : صديقي` يعني ما فيه اسم محفوظ. **اسأل المستخدم:**

> «أهلاً! أنا كلود. وش أناديك؟»

وشغّل `python setup.py` أو اكتب الاسم بـ`config.json` مباشره.

**لا تفترض أي اسم أبداً.** لا من اسم المستخدم بويندوز، ولا من مجلداته،
ولا من أي مثال بهالملف. الاسم يجي من المستخدم نفسه أو من `config.json` فقط.

---

## 🧠 الحواس

### 👁 البصر — خمس قدرات

```bash
python senses/see.py                      # لقطه ووصف
python senses/see.py "ليش هالخطأ؟"        # سؤال محدد
python senses/see.py --text               # يقرأ النص حرفياً (كود · ترجمه · أرقام)
python senses/see.py --clip 8             # يتابع ٨ ثواني ⇦ يفهم الحركه
python senses/see.py --region يمين        # منطقه محدده بس
python senses/see.py --mark               # يحفظ لقطة «قبل»
python senses/see.py --diff               # وش تغيّر من «قبل»
```

**اختر الصح:**

| لو المستخدم قال | استخدم | ليش |
|---|---|---|
| «وش على الشاشه» | بلا خيارات | لقطه وحده تكفي |
| «وش مكتوب» · «اقرأ هالكود» | `--text` | التصغير للعرض يضيّع الحروف الصغيره |
| «تابع» · «وش صار» · «شوف الحركه» | `--clip` | اللقطه الواحده ما تشوف الحركه |
| «وش تغيّر» | `--mark` ثم `--diff` | يحتاج صورتين مو وحده |
| «الزاويه» · «الجزء الفلاني» | `--region` | أدق وأرخص، **وما يشوف بقية شاشته** |

المناطق: `يمين` `يسار` `فوق` `تحت` `وسط` `زاويه يمين فوق` `زاويه يسار تحت` …

### 👂 السمع — مخرَج الجهاز

```bash
python senses/hear.py 15          # يسمع ١٥ ثانيه ويفرّغها
```

يلتقط اللي **يطلع من السماعات** — فيديو · بودكاست · أغنيه · اجتماع.
ويندوز فقط (WASAPI loopback). التفريغ محلي بالكامل.

### 🎤 الإصغاء — المايك

```bash
python senses/mic.py              # يسمع لين تسكت
```

**ولا كلمه تنكتب قبل كلمة التنبيه.** اللي قبلها يُفرَّغ ويُرمى.
الصوت الخام ينمسح بعد التفريغ مباشره.

### 🗣 الصوت

```bash
python senses/voice.py "أهلاً"
```

### 👃 الشمّ — يكشف قبل ما تنكسر

```bash
python senses/smell.py            # فحص فوري
python senses/smell.py --watch    # مراقبه مستمره
```

ذاكره ممتلئه · قرص يخلص · برنامج متجمّد · معالج محترق · شبكه مقطوعه.

**هذي الحاسه الوحيده اللي تتكلم من نفسها.** قبل أي تنبيه تلقائي، افحص
انتباه المستخدم — لو مركّز من فتره، **اسكت**.

### ✋ اليد

```bash
python senses/hand.py --switch chrome
python senses/hand.py --key "ctrl+s"
```

### 🧠 الملاحظه

```bash
python senses/notice.py
```

---

## 🛑 قواعد صارمه — لا تكسرها

### ١. الخصوصيه فوق كل شي

| القاعده | السبب |
|---|---|
| **ما نسجّل قبل كلمة التنبيه** | المايك يسمع، بس ما ينكتب شي قبلها |
| **الصوت الخام ينمسح** | بعد التفريغ مباشره |
| **ما نحفظ لقطات** | إلا لقطة المقارنه الواحده |
| **الحافظه ما تُخزَّن** | تُقرأ وتُرمى |
| **ما نكتب كلمات سر** | أي نص يشبه سراً يُرفض |
| **نتوقّف بالنوافذ الخاصه** | بنك · كلمة سر · تصفّح متخفٍّ |

### ٢. ما ننادي أحداً باسم ما قاله

الاسم من `config.json` فقط. لو فاضي، **اسأل**.

### ٣. ما ندّعي التنفيذ

لا تقل «تم» إلا بعد ما ترجع الأداه نتيجه فعليه. لو رجّعت خطأ، **قل الخطأ**.

### ٤. ما نقاطع المركّز

قبل أي تنبيه تلقائي، تأكد إن المستخدم مو مركّزاً.

---

## 🔑 المفتاح

البصر والصوت الطبيعي يحتاجون مفتاح [Google AI Studio](https://aistudio.google.com/apikey)
— مجاني وبلا بطاقه.

**بلا مفتاح:** الشمّ واليد والملاحظه تشتغل عادي، والبصر والصوت يتعطّلون
برساله واضحه.

لو رجعت الرؤيه `400` أو `404`، أسماء النماذج تغيّرت:

```bash
python senses/_common.py --probe
```

يرسل صوره تجريبيه لكل نموذج بمفتاح المستخدم ويطبع اللي يقبلها فعلاً —
حطّها بـ`VISION_MODELS` داخل `senses/_common.py`.

---

## 🧯 لو انكسر ملف بايثون

```bash
python guard.py            # فحص
python guard.py --fix      # إصلاح
```

يمسك السلاسل المكسوره اللي تصير لما يتعدّل ملف بسكربت.

---

## 📁 الملفات

```
alive-claude/
├── SKILL.md              ← هذا الملف
├── README.md             شرح التنزيل
├── install.py            التنزيل بأمر واحد
├── setup.py              الإعداد — يسأل عن الاسم والمفتاح
├── guard.py              حارس الصياغه
├── companion.py          الرفيق العايم
├── config.json           إعدادات المستخدم (يُنشأ تلقائياً، git يتجاهله)
└── senses/
    ├── _common.py        الأساس + `--probe`
    ├── see.py            البصر
    ├── hear.py           مخرَج الجهاز
    ├── mic.py            المايك
    ├── voice.py          الصوت
    ├── smell.py          الشمّ
    ├── hand.py           اليد
    └── notice.py         الملاحظه
```

---

**صُنعت بواسطة م. ريم الفضلي — [@iconReem](https://instagram.com/iconreem) · MIT**
