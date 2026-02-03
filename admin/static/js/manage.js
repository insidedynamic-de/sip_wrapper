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
        loadSettings()
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
// Init
// =============================================================================

document.addEventListener('DOMContentLoaded', loadAll);
