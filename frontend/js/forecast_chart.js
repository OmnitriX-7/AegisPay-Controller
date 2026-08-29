/**
 * AegisPay-Controller: Minimalist High-Contrast Forecaster Chart
 * Minimal Swiss Style: Crisp lines, neutral grids, no neon blue blobs
 */

const ForecastChart = {
  canvas: null,
  ctx: null,
  data: null,

  init(canvasId = 'forecastCanvas') {
    this.canvas = document.getElementById(canvasId || 'forecastCanvas');
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.resize();
    window.addEventListener('resize', () => this.resize());
  },

  resize() {
    if (!this.canvas) return;
    const parent = this.canvas.parentElement;
    const rect = parent ? parent.getBoundingClientRect() : null;
    const w = (rect && rect.width > 50) ? rect.width : (parent && parent.offsetWidth > 50 ? parent.offsetWidth : 720);
    const h = (rect && rect.height > 50) ? rect.height : (parent && parent.offsetHeight > 50 ? parent.offsetHeight : 240);
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(h * dpr);
    this.canvas.style.width = `${w}px`;
    this.canvas.style.height = `${h}px`;
    if (this.ctx) {
      this.ctx.setTransform(1, 0, 0, 1, 0, 0);
      this.ctx.scale(dpr, dpr);
    }
    this.draw();
  },

  updateData(forecastResult) {
    this.data = forecastResult;
    if (!this.canvas) this.init('forecastCanvas');
    this.resize();
  },

  draw() {
    if (!this.canvas || !this.ctx || !this.data) return;

    const ctx = this.ctx;
    const dpr = window.devicePixelRatio || 1;
    const w = this.canvas.width / dpr;
    const h = this.canvas.height / dpr;

    ctx.clearRect(0, 0, w, h);

    const padLeft = 70;
    const padRight = 30;
    const padTop = 30;
    const padBottom = 40;
    const chartW = w - padLeft - padRight;
    const chartH = h - padTop - padBottom;

    const days = this.data.projections || this.data.forecast_days || [];
    if (days.length === 0) return;

    // Find min and max
    let minVal = Infinity;
    let maxVal = -Infinity;

    days.forEach(d => {
      const lower = d.lower_bound_95ci !== undefined ? d.lower_bound_95ci : (d.lower_bound_95 || d.projected_cash_balance);
      const upper = d.upper_bound_95ci !== undefined ? d.upper_bound_95ci : (d.upper_bound_95 || d.projected_cash_balance);
      if (lower < minVal) minVal = lower;
      if (upper > maxVal) maxVal = upper;
    });

    const range = (maxVal - minVal) * 1.15 || 1;
    const baseMin = minVal - range * 0.05;

    const getX = (idx) => padLeft + (idx / Math.max(1, days.length - 1)) * chartW;
    const getY = (val) => padTop + chartH - ((val - baseMin) / range) * chartH;

    // 1. Grid Lines & Y Labels
    ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#71717a";
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "right";

    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      const v = baseMin + (range / steps) * i;
      const y = getY(v);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(w - padRight, y);
      ctx.stroke();

      const inrStr = `₹${(v / 100000).toFixed(1)}L`;
      ctx.fillText(inrStr, padLeft - 10, y + 3);
    }

    // 2. Confidence Band Area (Subtle Neutral Fill)
    ctx.beginPath();
    days.forEach((d, idx) => {
      const upper = d.upper_bound_95ci !== undefined ? d.upper_bound_95ci : (d.upper_bound_95 || d.projected_cash_balance);
      const x = getX(idx);
      const y = getY(upper);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    for (let idx = days.length - 1; idx >= 0; idx--) {
      const d = days[idx];
      const lower = d.lower_bound_95ci !== undefined ? d.lower_bound_95ci : (d.lower_bound_95 || d.projected_cash_balance);
      const x = getX(idx);
      const y = getY(lower);
      ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = "rgba(255, 255, 255, 0.04)";
    ctx.fill();

    // 3. Projected Cash Trajectory Line (Crisp White)
    ctx.beginPath();
    days.forEach((d, idx) => {
      const x = getX(idx);
      const y = getY(d.projected_cash_balance);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.stroke();

    // 4. Data Points & X-Labels
    ctx.textAlign = "center";
    days.forEach((d, idx) => {
      const x = getX(idx);
      const y = getY(d.projected_cash_balance);

      // Point circle
      ctx.beginPath();
      ctx.arc(x, y, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.fill();
      ctx.strokeStyle = "#18181c";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // X Label
      if (idx % 2 === 0 || idx === days.length - 1) {
        ctx.fillStyle = "#71717a";
        const label = d.date ? d.date.slice(5) : `D+${d.day_index || idx + 1}`;
        ctx.fillText(label, x, h - padBottom + 18);
      }
    });
  }
};

window.ForecastChart = ForecastChart;
