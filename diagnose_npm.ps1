# NPM Corporate Network Diagnostic Script
# Run this on your company laptop to identify the issue

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "NPM Corporate Network Diagnostics" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Check Windows Proxy Settings
Write-Host "[1] Checking Windows Proxy Settings..." -ForegroundColor Yellow
$proxySettings = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
Write-Host "  Proxy Enabled: $($proxySettings.ProxyEnable)" -ForegroundColor White
Write-Host "  Proxy Server: $($proxySettings.ProxyServer)" -ForegroundColor White

# 2. Check Environment Variables
Write-Host "`n[2] Checking Environment Variables..." -ForegroundColor Yellow
Write-Host "  HTTP_PROXY: $env:HTTP_PROXY" -ForegroundColor White
Write-Host "  HTTPS_PROXY: $env:HTTPS_PROXY" -ForegroundColor White
Write-Host "  NO_PROXY: $env:NO_PROXY" -ForegroundColor White

# 3. Check NPM Config
Write-Host "`n[3] Checking NPM Configuration..." -ForegroundColor Yellow
Write-Host "  Registry: $(npm config get registry)" -ForegroundColor White
Write-Host "  Proxy: $(npm config get proxy)" -ForegroundColor White
Write-Host "  HTTPS Proxy: $(npm config get https-proxy)" -ForegroundColor White
Write-Host "  Strict SSL: $(npm config get strict-ssl)" -ForegroundColor White

# 4. Test DNS Resolution
Write-Host "`n[4] Testing DNS Resolution..." -ForegroundColor Yellow
try {
    $dns = Resolve-DnsName registry.npmjs.org -ErrorAction Stop
    Write-Host "  [OK] Can resolve registry.npmjs.org" -ForegroundColor Green
    Write-Host "  IP: $($dns[0].IPAddress)" -ForegroundColor White
} catch {
    Write-Host "  [ERROR] Cannot resolve registry.npmjs.org" -ForegroundColor Red
}

# 5. Test Network Connectivity
Write-Host "`n[5] Testing Network Connectivity..." -ForegroundColor Yellow
try {
    $ping = Test-Connection registry.npmjs.org -Count 2 -ErrorAction Stop
    Write-Host "  [OK] Can ping registry.npmjs.org" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Cannot ping (may be blocked by firewall)" -ForegroundColor Yellow
}

# 6. Test HTTPS Connection
Write-Host "`n[6] Testing HTTPS Connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://registry.npmjs.org/" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    Write-Host "  [OK] Can connect to npm registry via HTTPS" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Cannot connect to npm registry" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 7. Test NPM Ping
Write-Host "`n[7] Testing NPM Ping..." -ForegroundColor Yellow
try {
    $npmPing = npm ping 2>&1
    if ($npmPing -match "PONG") {
        Write-Host "  [OK] NPM ping successful" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] NPM ping failed" -ForegroundColor Red
    }
} catch {
    Write-Host "  [ERROR] NPM ping failed" -ForegroundColor Red
}

# Summary and Recommendations
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RECOMMENDATIONS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($proxySettings.ProxyEnable -eq 1 -and $proxySettings.ProxyServer) {
    Write-Host "[ACTION REQUIRED] Configure NPM to use company proxy:" -ForegroundColor Yellow
    Write-Host "  npm config set proxy http://$($proxySettings.ProxyServer)" -ForegroundColor White
    Write-Host "  npm config set https-proxy http://$($proxySettings.ProxyServer)" -ForegroundColor White
    Write-Host "`n[OPTION] If authentication needed:" -ForegroundColor Yellow
    Write-Host "  npm config set proxy http://USERNAME:PASSWORD@$($proxySettings.ProxyServer)" -ForegroundColor White
} else {
    Write-Host "[INFO] No Windows proxy detected" -ForegroundColor White
}

Write-Host "`n[OPTION] If SSL certificate issues:" -ForegroundColor Yellow
Write-Host "  npm config set strict-ssl false" -ForegroundColor White

Write-Host "`n[OPTION] Use offline installation:" -ForegroundColor Yellow
Write-Host "  1. Install on personal laptop" -ForegroundColor White
Write-Host "  2. Zip node_modules folder" -ForegroundColor White
Write-Host "  3. Transfer to company laptop" -ForegroundColor White
Write-Host "  4. Extract and use" -ForegroundColor White

Write-Host "`n========================================`n" -ForegroundColor Cyan

