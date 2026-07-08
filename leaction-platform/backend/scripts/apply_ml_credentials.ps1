# Aplica credenciais ML em backend/.env a partir de .env.ml.secrets ou leaction-platform/.env
$ErrorActionPreference = "Stop"
$backend = Split-Path $PSScriptRoot -Parent
$rootEnv = Join-Path (Split-Path $backend -Parent) ".env"
$secrets = Join-Path $backend ".env.ml.secrets"
$target = Join-Path $backend ".env"

function Read-DotenvKeys([string]$path, [string[]]$keys) {
    $result = @{}
    if (-not (Test-Path $path)) { return $result }
    foreach ($line in Get-Content $path -Encoding UTF8) {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        $parts = $line.Split('=', 2)
        $k = $parts[0].Trim()
        $v = $parts[1].Trim()
        if ($keys -contains $k -and $v) { $result[$k] = $v }
    }
    return $result
}

$keys = @('ML_APP_ID', 'ML_SECRET_KEY')
$values = @{}
foreach ($src in @($secrets, $rootEnv)) {
    $found = Read-DotenvKeys $src $keys
    foreach ($k in $found.Keys) {
        if (-not $values[$k]) { $values[$k] = $found[$k] }
    }
}

if (-not $values['ML_APP_ID'] -or -not $values['ML_SECRET_KEY']) {
    Write-Host "Faltam credenciais. Preencha ML_APP_ID e ML_SECRET_KEY em:"
    Write-Host "  $secrets"
    Write-Host "  ou $rootEnv"
    exit 1
}

$content = if (Test-Path $target) { Get-Content $target -Raw -Encoding UTF8 } else { "" }
foreach ($k in $keys) {
    $line = "$k=$($values[$k])"
    if ($content -match "(?m)^$k=.*$") {
        $content = $content -replace "(?m)^$k=.*$", $line
    } else {
        $content = $content.TrimEnd() + "`n$line`n"
    }
}
Set-Content -Path $target -Value $content -Encoding UTF8 -NoNewline
Write-Host "backend/.env atualizado (ML_APP_ID + ML_SECRET_KEY)."
Write-Host "Reinicie o Marketplace :4012 e acesse /marketplace-api/ml/login"
