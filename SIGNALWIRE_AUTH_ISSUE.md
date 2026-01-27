# SignalWire Authentication Issue - Quick Fix

## 🔴 Problem

SignalWire has changed their access policy:
- **Repository** `files.freeswitch.org` now requires authentication (returns 401 Unauthorized)
- **Docker Hub** image `signalwire/freeswitch` is not accessible (requires login or doesn't exist)

## ✅ Solution

Use alternative deployment methods that don't require SignalWire authentication.

---

## 🚀 Quick Fix (2 minutes)

### Option 1: Pre-built Image (RECOMMENDED)

**File:** `docker-compose.coolify-prebuilt.yml`
**Time:** 2-3 minutes
**Source:** GitHub Container Registry (no auth needed)

#### In Coolify UI:

1. **Docker Compose file:** `docker-compose.coolify-prebuilt.yml`
2. **Environment variables:** (keep the same)
   ```
   FS_DOMAIN=apps.linkify.cloud
   EXTERNAL_SIP_IP=46.224.205.100
   EXTERNAL_RTP_IP=46.224.205.100
   USERS=alice:SecretPass:1001
   GATEWAYS=provider:fpbx.de:5060:user:pass:true:udp
   DEFAULT_GATEWAY=provider
   DEFAULT_EXTENSION=1001
   ```
3. **Click Deploy**
4. **Check logs** - should complete in 2-3 minutes

#### Expected Log:

```
FreeSWITCH Coolify - Pre-built Image
[STEP 1/4] Validating environment variables... ✓
[STEP 2/4] Installing dependencies... ✓
[STEP 3/4] Preparing configuration... ✓
[STEP 4/4] Running provision script... ✓
Starting FreeSWITCH...
```

✅ **FreeSWITCH is running!**

---

## 🛠️ Alternative: Build from Source

**File:** `docker-compose.coolify-source.yml`
**Time:** 15-20 minutes (first build only)
**Source:** GitHub (official FreeSWITCH repository)

### When to use:

- Pre-built image doesn't work
- You need full independence from Docker registries
- You want the latest version from GitHub

### In Coolify UI:

1. **Docker Compose file:** `docker-compose.coolify-source.yml`
2. **Environment variables:** (same as above)
3. **Click Deploy**
4. **WAIT** ~15-20 minutes for compilation
5. **Check logs** - after compilation, FreeSWITCH will start

---

## 📋 Files to Commit

Before deploying in Coolify, commit the new files:

```bash
git add docker-compose.coolify-prebuilt.yml
git add docker-compose.coolify-source.yml
git add GPG_KEY_FIX.md
git add SIGNALWIRE_AUTH_ISSUE.md
git commit -m "Add alternative deployment without SignalWire auth"
git push origin main
```

---

## ⚠️ What NOT to Use

**DON'T USE:**
- `docker-compose.coolify-debug.yml` - requires SignalWire auth (will fail)
- `docker-compose.coolify-debian.yml` - requires SignalWire auth (will fail)

These versions try to install from SignalWire repository which now requires authentication.

---

## 🎯 Comparison

| Method | Time | Dependencies | Reliability |
|--------|------|--------------|-------------|
| **Pre-built Image** | ⚡ 2-3 min | GitHub CR | ✅✅✅ High |
| **Build from Source** | 🐢 15-20 min | GitHub | ✅✅✅ High |
| Debug/Debian | 🚫 Fails | SignalWire | ❌ Won't work |

---

## ❓ FAQ

### Q: Why is SignalWire repository not accessible?

**A:** SignalWire changed their access policy and now requires authentication (registration + token) to access FreeSWITCH packages.

### Q: Which version should I use?

**A:** Use **Pre-built Image** (`docker-compose.coolify-prebuilt.yml`) - it's fast and doesn't require SignalWire access.

### Q: What if GitHub Container Registry is also blocked?

**A:** Use **Build from Source** (`docker-compose.coolify-source.yml`) - it compiles FreeSWITCH from GitHub source code.

### Q: Will my provision.sh still work?

**A:** YES! Both versions run your provision.sh script to generate FreeSWITCH configuration from environment variables.

### Q: Can I get SignalWire access token?

**A:** Yes, but it's not necessary. The alternative methods work without any authentication.

---

## 📚 Full Documentation

See [GPG_KEY_FIX.md](GPG_KEY_FIX.md) for detailed troubleshooting and all available options.

---

## ✅ Summary

1. **Commit** new files to Git
2. **Change** Docker Compose file in Coolify to `docker-compose.coolify-prebuilt.yml`
3. **Deploy** and wait 2-3 minutes
4. **Done!** FreeSWITCH is running

No SignalWire authentication needed! 🎉
