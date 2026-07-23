#Requires -Version 5.1
<#
.SYNOPSIS
  Smoke test do vetor Dia a Dia (API /api/daily/*) no inove4us local.

.DESCRIPTION
  1) Checa API + gatekeeper
  2) Garante codigo de acesso do usuario de teste
  3) Login (cookie de sessao)
  4) Exercita sugerir -> planejar -> listar -> buscar -> atualizar -> excluir

.EXAMPLE
  .\infra\scripts\smoke-daily.ps1

.EXAMPLE
  .\infra\scripts\smoke-daily.ps1 -BaseUrl http://127.0.0.1:5011 -SkipCleanup
#>
param(
  [string]$BaseUrl = "http://127.0.0.1:5011",
  [string]$Email = "inovador@inove4us.com.br",
  [string]$Code = "LA-INOVE1",
  [string]$DbContainer = "leaction_db",
  [string]$DbName = "inove4us",
  [string]$DbUser = "admin",
  [switch]$SkipCleanup
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$msg) {
  Write-Host ""
  Write-Host "==> $msg" -ForegroundColor Cyan
}

function Assert-True([bool]$cond, [string]$ok, [string]$fail) {
  if (-not $cond) { throw $fail }
  Write-Host "  OK  $ok" -ForegroundColor Green
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
    TimeoutSec      = 20
  }
  if ($null -ne $Body) {
    $params.ContentType = "application/json; charset=utf-8"
    $params.Body = ($Body | ConvertTo-Json -Depth 8 -Compress)
  }
  try {
    $resp = Invoke-WebRequest @params
    $text = $resp.Content
    return [pscustomobject]@{
      StatusCode = [int]$resp.StatusCode
      Content    = $text
      Json       = $(try { $text | ConvertFrom-Json } catch { $null })
    }
  } catch {
    $r = $_.Exception.Response
    if (-not $r) { throw }
    $stream = $r.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $text = $reader.ReadToEnd()
    $code = [int]$r.StatusCode
    return [pscustomobject]@{
      StatusCode = $code
      Content    = $text
      Json       = $(try { $text | ConvertFrom-Json } catch { $null })
    }
  }
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$base = $BaseUrl.TrimEnd("/")

Write-Step "Health / gatekeeper ($base)"
$gk = Invoke-Json -Method GET -Url "$base/gatekeeper/status" -Session $session
Assert-True ($gk.StatusCode -eq 200) "gatekeeper status HTTP 200" "gatekeeper status falhou: $($gk.StatusCode)"
Assert-True (-not [bool]$gk.Json.locked) "sistema desbloqueado (locked=false)" "sistema ainda locked=true"

$me0 = Invoke-Json -Method GET -Url "$base/api/auth/me" -Session $session
Assert-True ($me0.StatusCode -eq 200) "/api/auth/me acessivel" "auth/me bloqueado: $($me0.StatusCode) $($me0.Content)"

Write-Step "Garantir access code $Code para $Email"
$sqlLines = @(
  "DO `$`$",
  "DECLARE v_id int;",
  "BEGIN",
  "  SELECT id_clie INTO v_id FROM public.ctdi_clie WHERE lower(mail_clie) = lower('$Email') LIMIT 1;",
  "  IF v_id IS NULL THEN",
  "    RAISE EXCEPTION 'Usuario % nao encontrado', '$Email';",
  "  END IF;",
  "  INSERT INTO public.ctdi_lead_access (id_clie, access_code)",
  "  VALUES (v_id, '$Code')",
  "  ON CONFLICT (id_clie) DO UPDATE SET access_code = EXCLUDED.access_code;",
  "END",
  "`$`$;"
)
($sqlLines -join "`n") | docker exec -i $DbContainer psql -U $DbUser -d $DbName -v ON_ERROR_STOP=1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Falha ao gravar access code no DB" }
Write-Host "  OK  codigo $Code gravado" -ForegroundColor Green

Write-Step "Login verify-code"
$login = Invoke-Json -Method POST -Url "$base/api/auth/verify-code" -Session $session -Body @{
  email = $Email
  code  = $Code
}
Assert-True ($login.StatusCode -eq 200) "login HTTP 200" "login falhou: $($login.StatusCode) $($login.Content)"
$me = Invoke-Json -Method GET -Url "$base/api/auth/me" -Session $session
Assert-True ($me.Json.authenticated -eq $true) "sessao autenticada" "sessao nao autenticada apos login"
Write-Host "  user: $($me.Json.user.nome_clie) | creditos=$($me.Json.user.creditos_ia)" -ForegroundColor DarkGray

Write-Step "GET /api/daily/sugerir-dinamicas"
$sug = Invoke-Json -Method GET -Url "$base/api/daily/sugerir-dinamicas?q=minute" -Session $session
if ($sug.StatusCode -eq 503 -and $sug.Json.code -eq "schema_pending") {
  Write-Host "  WARN schema_pending - esperado em prod sem migration 007; abortando CRUD." -ForegroundColor Yellow
  exit 0
}
Assert-True ($sug.StatusCode -eq 200) "sugerir HTTP 200" "sugerir falhou: $($sug.StatusCode) $($sug.Content)"
Assert-True ([int]$sug.Json.total -ge 1) "pelo menos 1 dinamica" "cache de dinamicas vazio"
$din = $sug.Json.dinamicas[0]
Write-Host "  dinamica: $($din.id) - $($din.nome)" -ForegroundColor DarkGray

Write-Step "POST /api/daily/planejar"
$hoje = (Get-Date).ToString("yyyy-MM-dd")
$plan = Invoke-Json -Method POST -Url "$base/api/daily/planejar" -Session $session -Body @{
  tema_aula             = "Smoke Dia a Dia - fracoes equivalentes"
  data_planejada        = $hoje
  turma_nome            = "7A"
  objetivo_aprendizagem = "Reconhecer fracoes equivalentes"
  acolhida              = "Pergunta rapida no quadro"
  conteudo_essencial    = "Definir equivalencia com exemplos"
  dinamica_ativa_id     = [string]$din.id
  fechamento_checkout   = "Exit ticket: 1 duvida restante"
}
Assert-True ($plan.StatusCode -in @(200, 201)) "planejar criado" "planejar falhou: $($plan.StatusCode) $($plan.Content)"
$aulaId = $plan.Json.id
if (-not $aulaId) { $aulaId = $plan.Json.aula.id }
Assert-True ($null -ne $aulaId) "id=$aulaId" "resposta sem id"

Write-Step "GET listar + buscar"
$listUrl = "$base/api/daily/?page=1" + "&page_size=20"
$list = Invoke-Json -Method GET -Url $listUrl -Session $session
Assert-True ($list.StatusCode -eq 200) "listar HTTP 200" "listar falhou: $($list.StatusCode)"
$found = @($list.Json.aulas) | Where-Object { [string]$_.id -eq [string]$aulaId }
Assert-True ($null -ne $found -and @($found).Count -ge 1) "aula na listagem" "aula $aulaId nao listada"

$get = Invoke-Json -Method GET -Url "$base/api/daily/$aulaId" -Session $session
Assert-True ($get.StatusCode -eq 200) "buscar HTTP 200" "buscar falhou: $($get.StatusCode)"
$gotDin = $get.Json.aula.dinamica_ativa_id
if (-not $gotDin) { $gotDin = $get.Json.dinamica_ativa_id }
Assert-True ([string]$gotDin -eq [string]$din.id) "dinamica_ativa_id persistida" "dinamica_ativa_id nao bateu ($gotDin vs $($din.id))"

Write-Step "PUT atualizar"
$upd = Invoke-Json -Method PUT -Url "$base/api/daily/$aulaId" -Session $session -Body @{
  tema_aula = "Smoke Dia a Dia - fracoes (atualizado)"
  status    = "planejado"
  acolhida  = "Acolhida revisada no smoke test"
}
Assert-True ($upd.StatusCode -eq 200) "atualizar HTTP 200" "atualizar falhou: $($upd.StatusCode) $($upd.Content)"

if (-not $SkipCleanup) {
  Write-Step "DELETE aula"
  $del = Invoke-Json -Method DELETE -Url "$base/api/daily/$aulaId" -Session $session
  Assert-True ($del.StatusCode -eq 200) "excluir HTTP 200" "excluir falhou: $($del.StatusCode) $($del.Content)"
} else {
  Write-Host ""
  Write-Host "SkipCleanup: aula $aulaId mantida para UI /dia-a-dia" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "SMOKE DAILY OK" -ForegroundColor Green
Write-Host ""
Write-Host "Checklist manual UI (http://localhost:5174):"
Write-Host "  [ ] Login -> Mesa limpa"
Write-Host "  [ ] Mesa -> Dia a Dia"
Write-Host "  [ ] Planejar Nova Aula + Sugerir Dinamica"
Write-Host "  [ ] Warn on exit sem salvar"
Write-Host "  [ ] Mobile: 1 coluna + botoes grandes"
Write-Host "  [ ] + Desafio e fluxo separado (opcional)"
