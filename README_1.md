# 📚 نظام رفع المشاريع الطلابية

نظام ويب بسيط وديناميكي لرفع مشاريع الطلاب.

## 🛠️ التقنيات المستخدمة

- **Streamlit** - واجهة المستخدم
- **Supabase** - قاعدة البيانات
- **Google Drive API** - تخزين الملفات

## 📋 الملفات المطلوبة

1. `app.py` - الكود الرئيسي
2. `requirements.txt` - المكتبات
3. `database_schema.sql` - قاعدة البيانات

## 🚀 التشغيل على Render

### 1. رفع على GitHub
```bash
ارفع الملفات على GitHub repository
```

### 2. إنشاء Web Service في Render
```
- Build Command: pip install -r requirements.txt
- Start Command: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
```

### 3. إضافة Environment Variables
```
SUPABASE_URL = [URL من Supabase]
SUPABASE_KEY = [Key من Supabase]
GOOGLE_CREDENTIALS = [JSON من Google Cloud]
```

## 📝 إعداد قاعدة البيانات

1. أنشئ مشروع في Supabase
2. نفذ محتوى `database_schema.sql` في SQL Editor
3. احصل على Project URL و API Key

## 🔑 إعداد Google Drive

1. أنشئ مشروع في Google Cloud Console
2. فعّل Google Drive API
3. أنشئ Service Account
4. نزّل ملف JSON

## ✅ جاهز للاستخدام!

بعد اتباع الخطوات، سيعمل التطبيق على:
```
https://your-app-name.onrender.com
```

---

**صُنع بـ ❤️ للمؤسسات التعليمية**