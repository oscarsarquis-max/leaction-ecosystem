# Percurso real AF -> Spider -> FORWARD -> Hub isolado. Não imprime tokens.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\_lib.ps1")
$root = Get-ActionFinanceRoot
$tokens = Read-ActionFinanceEnvFile (Join-Path $root ".local\demo-tokens.env")
$evidence = Join-Path $root "documents\reviews\evidence\prm-009-continuidade-001"
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
$op = $tokens.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A
$viewer = $tokens.ACTIONFINANCE_DEMO_TOKEN_VIEWER_A
$company = "11111111-1111-4111-a111-111111111111"
$af = "http://127.0.0.1:8091"

function Invoke-Af([string]$method, [string]$path, [string]$token, [hashtable]$query = @{}) {
    $headers = @{ Authorization = "Bearer $token"; Accept = "application/json" }
    $uri = "$af$path"
    if ($query.Count) {
        $qs = ($query.GetEnumerator() | ForEach-Object { "$($_.Key)=$([uri]::EscapeDataString($_.Value))" }) -join "&"
        $uri = "$uri`?$qs"
    }
    return Invoke-RestMethod -Method $method -Uri $uri -Headers $headers
}

$before = Invoke-Af GET "/api/v1/pay-receipts/integrity" $op @{ companyId = $company }
$hubBefore = Invoke-RestMethod "http://127.0.0.1:4101/__test/counts"
$edgeReset = Invoke-RestMethod -Method POST "http://127.0.0.1:8098/__test/reset-counts"
$first = Invoke-Af POST "/api/v1/pay-receipts/sync" $op @{ companyId = $company }
$afterFirst = Invoke-Af GET "/api/v1/pay-receipts" $op @{ companyId = $company }
$integrityAfter = Invoke-Af GET "/api/v1/pay-receipts/integrity" $op @{ companyId = $company }
$repeat = Invoke-Af POST "/api/v1/pay-receipts/sync" $op @{ companyId = $company }

$ids = @($afterFirst.items | ForEach-Object { $_.transactionId })
$hasOther = $ids -contains "30000000-0000-4000-8000-000000000001"
$item001 = $afterFirst.items | Where-Object { $_.transactionId -eq "20000000-0000-4000-8000-000000000001" } | Select-Object -First 1
$item002 = $afterFirst.items | Where-Object { $_.transactionId -eq "20000000-0000-4000-8000-000000000002" } | Select-Object -First 1
$item003 = $afterFirst.items | Where-Object { $_.transactionId -eq "20000000-0000-4000-8000-000000000003" } | Select-Object -First 1

docker exec prm009-hub-postgres psql -U prm009 -d hub_prm009 -c "update orders set status='REFUNDED', updated_at=now(), external_resource_id='{""app_id"":""homolog-padaria"",""sandbox"":true,""test_order"":true,""amount_cents"":12550,""currency"":""BRL""}' where id='20000000-0000-4000-8000-000000000001';" | Out-Null
$afterUpdate = Invoke-Af POST "/api/v1/pay-receipts/sync" $op @{ companyId = $company }
$listAfterUpdate = Invoke-Af GET "/api/v1/pay-receipts" $op @{ companyId = $company }
$updated001 = $listAfterUpdate.items | Where-Object { $_.transactionId -eq "20000000-0000-4000-8000-000000000001" } | Select-Object -First 1

$report = [ordered]@{
    hubHealth = (Invoke-RestMethod "http://127.0.0.1:4101/health")
    edgeHealth = (Invoke-RestMethod "http://127.0.0.1:8098/health")
    spiderHealth = (Invoke-RestMethod "http://127.0.0.1:8080/actuator/health")
    monitor = "http://127.0.0.1:5180/"
    finance = "http://127.0.0.1:5179/pay-receipts"
    integrityBefore = $before
    integrityAfter = $integrityAfter
    firstRun = @{ status = $first.run.status; imported = $first.run.importedCount; updated = $first.run.updatedCount; review = $first.run.reviewCount; pages = $first.run.pageCount; correlation = $first.run.rootCorrelationId; spiderMessageId = $first.run.spiderMessageId; monitorUrl = $first.run.monitorUrl }
    itemCountAfterFirst = @($afterFirst.items).Count
    otherCompanyLeaked = $hasOther
    amount001 = $item001.amountMinor
    amount002chargedPreferred = $item002.amountMinor
    amount003absent = $item003.amountAbsent
    amount003display = $item003.amountMinor
    repeatRun = @{ status = $repeat.run.status; imported = $repeat.run.importedCount; updated = $repeat.run.updatedCount }
    updated001status = $updated001.normalizedStatus
    updateRun = @{ status = $afterUpdate.run.status; imported = $afterUpdate.run.importedCount; updated = $afterUpdate.run.updatedCount }
    hubCounts = (Invoke-RestMethod "http://127.0.0.1:4101/__test/counts")
    edgeCounts = (Invoke-RestMethod "http://127.0.0.1:8098/__test/counts")
}
$report | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $evidence "live-first-pass.json") -Encoding utf8
Write-Output "FIRST status=$($first.run.status) imported=$($first.run.importedCount) pages=$($first.run.pageCount) items=$($report.itemCountAfterFirst) otherLeaked=$hasOther"
Write-Output "AMOUNT 001=$($item001.amountMinor) 002=$($item002.amountMinor) 003absent=$($item003.amountAbsent)"
Write-Output "REPEAT imported=$($repeat.run.importedCount) updated=$($repeat.run.updatedCount) status=$($repeat.run.status)"
Write-Output "UPDATE 001=$($updated001.normalizedStatus) updatedCount=$($afterUpdate.run.updatedCount)"
Write-Output "INTEGRITY titles $($before.titles)->$($integrityAfter.titles) settlements $($before.settlements)->$($integrityAfter.settlements)"
Write-Output "MONITOR $($first.run.monitorUrl)"
