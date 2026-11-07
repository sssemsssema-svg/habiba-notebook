# 🌸 دفتر يوميات حبيبة السري (Habiba's Magic Anime Notebook)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sssemsssema-svg/habiba-notebook)

تطبيق ويب تقدمي (PWA) ثلاثي الأبعاد على هيئة دفتر سلك أنمي تفاعلي مخصص لحبيبة مع الذكاء الاصطناعي لشخصية "نوبارا كوجيساكي" (Nobara Kugisaki) من Jujutsu Kaisen باللهجة المصرية الدافئة.

---

### ✨ الميزات الرئيسية
1. **إملاء صوتي فوري ومتواصل (Real-Time Live Dictation):**
   - الكتابة الحية كلمة بكلمة على أسطر الدفتر دون أي انقطاع (`continuous = true`).
2. **تصحيح لغوي وتحويل لعامية مصرية دافئة:**
   - تحويل الكلام وتوليد رد صوتي فوري بنبرة نوبارا المصرية المشجعة.
3. **المرافقة المستمرة والمنبه الذكي (Ambient Companion):**
   - تذكير بمواعيد المذاكرة، النوم، شرب المياه، وجدول المهام الأسبوعي.
4. **محاكاة اتصال هاتفي وارد (Simulated Voice Call):**
   - رنة هاتف حقيقية مولدة عبر Web Audio API مع شاشة مكالمة تفاعلية.
5. **تطبيق PWA متكامل:**
   - قابل للتثبيت كأيقونة تطبيق مستقلة على الهاتف "دفتر حبيبة".

---

### 🚀 النشر السحابي التلقائي
- **الرابط المباشر:** [Deploy to Render](https://render.com/deploy?repo=https://github.com/sssemsssema-svg/habiba-notebook)
- **Service Name:** `habiba-notebook`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
