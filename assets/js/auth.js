/**
 * CampusIQ Authentication & Session Manager
 * Eliminates insecure localStorage credentials and uses secure HTTP-only signed cookies.
 */

class AuthManager {
  constructor() {
    this.currentUser = null;
    this.isAuthenticated = false;
  }

  async init() {
    await this.checkSession();
    this.renderNavAuthState();
  }

  async checkSession() {
    try {
      const res = await window.api.get('/auth/me');
      if (res.success && res.data) {
        this.currentUser = res.data;
        this.isAuthenticated = true;
      } else {
        this.currentUser = null;
        this.isAuthenticated = false;
      }
    } catch (e) {
      this.currentUser = null;
      this.isAuthenticated = false;
    }
    return this.isAuthenticated;
  }

  async login(email, password) {
    const res = await window.api.post('/auth/login', { email, password });
    if (res.success) {
      this.currentUser = res.data.user || res.data;
      this.isAuthenticated = true;
      window.showToast('Login successful! Welcome to CampusIQ.', 'success');
      return { success: true, user: this.currentUser };
    }
    return { success: false, error: res.error || 'Invalid credentials' };
  }

  async register(fullName, email, password) {
    const res = await window.api.post('/auth/register', {
      full_name: fullName,
      email: email,
      password: password,
    });
    if (res.success) {
      window.showToast('Account registered successfully! Please log in.', 'success');
      return { success: true };
    }
    return { success: false, error: res.error || 'Registration failed' };
  }

  async logout() {
    await window.api.post('/auth/logout');
    this.currentUser = null;
    this.isAuthenticated = false;
    window.showToast('Logged out successfully.', 'info');
    setTimeout(() => {
      window.location.href = 'login.html';
    }, 600);
  }

  renderNavAuthState() {
    const navActions = document.getElementById('nav-auth-container');
    if (!navActions) return;

    if (this.isAuthenticated && this.currentUser) {
      const isAdmin = this.currentUser.role === 'admin';
      navActions.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          ${isAdmin ? `<a href="admin_view.html" class="btn btn-sm btn-outline">Admin Panel</a>` : ''}
          <div style="display: flex; align-items: center; gap: 0.5rem; background: rgba(255,255,255,0.06); padding: 0.3rem 0.65rem; border-radius: 9999px;">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: #10b981;"></span>
            <span style="font-size: 0.82rem; font-weight: 600; color: #f8fafc;">${this.currentUser.full_name.split(' ')[0]}</span>
            <span class="badge ${isAdmin ? 'badge-naac' : 'badge-mca'}" style="font-size: 0.65rem;">${this.currentUser.role}</span>
          </div>
          <button id="btn-logout-trigger" class="btn btn-sm btn-secondary" title="Sign Out">Sign Out</button>
        </div>
      `;

      const logoutBtn = document.getElementById('btn-logout-trigger');
      if (logoutBtn) {
        logoutBtn.addEventListener('click', () => this.logout());
      }
    } else {
      navActions.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.6rem;">
          <a href="login.html" class="btn btn-sm btn-secondary">Sign In</a>
          <a href="signup.html" class="btn btn-sm btn-primary">Register</a>
        </div>
      `;
    }
  }

  async requireAuth() {
    const isAuthed = await this.checkSession();
    if (!isAuthed) {
      window.location.href = `login.html?redirect=${encodeURIComponent(window.location.pathname)}`;
    }
  }

  async requireAdmin() {
    const isAuthed = await this.checkSession();
    if (!isAuthed || this.currentUser.role !== 'admin') {
      window.showToast('Administrator privileges required.', 'error');
      setTimeout(() => {
        window.location.href = 'login.html';
      }, 1000);
    }
  }
}

window.auth = new AuthManager();
document.addEventListener('DOMContentLoaded', () => {
  window.auth.init();
});
