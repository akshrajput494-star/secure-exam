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
        if (!endpoint.includes('/auth/login')) {
            localStorage.removeItem('secure_exam_token');
            localStorage.removeItem('secure_exam_user');
            window.location.href = 'index.html';
            throw new Error('Session expired');
        }
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

// Automatically initialize responsive mobile sidebar toggle on all pages
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.querySelector('.sidebar');
    const header = document.querySelector('.sidebar-header');
    
    if (sidebar && header && !header.querySelector('.sidebar-toggle-btn')) {
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'sidebar-toggle-btn';
        toggleBtn.setAttribute('aria-label', 'Toggle Navigation');
        toggleBtn.innerHTML = '☰';
        
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('mobile-open');
            const isOpen = sidebar.classList.contains('mobile-open');
            toggleBtn.innerHTML = isOpen ? '✕' : '☰';
        });
        
        header.appendChild(toggleBtn);
        
        // Close menu when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('mobile-open') && !sidebar.contains(e.target)) {
                sidebar.classList.remove('mobile-open');
                toggleBtn.innerHTML = '☰';
            }
        });

        // Close menu when any nav link is tapped on mobile
        const navLinks = sidebar.querySelectorAll('.sidebar-nav a');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                sidebar.classList.remove('mobile-open');
                toggleBtn.innerHTML = '☰';
            });
        });
    }
});

