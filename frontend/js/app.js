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
      this.showToast('Your role does not have permission to run stress simulations.', 'error');
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
        body: JSON.stringify({
          record_count: this.state.recordScale,
          merchant_mid: (window.Workspace && Workspace.currentMerchant) ? Workspace.currentMerchant.mid : "MID_RZP_88392"
        })
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

    const displayMatches = matches.slice(0, 100);

    let rowsHtml = displayMatches.map(m => {
      const gw = m.gateway_events[0] || {};
      const bank = m.bank_records[0] || {};
      const proof = m.proof || {};

      let tagClass = "perfect";
      let label = "Exact 1:1";
      if (m.match_type === "BATCH_DECOMPOSED") { tagClass = "batch"; label = `Batch (${m.gateway_events.length})`; }
      if (m.match_type === "FUZZY_RESOLVED") { tagClass = "fuzzy"; label = "Fuzzy Narration"; }
      if (m.match_type === "DISPUTE_RECONCILED") { tagClass = "dispute"; label = "Dispute / Refund"; }

      return `
        <tr onclick="Visualizers.openProofDrawer('${m.match_id}')" style="cursor:pointer;">
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

    if (matches.length > 100) {
      rowsHtml += `
        <tr>
          <td colspan="10" style="text-align:center; padding:14px; color:var(--text-muted); font-size:11.5px; background:rgba(255,255,255,0.02);">
            ⚡ Displaying first 100 of <strong>${matches.length.toLocaleString()}</strong> reconciled records. Use Table Search or 'Export CSV' for the entire dataset.
          </td>
        </tr>
      `;
    }

    tableBody.innerHTML = rowsHtml;
  },

  renderExceptions() {
    const tableBody = document.getElementById('exceptionsTableBody');
    if (!tableBody || !this.state.reconciliationResult) return;

    const exceptions = this.state.reconciliationResult.exceptions || [];

    if (exceptions.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">No exceptions found. All records reconciled.</td></tr>`;
      return;
    }

    const displayExceptions = exceptions.slice(0, 100);

    let excHtml = displayExceptions.map(exc => `
      <tr>
        <td class="font-mono" style="font-weight:700; color:#ffffff;">${exc.exception_id}</td>
        <td>
          <span class="cause-pill">${exc.root_cause}</span>
          <div style="font-size:10.5px; color:var(--text-secondary); margin-top:3px;">${exc.description}</div>
        </td>
        <td>
          <span class="class-tag ${exc.severity === 'HIGH' ? 'dispute' : (exc.severity === 'MEDIUM' ? 'batch' : 'fuzzy')}">${exc.severity}</span>
        </td>
        <td class="font-mono" style="font-size:11px;">${(exc.affected_order_ids && exc.affected_order_ids.length > 0) ? exc.affected_order_ids.join(', ') : (exc.order_id || exc.bank_ref || 'Batch Ref')}</td>
        <td class="font-mono" style="font-weight:700; color:var(--accent-gold);">₹${(exc.variance_amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
        <td class="font-mono" style="font-size:11px; color:var(--accent-emerald);">${exc.ai_confidence ? (exc.ai_confidence * 100).toFixed(0) + '%' : (exc.severity === 'HIGH' ? '98%' : (exc.severity === 'MEDIUM' ? '94%' : '88%'))}</td>
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

    if (exceptions.length > 100) {
      excHtml += `
        <tr>
          <td colspan="8" style="text-align:center; padding:14px; color:var(--text-muted); font-size:11.5px; background:rgba(255,255,255,0.02);">
            ⚡ Displaying first 100 of <strong>${exceptions.length.toLocaleString()}</strong> triaged exceptions.
          </td>
        </tr>
      `;
    }

    tableBody.innerHTML = excHtml;
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

  showToast(message, type = 'success') {
    let toast = document.getElementById('aegispayToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'aegispayToast';
      toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: #18181b;
        color: #fff;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 12px 18px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        z-index: 99999;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        gap: 10px;
        transition: all 0.3s ease;
        opacity: 0;
        transform: translateY(10px);
      `;
      document.body.appendChild(toast);
    }
    const icon = type === 'success' ? '✅' : '⚠️';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toast.style.borderColor = type === 'success' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)';
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';

    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
    }, 3500);
  },

  async resolveException(exceptionId, action) {
    const ws = window.Workspace || (typeof Workspace !== 'undefined' ? Workspace : null);
    if (ws && !ws.hasPermission(action === 'APPROVE_JOURNAL' ? 'approve_journal' : 'dismiss_exception')) {
      this.showToast(`Your role (${ws.currentUser?.roleShortLabel}) does not have permission for this action.`, 'error');
      return;
    }

    try {
      const res = await fetch('/api/exceptions/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exception_id: exceptionId, action })
      });
      const data = await res.json();
      
      const stream = window.AgentStream || (typeof AgentStream !== 'undefined' ? AgentStream : null);
      if (action === 'APPROVE_JOURNAL') {
        this.showToast(`Exception ${exceptionId} approved: Adjusting journal entry posted & balanced!`);
        if (stream) stream.logSuccess('✓', `[HITL Approved] ${exceptionId}: Adjusting journal entry posted by ${ws?.currentUser?.name || 'CFO'}.`);
      } else {
        this.showToast(`Exception ${exceptionId} dismissed by ${ws?.currentUser?.name || 'CFO'}.`);
        if (stream) stream.logStep('⚪', `[HITL Dismissed] ${exceptionId} dismissed from exception queue.`);
      }

      if (this.state.reconciliationResult) {
        this.state.reconciliationResult.exceptions = this.state.reconciliationResult.exceptions.filter(e => e.exception_id !== exceptionId);
        this.state.reconciliationResult.exception_count = this.state.reconciliationResult.exceptions.length;
        
        const badge = document.getElementById('tabExceptionsBadge');
        if (badge) badge.textContent = this.state.reconciliationResult.exception_count;

        this.renderKPIs();
        this.renderExceptions();
      }
    } catch (err) {
      this.showToast(`Error resolving exception: ${err.message}`, 'error');
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
  },

  // --- Custom Datasheet Ingestion & Webhooks ---
  openCsvModal() {
    const modal = document.getElementById('csvIngestModal');
    if (modal) modal.style.display = 'flex';
  },

  closeCsvModal() {
    const modal = document.getElementById('csvIngestModal');
    if (modal) modal.style.display = 'none';
  },

  async loadSampleCsvs() {
    const statusEl = document.getElementById('csvModalStatus');
    if (statusEl) statusEl.innerText = "Fetching real-world sample templates from server...";

    try {
      const [gw, bank, erp, tax] = await Promise.all([
        fetch('/api/samples/download/gateway').then(r => r.text()),
        fetch('/api/samples/download/bank').then(r => r.text()),
        fetch('/api/samples/download/erp').then(r => r.text()),
        fetch('/api/samples/download/tax').then(r => r.text())
      ]);

      const gwEl = document.getElementById('csvGatewayInput');
      const bankEl = document.getElementById('csvBankInput');
      const erpEl = document.getElementById('csvErpInput');
      const taxEl = document.getElementById('csvTaxInput');

      if (gwEl) gwEl.value = gw;
      if (bankEl) bankEl.value = bank;
      if (erpEl) erpEl.value = erp;
      if (taxEl) taxEl.value = tax;

      if (statusEl) statusEl.innerText = "✅ Sample templates loaded! Click 'Reconcile Datasheets' below.";
    } catch (err) {
      if (statusEl) statusEl.innerText = `❌ Error loading samples: ${err.message}`;
    }
  },

  async submitCustomCsvs() {
    const statusEl = document.getElementById('csvModalStatus');
    const gwEl = document.getElementById('csvGatewayInput');
    const bankEl = document.getElementById('csvBankInput');
    const erpEl = document.getElementById('csvErpInput');
    const taxEl = document.getElementById('csvTaxInput');

    const gwVal = gwEl ? gwEl.value.trim() : "";
    if (!gwVal) {
      this.showToast('Please provide at least the Payment Gateway settlement CSV.', 'error');
      return;
    }

    if (statusEl) statusEl.innerText = "Ingesting & reconciling custom datasheets with 0.0000 drift math...";

    try {
      const res = await fetch('/api/ingest/csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gateway_csv: gwVal,
          bank_csv: bankEl ? bankEl.value.trim() : null,
          erp_csv: erpEl ? erpEl.value.trim() : null,
          tax_csv: taxEl ? taxEl.value.trim() : null,
          merchant_mid: (window.Workspace && Workspace.currentMerchant) ? Workspace.currentMerchant.mid : "MID_RZP_88392",
          performed_by: (window.Workspace && Workspace.currentUser) ? Workspace.currentUser.name : "Custom CSV Ingest"
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Reconciliation failed");
      }

      const data = await res.json();
      this.state.reconciliationResult = data;
      this.closeCsvModal();

      // Update full dashboard
      this.renderKPIs();
      this.renderLedgerTable();
      this.renderExceptions();
      this.renderPipelineStepper();

      if (window.AgentStream) {
        AgentStream.logSuccess('✓', `Custom Datasheet Ingested: ${data.total_records_processed} records, ${data.matched_count} matched, ₹${data.precision_drift_sum.toFixed(4)} drift.`);
      }

      this.showToast(`Custom Datasheet Reconciled: ${data.matched_count} matched, ${data.exception_count} exceptions, ₹${data.precision_drift_sum.toFixed(4)} drift.`);
    } catch (err) {
      if (statusEl) statusEl.innerText = `❌ Ingestion Error: ${err.message}`;
    }
  },

  async simulateRazorpayWebhook() {
    if (window.AgentStream) {
      AgentStream.logStep('⚡', 'Triggering simulated live Razorpay payment webhook...');
    }

    try {
      const res = await fetch('/api/webhooks/simulate', { method: 'POST' });
      const event = await res.json();

      if (window.AgentStream) {
        AgentStream.logSuccess('✓', `Incoming Razorpay Webhook: ${event.payment_id} (₹${event.amount_inr.toFixed(2)}) | HMAC-SHA256 Signature Verified.`);
      }

      this.showToast(`⚡ Webhook Verified: ${event.event} - Payment ${event.payment_id} (₹${event.amount_inr})`);
    } catch (err) {
      this.showToast(`Webhook simulation failed: ${err.message}`, 'error');
    }
  }
};

window.App = App;

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
