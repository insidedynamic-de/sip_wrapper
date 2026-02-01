# FreeSWITCH Production Deployment

Production-ready FreeSWITCH installation and configuration system with full automation via environment variables. No demo configurations, no manual XML editing.

## Features

- **Automated Installation**: One-command installation from official SignalWire repositories
- **ENV-based Configuration**: All settings via environment variables
- **Multiple Users**: Support for authenticated (password) and ACL-based (IP) users
- **Multiple Gateways**: Connect to multiple SIP providers/trunks
- **Flexible Routing**: Custom inbound (DID → user) and outbound (user → gateway) routes
- **NAT Support**: Built-in NAT traversal with external IP configuration
- **Production-Ready**: Clean configuration without demo/example files
- **Docker Support**: Full Docker/Kubernetes deployment support
- **Auto-Provisioning**: Configuration regeneration on container start

## Project Structure

```
.
├── install.sh                      # FreeSWITCH installation script (Debian/Ubuntu)
├── provision.sh                    # Configuration generator from ENV
├── docker-entrypoint.sh            # Docker entrypoint
├── Dockerfile.production           # Production Docker image
├── docker-compose.production.yml   # Docker Compose configuration
├── .env.example                    # Environment variables template
├── DEPLOYMENT.md                   # Complete deployment guide
└── README.production.md            # This file
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit configuration
nano .env
# Set: FS_DOMAIN, EXTERNAL_SIP_IP, USERS, GATEWAYS, etc.

# 3. Build and run
docker-compose -f docker-compose.production.yml up -d

# 4. Check status
docker-compose exec freeswitch fs_cli -x "sofia status"
```

### Option 2: Direct Installation (Bare Metal)

```bash
# 1. Install FreeSWITCH
sudo bash install.sh

# 2. Set environment variables
export FS_DOMAIN="sip.example.com"
export EXTERNAL_SIP_IP="203.0.113.10"
export EXTERNAL_RTP_IP="203.0.113.10"
export USERS="alice:pass123:1001,bob:pass456:1002"
export GATEWAYS="provider:sip.provider.com:5060:user:pass:true:udp"
export DEFAULT_GATEWAY="provider"
export INBOUND_ROUTES="*:1001"

# 3. Generate configuration
sudo bash provision.sh

# 4. Start FreeSWITCH
sudo systemctl start freeswitch
```

## Environment Variables Overview

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `FS_DOMAIN` | SIP domain | `sip.example.com` |
| `EXTERNAL_SIP_IP` | External IP for SIP | `203.0.113.10` |
| `EXTERNAL_RTP_IP` | External IP for RTP | `203.0.113.10` |

### Users

```bash
# Authenticated users (password)
USERS="user1:password1:1001,user2:password2:1002"

# ACL users (IP-based, no password)
ACL_USERS="trunk1:192.168.1.100:2001"
```

### Gateways

```bash
# Format: name:host:port:username:password:register:transport
GATEWAYS="provider:sip.provider.com:5060:myuser:mypass:true:udp"
```

### Routing

```bash
# Outbound: pattern:gateway:prepend:strip
OUTBOUND_ROUTES="^00.*:provider1,^0.*:provider2:+49:0"
# Or simple:
DEFAULT_GATEWAY="provider1"

# Inbound: DID:extension
INBOUND_ROUTES="+49301234567:1001,+49301234568:1002,*:1000"
# Or simple:
DEFAULT_EXTENSION="1000"
```

See [.env.example](.env.example) for complete reference.

## Configuration Examples

### Example 1: Simple Office PBX

3 users, 1 provider, basic routing:

```bash
FS_DOMAIN=office.local
EXTERNAL_SIP_IP=203.0.113.50
EXTERNAL_RTP_IP=203.0.113.50
USERS=alice:pass123:1001,bob:pass456:1002,carol:pass789:1003
GATEWAYS=voip_provider:sip.provider.com:5060:account123:secret:true:udp
DEFAULT_GATEWAY=voip_provider
INBOUND_ROUTES=*:1001
```

### Example 2: Multi-Provider Routing

Route calls based on destination:

```bash
FS_DOMAIN=pbx.company.com
EXTERNAL_SIP_IP=203.0.113.100
EXTERNAL_RTP_IP=203.0.113.100
USERS=user1:pass1:1001,user2:pass2:1002
GATEWAYS=provider_de:sip.de.com:5060:user_de:pass_de:true:udp,provider_us:sip.us.com:5060:user_us:pass_us:true:udp
OUTBOUND_ROUTES=^\\+49.*:provider_de,^\\+1.*:provider_us
INBOUND_ROUTES=+4930111111:1001,+4930222222:1002
```

### Example 3: SIP Trunk (No Auth)

IP-based trunk without authentication:

```bash
FS_DOMAIN=trunk.example.com
EXTERNAL_SIP_IP=203.0.113.200
EXTERNAL_RTP_IP=203.0.113.200
ACL_USERS=trunk:198.51.100.50:9000
GATEWAYS=provider:sip.provider.net:5060:::false:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=9000
```

More examples in [DEPLOYMENT.md](DEPLOYMENT.md).

## Scripts Reference

### install.sh

Installs FreeSWITCH from official SignalWire repositories.

**Usage:**
```bash
sudo bash install.sh
```

**What it does:**
- Detects OS (Debian/Ubuntu)
- Adds SignalWire repository
- Installs FreeSWITCH packages
- Removes demo/example configurations
- Sets up minimal config structure
- Configures systemd service

**Requirements:**
- Debian 11/12 or Ubuntu 20.04/22.04
- Root access
- Internet connection

### provision.sh

Generates complete FreeSWITCH configuration from environment variables.

**Usage:**
```bash
# Set ENV variables first
export FS_DOMAIN="sip.example.com"
export EXTERNAL_SIP_IP="203.0.113.10"
# ... (see .env.example)

# Run provisioning
sudo bash provision.sh
```

**What it generates:**
- `vars.xml` - Global variables
- `sip_profiles/internal.xml` - Profile for authenticated users
- `sip_profiles/external.xml` - Profile for gateways and inbound
- `directory/default.xml` - User directory
- `directory/default/*.xml` - Individual user files
- `sip_profiles/external/*.xml` - Gateway configurations
- `dialplan/default/00_outbound.xml` - Outbound routing
- `dialplan/public/00_inbound.xml` - Inbound routing
- `autoload_configs/acl.conf.xml` - ACL configuration (if ACL_USERS defined)

**Live reload:**
Automatically runs `reloadxml` and `sofia rescan` if FreeSWITCH is running.

## Docker Usage

### Build Image

```bash
docker build -f Dockerfile.production -t freeswitch-prod:latest .
```

### Run Container

```bash
docker run -d \
  --name freeswitch \
  --network host \
  --env-file .env \
  --restart unless-stopped \
  freeswitch-prod:latest
```

### Management Commands

```bash
# Check status
docker exec freeswitch fs_cli -x "sofia status"

# View registrations
docker exec freeswitch fs_cli -x "show registrations"

# View gateway status
docker exec freeswitch fs_cli -x "sofia status gateway"

# View channels
docker exec freeswitch fs_cli -x "show channels"

# Interactive CLI
docker exec -it freeswitch fs_cli

# View logs
docker logs -f freeswitch

# Restart (will re-provision)
docker restart freeswitch
```

## Verification

After deployment, verify the setup:

```bash
# 1. Check FreeSWITCH is running
fs_cli -x "status"

# 2. Check SIP profiles
fs_cli -x "sofia status"
# Should show: internal (5060), external (5080)

# 3. Check gateway registration
fs_cli -x "sofia status gateway"
# Should show: REGED for gateways with register=true

# 4. Check user registrations (if users have registered)
fs_cli -x "show registrations"

# 5. Test call routing (optional)
fs_cli -x "originate user/1001 &echo"
```

## Troubleshooting

### Gateway Not Registering

```bash
# Check gateway status
fs_cli -x "sofia status gateway gateway_name"

# Enable SIP trace
fs_cli -x "sofia profile external siptrace on"

# Check credentials and firewall
```

### Users Can't Register

```bash
# Check internal profile
fs_cli -x "sofia status profile internal"

# Check user exists
ls /etc/freeswitch/directory/default/

# Enable auth debugging
fs_cli -x "console loglevel debug"
```

### No Audio

```bash
# Verify RTP settings
echo $EXTERNAL_RTP_IP

# Check firewall allows RTP ports
# Default: 16384-32768/udp

# Check NAT settings in vars.xml
cat /etc/freeswitch/vars.xml | grep external
```

### Configuration Not Applied

```bash
# Re-run provisioning
/usr/local/bin/provision.sh

# Force reload
fs_cli -x "reloadxml"
fs_cli -x "sofia profile internal restart reloadxml"
fs_cli -x "sofia profile external restart reloadxml"
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete troubleshooting guide.

## Production Checklist

Before going to production:

- [ ] Set strong passwords in `USERS`
- [ ] Configure correct `EXTERNAL_SIP_IP` and `EXTERNAL_RTP_IP`
- [ ] Firewall allows required ports (5060, 5080, 16384-32768)
- [ ] Gateway credentials are correct
- [ ] Test inbound calls (check `INBOUND_ROUTES`)
- [ ] Test outbound calls (check `OUTBOUND_ROUTES` or `DEFAULT_GATEWAY`)
- [ ] Test audio quality
- [ ] Configure monitoring/alerts
- [ ] Set up backups (volume: `/var/backups/freeswitch`)
- [ ] Review security settings (ACLs, fail2ban)
- [ ] Document your configuration

## Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide with all scenarios
- **[.env.example](.env.example)** - Environment variables reference
- **[docker-compose.production.yml](docker-compose.production.yml)** - Docker Compose setup

## Architecture

### SIP Profiles

**Internal Profile (port 5060):**
- For authenticated SIP users
- Requires username/password
- Context: `default` (outbound calls)
- NAT-aware with `EXTERNAL_SIP_IP` and `EXTERNAL_RTP_IP`

**External Profile (port 5080):**
- For SIP gateways/trunks
- No authentication required (provider authenticates to FreeSWITCH)
- Context: `public` (inbound calls)
- Includes gateway definitions

### Call Flow

**Outbound (User → Gateway):**
1. User registers to internal profile
2. User dials number
3. Number matched against `OUTBOUND_ROUTES` patterns
4. Call routed to gateway via external profile
5. Gateway forwards to provider

**Inbound (Gateway → User):**
1. Provider sends call to external profile
2. DID matched against `INBOUND_ROUTES`
3. Call transferred to `default` context
4. Call routed to user extension

### Directory Structure

```
/etc/freeswitch/
├── vars.xml                          # Global variables
├── freeswitch.xml                    # Main config (pre-existing)
├── sip_profiles/
│   ├── internal.xml                  # Internal profile (users)
│   ├── external.xml                  # External profile (gateways)
│   └── external/
│       ├── gateway1.xml              # Gateway definitions
│       └── gateway2.xml
├── directory/
│   ├── default.xml                   # Domain config
│   └── default/
│       ├── user1.xml                 # User definitions
│       └── user2.xml
├── dialplan/
│   ├── default/
│   │   └── 00_outbound.xml           # Outbound routes
│   └── public/
│       └── 00_inbound.xml            # Inbound routes
└── autoload_configs/
    ├── acl.conf.xml                  # ACL rules (if ACL_USERS)
    ├── modules.conf.xml              # Loaded modules
    └── switch.conf.xml               # Core settings
```

## Security

### Best Practices

1. **Strong Passwords**: Use complex passwords for SIP users
2. **IP Whitelisting**: Use `ACL_USERS` for trusted endpoints
3. **Firewall**: Restrict access to SIP ports
4. **Monitoring**: Monitor authentication failures
5. **Updates**: Keep FreeSWITCH updated
6. **Fail2ban**: Implement rate limiting

### Fail2ban Configuration

Example filter for `/etc/fail2ban/filter.d/freeswitch.conf`:

```ini
[Definition]
failregex = \[WARNING\] sofia_reg\.c:\d+ SIP auth challenge \(REGISTER\) on sofia profile \'[^']+\' for \[.*@.*\] from ip <HOST>
            \[WARNING\] sofia_reg\.c:\d+ SIP auth failure \(REGISTER\) on sofia profile \'[^']+\' for \[.*@.*\] from ip <HOST>
ignoreregex =
```

Jail config in `/etc/fail2ban/jail.local`:

```ini
[freeswitch]
enabled = true
port = 5060,5080
protocol = udp
filter = freeswitch
logpath = /var/log/freeswitch/freeswitch.log
maxretry = 5
bantime = 3600
```

## Support

For issues, questions, or contributions:

1. Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed documentation
2. Review troubleshooting section above
3. Open an issue on GitHub
4. FreeSWITCH community: https://freeswitch.org/support/

## License

This solution is provided as-is for production deployment of FreeSWITCH.

---

**Made for DevOps/VoIP Engineers** who need reliable, automated FreeSWITCH deployments.
