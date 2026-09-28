// Main Frontend Controller & WebSocket Client for JARVIS
document.addEventListener('DOMContentLoaded', () => {
  const terminalFeed = document.getElementById('terminal-feed');
  const commandForm = document.getElementById('command-form');
  const commandInput = document.getElementById('command-input');
  const btnMic = document.getElementById('btn-mic');
  const btnClearLog = document.getElementById('btn-clear-log');
  const statusText = document.getElementById('status-text');
  const authStatusBadge = document.getElementById('auth-status-badge');
  const audioPlayer = document.getElementById('audio-player');
  const authActionLabel = document.getElementById('auth-action-label');
  const authIcon = document.getElementById('auth-icon');

  // WebSocket Connection
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
  let socket = null;
  let isRecognitionActive = false;
  let recognition = null;

  // Initialize Speech Recognition if supported
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isRecognitionActive = true;
      btnMic.classList.add('listening');
      statusText.innerText = 'LISTENING FOR VOICE COMMAND...';
      if (window.visualizer) window.visualizer.setListening(true);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      appendLog('USER', transcript);
      sendCommand(transcript);
    };

    recognition.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      stopListening();
    };

    recognition.onend = () => {
      stopListening();
    };
  }

  function stopListening() {
    isRecognitionActive = false;
    btnMic.classList.remove('listening');
    statusText.innerText = 'ONLINE // STANDING BY';
    if (window.visualizer) window.visualizer.setListening(false);
  }

  function toggleListening() {
    if (!recognition) {
      alert('Speech Recognition is not supported in this browser. Please use Google Chrome or Edge.');
      return;
    }
    if (isRecognitionActive) {
      recognition.stop();
    } else {
      recognition.start();
    }
  }

  btnMic.addEventListener('click', toggleListening);

  function connectWebSocket() {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      statusText.innerText = 'ONLINE // STANDING BY';
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
      
      // Update Auth status badge
      if (data.unlocked !== undefined) {
        updateAuthBadge(data.unlocked);
      }

      // Play neural speech audio if present
      if (data.audio_base64) {
        playNeuralVoice(data.audio_base64);
      }
    } else if (data.type === 'status_update') {
      if (data.unlocked !== undefined) {
        updateAuthBadge(data.unlocked);
      }
    }
  }

  function updateAuthBadge(isUnlocked) {
    if (isUnlocked) {
      authStatusBadge.innerText = 'AUTHORIZED';
      authStatusBadge.classList.add('unlocked');
      authActionLabel.innerText = 'Lock System';
      authIcon.innerText = '🔓';
    } else {
      authStatusBadge.innerText = 'LOCKED';
      authStatusBadge.classList.remove('unlocked');
      authActionLabel.innerText = 'Unlock JARVIS';
      authIcon.innerText = '🔒';
    }
  }

  function playNeuralVoice(b64Audio) {
    audioPlayer.src = `data:audio/mp3;base64,${b64Audio}`;
    if (window.visualizer) window.visualizer.setSpeaking(true);
    statusText.innerText = 'JARVIS TRANSMITTING AUDIO...';

    audioPlayer.play().catch(e => console.warn('Audio auto-play prevented:', e));

    audioPlayer.onended = () => {
      if (window.visualizer) window.visualizer.setSpeaking(false);
      statusText.innerText = 'ONLINE // STANDING BY';
    };
  }

  function sendCommand(text) {
    if (!text.trim()) return;
    if (socket && socket.readyState === WebSocket.OPEN) {
      statusText.innerText = 'PROCESSING TELEMETRY...';
      socket.send(JSON.stringify({ text: text.trim() }));
    } else {
      appendLog('SYSTEM', 'Cannot send: Gateway link inactive.');
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
    appendLog('USER', 'Check weather');
    sendCommand('weather in Mumbai');
  });

  document.getElementById('btn-quick-auth').addEventListener('click', () => {
    const isCurrentlyUnlocked = authStatusBadge.classList.contains('unlocked');
    if (isCurrentlyUnlocked) {
      appendLog('USER', 'Lock system');
      sendCommand('lock system');
    } else {
      const code = prompt('Enter your secret Voice/Security Passcode:', 'omega-protocol-9');
      if (code) {
        appendLog('USER', `Authorization Code: ${code}`);
        sendCommand(code);
      }
    }
  });

  // Initialize
  connectWebSocket();
});
