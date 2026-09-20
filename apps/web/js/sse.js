/**
 * OpsPilot AI — Resilient Server-Sent Events (SSE) Stream Consumer
 */

export class StreamConsumer {
  constructor() {
    this.eventSource = null;
    this.currentIncidentId = null;
    this.listeners = new Map();
    this.reconnectTimeout = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.statusCallback = null;
  }

  onStatusChange(callback) {
    this.statusCallback = callback;
  }

  _setStatus(status) {
    if (this.statusCallback) {
      this.statusCallback(status);
    }
  }

  subscribe(incidentId) {
    if (this.currentIncidentId === incidentId && this.eventSource) {
      return; // Already streaming this incident
    }

    this.disconnect();
    this.currentIncidentId = incidentId;
    this.reconnectAttempts = 0;
    this._connect();
  }

  _connect() {
    if (!this.currentIncidentId) return;

    const streamUrl = `/api/v1/incidents/${this.currentIncidentId}/stream`;
    this._setStatus('connecting');

    try {
      this.eventSource = new EventSource(streamUrl);

      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this._setStatus('connected');
      };

      this.eventSource.onmessage = (event) => {
        this._handleMessage(event);
      };

      this.eventSource.onerror = () => {
        this._setStatus('disconnected');
        this.eventSource.close();
        this.eventSource = null;
        this._scheduleReconnect();
      };
    } catch (err) {
      console.error('SSE initialization error:', err);
      this._setStatus('disconnected');
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('Max SSE reconnect attempts reached.');
      this._setStatus('failed');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 15000);
    clearTimeout(this.reconnectTimeout);
    this.reconnectTimeout = setTimeout(() => {
      if (this.currentIncidentId) {
        this._connect();
      }
    }, delay);
  }

  _handleMessage(event) {
    if (!event.data) return;

    try {
      const data = JSON.parse(event.data);
      const eventType = data.event_type || 'message';

      // Dispatch to specific listeners
      const callbacks = this.listeners.get(eventType) || [];
      callbacks.forEach((cb) => cb(data.payload, data));

      // Also dispatch wildcard listener
      const wildcards = this.listeners.get('*') || [];
      wildcards.forEach((cb) => cb(eventType, data.payload, data));
    } catch (err) {
      console.error('Failed to parse SSE event data:', err, event.data);
    }
  }

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
  }

  disconnect() {
    clearTimeout(this.reconnectTimeout);
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.currentIncidentId = null;
    this._setStatus('disconnected');
  }
}

export const stream = new StreamConsumer();
