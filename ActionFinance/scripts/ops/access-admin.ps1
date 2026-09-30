#Requires -Version 5.1
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [ValidateSet("bootstrap-org", "provision", "revoke", "block", "unblock")]
  [string] $Command,
  [string] $TenantCode,
  [string] $TenantName,
  [string] $CompanyCode,
  [string] $CompanyName,
  [string] $Timezone = "America/Sao_Paulo",
  [string] $ResponsibleName,
  [string] $DisplayName,
  [string] $Issuer,
  [string] $Subject,
  [string] $TenantId,
  [string] $CompanyId,
  [ValidateSet("VIEWER", "OPERATOR")]
  [string] $Role,
  [string] $UserId,
  [Parameter(Mandatory = $true)]
  [string] $Reason,
  [string] $Executor = "access-admin",
  [switch] $DryRun
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$forward = [System.Collections.Generic.List[string]]::new()
$forward.Add($Command)
if ($DryRun) { $forward.Add("--dry-run") }
$forward.Add("--reason=$Reason")
$forward.Add("--executor=$Executor")
if ($DisplayName) { $forward.Add("--display-name=$DisplayName") }
if ($Issuer) { $forward.Add("--issuer=$Issuer") }
if ($Subject) { $forward.Add("--subject=$Subject") }
if ($TenantId) { $forward.Add("--tenant-id=$TenantId") }
if ($CompanyId) { $forward.Add("--company-id=$CompanyId") }
if ($Role) { $forward.Add("--role=$Role") }
if ($UserId) { $forward.Add("--user-id=$UserId") }
if ($TenantCode) { $forward.Add("--tenant-code=$TenantCode") }
if ($TenantName) { $forward.Add("--tenant-name=$TenantName") }
if ($CompanyCode) { $forward.Add("--company-code=$CompanyCode") }
if ($CompanyName) { $forward.Add("--company-name=$CompanyName") }
if ($Timezone) { $forward.Add("--timezone=$Timezone") }
if ($ResponsibleName) { $forward.Add("--responsible-name=$ResponsibleName") }

Set-Location (Join-Path $root "backend")
$joined = $forward -join " "
& .\mvnw spring-boot:run "-Dspring-boot.run.profiles=access-admin" "-Dspring-boot.run.arguments=$joined"
