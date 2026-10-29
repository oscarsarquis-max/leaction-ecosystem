#Requires -Version 5.1
# Immutable identity of the cadastros candidate. No secrets. Does not publish.
[CmdletBinding()]
param(
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $OutFile) {
  $OutFile = Join-Path $root "documents\reviews\evidence\pre-publicacao-cadastros-015\identidade-candidata.json"
}

$files = @(
  "database\migrations\V13__pay_receipt_operational_env.sql",
  "database\migrations\V14__counterparty_directory.sql",
  "database\migrations\V15__counterparty_directory_grants.sql",
  "database\migrations\V16__counterparty_directory_integrity.sql",
  "database\migrations\V17__counterparty_directory_integrity_grants.sql",
  "database\migrations\V18__counterparty_import_line_idem_scope.sql",
  "database\migrations\V19__counterparty_document_claim_backfill.sql",
  "backend\src\main\java\br\com\actionfinance\application\finance\PartyDirectoryService.java",
  "backend\src\main\java\br\com\actionfinance\application\finance\PartyImportService.java",
  "backend\src\main\java\br\com\actionfinance\application\finance\PartyRecords.java",
  "backend\src\main\java\br\com\actionfinance\domain\DocumentNumbers.java",
  "backend\src\main\java\br\com\actionfinance\domain\DocumentType.java",
  "backend\src\main\java\br\com\actionfinance\domain\PersonKind.java",
  "backend\src\main\java\br\com\actionfinance\domain\UnitKind.java",
  "backend\src\main\java\br\com\actionfinance\domain\AddressUsage.java",
  "backend\src\main\java\br\com\actionfinance\infrastructure\persistence\JdbcPartyRepository.java",
  "backend\src\main\java\br\com\actionfinance\interfaces\http\PartyDirectoryController.java",
  "backend\src\test\java\br\com\actionfinance\PartyDirectoryIT.java",
  "backend\src\test\java\br\com\actionfinance\PartyDirectorySchemaUpgradeIT.java",
  "backend\src\test\java\br\com\actionfinance\PartyDirectoryUpgradeDataIT.java",
  "frontend\src\CounterpartiesPages.tsx",
  "frontend\src\CounterpartiesPages.test.tsx",
  "frontend\src\app.css",
  "frontend\scripts\capture-cadastros-014.mjs",
  "documents\operations\ACTIONFINANCE_PACOTE_CADASTROS_011.md"
)

$hashes = @()
foreach ($rel in $files) {
  $path = Join-Path $root $rel
  if (-not (Test-Path -LiteralPath $path)) {
    throw "Missing candidate file: $rel"
  }
  $hashes += [ordered]@{
    path   = ($rel -replace '\\', '/')
    sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    bytes  = (Get-Item -LiteralPath $path).Length
  }
}

$gitHead = (git -C $root rev-parse HEAD).Trim()
$gitSubject = (git -C $root log -1 --format=%s).Trim()

$previousLocal = "actionfinance:sair-cognito-010-4e556ecd"
$previousInspect = $null
try {
  $raw = docker image inspect $previousLocal --format "{{json .}}" | Out-String
  $img = $raw | ConvertFrom-Json
  $previousInspect = [ordered]@{
    tag          = $previousLocal
    id           = [string]$img.Id
    repoDigests  = @($img.RepoDigests)
    created      = [string]$img.Created
    equivalentTo = "253137917703.dkr.ecr.us-east-2.amazonaws.com/actionfinance@sha256:06e067e772f65d37a0cf43c53022e32d9e0a76eb9841cfebaf75d684b28f953c"
  }
} catch {
  $previousInspect = [ordered]@{ tag = $previousLocal; error = $_.Exception.Message }
}

$payload = [ordered]@{
  recordedAt          = (Get-Date).ToUniversalTime().ToString("o")
  prompt              = "ACTIONFINANCE_PROMPT_PRE_PUBLICACAO_CADASTROS_015"
  gitHeadAtRecord     = $gitHead
  gitHeadSubject      = $gitSubject
  identityKind        = "file-manifest-sha256"
  note                = "HEAD alone plus a dirty tree is not the candidate. Reproduce from these hashes. No secrets. Image of this candidate was not published."
  schemaFiles         = @("V13","V14","V15","V16","V17","V18","V19")
  build               = [ordered]@{
    backendArtifact = "not-built-in-015"
    frontendDist    = "not-built-in-015"
    candidateImage  = "none-not-published"
    genericVersion  = "0.1.0 is not an identity"
  }
  previousPublished   = [ordered]@{
    taskFamily = "actionfinance-web"
    revision   = 11
    ecr        = "253137917703.dkr.ecr.us-east-2.amazonaws.com/actionfinance@sha256:06e067e772f65d37a0cf43c53022e32d9e0a76eb9841cfebaf75d684b28f953c"
    jarSha256  = "79dd27b0bb00a349cf596d6fe22a6ed417da747f8ff0addabf72d41d32302830"
    flywayInJar = @("V1","V2","V3","V4","V5","V6","V7","V8","V9","V10","V11","V12")
    webFlywayEnabledInProduction = $false
  }
  previousLocalImage  = $previousInspect
  files               = $hashes
}

New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutFile -Encoding utf8
Write-Host "Wrote $OutFile"
Write-Host "files=$($hashes.Count) gitHead=$gitHead"
