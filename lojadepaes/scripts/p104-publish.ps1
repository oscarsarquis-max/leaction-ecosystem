$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
Set-Location $root
Write-Host "building image"
docker build -t lojadepaes:prod-20261027g .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
docker run --rm --entrypoint sh lojadepaes:prod-20261027g -c "grep -q 'us.anthropic.claude-sonnet-4-6' /app/backend/app/domain/gigio/settings.py && grep -q empty_query /app/backend/app/domain/gigio/tools.py && grep -q 'Consulta livre' /app/backend/app/domain/gigio/consult.py && grep -q deepen_offer /app/frontend/dist/assets/*.js && grep -q 'Ciclo dos pedidos' /app/frontend/dist/assets/*.js && grep -q 'Pagamentos dos ativos' /app/frontend/dist/assets/*.js && grep -q admin-cycle-track /app/frontend/dist/assets/*.css && grep -q admin-recipe-actions /app/frontend/dist/assets/*.css"
if ($LASTEXITCODE -ne 0) { throw "image is missing the Gigio model or the 103A layout" }
docker save -o C:\Temp\loja-prod-20261027g.tar lojadepaes:prod-20261027g
if ($LASTEXITCODE -ne 0) { throw "docker save failed" }
& "$root\scripts\p96-refresh-ssh.ps1" | Out-Null
$dir = (Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw).Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 -o TCPKeepAlive=yes C:\Temp\loja-prod-20261027g.tar lojadepaes:/tmp/loja-prod-20261027g.tar
if ($LASTEXITCODE -ne 0) { throw "scp da imagem falhou" }
scp -F $cfg "$root\scripts\p104-backup-and-deploy.sh" lojadepaes:/tmp/p104-backup-and-deploy.sh
if ($LASTEXITCODE -ne 0) { throw "scp do deploy falhou" }
ssh -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 lojadepaes "sed -i 's/\r$//' /tmp/p104-backup-and-deploy.sh && bash /tmp/p104-backup-and-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "publicação remota falhou" }
