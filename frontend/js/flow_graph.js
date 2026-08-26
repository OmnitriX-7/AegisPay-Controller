/**
 * AegisPay-Controller: Visual Settlement Flow Graph
 * Interactive 4-source money flow visualization rendered in the proof drawer.
 */

const FlowGraph = {
  render(container, match) {
    if (!container || !match) return;

    const proof = match.proof || {};
    const gwCount = (match.gateway_events || []).length;
    const bank = (match.bank_records || [])[0] || {};

    const fmt = (v) => {
      if (!v && v !== 0) return '₹0';
      return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v);
    };

    container.innerHTML = `
      <div class="flow-graph-wrapper">
        <div class="flow-graph-row">
          <!-- Source: Customer -->
          <div class="fg-node fg-node-source">
            <div class="fg-node-icon">👤</div>
            <div class="fg-node-label">Customer</div>
            <div class="fg-node-amount">${fmt(proof.gross_sum)}</div>
            <div class="fg-node-sub">${gwCount} Order${gwCount > 1 ? 's' : ''}</div>
          </div>

          <div class="fg-edge">
            <div class="fg-edge-line"></div>
            <div class="fg-edge-label">Gross</div>
          </div>

          <!-- Node: Razorpay Gateway -->
          <div class="fg-node fg-node-gateway">
            <div class="fg-node-icon">⚡</div>
            <div class="fg-node-label">Razorpay</div>
            <div class="fg-node-deductions">
              <div>MDR: <strong>-${fmt(proof.mdr_total)}</strong></div>
              <div>GST: <strong>-${fmt(proof.gst_total)}</strong></div>
              ${proof.tds_total > 0 ? `<div>TDS: <strong>-${fmt(proof.tds_total)}</strong></div>` : ''}
              ${proof.refunds_total > 0 ? `<div style="color:var(--accent-crimson);">Ref: <strong>-${fmt(proof.refunds_total)}</strong></div>` : ''}
            </div>
          </div>

          <div class="fg-edge">
            <div class="fg-edge-line fg-edge-settlement"></div>
            <div class="fg-edge-label">Net</div>
          </div>

          <!-- Node: Bank Account -->
          <div class="fg-node fg-node-bank">
            <div class="fg-node-icon">🏦</div>
            <div class="fg-node-label">Bank Credit</div>
            <div class="fg-node-amount" style="color:var(--accent-emerald);">${fmt(proof.bank_credit)}</div>
            <div class="fg-node-sub">${bank.clearing_channel || 'NEFT'}</div>
          </div>

          <div class="fg-edge">
            <div class="fg-edge-line fg-edge-verified"></div>
            <div class="fg-edge-label">Balanced</div>
          </div>

          <!-- Node: ERP Ledger -->
          <div class="fg-node fg-node-erp">
            <div class="fg-node-icon">📒</div>
            <div class="fg-node-label">ERP Ledger</div>
            <div class="fg-node-amount" style="color:var(--accent-emerald);">Balanced</div>
            <div class="fg-node-sub">Drift: ₹${(proof.variance || 0).toFixed(4)}</div>
          </div>
        </div>
      </div>
    `;
  }
};

window.FlowGraph = FlowGraph;
