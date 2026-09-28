// Web Audio API & Canvas Waveform Visualizer for JARVIS Core
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
    this.numBars = 64;
    this.isSpeaking = false;
    this.isListening = false;
    this.phase = 0;

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

  render() {
    this.ctx.clearRect(0, 0, this.width, this.height);
    this.phase += 0.04;

    const angleStep = (Math.PI * 2) / this.numBars;

    for (let i = 0; i < this.numBars; i++) {
      const angle = i * angleStep;
      
      // Calculate dynamic bar height
      let magnitude = 6;
      if (this.isSpeaking) {
        magnitude = 15 + Math.sin(this.phase * 4 + i * 0.5) * 18 + Math.cos(this.phase * 2 + i * 0.2) * 12;
      } else if (this.isListening) {
        magnitude = 10 + Math.sin(this.phase * 6 + i) * 12;
      } else {
        magnitude = 4 + Math.sin(this.phase + i * 0.3) * 3;
      }

      const x1 = this.centerX + Math.cos(angle) * this.baseRadius;
      const y1 = this.centerY + Math.sin(angle) * this.baseRadius;
      const x2 = this.centerX + Math.cos(angle) * (this.baseRadius + magnitude);
      const y2 = this.centerY + Math.sin(angle) * (this.baseRadius + magnitude);

      // Colors
      this.ctx.beginPath();
      this.ctx.moveTo(x1, y1);
      this.ctx.lineTo(x2, y2);
      this.ctx.lineWidth = 2.5;

      if (this.isSpeaking) {
        this.ctx.strokeStyle = `rgba(0, 243, 255, ${0.4 + (magnitude / 45)})`;
        this.ctx.shadowColor = '#00f3ff';
        this.ctx.shadowBlur = 10;
      } else if (this.isListening) {
        this.ctx.strokeStyle = `rgba(239, 68, 68, ${0.5 + (magnitude / 30)})`;
        this.ctx.shadowColor = '#ef4444';
        this.ctx.shadowBlur = 8;
      } else {
        this.ctx.strokeStyle = 'rgba(0, 243, 255, 0.25)';
        this.ctx.shadowBlur = 0;
      }

      this.ctx.stroke();
    }

    requestAnimationFrame(this.render);
  }
}

window.visualizer = new HudVisualizer('waveform-canvas');
