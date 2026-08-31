document.addEventListener('DOMContentLoaded', () => {
    requireAuth();
    const user = getUser();
    const nameEl = document.getElementById('userNameDisplay');
    if (nameEl && user) nameEl.textContent = user.username;
    loadDashboardStats();
    loadUpcomingExams();
});

async function loadDashboardStats() {
    try {
        const data = await apiFetch('/dashboard/stats');
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set('totalCenters', data.total_centers || 0);
        set('scheduledExams', data.scheduled_exams || 0);
        set('totalPapers', data.total_papers || 0);
        set('totalDownloads', data.downloads_count || 0);
        
        const list = document.getElementById('recentActivityList');
        if (list && data.recent_activity) {
            list.innerHTML = '';
            if (data.recent_activity.length === 0) {
                list.innerHTML = '<li style="color:#999;">No recent activity</li>';
            }
            data.recent_activity.forEach(a => {
                const li = document.createElement('li');
                li.innerHTML = a.action + '<span class="activity-date">' + new Date(a.timestamp).toLocaleString() + '</span>';
                list.appendChild(li);
            });
        }
    } catch (e) {
        console.error('Dashboard stats error', e);
    }
}

async function loadUpcomingExams() {
    try {
        const exams = await apiFetch('/exams/');
        const tbody = document.getElementById('upcomingExamsTable');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (exams.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#999;">No exams scheduled</td></tr>';
            return;
        }
        exams.slice(0, 5).forEach(exam => {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td>' + exam.exam_date + '</td><td>' + exam.exam_code + '</td><td>' + exam.subject + '</td><td><span class="status-badge status-' + exam.status + '">' + exam.status + '</span></td>';
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('Exams error', e);
    }
}
