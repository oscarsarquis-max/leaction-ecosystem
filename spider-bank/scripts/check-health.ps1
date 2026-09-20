$ErrorActionPreference = 'Stop'
function Show-Check([string]$Name, [string]$Url) {
  try {
    $req = [System.Net.HttpWebRequest]::Create($Url)
    $req.Timeout = 2000
    $req.ProtocolVersion = [Version]'1.1'
    $resp = $req.GetResponse()
    $code = [int]$resp.StatusCode
    $resp.Close()
    Write-Output "OK $Name $code $Url"
  } catch {
    Write-Output "FAIL $Name $Url $($_.Exception.Message)"
  }
}
Show-Check 'spider-engine' 'http://127.0.0.1:8080/actuator/health'
Show-Check 'spider-monitor' 'http://127.0.0.1:5180/'
Show-Check 'spiderbank-bff' 'http://127.0.0.1:8090/api/health'
Show-Check 'spiderbank-fe' 'http://127.0.0.1:5190/'
Show-Check 'credit-mock' 'http://127.0.0.1:8096/health'
Write-Output "Supported shell: Windows PowerShell 5.1+"
Write-Output "spiderbank product URL is http://127.0.0.1:5190/ — not Monitor /spiderbank"
Write-Output "Mock /health is process evidence only; chain readiness is determined by Spider."
