/**
 * OpsPilot AI — Interactive Microservice Topology Visualizer
 */

export class ServiceTopologyGraph {
  constructor(svgElement) {
    this.svg = svgElement;
    this.nodes = {
      'api-gateway': { x: 450, y: 75, name: 'api-gateway', status: 'healthy', tier: 'Edge API Gateway', port: ':8080' },
      'auth-service': { x: 220, y: 220, name: 'auth-service', status: 'healthy', tier: 'Auth & Session Tokens', port: ':8081' },
      'order-service': { x: 450, y: 235, name: 'order-service', status: 'healthy', tier: 'Core Order Orchestration', port: ':8082' },
      'payment-service': { x: 680, y: 220, name: 'payment-service', status: 'healthy', tier: 'Stripe/DB Transactions', port: ':8083' },
      'inventory-service': { x: 450, y: 405, name: 'inventory-service', status: 'healthy', tier: 'Warehouse Stock RPC', port: ':8084' },
    };

    this.edges = [
      { from: 'api-gateway', to: 'auth-service' },
      { from: 'api-gateway', to: 'order-service' },
      { from: 'order-service', to: 'payment-service' },
      { from: 'order-service', to: 'inventory-service' },
      { from: 'auth-service', to: 'payment-service' },
    ];

    this.blastRadius = new Set();
  }

  render() {
    if (!this.svg) return;

    // SVG Defs for Arrowheads & Gradients
    const defsHtml = `
      <defs>
        <marker id="arrow-default" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255, 255, 255, 0.3)" />
        </marker>
        <marker id="arrow-active" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#6366f1" />
        </marker>
        <marker id="arrow-critical" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#ff3366" />
        </marker>
      </defs>
    `;

    // Edges Rendering
    const edgesHtml = this.edges
      .map((edge) => {
        const u = this.nodes[edge.from];
        const v = this.nodes[edge.to];
        const isCritical = u.status === 'critical' || v.status === 'critical';
        const edgeClass = isCritical ? 'topo-edge critical-flow' : 'topo-edge active';
        const marker = isCritical ? 'url(#arrow-critical)' : 'url(#arrow-active)';

        // Curved Bézier path for aesthetic smoothness
        const dx = v.x - u.x;
        const dy = v.y - u.y;
        const cx = u.x + dx / 2;
        const cy = u.y + dy / 2 - 15;

        return `<path d="M ${u.x} ${u.y} Q ${cx} ${cy} ${v.x} ${v.y}" class="${edgeClass}" marker-end="${marker}" />`;
      })
      .join('');

    // Nodes Rendering (Width: 160, Height: 70)
    const nw = 160;
    const nh = 66;

    const nodesHtml = Object.values(this.nodes)
      .map((node) => {
        const x = node.x - nw / 2;
        const y = node.y - nh / 2;
        const isBlast = this.blastRadius.has(node.name);
        const blastClass = isBlast ? 'in-blast' : '';

        return `
          <g class="topo-node ${node.status} ${blastClass}" data-service="${node.name}" transform="translate(${x}, ${y})">
            <rect class="topo-node-rect" width="${nw}" height="${nh}" />
            <circle class="topo-node-status-circle" />
            <text class="topo-node-title" x="${nw / 2}" y="32">${node.name}</text>
            <text class="topo-node-meta" x="${nw / 2}" y="48">${node.tier} ${node.port}</text>
          </g>
        `;
      })
      .join('');

    this.svg.innerHTML = `${defsHtml}<g id="edgesGroup">${edgesHtml}</g><g id="nodesGroup">${nodesHtml}</g>`;
  }

  setServiceStatus(serviceName, status) {
    if (this.nodes[serviceName]) {
      this.nodes[serviceName].status = status;
      this.render();
    }
  }

  updateIncidentServices(affectedServices = []) {
    // Reset all to healthy first
    Object.keys(this.nodes).forEach((k) => (this.nodes[k].status = 'healthy'));

    // Mark affected as critical
    affectedServices.forEach((svc) => {
      if (this.nodes[svc]) {
        this.nodes[svc].status = 'critical';
      }
    });

    this.render();
  }

  highlightBlastRadius(serviceList = []) {
    this.blastRadius = new Set(serviceList);
    this.render();
  }

  reset() {
    Object.keys(this.nodes).forEach((k) => (this.nodes[k].status = 'healthy'));
    this.blastRadius.clear();
    this.render();
  }
}
