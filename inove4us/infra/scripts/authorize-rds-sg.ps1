# Fallback AWS CLI caso o Terraform da regra RDS ainda não tenha sido aplicado.
# Libera TCP 5432 no SG do Postgres SOMENTE a partir do SG das tasks inove4us.
param(
  [Parameter(Mandatory = $true)][string]$RdsSecurityGroupId,
  [Parameter(Mandatory = $true)][string]$Inove4usTasksSecurityGroupId,
  [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Stop"

Write-Host "Autorizando $RdsSecurityGroupId <- $Inove4usTasksSecurityGroupId :5432"

aws ec2 authorize-security-group-ingress `
  --region $Region `
  --group-id $RdsSecurityGroupId `
  --ip-permissions "IpProtocol=tcp,FromPort=5432,ToPort=5432,UserIdGroupPairs=[{GroupId=$Inove4usTasksSecurityGroupId,Description='inove4us ECS Fargate'}]"

Write-Host "OK. Verifique:"
aws ec2 describe-security-groups --region $Region --group-ids $RdsSecurityGroupId `
  --query "SecurityGroups[0].IpPermissions[?FromPort==``5432``]" --output table
