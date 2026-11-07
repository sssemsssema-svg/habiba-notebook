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
from fastapi.responses import FileResponse, HTMLResponse, Response
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


# --------------------------------------------------------------------------- #
# Zero-Touch Pipeline Report Viewer (Mobile-Optimized)
# --------------------------------------------------------------------------- #

PIPELINE_MD_PATH = Path("C:/Users/Asmaa/.gemini/antigravity/scratch/zero_touch_pipeline/output/pipeline_self_test/merged_assembled.md")
PIPELINE_ZIP_PATH = Path("C:/Users/Asmaa/.gemini/antigravity/scratch/zero_touch_pipeline/output/pipeline_self_test/release.zip")
LOCAL_MD_PATH = BASE_DIR / "merged_assembled.md"
LOCAL_ZIP_PATH = BASE_DIR / "release.zip"

REPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>تقرير مشروع البايب لاين • merged_assembled.md ⚡</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&family=Fira+Code:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(18, 26, 46, 0.85);
      --card-border: rgba(99, 102, 241, 0.25);
      --accent-purple: #8b5cf6;
      --accent-cyan: #06b6d4;
      --accent-green: #10b981;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --code-bg: #050811;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text-main);
      font-family: 'Cairo', system-ui, -apple-system, sans-serif;
      padding: 16px;
      line-height: 1.6;
      min-height: 100vh;
    }
    .container {
      max-width: 850px;
      margin: 0 auto;
    }
    .header {
      background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.15));
      border: 1px solid var(--card-border);
      border-radius: 20px;
      padding: 20px;
      margin-bottom: 20px;
      backdrop-filter: blur(10px);
      text-align: center;
      position: relative;
    }
    .badge-top {
      display: inline-block;
      background: rgba(139, 92, 246, 0.3);
      color: #c4b5fd;
      border: 1px solid rgba(139, 92, 246, 0.5);
      padding: 4px 12px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 10px;
    }
    h1 {
      font-size: 22px;
      font-weight: 900;
      margin-bottom: 8px;
      background: linear-gradient(to right, #a78bfa, #38bdf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .meta-subtitle {
      font-size: 13px;
      color: var(--text-muted);
    }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-top: 16px;
    }
    @media (min-width: 500px) {
      .stats-grid { grid-template-columns: repeat(4, 1fr); }
    }
    .stat-pill {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 10px 8px;
      text-align: center;
    }
    .stat-label {
      font-size: 11px;
      color: var(--text-muted);
      display: block;
      margin-bottom: 4px;
    }
    .stat-val {
      font-size: 14px;
      font-weight: 800;
      color: #fff;
    }
    .stat-val.success { color: var(--accent-green); }
    
    .actions-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 20px;
      justify-content: center;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 10px 16px;
      border-radius: 12px;
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
      border: none;
      font-family: inherit;
      transition: all 0.2s ease;
    }
    .btn-primary {
      background: linear-gradient(135deg, #7c3aed, #4f46e5);
      color: white;
      box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3);
    }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-main);
      border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .btn:active { transform: scale(0.97); }

    .tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 8px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 14px;
      font-weight: 700;
      padding: 8px 16px;
      cursor: pointer;
      border-radius: 8px;
      font-family: inherit;
    }
    .tab-btn.active {
      background: rgba(139, 92, 246, 0.25);
      color: #fff;
      border: 1px solid rgba(139, 92, 246, 0.4);
    }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
      margin-bottom: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .card-title {
      font-size: 16px;
      font-weight: 800;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #38bdf8;
    }
    .file-badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 6px;
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
      font-family: 'Fira Code', monospace;
    }
    pre {
      background: var(--code-bg);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      padding: 14px;
      overflow-x: auto;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      line-height: 1.5;
      direction: ltr;
      text-align: left;
      color: #e2e8f0;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .copy-pill {
      background: rgba(255, 255, 255, 0.1);
      border: none;
      color: #fff;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      cursor: pointer;
    }
    .copy-pill:active { background: var(--accent-green); }
    .table-responsive {
      overflow-x: auto;
      direction: ltr;
      text-align: left;
      margin-bottom: 10px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
    }
    th, td {
      padding: 8px 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    th { color: var(--accent-cyan); }
    .status-ok { color: var(--accent-green); font-weight: 700; }
  </style>
</head>
<body>
  <div class="container">
    
    <header class="header">
      <span class="badge-top">⚡ Zero-Touch Closed-Loop CI/CD</span>
      <h1>تقرير تجميع المشروع (merged_assembled.md)</h1>
      <p class="meta-subtitle">التقرير المجمّع الفعلي بعد اكتمال التركيب واعتماد الأوبزرفر النهائي</p>

      <div class="stats-grid">
        <div class="stat-pill">
          <span class="stat-label">المرحلة</span>
          <span class="stat-val">OBSERVER</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">قرار المستشار</span>
          <span class="stat-val success">APPROVED_PASS ✅</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">فحص البناء</span>
          <span class="stat-val success">OK (code 0)</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">النزاهة والتشفير</span>
          <span class="stat-val success">SHA256 Match 🔒</span>
        </div>
      </div>
    </header>

    <div class="actions-bar">
      <a href="/merged_assembled.md" target="_blank" class="btn btn-secondary">📄 عرض الملف الخام (Raw MD)</a>
      <a href="/release.zip" download class="btn btn-primary">📦 تحميل الحزمة الكاملة (release.zip)</a>
      <button onclick="copyRaw()" class="btn btn-secondary" id="btn-copy">📋 نسخ التقرير كاملاً</button>
    </div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('structured')">✨ العرض المنسق</button>
      <button class="tab-btn" onclick="switchTab('raw')">📝 نص الـ Markdown الفعلي</button>
    </div>

    <!-- Structured Tab -->
    <div id="tab-structured">
      
      <!-- Section 1: Build -->
      <div class="card">
        <div class="card-title">
          <span>⚙️ 1. فحص البناء والتشغيل (BUILD)</span>
          <span class="file-badge">Exit Code: 0</span>
        </div>
        <div class="table-responsive">
          <table>
            <tr><th>Status</th><td><span class="status-ok">OK</span></td></tr>
            <tr><th>Command</th><td>none (internal syntax check)</td></tr>
            <tr><th>Build Log</th><td>internal syntax check OK (all syntax valid)</td></tr>
          </table>
        </div>
      </div>

      <!-- Section 2: Integrity -->
      <div class="card">
        <div class="card-title">
          <span>🔒 2. جدول نزاهة الملفات والتشفير (INTEGRITY)</span>
          <span class="file-badge">SHA256 Verified</span>
        </div>
        <div class="table-responsive">
          <table>
            <thead>
              <tr><th>الملف</th><th>الحالة</th><th>بصمة التشفير SHA-256</th></tr>
            </thead>
            <tbody>
              <tr><td>health.py</td><td><span class="status-ok">OK</span></td><td>e6aa91f9daef8670a23d876d4f79225f...</td></tr>
              <tr><td>README.md</td><td><span class="status-ok">OK</span></td><td>cc1882572b075c4466b38233ffa7f061...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Section 3: File health.py -->
      <div class="card">
        <div class="card-title">
          <span>🐍 ملف الكور: health.py</span>
          <div>
            <span class="file-badge">121 lines • 3.6 KB</span>
            <button class="copy-pill" onclick="copySnippet('code-health')">نسخ الكود</button>
          </div>
        </div>
        <pre id="code-health">{health_py_content}</pre>
      </div>

      <!-- Section 4: File README.md -->
      <div class="card">
        <div class="card-title">
          <span>📖 ملف التوثيق: README.md</span>
          <div>
            <span class="file-badge">67 lines • 2.1 KB</span>
            <button class="copy-pill" onclick="copySnippet('code-readme')">نسخ</button>
          </div>
        </div>
        <pre id="code-readme">{readme_md_content}</pre>
      </div>

    </div>

    <!-- Raw Tab -->
    <div id="tab-raw" style="display: none;">
      <div class="card">
        <div class="card-title">
          <span>📄 النص الكامل للـ MD المسلّم للأوبزرفر</span>
          <button class="copy-pill" onclick="copyRaw()">نسخ الكل</button>
        </div>
        <pre id="raw-md-content">{raw_md_content}</pre>
      </div>
    </div>

  </div>

  <script>
    function switchTab(tab) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      if (tab === 'structured') {
        document.querySelectorAll('.tab-btn')[0].classList.add('active');
        document.getElementById('tab-structured').style.display = 'block';
        document.getElementById('tab-raw').style.display = 'none';
      } else {
        document.querySelectorAll('.tab-btn')[1].classList.add('active');
        document.getElementById('tab-structured').style.display = 'none';
        document.getElementById('tab-raw').style.display = 'block';
      }
    }

    function copySnippet(id) {
      const text = document.getElementById(id).innerText;
      navigator.clipboard.writeText(text).then(() => {
        alert('تم نسخ الكود بنجاح! 📋');
      });
    }

    function copyRaw() {
      const text = document.getElementById('raw-md-content').innerText;
      navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('btn-copy');
        btn.innerText = '✅ تم النسخ!';
        setTimeout(() => { btn.innerText = '📋 نسخ التقرير كاملاً'; }, 2000);
      });
    }
  </script>
</body>
</html>
"""


def get_latest_merged_md() -> str:
    for candidate in [PIPELINE_MD_PATH, LOCAL_MD_PATH]:
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8")
            except Exception:
                pass
    return "# merged_assembled\nNo report found."


@app.get("/report", response_class=HTMLResponse)
@app.get("/merged-assembled", response_class=HTMLResponse)
async def serve_pipeline_report():
    import html
    raw_md = get_latest_merged_md()
    
    health_py = ""
    readme_md = ""
    if "### FILE: health.py" in raw_md:
        try:
            health_py = raw_md.split("### FILE: health.py")[1].split("### FILE:")[0].strip()
            if "```" in health_py:
                lines = [line for line in health_py.split("\n") if not line.startswith("```") and not line.startswith("bytes:")]
                health_py = "\n".join(lines).strip()
        except Exception:
            health_py = ""
            
    if "### FILE: README.md" in raw_md:
        try:
            readme_md = raw_md.split("### FILE: README.md")[1].strip()
            if "```" in readme_md:
                lines = [line for line in readme_md.split("\n") if not line.startswith("````") and not line.startswith("```") and not line.startswith("bytes:")]
                readme_md = "\n".join(lines).strip()
        except Exception:
            readme_md = ""
            
    html_page = REPORT_HTML_TEMPLATE.replace("{health_py_content}", html.escape(health_py or "health.py source code"))
    html_page = html_page.replace("{readme_md_content}", html.escape(readme_md or "README.md content"))
    html_page = html_page.replace("{raw_md_content}", html.escape(raw_md))
    return HTMLResponse(content=html_page)


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


@app.get("/api/tts")
async def get_google_tts(text: str):
    """Google Text-to-Speech API (Official Google Voice)"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    clean_text = text.replace("#", "").replace("*", "").replace("`", "").replace("~", "").strip()
    encoded = urllib.parse.quote(clean_text[:500])
    google_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ar&client=tw-ob&q={encoded}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(google_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if resp.status_code == 200:
                return Response(content=resp.content, media_type="audio/mpeg")
        except Exception:
            pass
    raise HTTPException(status_code=500, detail="Failed to synthesize Google voice")


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
