// Main Frontend Controller & WebSocket Client for JARVIS
document.addEventListener('DOMContentLoaded', () => {
  const terminalFeed = document.getElementById('terminal-feed');
  const commandForm = document.getElementById('command-form');
  const commandInput = document.getElementById('command-input');
  const btnMic = document.getElementById('btn-mic');
  const btnHardwareMic = document.getElementById('btn-hardware-mic');
  const btnClearLog = document.getElementById('btn-clear-log');
  const statusText = document.getElementById('status-text');
  const authStatusBadge = document.getElementById('auth-status-badge');
  const continuousModeBadge = document.getElementById('continuous-mode-badge');
  const btnToggleContinuous = document.getElementById('btn-toggle-continuous');
  const audioPlayer = document.getElementById('audio-player');
  const authActionLabel = document.getElementById('auth-action-label');
  const authIcon = document.getElementById('auth-icon');

  // Passcode Modal Elements
  const btnOpenPasscodeModal = document.getElementById('btn-open-passcode-modal');
  const passcodeModal = document.getElementById('passcode-modal');
  const modalPasscodeInput = document.getElementById('modal-passcode-input');
  const btnSavePasscode = document.getElementById('btn-save-passcode');
  const btnCancelPasscode = document.getElementById('btn-cancel-passcode');

  // Email Password Modal Elements
  const btnOpenEmailModal = document.getElementById('btn-open-email-modal');
  const emailModal = document.getElementById('email-modal');
  const modalEmailPasswordInput = document.getElementById('modal-email-password-input');
  const btnSaveEmail = document.getElementById('btn-save-email');
  const btnCancelEmail = document.getElementById('btn-cancel-email');

  // WebSocket Connection
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
  let socket = null;

  // Audio, Voice & 2-Way Conversational State
  let isListening = false;
  let isHardwareListening = false;
  let isContinuousMode = false;
  let mediaStream = null;
  let mediaRecorder = null;
  let recordedChunks = [];
  let audioContext = null;
  let recognition = null;
  let transcriptReceived = '';
  let silenceTimer = null;
  let fallbackAudioTimer = null;
  let lastVoiceText = '';

  // Setup Web Speech Recognition
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    try {
      recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const text = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            transcriptReceived = text;
          } else {
            interim += text;
          }
        }

        const activeText = (transcriptReceived || interim).trim();
        if (activeText) {
          commandInput.value = activeText;
          statusText.innerText = `HEARING: "${activeText.toUpperCase()}"`;

          // Automatic Silence Detector (VAD): commit after 1.4s of quiet
          clearTimeout(silenceTimer);
          silenceTimer = setTimeout(() => {
            if (isListening && commandInput.value.trim()) {
              stopListening(true);
            }
          }, 1400);
        }
      };

      recognition.onerror = (event) => {
        console.warn('Web Speech error:', event.error);
        if (event.error === 'not-allowed') {
          appendLog('SYSTEM', '⚠️ Microphone permission was not allowed in browser. Click the lock/settings icon in your URL bar to allow.');
        }
      };

      recognition.onend = () => {
        // If still flagged as listening in continuous mode, restart recognition
        if (isListening && isContinuousMode) {
          try { recognition.start(); } catch (e) {}
        }
      };
    } catch (e) {
      console.warn('SpeechRecognition init error:', e);
      recognition = null;
    }
  }

  // --- Continuous 2-Way Mode Toggle ---
  function toggleContinuousMode() {
    isContinuousMode = !isContinuousMode;
    if (isContinuousMode) {
      continuousModeBadge.innerText = 'ACTIVE 2-WAY';
      continuousModeBadge.classList.add('unlocked');
      continuousModeBadge.style.color = '#10b981';
      continuousModeBadge.style.borderColor = '#10b981';
      appendLog('SYSTEM', '🎙️ 2-Way Hands-Free Voice Mode ACTIVE. Speak freely—JARVIS will respond and listen automatically!');
      if (!isListening) {
        startListening();
      }
    } else {
      continuousModeBadge.innerText = 'IDLE';
      continuousModeBadge.classList.remove('unlocked');
      continuousModeBadge.style.color = 'var(--neon-cyan)';
      continuousModeBadge.style.borderColor = 'var(--border-cyan)';
      appendLog('SYSTEM', '2-Way Hands-Free Mode paused.');
      if (isListening) {
        stopListening(false);
      }
    }
  }

  if (btnToggleContinuous) {
    btnToggleContinuous.addEventListener('click', toggleContinuousMode);
  }

  // --- Browser Voice Recording & Processing ---
  async function startListening() {
    if (isListening || isHardwareListening) return;
    transcriptReceived = '';
    recordedChunks = [];
    clearTimeout(silenceTimer);

    try {
      // 1. Request microphone access
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // 2. Connect AudioContext for real-time visualizer
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        audioContext = new AudioCtx();
        const source = audioContext.createMediaStreamSource(mediaStream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 128;
        source.connect(analyser);
        if (window.visualizer) {
          window.visualizer.connectAudioSource(analyser);
        }
      } catch (err) {
        console.warn('AudioContext visualization setup warning:', err);
      }

      // 3. Setup MediaRecorder for backend audio fallback
      let mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      }

      try {
        mediaRecorder = new MediaRecorder(mediaStream, { mimeType });
      } catch (e) {
        mediaRecorder = new MediaRecorder(mediaStream);
      }

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          recordedChunks.push(e.data);
        }
      };

      mediaRecorder.start(200);

      // 4. Start Web Speech recognition in parallel
      if (recognition) {
        try {
          recognition.start();
        } catch (e) {
          console.debug('Recognition already running or restarting:', e);
        }
      }

      isListening = true;
      btnMic.classList.add('listening');
      statusText.innerText = isContinuousMode ? '🎙️ 2-WAY: LISTENING (SPEAK NOW)...' : 'LISTENING... (SPEAK COMMAND OR PASSCODE)';
      commandInput.placeholder = isContinuousMode ? '2-Way listening active... Speak naturally!' : 'Listening to your voice... Speak now!';
      if (window.visualizer) window.visualizer.setListening(true);

    } catch (err) {
      console.error('Microphone error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        appendLog('SYSTEM', '⚠️ Microphone permission denied by browser. Please grant permission in your URL bar.');
      } else {
        appendLog('SYSTEM', `⚠️ Microphone error: ${err.message}. Switching to hardware microphone...`);
        triggerHardwareMic();
      }
      stopListening(false);
    }
  }

  async function stopListening(processAudio = true) {
    if (!isListening) return;
    isListening = false;
    clearTimeout(silenceTimer);
    btnMic.classList.remove('listening');
    statusText.innerText = 'PROCESSING TELEMETRY...';
    if (window.visualizer) window.visualizer.setListening(false);

    if (recognition) {
      try { recognition.stop(); } catch (e) {}
    }

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }

    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close().catch(() => {});
    }

    commandInput.placeholder = "Speak or type a command... (e.g., 'omega-protocol-9' to unlock, or 'system status')";

    if (!processAudio) {
      statusText.innerText = 'ONLINE // STANDING BY';
      return;
    }

    // Wait 250ms for final recorder buffer
    await new Promise(r => setTimeout(r, 250));

    const finalSpoken = (transcriptReceived || commandInput.value).trim();
    if (finalSpoken && !finalSpoken.startsWith('Listening')) {
      appendLog('USER', finalSpoken);
      
      // Check for voice exit command
      if (["stop listening", "stop", "pause", "go to sleep", "standby"].includes(finalSpoken.toLowerCase())) {
        isContinuousMode = false;
        continuousModeBadge.innerText = 'IDLE';
        continuousModeBadge.classList.remove('unlocked');
        appendLog('JARVIS', 'Continuous listening paused. Click 2-WAY or the mic whenever you need me, Boss.');
        speakBrowserNative('Continuous listening paused. Standing by, Boss.');
        commandInput.value = '';
        return;
      }

      sendCommand(finalSpoken);
      commandInput.value = '';
      return;
    }

    // Silence or empty input: seamlessly continue listening in 2-Way mode
    commandInput.value = '';
    if (isContinuousMode) {
      statusText.innerText = '🎙️ 2-WAY: LISTENING (SPEAK NOW)...';
      setTimeout(() => {
        if (isContinuousMode && !isListening) {
          startListening();
        }
      }, 300);
    } else {
      statusText.innerText = 'ONLINE // STANDING BY';
    }
  }

  function toggleListening() {
    if (isListening) {
      stopListening(true);
    } else {
      // Clicking the mic button also engages 2-way mode automatically!
      isContinuousMode = true;
      continuousModeBadge.innerText = 'ACTIVE 2-WAY';
      continuousModeBadge.classList.add('unlocked');
      continuousModeBadge.style.color = '#10b981';
      continuousModeBadge.style.borderColor = '#10b981';
      startListening();
    }
  }

  btnMic.addEventListener('click', toggleListening);

  // --- Hardware System Mic Trigger ---
  async function triggerHardwareMic() {
    if (isHardwareListening || isListening) return;
    isHardwareListening = true;
    btnHardwareMic.classList.add('listening');
    statusText.innerText = 'LISTENING VIA REALTEK SYSTEM MICROPHONE (6s)...';
    if (window.visualizer) window.visualizer.setListening(true);
    appendLog('SYSTEM', '🎧 System hardware microphone active. Please speak your command or passcode now...');

    try {
      const res = await fetch('/api/voice/listen', { method: 'POST' });
      const data = await res.json();

      if (data.success && data.transcribed) {
        appendLog('USER', data.transcribed);
        appendLog('JARVIS', data.reply);
        if (data.unlocked !== undefined) updateAuthBadge(data.unlocked);
        playVoiceResponse(data.audio_base64, data.voice_reply || data.reply);
      } else {
        appendLog('SYSTEM', data.reply || 'Voice capture ended with no speech detected.');
        handleVoicePlaybackEnded();
      }
    } catch (err) {
      console.error('Hardware mic error:', err);
      appendLog('SYSTEM', '⚠️ Could not connect to system audio engine.');
      handleVoicePlaybackEnded();
    } finally {
      isHardwareListening = false;
      btnHardwareMic.classList.remove('listening');
    }
  }

  btnHardwareMic.addEventListener('click', triggerHardwareMic);

  // --- Voice Playback & Automatic 2-Way Loop Resume ---
  function stopAllAudio() {
    clearTimeout(fallbackAudioTimer);
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (audioPlayer) {
      audioPlayer.pause();
      audioPlayer.currentTime = 0;
    }
  }

  function playVoiceResponse(b64Audio, voiceText) {
    stopAllAudio();
    lastVoiceText = voiceText || '';

    if (b64Audio) {
      // Primary: High-fidelity neural Edge-TTS voice
      audioPlayer.src = `data:audio/mp3;base64,${b64Audio}`;
      if (window.visualizer) window.visualizer.setSpeaking(true);
      statusText.innerText = 'JARVIS TRANSMITTING AUDIO...';

      audioPlayer.onended = () => {
        handleVoicePlaybackEnded();
      };

      audioPlayer.onerror = (e) => {
        console.warn('Audio stream error, falling back to browser voice:', e);
        speakBrowserNative(voiceText);
      };

      audioPlayer.play().catch(e => {
        console.warn('Audio auto-play prevented, falling back to browser voice:', e);
        speakBrowserNative(voiceText);
      });
    } else if (voiceText) {
      // Fallback: Browser native voice (only when server audio is absent)
      speakBrowserNative(voiceText);
    } else {
      handleVoicePlaybackEnded();
    }
  }

  function speakBrowserNative(text) {
    stopAllAudio();
    if (!window.speechSynthesis || !text) {
      handleVoicePlaybackEnded();
      return;
    }

    try {
      const cleanText = text.replace(/[*_#`]/g, '').trim();
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      // Select an English voice
      const voices = window.speechSynthesis.getVoices();
      const ukVoice = voices.find(v => v.lang === 'en-GB' || v.name.includes('George') || v.name.includes('David') || v.name.includes('Natural'));
      if (ukVoice) utterance.voice = ukVoice;

      if (window.visualizer) window.visualizer.setSpeaking(true);
      statusText.innerText = 'JARVIS TRANSMITTING AUDIO...';

      utterance.onend = () => {
        handleVoicePlaybackEnded();
      };

      utterance.onerror = () => {
        handleVoicePlaybackEnded();
      };

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('Speech synthesis error:', e);
      handleVoicePlaybackEnded();
    }
  }

  function handleVoicePlaybackEnded() {
    if (window.visualizer) window.visualizer.setSpeaking(false);
    statusText.innerText = 'ONLINE // STANDING BY';

    // 2-WAY HANDS-FREE AUTOMATIC RESUME:
    // If continuous mode is on, automatically open the mic so the user can speak again!
    if (isContinuousMode) {
      statusText.innerText = '🎙️ 2-WAY: LISTENING FOR YOUR VOICE...';
      setTimeout(() => {
        if (isContinuousMode && !isListening) {
          startListening();
        }
      }, 400);
    }
  }

  // --- WebSocket Connection ---
  function connectWebSocket() {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      statusText.innerText = isContinuousMode ? '🎙️ 2-WAY MODE: LISTENING...' : 'ONLINE // STANDING BY';
      appendLog('SYSTEM', 'Quantum telemetry channel linked. All subsystems online.');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    socket.onclose = () => {
      statusText.innerText = 'DISCONNECTED // RECONNECTING...';
      setTimeout(connectWebSocket, 3000);
    };
  }

  function handleServerMessage(data) {
    if (data.type === 'response') {
      appendLog('JARVIS', data.reply);
      if (data.unlocked !== undefined) updateAuthBadge(data.unlocked);

      // Play single voice stream
      playVoiceResponse(data.audio_base64, data.voice_text || data.reply);
    } else if (data.type === 'status_update') {
      if (data.unlocked !== undefined) updateAuthBadge(data.unlocked);
    }
  }

  function updateAuthBadge(isUnlocked) {
    if (isUnlocked) {
      authStatusBadge.innerText = 'AUTHORIZED';
      authStatusBadge.classList.add('unlocked');
      authActionLabel.innerText = 'Lock System';
      authIcon.innerText = '🔓';
      try { localStorage.setItem('jarvis_unlocked', 'true'); } catch (e) {}
    } else {
      authStatusBadge.innerText = 'LOCKED';
      authStatusBadge.classList.remove('unlocked');
      authActionLabel.innerText = 'Unlock JARVIS';
      authIcon.innerText = '🔒';
      try { localStorage.setItem('jarvis_unlocked', 'false'); } catch (e) {}
    }
  }

  async function checkInitialStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (data && data.unlocked !== undefined) {
        updateAuthBadge(data.unlocked);
      }
    } catch (e) {
      if (localStorage.getItem('jarvis_unlocked') === 'true') {
        updateAuthBadge(true);
      }
    }
  }
  checkInitialStatus();

  function sendCommand(text) {
    if (!text.trim()) return;
    if (socket && socket.readyState === WebSocket.OPEN) {
      statusText.innerText = 'PROCESSING TELEMETRY...';
      socket.send(JSON.stringify({ text: text.trim() }));
    } else {
      // Fallback HTTP POST
      fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() })
      })
      .then(res => res.json())
      .then(data => {
        appendLog('JARVIS', data.reply);
        if (data.unlocked !== undefined) updateAuthBadge(data.unlocked);
        playVoiceResponse(data.audio_base64, data.voice_text || data.reply);
      })
      .catch(() => {
        appendLog('SYSTEM', 'Cannot send: Gateway link inactive.');
        handleVoicePlaybackEnded();
      });
    }
  }

  function appendLog(sender, message) {
    const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
    const entry = document.createElement('div');
    entry.className = `feed-entry ${sender.toLowerCase()}-entry`;

    let tag = `[${sender}]`;
    entry.innerHTML = `
      <span class="entry-time">[${timeStr}]</span>
      <span class="entry-tag">${tag}</span>
      <span class="entry-msg">${escapeHtml(message).replace(/\n/g, '<br>')}</span>
    `;

    terminalFeed.appendChild(entry);
    terminalFeed.scrollTop = terminalFeed.scrollHeight;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.innerText = str;
    return div.innerHTML;
  }

  commandForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const val = commandInput.value.trim();
    if (!val) return;
    appendLog('USER', val);
    sendCommand(val);
    commandInput.value = '';
  });

  btnClearLog.addEventListener('click', () => {
    terminalFeed.innerHTML = '';
  });

  // Passcode Configuration Modal Logic
  if (btnOpenPasscodeModal && passcodeModal) {
    btnOpenPasscodeModal.addEventListener('click', () => {
      passcodeModal.classList.add('active');
      modalPasscodeInput.focus();
    });

    btnCancelPasscode.addEventListener('click', () => {
      passcodeModal.classList.remove('active');
    });

    btnSavePasscode.addEventListener('click', async () => {
      const newPass = modalPasscodeInput.value.trim();
      if (!newPass) return;

      try {
        const res = await fetch('/api/security/set-passcode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_code: newPass })
        });
        const data = await res.json();
        if (data.success) {
          appendLog('SYSTEM', `✅ Voice security passcode updated to: "${data.passcode}". Stored in .env.`);
          passcodeModal.classList.remove('active');
          modalPasscodeInput.value = '';
        } else {
          appendLog('SYSTEM', `⚠️ Passcode error: ${data.message}`);
        }
      } catch (err) {
        appendLog('SYSTEM', `⚠️ Failed to save passcode: ${err}`);
      }
    });
  }

  // Email Configuration Modal Logic
  if (btnOpenEmailModal && emailModal) {
    btnOpenEmailModal.addEventListener('click', () => {
      emailModal.classList.add('active');
      modalEmailPasswordInput.focus();
    });

    btnCancelEmail.addEventListener('click', () => {
      emailModal.classList.remove('active');
    });

    btnSaveEmail.addEventListener('click', async () => {
      const pwd = modalEmailPasswordInput.value.trim();
      if (!pwd) return;

      try {
        const res = await fetch('/api/config/set-email-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: pwd })
        });
        const data = await res.json();
        if (data.success) {
          appendLog('SYSTEM', '✅ Gmail App Password saved to .env! Mail automation is now online.');
          emailModal.classList.remove('active');
          modalEmailPasswordInput.value = '';
          sendCommand('check mail');
        } else {
          appendLog('SYSTEM', `⚠️ Gmail setup notice: ${data.message}`);
        }
      } catch (err) {
        appendLog('SYSTEM', `⚠️ Failed to save email password: ${err}`);
      }
    });
  }

  // Quick Action Buttons
  document.getElementById('btn-quick-status').addEventListener('click', () => {
    appendLog('USER', 'Check system status');
    sendCommand('system status');
  });

  document.getElementById('btn-quick-mail').addEventListener('click', () => {
    appendLog('USER', 'Check unread email');
    sendCommand('check mail');
  });

  document.getElementById('btn-quick-news').addEventListener('click', () => {
    appendLog('USER', 'Get tech news');
    sendCommand('tech news');
  });

  document.getElementById('btn-quick-weather').addEventListener('click', () => {
    appendLog('USER', 'Check weather in Pune');
    sendCommand('weather in Pune');
  });

  document.getElementById('btn-quick-auth').addEventListener('click', () => {
    const isCurrentlyUnlocked = authStatusBadge.classList.contains('unlocked');
    if (isCurrentlyUnlocked) {
      appendLog('USER', 'Lock system');
      sendCommand('lock system');
    } else {
      const code = prompt('Enter your Voice/Security Passcode (Default is omega-protocol-9):', '');
      if (code !== null && code.trim() !== '') {
        appendLog('USER', `Authorization Code: ${code.trim()}`);
        sendCommand(code.trim());
      }
    }
  });

  // Initialize
  connectWebSocket();
});
