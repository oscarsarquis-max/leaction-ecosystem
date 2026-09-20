#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
try {
  $req = [System.Net.HttpWebRequest]::Create('http://127.0.0.1:8096/health')
  $req.Timeout = 2000
  $req.ProtocolVersion = [Version]'1.1'
  $resp = $req.GetResponse()
  $code = [int]$resp.StatusCode
  $resp.Close()
  Write-Output "OK credit-mock $code http://127.0.0.1:8096/health"
} catch {
  Write-Output "FAIL credit-mock http://127.0.0.1:8096/health $($_.Exception.Message)"
}
Write-Output "Supported shell: Windows PowerShell 5.1+. Health is process evidence, not Spider chain readiness."
