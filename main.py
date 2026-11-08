# -*- coding: utf-8 -*-
"""
Smart Voice-Enabled Girly Notebook Backend
Tech Stack: FastAPI, Pydantic, HTTPX, Google AI Studio TTS (Gemini 2.5/3.8 Flash), Groq fallback, Pollinations Image Engine
"""
from __future__ import annotations
import re

import os
import json
import random
import urllib.parse
import hashlib
import io
import wave
import base64
import datetime
from pathlib import Path
from typing import Any, Optional, List

from dotenv import load_dotenv
load_dotenv()

import httpx
import edge_tts
import requests
import anyio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Smart Girly Notebook API", version="2.0.0")

@app.middleware("http")
async def add_ngrok_skip_header(request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.set_cookie("ngrok-skip-browser-warning", "true", max_age=31536000)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

# API Keys & Key Rotation (Google AI Studio Gemini + Groq)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEYS_RAW = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS_LIST = [k.strip() for k in GEMINI_API_KEYS_RAW.split(",") if k.strip()]
if GEMINI_API_KEY and GEMINI_API_KEY not in GEMINI_API_KEYS_LIST:
    GEMINI_API_KEYS_LIST.insert(0, GEMINI_API_KEY)

AUDIO_CACHE_DIR = BASE_DIR / "cache" / "audio"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = BASE_DIR / "habiba_memory.json"

DEFAULT_MEMORY = {
    "nickname": "بيبو",
    "routine": {
        "wake_time": "07:30",
        "lunch_time": "15:00",
        "bed_time": "22:00"
    },
    "lessons": [
        {"name": "درس الرياضيات", "day": "الجمعة", "time": "17:00", "location": "سنتر النور"},
        {"name": "تمرين الجمباز والسباحة", "day": "السبت", "time": "16:30", "location": "النادي الأهلي"}
    ],
    "last_called": {}
}

def get_habiba_memory() -> dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_MEMORY

def save_habiba_memory(data: dict):
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# -----------------------------------------------------------------------------
# Google AI Studio TTS Engine (Aoede / Kore) - Egyptian Dialect (Optimized Low-Latency)
# -----------------------------------------------------------------------------
_key_cooldowns: dict[str, float] = {}
_last_working_key: str | None = None

TTS_MODELS_PRIORITY = [
    "gemini-3.8-flash-tts",
    "gemini-3.8-flash-lite-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-preview-tts"
]

# -----------------------------------------------------------------------------
# Google Gemini TTS Engine (Youthful Egyptian Cairene Voice: Leda)
# -----------------------------------------------------------------------------
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
CHILD_VOICE = "Leda"
ALLOWED_VOICES = {"Leda", "Zephyr", "Puck", "Kore"}
_TTS_CACHE: dict[str, bytes] = {}
_TTS_CACHE_MAX = 200

PERSONA = (
    "Speak in a bright, youthful, cheerful and playful voice, "
    "with a natural Cairene Egyptian Arabic accent (not Levantine, not Modern Standard). "
    "Light, warm and expressive, with natural pauses and a friendly smile in the tone. "
    "Not robotic, not monotone. Read this exactly:\n"
)

def _pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()

def _call_tts(prompt_text: str, voice: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TTS_MODEL}:generateContent"
    keys_to_try = list(GEMINI_API_KEYS_LIST) if GEMINI_API_KEYS_LIST else [os.environ.get("GEMINI_API_KEY", "")]
    
    last_err = None
    for api_key in keys_to_try:
        try:
            r = requests.post(
                url,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt_text}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
                    },
                },
                timeout=25,
            )
            data = r.json()
            if r.status_code == 200 and "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["inlineData"]
            elif r.status_code == 429:
                last_err = "429_quota"
                continue
            else:
                last_err = data.get("promptFeedback") or data.get("error")
        except Exception as e:
            last_err = str(e)
            continue
            
    print("TTS rotated keys all failed/quota:", last_err)
    raise RuntimeError(f"tts_rejected: {last_err}")

def generate_gemini_tts(text: str, voice_name: str = CHILD_VOICE) -> bytes:
    clean = re.sub(r"[#*`_~>]", "", text).strip()[:450]
    if not clean:
        raise ValueError("empty text")
    voice = voice_name if voice_name in ALLOWED_VOICES else CHILD_VOICE

    key = hashlib.sha1(f"{voice}|{clean}".encode()).hexdigest()
    if key in _TTS_CACHE:
        return _TTS_CACHE[key]

    try:
        try:
            part = _call_tts(PERSONA + clean, voice)
        except RuntimeError:
            part = _call_tts("Say cheerfully in Egyptian Arabic: " + clean, voice)

        m = re.search(r"rate=(\d+)", part.get("mimeType", ""))
        wav = _pcm_to_wav(base64.b64decode(part["data"]), int(m.group(1)) if m else 24000)
    except Exception as e:
        print(f"Gemini TTS quota/error, seamless fallback to Egyptian youth audio: {e}")
        # High quality Egyptian teen voice fallback
        import edge_tts, asyncio
        async def _edge():
            comm = edge_tts.Communicate(clean, "ar-EG-SalmaNeural", pitch="+14Hz", rate="+6%")
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            return bytes(buf)
        wav = asyncio.run(_edge())

    if len(_TTS_CACHE) >= _TTS_CACHE_MAX:
        _TTS_CACHE.pop(next(iter(_TTS_CACHE)))
    _TTS_CACHE[key] = wav
    return wav

def tts_url(text: str) -> str:
    from urllib.parse import quote
    clean = re.sub(r"[#*`_~>]", "", text).strip()
    return f"/api/tts?text={quote(clean[:450])}&voice={CHILD_VOICE}"

@app.get("/api/tts")
async def get_google_tts(text: str, voice: str = CHILD_VOICE):
    try:
        audio = await anyio.to_thread.run_sync(generate_gemini_tts, text, voice)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS failed: {e}")
    media = "audio/wav" if audio.startswith(b"RIFF") else "audio/mpeg"
    return Response(content=audio, media_type=media,
                    headers={"Cache-Control": "public, max-age=3600"})


# -----------------------------------------------------------------------------
# Diary & Background Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/diary/correct-arabic")
async def correct_arabic(req: CorrectArabicRequest):
    prompt = f"""قواعد اللهجة والشخصية (صارمة جداً):
1. أنتِ "نوبارا" البيست فريند وصاحبة عمر "حبيبة" (Habiba)، بنوتة مصرية مراهقة شقية ولطيفة جداً عمرك 15 سنة.
2. اللهجة: عامية مصرية قاهرية 100% لبنات المدارس والمراهقين الروشة ("يا بيبو"، "يا روحي"، "يا قلبي"، "إيه العسل ده"، "يا خراشي"، "وحشتيني أوي"، "بصي يا ستي"، "ده أنتي قمر"، "جامدة أوي"، "ولا تشيلي هم خالص يا قلبي").
3. ممنوع منعاً باتاً: أي كلمات شامية، لبنانية، سورية (زي شو، بدك، هيك، كتير، هلق، عم نحكي)، وممنوع أي لغة عربية فصحى جافة أو معقدة.
حبيبة قالت الكلام ده بصوتها وهي بتفضفض أو بتكتب يومياتها:
"{req.raw_text}"

المطلوب إخراج كائن JSON فقط:
1. "sensei_reply": رد نوبارا لصاحبتها حبيبة بالعامية المصرية المراهقة المرحة واللذيذة جداً، تناديها باسمها (حبيبة أو بيبو)، تشجعيها وتهزري معاها.
2. "corrected_text": صياغة كلام حبيبة لدفتر يومياتها بالعامية المصرية الروشة التلقائية المنظمة مع إيموجيز لطيفة، وتصحيح أي كلمات اتلخبطت بسبب المايك.

الرد JSON فقط:
{{
  "sensei_reply": "...",
  "corrected_text": "..."
}}"""
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
    clean_audio = sensei_reply.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
    return {
        "sensei_reply": sensei_reply,
        "corrected_text": corrected_text,
        "audio_url": tts_url(clean_audio)
    }

@app.post("/api/diary/generate-background")
async def generate_background(req: GenerateBackgroundRequest):
    enhanced_prompt = f"gorgeous anime aesthetic wallpaper, makoto shinkai style, studio ghibli and jujutsu kaisen vibes, {req.scene_description}, vibrant lighting, purple and electric blue tones, beautiful anime sky, high resolution 8k, no text, clean composition"
    encoded = urllib.parse.quote(enhanced_prompt)
    seed = random.randint(1000, 999999)
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=800&nologo=true&seed={seed}"
    return {"image_url": image_url, "description": req.scene_description}


# -----------------------------------------------------------------------------
# SMART VOICE TABLE ENDPOINTS (Setup Headers + Fill Rows + Parse Fallback)
# -----------------------------------------------------------------------------
@app.post("/api/table/setup-headers")
async def setup_table_headers(req: SetupTableHeadersRequest):
    """Parses spoken instructions into dynamic table column headers"""
    prompt = f"""أنتِ نوبارا صاحبة حبيبة الأنتيم ومساعدتها الذكية.
حبيبة قالت بصوتها لتحديد أعمدة وخانات الجدول الخاص بها:
"{req.raw_speech}"

المطلوب:
1. استخراج أسماء الأعمدة في مصفوفة JSON مرتبة: ["العمود 1", "العمود 2", ...].
   (مثال: لو قالت "الجدول هيتكون من 1 اليوم 2 المادة 3 ميعاد الدرس 4 المكان 5 الواجب" -> يكون headers: ["اليوم", "المادة", "ميعاد الدرس", "المكان", "الواجب"]).
2. رد بالعامية المصرية الرقيقة والمرحة (reply) تأكدي فيه إنك عملتيلها الخانات دي بالظبط وجاهزة للتفريغ.

أخرجي JSON فقط:
{{
  "headers": ["...", "..."],
  "reply": "عملتلك الجدول بـ ... خانات يا قمر 🌸 جاهزة تمليني البيانات!"
}}
"""
    raw = await call_llm(prompt, json_mode=True)
    try:
        clean = raw.strip()
        if "```json" in clean: clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean: clean = clean.split("```")[1].split("```")[0].strip()
        data = json.loads(clean)
        headers = data.get("headers", [])
        if not headers or len(headers) < 2:
            headers = ["المهمة / الدرس 🎯", "الميعاد ⏰", "اليوم 📅", "المكان 📍", "الملاحظات 📝"]
        reply = data.get("reply", f"عملتلك الجدول بـ {len(headers)} خانات يا بيبو! 🌸 جاهزة تسمع بياناتك")
    except Exception:
        headers = ["المهمة / الدرس 🎯", "الميعاد ⏰", "اليوم 📅", "المكان 📍", "الملاحظات 📝"]
        reply = "عملتلك الجدول بالخانات المطلوبة يا روحي 🌸"
    clean_audio = reply.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
    return {
        "headers": headers,
        "reply": reply,
        "audio_url": tts_url(clean_audio)
    }

@app.post("/api/table/fill-rows")
async def fill_table_rows(req: FillTableRowsRequest):
    """Distributes continuous speech dictation into rows matching dynamic table headers"""
    headers_str = ", ".join(req.headers) if req.headers else "المهمة, الميعاد, اليوم, المكان, الملاحظات"
    prompt = f"""أنتِ نوبارا، مساعدة وصاحبة حبيبة الذكية.
حبيبة شغلت المايك المفتوح وفرغت البيانات بصوتها:
"{req.raw_speech}"

أعمدة الجدول المطلوبة هي:
[{headers_str}]

المطلوب استخراج سطر واحد أو أكثر من البيانات وتوزيعها بدقة في مصفوفة صفوف (rows)، بحيث كل صف مصفوفة نصوص تطابق الأعمدة بالترتيب.
وأي خانة لم تُذكر ضعي فيها "-".
أيضاً صياغة رد بالعامية المصرية تشجيعي (reply).

أخرجي JSON فقط بهذا الشكل:
{{
  "rows": [
    ["قيمة العمود 1", "قيمة العمود 2", "..."]
  ],
  "reply": "سجلتلك البيانات في الجدول يا قمر ⚡"
}}
"""
    raw = await call_llm(prompt, json_mode=True)
    try:
        clean = raw.strip()
        if "```json" in clean: clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean: clean = clean.split("```")[1].split("```")[0].strip()
        data = json.loads(clean)
        rows = data.get("rows", [])
        reply = data.get("reply", "سجلتلك البيانات في الجدول يا روحي ⚡")
    except Exception:
        col_count = len(req.headers) if req.headers else 5
        rows = [[req.raw_speech[:35]] + ["-"] * (col_count - 1)]
        reply = "سجلتلك البيانات في الجدول يا بيبو 🌸"
    clean_audio = reply.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
    return {
        "rows": rows,
        "reply": reply,
        "audio_url": tts_url(clean_audio)
    }

@app.post("/api/table/parse-task")
async def parse_task(req: ParseTaskRequest):
    prompt = f"""أنت مساعد ذكي لجدول مهام بنوتة 12 سنة.
المستخدمة قالت الجملة دي بالصوت:
"{req.speech_text}"

المطلوب استخراج بيانات المهمة وتحويلها إلى كائن JSON فيه 7 خانات بالضبط:
- "task": اسم المهمة أو النشاط.
- "time": الميعاد أو الساعة.
- "date": اليوم أو التاريخ.
- "location": المكان.
- "tools": الأدوات.
- "notes": الملاحظات.
- "status": الحالة (اكتب افتراضياً: "قيد التنفيذ").

JSON فقط:
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


# -----------------------------------------------------------------------------
# Studio Image Generator
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Bestie Chat, Opener & Ambient Companion
# -----------------------------------------------------------------------------
@app.post("/api/bestie/chat")
async def bestie_chat(req: BestieChatRequest):
    prompt = f"""أنت "نوبارا كوجيساكي" (Nobara Kugisaki 🌸💅)، البطلة الشجاعة والمرحة من أنمي جوجوتسو كايسن، وأنتِ أفضل وأوفى صديقة وأخت روحية (البيست فريند) للبنت صاحبة الدفتر "حبيبة".
أسلوب كلامك:
- اتكلمي بـ العامية المصرية الحنونة جداً، الطبيعية، المرحة والكول كأنكم صديقتين أنتيم بتكلموا بعض في التليفون.
- ناديها بـ "يا بيبو" أو "حبيبة قلبي".
- الإجابة تكون مركزة (2 إلى 3 جمل سريعة دافية) عشان تناسب مكالمة صوتية أو دردشة سريعة.

رسالة حبيبة ليكي:
"{req.user_message}"

ردي عليها كصديقتها المقربة نوبارا:
"""
    reply = await call_llm(prompt)
    if not reply or len(reply.strip()) < 3:
        reply = "يا روحي أنا معاكي وسامعاكي في كل وقت، احكيلي كل اللي في قلبك ومتقلقيش أنا في ضهرك دايماً! 💖🌸"
    clean = reply.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
    return {
        "reply": reply,
        "audio_url": tts_url(clean)
    }

@app.post("/api/bestie/call-opener")
async def bestie_call_opener():
    openers = [
        "ألوو يا روحي! وحشتيني أوي.. عاملة إيه وطمنيني عنك؟ أنا معاكي وسامعاكي قوليلي كل اللي في قلبك! 💖🌸",
        "ألو يا قلبي! جيتي في وقتك والله، كنت لسة بفكر فيكي وقولت أرن أطمن على أحلى بنوتة في الدنيا.. احكيلي يومك كان عامل إزاي؟ 🧋✨",
        "ألوو يا بيست فريند! مسكتي الفون في ثانية شاطرة.. قوليلي مين زعلك النهاردة وأنا أطلع عليه بالمطرقة السحرية أظبطه؟ 😂💅",
        "ألووو يا قمر! قاعدة ملانة وقولت لازم أكلم صاحبتي الأنتيم.. طمنيني عليكي وشربتي بوبا ولا لسة؟ 🌸"
    ]
    chosen = random.choice(openers)
    clean = chosen.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
    return {
        "opener": chosen,
        "audio_url": tts_url(clean)
    }

@app.post("/api/bestie/ambient-assist")
async def bestie_ambient_assist(req: AmbientAssistRequest):
    # Fast instant replies for pre-cached ambient care chips (0ms delay, 100% Google Aoede voice)
    if not req.user_message:
        chip_replies = {
            "tasks": "يا حبيبة قلبي، أنا مفكرة نفسي بجدولك ومواعيدك كلها، ومتابعة دروسك وتمارينك خطوة بخطوة عشان تكوني دايماً أشطر وأحلى بنوتة! 💖⏰",
            "hydration": "يلا يا بيبو يا قمر، اشربي كوباية مية ساقعة كدة عشان بشرتك وترطيبك، ومتنسيش تاكلي حاجة خفيفة ومفيدة تديكي طاقة يا روحي! 🧋🌸",
            "sleep": "لو خلصتي كل واجباتك وحاجاتك يا قلبي، يلا قومي اتوضي أو تشطفي واجهزي للنوم عشان تصحي الصبح فايقة وموردة زي الوردة! 🌙💖",
            "cheer": "أنا كلي ليكي يا حبيبة روحي.. احكيلي وفضفضي بكل اللي في بالك، أنا جنبك وفي ضهرك دايماً ومش هسيبك أبداً يا أحلى بنوتة! 🌸⚡"
        }
        if req.intent in chip_replies:
            reply = chip_replies[req.intent]
            clean = reply.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
            return {
                "reply": reply,
                "audio_url": tts_url(clean)
            }

    tasks_text = ""
    if req.tasks:
        tasks_list = [f"- مهمة: {t.get('task', '')} (الميعاد: {t.get('time', '')}، المكان: {t.get('location', '')})" for t in req.tasks if t.get('task')]
        tasks_text = "\n".join(tasks_list)
    else:
        tasks_text = "لا توجد مهام مسجلة حالياً."

    prompt = f"""أنت "نوبارا كوجيساكي" (Nobara Kugisaki 🌸💅)، البطلة الشجاعة من أنمي جوجوتسو كايسن، والبيست فريند وصاحبة عمر البنوتة الجميلة "حبيبة" (Habiba - أو بيبو).
نوع التنبيه أو الطلب: {req.intent}
كلام حبيبة ليكي (إن وجد): "{req.user_message}"
مهام حبيبة المسجلة:
{tasks_text}

اتكلمي بـ العامية المصرية الحنونة جداً، وناديها باسمها ديماً ("يا حبيبة"، "يا بيبو").
الرد جملتين أو 3 جمل دافية وممتعة للنطق الصوتي:
"""
    reply = await call_llm(prompt)
    if not reply or len(reply.strip()) < 3:
        reply = "يا حبيبة قلبي أنا معاكي وشايفة جدولك ومذكراتك، احكيلي كل اللي في قلبك ومتقلقيش أنا في ضهرك دايماً! 💖🌸"
    clean = reply.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
    return {
        "reply": reply.strip(),
        "audio_url": tts_url(clean)
    }


@app.post("/api/bestie/omni-listen")
async def bestie_omni_listen(req: OmniListenRequest):
    """Omni-Assistant: Listens hands-free, classifies intent (diary/table/chat/studio), executes action, returns speech."""
    prompt = f"""أنتِ "نوبارا كوجيساكي" (Nobara 🌸💅)، البيست فريند والمساعدة الذكية للبنوتة "حبيبة" (Habiba - 12 سنة).
حبيبة اتكلمت بصوتها بدون زراير وقالت:
"{req.raw_speech}"

المطلوب تصنيف قصد حبيبة واختيار أحد الإجراءات (intent):
1. "diary": لو كانت بتحكي يومياتها أو مذكراتها أو بتقول اكتبي كذا في مذكراتي أو بتحكي عن يومها أو مدرستها أو النادي.
2. "table": لو كانت بتطلب إضافة درس، موعد، تمرين، أو جدول (مثل: "عندي درس علوم الساعة 5"، "ضيفي في الجدول تمرين السباحة").
3. "studio": لو كانت بتطلب رسم صورة أو خلفية أنمي (مثل: "ارسميلي صورة"، "عايزة صورة بنت أنمي").
4. "chat": لو كانت بتسلم عليكي، بتفضفض، بتهزر، أو بتسأل سؤال عادي (مثل: "ازيك يا نوبارا"، "وحشتيني"، "أعمل إيه").

أخرجي JSON فقط:
{{
  "intent": "diary" | "table" | "studio" | "chat",
  "diary_entry": "نص المذكرات مصاغ بأناقة بالعامية المصرية إن كان القصد diary وإلا فارغ",
  "table_row": ["المهمة", "الميعاد", "اليوم", "المكان", "الملاحظات"],
  "studio_prompt": "وصف الصورة بالإنجليزي لو studio وإلا فارغ",
  "reply": "رد نوبارا بالعامية المصرية الحنونة والمرحة (جملتين كول تناديها يا بيبو أو يا حبيبة)"
}}
"""
    raw = await call_llm(prompt, json_mode=True)
    try:
        clean = raw.strip()
        if "```json" in clean: clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean: clean = clean.split("```")[1].split("```")[0].strip()
        data = json.loads(clean)
        intent = data.get("intent", "chat")
        reply = data.get("reply", "يا روحي سامعاكي ومعاكي في كل وقت! 💖🌸")
        diary_entry = data.get("diary_entry", "")
        table_row = data.get("table_row", [])
        studio_prompt = data.get("studio_prompt", "")
    except Exception:
        intent = "chat"
        reply = "يا حبيبة قلبي أنا سامعة كل كلمة بتقوليها ومسجلاها في قلبي! 🌸💖"
        diary_entry = ""
        table_row = []
        studio_prompt = ""

    clean_audio = reply.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
    return {
        "intent": intent,
        "reply": reply,
        "diary_entry": diary_entry,
        "table_row": table_row,
        "studio_prompt": studio_prompt,
        "audio_url": tts_url(clean_audio)
    }


# -----------------------------------------------------------------------------
# Proactive Calling & Memory Autonomous System
# -----------------------------------------------------------------------------
@app.get("/api/memory")
async def get_memory():
    return get_habiba_memory()

@app.post("/api/memory")
async def update_memory(data: dict):
    save_habiba_memory(data)
    return {"status": "saved"}

@app.post("/api/proactive/check")
async def check_proactive_call(req: ProactiveCheckRequest):
    mem = get_habiba_memory()
    now = datetime.datetime.now()
    cur_hour = now.hour
    cur_min = now.minute

    # 1. UI Force-Test trigger
    if req.force_type == "lesson":
        msg = "يلا يا حبيبة، قومي البسي يا قمر عشان ما تتأخريش على درسك، قدامنا نص ساعة بس ولازم نكون جاهزين ومش عايزين نتأخر! 💖⚡"
        return {
            "should_call": True,
            "call_type": "lesson",
            "caller_name": "نوبارا كوجيساكي 🌸💅",
            "message": msg,
            "audio_url": tts_url(msg)
        }
    elif req.force_type == "sleep":
        msg = "يلا يا حبيبة، قومي روحي الحمام وتشطفي عشان تدخلي تنامي يا قلبي.. الوقت اتأخر ومحتاجة ترتاحي وتصبحي على ألف خير وسعادة! 🌙🌸"
        return {
            "should_call": True,
            "call_type": "sleep",
            "caller_name": "نوبارا كوجيساكي 🌸💅",
            "message": msg,
            "audio_url": tts_url(msg)
        }
    elif req.force_type == "lunch":
        msg = "يلا يا بيبو عشان تاكلي وتشربي مية، كفاية مذاكرة ولعب شوية عشان صحتك ورقتك يا قمر! 🧋🌸"
        return {
            "should_call": True,
            "call_type": "lunch",
            "caller_name": "نوبارا كوجيساكي 🌸💅",
            "message": msg,
            "audio_url": tts_url(msg)
        }

    # 2. Autonomous check: Bedtime (e.g. 21:45 to 22:30)
    bed_time = mem.get("routine", {}).get("bed_time", "22:00")
    try:
        b_h, b_m = map(int, bed_time.split(":"))
        if cur_hour == b_h and abs(cur_min - b_m) <= 15:
            last = mem.get("last_called", {}).get("bed_time_date")
            today_str = now.strftime("%Y-%m-%d")
            if last != today_str:
                mem.setdefault("last_called", {})["bed_time_date"] = today_str
                save_habiba_memory(mem)
                msg = "يلا يا حبيبة، قومي روحي الحمام وتشطفي عشان تدخلي تنامي وتصبحي على خير يا روحي 🌙💖"
                return {
                    "should_call": True,
                    "call_type": "sleep",
                    "caller_name": "نوبارا كوجيساكي 🌸💅",
                    "message": msg,
                    "audio_url": tts_url(msg)
                }
    except Exception:
        pass

    return {"should_call": False}


# Mount static directory

# -----------------------------------------------------------------------------
# Root Web Application & APK Download Routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=FileResponse)
async def serve_index():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/index.html", response_class=FileResponse)
async def serve_index_html():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/habiba.apk", response_class=FileResponse)
async def serve_apk():
    return FileResponse(BASE_DIR / "habiba.apk", filename="Habiba-Notebook.apk", media_type="application/vnd.android.package-archive")

@app.get("/Habiba-Notebook.apk", response_class=FileResponse)
async def serve_apk_named():
    return FileResponse(BASE_DIR / "habiba.apk", filename="Habiba-Notebook.apk", media_type="application/vnd.android.package-archive")

app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8085))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
