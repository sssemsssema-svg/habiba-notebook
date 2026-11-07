# -*- coding: utf-8 -*-
"""
Smart Voice-Enabled Girly Notebook Backend
Tech Stack: FastAPI, Pydantic, HTTPX, Google AI Studio TTS (Gemini 2.5/3.8 Flash), Groq fallback, Pollinations Image Engine
"""
from __future__ import annotations

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
import requests
import anyio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Smart Girly Notebook API", version="2.0.0")

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

def generate_gemini_tts(text: str, voice_name: str = "Aoede") -> bytes:
    global _last_working_key
    clean_text = text.replace("#", "").replace("*", "").replace("`", "").replace("~", "").replace("_", "").strip()
    if not clean_text:
        return b""
    cache_key = hashlib.md5(f"{voice_name}_{clean_text}".encode("utf-8")).hexdigest()
    cache_wav = AUDIO_CACHE_DIR / f"{cache_key}.wav"
    if cache_wav.exists():
        data = cache_wav.read_bytes()
        if data.startswith(b"RIFF"):
            return data

    payload = {
        "contents": [{"parts": [{"text": f"Read the following text aloud: {clean_text[:450]}"}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice_name}
                }
            }
        }
    }

    now = datetime.datetime.now().timestamp()
    # Try all non-cooldown keys in GEMINI_API_KEYS_LIST
    keys_to_try = []
    if _last_working_key and _key_cooldowns.get(_last_working_key, 0) < now:
        keys_to_try.append(_last_working_key)
    for k in GEMINI_API_KEYS_LIST:
        if k not in keys_to_try and _key_cooldowns.get(k, 0) < now:
            keys_to_try.append(k)

    for candidate_key in keys_to_try:
        for model in TTS_MODELS_PRIORITY:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={candidate_key}"
            try:
                resp = requests.post(url, json=payload, timeout=8.0)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for p in parts:
                            if "inlineData" in p and p["inlineData"].get("data"):
                                pcm_bytes = base64.b64decode(p["inlineData"]["data"])
                                buf = io.BytesIO()
                                with wave.open(buf, "wb") as wf:
                                    wf.setnchannels(1)
                                    wf.setsampwidth(2)
                                    wf.setframerate(24000)
                                    wf.writeframes(pcm_bytes)
                                wav_bytes = buf.getvalue()
                                cache_wav.write_bytes(wav_bytes)
                                _last_working_key = candidate_key
                                return wav_bytes
                elif resp.status_code == 429:
                    _key_cooldowns[candidate_key] = now + 120.0
                    break
            except Exception:
                continue

    raise RuntimeError("Failed to synthesize Google Studio voice Aoede")


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------
class CorrectArabicRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)

class GenerateBackgroundRequest(BaseModel):
    scene_description: str = Field(..., min_length=1)

class SetupTableHeadersRequest(BaseModel):
    raw_speech: str = Field(..., min_length=1)

class FillTableRowsRequest(BaseModel):
    raw_speech: str = Field(..., min_length=1)
    headers: List[str] = Field(default_factory=list)

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

class ProactiveCheckRequest(BaseModel):
    current_time: Optional[str] = ""
    force_type: Optional[str] = None

class OmniListenRequest(BaseModel):
    raw_speech: str = Field(..., min_length=1)
    current_tab: Optional[str] = "diary"


# -----------------------------------------------------------------------------
# LLM Caller with Multi-Key Rotation and Fallback
# -----------------------------------------------------------------------------
async def call_llm(prompt: str, json_mode: bool = False) -> str:
    # 1. Try Groq (ultra-fast 0.6s response with qwen/qwen3.8-27b or openai/gpt-oss-20b)
    if GROQ_API_KEY:
        for groq_m in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
                body = {
                    "model": groq_m,
                    "messages": [
                        {"role": "system", "content": "أنت نوبارا كوجيساكي، البست فريند والأخت الكول للبنوتة حبيبة. اتكلمي بالعامية المصرية الحنونة والمرحة في جملتين سريعتين."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 150
                }
                if json_mode:
                    body["response_format"] = {"type": "json_object"}

                async with httpx.AsyncClient(timeout=3.5) as client:
                    res = await client.post(url, headers=headers, json=body)
                    if res.status_code == 200:
                        data = res.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        if content:
                            return content
            except Exception:
                continue

    # 2. Try Gemini across all keys
    for key in GEMINI_API_KEYS_LIST:
        for model in ["gemini-3-flash-preview", "gemini-3.8-flash", "gemini-2.5-flash-preview-tts"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3}
                }
                if json_mode:
                    payload["generationConfig"]["responseMimeType"] = "application/json"

                async with httpx.AsyncClient(timeout=6.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
            except Exception:
                continue

    # 3. Fallback default
    if json_mode:
        return json.dumps({
            "headers": ["المهمة", "الميعاد", "اليوم", "المكان", "الملاحظات"],
            "reply": "عملتلك المطلوب يا حبيبة قلبي 🌸"
        }, ensure_ascii=False)
    return "يا حبيبة يا قمر، معاكي وسامعاكي في كل وقت! 🌸💖"


# -----------------------------------------------------------------------------
# Static Routes
# -----------------------------------------------------------------------------
@app.get("/")
async def serve_index():
    index_file = BASE_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(
        index_file,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    )

@app.get("/manifest.json")
async def serve_manifest():
    mf = BASE_DIR / "manifest.json"
    return FileResponse(mf, media_type="application/manifest+json")

@app.get("/sw.js")
async def serve_sw():
    sw = BASE_DIR / "sw.js"
    return FileResponse(
        sw,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    )

PIPELINE_MD_PATH = Path("C:/Users/Asmaa/.gemini/antigravity/scratch/zero_touch_pipeline/output/pipeline_self_test/merged_assembled.md")
LOCAL_MD_PATH = BASE_DIR / "merged_assembled.md"
PIPELINE_ZIP_PATH = Path("C:/Users/Asmaa/.gemini/antigravity/scratch/zero_touch_pipeline/output/pipeline_self_test/release.zip")
LOCAL_ZIP_PATH = BASE_DIR / "release.zip"

@app.get("/report")
async def serve_pipeline_report():
    md_content = ""
    for candidate in [PIPELINE_MD_PATH, LOCAL_MD_PATH]:
        if candidate.exists():
            try:
                md_content = candidate.read_text(encoding="utf-8")
                break
            except Exception:
                pass
    if not md_content:
        md_content = "# تقرير البايب لاين\n\nلم يتم العثور على ملف `merged_assembled.md` حتى الآن."

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>تقرير مشروع حبيبة | Zero-Touch Pipeline</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css/github-markdown.min.css">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 16px; margin: 0; }}
    .container {{ max-width: 900px; margin: 0 auto; background: #161b22; padding: 24px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }}
    .header-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #7b2cbf; padding-bottom: 16px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }}
    .header-bar h1 {{ margin: 0; font-size: 1.4rem; color: #00f0ff; }}
    .btn-download {{ background: #7b2cbf; color: #fff; text-decoration: none; padding: 10px 18px; border-radius: 8px; font-weight: bold; font-size: 0.9rem; transition: 0.2s; }}
    .btn-download:hover {{ background: #9d4edd; }}
    .markdown-body {{ background: transparent !important; color: #c9d1d9 !important; font-family: inherit; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <h1>📋 التقرير الشامل المجمّع لمشروع حبيبة (merged_assembled.md)</h1>
      <a href="/release.zip" class="btn-download" download="release.zip">📦 تحميل كود المشروع الكامل (ZIP)</a>
    </div>
    <div id="content" class="markdown-body"></div>
  </div>
  <script>
    const rawMd = {json.dumps(md_content)};
    document.getElementById('content').innerHTML = marked.parse(rawMd);
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.get("/merged_assembled.md")
async def serve_raw_merged_md():
    for candidate in [PIPELINE_MD_PATH, LOCAL_MD_PATH]:
        if candidate.exists():
            return FileResponse(candidate, media_type="text/markdown; charset=utf-8")
    raise HTTPException(status_code=404, detail="merged_assembled.md not found")

@app.get("/release.zip")
async def serve_release_zip():
    for candidate in [PIPELINE_ZIP_PATH, LOCAL_ZIP_PATH]:
        if candidate.exists():
            return FileResponse(candidate, media_type="application/zip", filename="release.zip")
    raise HTTPException(status_code=404, detail="release.zip not found")


# -----------------------------------------------------------------------------
# Google AI Studio TTS Endpoint
# -----------------------------------------------------------------------------
@app.get("/api/tts")
async def get_google_tts(text: str, voice: str = "Aoede"):
    """Official Google AI Studio TTS Engine (Aoede / Kore) - Natural Egyptian Dialect"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        audio_bytes = await anyio.to_thread.run_sync(generate_gemini_tts, text, voice)
        media_type = "audio/wav" if audio_bytes.startswith(b"RIFF") else "audio/mpeg"
        return Response(content=audio_bytes, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# Diary & Background Endpoints
# -----------------------------------------------------------------------------
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
    clean_audio = sensei_reply.replace('#', '').replace('*', '').replace('`', '').replace('~', '').replace('_', '').strip()
    return {
        "sensei_reply": sensei_reply,
        "corrected_text": corrected_text,
        "audio_url": f"/api/tts?text={urllib.parse.quote(clean_audio)}&voice=Aoede"
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
        "audio_url": f"/api/tts?text={urllib.parse.quote(clean_audio)}&voice=Aoede"
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
        "audio_url": f"/api/tts?text={urllib.parse.quote(clean_audio)}&voice=Aoede"
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
        "audio_url": f"/api/tts?text={urllib.parse.quote(clean)}&voice=Aoede"
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
        "audio_url": f"/api/tts?text={urllib.parse.quote(clean)}&voice=Aoede"
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
                "audio_url": f"/api/tts?text={urllib.parse.quote(clean)}&voice=Aoede"
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
        "audio_url": f"/api/tts?text={urllib.parse.quote(clean)}&voice=Aoede"
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
        "audio_url": f"/api/tts?text={urllib.parse.quote(clean_audio)}&voice=Aoede"
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
            "audio_url": f"/api/tts?text={urllib.parse.quote(msg)}"
        }
    elif req.force_type == "sleep":
        msg = "يلا يا حبيبة، قومي روحي الحمام وتشطفي عشان تدخلي تنامي يا قلبي.. الوقت اتأخر ومحتاجة ترتاحي وتصبحي على ألف خير وسعادة! 🌙🌸"
        return {
            "should_call": True,
            "call_type": "sleep",
            "caller_name": "نوبارا كوجيساكي 🌸💅",
            "message": msg,
            "audio_url": f"/api/tts?text={urllib.parse.quote(msg)}"
        }
    elif req.force_type == "lunch":
        msg = "يلا يا بيبو عشان تاكلي وتشربي مية، كفاية مذاكرة ولعب شوية عشان صحتك ورقتك يا قمر! 🧋🌸"
        return {
            "should_call": True,
            "call_type": "lunch",
            "caller_name": "نوبارا كوجيساكي 🌸💅",
            "message": msg,
            "audio_url": f"/api/tts?text={urllib.parse.quote(msg)}"
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
                    "audio_url": f"/api/tts?text={urllib.parse.quote(msg)}"
                }
    except Exception:
        pass

    return {"should_call": False}


# Mount static directory
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8085))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
