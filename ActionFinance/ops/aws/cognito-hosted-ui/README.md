# Hosted UI clássico do ActionFinance — cliente Finance

Escopo: app client confidencial do pool Finance (`actionfinance-confidential`, fluxo code). Domínio de prefixo `actionfinance-253137917703.auth.us-east-2.amazoncognito.com`. Sem managed login, sem troca de plano, sem `ClientId=ALL`.

## Autorização

A personalização clássica neste client foi autorizada em 02/10/2026 para alinhar o formulário público à faixa azul e à marca branca. [PRM_007_AUTORIZACAO](../../documents/prompts/ACTIONFINANCE_PRM_007_AUTORIZACAO.md) continua a cobrir pool/OIDC/primeiro operador; este pacote não altera outros clients nem o Hosted UI do Hub, Monitor ou Panne.

## Artefatos

| Arquivo | Papel |
|---|---|
| `hosted-ui-classic.css` | Só classes documentadas (banner, logo, fundo, campos, botão) |
| `logo-hosted-ui.png` | Recorte do `actionfinance-blue.png` oficial (≤100 KB, 350×178, campo `#1603AD`) |
| `make-logo.py` | Regenera o recorte a partir do asset oficial |
| `apply-hosted-ui.ps1` | Snapshot + `SetUICustomization` só no client Finance |
| `rollback-hosted-ui.ps1` | Restaura `snapshot-atual.json` |
| `snapshot-atual.json` | `GetUICustomization` imediatamente antes do apply |

## Apply

```powershell
cd C:\Projetos\ActionFinance\ops\aws\cognito-hosted-ui
python make-logo.py
.\apply-hosted-ui.ps1            # dry-run: resolve pool/client e grava snapshot
.\apply-hosted-ui.ps1 -Apply     # escreve CSS + logo neste client
```

Rollback:

```powershell
.\rollback-hosted-ui.ps1         # dry-run
.\rollback-hosted-ui.ps1 -Apply
```

## Limites do Cognito clássico

O Hosted UI clássico não aceita HTML livre. A marca entra como imagem centrada acima dos campos, não como lettering vazado na faixa. Os rótulos permanecem os do Cognito (`Username` / `Password`, ou a tradução que o serviço escolher). Recuperação e MFA usam as páginas nativas do mesmo estilo. Essas diferenças são impostas pelo produto, não por uma tela local fictícia.
