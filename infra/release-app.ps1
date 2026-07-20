<#
.SYNOPSIS
  Corta release versionado de inove4us ou Action Hub.

.DESCRIPTION
  Atualiza VERSION, garante seção no CHANGELOG, sincroniza package.json (Hub),
  opcionalmente grava GIT_SHA, cria commit e tag Git (inove4us/vX.Y.Z | actionhub/vX.Y.Z).

  NÃO faz deploy. Após o script: deploy + anotar DEPLOY_LOG.md + git push + git push --tags.

.EXAMPLE
  .\infra\release-app.ps1 -App inove4us -Version 1.0.1 -Summary "fix health" -Commit -Tag -WriteSha

.EXAMPLE
  .\infra\release-app.ps1 -App actionhub -Version 1.1.0 -Summary "credits inject" -Commit -Tag -Push
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('inove4us', 'actionhub')]
    [string]$App,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(-[A-Za-z0-9.-]+)?$')]
    [string]$Version,

    [string]$Summary = '',

    [switch]$Commit,
    [switch]$Tag,
    [switch]$WriteSha,
    [switch]$Push
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$map = @{
    inove4us   = @{
        Dir      = 'inove4us'
        TagPrefix = 'inove4us'
        PackageJson = $null
    }
    actionhub  = @{
        Dir      = 'leaction-platform'
        TagPrefix = 'actionhub'
        PackageJson = 'leaction-platform/frontend/action-hub/package.json'
    }
}

$cfg = $map[$App]
$appDir = Join-Path $Root $cfg.Dir
$versionFile = Join-Path $appDir 'VERSION'
$changelog = Join-Path $appDir 'CHANGELOG.md'
$deployLog = Join-Path $appDir 'DEPLOY_LOG.md'
$gitTag = "$($cfg.TagPrefix)/v$Version"
$today = Get-Date -Format 'yyyy-MM-dd'
$sha = (git rev-parse --short HEAD).Trim()

if (-not (Test-Path $appDir)) { throw "Pasta do app não encontrada: $appDir" }
if (-not (Test-Path $changelog)) { throw "CHANGELOG ausente: $changelog" }

Write-Host "==> App      : $App" -ForegroundColor Cyan
Write-Host "==> Version  : $Version"
Write-Host "==> Tag      : $gitTag"
Write-Host "==> SHA head : $sha"

# VERSION
[System.IO.File]::WriteAllText($versionFile, "$Version`n", [System.Text.UTF8Encoding]::new($false))
Write-Host "    wrote VERSION"

# package.json (Action Hub frontend)
if ($cfg.PackageJson) {
    $pkgPath = Join-Path $Root $cfg.PackageJson
    if (Test-Path $pkgPath) {
        $pkg = Get-Content $pkgPath -Raw -Encoding UTF8
        $pkg2 = $pkg -replace '"version"\s*:\s*"[^"]+"', "`"version`": `"$Version`""
        if ($pkg2 -eq $pkg) { throw "Não foi possível atualizar version em $pkgPath" }
        [System.IO.File]::WriteAllText($pkgPath, $pkg2, [System.Text.UTF8Encoding]::new($false))
        Write-Host "    updated package.json → $Version"
    }
}

# CHANGELOG — se a versão ainda não existe, promove Unreleased
$cl = Get-Content $changelog -Raw -Encoding UTF8
if ($cl -notmatch [regex]::Escape("## [$Version]")) {
    $section = @"
## [$Version] - $today

### Changed
- $Summary

"@
    if (-not $Summary) {
        $section = @"
## [$Version] - $today

### Changed
- Release $Version (preencher detalhes no CHANGELOG).

"@
    }
    if ($cl -match '(?m)^## \[Unreleased\]\s*\r?\n') {
        $cl = $cl -replace '(?m)^(## \[Unreleased\]\s*\r?\n)', "`$1`r`n$section"
    } else {
        $cl = $cl.TrimEnd() + "`r`n`r`n" + $section
    }
    [System.IO.File]::WriteAllText($changelog, $cl, [System.Text.UTF8Encoding]::new($false))
    Write-Host "    inserted CHANGELOG section [$Version]"
} else {
    Write-Host "    CHANGELOG já contém [$Version] — mantido"
}

# DEPLOY_LOG linha placeholder (SHA final após commit pode mudar — atualize no deploy)
if (Test-Path $deployLog) {
    $line = "| $today | $Version | $gitTag | $sha | prod | $Summary | |"
    $dl = Get-Content $deployLog -Raw -Encoding UTF8
    if ($dl -notmatch [regex]::Escape("|$Version|") -and $dl -notmatch [regex]::Escape("| $Version |")) {
        # Insere após o cabeçalho da tabela (primeira linha que começa com |---)
        if ($dl -match '(?m)^(\|[-| :]+\|\s*\r?\n)') {
            $dl = $dl -replace '(?m)^(\|[-| :]+\|\s*\r?\n)', "`$1$line`r`n"
            [System.IO.File]::WriteAllText($deployLog, $dl, [System.Text.UTF8Encoding]::new($false))
            Write-Host "    appended DEPLOY_LOG row"
        }
    }
}

if ($WriteSha) {
    $shaFile = Join-Path $appDir 'GIT_SHA'
    [System.IO.File]::WriteAllText($shaFile, "$sha`n", [System.Text.UTF8Encoding]::new($false))
    Write-Host "    wrote GIT_SHA ($sha) — regenere após o commit se o SHA mudar"
}

$paths = @(
    (Join-Path $cfg.Dir 'VERSION'),
    (Join-Path $cfg.Dir 'CHANGELOG.md'),
    (Join-Path $cfg.Dir 'DEPLOY_LOG.md')
)
if ($cfg.PackageJson) { $paths += $cfg.PackageJson }
if ($WriteSha) { $paths += (Join-Path $cfg.Dir 'GIT_SHA') }

if ($Commit) {
    git add -- @paths
    $msgFile = Join-Path $env:TEMP "release-$App-$Version.txt"
    $body = if ($Summary) { "release($App): v$Version — $Summary" } else { "release($App): v$Version" }
    [System.IO.File]::WriteAllText($msgFile, "$body`n")
    git commit -F $msgFile
    if ($LASTEXITCODE -ne 0) { throw 'git commit falhou' }
    $sha = (git rev-parse --short HEAD).Trim()
    Write-Host "    commit OK ($sha)" -ForegroundColor Green
    if ($WriteSha) {
        [System.IO.File]::WriteAllText((Join-Path $appDir 'GIT_SHA'), "$sha`n", [System.Text.UTF8Encoding]::new($false))
        git add -- (Join-Path $cfg.Dir 'GIT_SHA')
        # amend only if we created the commit in this script and not pushed — user rules are strict about amend
        # Prefer a tiny follow-up note in DEPLOY_LOG instead of amend
        Write-Host "    GIT_SHA atualizado para $sha (inclua no próximo commit se necessário)"
    }
}

if ($Tag) {
    $existing = git tag -l $gitTag
    if ($existing) { throw "Tag já existe: $gitTag" }
    $tagMsg = if ($Summary) { "$App v$Version — $Summary" } else { "$App v$Version" }
    git tag -a $gitTag -m $tagMsg
    if ($LASTEXITCODE -ne 0) { throw 'git tag falhou' }
    Write-Host "    tag OK: $gitTag" -ForegroundColor Green
}

if ($Push) {
    git push origin HEAD
    if ($LASTEXITCODE -ne 0) { throw 'git push falhou' }
    if ($Tag) {
        git push origin $gitTag
        if ($LASTEXITCODE -ne 0) { throw 'git push tag falhou' }
    }
    Write-Host "    push OK" -ForegroundColor Green
}

Write-Host "`nPróximos passos:" -ForegroundColor Cyan
Write-Host "  1) Deploy do app ($App)"
Write-Host "  2) Confirme health (version=$Version)"
Write-Host "  3) Ajuste SHA no DEPLOY_LOG.md se necessário"
if (-not $Push) {
    Write-Host "  4) git push origin HEAD && git push origin $gitTag"
}
