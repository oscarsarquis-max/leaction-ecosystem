# Restricts a local secrets file to the current user, SYSTEM and Administrators.
# Does not print file contents.
$ErrorActionPreference = 'Stop'

function Test-MvpRestrictedAcl {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return $false
  }
  $acl = Get-Acl -LiteralPath $Path
  if (-not $acl.AreAccessRulesProtected) {
    return $false
  }
  $allowed = @(
    [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value,
    'S-1-5-18',
    'S-1-5-32-544'
  )
  foreach ($rule in $acl.Access) {
    $sid = $null
    try {
      $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
    } catch {
      return $false
    }
    if ($allowed -notcontains $sid) {
      return $false
    }
  }
  return $true
}

function Set-MvpRestrictedAcl {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Missing $Path"
  }
  $userSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
  $grant = @(
    "/inheritance:r",
    "/grant:r", "*${userSid}:M",
    "/grant:r", "*S-1-5-18:F",
    "/grant:r", "*S-1-5-32-544:F"
  )
  $output = & icacls $Path @grant 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "icacls failed to restrict ACL on secrets file (exit $LASTEXITCODE)."
  }
  if (-not (Test-MvpRestrictedAcl -Path $Path)) {
    throw "Secrets file ACL is not restricted to the current user, SYSTEM and Administrators. This machine is not ready as a shared computer."
  }
}
