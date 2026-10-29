#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$src = Join-Path $here "..\..\..\frontend\src\assets\brand\actionfinance-blue.png"
$dst = Join-Path $here "logo-hosted-ui.png"
if (-not (Test-Path -LiteralPath $src)) {
  throw "Official blue mark missing: $src"
}

python -c @"
from PIL import Image
src = Image.open(r'''$src''').convert('RGB')
target_w, target_h = 350, 178
scale = target_w / src.size[0]
nw, nh = target_w, max(1, int(src.size[1] * scale))
resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
canvas = Image.new('RGB', (target_w, target_h), (22, 3, 173))
canvas.paste(resized, (0, (target_h - nh) // 2))
canvas.save(r'''$dst''', format='PNG', optimize=True)
print(canvas.size, __import__('os').path.getsize(r'''$dst'''))
"@
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$info = Get-Item -LiteralPath $dst
if ($info.Length -gt 100KB) {
  throw "logo-hosted-ui.png is $($info.Length) bytes; classic Hosted UI limit is 100 KB."
}
Write-Host "Wrote $dst ($($info.Length) bytes)"
