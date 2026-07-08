/** Paleta e helpers de gráficos — espelho PanelDX scripts.js (DIAG_CHART) */

export const DIAG_CHART = {
  realidade: { bg: 'rgba(124, 45, 18, 0.32)', border: '#7c2d12', point: '#7c2d12' },
  gapLine: '#b91c1c',
  ambicao: { bg: 'rgba(108, 92, 231, 0.28)', border: '#6c5ce7', point: '#6c5ce7' },
  setorial: { bg: 'rgba(217, 119, 6, 0.28)', border: '#d97706', point: '#d97706' },
  font: { family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif", size: 11 },
  grid: 'rgba(74, 46, 128, 0.08)',
  tick: '#64748b',
};

export function diagBarFill(color) {
  return color.bg.replace(/[\d.]+\)$/, '0.88)');
}

export function computeFocusedScale(scores, minSpan = 1.4) {
  const vals = scores.filter((v) => Number.isFinite(v));
  if (!vals.length) return { min: 0, max: 5 };

  const dataMin = Math.min(...vals);
  const dataMax = Math.max(...vals);
  const pad = Math.max((dataMax - dataMin) * 0.18, 0.25);
  let min = Math.max(0, dataMin - pad);
  let max = Math.min(5, dataMax + pad);

  if (max - min < minSpan) {
    const mid = (dataMin + dataMax) / 2;
    min = Math.max(0, mid - minSpan / 2);
    max = Math.min(5, mid + minSpan / 2);
  }

  return {
    min: Math.floor(min * 10) / 10,
    max: Math.ceil(max * 10) / 10,
  };
}

export function createDiagGapPlugin(items, mode, pluginId = 'diagGap') {
  return {
    id: pluginId,
    afterDraw(chart) {
      const xScale = chart.scales.x;
      const yScale = chart.scales.y;
      if (!xScale || !yScale || !items.length) return;

      const { ctx, chartArea } = chart;
      ctx.save();
      ctx.beginPath();
      ctx.rect(
        chartArea.left,
        chartArea.top,
        chartArea.right - chartArea.left,
        chartArea.bottom - chartArea.top,
      );
      ctx.clip();

      items.forEach((item) => {
        const gapVal = Number.isFinite(item.gap) ? item.gap : item.fut - item.pres;
        if (!Number.isFinite(gapVal) || gapVal <= 0.001) return;

        const x1 = xScale.getPixelForValue(item.pres);
        const x2 = xScale.getPixelForValue(item.fut);

        let y1;
        let y2;
        if (mode === 'grouped') {
          const label = chart.data.labels[item.index];
          const yCenter = yScale.getPixelForValue(label);
          const band = chart.data.labels.length
            ? (yScale.bottom - yScale.top) / chart.data.labels.length
            : 24;
          y1 = yCenter - band * 0.18;
          y2 = yCenter + band * 0.18;
        } else {
          y1 = yScale.getPixelForValue('Real.');
          y2 = yScale.getPixelForValue('Amb.');
        }

        ctx.strokeStyle = DIAG_CHART.gapLine;
        ctx.lineWidth = 3;
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        ctx.setLineDash([]);

        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        const text = `Δ ${gapVal.toFixed(1)}`;
        ctx.font = 'bold 10px Segoe UI, Tahoma, sans-serif';
        const textW = ctx.measureText(text).width;
        const boxW = textW + 10;
        const boxH = 16;

        ctx.fillStyle = DIAG_CHART.gapLine;
        ctx.fillRect(midX - boxW / 2, midY - boxH / 2, boxW, boxH);
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, midX, midY);
      });

      ctx.restore();
    },
  };
}
