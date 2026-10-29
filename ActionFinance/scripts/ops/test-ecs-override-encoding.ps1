#Requires -Version 5.1
# Isolated proof of the bootstrap argument path. Does not touch production.
# Source is ASCII-only so PowerShell 5.1 does not misread the test file.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "af-ecs-override-json.ps1")

# "Padaria São João — Ação e Pães"
$sample = "Padaria S" + [char]0x00E3 + "o Jo" + [char]0x00E3 + "o " + [char]0x2014 + " A" + [char]0x00E7 + [char]0x00E3 + "o e P" + [char]0x00E3 + "es"
Assert-AfEcsOverrideJsonPreservesText -Text $sample -ExpectedCodepoints @(0x00E3, 0x00E7, 0x2014)

$loja = "Loja de P" + [char]0x00E3 + "es"
$escaped = ConvertTo-AfEcsOverrideJson -Overrides @{
  containerOverrides = @(@{ name = "probe"; command = @("--company-name=$loja") })
}
if ($escaped -notmatch '\\u00e3') {
  throw "Expected \\u00e3 escape for U+00E3."
}
# First break of the original path: UTF-8 file bytes read as Windows-1252.
$utf8 = New-Object System.Text.UTF8Encoding $false
$rawUtf8 = $utf8.GetBytes($loja)
$as1252 = [System.Text.Encoding]::GetEncoding(1252).GetString($rawUtf8)
$as1252Codes = @($as1252.ToCharArray() | ForEach-Object { [int]$_ })
if ($as1252Codes -notcontains 0x00C3 -or $as1252Codes -notcontains 0x00A3) {
  throw "Expected the historical Windows-1252 misread of UTF-8 U+00E3 to yield U+00C3 U+00A3."
}
Write-Host "ECS override JSON keeps U+00E3 / U+00E7 / U+2014 without Windows-1252 mojibake."
