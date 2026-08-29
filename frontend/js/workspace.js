/**
 * AegisPay-Controller: Multi-Merchant Workspace, Authentication & User Profile
 * Supports Sign In, Registration with duplicate checks, password strength validation,
 * RBAC Persona switching, and interactive User Profile & Workspace Settings.
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
      color: '#f59e0b',
      permLabels: [
        'Approve Journal Entries',
        'Dismiss Exceptions',
        'Export Cryptographic Audit Seals',
        'Run 14-Day Monte Carlo Forecaster',
        'Inspect Section 194-O Tax Radar',
        'Execute Scalability Benchmarks',
        'Autonomous CFO Copilot Reasoning'
      ]
    },
    finops: {
      label: 'FinOps Analyst',
      shortLabel: 'FinOps',
      permissions: ['dismiss_exception', 'export_csv', 'export_json', 'copilot_query', 'view_tax_radar'],
      color: '#3b82f6',
      permLabels: [
        'Dismiss Exceptions',
        'Export Reconciled Datasets',
        'Inspect Section 194-O Tax Radar',
        'CFO Copilot Operational Queries'
      ]
    },
    auditor: {
      label: 'External Auditor (Read-Only)',
      shortLabel: 'Auditor',
      permissions: ['audit_certificate', 'view_tax_radar'],
      color: '#10b981',
      permLabels: [
        'Inspect Cryptographic Seals (Read-Only)',
        'Print Audit Certificates',
        'Statutory Tax Compliance Verification'
      ]
    }
  },

  demoCredentials: {
    cfo: { email: 'cfo@acme-retail.com', password: 'demo2026', name: 'Priya Sharma' },
    finops: { email: 'ops@acme-retail.com', password: 'demo2026', name: 'Arjun Mehta' },
    auditor: { email: 'audit@pwc-india.com', password: 'demo2026', name: 'Deepak Verma' }
  },

  init() {
    this.initPasswordChecker();

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

  // --- Password Strength Checker ---
  initPasswordChecker() {
    const regPwd = document.getElementById('regPassword');
    if (!regPwd) return;

    regPwd.addEventListener('input', () => {
      const val = regPwd.value;
      const box = document.getElementById('pwdStrengthBox');
      if (!box) return;

      if (!val) {
        box.style.display = 'none';
        return;
      }
      box.style.display = 'block';

      const isLen = val.length >= 6;
      const isUpper = /[A-Z]/.test(val);
      const isNum = /[0-9]/.test(val);
      const isSym = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(val);

      this.updateReqBadge('pwdReqLen', isLen);
      this.updateReqBadge('pwdReqUpper', isUpper);
      this.updateReqBadge('pwdReqNum', isNum);
      this.updateReqBadge('pwdReqSym', isSym);

      let score = 0;
      if (isLen) score++;
      if (isUpper) score++;
      if (isNum) score++;
      if (isSym) score++;

      const bar = document.getElementById('pwdStrengthBar');
      const label = document.getElementById('pwdStrengthLabel');

      if (bar && label) {
        if (score <= 1) {
          bar.style.width = '25%';
          bar.style.background = 'var(--accent-crimson)';
          label.textContent = 'Too Weak';
          label.style.color = 'var(--accent-crimson)';
        } else if (score === 2) {
          bar.style.width = '50%';
          bar.style.background = 'var(--accent-gold)';
          label.textContent = 'Fair';
          label.style.color = 'var(--accent-gold)';
        } else if (score === 3) {
          bar.style.width = '75%';
          bar.style.background = '#3b82f6';
          label.textContent = 'Good';
          label.style.color = '#3b82f6';
        } else {
          bar.style.width = '100%';
          bar.style.background = 'var(--accent-emerald)';
          label.textContent = 'Strong ✓';
          label.style.color = 'var(--accent-emerald)';
        }
      }
    });
  },

  updateReqBadge(elemId, isValid) {
    const el = document.getElementById(elemId);
    if (!el) return;
    if (isValid) {
      el.style.color = 'var(--accent-emerald)';
      el.style.fontWeight = '700';
    } else {
      el.style.color = 'var(--text-muted)';
      el.style.fontWeight = '400';
    }
  },

  validatePassword(val) {
    if (!val || val.length < 6) return false;
    const isUpper = /[A-Z]/.test(val);
    const isNum = /[0-9]/.test(val);
    const isSym = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(val);
    return isUpper && isNum && isSym;
  },

  // --- Registered Accounts Storage ---
  getRegisteredUsers() {
    try {
      const stored = localStorage.getItem('aegispay_registered_users');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  },

  saveRegisteredUser(userData) {
    const users = this.getRegisteredUsers();
    users.push(userData);
    localStorage.setItem('aegispay_registered_users', JSON.stringify(users));
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
    const email = document.getElementById('loginEmail')?.value.trim();
    const password = document.getElementById('loginPassword')?.value;

    if (!email || !password) {
      if (window.AegisNotice) AegisNotice.toast('Please enter email and password.', 'error');
      return;
    }

    // 1. Check demo credentials
    for (const [roleKey, cred] of Object.entries(this.demoCredentials)) {
      if (cred.email.toLowerCase() === email.toLowerCase() && cred.password === password) {
        this.loginAs(roleKey);
        return;
      }
    }

    // 2. Check registered custom users
    const registered = this.getRegisteredUsers();
    const match = registered.find(u => u.email.toLowerCase() === email.toLowerCase());
    if (match) {
      const roleKey = match.roleKey || 'cfo';
      const role = this.roles[roleKey] || this.roles.cfo;
      this.currentUser = {
        name: match.name,
        email: match.email,
        role: roleKey,
        roleLabel: role.label,
        roleShortLabel: role.shortLabel,
        permissions: role.permissions,
        color: role.color
      };

      const matchedMerchant = this.merchants.find(m => m.name === match.companyName) || this.merchants[0];
      this.currentMerchant = matchedMerchant;

      localStorage.setItem('aegispay_session', JSON.stringify({
        user: this.currentUser,
        merchant: this.currentMerchant
      }));

      this.onAuthSuccess();
      return;
    }

    // 3. Fallback standard login for custom inputs
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
      if (window.AegisNotice) AegisNotice.toast('Please fill out Company Name, Contact Name, Email, and Password.', 'error');
      return;
    }

    // --- Duplicate Account Check ---
    const lowerEmail = email.toLowerCase();
    const isDemoEmail = Object.values(this.demoCredentials).some(c => c.email.toLowerCase() === lowerEmail);
    const isCustomEmail = this.getRegisteredUsers().some(u => u.email.toLowerCase() === lowerEmail);
    const isDuplicateCompany = this.merchants.some(m => m.name.toLowerCase() === companyName.toLowerCase());

    if (isDemoEmail || isCustomEmail || isDuplicateCompany) {
      if (window.AegisNotice) {
        AegisNotice.alert(`An account with this email address (${email}) or company name is already registered.\n\nRedirecting you to Sign In...`, 'Account Exists', '⚠️');
      }
      this.switchAuthTab('signin');
      const loginEmailInp = document.getElementById('loginEmail');
      if (loginEmailInp) {
        loginEmailInp.value = email;
      }
      const loginPwdInp = document.getElementById('loginPassword');
      if (loginPwdInp) loginPwdInp.focus();
      return;
    }

    // --- Password Strength Check ---
    if (!this.validatePassword(password)) {
      if (window.AegisNotice) {
        AegisNotice.alert(
          'Please ensure your password has:\n• At least 6 characters\n• At least one uppercase letter (A-Z)\n• At least one number (0-9)\n• At least one symbol (!@#$%^&*)\n\nExample: Demo@2026',
          'Password Requirements Not Met',
          '⚠️'
        );
      }
      document.getElementById('regPassword')?.focus();
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

    // Save registered user & session
    this.saveRegisteredUser({
      name: contactName,
      email: email,
      roleKey: roleKey,
      companyName: companyName
    });

    localStorage.setItem('aegispay_session', JSON.stringify({
      user: this.currentUser,
      merchant: this.currentMerchant,
      customMerchants: [newMerchant]
    }));

    if (window.AegisNotice) {
      AegisNotice.toast(`Merchant workspace "${companyName}" registered! Logged in as ${role.label}.`, 'success');
    }
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

  // --- Logout & Confirmation Modal ---
  promptLogout() {
    const textEl = document.getElementById('logoutConfirmText');
    if (textEl && this.currentUser) {
      textEl.textContent = `Are you sure you want to sign out of ${this.currentUser.name}'s session (${this.currentUser.roleShortLabel})?`;
    }
    const modal = document.getElementById('logoutConfirmModal');
    if (modal) {
      modal.classList.add('active');
      modal.style.display = 'flex';
    }
  },

  closeLogoutModal() {
    const modal = document.getElementById('logoutConfirmModal');
    if (modal) {
      modal.classList.remove('active');
      modal.style.display = 'none';
    }
  },

  confirmLogout() {
    this.closeLogoutModal();
    this.logout();
  },

  logout() {
    localStorage.removeItem('aegispay_session');
    this.currentUser = null;
    this.currentMerchant = null;
    this.showLoginModal();
  },

  // --- Interactive Profile Page / Modal ---
  openProfileModal() {
    if (!this.currentUser) return;

    const modal = document.getElementById('userProfileModal');
    if (!modal) return;

    // User Identity
    const avatar = document.getElementById('profileModalAvatar');
    if (avatar) {
      avatar.textContent = this.currentUser.name.charAt(0).toUpperCase();
      avatar.style.background = this.currentUser.color || '#f59e0b';
    }
    const nameEl = document.getElementById('profileModalName');
    if (nameEl) nameEl.textContent = this.currentUser.name;

    const emailEl = document.getElementById('profileModalEmail');
    if (emailEl) emailEl.textContent = this.currentUser.email;

    const roleBadge = document.getElementById('profileModalRoleBadge');
    if (roleBadge) {
      roleBadge.textContent = this.currentUser.roleShortLabel;
      roleBadge.style.borderColor = this.currentUser.color;
      roleBadge.style.color = this.currentUser.color;
    }

    // Merchant Details
    const m = this.currentMerchant || this.merchants[0];
    const mName = document.getElementById('profileModalMerchantName');
    if (mName) mName.textContent = m.name;

    const mMid = document.getElementById('profileModalMerchantMid');
    if (mMid) mMid.textContent = m.mid;

    const mGstin = document.getElementById('profileModalGstin');
    if (mGstin) mGstin.textContent = m.gstin;

    const mCat = document.getElementById('profileModalCategory');
    if (mCat) mCat.textContent = m.type;

    // Role Permissions Matrix
    const permContainer = document.getElementById('profileModalPermissions');
    if (permContainer) {
      const roleObj = this.roles[this.currentUser.role] || this.roles.cfo;
      permContainer.innerHTML = (roleObj.permLabels || []).map(p => `
        <span style="font-size:10.5px; font-weight:600; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); padding:3px 9px; border-radius:4px; color:#fff;">
          ✓ ${p}
        </span>
      `).join('');
    }

    // Session Fingerprint Hash
    const sessionHashEl = document.getElementById('profileSessionHash');
    if (sessionHashEl) {
      sessionHashEl.textContent = 'auth_sha256_' + Math.abs(this.hashCode(this.currentUser.email + (m ? m.mid : ''))).toString(16).padEnd(8, '0');
    }

    modal.classList.add('active');
    modal.style.display = 'flex';
  },

  closeProfileModal() {
    const modal = document.getElementById('userProfileModal');
    if (modal) {
      modal.classList.remove('active');
      modal.style.display = 'none';
    }
  },

  hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return hash;
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
      userBlock.style.cursor = 'pointer';
      userBlock.title = 'Click to open User Profile & Workspace Settings';
      userBlock.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        Workspace.openProfileModal();
      };
      userBlock.innerHTML = `
        <div class="user-avatar" style="background:${this.currentUser.color};">${this.currentUser.name.charAt(0).toUpperCase()}</div>
        <div class="user-info-text">
          <div class="user-name" style="display:flex; align-items:center; gap:4px;">
            ${this.currentUser.name}
            <span style="font-size:8px; opacity:0.6; color:#fff;">▼</span>
          </div>
          <div class="user-role-label" style="color:${this.currentUser.color}; font-weight:700;">${this.currentUser.roleShortLabel}</div>
        </div>
      `;
    }

    const logoutBtn = document.getElementById('navLogoutBtn') || document.querySelector('button[title*="Sign out"]');
    if (logoutBtn) {
      logoutBtn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        Workspace.promptLogout();
      };
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
