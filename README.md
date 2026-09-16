# Laila Bot — دليل الرفع على GitHub و Railway

## ⚠️ خطوة أولى ومهمة جدًا: غيّر التوكن
التوكن بتاع البوت كان مكتوب صراحةً جوه الكود القديم. حتى لو مش هترفعه على GitHub، الأفضل تروح لـ **@BotFather** وتعمل `/revoke` وتاخد توكن جديد، عشان تتأكد إن محدش شايف التوكن القديم. بعد كده حط التوكن الجديد في مكانه الصح (شرح تحت) — **متكتبوش جوه الكود تاني**.

## الملفات اللي جاهزة ليك
- `laila_lbot.py` — البوت، بعد ما عدّلت فيه التوكن والـ OWNER_ID يترقروا من Environment Variables
- `db.py` — بعد ما عدّلت مسار قاعدة البيانات يترقرأ من Environment Variable (`DB_PATH`)
- `requirements.txt` — المكتبات المطلوبة
- `Procfile` — بيقول لـ Railway يشغل البوت إزاي
- `.gitignore` — عشان ملف الداتا و`.env` متترفعش على GitHub
- `.env.example` — نموذج للمتغيرات المطلوبة (من غير قيم حقيقية)

## 1) الرفع على GitHub
```bash
cd اسم-المجلد
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO_NAME.git
git push -u origin main
```
بما إن `.gitignore` بيستبعد `.env` و `data.db`، التوكن والداتا مش هيترفعوا على GitHub.

## 2) الرفع على Railway
1. ادخل [railway.app](https://railway.app) واعمل **New Project → Deploy from GitHub repo** واختار الريبو.
2. Railway هيكتشف إنه مشروع Python ويستخدم `requirements.txt` و `Procfile` تلقائيًا.
3. من تبويب **Variables** ضيف:
   - `BOT_TOKEN` = التوكن الجديد بتاعك
   - `OWNER_ID` = آيدي التليجرام بتاعك
   - `DB_PATH` = `/data/data.db` (هنجهزها في الخطوة الجاية)

## 3) عشان الداتا متتمسحش (الجزء المهم)
مشكلة Railway إن التخزين العادي (filesystem) بتاع الكونتينر **مؤقت** — أي ديبلوي جديد أو ريستارت ممكن يمسح أي ملف اتعمل وانت شغال، بما فيها `data.db`. الحل هو **Volume** (تخزين دائم):

1. من صفحة المشروع على Railway، افتح السيرفس بتاع البوت.
2. روح لتبويب **Settings → Volumes** واعمل **New Volume**.
3. حط الـ **Mount Path** بالظبط: `/data`
4. تأكد إن الـ Variable `DB_PATH` متساوية `/data/data.db` (زي ما عملنا فوق).
5. اعمل Redeploy.

بعد كده، `data.db` هيتخزن جوه الـ Volume، وهيفضل موجود حتى لو عملت ريستارت أو ديبلوي جديد للكود. لو مسحت الـ Volume نفسه بس هتفقد الداتا.

### نسخة احتياطية إضافية (اختياري بس منصوح بيه)
جوه البوت نفسه فيه زرار "تصدير قاعدة البيانات" في قايمة المالك بيبعتلك ملف `data.db` على الخاص — استخدمه بين فترة والتانية كنسخة احتياطية إضافية حتى مع الـ Volume.

## تشغيل محلي (اختياري، عشان تجرب قبل ما ترفع)
```bash
pip install -r requirements.txt
cp .env.example .env
# افتح .env وحط فيه التوكن والـ OWNER_ID الحقيقيين
export $(cat .env | xargs)   # على ماك/لينكس
python laila_lbot.py
```
