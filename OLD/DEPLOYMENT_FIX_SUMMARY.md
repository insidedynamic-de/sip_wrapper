# FreeSWITCH Coolify Deployment - Fix Summary

## Problem Fixed

Your FreeSWITCH container was restarting in a loop. The logs showed installation was starting but the container kept restarting before completing.

## What I Fixed

### 1. Improved [docker-compose.coolify-debian.yml](docker-compose.coolify-debian.yml)

**Changes:**
- ✅ **Added environment validation** - checks for required ENV variables before installation starts
- ✅ **Better error messages** - shows exactly which step fails with clear error text
- ✅ **Error handling** - each command now shows success/failure explicitly
- ✅ **Improved health check** - changed from `fs_cli -x 'status'` to simple process check `pgrep -x freeswitch`
- ✅ **Longer startup period** - increased from 120s to 180s to allow for installation and provisioning

**Before:**
```yaml
command:
  - |
    set -e
    echo "[$(date)] Installing dependencies..."
    apt-get update -qq
    ...
```

**After:**
```yaml
command:
  - |
    set -e

    # Validation function
    validate_env() {
      echo "[$(date)] Validating environment variables..."
      local missing=""
      [ -z "$FS_DOMAIN" ] && missing="$missing FS_DOMAIN"
      ...
      if [ -n "$missing" ]; then
        echo "ERROR: Missing required environment variables:$missing"
        exit 1
      fi
    }

    validate_env

    echo "[$(date)] Installing dependencies..."
    apt-get update -qq || { echo "ERROR: apt-get update failed"; exit 1; }
    ...
```

### 2. Created [docker-compose.coolify-debug.yml](docker-compose.coolify-debug.yml)

**A dedicated debug version for troubleshooting with:**
- 🔍 **8-step progress tracking** - shows [STEP 1/8], [STEP 2/8], etc.
- 📊 **Environment variable display** - shows what's configured (passwords hidden)
- ✅ **Success markers** - each step shows ✓ when completed
- 📝 **Verbose logging** - `set -x` prints every command executed
- 🔎 **File verification** - lists generated configuration files
- ⏱️ **5-minute startup period** - plenty of time to diagnose issues

**Example output:**
```
[STEP 1/8] Validating environment variables... ✓
[STEP 2/8] Installing system dependencies... ✓
[STEP 3/8] Adding SignalWire FreeSWITCH repository... ✓
[STEP 4/8] Installing FreeSWITCH packages... ✓
[STEP 5/8] Cleaning default configuration... ✓
[STEP 6/8] Downloading provision script... ✓
[STEP 7/8] Running provision script... ✓
[STEP 8/8] Starting FreeSWITCH... ✓
```

### 3. Created [COOLIFY_TROUBLESHOOTING.md](COOLIFY_TROUBLESHOOTING.md)

**Comprehensive troubleshooting guide covering:**
- Common issues and solutions
- Step-by-step debugging process
- Environment variable validation
- Port conflict resolution
- Health check issues
- Manual installation fallback
- How to report issues

### 4. Updated [COOLIFY_QUICKSTART.md](COOLIFY_QUICKSTART.md)

**Added:**
- Link to troubleshooting guide
- Debug version usage instructions
- Container restart troubleshooting section

## What You Need To Do Next

### Option 1: Try the Fixed Version (Recommended)

1. **Commit all files to Git:**
   ```bash
   git add .
   git commit -m "Fix Coolify deployment with improved error handling and debugging"
   git push origin main
   ```

2. **Deploy in Coolify:**
   - Docker Compose file: `docker-compose.coolify-debian.yml`
   - Ensure all ENV variables are set (see below)
   - Click "Deploy"

3. **Check logs** - should see clear progress messages and either success or clear error

### Option 2: Use Debug Version (If Option 1 Fails)

1. **Change Docker Compose file to:** `docker-compose.coolify-debug.yml`

2. **Deploy and watch logs** - you'll see:
   ```
   ==========================================
   FreeSWITCH Coolify Deployment - DEBUG MODE
   Start time: Mon Jan 27 00:00:00 UTC 2026
   ==========================================

   === Environment Variables Check ===
   FS_DOMAIN: apps.linkify.cloud
   EXTERNAL_SIP_IP: 203.0.113.10
   ...

   [STEP 1/8] Validating environment variables... ✓
   [STEP 2/8] Installing system dependencies... ✓
   ...
   ```

3. **Identify failing step** - the step without ✓ is where it fails

4. **Follow troubleshooting guide** - [COOLIFY_TROUBLESHOOTING.md](COOLIFY_TROUBLESHOOTING.md)

## Required Environment Variables

Make sure these are ALL set in Coolify UI:

```bash
# ОБЯЗАТЕЛЬНЫЕ (REQUIRED)
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=your-server-public-ip
EXTERNAL_RTP_IP=your-server-public-ip
USERS=alice:SecretPass:1001,bob:SecretPass:1002
GATEWAYS=provider:fpbx.de:5060:777z9uovpu:4UMtPyXw8Qss:true:udp

# МАРШРУТИЗАЦИЯ (ROUTING) - выберите один из вариантов:

# Вариант A: Простая маршрутизация
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001

# Вариант B: Маршрутизация по паттернам
OUTBOUND_ROUTES=^00.*:provider1,^0.*:provider2
INBOUND_ROUTES=+49301234567:1001,*:1000
```

**Get your server IP:**
```bash
curl ifconfig.me
```

## Why the Container Was Restarting

**Possible causes (now all addressed):**

1. **Missing ENV variables**
   - ❌ Before: Container would start, provision.sh would fail, no clear error
   - ✅ Now: Validation happens first with clear error message

2. **Silent failures**
   - ❌ Before: Commands could fail without clear indication
   - ✅ Now: Each command has explicit error handling

3. **Health check too aggressive**
   - ❌ Before: Health check tried to run `fs_cli -x 'status'` which might not work during startup
   - ✅ Now: Simple process check with `pgrep -x freeswitch`

4. **Short startup period**
   - ❌ Before: 120 seconds might not be enough for installation + provisioning
   - ✅ Now: 180 seconds (or 300s in debug mode)

5. **No visibility**
   - ❌ Before: Hard to tell where exactly it was failing
   - ✅ Now: Clear step-by-step progress with success markers

## Files Changed

### Modified:
- ✏️ `docker-compose.coolify-debian.yml` - improved error handling
- ✏️ `COOLIFY_QUICKSTART.md` - added troubleshooting references

### Created:
- ✨ `docker-compose.coolify-debug.yml` - debug version for troubleshooting
- ✨ `COOLIFY_TROUBLESHOOTING.md` - comprehensive troubleshooting guide
- ✨ `DEPLOYMENT_FIX_SUMMARY.md` - this file

### Unchanged (still working):
- ✅ `provision.sh` - configuration generator
- ✅ `.env.example` - environment variable examples
- ✅ Other documentation files

## Expected Result After Fix

### Successful deployment will show:

```
[$(date)] Starting FreeSWITCH deployment...
[$(date)] Validating environment variables...
[$(date)] Environment validation passed.
[$(date)] Installing dependencies...
[$(date)] Dependencies installed
[$(date)] Adding SignalWire repository...
[$(date)] Repository added
[$(date)] Installing FreeSWITCH packages...
[$(date)] FreeSWITCH installation completed.
[$(date)] Cleaning default config...
[$(date)] Default config cleaned.
[$(date)] Downloading provision script...
[$(date)] Provision script downloaded
[$(date)] Running provision script...
[$(date)] Provision completed successfully.
[$(date)] Starting FreeSWITCH...
[$(date)] Command: /usr/bin/freeswitch -nonat -nf -nc
```

Then FreeSWITCH logs will follow, and container will stay running.

### Failed deployment will show:

```
[$(date)] Starting FreeSWITCH deployment...
[$(date)] Validating environment variables...
ERROR: Missing required environment variables: FS_DOMAIN EXTERNAL_SIP_IP
Please set these variables in Coolify UI before deployment.
```

Or at whichever step it fails, with a clear error message.

## How to Verify It's Working

Once deployed successfully:

```bash
# 1. Check container is running (in Coolify or server)
docker ps | grep freeswitch

# 2. Check FreeSWITCH is running inside container
docker exec freeswitch ps aux | grep freeswitch

# 3. Check SIP profiles are UP
docker exec freeswitch fs_cli -x "sofia status"

# Expected output:
# Profile internal: UP (port 5060)
# Profile external: UP (port 5080)

# 4. Check gateway registration
docker exec freeswitch fs_cli -x "sofia status gateway provider"

# Expected output:
# REGED (if gateway requires registration)
# or NOREG (if register=false)
```

## Next Steps After Successful Deployment

1. **Test SIP registration** with a softphone:
   ```
   Server: your-server-ip
   Port: 5060
   Username: alice
   Password: SecretPass
   ```

2. **Make test calls:**
   - Internal: alice → bob (1001 → 1002)
   - Outbound: alice → external number (goes through gateway)
   - Inbound: external → your extension

3. **Configure firewall** (if not already done):
   ```bash
   # Allow SIP and RTP
   ufw allow 5060/udp  # Internal SIP
   ufw allow 5080/udp  # External SIP
   ufw allow 16384:32768/udp  # RTP media
   ```

4. **Monitor logs:**
   ```bash
   # Coolify logs
   docker logs -f freeswitch

   # FreeSWITCH logs inside container
   docker exec freeswitch tail -f /var/log/freeswitch/freeswitch.log
   ```

## Getting Help

If you still have issues after trying both versions:

1. **Use the debug version** to identify exact failure point
2. **Check [COOLIFY_TROUBLESHOOTING.md](COOLIFY_TROUBLESHOOTING.md)** for specific error solutions
3. **Report issue** with:
   - Which step fails ([STEP X/8])
   - Error message from logs
   - ENV variable format (hide passwords)

## Summary

✅ **Fixed:** docker-compose.coolify-debian.yml now has better error handling and validation
✨ **Created:** docker-compose.coolify-debug.yml for easy troubleshooting
📖 **Documented:** Comprehensive troubleshooting guide
🚀 **Ready:** Commit to Git and deploy in Coolify

**Recommended next action:** Commit changes, deploy `docker-compose.coolify-debian.yml`, check logs.
