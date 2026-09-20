/**
 * OpsPilot AI — Incident Feed & List Component
 */

export class IncidentListComponent {
  constructor(containerElement, onSelectIncident) {
    this.container = containerElement;
    this.onSelectIncident = onSelectIncident;
    this.incidents = [];
    this.activeIncidentId = null;
    this.activeFilter = 'all';
    this.searchQuery = '';
  }

  setIncidents(incidents) {
    this.incidents = incidents || [];
    this.render();
  }

  setActiveIncident(incidentId) {
    this.activeIncidentId = incidentId;
    this.render();
  }

  setFilter(filter) {
    this.activeFilter = filter;
    this.render();
  }

  setSearchQuery(query) {
    this.searchQuery = (query || '').toLowerCase().trim();
    this.render();
  }

  _formatTimeAgo(isoString) {
    if (!isoString) return 'Just now';
    const date = new Date(isoString);
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);

    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    return `${diffHours}h ago`;
  }

  render() {
    if (!this.container) return;

    let filtered = this.incidents.filter((inc) => {
      // Filter tab
      if (this.activeFilter === 'SEV1' && inc.severity !== 'SEV1') return false;
      if (this.activeFilter === 'active' && (inc.is_resolved || inc.stage === 'RESOLVED')) return false;
      if (this.activeFilter === 'awaiting' && inc.stage !== 'AWAITING_APPROVAL') return false;
      if (this.activeFilter === 'RESOLVED' && !inc.is_resolved && inc.stage !== 'RESOLVED') return false;

      // Search query
      if (this.searchQuery) {
        const matchTitle = inc.title.toLowerCase().includes(this.searchQuery);
        const matchId = inc.id.toLowerCase().includes(this.searchQuery);
        const matchSvc = (inc.affected_services || []).some((s) => s.toLowerCase().includes(this.searchQuery));
        if (!matchTitle && !matchId && !matchSvc) return false;
      }

      return true;
    });

    if (filtered.length === 0) {
      this.container.innerHTML = `
        <div class="empty-feed">
          <p style="color: var(--text-muted); text-align: center; padding: 24px 12px; font-size: 13px;">
            No incidents match your filter.
          </p>
        </div>
      `;
      return;
    }

    this.container.innerHTML = filtered
      .map((inc) => {
        const isActive = inc.id === this.activeIncidentId ? 'active' : '';
        const sevBadgeClass = inc.severity === 'SEV1' ? 'badge-sev1' : inc.severity === 'SEV2' ? 'badge-sev2' : 'badge-sev3';
        const timeAgo = this._formatTimeAgo(inc.created_at);
        const servicesHtml = (inc.affected_services || [])
          .slice(0, 2)
          .map((s) => `<span class="service-pill">${s}</span>`)
          .join('');

        return `
          <div class="incident-card ${isActive}" data-id="${inc.id}">
            <div class="card-top">
              <span class="card-id">${inc.id}</span>
              <span class="badge ${sevBadgeClass}">${inc.severity}</span>
            </div>
            <div class="card-title">${inc.title}</div>
            <div class="card-meta">
              <div class="card-services">
                <span class="badge badge-stage">${inc.stage}</span>
                ${servicesHtml}
              </div>
              <span class="card-time">${timeAgo}</span>
            </div>
          </div>
        `;
      })
      .join('');

    // Attach click listeners
    this.container.querySelectorAll('.incident-card').forEach((card) => {
      card.addEventListener('click', () => {
        const incId = card.getAttribute('data-id');
        if (this.onSelectIncident) {
          this.onSelectIncident(incId);
        }
      });
    });
  }
}
