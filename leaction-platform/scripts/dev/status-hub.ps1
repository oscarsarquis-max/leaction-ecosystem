# Status dos servicos locais do Action Hub.
# Uso: .\scripts\dev\status-hub.ps1

. "$PSScriptRoot\_hub-dev-common.ps1"

$checks = @(
    @{ Name = 'Postgres'; Kind = 'tcp'; Port = (Get-DatabaseHostPortFromUrl (Get-HubDatabaseUrl)).Port; Host = '127.0.0.1' },
    @{ Name = 'Gateway'; Kind = 'http'; Url = 'http://127.0.0.1:4001/health' },
    @{ Name = 'Marketplace'; Kind = 'http'; Url = 'http://127.0.0.1:4012/api/marketplace/health' },
    @{ Name = 'Action Hub FE'; Kind = 'http'; Url = 'http://127.0.0.1:4000/api/health' },
    @{ Name = 'Curation API'; Kind = 'http'; Url = 'http://127.0.0.1:4012/api/marketplace/curation'; Accept = @(200, 401) }
)

$failed = 0
foreach ($c in $checks) {
    if ($c.Kind -eq 'tcp') {
        $ok = Test-TcpPortOpen -HostName $c.Host -Port $c.Port
        if ($ok) { Write-HubOk "$($c.Name) :$($c.Port) listening" }
        else { Write-HubErr "$($c.Name) :$($c.Port) down"; $failed++ }
        continue
    }

    $accept = if ($c.Accept) { $c.Accept } else { @(200) }
    try {
        $resp = Invoke-WebRequest -Uri $c.Url -UseBasicParsing -TimeoutSec 3
        $code = [int]$resp.StatusCode
        if ($accept -contains $code) {
            Write-HubOk "$($c.Name) HTTP $code  $($c.Url)"
        } else {
            Write-HubErr "$($c.Name) HTTP $code  $($c.Url)"
            $failed++
        }
    } catch {
        $code = $null
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        if ($code -and ($accept -contains $code)) {
            Write-HubOk "$($c.Name) HTTP $code  $($c.Url)"
        } else {
            $msg = $_.Exception.Message
            Write-HubErr "$($c.Name) FAIL  $($c.Url) - $msg"
            $failed++
        }
    }
}

if ($failed -gt 0) {
    Write-HubErr "$failed check(s) falharam. Rode: .\scripts\dev\start-hub.ps1"
    exit 1
}

Write-HubOk "Todos os checks passaram."
exit 0
