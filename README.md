# بلوك هَب (Block Hub)

منصة عربية خفيفة وسريعة لاكتشاف مودات Minecraft، Resource Packs، Shaders، وData Packs.
البيانات تُجلب تلقائيًا من [Modrinth](https://modrinth.com) عبر GitHub Actions، ويُولَّد
ملف `index.html` مباشرة بدون أي قاعدة بيانات أو ملفات وسيطة.

```
Modrinth API  →  bot.py  →  index.html
```

## بنية المشروع

```
block-hub/
├── index.html          # الموقع النهائي (يُولَّد تلقائيًا من bot.py)
├── bot.py              # يجلب البيانات من Modrinth ويبني index.html
├── requirements.txt    # متطلبات Python
├── README.md
└── .github/
    └── workflows/
        └── update.yml  # يشغّل bot.py كل 15 دقيقة تلقائيًا
```

لا يحتوي المشروع على `mods_data.json` ولا Firebase ولا GitLab ولا أي قاعدة بيانات خارجية.

---

## الخطوة 1: إنشاء GitHub Repository

1. افتح [github.com/new](https://github.com/new).
2. اختر اسمًا للمستودع، مثلًا: `block-hub`.
3. اجعله **Public** (أو Private إن رغبت، Cloudflare Pages يدعم كليهما).
4. لا تُفعّل خيار "Add a README file" لأنك سترفع الملفات الجاهزة بنفسك.
5. اضغط **Create repository**.

## الخطوة 2: رفع الملفات

من جهازك، داخل مجلد المشروع `block-hub`:

```bash
git init
git add .
git commit -m "النسخة الأولى من بلوك هَب"
git branch -M main
git remote add origin https://github.com/USERNAME/block-hub.git
git push -u origin main
```

استبدل `USERNAME` باسم حسابك على GitHub.

## الخطوة 3: إنشاء Secret باسم MODRINTH_USER_AGENT

Modrinth تطلب User-Agent واضح يحدد هوية تطبيقك (بدون أي مفتاح سري فعلي):

1. داخل المستودع على GitHub، اذهب إلى **Settings**.
2. من القائمة الجانبية: **Secrets and variables** → **Actions**.
3. اضغط **New repository secret**.
4. **Name**: `MODRINTH_USER_AGENT`
5. **Value**: مثال:
   ```
   USERNAME/block-hub/1.0 (your-email@example.com)
   ```
   استبدل `USERNAME` وبريدك الإلكتروني بمعلوماتك الحقيقية (Modrinth توصي بذلك
   لسهولة التواصل في حال وجود مشكلة).
6. اضغط **Add secret**.

> ملاحظة: هذا المتغير ليس توكن سري حساس، لكن استخدام Secret يسمح لك بتغييره
> بسهولة دون تعديل الكود.

## الخطوة 4: فتح Actions

1. من أعلى صفحة المستودع، اضغط تبويب **Actions**.
2. إذا ظهرت رسالة تفعيل Workflows، اضغط **I understand my workflows, go ahead
   and enable them**.
3. ستجد في القائمة الجانبية اسم الـ workflow: **Update Block Hub Content**.

## الخطوة 5: تشغيل Workflow يدويًا (Run workflow)

1. اضغط على **Update Block Hub Content** من القائمة الجانبية.
2. اضغط زر **Run workflow** (على اليمين) → ثم **Run workflow** للتأكيد.
3. انتظر بضع ثوانٍ وسيبدأ تشغيل جديد باللون الأصفر (قيد التنفيذ).

## الخطوة 6: التأكد من نجاح البوت

1. اضغط على التشغيل الحالي لرؤية التفاصيل.
2. افتح خطوة **Run bot (fetch Modrinth data and generate index.html)** وتأكد
   من عدم وجود أخطاء حمراء، وأن السجلات تُظهر عدد العناصر التي جُلبت لكل قسم.
3. علامة ✅ خضراء تعني نجاح التشغيل بالكامل.
4. إذا نجح البوت وكان هناك تغيير في المحتوى، ستجد commit جديد تلقائي في
   تبويب **Code** بعنوان: `chore: تحديث تلقائي للمحتوى من Modrinth`.

## الخطوة 7: ربط Cloudflare Pages

1. افتح [dash.cloudflare.com](https://dash.cloudflare.com).
2. من القائمة الجانبية: **Workers & Pages** → **Create application** →
   تبويب **Pages** → **Connect to Git**.
3. اختر حساب GitHub الخاص بك وامنح Cloudflare صلاحية الوصول إلى مستودع
   `block-hub` (أو كل مستودعاتك).
4. اختر مستودع `block-hub` واضغط **Begin setup**.

## الخطوة 8: إعداد Build في Cloudflare Pages

في صفحة إعدادات البناء، ضع بالضبط:

| الحقل | القيمة |
|---|---|
| **Production branch** | `main` |
| **Framework preset** | `None` |
| **Build command** | اتركه **فارغًا** (الموقع HTML/CSS/JS ثابت، لا يحتاج بناء) |
| **Build output directory** | `/` |
| **Root directory** | `/` (اتركه كما هو) |

اضغط **Save and Deploy**. سينتظر Cloudflare حتى ينسخ الملفات وينشرها مباشرة
دون أي خطوة بناء إضافية.

بعد هذا الإعداد، كل commit جديد يصل إلى فرع `main` (سواء منك يدويًا أو من
البوت تلقائيًا) سيؤدي إلى إعادة نشر تلقائي للموقع على Cloudflare Pages.

## الخطوة 9: فتح رابط الموقع

بعد انتهاء أول عملية نشر (Deployment)، سيعطيك Cloudflare رابطًا تلقائيًا
بالشكل:

```
https://block-hub.pages.dev
```

(أو باسم قريب منه إذا كان الاسم مستخدمًا من قبل — يمكنك رؤية الرابط الدقيق
داخل تبويب **Deployments** في مشروعك على Cloudflare Pages).

---

## إضافة نطاق مخصص (Custom Domain)

1. داخل مشروعك في Cloudflare Pages، اذهب إلى تبويب **Custom domains**.
2. اضغط **Set up a custom domain**.
3. اكتب نطاقك، مثل: `blockhub.com` أو `www.blockhub.com`.
4. إذا كان النطاق مُدارًا عبر Cloudflare مسبقًا، ستتم الإضافة تلقائيًا.
   إن لم يكن كذلك، اتبع تعليمات إضافة سجلات DNS (CNAME) التي يعرضها
   Cloudflare.
5. انتظر بضع دقائق حتى يتم تفعيل الشهادة (SSL) تلقائيًا.

## إيقاف التحديث التلقائي أو تغيير توقيته

توقيت التحديث موجود في الملف:

```
.github/workflows/update.yml
```

في السطر:

```yaml
schedule:
  - cron: "*/15 * * * *"
```

- **لتغيير التوقيت**: عدّل تعبير cron. مثلًا كل 30 دقيقة: `*/30 * * * *`،
  أو كل ساعة: `0 * * * *`.
- **لإيقاف التحديث التلقائي كليًا**: احذف قسم `schedule` بالكامل (أو ضع
  علامة `#` في بداية كل سطر منه)، مع الإبقاء على `workflow_dispatch` إن
  أردت الاستمرار في التشغيل اليدوي فقط.
- بعد أي تعديل، اعمل commit و push للتغيير على فرع `main`.

يمكنك أيضًا تعطيل الـ workflow مؤقتًا دون تعديل الكود: من تبويب **Actions** →
اختر **Update Block Hub Content** → الثلاث نقاط (⋯) أعلى اليمين → **Disable
workflow**.

---

## ملاحظات تقنية

- **لا توجد أي مفاتيح سرية داخل الكود**. الـ `GITHUB_TOKEN` المستخدم لعمل
  push هو التوكن المدمج تلقائيًا في كل تشغيل لـ GitHub Actions، ولا حاجة
  لإنشاء Personal Access Token يدويًا.
- **الحماية من تعارضات Git (Merge Conflicts)**: بما أن `index.html` يُولَّد
  بالكامل من `bot.py` في كل تشغيل، والـ workflow يستخدم `concurrency` لمنع
  تشغيل نسختين في نفس الوقت، فلا يحدث تعارض على هذا الملف. كما أن الـ
  workflow يزامن الفرع (`git fetch` + `git merge --ff-only`) قبل أي commit،
  وبما أنه المصدر الوحيد للتعديل على `index.html`، فالدمج يكون دائمًا
  Fast-Forward بدون تعارض.
- **الأمان عند فشل Modrinth**: إذا فشل الاتصال بـ Modrinth بالكامل (صفر
  عناصر من كل الأقسام)، يتوقف البوت دون أي تعديل على `index.html` الحالي،
  حتى لا يتحول الموقع إلى صفحة فارغة.
- **بدون commit عند عدم وجود تغيير**: إذا لم يتغيّر المحتوى بين تشغيلة
  وأخرى، لا يُنشئ الـ workflow أي commit جديد.
