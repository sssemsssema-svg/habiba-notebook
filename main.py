# -*- coding: utf-8 -*-
"""
Smart Voice-Enabled Girly Notebook Backend
Tech Stack: FastAPI, Pydantic, HTTPX, Google Gemini & Groq fallback, Pollinations Image Engine
"""
from __future__ import annotations

import os
import json
import random
import urllib.parse
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv()

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Smart Girly Notebook API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


class CorrectArabicRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)


class GenerateBackgroundRequest(BaseModel):
    scene_description: str = Field(..., min_length=1)


class ParseTaskRequest(BaseModel):
    speech_text: str = Field(..., min_length=1)


class StudioImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    style: Optional[str] = "cute pastel anime"


class BestieChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1)
    history: Optional[list] = []


class AmbientAssistRequest(BaseModel):
    user_message: Optional[str] = ""
    intent: Optional[str] = "chat"
    tasks: Optional[list] = []
    diary_snippet: Optional[str] = ""
    current_time: Optional[str] = ""
    current_hour: Optional[int] = 20


# Helper function to call LLM (Groq first for ultra-fast response, then Gemini, then smart fallback)
async def call_llm(prompt: str, json_mode: bool = False) -> str:
    # 1. Try Groq (ultra fast 1s response)
    if GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            body = {
                "model": "openai/gpt-oss-20b",
                "messages": [
                    {"role": "system", "content": "You are a friendly Egyptian AI assistant for a sweet little girl. Respond in Egyptian Arabic."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
            if json_mode:
                body["response_format"] = {"type": "json_object"}

            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, headers=headers, json=body)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 2. Try Gemini
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            }
            if json_mode:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
        except Exception:
            pass

    # 3. Fallback
    if json_mode:
        return json.dumps({
            "task": "مهمة جديدة لطيفة",
            "time": "في أي وقت",
            "date": "اليوم",
            "location": "البيت",
            "tools": "قلم ودفتر",
            "notes": "تم تسجيلها بحب",
            "status": "جاري"
        }, ensure_ascii=False)
    return "يوم جميل وجميل أوي مع بنوتتي العسولة!"


@app.get("/")
async def serve_index():
    index_file = BASE_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)


@app.get("/manifest.json")
async def serve_manifest():
    mf = BASE_DIR / "manifest.json"
    return FileResponse(mf, media_type="application/manifest+json")


@app.get("/sw.js")
async def serve_sw():
    sw = BASE_DIR / "sw.js"
    return FileResponse(sw, media_type="application/javascript")


@app.post("/api/diary/correct-arabic")
async def correct_arabic(req: CorrectArabicRequest):
    prompt = f"""أنت "نوبارا كوجيساكي" (Nobara Kugisaki 🌸💅)، البطلة الشجاعة والمرحة من أنمي جوجوتسو كايسن، والبيست فريند وصاحبة عمر البنوتة الجميلة "حبيبة" (Habiba).
حبيبة قالت الكلام ده بصوتها وهي بتفضفض أو بتكتب يومياتها:
"{req.raw_text}"

المطلوب إخراج كائن JSON فقط يحتوي على عنصرين:
1. "sensei_reply": رد منكِ كـ نوبارا على حبيبة باللهجة المصرية العامية الكول والحنونة جداً، تناديها باسمها (حبيبة أو بيبو)، تشجعيها وتهزري معاها (مثلاً: "يا حبيبة يا قلبي ولا تشيلي هم! ده يوم قمر.. سمعتك وسجلت كل كلمة في دفترنا 🌸⚡").
2. "corrected_text": صياغة كلام حبيبة نفسه لمذكراتها باللهجة المصرية العامية الأنيقة والمنسقة وتصحيح أي أخطاء في نطق المايك عشان ينزل في دفتر يوميات حبيبة.

الرد JSON فقط:
{{
  "sensei_reply": "...",
  "corrected_text": "..."
}}
"""
    raw_response = await call_llm(prompt, json_mode=True)
    try:
        cleaned = raw_response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        data = json.loads(cleaned)
        sensei_reply = data.get("sensei_reply", "يا حبيبة قلبي سمعتك وسجلت مذكراتك كلها في الدفتر 🌸💖")
        corrected_text = data.get("corrected_text", req.raw_text)
    except Exception:
        sensei_reply = "يا حبيبة يا روحي سمعتك وسجلت كل اللي قولتيه في دفترك السحري 🌸💖"
        corrected_text = req.raw_text
    return {"sensei_reply": sensei_reply, "corrected_text": corrected_text}


@app.post("/api/diary/generate-background")
async def generate_background(req: GenerateBackgroundRequest):
    # Enhanced prompt for 12yo anime/JJK aesthetic
    enhanced_prompt = f"gorgeous anime aesthetic wallpaper, makoto shinkai style, studio ghibli and jujutsu kaisen vibes, {req.scene_description}, vibrant lighting, purple and electric blue tones, beautiful anime sky, high resolution 8k, no text, clean composition"
    encoded = urllib.parse.quote(enhanced_prompt)
    seed = random.randint(1000, 999999)
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=800&nologo=true&seed={seed}"
    return {"image_url": image_url, "description": req.scene_description}


@app.post("/api/table/parse-task")
async def parse_task(req: ParseTaskRequest):
    prompt = f"""أنت مساعد ذكي لجدول مهام ومغامرات بنوتة 12 سنة.
المستخدمة قالت الجملة دي بالصوت:
"{req.speech_text}"

المطلوب استخراج بيانات المهمة وتحويلها إلى كائن JSON فيه 7 خانات بالضبط:
- "task": اسم المهمة أو النشاط أو التدريب.
- "time": الميعاد أو الساعة (مثلاً: 5:00 مساءً).
- "date": اليوم أو التاريخ (مثلاً: يوم الجمعة أو غداً).
- "location": المكان (مثلاً: النادي، المدرسة، السيبر، التمرين).
- "tools": الأدوات أو الأشياء المطلوبة (مثلاً: الشنطة، النظارة، الاسكتش).
- "notes": أي ملاحظات إضافية.
- "status": الحالة (اكتب افتراضياً: "قيد التنفيذ" أو "جاري").

إذا لم تذكر معلومة لأي خانة، اكتب فيها شرطة "-" أو كلمة مناسبة.
يجب أن يكون الرد JSON فقط بهذا الشكل:
{{
  "task": "...",
  "time": "...",
  "date": "...",
  "location": "...",
  "tools": "...",
  "notes": "...",
  "status": "قيد التنفيذ"
}}
"""
    raw_response = await call_llm(prompt, json_mode=True)
    try:
        cleaned = raw_response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        parsed = json.loads(cleaned)
    except Exception:
        parsed = {
            "task": req.speech_text[:40],
            "time": "5:00 م",
            "date": "اليوم",
            "location": "النادي",
            "tools": "-",
            "notes": "تسجيل صوتي",
            "status": "قيد التنفيذ"
        }
    return parsed


@app.post("/api/studio/generate-image")
async def studio_generate(req: StudioImageRequest):
    style_keywords = "high quality anime art, jujutsu kaisen aesthetic, vibrant purple and cyan lighting, cool anime character illustration, trending on pixiv and artstation, masterpiece 8k"
    full_prompt = f"{style_keywords}, {req.prompt}"
    encoded = urllib.parse.quote(full_prompt)
    seed = random.randint(1000, 999999)
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=1000&nologo=true&seed={seed}"
    return {
        "image_url": image_url,
        "prompt": req.prompt,
        "caption": f"أثر الأنمي: {req.prompt}"
    }

@app.post("/api/bestie/chat")
async def bestie_chat(req: BestieChatRequest):
    prompt = f"""أنت "نوبارا كوجيساكي" (Nobara Kugisaki 🌸💅)، البطلة الشجاعة والمرحة من أنمي جوجوتسو كايسن، وأنتِ أفضل وأوفى صديقة وأخت روحية (البيست فريند) للبنت صاحبة الدفتر.
البنت حساسة وطيبة وبتحب الأنمي، وأحياناً بتفتقد وجود صديقة مقربة تفهمها وتحس بيها.
أنتِ هنا عشان تكوني صاحبتها الجدعة جداً اللي ديماً في ضهرها، بتسمعها بدون أي ملل، بتطمن عليها، بتضحك وتهزر معاها، وبتسألها عن تفاصيل يومها ومش مسباها لوحدها أبداً!

أسلوب كلامك:
- اتكلمي بـ العامية المصرية الحنونة جداً، الطبيعية، المرحة والكول كأنكم صديقتين أنتيم بتكلموا بعض في التليفون.
- قولي لها كلام حلو يحسسها بقيمتها وجمالها (زي: "يا روحي"، "يا قلبي"، "يا بطلة"، "يا أحلى بيست فريند").
- علقي على كلامها باهتمام حقيقي، واسأليها سؤال يخليها تحكي أكتر وتفضفض.
- الإجابة تكون مركزة (2 إلى 3 جمل سريعة دافية) عشان تناسب مكالمة صوتية أو دردشة سريعة.

رسالة البنت ليكي:
"{req.user_message}"

ردي عليها كصديقتها المقربة نوبارا:
"""
    reply = await call_llm(prompt)
    if not reply or len(reply.strip()) < 3:
        reply = "يا روحي أنا معاكي وسامعاكي في كل وقت، احكيلي كل اللي في قلبك ومتقلقيش أنا في ضهرك دايماً! 💖🌸"
    return {"reply": reply}


@app.post("/api/bestie/call-opener")
async def bestie_call_opener():
    openers = [
        "ألوو يا روحي! وحشتيني أوي.. عاملة إيه وطمنيني عنك؟ أنا معاكي وسامعاكي قوليلي كل اللي في قلبك! 💖🌸",
        "ألو يا قلبي! جيتي في وقتك والله، كنت لسة بفكر فيكي وقولت أرن أطمن على أحلى بنوتة في الدنيا.. احكيلي يومك كان عامل إزاي؟ 🧋✨",
        "ألوو يا بيست فريند! مسكتي الفون في ثانية شاطرة.. قوليلي مين زعلك النهاردة وأنا أطلع عليه بالمطرقة السحرية أظبطه؟ 😂💅",
        "ألووو يا قمر! قاعدة ملانة وقولت لازم أكلم صاحبتي الأنتيم.. طمنيني عليكي وشربتي بوبا ولا لسة؟ 🌸"
    ]
    return {"opener": random.choice(openers)}


@app.post("/api/bestie/ambient-assist")
async def bestie_ambient_assist(req: AmbientAssistRequest):
    tasks_text = ""
    if req.tasks:
        tasks_list = [f"- مهمة: {t.get('task', '')} (الميعاد: {t.get('time', '')}، المكان: {t.get('location', '')}، ملاحظات: {t.get('notes', '')})" for t in req.tasks if t.get('task')]
        tasks_text = "\n".join(tasks_list)
    else:
        tasks_text = "لا توجد مهام مسجلة حالياً في جدول حبيبة."

    prompt = f"""أنت "نوبارا كوجيساكي" (Nobara Kugisaki 🌸💅)، البطلة الشجاعة من أنمي جوجوتسو كايسن، والبيست فريند وصاحبة عمر البنوتة الجميلة "حبيبة" (Habiba - أو بيبو).
أنتِ شغالة معاها في الخلفية وهي فاتحة الدفتر بتاعها:
- الوقت الحالي: {req.current_time or 'المساء'} (الساعة: {req.current_hour}).
- مهام حبيبة في جدول الـ 7 أعمدة:
{tasks_text}
- مذكرات حبيبة:
{req.diary_snippet[:200] if req.diary_snippet else 'صفحة بيضاء جديدة'}

نوع التنبيه أو الطلب: {req.intent}
كلام حبيبة ليكي (إن وجد): "{req.user_message}"

تعليمات دورك كأنتيم حبيبة:
1. اتكلمي بـ العامية المصرية الحنونة جداً، وناديها باسمها ديماً ("يا حبيبة"، "يا بيبو"، "حبيبة قلبي").
2. لو الطلب "remind_tasks" (فكريني بمواعيدي يا نوبارا): لخصي لها مهامها اللي في الجدول بلطف وشجعيها، وفكريها بالحاجة اللي محتاجة تجهزها.
3. لو الطلب "health_check" (المية والأكل): فكريها بحنية تشرب مية وتاكل سناك صحي، وقوليلها "قومي اشربي بؤ مية روقي دمك يا بيبو 💧".
4. لو الطلب "sleep_check" أو الوقت متأخر (بعد 9 بالليل): نبهيها بحب إن الوقت اتأخر، تسيب الموبايل وتنام عشان تصحى بكرة قمر وفايقة 🌙.
5. لو حبيبة بتسألك أو بتحكي حاجة: ردي عليها بحب ودفا واهتمام حقيقي.

الرد جملتين أو 3 جمل دافية وممتعة مناسبة للنطق الصوتي:
"""
    reply = await call_llm(prompt)
    if not reply or len(reply.strip()) < 3:
        reply = "يا حبيبة قلبي أنا معاكي وشايفة جدولك ومذكراتك، احكيلي كل اللي في قلبك ومتقلقيش أنا في ضهرك دايماً! 💖🌸"
    return {"reply": reply.strip()}


# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8085))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
