document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    const loginError = document.getElementById('loginError');

    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', () => {
            const type = passwordInput.type === 'password' ? 'text' : 'password';
            passwordInput.type = type;
            togglePassword.textContent = type === 'password' ? 'Show' : 'Hide';
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const password = passwordInput.value;
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            
            if (!username || !password) {
                loginError.textContent = 'Please enter both username and password';
                loginError.classList.remove('hidden');
                return;
            }

            try {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Authenticating...';
                
                const response = await apiFetch('/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({ username, password })
                });

                localStorage.setItem('secure_exam_token', response.token);
                localStorage.setItem('secure_exam_user', JSON.stringify(response.user));
                
                window.location.href = response.user.role === 'admin' ? 'dashboard.html' : 'center-dashboard.html';
            } catch (error) {
                loginError.textContent = error.message || 'Invalid username or password';
                loginError.classList.remove('hidden');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Secure Login';
            }
        });
    }
});

function logout() {
    localStorage.removeItem('secure_exam_token');
    localStorage.removeItem('secure_exam_user');
    window.location.href = 'index.html';
}
