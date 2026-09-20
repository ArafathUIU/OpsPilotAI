/**
 * OpsPilot AI — Master Application Controller
 */

import { api } from './api.js';
import { stream } from './sse.js';
import { ServiceTopologyGraph } from './topology.js';
import { IncidentListComponent } from './components/incidentList.js';
import { AgentStreamComponent } from './components/agentStream.js';
import { EvidenceViewerComponent } from './components/evidenceViewer.js';
import { RcaCardsComponent } from './components/rcaCards.js';
import { ApprovalModalComponent } from './components/approvalModal.js';
import { PostmortemViewerComponent } from './components/postmortemViewer.js';

// Pre-registered failure scenarios for interactive simulation
const SIMULATED_SCENARIOS = [
  { id: 'redis_pool_exhaustion', title: 'Redis Connection Pool Exhaustion', service: 'payment-service', sev: 'SEV1', desc: 'Pool exhaustion causing HTTP 500 spike and checkout payment failures.' },
  { id: 'deadlock_under_load', title: 'Database Transaction Deadlock', service: 'order-service', sev: 'SEV1', desc: 'Concurrent row locking leading to thread stalls and timeout cascades.' },
  { id: 'auth_token_leak', title: 'JWT Secret Invalidation / Auth Token Leak', service: 'auth-service', sev: 'SEV1', desc: 'Compromised token signature resulting in 401 unauthorized rejection loops.' },
  { id: 'circuit_breaker_cascade', title: 'Circuit Breaker Cascade Trip', service: 'api-gateway', sev: 'SEV1', desc: 'Cascading timeout tripping upstream circuit breakers across all gateways.' },
  { id: 'memory_leak_oom', title: 'Garbage Collection OOM Crash Loop', service: 'order-service', sev: 'SEV2', desc: 'Linear memory growth leading to SIGKILL OOMKilled pod restarts.' },
  { id: 'dns_resolution_failure', title: 'CoreDNS Upstream Resolution Failure', service: 'inventory-service', sev: 'SEV2', desc: 'Intermittent NXDOMAIN failures contacting warehouse database clusters.' },
  { id: 'stale_cache_invalidation', title: 'Stale Cache Stampede', service: 'order-service', sev: 'SEV2', desc: 'Missing cache lock causing thundering herd database overload.' },
  { id: 'slow_database_query', title: 'Missing Index Table Scan Slowdown', service: 'payment-service', sev: 'SEV3', desc: 'Unindexed sequential table scans triggering high p99 latency alerts.' },
  { id: 'ssl_certificate_expiry', title: 'TLS/SSL Handshake Certificate Expiry', service: 'api-gateway', sev: 'SEV1', desc: 'Expired edge TLS certificate halting all customer incoming traffic.' },
  { id: 'cpu_throttling_spike', title: 'K8s CFS Quota CPU Throttling', service: 'auth-service', sev: 'SEV3', desc: 'Aggressive CPU limit throttling during bursty authentication traffic.' },
];

class AppController {
  constructor() {
    this.currentIncident = null;
    this.incidents = [];
    this.pendingApprovals = [];

    this._initDomElements();
    this._initComponents();
    this._bindEvents();
  }

  _initDomElements() {
    this.el = {
      // Header Stats
      systemHealthText: document.getElementById('systemHealthText'),
      activeIncidentsCount: document.getElementById('activeIncidentsCount'),
      sseDot: document.getElementById('sseDot'),
      sseStatusText: document.getElementById('sseStatusText'),

      // Header Buttons
      btnSimulateScenario: document.getElementById('btnSimulateScenario'),
      btnNewIncident: document.getElementById('btnNewIncident'),

      // Incident Feed
      totalIncidentsBadge: document.getElementById('totalIncidentsBadge'),
      incidentSearchInput: document.getElementById('incidentSearchInput'),
      filterChips: document.getElementById('filterChips'),
      incidentListContainer: document.getElementById('incidentListContainer'),

      // War Room Header
      activeSevBadge: document.getElementById('activeSevBadge'),
      activeStageBadge: document.getElementById('activeStageBadge'),
      activeIncidentIdTag: document.getElementById('activeIncidentIdTag'),
      activeIncidentTime: document.getElementById('activeIncidentTime'),
      activeIncidentTitle: document.getElementById('activeIncidentTitle'),
      activeServicesList: document.getElementById('activeServicesList'),
      pipelineStepper: document.getElementById('pipelineStepper'),

      // Approval Banner
      approvalAlertBanner: document.getElementById('approvalAlertBanner'),
      approvalBannerTitle: document.getElementById('approvalBannerTitle'),
      approvalBannerDesc: document.getElementById('approvalBannerDesc'),
      btnReviewApproval: document.getElementById('btnReviewApproval'),

      // Tabs & Panes
      warroomTabs: document.getElementById('warroomTabs'),
      autoScrollToggle: document.getElementById('autoScrollToggle'),
      btnClearStream: document.getElementById('btnClearStream'),
      streamMessagesContainer: document.getElementById('streamMessagesContainer'),
      topologySvg: document.getElementById('topologySvg'),
      btnRefreshTopology: document.getElementById('btnRefreshTopology'),

      // Evidence Subtabs
      logsTerminal: document.getElementById('terminalLogsContent'),
      metricsGrid: document.getElementById('metricsGrid'),
      diffsContainer: document.getElementById('diffsContainer'),
      memoryGrid: document.getElementById('memoryGrid'),

      // RCA & Postmortem
      hypothesesContainer: document.getElementById('hypothesesContainer'),
      postmortemContent: document.getElementById('postmortemContent'),
      reportMetaStats: document.getElementById('reportMetaStats'),
      btnExportMarkdown: document.getElementById('btnExportMarkdown'),
      btnGenerateReportNow: document.getElementById('btnGenerateReportNow'),

      // Modals
      approvalModal: document.getElementById('approvalModal'),
      btnCloseApprovalModal: document.getElementById('btnCloseApprovalModal'),
      btnApproveAction: document.getElementById('btnApproveAction'),
      btnRejectAction: document.getElementById('btnRejectAction'),

      simulateModal: document.getElementById('simulateModal'),
      btnCloseSimulateModal: document.getElementById('btnCloseSimulateModal'),
      scenarioGrid: document.getElementById('scenarioGrid'),

      newIncidentModal: document.getElementById('newIncidentModal'),
      btnCloseNewIncidentModal: document.getElementById('btnCloseNewIncidentModal'),
      btnCancelNewIncident: document.getElementById('btnCancelNewIncident'),
      newIncidentForm: document.getElementById('newIncidentForm'),

      toastContainer: document.getElementById('toastContainer'),
    };
  }

  _initComponents() {
    // 1. Topology Visualizer
    this.topology = new ServiceTopologyGraph(this.el.topologySvg);
    this.topology.render();

    // 2. Incident Feed
    this.incidentList = new IncidentListComponent(
      this.el.incidentListContainer,
      (incidentId) => this.selectIncident(incidentId)
    );

    // 3. Agent Stream
    this.agentStream = new AgentStreamComponent(this.el.streamMessagesContainer);

    // 4. Evidence Viewer
    this.evidenceViewer = new EvidenceViewerComponent({
      logsContent: this.el.logsTerminal,
      metricsGrid: this.el.metricsGrid,
      diffsContainer: this.el.diffsContainer,
      memoryGrid: this.el.memoryGrid,
      counts: {
        logs: document.getElementById('logCount'),
        metrics: document.getElementById('metricCount'),
        diffs: document.getElementById('diffCount'),
        memory: document.getElementById('memoryCount'),
        total: document.getElementById('evidenceCountBadge'),
      },
    });

    // 5. RCA Cards
    this.rcaCards = new RcaCardsComponent(
      this.el.hypothesesContainer,
      document.getElementById('hypothesesCountBadge')
    );

    // 6. Approval Modal
    this.approvalModal = new ApprovalModalComponent({
      modalEl: this.el.approvalModal,
      closeBtn: this.el.btnCloseApprovalModal,
      approveBtn: this.el.btnApproveAction,
      rejectBtn: this.el.btnRejectAction,
      onDecision: (incId, apprId, payload) => this._handleApprovalDecision(incId, apprId, payload),
    });

    // 7. Postmortem Viewer
    this.postmortemViewer = new PostmortemViewerComponent({
      contentEl: this.el.postmortemContent,
      statsEl: this.el.reportMetaStats,
      onGenerateReport: () => this._generatePostmortem(),
    });
  }

  _bindEvents() {
    // SSE Status callback
    stream.onStatusChange((status) => {
      this.el.sseDot.className = `status-dot ${status === 'connected' ? 'connected' : 'disconnected'}`;
      this.el.sseStatusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    });

    // SSE Inbound Events
    stream.on('agent_thought', (payload) => {
      this.agentStream.addMessage({
        actor: payload.actor || 'Agent',
        stage: payload.stage,
        message: payload.thought || payload.message,
        metadata: payload,
      });
    });

    stream.on('stage_change', (payload) => {
      if (this.currentIncident && payload.new_stage) {
        this.currentIncident.stage = payload.new_stage;
        this._updateHeaderStage(payload.new_stage);
        this._updateStepper(payload.new_stage);
      }
    });

    stream.on('evidence_found', (payload) => {
      this.showToast(`New Evidence [${payload.source_type}]: ${payload.title || 'Anomaly identified'}`, 'info');
      this._reloadEvidence();
    });

    stream.on('approval_required', (payload) => {
      this.showToast(`Human Approval Required: ${payload.description || 'Remediation Action'}`, 'warning');
      this._checkApprovals();
    });

    stream.on('resolved', () => {
      this.showToast('Incident successfully remediated and verified!', 'success');
      this._reloadCurrentIncident();
      this._loadIncidents();
    });

    // Feed Search & Filter
    this.el.incidentSearchInput.addEventListener('input', (e) => {
      this.incidentList.setSearchQuery(e.target.value);
    });

    this.el.filterChips.querySelectorAll('.chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        this.el.filterChips.querySelectorAll('.chip').forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        this.incidentList.setFilter(chip.getAttribute('data-filter'));
      });
    });

    // Tabs Navigation
    this.el.warroomTabs.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        this._switchTab(tab);
      });
    });

    // Evidence Subtabs
    document.querySelectorAll('.subtab-btn').forEach((subBtn) => {
      subBtn.addEventListener('click', () => {
        document.querySelectorAll('.subtab-btn').forEach((b) => b.classList.remove('active'));
        document.querySelectorAll('.evidence-pane').forEach((p) => p.classList.remove('active'));

        subBtn.classList.add('active');
        const targetPane = document.getElementById(`subpane${subBtn.getAttribute('data-subtab').charAt(0).toUpperCase() + subBtn.getAttribute('data-subtab').slice(1)}`);
        if (targetPane) targetPane.classList.add('active');
      });
    });

    // Stream Controls
    this.el.autoScrollToggle.addEventListener('change', (e) => {
      this.agentStream.setAutoScroll(e.target.checked);
    });

    this.el.btnClearStream.addEventListener('click', () => {
      this.agentStream.clear();
    });

    this.el.btnRefreshTopology.addEventListener('click', () => {
      if (this.currentIncident) {
        this.topology.updateIncidentServices(this.currentIncident.affected_services);
      }
    });

    // Approval Review Button
    this.el.btnReviewApproval.addEventListener('click', () => {
      if (this.pendingApprovals.length > 0) {
        this.approvalModal.show(this.currentIncident.id, this.pendingApprovals[0]);
      }
    });

    // Postmortem Actions
    this.el.btnExportMarkdown.addEventListener('click', () => {
      this.postmortemViewer.exportMarkdown();
    });

    if (this.el.btnGenerateReportNow) {
      this.el.btnGenerateReportNow.addEventListener('click', () => this._generatePostmortem());
    }

    // Modal Triggers: Simulation
    this.el.btnSimulateScenario.addEventListener('click', () => this._showSimulateModal());
    this.el.btnCloseSimulateModal.addEventListener('click', () => {
      this.el.simulateModal.style.display = 'none';
    });

    // Modal Triggers: New Incident
    this.el.btnNewIncident.addEventListener('click', () => {
      this.el.newIncidentModal.style.display = 'flex';
    });
    this.el.btnCloseNewIncidentModal.addEventListener('click', () => {
      this.el.newIncidentModal.style.display = 'none';
    });
    this.el.btnCancelNewIncident.addEventListener('click', () => {
      this.el.newIncidentModal.style.display = 'none';
    });

    this.el.newIncidentForm.addEventListener('submit', (e) => this._handleNewIncidentSubmit(e));
  }

  _switchTab(tabName) {
    this.el.warroomTabs.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach((p) => p.classList.remove('active'));

    const activeBtn = this.el.warroomTabs.querySelector(`[data-tab="${tabName}"]`);
    const activePane = document.getElementById(`pane${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);

    if (activeBtn) activeBtn.classList.add('active');
    if (activePane) activePane.classList.add('active');

    // If switching to topology tab, trigger render
    if (tabName === 'topology') {
      this.topology.render();
    }
  }

  async init() {
    // 1. Initial Health Check
    this._checkHealth();
    setInterval(() => this._checkHealth(), 30000);

    // 2. Load Incidents
    await this._loadIncidents();

    // 3. Auto-select first incident or seed demo incident if none
    if (this.incidents.length > 0) {
      this.selectIncident(this.incidents[0].id);
    } else {
      // Auto-trigger the Redis Pool Exhaustion scenario as demonstration
      await this.simulateScenario('redis_pool_exhaustion');
    }
  }

  async _checkHealth() {
    try {
      const res = await api.getHealth();
      this.el.systemHealthText.textContent = res.status === 'ok' ? 'Operational' : 'Degraded';
    } catch (_) {
      this.el.systemHealthText.textContent = 'Offline';
    }
  }

  async _loadIncidents() {
    try {
      const res = await api.getIncidents({ limit: 100 });
      this.incidents = Array.isArray(res) ? res : (res.items || []);
      this.incidentList.setIncidents(this.incidents);
      this.el.totalIncidentsBadge.textContent = `${this.incidents.length} Total`;

      const activeCount = this.incidents.filter((i) => !i.is_resolved && i.stage !== 'RESOLVED').length;
      this.el.activeIncidentsCount.textContent = activeCount;
    } catch (err) {
      console.error('Failed to load incidents:', err);
    }
  }

  async selectIncident(incidentId) {
    try {
      const inc = await api.getIncident(incidentId);
      this.currentIncident = inc;
      this.incidentList.setActiveIncident(incidentId);

      // Update Header
      this.el.activeSevBadge.textContent = inc.severity;
      this.el.activeSevBadge.className = `badge ${inc.severity === 'SEV1' ? 'badge-sev1' : inc.severity === 'SEV2' ? 'badge-sev2' : 'badge-sev3'}`;
      this._updateHeaderStage(inc.stage);
      this.el.activeIncidentIdTag.textContent = inc.id;
      this.el.activeIncidentTitle.textContent = inc.title;

      // Affected services badges & Topology
      this.el.activeServicesList.innerHTML = (inc.affected_services || [])
        .map((s) => `<span class="service-tag">${s}</span>`)
        .join('');
      this.topology.updateIncidentServices(inc.affected_services || []);

      // Stepper
      this._updateStepper(inc.stage);

      // Timeline / Stream
      this.agentStream.setTimeline(inc.timeline || []);

      // Subscribe to real-time SSE stream
      stream.subscribe(inc.id);

      // Fetch Evidence, Hypotheses, Approvals, Report
      this._reloadEvidence();
      this._reloadHypotheses();
      this._checkApprovals();
      this._loadReport();
    } catch (err) {
      this.showToast(`Failed to load incident: ${err.message}`, 'error');
    }
  }

  _updateHeaderStage(stage) {
    this.el.activeStageBadge.textContent = stage;
  }

  _updateStepper(stage) {
    const stageOrder = ['CREATED', 'INVESTIGATING', 'HYPOTHESIZING', 'AWAITING_APPROVAL', 'REMEDIATING', 'VERIFYING', 'RESOLVED'];
    const currentIdx = stageOrder.indexOf(stage);

    this.el.pipelineStepper.querySelectorAll('.step-node').forEach((node) => {
      const nodeStage = node.getAttribute('data-stage');
      const nodeIdx = stageOrder.indexOf(nodeStage);

      node.classList.remove('active', 'completed');
      if (nodeIdx < currentIdx) {
        node.classList.add('completed');
      } else if (nodeIdx === currentIdx) {
        node.classList.add('active');
      }
    });
  }

  async _reloadEvidence() {
    if (!this.currentIncident) return;
    try {
      const res = await api.getEvidence(this.currentIncident.id);
      this.evidenceViewer.setEvidence(res.evidence || []);
    } catch (err) {
      console.warn('Failed to fetch evidence:', err);
    }
  }

  async _reloadHypotheses() {
    if (!this.currentIncident) return;
    try {
      const res = await api.getHypotheses(this.currentIncident.id);
      this.rcaCards.setHypotheses(res.hypotheses || []);
    } catch (err) {
      console.warn('Failed to fetch hypotheses:', err);
    }
  }

  async _checkApprovals() {
    if (!this.currentIncident) return;
    try {
      const res = await api.getApprovals(this.currentIncident.id);
      this.pendingApprovals = (res.approvals || []).filter((a) => a.status === 'PENDING');

      if (this.pendingApprovals.length > 0) {
        const top = this.pendingApprovals[0];
        this.el.approvalBannerTitle.textContent = `Remediation Approval Required: ${top.action_type} on ${top.target_service}`;
        this.el.approvalBannerDesc.textContent = top.description || 'Action paused due to high risk assessment.';
        this.el.approvalAlertBanner.style.display = 'flex';

        // Highlight blast radius on topology diagram
        this.topology.highlightBlastRadius(top.blast_radius || [top.target_service]);
      } else {
        this.el.approvalAlertBanner.style.display = 'none';
        this.topology.highlightBlastRadius([]);
      }
    } catch (err) {
      console.warn('Failed to check approvals:', err);
    }
  }

  async _loadReport() {
    if (!this.currentIncident) return;
    try {
      const res = await api.getReport(this.currentIncident.id);
      this.postmortemViewer.setReport(res);
    } catch (_) {
      this.postmortemViewer.setReport(null);
    }
  }

  async _generatePostmortem() {
    if (!this.currentIncident) return;
    try {
      const res = await api.generateReport(this.currentIncident.id);
      this.postmortemViewer.setReport(res);
      this.showToast('Postmortem report generated successfully.', 'success');
    } catch (err) {
      this.showToast(`Error generating report: ${err.message}`, 'error');
    }
  }

  async _handleApprovalDecision(incidentId, approvalId, payload) {
    try {
      await api.submitApproval(incidentId, approvalId, payload);
      this.showToast(`Action decision [${payload.decision}] registered. Pipeline resuming...`, 'success');
      this._checkApprovals();
      this._reloadCurrentIncident();
    } catch (err) {
      this.showToast(`Approval submission failed: ${err.message}`, 'error');
    }
  }

  async _reloadCurrentIncident() {
    if (this.currentIncident) {
      await this.selectIncident(this.currentIncident.id);
    }
  }

  _showSimulateModal() {
    this.el.scenarioGrid.innerHTML = SIMULATED_SCENARIOS.map((sc) => `
      <div class="scenario-card" data-id="${sc.id}">
        <div class="scenario-info">
          <h4>${sc.title}</h4>
          <p>${sc.desc}</p>
        </div>
        <div style="text-align: right; display: flex; flex-direction: column; gap: 4px; align-items: flex-end;">
          <span class="badge ${sc.sev === 'SEV1' ? 'badge-sev1' : sc.sev === 'SEV2' ? 'badge-sev2' : 'badge-sev3'}">${sc.sev}</span>
          <span class="service-pill">${sc.service}</span>
        </div>
      </div>
    `).join('');

    this.el.scenarioGrid.querySelectorAll('.scenario-card').forEach((card) => {
      card.addEventListener('click', () => {
        const scenarioId = card.getAttribute('data-id');
        this.el.simulateModal.style.display = 'none';
        this.simulateScenario(scenarioId);
      });
    });

    this.el.simulateModal.style.display = 'flex';
  }

  async simulateScenario(scenarioId) {
    const sc = SIMULATED_SCENARIOS.find((s) => s.id === scenarioId) || SIMULATED_SCENARIOS[0];
    this.showToast(`Simulating scenario: ${sc.title}...`, 'info');

    try {
      const inc = await api.createIncident({
        title: sc.title,
        severity: sc.sev,
        affected_services: [sc.service],
        symptoms: sc.desc,
      });

      this.showToast(`Incident [${inc.id}] initialized! Autonomous agents dispatched.`, 'success');
      await this._loadIncidents();
      await this.selectIncident(inc.id);
    } catch (err) {
      this.showToast(`Simulation failed: ${err.message}`, 'error');
    }
  }

  async _handleNewIncidentSubmit(e) {
    e.preventDefault();
    const title = document.getElementById('newIncTitle').value;
    const severity = document.getElementById('newIncSeverity').value;
    const service = document.getElementById('newIncService').value;
    const symptoms = document.getElementById('newIncSymptoms').value;

    try {
      const inc = await api.createIncident({
        title,
        severity,
        affected_services: [service],
        symptoms,
      });

      this.el.newIncidentModal.style.display = 'none';
      this.el.newIncidentForm.reset();
      this.showToast(`Incident [${inc.id}] dispatched successfully.`, 'success');
      await this._loadIncidents();
      await this.selectIncident(inc.id);
    } catch (err) {
      this.showToast(`Failed to dispatch incident: ${err.message}`, 'error');
    }
  }

  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    if (type === 'success') toast.style.borderColor = 'var(--success-emerald)';
    if (type === 'warning') toast.style.borderColor = 'var(--sev2-amber)';
    if (type === 'error') toast.style.borderColor = 'var(--sev1-crimson)';

    this.el.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}

// Instantiate and start app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new AppController();
  app.init();
});
