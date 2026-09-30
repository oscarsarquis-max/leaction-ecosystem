#Requires -Version 5.1
[CmdletBinding()]
param(
  [Parameter(ParameterSetName = "jdbc", Mandatory = $true)][string] $JdbcUrl,
  [Parameter(ParameterSetName = "jdbc", Mandatory = $true)][string] $RuntimeUser,
  [Parameter(ParameterSetName = "jdbc", Mandatory = $true)][string] $RuntimePassword,
  [Parameter(ParameterSetName = "container", Mandatory = $true)][string] $ContainerName,
  [Parameter(ParameterSetName = "container")][string] $ContainerUser = "actionfinance_runtime",
  [Parameter(ParameterSetName = "container")][string] $ContainerPassword
)

$ErrorActionPreference = "Stop"
# After an operational restore, invalidate application sessions and keep financial rows and audit.
Write-Host "This command deletes actionfinance.SPRING_SESSION rows only. Financial facts and access_admin_audit stay."

if ($PSCmdlet.ParameterSetName -eq "container") {
  $args = @("exec")
  if ($ContainerPassword) {
    $args += @("-e", "PGPASSWORD=$ContainerPassword")
  }
  $args += @(
    $ContainerName, "psql", "-v", "ON_ERROR_STOP=1", "-U", $ContainerUser, "-d", "actionfinance",
    "-c", "delete from actionfinance.SPRING_SESSION;"
  )
  & docker @args
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  return
}

$env:PGPASSWORD = $RuntimePassword
try {
  psql $JdbcUrl.Replace('jdbc:', '') -U $RuntimeUser -c "delete from actionfinance.SPRING_SESSION;"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
