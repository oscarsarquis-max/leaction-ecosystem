# Deletes only demo journey rows. Does not drop other SegSense data.
$env:PGPASSWORD = $env:SEGSENSE_DATASOURCE_PASSWORD
if (-not $env:PGPASSWORD) { $env:PGPASSWORD = 'segsense_local_dev' }
$psql = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psql) {
  Write-Output 'psql not in PATH. Delete segsense.demo_protection_journey manually if needed.'
  exit 0
}
& psql -h 127.0.0.1 -p 5437 -U segsense -d segsense -c "TRUNCATE segsense.demo_protection_journey;"
Write-Output 'Demo journeys truncated. Spider local-demo memory resets on process restart.'
