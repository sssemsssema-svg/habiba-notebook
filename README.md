# 🌸 دفتر يوميات حبيبة الذكي مع نوبارا (Habiba's Smart Anime Notebook)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sssemsssema-svg/smart_girl_notebook)

تطبيق ويب تقدمي (PWA) ثلاثي الأبعاد على هيئة دفتر سلك أنمي تفاعلي، مخصص للبطلة "حبيبة" مع الذكاء الاصطناعي لشخصية "نوبارا كوجيساكي" (Nobara Kugisaki) باللهجة المصرية الدافئة.

---

### ✨ الميزات الرئيسية
1. **إملاء صوتي فوري ومتواصل (Real-Time Live Dictation):**
   - الكتابة الحية كلمة بكلمة على أسطر الدفتر دون أي انقطاع (`continuous = true`).
2. **تصحيح لغوي وتحويل لعامية مصرية دافئة:**
   - تحويل النص وتوليد رد صوتي فوري بنبرة نوبارا المصرية المشجعة عبر Web Speech API.
3. **المرافقة المستمرة والمنبه الذكي (Ambient Companion):**
   - تذكير بمواعيد المذاكرة، النوم، شرب المياه، والمهام اليومية وفق جدول الـ 7 أعمدة.
4. **محاكاة مكالمة هاتفية حقيقية (Simulated Voice Call):**
   - رنة هاتف مولدة برمجياً عبر Web Audio API بدون الحاجة لملفات خارجية، مع وضع التحدث الحر.
5. **تطبيق PWA متكامل:**
   - قابل للتثبيت كأيقونة تطبيق مستقل على الهاتف والحاسوب بأيقونات ثلاثية الأبعاد.

---

### 🚀 النشر على Render.com
التطبيق مهيأ كـ Web Service سحابي عبر `render.yaml` و `Procfile`.

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### متغيرات البيئة المطلوبة (Environment Variables):
- `GEMINI_API_KEY`: مفتاح Google Gemini من AI Studio.
- `GROQ_API_KEY`: مفتاح Groq (اختياري للاستجابة فائقة السرعة).
