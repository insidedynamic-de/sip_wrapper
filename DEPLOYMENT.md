# FreeSWITCH Production Deployment Guide

Complete guide for deploying FreeSWITCH with automated provisioning from environment variables.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation Methods](#installation-methods)
3. [Environment Variables](#environment-variables)
4. [Configuration Examples](#configuration-examples)
5. [Usage Scenarios](#usage-scenarios)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Docker Deployment (Recommended)

1. **Clone repository:**
```bash
git clone https://github.com/your-org/freeswitch-production.git
cd freeswitch-production
```

2. **Copy example environment file:**
```bash
cp .env.example .env
```

3. **Edit environment variables:**
```bash
nano .env
```

4. **Build and run:**
```bash
docker-compose -f docker-compose.production.yml up -d
```

5. **Check status:**
```bash
docker-compose exec freeswitch fs_cli -x "sofia status"
```

### Direct Linux Installation

1. **Run installation script:**
```bash
sudo bash install.sh
```

2. **Set environment variables:**
```bash
export FS_DOMAIN="sip.example.com"
export EXTERNAL_SIP_IP="203.0.113.10"
export EXTERNAL_RTP_IP="203.0.113.10"
# ... (see Environment Variables section)
```

3. **Run provisioning:**
```bash
sudo bash provision.sh
```

4. **Start FreeSWITCH:**
```bash
sudo systemctl start freeswitch
```

---

## Installation Methods

### Method 1: Docker (Production)

**Dockerfile.production** - Uses official SignalWire packages

```bash
docker build -f Dockerfile.production -t freeswitch-prod:latest .
```

### Method 2: Direct Installation

**install.sh** - Automated installation on Debian/Ubuntu

Supported OS:
- Debian 11 (Bullseye)
- Debian 12 (Bookworm)
- Ubuntu 20.04 LTS
- Ubuntu 22.04 LTS

Requirements:
- Root access
- Internet connection

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `FS_DOMAIN` | SIP domain name | `sip.example.com` |
| `EXTERNAL_SIP_IP` | External IP for SIP signaling | `203.0.113.10` |
| `EXTERNAL_RTP_IP` | External IP for RTP media | `203.0.113.10` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `INTERNAL_SIP_PORT` | Internal profile SIP port | `5060` | `5060` |
| `EXTERNAL_SIP_PORT` | External profile SIP port | `5080` | `5080` |
| `RTP_START_PORT` | RTP port range start | `16384` | `16384` |
| `RTP_END_PORT` | RTP port range end | `32768` | `32768` |
| `CODEC_PREFS` | Codec preferences | `PCMU,PCMA,G729,opus` | `PCMU,PCMA` |
| `SIP_DEBUG` | Enable SIP debugging | `0` | `1` |
| `SIP_TRACE` | Enable SIP tracing | `no` | `yes` |

### Users Configuration

#### Authenticated Users (Password-based)

**Format:** `username:password:extension`

```bash
USERS="alice:secret123:1001,bob:secret456:1002,charlie:secret789:1003"
```

- `username`: SIP username for authentication
- `password`: SIP password
- `extension`: Extension number (optional, defaults to username)

#### ACL Users (IP-based, no password)

**Format:** `username:ip_address:extension`

```bash
ACL_USERS="trunk1:192.168.1.100:2001,trunk2:192.168.1.101:2002"
```

- `username`: Identifier
- `ip_address`: IP address to allow
- `extension`: Extension number

### Gateways Configuration

**Format:** `name:host:port:username:password:register:transport`

```bash
GATEWAYS="provider1:sip.provider1.com:5060:myuser:mypass:true:udp,provider2:sip.provider2.com:5060:::false:udp"
```

Fields:
- `name`: Gateway identifier (required)
- `host`: SIP provider hostname/IP (required)
- `port`: SIP port (default: 5060)
- `username`: Authentication username (optional)
- `password`: Authentication password (optional)
- `register`: Register with provider (true/false, default: true)
- `transport`: Transport protocol (udp/tcp, default: udp)

### Outbound Routes Configuration

**Format:** `pattern:gateway:prepend:strip`

```bash
OUTBOUND_ROUTES="^00.*:provider1::00,^[1-9].*:provider2:+49:"
```

Fields:
- `pattern`: Regex pattern for destination number (required)
- `gateway`: Gateway name to use (required)
- `prepend`: Prefix to add to number (optional)
- `strip`: Prefix to remove from number (optional)

Alternatively, use a default gateway:
```bash
DEFAULT_GATEWAY="provider1"
```

### Inbound Routes Configuration

**Format:** `DID:extension`

```bash
INBOUND_ROUTES="+49301234567:1001,+49301234568:1002,*:1000"
```

Fields:
- `DID`: Incoming phone number (or `*` for catch-all)
- `extension`: Target extension/user

Alternatively, use a default extension:
```bash
DEFAULT_EXTENSION="1000"
```

---

## Configuration Examples

### Example 1: Simple Office PBX

**Scenario:** 3 users, 1 SIP trunk provider, simple routing

```bash
# Core settings
FS_DOMAIN="office.local"
EXTERNAL_SIP_IP="203.0.113.50"
EXTERNAL_RTP_IP="203.0.113.50"

# Users
USERS="alice:pass123:1001,bob:pass456:1002,carol:pass789:1003"

# Gateway
GATEWAYS="voip_provider:sip.provider.com:5060:account123:secret123:true:udp"

# Outbound: all calls via provider
DEFAULT_GATEWAY="voip_provider"

# Inbound: route to alice
INBOUND_ROUTES="*:1001"
```

### Example 2: Multi-Provider Setup

**Scenario:** 2 providers, route based on destination

```bash
FS_DOMAIN="pbx.company.com"
EXTERNAL_SIP_IP="203.0.113.100"
EXTERNAL_RTP_IP="203.0.113.100"

USERS="user1:pass1:1001,user2:pass2:1002"

# Multiple providers
GATEWAYS="provider_de:sip.de-provider.com:5060:user_de:pass_de:true:udp,provider_us:sip.us-provider.com:5060:user_us:pass_us:true:udp"

# Route German numbers via provider_de, US numbers via provider_us
OUTBOUND_ROUTES="^\\+49.*:provider_de,^\\+1.*:provider_us,^.*:provider_de"

# Route different DIDs to different users
INBOUND_ROUTES="+4930111111:1001,+4930222222:1002"
```

### Example 3: SIP Trunk with ACL (no auth)

**Scenario:** SIP trunk from provider without authentication, IP-based

```bash
FS_DOMAIN="trunk.example.com"
EXTERNAL_SIP_IP="203.0.113.200"
EXTERNAL_RTP_IP="203.0.113.200"

# No password-based users
USERS=""

# IP-based trunk
ACL_USERS="provider_trunk:198.51.100.50:9000"

# Gateway without registration
GATEWAYS="provider:sip.provider.net:5060:::false:udp"

# All outbound via provider
DEFAULT_GATEWAY="provider"

# All inbound to trunk extension
DEFAULT_EXTENSION="9000"
```

### Example 4: Multiple DIDs with IVR

**Scenario:** Multiple phone numbers, route to different extensions

```bash
FS_DOMAIN="call-center.example.com"
EXTERNAL_SIP_IP="203.0.113.150"
EXTERNAL_RTP_IP="203.0.113.150"

USERS="reception:pass1:1000,support:pass2:2000,sales:pass3:3000"

GATEWAYS="trunk:sip.trunk-provider.com:5060:acc123:sec123:true:udp"

DEFAULT_GATEWAY="trunk"

# Route different incoming numbers
INBOUND_ROUTES="+49301111111:1000,+49302222222:2000,+49303333333:3000,*:1000"
```

### Example 5: Number Transformation

**Scenario:** Transform numbers before sending to provider

```bash
FS_DOMAIN="transform.example.com"
EXTERNAL_SIP_IP="203.0.113.175"
EXTERNAL_RTP_IP="203.0.113.175"

USERS="user:password:1001"

GATEWAYS="provider:sip.provider.com:5060:myuser:mypass:true:udp"

# Remove leading 0, add +49 (Germany)
# Pattern: match 0XXXXXXX, strip 0, prepend +49
OUTBOUND_ROUTES="^0[1-9][0-9]{6,}$:provider:+49:0"

INBOUND_ROUTES="*:1001"
```

---

## Usage Scenarios

### Scenario 1: Docker Compose with Coolify

**docker-compose.production.yml:**

```yaml
version: '3.9'

services:
  freeswitch:
    build:
      context: .
      dockerfile: Dockerfile.production
    container_name: freeswitch-prod
    env_file:
      - .env
    network_mode: host
    restart: unless-stopped
    volumes:
      - fs_backups:/var/backups/freeswitch
    healthcheck:
      test: ["CMD", "fs_cli", "-x", "status"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  fs_backups:
```

Deploy on Coolify:
1. Create new service: Docker Compose
2. Upload docker-compose.production.yml
3. Set environment variables in Coolify UI
4. Deploy

### Scenario 2: Kubernetes Deployment

**freeswitch-deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: freeswitch
spec:
  replicas: 1
  selector:
    matchLabels:
      app: freeswitch
  template:
    metadata:
      labels:
        app: freeswitch
    spec:
      containers:
      - name: freeswitch
        image: your-registry/freeswitch-prod:latest
        envFrom:
        - configMapRef:
            name: freeswitch-config
        - secretRef:
            name: freeswitch-secrets
        ports:
        - containerPort: 5060
          protocol: UDP
        - containerPort: 5080
          protocol: UDP
        volumeMounts:
        - name: backups
          mountPath: /var/backups/freeswitch
      volumes:
      - name: backups
        persistentVolumeClaim:
          claimName: freeswitch-backups-pvc
```

### Scenario 3: Systemd Service (Bare Metal)

After running install.sh:

```bash
# Set environment in /etc/environment or /etc/freeswitch/env
sudo nano /etc/freeswitch/env

# Add all ENV variables
FS_DOMAIN=sip.example.com
EXTERNAL_SIP_IP=203.0.113.10
...

# Create systemd override
sudo systemctl edit freeswitch

# Add:
[Service]
EnvironmentFile=/etc/freeswitch/env
ExecStartPre=/usr/local/bin/provision.sh

# Reload and start
sudo systemctl daemon-reload
sudo systemctl start freeswitch
```

---

## Troubleshooting

### Check FreeSWITCH Status

```bash
# Via CLI
fs_cli -x "status"
fs_cli -x "sofia status"
fs_cli -x "sofia status profile internal"
fs_cli -x "sofia status profile external"
fs_cli -x "sofia status gateway"
fs_cli -x "show registrations"
fs_cli -x "show channels"
```

### Check Configuration

```bash
# Inside Docker
docker exec -it freeswitch-prod bash
ls -la /etc/freeswitch/

# Check generated files
cat /etc/freeswitch/vars.xml
cat /etc/freeswitch/sip_profiles/internal.xml
cat /etc/freeswitch/directory/default.xml
```

### Enable SIP Debugging

```bash
# Set environment variables
SIP_DEBUG=9
SIP_TRACE=yes

# In fs_cli
sofia profile internal siptrace on
sofia profile external siptrace on

# View logs
fs_cli -x "console loglevel debug"
```

### Common Issues

#### Gateway not registering

Check:
1. Gateway credentials correct
2. Firewall allows outbound to provider
3. NAT settings correct (`EXTERNAL_SIP_IP`)
4. Provider allows your IP

```bash
fs_cli -x "sofia status gateway gateway_name"
```

#### Inbound calls not routing

Check:
1. `INBOUND_ROUTES` defined correctly
2. DID matches exactly (including country code)
3. External profile listening on correct port
4. Provider sending to correct IP:port

```bash
fs_cli -x "sofia global siptrace on"
# Make test call and watch logs
```

#### No Audio / One-way Audio

Check:
1. `EXTERNAL_RTP_IP` set correctly
2. Firewall allows UDP `RTP_START_PORT`-`RTP_END_PORT`
3. NAT traversal working
4. Codecs match between endpoints

```bash
fs_cli -x "show channels"
# Check RTP IP addresses
```

#### Users can't register

Check:
1. `USERS` format correct
2. Internal profile started
3. Firewall allows UDP 5060
4. User credentials match exactly

```bash
fs_cli -x "sofia status profile internal"
```

### Reload Configuration

If you change environment variables:

```bash
# Docker
docker-compose down
docker-compose up -d

# Bare metal
sudo /usr/local/bin/provision.sh
sudo systemctl reload freeswitch
```

Or live reload:

```bash
fs_cli -x "reloadxml"
fs_cli -x "sofia profile internal rescan"
fs_cli -x "sofia profile external rescan"
```

---

## Security Best Practices

1. **Use strong passwords** for SIP users
2. **Restrict ACLs** - only allow known IPs
3. **Enable TLS** for SIP signaling if possible
4. **Firewall rules** - only open necessary ports
5. **Regular updates** - keep FreeSWITCH updated
6. **Monitor logs** - watch for authentication failures
7. **Fail2ban** - implement rate limiting for auth failures

---

## Additional Resources

- FreeSWITCH Documentation: https://freeswitch.org/confluence/
- SignalWire Repository: https://developer.signalwire.com/freeswitch
- Community Support: https://freeswitch.org/support/

---

## License

This deployment solution is provided as-is for production use.
