/**
 * OpsPilot AI — Live Agent War Room Stream Component
 */

export class AgentStreamComponent {
  constructor(containerElement) {
    this.container = containerElement;
    this.messages = [];
    this.autoScroll = true;
  }

  setAutoScroll(enabled) {
    this.autoScroll = enabled;
  }

  clear() {
    this.messages = [];
    this.render();
  }

  _getRoleClass(actor = '') {
    const act = (actor || '').toLowerCase();
    if (act.includes('supervisor')) return 'supervisor';
    if (act.includes('log')) return 'log-analyst';
    if (act.includes('metric')) return 'metrics-analyst';
    if (act.includes('code')) return 'code-analyst';
    if (act.includes('critic')) return 'critic';
    if (act.includes('rca') || act.includes('root')) return 'rca';
    if (act.includes('remediat')) return 'remediation';
    if (act.includes('verif')) return 'verifier';
    return 'supervisor';
  }

  _getInitials(actor = '') {
    const act = (actor || '').toUpperCase();
    if (act.includes('SUPERVISOR')) return 'SUP';
    if (act.includes('LOG')) return 'LOG';
    if (act.includes('METRIC')) return 'MET';
    if (act.includes('CODE')) return 'COD';
    if (act.includes('CRITIC')) return 'CRT';
    if (act.includes('RCA')) return 'RCA';
    if (act.includes('REMEDIAT')) return 'REM';
    if (act.includes('VERIF')) return 'VER';
    return act.substring(0, 3) || 'AI';
  }

  addMessage({ actor, stage, message, metadata, timestamp }) {
    const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    this.messages.push({
      actor: actor || 'System',
      stage: stage || 'INFO',
      message: message || '',
      metadata: metadata || {},
      timeStr,
    });
    this.render();
  }

  setTimeline(timeline = []) {
    this.messages = (timeline || []).map((ev) => ({
      actor: ev.actor || 'Agent',
      stage: ev.stage || 'PROGRESS',
      message: ev.message || '',
      metadata: ev.metadata || {},
      timeStr: ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '',
    }));
    this.render();
  }

  render() {
    if (!this.container) return;

    if (this.messages.length === 0) {
      this.container.innerHTML = `
        <div class="stream-placeholder">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width: 48px; height: 48px; color: var(--text-dim); margin-bottom: 12px;">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 14 14"/>
          </svg>
          <p style="color: var(--text-muted); font-size: 13px;">No agent activity recorded yet for this incident.</p>
        </div>
      `;
      return;
    }

    this.container.innerHTML = this.messages
      .map((msg) => {
        const roleClass = this._getRoleClass(msg.actor);
        const initials = this._getInitials(msg.actor);

        // Tool call or metadata chip
        let toolHtml = '';
        if (msg.metadata && msg.metadata.tool_name) {
          toolHtml = `<div class="tool-chip"><span>⚡ Tool:</span> ${msg.metadata.tool_name}</div>`;
        }

        return `
          <div class="stream-message-card">
            <div class="agent-avatar ${roleClass}" title="${msg.actor}">${initials}</div>
            <div class="message-body">
              <div class="message-header">
                <span class="message-author">${msg.actor}</span>
                <span class="message-time">${msg.timeStr}</span>
              </div>
              <div class="message-content">${msg.message}</div>
              ${toolHtml}
            </div>
          </div>
        `;
      })
      .join('');

    if (this.autoScroll) {
      this.container.scrollTop = this.container.scrollHeight;
    }
  }
}
