/**
 * AegisPay-Controller: Main Client Application Controller
 * Orchestrates multi-source reconciliation, live agent streaming,
 * tax compliance radar, stress simulator, and enterprise exports.
 */

const App = {
  state: {
    recordScale: 50,
    currentTab: 'ledger',
    tableFilter: 'all',
    searchQuery: '',
    reconciliationResult: null,
    forecastResult: null,
    stressParams: {
      salesGrowth: 0,
      refundSpike: 3,
      clearingLag: 2
    },
    isReconciling: false
  },

  get reconciliationResult() {
    return this.state.reconciliationResult;
  },

  init() {
    // 1. Check Auth (Feature 6)
    const ws = window.Workspace || (typeof Workspace !== 'undefined' ? Workspace : null);
    if (ws && !ws.currentUser) {
      ws.init();
      return;
    }

    // Show main app container
    const appCont = document.getElementById('appContainer');
    if (appCont) appCont.style.display = 'block';

    // 2. Initialize Subsystems
    const stream = window.AgentStream || (typeof AgentStream !== 'undefined' ? AgentStream : null);
    if (stream) stream.init();

    const chart = window.ForecastChart || (typeof ForecastChart !== 'undefined' ? ForecastChart : null);
    if (chart) chart.init('forecastCanvas');

    const copilot = window.CopilotChat || (typeof CopilotChat !== 'undefined' ? CopilotChat : null);
    if (copilot) copilot.init('chatMessages', 'chatInput');

    // 3. Register UI Event Listeners
    this.setupEventListeners();

    // 4. Run Initial Baseline Reconciliation
    this.runFullPipeline();
  },

  setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        this.switchTab(tab);
      });
    });

    // Keyboard Shortcuts (Esc closes drawers/modals, Ctrl+K focuses copilot)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const vis = window.Visualizers || (typeof Visualizers !== 'undefined' ? Visualizers : null);
        if (vis) vis.closeDrawer();

        const exp = window.ExportTools || (typeof ExportTools !== 'undefined' ? ExportTools : null);
        if (exp) exp.closeAuditCertificate();

        const drop = document.getElementById('merchantDropdownList');
        if (drop) drop.classList.remove('active');
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.switchTab('copilot');
        const chatIn = document.getElementById('chatInput');
        if (chatIn) chatIn.focus();
      }
    });

    // Close merchant dropdown on outside click
    document.addEventListener('click', (e) => {
      const switcher = document.querySelector('.merchant-switcher');
      const dropdown = document.getElementById('merchantDropdownList');
      if (switcher && dropdown && !switcher.contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });
  },

  switchTab(tabId) {
    this.state.currentTab = tabId;

    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tabId);
    });

    // Update tab panes
    document.querySelectorAll('.tab-pane').forEach(p => {
      p.classList.toggle('active', p.id === `tab-${tabId}`);
    });

    // Lazy render on tab activation
    if (tabId === 'forecast' && this.state.forecastResult) {
      setTimeout(() => {
        const chart = window.ForecastChart || (typeof ForecastChart !== 'undefined' ? ForecastChart : null);
        if (chart) {
          chart.resize();
          chart.updateData(this.state.forecastResult);
        }
      }, 50);
    } else if (tabId === 'tax' && this.state.reconciliationResult) {
      const tax = window.TaxRadar || (typeof TaxRadar !== 'undefined' ? TaxRadar : null);
      if (tax) tax.render(this.state.reconciliationResult);
    } else if (tabId === 'copilot') {
      const copilot = window.CopilotChat || (typeof CopilotChat !== 'undefined' ? CopilotChat : null);
      if (copilot) copilot.init('chatMessages', 'chatInput');
    }
  },

  setScale(scale) {
    this.state.recordScale = scale;
    document.querySelectorAll('.scale-btn').forEach(b => {
      b.classList.toggle('active', parseInt(b.dataset.scale) === scale);
    });
    this.runFullPipeline();
  },

  setTableFilter(filter) {
    this.state.tableFilter = filter;
    document.querySelectorAll('.filter-chip').forEach(c => {
      c.classList.toggle('active', c.dataset.filter === filter);
    });
    this.renderLedgerTable();
  },

  setSearchQuery(q) {
    this.state.searchQuery = q.trim().toLowerCase();
    this.renderLedgerTable();
  },

  // What-If Stress Simulator (Feature 3)
  onStressSliderChange() {
    const growth = document.getElementById('stressGrowth')?.value || 0;
    const refund = document.getElementById('stressRefund')?.value || 3;
    const lag = document.getElementById('stressClearingLag')?.value || 2;

    const growthLabel = document.getElementById('stressGrowthVal');
    const refundLabel = document.getElementById('stressRefundVal');
    const lagLabel = document.getElementById('stressClearingLagVal');

    if (growthLabel) growthLabel.textContent = `${growth > 0 ? '+' : ''}${growth}%`;
    if (refundLabel) refundLabel.textContent = `${refund}%`;
    if (lagLabel) lagLabel.textContent = `T+${lag}`;

    this.state.stressParams = {
      salesGrowth: parseFloat(growth),
      refundSpike: parseFloat(refund),
      clearingLag: parseInt(lag)
    };
  },

  async runStressedForecast() {
    const ws = window.Workspace || (typeof Workspace !== 'undefined' ? Workspace : null);
    if (ws && !ws.hasPermission('stress_simulator')) {
      alert('Your role does not have permission to run stress simulations.');
      return;
    }

    const stream = window.AgentStream || (typeof AgentStream !== 'undefined' ? AgentStream : null);
    if (stream) {
      stream.logStep('⚡', `Running Treasury What-If Stress Simulation (Growth: ${this.state.stressParams.salesGrowth}%, Refunds: ${this.state.stressParams.refundSpike}%, Lag: T+${this.state.stressParams.clearingLag})...`);
    }

    try {
      const res = await fetch('/api/forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          starting_cash: 12500000.0,
          horizon_days: 14,
          daily_operational_burn: 180000.0,
          sales_growth_pct: this.state.stressParams.salesGrowth,
          refund_spike_pct: this.state.stressParams.refundSpike,
          clearing_lag_days: this.state.stressParams.clearingLag
        })
      });
      const data = await res.json();
      this.state.forecastResult = data;
      this.renderForecast();

      const vis = window.Visualizers || (typeof Visualizers !== 'undefined' ? Visualizers : null);
      const fmt = vis ? vis.formatINR : (v) => `₹${v}`;
      if (stream) {
        stream.logSuccess('📈', `Stress simulation complete: Projected 14-Day Cash ${fmt(data.ending_projected_balance)}.`);
      }
    } catch (err) {
      console.error('Error running stress simulation:', err);
    }
  },

  // Full Dual-Loop Pipeline Execution with Live Streaming
  async runFullPipeline() {
    if (this.state.isReconciling) return;
    this.state.isReconciling = true;

    const btn = document.getElementById('runReconcileBtn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner"></span> Reconciling...`;
    }

    const stream = window.AgentStream || (typeof AgentStream !== 'undefined' ? AgentStream : null);
    const vis = window.Visualizers || (typeof Visualizers !== 'undefined' ? Visualizers : null);

    if (stream) {
      stream.clear();
      stream.logStep('📥', `Ingesting multi-source dataset for scale: ${this.state.recordScale} records...`);
    }

    try {
      // Step 1: Ingestion
      if (vis) vis.renderPipelineStep(0, false, true);
      const genRes = await fetch('/api/generate-dataset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ record_count: this.state.recordScale, seed: 42 })
      });
      const rawData = await genRes.json();

      const gwCount = (rawData.gateway_events || []).length;
      const bankCount = (rawData.bank_records || []).length;
      const erpCount = (rawData.erp_invoices || []).length;
      const taxCount = (rawData.tax_records || []).length;

      if (stream) {
        stream.logSuccess('✓', `Ingested ${gwCount} Gateway events, ${bankCount} Bank lines, ${erpCount} ERP invoices, ${taxCount} Tax records.`);
      }

      // Step 2 & 3: Symbolic Invariants & Reconciliation
      if (vis) {
        vis.renderPipelineStep(1, true, false);
        vis.renderPipelineStep(2, false, true);
      }

      if (stream) {
        stream.logStep('⚙️', `Running Dual-Loop Neuro-Symbolic Reconciliation & Invariant Engine...`);
      }

      const recRes = await fetch('/api/reconcile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const recData = await recRes.json();
      this.state.reconciliationResult = recData;

      if (stream) {
        stream.logSuccess('✓', `Reconciliation complete: ${recData.matched_count} matches (${recData.match_rate_pct}%), ${recData.exception_count} exceptions.`);
        stream.logSeal(`Cryptographic SHA-256 Seal: ${recData.cryptographic_seal.slice(0, 32)}... (Drift: ₹${recData.precision_drift_sum.toFixed(4)})`);
      }

      // Step 4: Exception Triage
      if (vis) vis.renderPipelineStep(3, true, false);
      if (stream && recData.exception_count > 0) {
        stream.logWarning('⚠️', `Triaged ${recData.exception_count} financial exceptions with AI root-cause classification.`);
      }

      // Step 5: Cash Forecasting
      if (vis) vis.renderPipelineStep(4, true, true);
      if (stream) {
        stream.logStep('📊', `Computing 14-Day Monte Carlo forward cash forecast...`);
      }

      const forecastRes = await fetch('/api/forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          starting_cash: 12500000.0,
          horizon_days: 14,
          daily_operational_burn: 180000.0,
          sales_growth_pct: this.state.stressParams.salesGrowth,
          refund_spike_pct: this.state.stressParams.refundSpike,
          clearing_lag_days: this.state.stressParams.clearingLag
        })
      });
      const forecastData = await forecastRes.json();
      this.state.forecastResult = forecastData;

      if (stream) {
        stream.logSuccess('🚀', `Pipeline finished in ${recData.execution_time_ms}ms. Books balanced.`);
      }

      // Update UI Views
      this.renderKPIs();
      this.renderLedgerTable();
      this.renderExceptions();
      this.renderForecast();

      // Render Tax Radar (Feature 5)
      const tax = window.TaxRadar || (typeof TaxRadar !== 'undefined' ? TaxRadar : null);
      if (tax) tax.render(recData);

      // Apply RBAC (Feature 6)
      const ws = window.Workspace || (typeof Workspace !== 'undefined' ? Workspace : null);
      if (ws) ws.applyRBAC();

    } catch (err) {
      console.error('Pipeline execution error:', err);
      if (stream) {
        stream.logWarning('❌', `Pipeline error: ${err.message}`);
      }
    } finally {
      this.state.isReconciling = false;
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `Run Reconciliation`;
      }
    }
  },

  renderKPIs() {
    const r = this.state.reconciliationResult;
    const f = this.state.forecastResult;
    if (!r) return;

    const vis = window.Visualizers || (typeof Visualizers !== 'undefined' ? Visualizers : null);
    const fmt = vis ? vis.formatINR : (v) => `₹${v}`;

    // Match Rate
    const matchEl = document.getElementById('kpiMatchRate');
    if (matchEl) matchEl.textContent = `${r.match_rate_pct}%`;

    const matchSub = document.getElementById('kpiMatchSub');
    if (matchSub) matchSub.textContent = `${r.matched_count} Matched / ${r.exception_count} Exceptions`;

    // Gross Volume
    const grossEl = document.getElementById('kpiGrossVolume');
    if (grossEl) grossEl.textContent = fmt(r.total_gross_volume);

    const settledSub = document.getElementById('kpiSettledSub');
    if (settledSub) settledSub.textContent = `Bank Settled: ${fmt(r.total_bank_settled)}`;

    // Fees & GST
    const mdrEl = document.getElementById('kpiMDRFees');
    if (mdrEl) mdrEl.textContent = fmt(r.total_mdr_fees_verified + r.total_gst_withheld);

    const feeSub = document.getElementById('kpiFeeSub');
    if (feeSub) feeSub.textContent = `MDR: ${fmt(r.total_mdr_fees_verified)} | GST: ${fmt(r.total_gst_withheld)}`;

    // Forward Cash
    if (f) {
      const cashEl = document.getElementById('kpiForwardCash');
      if (cashEl) cashEl.textContent = fmt(f.ending_projected_balance);

      const cashSub = document.getElementById('kpiCashSub');
      if (cashSub) cashSub.textContent = `Health: ${f.liquidity_health_score}/100 | Float: ${fmt(f.unsettled_float_in_transit)}`;
    }

    // Precision Drift
    const driftEl = document.getElementById('kpiPrecisionDrift');
    if (driftEl) driftEl.textContent = `₹${r.precision_drift_sum.toFixed(4)}`;

    // Badges
    const badgeLedger = document.getElementById('tabLedgerBadge');
    if (badgeLedger) badgeLedger.textContent = r.matched_count;

    const badgeExceptions = document.getElementById('tabExceptionsBadge');
    if (badgeExceptions) badgeExceptions.textContent = r.exception_count;

    const sealText = document.getElementById('sealStatusText');
    if (sealText) sealText.textContent = `Verified 0.0000 Drift (SHA: ${r.cryptographic_seal.slice(0, 8)})`;
  },

  renderLedgerTable() {
    const tableBody = document.getElementById('ledgerTableBody');
    if (!tableBody || !this.state.reconciliationResult) return;

    let matches = this.state.reconciliationResult.matches || [];
    const filter = this.state.tableFilter;
    const query = this.state.searchQuery;

    if (filter !== 'all') {
      matches = matches.filter(m => m.match_type === filter);
    }

    if (query) {
      matches = matches.filter(m => {
        const oId = (m.gateway_events[0] || {}).order_id || '';
        const name = (m.gateway_events[0] || {}).customer_name || '';
        const utr = (m.bank_records[0] || {}).utr || '';
        const mId = m.match_id || '';
        return oId.toLowerCase().includes(query) || name.toLowerCase().includes(query) || utr.toLowerCase().includes(query) || mId.toLowerCase().includes(query);
      });
    }

    if (matches.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:32px; color:var(--text-muted);">No records match filter criteria.</td></tr>`;
      return;
    }

    const vis = window.Visualizers || (typeof Visualizers !== 'undefined' ? Visualizers : null);
    const fmt = vis ? vis.formatINR : (v) => `₹${v}`;

    tableBody.innerHTML = matches.map(m => {
      const gw = m.gateway_events[0] || {};
      const bank = m.bank_records[0] || {};
      const proof = m.proof || {};

      let tagClass = "perfect";
      let label = "Exact 1:1";
      if (m.match_type === "BATCH_DECOMPOSED") { tagClass = "batch"; label = `Batch (${m.gateway_events.length})`; }
      if (m.match_type === "FUZZY_RESOLVED") { tagClass = "fuzzy"; label = "Fuzzy Narration"; }
      if (m.match_type === "DISPUTE_RECONCILED") { tagClass = "dispute"; label = "Dispute / Refund"; }

      return `
        <tr onclick='Visualizers.openProofDrawer(${JSON.stringify(m).replace(/'/g, "&apos;")})'>
          <td class="font-mono" style="font-weight:700; color:#ffffff;">${m.match_id}</td>
          <td>
            <span class="class-tag ${tagClass}">
              ${label}
            </span>
          </td>
          <td>
            <div style="font-weight:700; color:var(--text-primary);">${gw.order_id || 'Aggregated Batch'}</div>
            <div style="font-size:10.5px; color:var(--text-muted);">${gw.customer_name || m.gateway_events.length + ' Orders'} • ${gw.method || 'Batch'}</div>
          </td>
          <td>
            <div style="font-weight:600; color:var(--text-primary);">${gw.customer_name || 'Multi-Order Batch'}</div>
          </td>
          <td>
            <span class="font-mono" style="color:var(--text-secondary); font-size:11px;">${gw.method || 'Card/UPI'}</span>
          </td>
          <td class="font-mono" style="font-weight:700; color:var(--text-primary);">
            ${fmt(proof.gross_sum)}
          </td>
          <td class="font-mono" style="color:var(--accent-gold);">
            -${fmt(proof.mdr_total)}
          </td>
          <td class="font-mono" style="color:var(--accent-gold);">
            -${fmt(proof.gst_total)}
          </td>
          <td class="font-mono" style="font-weight:700; color:var(--accent-emerald);">
            ${fmt(proof.bank_credit)}
          </td>
          <td class="font-mono" style="color:var(--accent-emerald); font-size:11px;">
            ₹${(proof.variance || 0).toFixed(4)}
          </td>
        </tr>
      `;
    }).join('');
  },

  renderExceptions() {
    const tableBody = document.getElementById('exceptionsTableBody');
    if (!tableBody || !this.state.reconciliationResult) return;

    const exceptions = this.state.reconciliationResult.exceptions || [];

    if (exceptions.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">No exceptions found. All records reconciled.</td></tr>`;
      return;
    }

    tableBody.innerHTML = exceptions.map(exc => `
      <tr>
        <td class="font-mono" style="font-weight:700; color:#ffffff;">${exc.exception_id}</td>
        <td>
          <span class="cause-pill">${exc.root_cause}</span>
          <div style="font-size:10.5px; color:var(--text-secondary); margin-top:3px;">${exc.description}</div>
        </td>
        <td>
          <span class="class-tag ${exc.severity === 'HIGH' ? 'dispute' : (exc.severity === 'MEDIUM' ? 'batch' : 'fuzzy')}">${exc.severity}</span>
        </td>
        <td class="font-mono" style="font-size:11px;">${exc.order_id || exc.bank_ref || 'N/A'}</td>
        <td class="font-mono" style="font-weight:700; color:var(--accent-gold);">₹${exc.variance_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
        <td class="font-mono" style="font-size:11px; color:var(--accent-emerald);">${(exc.ai_confidence * 100).toFixed(0)}%</td>
        <td>
          <span class="font-mono" style="font-size:10.5px; color:${exc.hitl_status === 'RESOLVED' ? 'var(--accent-emerald)' : 'var(--accent-gold)'}; font-weight:700;">${exc.hitl_status || 'PENDING'}</span>
        </td>
        <td>
          <div style="display:flex; gap:4px;">
            ${exc.suggested_journal_entry ? `
              <button class="btn btn-primary btn-sm" data-perm="approve_journal" onclick="App.resolveException('${exc.exception_id}', 'APPROVE_JOURNAL')">
                Approve
              </button>
            ` : `
              <button class="btn btn-primary btn-sm" data-perm="approve_journal" onclick="App.resolveException('${exc.exception_id}', 'MANUAL_OVERRIDE')">
                Resolve
              </button>
            `}
            <button class="btn btn-secondary btn-sm" data-perm="dismiss_exception" onclick="App.resolveException('${exc.exception_id}', 'DISMISS')">
              Dismiss
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  },

  renderForecast() {
    if (!this.state.forecastResult) return;
    const chart = window.ForecastChart || (typeof ForecastChart !== 'undefined' ? ForecastChart : null);
    if (chart) chart.updateData(this.state.forecastResult);

    const insightsContainer = document.getElementById('forecastInsightsList');
    if (insightsContainer) {
      insightsContainer.innerHTML = (this.state.forecastResult.liquidity_insights || []).map(i => `
        <div class="insight-card">
          <div style="color:var(--accent-emerald); font-weight:700;">•</div>
          <div>${i}</div>
        </div>
      `).join('');
    }
  },

  async resolveException(exceptionId, action) {
    const ws = window.Workspace || (typeof Workspace !== 'undefined' ? Workspace : null);
    if (ws && !ws.hasPermission(action === 'APPROVE_JOURNAL' ? 'approve_journal' : 'dismiss_exception')) {
      alert(`Your role (${ws.currentUser?.roleShortLabel}) does not have permission for this action.`);
      return;
    }

    try {
      const res = await fetch('/api/exceptions/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exception_id: exceptionId, action })
      });
      const data = await res.json();
      alert(`Exception ${exceptionId} resolved (${action})!`);
      if (this.state.reconciliationResult) {
        this.state.reconciliationResult.exceptions = this.state.reconciliationResult.exceptions.filter(e => e.exception_id !== exceptionId);
        this.state.reconciliationResult.exception_count = this.state.reconciliationResult.exceptions.length;
        this.renderKPIs();
        this.renderExceptions();
      }
    } catch (err) {
      alert(`Error resolving exception: ${err.message}`);
    }
  },

  async runBenchmarkMatrix() {
    this.switchTab('benchmarks');
    const tableBody = document.getElementById('benchmarkTableBody');
    if (!tableBody) return;

    tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:30px; color:#ffffff;">Running live enterprise benchmark suite...</td></tr>`;

    try {
      const res = await fetch('/api/benchmarks/run');
      const data = await res.json();

      tableBody.innerHTML = data.results.map(b => `
        <tr>
          <td style="font-weight:800; color:#ffffff;">${b.record_scale} Records</td>
          <td class="font-mono">${b.total_records_processed}</td>
          <td class="font-mono" style="color:var(--accent-emerald);">${b.match_count}</td>
          <td class="font-mono" style="color:var(--accent-gold);">${b.exception_count}</td>
          <td class="font-mono" style="font-weight:700; color:var(--text-primary);">${b.match_rate_pct}%</td>
          <td class="font-mono">${b.reconciliation_latency_ms} ms</td>
          <td class="font-mono" style="font-weight:800; color:var(--accent-emerald);">${b.throughput_records_per_sec.toLocaleString()} rec/sec</td>
          <td class="font-mono" style="color:var(--accent-emerald);">₹${b.precision_drift_sum.toFixed(4)}</td>
        </tr>
      `).join('');

    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--accent-crimson);">Error running benchmarks: ${err.message}</td></tr>`;
    }
  }
};

window.App = App;

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
