# Invite a real operator into the Spider sandbox Monitor group.
# Do not put the email or password in Terraform, state, or reports.
# email_verified=true is required because the pool uses email as username;
# hosted UI will not complete FORCE_CHANGE_PASSWORD until the address is verified.
# That flag does not replace Cognito EMAIL delivery of the temporary password.
# Usage: .\invite-monitor-operator.ps1 -UserPoolId us-east-2_xxx -Email person@example.com

param(
  [Parameter(Mandatory = $true)][string]$UserPoolId,
  [Parameter(Mandatory = $true)][string]$Email,
  [string]$GroupName = "spider-sandbox-operators",
  [string]$Region = "us-east-2"
)

$ErrorActionPreference = "Stop"
$username = aws cognito-idp admin-create-user `
  --user-pool-id $UserPoolId `
  --username $Email `
  --user-attributes "Name=email,Value=$Email" "Name=email_verified,Value=true" `
  --desired-delivery-mediums EMAIL `
  --region $Region `
  --query "User.Username" `
  --output text

if (-not $username) {
  throw "User was not created"
}

aws cognito-idp admin-add-user-to-group `
  --user-pool-id $UserPoolId `
  --username $username `
  --group-name $GroupName `
  --region $Region | Out-Null

Write-Output "Operator invited. Temporary password was sent by Cognito email, not printed here."
