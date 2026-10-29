#Requires -Version 5.1
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string] $UserPoolId,
  [Parameter(Mandatory = $true)][string] $Username,
  [Parameter(Mandatory = $true)][string] $ContactEmail,
  [switch] $SendInvite
)

$ErrorActionPreference = "Stop"
if ($ContactEmail -match '@(actionhub|lojadepaes)\.com\.br$') {
  Write-Error "Refusing to use a login-only or product mailbox as the contact destination."
  exit 2
}

$createArgs = @(
  "cognito-idp", "admin-create-user",
  "--region", "us-east-2",
  "--user-pool-id", $UserPoolId,
  "--username", $Username,
  "--user-attributes", "Name=email,Value=$ContactEmail"
)
if ($SendInvite) {
  Write-Host "Invite/verification will be sent only to the configured contact email attribute."
} else {
  $createArgs += @("--message-action", "SUPPRESS")
}

aws @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Cognito user prepared. Username is the login identifier; contact email is a separate attribute (not marked verified here)."
Write-Host "Next: first login on the hosted UI, then provision OPERATOR with issuer+subject."
