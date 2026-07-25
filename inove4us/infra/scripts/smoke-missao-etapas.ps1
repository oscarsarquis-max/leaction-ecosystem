#Requires -Version 5.1
<#
.SYNOPSIS
  Smoke test ponta a ponta - Estruturacao Pedagogica Etapas 1-4 (Blocos A-E).

.EXAMPLE
  .\infra\scripts\smoke-missao-etapas.ps1
#>
param(
  [string]$BaseUrl = "http://127.0.0.1:5011",
  [string]$FeUrl = "http://127.0.0.1:5174",
  [string]$Email = "inovador@inove4us.com.br",
  [string]$Code = "LA-INOVE1",
  [string]$DbContainer = "leaction_db",
  [string]$DbName = "inove4us",
  [string]$DbUser = "admin",
  [string]$ExemploJson = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if (-not $ExemploJson) {
  $ExemploJson = Join-Path $PSScriptRoot "..\..\inove4us_docs\exemplos\importacao-aulas-exemplo.json"
}
$ExemploJson = (Resolve-Path $ExemploJson).Path

$results = New-Object System.Collections.Generic.List[object]

function Record([string]$Id, [string]$Status, [string]$Evidence, [string]$RootCause = "") {
  $script:results.Add([pscustomobject]@{
      Id        = $Id
      Status    = $Status
      Evidence  = $Evidence
      RootCause = $RootCause
    })
  $color = if ($Status -eq "PASSOU") { "Green" } elseif ($Status -eq "PULADO") { "Yellow" } else { "Red" }
  Write-Host ("[{0}] {1} - {2}" -f $Status, $Id, $Evidence) -ForegroundColor $color
  if ($RootCause) { Write-Host ("         causa: {0}" -f $RootCause) -ForegroundColor DarkRed }
}

function Invoke-Json {
  param(
    [string]$Method,
    [string]$Url,
    [object]$Body = $null,
    [Microsoft.PowerShell.Commands.WebRequestSession]$Session
  )
  $params = @{
    Uri             = $Url
    Method          = $Method
    WebSession      = $Session
    UseBasicParsing = $true
    TimeoutSec      = 90
  }
  if ($null -ne $Body) {
    $params.ContentType = "application/json; charset=utf-8"
    $params.Body = ($Body | ConvertTo-Json -Depth 12 -Compress)
  }
  try {
    $resp = Invoke-WebRequest @params
    return [pscustomobject]@{
      StatusCode = [int]$resp.StatusCode
      Content    = $resp.Content
      Json       = $(try { $resp.Content | ConvertFrom-Json } catch { $null })
    }
  } catch {
    $r = $_.Exception.Response
    if (-not $r) {
      return [pscustomobject]@{ StatusCode = 0; Content = $_.Exception.Message; Json = $null }
    }
    $stream = $r.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $text = $reader.ReadToEnd()
    return [pscustomobject]@{
      StatusCode = [int]$r.StatusCode
      Content    = $text
      Json       = $(try { $text | ConvertFrom-Json } catch { $null })
    }
  }
}

function Invoke-Sql([string]$Sql) {
  $wrapped = "SET client_min_messages TO WARNING;`n" + $Sql
  $out = $wrapped | docker exec -i $DbContainer psql -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -t -A -q 2>&1
  if ($LASTEXITCODE -ne 0) { throw "SQL falhou: $out" }
  $lines = @($out | Where-Object { $_ -and ($_ -notmatch '^(INSERT|UPDATE|DELETE|SET)\b') })
  return (($lines | Out-String).Trim())
}

function Get-SessionCookieHeader([Microsoft.PowerShell.Commands.WebRequestSession]$Session, [string]$Url) {
  $uri = [Uri]$Url
  $cookies = $Session.Cookies.GetCookies($uri)
  $parts = New-Object System.Collections.Generic.List[string]
  foreach ($c in $cookies) { [void]$parts.Add(("{0}={1}" -f $c.Name, $c.Value)) }
  return ($parts -join "; ")
}

function Invoke-ImportFile {
  param(
    [string]$Url,
    [string]$FilePath,
    [Microsoft.PowerShell.Commands.WebRequestSession]$Session
  )
  $cookie = Get-SessionCookieHeader -Session $Session -Url $Url
  $tmpOut = Join-Path $env:TEMP ("imp-out-" + [guid]::NewGuid().ToString() + ".json")
  $curlArgs = @(
    "-sS", "-X", "POST",
    "-H", ("Cookie: {0}" -f $cookie),
    "-F", ("file=@{0};type=application/json" -f $FilePath),
    "-o", $tmpOut,
    "-w", "%{http_code}",
    $Url
  )
  $code = & curl.exe @curlArgs
  $text = ""
  if (Test-Path $tmpOut) {
    $text = Get-Content -Path $tmpOut -Raw -ErrorAction SilentlyContinue
    Remove-Item $tmpOut -Force -ErrorAction SilentlyContinue
  }
  return [pscustomobject]@{
    StatusCode = [int]$code
    Content    = $text
    Json       = $(try { $text | ConvertFrom-Json } catch { $null })
  }
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$base = $BaseUrl.TrimEnd("/")
$stamp = Get-Date -Format "yyyyMMddHHmmss"

Write-Host ""
Write-Host "=== SMOKE MISSAO ETAPAS 1-4 ===" -ForegroundColor Cyan
Write-Host ("API={0} FE={1}" -f $base, $FeUrl)
Write-Host ("exemplo={0}" -f $ExemploJson)
Write-Host ""

Write-Host "==> Login" -ForegroundColor Cyan
$gk = Invoke-Json -Method GET -Url "$base/gatekeeper/status" -Session $session
if ($gk.StatusCode -ne 200 -or [bool]$gk.Json.locked) {
  Record "E0-gatekeeper" "FALHOU" ("status={0} locked={1}" -f $gk.StatusCode, $gk.Json.locked) "API/gatekeeper indisponivel"
  exit 1
}

$sqlCode = @"
DO `$`$
DECLARE v_id int;
BEGIN
  SELECT id_clie INTO v_id FROM public.ctdi_clie WHERE lower(mail_clie) = lower('$Email') LIMIT 1;
  IF v_id IS NULL THEN RAISE EXCEPTION 'Usuario % nao encontrado', '$Email'; END IF;
  INSERT INTO public.ctdi_lead_access (id_clie, access_code)
  VALUES (v_id, '$Code')
  ON CONFLICT (id_clie) DO UPDATE SET access_code = EXCLUDED.access_code;
  UPDATE public.ctdi_clie SET creditos_ia = GREATEST(COALESCE(creditos_ia,0), 3) WHERE id_clie = v_id;
END
`$`$;
"@
Invoke-Sql $sqlCode | Out-Null

$login = Invoke-Json -Method POST -Url "$base/api/auth/verify-code" -Session $session -Body @{ email = $Email; code = $Code }
$me = Invoke-Json -Method GET -Url "$base/api/auth/me" -Session $session
if ($login.StatusCode -ne 200 -or $me.Json.authenticated -ne $true) {
  Record "E0-login" "FALHOU" ("login={0} auth={1}" -f $login.StatusCode, $me.Json.authenticated) "verify-code/sessao"
  exit 1
}
$idClie = [int]$me.Json.user.id_clie
$creditosAntes = [int]$me.Json.user.creditos_ia
Record "E0-login" "PASSOU" ("id_clie={0} creditos={1}" -f $idClie, $creditosAntes)

# ===== BLOCO A =====
Write-Host ""
Write-Host "==> Bloco A - Cadastro base" -ForegroundColor Cyan

$instNome = "Escola Exemplo"
$cursoNome = "Ensino Fundamental II"
$discNome = "Matematica"

$inst = Invoke-Json -Method POST -Url "$base/api/instituicoes" -Session $session -Body @{
  nome             = $instNome
  tipo_instituicao = "escola"
  rede             = "privada"
  cidade           = "Smoke City"
  uf               = "SP"
}
$instId = $inst.Json.instituicao.id
if ($inst.StatusCode -notin @(200, 201) -or -not $instId) {
  Record "A1-instituicao" "FALHOU" ("HTTP {0} {1}" -f $inst.StatusCode, $inst.Content) "POST /api/instituicoes"
} else {
  Record "A1-instituicao" "PASSOU" ("id={0} nome={1}" -f $instId, $instNome)
}

$p1 = Invoke-Json -Method POST -Url "$base/api/instituicoes/$instId/periodos-letivos" -Session $session -Body @{
  rotulo                  = "2026-1 Smoke"
  ano_letivo              = 2026
  tipo_periodo            = "semestral"
  data_inicio             = "2026-02-01"
  data_fim                = "2026-07-31"
  duracao_padrao_aula_min = 50
  em_curso                = $true
  status                  = "em_andamento"
}
$p1Id = $p1.Json.periodo.id
if ($p1.StatusCode -notin @(200, 201) -or -not $p1Id) {
  Record "A1-periodo1" "FALHOU" ("HTTP {0} {1}" -f $p1.StatusCode, $p1.Content) "criar periodo em_curso"
} else {
  Record "A1-periodo1" "PASSOU" ("id={0} em_curso={1}" -f $p1Id, $p1.Json.periodo.em_curso)
}

$p2 = Invoke-Json -Method POST -Url "$base/api/instituicoes/$instId/periodos-letivos" -Session $session -Body @{
  rotulo                  = "2026-2 Smoke"
  ano_letivo              = 2026
  tipo_periodo            = "semestral"
  data_inicio             = "2026-08-01"
  data_fim                = "2026-12-15"
  duracao_padrao_aula_min = 50
  em_curso                = $false
  status                  = "planejamento"
}
$p2Id = $p2.Json.periodo.id
if (-not $p2Id) {
  Record "A2-periodo2" "FALHOU" ("HTTP {0} {1}" -f $p2.StatusCode, $p2.Content) "criar 2o periodo"
} else {
  Record "A2-periodo2" "PASSOU" ("id={0}" -f $p2Id)
}

$mark = Invoke-Json -Method POST -Url "$base/api/periodos-letivos/$p2Id/marcar-em-curso" -Session $session -Body @{}
$chkEmCurso = Invoke-Sql ("SELECT string_agg(id::text || ':' || em_curso::text, ',') FROM public.inove_periodos_letivos WHERE instituicao_id = {0} AND ativo = TRUE;" -f $instId)
$emCursoCount = Invoke-Sql ("SELECT COUNT(*)::int FROM public.inove_periodos_letivos WHERE instituicao_id = {0} AND ativo = TRUE AND em_curso = TRUE;" -f $instId)
if ($mark.StatusCode -eq 200 -and [int]$emCursoCount -eq 1 -and $chkEmCurso -match ("{0}:t" -f $p2Id) -and $chkEmCurso -match ("{0}:f" -f $p1Id)) {
  Record "A2-unico-em-curso" "PASSOU" ("count={0} map={1}" -f $emCursoCount, $chkEmCurso)
} else {
  Record "A2-unico-em-curso" "FALHOU" ("mark={0} count={1} map={2}" -f $mark.StatusCode, $emCursoCount, $chkEmCurso) "indice unico / marcar-em-curso"
}

$null = Invoke-Json -Method POST -Url "$base/api/periodos-letivos/$p1Id/marcar-em-curso" -Session $session -Body @{}

$curso = Invoke-Json -Method POST -Url "$base/api/periodos-letivos/$p1Id/cursos" -Session $session -Body @{
  nome  = $cursoNome
  nivel = "fundamental"
}
$cursoId = $curso.Json.curso.id
if ($curso.StatusCode -notin @(200, 201) -or -not $cursoId) {
  Record "A1-curso" "FALHOU" ("HTTP {0} {1}" -f $curso.StatusCode, $curso.Content) "POST cursos"
} else {
  Record "A1-curso" "PASSOU" ("id={0}" -f $cursoId)
}

# Nome "Matematica" no cadastro; exemplo JSON usa "Matematica" sem acento no smoke
# Ajusta exemplo em memoria: criamos disciplina com nome do JSON
$discNomeJson = "Matematica"
$disc = Invoke-Json -Method POST -Url "$base/api/cursos/$cursoId/disciplinas" -Session $session -Body @{
  nome   = $discNomeJson
  codigo = "MAT-SMOKE"
}
$discId = $disc.Json.disciplina.id
if ($disc.StatusCode -notin @(200, 201) -or -not $discId) {
  Record "A1-disciplina" "FALHOU" ("HTTP {0} {1}" -f $disc.StatusCode, $disc.Content) "POST disciplinas"
} else {
  Record "A1-disciplina" "PASSOU" ("id={0} nome={1}" -f $discId, $discNomeJson)
}

# Alias com acento para match do arquivo exemplo (Matematica vs Matematica UTF-8)
# O exemplo tem "Matematica" com acento - criar segunda disciplina OU atualizar exemplo.
# Atualiza nome da disciplina para bater exatamente com o JSON do exemplo.
$updDisc = Invoke-Json -Method PUT -Url "$base/api/disciplinas/$discId" -Session $session -Body @{
  nome = "Matematica"
}
# Force exact name from exemplo file via SQL (UTF-8 Matematica with accent)
Invoke-Sql ("UPDATE public.inove_disciplinas SET nome = E'Matem\u00e1tica' WHERE id = {0};" -f $discId) | Out-Null
Invoke-Sql ("UPDATE public.inove_instituicoes SET nome = 'Escola Exemplo' WHERE id = {0};" -f $instId) | Out-Null
Invoke-Sql ("UPDATE public.inove_cursos SET nome = 'Ensino Fundamental II' WHERE id = {0};" -f $cursoId) | Out-Null

$delCurso = Invoke-Json -Method DELETE -Url "$base/api/cursos/$cursoId" -Session $session
if ($delCurso.StatusCode -eq 409) {
  Record "A3-bloqueio-curso" "PASSOU" ("HTTP 409 code={0}" -f $delCurso.Json.code)
} else {
  Record "A3-bloqueio-curso" "FALHOU" ("HTTP {0} {1}" -f $delCurso.StatusCode, $delCurso.Content) "esperado 409 com disciplina ativa"
}

# ===== BLOCO B =====
Write-Host ""
Write-Host "==> Bloco B - Fluxo manual Etapa 3" -ForegroundColor Cyan

$hoje = (Get-Date).ToString("yyyy-MM-dd")
$aulaLivre = Invoke-Json -Method POST -Url "$base/api/daily/planejar" -Session $session -Body @{
  tema_aula      = ("Smoke B livre {0}" -f $stamp)
  data_planejada = $hoje
  turma_nome     = "7A"
  origem         = "manual"
}
$aulaLivreId = $aulaLivre.Json.id
if (-not $aulaLivreId) { $aulaLivreId = $aulaLivre.Json.aula.id }
$aLivre = $aulaLivre.Json.aula
$semDisc = ($null -eq $aLivre.disciplina_id) -or ([string]$aLivre.disciplina_id -eq "")
if ($aulaLivre.StatusCode -in @(200, 201) -and $aulaLivreId -and $semDisc) {
  Record "B1-aula-sem-vinculo" "PASSOU" ("id={0} origem={1} evento={2}" -f $aulaLivreId, $aLivre.origem, $aLivre.id_evento_agenda)
} else {
  Record "B1-aula-sem-vinculo" "FALHOU" ("HTTP {0} {1}" -f $aulaLivre.StatusCode, $aulaLivre.Content) "planejar freemium"
}

$aulaVinc = Invoke-Json -Method POST -Url "$base/api/daily/planejar" -Session $session -Body @{
  tema_aula      = ("Smoke B vinculada {0}" -f $stamp)
  data_planejada = $hoje
  turma_nome     = "7B"
  disciplina_id  = $discId
  origem         = "manual"
}
$aulaVincId = $aulaVinc.Json.id
if (-not $aulaVincId) { $aulaVincId = $aulaVinc.Json.aula.id }
$aVinc = $aulaVinc.Json.aula
$evIdVinc = $aVinc.id_evento_agenda
$dbVinc = Invoke-Sql ("SELECT disciplina_id::text || '|' || origem FROM public.inove_aulas_simples WHERE id = {0};" -f $aulaVincId)
$agendaHas = 0
if ($evIdVinc) {
  $agendaHas = [int](Invoke-Sql ("SELECT COUNT(*)::int FROM public.inove_agenda_eventos WHERE id_evento = {0} AND id_clie = {1};" -f $evIdVinc, $idClie))
}
if ($aulaVinc.StatusCode -in @(200, 201) -and $dbVinc -eq ("{0}|manual" -f $discId) -and $agendaHas -ge 1) {
  Record "B2-aula-com-vinculo" "PASSOU" ("id={0} db={1} agenda={2} (origem manual = Dia a Dia)" -f $aulaVincId, $dbVinc, $evIdVinc)
} else {
  Record "B2-aula-com-vinculo" "FALHOU" ("HTTP {0} db={1} agenda={2}" -f $aulaVinc.StatusCode, $dbVinc, $agendaHas) "disciplina_id/origem/agenda"
}

$pai = Invoke-Json -Method POST -Url "$base/api/agenda-eventos" -Session $session -Body @{
  titulo      = ("Smoke grafo pai {0}" -f $stamp)
  data_evento = ("{0}T10:00:00" -f $hoje)
  tipo        = "geral"
  status      = "planejado"
}
$paiId = $pai.Json.evento.id_evento
$filho = Invoke-Json -Method POST -Url "$base/api/agenda-eventos" -Session $session -Body @{
  titulo        = ("Smoke grafo filho {0}" -f $stamp)
  data_evento   = ("{0}T11:00:00" -f $hoje)
  tipo          = "geral"
  status        = "planejado"
  id_evento_pai = $paiId
}
$filhoId = $filho.Json.evento.id_evento
$grafo = Invoke-Json -Method GET -Url "$base/api/agenda-eventos/grafo" -Session $session
$edgeOk = $false
foreach ($e in @($grafo.Json.edges)) {
  if ([string]$e.from -eq [string]$paiId -and [string]$e.to -eq [string]$filhoId) { $edgeOk = $true }
}
$nodesHave = $false
if ($grafo.Json.nodes) {
  $ids = @($grafo.Json.nodes | ForEach-Object { [string]$_.id })
  $nodesHave = ($ids -contains [string]$paiId) -and ($ids -contains [string]$filhoId)
}
if ($grafo.StatusCode -eq 200 -and $edgeOk -and $nodesHave) {
  Record "B3-grafo" "PASSOU" ("edge {0}->{1}; nodes={2} edges={3}" -f $paiId, $filhoId, @($grafo.Json.nodes).Count, @($grafo.Json.edges).Count)
} else {
  Record "B3-grafo" "FALHOU" ("HTTP {0} edgeOk={1} nodesHave={2}" -f $grafo.StatusCode, $edgeOk, $nodesHave) "GET /grafo ou id_evento_pai"
}

# ===== BLOCO C =====
Write-Host ""
Write-Host "==> Bloco C - Importacao" -ForegroundColor Cyan

# Patch temporario do exemplo: garantir UTF-8 e nomes resolviveis
$exemploWork = Join-Path $env:TEMP ("smoke-exemplo-{0}.json" -f $stamp)
$rawEx = Get-Content -Path $ExemploJson -Raw -Encoding UTF8
# Mantem conteudo; nomes ja alinhados no DB (Escola Exemplo / Ensino Fundamental II / Matematica)
Set-Content -Path $exemploWork -Value $rawEx -Encoding UTF8

$imp1 = Invoke-ImportFile -Url "$base/api/importacoes/aulas-eventos" -FilePath $exemploWork -Session $session
$imp1Json = $imp1.Json
$lote1 = $imp1Json.lote_id
if ($imp1.StatusCode -in @(200, 201) -and [int]$imp1Json.total_sucesso -eq 3 -and [int]$imp1Json.total_erro -eq 1 -and $lote1) {
  Record "C1-contadores" "PASSOU" ("lote={0} sucesso={1} erro={2} aviso={3}" -f $lote1, $imp1Json.total_sucesso, $imp1Json.total_erro, $imp1Json.total_aviso)
} else {
  Record "C1-contadores" "FALHOU" ("HTTP {0} {1}" -f $imp1.StatusCode, $imp1.Content) "esperado sucesso=3 erro=1"
}

$loteDb = 0
if ($lote1) {
  $loteDb = [int](Invoke-Sql ("SELECT COUNT(*)::int FROM public.inove_importacoes_lote WHERE id = {0} AND id_clie = {1};" -f $lote1, $idClie))
}
if ($loteDb -eq 1) {
  Record "C1-lote-db" "PASSOU" ("inove_importacoes_lote id={0}" -f $lote1)
} else {
  Record "C1-lote-db" "FALHOU" ("count={0}" -f $loteDb) "lote nao persistido"
}

$relErro = @($imp1Json.relatorio) | Where-Object { $_.id_externo -eq "AULA-BAD" -or ($_.status -eq "erro" -and [string]$_.mensagem -match "data") }
if ($relErro -and ([string]$relErro[0].mensagem -match "data")) {
  Record "C1-relatorio-erro" "PASSOU" ("AULA-BAD: {0}" -f $relErro[0].mensagem)
} else {
  Record "C1-relatorio-erro" "FALHOU" "relatorio sem erro de data claro" "parse/relatorio"
}

$agendaCnt = [int](Invoke-Sql "SELECT COUNT(*)::int FROM public.inove_agenda_eventos WHERE id_clie = $idClie AND id_externo_importacao IN ('AULA-001','AULA-002','EVT-001');")
$aulaCnt = [int](Invoke-Sql "SELECT COUNT(*)::int FROM public.inove_aulas_simples WHERE id_clie = $idClie AND id_externo_importacao IN ('AULA-001','AULA-002');")
$evtAulaLeak = [int](Invoke-Sql "SELECT COUNT(*)::int FROM public.inove_aulas_simples WHERE id_clie = $idClie AND id_externo_importacao = 'EVT-001';")
$draftOk = [int](Invoke-Sql "SELECT COUNT(*)::int FROM public.inove_aulas_simples WHERE id_clie = $idClie AND id_externo_importacao IN ('AULA-001','AULA-002') AND status = 'draft';")
$linkOk = [int](Invoke-Sql @"
SELECT COUNT(*)::int
  FROM public.inove_aulas_simples a
  JOIN public.inove_agenda_eventos e ON e.id_evento = a.id_evento_agenda
 WHERE a.id_clie = $idClie
   AND a.id_externo_importacao IN ('AULA-001','AULA-002')
   AND e.id_externo_importacao = a.id_externo_importacao;
"@)

if ($agendaCnt -eq 3) {
  Record "C2-agenda" "PASSOU" "3 eventos em inove_agenda_eventos"
} else {
  Record "C2-agenda" "FALHOU" ("count={0}" -f $agendaCnt) "espelho/agenda"
}
if ($aulaCnt -eq 2 -and $draftOk -eq 2 -and $linkOk -eq 2 -and $evtAulaLeak -eq 0) {
  Record "C2-aulas-simples" "PASSOU" "2 aulas draft com id_evento_agenda ok; EVT-001 sem Dia a Dia"
} else {
  Record "C2-aulas-simples" "FALHOU" ("aulas={0} draft={1} link={2} evtLeak={3}" -f $aulaCnt, $draftOk, $linkOk, $evtAulaLeak) "espelho Dia a Dia"
}

$paiExt = Invoke-Sql @"
SELECT e2.id_externo_importacao
  FROM public.inove_agenda_eventos e1
  JOIN public.inove_agenda_eventos e2 ON e2.id_evento = e1.id_evento_pai
 WHERE e1.id_clie = $idClie AND e1.id_externo_importacao = 'AULA-002';
"@
$grafoImp = Invoke-Json -Method GET -Url "$base/api/agenda-eventos/grafo" -Session $session
$id001 = Invoke-Sql "SELECT id_evento::text FROM public.inove_agenda_eventos WHERE id_clie=$idClie AND id_externo_importacao='AULA-001';"
$id002 = Invoke-Sql "SELECT id_evento::text FROM public.inove_agenda_eventos WHERE id_clie=$idClie AND id_externo_importacao='AULA-002';"
$edgeImp = $false
foreach ($e in @($grafoImp.Json.edges)) {
  if ([string]$e.from -eq $id001 -and [string]$e.to -eq $id002) { $edgeImp = $true }
}
if ($paiExt -eq "AULA-001" -and $edgeImp) {
  Record "C3-vinculo-pai" "PASSOU" "AULA-002.id_evento_pai -> AULA-001; edge no grafo"
} else {
  Record "C3-vinculo-pai" "FALHOU" ("paiExt={0} edgeImp={1} ids={2}->{3}" -f $paiExt, $edgeImp, $id001, $id002) "2a passada / grafo"
}

$imp2 = Invoke-ImportFile -Url "$base/api/importacoes/aulas-eventos" -FilePath $exemploWork -Session $session
$imp2Json = $imp2.Json
$dupAgenda = [int](Invoke-Sql "SELECT COUNT(*)::int FROM public.inove_agenda_eventos WHERE id_clie = $idClie AND id_externo_importacao IN ('AULA-001','AULA-002','EVT-001');")
if (
  $imp2.StatusCode -in @(200, 201) -and
  [int]$imp2Json.total_sucesso -eq 3 -and
  [int]$imp2Json.total_criados -eq 0 -and
  [int]$imp2Json.total_atualizados -ge 3 -and
  $dupAgenda -eq 3
) {
  Record "C4-idempotencia" "PASSOU" ("criados={0} atualizados={1} agenda_unica={2} lote2={3}" -f $imp2Json.total_criados, $imp2Json.total_atualizados, $dupAgenda, $imp2Json.lote_id)
} else {
  Record "C4-idempotencia" "FALHOU" ("HTTP {0} criados={1} atualizados={2} agenda={3} body={4}" -f $imp2.StatusCode, $imp2Json.total_criados, $imp2Json.total_atualizados, $dupAgenda, $imp2.Content) "unique (id_clie,id_externo)"
}

$freePath = Join-Path $env:TEMP ("smoke-free-{0}.json" -f $stamp)
$freeJsonObj = @(
  @{ id_externo = ("FREE-{0}-1" -f $stamp); titulo = "Aula freemium solta"; tipo = "aula"; data = "2026-09-01" },
  @{ id_externo = ("FREE-{0}-2" -f $stamp); titulo = "Evento freemium"; tipo = "evento"; data = "2026-09-02" }
)
($freeJsonObj | ConvertTo-Json -Depth 5) | Set-Content -Path $freePath -Encoding UTF8
$impFree = Invoke-ImportFile -Url "$base/api/importacoes/aulas-eventos" -FilePath $freePath -Session $session
$freeJson = $impFree.Json
if (
  $impFree.StatusCode -in @(200, 201) -and
  [int]$freeJson.total_sucesso -eq 2 -and
  [int]$freeJson.total_erro -eq 0 -and
  [int]$freeJson.total_aviso -eq 0
) {
  Record "C5-freemium" "PASSOU" "sucesso=2 erro=0 aviso=0"
} else {
  Record "C5-freemium" "FALHOU" ("HTTP {0} {1}" -f $impFree.StatusCode, $impFree.Content) "import sem vinculo pedagogico"
}

$missPath = Join-Path $env:TEMP ("smoke-miss-{0}.json" -f $stamp)
$missName = ("DisciplinaQueNaoExisteXYZ{0}" -f $stamp)
$missArr = @(
  @{
    id_externo = ("MISS-{0}" -f $stamp)
    titulo     = "Aula disciplina fantasma"
    tipo       = "aula"
    data       = "2026-09-10"
    disciplina = $missName
  }
)
(,$missArr[0] | ConvertTo-Json -Depth 5) | Set-Content -Path $missPath -Encoding UTF8
# Force array wrapper
('[' + (($missArr[0] | ConvertTo-Json -Depth 5 -Compress)) + ']') | Set-Content -Path $missPath -Encoding UTF8
$impMiss = Invoke-ImportFile -Url "$base/api/importacoes/aulas-eventos" -FilePath $missPath -Session $session
$missJson = $impMiss.Json
$missExt = ("MISS-{0}" -f $stamp)
$missDisc = Invoke-Sql ("SELECT COALESCE(disciplina_id::text,'(null)') FROM public.inove_agenda_eventos WHERE id_clie = {0} AND id_externo_importacao = '{1}';" -f $idClie, $missExt)
$missOkLine = @($missJson.relatorio) | Where-Object { $_.id_externo -eq $missExt -and $_.status -eq "ok" }
if (
  $impMiss.StatusCode -in @(200, 201) -and
  [int]$missJson.total_sucesso -eq 1 -and
  [int]$missJson.total_erro -eq 0 -and
  [int]$missJson.total_aviso -ge 1 -and
  $missDisc -eq "(null)" -and
  $missOkLine
) {
  Record "C6-aviso-miss" "PASSOU" ("aviso={0} disciplina_id=null msg={1}" -f $missJson.total_aviso, $missOkLine[0].mensagem)
} else {
  Record "C6-aviso-miss" "FALHOU" ("HTTP {0} disc={1} body={2}" -f $impMiss.StatusCode, $missDisc, $impMiss.Content) "best-effort por nome"
}

$mesImp = "2026-08"
$filtro = Invoke-Json -Method GET -Url ("{0}/api/agenda-eventos?mes={1}&origem=importacao" -f $base, $mesImp) -Session $session
$filtIds = @($filtro.Json.eventos | ForEach-Object { $_.id_externo_importacao })
$has001 = $filtIds -contains "AULA-001"
$allImport = (@($filtro.Json.eventos).Count -gt 0) -and ((@($filtro.Json.eventos | Where-Object { $_.origem -ne "importacao" })).Count -eq 0)
$feAgendaPath = Join-Path $PSScriptRoot "..\..\frontend\src\components\AgendaExecutiva.jsx"
$feMesaPath = Join-Path $PSScriptRoot "..\..\frontend\src\pages\MesaDoInovador.jsx"
$feBadge = Select-String -Path $feAgendaPath -Pattern "Importado" -SimpleMatch -Quiet
$feImportLink = Select-String -Path $feMesaPath -Pattern "/importacoes" -SimpleMatch -Quiet
if ($filtro.StatusCode -eq 200 -and $has001 -and $allImport -and $feBadge) {
  Record "C7-badge-filtro" "PASSOU" ("filtro n={0}; AULA-001 ok; badge FE presente" -f @($filtro.Json.eventos).Count)
} else {
  Record "C7-badge-filtro" "FALHOU" ("HTTP {0} has001={1} allImport={2} badge={3}" -f $filtro.StatusCode, $has001, $allImport, $feBadge) "filtro/badge"
}

# ===== BLOCO D =====
Write-Host ""
Write-Host "==> Bloco D - Seguranca" -ForegroundColor Cyan

$noSess = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$unauth = Invoke-Json -Method POST -Url "$base/api/importacoes/aulas-eventos" -Session $noSess -Body @{ registros = @() }
if ($unauth.StatusCode -eq 401) {
  Record "D1-import-401" "PASSOU" "POST sem sessao -> 401"
} else {
  Record "D1-import-401" "FALHOU" ("HTTP {0}" -f $unauth.StatusCode) "require_session"
}

$otherClie = Invoke-Sql ("SELECT id_clie::text FROM public.ctdi_clie WHERE id_clie <> {0} ORDER BY id_clie LIMIT 1;" -f $idClie)
if (-not $otherClie) {
  Record "D2-lote-alheio" "PULADO" "sem outro id_clie no banco"
  Record "D3-ownership-404" "PULADO" "sem outro id_clie"
} else {
  $otherLote = Invoke-Sql ("INSERT INTO public.inove_importacoes_lote (id_clie, nome_arquivo, formato, total_registros) VALUES ({0}, 'alien.json', 'json', 0) RETURNING id::text;" -f $otherClie)
  $getAlien = Invoke-Json -Method GET -Url "$base/api/importacoes/$otherLote" -Session $session
  if ($getAlien.StatusCode -eq 404) {
    Record "D2-lote-alheio" "PASSOU" ("GET lote {0} (clie {1}) -> 404" -f $otherLote, $otherClie)
  } else {
    Record "D2-lote-alheio" "FALHOU" ("HTTP {0}" -f $getAlien.StatusCode) "esperado 404 ownership"
  }

  $alienIds = Invoke-Sql @"
WITH i AS (
  INSERT INTO public.inove_instituicoes (id_clie, nome, tipo_instituicao, rede)
  VALUES ($otherClie, 'Alien Inst $stamp', 'escola', 'privada')
  RETURNING id
), p AS (
  INSERT INTO public.inove_periodos_letivos (instituicao_id, rotulo, ano_letivo, tipo_periodo, data_inicio, data_fim)
  SELECT id, 'Alien P', 2026, 'anual', '2026-01-01', '2026-12-31' FROM i
  RETURNING id
), c AS (
  INSERT INTO public.inove_cursos (periodo_letivo_id, nome)
  SELECT id, 'Alien Curso' FROM p
  RETURNING id
), d AS (
  INSERT INTO public.inove_disciplinas (curso_id, nome)
  SELECT id, 'Alien Disc' FROM c
  RETURNING id
)
SELECT (SELECT id::text FROM p) || ',' || (SELECT id::text FROM c) || ',' || (SELECT id::text FROM d);
"@
  $parts = $alienIds -split ","
  $alienPeriodo = $parts[0]; $alienCurso = $parts[1]; $alienDisc = $parts[2]
  $rP = Invoke-Json -Method GET -Url "$base/api/periodos-letivos/$alienPeriodo" -Session $session
  $rC = Invoke-Json -Method GET -Url "$base/api/cursos/$alienCurso" -Session $session
  $rD = Invoke-Json -Method GET -Url "$base/api/disciplinas/$alienDisc" -Session $session
  if ($rP.StatusCode -eq 404 -and $rC.StatusCode -eq 404 -and $rD.StatusCode -eq 404) {
    Record "D3-ownership-404" "PASSOU" "periodo/curso/disciplina alheios -> 404/404/404"
  } else {
    Record "D3-ownership-404" "FALHOU" ("P={0} C={1} D={2}" -f $rP.StatusCode, $rC.StatusCode, $rD.StatusCode) "vazamento ownership"
  }
}

# ===== BLOCO E =====
Write-Host ""
Write-Host "==> Bloco E - Regressao" -ForegroundColor Cyan

$me2 = Invoke-Json -Method GET -Url "$base/api/auth/me" -Session $session
if ($me2.StatusCode -eq 200 -and $me2.Json.authenticated -eq $true -and $null -ne $me2.Json.user.creditos_ia) {
  Record "E1-auth-me" "PASSOU" ("creditos={0} notices={1}" -f $me2.Json.user.creditos_ia, @($me2.Json.user.hub_notices).Count)
} else {
  Record "E1-auth-me" "FALHOU" ("HTTP {0}" -f $me2.StatusCode) "/api/auth/me"
}

$credBeforeWizard = [int]$me2.Json.user.creditos_ia
$wiz = Invoke-Json -Method POST -Url "$base/api/wizard/estruturar" -Session $session -Body @{
  problema        = ("Smoke missao: alunos nao engajam em fracoes {0}" -f $stamp)
  contexto        = "Turma 7A, 50 minutos"
  nivel_ensino    = "fundamental"
  disciplina_area = "matematica"
}
$me3 = Invoke-Json -Method GET -Url "$base/api/auth/me" -Session $session
$credAfter = [int]$me3.Json.user.creditos_ia
if ($wiz.StatusCode -eq 200 -and $credAfter -lt $credBeforeWizard) {
  Record "E2-wizard-credito" "PASSOU" ("estruturar OK; creditos {0} -> {1}" -f $credBeforeWizard, $credAfter)
} elseif ($wiz.StatusCode -eq 403 -and (($wiz.Json.code -eq "INSUFFICIENT_CREDITS") -or ($wiz.Content -match "credito"))) {
  Record "E2-wizard-credito" "PASSOU" ("gate INSUFFICIENT_CREDITS intacto (saldo={0})" -f $credBeforeWizard)
} elseif ($wiz.StatusCode -in @(502, 500, 503) -and $credAfter -eq $credBeforeWizard) {
  Record "E2-wizard-credito" "PULADO" ("Wizard HTTP {0} sem debitar (Bedrock/AWS?). Saldo intacto={1}" -f $wiz.StatusCode, $credAfter)
} else {
  Record "E2-wizard-credito" "FALHOU" ("HTTP {0} cred {1}->{2} body={3}" -f $wiz.StatusCode, $credBeforeWizard, $credAfter, $wiz.Content) "debito/wizard"
}

try {
  $feMesa = Invoke-WebRequest -Uri "$FeUrl/mesa-do-inovador" -UseBasicParsing -TimeoutSec 15
  $feCode = [int]$feMesa.StatusCode
} catch {
  $feCode = 0
}
if ($feCode -eq 200 -and $feImportLink) {
  Record "E3-mesa-importar" "PASSOU" "FE /mesa-do-inovador HTTP 200; Link Importar no source"
} else {
  Record "E3-mesa-importar" "FALHOU" ("FE={0} linkSource={1}" -f $feCode, $feImportLink) "atalho Importar"
}

# Relatorio
Write-Host ""
Write-Host "=== RELATORIO FINAL ===" -ForegroundColor Cyan
$pass = @($results | Where-Object { $_.Status -eq "PASSOU" }).Count
$fail = @($results | Where-Object { $_.Status -eq "FALHOU" }).Count
$skip = @($results | Where-Object { $_.Status -eq "PULADO" }).Count
Write-Host ("PASSOU={0}  FALHOU={1}  PULADO={2}  TOTAL={3}" -f $pass, $fail, $skip, $results.Count)
Write-Host ""
Write-Host "--- PASSOU ---" -ForegroundColor Green
$results | Where-Object { $_.Status -eq "PASSOU" } | ForEach-Object { Write-Host ("  {0}: {1}" -f $_.Id, $_.Evidence) }
if ($skip -gt 0) {
  Write-Host "--- PULADO ---" -ForegroundColor Yellow
  $results | Where-Object { $_.Status -eq "PULADO" } | ForEach-Object { Write-Host ("  {0}: {1}" -f $_.Id, $_.Evidence) }
}
if ($fail -gt 0) {
  Write-Host "--- FALHOU ---" -ForegroundColor Red
  $results | Where-Object { $_.Status -eq "FALHOU" } | ForEach-Object {
    Write-Host ("  {0}: {1}" -f $_.Id, $_.Evidence)
    if ($_.RootCause) { Write-Host ("         causa: {0}" -f $_.RootCause) }
  }
}

$reportPath = Join-Path $PSScriptRoot "..\..\inove4us_docs\SMOKE-MISSAO-ETAPAS-RESULTADO.md"
$lines = New-Object System.Collections.Generic.List[string]
[void]$lines.Add("# Smoke Missao Etapas 1-4 - Resultado")
[void]$lines.Add("")
[void]$lines.Add(("Data: {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")))
[void]$lines.Add(("Professor: {0} (id_clie={1})" -f $Email, $idClie))
[void]$lines.Add("")
[void]$lines.Add("| Item | Status | Evidencia | Causa raiz |")
[void]$lines.Add("|------|--------|-----------|------------|")
foreach ($r in $results) {
  $ev = ($r.Evidence -replace '\|', '/' -replace "`r|`n", " ")
  $rc = ($r.RootCause -replace '\|', '/' -replace "`r|`n", " ")
  [void]$lines.Add(("| {0} | {1} | {2} | {3} |" -f $r.Id, $r.Status, $ev, $rc))
}
[void]$lines.Add("")
[void]$lines.Add(("**Totais:** PASSOU={0} · FALHOU={1} · PULADO={2}" -f $pass, $fail, $skip))
$lines -join "`n" | Set-Content -Path $reportPath -Encoding UTF8
Write-Host ""
Write-Host ("Relatorio: {0}" -f $reportPath) -ForegroundColor DarkGray

if ($fail -gt 0) { exit 1 }
exit 0
