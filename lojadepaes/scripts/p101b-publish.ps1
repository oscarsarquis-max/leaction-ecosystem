$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
Set-Location $root
Write-Host "building image"
docker build -t lojadepaes:prod-20261021d .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
docker run --rm --entrypoint sh lojadepaes:prod-20261021d -c "grep -q delivery_confirmed_at /app/backend/app/models/orders.py && grep -q 'FLOW_ORDER_STATUSES,' /app/backend/app/domain/order_board.py && grep -q 'Iniciar mesmo sem pagamento' /app/frontend/dist/assets/*.js"
if ($LASTEXITCODE -ne 0) { throw "image is missing the 101B change" }
docker save -o C:\Temp\loja-prod-20261021d.tar lojadepaes:prod-20261021d
& "$root\scripts\p96-refresh-ssh.ps1"
$dir = Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw
$dir = $dir.Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg C:\Temp\loja-prod-20261021d.tar lojadepaes:/tmp/loja-prod-20261021d.tar
if ($LASTEXITCODE -ne 0) { throw "scp da imagem falhou" }
scp -F $cfg "$root\scripts\p101b-backup-and-deploy.sh" lojadepaes:/tmp/p101b-backup-and-deploy.sh
if ($LASTEXITCODE -ne 0) { throw "scp do deploy falhou" }
scp -F $cfg "$root\scripts\p101b-read.py" lojadepaes:/tmp/p101b-read.py
if ($LASTEXITCODE -ne 0) { throw "scp da leitura falhou" }
ssh -F $cfg lojadepaes "sed -i 's/\r$//' /tmp/p101b-backup-and-deploy.sh /tmp/p101b-read.py && bash /tmp/p101b-backup-and-deploy.sh && cid=`$(sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml ps -q api) && sudo docker cp /tmp/p101b-read.py `$cid:/tmp/p101b-read.py && sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T -w /app/backend api python /tmp/p101b-read.py"
if ($LASTEXITCODE -ne 0) { throw "publicação remota falhou" }
