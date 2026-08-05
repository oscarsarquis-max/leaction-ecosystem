<#
.SYNOPSIS
  Observacao diaria homolog QMind (gate 011 V8) - nao bloqueante ao piloto.
  Coleta custo (tag Project=qmind), Lightsail CPU/disco, health/ready, HTTPS,
  alarmes, backup, metricas de worker/jobs (CloudWatch QMind/Homolog).
  Avalia gatilhos de interrupcao do piloto.
#>
param(
  [string] $Region = "us-east-2",
  [string] $InstanceName = "qmind-homolog-app",
  [string] $ApiBase = "https://api.homolog.qmind.com.br",
  [string] $AppBase = "https://app.homolog.qmind.com.br",
  [string] $BackupBucket = "",
  [string] $BackupPrefix = "pgdump/",
  [string] $OutDir = (Join-Path $PSScriptRoot "..\terraform-lightsail\observe"),
  [switch] $Baseline
)

$ErrorActionPreference = "Stop"
$day = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$now = (Get-Date).ToUniversalTime()
$start24 = $now.AddHours(-24)
$startMonth = Get-Date -Year $now.Year -Month $now.Month -Day 1 -Hour 0 -Minute 0 -Second 0
$startMonthUtc = [DateTime]::SpecifyKind($startMonth, "Utc")

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Get-HttpStatus([string]$Url) {
  try {
    $r = Invoke-WebRequest -Uri $Url -TimeoutSec 20 -UseBasicParsing
    return @{ ok = $true; status = [int]$r.StatusCode; ms = 0; error = $null }
  } catch {
    $code = $null
    try { $code = [int]$_.Exception.Response.StatusCode } catch {}
    return @{ ok = $false; status = $code; ms = 0; error = $_.Exception.Message }
  }
}

function Get-CertDaysLeft([string]$HostName) {
  try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $iar = $tcp.BeginConnect($HostName, 443, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne(8000)) { $tcp.Close(); return $null }
    $tcp.EndConnect($iar)
    $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, ({ $true }))
    $ssl.AuthenticateAsClient($HostName)
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ssl.RemoteCertificate)
    $days = [math]::Floor(($cert.NotAfter.ToUniversalTime() - $now).TotalDays)
    $ssl.Close(); $tcp.Close()
    return @{ not_after = $cert.NotAfter.ToUniversalTime().ToString("o"); days_left = [int]$days; subject = $cert.Subject }
  } catch {
    return @{ error = $_.Exception.Message; days_left = $null }
  }
}

function Get-LsMetric([string]$Metric, [string]$Unit, [string[]]$Stats) {
  try {
    $statArgs = @()
    foreach ($s in $Stats) { $statArgs += @("--statistics", $s) }
    $rawJson = & aws lightsail get-instance-metric-data `
      --instance-name $InstanceName `
      --metric-name $Metric `
      --period 3600 `
      --start-time ($start24.ToString("yyyy-MM-ddTHH:mm:ssZ")) `
      --end-time ($now.ToString("yyyy-MM-ddTHH:mm:ssZ")) `
      --unit $Unit `
      @statArgs `
      --region $Region `
      --output json 2>&1
    if ($LASTEXITCODE -ne 0) {
      return @{ available = $false; error = [string]$rawJson }
    }
    $raw = $rawJson | ConvertFrom-Json
    $points = @($raw.metricData)
    if ($points.Count -eq 0) { return @{ available = $false; points = 0 } }
    $avgs = @($points | ForEach-Object { $_.average } | Where-Object { $null -ne $_ })
    $maxs = @($points | ForEach-Object { $_.maximum } | Where-Object { $null -ne $_ })
    $last = $points | Sort-Object { $_.timestamp } | Select-Object -Last 1
    return @{
      available = $true
      last_average = $last.average
      last_maximum = $last.maximum
      period_max = if ($maxs.Count) { ($maxs | Measure-Object -Maximum).Maximum } else { $null }
      period_avg = if ($avgs.Count) { ($avgs | Measure-Object -Average).Average } else { $null }
      points = $points.Count
    }
  } catch {
    return @{ available = $false; error = $_.Exception.Message }
  }
}

function Get-CwLatest([string]$Metric, [int]$Period = 86400) {
  try {
    $raw = aws cloudwatch get-metric-statistics `
      --namespace QMind/Homolog `
      --metric-name $Metric `
      --dimensions Name=Environment,Value=homolog `
      --start-time ($start24.ToString("yyyy-MM-ddTHH:mm:ssZ")) `
      --end-time ($now.ToString("yyyy-MM-ddTHH:mm:ssZ")) `
      --period $Period `
      --statistics Maximum Average `
      --region $Region `
      --output json | ConvertFrom-Json
    $d = @($raw.Datapoints | Sort-Object Timestamp)
    if ($d.Count -eq 0) { return @{ available = $false } }
    return @{
      available = $true
      maximum = $d[-1].Maximum
      average = $d[-1].Average
      timestamp = $d[-1].Timestamp
    }
  } catch {
    return @{ available = $false; error = $_.Exception.Message }
  }
}

# --- Availability ---
$health = Get-HttpStatus "$ApiBase/health"
$ready = Get-HttpStatus "$ApiBase/ready"
$app = Get-HttpStatus "$AppBase/"
$certApi = Get-CertDaysLeft "api.homolog.qmind.com.br"
$certApp = Get-CertDaysLeft "app.homolog.qmind.com.br"

# --- Lightsail metrics ---
$cpu = Get-LsMetric "CPUUtilization" "Percent" @("Average", "Maximum")
$disk = Get-LsMetric "DiskUtilization" "Percent" @("Average", "Maximum")
$status = Get-LsMetric "StatusCheckFailed" "Count" @("Maximum")

# --- Host-emitted CW metrics (from observe-homolog-host.sh) ---
$workerHealthy = Get-CwLatest "WorkerHealthy" 3600
$memUsed = Get-CwLatest "MemUsedPercent" 3600
$diskHost = Get-CwLatest "DiskUsedPercent" 3600
$jobQueued = Get-CwLatest "JobQueuedCount" 3600
$jobRunning = Get-CwLatest "JobRunningCount" 3600
$jobFailed = Get-CwLatest "JobFailed24h" 3600
$jobStuck = Get-CwLatest "JobStuckRunning" 3600
$jobAvgSec = Get-CwLatest "JobAvgSuccessSeconds24h" 3600
$backupOk = Get-CwLatest "BackupSuccess" 86400

# --- Alarms ---
$cwAlarms = @()
try {
  $cwAlarms = @(
    aws cloudwatch describe-alarms --alarm-names qmind-homolog-backup-failed --region $Region --output json |
      ConvertFrom-Json | Select-Object -ExpandProperty MetricAlarms
  )
} catch {}
$lsAlarms = @()
try {
  $lsAlarms = @(
    (aws lightsail get-alarms --region $Region --output json | ConvertFrom-Json).alarms |
      Where-Object { $_.name -like "qmind-homolog-*" }
  )
} catch {}

# --- Cost (tag Project=qmind) ---
$cost = @{ available = $false }
try {
  $endExclusive = $now.Date.AddDays(1).ToString("yyyy-MM-dd")
  $startMonthStr = $startMonthUtc.ToString("yyyy-MM-dd")
  $filter = @{
    Tags = @{
      Key = "Project"
      Values = @("qmind")
    }
  } | ConvertTo-Json -Compress
  $tmpFilter = Join-Path $env:TEMP ("ce-filter-" + [guid]::NewGuid().ToString("N") + ".json")
  Set-Content $tmpFilter -Value $filter -Encoding ascii
  $ce = aws ce get-cost-and-usage `
    --time-period "Start=$startMonthStr,End=$endExclusive" `
    --granularity MONTHLY `
    --metrics UnblendedCost `
    --filter "file://$tmpFilter" `
    --region us-east-1 `
    --output json | ConvertFrom-Json
  Remove-Item $tmpFilter -Force -ErrorAction SilentlyContinue
  $amount = 0.0
  foreach ($r in @($ce.ResultsByTime)) {
    $amount += [double]$r.Total.UnblendedCost.Amount
  }
  # Projected month: scale by day-of-month
  $dom = [math]::Max(1, $now.Day)
  $daysInMonth = [DateTime]::DaysInMonth($now.Year, $now.Month)
  $projected = if ($dom -gt 0) { $amount * ($daysInMonth / $dom) } else { $amount }
  $cost = @{
    available = $true
    month_to_date_usd = [math]::Round($amount, 4)
    projected_month_usd = [math]::Round($projected, 2)
    tag = "Project=qmind"
    note = "Cost Explorer can lag 24h; Lightsail may appear under untagged until CUR/tags activate"
  }
} catch {
  $cost = @{ available = $false; error = $_.Exception.Message }
}

# --- Backup object presence (operator credentials) ---
$backup = @{ available = $false }
if (-not $BackupBucket) {
  try {
    $BackupBucket = (aws s3api list-buckets --output json | ConvertFrom-Json).Buckets |
      Where-Object { $_.Name -like "qmind-homolog-pgdump-*" } |
      Select-Object -First 1 -ExpandProperty Name
  } catch {}
}
if ($BackupBucket) {
  try {
    $objs = aws s3api list-objects-v2 --bucket $BackupBucket --prefix $BackupPrefix --region $Region --output json | ConvertFrom-Json
    $latest = @($objs.Contents | Sort-Object LastModified -Descending | Select-Object -First 1)
    $backup = @{
      available = $true
      bucket = $BackupBucket
      latest_key = if ($latest) { $latest[0].Key } else { $null }
      latest_modified = if ($latest) { $latest[0].LastModified } else { $null }
      object_count_listed = @($objs.Contents).Count
      cw_backup_success = $backupOk
    }
  } catch {
    $backup = @{ available = $false; error = $_.Exception.Message; cw_backup_success = $backupOk }
  }
}

# --- Trigger evaluation ---
$triggers = New-Object System.Collections.ArrayList
function Add-Trigger([string]$Id, [string]$Severity, [string]$Detail) {
  [void]$triggers.Add([ordered]@{ id = $Id; severity = $Severity; detail = $Detail })
}

$diskPct = $null
if ($diskHost.available) { $diskPct = [double]$diskHost.maximum }
elseif ($disk.available -and $disk.period_max) { $diskPct = [double]$disk.period_max }
if ($null -ne $diskPct -and $diskPct -gt 80) {
  Add-Trigger "disk_above_80" "critical" "disk_used_percent=$diskPct"
}

if ($cost.available -and [double]$cost.projected_month_usd -gt 30) {
  Add-Trigger "cost_projected_above_30" "critical" "projected=$($cost.projected_month_usd)"
}

if (-not $backupOk.available -or [double]$backupOk.maximum -lt 1) {
  # Only fire if we are past expected daily window OR no S3 object in 36h
  $backupMissing = $true
  if ($backup.available -and $backup.latest_modified) {
    try {
      $lm = [DateTime]::Parse($backup.latest_modified).ToUniversalTime()
      if (($now - $lm).TotalHours -lt 36) { $backupMissing = $false }
    } catch {}
  }
  if ($backupMissing) {
    Add-Trigger "backup_absent" "critical" "BackupSuccess missing/0 and no fresh S3 object (<36h)"
  }
}

foreach ($a in $cwAlarms) {
  if ($a.StateValue -eq "ALARM") {
    Add-Trigger "cw_alarm" "critical" "$($a.AlarmName)=$($a.StateValue)"
  }
}
foreach ($a in $lsAlarms) {
  if ($a.state -eq "ALARM") {
    Add-Trigger "ls_alarm" "critical" "$($a.name)=$($a.state)"
  }
}

if ($workerHealthy.available -and [double]$workerHealthy.maximum -lt 1) {
  Add-Trigger "worker_unhealthy" "high" "WorkerHealthy=0"
}
if ($jobStuck.available -and [double]$jobStuck.maximum -ge 1) {
  Add-Trigger "jobs_stuck" "critical" "JobStuckRunning=$($jobStuck.maximum)"
}
if ($jobQueued.available -and [double]$jobQueued.maximum -gt 20) {
  Add-Trigger "queue_growth" "high" "JobQueuedCount=$($jobQueued.maximum)"
}

$availFails = 0
if (-not $health.ok) { $availFails++ }
if (-not $ready.ok) { $availFails++ }
if ($availFails -ge 1) {
  Add-Trigger "availability_fail" "high" "health_ok=$($health.ok) ready_ok=$($ready.ok)"
}

if ($certApi.days_left -ne $null -and $certApi.days_left -lt 14) {
  Add-Trigger "https_expiring" "high" "api_days_left=$($certApi.days_left)"
}
if ($certApp.days_left -ne $null -and $certApp.days_left -lt 14) {
  Add-Trigger "https_expiring" "high" "app_days_left=$($certApp.days_left)"
}

$pilotInterrupt = @($triggers | Where-Object { $_.severity -eq "critical" }).Count -gt 0

$report = [ordered]@{
  gate = "011-V8-observation"
  day_utc = $day
  collected_at = $now.ToString("o")
  baseline = [bool]$Baseline
  api_base = $ApiBase
  availability = @{
    health = $health
    ready = $ready
    app = $app
  }
  https = @{
    api = $certApi
    app = $certApp
  }
  lightsail = @{
    instance = $InstanceName
    cpu = $cpu
    disk = $disk
    status_check_failed = $status
  }
  host_metrics_cw = @{
    worker_healthy = $workerHealthy
    mem_used_percent = $memUsed
    disk_used_percent = $diskHost
    job_queued = $jobQueued
    job_running = $jobRunning
    job_failed_24h = $jobFailed
    job_stuck_running = $jobStuck
    job_avg_success_seconds_24h = $jobAvgSec
  }
  cost = $cost
  backup = $backup
  alarms = @{
    cloudwatch = @($cwAlarms | ForEach-Object { @{ name = $_.AlarmName; state = $_.StateValue } })
    lightsail = @($lsAlarms | ForEach-Object { @{ name = $_.name; state = $_.state } })
  }
  triggers = @($triggers)
  pilot_interrupt_recommended = $pilotInterrupt
  notes = @(
    "Observation is post-release monitoring (non-blocking to controlled pilot).",
    "Manual/security triggers (isolation breach, secret exposure) are process-owned, not auto-detected here."
  )
}

$outFile = Join-Path $OutDir ("$day.json")
if ($Baseline) {
  $outFile = Join-Path $OutDir ("BASELINE_$day.json")
}
$json = ($report | ConvertTo-Json -Depth 10)
[IO.File]::WriteAllText($outFile, $json, [Text.UTF8Encoding]::new($false))

# Append to index
$indexPath = Join-Path $OutDir "INDEX.md"
$line = "| $day | cost_mtd=$($cost.month_to_date_usd) proj=$($cost.projected_month_usd) | health=$($health.ok)/ready=$($ready.ok) | worker=$($workerHealthy.maximum) | disk=$diskPct | triggers=$($triggers.Count) | interrupt=$pilotInterrupt |"
if (-not (Test-Path $indexPath)) {
  @(
    "# Observacao 7 dias - indice",
    "",
    "| Dia UTC | Custo | Disponibilidade | Worker | Disco | Triggers | Interrupt |",
    "|---|---|---|---|---|---|---|"
  ) | Set-Content $indexPath -Encoding utf8
}
Add-Content $indexPath $line -Encoding utf8

Write-Host "Wrote $outFile"
Write-Host "triggers=$($triggers.Count) pilot_interrupt_recommended=$pilotInterrupt"
if ($pilotInterrupt) { exit 2 }
exit 0
