# Build production web, serve with preview proxy, run Playwright MVP gate.
$ErrorActionPreference = "Stop"
$WebRoot = Split-Path -Parent $PSScriptRoot
Set-Location $WebRoot

Write-Host "== npm ci (if needed) =="
if (-not (Test-Path "node_modules\@playwright\test")) {
  Set-Location (Split-Path -Parent $WebRoot)
  npm ci
  Set-Location $WebRoot
}

Write-Host "== install chromium =="
npx playwright install chromium

Write-Host "== production build =="
npm run build:gate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== start preview :4178 =="
$preview = Start-Process -PassThru -NoNewWindow -FilePath "npx" -ArgumentList @(
  "vite", "preview", "--host", "127.0.0.1", "--port", "4178"
)
Start-Sleep -Seconds 3
try {
  $ok = $false
  for ($i = 0; $i -lt 30; $i++) {
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:4178/" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -lt 500) { $ok = $true; break }
    } catch { Start-Sleep -Seconds 1 }
  }
  if (-not $ok) { throw "preview did not become ready" }

  Write-Host "== playwright e2e =="
  $env:QMIND_E2E_BASE_URL = "http://127.0.0.1:4178"
  npx playwright test
  $code = $LASTEXITCODE
} finally {
  if ($preview -and -not $preview.HasExited) {
    Stop-Process -Id $preview.Id -Force -ErrorAction SilentlyContinue
  }
}
exit $code
