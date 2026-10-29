# Postgres descartável + endpoint real de listagem Pay. Não usa :5433.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$name = "prm009-hub-postgres"
$port = 55432
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    $owner = (Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object -First 1).OwningProcess
    throw "Porta $port ocupada por pid=$owner. Recusando iniciar."
}
$existing = docker ps -a --filter "name=^/${name}$" --format "{{.Names}}"
if ($existing -eq $name) {
    $inspect = docker inspect $name --format "{{.State.Status}} {{json .Config.Labels}}"
    if ($inspect -notmatch "prm009=1") {
        throw "Container $name existe e não é do PRM009. Recusando."
    }
    docker start $name | Out-Null
} else {
    docker run -d --name $name --label prm009=1 `
        -e POSTGRES_USER=prm009 -e POSTGRES_PASSWORD=prm009 -e POSTGRES_DB=hub_prm009 `
        -p 127.0.0.1:${port}:5432 postgres:17.6 | Out-Null
}
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    docker exec $name pg_isready -U prm009 -d hub_prm009 | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw "Postgres descartável $name não ficou pronto" }
Get-Content (Join-Path $here "seed-hub.sql") -Raw | docker exec -i $name psql -U prm009 -d hub_prm009 | Out-Null
Write-Output "HUB_DB 127.0.0.1:${port}/hub_prm009 test-only"
