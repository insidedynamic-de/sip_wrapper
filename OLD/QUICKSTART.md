# FreeSWITCH Production - Quick Start Guide

## 🚀 Coolify Deployment (Easiest)

**Самый простой способ** - развертывание через Coolify:

### Шаг 1: Создать сервис в Coolify

1. Coolify → Add New Service → **Docker Compose**
2. Git Repository: `https://github.com/your-org/freeswitch-production`
3. Docker Compose file: `docker-compose.coolify.yml`

### Шаг 2: Настроить ENV в Coolify UI

В разделе **Environment Variables** добавьте:

```bash
FS_DOMAIN=sip.example.com
EXTERNAL_SIP_IP=your-server-ip      # Публичный IP вашего Coolify сервера
EXTERNAL_RTP_IP=your-server-ip      # Тот же IP
USERS=alice:SecretPass123:1001,bob:SecretPass456:1002
GATEWAYS=provider:sip.provider.com:5060:username:password:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

### Шаг 3: Deploy

Нажмите **Deploy** и дождитесь завершения!

### Проверка

В Coolify Terminal:
```bash
fs_cli -x "sofia status"
```

**📖 Детальное руководство:** [COOLIFY.md](COOLIFY.md)

---

## 30-Second Setup (Docker Local)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit these required variables
nano .env
# Set: FS_DOMAIN, EXTERNAL_SIP_IP, EXTERNAL_RTP_IP, USERS, GATEWAYS

# 3. Start
docker-compose -f docker-compose.production.yml up -d

# 4. Verify
docker-compose exec freeswitch fs_cli -x "sofia status"
```

## Minimal Configuration

Edit `.env` with these minimal settings:

```bash
# Domain
FS_DOMAIN=sip.example.com

# Public IP (replace with your server's public IP)
EXTERNAL_SIP_IP=203.0.113.10
EXTERNAL_RTP_IP=203.0.113.10

# Add 2 users
USERS=alice:SecretPass123:1001,bob:SecretPass456:1002

# Add 1 provider
GATEWAYS=myprovider:sip.provider.com:5060:myusername:mypassword:true:udp

# Route all outbound via provider
DEFAULT_GATEWAY=myprovider

# Route all inbound to alice
INBOUND_ROUTES=*:1001
```

## Verify Setup

```bash
# Check profiles running
docker exec freeswitch fs_cli -x "sofia status"
# Should show: internal (UP), external (UP)

# Check gateway registered
docker exec freeswitch fs_cli -x "sofia status gateway"
# Should show: myprovider - REGED

# Check users can register
# Configure SIP client: sip:alice@203.0.113.10:5060, password: SecretPass123
```

## Test Calls

**Register SIP client:**
- Server: Your server IP (e.g., 203.0.113.10)
- Port: 5060
- Username: alice
- Password: SecretPass123
- Domain: sip.example.com (or leave blank)

**Make test call:**
- Dial any number → should route via gateway to provider
- Provider sends call to your DID → should route to alice (1001)

## Common Commands

```bash
# View logs
docker-compose logs -f freeswitch

# Interactive CLI
docker exec -it freeswitch fs_cli

# Restart (re-provisions)
docker-compose restart freeswitch

# Check active calls
docker exec freeswitch fs_cli -x "show channels"

# Show registrations
docker exec freeswitch fs_cli -x "show registrations"
```

## Troubleshooting

**Gateway not registering?**
```bash
# Check gateway details
docker exec freeswitch fs_cli -x "sofia status gateway myprovider"

# Enable SIP trace
docker exec freeswitch fs_cli -x "sofia global siptrace on"
```

**Users can't register?**
```bash
# Check internal profile
docker exec freeswitch fs_cli -x "sofia status profile internal"

# Check firewall allows UDP 5060
```

**No audio?**
```bash
# Check external IPs set correctly
docker exec freeswitch cat /etc/freeswitch/vars.xml | grep external

# Check firewall allows UDP 16384-32768
```

## Next Steps

- **For Coolify users:** Read [COOLIFY.md](COOLIFY.md) for detailed Coolify deployment guide
- Read [DEPLOYMENT.md](DEPLOYMENT.md) for advanced configuration
- Read [README.production.md](README.production.md) for complete reference
- Add more users, gateways, and routing rules as needed

## Production Checklist

- [ ] Change default passwords
- [ ] Set correct EXTERNAL_SIP_IP and EXTERNAL_RTP_IP
- [ ] Configure firewall (5060, 5080, 16384-32768 UDP)
- [ ] Test inbound calls
- [ ] Test outbound calls
- [ ] Test audio quality
- [ ] Set up monitoring
- [ ] Configure backups
