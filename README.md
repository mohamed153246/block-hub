# بلوك هَب

موقع خفيف لمودات ماين كرافت.

## كيف يعمل؟

`bot.py` يجلب البيانات من Modrinth ويعيد توليد `index.html`.

GitHub Actions يشغل البوت تلقائياً كل 15 دقيقة طوال اليوم، ويمكن تشغيله يدوياً من تبويب Actions.

لا يوجد `mods_data.json`.

## الملفات

- `index.html`
- `bot.py`
- `requirements.txt`
- `.github/workflows/update.yml`

## User-Agent

ضع في GitHub:

Settings → Secrets and variables → Actions → New repository secret

الاسم:
`MODRINTH_USER_AGENT`

مثال القيمة:
`mohamed153246/block-hub/1.0`

إذا لم تضف الـSecret سيستخدم البوت قيمة افتراضية.
