/**
 * OpsPilot AI — Human In The Loop (HITL) Approval Modal Component
 */

export class ApprovalModalComponent {
  constructor({ modalEl, closeBtn, approveBtn, rejectBtn, onDecision }) {
    this.modal = modalEl;
    this.closeBtn = closeBtn;
    this.approveBtn = approveBtn;
    this.rejectBtn = rejectBtn;
    this.onDecision = onDecision;

    this.currentIncidentId = null;
    this.currentApproval = null;

    this._bindEvents();
  }

  _bindEvents() {
    if (this.closeBtn) {
      this.closeBtn.addEventListener('click', () => this.hide());
    }

    if (this.approveBtn) {
      this.approveBtn.addEventListener('click', () => this._handleDecision('APPROVED'));
    }

    if (this.rejectBtn) {
      this.rejectBtn.addEventListener('click', () => this._handleDecision('REJECTED'));
    }

    // Dismiss on clicking overlay
    if (this.modal) {
      this.modal.addEventListener('click', (e) => {
        if (e.target === this.modal) this.hide();
      });
    }
  }

  show(incidentId, approval) {
    this.currentIncidentId = incidentId;
    this.currentApproval = approval;

    // Populate elements
    const riskBadge = document.getElementById('modalRiskBadge');
    const actionId = document.getElementById('modalActionId');
    const actionType = document.getElementById('modalActionType');
    const targetService = document.getElementById('modalTargetService');
    const actionDesc = document.getElementById('modalActionDescription');
    const blastRadiusEl = document.getElementById('modalBlastRadius');
    const rollbackPlan = document.getElementById('modalRollbackPlan');
    const paramEditor = document.getElementById('modalParamEditor');
    const decisionReason = document.getElementById('modalDecisionReason');

    if (riskBadge) {
      const risk = (approval.risk_level || 'HIGH').toUpperCase();
      riskBadge.textContent = `${risk} RISK`;
      riskBadge.className = `risk-badge-lg ${risk === 'CRITICAL' ? 'critical' : risk === 'HIGH' ? 'high' : 'low'}`;
    }

    if (actionId) actionId.textContent = approval.action_id || approval.id;
    if (actionType) actionType.textContent = approval.action_type;
    if (targetService) targetService.textContent = approval.target_service;
    if (actionDesc) actionDesc.textContent = approval.description || 'Automated remediation step requiring human authorization.';
    if (rollbackPlan) rollbackPlan.textContent = approval.rollback_plan || 'Revert state changes automatically if verification probes fail.';

    if (blastRadiusEl) {
      const blast = approval.blast_radius || [approval.target_service];
      blastRadiusEl.innerHTML = blast
        .map((svc) => `<span class="blast-tag">${svc}</span>`)
        .join('');
    }

    if (paramEditor) {
      paramEditor.value = JSON.stringify(approval.parameters || {}, null, 2);
    }

    if (decisionReason) {
      decisionReason.value = '';
    }

    this.modal.style.display = 'flex';
  }

  hide() {
    if (this.modal) {
      this.modal.style.display = 'none';
    }
    this.currentApproval = null;
  }

  async _handleDecision(decision) {
    if (!this.currentApproval || !this.currentIncidentId) return;

    const paramEditor = document.getElementById('modalParamEditor');
    const decisionReason = document.getElementById('modalDecisionReason');

    let modifiedParams = null;
    let actualDecision = decision;

    if (decision === 'APPROVED' && paramEditor && paramEditor.value) {
      try {
        const parsed = JSON.parse(paramEditor.value);
        if (JSON.stringify(parsed) !== JSON.stringify(this.currentApproval.parameters || {})) {
          modifiedParams = parsed;
          actualDecision = 'MODIFIED';
        }
      } catch (err) {
        alert('Invalid JSON in Action Parameters editor: ' + err.message);
        return;
      }
    }

    const payload = {
      decision: actualDecision,
      approver_id: 'lead-sre@company.com',
      approver_role: 'OPERATOR',
      reason: decisionReason ? decisionReason.value : '',
      modified_parameters: modifiedParams,
    };

    if (this.onDecision) {
      await this.onDecision(this.currentIncidentId, this.currentApproval.id, payload);
    }

    this.hide();
  }
}
