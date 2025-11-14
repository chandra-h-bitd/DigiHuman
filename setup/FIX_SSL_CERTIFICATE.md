# Fix: SSL Certificate Issues

## Problem

**Error:** `unable to get issuer certificate locally`

**Cause:** Company network uses SSL inspection with their own certificate authority.

## Quick Fix

```bash
# Disable SSL verification
npm config set strict-ssl false

# Test connection
npm ping

# Install dependencies
cd frontend
npm install
```

## With Proxy

If the above doesn't work, configure proxy:

```bash
# Get proxy settings (Windows PowerShell)
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'

# Configure npm
npm config set proxy http://YOUR_PROXY:PORT
npm config set https-proxy http://YOUR_PROXY:PORT
npm config set strict-ssl false

# Test
npm ping
```

## Security Note

- Safe in corporate environment (company network)
- Only affects npm downloads
- Don't use on public/untrusted networks

