#!/usr/bin/env python3
"""
InsideDynamic Wrapper - Admin Portal
Simple web interface for FreeSWITCH configuration management
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from functools import wraps

# Config store for CRUD operations
import config_store

# Load .env file for local development
try:
    from dotenv import load_dotenv
    # Look for .env in admin folder or parent folder
    env_paths = [
        Path(__file__).parent / '.env',
        Path(__file__).parent.parent / '.env'
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment from: {env_path}")
            break
except ImportError:
    pass  # dotenv not installed, use system environment

app = Flask(__name__)
app.secret_key = os.environ.get('ADMIN_SECRET', 'insidedynamic-wrapper-secret')

# Configuration
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin')

# FreeSWITCH connection settings
FS_HOST = os.environ.get('FS_HOST', '127.0.0.1')
FS_PORT = int(os.environ.get('FS_PORT', '8021'))
FS_PASS = os.environ.get('FS_PASS', 'ClueCon')

# Security: IP-based access control for FS commands
# Format: comma-separated IPs or CIDR ranges
# Special values: 0.0.0.0 = allow all, 127.0.0.1 = localhost only (default)
FS_ALLOWED_IPS = os.environ.get('FS_ALLOWED_IPS', '127.0.0.1').split(',')
FS_ALLOWED_IPS = [ip.strip() for ip in FS_ALLOWED_IPS if ip.strip()]

# Try to import ESL library
try:
    from greenswitch import InboundESL
    ESL_AVAILABLE = True
except ImportError:
    ESL_AVAILABLE = False
    print("WARNING: greenswitch not installed - FreeSWITCH commands will not work")

# Try to import ipaddress for CIDR matching
try:
    import ipaddress
    IPADDRESS_AVAILABLE = True
except ImportError:
    IPADDRESS_AVAILABLE = False

def ip_matches(client_ip, allowed_pattern):
    """Check if client IP matches allowed pattern (IP or CIDR)"""
    if allowed_pattern == '0.0.0.0':
        return True  # Allow all
    if client_ip == allowed_pattern:
        return True
    # Try CIDR matching
    if IPADDRESS_AVAILABLE and '/' in allowed_pattern:
        try:
            network = ipaddress.ip_network(allowed_pattern, strict=False)
            client = ipaddress.ip_address(client_ip)
            return client in network
        except ValueError:
            pass
    return False

def fs_allowed():
    """Check if FreeSWITCH commands are allowed for this request"""
    try:
        client_ip = request.remote_addr
        # Handle IPv6 localhost
        if client_ip == '::1':
            client_ip = '127.0.0.1'
        for allowed in FS_ALLOWED_IPS:
            if ip_matches(client_ip, allowed):
                return True
        return False
    except RuntimeError:
        # Outside request context - allow (startup, etc.)
        return True

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
    """Execute FreeSWITCH CLI command via ESL

    Uses ESL (Event Socket Library) for direct Python connection.
    No fs_cli binary required.

    Connection: FS_HOST:FS_PORT with FS_PASS
    """
    if not ESL_AVAILABLE:
        print("ESL not available - install greenswitch")
        return None

    try:
        esl = InboundESL(host=FS_HOST, port=FS_PORT, password=FS_PASS)
        esl.connect()
        result = esl.send(f'api {command}')
        esl.stop()
        if result and result.data:
            data = result.data
            # Handle both bytes and str (greenswitch version dependent)
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            return data.strip()
        return None
    except Exception as e:
        print(f"ESL error ({FS_HOST}:{FS_PORT}): {e}")
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
        # Skip summary lines like "6 total" or lines starting with numbers
        if line[0].isdigit():
            continue
        # Skip lines containing "total" or other summary keywords
        if 'total' in line.lower():
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
    # Check if FS commands are allowed (IP-based security)
    fs_access = fs_allowed()

    profiles = parse_sofia_status() if fs_access else []
    gateways = parse_gateway_status() if fs_access else []
    registrations = parse_registrations() if fs_access else []

    return render_template('dashboard.html',
        profiles=profiles,
        gateways=gateways,
        registrations=registrations,
        fs_access=fs_access,
        client_ip=request.remote_addr,
        config={
            'LICENSE_KEY': os.environ.get('LICENSE_KEY', 'UNLICENSED'),
            'CLIENT_NAME': os.environ.get('CLIENT_NAME', ''),
            'FS_DOMAIN': os.environ.get('FS_DOMAIN', ''),
            'EXTERNAL_SIP_IP': os.environ.get('EXTERNAL_SIP_IP', ''),
            'CODEC_PREFS': os.environ.get('CODEC_PREFS', ''),
            'FS_HOST': FS_HOST,
            'FS_PORT': FS_PORT,
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

@app.route('/manage')
@login_required
def manage():
    return render_template('manage.html')

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
    """Parse routing configuration from JSON file (generated by provision.sh)"""
    json_file = '/var/lib/freeswitch/routing_config.json'

    routing = {
        'outbound_routes': [],
        'inbound_routes': [],
        'user_routes': [],
        'gateways': [],
        'users': [],
        'default_gateway': '',
        'default_extension': '',
        'default_country_code': '49',
    }

    # Try to read from JSON file first
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r') as f:
                config = json.load(f)
                routing['inbound_routes'] = config.get('inbound_routes', [])
                routing['user_routes'] = config.get('outbound_user_routes', [])
                routing['gateways'] = config.get('gateways', [])
                routing['users'] = config.get('users', [])
                routing['default_gateway'] = config.get('default_gateway', '')
                routing['default_extension'] = config.get('default_extension', '')
                routing['default_country_code'] = config.get('default_country_code', '49')
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading routing config JSON: {e}")

    # Fallback to environment variables if JSON empty or missing
    if not routing['default_gateway']:
        routing['default_gateway'] = os.environ.get('DEFAULT_GATEWAY', '')
    if not routing['default_extension']:
        routing['default_extension'] = os.environ.get('DEFAULT_EXTENSION', '')
    if not routing['default_country_code'] or routing['default_country_code'] == '49':
        routing['default_country_code'] = os.environ.get('DEFAULT_COUNTRY_CODE', '49')

    # Parse OUTBOUND_ROUTES from env (pattern-based, not in JSON)
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

    # Fallback: Parse INBOUND_ROUTES from env if not in JSON
    if not routing['inbound_routes']:
        inbound_env = os.environ.get('INBOUND_ROUTES', '')
        if inbound_env:
            for route in inbound_env.split(','):
                parts = route.strip().split(':')
                if len(parts) >= 2:
                    routing['inbound_routes'].append({
                        'gateway': parts[0],
                        'extension': parts[1],
                    })

    # Fallback: Parse OUTBOUND_USER_ROUTES from env if not in JSON
    if not routing['user_routes']:
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

    # Use users from JSON config, fallback to env parsing
    if routing_config.get('users'):
        configured_users = routing_config['users']
    else:
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

@app.route('/api/config')
def api_config():
    """Public endpoint for routing config (for landing page)"""
    config_file = '/var/lib/freeswitch/routing_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return jsonify(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
    # Fallback to parsed config
    return jsonify(parse_routing_config())

@app.route('/api/config.js')
def api_config_js():
    """Serve config as JavaScript for static pages"""
    config_file = '/var/lib/freeswitch/routing_config.json'
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            config = parse_routing_config()
    else:
        config = parse_routing_config()

    js_content = f"window.ROUTING_CONFIG = {json.dumps(config)};"
    return js_content, 200, {'Content-Type': 'application/javascript'}

@app.route('/api/status')
@login_required
def api_status():
    if not fs_allowed():
        return jsonify({
            'profiles': [],
            'gateways': [],
            'registrations': [],
            'fs_access': False,
            'error': 'Access denied - IP not in FS_ALLOWED_IPS'
        })
    return jsonify({
        'profiles': parse_sofia_status(),
        'gateways': parse_gateway_status(),
        'registrations': parse_registrations(),
        'fs_access': True
    })

@app.route('/api/gateways')
@login_required
def api_gateways():
    if not fs_allowed():
        return jsonify({'error': 'Access denied', 'gateways': []})
    return jsonify(parse_gateway_status())

@app.route('/api/registrations')
@login_required
def api_registrations():
    if not fs_allowed():
        return jsonify({'error': 'Access denied', 'registrations': []})
    return jsonify(parse_registrations())

@app.route('/api/reload', methods=['POST'])
@login_required
def api_reload():
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied - IP not in FS_ALLOWED_IPS'})
    result = fs_cli('reloadxml')
    if result is not None:
        fs_cli('sofia profile internal rescan')
        fs_cli('sofia profile external rescan')
        return jsonify({'success': True, 'message': 'Configuration reloaded'})
    return jsonify({'success': False, 'error': 'Failed to connect to FreeSWITCH'})

@app.route('/api/fs-cli', methods=['POST'])
@login_required
def api_fs_cli():
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied - IP not in FS_ALLOWED_IPS'})

    command = request.json.get('command', '')
    if not command:
        return jsonify({'success': False, 'error': 'No command provided'})

    # Security: only allow safe read-only commands
    safe_commands = ['sofia status', 'show channels', 'show calls', 'status', 'version']
    if not any(command.startswith(cmd) for cmd in safe_commands):
        return jsonify({'success': False, 'error': 'Command not allowed'})

    result = fs_cli(command)
    if result is not None:
        return jsonify({'success': True, 'output': result})
    return jsonify({'success': False, 'error': 'Failed to connect to FreeSWITCH'})

################################################################################
# CRUD API - Users
################################################################################

@app.route('/api/crud/users', methods=['GET'])
@login_required
def crud_get_users():
    return jsonify(config_store.get_users())

@app.route('/api/crud/users', methods=['POST'])
@login_required
def crud_add_user():
    data = request.json
    success, msg = config_store.add_user(
        data.get('username'),
        data.get('password'),
        data.get('extension'),
        data.get('enabled', True)
    )
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/users/<username>', methods=['PUT'])
@login_required
def crud_update_user(username):
    data = request.json
    success, msg = config_store.update_user(username, data)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/users/<username>', methods=['DELETE'])
@login_required
def crud_delete_user(username):
    success, msg = config_store.delete_user(username)
    return jsonify({'success': success, 'message': msg})

################################################################################
# CRUD API - ACL Users
################################################################################

@app.route('/api/crud/acl-users', methods=['GET'])
@login_required
def crud_get_acl_users():
    return jsonify(config_store.get_acl_users())

@app.route('/api/crud/acl-users', methods=['POST'])
@login_required
def crud_add_acl_user():
    data = request.json
    success, msg = config_store.add_acl_user(
        data.get('username'),
        data.get('ip_address'),
        data.get('extension'),
        data.get('caller_id', '')
    )
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/acl-users/<username>', methods=['PUT'])
@login_required
def crud_update_acl_user(username):
    data = request.json
    success, msg = config_store.update_acl_user(username, data)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/acl-users/<username>', methods=['DELETE'])
@login_required
def crud_delete_acl_user(username):
    success, msg = config_store.delete_acl_user(username)
    return jsonify({'success': success, 'message': msg})

################################################################################
# CRUD API - Gateways
################################################################################

@app.route('/api/crud/gateways', methods=['GET'])
@login_required
def crud_get_gateways():
    return jsonify(config_store.get_gateways())

@app.route('/api/crud/gateways', methods=['POST'])
@login_required
def crud_add_gateway():
    data = request.json
    success, msg = config_store.add_gateway(
        data.get('name'),
        data.get('host'),
        data.get('port', 5060),
        data.get('username', ''),
        data.get('password', ''),
        data.get('register', True),
        data.get('transport', 'udp'),
        data.get('auth_username', '')
    )
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/gateways/<name>', methods=['PUT'])
@login_required
def crud_update_gateway(name):
    data = request.json
    success, msg = config_store.update_gateway(name, data)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/gateways/<name>', methods=['DELETE'])
@login_required
def crud_delete_gateway(name):
    success, msg = config_store.delete_gateway(name)
    return jsonify({'success': success, 'message': msg})

################################################################################
# CRUD API - Routes
################################################################################

@app.route('/api/crud/routes', methods=['GET'])
@login_required
def crud_get_routes():
    return jsonify(config_store.get_routes())

@app.route('/api/crud/routes', methods=['PUT'])
@login_required
def crud_update_routes():
    data = request.json
    success, msg = config_store.update_routes(data)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/routes/inbound', methods=['POST'])
@login_required
def crud_add_inbound_route():
    data = request.json
    success, msg = config_store.add_inbound_route(
        data.get('did'),
        data.get('destination'),
        data.get('destination_type', 'extension')
    )
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/routes/inbound/<did>', methods=['DELETE'])
@login_required
def crud_delete_inbound_route(did):
    success, msg = config_store.delete_inbound_route(did)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/routes/outbound', methods=['POST'])
@login_required
def crud_add_outbound_route():
    data = request.json
    success, msg = config_store.add_outbound_route(
        data.get('pattern'),
        data.get('gateway'),
        data.get('prepend', ''),
        data.get('strip', '')
    )
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/routes/user', methods=['POST'])
@login_required
def crud_add_user_route():
    data = request.json
    success, msg = config_store.add_user_route(
        data.get('username'),
        data.get('gateway')
    )
    return jsonify({'success': success, 'message': msg})

################################################################################
# CRUD API - Settings
################################################################################

@app.route('/api/crud/settings', methods=['GET'])
@login_required
def crud_get_settings():
    return jsonify(config_store.get_settings())

@app.route('/api/crud/settings', methods=['PUT'])
@login_required
def crud_update_settings():
    data = request.json
    success, msg = config_store.update_settings(data)
    return jsonify({'success': success, 'message': msg})

################################################################################
# CRUD API - Full Config
################################################################################

@app.route('/api/crud/full-config', methods=['GET'])
@login_required
def crud_get_full_config():
    """Get the full JSON configuration"""
    return jsonify(config_store.get_full_config())

################################################################################
# CRUD API - License
################################################################################

@app.route('/api/crud/license', methods=['GET'])
@login_required
def crud_get_license():
    """Get license info"""
    config = config_store.load_config()
    return jsonify(config.get('license', {'key': '', 'client_name': ''}))

@app.route('/api/crud/license', methods=['PUT'])
@login_required
def crud_update_license():
    """Update license info"""
    data = request.json
    config = config_store.load_config()
    config['license'] = {
        'key': data.get('key', ''),
        'client_name': data.get('client_name', '')
    }
    config_store.save_config(config)
    return jsonify({'success': True, 'message': 'License updated'})

################################################################################
# CRUD API - Inbound Routes (by gateway)
################################################################################

@app.route('/api/crud/inbound-routes', methods=['GET'])
@login_required
def crud_get_inbound_routes():
    """Get all inbound routes"""
    return jsonify(config_store.get_inbound_routes())

@app.route('/api/crud/inbound-routes', methods=['POST'])
@login_required
def crud_add_inbound_route_gw():
    """Add inbound route (gateway -> extension)"""
    data = request.json
    success, msg = config_store.add_inbound_route_gw(
        data.get('gateway'),
        data.get('extension')
    )
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/inbound-routes/<gateway>', methods=['PUT'])
@login_required
def crud_update_inbound_route_gw(gateway):
    """Update inbound route"""
    data = request.json
    success, msg = config_store.update_inbound_route(gateway, data.get('extension'))
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/inbound-routes/<gateway>', methods=['DELETE'])
@login_required
def crud_delete_inbound_route_gw(gateway):
    """Delete inbound route by gateway"""
    success, msg = config_store.delete_inbound_route_gw(gateway)
    return jsonify({'success': success, 'message': msg})

################################################################################
# CRUD API - User Routes (user -> gateway)
################################################################################

@app.route('/api/crud/user-routes', methods=['GET'])
@login_required
def crud_get_user_routes():
    """Get all user outbound routes"""
    return jsonify(config_store.get_outbound_user_routes())

@app.route('/api/crud/user-routes', methods=['POST'])
@login_required
def crud_add_user_route_new():
    """Add/update user route"""
    data = request.json
    success, msg = config_store.add_outbound_user_route(
        data.get('username'),
        data.get('gateway')
    )
    return jsonify({'success': success, 'message': msg})

@app.route('/api/crud/user-routes/<username>', methods=['DELETE'])
@login_required
def crud_delete_user_route_new(username):
    """Delete user route"""
    success, msg = config_store.delete_outbound_user_route(username)
    return jsonify({'success': success, 'message': msg})

################################################################################
# CRUD API - Defaults
################################################################################

@app.route('/api/crud/defaults', methods=['GET'])
@login_required
def crud_get_defaults():
    """Get default gateway/extension"""
    return jsonify({
        'default_gateway': config_store.get_default_gateway(),
        'default_extension': config_store.get_default_extension(),
        'outbound_caller_id': config_store.get_outbound_caller_id()
    })

@app.route('/api/crud/defaults', methods=['PUT'])
@login_required
def crud_update_defaults():
    """Update defaults"""
    data = request.json
    if 'default_gateway' in data:
        config_store.set_default_gateway(data['default_gateway'])
    if 'default_extension' in data:
        config_store.set_default_extension(data['default_extension'])
    if 'outbound_caller_id' in data:
        config_store.set_outbound_caller_id(data['outbound_caller_id'])
    return jsonify({'success': True, 'message': 'Defaults updated'})

################################################################################
# Import from ENV
################################################################################

@app.route('/api/crud/import-env', methods=['POST'])
@login_required
def crud_import_from_env():
    """Import configuration from environment variables to JSON"""
    imported = config_store.import_from_env()
    return jsonify({
        'success': True,
        'message': 'Imported from environment',
        'imported': imported
    })

################################################################################
# Config File Import/Export
################################################################################

@app.route('/api/config/export', methods=['GET'])
@login_required
def api_export_config_file():
    """Export full JSON config as downloadable file"""
    from flask import Response
    config = config_store.get_full_config()

    # Create filename with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"wrapper_config_{timestamp}.json"

    json_content = json.dumps(config, indent=2, ensure_ascii=False)

    return Response(
        json_content,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'application/json; charset=utf-8'
        }
    )

@app.route('/api/config/import', methods=['POST'])
@login_required
def api_import_config_file():
    """Import JSON config from uploaded file"""
    # Check if file was uploaded
    if 'file' not in request.files:
        # Try to get JSON from request body
        if request.is_json:
            try:
                new_config = request.json
            except Exception as e:
                return jsonify({'success': False, 'error': f'Invalid JSON: {e}'})
        else:
            return jsonify({'success': False, 'error': 'No file uploaded'})
    else:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})

        try:
            content = file.read().decode('utf-8')
            new_config = json.loads(content)
        except json.JSONDecodeError as e:
            return jsonify({'success': False, 'error': f'Invalid JSON: {e}'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error reading file: {e}'})

    # Validate config structure
    required_keys = ['users', 'gateways', 'routes']
    for key in required_keys:
        if key not in new_config:
            return jsonify({'success': False, 'error': f'Missing required key: {key}'})

    # Backup current config
    try:
        current_config = config_store.get_full_config()
        backup_path = config_store.get_config_path()
        backup_file = str(backup_path) + '.backup'
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Could not create backup: {e}")

    # Merge with defaults to ensure all required fields exist
    for key in config_store.DEFAULT_CONFIG:
        if key not in new_config:
            new_config[key] = config_store.DEFAULT_CONFIG[key]

    # Save new config
    if config_store.save_config(new_config):
        return jsonify({
            'success': True,
            'message': 'Config imported successfully',
            'stats': {
                'users': len(new_config.get('users', [])),
                'gateways': len(new_config.get('gateways', [])),
                'acl_users': len(new_config.get('acl_users', [])),
                'inbound_routes': len(new_config.get('routes', {}).get('inbound', [])),
                'user_routes': len(new_config.get('routes', {}).get('user_routes', []))
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to save config'})

################################################################################
# CRUD API - Export & Apply
################################################################################

@app.route('/api/crud/export', methods=['GET'])
@login_required
def crud_export():
    """Export config for provision.sh compatibility"""
    return jsonify(config_store.export_for_provision())

@app.route('/api/crud/apply', methods=['POST'])
@login_required
def crud_apply():
    """Export config and reload FreeSWITCH"""
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied - IP not in FS_ALLOWED_IPS'})

    # Export config to routing_config.json
    export_data = config_store.export_for_provision()
    config_file = '/var/lib/freeswitch/routing_config.json'
    try:
        with open(config_file, 'w') as f:
            json.dump(export_data, f, indent=2)
    except IOError as e:
        return jsonify({'success': False, 'error': f'Failed to write config: {e}'})

    # Reload FreeSWITCH
    result = fs_cli('reloadxml')
    if result is not None:
        fs_cli('sofia profile internal rescan')
        fs_cli('sofia profile external rescan')
        return jsonify({'success': True, 'message': 'Config applied and FreeSWITCH reloaded'})

    return jsonify({'success': False, 'error': 'Config saved but failed to reload FreeSWITCH'})

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
