/**
 * Smart Voice-Enabled Anime Notebook (Habiba's Secret Diary & Nobara Bestie Edition)
 * Real-Time Continuous Dictation + Google AI Studio TTS (Egyptian Dialect) + Proactive Calls + Dynamic Smart Table
 */

document.addEventListener("DOMContentLoaded", () => {
  // -------------------------------------------------------------------------
  // 1. Text-To-Speech (Official Google AI Studio TTS Voice Output - Egyptian Dialect)
  // -------------------------------------------------------------------------
  let isNobaraSpeaking = false;
  let currentGoogleAudio = null;

  function speakNobara(text, onEnd, audioUrl = null) {
    if (!text || !text.trim()) {
      if (onEnd) onEnd();
      return;
    }
    try {
      if (currentGoogleAudio) {
        currentGoogleAudio.pause();
        currentGoogleAudio = null;
      }
      isNobaraSpeaking = true;
      const clean = text.replace(/[#*`~_]/g, "").trim();
      const url = audioUrl || `/api/tts?text=${encodeURIComponent(clean)}&voice=Aoede`;
      currentGoogleAudio = new Audio(url);
      // Lively, enthusiastic anime bestie speed (+8%)
      currentGoogleAudio.playbackRate = 1.08;

      const finishHandler = () => {
        currentGoogleAudio = null;
        // Resume mic listening after audio finishes (echo prevention)
        setTimeout(() => { isNobaraSpeaking = false; }, 350);
        if (onEnd) onEnd();
      };

      currentGoogleAudio.onended = finishHandler;
      currentGoogleAudio.onerror = finishHandler;
      currentGoogleAudio.play().catch(e => {
        console.warn("Audio autoplay blocked by browser policy:", e);
        isNobaraSpeaking = false;
        if (onEnd) onEnd();
      });
    } catch (err) {
      console.warn("TTS error:", err);
      isNobaraSpeaking = false;
      if (onEnd) onEnd();
    }
  }

  // -------------------------------------------------------------------------
  // 2. Synthesized Telephone Ringtone (Web Audio API - 100% Reliable & Mobile-Safe)
  // -------------------------------------------------------------------------
  let ringtoneCtx = null;
  let ringtoneInterval = null;

  function playRingtone() {
    stopRingtone();
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      ringtoneCtx = new AudioContext();
    } catch (e) {
      return;
    }

    function ringCycle() {
      if (!ringtoneCtx || ringtoneCtx.state === "closed") return;
      const now = ringtoneCtx.currentTime;

      const osc1 = ringtoneCtx.createOscillator();
      const osc2 = ringtoneCtx.createOscillator();
      const gain = ringtoneCtx.createGain();

      osc1.type = "sine";
      osc2.type = "sine";
      osc1.frequency.setValueAtTime(440, now);
      osc2.frequency.setValueAtTime(480, now);

      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(0.2, now + 0.05);
      gain.gain.setValueAtTime(0.2, now + 0.8);
      gain.gain.linearRampToValueAtTime(0, now + 0.85);

      gain.gain.setValueAtTime(0, now + 1.0);
      gain.gain.linearRampToValueAtTime(0.2, now + 1.05);
      gain.gain.setValueAtTime(0.2, now + 1.8);
      gain.gain.linearRampToValueAtTime(0, now + 1.85);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ringtoneCtx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 2.0);
      osc2.stop(now + 2.0);
    }

    ringCycle();
    ringtoneInterval = setInterval(ringCycle, 3500);
  }

  function stopRingtone() {
    if (ringtoneInterval) {
      clearInterval(ringtoneInterval);
      ringtoneInterval = null;
    }
    if (ringtoneCtx) {
      try { ringtoneCtx.close(); } catch (e) {}
      ringtoneCtx = null;
    }
  }

  // -------------------------------------------------------------------------
  // 3. Multi-Slot Page Navigation (Mobile Bottom Bar + Ribbon Tabs)
  // -------------------------------------------------------------------------
  const ribbonTabs = document.querySelectorAll(".tab-ribbon");
  const bottomNavTabs = document.querySelectorAll(".mobile-bottom-nav .nav-tab");
  const tabContents = document.querySelectorAll(".tab-content");

  function switchTab(targetId) {
    ribbonTabs.forEach((r) => {
      r.classList.toggle("active", r.dataset.tab === targetId);
    });
    bottomNavTabs.forEach((n) => {
      n.classList.toggle("active", n.dataset.tab === targetId);
    });
    tabContents.forEach((sec) => {
      sec.classList.toggle("active", sec.id === targetId);
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  ribbonTabs.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  bottomNavTabs.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  // -------------------------------------------------------------------------
  // 4. Speech De-duplication & Anti-Stutter Filter (Eliminates Android Repeat Bug)
  // -------------------------------------------------------------------------
  function deduplicateSpeech(text) {
    if (!text) return "";
    const words = text.trim().split(/\s+/);
    if (words.length <= 1) return text.trim();
    const result = [];
    let repeatCount = 0;
    let lastWord = "";

    for (let i = 0; i < words.length; i++) {
      const w = words[i];
      if (w.toLowerCase() === lastWord.toLowerCase()) {
        repeatCount++;
        // Allow at most 1 consecutive repeated word (e.g. "الو الو" ok, but not "الو الو الو الو")
        if (repeatCount <= 1) {
          result.push(w);
        }
      } else {
        repeatCount = 0;
        lastWord = w;
        result.push(w);
      }
    }

    let cleaned = result.join(" ");
    // Eliminate repeating multi-word phrases (e.g. "لا هي المفروض ان لا هي المفروض ان")
    for (let phraseLen = 6; phraseLen >= 2; phraseLen--) {
      const phraseWords = cleaned.split(/\s+/);
      if (phraseWords.length < phraseLen * 2) continue;
      for (let j = 0; j <= phraseWords.length - phraseLen * 2; j++) {
        const p1 = phraseWords.slice(j, j + phraseLen).join(" ");
        const p2 = phraseWords.slice(j + phraseLen, j + phraseLen * 2).join(" ");
        if (p1 === p2 && p1.length > 4) {
          phraseWords.splice(j + phraseLen, phraseLen);
          cleaned = phraseWords.join(" ");
          break;
        }
      }
    }
    return cleaned.trim();
  }

  // -------------------------------------------------------------------------
  // 4B. Universal Persistent Voice Recognizer (Single-Pass Safe Accumulator)
  // -------------------------------------------------------------------------
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function createPersistentRecognizer({
    btn,
    onStart,
    onInterim,
    onFinal,
    onStop
  }) {
    if (!SpeechRecognition) return null;
    const rec = new SpeechRecognition();
    rec.lang = "ar-EG";
    rec.continuous = true;
    rec.interimResults = true;

    let isRecording = false;
    let committedHistory = "";
    let restartTimer = null;

    rec.onstart = () => {
      btn?.classList.add("listening", "pulse-red");
      if (onStart) onStart();
    };

    rec.onresult = (e) => {
      // Acoustic Echo Muting: Ignore mic input while phone speaker is playing Nobara's voice
      if (isNobaraSpeaking) return;

      let currentFinal = "";
      let currentInterim = "";
      for (let i = 0; i < e.results.length; ++i) {
        const item = e.results[i];
        if (item.isFinal) {
          currentFinal += item[0].transcript + " ";
        } else {
          currentInterim += item[0].transcript;
        }
      }

      const rawFull = (committedHistory + " " + currentFinal + " " + currentInterim).trim();
      const cleanFull = deduplicateSpeech(rawFull);
      if (onInterim) onInterim(cleanFull, currentInterim, deduplicateSpeech((committedHistory + " " + currentFinal).trim()));
    };

    rec.onend = () => {
      if (isRecording) {
        clearTimeout(restartTimer);
        restartTimer = setTimeout(() => {
          if (isRecording && !isNobaraSpeaking) {
            try { rec.start(); } catch (err) {}
          }
        }, 300);
      } else {
        btn?.classList.remove("listening", "pulse-red");
        const full = deduplicateSpeech(committedHistory.trim());
        if (onFinal) onFinal(full);
      }
    };

    rec.onerror = (e) => {
      console.warn("Recognizer event:", e.error);
      if (isRecording && (e.error === "no-speech" || e.error === "network")) {
        clearTimeout(restartTimer);
        restartTimer = setTimeout(() => {
          if (isRecording && !isNobaraSpeaking) {
            try { rec.start(); } catch (err) {}
          }
        }, 350);
      }
    };

    btn?.addEventListener("click", () => {
      if (!isRecording) {
        isRecording = true;
        committedHistory = "";
        try { rec.start(); } catch (err) {}
      } else {
        isRecording = false;
        clearTimeout(restartTimer);
        try { rec.stop(); } catch (err) {}
        if (onStop) onStop();
      }
    });

    return {
      start: () => { isRecording = true; committedHistory = ""; try { rec.start(); } catch (e) {} },
      stop: () => { isRecording = false; clearTimeout(restartTimer); try { rec.stop(); } catch (e) {} },
      isRecording: () => isRecording
    };
  }

  // -------------------------------------------------------------------------
  // 5. Nobara Companion Bubble & Header Call Triggers
  // -------------------------------------------------------------------------
  const assistantBubble = document.getElementById("assistant-bubble");
  const ambientStatusText = document.getElementById("ambient-status-text");
  const btnToggleAmbient = document.getElementById("btn-toggle-ambient");
  const ambientToggleLabel = document.getElementById("ambient-toggle-label");
  const btnHeaderCall = document.getElementById("btn-header-call");
  const btnSlotStartCall = document.getElementById("btn-slot-start-call");

  function showNobaraMessage(msg, speakIt = false, audioUrl = null) {
    if (assistantBubble) {
      assistantBubble.innerText = msg;
      assistantBubble.classList.add("pulse-aura");
      setTimeout(() => assistantBubble.classList.remove("pulse-aura"), 1200);
    }
    if (speakIt) {
      speakNobara(msg, null, audioUrl);
    }
  }

  let isAmbientActive = true;
  btnToggleAmbient?.addEventListener("click", () => {
    isAmbientActive = !isAmbientActive;
    if (isAmbientActive) {
      btnToggleAmbient.classList.add("active");
      if (ambientToggleLabel) ambientToggleLabel.innerText = "نوبارا شغالة 🟢";
      showNobaraMessage("أنا رجعت معاكي يا حبيبة قلبي وسامعاكي في أي وقت! 🌸💖", true);
    } else {
      btnToggleAmbient.classList.remove("active");
      if (ambientToggleLabel) ambientToggleLabel.innerText = "نوبارا نايمة ⚪";
      showNobaraMessage("ارتاحي شوية يا قمر وأنا هفضل في انتظارك لما تناديني.. 💤", false);
    }
  });

  // -------------------------------------------------------------------------
  // 6. Ambient Care Chips & Test Proactive Calling
  // -------------------------------------------------------------------------
  const careChips = document.querySelectorAll(".ambient-care-chips .care-chip[data-intent]");
  const btnTestLessonCall = document.getElementById("btn-test-lesson-call");
  const btnTestSleepCall = document.getElementById("btn-test-sleep-call");

  careChips.forEach(chip => {
    chip.addEventListener("click", async () => {
      const intent = chip.dataset.intent;
      try {
        const res = await fetch("/api/bestie/ambient-assist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ intent: intent })
        });
        const data = await res.json();
        if (data.reply) {
          showNobaraMessage(data.reply, true, data.audio_url);
        }
      } catch (e) {
        showNobaraMessage("معاكي وسامعاكي يا بيبو يا قمر! 🌸", true);
      }
    });
  });

  btnTestLessonCall?.addEventListener("click", async () => {
    triggerProactiveIncomingCall("lesson");
  });

  btnTestSleepCall?.addEventListener("click", async () => {
    triggerProactiveIncomingCall("sleep");
  });

  // Ambient Mic with Persistent Continuous Recognizer
  const btnAmbientMic = document.getElementById("btn-ambient-mic");
  createPersistentRecognizer({
    btn: btnAmbientMic,
    onStart: () => {
      btnAmbientMic?.classList.add("speaking");
      if (ambientStatusText) ambientStatusText.innerText = "🔴 نوبارا سامعاكي يا روحي.. اتكلمي براحتك واضغطي إيقاف لما تخلصي ⏹️";
    },
    onInterim: (full) => {
      if (assistantBubble) assistantBubble.innerText = "سامعاكي: " + full;
    },
    onFinal: async (full) => {
      btnAmbientMic?.classList.remove("speaking");
      if (!full) return;
      if (ambientStatusText) ambientStatusText.innerText = "نوبارا بتفكر وبترد عليكي... 💖";
      try {
        const res = await fetch("/api/bestie/ambient-assist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ intent: "chat", user_message: full })
        });
        const data = await res.json();
        showNobaraMessage(data.reply, true, data.audio_url);
      } catch (err) {
        showNobaraMessage("يا روحي أنا معاكي وسامعة كل كلامك الحلو ده! 🌸", true);
      }
    }
  });

  // -------------------------------------------------------------------------
  // 6B. Hands-Free Omni Listening Mode (Open & Just Talk - Zero Buttons Needed!)
  // -------------------------------------------------------------------------
  let isHandsFreeActive = true;
  let omniRecognizer = null;
  let omniSilenceTimer = null;
  let currentSpokenBuffer = "";

  function initHandsFreeOmniMode() {
    if (!SpeechRecognition) return;
    try {
      omniRecognizer = new SpeechRecognition();
      omniRecognizer.lang = "ar-EG";
      omniRecognizer.continuous = true;
      omniRecognizer.interimResults = true;

      omniRecognizer.onresult = (e) => {
        // Echo cancellation: Don't listen to Nobara's own voice
        if (isNobaraSpeaking || isCallActive) return;

        let liveText = "";
        for (let i = 0; i < e.results.length; ++i) {
          liveText += e.results[i][0].transcript + " ";
        }
        liveText = deduplicateSpeech(liveText);
        if (!liveText || liveText.length < 2) return;

        currentSpokenBuffer = liveText;
        if (assistantBubble) {
          assistantBubble.innerText = "سامعاكي: " + currentSpokenBuffer;
        }

        clearTimeout(omniSilenceTimer);
        omniSilenceTimer = setTimeout(async () => {
          if (!currentSpokenBuffer || currentSpokenBuffer.length < 3) return;
          const phrase = currentSpokenBuffer;
          currentSpokenBuffer = "";

          if (ambientStatusText) {
            ambientStatusText.innerText = "نوبارا بتنفذ طلبك وبترد عليكي... 💖⚡";
          }

          try {
            const res = await fetch("/api/bestie/omni-listen", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ raw_speech: phrase })
            });
            const d = await res.json();

            // 1. If Intent is DIARY -> write into diary and switch to diary tab
            if (d.intent === "diary" && d.diary_entry) {
              if (diaryTextarea) {
                const prev = diaryTextarea.value.trim();
                diaryTextarea.value = (prev ? prev + "\n\n" : "") + d.diary_entry;
                localStorage.setItem("habiba_secret_diary", diaryTextarea.value);
              }
              switchTab("diary-tab");
            }
            // 2. If Intent is TABLE -> add row to table and switch to table tab
            else if (d.intent === "table" && d.table_row && d.table_row.length > 0) {
              if (tableBody) {
                const tr = document.createElement("tr");
                let tds = "";
                for (let idx = 0; idx < tableHeaders.length; idx++) {
                  const val = d.table_row[idx] || "-";
                  tds += `<td contenteditable="true">${val}</td>`;
                }
                tds += `<td><button class="btn-del-row" title="حذف">🗑️</button></td>`;
                tr.innerHTML = tds;
                tableBody.appendChild(tr);
                bindTableEvents();
                saveTableToStorage();
              }
              switchTab("table-tab");
            }
            // 3. If Intent is STUDIO -> trigger image generation and switch to studio tab
            else if (d.intent === "studio" && d.studio_prompt) {
              switchTab("studio-tab");
              generateStudioImage(d.studio_prompt);
            }

            // Speak Nobara's warm Google Aoede reply
            showNobaraMessage(d.reply, true, d.audio_url);
            if (ambientStatusText) {
              ambientStatusText.innerText = "🟢 نوبارا سامعاكي دايماً.. قولي اللي تحبيه في أي وقت ✨";
            }
          } catch (e) {
            showNobaraMessage("يا روحي أنا معاكي وسامعة كل كلامك الحلو ده! 🌸", true);
          }
        }, 1300);
      };

      omniRecognizer.onend = () => {
        if (isHandsFreeActive && !isNobaraSpeaking && !isCallActive) {
          setTimeout(() => {
            try { omniRecognizer.start(); } catch (err) {}
          }, 350);
        }
      };

      omniRecognizer.onerror = (e) => {
        if (isHandsFreeActive && (e.error === "no-speech" || e.error === "network")) {
          setTimeout(() => {
            try { omniRecognizer.start(); } catch (err) {}
          }, 450);
        }
      };

      // Browser policy: start microphone on first tap/interaction anywhere on page
      const armHandsFree = () => {
        if (isHandsFreeActive) {
          try { omniRecognizer.start(); } catch (e) {}
        }
        document.removeEventListener("click", armHandsFree);
        document.removeEventListener("touchstart", armHandsFree);
      };
      document.addEventListener("click", armHandsFree, { once: true });
      document.addEventListener("touchstart", armHandsFree, { once: true });
    } catch (e) {
      console.warn("Hands-free init:", e);
    }
  }

  initHandsFreeOmniMode();

  // -------------------------------------------------------------------------
  // 7. Simulated Phone Call System (Incoming + Active Voice Call)
  // -------------------------------------------------------------------------
  const incomingCallModal = document.getElementById("incoming-call-modal");
  const activeCallModal = document.getElementById("active-call-modal");
  const btnAcceptCall = document.getElementById("btn-accept-call");
  const btnDeclineCall = document.getElementById("btn-decline-call");
  const btnEndCall = document.getElementById("btn-end-call");
  const btnCallMicToggle = document.getElementById("btn-call-mic-toggle");
  const nobaraLiveReply = document.getElementById("nobara-live-reply");
  const userCallLiveText = document.getElementById("user-call-live-text");
  const callTimer = document.getElementById("call-timer");
  const callerSubtitle = document.querySelector(".caller-subtitle");

  let isCallActive = false;
  let callStartTime = 0;
  let callTimerInterval = null;
  let activeCallProactiveMessage = "";
  let preloadedCallAudio = null;
  let preloadedCallText = "";

  function prepareCallAudio(text, audioUrl = null) {
    if (!text) return;
    preloadedCallText = text;
    const clean = text.replace(/[#*`~_]/g, "").trim();
    const url = audioUrl || `/api/tts?text=${encodeURIComponent(clean)}&voice=Aoede`;
    try {
      preloadedCallAudio = new Audio(url);
      preloadedCallAudio.playbackRate = 1.08;
      preloadedCallAudio.preload = "auto";
      preloadedCallAudio.load();
    } catch (e) {
      console.warn("Failed to preload audio:", e);
    }
  }

  async function triggerProactiveIncomingCall(forceType = null) {
    try {
      const res = await fetch("/api/proactive/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_type: forceType })
      });
      const data = await res.json();
      if (data.should_call) {
        activeCallProactiveMessage = data.message;
        if (callerSubtitle) callerSubtitle.innerText = data.message.slice(0, 40) + "... 💖";
        // Pre-warm audio instantly while phone rings so answer is 0ms delay!
        prepareCallAudio(data.message, data.audio_url);
        incomingCallModal?.classList.remove("hidden");
        playRingtone();
      }
    } catch (e) {
      console.warn("Proactive check error:", e);
    }
  }

  // Periodic Heartbeat check every 25 seconds for autonomous call reminders
  setInterval(() => {
    if (!isCallActive && incomingCallModal?.classList.contains("hidden")) {
      triggerProactiveIncomingCall();
    }
  }, 25000);

  function startIncomingCallRing() {
    activeCallProactiveMessage = "";
    incomingCallModal?.classList.remove("hidden");
    playRingtone();

    // Fetch and preload opener IMMEDIATELY while ringing!
    fetch("/api/bestie/call-opener", { method: "POST" })
      .then(r => r.json())
      .then(d => {
        if (d.opener) {
          prepareCallAudio(d.opener, d.audio_url);
        }
      })
      .catch(() => {
        const fallbackText = "ألوو يا حبيبة يا قلبي! سامعاكي يا روحي احكيلي كل حاجة 💖";
        prepareCallAudio(fallbackText);
      });
  }

  btnHeaderCall?.addEventListener("click", startIncomingCallRing);
  btnSlotStartCall?.addEventListener("click", startIncomingCallRing);

  btnDeclineCall?.addEventListener("click", () => {
    stopRingtone();
    incomingCallModal?.classList.add("hidden");
    preloadedCallAudio = null;
  });

  btnAcceptCall?.addEventListener("click", () => {
    stopRingtone();
    incomingCallModal?.classList.add("hidden");
    openActiveCall();
  });

  btnEndCall?.addEventListener("click", () => {
    endActiveCall();
  });

  function openActiveCall() {
    isCallActive = true;
    activeCallModal?.classList.remove("hidden");
    callStartTime = Date.now();
    callTimerInterval = setInterval(updateCallTimer, 1000);

    const callGreeting = activeCallProactiveMessage || preloadedCallText || "ألوو يا حبيبة يا قلبي! سامعاكي يا روحي احكيلي كل حاجة 💖";
    if (nobaraLiveReply) nobaraLiveReply.innerText = callGreeting;

    // INSTANT PLAYBACK: If audio was pre-buffered during ringing, play it immediately inside click gesture!
    if (preloadedCallAudio) {
      if (currentGoogleAudio) {
        currentGoogleAudio.pause();
        currentGoogleAudio = null;
      }
      currentGoogleAudio = preloadedCallAudio;
      currentGoogleAudio.playbackRate = 1.08;
      preloadedCallAudio = null;
      currentGoogleAudio.onended = () => {
        currentGoogleAudio = null;
        if (isCallActive) startCallSpeechRecognition();
      };
      currentGoogleAudio.onerror = () => {
        currentGoogleAudio = null;
        if (isCallActive) startCallSpeechRecognition();
      };
      currentGoogleAudio.play().catch(e => {
        console.warn("Direct preloaded audio play catch:", e);
        if (isCallActive) startCallSpeechRecognition();
      });
    } else {
      speakNobara(callGreeting, () => {
        if (isCallActive) startCallSpeechRecognition();
      });
    }
  }

  function endActiveCall() {
    isCallActive = false;
    clearInterval(callTimerInterval);
    callTimerInterval = null;
    activeCallModal?.classList.add("hidden");
    if (currentGoogleAudio) {
      currentGoogleAudio.pause();
      currentGoogleAudio = null;
    }
  }

  function updateCallTimer() {
    const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const s = String(elapsed % 60).padStart(2, "0");
    if (callTimer) callTimer.innerText = `${m}:${s}`;
  }

  function startCallSpeechRecognition() {
    if (!SpeechRecognition || !isCallActive) return;
    const callRec = new SpeechRecognition();
    callRec.lang = "ar-EG";
    callRec.continuous = true;
    callRec.interimResults = true;

    btnCallMicToggle?.classList.add("speaking");

    callRec.onresult = (e) => {
      let interim = "";
      let finalTxt = "";
      for (let i = e.resultIndex; i < e.results.length; ++i) {
        if (e.results[i].isFinal) finalTxt += e.results[i][0].transcript + " ";
        else interim += e.results[i][0].transcript;
      }
      const full = (finalTxt + " " + interim).trim();
      if (userCallLiveText) userCallLiveText.innerText = full;

      if (finalTxt.trim().length > 3) {
        callRec.stop();
        sendUserCallMessage(finalTxt.trim());
      }
    };

    callRec.onend = () => {
      if (isCallActive && !currentGoogleAudio) {
        try { callRec.start(); } catch (err) {}
      }
    };

    try { callRec.start(); } catch (e) {}
  }

  async function sendUserCallMessage(msg) {
    if (!isCallActive) return;
    try {
      const res = await fetch("/api/bestie/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_message: msg })
      });
      const d = await res.json();
      if (nobaraLiveReply) nobaraLiveReply.innerText = d.reply;
      speakNobara(d.reply, () => {
        if (isCallActive) startCallSpeechRecognition();
      }, d.audio_url);
    } catch (e) {
      if (nobaraLiveReply) nobaraLiveReply.innerText = "يا روحي معاكي وسامعة كل كلامك العسل ده! 🌸";
      speakNobara("يا روحي معاكي وسامعة كل كلامك العسل ده!", () => {
        if (isCallActive) startCallSpeechRecognition();
      });
    }
  }

  // -------------------------------------------------------------------------
  // 8. TAB 1: SMART DIARY (Continuous Voice Dictation + AI Correction)
  // -------------------------------------------------------------------------
  const diaryTextarea = document.getElementById("diary-textarea");
  const diaryMicBtn = document.getElementById("btn-diary-mic");
  const diaryVoiceStatus = document.getElementById("diary-voice-status");
  const diaryLiveBar = document.getElementById("diary-live-stream-bar");
  const diaryLiveWords = document.getElementById("diary-live-words");
  const saveDiaryBtn = document.getElementById("btn-save-diary");
  const clearDiaryBtn = document.getElementById("btn-clear-diary");

  const savedDiary = localStorage.getItem("habiba_secret_diary");
  if (savedDiary && diaryTextarea) diaryTextarea.value = savedDiary;

  saveDiaryBtn?.addEventListener("click", () => {
    localStorage.setItem("habiba_secret_diary", diaryTextarea.value);
    showNobaraMessage("حفظت كل مذكراتك وأسرارك في الدفتر بأمان يا حبيبة! 🌸💖", true);
  });

  clearDiaryBtn?.addEventListener("click", () => {
    if (confirm("عايزة تمسحي صفحة المذكرات وتبدأي صفحة بيضاء جديدة؟")) {
      diaryTextarea.value = "";
      localStorage.removeItem("habiba_secret_diary");
      showNobaraMessage("عملتلك صفحة بيضاء جديدة وجميلة.. اكتبي اللي تحبيه! ✨", false);
    }
  });

  let diaryBaseText = "";
  createPersistentRecognizer({
    btn: diaryMicBtn,
    onStart: () => {
      diaryBaseText = diaryTextarea ? diaryTextarea.value.trim() : "";
      diaryLiveBar?.classList.remove("hidden");
      if (diaryLiveWords) diaryLiveWords.innerText = "أنا سامعاكي يا بيبو.. احكي براحتك ومش هيقفل إلا لما تضغطي إيقاف ⏹️";
      if (diaryVoiceStatus) diaryVoiceStatus.innerText = "🔴 التسجيل مفتوح وشغال.. احكي يومياتك كلها وسامعاكي كلمة بكلمة";
    },
    onInterim: (full) => {
      if (diaryLiveWords) diaryLiveWords.innerText = full;
      if (diaryTextarea) {
        const prefix = diaryBaseText ? diaryBaseText + "\n\n" : "";
        diaryTextarea.value = prefix + full;
        diaryTextarea.scrollTop = diaryTextarea.scrollHeight;
      }
    },
    onFinal: async (full) => {
      diaryLiveBar?.classList.add("hidden");
      if (!full || full.startsWith("أنا سامعاكي")) {
        if (diaryVoiceStatus) diaryVoiceStatus.innerText = "اضغطي المايك واحكي.. نوبارا جنبك وسامعاكي! 🌸";
        return;
      }
      if (diaryVoiceStatus) diaryVoiceStatus.innerText = "نوبارا بتظبط مذكراتك بالعامية المصرية الرقيقة وبترد عليكي... ⚡";
      try {
        const res = await fetch("/api/diary/correct-arabic", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_text: full })
        });
        const data = await res.json();
        const prefix = diaryBaseText ? diaryBaseText + "\n\n" : "";
        if (diaryTextarea) {
          diaryTextarea.value = prefix + (data.corrected_text || full);
          localStorage.setItem("habiba_secret_diary", diaryTextarea.value);
        }
        if (diaryVoiceStatus) diaryVoiceStatus.innerText = "تم حفظ وترتيب مذكراتك بنجاح! 🌸";
        showNobaraMessage(data.sensei_reply, true, data.audio_url);
      } catch (err) {
        if (diaryVoiceStatus) diaryVoiceStatus.innerText = "تم تسجيل مذكراتك بحب 🌸";
        showNobaraMessage("سجلت كل كلمة قولتيها يا حبيبة قلبي! 💖", true);
      }
    }
  });

  // Background Scene Mic with Persistent Recognizer
  const bgMicBtn = document.getElementById("btn-bg-mic");
  const bgInput = document.getElementById("bg-scene-input");
  const generateBgBtn = document.getElementById("btn-generate-bg");
  const diaryBgOverlay = document.getElementById("diary-bg-overlay");
  const bgDrawer = document.getElementById("bg-drawer");
  const btnToggleBgDrawer = document.getElementById("btn-toggle-bg-drawer");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");

  btnToggleBgDrawer?.addEventListener("click", () => bgDrawer?.classList.toggle("hidden"));
  btnCloseDrawer?.addEventListener("click", () => bgDrawer?.classList.add("hidden"));

  createPersistentRecognizer({
    btn: bgMicBtn,
    onStart: () => {
      if (bgInput) bgInput.placeholder = "🔴 سامعاكي.. قولي وصف الخلفية واضغطي إيقاف لما تخلصي ⏹️";
    },
    onInterim: (full) => {
      if (bgInput) bgInput.value = full;
    },
    onFinal: (full) => {
      if (full) triggerBgGeneration(full);
    }
  });

  generateBgBtn?.addEventListener("click", () => {
    triggerBgGeneration(bgInput?.value);
  });

  function triggerBgGeneration(prompt) {
    if (!prompt) return;
    showNobaraMessage("برسم لكِ خلفية أنمي قمر زي ما طلبتي... 🎨", false);
    fetch("/api/diary/generate-background", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scene_description: prompt })
    })
      .then(r => r.json())
      .then(d => {
        if (diaryBgOverlay && d.image_url) {
          diaryBgOverlay.style.backgroundImage = `url('${d.image_url}')`;
          diaryBgOverlay.classList.add("has-bg");
          showNobaraMessage("الخلفية جهزت وبقت سحرية في دفترك يا بيبو! 🌸✨", true);
        }
      })
      .catch(() => {
        showNobaraMessage("حبيبة يا قمر، هحاول أرسمها تاني بعد شوية! 🌸", false);
      });
  }

  // -------------------------------------------------------------------------
  // 9. TAB 2: SMART VOICE TABLE (Dynamic Columns + Continuous Dictation)
  // -------------------------------------------------------------------------
  const missionsTable = document.getElementById("missions-table");
  const tableBody = document.getElementById("table-body");
  const btnTableSetupMic = document.getElementById("btn-table-setup-mic");
  const btnTableContinuousMic = document.getElementById("btn-table-continuous-mic");
  const tableSetupStatus = document.getElementById("table-setup-status");
  const tableContinuousStatus = document.getElementById("table-continuous-status");
  const tableLiveBar = document.getElementById("table-live-stream-bar");
  const tableLiveWords = document.getElementById("table-live-words");
  const btnAddManualRow = document.getElementById("btn-add-manual-row");
  const btnClearTable = document.getElementById("btn-clear-table");

  let tableHeaders = ["المهمة / الدرس 🎯", "الميعاد ⏰", "اليوم 📅", "المكان 📍", "الملاحظات 📝"];
  const savedHeaders = localStorage.getItem("habiba_table_headers");
  if (savedHeaders) {
    try {
      tableHeaders = JSON.parse(savedHeaders);
      renderTableHeaders();
    } catch (e) {}
  }

  const savedRows = localStorage.getItem("habiba_table_rows");
  if (savedRows && tableBody) {
    tableBody.innerHTML = savedRows;
    bindTableEvents();
  }

  function renderTableHeaders() {
    if (!missionsTable) return;
    const thead = missionsTable.querySelector("thead");
    if (!thead) return;
    let ths = "";
    tableHeaders.forEach(h => {
      ths += `<th>${h}</th>`;
    });
    ths += `<th class="col-actions">حذف</th>`;
    thead.innerHTML = `<tr>${ths}</tr>`;
  }

  function saveTableToStorage() {
    if (tableBody) localStorage.setItem("habiba_table_rows", tableBody.innerHTML);
    localStorage.setItem("habiba_table_headers", JSON.stringify(tableHeaders));
  }

  function bindTableEvents() {
    if (!tableBody) return;
    tableBody.querySelectorAll(".btn-del-row").forEach(btn => {
      btn.onclick = () => {
        btn.closest("tr")?.remove();
        saveTableToStorage();
      };
    });
    tableBody.querySelectorAll("td[contenteditable='true']").forEach(td => {
      td.onblur = () => saveTableToStorage();
    });
  }

  // Mic 1: Setup Column Headers with Continuous Persistent Recognizer
  createPersistentRecognizer({
    btn: btnTableSetupMic,
    onStart: () => {
      tableLiveBar?.classList.remove("hidden");
      if (tableLiveWords) tableLiveWords.innerText = "سامعاكي.. قولي مثلاً: 1 اليوم، 2 المادة، 3 ميعاد الدرس، 4 المكان...";
      if (tableSetupStatus) tableSetupStatus.innerText = "🔴 التسجيل مفتوح.. حددي الأعمدة واضغطي إيقاف لما تخلصي ⏹️";
    },
    onInterim: (full) => {
      if (tableLiveWords) tableLiveWords.innerText = full;
    },
    onFinal: async (full) => {
      tableLiveBar?.classList.add("hidden");
      if (!full || full.startsWith("سامعاكي")) {
        if (tableSetupStatus) tableSetupStatus.innerText = "اضغطي لتحديد الخانات";
        return;
      }
      if (tableSetupStatus) tableSetupStatus.innerText = "نوبارا بترتب أعمدة جدولك... ⏳";
      try {
        const res = await fetch("/api/table/setup-headers", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_speech: full })
        });
        const d = await res.json();
        if (d.headers && d.headers.length >= 2) {
          tableHeaders = d.headers;
          renderTableHeaders();
          saveTableToStorage();
          if (tableSetupStatus) tableSetupStatus.innerText = `تم تجهيز ${d.headers.length} خانات بنجاح! 🌸`;
          showNobaraMessage(d.reply, true, d.audio_url);
        }
      } catch (err) {
        if (tableSetupStatus) tableSetupStatus.innerText = "اضغطي وجربي تاني يا بيبو 🌸";
      }
    }
  });

  // Mic 2: Continuous Open Live Dictation into Table Rows
  createPersistentRecognizer({
    btn: btnTableContinuousMic,
    onStart: () => {
      tableLiveBar?.classList.remove("hidden");
      if (tableLiveWords) tableLiveWords.innerText = "🔴 نوبارا سامعاكي ومفتوحة علطول.. املي بياناتك كلمة بكلمة ومش هيقفل إلا لما تضغطي إيقاف ⏹️";
      if (tableContinuousStatus) tableContinuousStatus.innerText = "🔴 التفريغ المفتوح شغال.. احكي كل تفاصيلك وسامعاكي كلمة بكلمة";
    },
    onInterim: (full) => {
      if (tableLiveWords) tableLiveWords.innerText = full;
    },
    onFinal: async (full) => {
      tableLiveBar?.classList.add("hidden");
      if (!full || full.startsWith("🔴 نوبارا سامعاكي")) {
        if (tableContinuousStatus) tableContinuousStatus.innerText = "جاهز للتفريغ المستمر..";
        return;
      }
      if (tableContinuousStatus) tableContinuousStatus.innerText = "نوبارا بتفرغ البيانات في الخانات المناسبة... ⚡";
      try {
        const res = await fetch("/api/table/fill-rows", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_speech: full, headers: tableHeaders })
        });
        const d = await res.json();
        if (d.rows && d.rows.length > 0) {
          d.rows.forEach(r => {
            const tr = document.createElement("tr");
            let tds = "";
            for (let idx = 0; idx < tableHeaders.length; idx++) {
              const val = r[idx] || "-";
              tds += `<td contenteditable="true">${val}</td>`;
            }
            tds += `<td><button class="btn-del-row" title="حذف">🗑️</button></td>`;
            tr.innerHTML = tds;
            tableBody?.appendChild(tr);
          });
          bindTableEvents();
          saveTableToStorage();
          if (tableContinuousStatus) tableContinuousStatus.innerText = "تم تفريغ البيانات في الجدول بنجاح! ⚡";
          showNobaraMessage(d.reply, true, d.audio_url);
        }
      } catch (err) {
        if (tableContinuousStatus) tableContinuousStatus.innerText = "اضغطي المايك للتفريغ تاني يا روحي 🌸";
      }
    }
  });

  btnAddManualRow?.addEventListener("click", () => {
    if (!tableBody) return;
    const tr = document.createElement("tr");
    let tds = "";
    for (let idx = 0; idx < tableHeaders.length; idx++) {
      tds += `<td contenteditable="true">جديد</td>`;
    }
    tds += `<td><button class="btn-del-row" title="حذف">🗑️</button></td>`;
    tr.innerHTML = tds;
    tableBody.appendChild(tr);
    bindTableEvents();
    saveTableToStorage();
  });

  btnClearTable?.addEventListener("click", () => {
    if (confirm("عايزة تمسحي كل البيانات اللي في الجدول وتبدأي من الأول؟")) {
      if (tableBody) tableBody.innerHTML = "";
      localStorage.removeItem("habiba_table_rows");
      showNobaraMessage("مسحت الجدول وبقى جاهز لمغامراتك الجديدة يا قمر! 🌸", false);
    }
  });

  // -------------------------------------------------------------------------
  // 10. TAB 3: MAGIC ANIME STUDIO (Persistent Voice Prompt + Polaroid)
  // -------------------------------------------------------------------------
  const studioInput = document.getElementById("studio-prompt-input");
  const studioMicBtn = document.getElementById("btn-studio-mic");
  const studioGenerateBtn = document.getElementById("btn-generate-image");
  const polaroidGallery = document.getElementById("polaroid-gallery");
  const studioLoader = document.getElementById("studio-loader");

  createPersistentRecognizer({
    btn: studioMicBtn,
    onStart: () => {
      if (studioInput) studioInput.placeholder = "🔴 سامعاكي.. وصفي صورتك براحتك واضغطي إيقاف لما تخلصي ⏹️";
    },
    onInterim: (full) => {
      if (studioInput) studioInput.value = full;
    },
    onFinal: (full) => {
      if (full) generateStudioImage(full);
    }
  });

  studioGenerateBtn?.addEventListener("click", () => {
    generateStudioImage(studioInput?.value);
  });

  function generateStudioImage(prompt) {
    if (!prompt) return;
    studioLoader?.classList.remove("hidden");
    showNobaraMessage("برسم الصورة السحرية في استوديو الأنمي... 🎨⚡", false);

    fetch("/api/studio/generate-image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt })
    })
      .then(r => r.json())
      .then(d => {
        studioLoader?.classList.add("hidden");
        if (d.image_url && polaroidGallery) {
          const card = document.createElement("div");
          card.className = "polaroid-card";
          card.innerHTML = `
            <div class="washi-tape washi-purple"></div>
            <div class="polaroid-frame">
              <img src="${d.image_url}" alt="${d.prompt}" loading="lazy">
            </div>
            <div class="polaroid-caption">
              <span class="caption-text">${d.caption || d.prompt}</span>
              <span class="caption-date">خاص لدفتر حبيبة 🌸</span>
            </div>
          `;
          polaroidGallery.prepend(card);
          showNobaraMessage("الصورة جهزت ونزلت في ألبومك يا حبيبة قلبي! 💖✨", true);
        }
      })
      .catch(() => {
        studioLoader?.classList.add("hidden");
        showNobaraMessage("حبيبة يا روحي، هنجرب نرسمها تاني بعد ثواني! 🌸", false);
      });
  }

  // -------------------------------------------------------------------------
  // 11. PWA & Service Worker Registration
  // -------------------------------------------------------------------------
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(e => console.warn("SW error:", e));
  }

  let deferredPrompt = null;
  const btnPwaInstall = document.getElementById("btn-pwa-install");
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (btnPwaInstall) btnPwaInstall.style.display = "inline-flex";
  });

  btnPwaInstall?.addEventListener("click", async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      if (choice.outcome === "accepted") {
        if (btnPwaInstall) btnPwaInstall.style.display = "none";
      }
      deferredPrompt = null;
    } else {
      alert("لتثبيت التطبيق على الموبايل:\nاضغطي على زر المشاركة (Share) في المتصفح، ثم اختاري (إضافة إلى الشاشة الرئيسية / Add to Home Screen) 📲✨");
    }
  });

  // Welcome greeting
  setTimeout(() => {
    speakNobara("أهلاً يا حبيبة قلبي! أنا نوبارا صاحبتك الأنتيم، وحشتيني أوي.. مستنياكي نحكي ونرتب يومك سوا!");
  }, 1000);
});
