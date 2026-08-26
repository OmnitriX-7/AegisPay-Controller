/**
 * AegisPay-Controller: Multi-Merchant Workspace, Login & Registration
 * Supports Sign In, New Merchant Registration, and RBAC Persona switching.
 */

const Workspace = {
  currentUser: null,
  currentMerchant: null,
  currentAuthTab: 'signin',

  merchants: [
    {
      mid: 'MID_RZP_88392',
      name: 'Acme Retail Electronics Pvt Ltd',
      type: 'High-Volume UPI & Domestic Cards',
      gstin: '27AABCA1234F1Z5',
      defaultScale: 50
    },
    {
      mid: 'MID_RZP_44019',
      name: 'Zenith D2C Fashion Store',
      type: 'High Refund Rate (D2C Fashion)',
      gstin: '29AABCZ5678G2H7',
      defaultScale: 200
    },
    {
      mid: 'MID_RZP_71005',
      name: 'CloudSync Global SaaS',
      type: 'International Cards & Amex',
      gstin: '06AABCC9012J3K1',
      defaultScale: 100
    }
  ],

  roles: {
    cfo: {
      label: 'Chief Financial Officer',
      shortLabel: 'CFO',
      permissions: ['approve_journal', 'dismiss_exception', 'export_csv', 'export_json', 'audit_certificate', 'stress_simulator', 'view_tax_radar', 'run_benchmarks', 'copilot_query'],
      color: '#f59e0b'
    },
    finops: {
      label: 'FinOps Analyst',
      shortLabel: 'FinOps',
      permissions: ['dismiss_exception', 'export_csv', 'export_json', 'copilot_query', 'view_tax_radar'],
      color: '#3b82f6'
    },
    auditor: {
      label: 'External Auditor (Read-Only)',
      shortLabel: 'Auditor',
      permissions: ['audit_certificate', 'view_tax_radar'],
      color: '#10b981'
    }
  },

  demoCredentials: {
    cfo: { email: 'cfo@acme-retail.com', password: 'demo2026', name: 'Priya Sharma' },
    finops: { email: 'ops@acme-retail.com', password: 'demo2026', name: 'Arjun Mehta' },
    auditor: { email: 'audit@pwc-india.com', password: 'demo2026', name: 'Deepak Verma' }
  },

  init() {
    const saved = localStorage.getItem('aegispay_session');
    if (saved) {
      try {
        const session = JSON.parse(saved);
        this.currentUser = session.user;
        this.currentMerchant = session.merchant;
        if (session.customMerchants && Array.isArray(session.customMerchants)) {
          this.merchants = [...this.merchants, ...session.customMerchants];
        }
        this.onAuthSuccess();
        return;
      } catch (e) { /* fall through to login */ }
    }
    this.showLoginModal();
  },

  switchAuthTab(tab) {
    this.currentAuthTab = tab;
    const signInTabBtn = document.getElementById('authTabSignIn');
    const regTabBtn = document.getElementById('authTabRegister');
    const signInForm = document.getElementById('authSignInSection');
    const regForm = document.getElementById('authRegisterSection');

    if (signInTabBtn) signInTabBtn.classList.toggle('active', tab === 'signin');
    if (regTabBtn) regTabBtn.classList.toggle('active', tab === 'register');
    if (signInForm) signInForm.style.display = tab === 'signin' ? 'block' : 'none';
    if (regForm) regForm.style.display = tab === 'register' ? 'block' : 'none';
  },

  showLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.classList.add('active');
    const appCont = document.getElementById('appContainer');
    if (appCont) appCont.style.display = 'none';
    this.switchAuthTab('signin');
  },

  hideLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.classList.remove('active');
    const appCont = document.getElementById('appContainer');
    if (appCont) appCont.style.display = 'block';
  },

  loginAs(roleKey) {
    const cred = this.demoCredentials[roleKey];
    const role = this.roles[roleKey];
    if (!cred || !role) return;

    this.currentUser = {
      name: cred.name,
      email: cred.email,
      role: roleKey,
      roleLabel: role.label,
      roleShortLabel: role.shortLabel,
      permissions: role.permissions,
      color: role.color
    };
    this.currentMerchant = this.merchants[0];

    localStorage.setItem('aegispay_session', JSON.stringify({
      user: this.currentUser,
      merchant: this.currentMerchant
    }));

    this.onAuthSuccess();
  },

  loginWithCredentials() {
    const email = document.getElementById('loginEmail')?.value;
    const password = document.getElementById('loginPassword')?.value;

    if (!email || !password) {
      alert('Please enter email and password.');
      return;
    }

    for (const [roleKey, cred] of Object.entries(this.demoCredentials)) {
      if (cred.email === email && cred.password === password) {
        this.loginAs(roleKey);
        return;
      }
    }

    // Default dynamic login for custom accounts
    const roleKey = 'cfo';
    const role = this.roles[roleKey];
    this.currentUser = {
      name: email.split('@')[0],
      email: email,
      role: roleKey,
      roleLabel: role.label,
      roleShortLabel: role.shortLabel,
      permissions: role.permissions,
      color: role.color
    };
    this.currentMerchant = this.merchants[0];

    localStorage.setItem('aegispay_session', JSON.stringify({
      user: this.currentUser,
      merchant: this.currentMerchant
    }));

    this.onAuthSuccess();
  },

  registerNewMerchant() {
    const companyName = document.getElementById('regCompanyName')?.value.trim();
    const contactName = document.getElementById('regContactName')?.value.trim();
    const email = document.getElementById('regEmail')?.value.trim();
    const password = document.getElementById('regPassword')?.value;
    const gstin = document.getElementById('regGSTIN')?.value.trim() || '27AAACE1234H1Z8';
    const roleKey = document.getElementById('regRole')?.value || 'cfo';
    const category = document.getElementById('regCategory')?.value || 'D2C Retail';

    if (!companyName || !contactName || !email || !password) {
      alert('Please fill out Company Name, Contact Name, Email, and Password.');
      return;
    }

    const randomMid = `MID_RZP_${Math.floor(10000 + Math.random() * 90000)}`;
    const newMerchant = {
      mid: randomMid,
      name: companyName,
      type: `${category} (Custom Workspace)`,
      gstin: gstin,
      defaultScale: 50
    };

    this.merchants.unshift(newMerchant);
    this.currentMerchant = newMerchant;

    const role = this.roles[roleKey] || this.roles.cfo;
    this.currentUser = {
      name: contactName,
      email: email,
      role: roleKey,
      roleLabel: role.label,
      roleShortLabel: role.shortLabel,
      permissions: role.permissions,
      color: role.color
    };

    localStorage.setItem('aegispay_session', JSON.stringify({
      user: this.currentUser,
      merchant: this.currentMerchant,
      customMerchants: [newMerchant]
    }));

    alert(`🎉 Merchant workspace "${companyName}" registered successfully! Logged in as ${role.label}.`);
    this.onAuthSuccess();
  },

  switchMerchant(merchantIndex) {
    this.currentMerchant = this.merchants[merchantIndex];
    localStorage.setItem('aegispay_session', JSON.stringify({
      user: this.currentUser,
      merchant: this.currentMerchant
    }));
    this.updateNavUI();
    const dropdown = document.getElementById('merchantDropdownList');
    if (dropdown) dropdown.classList.remove('active');

    if (window.App || typeof App !== 'undefined') {
      const app = window.App || App;
      app.setScale(this.currentMerchant.defaultScale || 50);
    }
  },

  logout() {
    localStorage.removeItem('aegispay_session');
    this.currentUser = null;
    this.currentMerchant = null;
    this.showLoginModal();
  },

  hasPermission(perm) {
    if (!this.currentUser) return false;
    return this.currentUser.permissions.includes(perm);
  },

  onAuthSuccess() {
    this.hideLoginModal();
    this.updateNavUI();
    this.applyRBAC();
    if (window.App || typeof App !== 'undefined') {
      const app = window.App || App;
      if (!app.state || !app.state.reconciliationResult) {
        app.init();
      }
    }
  },

  updateNavUI() {
    const userBlock = document.getElementById('navUserBlock');
    if (userBlock && this.currentUser) {
      userBlock.innerHTML = `
        <div class="user-avatar" style="background:${this.currentUser.color};">${this.currentUser.name.charAt(0).toUpperCase()}</div>
        <div class="user-info-text">
          <div class="user-name">${this.currentUser.name}</div>
          <div class="user-role-label" style="color:${this.currentUser.color};">${this.currentUser.roleShortLabel}</div>
        </div>
      `;
    }

    const merchantLabel = document.getElementById('merchantSwitcherLabel');
    if (merchantLabel && this.currentMerchant) {
      merchantLabel.textContent = this.currentMerchant.name;
    }

    const merchantDropdown = document.getElementById('merchantDropdownList');
    if (merchantDropdown) {
      merchantDropdown.innerHTML = this.merchants.map((m, idx) => `
        <div class="merchant-option ${this.currentMerchant && this.currentMerchant.mid === m.mid ? 'active' : ''}" onclick="event.stopPropagation(); Workspace.switchMerchant(${idx})">
          <div style="font-weight:700; font-size:12px; color:#fff;">${m.name}</div>
          <div style="font-size:10.5px; color:var(--text-muted);">${m.mid} • ${m.type}</div>
        </div>
      `).join('');
    }
  },

  applyRBAC() {
    if (!this.currentUser) return;

    if (!this.hasPermission('approve_journal')) {
      document.querySelectorAll('[data-perm="approve_journal"]').forEach(el => {
        el.disabled = true;
        el.title = 'Requires CFO approval rights';
        el.style.opacity = '0.4';
      });
    }

    if (!this.hasPermission('stress_simulator')) {
      const stressPanel = document.getElementById('stressSimulatorPanel');
      if (stressPanel) stressPanel.style.opacity = '0.5';
    }

    document.querySelectorAll('[data-perm]').forEach(el => {
      const perm = el.getAttribute('data-perm');
      if (!this.hasPermission(perm)) {
        el.disabled = true;
        el.style.opacity = '0.4';
        el.title = `Requires higher permissions (${this.currentUser.roleShortLabel})`;
      }
    });
  },

  toggleMerchantDropdown() {
    const dropdown = document.getElementById('merchantDropdownList');
    if (dropdown) dropdown.classList.toggle('active');
  }
};

window.Workspace = Workspace;
