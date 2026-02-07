// SIP Wrapper Admin JavaScript

let refreshIntervalId = null;
const STORAGE_KEY = 'adminRefreshInterval';

// Translations (set from template)
let TRANSLATIONS = {
    registered: 'Registered',
    not_registered: 'Not registered',
    online: 'Online',
    offline: 'Offline'
};

// Initialize translations from template
function initTranslations(translations) {
    TRANSLATIONS = translations;
}

// Language switching
function setLang(lang) {
    fetch('/api/set-lang', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({lang: lang})
    }).then(() => location.reload());
}

// Refresh status from API
function refreshStatus() {
    // Refresh main status (gateways, users, profiles)
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            updateDashboardUI(data);
            updateUsersUI(data.registrations);
            updateGatewaysUI(data.gateways);
        })
        .catch(err => console.error('Status refresh failed:', err));

    // Refresh active calls
    refreshActiveCalls();

    // Refresh call logs (CDR) - silent refresh without loading indicator
    refreshCDRSilent();

    // Refresh logs preview
    refreshLogsSilent();

    // Call page-specific refresh if defined
    if (typeof window.pageRefresh === 'function') {
        window.pageRefresh();
    }
}

// Refresh Logs Preview (dashboard)
function refreshLogsSilent() {
    const container = document.getElementById('logs-preview-container');
    if (!container) return;

    fetch('/api/logs?count=10')
        .then(r => r.json())
        .then(data => {
            if (!data.logs || data.logs.length === 0) {
                container.innerHTML = '<div class="p-2 text-center text-muted small">No logs</div>';
                return;
            }

            let html = '';
            data.logs.forEach(log => {
                let classes = 'px-2 py-1 border-bottom';
                if (log.level === 'error') classes += ' bg-danger bg-opacity-10 text-danger';
                else if (log.level === 'warning') classes += ' bg-warning bg-opacity-10';
                else if (log.level === 'debug') classes += ' text-muted';
                const text = log.text.length > 120 ? log.text.substring(0, 120) + '...' : log.text;
                html += `<div class="${classes}">${escapeHtml(text)}</div>`;
            });
            container.innerHTML = html;
        })
        .catch(err => console.error('Logs refresh failed:', err));
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Refresh Active Calls
function refreshActiveCalls() {
    const container = document.getElementById('active-calls-container');
    const card = document.getElementById('active-calls-card');
    if (!container || !card) return;

    fetch('/api/active-calls')
        .then(r => r.json())
        .then(data => {
            // Update call count in stat card
            const countEl = document.querySelector('[data-stat="calls"]');
            if (countEl) countEl.textContent = data.count || 0;

            // Update active calls table
            if (!data.calls || data.calls.length === 0) {
                container.innerHTML = '';
                card.style.display = 'none';
                return;
            }

            // Show the card
            card.style.display = '';

            // Update header count
            const headerCount = card.querySelector('.card-header');
            if (headerCount) {
                headerCount.innerHTML = '<i class="bi bi-telephone-forward me-2"></i>Active Calls (' + data.calls.length + ')';
            }

            // Build table
            let html = '<div class="table-responsive"><table class="table table-sm table-hover mb-0"><thead><tr>';
            html += '<th style="width: 100px;">Direction</th>';
            html += '<th>Connection</th>';
            html += '<th style="width: 100px;">Status</th>';
            html += '<th style="width: 120px;">Time</th>';
            html += '</tr></thead><tbody>';

            data.calls.forEach(call => {
                html += '<tr>';
                // Direction
                if (call.direction === 'inbound') {
                    html += '<td><span class="badge bg-success"><i class="bi bi-telephone-inbound me-1"></i>In</span></td>';
                } else {
                    html += '<td><span class="badge bg-primary"><i class="bi bi-telephone-outbound me-1"></i>Out</span></td>';
                }
                // Call flow
                html += '<td><div class="d-flex align-items-center gap-1 flex-wrap">';
                if (call.direction === 'inbound') {
                    html += `<code class="bg-light px-1">${call.cid_num || '?'}</code>`;
                    html += '<i class="bi bi-arrow-right text-muted small"></i>';
                    html += `<span class="text-info small">${call.name || 'GW'}</span>`;
                    html += '<i class="bi bi-arrow-right text-muted small"></i>';
                    html += `<code class="bg-success bg-opacity-10 text-success px-1">${call.dest || '?'}</code>`;
                } else {
                    html += `<code class="bg-success bg-opacity-10 text-success px-1">${call.cid_num || '?'}</code>`;
                    html += '<i class="bi bi-arrow-right text-muted small"></i>';
                    html += `<span class="text-info small">${call.name || 'GW'}</span>`;
                    html += '<i class="bi bi-arrow-right text-muted small"></i>';
                    html += `<code class="bg-light px-1">${call.dest || '?'}</code>`;
                }
                html += '</div></td>';
                // State
                html += `<td><span class="badge bg-warning text-dark"><i class="bi bi-activity me-1"></i>${call.state}</span></td>`;
                // Time
                html += `<td><small class="text-muted">${call.created}</small></td>`;
                html += '</tr>';
            });

            html += '</tbody></table></div>';
            container.innerHTML = html;
        })
        .catch(err => console.error('Active calls refresh failed:', err));
}

// Silent CDR refresh (no loading indicator)
function refreshCDRSilent() {
    const container = document.getElementById('cdr-container');
    if (!container) return;

    fetch('/api/cdr?count=10')
        .then(r => r.json())
        .then(data => {
            if (!data.calls || data.calls.length === 0) {
                container.innerHTML = '<div class="p-4 text-center text-muted"><i class="bi bi-telephone-x fs-1 d-block mb-2"></i>No calls recorded</div>';
                return;
            }

            let html = '<div class="table-responsive"><table class="table table-sm table-hover mb-0"><thead><tr>';
            html += '<th style="width: 100px;">Direction</th>';
            html += '<th>From</th>';
            html += '<th>To</th>';
            html += '<th style="width: 80px;">Duration</th>';
            html += '<th style="width: 100px;">Result</th>';
            html += '<th style="width: 150px;">Time</th>';
            html += '</tr></thead><tbody>';

            data.calls.forEach(call => {
                html += '<tr>';
                if (call.direction === 'inbound') {
                    html += '<td><span class="badge bg-success"><i class="bi bi-telephone-inbound me-1"></i>In</span></td>';
                } else {
                    html += '<td><span class="badge bg-primary"><i class="bi bi-telephone-outbound me-1"></i>Out</span></td>';
                }
                html += `<td><code>${call.caller_num}</code></td>`;
                html += `<td><code>${call.dest}</code></td>`;
                const dur = parseInt(call.billsec) || 0;
                const mins = Math.floor(dur / 60);
                const secs = dur % 60;
                const durStr = `${mins}:${secs.toString().padStart(2, '0')}`;
                html += dur > 0
                    ? `<td><span class="text-success">${durStr}</span></td>`
                    : '<td><span class="text-muted">0:00</span></td>';
                const cause = call.hangup_cause || '';
                if (cause.includes('NORMAL') || cause.includes('SUCCESS')) {
                    html += '<td><span class="badge bg-success">OK</span></td>';
                } else if (cause.includes('BUSY')) {
                    html += '<td><span class="badge bg-warning text-dark">Busy</span></td>';
                } else if (cause.includes('NO_ANSWER')) {
                    html += '<td><span class="badge bg-secondary">No Answer</span></td>';
                } else if (cause.includes('CANCEL')) {
                    html += '<td><span class="badge bg-secondary">Cancelled</span></td>';
                } else {
                    html += `<td><span class="badge bg-danger" title="${cause}">Failed</span></td>`;
                }
                const time = call.start && call.start.length > 19 ? call.start.slice(-19) : call.start;
                html += `<td><small class="text-muted">${time}</small></td>`;
                html += '</tr>';
            });

            html += '</tbody></table></div>';
            container.innerHTML = html;
        })
        .catch(err => console.error('CDR refresh failed:', err));
}

// Update dashboard statistics
function updateDashboardUI(data) {
    // Update gateway count
    const gwOnline = data.gateways ? data.gateways.filter(g => g.status === 'online').length : 0;
    const gwTotal = data.gateways ? data.gateways.length : 0;
    const gwEl = document.querySelector('[data-stat="gateways"]');
    if (gwEl) gwEl.textContent = `${gwOnline}/${gwTotal}`;

    // Update user count
    const usersOnline = data.registrations ? data.registrations.length : 0;
    const usersEl = document.querySelector('[data-stat="users"]');
    if (usersEl) usersEl.textContent = usersOnline;

    // Update profiles
    const profilesOnline = data.profiles ? data.profiles.filter(p => p.status === 'online').length : 0;
    const profilesEl = document.querySelector('[data-stat="profiles"]');
    if (profilesEl) profilesEl.textContent = profilesOnline;
}

// Update users UI
function updateUsersUI(registrations) {
    if (!registrations) return;
    const regUsers = {};
    registrations.forEach(r => {
        const username = (r.user || '').split('@')[0];
        if (username) regUsers[username] = r;
    });

    // Update user cards
    document.querySelectorAll('[data-user]').forEach(container => {
        const username = container.dataset.user;
        const isOnline = username in regUsers;
        const reg = regUsers[username] || {};

        // Update card border and header
        const cardEl = container.querySelector('.card');
        if (cardEl) {
            cardEl.classList.toggle('border-success', isOnline);
            cardEl.classList.toggle('border-secondary', !isOnline);
        }

        const header = container.querySelector('.card-header');
        if (header) {
            header.classList.toggle('bg-success', isOnline);
            header.classList.toggle('bg-opacity-10', true);
            header.classList.toggle('bg-secondary', !isOnline);
        }

        // Update status badge
        const badge = container.querySelector('.card-header .badge');
        if (badge) {
            badge.classList.toggle('bg-success', isOnline);
            badge.classList.toggle('bg-secondary', !isOnline);
            badge.innerHTML = isOnline
                ? '<i class="bi bi-circle-fill me-1" style="font-size: 0.5rem;"></i>' + TRANSLATIONS.online
                : '<i class="bi bi-circle me-1" style="font-size: 0.5rem;"></i>' + TRANSLATIONS.offline;
        }

        // Update icon color
        const icon = container.querySelector('.bi-person-circle');
        if (icon) {
            icon.classList.toggle('text-success', isOnline);
            icon.classList.toggle('text-secondary', !isOnline);
        }

        // Update footer
        const footer = container.querySelector('.card-footer small');
        if (footer) {
            footer.innerHTML = isOnline
                ? '<i class="bi bi-check-circle-fill text-success me-1"></i>' + TRANSLATIONS.registered
                : '<i class="bi bi-dash-circle text-secondary me-1"></i>' + TRANSLATIONS.not_registered;
        }
    });
}

// Update gateways UI
function updateGatewaysUI(gateways) {
    if (!gateways) return;
    const gwStatus = {};
    gateways.forEach(g => gwStatus[g.name] = g);

    document.querySelectorAll('[data-gateway]').forEach(el => {
        const gwName = el.dataset.gateway;
        const gw = gwStatus[gwName];
        if (!gw) return;

        const isOnline = gw.status === 'online';
        const badge = el.querySelector('.badge');
        if (badge) {
            badge.classList.toggle('bg-success', isOnline);
            badge.classList.toggle('bg-secondary', !isOnline);
            badge.textContent = isOnline ? 'Online' : 'Offline';
        }
    });
}

// Update refresh interval
function updateRefreshInterval(interval) {
    interval = parseInt(interval);

    // Save to localStorage
    localStorage.setItem(STORAGE_KEY, interval);

    // Clear existing interval
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
    }

    // Update indicator
    const indicator = document.getElementById('refreshIndicator');
    if (interval === 0) {
        indicator.classList.add('paused');
    } else {
        indicator.classList.remove('paused');
        refreshIntervalId = setInterval(refreshStatus, interval);
    }
}

// Manual refresh button
function manualRefresh() {
    const btn = document.querySelector('.auto-refresh-control button');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i>';

    refreshStatus();

    setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
    }, 500);
}

// Refresh CDR (Call Logs)
function refreshCDR() {
    const container = document.getElementById('cdr-container');
    if (!container) return;

    container.innerHTML = '<div class="p-3 text-center text-muted"><i class="bi bi-arrow-clockwise spin me-2"></i>Loading...</div>';

    fetch('/api/cdr?count=10')
        .then(r => r.json())
        .then(data => {
            if (!data.calls || data.calls.length === 0) {
                container.innerHTML = '<div class="p-4 text-center text-muted"><i class="bi bi-telephone-x fs-1 d-block mb-2"></i>No calls recorded</div>';
                return;
            }

            let html = '<div class="table-responsive"><table class="table table-sm table-hover mb-0"><thead><tr>';
            html += '<th style="width: 100px;">Direction</th>';
            html += '<th>From</th>';
            html += '<th>To</th>';
            html += '<th style="width: 80px;">Duration</th>';
            html += '<th style="width: 100px;">Result</th>';
            html += '<th style="width: 150px;">Time</th>';
            html += '</tr></thead><tbody>';

            data.calls.forEach(call => {
                html += '<tr>';
                // Direction
                if (call.direction === 'inbound') {
                    html += '<td><span class="badge bg-success"><i class="bi bi-telephone-inbound me-1"></i>In</span></td>';
                } else {
                    html += '<td><span class="badge bg-primary"><i class="bi bi-telephone-outbound me-1"></i>Out</span></td>';
                }
                // From / To
                html += `<td><code>${call.caller_num}</code></td>`;
                html += `<td><code>${call.dest}</code></td>`;
                // Duration
                const dur = parseInt(call.billsec) || 0;
                const mins = Math.floor(dur / 60);
                const secs = dur % 60;
                const durStr = `${mins}:${secs.toString().padStart(2, '0')}`;
                html += dur > 0
                    ? `<td><span class="text-success">${durStr}</span></td>`
                    : '<td><span class="text-muted">0:00</span></td>';
                // Result
                const cause = call.hangup_cause || '';
                if (cause.includes('NORMAL') || cause.includes('SUCCESS')) {
                    html += '<td><span class="badge bg-success">OK</span></td>';
                } else if (cause.includes('BUSY')) {
                    html += '<td><span class="badge bg-warning text-dark">Busy</span></td>';
                } else if (cause.includes('NO_ANSWER')) {
                    html += '<td><span class="badge bg-secondary">No Answer</span></td>';
                } else if (cause.includes('CANCEL')) {
                    html += '<td><span class="badge bg-secondary">Cancelled</span></td>';
                } else {
                    html += `<td><span class="badge bg-danger" title="${cause}">Failed</span></td>`;
                }
                // Time
                const time = call.start && call.start.length > 19 ? call.start.slice(-19) : call.start;
                html += `<td><small class="text-muted">${time}</small></td>`;
                html += '</tr>';
            });

            html += '</tbody></table></div>';
            container.innerHTML = html;
        })
        .catch(err => {
            console.error('CDR refresh failed:', err);
            container.innerHTML = '<div class="p-3 text-center text-danger">Failed to load call logs</div>';
        });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedInterval = localStorage.getItem(STORAGE_KEY);
    const select = document.getElementById('refreshInterval');

    if (select) {
        if (savedInterval !== null) {
            select.value = savedInterval;
        }
        updateRefreshInterval(select.value);
    }
});
