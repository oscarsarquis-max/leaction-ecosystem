$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
Set-Location $root
Write-Host "building image"
docker build -t lojadepaes:prod-20261021b .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
docker save -o C:\Temp\loja-prod-20261021b.tar lojadepaes:prod-20261021b
& "$root\scripts\p96-refresh-ssh.ps1"
$dir = Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw
$dir = $dir.Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg C:\Temp\loja-prod-20261021b.tar lojadepaes:/tmp/loja-prod-20261021b.tar
scp -F $cfg "$root\scripts\p101-backup-and-deploy.sh" lojadepaes:/tmp/p101-backup-and-deploy.sh
scp -F $cfg "$root\scripts\p101-read.py" lojadepaes:/tmp/p101-read.py
ssh -F $cfg lojadepaes "sed -i 's/\r$//' /tmp/p101-backup-and-deploy.sh /tmp/p101-read.py && bash /tmp/p101-backup-and-deploy.sh && cid=`$(sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml ps -q api) && sudo docker cp /tmp/p101-read.py `$cid:/tmp/p101-read.py && sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T -w /app/backend api python /tmp/p101-read.py"
