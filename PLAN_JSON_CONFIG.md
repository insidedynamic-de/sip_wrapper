# Plan: Full JSON Config System

## Goal
Replace ENV-based configuration with JSON file for:
- Users (SIP users)
- Gateways (SIP trunks)
- Routing (inbound/outbound routes)
- ACL Users (IP-based auth)

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Admin Portal   │────▶│  config_store.py │────▶│  JSON Config    │
│  (Flask App)    │     │  (CRUD API)      │     │  wrapper_config │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   FreeSWITCH    │◀────│   provision.sh   │◀────│  "Apply Config" │
│   (XML Config)  │     │   (JSON → XML)   │     │  (Button/API)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## JSON Config Structure

```json
{
  "version": "1.0",
  "last_modified": "2026-02-03T00:00:00Z",

  "settings": {
    "domain": "apps.linkify.cloud",
    "external_sip_ip": "46.224.205.100",
    "external_rtp_ip": "46.224.205.100",
    "default_gateway": "fritz-rt",
    "default_extension": "1001",
    "default_country_code": "49",
    "outbound_caller_id": "+4932221803989"
  },

  "users": [
    {
      "id": "user_001",
      "username": "fritz",
      "password": "SecretPass",
      "extension": "1001",
      "enabled": true
    }
  ],

  "acl_users": [
    {
      "id": "acl_001",
      "username": "vapi1",
      "ips": ["34.213.129.25", "44.238.177.138"],
      "extension": "9000",
      "caller_id": "+4932221803988",
      "enabled": true
    }
  ],

  "gateways": [
    {
      "id": "gw_001",
      "name": "fritz-rt",
      "type": "sip",
      "host": "7cj8rm6hnqk5fwta.myfritz.net",
      "port": 5060,
      "username": "INDYN-VNI-74",
      "password": "Mannheim.68165",
      "register": true,
      "transport": "udp",
      "enabled": true
    }
  ],

  "inbound_routes": [
    {
      "id": "in_001",
      "gateway": "fritz-rt",
      "extension": "1001",
      "description": "Fritz -> Extension 1001"
    }
  ],

  "outbound_user_routes": [
    {
      "id": "out_001",
      "user": "fritz",
      "gateway": "fritz-rt",
      "description": "Fritz user -> Fritz gateway"
    }
  ],

  "outbound_pattern_routes": [
    {
      "id": "pat_001",
      "pattern": "^49",
      "gateway": "fritz-rt",
      "prepend": "",
      "strip": "0",
      "description": "Germany -> Fritz"
    }
  ]
}
```

## Implementation Steps

### Phase 1: Config Store (config_store.py)
- [x] Basic structure exists
- [ ] Add full CRUD for users
- [ ] Add full CRUD for gateways
- [ ] Add full CRUD for acl_users
- [ ] Add full CRUD for inbound_routes
- [ ] Add full CRUD for outbound_user_routes
- [ ] Add full CRUD for outbound_pattern_routes
- [ ] Add settings management
- [ ] Add JSON validation
- [ ] Add backup before save

### Phase 2: Admin Portal (app.py + templates)
- [ ] Update /users page - full CRUD UI
- [ ] Update /gateways page - full CRUD UI
- [ ] Update /routing page - full CRUD UI
- [ ] Add /config page - settings management
- [ ] Add "Apply Changes" button (runs provision.sh)
- [ ] Add "Pending Changes" indicator
- [ ] Add validation feedback

### Phase 3: Provision Script (provision.sh)
- [ ] Read users from JSON (fallback to ENV)
- [ ] Read gateways from JSON (fallback to ENV)
- [ ] Read acl_users from JSON (fallback to ENV)
- [ ] Read routes from JSON (fallback to ENV)
- [ ] Add --from-json flag for explicit JSON mode
- [ ] Keep ENV support for backwards compatibility

### Phase 4: Apply Config Flow
- [ ] API endpoint: POST /api/apply-config
- [ ] Backup current FreeSWITCH config
- [ ] Run provision.sh --from-json
- [ ] Reload FreeSWITCH (sofia profile restart)
- [ ] Return status to UI
- [ ] Rollback on failure

## Files to Modify

1. **admin/config_store.py** - Full CRUD implementation
2. **admin/app.py** - API endpoints and routes
3. **admin/templates/users.html** - CRUD UI
4. **admin/templates/gateways.html** - CRUD UI
5. **admin/templates/routing.html** - CRUD UI
6. **admin/templates/config.html** - Settings UI
7. **admin/static/js/admin.js** - Frontend logic
8. **provision.sh** - JSON config reader

## API Endpoints

```
# Users
GET    /api/users              - List all users
POST   /api/users              - Create user
PUT    /api/users/<id>         - Update user
DELETE /api/users/<id>         - Delete user

# Gateways
GET    /api/gateways           - List all gateways
POST   /api/gateways           - Create gateway
PUT    /api/gateways/<id>      - Update gateway
DELETE /api/gateways/<id>      - Delete gateway

# ACL Users
GET    /api/acl-users          - List all ACL users
POST   /api/acl-users          - Create ACL user
PUT    /api/acl-users/<id>     - Update ACL user
DELETE /api/acl-users/<id>     - Delete ACL user

# Routing
GET    /api/routes/inbound     - List inbound routes
POST   /api/routes/inbound     - Create inbound route
PUT    /api/routes/inbound/<id>- Update inbound route
DELETE /api/routes/inbound/<id>- Delete inbound route

GET    /api/routes/outbound    - List outbound user routes
POST   /api/routes/outbound    - Create outbound route
...

# Config
GET    /api/config             - Get all config
POST   /api/config/apply       - Apply config to FreeSWITCH
POST   /api/config/backup      - Create backup
POST   /api/config/restore     - Restore from backup
```

## Migration Path

1. First deploy keeps ENV support (backwards compatible)
2. Admin portal reads from JSON, falls back to ENV
3. Any change via admin portal writes to JSON
4. "Apply Config" regenerates FreeSWITCH config from JSON
5. Eventually ENV can be deprecated

## Priority Order

1. **Users CRUD** - Most commonly changed
2. **Gateways CRUD** - Second most common
3. **Routing CRUD** - Third priority
4. **Settings** - Least often changed
5. **ACL Users** - Special use case
