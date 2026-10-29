$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
Set-Location $root
Write-Host "building image"
docker build -t lojadepaes:prod-20261021e .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
docker run --rm --entrypoint sh lojadepaes:prod-20261021e -c "grep -q correct_ready_to_in_production /app/backend/app/domain/orders.py && grep -q VIGENTE_ORDER_STATUSES /app/backend/app/domain/order_board.py && grep -q 'entra no total vigente' /app/frontend/dist/assets/*.js"
if ($LASTEXITCODE -ne 0) { throw "image is missing the 101C change" }
docker save -o C:\Temp\loja-prod-20261021e.tar lojadepaes:prod-20261021e
if ($LASTEXITCODE -ne 0) { throw "docker save failed" }
& "$root\scripts\p96-refresh-ssh.ps1" | Out-Null
$dir = (Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw).Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg C:\Temp\loja-prod-20261021e.tar lojadepaes:/tmp/loja-prod-20261021e.tar
if ($LASTEXITCODE -ne 0) { throw "scp da imagem falhou" }
scp -F $cfg "$root\scripts\p101c-backup-and-deploy.sh" "$root\scripts\p101c-read.py" "$root\scripts\p101c-repair.py" lojadepaes:/tmp/
if ($LASTEXITCODE -ne 0) { throw "scp dos scripts falhou" }
ssh -F $cfg lojadepaes "sed -i 's/\r$//' /tmp/p101c-backup-and-deploy.sh /tmp/p101c-read.py /tmp/p101c-repair.py && bash /tmp/p101c-backup-and-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "publicação remota falhou" }
ssh -F $cfg lojadepaes "cid=`$(sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml ps -q api) && sudo docker cp /tmp/p101c-read.py `$cid:/tmp/p101c-read.py && sudo docker cp /tmp/p101c-repair.py `$cid:/tmp/p101c-repair.py && echo READ_BEFORE && sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T -w /app/backend api python /tmp/p101c-read.py && echo REPAIR && sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T -w /app/backend api python /tmp/p101c-repair.py && echo READ_AFTER && sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T -w /app/backend api python /tmp/p101c-read.py"
if ($LASTEXITCODE -ne 0) { throw "leitura ou reparação falhou" }
