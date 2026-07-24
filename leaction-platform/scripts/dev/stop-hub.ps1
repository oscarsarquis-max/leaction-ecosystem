# Para Action Hub local (Next :4000, Gateway :4001, Marketplace :4012).
# Uso: .\scripts\dev\stop-hub.ps1

. "$PSScriptRoot\_hub-dev-common.ps1"

Write-HubInfo "Parando servicos do Action Hub..."
Stop-PortListeners -Ports $script:HubPorts
Write-HubOk "Portas 4000 / 4001 / 4012 liberadas."
