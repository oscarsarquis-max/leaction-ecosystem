#Requires -Version 5.1
<#
.SYNOPSIS
  Starts Mock de Sistemas de Credito on 127.0.0.1:8096 when the port is free.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
function Test-Listen([int]$Port) {
  return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}
if (-not $env:CREDIT_MOCK_CREDENTIAL -or $env:CREDIT_MOCK_CREDENTIAL.Length -lt 16) {
  throw "CREDIT_MOCK_CREDENTIAL must contain at least 16 characters. Secrets are not printed."
}
if (Test-Listen 8096) {
  Write-Output "port 8096 already in use — reusing credit mock"
} else {
  $env:PORT = '8096'
  Start-Process -FilePath 'node.exe' -ArgumentList @('server.js') -WorkingDirectory $root -WindowStyle Hidden
  Write-Output "started credit-provider-mock on 127.0.0.1:8096"
}
Write-Output "Supported shell: Windows PowerShell 5.1+"
