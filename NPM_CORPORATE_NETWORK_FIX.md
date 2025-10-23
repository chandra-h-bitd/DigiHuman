# 🏢 NPM Install Stuck on Company Laptop - Solutions

## 🔍 Problem Identified

**Symptom:** `npm install` hangs/stuck  
**Cause:** Company firewall/proxy blocking npm registry  
**Test Result:** `npm ping` - No PONG response ❌

## ✅ Solutions (Try in Order)

### Solution 1: Configure Corporate Proxy ⭐ (Most Common)

Ask your IT department for proxy settings, then configure npm:

```bash
# Get proxy details from IT (example):
# HTTP Proxy: http://proxy.company.com:8080
# HTTPS Proxy: http://proxy.company.com:8080
# Username: your-username
# Password: your-password

# Set npm proxy (without authentication)
npm config set proxy http://proxy.company.com:8080
npm config set https-proxy http://proxy.company.com:8080

# Set npm proxy (with authentication)
npm config set proxy http://username:password@proxy.company.com:8080
npm config set https-proxy http://username:password@proxy.company.com:8080

# Verify
npm config get proxy
npm config get https-proxy

# Test
npm ping
```

**How to find your company proxy:**
```bash
# Windows - Check Internet Options
# 1. Open Control Panel → Internet Options → Connections → LAN Settings
# 2. Look for "Proxy server" address and port

# OR check environment variables
echo $env:HTTP_PROXY
echo $env:HTTPS_PROXY

# OR via PowerShell
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' | Select-Object ProxyServer, ProxyEnable
```

### Solution 2: Disable SSL Verification (If Corporate SSL Inspection)

```bash
# ⚠️ Only use this in corporate environment with IT approval
npm config set strict-ssl false

# Test
npm ping

# Try install
npm install
```

**Note:** This is needed when your company uses SSL inspection/MITM certificates.

### Solution 3: Use Company npm Registry (If Available)

```bash
# Ask IT if company has internal npm mirror/registry
# Example: Artifactory, Nexus, Verdaccio

# Set registry
npm config set registry http://npm.company.com/repository/npm-public/

# Test
npm ping

# Try install
npm install
```

### Solution 4: Offline Installation (No Network Needed) ⭐

If you can't access npm registry at all, use offline installation:

#### Option A: Download on Personal Laptop, Transfer to Company Laptop

**On your personal laptop (home network):**

```bash
# 1. Go to frontend directory
cd C:\CodeSpace\NTT\frontend

# 2. Install and create offline package
npm install

# 3. Create tarball of node_modules
tar -czf node_modules.tar.gz node_modules

# OR use 7-Zip on Windows:
# Right-click node_modules → 7-Zip → Add to archive → node_modules.zip

# 4. Transfer this file to company laptop via USB/email/cloud
```

**On company laptop:**

```bash
# 1. Copy node_modules.tar.gz to frontend directory
cd C:\CodeSpace\NTT\frontend

# 2. Extract
tar -xzf node_modules.tar.gz

# OR use 7-Zip to extract .zip file

# 3. Done! Skip npm install
```

#### Option B: Use npm-bundle

**On personal laptop:**

```bash
cd C:\CodeSpace\NTT\frontend

# Create bundle
npm pack

# This creates a .tgz file with all dependencies
# Transfer to company laptop
```

### Solution 5: Request IT Whitelist

Ask your IT department to whitelist these domains:

```
registry.npmjs.org
*.npmjs.org
*.npm.taobao.org (if using mirror)
github.com (for git dependencies)
raw.githubusercontent.com
```

### Solution 6: Use Mobile Hotspot (Temporary)

```bash
# 1. Connect laptop to your phone's mobile hotspot
# 2. Bypass corporate network completely
# 3. Run npm install
# 4. Switch back to company WiFi
```

## 🧪 Diagnostic Commands

Run these to identify the exact issue:

```bash
# 1. Test npm connectivity
npm ping

# 2. Check current npm config
npm config list

# 3. Test with verbose logging
npm install --verbose

# 4. Check if proxy is blocking
curl https://registry.npmjs.org/

# 5. Check DNS resolution
nslookup registry.npmjs.org

# 6. Test direct connection
ping registry.npmjs.org
```

## 📋 Quick Fix Checklist

```bash
# Run these commands on company laptop:

# 1. Check proxy settings
npm config get proxy
npm config get https-proxy

# 2. If null, ask IT for proxy and set it
npm config set proxy http://PROXY:PORT
npm config set https-proxy http://PROXY:PORT

# 3. If SSL issues
npm config set strict-ssl false

# 4. Test connection
npm ping

# 5. Clear cache and retry
npm cache clean --force
npm install
```

## 🎯 Recommended Solution for You

**Best approach:**

1. **Try this first** (works in most corporate networks):
   ```bash
   # Get proxy from Windows settings
   Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
   
   # Set npm proxy (replace with your actual proxy)
   npm config set proxy http://proxy.company.com:8080
   npm config set https-proxy http://proxy.company.com:8080
   
   # Disable SSL if needed
   npm config set strict-ssl false
   
   # Test
   npm ping
   
   # Install
   cd C:\CodeSpace\NTT\frontend
   npm install
   ```

2. **If still stuck** - Use offline method:
   - Install `node_modules` on personal laptop
   - Zip and transfer to company laptop
   - Extract and you're done!

## 🔒 Corporate Network Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Proxy blocking** | npm ping fails | Set proxy config |
| **SSL inspection** | Certificate errors | `strict-ssl false` |
| **Firewall** | Timeout on install | Whitelist domains |
| **Port blocking** | Cannot reach registry | Use company registry |
| **Bandwidth throttling** | Very slow downloads | Use offline method |

## ✅ Verification Steps

After applying fix:

```bash
# 1. Test connection
npm ping
# Should see: PONG

# 2. Try simple install
npm install lodash --verbose

# 3. If works, install full project
cd C:\CodeSpace\NTT\frontend
npm install

# 4. Run the app
npm start
```

## 📞 What to Ask Your IT Department

1. "What is the corporate HTTP/HTTPS proxy server and port?"
2. "Do I need authentication for the proxy?"
3. "Does the company have an internal npm registry/mirror?"
4. "Are there any domains I need to whitelist for npm?"
5. "Does the company use SSL inspection/MITM certificates?"

## 🚀 Quick Workaround (If Nothing Works)

**Use the already-installed `node_modules` from your personal laptop:**

Since frontend is already running on port 4200, it means `node_modules` exists. You can:

```bash
# 1. On personal laptop, zip the node_modules
cd C:\CodeSpace\NTT\frontend
# Create zip of node_modules folder

# 2. Transfer to company laptop via USB/cloud

# 3. Extract in same location

# 4. Done! No npm install needed
```

---

**Current Status:**
- ✅ Backend works on company laptop
- ❌ npm install stuck (network issue)
- ✅ npm ping fails (confirmed network block)

**Recommended Action:**
1. Find company proxy settings
2. Configure npm proxy
3. If still fails, use offline installation method

