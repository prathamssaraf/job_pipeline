/**
 * Job Pipeline Tracker - Dashboard JavaScript
 * Handles UI interactions and API calls
 */

// ============================================================
// State Management
// ============================================================
const state = {
    currentSection: 'dashboard',
    jobs: [],
    sources: [],
    companies: [],
    stats: null,
    jobsBySource: [],
    // New state for Jobs page navigation
    selectedSourceId: null,
    viewMode: 'sources' // 'sources' or 'list'
};

// ============================================================
// API Functions
// ============================================================
const api = {
    baseUrl: '',

    async get(endpoint) {
        const response = await fetch(`${this.baseUrl}/api${endpoint}`);
        if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
        return response.json();
    },

    async post(endpoint, data = {}) {
        const response = await fetch(`${this.baseUrl}/api${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
        return response.json();
    },

    async delete(endpoint) {
        const response = await fetch(`${this.baseUrl}/api${endpoint}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
        return response.json();
    }
};

// ============================================================
// UI Components
// ============================================================
const ui = {
    // Toast notification
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-message">${message}</span>
        `;

        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    },

    // Format date for display
    formatDate(dateStr) {
        if (!dateStr) return 'Never';
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;

        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Truncate URL for display
    truncateUrl(url, maxLen = 40) {
        if (!url || url.length <= maxLen) return url;
        return url.substring(0, maxLen) + '...';
    },

    // Show/hide sections
    showSection(sectionName) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.getElementById(`${sectionName}Section`).classList.add('active');

        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');

        const titles = {
            dashboard: ['Dashboard', 'Overview of your job tracking pipeline'],
            jobs: ['Jobs', 'Browse jobs by source'],
            sources: ['Sources', 'Manage job sources to track'],
            settings: ['Settings', 'Configure scheduler and preferences']
        };

        document.getElementById('pageTitle').textContent = titles[sectionName][0];
        document.getElementById('pageSubtitle').textContent = titles[sectionName][1];

        state.currentSection = sectionName;

        // Reset Jobs view when switching back to it
        if (sectionName === 'jobs') {
            showJobsSourceView();
        }
    },

    // Modal functions
    openModal() {
        document.getElementById('addSourceModal').classList.add('active');
        document.getElementById('sourceName').focus();
    },

    closeModal() {
        document.getElementById('addSourceModal').classList.remove('active');
        document.getElementById('addSourceForm').reset();
    }
};

// ============================================================
// Data Loading & Rendering
// ============================================================
async function loadStats() {
    try {
        const stats = await api.get('/stats');
        state.stats = stats;

        document.getElementById('totalJobs').textContent = stats.total_jobs || 0;
        document.getElementById('totalSources').textContent = stats.total_sources || 0;
        document.getElementById('checksToday').textContent = stats.checks_today || 0;
        document.getElementById('changesDetected').textContent = stats.changes_detected || 0;

        document.getElementById('lastRun').textContent = ui.formatDate(stats.last_run);
        document.getElementById('nextRun').textContent = ui.formatDate(stats.next_run);

        // Update scheduler status
        const statusEl = document.getElementById('schedulerStatus');
        if (stats.scheduler_running) {
            statusEl.classList.remove('inactive');
            statusEl.querySelector('.status-text').textContent = 'Scheduler Active';
        } else {
            statusEl.classList.add('inactive');
            statusEl.querySelector('.status-text').textContent = 'Scheduler Paused';
        }

        // Update settings UI
        document.getElementById('schedulerEnabled').checked = stats.scheduler_running;
        document.getElementById('intervalSelect').value = stats.interval_minutes;

    } catch (error) {
        console.error('Failed to load stats:', error);
        ui.showToast('Failed to load statistics', 'error');
    }
}

async function loadJobs() {
    try {
        // Load grouped jobs
        const data = await api.get('/jobs/by-source');
        state.jobsBySource = data;

        // Flatten for recent jobs
        const allJobs = data.flatMap(group => group.jobs).sort((a, b) =>
            new Date(b.first_seen) - new Date(a.first_seen)
        );
        state.jobs = allJobs;

        renderRecentJobs(allJobs.slice(0, 5));
        renderJobsSourceGrid(); // Initial render of sources grid

    } catch (error) {
        console.error('Failed to load jobs:', error);
        ui.showToast('Failed to load jobs', 'error');
    }
}

function renderRecentJobs(jobs) {
    const container = document.getElementById('recentJobsList');

    if (!jobs.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>No jobs tracked yet. Add some sources and run the pipeline!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = jobs.map(job => `
        <div class="job-card">
            <div class="job-info">
                <div class="job-title">
                    <a href="${job.url || '#'}" target="_blank">${escapeHtml(job.title)}</a>
                    ${!job.notified ? '<span class="new-badge">New</span>' : ''}
                </div>
                <div class="job-meta">
                    <span>🏢 ${escapeHtml(job.company || 'Unknown')}</span>
                    <span>📍 ${escapeHtml(job.location || 'Not specified')}</span>
                </div>
            </div>
            <div class="job-date">${ui.formatDate(job.first_seen)}</div>
        </div>
    `).join('');
}

// Render the grid of sources to click on
function renderJobsSourceGrid() {
    const container = document.getElementById('jobsSourcesList');

    if (!state.jobsBySource.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔗</div>
                <p>No sources found.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.jobsBySource.map(item => {
        const source = item.source;
        const jobCount = item.jobs.length;

        return `
            <div class="source-card" onclick="selectSource(${source.id}, '${escapeHtml(source.name || 'Other Sources').replace(/'/g, "\\'")}')">
                <div class="source-header">
                    <div>
                        <div class="source-name">${escapeHtml(source.name || 'Other Sources')}</div>
                        <div class="source-url">${escapeHtml(ui.truncateUrl(source.url))}</div>
                    </div>
                </div>
                <div class="source-stats">
                    <span class="source-stat">💼 ${jobCount} jobs</span>
                    <span class="source-stat">👉 Click to view</span>
                </div>
            </div>
        `;
    }).join('');
}

// Handle source selection to show job list
function selectSource(sourceId, sourceName) {
    state.selectedSourceId = sourceId;
    state.viewMode = 'list';

    document.getElementById('jobsSourceView').style.display = 'none';
    document.getElementById('jobsListView').style.display = 'block';

    // Clean name presentation
    const cleanName = sourceName.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#039;/g, "'");
    document.getElementById('selectedSourceName').textContent = cleanName;

    // Find jobs for this source
    const group = state.jobsBySource.find(g => g.source.id === sourceId);
    const jobs = group ? group.jobs : [];

    // Clear search
    document.getElementById('jobSearch').value = '';

    renderJobsTable(jobs);
}

function showJobsSourceView() {
    state.selectedSourceId = null;
    state.viewMode = 'sources';

    document.getElementById('jobsListView').style.display = 'none';
    document.getElementById('jobsSourceView').style.display = 'block';
}

function renderJobsTable(jobs) {
    const tbody = document.getElementById('jobsTableBody');

    if (!jobs.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>No jobs found for this source.</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = jobs.map(job => `
        <tr>
            <td><a href="${job.url || '#'}" target="_blank">${escapeHtml(job.title)}</a></td>
            <td>${escapeHtml(job.company || 'Unknown')}</td>
            <td>${escapeHtml(job.location || '-')}</td>
            <td>${ui.formatDate(job.first_seen)}</td>
            <td>
                <span class="badge ${job.notified ? 'badge-notified' : 'badge-new'}">
                    ${job.notified ? 'Notified' : 'New'}
                </span>
            </td>
            <td>
                <a href="${job.url || '#'}" target="_blank">View →</a>
            </td>
        </tr>
    `).join('');
}

async function loadSources() {
    try {
        const sources = await api.get('/sources');
        state.sources = sources;
        renderSources(sources);

    } catch (error) {
        console.error('Failed to load sources:', error);
        ui.showToast('Failed to load sources', 'error');
    }
}

function renderSources(sources) {
    const container = document.getElementById('sourcesList');

    if (!sources.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔗</div>
                <p>No sources configured yet. Add your first job source!</p>
                <button class="btn btn-primary" onclick="ui.openModal()">
                    + Add Source
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = sources.map(source => `
        <div class="source-card">
            <div class="source-header">
                <div>
                    <div class="source-name">${escapeHtml(source.name || 'Unnamed')}</div>
                    <div class="source-url">${escapeHtml(ui.truncateUrl(source.url))}</div>
                </div>
                <button class="source-delete" onclick="deleteSource(${source.id})" title="Delete source">
                    🗑️
                </button>
            </div>
            <div class="source-stats">
                <span class="source-stat">💼 ${source.job_count || 0} jobs</span>
                <span class="source-stat">🕐 ${ui.formatDate(source.last_checked)}</span>
                <span class="source-stat">${source.requires_browser ? '🌐 Browser' : '📄 Basic'}</span>
            </div>
        </div>
    `).join('');
}

// ============================================================
// Actions
// ============================================================
async function runPipeline() {
    const btn = document.getElementById('runPipelineBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon">⏳</span> Running...';

    try {
        const result = await api.post('/run');

        if (result.success) {
            ui.showToast(`Pipeline complete! Found ${result.new_jobs} new jobs.`, 'success');
        } else {
            ui.showToast(result.message || 'Pipeline completed with issues', 'warning');
        }

        // Reload data
        await Promise.all([loadStats(), loadJobs(), loadSources()]);

        // If we are viewing a specific source, refresh its list
        if (state.selectedSourceId && state.viewMode === 'list') {
            const group = state.jobsBySource.find(g => g.source.id === state.selectedSourceId);
            if (group) renderJobsTable(group.jobs);
        }

    } catch (error) {
        console.error('Pipeline failed:', error);
        ui.showToast('Failed to run pipeline', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">▶️</span> Run Pipeline';
    }
}

async function addSource(event) {
    event.preventDefault();

    const source = {
        name: document.getElementById('sourceName').value,
        url: document.getElementById('sourceUrl').value,
        requires_browser: document.getElementById('requiresBrowser').checked
    };

    try {
        await api.post('/sources', source);
        ui.showToast('Source added successfully', 'success');
        ui.closeModal();
        await Promise.all([loadSources(), loadJobs(), loadStats()]);

    } catch (error) {
        console.error('Failed to add source:', error);
        ui.showToast('Failed to add source', 'error');
    }
}

async function deleteSource(sourceId) {
    if (!confirm('Are you sure you want to delete this source?')) return;

    try {
        await api.delete(`/sources/${sourceId}`);
        ui.showToast('Source deleted', 'success');
        // If deleted source was open, go back
        if (state.selectedSourceId === sourceId) {
            showJobsSourceView();
        }
        await Promise.all([loadSources(), loadJobs(), loadStats()]);

    } catch (error) {
        console.error('Failed to delete source:', error);
        ui.showToast('Failed to delete source', 'error');
    }
}

async function saveSettings() {
    const enabled = document.getElementById('schedulerEnabled').checked;
    const interval = parseInt(document.getElementById('intervalSelect').value);

    try {
        await api.post('/scheduler', {
            enabled: enabled,
            interval_minutes: interval
        });

        ui.showToast('Settings saved successfully', 'success');
        await loadStats();

    } catch (error) {
        console.error('Failed to save settings:', error);
        ui.showToast('Failed to save settings', 'error');
    }
}

// Search functionality
function filterJobs(query) {
    if (state.viewMode !== 'list' || !state.selectedSourceId) return;

    const group = state.jobsBySource.find(g => g.source.id === state.selectedSourceId);
    if (!group) return;

    const search = query.toLowerCase();
    const filtered = group.jobs.filter(job => {
        return (
            (job.title && job.title.toLowerCase().includes(search)) ||
            (job.company && job.company.toLowerCase().includes(search)) ||
            (job.location && job.location.toLowerCase().includes(search))
        );
    });
    renderJobsTable(filtered);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// Event Listeners
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            ui.showSection(item.dataset.section);
        });
    });

    document.querySelectorAll('.view-all').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            ui.showSection(link.dataset.section);
        });
    });

    // Run Pipeline
    document.getElementById('runPipelineBtn').addEventListener('click', runPipeline);

    // Modal
    document.getElementById('addSourceBtn').addEventListener('click', ui.openModal);
    document.getElementById('closeModalBtn').addEventListener('click', ui.closeModal);
    document.getElementById('cancelModalBtn').addEventListener('click', ui.closeModal);
    document.querySelector('.modal-backdrop').addEventListener('click', ui.closeModal);
    document.getElementById('addSourceForm').addEventListener('submit', addSource);

    // Settings
    document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);

    // Search
    document.getElementById('jobSearch').addEventListener('input', (e) => {
        filterJobs(e.target.value);
    });

    // Global exposure for onClick handlers
    window.selectSource = selectSource;
    window.showJobsSourceView = showJobsSourceView;
    window.deleteSource = deleteSource;
    window.ui = ui; // Expose UI for modals

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') ui.closeModal();
    });

    // Initial load
    loadStats();
    loadJobs();
    loadSources();

    // Auto-refresh every 30 seconds
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            loadStats();
        }
    }, 30000);
});
