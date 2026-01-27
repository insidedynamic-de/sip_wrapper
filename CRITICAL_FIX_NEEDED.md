# CRITICAL: Your Deployment is Failing!

## ✅ NEW: Auto IP Detection Added!

**Good news!** The docker-compose files now **automatically detect** your server's public IP if you leave the placeholder values.

**You can now:**
1. Leave `EXTERNAL_SIP_IP=your-server-ip` in Coolify
2. Container will auto-detect your public IP on startup
3. Or manually set your real IP for production use

See [AUTO_IP_DETECTION.md](AUTO_IP_DETECTION.md) for details.

---

## Problem Identified

Your container was **stuck in a restart loop** at STEP 3/8. I found **TWO critical issues**:

### Issue 1: PLACEHOLDER IP ADDRESSES (NOW FIXED) ✅

Your environment variables were set to **placeholder strings**:

```
EXTERNAL_SIP_IP: your-server-ip
EXTERNAL_RTP_IP: your-server-ip
```

**NOW:** Container will automatically detect your public IP!

**Or manually set** your real IP for production.

### Issue 2: Container Hangs at GPG Download

The container is hanging when downloading the SignalWire GPG key and then restarting. The debug version now has retry logic to handle this.

---

## IMMEDIATE FIX REQUIRED

### Step 1: Get Your Server IP

**In Coolify server terminal, run:**
```bash
curl ifconfig.me
```

This will show your **public IP address**, something like: `203.0.113.10`

### Step 2: Update Environment Variables in Coolify

Go to your Coolify service → **Environment Variables** and change:

**BEFORE (WRONG):**
```bash
EXTERNAL_SIP_IP=your-server-ip
EXTERNAL_RTP_IP=your-server-ip
```

**AFTER (CORRECT):**
```bash
EXTERNAL_SIP_IP=203.0.113.10  # Use YOUR actual IP from step 1
EXTERNAL_RTP_IP=203.0.113.10  # Same IP
```

### Step 3: Redeploy with Updated Debug Version

The updated `docker-compose.coolify-debug.yml` now:
- ✅ Detects placeholder values and shows clear error
- ✅ Has retry logic for GPG key download (3 attempts with timeout)
- ✅ Shows more detailed progress at each step

**Redeploy in Coolify** and check the logs.

---

## What You'll See After Fix

### If IP is Still Placeholder:

```
ERROR: EXTERNAL_SIP_IP and EXTERNAL_RTP_IP are still set to placeholder values!
Current values:
  EXTERNAL_SIP_IP: your-server-ip
  EXTERNAL_RTP_IP: your-server-ip

Please change these to your ACTUAL server public IP address.
Find your IP with: curl ifconfig.me
```

### If GPG Download Works:

```
[STEP 3/8] Adding SignalWire FreeSWITCH repository...
Downloading GPG key from SignalWire...
Attempt 1 of 3...
✓ GPG key downloaded successfully
Adding repository for bookworm...
✓ Repository added for bookworm

[STEP 4/8] Installing FreeSWITCH packages...
```

---

## Still Having Issues?

### If STEP 3 Still Fails After 3 Attempts:

This means:
1. **Network issue** - Coolify server can't reach files.freeswitch.org
2. **Firewall blocking** outbound HTTPS to SignalWire
3. **DNS issue** - can't resolve files.freeswitch.org

**Debug in Coolify server terminal:**
```bash
# Test network connectivity
curl -I https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc

# Should show: HTTP/2 200
```

### If It Passes STEP 3 But Fails Later:

Check which step it fails at:
- **STEP 4**: FreeSWITCH package installation issue
- **STEP 5**: Config cleanup issue
- **STEP 6**: Can't download provision.sh from GitHub
- **STEP 7**: provision.sh script failed (likely due to invalid ENV values)
- **STEP 8**: FreeSWITCH won't start

---

## Complete Environment Variables Template

**Copy this into Coolify UI** (replace with YOUR values):

```bash
# REQUIRED - MUST BE REAL VALUES
FS_DOMAIN=apps.linkify.cloud
EXTERNAL_SIP_IP=203.0.113.10           # ← YOUR actual server IP here!
EXTERNAL_RTP_IP=203.0.113.10           # ← YOUR actual server IP here!
USERS=alice:SecretPass123:1001
GATEWAYS=provider:fpbx.de:5060:777z9uovpu:4UMtPyXw8Qss:true:udp

# ROUTING
DEFAULT_GATEWAY=provider
DEFAULT_EXTENSION=1001

# OPTIONAL (defaults are usually fine)
INTERNAL_SIP_PORT=5060
EXTERNAL_SIP_PORT=5080
RTP_START_PORT=16384
RTP_END_PORT=32768
CODEC_PREFS=PCMU,PCMA,G729,opus
SIP_DEBUG=0
SIP_TRACE=no
```

---

## Quick Checklist

Before redeploying, verify:

- [ ] `EXTERNAL_SIP_IP` is set to **actual server public IP** (not "your-server-ip")
- [ ] `EXTERNAL_RTP_IP` is set to **actual server public IP** (not "your-server-ip")
- [ ] `FS_DOMAIN` is set to your domain
- [ ] `USERS` has real usernames and passwords
- [ ] `GATEWAYS` has real provider credentials
- [ ] Coolify server can access internet (for downloading packages)
- [ ] Using `docker-compose.coolify-debug.yml` for detailed logs

---

## After Successful Deployment

Once you see:

```
[STEP 8/8] Starting FreeSWITCH...
Command: /usr/bin/freeswitch -nonat -nf -nc

==========================================
If you see this message, FreeSWITCH is starting...
Check logs for FreeSWITCH startup messages
==========================================
```

**Then** FreeSWITCH logs will start appearing. Look for:
```
2026-01-26 23:XX:XX [INFO] mod_sofia.c:6259 Starting SOFIA Profile internal
2026-01-26 23:XX:XX [INFO] mod_sofia.c:6259 Starting SOFIA Profile external
```

Container should stay running (no more restarts).

---

## Need More Help?

If it still fails after fixing the IP addresses:

1. **Copy the FULL logs** from Coolify (from the very start)
2. **Note which STEP fails** (e.g., "Fails at STEP 7/8")
3. **Copy the error message**
4. Provide this info for further troubleshooting

---

**TL;DR:**
1. Get your server IP: `curl ifconfig.me`
2. Set `EXTERNAL_SIP_IP` and `EXTERNAL_RTP_IP` to that **real IP**
3. Deploy `docker-compose.coolify-debug.yml`
4. Watch logs - should now pass STEP 3 and continue
