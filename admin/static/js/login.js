// SIP Wrapper Admin Login JavaScript

const _base = window.BASE_URL || '';

function setLang(lang) {
    fetch(_base + '/api/set-lang', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({lang: lang})
    }).then(() => location.reload());
}

document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);

    fetch(_base + '/login', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            window.location.href = _base + '/';
        } else {
            const alert = document.getElementById('error-alert');
            alert.textContent = data.error || 'Login failed';
            alert.classList.remove('d-none');
        }
    });
});
