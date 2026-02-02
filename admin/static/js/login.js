// SIP Wrapper Admin Login JavaScript

function setLang(lang) {
    fetch('/api/set-lang', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({lang: lang})
    }).then(() => location.reload());
}

document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);

    fetch('/login', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/';
        } else {
            const alert = document.getElementById('error-alert');
            alert.textContent = data.error || 'Login failed';
            alert.classList.remove('d-none');
        }
    });
});
