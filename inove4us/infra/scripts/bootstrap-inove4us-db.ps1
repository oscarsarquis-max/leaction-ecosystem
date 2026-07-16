#Requires -Version 5.1
<#
.SYNOPSIS
  Copia schema + dados das tabelas da Mesa/Oficina de LeAction_SysF -> inove4us
  no Docker leaction_db, sem alterar LeAction_SysF nem as 3 tabelas legadas de inove4us.

.NOTES
  Acesso: mesmo user/host do PanelDX (admin @ localhost:5433).
  Idempotente: recria apenas as tabelas listadas (DROP + restore).
#>
param(
  [string]$Container = "leaction_db",
  [string]$SourceDb = "LeAction_SysF",
  [string]$TargetDb = "inove4us",
  [string]$DbUser = "admin"
)

$ErrorActionPreference = "Stop"

# Tabelas usadas pelo app + pais de FK necessários para constraints.
$Tables = @(
  "esim_provedores",
  "esim_eventos_catalog",
  "leaf_dime",
  "leaf_doma",
  "dx_direcionadores",
  "dx_objetivos",
  "dx_krs",
  "ctdi_clie",
  "paneldx_usuarios",
  "ctdi_team",
  "esim_eventos",
  "ctdi_matu",
  "ctdi_lead_access",
  "ctdi_problemas_referencia",
  "ctdi_projetos",
  "ctdi_squads",
  "ctdi_sprn",
  "ctdi_main",
  "ctdi_itera",
  "ctdi_okr_direcionadores",
  "ctdi_okr_objetivos_dt",
  "ctdi_okr_krs",
  "ctdi_okr_atividades",
  "inov_metod_ativas",
  "metodo_ativas_praticas",
  "inov_agenda_rotina",
  "inov_agenda_notas",
  "inov_acoes",
  "inov_acao_notas_mapping",
  "inov_acoes_escolas_vinculo",
  "inov_subtasks",
  "esim_mesa_backlog",
  "espex_acao",
  "leaf_bloc"
)

$Preserve = @("interaction_history", "projects", "step_progress")
$DumpPath = "/tmp/inove4us-bootstrap.sql"

Write-Host "==> Verificando container $Container..."
docker inspect $Container --format "{{.State.Status}}" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Container $Container nao encontrado." }

Write-Host "==> Garantindo database $TargetDb..."
$exists = (docker exec $Container psql -U $DbUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$TargetDb'").Trim()
if (-not $exists) {
  docker exec $Container psql -U $DbUser -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $TargetDb OWNER $DbUser;"
  if ($LASTEXITCODE -ne 0) { throw "CREATE DATABASE falhou" }
}

Write-Host "==> Preservando tabelas legadas: $($Preserve -join ', ')"
$preserveCheck = (docker exec $Container psql -U $DbUser -d $TargetDb -tAc `
  "SELECT string_agg(tablename, ',' ORDER BY tablename) FROM pg_tables WHERE schemaname='public' AND tablename IN ('interaction_history','projects','step_progress')").Trim()
Write-Host "    encontradas: $preserveCheck"

Write-Host "==> Removendo apenas tabelas alvo em $TargetDb (se existirem)..."
$dropList = ($Tables | ForEach-Object { "public.$_" }) -join ", "
docker exec $Container psql -U $DbUser -d $TargetDb -v ON_ERROR_STOP=1 -c "DROP TABLE IF EXISTS $dropList CASCADE;"
if ($LASTEXITCODE -ne 0) { throw "Falha ao dropar tabelas alvo em $TargetDb" }

$Functions = @("fn_recalcular_progresso_kr", "fn_sync_atividade_dx_kr_id")
$FnPath = "/tmp/inove4us-fns.sql"

Write-Host "==> Copiando funcoes de trigger ($($Functions -join ', '))..."
$fnList = ($Functions | ForEach-Object { "'$_'" }) -join ","
$fnExtract = "SELECT pg_get_functiondef(p.oid) || ';' FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'public' AND p.proname IN ($fnList) ORDER BY p.proname;"
$fnSql = docker exec $Container psql -U $DbUser -d $SourceDb -Atc $fnExtract
if ($LASTEXITCODE -ne 0 -or -not $fnSql) { throw "Extracao de funcoes falhou" }
$fnSql | docker exec -i $Container tee $FnPath | Out-Null
docker exec $Container psql -U $DbUser -d $TargetDb -v ON_ERROR_STOP=1 -f $FnPath
if ($LASTEXITCODE -ne 0) { throw "Apply de funcoes falhou" }

Write-Host "==> Dump schema+data de $SourceDb ($($Tables.Count) tabelas)..."
$tableArgs = @()
foreach ($t in $Tables) { $tableArgs += @("-t", "public.$t") }
$dumpCmd = @(
  "pg_dump", "-U", $DbUser, "-d", $SourceDb,
  "--no-owner", "--no-acl", "--clean", "--if-exists",
  "-f", $DumpPath
) + $tableArgs
docker exec $Container @dumpCmd
if ($LASTEXITCODE -ne 0) { throw "pg_dump falhou (exit $LASTEXITCODE)" }

Write-Host "==> Restore em $TargetDb..."
docker exec $Container psql -U $DbUser -d $TargetDb -v ON_ERROR_STOP=1 -f $DumpPath
if ($LASTEXITCODE -ne 0) { throw "psql restore falhou (exit $LASTEXITCODE)" }

Write-Host "==> Owner/grants (admin, como PanelDX)..."
$grantLines = foreach ($t in $Tables) {
  "ALTER TABLE IF EXISTS public.$t OWNER TO $DbUser; GRANT ALL ON TABLE public.$t TO $DbUser;"
}
$grantSql = $grantLines -join " "
docker exec $Container psql -U $DbUser -d $TargetDb -v ON_ERROR_STOP=1 -c $grantSql | Out-Null

# sequences owned by serial columns
docker exec $Container psql -U $DbUser -d $TargetDb -v ON_ERROR_STOP=1 -c @"
DO `$`$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'S'
  LOOP
    EXECUTE format('ALTER SEQUENCE public.%I OWNER TO %I', r.relname, '$DbUser');
    EXECUTE format('GRANT ALL ON SEQUENCE public.%I TO %I', r.relname, '$DbUser');
  END LOOP;
END
`$`$;
"@

Write-Host "==> Validacao..."
$inList = ($Tables | ForEach-Object { "'$_'" }) -join ","
docker exec $Container psql -U $DbUser -d $TargetDb -c @"
SELECT 'legacy_tables' AS check, COUNT(*)::text AS value
FROM pg_tables WHERE schemaname='public'
  AND tablename IN ('interaction_history','projects','step_progress')
UNION ALL
SELECT 'app_tables', COUNT(*)::text
FROM pg_tables WHERE schemaname='public' AND tablename IN ($inList)
UNION ALL
SELECT 'ctdi_clie_rows', COUNT(*)::text FROM public.ctdi_clie
UNION ALL
SELECT 'leaf_bloc_rows', COUNT(*)::text FROM public.leaf_bloc
UNION ALL
SELECT 'problemas_ref', COUNT(*)::text FROM public.ctdi_problemas_referencia;
"@

# Confirm source untouched (spot-check)
$srcCount = (docker exec $Container psql -U $DbUser -d $SourceDb -tAc "SELECT COUNT(*) FROM public.ctdi_clie").Trim()
Write-Host "==> OK. $SourceDb.ctdi_clie ainda tem $srcCount linhas (inalterado)."
Write-Host "    Ajuste .env: DB_NAME=$TargetDb"
docker exec $Container rm -f $DumpPath $FnPath | Out-Null
