const API_BASE_URL = '/api';

function getToken() {
    return localStorage.getItem('secure_exam_token');
}

function getUser() {
    const u = localStorage.getItem('secure_exam_user');
    try { return u ? JSON.parse(u) : null; } catch(e) { return null; }
}

async function apiFetch(endpoint, options = {}) {
    const url = API_BASE_URL + endpoint;
    const headers = { ...options.headers };
    
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    
    // Only set Content-Type for non-FormData bodies
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, { ...options, headers });
    
    if (response.status === 401) {
        localStorage.removeItem('secure_exam_token');
        localStorage.removeItem('secure_exam_user');
        window.location.href = 'index.html';
        throw new Error('Session expired');
    }
    
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Request failed');
    return data;
}

function requireAuth() {
    if (!getToken()) {
        window.location.href = 'index.html';
    }
}

// Toast notification helper
function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
