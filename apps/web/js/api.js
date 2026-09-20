/**
 * OpsPilot AI — Production REST API Client
 */

export class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  async _request(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        let errorDetail = `HTTP ${response.status} ${response.statusText}`;
        try {
          const body = await response.json();
          if (body.detail) errorDetail = body.detail;
        } catch (_) {}
        throw new Error(errorDetail);
      }
      return await response.json();
    } catch (err) {
      console.error(`API Error [${options.method || 'GET'} ${path}]:`, err);
      throw err;
    }
  }

  async getHealth() {
    return this._request('/health');
  }

  async getIncidents({ severity, stage, service, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams();
    if (severity) params.append('severity', severity);
    if (stage) params.append('stage', stage);
    if (service) params.append('service', service);
    params.append('limit', limit);
    params.append('offset', offset);
    return this._request(`/api/v1/incidents?${params.toString()}`);
  }

  async getIncident(incidentId) {
    return this._request(`/api/v1/incidents/${incidentId}`);
  }

  async createIncident({ title, severity = 'SEV1', affected_services = [], symptoms = '' }) {
    return this._request('/api/v1/incidents', {
      method: 'POST',
      body: JSON.stringify({
        title,
        severity,
        affected_services,
        symptoms,
        auto_remediate: false,
      }),
    });
  }

  async getEvidence(incidentId) {
    return this._request(`/api/v1/incidents/${incidentId}/evidence`);
  }

  async getHypotheses(incidentId) {
    return this._request(`/api/v1/incidents/${incidentId}/hypotheses`);
  }

  async getApprovals(incidentId) {
    return this._request(`/api/v1/incidents/${incidentId}/approvals`);
  }

  async submitApproval(incidentId, approvalId, { decision, approver_id = 'lead-sre@company.com', approver_role = 'OPERATOR', reason = '', modified_parameters = null }) {
    return this._request(`/api/v1/incidents/${incidentId}/approvals/${approvalId}`, {
      method: 'POST',
      body: JSON.stringify({
        decision,
        approver_id,
        approver_role,
        reason,
        modified_parameters,
      }),
    });
  }

  async getReport(incidentId) {
    return this._request(`/api/v1/incidents/${incidentId}/report`);
  }

  async generateReport(incidentId) {
    return this._request(`/api/v1/incidents/${incidentId}/report`, {
      method: 'POST',
    });
  }

  async triggerAlertWebhook(payload) {
    return this._request('/api/v1/webhooks/alerts', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
}

export const api = new ApiClient();
