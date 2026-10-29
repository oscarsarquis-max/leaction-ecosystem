$ErrorActionPreference = "Stop"
$root = "C:\Projetos\lojadepaes"
& "$root\scripts\p96-refresh-ssh.ps1" | Out-Null
$dir = (Get-Content "C:\Temp\loja-ssh-p96-current.txt" -Raw).Trim()
$cfg = Join-Path $dir "ssh_config"
scp -F $cfg "$root\scripts\p101c-investigate.py" lojadepaes:/tmp/p101c-investigate.py
if ($LASTEXITCODE -ne 0) { throw "scp da leitura falhou" }
ssh -F $cfg lojadepaes "sed -i 's/\r$//' /tmp/p101c-investigate.py && cid=`$(sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml ps -q api) && sudo docker cp /tmp/p101c-investigate.py `$cid:/tmp/p101c-investigate.py && sudo docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T -w /app/backend api python /tmp/p101c-investigate.py"
if ($LASTEXITCODE -ne 0) { throw "leitura remota falhou" }
