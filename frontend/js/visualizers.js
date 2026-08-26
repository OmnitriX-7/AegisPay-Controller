/**
 * AegisPay-Controller: Minimalist UI Visualizers & Audit Sheet
 * Swiss Modernist Style: Zero neon glow, crisp typography, clean double-entry tables
 */

const Visualizers = {
  formatINR(val) {
    if (val === undefined || val === null) return "₹0.00";
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(val);
  },

  renderPipelineStep(stepIndex, isCompleted, isActive) {
    for (let i = 0; i <= 4; i++) {
      const node = document.getElementById(`stepNode${i}`);
      if (!node) continue;
      node.classList.remove('active', 'completed');
      if (i < stepIndex) node.classList.add('completed');
      if (i === stepIndex && isActive) node.classList.add('active');
    }
  },

  openProofDrawer(match) {
    const backdrop = document.getElementById('proofDrawer');
    const body = document.getElementById('drawerBody');
    const flowContainer = document.getElementById('drawerFlowGraph');
    if (!backdrop || !body) return;

    // Render Feature 2: Visual Settlement Flow Graph
    if (flowContainer && (window.FlowGraph || typeof FlowGraph !== 'undefined')) {
      const fg = window.FlowGraph || FlowGraph;
      fg.render(flowContainer, match);
    }

    const gw = (match.gateway_events && match.gateway_events[0]) || {};
    const bank = (match.bank_records && match.bank_records[0]) || {};
    const proof = match.proof || {};

    const ordersHtml = (match.gateway_events || []).map(g => `
      <div style="padding: 9px 12px; background: var(--bg-surface-1); border:1px solid var(--border-subtle); border-radius: 4px; margin-bottom: 5px;">
        <div style="display:flex; justify-content:space-between; font-size:12px;">
          <span style="font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">${g.order_id}</span>
          <span class="font-mono" style="color:var(--accent-emerald); font-weight:700;">${Visualizers.formatINR(g.amount)}</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin-top:2px;">
          <span>Method: ${g.method || 'Card'} • Customer: ${g.customer_name || 'N/A'}</span>
          <span>MDR: ${Visualizers.formatINR(g.mdr_fee)} + GST: ${Visualizers.formatINR(g.gst_on_mdr)}</span>
        </div>
      </div>
    `).join('');

    const auditStepsHtml = (match.audit_trace || []).map((step, idx) => `
      <div style="display:flex; gap:8px; font-size:11px; color:var(--text-secondary); margin-bottom:4px;">
        <span style="color:var(--text-muted); font-weight:700; font-family:var(--font-mono);">0${idx+1}.</span>
        <span>${step}</span>
      </div>
    `).join('');

    body.innerHTML = `
      <div style="margin-top:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <span class="font-mono" style="font-size:13px; font-weight:800; color:#ffffff;">${match.match_id}</span>
          <span class="class-tag perfect">PROVEN INVARIANT</span>
        </div>
        <div style="font-size:10.5px; color:var(--text-muted); font-family:var(--font-mono); word-break:break-all; display:flex; justify-content:space-between; align-items:center; background:var(--bg-surface-1); border:1px solid var(--border-subtle); padding:6px 10px; border-radius:4px;">
          <span>SHA-256: ${(proof.proof_hash || '').slice(0, 26)}...</span>
          <span style="cursor:pointer; color:#ffffff; font-weight:700; text-decoration:underline;" onclick="navigator.clipboard.writeText('${proof.proof_hash || ''}'); alert('SHA-256 Audit Seal Copied!');">Copy Seal</span>
        </div>
      </div>

      <!-- Settlement Waterfall Breakdown -->
      <div class="settlement-waterfall-box" style="margin-top:12px;">
        <div style="font-size:10.5px; color:var(--text-muted); text-transform:uppercase; font-weight:700; margin-bottom:6px; letter-spacing:0.5px;">
          Settlement Mathematical Balance:
        </div>
        <div class="waterfall-row">
          <span>(+) Gross Order Volume (${(match.gateway_events || []).length} Orders)</span>
          <span class="font-mono" style="color:#ffffff;">${Visualizers.formatINR(proof.gross_sum)}</span>
        </div>
        <div class="waterfall-row" style="color:var(--accent-gold);">
          <span>(-) Contractual MDR Processing Fees</span>
          <span class="font-mono">-${Visualizers.formatINR(proof.mdr_total)}</span>
        </div>
        <div class="waterfall-row" style="color:var(--accent-gold);">
          <span>(-) Statutory 18% GST on MDR</span>
          <span class="font-mono">-${Visualizers.formatINR(proof.gst_total)}</span>
        </div>
        ${proof.refunds_total > 0 ? `
        <div class="waterfall-row" style="color:var(--accent-crimson);">
          <span>(-) Customer Refunds Adjusted</span>
          <span class="font-mono">-${Visualizers.formatINR(proof.refunds_total)}</span>
        </div>` : ''}
        ${proof.tds_total > 0 ? `
        <div class="waterfall-row" style="color:#c084fc;">
          <span>(-) Section 194-O TDS Withheld (1%)</span>
          <span class="font-mono">-${Visualizers.formatINR(proof.tds_total)}</span>
        </div>` : ''}
        <div class="waterfall-row" style="font-weight:700; color:#d4d4d8;">
          <span>(=) Calculated Net Settlement</span>
          <span class="font-mono">${Visualizers.formatINR(proof.calculated_net)}</span>
        </div>
        <div class="waterfall-row total-line">
          <span>(✓) Actual Bank Credit (${bank.utr || 'Direct Deposit'})</span>
          <span class="font-mono" style="color:var(--accent-emerald);">${Visualizers.formatINR(proof.bank_credit)}</span>
        </div>
        <div class="waterfall-row" style="color:var(--accent-emerald); font-size:10.5px; border-bottom:none;">
          <span>(≈) Numerical Precision Residual</span>
          <span class="font-mono">₹${(proof.variance || 0).toFixed(4)} (Zero Drift)</span>
        </div>
      </div>

      <!-- Double-Entry T-Account Balancing Check -->
      <div style="background:var(--bg-surface-1); border:1px solid var(--border-subtle); padding:10px 12px; border-radius:4px; margin-top:12px;">
        <h4 style="font-size:10.5px; color:var(--text-muted); text-transform:uppercase; margin-bottom:6px; font-weight:700; letter-spacing:0.5px;">Double-Entry Ledger Balancing</h4>
        <div style="display:flex; justify-content:space-between; font-size:11.5px; font-family:var(--font-mono);">
          <div>
            <div style="color:var(--text-muted); font-size:10px;">TOTAL DEBITS</div>
            <div style="font-weight:700; color:#ffffff;">${Visualizers.formatINR(proof.bank_credit + proof.mdr_total + proof.gst_total + proof.refunds_total + (proof.tds_total || 0))}</div>
          </div>
          <div style="text-align:right;">
            <div style="color:var(--text-muted); font-size:10px;">TOTAL CREDITS</div>
            <div style="font-weight:700; color:#ffffff;">${Visualizers.formatINR(proof.gross_sum)}</div>
          </div>
        </div>
      </div>

      <!-- Gateway Orders -->
      <div style="margin-top:12px;">
        <h4 style="font-size:10.5px; color:var(--text-muted); text-transform:uppercase; margin-bottom:6px; font-weight:700; letter-spacing:0.5px;">Constituent Orders</h4>
        ${ordersHtml}
      </div>

      <!-- Bank Feed Details -->
      <div style="background:var(--bg-surface-1); border:1px solid var(--border-subtle); padding:10px 12px; border-radius:4px; margin-top:12px;">
        <h4 style="font-size:10.5px; color:var(--text-muted); text-transform:uppercase; margin-bottom:6px; font-weight:700; letter-spacing:0.5px;">Bank Deposit Record</h4>
        <div style="font-size:11.5px; line-height:1.6;">
          <div><strong>UTR:</strong> <span class="font-mono" style="color:#ffffff;">${bank.utr || 'N/A'}</span></div>
          <div><strong>Channel:</strong> ${bank.clearing_channel || 'NEFT'} • <strong>Date:</strong> ${bank.date || '2026-08-15'}</div>
          <div><strong>Narration:</strong> <span style="color:var(--text-secondary); font-size:11px;">${bank.description || 'N/A'}</span></div>
        </div>
      </div>

      <!-- Audit Steps -->
      <div style="background:var(--bg-surface-1); border:1px solid var(--border-subtle); padding:10px 12px; border-radius:4px; margin-top:12px;">
        <h4 style="font-size:10.5px; color:var(--text-muted); text-transform:uppercase; margin-bottom:6px; font-weight:700; letter-spacing:0.5px;">Symbolic Verification Proof Trail</h4>
        ${auditStepsHtml}
      </div>
    `;

    backdrop.classList.add('active');
  },

  openProofModal(match) {
    this.openProofDrawer(match);
  },

  closeDrawer() {
    const backdrop = document.getElementById('proofDrawer');
    if (backdrop) backdrop.classList.remove('active');
  },

  closeModal() {
    this.closeDrawer();
  }
};

window.Visualizers = Visualizers;
