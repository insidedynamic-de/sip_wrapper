// SIP Wrapper Admin - CRUD Management JavaScript

// Data cache
let users = [];
let aclUsers = [];
let gateways = [];
let routes = {};

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

async function apiPut(url, data) {
    const res = await fetch(url, {
        method: 'PUT',
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
// Load Data
// =============================================================================

async function loadAll() {
    await Promise.all([
        loadUsers(),
        loadAclUsers(),
        loadGateways(),
        loadRoutes(),
        loadSettings(),
        loadSecurity()
    ]);
    updateGatewaySelects();
    updateUserSelects();
}

async function loadUsers() {
    users = await apiGet('/api/crud/users');
    renderUsers();
}

async function loadAclUsers() {
    aclUsers = await apiGet('/api/crud/acl-users');
    renderAclUsers();
}

async function loadGateways() {
    gateways = await apiGet('/api/crud/gateways');
    renderGateways();
}

async function loadRoutes() {
    routes = await apiGet('/api/crud/routes');
    renderRoutes();
}

async function loadSettings() {
    const settings = await apiGet('/api/crud/settings');
    document.getElementById('setting-fs-domain').value = settings.fs_domain || '';
    document.getElementById('setting-external-sip-ip').value = settings.external_sip_ip || '';
    document.getElementById('setting-internal-sip-port').value = settings.internal_sip_port || 5060;
    document.getElementById('setting-external-sip-port').value = settings.external_sip_port || 5080;
    document.getElementById('setting-codec-prefs').value = settings.codec_prefs || '';
    document.getElementById('setting-country-code').value = settings.default_country_code || '49';

    // Load license
    const license = await apiGet('/api/crud/license');
    document.getElementById('setting-license-key').value = license.key || '';
    document.getElementById('setting-client-name').value = license.client_name || '';

    // Load defaults (outbound_caller_id)
    const defaults = await apiGet('/api/crud/defaults');
    document.getElementById('setting-outbound-caller-id').value = defaults.outbound_caller_id || '';
}

// =============================================================================
// Render Tables
// =============================================================================

function renderUsers() {
    const tbody = document.querySelector('#users-table tbody');
    if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center">No users configured</td></tr>';
        return;
    }
    tbody.innerHTML = users.map(u => `
        <tr>
            <td><strong>${u.username}</strong></td>
            <td><span class="badge bg-primary">${u.extension}</span></td>
            <td>${u.enabled !== false ? '<span class="badge bg-success">Enabled</span>' : '<span class="badge bg-secondary">Disabled</span>'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editUser('${u.username}')"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteUser('${u.username}')"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

function renderAclUsers() {
    const tbody = document.querySelector('#acl-users-table tbody');
    if (!aclUsers.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center">No ACL users configured</td></tr>';
        return;
    }
    tbody.innerHTML = aclUsers.map(u => `
        <tr>
            <td><strong>${u.username}</strong></td>
            <td><code>${u.ip_address}</code></td>
            <td><span class="badge bg-primary">${u.extension || '-'}</span></td>
            <td>${u.caller_id || '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editAclUser('${u.username}')"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteAclUser('${u.username}')"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

function renderGateways() {
    const tbody = document.querySelector('#gateways-table tbody');
    if (!gateways.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center">No gateways configured</td></tr>';
        return;
    }
    tbody.innerHTML = gateways.map(g => `
        <tr>
            <td><strong>${g.name}</strong></td>
            <td>${g.host}</td>
            <td>${g.port || 5060}</td>
            <td>${g.username || '-'}</td>
            <td>${g.register ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-dash-circle text-secondary"></i>'}</td>
            <td>${g.enabled !== false ? '<span class="badge bg-success">Enabled</span>' : '<span class="badge bg-secondary">Disabled</span>'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editGateway('${g.name}')"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteGateway('${g.name}')"><i class="bi bi-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

function renderRoutes() {
    // Default routes
    document.getElementById('default-gateway').value = routes.default_gateway || '';
    document.getElementById('default-extension').value = routes.default_extension || '';

    // Inbound routes
    const inboundTbody = document.querySelector('#inbound-routes-table tbody');
    const inbound = routes.inbound || [];
    if (!inbound.length) {
        inboundTbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center">No inbound routes</td></tr>';
    } else {
        inboundTbody.innerHTML = inbound.map(r => `
            <tr>
                <td><code>${r.did}</code></td>
                <td><strong>${r.destination}</strong></td>
                <td><span class="badge ${r.destination_type === 'gateway' ? 'bg-warning' : 'bg-info'}">${r.destination_type}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteInboundRoute('${r.did}')"><i class="bi bi-trash"></i></button>
                </td>
            </tr>
        `).join('');
    }

    // User routes
    const userRoutesTbody = document.querySelector('#user-routes-table tbody');
    const userRoutes = routes.user_routes || [];
    if (!userRoutes.length) {
        userRoutesTbody.innerHTML = '<tr><td colspan="3" class="text-muted text-center">No user routes (using default gateway)</td></tr>';
    } else {
        userRoutesTbody.innerHTML = userRoutes.map(r => `
            <tr>
                <td><strong>${r.username}</strong></td>
                <td>${r.gateway}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteUserRoute('${r.username}')"><i class="bi bi-trash"></i></button>
                </td>
            </tr>
        `).join('');
    }
}

// =============================================================================
// Update Selects
// =============================================================================

function updateGatewaySelects() {
    const options = '<option value="">-- Select --</option>' +
        gateways.map(g => `<option value="${g.name}">${g.name}</option>`).join('');

    document.getElementById('default-gateway').innerHTML = options;
    document.getElementById('user-route-gateway').innerHTML = options;

    // Restore selected values
    document.getElementById('default-gateway').value = routes.default_gateway || '';
}

function updateUserSelects() {
    const allUsers = [...users, ...aclUsers];
    const options = allUsers.map(u => `<option value="${u.username}">${u.username}</option>`).join('');
    document.getElementById('user-route-user').innerHTML = options;
}

// =============================================================================
// Users CRUD
// =============================================================================

function showAddUserModal() {
    document.getElementById('userModalTitle').textContent = 'Add User';
    document.getElementById('user-edit-mode').value = '';
    document.getElementById('user-username').value = '';
    document.getElementById('user-username').disabled = false;
    document.getElementById('user-password').value = '';
    document.getElementById('user-extension').value = '';
    document.getElementById('user-enabled').checked = true;
    new bootstrap.Modal(document.getElementById('userModal')).show();
}

function editUser(username) {
    const user = users.find(u => u.username === username);
    if (!user) return;

    document.getElementById('userModalTitle').textContent = 'Edit User';
    document.getElementById('user-edit-mode').value = username;
    document.getElementById('user-username').value = user.username;
    document.getElementById('user-username').disabled = true;
    document.getElementById('user-password').value = user.password || '';
    document.getElementById('user-extension').value = user.extension || '';
    document.getElementById('user-enabled').checked = user.enabled !== false;
    new bootstrap.Modal(document.getElementById('userModal')).show();
}

async function saveUser() {
    const editMode = document.getElementById('user-edit-mode').value;
    const data = {
        username: document.getElementById('user-username').value,
        password: document.getElementById('user-password').value,
        extension: document.getElementById('user-extension').value,
        enabled: document.getElementById('user-enabled').checked
    };

    let result;
    if (editMode) {
        result = await apiPut(`/api/crud/users/${editMode}`, data);
    } else {
        result = await apiPost('/api/crud/users', data);
    }

    bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();

    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadUsers();
        updateUserSelects();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function deleteUser(username) {
    if (!confirm(`Delete user "${username}"?`)) return;

    const result = await apiDelete(`/api/crud/users/${username}`);
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadUsers();
        updateUserSelects();
    } else {
        showToast('Error', result.message, 'error');
    }
}

// =============================================================================
// ACL Users CRUD
// =============================================================================

function showAddAclUserModal() {
    document.getElementById('aclUserModalTitle').textContent = 'Add ACL User';
    document.getElementById('acl-user-edit-mode').value = '';
    document.getElementById('acl-user-username').value = '';
    document.getElementById('acl-user-username').disabled = false;
    document.getElementById('acl-user-ip').value = '';
    document.getElementById('acl-user-extension').value = '';
    document.getElementById('acl-user-callerid').value = '';
    new bootstrap.Modal(document.getElementById('aclUserModal')).show();
}

function editAclUser(username) {
    const user = aclUsers.find(u => u.username === username);
    if (!user) return;

    document.getElementById('aclUserModalTitle').textContent = 'Edit ACL User';
    document.getElementById('acl-user-edit-mode').value = username;
    document.getElementById('acl-user-username').value = user.username;
    document.getElementById('acl-user-username').disabled = true;
    document.getElementById('acl-user-ip').value = user.ip_address || '';
    document.getElementById('acl-user-extension').value = user.extension || '';
    document.getElementById('acl-user-callerid').value = user.caller_id || '';
    new bootstrap.Modal(document.getElementById('aclUserModal')).show();
}

async function saveAclUser() {
    const editMode = document.getElementById('acl-user-edit-mode').value;
    const data = {
        username: document.getElementById('acl-user-username').value,
        ip_address: document.getElementById('acl-user-ip').value,
        extension: document.getElementById('acl-user-extension').value,
        caller_id: document.getElementById('acl-user-callerid').value
    };

    let result;
    if (editMode) {
        result = await apiPut(`/api/crud/acl-users/${editMode}`, data);
    } else {
        result = await apiPost('/api/crud/acl-users', data);
    }

    bootstrap.Modal.getInstance(document.getElementById('aclUserModal')).hide();

    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadAclUsers();
        updateUserSelects();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function deleteAclUser(username) {
    if (!confirm(`Delete ACL user "${username}"?`)) return;

    const result = await apiDelete(`/api/crud/acl-users/${username}`);
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadAclUsers();
        updateUserSelects();
    } else {
        showToast('Error', result.message, 'error');
    }
}

// =============================================================================
// Gateways CRUD
// =============================================================================

function showAddGatewayModal() {
    document.getElementById('gatewayModalTitle').textContent = 'Add Gateway';
    document.getElementById('gateway-edit-mode').value = '';
    document.getElementById('gateway-name').value = '';
    document.getElementById('gateway-name').disabled = false;
    document.getElementById('gateway-host').value = '';
    document.getElementById('gateway-port').value = '5060';
    document.getElementById('gateway-username').value = '';
    document.getElementById('gateway-password').value = '';
    document.getElementById('gateway-auth-username').value = '';
    document.getElementById('gateway-transport').value = 'udp';
    document.getElementById('gateway-register').checked = true;
    new bootstrap.Modal(document.getElementById('gatewayModal')).show();
}

function editGateway(name) {
    const gw = gateways.find(g => g.name === name);
    if (!gw) return;

    document.getElementById('gatewayModalTitle').textContent = 'Edit Gateway';
    document.getElementById('gateway-edit-mode').value = name;
    document.getElementById('gateway-name').value = gw.name;
    document.getElementById('gateway-name').disabled = true;
    document.getElementById('gateway-host').value = gw.host || '';
    document.getElementById('gateway-port').value = gw.port || 5060;
    document.getElementById('gateway-username').value = gw.username || '';
    document.getElementById('gateway-password').value = gw.password || '';
    document.getElementById('gateway-auth-username').value = gw.auth_username || '';
    document.getElementById('gateway-transport').value = gw.transport || 'udp';
    document.getElementById('gateway-register').checked = gw.register !== false;
    new bootstrap.Modal(document.getElementById('gatewayModal')).show();
}

async function saveGateway() {
    const editMode = document.getElementById('gateway-edit-mode').value;
    const data = {
        name: document.getElementById('gateway-name').value,
        host: document.getElementById('gateway-host').value,
        port: parseInt(document.getElementById('gateway-port').value) || 5060,
        username: document.getElementById('gateway-username').value,
        password: document.getElementById('gateway-password').value,
        auth_username: document.getElementById('gateway-auth-username').value,
        transport: document.getElementById('gateway-transport').value,
        register: document.getElementById('gateway-register').checked
    };

    let result;
    if (editMode) {
        result = await apiPut(`/api/crud/gateways/${editMode}`, data);
    } else {
        result = await apiPost('/api/crud/gateways', data);
    }

    bootstrap.Modal.getInstance(document.getElementById('gatewayModal')).hide();

    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadGateways();
        updateGatewaySelects();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function deleteGateway(name) {
    if (!confirm(`Delete gateway "${name}"?`)) return;

    const result = await apiDelete(`/api/crud/gateways/${name}`);
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadGateways();
        updateGatewaySelects();
    } else {
        showToast('Error', result.message, 'error');
    }
}

// =============================================================================
// Routes CRUD
// =============================================================================

async function saveDefaultRoutes() {
    const data = {
        default_gateway: document.getElementById('default-gateway').value,
        default_extension: document.getElementById('default-extension').value
    };

    const result = await apiPut('/api/crud/routes', data);
    if (result.success) {
        showToast('Success', 'Default routes saved', 'success');
        await loadRoutes();
    } else {
        showToast('Error', result.message, 'error');
    }
}

function showAddInboundRouteModal() {
    document.getElementById('inbound-did').value = '';
    document.getElementById('inbound-dest-type').value = 'extension';
    document.getElementById('inbound-destination').value = '';
    new bootstrap.Modal(document.getElementById('inboundRouteModal')).show();
}

async function saveInboundRoute() {
    const data = {
        did: document.getElementById('inbound-did').value,
        destination_type: document.getElementById('inbound-dest-type').value,
        destination: document.getElementById('inbound-destination').value
    };

    const result = await apiPost('/api/crud/routes/inbound', data);
    bootstrap.Modal.getInstance(document.getElementById('inboundRouteModal')).hide();

    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadRoutes();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function deleteInboundRoute(did) {
    if (!confirm(`Delete inbound route for "${did}"?`)) return;

    const result = await apiDelete(`/api/crud/routes/inbound/${encodeURIComponent(did)}`);
    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadRoutes();
    } else {
        showToast('Error', result.message, 'error');
    }
}

function showAddUserRouteModal() {
    new bootstrap.Modal(document.getElementById('userRouteModal')).show();
}

async function saveUserRoute() {
    const data = {
        username: document.getElementById('user-route-user').value,
        gateway: document.getElementById('user-route-gateway').value
    };

    const result = await apiPost('/api/crud/routes/user', data);
    bootstrap.Modal.getInstance(document.getElementById('userRouteModal')).hide();

    if (result.success) {
        showToast('Success', result.message, 'success');
        await loadRoutes();
    } else {
        showToast('Error', result.message, 'error');
    }
}

async function deleteUserRoute(username) {
    // For now, set to empty gateway (remove route)
    const data = { username, gateway: '' };
    const result = await apiPost('/api/crud/routes/user', data);
    if (result.success) {
        showToast('Success', 'User route removed', 'success');
        await loadRoutes();
    }
}

// =============================================================================
// Settings
// =============================================================================

async function saveSettings() {
    // Save settings
    const settingsData = {
        fs_domain: document.getElementById('setting-fs-domain').value,
        external_sip_ip: document.getElementById('setting-external-sip-ip').value,
        internal_sip_port: parseInt(document.getElementById('setting-internal-sip-port').value) || 5060,
        external_sip_port: parseInt(document.getElementById('setting-external-sip-port').value) || 5080,
        codec_prefs: document.getElementById('setting-codec-prefs').value,
        default_country_code: document.getElementById('setting-country-code').value
    };

    // Save license
    const licenseData = {
        key: document.getElementById('setting-license-key').value,
        client_name: document.getElementById('setting-client-name').value
    };

    // Save defaults (outbound_caller_id)
    const defaultsData = {
        outbound_caller_id: document.getElementById('setting-outbound-caller-id').value
    };

    const results = await Promise.all([
        apiPut('/api/crud/settings', settingsData),
        apiPut('/api/crud/license', licenseData),
        apiPut('/api/crud/defaults', defaultsData)
    ]);

    const allSuccess = results.every(r => r.success);
    if (allSuccess) {
        showToast('Success', 'Settings saved', 'success');
    } else {
        showToast('Error', 'Failed to save some settings', 'error');
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
// Config Import / Export
// =============================================================================

async function exportConfig() {
    try {
        const response = await fetch('/api/config/export');
        if (!response.ok) {
            throw new Error('Export failed');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'wrapper_config.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showToast('Success', 'Config exported', 'success');
    } catch (e) {
        showToast('Error', 'Export failed: ' + e.message, 'error');
    }
}

async function importConfig() {
    const fileInput = document.getElementById('config-file-input');
    if (!fileInput.files.length) {
        showToast('Error', 'Please select a JSON file', 'error');
        return;
    }

    const file = fileInput.files[0];
    if (!file.name.endsWith('.json')) {
        showToast('Error', 'Please select a .json file', 'error');
        return;
    }

    if (!confirm('Import config will overwrite all current settings. Continue?')) {
        return;
    }

    try {
        const text = await file.text();
        const json = JSON.parse(text);

        const response = await fetch('/api/config/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(json)
        });

        const result = await response.json();
        if (result.success) {
            showToast('Success', result.message, 'success');
            fileInput.value = '';
            await loadAll();
        } else {
            showToast('Error', result.message, 'error');
        }
    } catch (e) {
        showToast('Error', 'Invalid JSON file: ' + e.message, 'error');
    }
}

async function importFromEnv() {
    if (!confirm('Import from ENV variables? This will merge ENV config into current settings.')) {
        return;
    }

    try {
        const result = await apiPost('/api/crud/import-env', {});
        if (result.success) {
            showToast('Success', result.message, 'success');
            await loadAll();
        } else {
            showToast('Error', result.message, 'error');
        }
    } catch (e) {
        showToast('Error', 'Import failed: ' + e.message, 'error');
    }
}

// =============================================================================
// URL Hash Navigation
// =============================================================================

function handleHashNavigation() {
    const hash = window.location.hash.substring(1); // Remove #
    if (hash) {
        // Find tab button with matching id (e.g., #gateways -> gateways-btn)
        const btnId = hash + '-btn';
        const tabButton = document.getElementById(btnId);
        if (tabButton) {
            const tab = new bootstrap.Tab(tabButton);
            tab.show();
        }
    }
}

function updateHashOnTabChange() {
    // Listen to tab changes and update URL hash
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            const targetId = e.target.getAttribute('data-bs-target');
            if (targetId) {
                // Convert #users-tab to users
                const hash = targetId.replace('#', '').replace('-tab', '');
                history.replaceState(null, null, '#' + hash);
            }
        });
    });
}

// =============================================================================
// Auto-Refresh for Manage Page
// =============================================================================

let manageRefreshIntervalId = null;
const MANAGE_REFRESH_KEY = 'manageRefreshInterval';

function refreshManagePage() {
    // Only refresh if on Security tab
    const securityTab = document.getElementById('security-tab');
    if (securityTab && securityTab.classList.contains('active')) {
        loadFailedAttempts();
    }
}

function updateManageRefreshInterval(interval) {
    interval = parseInt(interval);
    localStorage.setItem(MANAGE_REFRESH_KEY, interval);

    if (manageRefreshIntervalId) {
        clearInterval(manageRefreshIntervalId);
        manageRefreshIntervalId = null;
    }

    if (interval > 0) {
        manageRefreshIntervalId = setInterval(refreshManagePage, interval);
    }
}

// =============================================================================
// Init
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadAll();
    handleHashNavigation();
    updateHashOnTabChange();

    // Start auto-refresh (use same interval as dashboard, default 5s)
    const savedInterval = localStorage.getItem('adminRefreshInterval') || 5000;
    updateManageRefreshInterval(parseInt(savedInterval));
});

// Handle back/forward navigation
window.addEventListener('hashchange', handleHashNavigation);

// Sync refresh interval when changed on another page (dashboard)
window.addEventListener('storage', function(e) {
    if (e.key === 'adminRefreshInterval') {
        updateManageRefreshInterval(parseInt(e.newValue) || 5000);
    }
});

// =============================================================================
// Security - Blacklist / Whitelist
// =============================================================================

let securityData = { blacklist: [], whitelist: [], whitelist_enabled: false };

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
    } catch (e) {
        console.error('Failed to load security:', e);
    }
}

function renderBlacklist() {
    const container = document.getElementById('blacklist-container');
    if (!container) return;

    const list = securityData.blacklist || [];
    if (list.length === 0) {
        container.innerHTML = '<div class="p-3 text-center text-muted"><i class="bi bi-shield-check me-2"></i>No blocked IPs</div>';
        return;
    }

    let html = '<table class="table table-sm table-hover mb-0"><tbody>';
    list.forEach(entry => {
        html += `<tr>
            <td>
                <code class="text-danger">${entry.ip}</code>
                ${entry.comment ? `<small class="text-muted d-block">${entry.comment}</small>` : ''}
            </td>
            <td class="text-end">
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
