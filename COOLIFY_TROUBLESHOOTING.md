# Coolify Deployment Troubleshooting Guide

## Current Issue: Container Restart Loop

If your FreeSWITCH container keeps restarting, this guide will help you diagnose and fix the problem.

---

## Quick Fix: Try These Updated Files

### 1. Updated docker-compose.coolify-debian.yml (Recommended)

The main deployment file has been updated with:
- **Environment validation** - checks required ENV variables before installation
- **Better error messages** - shows exactly where deployment fails
- **Improved health check** - more lenient during startup
- **Longer startup period** - 180 seconds for installation and provisioning

**Deploy this file in Coolify** with your environment variables set.

### 2. Debug Version: docker-compose.coolify-debug.yml (For Troubleshooting)

If the standard version still fails, use this debug version:
- **8-step process** with clear progress markers
- **Verbose logging** - prints every command executed
- **ENV variable display** - shows what's configured (passwords hidden)
- **File verification** - confirms generated configuration files
- **5-minute startup period** - plenty of time to read logs

**How to use:**
1. In Coolify, change Docker Compose file to: `docker-compose.coolify-debug.yml`
2. Deploy
3. Check logs - you'll see `[STEP X/8]` progress
4. Identify which step fails
5. Report the step number and error message

---

## Common Issues and Solutions

### Issue 1: "Missing required environment variables"

**Error in logs:**
```
ERROR: Missing required environment variables: FS_DOMAIN EXTERNAL_SIP_IP
```

**Solution:**
Set these **REQUIRED** variables in Coolify UI:
```bash
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=your-server-public-ip
EXTERNAL_RTP_IP=your-server-public-ip
USERS=alice:SecretPass:1001
GATEWAYS=provider:sip.provider.com:5060:user:pass:true:udp
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001
```

Get your server IP:
```bash
curl ifconfig.me
```

### Issue 2: "Provision script failed"

**Error in logs:**
```
ERROR: Provision script failed with exit code 1
```

**Possible causes:**
1. Invalid format in USERS or GATEWAYS variables
2. Network issue downloading provision.sh from GitHub
3. Missing required ENV variables for routing (DEFAULT_GATEWAY or OUTBOUND_ROUTES)

**Solution:**
- **Check USERS format:** `username:password:extension` (comma-separated)
  ```bash
  USERS=alice:pass123:1001,bob:pass456:1002
  ```

- **Check GATEWAYS format:** `name:host:port:user:pass:register:transport`
  ```bash
  GATEWAYS=provider:sip.provider.com:5060:username:password:true:udp
  ```

- **Set routing:** Choose ONE of these:
  ```bash
  # Option A: Simple routing (all calls go through one gateway)
  DEFAULT_GATEWAY=provider
  DEFAULT_EXTENSION=1001

  # Option B: Pattern-based routing
  OUTBOUND_ROUTES=^00.*:provider1,^0.*:provider2
  INBOUND_ROUTES=+49301234567:1001,*:1000
  ```

### Issue 3: "FreeSWITCH binary not found"

**Error in logs:**
```
ERROR: FreeSWITCH binary not found at /usr/bin/freeswitch
```

**Possible causes:**
1. FreeSWITCH package installation failed
2. Network issues accessing SignalWire repository
3. Debian version incompatibility

**Solution:**
- Check Coolify logs for errors during `[STEP 4/8] Installing FreeSWITCH packages...`
- Ensure your Coolify server has internet access
- Try redeploying (temporary network glitch)

### Issue 4: "FreeSWITCH starts but immediately exits"

**Symptoms:**
- Logs show "Starting FreeSWITCH..."
- Container exits immediately after
- No error message

**Possible causes:**
1. Port conflict (5060/5080 already in use)
2. Insufficient permissions
3. Configuration file syntax error

**Solution:**

1. **Check port conflicts:**
   - In Coolify server terminal:
     ```bash
     netstat -tuln | grep -E '5060|5080'
     ```
   - If ports are in use, stop conflicting services or change ports:
     ```bash
     INTERNAL_SIP_PORT=5062
     EXTERNAL_SIP_PORT=5082
     ```

2. **Check FreeSWITCH logs** (if container stays up long enough):
   ```bash
   docker exec freeswitch cat /var/log/freeswitch/freeswitch.log
   ```

3. **Validate generated config:**
   - Use debug version to see what files were created
   - Check for XML syntax errors in generated configs

### Issue 5: Container restarts every 30 seconds

**Symptoms:**
- Container starts, runs for 30s, restarts
- Health check failing

**Solution:**
The updated version now uses a simpler health check:
```yaml
healthcheck:
  test: ["CMD", "bash", "-c", "pgrep -x freeswitch > /dev/null || exit 1"]
  start_period: 180s  # Gives 3 minutes before health checks start
```

If still failing:
1. Check if FreeSWITCH process is actually running:
   ```bash
   docker exec freeswitch ps aux | grep freeswitch
   ```

2. Temporarily disable health check (for testing only):
   - Comment out the entire healthcheck section
   - Redeploy
   - Check if container stays running

---

## Step-by-Step Debugging Process

### Step 1: Verify Environment Variables

In Coolify UI, ensure ALL required variables are set:
```bash
# REQUIRED - NO DEFAULTS
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=203.0.113.10
EXTERNAL_RTP_IP=203.0.113.10
USERS=alice:SecretPass:1001
GATEWAYS=provider:sip.provider.com:5060:user:pass:true:udp

# ROUTING - CHOOSE ONE APPROACH
DEFAULT_GATEWAY=provider          # Simple: all calls through this gateway
DEFAULT_EXTENSION=1001            # Simple: all inbound to this extension
# OR
OUTBOUND_ROUTES=^00.*:provider1   # Advanced: pattern-based routing
INBOUND_ROUTES=+49301234567:1001  # Advanced: DID-based routing
```

### Step 2: Deploy Debug Version

1. Change Docker Compose file to: `docker-compose.coolify-debug.yml`
2. Save and deploy
3. Watch logs in real-time

### Step 3: Identify the Failing Step

Logs will show:
```
[STEP 1/8] Validating environment variables... ✓
[STEP 2/8] Installing system dependencies... ✓
[STEP 3/8] Adding SignalWire FreeSWITCH repository... ✓
[STEP 4/8] Installing FreeSWITCH packages... ✓
[STEP 5/8] Cleaning default configuration... ✓
[STEP 6/8] Downloading provision script... ✓
[STEP 7/8] Running provision script... ERROR
```

The step without a ✓ checkmark is where it fails.

### Step 4: Get Help

If you're stuck, provide:
1. **Which step fails** (e.g., "STEP 7/8 Running provision script")
2. **Error message** from logs
3. **Your ENV variables** (format only, hide passwords):
   ```
   FS_DOMAIN: SET
   EXTERNAL_SIP_IP: SET
   USERS: alice:***:1001,bob:***:1002
   GATEWAYS: provider:***:5060:***:***:true:udp
   DEFAULT_GATEWAY: SET
   ```

---

## Files in This Repository

### Deployment Files (Choose ONE)

1. **[docker-compose.coolify-debian.yml](docker-compose.coolify-debian.yml)** (RECOMMENDED)
   - Production-ready
   - Better error handling
   - Use this for actual deployment

2. **[docker-compose.coolify-debug.yml](docker-compose.coolify-debug.yml)** (DEBUGGING)
   - Verbose logging
   - Step-by-step progress
   - Use this to troubleshoot

3. **[docker-compose.coolify-simple.yml](docker-compose.coolify-simple.yml)** (DEPRECATED)
   - Alpine-based - **DO NOT USE**
   - Incompatible with provision.sh

4. **[docker-compose.coolify-prebuilt.yml](docker-compose.coolify-prebuilt.yml)** (ALTERNATIVE)
   - Installs FreeSWITCH on startup
   - Slower but more flexible

### Documentation Files

- **[COOLIFY_QUICKSTART.md](COOLIFY_QUICKSTART.md)** - Quick deployment guide
- **[COOLIFY_TROUBLESHOOTING.md](COOLIFY_TROUBLESHOOTING.md)** - This file
- **[.env.example](.env.example)** - All ENV variables with examples

---

## Successful Deployment Checklist

Once deployed successfully, verify:

```bash
# 1. Container is running
docker ps | grep freeswitch

# 2. FreeSWITCH process is running
docker exec freeswitch ps aux | grep freeswitch

# 3. SIP profiles are UP
docker exec freeswitch fs_cli -x "sofia status"
# Should show:
# Profile internal: UP (port 5060)
# Profile external: UP (port 5080)

# 4. Gateways are registered
docker exec freeswitch fs_cli -x "sofia status gateway"
# Should show: REGED (if gateway requires registration)

# 5. Users can register
# Test with SIP client:
# Server: EXTERNAL_SIP_IP
# Port: 5060
# Username: alice
# Password: SecretPass
```

---

## Still Having Issues?

### Option 1: Manual Installation (Fallback)

If Docker deployment continues to fail, you can install FreeSWITCH directly on the Coolify server:

```bash
# SSH into Coolify server
ssh user@your-server

# Download and run install script
curl -fsSL https://raw.githubusercontent.com/insidedynamic-de/sip_wrapper/main/install.sh | sudo bash

# Set environment variables
export FS_DOMAIN="apps.linkify.cloud"
export EXTERNAL_SIP_IP="203.0.113.10"
export EXTERNAL_RTP_IP="203.0.113.10"
export USERS="alice:SecretPass:1001"
export GATEWAYS="provider:sip.provider.com:5060:user:pass:true:udp"
export DEFAULT_GATEWAY="provider"
export DEFAULT_EXTENSION="1001"

# Run provision script
curl -fsSL https://raw.githubusercontent.com/insidedynamic-de/sip_wrapper/main/provision.sh | sudo bash

# Start FreeSWITCH
systemctl start freeswitch
```

### Option 2: Report an Issue

If none of the solutions work, report the issue with:

1. **Coolify logs** (full output from debug version)
2. **Step where it fails** ([STEP X/8])
3. **ENV variables format** (hide passwords)
4. **Server details:**
   - Coolify version
   - OS version (from Coolify)
   - Available memory

---

## Summary of Recent Fixes

### What Was Fixed in docker-compose.coolify-debian.yml:

1. ✅ **Added ENV validation** - catches missing variables before installation
2. ✅ **Better error messages** - each step shows clear success/failure
3. ✅ **Improved health check** - uses `pgrep` instead of `fs_cli` for reliability
4. ✅ **Longer startup period** - 180s instead of 120s for provisioning
5. ✅ **Explicit error handling** - shows exactly which command failed

### What's New in docker-compose.coolify-debug.yml:

1. ✅ **8-step progress tracking** - see exactly how far deployment gets
2. ✅ **ENV variable display** - confirm what's configured
3. ✅ **File verification** - lists generated configuration files
4. ✅ **Verbose command output** - `set -x` shows every executed command
5. ✅ **Extended startup period** - 300s (5 minutes) for thorough debugging

---

**Next Step:** Deploy the updated [docker-compose.coolify-debian.yml](docker-compose.coolify-debian.yml) in Coolify and check the logs!
