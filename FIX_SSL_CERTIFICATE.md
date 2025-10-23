# ✅ Fix: Unable to Get Issuer Certificate Locally

## 🔍 Problem
```
Error: unable to get issuer certificate locally
```

**Cause:** Your company network uses SSL inspection (Man-in-the-Middle proxy) with their own certificate authority.

## ✅ Quick Fix (Run These Commands)

### Option 1: Disable SSL Verification (Easiest) ⭐

```bash
# Run on your company laptop:
npm config set strict-ssl false

# Verify
npm config get strict-ssl
# Should show: false

# Test connection
npm ping
# Should now show: PONG

# Try install
cd C:\CodeSpace\NTT\frontend
npm install
```

**This should fix it immediately!**

### Option 2: Set Proxy + Disable SSL

If Option 1 doesn't work completely, also set proxy:

```bash
# Get proxy from Windows (run this first)
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'

# Set npm proxy (replace with your actual proxy if shown above)
npm config set proxy http://YOUR_PROXY:PORT
npm config set https-proxy http://YOUR_PROXY:PORT

# Disable SSL
npm config set strict-ssl false

# Test
npm ping

# Install
cd C:\CodeSpace\NTT\frontend
npm install
```

### Option 3: Add Company Certificate (Proper Way)

Ask your IT department for the company's root CA certificate, then:

```bash
# Set the certificate file path
npm config set cafile "C:\path\to\company-ca-cert.crt"

# Keep SSL enabled
npm config set strict-ssl true
```

## 🧪 Test the Fix

```bash
# 1. Disable SSL
npm config set strict-ssl false

# 2. Test connection
npm ping
# Expected: PONG ✅

# 3. Test simple install
npm install lodash
# Expected: Success ✅

# 4. Install full project
cd C:\CodeSpace\NTT\frontend
npm install --verbose
# Expected: Downloads packages ✅
```

## 📋 Complete Setup Commands for Company Laptop

**Copy and run these one by one:**

```bash
# 1. Disable SSL verification
npm config set strict-ssl false

# 2. Clear npm cache
npm cache clean --force

# 3. Test connection
npm ping

# 4. Go to frontend directory
cd C:\CodeSpace\NTT\frontend

# 5. Remove old node_modules if exists
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue

# 6. Install dependencies
npm install

# 7. Start frontend
npm start
```

## ⚠️ Security Note

**Why this happens:**
- Your company intercepts HTTPS traffic for security monitoring
- They use their own certificates (not recognized by npm/Node.js)
- This causes SSL verification to fail

**Is `strict-ssl false` safe?**
- ✅ Safe in corporate environment (you're on company network)
- ✅ Only affects npm downloads
- ⚠️ Don't use on public/untrusted networks
- ⚠️ Only use for internal company network

## 🔄 Alternative: Use Node.js Environment Variable

Instead of npm config, you can use environment variable:

```bash
# Windows PowerShell
$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"
npm install

# OR set permanently
[System.Environment]::SetEnvironmentVariable('NODE_TLS_REJECT_UNAUTHORIZED', '0', 'User')
```

## ✅ Verification

After running the fix:

```bash
npm config list
```

Should show:
```
strict-ssl = false  ✅
```

Then:
```bash
npm ping
```

Should show:
```
PONG  ✅
```

## 🎯 Summary

**Your exact issue:**
- ❌ `unable to get issuer certificate locally`
- ✅ Fix: `npm config set strict-ssl false`

**Run this now:**
```bash
npm config set strict-ssl false
cd C:\CodeSpace\NTT\frontend
npm install
```

**That's it!** This should work immediately. 🚀

