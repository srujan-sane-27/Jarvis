// Web Audio API & Canvas Waveform Visualizer for JARVIS Core (Optimized for ultra-low CPU/GPU load)
class HudVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.width = this.canvas.width;
    this.height = this.canvas.height;
    this.centerX = this.width / 2;
    this.centerY = this.height / 2;
    this.baseRadius = 90;
    this.numBars = 48; // Optimized bar count
    this.isSpeaking = false;
    this.isListening = false;
    this.phase = 0;
    this.lastFrameTime = 0;
    this.isTabActive = !document.hidden;

    // Handle tab visibility to save 100% CPU when tab is hidden
    document.addEventListener('visibilitychange', () => {
      this.isTabActive = !document.hidden;
      if (this.isTabActive) {
        requestAnimationFrame(this.render);
      }
    });

    this.render = this.render.bind(this);
    requestAnimationFrame(this.render);
  }

  setSpeaking(speaking) {
    this.isSpeaking = speaking;
    const orb = document.getElementById('core-orb');
    if (orb) {
      if (speaking) orb.classList.add('speaking');
      else orb.classList.remove('speaking');
    }
  }

  setListening(listening) {
    this.isListening = listening;
  }

  connectAudioSource(analyserNode) {
    this.analyser = analyserNode;
    this.audioData = new Uint8Array(this.analyser.frequencyBinCount);
  }

  render(timestamp) {
    if (!this.isTabActive) return;

    // Throttle idle animation to ~25fps (40ms) to keep CPU load near 0%
    const isEngaged = this.isSpeaking || this.isListening;
    const minInterval = isEngaged ? 16 : 40; // 60fps when active, 25fps when idle
    const elapsed = timestamp - this.lastFrameTime;

    if (elapsed < minInterval) {
      requestAnimationFrame(this.render);
      return;
    }
    this.lastFrameTime = timestamp;

    this.ctx.clearRect(0, 0, this.width, this.height);
    this.phase += isEngaged ? 0.08 : 0.02;

    const angleStep = (Math.PI * 2) / this.numBars;

    // Setup styles once per frame (avoids costly canvas context switching)
    this.ctx.lineWidth = 2.0;
    if (this.isSpeaking) {
      this.ctx.strokeStyle = 'rgba(0, 243, 255, 0.9)';
      this.ctx.shadowColor = '#00f3ff';
      this.ctx.shadowBlur = 8;
    } else if (this.isListening) {
      this.ctx.strokeStyle = 'rgba(239, 68, 68, 0.9)';
      this.ctx.shadowColor = '#ef4444';
      this.ctx.shadowBlur = 8;
    } else {
      this.ctx.strokeStyle = 'rgba(0, 243, 255, 0.3)';
      this.ctx.shadowColor = 'transparent';
      this.ctx.shadowBlur = 0;
    }

    if (this.analyser && this.isListening && this.audioData) {
      this.analyser.getByteFrequencyData(this.audioData);
    }

    // Batch all strokes into a single draw call
    this.ctx.beginPath();
    for (let i = 0; i < this.numBars; i++) {
      const angle = i * angleStep;
      
      let magnitude = 4;
      if (this.isSpeaking) {
        magnitude = 14 + Math.sin(this.phase * 4 + i * 0.5) * 16 + Math.cos(this.phase * 2 + i * 0.2) * 10;
      } else if (this.isListening) {
        if (this.analyser && this.audioData) {
          const dataIdx = Math.floor(i * (this.audioData.length / this.numBars));
          magnitude = 6 + ((this.audioData[dataIdx] || 0) / 255) * 26;
        } else {
          magnitude = 8 + Math.sin(this.phase * 5 + i) * 10;
        }
      } else {
        magnitude = 3 + Math.sin(this.phase + i * 0.4) * 2.5;
      }

      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      const x1 = this.centerX + cosA * this.baseRadius;
      const y1 = this.centerY + sinA * this.baseRadius;
      const x2 = this.centerX + cosA * (this.baseRadius + magnitude);
      const y2 = this.centerY + sinA * (this.baseRadius + magnitude);

      this.ctx.moveTo(x1, y1);
      this.ctx.lineTo(x2, y2);
    }
    this.ctx.stroke();

    requestAnimationFrame(this.render);
  }
}

window.visualizer = new HudVisualizer('waveform-canvas');
