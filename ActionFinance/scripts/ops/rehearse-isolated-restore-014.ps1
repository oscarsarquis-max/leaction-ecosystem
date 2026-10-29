#Requires -Version 5.1
# Pre-publication procedure for a restored copy of the public origin.
# This prompt does not authorize a productive restore or paid infrastructure.
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
    throw "Set AF_REHEARSAL_JDBC_URL to an isolated database. This script refuses the public RDS."
  }
  foreach ($marker in $publicHosts) {
    if ($url.ToLowerInvariant().Contains($marker.ToLowerInvariant())) {
      throw "Refused: URL points to the public destination ($marker)."
    }
  }
}

Write-Host "ACTIONFINANCE_REHEARSAL_014 prints instructions only. Executable synthetic rehearsal: rehearse-isolated-restore-015.ps1 -Synthetic"
Write-Host "Dump protection: treat the dump as production data; store only on the isolated host; no copy to laptops or chat."
Write-Host "Destination: a disposable Postgres that is not the public RDS and not the developer volume actionfinance_pgdata_17."
Write-Host "Exact steps after authorization and access to a read-only dump:"
Write-Host "  1. Freeze writes on origin only if a destination switch is later approved. Record RPO. Not authorized now."
Write-Host "  2. pg_dump --schema=actionfinance --format=custom --file=actionfinance-origin-v13.dump using a read-only role."
Write-Host "  3. Copy the dump to the isolated host over a private channel. Checksum SHA-256 at source and destination."
Write-Host "  4. pg_restore into an empty isolated database. Never restore over the origin."
Write-Host "  5. flyway migrate to V19. Do not edit V14-V16. Confirm V13 checksum 728072343 remains."
Write-Host "  6. Invariants on the COPY only:"
Write-Host "     - flyway_schema_history versions 1-19 success"
Write-Host "     - count and ids of financial_title.counterparty_id still resolve"
Write-Host "     - counterparties without document stay document_pending"
Write-Host "     - counterparty_document_claim covers person and unit identities; collisions RAISE"
Write-Host "     - connection_key NOT NULL; address composite FK"
Write-Host "  7. Optional: point a disposable API at that JDBC. Do not use PartyDirectoryIT as proof of this copy."
Write-Host "This script does not dump, restore or migrate."

Assert-IsolatedJdbc $JdbcUrl
if ($CompareOnly) {
  Write-Host "CompareOnly: isolated URL accepted. No dump or migrate."
  exit 0
}

Write-Host "No migrate in this prompt. Operator runs dump/restore only with later authorization."
exit 0
