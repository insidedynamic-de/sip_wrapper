// SIP Wrapper Landing Page JavaScript

// Configuration API URL (change to your deployed URL)
const CONFIG_API_URL = '/api/config';

// Load live configuration from API
async function loadConfig() {
    // Skip if running from file:// (local testing)
    if (window.location.protocol === 'file:') return;

    try {
        const response = await fetch(CONFIG_API_URL);
        if (!response.ok) throw new Error('Config not available');

        const config = await response.json();

        // Show the config section
        document.getElementById('live-config').style.display = 'block';

        // Render Users
        const usersDiv = document.getElementById('config-users');
        if (config.users && config.users.length > 0) {
            usersDiv.innerHTML = config.users.map(u =>
                `<div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee;">
                    <code>${u.username}</code>
                    <span style="background: #e0f2fe; padding: 2px 8px; border-radius: 4px; font-size: 0.875rem;">${u.extension}</span>
                </div>`
            ).join('');
        } else {
            usersDiv.innerHTML = '<span style="color: #999;">Keine Benutzer</span>';
        }

        // Render Inbound Routes
        const inboundDiv = document.getElementById('config-inbound');
        if (config.inbound_routes && config.inbound_routes.length > 0) {
            inboundDiv.innerHTML = config.inbound_routes.map(r =>
                `<div style="display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid #eee;">
                    <span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.875rem;">${r.gateway}</span>
                    <span>→</span>
                    <code>${r.extension}</code>
                </div>`
            ).join('');
        } else {
            inboundDiv.innerHTML = '<span style="color: #999;">Keine Inbound-Routen</span>';
        }

        // Render Outbound Routes
        const outboundDiv = document.getElementById('config-outbound');
        if (config.outbound_user_routes && config.outbound_user_routes.length > 0) {
            outboundDiv.innerHTML = config.outbound_user_routes.map(r =>
                `<div style="display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid #eee;">
                    <code>${r.username}</code>
                    <span>→</span>
                    <span style="background: #2563eb; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.875rem;">${r.gateway}</span>
                </div>`
            ).join('');
        } else if (config.default_gateway) {
            outboundDiv.innerHTML = `<div>Default: <span style="background: #2563eb; color: white; padding: 2px 8px; border-radius: 4px;">${config.default_gateway}</span></div>`;
        } else {
            outboundDiv.innerHTML = '<span style="color: #999;">Keine Outbound-Routen</span>';
        }

        // Render Gateways
        const gatewaysDiv = document.getElementById('config-gateways');
        if (config.gateways && config.gateways.length > 0) {
            gatewaysDiv.innerHTML = config.gateways.map(g =>
                `<div style="display: inline-block; background: #f1f5f9; padding: 4px 12px; border-radius: 20px; margin: 4px; font-size: 0.875rem;">
                    ${g.name}
                </div>`
            ).join('');
        } else {
            gatewaysDiv.innerHTML = '<span style="color: #999;">Keine Gateways</span>';
        }

    } catch (error) {
        console.log('Config not available:', error.message);
        // Keep section hidden if config not available
    }
}

// Load and render integrations from JS data
function loadIntegrations() {
    const data = window.INTEGRATIONS_DATA;
    if (!data) {
        document.getElementById('providers-table').innerHTML = '<p style="color: #999;">Keine Daten</p>';
        return;
    }

    const statusLabels = data.status_labels;

    // Helper function to render status badge
    function renderStatus(status) {
        const info = statusLabels[status] || {label: status, class: 'status-pending'};
        return `<span class="status ${info.class}">${info.label}</span>`;
    }

    // Render Providers table
    const providersDiv = document.getElementById('providers-table');
    if (data.providers && data.providers.length > 0) {
        providersDiv.innerHTML = `
            <table class="integration-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Beschreibung</th>
                        <th colspan="2">Outbound</th>
                        <th colspan="2">Inbound</th>
                    </tr>
                    <tr style="font-size: 0.75rem; color: #666;">
                        <th></th>
                        <th></th>
                        <th>Wrapper</th>
                        <th>AI</th>
                        <th>Wrapper</th>
                        <th>AI</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.providers.map(p => `
                        <tr>
                            <td><strong>${p.name}</strong> ${p.type || ''}</td>
                            <td>${p.description}</td>
                            <td>${renderStatus(p.outbound_wrapper)}</td>
                            <td>${renderStatus(p.outbound_ai)}</td>
                            <td>${renderStatus(p.inbound_wrapper)}</td>
                            <td>${renderStatus(p.inbound_ai)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // Render AI Platforms table
    const aiDiv = document.getElementById('ai-platforms-table');
    if (data.ai_platforms && data.ai_platforms.length > 0) {
        aiDiv.innerHTML = `
            <table class="integration-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Beschreibung</th>
                        <th colspan="2">Outbound</th>
                        <th colspan="2">Inbound</th>
                    </tr>
                    <tr style="font-size: 0.75rem; color: #666;">
                        <th></th>
                        <th></th>
                        <th>Wrapper</th>
                        <th>AI</th>
                        <th>Wrapper</th>
                        <th>AI</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.ai_platforms.map(p => `
                        <tr>
                            <td><strong>${p.name}</strong></td>
                            <td>${p.description}</td>
                            <td>${renderStatus(p.outbound_wrapper)}</td>
                            <td>${renderStatus(p.outbound_ai)}</td>
                            <td>${renderStatus(p.inbound_wrapper)}</td>
                            <td>${renderStatus(p.inbound_ai)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadIntegrations();
    loadConfig();
});
