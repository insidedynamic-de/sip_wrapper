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
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            updateDashboardUI(data);
            updateUsersUI(data.registrations);
            updateGatewaysUI(data.gateways);
        })
        .catch(err => console.error('Refresh failed:', err));
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
