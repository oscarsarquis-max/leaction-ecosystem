# Deploy Phanton para a EC2 do MAtivas (build local + push ECR + merge compose/Caddy).
# Uso:
#   cd C:\Projetos\phanton
#   .\scripts\deploy-to-mativas-ec2.ps1
#
# Requer: Docker Desktop, AWS CLI, npm, chave MAtivas\chaves\mativas-key.pem

[CmdletBinding()]
param(
    [string]$Ec2Host = '3.150.84.169',
    [string]$KeyPath = 'C:\Projetos\MAtivas\chaves\mativas-key.pem',
    [string]$GeminiApiKey = '',
    [string]$JwtSecret = '',
    [string]$AdminPassword = '',
    [string]$AndreaPassword = '',
    [switch]$SeedUsers
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$Ecr = '253137917703.dkr.ecr.us-east-2.amazonaws.com'
$Region = 'us-east-2'
$AwsExtra = @('--no-verify-ssl')

if (-not (Test-Path $KeyPath)) { throw "Chave SSH não encontrada: $KeyPath" }

Write-Host '==> Frontend build (same-origin API)...' -ForegroundColor Cyan
Push-Location (Join-Path $Root 'frontend')
$env:VITE_API_BASE = ''
npm run build
if ($LASTEXITCODE -ne 0) { throw 'npm run build failed' }
Pop-Location

Write-Host '==> ECR login (local)...' -ForegroundColor Cyan
$loginPass = aws ecr get-login-password --region $Region @AwsExtra
if (-not $loginPass) { throw 'aws ecr get-login-password failed' }
$loginPass | docker login --username AWS --password-stdin $Ecr
if ($LASTEXITCODE -ne 0) { throw 'docker login ECR failed' }

Write-Host '==> Build + push backend image...' -ForegroundColor Cyan
Push-Location $Root
docker build --platform linux/amd64 -t phanton-backend:latest -f backend/Dockerfile .
if ($LASTEXITCODE -ne 0) { throw 'backend docker build failed' }
docker tag phanton-backend:latest "$Ecr/phanton-backend:latest"
docker push "$Ecr/phanton-backend:latest"
if ($LASTEXITCODE -ne 0) { throw 'backend docker push failed' }
Pop-Location

Write-Host '==> Build + push frontend image...' -ForegroundColor Cyan
Push-Location (Join-Path $Root 'frontend')
docker build --platform linux/amd64 -t phanton-frontend:latest -f Dockerfile.prod .
if ($LASTEXITCODE -ne 0) { throw 'frontend docker build failed' }
docker tag phanton-frontend:latest "$Ecr/phanton-frontend:latest"
docker push "$Ecr/phanton-frontend:latest"
if ($LASTEXITCODE -ne 0) { throw 'frontend docker push failed' }
Pop-Location

Write-Host '==> Secrets...' -ForegroundColor Cyan
if (-not $GeminiApiKey) {
    $envFile = Join-Path $Root 'backend\.env'
    if (Test-Path $envFile) {
        $line = Select-String -Path $envFile -Pattern '^GEMINI_API_KEY=(.+)$' | Select-Object -First 1
        if ($line) { $GeminiApiKey = $line.Matches[0].Groups[1].Value.Trim() }
    }
}

# Reutiliza secrets já publicados na EC2 — evita rotacionar senha/JWT a cada deploy
$remoteSecrets = Join-Path $env:TEMP 'phanton-prod-secrets-remote.env'
$hadRemoteSecrets = $false
try {
    scp -i $KeyPath -o StrictHostKeyChecking=no -o ConnectTimeout=8 `
        "ubuntu@${Ec2Host}:/home/ubuntu/phanton-prod-secrets.env" $remoteSecrets 2>$null
    if ((Test-Path $remoteSecrets) -and ((Get-Item $remoteSecrets).Length -gt 0)) {
        $hadRemoteSecrets = $true
        foreach ($line in Get-Content $remoteSecrets) {
            if ($line -match '^GEMINI_API_KEY=(.+)$' -and -not $GeminiApiKey) {
                $GeminiApiKey = $Matches[1].Trim()
            }
            elseif ($line -match '^PHANTON_JWT_SECRET=(.+)$' -and -not $JwtSecret) {
                $JwtSecret = $Matches[1].Trim()
            }
            elseif ($line -match '^PHANTON_ADMIN_PASSWORD=(.+)$' -and -not $AdminPassword) {
                $AdminPassword = $Matches[1].Trim()
            }
            elseif ($line -match '^PHANTON_ANDREA_PASSWORD=(.+)$' -and -not $AndreaPassword) {
                $AndreaPassword = $Matches[1].Trim()
            }
        }
        Write-Host '    reusando phanton-prod-secrets.env da EC2' -ForegroundColor DarkGray
    }
} catch {
    Write-Host '    sem secrets remotos (primeiro deploy?)' -ForegroundColor DarkGray
}

$seedUsersExplicit = $PSBoundParameters.ContainsKey('AdminPassword') -or `
    $PSBoundParameters.ContainsKey('AndreaPassword') -or `
    $SeedUsers

if (-not $JwtSecret) {
    $JwtSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
}
if (-not $AdminPassword) {
    $AdminPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 20 | ForEach-Object { [char]$_ })
}
if (-not $AndreaPassword) {
    $AndreaPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 20 | ForEach-Object { [char]$_ })
}
if (-not $GeminiApiKey) { throw 'GEMINI_API_KEY ausente (param ou backend\.env)' }

$secretsLocal = Join-Path $env:TEMP 'phanton-prod-secrets.env'
$secretsBody = @"
GEMINI_API_KEY=$GeminiApiKey
PHANTON_JWT_SECRET=$JwtSecret
PHANTON_ADMIN_PASSWORD=$AdminPassword
PHANTON_ANDREA_PASSWORD=$AndreaPassword
"@ -replace "`r`n", "`n"
[IO.File]::WriteAllText($secretsLocal, $secretsBody, (New-Object System.Text.UTF8Encoding $false))

Write-Host '==> SCP scripts/fragments para EC2...' -ForegroundColor Cyan
scp -i $KeyPath -o StrictHostKeyChecking=no $secretsLocal "ubuntu@${Ec2Host}:/home/ubuntu/phanton-prod-secrets.env"
scp -i $KeyPath -o StrictHostKeyChecking=no (Join-Path $PSScriptRoot 'deploy-prod-ec2.sh') "ubuntu@${Ec2Host}:/home/ubuntu/deploy-phanton-prod.sh"
scp -i $KeyPath -o StrictHostKeyChecking=no (Join-Path $PSScriptRoot 'docker-compose.phanton.fragment.yml') "ubuntu@${Ec2Host}:/home/ubuntu/docker-compose.phanton.fragment.yml"
scp -i $KeyPath -o StrictHostKeyChecking=no (Join-Path $PSScriptRoot 'Caddyfile.phanton.fragment') "ubuntu@${Ec2Host}:/home/ubuntu/Caddyfile.phanton.fragment"
scp -i $KeyPath -o StrictHostKeyChecking=no (Join-Path $PSScriptRoot 'merge-phanton-into-host.sh') "ubuntu@${Ec2Host}:/home/ubuntu/merge-phanton-into-host.sh"

Write-Host '==> Merge compose/Caddy + pull/up...' -ForegroundColor Cyan
ssh -i $KeyPath -o StrictHostKeyChecking=no "ubuntu@${Ec2Host}" "chmod +x /home/ubuntu/merge-phanton-into-host.sh /home/ubuntu/deploy-phanton-prod.sh; bash /home/ubuntu/merge-phanton-into-host.sh; bash /home/ubuntu/deploy-phanton-prod.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote merge/deploy failed' }

# Seed só no 1º deploy, ou se pediu -SeedUsers / passou senhas explicitamente
if (-not $hadRemoteSecrets -or $seedUsersExplicit) {
    Write-Host '==> Seed users (oscar admin + andrea restricted)...' -ForegroundColor Cyan
    ssh -i $KeyPath -o StrictHostKeyChecking=no "ubuntu@${Ec2Host}" "set -a; source /home/ubuntu/phanton-prod-secrets.env; set +a; sudo docker exec -e PYTHONPATH=/app:/app/backend -e PHANTON_ADMIN_PASSWORD=`"`$PHANTON_ADMIN_PASSWORD`" -e PHANTON_ANDREA_PASSWORD=`"`$PHANTON_ANDREA_PASSWORD`" phanton_prod_backend python /app/backend/scripts/seed_prod_users.py"
    if ($LASTEXITCODE -ne 0) { throw 'seed users failed' }
    Write-Host ''
    Write-Host "Deploy concluído. URL: https://phanton.ia.br" -ForegroundColor Green
    Write-Host "Senhas em $secretsLocal (não commit)." -ForegroundColor Yellow
    Write-Host "admin (oscar) password: $AdminPassword"
    Write-Host "andrea password: $AndreaPassword"
} else {
    Write-Host '==> Seed users: pulado (senhas existentes preservadas). Use -SeedUsers para forçar.' -ForegroundColor DarkGray
    Write-Host ''
    Write-Host "Deploy concluído. URL: https://phanton.ia.br" -ForegroundColor Green
    Write-Host "Senhas preservadas em /home/ubuntu/phanton-prod-secrets.env na EC2." -ForegroundColor Yellow
}
