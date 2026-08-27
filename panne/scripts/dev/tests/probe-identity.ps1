#Requires -Version 5.1
. (Join-Path $PSScriptRoot "..\demo-lifecycle.ps1")
$Root = Get-PanneDemoRoot (Join-Path $PSScriptRoot "..")
foreach ($pidVal in @(42328, 53712)) {
    $id = Get-ProcessIdentity -ProcessId $pidVal
    if ($null -eq $id) {
        Write-Host "PID $pidVal ausente"
        continue
    }
    Write-Host "PID=$($id.Pid) Name=$($id.Name)"
    Write-Host "Path=$($id.Path)"
    Write-Host "Cmd=$($id.CommandSafe)"
    Write-Host "Panne=$(Test-PanneDemoProcessIdentity -Identity $id -Root $Root)"
    Write-Host "---"
}
