/**
 * CampusIQ Centralized REST API Client
 * Manages HTTP communication with FastAPI backend using HTTP-only signed session cookies.
 */

const API_BASE = window.location.origin.includes('8000') 
  ? `${window.location.origin}/api/v1`
  : 'http://localhost:8000/api/v1';

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
    const defaultHeaders = {
      'Accept': 'application/json',
    };

    if (options.body && !(options.body instanceof FormData)) {
      defaultHeaders['Content-Type'] = 'application/json';
    }

    const config = {
      ...options,
      credentials: 'include', // Automatically passes HTTP-only session cookies
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      // Handle 204 No Content
      if (response.status === 204) {
        return { success: true, status: 204 };
      }

      const contentType = response.headers.get('content-type') || '';
      let data = null;
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorMsg = data && data.detail ? data.detail : `Request failed with status ${response.status}`;
        return { success: false, status: response.status, error: errorMsg };
      }

      return { success: true, status: response.status, data };
    } catch (err) {
      console.error(`[API Error] ${options.method || 'GET'} ${url}:`, err);
      return {
        success: false,
        status: 0,
        error: 'Network connection error. Please verify the CampusIQ backend is running.',
      };
    }
  }

  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    const fullPath = query ? `${endpoint}?${query}` : endpoint;
    return this.request(fullPath, { method: 'GET' });
  }

  post(endpoint, body = {}) {
    const payload = body instanceof FormData ? body : JSON.stringify(body);
    return this.request(endpoint, { method: 'POST', body: payload });
  }

  put(endpoint, body = {}) {
    const payload = body instanceof FormData ? body : JSON.stringify(body);
    return this.request(endpoint, { method: 'PUT', body: payload });
  }

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

// Global API instance
window.api = new ApiClient(API_BASE);

// Lightweight Toast Notification
window.showToast = function(message, type = 'info') {
  let container = document.getElementById('campusiq-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'campusiq-toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 200ms ease';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
};
