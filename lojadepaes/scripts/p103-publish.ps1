$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
Set-Location $root
Write-Host "building image"
docker build -t lojadepaes:prod-20261026a .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
docker run --rm --entrypoint sh lojadepaes:prod-20261026a -c "grep -q 'Pagamento dos vigentes' /app/frontend/dist/assets/*.js && grep -q 'Soma deste recorte' /app/frontend/dist/assets/*.js && grep -q 'admin-recipe-actions' /app/frontend/dist/assets/*.css"
if ($LASTEXITCODE -ne 0) { throw "image is missing the 103 change" }
docker save -o C:\Temp\loja-prod-20261026a.tar lojadepaes:prod-20261026a
if ($LASTEXITCODE -ne 0) { throw "docker save failed" }
& "$root\scripts\p96-refresh-ssh.ps1" | Out-Null
$dir = (Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw).Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg C:\Temp\loja-prod-20261026a.tar lojadepaes:/tmp/loja-prod-20261026a.tar
if ($LASTEXITCODE -ne 0) { throw "scp da imagem falhou" }
scp -F $cfg "$root\scripts\p103-backup-and-deploy.sh" lojadepaes:/tmp/p103-backup-and-deploy.sh
if ($LASTEXITCODE -ne 0) { throw "scp do deploy falhou" }
ssh -F $cfg lojadepaes "sed -i 's/\r$//' /tmp/p103-backup-and-deploy.sh && bash /tmp/p103-backup-and-deploy.sh"
if ($LASTEXITCODE -ne 0) { throw "publicação remota falhou" }
