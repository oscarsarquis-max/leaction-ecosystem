$ErrorActionPreference = 'Stop'
$secretFile = Join-Path $PSScriptRoot '.local-secrets.env'
if (-not (Test-Path $secretFile)) {
  throw "missing $secretFile - run setup-local-secrets.ps1 first"
}
Get-Content $secretFile | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $parts = $_.Split('=', 2)
  if ($parts.Count -eq 2) {
    Set-Item -Path ("Env:" + $parts[0]) -Value $parts[1]
  }
}
