#!/usr/bin/env python3
"""
InsideDynamic Wrapper - Admin Portal
Simple web interface for FreeSWITCH configuration management
"""

import os
import subprocess
import json
from flask import Flask, render_template, request, jsonify, session
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('ADMIN_SECRET', 'insidedynamic-wrapper-secret')

# Configuration
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin')
FS_CLI = '/usr/bin/fs_cli'

################################################################################
# Translations
################################################################################

TRANSLATIONS = {
    'de': {
        'title': 'InsideDynamic Wrapper - Admin',
        'dashboard': 'Dashboard',
        'config': 'Konfiguration',
        'gateways': 'Gateways',
        'users': 'Benutzer',
        'routing': 'Routing',
        'logs': 'Logs',
        'login': 'Anmelden',
        'logout': 'Abmelden',
        'username': 'Benutzername',
        'password': 'Passwort',
        'save': 'Speichern',
        'reload': 'Neu laden',
        'status': 'Status',
        'online': 'Online',
        'offline': 'Offline',
        'registered': 'Registriert',
        'not_registered': 'Nicht registriert',
        'gateway_status': 'Gateway Status',
        'user_registrations': 'Benutzer Registrierungen',
        'environment': 'Umgebungsvariablen',
        'license': 'Lizenz',
        'client': 'Kunde',
        'domain': 'Domain',
        'external_ip': 'Externe IP',
        'codecs': 'Codecs',
        'language': 'Sprache',
        'german': 'Deutsch',
        'english': 'Englisch',
        'apply_changes': 'Änderungen anwenden',
        'restart_required': 'Neustart erforderlich',
        'success': 'Erfolgreich',
        'error': 'Fehler',
        'connection_error': 'Verbindungsfehler zu FreeSWITCH',
        'profile': 'Profil',
        'extension': 'Nebenstelle',
        'ip_address': 'IP-Adresse',
        'user_agent': 'User-Agent',
        'contact': 'Kontakt',
        'outbound_routing': 'Ausgehende Routen',
        'inbound_routing': 'Eingehende Routen',
        'user_routing': 'Benutzer-Routen',
        'default_gateway': 'Standard-Gateway',
        'default_extension': 'Standard-Nebenstelle',
        'pattern': 'Muster',
        'destination': 'Ziel',
        'did': 'DID/Rufnummer',
        'no_routes': 'Keine Routen konfiguriert',
    },
    'en': {
        'title': 'InsideDynamic Wrapper - Admin',
        'dashboard': 'Dashboard',
        'config': 'Configuration',
        'gateways': 'Gateways',
        'users': 'Users',
        'routing': 'Routing',
        'logs': 'Logs',
        'login': 'Login',
        'logout': 'Logout',
        'username': 'Username',
        'password': 'Password',
        'save': 'Save',
        'reload': 'Reload',
        'status': 'Status',
        'online': 'Online',
        'offline': 'Offline',
        'registered': 'Registered',
        'not_registered': 'Not registered',
        'gateway_status': 'Gateway Status',
        'user_registrations': 'User Registrations',
        'environment': 'Environment Variables',
        'license': 'License',
        'client': 'Client',
        'domain': 'Domain',
        'external_ip': 'External IP',
        'codecs': 'Codecs',
        'language': 'Language',
        'german': 'German',
        'english': 'English',
        'apply_changes': 'Apply Changes',
        'restart_required': 'Restart Required',
        'success': 'Success',
        'error': 'Error',
        'connection_error': 'Connection error to FreeSWITCH',
        'profile': 'Profile',
        'extension': 'Extension',
        'ip_address': 'IP Address',
        'user_agent': 'User-Agent',
        'contact': 'Contact',
        'outbound_routing': 'Outbound Routes',
        'inbound_routing': 'Inbound Routes',
        'user_routing': 'User Routes',
        'default_gateway': 'Default Gateway',
        'default_extension': 'Default Extension',
        'pattern': 'Pattern',
        'destination': 'Destination',
        'did': 'DID/Number',
        'no_routes': 'No routes configured',
    }
}

def get_lang():
    return session.get('lang', 'de')

def t(key):
    lang = get_lang()
    return TRANSLATIONS.get(lang, TRANSLATIONS['de']).get(key, key)

@app.context_processor
def inject_translations():
    return {'t': t, 'lang': get_lang()}

################################################################################
# Authentication
################################################################################

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return render_template('login.html')
        return f(*args, **kwargs)
    return decorated_function

################################################################################
# FreeSWITCH CLI Helper
################################################################################

def fs_cli(command):
    """Execute FreeSWITCH CLI command and return output"""
    try:
        result = subprocess.run(
            [FS_CLI, '-x', command],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        return None
    except Exception as e:
        return None

def parse_sofia_status():
    """Parse sofia status output"""
    output = fs_cli('sofia status')
    if not output:
        return []

    profiles = []
    for line in output.split('\n'):
        if 'profile' in line.lower() and ('internal' in line.lower() or 'external' in line.lower()):
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                status = 'online' if 'RUNNING' in line else 'offline'
                profiles.append({'name': name, 'status': status})
    return profiles

def parse_gateway_status():
    """Parse gateway status"""
    output = fs_cli('sofia status gateway')
    if not output:
        return []

    gateways = []
    for line in output.split('\n'):
        line = line.strip()
        if not line or line.startswith('=') or 'Name' in line:
            continue
        parts = line.split()
        if len(parts) >= 3:
            gateways.append({
                'name': parts[0],
                'status': 'online' if 'REGED' in line or 'NOREG' in line else 'offline',
                'registered': 'REGED' in line
            })
    return gateways

def parse_registrations():
    """Parse user registrations"""
    output = fs_cli('sofia status profile internal reg')
    if not output:
        return []

    registrations = []
    current_reg = {}

    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('Call-ID:'):
            if current_reg:
                registrations.append(current_reg)
            current_reg = {}
        elif ':' in line:
            key, _, value = line.partition(':')
            key = key.strip().lower().replace(' ', '_').replace('-', '_')
            value = value.strip()
            if key in ['user', 'contact', 'agent', 'status', 'host']:
                current_reg[key] = value

    if current_reg:
        registrations.append(current_reg)

    return registrations

################################################################################
# Routes
################################################################################

@app.route('/')
@login_required
def dashboard():
    profiles = parse_sofia_status()
    gateways = parse_gateway_status()
    registrations = parse_registrations()

    return render_template('dashboard.html',
        profiles=profiles,
        gateways=gateways,
        registrations=registrations,
        config={
            'LICENSE_KEY': os.environ.get('LICENSE_KEY', 'UNLICENSED'),
            'CLIENT_NAME': os.environ.get('CLIENT_NAME', ''),
            'FS_DOMAIN': os.environ.get('FS_DOMAIN', ''),
            'EXTERNAL_SIP_IP': os.environ.get('EXTERNAL_SIP_IP', ''),
            'CODEC_PREFS': os.environ.get('CODEC_PREFS', ''),
        }
    )

@app.route('/config')
@login_required
def config():
    env_vars = {
        'LICENSE_KEY': os.environ.get('LICENSE_KEY', ''),
        'CLIENT_NAME': os.environ.get('CLIENT_NAME', ''),
        'FS_DOMAIN': os.environ.get('FS_DOMAIN', ''),
        'EXTERNAL_SIP_IP': os.environ.get('EXTERNAL_SIP_IP', ''),
        'EXTERNAL_RTP_IP': os.environ.get('EXTERNAL_RTP_IP', ''),
        'USERS': os.environ.get('USERS', ''),
        'ACL_USERS': os.environ.get('ACL_USERS', ''),
        'GATEWAYS': os.environ.get('GATEWAYS', ''),
        'DEFAULT_GATEWAY': os.environ.get('DEFAULT_GATEWAY', ''),
        'DEFAULT_EXTENSION': os.environ.get('DEFAULT_EXTENSION', ''),
        'CODEC_PREFS': os.environ.get('CODEC_PREFS', ''),
        'OUTBOUND_CODEC_PREFS': os.environ.get('OUTBOUND_CODEC_PREFS', ''),
        'INTERNAL_SIP_PORT': os.environ.get('INTERNAL_SIP_PORT', '5060'),
        'EXTERNAL_SIP_PORT': os.environ.get('EXTERNAL_SIP_PORT', '5080'),
    }
    return render_template('config.html', env_vars=env_vars)

@app.route('/gateways')
@login_required
def gateways():
    gateways = parse_gateway_status()
    return render_template('gateways.html', gateways=gateways)

def parse_configured_users():
    """Parse USERS and ACL_USERS environment variables"""
    users_list = []

    # Parse USERS (format: username:password:extension,...)
    users_env = os.environ.get('USERS', '')
    if users_env:
        for user_str in users_env.split(','):
            parts = user_str.strip().split(':')
            if len(parts) >= 3:
                users_list.append({
                    'username': parts[0],
                    'extension': parts[2],
                    'type': 'auth',
                    'ip': None
                })

    # Parse ACL_USERS (format: username:ip|ip2:extension:callerid,...)
    acl_users_env = os.environ.get('ACL_USERS', '')
    if acl_users_env:
        for user_str in acl_users_env.split(','):
            parts = user_str.strip().split(':')
            if len(parts) >= 3:
                users_list.append({
                    'username': parts[0],
                    'extension': parts[2] if len(parts) > 2 else '',
                    'type': 'acl',
                    'ip': parts[1] if len(parts) > 1 else ''
                })

    return users_list

@app.route('/users')
@login_required
def users():
    registrations = parse_registrations()
    configured_users = parse_configured_users()

    # Build user list with online/offline status
    users_with_status = []
    registered_users = {r.get('user', '').split('@')[0]: r for r in registrations}

    for user in configured_users:
        username = user['username']
        is_online = username in registered_users
        reg_info = registered_users.get(username, {})

        users_with_status.append({
            'username': username,
            'extension': user['extension'],
            'type': user['type'],
            'ip': user.get('ip'),
            'online': is_online,
            'contact': reg_info.get('contact', ''),
            'agent': reg_info.get('agent', ''),
            'host': reg_info.get('host', '')
        })

    return render_template('users.html', users=users_with_status, registrations=registrations)

def parse_routing_config():
    """Parse routing configuration from environment variables"""
    routing = {
        'outbound_routes': [],
        'inbound_routes': [],
        'user_routes': [],
        'default_gateway': os.environ.get('DEFAULT_GATEWAY', ''),
        'default_extension': os.environ.get('DEFAULT_EXTENSION', ''),
        'default_country_code': os.environ.get('DEFAULT_COUNTRY_CODE', '49'),
    }

    # Parse OUTBOUND_ROUTES (format: pattern:gateway:prepend:strip,...)
    outbound_env = os.environ.get('OUTBOUND_ROUTES', '')
    if outbound_env:
        for route in outbound_env.split(','):
            parts = route.strip().split(':')
            if len(parts) >= 2:
                routing['outbound_routes'].append({
                    'pattern': parts[0],
                    'gateway': parts[1],
                    'prepend': parts[2] if len(parts) > 2 else '',
                    'strip': parts[3] if len(parts) > 3 else '',
                })

    # Parse INBOUND_ROUTES (format: DID:extension,...)
    inbound_env = os.environ.get('INBOUND_ROUTES', '')
    if inbound_env:
        for route in inbound_env.split(','):
            parts = route.strip().split(':')
            if len(parts) >= 2:
                routing['inbound_routes'].append({
                    'did': parts[0],
                    'extension': parts[1],
                })

    # Parse OUTBOUND_USER_ROUTES (format: username:gateway,...)
    user_routes_env = os.environ.get('OUTBOUND_USER_ROUTES', '')
    if user_routes_env:
        for route in user_routes_env.split(','):
            parts = route.strip().split(':')
            if len(parts) >= 2:
                routing['user_routes'].append({
                    'username': parts[0],
                    'gateway': parts[1],
                })

    return routing

@app.route('/routing')
@login_required
def routing():
    routing_config = parse_routing_config()
    gateways = parse_gateway_status()
    configured_users = parse_configured_users()

    # Create user extension map for display
    user_extensions = {u['username']: u['extension'] for u in configured_users}

    # Add extension info to user routes
    for route in routing_config['user_routes']:
        route['extension'] = user_extensions.get(route['username'], '-')

    return render_template('routing.html', routing=routing_config, gateways=gateways, users=configured_users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid credentials'})
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return render_template('login.html')

@app.route('/api/set-lang', methods=['POST'])
def set_lang():
    lang = request.json.get('lang', 'de')
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return jsonify({'success': True, 'lang': lang})

################################################################################
# API Endpoints
################################################################################

@app.route('/api/status')
@login_required
def api_status():
    return jsonify({
        'profiles': parse_sofia_status(),
        'gateways': parse_gateway_status(),
        'registrations': parse_registrations()
    })

@app.route('/api/gateways')
@login_required
def api_gateways():
    return jsonify(parse_gateway_status())

@app.route('/api/registrations')
@login_required
def api_registrations():
    return jsonify(parse_registrations())

@app.route('/api/reload', methods=['POST'])
@login_required
def api_reload():
    result = fs_cli('reloadxml')
    if result is not None:
        fs_cli('sofia profile internal rescan')
        fs_cli('sofia profile external rescan')
        return jsonify({'success': True, 'message': 'Configuration reloaded'})
    return jsonify({'success': False, 'error': 'Failed to reload'})

@app.route('/api/fs-cli', methods=['POST'])
@login_required
def api_fs_cli():
    command = request.json.get('command', '')
    if not command:
        return jsonify({'success': False, 'error': 'No command provided'})

    # Security: only allow safe commands
    safe_commands = ['sofia status', 'show channels', 'show calls', 'status', 'version']
    if not any(command.startswith(cmd) for cmd in safe_commands):
        return jsonify({'success': False, 'error': 'Command not allowed'})

    result = fs_cli(command)
    if result is not None:
        return jsonify({'success': True, 'output': result})
    return jsonify({'success': False, 'error': 'Command failed'})

################################################################################
# Main
################################################################################

if __name__ == '__main__':
    port = int(os.environ.get('ADMIN_PORT', 8888))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print(f"""
================================================================================
  InsideDynamic Wrapper - Admin Portal
================================================================================
  URL: http://localhost:{port}
  User: {ADMIN_USER}
  Pass: {'*' * len(ADMIN_PASS)}
================================================================================
""")

    app.run(host='0.0.0.0', port=port, debug=debug)
