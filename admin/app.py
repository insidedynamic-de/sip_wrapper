#!/usr/bin/env python3
"""
InsideDynamic Wrapper - Admin Portal
Simple web interface for FreeSWITCH configuration management
"""

import os
import json
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from functools import wraps

# Config store for CRUD operations
import config_store

# Auto-initialize config from ENV on first run
config_store.init_config()

# Initialize trial license if no key
config_store.init_license()

# ESL Event Subscriber for real-time FreeSWITCH events
import esl_events

# Version info
def get_version_info():
    """Get version info from VERSION file and git"""
    version_info = {
        'version': '0.0.0',
        'git_commit': None,
        'git_branch': None,
        'build_date': None
    }

    # Read VERSION file
    version_paths = [
        Path(__file__).parent.parent / 'VERSION',
        Path(__file__).parent / 'VERSION',
        Path('/app/VERSION'),
    ]
    for vpath in version_paths:
        if vpath.exists():
            try:
                version_info['version'] = vpath.read_text().strip()
                break
            except Exception:
                pass

    # Try Docker build info files first (for containerized deployments)
    docker_commit_path = Path('/app/GIT_COMMIT')
    docker_date_path = Path('/app/BUILD_DATE')

    if docker_commit_path.exists():
        try:
            commit = docker_commit_path.read_text().strip()
            if commit and commit != 'unknown':
                version_info['git_commit'] = commit
        except Exception:
            pass

    if docker_date_path.exists():
        try:
            build_date = docker_date_path.read_text().strip()
            if build_date and build_date != 'unknown':
                version_info['build_date'] = build_date
        except Exception:
            pass

    # If no Docker info, try git directly (for local development)
    if not version_info['git_commit']:
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True, text=True, timeout=5,
                cwd=Path(__file__).parent.parent
            )
            if result.returncode == 0:
                version_info['git_commit'] = result.stdout.strip()
        except Exception:
            pass

    if not version_info['git_branch']:
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, timeout=5,
                cwd=Path(__file__).parent.parent
            )
            if result.returncode == 0:
                version_info['git_branch'] = result.stdout.strip()
        except Exception:
            pass

    return version_info

VERSION_INFO = get_version_info()

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

# Auto-reload templates without restarting Python (works in debug mode)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Configuration
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin')

# FreeSWITCH ESL connection settings from JSON config
def _get_esl_config():
    try:
        settings = config_store.get_settings()
        return (
            settings.get('esl_host', '127.0.0.1') or '127.0.0.1',
            int(settings.get('esl_port', 8021) or 8021),
            settings.get('esl_password', 'ClueCon') or 'ClueCon'
        )
    except Exception:
        return ('127.0.0.1', 8021, 'ClueCon')

FS_HOST, FS_PORT, FS_PASS = _get_esl_config()

# Security: IP-based access control
# Format: comma-separated IPs or CIDR ranges
# Special values: 0.0.0.0 = allow all, 127.0.0.1 = localhost only (default)
# Supports generic name API_ACL with fallback to FS_ALLOWED_IPS
_acl_raw = os.environ.get('API_ACL', '') or os.environ.get('FS_ALLOWED_IPS', '127.0.0.1')
FS_ALLOWED_IPS = [ip.strip() for ip in _acl_raw.split(',') if ip.strip()]

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
# Translations - Load from JSON files
################################################################################

def load_translations():
    """Load translations from JSON files in lang/ folder"""
    translations = {}
    lang_dir = Path(__file__).parent / 'lang'

    if lang_dir.exists():
        for lang_file in lang_dir.glob('*.json'):
            lang_code = lang_file.stem  # e.g., 'en', 'de'
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    translations[lang_code] = json.load(f)
            except Exception as e:
                print(f"Error loading {lang_file}: {e}")

    # Fallback if no files found
    if not translations:
        translations = {'en': {}, 'de': {}}

    return translations

TRANSLATIONS = load_translations()

# Legacy flat dict for backwards compatibility (auto-generated from nested)
def flatten_translations(d, parent_key=''):
    """Flatten nested dict: {'nav': {'dashboard': 'X'}} -> {'nav.dashboard': 'X', 'dashboard': 'X'}"""
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_translations(v, new_key))
            # Also add without prefix for backwards compatibility
            items.update(flatten_translations(v, ''))
        else:
            items[new_key] = v
            # Also add short key for backwards compatibility
            if parent_key:
                items[k] = v
    return items

# Create flattened versions for easy lookup
TRANSLATIONS_FLAT = {
    lang: flatten_translations(data) for lang, data in TRANSLATIONS.items()
}

# Legacy dict format (kept for reference, now loaded from JSON)
_LEGACY_TRANSLATIONS = {
    'de': {
        'title': 'InsideDynamic Wrapper - Admin',
        'dashboard': 'Dashboard',
        'config': 'Konfiguration',
        'gateways': 'Gateways',
        'users': 'Benutzer',
        'routing': 'Routing',
        'security': 'Sicherheit',
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
        # Profile page
        'change_password': 'Passwort ändern',
        'current_password': 'Aktuelles Passwort',
        'new_password': 'Neues Passwort',
        'confirm_password': 'Passwort bestätigen',
        'appearance': 'Erscheinungsbild',
        'theme_mode': 'Theme-Modus',
        'color_theme': 'Farbschema',
        'company_info': 'Firmeninformationen',
        'company_name': 'Firmenname',
        'address': 'Adresse',
        'zip_code': 'PLZ',
        'city': 'Stadt',
        'country': 'Land',
        'invoice_info': 'Rechnungsadresse',
        'same_as_company': 'Wie Firmenadresse',
        'invoice_name': 'Rechnungsempfänger',
        'invoice_address': 'Rechnungsadresse',
        'invoice_email': 'Rechnungs-E-Mail',
        'invoice_email_hint': 'Rechnungen werden an diese Adresse gesendet',
        'license_info': 'Lizenzinformationen',
        'license_key': 'Lizenzschlüssel',
        'client_name': 'Kundenname',
        'version': 'Version',
        'update_license': 'Lizenz aktualisieren',
        'activate': 'Aktivieren',
        'passwords_not_match': 'Passwörter stimmen nicht überein',
    },
    'en': {
        'title': 'InsideDynamic Wrapper - Admin',
        'dashboard': 'Dashboard',
        'config': 'Configuration',
        'gateways': 'Gateways',
        'users': 'Users',
        'routing': 'Routing',
        'security': 'Security',
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
        # Profile page
        'change_password': 'Change Password',
        'current_password': 'Current Password',
        'new_password': 'New Password',
        'confirm_password': 'Confirm Password',
        'appearance': 'Appearance',
        'theme_mode': 'Theme Mode',
        'color_theme': 'Color Theme',
        'company_info': 'Company Information',
        'company_name': 'Company Name',
        'address': 'Address',
        'zip_code': 'ZIP Code',
        'city': 'City',
        'country': 'Country',
        'invoice_info': 'Invoice Address',
        'same_as_company': 'Same as company address',
        'invoice_name': 'Invoice Recipient',
        'invoice_address': 'Invoice Address',
        'invoice_email': 'Invoice Email',
        'invoice_email_hint': 'Invoices will be sent to this address',
        'license_info': 'License Information',
        'license_key': 'License Key',
        'client_name': 'Client Name',
        'version': 'Version',
        'update_license': 'Update License',
        'activate': 'Activate',
        'passwords_not_match': 'Passwords do not match',
    }
}
# End of legacy translations - now loaded from JSON files in lang/ folder

def get_lang():
    return session.get('lang', 'de')

def t(key):
    """Get translation for key.

    Supports:
    - Simple keys: t('save') -> 'Save'
    - Nested keys: t('nav.dashboard') -> 'Dashboard'
    - Returns UPPERCASE key if not found: t('unknown') -> 'UNKNOWN'
    """
    lang = get_lang()
    translations = TRANSLATIONS_FLAT.get(lang, TRANSLATIONS_FLAT.get('en', {}))

    # Try exact key first
    if key in translations:
        return translations[key]

    # Fallback to English
    en_translations = TRANSLATIONS_FLAT.get('en', {})
    if key in en_translations:
        return en_translations[key]

    # Not found - return UPPERCASE key
    return key.upper().replace('.', '_')

@app.context_processor
def inject_translations():
    license_status = config_store.get_license_status()
    return {'t': t, 'lang': get_lang(), 'version_info': VERSION_INFO, 'license_status': license_status}

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

def fs_cli(command, allow_empty=False):
    """Execute FreeSWITCH CLI command via ESL

    Uses ESL (Event Socket Library) for direct Python connection.
    No fs_cli binary required.

    Connection: FS_HOST:FS_PORT with FS_PASS

    Args:
        command: The FreeSWITCH API command to execute
        allow_empty: If True, return empty string instead of None for empty responses
    """
    if not ESL_AVAILABLE:
        print("ESL not available - install greenswitch")
        return None

    try:
        esl = InboundESL(host=FS_HOST, port=FS_PORT, password=FS_PASS)
        esl.connect()
        result = esl.send(f'api {command}')
        esl.stop()

        if result:
            data = result.data if hasattr(result, 'data') else None
            if data:
                # Handle both bytes and str (greenswitch version dependent)
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                return data.strip()
            elif allow_empty:
                # Command executed but returned empty response
                return ''
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

def parse_call_statistics():
    """Parse call statistics from sofia profiles (CALLS-IN, FAILED-CALLS-IN, etc.)"""
    stats = {
        'internal': {'calls_in': 0, 'failed_in': 0, 'calls_out': 0, 'failed_out': 0, 'registrations': 0},
        'external': {'calls_in': 0, 'failed_in': 0, 'calls_out': 0, 'failed_out': 0, 'registrations': 0},
        'total': {'calls_in': 0, 'failed_in': 0, 'calls_out': 0, 'failed_out': 0}
    }

    for profile in ['internal', 'external']:
        output = fs_cli(f'sofia status profile {profile}')
        if not output:
            continue

        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Parse key-value pairs like "CALLS-IN \t 5"
            if '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    key = parts[0].strip().upper()
                    value = parts[-1].strip()

                    try:
                        val = int(value)
                        if key == 'CALLS-IN':
                            stats[profile]['calls_in'] = val
                            stats['total']['calls_in'] += val
                        elif key == 'FAILED-CALLS-IN':
                            stats[profile]['failed_in'] = val
                            stats['total']['failed_in'] += val
                        elif key == 'CALLS-OUT':
                            stats[profile]['calls_out'] = val
                            stats['total']['calls_out'] += val
                        elif key == 'FAILED-CALLS-OUT':
                            stats[profile]['failed_out'] = val
                            stats['total']['failed_out'] += val
                        elif key == 'REGISTRATIONS':
                            stats[profile]['registrations'] = val
                    except ValueError:
                        pass

    return stats

################################################################################
# FreeSWITCH Logs - ESL Event Based (No File Access Needed)
################################################################################

import time
import re

def get_recent_logs(count=100):
    """Get recent FreeSWITCH events via ESL Event Subscriber"""
    if not fs_allowed():
        return []

    subscriber = esl_events.get_subscriber()

    # Ensure subscriber is running
    if not subscriber.running:
        subscriber.start()

    # Get events from buffer
    events = subscriber.get_events(count)

    # Convert to log format
    logs = []
    for event in events:
        logs.append({
            'text': event.get('text', ''),
            'level': event.get('level', 'info'),
            'timestamp': event.get('timestamp', time.time()),
            'type': event.get('type', 'UNKNOWN'),
            'subtype': event.get('subtype', ''),
        })

    return logs

def get_log_status():
    """Get status info about ESL event subscriber"""
    subscriber = esl_events.get_subscriber()
    status = subscriber.get_status()

    return {
        'available': status['connected'] or status['running'],
        'mode': 'esl_events',
        'esl_host': status['host'],
        'connected': status['connected'],
        'running': status['running'],
        'last_error': status['last_error'],
        'buffer_stats': status['buffer_stats'],
        'esl_available': status['esl_available']
    }

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
    call_stats = parse_call_statistics() if fs_access else {}

    call_logs = get_call_logs(10) if fs_access else []

    return render_template('dashboard.html',
        profiles=profiles,
        gateways=gateways,
        registrations=registrations,
        active_calls=active_calls,
        channels_count=channels_count,
        call_stats=call_stats,
        call_logs=call_logs,
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

@app.route('/security')
@login_required
def security():
    return render_template('security.html')

@app.route('/profile')
@login_required
def profile():
    # Load profile data
    config = config_store.load_config()
    profile_data = config.get('profile', {})
    license_data = config.get('license', {})
    return render_template('profile.html', profile=profile_data, license=license_data)

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

@app.route('/api/version')
def api_version():
    """Get version info"""
    return jsonify(VERSION_INFO)

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
    status = get_log_status()
    return jsonify({
        'logs': logs,
        'count': len(logs),
        'status': status,
        'fs_connected': fs_allowed() and ESL_AVAILABLE
    })

@app.route('/api/esl/events')
@login_required
def api_esl_events():
    """Get ESL events from buffer"""
    if not fs_allowed():
        return jsonify({'error': 'Access denied', 'events': []})

    count = request.args.get('count', 100, type=int)
    since = request.args.get('since', 0, type=float)
    count = min(max(count, 1), 1000)

    subscriber = esl_events.get_subscriber()

    if since > 0:
        events = subscriber.get_events_since(since)
    else:
        events = subscriber.get_events(count)

    return jsonify({
        'events': events,
        'count': len(events),
        'status': subscriber.get_status()
    })

@app.route('/api/esl/status')
@login_required
def api_esl_status():
    """Get ESL subscriber status"""
    subscriber = esl_events.get_subscriber()
    return jsonify(subscriber.get_status())

@app.route('/api/esl/command', methods=['POST'])
@login_required
def api_esl_command():
    """Send command to FreeSWITCH via ESL"""
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied'})

    command = request.json.get('command', '')
    if not command:
        return jsonify({'success': False, 'error': 'No command provided'})

    # Security: only allow safe read-only commands
    safe_commands = ['status', 'sofia', 'show', 'fsctl loglevel', 'version', 'uptime']
    is_safe = any(command.lower().startswith(cmd) for cmd in safe_commands)
    if not is_safe:
        return jsonify({'success': False, 'error': 'Command not allowed'})

    subscriber = esl_events.get_subscriber()
    result = subscriber.send_command(command)
    return jsonify(result)

@app.route('/api/esl/start', methods=['POST'])
@login_required
def api_esl_start():
    """Start ESL subscriber"""
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied'})

    subscriber = esl_events.start_subscriber()
    return jsonify({'success': True, 'status': subscriber.get_status()})

@app.route('/api/esl/stop', methods=['POST'])
@login_required
def api_esl_stop():
    """Stop ESL subscriber"""
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied'})

    esl_events.stop_subscriber()
    return jsonify({'success': True, 'message': 'ESL subscriber stopped'})

@app.route('/api/esl/clear', methods=['POST'])
@login_required
def api_esl_clear():
    """Clear ESL event buffer"""
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied'})

    subscriber = esl_events.get_subscriber()
    subscriber.buffer.clear()
    return jsonify({'success': True, 'message': 'Event buffer cleared'})

@app.route('/api/esl/test', methods=['POST'])
@login_required
def api_esl_test():
    """Test ESL connection without saving"""
    data = request.json or {}
    host = data.get('host', '127.0.0.1')
    port = data.get('port', 8021)
    password = data.get('password', 'ClueCon')
    result = esl_events.test_esl_connection(host, port, password)
    return jsonify(result)

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
# FreeSWITCH Log Level Control
################################################################################

# Log level names mapping
FS_LOG_LEVELS = {
    0: 'CONSOLE',
    1: 'ALERT',
    2: 'CRIT',
    3: 'ERR',
    4: 'WARNING',
    5: 'NOTICE',
    6: 'INFO',
    7: 'DEBUG'
}

@app.route('/api/fs-loglevel', methods=['GET'])
@login_required
def api_get_loglevel():
    """Get current log level from config (source of truth)"""
    if not fs_allowed():
        return jsonify({'error': 'Access denied', 'config_level': 4})

    # Get from config (source of truth)
    config_level = 4  # default
    try:
        config = config_store.load_config()
        config_level = config.get('settings', {}).get('fs_loglevel', 4)
    except Exception:
        pass

    return jsonify({
        'config_level': config_level,
        'config_level_name': FS_LOG_LEVELS.get(config_level, str(config_level))
    })

@app.route('/api/fs-loglevel', methods=['POST'])
@login_required
def api_set_loglevel():
    """Set FreeSWITCH log level (0-7)

    Always saves to config AND pushes to FreeSWITCH server.
    Config is source of truth.
    """
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied - IP not in FS_ALLOWED_IPS'})

    data = request.json
    level = data.get('level', 4)

    # Validate level
    if not isinstance(level, int) or level < 0 or level > 7:
        return jsonify({'success': False, 'error': 'Invalid log level (must be 0-7)'})

    # 1. Save to config (source of truth)
    try:
        config = config_store.load_config()
        if 'settings' not in config:
            config['settings'] = {}
        config['settings']['fs_loglevel'] = level
        config_store.save_config(config)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to save config: {e}'})

    # 2. Push to FreeSWITCH server
    result = fs_cli(f'fsctl loglevel {level}', allow_empty=True)

    if result is not None:
        return jsonify({
            'success': True,
            'level': level,
            'level_name': FS_LOG_LEVELS.get(level, str(level)),
            'message': f'Log level set to {level} ({FS_LOG_LEVELS.get(level, "")})'
        })

    # Config saved but server push failed
    return jsonify({
        'success': True,
        'level': level,
        'level_name': FS_LOG_LEVELS.get(level, str(level)),
        'message': f'Saved to config (server push failed)',
        'warning': 'ESL connection error'
    })

@app.route('/api/sofia-trace', methods=['POST'])
@login_required
def api_sofia_trace():
    """Enable/disable Sofia SIP trace logging"""
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied'})

    data = request.json
    enable = data.get('enable', False)
    profile = data.get('profile', 'all')  # internal, external, or all

    try:
        if enable:
            # Enable SIP trace for profile - maximum debug
            fs_cli('console loglevel 7')  # DEBUG level
            if profile == 'all':
                fs_cli('sofia loglevel all 9')
                fs_cli('sofia global siptrace on')
            else:
                fs_cli(f'sofia loglevel {profile} 9')
                fs_cli(f'sofia profile {profile} siptrace on')
            message = f'Sofia SIP trace enabled for {profile}'
        else:
            # Disable SIP trace
            if profile == 'all':
                fs_cli('sofia loglevel all 0')
                fs_cli('sofia global siptrace off')
            else:
                fs_cli(f'sofia loglevel {profile} 0')
                fs_cli(f'sofia profile {profile} siptrace off')
            message = f'Sofia SIP trace disabled for {profile}'

        return jsonify({'success': True, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sofia-debug', methods=['GET'])
@login_required
def api_sofia_debug():
    """Get detailed Sofia debug information"""
    if not fs_allowed():
        return jsonify({'success': False, 'error': 'Access denied'})

    debug_info = []

    # Get detailed sofia info
    commands = [
        'sofia status',
        'sofia status profile internal',
        'sofia status profile external',
        'sofia status profile internal reg',
        'sofia status gateway',
        'sofia xmlstatus profile internal',
        'show registrations',
        'show calls',
        'show channels',
    ]

    for cmd in commands:
        result = fs_cli(cmd)
        if result and not result.startswith('-ERR'):
            debug_info.append({
                'command': cmd,
                'output': result
            })

    return jsonify({
        'success': True,
        'debug': debug_info,
        'timestamp': time.time()
    })

@app.route('/api/log-sources', methods=['GET'])
@login_required
def api_log_sources():
    """Get available log sources"""
    status = get_log_status()
    return jsonify(status)

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
    """Update/activate license"""
    data = request.json
    key = data.get('key', '')
    client_name = data.get('client_name', '')

    if key:
        success, msg = config_store.activate_license(key, client_name)
        return jsonify({'success': success, 'message': msg})
    else:
        # Just update client_name without key
        config = config_store.load_config()
        config['license']['client_name'] = client_name
        config_store.save_config(config)
        return jsonify({'success': True, 'message': 'License info updated'})

@app.route('/api/license/status')
@login_required
def api_license_status():
    """Get license status"""
    return jsonify(config_store.get_license_status())

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

    # Create filename: instancename_YYYYMMDD_HHMMSS.json
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    settings = config.get('settings', {})
    domain = settings.get('fs_domain', '') or 'wrapper'
    # Sanitize domain for filename
    import re as _re
    safe_domain = _re.sub(r'[^a-zA-Z0-9_-]', '_', domain)
    filename = f"{safe_domain}_{timestamp}.json"

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
# FreeSWITCH XML CURL Directory (Strict User Authentication)
################################################################################

@app.route('/api/freeswitch/directory', methods=['POST'])
def freeswitch_directory():
    """
    XML CURL endpoint for FreeSWITCH directory lookups.

    This enables STRICT username validation - only users that exist in the
    config can register. Without this, FreeSWITCH's digest auth can accept
    any username if the password matches ANY user in the directory.

    FreeSWITCH sends POST with:
    - user: the username trying to authenticate
    - domain: the SIP domain
    - action: auth-check, user_call, etc.
    """
    # Get POST data from FreeSWITCH
    user = request.form.get('user', '')
    domain = request.form.get('domain', '')
    action = request.form.get('action', '')
    purpose = request.form.get('purpose', '')

    # Log the request for debugging
    app.logger.info(f"[XML_CURL] Directory lookup: user={user}, domain={domain}, action={action}, purpose={purpose}")

    # Load config and find user
    config = config_store.load_config()
    users = config.get('users', [])

    # Find user by username
    user_data = None
    for u in users:
        if u.get('username') == user and u.get('enabled', True):
            user_data = u
            break

    if not user_data:
        # User not found - return "not found" response
        app.logger.warning(f"[XML_CURL] REJECTED: User '{user}' not found in directory")
        return '''<?xml version="1.0" encoding="UTF-8"?>
<document type="freeswitch/xml">
  <section name="result">
    <result status="not found"/>
  </section>
</document>''', 200, {'Content-Type': 'text/xml'}

    # User found - return directory entry with password
    password = user_data.get('password', '')
    extension = user_data.get('extension', user)

    app.logger.info(f"[XML_CURL] User '{user}' found, returning directory entry")

    xml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
<document type="freeswitch/xml">
  <section name="directory">
    <domain name="{domain}">
      <params>
        <param name="dial-string" value="{{^^:sip_invite_domain=${{domain}}:presence_id=${{dialed_user}}@${{domain}}}}{{${{sofia_contact(${{dialed_user}}@${{domain}})}}}}"/>
      </params>
      <user id="{user}">
        <params>
          <param name="password" value="{password}"/>
          <param name="vm-password" value="{password}"/>
        </params>
        <variables>
          <variable name="toll_allow" value="domestic,international,local"/>
          <variable name="accountcode" value="{user}"/>
          <variable name="user_context" value="default"/>
          <variable name="effective_caller_id_name" value="{user}"/>
          <variable name="effective_caller_id_number" value="{extension}"/>
          <variable name="outbound_caller_id_name" value="{user}"/>
          <variable name="outbound_caller_id_number" value="{extension}"/>
        </variables>
      </user>
    </domain>
  </section>
</document>'''

    return xml_response, 200, {'Content-Type': 'text/xml'}


################################################################################
# Profile API
################################################################################

@app.route('/api/profile/password', methods=['POST'])
@login_required
def api_profile_password():
    """Change admin password"""
    data = request.get_json()
    current = data.get('current_password', '')
    new_pass = data.get('new_password', '')

    # Verify current password
    if current != ADMIN_PASS:
        return jsonify({'success': False, 'message': 'Aktuelles Passwort ist falsch'})

    if len(new_pass) < 6:
        return jsonify({'success': False, 'message': 'Passwort muss mindestens 6 Zeichen haben'})

    # Update password in config
    config = config_store.load_config()
    if 'profile' not in config:
        config['profile'] = {}
    config['profile']['admin_password'] = new_pass
    config_store.save_config(config)

    return jsonify({'success': True, 'message': 'Passwort geändert. Neustart erforderlich.'})

@app.route('/api/profile/company', methods=['POST'])
@login_required
def api_profile_company():
    """Save company information"""
    data = request.get_json()
    config = config_store.load_config()
    if 'profile' not in config:
        config['profile'] = {}

    config['profile']['company_name'] = data.get('company_name', '')
    config['profile']['company_address'] = data.get('company_address', '')
    config['profile']['company_zip'] = data.get('company_zip', '')
    config['profile']['company_city'] = data.get('company_city', '')
    config['profile']['company_country'] = data.get('company_country', '')

    config_store.save_config(config)
    return jsonify({'success': True, 'message': 'Firmeninformationen gespeichert'})

@app.route('/api/profile/invoice', methods=['POST'])
@login_required
def api_profile_invoice():
    """Save invoice information"""
    data = request.get_json()
    config = config_store.load_config()
    if 'profile' not in config:
        config['profile'] = {}

    config['profile']['invoice_same_as_company'] = data.get('invoice_same_as_company', False)
    config['profile']['invoice_name'] = data.get('invoice_name', '')
    config['profile']['invoice_address'] = data.get('invoice_address', '')
    config['profile']['invoice_zip'] = data.get('invoice_zip', '')
    config['profile']['invoice_city'] = data.get('invoice_city', '')
    config['profile']['invoice_email'] = data.get('invoice_email', '')

    config_store.save_config(config)
    return jsonify({'success': True, 'message': 'Rechnungsinformationen gespeichert'})

@app.route('/api/profile/preferences', methods=['POST'])
@login_required
def api_profile_preferences():
    """Save UI preferences"""
    data = request.get_json()
    config = config_store.load_config()
    if 'profile' not in config:
        config['profile'] = {}

    config['profile']['theme_mode'] = data.get('theme_mode', 'light')
    config['profile']['color_theme'] = data.get('color_theme', 'default')

    config_store.save_config(config)
    return jsonify({'success': True})


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
  ESL: {FS_HOST}:{FS_PORT}
================================================================================
""")

    # Start ESL Event Subscriber in background
    if ESL_AVAILABLE:
        print("[ESL] Starting event subscriber...")
        esl_events.start_subscriber()
    else:
        print("[ESL] WARNING: greenswitch not installed - events will not work")

    # Watch JSON translation files for auto-reload in debug mode
    extra_files = list((Path(__file__).parent / 'lang').glob('*.json'))

    try:
        app.run(host='0.0.0.0', port=port, debug=debug, extra_files=extra_files)
    finally:
        # Stop ESL subscriber on shutdown
        if ESL_AVAILABLE:
            print("[ESL] Stopping event subscriber...")
            esl_events.stop_subscriber()
