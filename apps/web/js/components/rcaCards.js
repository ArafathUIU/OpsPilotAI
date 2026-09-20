/**
 * OpsPilot AI — Hypotheses & Critic RCA View Component
 */

export class RcaCardsComponent {
  constructor(containerElement, countBadge) {
    this.container = containerElement;
    this.countBadge = countBadge;
    this.hypotheses = [];
  }

  setHypotheses(hypotheses = []) {
    this.hypotheses = hypotheses || [];
    this.render();
  }

  render() {
    if (this.countBadge) {
      this.countBadge.textContent = this.hypotheses.length;
    }

    if (!this.container) return;

    if (this.hypotheses.length === 0) {
      this.container.innerHTML = `
        <div class="empty-feed">
          <p style="color: var(--text-muted); text-align: center; padding: 48px; font-size: 13px;">
            Root cause analysis has not synthesized hypotheses yet. Investigation is in progress.
          </p>
        </div>
      `;
      return;
    }

    // Sort descending by confidence
    const sorted = [...this.hypotheses].sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0));

    this.container.innerHTML = sorted
      .map((hyp, index) => {
        const isTop = index === 0;
        const confidencePct = Math.round((hyp.confidence_score || 0.8) * 100);
        const evidenceChips = (hyp.supporting_evidence_ids || [])
          .map((id) => `<span class="service-pill" style="color: var(--brand-primary);">${id}</span>`)
          .join('');

        const criticHtml = hyp.critic_notes
          ? `
            <div class="critic-feedback-box">
              <strong>Critic Agent Review:</strong> ${hyp.critic_notes}
            </div>
          `
          : '';

        return `
          <div class="hypothesis-card ${isTop ? 'top-ranked' : ''}">
            <div class="hypothesis-top">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="badge ${isTop ? 'badge-sev1' : 'badge-subtle'}">Rank #${index + 1}</span>
                <span class="card-id">${hyp.hypothesis_id || 'HYP'}</span>
              </div>
              <div class="confidence-bar-wrap">
                <span class="confidence-text">${confidencePct}% Confidence</span>
                <div class="confidence-bar">
                  <div class="confidence-fill" style="width: ${confidencePct}%;"></div>
                </div>
              </div>
            </div>

            <div class="hypothesis-statement">
              ${hyp.statement}
            </div>

            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span style="font-size: 11px; color: var(--text-muted);">Supporting Evidence:</span>
              ${evidenceChips || '<span style="font-size: 11px; color: var(--text-dim);">None</span>'}
            </div>

            ${criticHtml}
          </div>
        `;
      })
      .join('');
  }
}
