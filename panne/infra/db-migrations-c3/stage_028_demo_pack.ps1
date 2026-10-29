$ErrorActionPreference = "Stop"
$Src = "C:\Projetos\_release-028\panne\backend"
$Root = "C:\Projetos\_release-028\panne"
$Dest = "C:\Projetos\panne\infra\db-migrations-c3\_build_028_demo_pack"
$Stamp = Get-Date -Format "yyyyMMddHHmm"
$Tag = "backend-028-demo-pack-$Stamp"
$Head = (git -C $Root rev-parse HEAD)

if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
New-Item -ItemType Directory -Path $Dest | Out-Null

& robocopy $Src $Dest /E /NFL /NDL /NJH /NJS /nc /ns /np /XD .venv __pycache__ .pytest_cache .ruff_cache .mypy_cache htmlcov .git | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed exit=$LASTEXITCODE" }

Copy-Item "C:\Projetos\panne\infra\db-migrations-c3\_build_028_custos\Dockerfile" $Dest -Force
Copy-Item "C:\Projetos\panne\infra\db-migrations-c3\_build_028_custos\migrate_runner.py" $Dest -Force
Copy-Item "C:\Projetos\panne\infra\db-migrations-c3\_build_028_custos\redaction.py" $Dest -Force
Copy-Item "C:\Projetos\panne\infra\db-migrations-c3\_build_028_custos\rotate_demo_migrator.py" $Dest -Force
Copy-Item "C:\Projetos\panne\infra\db-migrations-c3\_build_028_custos\seed_runner.py" $Dest -Force

$mr = Join-Path $Dest "migrate_runner.py"
(Get-Content $mr -Raw).Replace('EXPECTED_HEAD = "0022_fiscal_inbound"', 'EXPECTED_HEAD = "0025_economic_audit_policy"') | Set-Content $mr -NoNewline -Encoding utf8

New-Item -ItemType Directory -Path (Join-Path $Dest "scripts") | Out-Null
Copy-Item (Join-Path $Root "scripts\gate3_append_demo_economy.py") (Join-Path $Dest "scripts\gate3_append_demo_economy.py") -Force
$g3 = Join-Path $Dest "scripts\gate3_append_demo_economy.py"
(Get-Content $g3 -Raw).Replace(
  'EVIDENCE = ROOT / "documentacao" / "evidencias" / "cursor-028-custos-organic" / "gate3"',
  'EVIDENCE = Path("/tmp/gate3-evidence")'
) | Set-Content $g3 -NoNewline -Encoding utf8

Add-Content (Join-Path $Dest "Dockerfile") "`nCOPY scripts/gate3_append_demo_economy.py ./scripts/gate3_append_demo_economy.py"

@{
  tag = $Tag
  git_head = $Head
  git_short = $Head.Substring(0, 7)
  git_dirty = $true
  source_worktree = $Root
  built_at = (Get-Date).ToUniversalTime().ToString("o")
  theme = "marrom/bege"
  notes = "CURSOR-028 demo pack. Dirty worktree. Tag does not claim git SHA. Destino exclusivo panne_demo."
  forbidden = @("tema verde", "DB panne", "Action Hub", "CMS")
  expected_alembic_head = "0025_economic_audit_policy"
} | ConvertTo-Json | Set-Content (Join-Path $Dest "MANIFEST.json") -Encoding utf8

Set-Content (Join-Path $Dest "IMAGE_TAG.txt") $Tag -NoNewline
Set-Content (Join-Path $Dest "SOURCE_SHA.txt") "$Head dirty-worktree tag-does-not-claim-sha" -NoNewline

Write-Output "DEST=$Dest"
Write-Output "TAG=$Tag"
Write-Output "HEAD=$Head"
Get-Content $mr | Select-String "EXPECTED_HEAD"
