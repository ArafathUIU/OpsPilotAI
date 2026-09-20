/**
 * OpsPilot AI — Postmortem Report Viewer Component
 */

export class PostmortemViewerComponent {
  constructor({ contentEl, statsEl, onGenerateReport }) {
    this.contentEl = contentEl;
    this.statsEl = statsEl;
    this.onGenerateReport = onGenerateReport;
    this.currentReport = null;
  }

  setReport(report) {
    this.currentReport = report;
    this.render();
  }

  _simpleMarkdownToHtml(markdown = '') {
    if (!markdown) return '';

    return markdown
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\> (.*$)/gim, '<blockquote style="border-left: 3px solid var(--brand-primary); padding-left: 12px; margin: 8px 0; color: #a5b4fc;">$1</blockquote>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/```([\s\S]*?)```/gim, '<pre>$1</pre>')
      .replace(/`([^`]+)`/gim, '<code style="background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); color: #38bdf8;">$1</code>')
      .replace(/\n\n/gim, '<br><br>');
  }

  exportMarkdown() {
    if (!this.currentReport || !this.currentReport.markdown_content) {
      alert('No postmortem report content available to export.');
      return;
    }

    const blob = new Blob([this.currentReport.markdown_content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `postmortem-${this.currentReport.incident_id}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  render() {
    if (!this.contentEl) return;

    if (!this.currentReport) {
      this.contentEl.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: 48px 24px;">
          <p style="color: var(--text-muted); font-size: 13px;">No postmortem report generated for this incident yet.</p>
          <button class="btn btn-primary btn-sm" id="btnGenReportInline" style="margin-top: 14px;">Generate Preliminary Report</button>
        </div>
      `;

      const genBtn = document.getElementById('btnGenReportInline');
      if (genBtn && this.onGenerateReport) {
        genBtn.addEventListener('click', () => this.onGenerateReport());
      }

      if (this.statsEl) this.statsEl.innerHTML = '';
      return;
    }

    // Stats bar
    if (this.statsEl) {
      const mttd = Math.round(this.currentReport.mttd_seconds || 0);
      const mttr = Math.round(this.currentReport.mttr_seconds || 0);
      this.statsEl.innerHTML = `
        <div class="meta-chip">MTTD: <strong>${mttd}s</strong></div>
        <div class="meta-chip">MTTR: <strong>${mttr}s</strong></div>
        <div class="meta-chip">Status: <strong style="color: var(--success-emerald);">${this.currentReport.is_resolved ? 'RESOLVED' : 'IN PROGRESS'}</strong></div>
      `;
    }

    // Body content
    const html = this._simpleMarkdownToHtml(this.currentReport.markdown_content);
    this.contentEl.innerHTML = html;
  }
}
