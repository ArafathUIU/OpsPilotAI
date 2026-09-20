/**
 * OpsPilot AI — Multi-Tab Evidence Inspector Component
 */

export class EvidenceViewerComponent {
  constructor({ logsContent, metricsGrid, diffsContainer, memoryGrid, counts }) {
    this.logsEl = logsContent;
    this.metricsEl = metricsGrid;
    this.diffsEl = diffsContainer;
    this.memoryEl = memoryGrid;
    this.counts = counts || {};
    this.evidence = [];
  }

  setEvidence(evidenceList = []) {
    this.evidence = evidenceList || [];
    this.render();
  }

  _renderSparkline(points = []) {
    if (!points || points.length < 2) return '';
    const min = Math.min(...points);
    const max = Math.max(...points) || 1;
    const range = max - min || 1;
    const width = 240;
    const height = 40;

    const coords = points.map((val, idx) => {
      const x = (idx / (points.length - 1)) * width;
      const y = height - ((val - min) / range) * (height - 8) - 4;
      return `${x},${y}`;
    });

    return `
      <svg class="metric-sparkline" viewBox="0 0 ${width} ${height}">
        <polyline fill="none" stroke="#6366f1" stroke-width="2" points="${coords.join(' ')}" />
      </svg>
    `;
  }

  render() {
    const logs = this.evidence.filter((e) => e.source_type === 'logs' || e.source_type === 'log');
    const metrics = this.evidence.filter((e) => e.source_type === 'metrics' || e.source_type === 'metric');
    const diffs = this.evidence.filter((e) => e.source_type === 'git_diff' || e.source_type === 'code');
    const memory = this.evidence.filter((e) => e.source_type === 'rag_incident' || e.source_type === 'memory');

    // Update counts badges
    if (this.counts.logs) this.counts.logs.textContent = logs.length;
    if (this.counts.metrics) this.counts.metrics.textContent = metrics.length;
    if (this.counts.diffs) this.counts.diffs.textContent = diffs.length;
    if (this.counts.memory) this.counts.memory.textContent = memory.length;
    if (this.counts.total) this.counts.total.textContent = this.evidence.length;

    // 1. Logs Pane
    if (this.logsEl) {
      if (logs.length === 0) {
        this.logsEl.textContent = 'No log anomalies or error stack traces captured yet.';
      } else {
        const logLines = logs.map((l) => {
          const raw = l.data && l.data.raw ? l.data.raw : JSON.stringify(l.data, null, 2);
          return `[${l.timestamp || 'LOG'}] ${l.service_name || 'SYSTEM'}: ${raw}`;
        });
        this.logsEl.textContent = logLines.join('\n\n');
      }
    }

    // 2. Metrics Pane
    if (this.metricsEl) {
      if (metrics.length === 0) {
        this.metricsEl.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No metric anomalies detected.</p>';
      } else {
        this.metricsEl.innerHTML = metrics
          .map((m) => {
            const data = m.data || {};
            const isAnomaly = data.is_anomalous !== false;
            const val = data.current_value !== undefined ? data.current_value : (data.value || 0);
            const valClass = isAnomaly ? 'danger' : 'healthy';
            const sparkPoints = data.history || [val * 0.4, val * 0.6, val * 0.5, val * 0.9, val];

            return `
              <div class="metric-card ${isAnomaly ? 'anomalous' : ''}">
                <div class="metric-header">
                  <span class="metric-name">${m.service_name} / ${data.metric_name || 'telemetry'}</span>
                  <span class="badge ${isAnomaly ? 'badge-sev1' : 'badge-subtle'}">${isAnomaly ? 'ANOMALY' : 'NORMAL'}</span>
                </div>
                <div class="metric-value ${valClass}">${val} <span style="font-size: 14px; color: var(--text-muted);">${data.unit || ''}</span></div>
                ${this._renderSparkline(sparkPoints)}
              </div>
            `;
          })
          .join('');
      }
    }

    // 3. Diffs Pane
    if (this.diffsEl) {
      if (diffs.length === 0) {
        this.diffsEl.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No suspicious commit diffs or code changes flagged.</p>';
      } else {
        this.diffsEl.innerHTML = diffs
          .map((d) => {
            const diffText = (d.data && d.data.diff) || JSON.stringify(d.data, null, 2);
            const lines = diffText.split('\n').map((line) => {
              if (line.startsWith('+')) return `<div class="diff-line addition">${line}</div>`;
              if (line.startsWith('-')) return `<div class="diff-line deletion">${line}</div>`;
              if (line.startsWith('@@') || line.startsWith('diff --git')) return `<div class="diff-line header">${line}</div>`;
              return `<div class="diff-line">${line}</div>`;
            });
            return `<div style="margin-bottom: 20px;"><h4>${d.service_name} (Commit: ${d.data?.commit_hash || 'HEAD'})</h4>${lines.join('')}</div>`;
          })
          .join('');
      }
    }

    // 4. Memory Pane
    if (this.memoryEl) {
      if (memory.length === 0) {
        this.memoryEl.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No matching historical postmortems found in vector memory.</p>';
      } else {
        this.memoryEl.innerHTML = memory
          .map((mem) => {
            const d = mem.data || {};
            const scorePercent = Math.round((d.similarity_score || 0.88) * 100);
            return `
              <div class="memory-card">
                <div class="memory-similarity">Cosine Similarity: ${scorePercent}% match</div>
                <div class="memory-title">${d.title || 'Historical Incident'}</div>
                <div class="memory-rca"><strong>Root Cause:</strong> ${d.root_cause || 'Pool exhaustion from connection leak'}</div>
                <div class="memory-rca" style="color: var(--brand-primary);"><strong>Remediation:</strong> ${d.remediation_applied || 'Rollback commit and increase pool limit'}</div>
              </div>
            `;
          })
          .join('');
      }
    }
  }
}
