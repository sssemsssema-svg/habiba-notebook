/**
 * Smart Voice-Enabled Anime Notebook (Habiba's Secret Diary & Nobara Bestie Edition)
 * Real-Time Streaming Dictation + Simulated Phone Call + Ambient Background Bestie Companion
 */

document.addEventListener("DOMContentLoaded", () => {
  // -------------------------------------------------------------------------
  // 1. Text-To-Speech (Nobara Bestie Voice Output in Warm Egyptian Arabic)
  // -------------------------------------------------------------------------
  function speakNobara(text, onEnd) {
    if (!('speechSynthesis' in window)) {
      if (onEnd) onEnd();
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "ar-EG";
      utterance.rate = 1.05;
      utterance.pitch = 1.15; // Cheerful, sweet female tone

      const voices = window.speechSynthesis.getVoices();
      const arVoice = voices.find(v => v.lang.startsWith("ar"));
      if (arVoice) utterance.voice = arVoice;

      if (onEnd) {
        utterance.onend = onEnd;
        utterance.onerror = onEnd;
      }

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("TTS error:", e);
      if (onEnd) onEnd();
    }
  }

  // -------------------------------------------------------------------------
  // 2. Synthesized Telephone Ringtone (Web Audio API - 100% Reliable & Mobile-Safe)
  // -------------------------------------------------------------------------
  let ringtoneAudioCtx = null;
  let ringtoneInterval = null;

  function startRingtone() {
    stopRingtone();
    try {
      ringtoneAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const playMelody = () => {
        if (!ringtoneAudioCtx || ringtoneAudioCtx.state === "closed") return;
        const notes = [659.25, 830.61, 987.77, 1318.51, 987.77, 1318.51];
        notes.forEach((freq, idx) => {
          const osc = ringtoneAudioCtx.createOscillator();
          const gain = ringtoneAudioCtx.createGain();
          osc.type = "sine";
          const startTime = ringtoneAudioCtx.currentTime + idx * 0.12;
          osc.frequency.setValueAtTime(freq, startTime);
          gain.gain.setValueAtTime(0.25, startTime);
          gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.32);
          osc.connect(gain);
          gain.connect(ringtoneAudioCtx.destination);
          osc.start(startTime);
          osc.stop(startTime + 0.35);
        });
      };
      playMelody();
      ringtoneInterval = setInterval(playMelody, 1600);
    } catch (e) {
      console.warn("Ringtone error:", e);
    }
  }

  function stopRingtone() {
    if (ringtoneInterval) {
      clearInterval(ringtoneInterval);
      ringtoneInterval = null;
    }
    if (ringtoneAudioCtx) {
      try { ringtoneAudioCtx.close(); } catch (e) {}
      ringtoneAudioCtx = null;
    }
  }

  // -------------------------------------------------------------------------
  // 3. Tab Switching System (Bookmark Ribbons)
  // -------------------------------------------------------------------------
  const tabs = document.querySelectorAll(".tab-ribbon");
  const tabContents = document.querySelectorAll(".tab-content");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tabContents.forEach((c) => c.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });

  // Mood selector
  const moodChips = document.querySelectorAll(".mood-chip");
  moodChips.forEach((btn) => {
    btn.addEventListener("click", () => {
      moodChips.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const mood = btn.getAttribute("data-mood");
      let reply = "مود رايق وجميل 🌸 دفترك جاهز لكل أفكارك يا حبيبة قلبي!";
      if (mood === "super") reply = "طاقتك خارقة النهاردة وقمر! ⚡ أنا فخورة بيكي يا أحلى بيبو!";
      else if (mood === "gaming") reply = "مود الجيمينج شغال! 🎮 قوليلي بتلعبي إيه وأنا أشجعك يا حبيبة؟";
      else if (mood === "chill") reply = "وقت البوبا والروقان 🧋 احكيلي براحتك يا بيبو أنا سامعاكي ديماً.";
      showNobaraMessage(reply);
      speakNobara(reply);
    });
  });

  // Date display in Arabic
  const dateEl = document.getElementById("current-date");
  if (dateEl) {
    const today = new Date();
    const options = { weekday: "long", day: "numeric", month: "long" };
    dateEl.innerText = today.toLocaleDateString("ar-EG", options);
  }

  // Web Speech Recognition API Setup
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  // -------------------------------------------------------------------------
  // 4. AMBIENT BACKGROUND BESTIE COMPANION (نوبارا شغالة مع حبيبة في الخلفية)
  // -------------------------------------------------------------------------
  const ambientToggleBtn = document.getElementById("btn-toggle-ambient");
  const ambientToggleLabel = document.getElementById("ambient-toggle-label");
  const ambientStatusText = document.getElementById("ambient-status-text");
  const assistantBubble = document.getElementById("assistant-bubble");
  const btnAmbientMic = document.getElementById("btn-ambient-mic");
  let isAmbientActive = true;

  function showNobaraMessage(msg) {
    if (assistantBubble) {
      assistantBubble.style.opacity = 0;
      setTimeout(() => {
        assistantBubble.innerText = msg;
        assistantBubble.style.opacity = 1;
      }, 150);
    }
  }

  // Extract tasks from Habiba's 7-column table
  function getNotebookTasks() {
    const tasks = [];
    document.querySelectorAll("#missions-table tbody tr").forEach((tr) => {
      const cells = tr.querySelectorAll("td");
      if (cells.length >= 6) {
        tasks.push({
          task: cells[0].innerText.trim(),
          time: cells[1].innerText.trim(),
          date: cells[2].innerText.trim(),
          location: cells[3].innerText.trim(),
          tools: cells[4].innerText.trim(),
          notes: cells[5].innerText.trim()
        });
      }
    });
    return tasks;
  }

  // Ambient Assist API Call
  async function triggerAmbientAssist(intent = "chat", userMessage = "") {
    const tasks = getNotebookTasks();
    const diaryText = document.getElementById("diary-textarea")?.value || "";
    const now = new Date();
    const currentHour = now.getHours();
    const currentTime = now.toLocaleTimeString("ar-EG", { hour: "numeric", minute: "numeric" });

    if (ambientStatusText) ambientStatusText.innerText = "نوبارا بتفكر وبترد على حبيبة... 🌸";

    try {
      const res = await fetch("/api/bestie/ambient-assist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_message: userMessage,
          intent: intent,
          tasks: tasks,
          diary_snippet: diaryText,
          current_time: currentTime,
          current_hour: currentHour
        })
      });
      const data = await res.json();
      const reply = data.reply || "يا حبيبة قلبي أنا جنبك وشايفة كل حاجة في دفترك 💖🌸";

      showNobaraMessage(reply);
      speakNobara(reply);
      if (ambientStatusText) ambientStatusText.innerText = "نوبارا جنبك وسامعاكي وشايفة جدولك ومذكراتك يا حبيبة ✨";
    } catch (e) {
      console.error(e);
      if (ambientStatusText) ambientStatusText.innerText = "نوبارا جنبك وسامعاكي دايماً 💖";
    }
  }

  // Care Chips Clicking
  document.querySelectorAll(".care-chip[data-intent]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const intent = chip.getAttribute("data-intent");
      triggerAmbientAssist(intent, "");
    });
  });

  // Ambient Mic (Talk to Nobara anytime without leaving notebook)
  if (SpeechRecognition) {
    const ambientRec = new SpeechRecognition();
    ambientRec.lang = "ar-EG";
    ambientRec.onresult = (e) => {
      const spoken = e.results[0][0].transcript;
      triggerAmbientAssist("chat", spoken);
    };
    ambientRec.onstart = () => {
      btnAmbientMic?.classList.add("speaking");
      if (ambientStatusText) ambientStatusText.innerText = "سامعاكي يا حبيبة.. احكيلي! 🎙️";
    };
    ambientRec.onend = () => {
      btnAmbientMic?.classList.remove("speaking");
    };

    btnAmbientMic?.addEventListener("click", () => {
      try { ambientRec.start(); } catch (e) { ambientRec.stop(); }
    });
  }

  // Toggle Ambient On/Off
  ambientToggleBtn?.addEventListener("click", () => {
    isAmbientActive = !isAmbientActive;
    if (isAmbientActive) {
      ambientToggleBtn.classList.add("active");
      if (ambientToggleLabel) ambientToggleLabel.innerText = "نوبارا شغالة 🟢";
      if (ambientStatusText) ambientStatusText.innerText = "نوبارا شايفة جدولك ومذكراتك وسامعاكي يا حبيبة ✨";
      const startMsg = "أنا شغالة في الخلفية معاكي يا حبيبة قلبي! اتصفحي براحتك وأنا في ضهرك دايماً 🌸";
      showNobaraMessage(startMsg);
      speakNobara(startMsg);
    } else {
      ambientToggleBtn.classList.remove("active");
      if (ambientToggleLabel) ambientToggleLabel.innerText = "نوبارا متوقفة ⚪";
      if (ambientStatusText) ambientStatusText.innerText = "تم إيقاف الرفيقة في الخلفية مؤقتاً";
    }
  });

  // Automated Care Reminders (Every 3.5 minutes while ambient mode is active)
  setInterval(() => {
    if (isAmbientActive) {
      const now = new Date();
      const hr = now.getHours();
      const randomIntents = hr >= 20 ? ["sleep_check", "health_check"] : ["health_check", "remind_tasks"];
      const chosenIntent = randomIntents[Math.floor(Math.random() * randomIntents.length)];
      triggerAmbientAssist(chosenIntent, "");
    }
  }, 210000);

  // -------------------------------------------------------------------------
  // 5. SIMULATED PHONE CALL SYSTEM (مكالمة هاتفية مع نوبارا)
  // -------------------------------------------------------------------------
  const incomingCallModal = document.getElementById("incoming-call-modal");
  const activeCallModal = document.getElementById("active-call-modal");
  const btnHeaderCall = document.getElementById("btn-header-call");
  const btnCardCall = document.getElementById("btn-card-call");
  const btnAcceptCall = document.getElementById("btn-accept-call");
  const btnDeclineCall = document.getElementById("btn-decline-call");
  const btnEndCall = document.getElementById("btn-end-call");
  const btnCallMicToggle = document.getElementById("btn-call-mic-toggle");
  const callTimerEl = document.getElementById("call-timer");
  const nobaraLiveReplyEl = document.getElementById("nobara-live-reply");
  const userCallLiveTextEl = document.getElementById("user-call-live-text");
  const nobaraCallStatusEl = document.getElementById("nobara-call-status");

  let callSeconds = 0;
  let callTimerInterval = null;
  let callRecognizer = null;
  let isCallActive = false;

  function triggerIncomingCall() {
    if (isCallActive) return;
    startRingtone();
    incomingCallModal?.classList.remove("hidden");
  }

  btnHeaderCall?.addEventListener("click", triggerIncomingCall);
  btnCardCall?.addEventListener("click", triggerIncomingCall);

  btnDeclineCall?.addEventListener("click", () => {
    stopRingtone();
    incomingCallModal?.classList.add("hidden");
  });

  btnAcceptCall?.addEventListener("click", async () => {
    stopRingtone();
    incomingCallModal?.classList.add("hidden");
    activeCallModal?.classList.remove("hidden");
    startActiveCallSession();
  });

  async function startActiveCallSession() {
    isCallActive = true;
    callSeconds = 0;
    if (callTimerEl) callTimerEl.innerText = "00:00";
    if (nobaraCallStatusEl) nobaraCallStatusEl.innerText = "نوبارا بترد على حبيبة لايف...";
    if (userCallLiveTextEl) userCallLiveTextEl.innerText = "تحدثي، كلامك بيظهر هنا لايف...";

    callTimerInterval = setInterval(() => {
      callSeconds++;
      const mins = String(Math.floor(callSeconds / 60)).padStart(2, "0");
      const secs = String(callSeconds % 60).padStart(2, "0");
      if (callTimerEl) callTimerEl.innerText = `${mins}:${secs}`;
    }, 1000);

    const opener = "ألوو يا حبيبة يا قلبي! وحشتيني أوي.. عاملة إيه يا بيبو؟ أنا معاكي وسامعاكي قوليلي كل اللي في قلبك! 💖🌸";
    if (nobaraLiveReplyEl) nobaraLiveReplyEl.innerText = opener;
    speakNobara(opener, () => {
      if (isCallActive) startCallSpeechRecognition();
    });
  }

  function startCallSpeechRecognition() {
    if (!SpeechRecognition || !isCallActive) return;
    try { if (callRecognizer) callRecognizer.stop(); } catch(e) {}

    callRecognizer = new SpeechRecognition();
    callRecognizer.lang = "ar-EG";
    callRecognizer.continuous = true;
    callRecognizer.interimResults = true;

    let callFinalText = "";
    let pauseTimer = null;

    callRecognizer.onstart = () => {
      btnCallMicToggle?.classList.add("speaking");
      if (nobaraCallStatusEl) nobaraCallStatusEl.innerText = "نوبارا بتسمعك يا حبيبة.. اتكلمي براحتك 🎙️";
    };

    callRecognizer.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          callFinalText += text + " ";
        } else {
          interim += text;
        }
      }

      const stream = (callFinalText + " " + interim).trim();
      if (userCallLiveTextEl) userCallLiveTextEl.innerText = stream;

      clearTimeout(pauseTimer);
      pauseTimer = setTimeout(() => {
        if (stream && isCallActive) {
          sendCallMessageToNobara(stream);
          callFinalText = "";
        }
      }, 2200);
    };

    callRecognizer.onend = () => {
      btnCallMicToggle?.classList.remove("speaking");
      if (isCallActive) {
        try { callRecognizer.start(); } catch(e) {}
      }
    };

    try {
      callRecognizer.start();
    } catch(e) {
      console.warn("Call mic error:", e);
    }
  }

  async function sendCallMessageToNobara(message) {
    if (!message || !isCallActive) return;
    if (nobaraCallStatusEl) nobaraCallStatusEl.innerText = "نوبارا بتفكر وبترد على حبيبة... 💖";

    try {
      try { callRecognizer?.stop(); } catch(e) {}

      const res = await fetch("/api/bestie/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_message: `حبيبة بتقولك: ${message}` }),
      });
      const data = await res.json();
      const reply = data.reply || "يا حبيبة قلبي أنا في ضهرك ومعاكي دايماً، كملي حكايتك أنا سامعاكي! 🌸";

      if (nobaraLiveReplyEl) nobaraLiveReplyEl.innerText = reply;
      speakNobara(reply, () => {
        if (isCallActive) {
          if (userCallLiveTextEl) userCallLiveTextEl.innerText = "تحدثي، كلامك بيظهر هنا لايف...";
          startCallSpeechRecognition();
        }
      });
    } catch (e) {
      console.error(e);
      if (isCallActive) startCallSpeechRecognition();
    }
  }

  btnEndCall?.addEventListener("click", () => {
    isCallActive = false;
    clearInterval(callTimerInterval);
    try { callRecognizer?.stop(); } catch(e) {}
    activeCallModal?.classList.add("hidden");
    const signOff = "باي يا حبيبة قلبي، هتوحشيني وهرن عليكي تاني قريب أوي! 💖🌸";
    showNobaraMessage(signOff);
    speakNobara(signOff);
  });

  // -------------------------------------------------------------------------
  // 6. FEATURE 1: REAL-TIME STREAMING DIARY (كلمة بكلمة لحبيبة)
  // -------------------------------------------------------------------------
  const diaryTextarea = document.getElementById("diary-textarea");
  const diaryMicBtn = document.getElementById("btn-diary-mic");
  const diaryVoiceStatus = document.getElementById("diary-voice-status");
  const diaryBgOverlay = document.getElementById("diary-bg-overlay");
  const diaryLiveBar = document.getElementById("diary-live-stream-bar");
  const diaryLiveWords = document.getElementById("diary-live-words");

  const savedDiary = localStorage.getItem("habiba_diary_text");
  if (savedDiary && diaryTextarea) {
    diaryTextarea.value = savedDiary;
  }

  document.getElementById("btn-save-diary")?.addEventListener("click", () => {
    localStorage.setItem("habiba_diary_text", diaryTextarea.value);
    const msg = "عاش يا حبيبة قلبي! مذكراتك وأسرارك اتحفظت بأمان في دفترنا 🌸💖";
    showNobaraMessage(msg);
    speakNobara(msg);
  });

  document.getElementById("btn-clear-diary")?.addEventListener("click", () => {
    if (confirm("عايزة تمسحي المكتوب في الصفحة دي ونبدأ صفحة جديدة يا حبيبة؟")) {
      diaryTextarea.value = "";
      localStorage.removeItem("habiba_diary_text");
      const msg = "الصفحة بيضاء ونظيفة وجاهزة لمغامرتك وأسرارك الجديدة يا حبيبة! ✨";
      showNobaraMessage(msg);
      speakNobara(msg);
    }
  });

  let diaryRecognizer = null;
  let isDiaryRecording = false;
  let diaryFinalTranscript = "";
  let diaryBaseText = "";

  if (SpeechRecognition) {
    diaryRecognizer = new SpeechRecognition();
    diaryRecognizer.lang = "ar-EG";
    diaryRecognizer.continuous = true;
    diaryRecognizer.interimResults = true;

    diaryRecognizer.onstart = () => {
      diaryMicBtn?.classList.add("listening");
      diaryLiveBar?.classList.remove("hidden");
      diaryVoiceStatus.innerText = "🔴 المايك شغال وسامعك يا حبيبة كلمة بكلمة.. اضغطي لإيقاف التسجيل ⏹️";
    };

    diaryRecognizer.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          diaryFinalTranscript += text + " ";
        } else {
          interim += text;
        }
      }

      const liveFull = (diaryFinalTranscript + " " + interim).trim();
      if (diaryLiveWords) diaryLiveWords.innerText = liveFull || "بيسمع صوت حبيبة الآن...";

      if (diaryTextarea) {
        const prefix = diaryBaseText ? diaryBaseText + "\n\n" : "";
        diaryTextarea.value = prefix + liveFull;
        diaryTextarea.scrollTop = diaryTextarea.scrollHeight;
      }
    };

    diaryRecognizer.onend = () => {
      if (isDiaryRecording) {
        try { diaryRecognizer.start(); } catch (e) {}
      } else {
        diaryMicBtn?.classList.remove("listening");
        diaryLiveBar?.classList.add("hidden");
        handleDiaryVoiceFinished();
      }
    };

    diaryRecognizer.onerror = (event) => {
      if (event.error === "no-speech") {
        diaryVoiceStatus.innerText = "🔴 سامعاكي يا حبيبة.. احكي أول ما تبدأي!";
      }
    };

    diaryMicBtn?.addEventListener("click", () => {
      if (!isDiaryRecording) {
        isDiaryRecording = true;
        diaryFinalTranscript = "";
        diaryBaseText = diaryTextarea.value.trim();
        if (diaryLiveWords) diaryLiveWords.innerText = "جاهزة وبسمع حبيبة أول بأول...";
        try { diaryRecognizer.start(); } catch (e) {}
      } else {
        isDiaryRecording = false;
        try { diaryRecognizer.stop(); } catch (e) {}
      }
    });
  }

  async function handleDiaryVoiceFinished() {
    const spokenText = (diaryFinalTranscript || diaryLiveWords?.innerText || "").trim();
    if (!spokenText || spokenText.startsWith("جاهزة وبسمع")) {
      diaryVoiceStatus.innerText = "اضغطي المايك واحكي.. نوبارا جنبك وسامعاكي! 🌸";
      return;
    }

    diaryVoiceStatus.innerText = "نوبارا بتسمعك وبتظبطلك الرد بالمصري يا حبيبة... 🪄";
    showNobaraMessage("سمعتك كويس أوي يا بيبو.. بجهزلك الرد الجميل دلوقتي ⏳");

    try {
      const response = await fetch("/api/diary/correct-arabic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: spokenText }),
      });
      const data = await response.json();

      const nobaraReply = data.sensei_reply || "يا حبيبة قلبي سمعتك وسجلت كل كلمة في دفترنا السحري 💖🌸";
      const corrected = data.corrected_text || spokenText;

      showNobaraMessage(nobaraReply);
      speakNobara(nobaraReply);

      const prefix = diaryBaseText ? diaryBaseText + "\n\n" : "";
      diaryTextarea.value = prefix + corrected;
      localStorage.setItem("habiba_diary_text", diaryTextarea.value);

      diaryVoiceStatus.innerText = "تمت الصياغة بالعامية المصرية وتسجيل مذكراتك بنجاح! 🌸";
    } catch (err) {
      console.error(err);
      diaryVoiceStatus.innerText = "تم حفظ الكلام المسجل في الدفتر 🌸";
    }
  }

  // -------------------------------------------------------------------------
  // 7. Background AI Drawer
  // -------------------------------------------------------------------------
  const bgDrawer = document.getElementById("bg-drawer");
  const btnToggleBg = document.getElementById("btn-toggle-bg-drawer");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");
  const bgInput = document.getElementById("bg-scene-input");
  const bgMicBtn = document.getElementById("btn-bg-mic");
  const generateBgBtn = document.getElementById("btn-generate-bg");

  btnToggleBg?.addEventListener("click", () => {
    bgDrawer?.classList.toggle("hidden");
  });
  btnCloseDrawer?.addEventListener("click", () => {
    bgDrawer?.classList.add("hidden");
  });

  document.querySelectorAll(".preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (bgInput) bgInput.value = prompt;
      triggerBgGeneration(prompt);
    });
  });

  const savedBg = localStorage.getItem("habiba_diary_bg");
  if (savedBg && diaryBgOverlay) {
    diaryBgOverlay.style.backgroundImage = `url('${savedBg}')`;
  }

  async function triggerBgGeneration(sceneText) {
    if (!sceneText || !sceneText.trim()) return;
    const msg = `برسملك خلفية أنمي قمر عن: "${sceneText}" يا حبيبة... 🎨`;
    showNobaraMessage(msg);
    speakNobara("ثانية واحدة ونوبارا هتغيرلك الخلفية لأجمل منظر أنمي!");

    try {
      const res = await fetch("/api/diary/generate-background", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scene_description: sceneText }),
      });
      const data = await res.json();
      if (data.image_url) {
        const img = new Image();
        img.onload = () => {
          diaryBgOverlay.style.backgroundImage = `url('${data.image_url}')`;
          localStorage.setItem("habiba_diary_bg", data.image_url);
          const doneMsg = "شوفي الخلفية الأنمي بقت ورا مذكراتنا إزاي يا بيبو! واو بجد 🌸💖";
          showNobaraMessage(doneMsg);
          speakNobara(doneMsg);
          bgDrawer?.classList.add("hidden");
        };
        img.src = data.image_url;
      }
    } catch (e) {
      console.error(e);
    }
  }

  generateBgBtn?.addEventListener("click", () => {
    triggerBgGeneration(bgInput?.value);
  });

  if (SpeechRecognition) {
    const bgRec = new SpeechRecognition();
    bgRec.lang = "ar-EG";
    bgRec.onresult = (e) => {
      const txt = e.results[0][0].transcript;
      if (bgInput) bgInput.value = txt;
      triggerBgGeneration(txt);
    };
    bgMicBtn?.addEventListener("click", () => {
      try { bgRec.start(); } catch (e) { bgRec.stop(); }
    });
  }

  // -------------------------------------------------------------------------
  // 8. FEATURE 2: SMART VOICE TABLE (7 Columns + Master Mic)
  // -------------------------------------------------------------------------
  const tableMasterMicBtn = document.getElementById("btn-table-master-mic");
  const tableBody = document.getElementById("table-body");
  const tableVoiceStatus = document.getElementById("table-voice-status");
  const tableLiveBar = document.getElementById("table-live-stream-bar");
  const tableLiveWords = document.getElementById("table-live-words");
  const btnAddManualRow = document.getElementById("btn-add-manual-row");
  const btnClearTable = document.getElementById("btn-clear-table");

  const savedTable = localStorage.getItem("habiba_table_rows");
  if (savedTable && tableBody) {
    tableBody.innerHTML = savedTable;
    bindTableEvents();
  }

  function saveTableToStorage() {
    localStorage.setItem("habiba_table_rows", tableBody.innerHTML);
  }

  let tableRecognizer = null;
  let isTableRecording = false;
  let tableFinalTranscript = "";

  if (SpeechRecognition) {
    tableRecognizer = new SpeechRecognition();
    tableRecognizer.lang = "ar-EG";
    tableRecognizer.continuous = true;
    tableRecognizer.interimResults = true;

    tableRecognizer.onstart = () => {
      tableMasterMicBtn?.classList.add("listening");
      tableLiveBar?.classList.remove("hidden");
      tableVoiceStatus.innerText = "🔴 سامعاكي يا حبيبة وبفرّغ مهمتك كلمة بكلمة.. اضغطي لإيقاف التسجيل ⏹️";
    };

    tableRecognizer.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          tableFinalTranscript += text + " ";
        } else {
          interim += text;
        }
      }
      const stream = (tableFinalTranscript + " " + interim).trim();
      if (tableLiveWords) tableLiveWords.innerText = stream;
    };

    tableRecognizer.onend = () => {
      if (isTableRecording) {
        try { tableRecognizer.start(); } catch (e) {}
      } else {
        tableMasterMicBtn?.classList.remove("listening");
        tableLiveBar?.classList.add("hidden");
        handleTableVoiceFinished();
      }
    };

    tableMasterMicBtn?.addEventListener("click", () => {
      if (!isTableRecording) {
        isTableRecording = true;
        tableFinalTranscript = "";
        if (tableLiveWords) tableLiveWords.innerText = "سامعاكي يا حبيبة.. قولي ميعادك ومكانك وكل تفاصيلك!";
        try { tableRecognizer.start(); } catch (e) {}
      } else {
        isTableRecording = false;
        try { tableRecognizer.stop(); } catch (e) {}
      }
    });
  }

  async function handleTableVoiceFinished() {
    const spoken = (tableFinalTranscript || tableLiveWords?.innerText || "").trim();
    if (!spoken || spoken.startsWith("سامعاكي")) {
      tableVoiceStatus.innerText = "جاهزة للاستماع لمهمتك يا حبيبة..";
      return;
    }

    tableVoiceStatus.innerText = "جاري فهم المهمة وتوزيعها في الأعمدة الـ 7... ⏳";

    try {
      const res = await fetch("/api/table/parse-task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speech_text: spoken }),
      });
      const rowData = await res.json();
      addTableRow(rowData);

      tableVoiceStatus.innerText = "تمت إضافة المهمة إلى جدولك بنجاح! ⚡";
      const reply = `شاطرة يا حبيبة قلبي! سجلتلك مهمة "${rowData.task}" في ميعادها ومكانها 🎯`;
      showNobaraMessage(reply);
      speakNobara(reply);
    } catch (err) {
      console.error(err);
      tableVoiceStatus.innerText = "حصل خطأ، اضغطي المايك وجربي تاني 🌸";
    }
  }

  function addTableRow(data) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td contenteditable="true">${data.task || "مهمة جديدة"}</td>
      <td contenteditable="true">${data.time || "5:00 م"}</td>
      <td contenteditable="true">${data.date || "اليوم"}</td>
      <td contenteditable="true">${data.location || "-"}</td>
      <td contenteditable="true">${data.tools || "-"}</td>
      <td contenteditable="true">${data.notes || "-"}</td>
      <td>
        <select class="status-select">
          <option value="pending" selected>⚡ قيد التنفيذ</option>
          <option value="done">✨ تمت بنجاح</option>
          <option value="delayed">⏳ مؤجلة</option>
        </select>
      </td>
      <td><button class="btn-del-row" title="حذف">🗑️</button></td>
    `;
    tableBody?.prepend(tr);
    bindRowEvents(tr);
    saveTableToStorage();
  }

  function bindRowEvents(row) {
    row.querySelector(".btn-del-row")?.addEventListener("click", () => {
      row.remove();
      saveTableToStorage();
    });
    row.querySelectorAll('td[contenteditable="true"]').forEach((cell) => {
      cell.addEventListener("blur", saveTableToStorage);
    });
    row.querySelector(".status-select")?.addEventListener("change", saveTableToStorage);
  }

  function bindTableEvents() {
    tableBody?.querySelectorAll("tr").forEach(bindRowEvents);
  }
  bindTableEvents();

  btnAddManualRow?.addEventListener("click", () => {
    addTableRow({
      task: "مهمة جديدة مع نوبارا",
      time: "الساعة ...",
      date: "غداً",
      location: "النادي",
      tools: "الشنطة",
      notes: "تسجيل يدوي",
      status: "قيد التنفيذ"
    });
  });

  btnClearTable?.addEventListener("click", () => {
    if (confirm("عايزة تمسحي كل المهام وتبدئي جدول جديد يا حبيبة؟")) {
      if (tableBody) tableBody.innerHTML = "";
      localStorage.removeItem("habiba_table_rows");
      const msg = "الجدول بقى فاضي وجاهز لمهماتك الجديدة يا بيبو! 🎯";
      showNobaraMessage(msg);
      speakNobara(msg);
    }
  });

  // -------------------------------------------------------------------------
  // 9. FEATURE 3: MAGIC ANIME STUDIO (Polaroid Cards)
  // -------------------------------------------------------------------------
  const studioInput = document.getElementById("studio-prompt-input");
  const studioMicBtn = document.getElementById("btn-studio-mic");
  const studioGenerateBtn = document.getElementById("btn-generate-image");
  const studioGallery = document.getElementById("polaroid-gallery");
  const studioLoader = document.getElementById("studio-loader");

  document.querySelectorAll(".studio-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (studioInput) studioInput.value = prompt;
      generateStudioImage(prompt);
    });
  });

  async function generateStudioImage(promptText) {
    if (!promptText || !promptText.trim()) return;
    studioLoader?.classList.remove("hidden");
    if (studioGenerateBtn) studioGenerateBtn.disabled = true;

    const startMsg = `بيتم رسم صورة أنمي أسطورية عن: "${promptText}" يا حبيبة... ⚡`;
    showNobaraMessage(startMsg);
    speakNobara("نوبارا بتجهز ضربة الجوجوتسو وترسم صورتك دلوقتي يا بيبو!");

    try {
      const res = await fetch("/api/studio/generate-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptText }),
      });
      const data = await res.json();
      if (data.image_url) {
        addPolaroidCard(data.image_url, data.prompt);
        const doneMsg = "شوفي الصورة الأنمي القمر نزلت في معرضنا يا حبيبة! 🌸✨";
        showNobaraMessage(doneMsg);
        speakNobara(doneMsg);
      }
    } catch (e) {
      console.error(e);
    } finally {
      studioLoader?.classList.add("hidden");
      if (studioGenerateBtn) studioGenerateBtn.disabled = false;
    }
  }

  function addPolaroidCard(url, prompt) {
    const card = document.createElement("div");
    card.className = "polaroid-card";
    const colors = ["washi-purple", "washi-blue"];
    const chosenColor = colors[Math.floor(Math.random() * colors.length)];
    card.innerHTML = `
      <div class="washi-tape ${chosenColor}"></div>
      <div class="polaroid-frame">
        <img src="${url}" alt="${prompt}" loading="lazy">
      </div>
      <div class="polaroid-caption">
        <span class="caption-text">${prompt} 🌸</span>
        <span class="caption-date">خاص لدفتر حبيبة ونوبارا</span>
      </div>
    `;
    studioGallery?.prepend(card);
  }

  studioGenerateBtn?.addEventListener("click", () => {
    generateStudioImage(studioInput?.value);
  });

  if (SpeechRecognition) {
    const studioRec = new SpeechRecognition();
    studioRec.lang = "ar-EG";
    studioRec.onresult = (e) => {
      const txt = e.results[0][0].transcript;
      if (studioInput) studioInput.value = txt;
      generateStudioImage(txt);
    };
    studioMicBtn?.addEventListener("click", () => {
      try { studioRec.start(); } catch (e) { studioRec.stop(); }
    });
  }

  // -------------------------------------------------------------------------
  // 10. PWA & Service Worker Registration + One-Click Install Handler
  // -------------------------------------------------------------------------
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.warn("SW error:", err);
    });
  }

  let deferredInstallPrompt = null;
  const btnPwaInstall = document.getElementById("btn-pwa-install");

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    if (btnPwaInstall) btnPwaInstall.style.display = "inline-flex";
  });

  btnPwaInstall?.addEventListener("click", async () => {
    if (deferredInstallPrompt) {
      deferredInstallPrompt.prompt();
      const { outcome } = await deferredInstallPrompt.userChoice;
      if (outcome === "accepted") {
        if (btnPwaInstall) btnPwaInstall.style.display = "none";
      }
      deferredInstallPrompt = null;
    } else {
      alert("لتثبيت تطبيق نوبارا على شاشة موبايلك:\n1. اضغطي على القائمة (الثلاث نقط ⋮ فوق في المتصفح).\n2. اختاري 'تثبيت التطبيق' أو 'إضافة للشاشة الرئيسية' (Add to Home screen) 📲🌸");
    }
  });
});
