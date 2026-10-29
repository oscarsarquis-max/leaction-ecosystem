# Falha entre páginas, retomada após restart do AF, disputa, viewer, alteração no limite do checkpoint.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\_lib.ps1")
$root = Get-ActionFinanceRoot
$tokens = Read-ActionFinanceEnvFile (Join-Path $root ".local\demo-tokens.env")
$evidence = Join-Path $root "documents\reviews\evidence\prm-009-continuidade-001"
$op = $tokens.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A
$viewer = $tokens.ACTIONFINANCE_DEMO_TOKEN_VIEWER_A
$company = "11111111-1111-4111-a111-111111111111"
$af = "http://127.0.0.1:8091"

function Invoke-AfRaw([string]$method, [string]$path, [string]$token, [hashtable]$query = @{}) {
    $uri = "$af$path"
    if ($query.Count) {
        $qs = ($query.GetEnumerator() | ForEach-Object { "$($_.Key)=$([uri]::EscapeDataString([string]$_.Value))" }) -join "&"
        $uri = "$uri`?$qs"
    }
    $tmpBody = Join-Path $env:TEMP ("prm009-" + [guid]::NewGuid().ToString("N") + ".json")
    $code = & curl.exe -s -o $tmpBody -w "%{http_code}" -X $method $uri -H "Authorization: Bearer $token" -H "Accept: application/json"
    $content = Get-Content $tmpBody -Raw
    Remove-Item $tmpBody -ErrorAction SilentlyContinue
    return [pscustomobject]@{ StatusCode = [int]$code; Content = $content }
}

function Invoke-Af([string]$method, [string]$path, [string]$token, [hashtable]$query = @{}) {
    return Invoke-RestMethod -Method $method -Uri "$af$path`?companyId=$company" -Headers @{ Authorization = "Bearer $token"; Accept = "application/json" }
}

Get-Content (Join-Path $PSScriptRoot "seed-more.sql") -Raw | docker exec -i prm009-hub-postgres psql -U prm009 -d hub_prm009 | Out-Null
Invoke-RestMethod -Method POST "http://127.0.0.1:8098/__test/reset-counts" | Out-Null
Invoke-RestMethod -Method PUT -Uri "http://127.0.0.1:8098/__test/list-fail-after" -ContentType "application/json" -Body '{"after":1}' | Out-Null

$partialResp = Invoke-AfRaw POST "/api/v1/pay-receipts/sync" $op @{ companyId = $company }
$partial = $partialResp.Content | ConvertFrom-Json
"PARTIAL http=$($partialResp.StatusCode) status=$($partial.run.status) imported=$($partial.run.importedCount) pages=$($partial.run.pageCount) error=$($partial.run.lastError)"

$firstNew = "20000000-0000-4000-8000-000000010001"
docker exec prm009-hub-postgres psql -U prm009 -d hub_prm009 -c "update orders set status='REFUNDED', updated_at=now() where id='$firstNew';" | Out-Null

# Restart only AF backend
$listener = Get-NetTCPConnection -LocalPort 8091 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$cim = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
if ($cim.CommandLine -notmatch "ActionFinanceApplication") { throw "8091 não é o AF" }
Stop-Process -Id $listener.OwningProcess
"STOPPED_AF pid=$($listener.OwningProcess)"
Start-Sleep -Seconds 2
Set-Location $root
& (Join-Path $root "scripts\dev\start-local.ps1") | Write-Output
Invoke-RestMethod -Method PUT -Uri "http://127.0.0.1:8098/__test/list-fail-after" -ContentType "application/json" -Body '{"after":null}' | Out-Null
Invoke-RestMethod -Method POST "http://127.0.0.1:8098/__test/reset-counts" | Out-Null

$resume = Invoke-Af POST "/api/v1/pay-receipts/sync" $op
"RESUME status=$($resume.run.status) imported=$($resume.run.importedCount) updated=$($resume.run.updatedCount) resumed=$($resume.resumed) pages=$($resume.run.pageCount)"

$list = Invoke-Af GET "/api/v1/pay-receipts" $op
$changed = $list.items | Where-Object { $_.transactionId -eq $firstNew } | Select-Object -First 1
"CHECKPOINT_UPDATE $($changed.transactionId) status=$($changed.normalizedStatus)"

$viewerResp = Invoke-AfRaw POST "/api/v1/pay-receipts/sync" $viewer @{ companyId = $company }
"VIEWER http=$($viewerResp.StatusCode)"

docker exec prm009-hub-postgres psql -U prm009 -d hub_prm009 -c "insert into orders (id,user_id,product_id,gateway_reference,gateway_ref,external_resource_id,status,created_at,updated_at) select ('20000000-0000-4000-8000-00000002'||lpad(n::text,4,'0'))::uuid,'10000000-0000-4000-8000-000000000001','10000000-0000-4000-8000-000000000002','proc-cc-'||n,'hub:homolog-padaria:cc'||n,json_build_object('app_id','homolog-padaria','sandbox',true,'test_order',true,'amount_cents',3000,'currency','BRL')::text,'PAID',now(),now() from generate_series(1,20) n on conflict do nothing;" | Out-Null
$tmp = Join-Path $evidence "concurrent"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$c1 = Join-Path $tmp "a.code"
$c2 = Join-Path $tmp "b.code"
$b1 = Join-Path $tmp "a.body"
$b2 = Join-Path $tmp "b.body"
$u = "http://127.0.0.1:8091/api/v1/pay-receipts/sync?companyId=$company"
$p1 = Start-Process -FilePath "curl.exe" -ArgumentList @("-s","-o",$b1,"-w","%{http_code}","-X","POST",$u,"-H","Authorization: Bearer $op") -RedirectStandardOutput $c1 -NoNewWindow -PassThru
$p2 = Start-Process -FilePath "curl.exe" -ArgumentList @("-s","-o",$b2,"-w","%{http_code}","-X","POST",$u,"-H","Authorization: Bearer $op") -RedirectStandardOutput $c2 -NoNewWindow -PassThru
Wait-Process -Id $p1.Id,$p2.Id
$concurrent = @((Get-Content $c1 -ErrorAction SilentlyContinue), (Get-Content $c2 -ErrorAction SilentlyContinue))
"CONCURRENT $($concurrent -join ' ')"

$out = [ordered]@{
    partialHttp = $partialResp.StatusCode
    partialStatus = $partial.run.status
    partialImported = $partial.run.importedCount
    resumeStatus = $resume.run.status
    resumeImported = $resume.run.importedCount
    resumeUpdated = $resume.run.updatedCount
    resumeResumed = $resume.resumed
    updatedDuringWindow = $changed.normalizedStatus
    viewerHttp = $viewerResp.StatusCode
    concurrent = $concurrent
    itemCount = @($list.items).Count
}
$out | ConvertTo-Json | Set-Content (Join-Path $evidence "live-resume.json") -Encoding utf8
