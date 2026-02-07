// SIP Wrapper Admin - Security Page JavaScript

// Security data cache
let securityData = { blacklist: [], whitelist: [], whitelist_enabled: false };

// Toast helper
function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    const icon = document.getElementById('toast-icon');
    const titleEl = document.getElementById('toast-title');
    const bodyEl = document.getElementById('toast-body');

    titleEl.textContent = title;
    bodyEl.textContent = message;

    icon.className = 'bi me-2';
    if (type === 'success') icon.classList.add('bi-check-circle', 'text-success');
    else if (type === 'error') icon.classList.add('bi-exclamation-circle', 'text-danger');
    else icon.classList.add('bi-info-circle', 'text-primary');

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// API helpers
async function apiGet(url) {
    const res = await fetch(url);
    return res.json();
}

async function apiPost(url, data) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}

async function apiDelete(url) {
    const res = await fetch(url, { method: 'DELETE' });
    return res.json();
}

// =============================================================================
// Load All Security Data
// =============================================================================

async function loadAll() {
    await loadSecurity();
}

async function loadSecurity() {
    try {
        securityData = await apiGet('/api/security');
        renderBlacklist();
        renderWhitelist();

        // Update whitelist mode toggle
        const toggle = document.getElementById('whitelist-enabled');
        if (toggle) {
            toggle.checked = securityData.whitelist_enabled || false;
        }

        // Load auto-blacklist settings and failed attempts
        await loadAutoBlacklistSettings();
        await loadFailedAttempts();

        // Load Fail2Ban settings
        await loadFail2banSettings();
    } catch (e) {
        console.error('Failed to load security:', e);
    }
}

// =============================================================================
// Blacklist / Whitelist Rendering
// =============================================================================

function renderBlacklist() {
    const container = document.getElementById('blacklist-container');
    if (!container) return;

    const list = securityData.blacklist || [];
    if (list.length === 0) {
        container.innerHTML = '<div class="p-3 text-center text-muted"><i class="bi bi-shield-check me-2"></i>No blocked IPs</div>';
        return;
    }

    let html = '<table class="table table-sm table-hover mb-0"><thead><tr>';
    html += '<th>IP</th><th>Blocked</th><th>Status</th><th>Actions</th>';
    html += '</tr></thead><tbody>';
    list.forEach(entry => {
        const blockedCount = entry.blocked_count || 1;
        const isFail2banned = entry.fail2ban_banned || false;

        html += `<tr>
            <td>
                <code class="text-danger">${entry.ip}</code>
                ${entry.comment ? `<small class="text-muted d-block">${entry.comment}</small>` : ''}
            </td>
            <td>
                <span class="badge ${blockedCount >= 50 ? 'bg-danger' : blockedCount >= 20 ? 'bg-warning text-dark' : 'bg-secondary'}">${blockedCount}x</span>
            </td>
            <td>
                ${isFail2banned
                    ? '<span class="badge bg-dark"><i class="bi bi-fire me-1"></i>Fail2Ban</span>'
                    : '<span class="badge bg-info">ACL only</span>'}
            </td>
            <td class="text-end">
                ${!isFail2banned
                    ? `<button class="btn btn-sm btn-outline-dark" onclick="banInFail2ban('${entry.ip}')" title="Add to Fail2Ban">
                        <i class="bi bi-fire"></i>
                    </button>`
                    : `<button class="btn btn-sm btn-outline-warning" onclick="unbanFromFail2ban('${entry.ip}')" title="Remove from Fail2Ban">
                        <i class="bi bi-unlock"></i>
                    </button>`}
                <button class="btn btn-sm btn-outline-danger" onclick="removeFromBlacklist('${entry.ip}')" title="Remove">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderWhitelist() {
    const container = document.getElementById('whitelist-container');
    if (!container) return;

    const list = securityData.whitelist || [];
    if (list.length === 0) {
        container.innerHTML = '<div class="p-3 text-center text-muted"><i class="bi bi-list-check me-2"></i>No allowed IPs</div>';
        return;
    }

    let html = '<table class="table table-sm table-hover mb-0"><tbody>';
    list.forEach(entry => {
        html += `<tr>
            <td>
                <code class="text-success">${entry.ip}</code>
                ${entry.comment ? `<small class="text-muted d-block">${entry.comment}</small>` : ''}
            </td>
            <td class="text-end">
                <button class="btn btn-sm btn-outline-danger" onclick="removeFromWhitelist('${entry.ip}')" title="Remove">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

// =============================================================================
// Blacklist / Whitelist Actions
// =============================================================================

function showAddBlacklistModal() {
    document.getElementById('blacklist-ip').value = '';
    document.getElementById('blacklist-comment').value = '';
    new bootstrap.Modal(document.getElementById('blacklistModal')).show();
}

function showAddWhitelistModal() {
    document.getElementById('whitelist-ip').value = '';
    document.getElementById('whitelist-comment').value = '';
    new bootstrap.Modal(document.getElementById('whitelistModal')).show();
}

async function addToBlacklist() {
    const ip = document.getElementById('blacklist-ip').value.trim();
    const comment = document.getElementById('blacklist-comment').value.trim();

    if (!ip) {
        showToast('Error', 'IP address required', 'error');
        return;
    }

    const result = await apiPost('/api/security/blacklist', { ip, comment });
    if (result.success) {
        bootstrap.Modal.getInstance(document.getElementById('blacklistModal')).hide();
        showToast('Success', result.message, 'success');
        await loadSecurity();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function addToWhitelist() {
    const ip = document.getElementById('whitelist-ip').value.trim();
    const comment = document.getElementById('whitelist-comment').value.trim();

    if (!ip) {
        showToast('Error', 'IP address required', 'error');
        return;
    }

    const result = await apiPost('/api/security/whitelist', { ip, comment });
    if (result.success) {
        bootstrap.Modal.getInstance(document.getElementById('whitelistModal')).hide();
        showToast('Success', result.message, 'success');
        await loadSecurity();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function removeFromBlacklist(ip) {
    if (!confirm(`Remove ${ip} from blacklist?`)) return;

    const result = await apiDelete(`/api/security/blacklist/${encodeURIComponent(ip)}`);
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadSecurity();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function removeFromWhitelist(ip) {
    if (!confirm(`Remove ${ip} from whitelist?`)) return;

    const result = await apiDelete(`/api/security/whitelist/${encodeURIComponent(ip)}`);
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadSecurity();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function toggleWhitelistMode() {
    const enabled = document.getElementById('whitelist-enabled').checked;
    const result = await apiPost('/api/security/whitelist-enabled', { enabled });
    if (result.success) {
        showToast('Success', result.message, 'success');
    } else {
        showToast('Error', result.message, 'error');
    }
}

// =============================================================================
// Auto-Blacklist
// =============================================================================

async function loadAutoBlacklistSettings() {
    try {
        const settings = await apiGet('/api/security/auto-blacklist');
        document.getElementById('auto-blacklist-enabled').checked = settings.enabled || false;
        document.getElementById('auto-blacklist-max-attempts').value = settings.max_attempts || 10;
        document.getElementById('auto-blacklist-time-window').value = settings.time_window || 300;
        document.getElementById('auto-blacklist-duration').value = settings.block_duration || 3600;
    } catch (e) {
        console.error('Failed to load auto-blacklist settings:', e);
    }
}

async function saveAutoBlacklistSettings() {
    const data = {
        enabled: document.getElementById('auto-blacklist-enabled').checked,
        max_attempts: parseInt(document.getElementById('auto-blacklist-max-attempts').value) || 10,
        time_window: parseInt(document.getElementById('auto-blacklist-time-window').value) || 300,
        block_duration: parseInt(document.getElementById('auto-blacklist-duration').value) || 3600
    };

    const result = await apiPost('/api/security/auto-blacklist', data);
    if (result.success) {
        showToast('Success', result.message, 'success');
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function loadFailedAttempts() {
    const container = document.getElementById('failed-attempts-container');
    if (!container) return;

    try {
        const data = await apiGet('/api/security/failed-attempts');
        const attempts = data.attempts || [];
        const settings = data.settings || {};

        if (attempts.length === 0) {
            container.innerHTML = '<div class="p-3 text-center text-muted"><i class="bi bi-shield-check me-2"></i>No suspicious activity detected</div>';
            return;
        }

        let html = '<table class="table table-sm table-hover mb-0"><thead><tr>';
        html += '<th>IP Address</th>';
        html += '<th>Attempts</th>';
        html += '<th>Status</th>';
        html += '<th>Action</th>';
        html += '</tr></thead><tbody>';

        attempts.forEach(a => {
            const count = a.count || 0;
            const maxAttempts = settings.max_attempts || 10;
            const percent = Math.min(100, Math.round((count / maxAttempts) * 100));
            const isWarning = count >= maxAttempts * 0.5;
            const isDanger = count >= maxAttempts * 0.8;

            html += '<tr>';
            html += `<td><code class="${isDanger ? 'text-danger' : isWarning ? 'text-warning' : ''}">${a.ip}</code></td>`;
            html += `<td>
                <div class="d-flex align-items-center gap-2">
                    <div class="progress flex-grow-1" style="height: 6px; width: 60px;">
                        <div class="progress-bar ${isDanger ? 'bg-danger' : isWarning ? 'bg-warning' : 'bg-info'}" style="width: ${percent}%"></div>
                    </div>
                    <small class="${isDanger ? 'text-danger fw-bold' : isWarning ? 'text-warning' : ''}">${count}/${maxAttempts}</small>
                </div>
            </td>`;
            html += `<td>`;
            if (isDanger) {
                html += '<span class="badge bg-danger">Critical</span>';
            } else if (isWarning) {
                html += '<span class="badge bg-warning text-dark">Warning</span>';
            } else {
                html += '<span class="badge bg-secondary">Monitoring</span>';
            }
            html += '</td>';
            html += `<td>
                <button class="btn btn-sm btn-outline-danger" onclick="quickBlockIp('${a.ip}')" title="Block immediately">
                    <i class="bi bi-x-octagon"></i>
                </button>
            </td>`;
            html += '</tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;

        // Show blocked count if any
        if (data.blocked && data.blocked.length > 0) {
            showToast('Auto-Blocked', `${data.blocked.length} IP(s) have been blocked`, 'success');
            await loadSecurity(); // Refresh blacklist
        }
    } catch (e) {
        console.error('Failed to load failed attempts:', e);
        container.innerHTML = '<div class="p-3 text-center text-danger">Failed to load data</div>';
    }
}

async function checkAutoBlacklist() {
    try {
        const result = await apiPost('/api/security/check-blacklist', {});
        if (result.success) {
            if (result.blocked && result.blocked.length > 0) {
                showToast('Success', `Blocked ${result.blocked.length} IP(s): ${result.blocked.join(', ')}`, 'success');
                await loadSecurity();
            } else {
                showToast('Info', 'No IPs exceeded the threshold', 'info');
            }
            await loadFailedAttempts();
        } else {
            showToast('Error', result.message, 'error');
        }
    } catch (e) {
        showToast('Error', 'Check failed: ' + e.message, 'error');
    }
}

async function quickBlockIp(ip) {
    if (!confirm(`Block IP ${ip} immediately?`)) return;

    const result = await apiPost('/api/security/blacklist', {
        ip: ip,
        comment: 'Manually blocked from monitor'
    });
    if (result.success) {
        showToast('Success', `IP ${ip} has been blocked`, 'success');
        await loadSecurity();
        await loadFailedAttempts();
    } else {
        showToast('Error', result.message, 'error');
    }
}

// =============================================================================
// Fail2Ban Integration
// =============================================================================

async function loadFail2banSettings() {
    try {
        const data = await apiGet('/api/security/fail2ban');
        const settings = data.settings || {};

        document.getElementById('fail2ban-enabled').checked = settings.enabled || false;
        document.getElementById('fail2ban-threshold').value = settings.threshold || 50;
        document.getElementById('fail2ban-jail').value = settings.jail_name || 'sip-blacklist';

        // Update status display
        updateFail2banStatusDisplay(data.status);
    } catch (e) {
        console.error('Failed to load Fail2Ban settings:', e);
    }
}

function updateFail2banStatusDisplay(status) {
    const container = document.getElementById('fail2ban-status');
    if (!container) return;

    if (!status) {
        container.innerHTML = '<span class="badge bg-secondary">Unknown</span>';
        return;
    }

    if (status.error) {
        container.innerHTML = `<span class="badge bg-danger" title="${status.error}"><i class="bi bi-x-circle me-1"></i>Error</span>
            <small class="text-danger d-block mt-1">${status.error}</small>`;
        return;
    }

    if (!status.available) {
        container.innerHTML = '<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle me-1"></i>Not installed</span>';
        return;
    }

    if (!status.jail_exists) {
        container.innerHTML = `<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle me-1"></i>Jail not found</span>
            <small class="text-muted d-block mt-1">Create the jail in Fail2Ban config</small>`;
        return;
    }

    const bannedCount = (status.banned_ips || []).length;
    container.innerHTML = `<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Active</span>
        <small class="text-success d-block mt-1">${bannedCount} IP(s) banned</small>`;
}

async function loadFail2banStatus() {
    try {
        const data = await apiGet('/api/security/fail2ban');
        updateFail2banStatusDisplay(data.status);
        showToast('Info', 'Fail2Ban status refreshed', 'info');
    } catch (e) {
        showToast('Error', 'Failed to load Fail2Ban status', 'error');
    }
}

async function saveFail2banSettings() {
    const data = {
        enabled: document.getElementById('fail2ban-enabled').checked,
        threshold: parseInt(document.getElementById('fail2ban-threshold').value) || 50,
        jail_name: document.getElementById('fail2ban-jail').value || 'sip-blacklist'
    };

    const result = await apiPost('/api/security/fail2ban', data);
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadFail2banStatus();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function banInFail2ban(ip) {
    if (!confirm(`Add IP ${ip} to Fail2Ban (firewall block)?`)) return;

    const result = await apiPost(`/api/security/fail2ban/ban/${encodeURIComponent(ip)}`, {});
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadSecurity();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function unbanFromFail2ban(ip) {
    if (!confirm(`Remove IP ${ip} from Fail2Ban?`)) return;

    const result = await apiPost(`/api/security/fail2ban/unban/${encodeURIComponent(ip)}`, {});
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadSecurity();
    } else {
        showToast('Error', result.message, 'error');
    }
}

// =============================================================================
// Apply Config
// =============================================================================

async function applyConfig() {
    if (!confirm('Apply configuration and reload FreeSWITCH?')) return;

    const result = await apiPost('/api/crud/apply', {});
    if (result.success) {
        showToast('Success', result.message, 'success');
    } else {
        showToast('Error', result.message, 'error');
    }
}

// =============================================================================
// Auto-Refresh
// =============================================================================

let securityRefreshIntervalId = null;

function refreshSecurityPage() {
    loadFailedAttempts();
}

function updateSecurityRefreshInterval(interval) {
    interval = parseInt(interval);

    if (securityRefreshIntervalId) {
        clearInterval(securityRefreshIntervalId);
        securityRefreshIntervalId = null;
    }

    if (interval > 0) {
        securityRefreshIntervalId = setInterval(refreshSecurityPage, interval);
    }
}

// =============================================================================
// Init
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadAll();

    // Start auto-refresh (use same interval as dashboard, default 10s)
    const savedInterval = localStorage.getItem('adminRefreshInterval') || 10000;
    updateSecurityRefreshInterval(parseInt(savedInterval));
});

// Sync refresh interval when changed on another page
window.addEventListener('storage', function(e) {
    if (e.key === 'adminRefreshInterval') {
        updateSecurityRefreshInterval(parseInt(e.newValue) || 10000);
    }
});
