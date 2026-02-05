"""
Config Store - JSON-based configuration storage for SIP Wrapper

Single JSON file for all configuration:
- Users (SIP users with password)
- ACL Users (IP-based users without password)
- Gateways (SIP providers/trunks)
- Routes (inbound/outbound routing rules)
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Config file path - can be overridden via environment
CONFIG_FILE = os.environ.get('CONFIG_FILE', '/var/lib/freeswitch/wrapper_config.json')

# Default config structure
DEFAULT_CONFIG = {
    "version": 1,
    "updated_at": None,
    "license": {
        "key": "",
        "client_name": ""
    },
    "settings": {
        "fs_domain": "",
        "external_sip_ip": "",
        "external_rtp_ip": "",
        "internal_sip_port": 5060,
        "external_sip_port": 5080,
        "codec_prefs": "PCMU,PCMA,G729,opus",
        "outbound_codec_prefs": "PCMU,PCMA,G729",
        "default_country_code": "49",
        "sip_user_agent": "InsideDynamic-Wrapper"
    },
    "users": [],
    "acl_users": [],
    "gateways": [],
    "routes": {
        "default_gateway": "",
        "default_extension": "",
        "outbound_caller_id": "",
        "inbound": [],
        "outbound": [],
        "user_routes": []
    },
    "security": {
        "blacklist": [],
        "whitelist": [],
        "whitelist_enabled": False
    }
}


def get_config_path():
    """Get config file path, create directory if needed"""
    path = Path(CONFIG_FILE)
    # For local development, use admin folder
    if not path.parent.exists():
        local_path = Path(__file__).parent / 'wrapper_config.json'
        return local_path
    return path


def load_config():
    """Load config from JSON file"""
    path = get_config_path()
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults for any missing keys
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save config to JSON file"""
    path = get_config_path()
    config['updated_at'] = datetime.now().isoformat()
    try:
        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving config: {e}")
        return False


# =============================================================================
# Users CRUD
# =============================================================================

def get_users():
    """Get all users"""
    config = load_config()
    return config.get('users', [])


def get_user(username):
    """Get user by username"""
    users = get_users()
    for user in users:
        if user.get('username') == username:
            return user
    return None


def add_user(username, password, extension, enabled=True):
    """Add new user"""
    config = load_config()
    # Check if exists
    for user in config['users']:
        if user.get('username') == username:
            return False, "User already exists"

    config['users'].append({
        'username': username,
        'password': password,
        'extension': extension,
        'enabled': enabled
    })
    save_config(config)
    return True, "User created"


def update_user(username, data):
    """Update existing user"""
    config = load_config()
    for i, user in enumerate(config['users']):
        if user.get('username') == username:
            config['users'][i].update(data)
            save_config(config)
            return True, "User updated"
    return False, "User not found"


def delete_user(username):
    """Delete user"""
    config = load_config()
    original_len = len(config['users'])
    config['users'] = [u for u in config['users'] if u.get('username') != username]
    if len(config['users']) < original_len:
        save_config(config)
        return True, "User deleted"
    return False, "User not found"


# =============================================================================
# ACL Users CRUD (IP-based, no password)
# =============================================================================

def get_acl_users():
    """Get all ACL users"""
    config = load_config()
    return config.get('acl_users', [])


def add_acl_user(username, ip_address, extension, caller_id=""):
    """Add new ACL user"""
    config = load_config()
    for user in config['acl_users']:
        if user.get('username') == username:
            return False, "ACL user already exists"

    config['acl_users'].append({
        'username': username,
        'ip_address': ip_address,
        'extension': extension,
        'caller_id': caller_id,
        'enabled': True
    })
    save_config(config)
    return True, "ACL user created"


def update_acl_user(username, data):
    """Update ACL user"""
    config = load_config()
    for i, user in enumerate(config['acl_users']):
        if user.get('username') == username:
            config['acl_users'][i].update(data)
            save_config(config)
            return True, "ACL user updated"
    return False, "ACL user not found"


def delete_acl_user(username):
    """Delete ACL user"""
    config = load_config()
    original_len = len(config['acl_users'])
    config['acl_users'] = [u for u in config['acl_users'] if u.get('username') != username]
    if len(config['acl_users']) < original_len:
        save_config(config)
        return True, "ACL user deleted"
    return False, "ACL user not found"


# =============================================================================
# Gateways CRUD
# =============================================================================

def get_gateways():
    """Get all gateways"""
    config = load_config()
    return config.get('gateways', [])


def get_gateway(name):
    """Get gateway by name"""
    gateways = get_gateways()
    for gw in gateways:
        if gw.get('name') == name:
            return gw
    return None


def add_gateway(name, host, port=5060, username="", password="",
                register=True, transport="udp", auth_username=""):
    """Add new gateway"""
    config = load_config()
    for gw in config['gateways']:
        if gw.get('name') == name:
            return False, "Gateway already exists"

    config['gateways'].append({
        'name': name,
        'host': host,
        'port': port,
        'username': username,
        'password': password,
        'register': register,
        'transport': transport,
        'auth_username': auth_username,
        'enabled': True
    })
    save_config(config)
    return True, "Gateway created"


def update_gateway(name, data):
    """Update gateway"""
    config = load_config()
    for i, gw in enumerate(config['gateways']):
        if gw.get('name') == name:
            config['gateways'][i].update(data)
            save_config(config)
            return True, "Gateway updated"
    return False, "Gateway not found"


def delete_gateway(name):
    """Delete gateway"""
    config = load_config()
    original_len = len(config['gateways'])
    config['gateways'] = [g for g in config['gateways'] if g.get('name') != name]
    if len(config['gateways']) < original_len:
        save_config(config)
        return True, "Gateway deleted"
    return False, "Gateway not found"


# =============================================================================
# Routes CRUD
# =============================================================================

def get_routes():
    """Get all routes"""
    config = load_config()
    return config.get('routes', DEFAULT_CONFIG['routes'])


def update_routes(routes_data):
    """Update routes configuration"""
    config = load_config()
    config['routes'].update(routes_data)
    save_config(config)
    return True, "Routes updated"


def add_inbound_route(did, destination, destination_type="extension"):
    """Add inbound route (DID -> extension or gateway)"""
    config = load_config()
    config['routes']['inbound'].append({
        'did': did,
        'destination': destination,
        'destination_type': destination_type  # 'extension' or 'gateway'
    })
    save_config(config)
    return True, "Inbound route added"


def delete_inbound_route(did):
    """Delete inbound route"""
    config = load_config()
    original_len = len(config['routes']['inbound'])
    config['routes']['inbound'] = [r for r in config['routes']['inbound'] if r.get('did') != did]
    if len(config['routes']['inbound']) < original_len:
        save_config(config)
        return True, "Inbound route deleted"
    return False, "Route not found"


def add_outbound_route(pattern, gateway, prepend="", strip=""):
    """Add outbound route (pattern -> gateway)"""
    config = load_config()
    config['routes']['outbound'].append({
        'pattern': pattern,
        'gateway': gateway,
        'prepend': prepend,
        'strip': strip
    })
    save_config(config)
    return True, "Outbound route added"


def add_user_route(username, gateway):
    """Add user-specific outbound route"""
    config = load_config()
    # Remove existing route for this user
    config['routes']['user_routes'] = [
        r for r in config['routes']['user_routes']
        if r.get('username') != username
    ]
    config['routes']['user_routes'].append({
        'username': username,
        'gateway': gateway
    })
    save_config(config)
    return True, "User route updated"


# =============================================================================
# Settings CRUD
# =============================================================================

def get_settings():
    """Get settings"""
    config = load_config()
    return config.get('settings', DEFAULT_CONFIG['settings'])


def update_settings(settings_data):
    """Update settings"""
    config = load_config()
    config['settings'].update(settings_data)
    save_config(config)
    return True, "Settings updated"


# =============================================================================
# Inbound Routes (gateway -> extension)
# =============================================================================

def get_inbound_routes():
    """Get all inbound routes"""
    config = load_config()
    return config.get('routes', {}).get('inbound', [])


def add_inbound_route_gw(gateway, extension):
    """Add inbound route (gateway -> extension)"""
    config = load_config()
    # Check if exists
    for route in config['routes']['inbound']:
        if route.get('gateway') == gateway:
            return False, "Route for this gateway already exists"

    config['routes']['inbound'].append({
        'gateway': gateway,
        'extension': extension
    })
    save_config(config)
    return True, "Inbound route added"


def update_inbound_route(gateway, extension):
    """Update inbound route"""
    config = load_config()
    for i, route in enumerate(config['routes']['inbound']):
        if route.get('gateway') == gateway:
            config['routes']['inbound'][i]['extension'] = extension
            save_config(config)
            return True, "Inbound route updated"
    return False, "Route not found"


def delete_inbound_route_gw(gateway):
    """Delete inbound route by gateway"""
    config = load_config()
    original_len = len(config['routes']['inbound'])
    config['routes']['inbound'] = [r for r in config['routes']['inbound'] if r.get('gateway') != gateway]
    if len(config['routes']['inbound']) < original_len:
        save_config(config)
        return True, "Inbound route deleted"
    return False, "Route not found"


# =============================================================================
# Outbound User Routes (user -> gateway)
# =============================================================================

def get_outbound_user_routes():
    """Get all outbound user routes"""
    config = load_config()
    return config.get('routes', {}).get('user_routes', [])


def add_outbound_user_route(username, gateway):
    """Add/update user-specific outbound route"""
    config = load_config()
    # Remove existing route for this user
    config['routes']['user_routes'] = [
        r for r in config['routes']['user_routes']
        if r.get('username') != username
    ]
    config['routes']['user_routes'].append({
        'username': username,
        'gateway': gateway
    })
    save_config(config)
    return True, "User route updated"


def delete_outbound_user_route(username):
    """Delete user route"""
    config = load_config()
    original_len = len(config['routes']['user_routes'])
    config['routes']['user_routes'] = [r for r in config['routes']['user_routes'] if r.get('username') != username]
    if len(config['routes']['user_routes']) < original_len:
        save_config(config)
        return True, "User route deleted"
    return False, "Route not found"


# =============================================================================
# Default Settings
# =============================================================================

def get_default_gateway():
    """Get default gateway"""
    config = load_config()
    return config.get('routes', {}).get('default_gateway', '')


def set_default_gateway(gateway):
    """Set default gateway"""
    config = load_config()
    config['routes']['default_gateway'] = gateway
    save_config(config)
    return True, "Default gateway updated"


def get_default_extension():
    """Get default extension"""
    config = load_config()
    return config.get('routes', {}).get('default_extension', '')


def set_default_extension(extension):
    """Set default extension"""
    config = load_config()
    config['routes']['default_extension'] = extension
    save_config(config)
    return True, "Default extension updated"


def get_outbound_caller_id():
    """Get outbound caller ID"""
    config = load_config()
    return config.get('routes', {}).get('outbound_caller_id', '')


def set_outbound_caller_id(caller_id):
    """Set outbound caller ID"""
    config = load_config()
    config['routes']['outbound_caller_id'] = caller_id
    save_config(config)
    return True, "Outbound caller ID updated"


# =============================================================================
# Import from ENV (one-time migration)
# =============================================================================

def import_from_env():
    """Import configuration from environment variables (one-time migration)"""
    import os

    config = load_config()
    imported = {'users': 0, 'gateways': 0, 'acl_users': 0, 'inbound_routes': 0, 'user_routes': 0}

    # Import License
    if 'license' not in config:
        config['license'] = {}
    config['license']['key'] = os.environ.get('LICENSE_KEY', config['license'].get('key', ''))
    config['license']['client_name'] = os.environ.get('CLIENT_NAME', config['license'].get('client_name', ''))

    # Import Settings
    if 'settings' not in config:
        config['settings'] = DEFAULT_CONFIG['settings'].copy()
    config['settings']['fs_domain'] = os.environ.get('FS_DOMAIN', config['settings'].get('fs_domain', ''))
    config['settings']['external_sip_ip'] = os.environ.get('EXTERNAL_SIP_IP', config['settings'].get('external_sip_ip', ''))
    config['settings']['external_rtp_ip'] = os.environ.get('EXTERNAL_RTP_IP', config['settings'].get('external_rtp_ip', ''))
    config['settings']['codec_prefs'] = os.environ.get('CODEC_PREFS', config['settings'].get('codec_prefs', 'PCMU,PCMA,G729,opus'))
    config['settings']['outbound_codec_prefs'] = os.environ.get('OUTBOUND_CODEC_PREFS', config['settings'].get('outbound_codec_prefs', 'PCMU,PCMA,G729'))
    config['settings']['sip_user_agent'] = os.environ.get('SIP_USER_AGENT', config['settings'].get('sip_user_agent', 'InsideDynamic-Wrapper'))

    # Import Users: username:password:extension,...
    users_env = os.environ.get('USERS', '')
    if users_env and not config.get('users'):
        config['users'] = []
        for user_str in users_env.split(','):
            parts = user_str.strip().split(':')
            if len(parts) >= 3:
                config['users'].append({
                    'username': parts[0],
                    'password': parts[1],
                    'extension': parts[2],
                    'enabled': True
                })
                imported['users'] += 1

    # Import Gateways: type:name:host:port:user:pass:register:transport[:auth_user],...
    gateways_env = os.environ.get('GATEWAYS', '')
    if gateways_env and not config.get('gateways'):
        config['gateways'] = []
        for gw_str in gateways_env.split(','):
            parts = gw_str.strip().split(':')
            if len(parts) >= 6:
                gw = {
                    'type': parts[0],
                    'name': parts[1],
                    'host': parts[2],
                    'port': int(parts[3]) if parts[3].isdigit() else 5060,
                    'username': parts[4],
                    'password': parts[5],
                    'register': parts[6].lower() == 'true' if len(parts) > 6 else True,
                    'transport': parts[7] if len(parts) > 7 else 'udp',
                    'auth_username': parts[8] if len(parts) > 8 else '',
                    'enabled': True
                }
                config['gateways'].append(gw)
                imported['gateways'] += 1

    # Import ACL Users: username:ip1|ip2|ip3:extension:caller_id,...
    acl_env = os.environ.get('ACL_USERS', '')
    if acl_env and not config.get('acl_users'):
        config['acl_users'] = []
        for acl_str in acl_env.split(','):
            parts = acl_str.strip().split(':')
            if len(parts) >= 3:
                config['acl_users'].append({
                    'username': parts[0],
                    'ips': parts[1].split('|'),
                    'extension': parts[2],
                    'caller_id': parts[3] if len(parts) > 3 else '',
                    'enabled': True
                })
                imported['acl_users'] += 1

    # Import Inbound Routes: gateway:extension,...
    inbound_env = os.environ.get('INBOUND_ROUTES', '')
    if inbound_env and not config.get('routes', {}).get('inbound'):
        if 'routes' not in config:
            config['routes'] = DEFAULT_CONFIG['routes'].copy()
        config['routes']['inbound'] = []
        for route_str in inbound_env.split(','):
            parts = route_str.strip().split(':')
            if len(parts) >= 2:
                config['routes']['inbound'].append({
                    'gateway': parts[0],
                    'extension': parts[1]
                })
                imported['inbound_routes'] += 1

    # Import Outbound User Routes: user:gateway,...
    user_routes_env = os.environ.get('OUTBOUND_USER_ROUTES', '')
    if user_routes_env and not config.get('routes', {}).get('user_routes'):
        if 'routes' not in config:
            config['routes'] = DEFAULT_CONFIG['routes'].copy()
        config['routes']['user_routes'] = []
        for route_str in user_routes_env.split(','):
            parts = route_str.strip().split(':')
            if len(parts) >= 2:
                config['routes']['user_routes'].append({
                    'username': parts[0],
                    'gateway': parts[1]
                })
                imported['user_routes'] += 1

    # Import defaults
    if 'routes' not in config:
        config['routes'] = DEFAULT_CONFIG['routes'].copy()

    config['routes']['default_gateway'] = os.environ.get('DEFAULT_GATEWAY', config['routes'].get('default_gateway', ''))
    config['routes']['default_extension'] = os.environ.get('DEFAULT_EXTENSION', config['routes'].get('default_extension', ''))
    config['routes']['outbound_caller_id'] = os.environ.get('OUTBOUND_CALLER_ID', config['routes'].get('outbound_caller_id', ''))

    if 'settings' not in config:
        config['settings'] = DEFAULT_CONFIG['settings'].copy()
    config['settings']['default_country_code'] = os.environ.get('DEFAULT_COUNTRY_CODE', '49')

    save_config(config)
    return imported


# =============================================================================
# Export for provision.sh
# =============================================================================

def get_full_config():
    """Get full configuration"""
    return load_config()


def export_for_provision():
    """Export config in format compatible with provision.sh / routing_config.json"""
    config = load_config()

    # Build users list for JSON
    users = []
    for user in config.get('users', []):
        if user.get('enabled', True):
            users.append({
                'username': user['username'],
                'password': user['password'],
                'extension': user['extension']
            })

    # Build gateways list
    gateways = []
    for gw in config.get('gateways', []):
        if gw.get('enabled', True):
            gateways.append({
                'name': gw['name'],
                'type': gw.get('type', 'sip'),
                'host': gw['host'],
                'port': gw.get('port', 5060),
                'username': gw.get('username', ''),
                'password': gw.get('password', ''),
                'register': gw.get('register', True),
                'transport': gw.get('transport', 'udp'),
                'auth_username': gw.get('auth_username', '')
            })

    # Build ACL users
    acl_users = []
    for acl in config.get('acl_users', []):
        if acl.get('enabled', True):
            acl_users.append({
                'username': acl['username'],
                'ips': acl.get('ips', []),
                'extension': acl['extension'],
                'caller_id': acl.get('caller_id', '')
            })

    routes = config.get('routes', {})
    settings = config.get('settings', {})
    license_info = config.get('license', {})

    return {
        # License
        'license_key': license_info.get('key', ''),
        'client_name': license_info.get('client_name', ''),

        # Settings
        'fs_domain': settings.get('fs_domain', ''),
        'external_sip_ip': settings.get('external_sip_ip', ''),
        'external_rtp_ip': settings.get('external_rtp_ip', ''),
        'codec_prefs': settings.get('codec_prefs', 'PCMU,PCMA,G729,opus'),
        'outbound_codec_prefs': settings.get('outbound_codec_prefs', 'PCMU,PCMA,G729'),
        'sip_user_agent': settings.get('sip_user_agent', 'InsideDynamic-Wrapper'),
        'default_country_code': settings.get('default_country_code', '49'),

        # Users & Gateways
        'users': users,
        'acl_users': acl_users,
        'gateways': gateways,

        # Routes
        'inbound_routes': routes.get('inbound', []),
        'outbound_user_routes': routes.get('user_routes', []),
        'outbound_routes': routes.get('outbound', []),
        'default_gateway': routes.get('default_gateway', ''),
        'default_extension': routes.get('default_extension', ''),
        'outbound_caller_id': routes.get('outbound_caller_id', ''),

        # Security
        'blacklist': config.get('security', {}).get('blacklist', []),
        'whitelist': config.get('security', {}).get('whitelist', []),
        'whitelist_enabled': config.get('security', {}).get('whitelist_enabled', False)
    }


# =============================================================================
# Security - Blacklist / Whitelist
# =============================================================================

def get_security():
    """Get security settings"""
    config = load_config()
    return config.get('security', DEFAULT_CONFIG['security'])


def update_security(security_data):
    """Update security settings"""
    config = load_config()
    if 'security' not in config:
        config['security'] = DEFAULT_CONFIG['security'].copy()
    config['security'].update(security_data)
    save_config(config)
    return True, "Security settings updated"


def add_to_blacklist(ip, comment=""):
    """Add IP to blacklist"""
    config = load_config()
    if 'security' not in config:
        config['security'] = DEFAULT_CONFIG['security'].copy()

    # Check if already exists
    for entry in config['security']['blacklist']:
        if entry.get('ip') == ip:
            return False, "IP already in blacklist"

    config['security']['blacklist'].append({
        'ip': ip,
        'comment': comment,
        'added_at': datetime.now().isoformat()
    })
    save_config(config)
    return True, "IP added to blacklist"


def remove_from_blacklist(ip):
    """Remove IP from blacklist"""
    config = load_config()
    if 'security' not in config:
        return False, "IP not found"

    original_len = len(config['security']['blacklist'])
    config['security']['blacklist'] = [
        e for e in config['security']['blacklist']
        if e.get('ip') != ip
    ]
    if len(config['security']['blacklist']) < original_len:
        save_config(config)
        return True, "IP removed from blacklist"
    return False, "IP not found"


def add_to_whitelist(ip, comment=""):
    """Add IP to whitelist"""
    config = load_config()
    if 'security' not in config:
        config['security'] = DEFAULT_CONFIG['security'].copy()

    # Check if already exists
    for entry in config['security']['whitelist']:
        if entry.get('ip') == ip:
            return False, "IP already in whitelist"

    config['security']['whitelist'].append({
        'ip': ip,
        'comment': comment,
        'added_at': datetime.now().isoformat()
    })
    save_config(config)
    return True, "IP added to whitelist"


def remove_from_whitelist(ip):
    """Remove IP from whitelist"""
    config = load_config()
    if 'security' not in config:
        return False, "IP not found"

    original_len = len(config['security']['whitelist'])
    config['security']['whitelist'] = [
        e for e in config['security']['whitelist']
        if e.get('ip') != ip
    ]
    if len(config['security']['whitelist']) < original_len:
        save_config(config)
        return True, "IP removed from whitelist"
    return False, "IP not found"


def set_whitelist_enabled(enabled):
    """Enable or disable whitelist mode"""
    config = load_config()
    if 'security' not in config:
        config['security'] = DEFAULT_CONFIG['security'].copy()
    config['security']['whitelist_enabled'] = enabled
    save_config(config)
    return True, "Whitelist mode " + ("enabled" if enabled else "disabled")
