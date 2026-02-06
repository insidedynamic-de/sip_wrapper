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
# Auto-Blacklist: Failed Attempts Tracker
################################################################################
import re
from datetime import datetime, timedelta
from collections import defaultdict
import threading

# In-memory storage for failed attempts: {ip: [(timestamp, user), ...]}
failed_attempts = defaultdict(list)
failed_attempts_lock = threading.Lock()
last_log_position = 0  # Track where we left off in the log file

def parse_failed_attempts_from_logs():
    """Parse FreeSWITCH logs for failed auth attempts"""
    global last_log_position

    log_paths = [
        '/var/log/freeswitch/freeswitch.log',
        '/usr/local/freeswitch/log/freeswitch.log',
        '/var/log/freeswitch.log'
    ]

    # Pattern to match failed auth: "SIP auth failure ... from ip X.X.X.X"
    auth_failure_pattern = re.compile(
        r'SIP auth (?:failure|challenge).*from ip (\d+\.\d+\.\d+\.\d+)'
    )

    for log_path in log_paths:
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Seek to last position
                    f.seek(last_log_position)
                    new_lines = f.readlines()
                    last_log_position = f.tell()

                    now = datetime.now()
                    with failed_attempts_lock:
                        for line in new_lines:
                            match = auth_failure_pattern.search(line)
                            if match:
                                ip = match.group(1)
                                failed_attempts[ip].append(now)

                    return True
            except Exception as e:
                print(f"Error parsing logs: {e}")
    return False


def check_and_auto_blacklist():
    """Check failed attempts and auto-blacklist if threshold exceeded"""
    settings = config_store.get_auto_blacklist_settings()
    if not settings.get('enabled', False):
        return []

    max_attempts = settings.get('max_attempts', 10)
    time_window = settings.get('time_window', 300)  # seconds

    now = datetime.now()
    cutoff = now - timedelta(seconds=time_window)
    blocked_ips = []

    # Get current blacklist
    security = config_store.get_security()
    current_blacklist = [e.get('ip') for e in security.get('blacklist', [])]

    with failed_attempts_lock:
        for ip, attempts in list(failed_attempts.items()):
            # Filter to recent attempts only
            recent = [ts for ts in attempts if ts > cutoff]
            failed_attempts[ip] = recent

            # Check if exceeds threshold
            if len(recent) >= max_attempts and ip not in current_blacklist:
                # Add to blacklist
                success, msg = config_store.add_to_blacklist(
                    ip,
                    f"Auto-blocked: {len(recent)} failed attempts in {time_window}s"
                )
                if success:
                    blocked_ips.append(ip)
                    # Clear attempts for this IP
                    failed_attempts[ip] = []

    return blocked_ips


def get_failed_attempts_summary():
    """Get summary of recent failed attempts"""
    settings = config_store.get_auto_blacklist_settings()
    time_window = settings.get('time_window', 300)

    now = datetime.now()
    cutoff = now - timedelta(seconds=time_window)

    # Get current blacklist to exclude already blocked IPs
    security = config_store.get_security()
    blacklisted_ips = {e.get('ip') for e in security.get('blacklist', [])}

    summary = []
    with failed_attempts_lock:
        for ip, attempts in failed_attempts.items():
            # Skip already blacklisted IPs
            if ip in blacklisted_ips:
                continue

            recent = [ts for ts in attempts if ts > cutoff]
            if recent:
                summary.append({
                    'ip': ip,
                    'count': len(recent),
                    'last_attempt': recent[-1].isoformat() if recent else None
                })

    # Sort by count descending
    summary.sort(key=lambda x: x['count'], reverse=True)
    return summary


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
        'active_calls': 'Aktive Anrufe',
        'call_flow': 'Verbindung',
        'call_logs': 'Anrufverlauf',
        'no_call_logs': 'Keine Anrufe aufgezeichnet',
        'direction': 'Richtung',
        'from': 'Von',
        'to': 'Zu',
        'duration': 'Dauer',
        'result': 'Ergebnis',
        'time': 'Zeit',
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
        'active_calls': 'Active Calls',
        'call_flow': 'Connection',
        'call_logs': 'Call Logs',
        'no_call_logs': 'No calls recorded',
        'direction': 'Direction',
        'from': 'From',
        'to': 'To',
        'duration': 'Duration',
        'result': 'Result',
        'time': 'Time',
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

def parse_active_calls():
    """Parse active calls from FreeSWITCH"""
    output = fs_cli('show calls')
    if not output:
        return []

    calls = []
    for line in output.split('\n'):
        line = line.strip()
        # Skip headers and empty lines
        if not line or 'uuid' in line.lower() or line.startswith('=') or line.startswith('-'):
            continue
        # Skip summary lines
        if 'total' in line.lower() or line[0].isdigit() and 'row' in line.lower():
            continue

        parts = line.split(',')
        if len(parts) >= 7:
            calls.append({
                'uuid': parts[0][:8] + '...' if len(parts[0]) > 8 else parts[0],
                'direction': parts[1] if len(parts) > 1 else '-',
                'created': parts[2] if len(parts) > 2 else '-',
                'name': parts[3] if len(parts) > 3 else '-',
                'state': parts[4] if len(parts) > 4 else '-',
                'cid_name': parts[5] if len(parts) > 5 else '-',
                'cid_num': parts[6] if len(parts) > 6 else '-',
                'dest': parts[9] if len(parts) > 9 else '-'
            })
    return calls

def parse_channels_count():
    """Get count of active channels"""
    output = fs_cli('show channels count')
    if not output:
        return 0
    # Output format: "X total."
    for line in output.split('\n'):
        if 'total' in line.lower():
            parts = line.split()
            if parts and parts[0].isdigit():
                return int(parts[0])
    return 0

def get_recent_logs(count=15):
    """Get recent FreeSWITCH log entries"""
    log_paths = [
        '/var/log/freeswitch/freeswitch.log',
        '/usr/local/freeswitch/log/freeswitch.log',
        '/var/log/freeswitch.log'
    ]

    for log_path in log_paths:
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last N lines
                    recent = lines[-count:] if len(lines) >= count else lines
                    # Parse and format
                    logs = []
                    for line in recent:
                        line = line.strip()
                        if not line:
                            continue
                        # Determine log level
                        level = 'info'
                        if 'ERR' in line or 'ERROR' in line:
                            level = 'error'
                        elif 'WARN' in line or 'WARNING' in line:
                            level = 'warning'
                        elif 'DEBUG' in line:
                            level = 'debug'
                        logs.append({'text': line[:200], 'level': level})
                    return logs
            except Exception:
                pass
    return []

def get_call_logs(count=50):
    """Get call detail records (CDR) from FreeSWITCH"""
    cdr_paths = [
        '/var/log/freeswitch/cdr-csv',
        '/usr/local/freeswitch/log/cdr-csv',
        '/var/log/cdr-csv'
    ]

    calls = []

    for cdr_dir in cdr_paths:
        if os.path.isdir(cdr_dir):
            try:
                # Find all CSV files in CDR directory
                csv_files = []
                for f in os.listdir(cdr_dir):
                    if f.endswith('.csv'):
                        csv_files.append(os.path.join(cdr_dir, f))

                # Sort by modification time (newest first)
                csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

                # Read CDR entries
                for csv_file in csv_files[:5]:  # Check last 5 files
                    if len(calls) >= count:
                        break
                    try:
                        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            # Process lines in reverse (newest first)
                            for line in reversed(lines):
                                if len(calls) >= count:
                                    break
                                line = line.strip()
                                if not line:
                                    continue
                                # Parse CSV - FreeSWITCH CDR format
                                # Typical fields: caller_id_name,caller_id_number,destination_number,context,start_stamp,answer_stamp,end_stamp,duration,billsec,hangup_cause,...
                                parts = line.split(',')
                                if len(parts) >= 10:
                                    # Extract key fields
                                    call = {
                                        'caller_name': parts[0].strip('"') if parts[0] else '-',
                                        'caller_num': parts[1].strip('"') if parts[1] else '-',
                                        'dest': parts[2].strip('"') if parts[2] else '-',
                                        'context': parts[3].strip('"') if parts[3] else '-',
                                        'start': parts[4].strip('"') if parts[4] else '-',
                                        'answer': parts[5].strip('"') if parts[5] else '-',
                                        'end': parts[6].strip('"') if parts[6] else '-',
                                        'duration': parts[7].strip('"') if parts[7] else '0',
                                        'billsec': parts[8].strip('"') if parts[8] else '0',
                                        'hangup_cause': parts[9].strip('"') if parts[9] else '-'
                                    }
                                    # Skip header lines
                                    if call['caller_name'].lower() in ['caller_id_name', 'calleridname']:
                                        continue
                                    # Determine direction
                                    call['direction'] = 'inbound' if 'public' in call['context'].lower() else 'outbound'
                                    calls.append(call)
                    except Exception as e:
                        continue

                if calls:
                    break  # Found CDR files, stop searching

            except Exception:
                pass

    return calls

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
    active_calls = parse_active_calls() if fs_access else []
    channels_count = parse_channels_count() if fs_access else 0
    recent_logs = get_recent_logs(15)

    call_logs = get_call_logs(10) if fs_access else []

    return render_template('dashboard.html',
        profiles=profiles,
        gateways=gateways,
        registrations=registrations,
        active_calls=active_calls,
        channels_count=channels_count,
        call_logs=call_logs,
        recent_logs=recent_logs,
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

@app.route('/manage')
@login_required
def manage():
    return render_template('manage.html')

@app.route('/logs')
@login_required
def logs():
    return render_template('logs.html')

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

@app.route('/api/logs')
@login_required
def api_logs():
    count = request.args.get('count', 15, type=int)
    # Limit to reasonable values
    count = min(max(count, 1), 1000)
    logs = get_recent_logs(count)
    return jsonify({'logs': logs, 'count': len(logs)})

@app.route('/api/cdr')
@login_required
def api_cdr():
    count = request.args.get('count', 50, type=int)
    # Limit to reasonable values
    count = min(max(count, 1), 500)
    calls = get_call_logs(count)
    return jsonify({'calls': calls, 'count': len(calls)})

@app.route('/api/active-calls')
@login_required
def api_active_calls():
    if not fs_allowed():
        return jsonify({'error': 'Access denied', 'calls': [], 'count': 0})
    calls = parse_active_calls()
    count = parse_channels_count()
    return jsonify({'calls': calls, 'count': count})

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
# Security API - Blacklist / Whitelist
################################################################################

@app.route('/api/security')
@login_required
def api_security():
    """Get security settings"""
    return jsonify(config_store.get_security())

@app.route('/api/security/blacklist', methods=['GET'])
@login_required
def api_blacklist_get():
    """Get blacklist"""
    security = config_store.get_security()
    return jsonify({'blacklist': security.get('blacklist', [])})

@app.route('/api/security/blacklist', methods=['POST'])
@login_required
def api_blacklist_add():
    """Add IP to blacklist"""
    data = request.get_json()
    ip = data.get('ip', '').strip()
    comment = data.get('comment', '').strip()

    if not ip:
        return jsonify({'success': False, 'message': 'IP address required'})

    success, message = config_store.add_to_blacklist(ip, comment)
    return jsonify({'success': success, 'message': message})

@app.route('/api/security/blacklist/<ip>', methods=['DELETE'])
@login_required
def api_blacklist_delete(ip):
    """Remove IP from blacklist"""
    success, message = config_store.remove_from_blacklist(ip)
    return jsonify({'success': success, 'message': message})

@app.route('/api/security/whitelist', methods=['GET'])
@login_required
def api_whitelist_get():
    """Get whitelist"""
    security = config_store.get_security()
    return jsonify({'whitelist': security.get('whitelist', [])})

@app.route('/api/security/whitelist', methods=['POST'])
@login_required
def api_whitelist_add():
    """Add IP to whitelist"""
    data = request.get_json()
    ip = data.get('ip', '').strip()
    comment = data.get('comment', '').strip()

    if not ip:
        return jsonify({'success': False, 'message': 'IP address required'})

    success, message = config_store.add_to_whitelist(ip, comment)
    return jsonify({'success': success, 'message': message})

@app.route('/api/security/whitelist/<ip>', methods=['DELETE'])
@login_required
def api_whitelist_delete(ip):
    """Remove IP from whitelist"""
    success, message = config_store.remove_from_whitelist(ip)
    return jsonify({'success': success, 'message': message})

@app.route('/api/security/whitelist-enabled', methods=['POST'])
@login_required
def api_whitelist_enabled():
    """Enable/disable whitelist mode"""
    data = request.get_json()
    enabled = data.get('enabled', False)
    success, message = config_store.set_whitelist_enabled(enabled)
    return jsonify({'success': success, 'message': message})

################################################################################
# Auto-Blacklist API
################################################################################

@app.route('/api/security/auto-blacklist', methods=['GET'])
@login_required
def api_auto_blacklist_get():
    """Get auto-blacklist settings"""
    settings = config_store.get_auto_blacklist_settings()
    return jsonify(settings)

@app.route('/api/security/auto-blacklist', methods=['POST'])
@login_required
def api_auto_blacklist_update():
    """Update auto-blacklist settings"""
    data = request.get_json()
    settings = {
        'enabled': data.get('enabled', False),
        'max_attempts': int(data.get('max_attempts', 10)),
        'time_window': int(data.get('time_window', 300)),
        'block_duration': int(data.get('block_duration', 3600))
    }
    success, message = config_store.update_auto_blacklist_settings(settings)
    return jsonify({'success': success, 'message': message})

@app.route('/api/security/failed-attempts', methods=['GET'])
@login_required
def api_failed_attempts():
    """Get failed attempts summary"""
    # First, parse new log entries
    parse_failed_attempts_from_logs()
    # Then check and auto-blacklist
    blocked = check_and_auto_blacklist()
    # Return summary
    summary = get_failed_attempts_summary()
    return jsonify({
        'attempts': summary,
        'auto_blocked': blocked,
        'settings': config_store.get_auto_blacklist_settings()
    })

@app.route('/api/security/check-blacklist', methods=['POST'])
@login_required
def api_check_blacklist():
    """Manually trigger auto-blacklist check"""
    parse_failed_attempts_from_logs()
    blocked = check_and_auto_blacklist()
    return jsonify({
        'success': True,
        'blocked': blocked,
        'message': f"Blocked {len(blocked)} IPs" if blocked else "No IPs blocked"
    })

################################################################################
# Fail2Ban Integration API
################################################################################

@app.route('/api/security/fail2ban', methods=['GET'])
@login_required
def api_fail2ban_get():
    """Get Fail2Ban settings and status"""
    settings = config_store.get_fail2ban_settings()
    status = config_store.get_fail2ban_status()
    return jsonify({
        'settings': settings,
        'status': status
    })

@app.route('/api/security/fail2ban', methods=['POST'])
@login_required
def api_fail2ban_update():
    """Update Fail2Ban settings"""
    data = request.get_json()
    settings = {
        'enabled': data.get('enabled', False),
        'threshold': int(data.get('threshold', 50)),
        'jail_name': data.get('jail_name', 'sip-blacklist')
    }
    success, message = config_store.update_fail2ban_settings(settings)
    return jsonify({'success': success, 'message': message})

@app.route('/api/security/fail2ban/ban/<ip>', methods=['POST'])
@login_required
def api_fail2ban_ban(ip):
    """Manually add IP to Fail2Ban jail"""
    success = config_store.trigger_fail2ban(ip)
    if success:
        return jsonify({'success': True, 'message': f'IP {ip} banned in Fail2Ban'})
    return jsonify({'success': False, 'message': 'Failed to ban IP in Fail2Ban'})

@app.route('/api/security/fail2ban/unban/<ip>', methods=['POST'])
@login_required
def api_fail2ban_unban(ip):
    """Remove IP from Fail2Ban jail"""
    success = config_store.unban_from_fail2ban(ip)
    if success:
        return jsonify({'success': True, 'message': f'IP {ip} unbanned from Fail2Ban'})
    return jsonify({'success': False, 'message': 'Failed to unban IP from Fail2Ban'})

@app.route('/api/security/blacklist/<ip>/reset-count', methods=['POST'])
@login_required
def api_blacklist_reset_count(ip):
    """Reset blocked_count for an IP"""
    success, message = config_store.reset_blocked_count(ip)
    return jsonify({'success': success, 'message': message})

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
