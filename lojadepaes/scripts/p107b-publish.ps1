$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
$image = "lojadepaes:prod-20261029a"
$tar = "C:\Temp\loja-prod-20261029a.tar"
$expectedBundle = "efc5c09e9fba1b6e16cb9799c2b6ddf76736f0df1acc517946c5424397a94bcc"
Set-Location $root

$free = (Get-PSDrive C).Free
if ($free -lt 3GB) {
  throw ("disco C: com menos de 3 GB livres: " + [math]::Round($free / 1GB, 2) + " GB")
}

Write-Host "building image"
docker build -t $image .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }

$bundle = docker run --rm --entrypoint sh $image -c "sha256sum /app/frontend/dist/assets/index-*.js"
if ($LASTEXITCODE -ne 0) { throw "nao foi possivel ler o bundle do frontend" }
Write-Host $bundle
if ($bundle -notmatch $expectedBundle) {
  throw "bundle do frontend difere de prod-20261028c; docker save nao foi feito"
}

docker run --rm --entrypoint sh $image -c "grep -q commit_on_error /app/backend/app/domain/storefront_orders.py && grep -q begin_nested /app/backend/app/domain/storefront_orders.py"
if ($LASTEXITCODE -ne 0) { throw "imagem sem commit_on_error ou begin_nested" }

docker save -o $tar $image
if ($LASTEXITCODE -ne 0) { throw "docker save failed; tar permanece em $tar" }

& "$root\scripts\p96-refresh-ssh.ps1" | Out-Null
$dir = (Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw).Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 -o TCPKeepAlive=yes $tar lojadepaes:/tmp/loja-prod-20261029a.tar
if ($LASTEXITCODE -ne 0) { throw "scp da imagem falhou; tar permanece em $tar" }
scp -F $cfg "$root\scripts\p107b-backup-and-deploy.sh" lojadepaes:/tmp/p107b-backup-and-deploy.sh
if ($LASTEXITCODE -ne 0) { throw "scp do deploy falhou; tar permanece em $tar" }
ssh -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 lojadepaes "sed -i 's/\r$//' /tmp/p107b-backup-and-deploy.sh && bash /tmp/p107b-backup-and-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "publicacao remota falhou; tar permanece em $tar" }

Remove-Item -Force $tar
Write-Host "tar local apagado"
