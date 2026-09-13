# SegSense Insurance Provider Mock

Aplicação **irmã independente**. Não pertence à Spider nem ao SegSense. Porta padrão **8095**, bind **127.0.0.1**.

Isto **não** é sandbox Icatu nem um “Provider Satellite” certificado. `providerId=SEGSENSE_PROVIDER_MOCK`, `origin=ILLUSTRATIVE_NOT_ICATU_CONTRACT`.

Somente a Spider deve chamar `POST /v1/illustrative-protection-items`.

O processo **não inicia** sem `SEGSENSE_MOCK_CREDENTIAL` no ambiente. Não há default versionado. Gere o material com `segsense/scripts/setup-mvp-demo-secrets.ps1` e não imprima o valor.

Contrato: `documents/SEGSENSE_MOCK_CONTRACT_001.md` (cópia do contrato em `segsense/documents/`).

```powershell
# SEGSENSE_MOCK_CREDENTIAL already in the session (do not echo it)
$env:PORT=8095
node server.js
```
