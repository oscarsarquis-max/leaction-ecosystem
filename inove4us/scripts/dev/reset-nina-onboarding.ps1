# Reseta o onboarding da Nina para um professor (local / Docker leaction_db).
#
# O que faz:
#   1) Resolve id_clie pelo e-mail em ctdi_clie
#   2) Soft-delete (ativo=false) das instituições criadas no onboarding
#      (observacoes ILIKE '%onboarding da Nina%') e períodos/cursos/disciplinas filhos
#   3) Mostra a chave de localStorage e URL de reset no FE
#
# Uso:
#   cd C:\Projetos\inove4us
#   .\scripts\dev\reset-nina-onboarding.ps1
#   .\scripts\dev\reset-nina-onboarding.ps1 -Email inovador@inove4us.com.br
#   .\scripts\dev\reset-nina-onboarding.ps1 -Email outro@escola.com -WhatIf
#   .\scripts\dev\reset-nina-onboarding.ps1 -Email x@y.com -AllOnboarding:$false -InstituicaoId 3
#
# Requisitos: Docker container `leaction_db` com banco `inove4us` (user admin).

param(
    [string]$Email = 'inovador@inove4us.com.br',
    [string]$Container = 'leaction_db',
    [string]$DbName = 'inove4us',
    [string]$DbUser = 'admin',
    [Nullable[int]]$InstituicaoId = $null,
    [switch]$AllOnboarding = $true,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

function Write-Info([string]$Message) { Write-Host "[nina-reset] $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "[nina-reset] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[nina-reset] $Message" -ForegroundColor Yellow }
function Write-Err([string]$Message) { Write-Host "[nina-reset] $Message" -ForegroundColor Red }

function Invoke-InoveSql([string]$Sql) {
    $tmp = Join-Path $env:TEMP ("inove-nina-reset-{0}.sql" -f [guid]::NewGuid().ToString('N'))
    try {
        # UTF-8 sem BOM (BOM quebra o psql no Docker)
        $utf8 = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($tmp, $Sql, $utf8)
        $out = Get-Content -LiteralPath $tmp -Raw |
            docker exec -i $Container psql -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -f - 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "psql falhou (exit $LASTEXITCODE): $out"
        }
        return ($out | Out-String)
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ''
Write-Info '=== Reset onboarding Nina (local) ==='
Write-Info "E-mail: $Email"
Write-Info "Container: $Container / db: $DbName"

$running = docker inspect -f '{{.State.Running}}' $Container 2>$null
if ($running -ne 'true') {
    Write-Err "Container '$Container' nao esta rodando. Suba o Postgres (start-inove / start-hub)."
    exit 1
}

$emailEsc = $Email.Replace("'", "''")
$lookup = Invoke-InoveSql @"
SELECT id_clie, mail_clie, nome_clie
  FROM public.ctdi_clie
 WHERE lower(mail_clie) = lower('$emailEsc');
"@

$idLine = @(
    $lookup -split "`r?`n" |
        Where-Object { $_ -match '^\s*\d+\s*\|' }
) | Select-Object -First 1

if (-not $idLine) {
    Write-Err "Cliente nao encontrado para e-mail: $Email"
    Write-Host $lookup
    exit 1
}

$idClie = [int](($idLine -split '\|')[0].Trim())
Write-Ok "id_clie=$idClie ($(($idLine -split '\|')[1].Trim()))"

$instFilter = if ($InstituicaoId) {
    "AND i.id = $($InstituicaoId.Value)"
} elseif ($AllOnboarding) {
    "AND coalesce(i.observacoes, '') ILIKE '%onboarding da Nina%'"
} else {
    throw 'Informe -InstituicaoId ou mantenha -AllOnboarding (padrao).'
}

$listSql = @"
SELECT i.id, i.nome, i.ativo, left(coalesce(i.observacoes,''), 60) AS obs
  FROM public.inove_instituicoes i
 WHERE i.id_clie = $idClie
   $instFilter
 ORDER BY i.id;
"@
Write-Info 'Instituicoes alvo:'
Write-Host (Invoke-InoveSql $listSql)

if ($WhatIf) {
    Write-Warn 'WhatIf: nenhuma alteracao aplicada.'
    exit 0
}

$resetSql = @"
BEGIN;

UPDATE public.ctdi_clie
   SET nina_onboarding_done = FALSE
 WHERE id_clie = $idClie;

UPDATE public.inove_disciplinas d
   SET ativo = FALSE
  FROM public.inove_cursos c
  JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
  JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
 WHERE d.curso_id = c.id
   AND i.id_clie = $idClie
   $instFilter;

UPDATE public.inove_cursos c
   SET ativo = FALSE
  FROM public.inove_periodos_letivos p
  JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
 WHERE c.periodo_letivo_id = p.id
   AND i.id_clie = $idClie
   $instFilter;

UPDATE public.inove_periodos_letivos p
   SET ativo = FALSE,
       em_curso = FALSE
  FROM public.inove_instituicoes i
 WHERE p.instituicao_id = i.id
   AND i.id_clie = $idClie
   $instFilter;

UPDATE public.inove_instituicoes i
   SET ativo = FALSE
 WHERE i.id_clie = $idClie
   $instFilter;

SELECT 'instituicoes' AS escopo, i.id, i.nome, i.ativo::text AS ativo
  FROM public.inove_instituicoes i
 WHERE i.id_clie = $idClie
 ORDER BY i.id;

COMMIT;
"@

Write-Info 'Aplicando soft-delete...'
Write-Host (Invoke-InoveSql $resetSql)

$lsKey = "i4_nina_onboarding_v3_$idClie"
Write-Host ''
Write-Ok 'Onboarding resetado no banco (nina_onboarding_done=false + soft-delete).'
Write-Host "  localStorage key (cache): $lsKey"
Write-Host '  Fonte da verdade: coluna ctdi_clie.nina_onboarding_done'
Write-Host '  Para reabrir a Nina: http://localhost:5174/mesa-do-inovador?reset_onboarding=1'
Write-Host ''
