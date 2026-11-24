$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
$image = "lojadepaes:prod-20261124d"
$tar = "C:\Temp\loja-prod-20261124d.tar"
Set-Location $root

$free = (Get-PSDrive C).Free
Write-Host ("disco C: livre " + [math]::Round($free / 1GB, 2) + " GB")
if ($free -lt 5GB) {
  throw ("disco C: com menos de 5 GB livres: " + [math]::Round($free / 1GB, 2) + " GB")
}

Write-Host "building image"
docker build -t $image .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }

Write-Host "B2B2R: sem migracao; retorno prod-20261124c"

docker save -o $tar $image
if ($LASTEXITCODE -ne 0) { throw "docker save failed; tar permanece em $tar" }

& "$root\scripts\p96-refresh-ssh.ps1" | Out-Null
$dir = (Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw).Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 -o TCPKeepAlive=yes $tar lojadepaes:/tmp/loja-prod-20261124d.tar
if ($LASTEXITCODE -ne 0) { throw "scp da imagem falhou; tar permanece em $tar" }
scp -F $cfg "$root\scripts\b2b2r-backup-and-deploy.sh" lojadepaes:/tmp/b2b2r-backup-and-deploy.sh
if ($LASTEXITCODE -ne 0) { throw "scp do deploy falhou; tar permanece em $tar" }
ssh -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 lojadepaes "sed -i 's/\r$//' /tmp/b2b2r-backup-and-deploy.sh && bash /tmp/b2b2r-backup-and-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "publicacao remota falhou; tar permanece em $tar" }

Remove-Item -Force $tar
Write-Host "tar local apagado"
Write-Host "publicado $image (retorno prod-20261124c)"
