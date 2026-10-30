$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
$image = "lojadepaes:prod-20261030a"
$previous = "lojadepaes:prod-20261029d"
$tar = "C:\Temp\loja-prod-20261030a.tar"
$marker = "Lentes da fila"
Set-Location $root

$free = (Get-PSDrive C).Free
Write-Host ("disco C: livre " + [math]::Round($free / 1GB, 2) + " GB")
if ($free -lt 5GB) {
  throw ("disco C: com menos de 5 GB livres: " + [math]::Round($free / 1GB, 2) + " GB")
}

Write-Host "building image"
docker build -t $image .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }

$bundle = docker run --rm --entrypoint sh $image -c "grep -R -l -F '$marker' /app/frontend/dist || true"
if ($LASTEXITCODE -ne 0) { throw "nao foi possivel ler o bundle do frontend" }
Write-Host $bundle
if ($bundle -notmatch "index-") {
  throw "bundle novo nao contem a fila"
}

$head = docker run --rm --entrypoint sh $image -c "cd /app/database && alembic heads"
if ($LASTEXITCODE -ne 0) { throw "nao foi possivel ler o alembic da imagem" }
Write-Host $head
if ($head -notmatch "d5e9f2a18b33") {
  throw "alembic head nao e d5e9f2a18b33"
}
Write-Host "sem migracao nova; backend desta imagem inclui a projecao das trilhas"

docker save -o $tar $image
if ($LASTEXITCODE -ne 0) { throw "docker save failed; tar permanece em $tar" }

& "$root\scripts\p96-refresh-ssh.ps1" | Out-Null
$dir = (Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw).Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 -o TCPKeepAlive=yes $tar lojadepaes:/tmp/loja-prod-20261030a.tar
if ($LASTEXITCODE -ne 0) { throw "scp da imagem falhou; tar permanece em $tar" }
scp -F $cfg "$root\scripts\p109-backup-and-deploy.sh" lojadepaes:/tmp/p109-backup-and-deploy.sh
if ($LASTEXITCODE -ne 0) { throw "scp do deploy falhou; tar permanece em $tar" }
ssh -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 lojadepaes "sed -i 's/\r$//' /tmp/p109-backup-and-deploy.sh && bash /tmp/p109-backup-and-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "publicacao remota falhou; tar permanece em $tar" }

Remove-Item -Force $tar
Write-Host "tar local apagado"
