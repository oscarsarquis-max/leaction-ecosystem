# Proves that mock, Spider local-demo and SegSense BFF are the expected processes.
# Does not print secret values. Does not kill processes.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_load-mvp-secrets.ps1')
. (Join-Path $PSScriptRoot '_mvp-preflight.ps1')
Invoke-MvpPreflight
