# Block Hub Pro

منصة Minecraft للمودات وResource Packs بتسجيل دخول عبر البريد الإلكتروني ونشر محتوى المستخدمين.

## تشغيل سريع

1. أنشئ مشروعًا في Supabase.
2. من SQL Editor شغّل محتوى `supabase.sql`.
3. فعّل Email Auth من Authentication > Providers > Email.
4. انسخ `.env.example` إلى `.env` وضع:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
5. ثبّت وشغّل:

```bash
npm install
npm run dev
```

6. للنشر على Vercel أو Netlify: أضف نفس متغيرات البيئة ثم Build command `npm run build` وOutput `dist`.

## ماذا يعمل؟
- تسجيل/تسجيل دخول بالإيميل.
- صفحات استكشاف مودات وResource Packs.
- بحث وفلاتر.
- رفع ملف المحتوى إلى Supabase Storage.
- رفع صورة غلاف.
- إنشاء منشور بحالة `pending`.
- عند تفعيل RLS يمكن للمستخدم إدارة منشوراته، بينما المنشورات المنشورة فقط تظهر للعامة.

## ملاحظة الإنتاج
قبل الإطلاق العام أضف نظام مراجعة Admin، مكافحة spam، حد حجم/نوع الملفات على مستوى Storage، وسياسة حقوق ملكية واضحة.
