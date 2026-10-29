$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
Set-Location $root
Write-Host "building image"
docker build -t lojadepaes:prod-20261009d .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
docker save -o C:\Temp\loja-prod-20261009d.tar lojadepaes:prod-20261009d
& "$root\scripts\p96-refresh-ssh.ps1"
$dir = Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw
$dir = $dir.Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg C:\Temp\loja-prod-20261009d.tar lojadepaes:/tmp/loja-prod-20261009d.tar
scp -F $cfg "$root\scripts\p97-backup-and-deploy.sh" lojadepaes:/tmp/p97-backup-and-deploy.sh
ssh -F $cfg lojadepaes "sed -i 's/\r$//' /tmp/p97-backup-and-deploy.sh && bash /tmp/p97-backup-and-deploy.sh"
