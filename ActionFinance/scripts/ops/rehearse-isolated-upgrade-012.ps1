#Requires -Version 5.1
# Isolated restore/upgrade rehearsal. Refuses the public RDS.
# PartyDirectoryIT uses its own Testcontainer and does not prove a restored copy.
[CmdletBinding()]
param(
  [string]$JdbcUrl = $env:AF_REHEARSAL_JDBC_URL,
  [switch]$CompareOnly
)

$ErrorActionPreference = "Stop"
$publicHosts = @(
  "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com",
  "rds.amazonaws.com"
)

function Assert-IsolatedJdbc([string]$url) {
  if (-not $url) {
    throw "Set AF_REHEARSAL_JDBC_URL or -JdbcUrl to an isolated database. This script does not connect to the public RDS."
  }
  foreach ($marker in $publicHosts) {
    if ($url.ToLowerInvariant().Contains($marker.ToLowerInvariant())) {
      throw "Refused: URL points to the public destination ($marker). Restore/upgrade only on an isolated database."
    }
  }
}

Write-Host "ACTIONFINANCE_REHEARSAL_012 isolated-only"
Write-Host "PartyDirectoryIT uses Testcontainer and does NOT prove a restored copy."
Write-Host "Proven steps require an explicit isolated JDBC URL:"
Write-Host "  1. Stop writes (agreed window/RPO). No productive restore authorization here."
Write-Host "  2. pg_dump schema actionfinance on the origin (read-only)."
Write-Host "  3. Restore the dump on an isolated instance. Never overwrite production as routine."
Write-Host "  4. Capture later writes (CDC/log) before any destination switch."
Write-Host "  5. flyway migrate to V19 on the isolated copy. Do not edit already-versioned V14/V15/V16."
Write-Host "  6. Check flyway_schema_history, financial_title FKs, grants and connection_key NOT NULL."
Write-Host "  7. Run invariant SQL on the COPY. Do not treat PartyDirectoryIT as proof of that copy."
Write-Host "  8. INSERT with V2 columns proves that SQL shape still works. It does NOT prove rollback of the previous image."
Write-Host "Preferred rollback proof: boot the previous effective artifact against the expanded schema in isolation; check Flyway, read/write of {name,role}, and new fields after an old-flow edit."
Write-Host "This script does not pull or run a previous image. Restore remains unauthorized here."

Assert-IsolatedJdbc $JdbcUrl
if ($CompareOnly) {
  Write-Host "CompareOnly: isolated URL accepted. No migration executed."
  exit 0
}

Write-Host "This prompt does not run migrate. With an authorized isolated JDBC, the operator runs flyway and invariant SQL."
exit 0
