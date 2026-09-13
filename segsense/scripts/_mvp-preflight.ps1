# Identity preflight helpers. Dot-source only. Does not print secrets. Does not kill processes.
$ErrorActionPreference = 'Stop'

function Get-HttpStatus {
  param([string]$Method, [string]$Url, [hashtable]$Headers = @{}, [string]$Body = $null)
  try {
    $params = @{
      Uri = $Url
      Method = $Method
      UseBasicParsing = $true
      TimeoutSec = 5
      Headers = $Headers
    }
    if ($null -ne $Body) {
      $params.ContentType = 'application/json'
      $params.Body = $Body
    }
    Invoke-WebRequest @params | Out-Null
    return 200
  } catch {
    $response = $_.Exception.Response
    if ($response -and $response.StatusCode) {
      return [int]$response.StatusCode.value__
    }
    throw
  }
}

function Get-MvpMockBase { if ($env:MVP_MOCK_BASE_URL) { $env:MVP_MOCK_BASE_URL } else { 'http://127.0.0.1:8095' } }
function Get-MvpSpiderBase { if ($env:MVP_SPIDER_BASE_URL) { $env:MVP_SPIDER_BASE_URL } else { 'http://127.0.0.1:8080' } }
function Get-MvpSegSenseBase { if ($env:MVP_SEGSENSE_BASE_URL) { $env:MVP_SEGSENSE_BASE_URL } else { 'http://127.0.0.1:8088' } }

function Test-MvpMockIdentity {
  $base = Get-MvpMockBase
  $health = Invoke-RestMethod "$base/health"
  if ($health.testDouble -ne $true -or $health.satelliteRole -ne 'PROVIDER_TEST_DOUBLE') {
    throw "Mock endpoint is occupied by a process that is not the Insurance Provider Mock Test Double. Will not replace it."
  }
  $status = Get-HttpStatus -Method POST -Url "$base/v1/provider/capabilities/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/executions" -Body '{}'
  if ($status -ne 401) {
    throw "Mock provider contract did not require authentication (status=$status)."
  }
}

function Test-MvpSpiderSatelliteAuth {
  $base = Get-MvpSpiderBase
  $health = Invoke-RestMethod "$base/actuator/health"
  if ($health.status -ne 'UP') {
    throw "Spider health is not UP."
  }
  $status = Get-HttpStatus -Method POST -Url "$base/v1/satellites/interactions" -Body '{}'
  if ($status -eq 404) {
    throw "This HTTP process does not expose Satellite Contract V1. Will not replace it."
  }
  if ($status -ne 401) {
    throw "Spider satellite endpoint did not require satellite authentication (status=$status)."
  }
}

function Test-MvpSegSenseIdentity {
  $base = Get-MvpSegSenseBase
  $info = Invoke-RestMethod "$base/api/v1/system/info"
  if ($info.applicationId -ne 'SEGSENSE') {
    throw "This HTTP process is not SegSense (applicationId mismatch). Will not replace it."
  }
}

function Invoke-MvpPreflight {
  Test-MvpMockIdentity
  Test-MvpSpiderSatelliteAuth
  Test-MvpSegSenseIdentity
  Write-Output 'preflight=ok mock=TEST_DOUBLE spider=SATELLITE_CONTRACT_V1 segsense=SEGSENSE'
}
