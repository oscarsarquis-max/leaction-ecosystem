$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
$image = "lojadepaes:prod-20261029b"
$previous = "lojadepaes:prod-20261029a"
$tar = "C:\Temp\loja-prod-20261029b.tar"
$marker = "Dias, tetos e fechamentos"
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
  throw "bundle novo nao contem a marca do menu"
}

$left = Join-Path $env:TEMP "p108-backend-a"
$right = Join-Path $env:TEMP "p108-backend-b"
if (Test-Path $left) { Remove-Item -Recurse -Force $left }
if (Test-Path $right) { Remove-Item -Recurse -Force $right }
New-Item -ItemType Directory -Path $left, $right | Out-Null
$idA = docker create $previous
if ($LASTEXITCODE -ne 0) { throw "nao foi possivel criar o container da imagem anterior" }
$idB = docker create $image
if ($LASTEXITCODE -ne 0) { docker rm $idA | Out-Null; throw "nao foi possivel criar o container da imagem nova" }
docker cp "${idA}:/app/backend/app" $left
if ($LASTEXITCODE -ne 0) { docker rm $idA $idB | Out-Null; throw "copia do backend anterior falhou" }
docker cp "${idB}:/app/backend/app" $right
if ($LASTEXITCODE -ne 0) { docker rm $idA $idB | Out-Null; throw "copia do backend novo falhou" }
docker rm $idA $idB | Out-Null
git -c core.autocrlf=false diff --no-index --ignore-cr-at-eol -- (Join-Path $left "app") (Join-Path $right "app")
if ($LASTEXITCODE -ne 0) { throw "backend da imagem difere de $previous" }
Write-Host "backend identico a $previous"

docker save -o $tar $image
if ($LASTEXITCODE -ne 0) { throw "docker save failed; tar permanece em $tar" }

& "$root\scripts\p96-refresh-ssh.ps1" | Out-Null
$dir = (Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw).Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 -o TCPKeepAlive=yes $tar lojadepaes:/tmp/loja-prod-20261029b.tar
if ($LASTEXITCODE -ne 0) { throw "scp da imagem falhou; tar permanece em $tar" }
scp -F $cfg "$root\scripts\p108-backup-and-deploy.sh" lojadepaes:/tmp/p108-backup-and-deploy.sh
if ($LASTEXITCODE -ne 0) { throw "scp do deploy falhou; tar permanece em $tar" }
ssh -F $cfg -o ServerAliveInterval=15 -o ServerAliveCountMax=40 lojadepaes "sed -i 's/\r$//' /tmp/p108-backup-and-deploy.sh && bash /tmp/p108-backup-and-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "publicacao remota falhou; tar permanece em $tar" }

Remove-Item -Force $tar
Write-Host "tar local apagado"
