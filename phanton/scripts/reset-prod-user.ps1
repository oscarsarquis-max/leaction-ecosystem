#Requires -Version 5.1
<#
.SYNOPSIS
  Upsert de usuário no Phanton de produção (EC2) sem redeploy.

.EXAMPLE
  cd C:\Projetos\phanton\scripts
  .\reset-prod-user.ps1 -Username andrea -Password 'SuaSenhaForte' -Role restricted_tester

.EXAMPLE
  .\reset-prod-user.ps1 -Username andrea -Role restricted_tester
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Username,

    [Parameter(Mandatory = $false)]
    [string]$Password = "",

    [ValidateSet("admin", "restricted_tester")]
    [string]$Role = "restricted_tester",

    [string]$Ec2Host = "3.150.84.169",
    [string]$KeyPath = "C:\Projetos\MAtivas\chaves\mativas-key.pem",
    [string]$Container = "phanton_prod_backend"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KeyPath)) {
    throw "Chave SSH nao encontrada: $KeyPath"
}

if ([string]::IsNullOrWhiteSpace($Password)) {
    $secure = Read-Host "Password (>=8)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $Password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

if ($Password.Length -lt 8) {
    throw "Password deve ter pelo menos 8 caracteres"
}

$localScript = Join-Path (Split-Path $PSScriptRoot -Parent) "backend\scripts\upsert_user.py"
if (-not (Test-Path $localScript)) {
    throw "Script local ausente: $localScript"
}

$uname = $Username.Trim().ToLowerInvariant()
$passwordB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Password))
$remotePy = "/tmp/phanton_upsert_user.py"
$remoteSh = "/tmp/phanton_upsert_user.sh"
$remoteB64 = "/tmp/phanton_upsert_pass.b64"

# Here-string literal: evita que o PowerShell expanda $(...) e zere a senha.
$bash = @'
#!/bin/bash
set -euo pipefail
CONTAINER='__CONTAINER__'
UNAME='__UNAME__'
ROLE='__ROLE__'
PASS_B64_FILE='__PASS_B64_FILE__'
REMOTE_PY='__REMOTE_PY__'
export PHANTON_UPSERT_PASSWORD="$(base64 -d < "$PASS_B64_FILE")"
if [ "${#PHANTON_UPSERT_PASSWORD}" -lt 8 ]; then
  echo "ERRO: senha decodificada invalida (<8)" >&2
  exit 1
fi
sudo docker cp "$REMOTE_PY" "${CONTAINER}:/tmp/upsert_user.py"
sudo docker exec \
  -e PYTHONPATH=/app:/app/backend \
  -e "PHANTON_UPSERT_PASSWORD=${PHANTON_UPSERT_PASSWORD}" \
  "${CONTAINER}" \
  python /tmp/upsert_user.py --username "${UNAME}" --role "${ROLE}" --password-from-env
sudo docker exec "${CONTAINER}" rm -f /tmp/upsert_user.py
rm -f "$REMOTE_PY" "$PASS_B64_FILE" __REMOTE_SH__
unset PHANTON_UPSERT_PASSWORD
'@

$bash = $bash.
    Replace('__CONTAINER__', $Container).
    Replace('__UNAME__', $uname).
    Replace('__ROLE__', $Role).
    Replace('__PASS_B64_FILE__', $remoteB64).
    Replace('__REMOTE_PY__', $remotePy).
    Replace('__REMOTE_SH__', $remoteSh)

$bashPath = Join-Path $env:TEMP "phanton-upsert-remote.sh"
$b64Path = Join-Path $env:TEMP "phanton-upsert-pass.b64"
[IO.File]::WriteAllText($bashPath, ($bash -replace "`r`n", "`n"), (New-Object System.Text.UTF8Encoding $false))
[IO.File]::WriteAllText($b64Path, $passwordB64, (New-Object System.Text.UTF8Encoding $false))

Write-Host "==> Enviando scripts para EC2..." -ForegroundColor Cyan
scp -i $KeyPath -o StrictHostKeyChecking=no $localScript "ubuntu@${Ec2Host}:$remotePy"
if ($LASTEXITCODE -ne 0) { throw "scp upsert_user.py falhou" }
scp -i $KeyPath -o StrictHostKeyChecking=no $b64Path "ubuntu@${Ec2Host}:$remoteB64"
if ($LASTEXITCODE -ne 0) { throw "scp password b64 falhou" }
scp -i $KeyPath -o StrictHostKeyChecking=no $bashPath "ubuntu@${Ec2Host}:$remoteSh"
if ($LASTEXITCODE -ne 0) { throw "scp shell remoto falhou" }

Write-Host "==> Executando upsert ($uname / $Role)..." -ForegroundColor Cyan
ssh -i $KeyPath -o StrictHostKeyChecking=no "ubuntu@${Ec2Host}" "bash $remoteSh"
if ($LASTEXITCODE -ne 0) { throw "upsert remoto falhou (exit $LASTEXITCODE)" }

Remove-Item -Force $bashPath, $b64Path -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "OK. Teste login em https://phanton.ia.br (user=$uname role=$Role)." -ForegroundColor Green
Write-Host "A senha nao foi impressa neste output." -ForegroundColor DarkGray
