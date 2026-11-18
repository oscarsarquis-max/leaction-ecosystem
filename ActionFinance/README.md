# ActionFinance

Gestão financeira do grupo além do recebimento de assinaturas do ActionHub. Satélite EXPERIENCE candidato: frontend e backend próprios, regras próprias, PostgreSQL próprio. Não é tela do Hub, ledger da Spider nem estoque do Panne.

| Campo | Valor |
|---|---|
| Produto | **0.2.11** |
| Schema | **V25** |
| Publicado em | https://actionfinance.actionhub.com.br |
| Data de referência | 09/11/2026 ([REV_055](documents/reviews/ACTIONFINANCE_REV_ESTADO_PUBLICADO_055.md)) |
| Task | `actionfinance-web:28`; retorno 0.2.10 em `actionfinance-web:27` |
| Destino | `C:\Projetos\ActionFinance` |
| Repositório | monorepo Git de `C:\Projetos` (sem Git aninhado) |
| Backend | Java 21, Spring Boot 3.4.2 |

Histórico do domínio: `finaction.com.br` foi o domínio planejado, com registro confirmado pelo proprietário ([DOMINIO_001](documents/architecture/ACTIONFINANCE_DOMINIO_001.md)). O host publicado é `actionfinance.actionhub.com.br`.

**Substituído em 09/11/2026 — ver [REV_055](documents/reviews/ACTIONFINANCE_REV_ESTADO_PUBLICADO_055.md).** O bloco abaixo era o estado da fundação e permanece no arquivo.

| Campo | Valor |
|---|---|
| Estado | **FOUNDATION** local + acesso OIDC preparado (PRM_006). Sem publicação do host público |
| Aplicação executável | Backend Java em `127.0.0.1:8091`; UI de diagnóstico em `127.0.0.1:5179` |
| Destino | `C:\Projetos\ActionFinance` |
| Repositório | monorepo Git de `C:\Projetos` (sem Git aninhado) |
| Identidade técnica candidata | `actionfinance` |
| Papel desejado | EXPERIENCE — manifesto preliminar `DRAFT/NOT_CERTIFIED`, `executable=false`, `acceptedBySpider=false` |
| Domínio planejado | `finaction.com.br` (registro confirmado; DNS/TLS não verificados) |
| Backend | Java 21, Spring Boot 3.4.2 |
| Primeira fatia planejada | Contas a pagar fictícias, sem pagamento — **não implementada** |

Índice: [`documents/README.md`](documents/README.md).  
Fundação obtida: [`documents/architecture/ACTIONFINANCE_FND_001.md`](documents/architecture/ACTIONFINANCE_FND_001.md).  
Operação: [`documents/operations/ACTIONFINANCE_RUN_001.md`](documents/operations/ACTIONFINANCE_RUN_001.md).

## Subir localmente

```powershell
cd C:\Projetos\ActionFinance
.\scripts\dev\setup-local.ps1
.\scripts\dev\start-local.ps1
```

Abrir http://127.0.0.1:5179/ (situação da fundação) e http://127.0.0.1:8091/api/v1/system/info.

Não execute `git init` aqui. Sem commit, push ou deploy neste ciclo.
