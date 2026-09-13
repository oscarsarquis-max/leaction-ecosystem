# Operational tests for ACL and preflight identity. Does not print secret values.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
. (Join-Path $here '_mvp-secrets-acl.ps1')
. (Join-Path $here '_mvp-preflight.ps1')

$failed = $false
function Assert-True($Condition, $Message) {
  if (-not $Condition) {
    Write-Output "FAIL $Message"
    $script:failed = $true
  } else {
    Write-Output "ok $Message"
  }
}

$tmp = Join-Path $env:TEMP ("mvp-acl-" + [guid]::NewGuid().ToString() + '.env')
Set-Content -LiteralPath $tmp -Value 'DUMMY=1' -Encoding ascii
try {
  Set-MvpRestrictedAcl -Path $tmp
  Assert-True (Test-MvpRestrictedAcl -Path $tmp) 'restricted ACL accepted'
  & icacls $tmp /grant:r '*S-1-5-32-545:R' | Out-Null
  Assert-True (-not (Test-MvpRestrictedAcl -Path $tmp)) 'wide ACL rejected'
} finally {
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

$wrongJs = Join-Path $env:TEMP ("mvp-wrong-mock-" + [guid]::NewGuid().ToString() + '.js')
@'
const http = require('http');
http.createServer((q, s) => {
  s.writeHead(200, { 'Content-Type': 'application/json' });
  s.end(JSON.stringify({ status: 'ok' }));
}).listen(18995, '127.0.0.1');
'@ | Set-Content -LiteralPath $wrongJs -Encoding ascii
$proc = Start-Process -FilePath 'node' -ArgumentList $wrongJs -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 1
$env:MVP_MOCK_BASE_URL = 'http://127.0.0.1:18995'
try {
  Test-MvpMockIdentity
  Assert-True $false 'preflight accepted a process without Test Double identity'
} catch {
  Assert-True $true 'preflight rejected a process without Test Double identity'
} finally {
  if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
  Remove-Item -LiteralPath $wrongJs -Force -ErrorAction SilentlyContinue
  Remove-Item Env:MVP_MOCK_BASE_URL -ErrorAction SilentlyContinue
}

if ($failed) { throw 'test-mvp-ops failed' }
Write-Output 'test-mvp-ops=ok'
