<#
.SYNOPSIS
  Publica inove4us-school no EC2 (domínio canônico: school.inove4us.com.br).
#>
[CmdletBinding()]
param(
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu',
    [string]$RemotePath = '/var/www/inove4us-school',
    [string]$Domain = 'school.inove4us.com.br',
    [string]$DnsZone = 'inove4us.com.br',
    [int]$Port = 5012
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HubRoot = (Resolve-Path (Join-Path $ScriptDir '../..')).Path
$SchoolRoot = (Resolve-Path (Join-Path $HubRoot '../inove4us-school')).Path
$KeyFile = if ($env:ACTION_HUB_SSH_KEY) { $env:ACTION_HUB_SSH_KEY } else { Join-Path $HubRoot 'chaves/action_hub_keys.pem' }
if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

$ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
$scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')

function Invoke-Ssh([string]$Cmd) {
    & ssh @ssh $Cmd
    if ($LASTEXITCODE -ne 0) { throw "SSH falhou: $Cmd" }
}

Write-Host "==> DNS $Domain -> $ServerHost (zona $DnsZone)" -ForegroundColor Cyan
$zoneId = aws route53 list-hosted-zones-by-name --dns-name "$DnsZone." --query "HostedZones[0].Id" --output text
$zoneId = $zoneId -replace '/hostedzone/', ''
if (-not $zoneId) { throw "Hosted zone nao encontrada: $DnsZone" }
$change = @{
  Comment = "school public endpoint"
  Changes = @(@{
    Action = 'UPSERT'
    ResourceRecordSet = @{
      Name = "$Domain."
      Type = 'A'
      TTL = 60
      ResourceRecords = @(@{ Value = $ServerHost })
    }
  })
} | ConvertTo-Json -Depth 8 -Compress
$changeFile = Join-Path $env:TEMP 'school-dns.json'
[System.IO.File]::WriteAllText($changeFile, $change)
aws route53 change-resource-record-sets --hosted-zone-id $zoneId --change-batch "file://$changeFile" | Out-Null
Write-Host "DNS UPSERT ok"

Write-Host "==> Empacotando school (tar.gz)" -ForegroundColor Cyan
$tarPath = Join-Path $env:TEMP 'inove4us-school-deploy.tar.gz'
if (Test-Path $tarPath) { Remove-Item $tarPath -Force }
Push-Location $SchoolRoot
try {
    # exclui artefatos locais pesados
    tar -czf $tarPath `
        --exclude=node_modules --exclude=.venv --exclude=dist --exclude=__pycache__ `
        --exclude=.git --exclude=frontend/node_modules --exclude=backend/.venv `
        backend frontend infra VERSION 2>$null
    if (-not (Test-Path $tarPath)) { throw 'tar falhou' }
}
finally { Pop-Location }

Write-Host "==> Upload" -ForegroundColor Cyan
Invoke-Ssh "sudo mkdir -p $RemotePath && sudo chown -R ${User}:${User} $RemotePath"
& scp @scp $tarPath "${User}@${ServerHost}:/tmp/inove4us-school-deploy.tar.gz"
if ($LASTEXITCODE -ne 0) { throw 'scp tar falhou' }
Invoke-Ssh "sudo rm -rf $RemotePath/backend $RemotePath/frontend $RemotePath/infra $RemotePath/VERSION; sudo mkdir -p $RemotePath && sudo chown -R ${User}:${User} $RemotePath && tar -xzf /tmp/inove4us-school-deploy.tar.gz -C $RemotePath && rm -f /tmp/inove4us-school-deploy.tar.gz && test -f $RemotePath/backend/app.py"

& scp @scp (Join-Path $ScriptDir '_school-db-bootstrap.py') "${User}@${ServerHost}:/tmp/school-db-bootstrap.py"
& scp @scp (Join-Path $ScriptDir 'remote-school-install.sh') "${User}@${ServerHost}:/tmp/remote-school-install.sh"

Write-Host "==> Install remoto" -ForegroundColor Cyan
Invoke-Ssh "sed -i 's/\r$//' /tmp/remote-school-install.sh /tmp/school-db-bootstrap.py; chmod +x /tmp/remote-school-install.sh; REMOTE=$RemotePath DOMAIN=$Domain PORT=$Port bash /tmp/remote-school-install.sh"

Write-Host "`n==> School publico: https://$Domain" -ForegroundColor Green
