# Índice de versões — ActionFinance

Atualizado em 09/10/2026 na adoção de AF-BL-023 1.0. Conferências novas substituem linhas; não apagar histórico de implantação encerrada — acrescentar retificação.

## Relações (não misturar)

```text
Prompt 023  →  AF-BL-023 rev 1.0     (requisitos)
Prompt 024  →  controle de versionamento (este índice)
Produto     →  publicada anterior     (0.2.0 é candidata de laboratório, não servida)
Banco       →  Flyway Vn             (origin em V20; V21 e V22 no repositório, não no RDS)
Implantação →  task / digest / SPA   (ver manifesto de adoção)
```

## Baseline

| ID | Revisão | Data | SHA-256 | Estado |
|---|---|---|---|---|
| AF-BL-023 | 1.0 | 09/10/2026 | `775B9CBD467B5F073FD73A3B01943D5A02E3BF0589B9EE2553B1D0662E20D073` | Histórico |
| AF-BL-023 | 1.1 | 15/10/2026 | `D372E02C83202FB820A6277073AAABFDBD7F07BB56D17B89593A7BBD602AE986` | Orientação de execução vigente. Não é versão de produto |
| Proposta 026 | — | 15/10/2026 | — | Contrato proposto, não aprovado e não publicado. [Proposta](../architecture/ACTIONFINANCE_PROPOSTA_CONTRATOS_FINANCEIROS_026.md) · [Regressão](../architecture/ACTIONFINANCE_MATRIZ_REGRESSAO_CONTRATOS_026.md) |

## Produto

| Versão | Estado | Base | Código | Schema alvo | Implantação | Aceite |
|---|---|---|---|---|---|---|
| 0.1.0 | Publicada até 15/10/2026 | Anterior à AF-BL-023; requisitos 023 **não** implementados | Sem tag de release imutável (limite histórico) | V19 no origin na inspect 05/10/2026; V20 depois, sem troca de produto | [manifesto de adoção](manifests/AF-0.1.0-published-at-bl023-adoption.md) | Cadastros/Pay: aceite de produto **não** atribuído (REV_017) |
| 0.1.1 | **Publicada** em 15/10/2026 | AF-BL-023 1.1, recorte de recebimentos do Prompt 027 | Sem tag Git neste manifesto | V20, sem migration nova | [manifesto 0.1.1](manifests/AF-0.1.1-enriquecimento-recebimentos-027.md) | Aceite **não** atribuído. Clique autenticado **não** executado |
| 0.2.0 | Candidata em 15/10/2026. Não publicada | AF-BL-023 1.2, extrato T1 dos Prompts 029, 030 e 031. Relatório real lido; carga produtiva não feita | Sem tag Git | V21 e V22 no repositório; origin permanece V20 | [manifesto 0.2.0](manifests/AF-0.2.0-extrato-t1-029.md) | Aceite **não** atribuído |

Não existe versão 1.0 de produto. `0.1.0` é a convenção desde a fundação (`pom.xml`, `package.json`, `actionfinance.app.version`).

## Banco (repositório)

Sequência no repositório: `V1` … `V22`. `V20` é migration de 019 (identidade comercial do recibo), **não** versão 20 do produto. `V21` é a observação de extrato. `V22` admite o perfil do relatório de liquidação ao lado do CSV de laboratório. Nenhuma das duas foi aplicada no origin. Checksums: não reiniciar, não renomear aplicadas.

Inspect de 05/10/2026 (REV_017): Flyway **1–19**. Retificação 15/10/2026: origin em Flyway **1–20**, checksum V20 `-145522935`. Produto permanece **0.1.0**. Relato: [REV_025](../reviews/ACTIONFINANCE_REV_FECHAMENTO_SINCRONIZACAO_025.md).

## Implantação vigente conferida em 09/10/2026

| Peça | Valor conferido |
|---|---|
| Host | `https://actionfinance.actionhub.com.br/` HTML 200 |
| SPA | `index-BYEiixeg.js` |
| `GET /api/v1/system/info` | `version=0.1.0`, `stage=FOUNDATION`, `accessMode=OIDC`, `receiptSyncEnabled=true`, `spiderIntegrationStatus=RECEIPT_SYNC` |
| Task definition / digest ECS | **Não reinspecionados** neste ciclo (último relato: `actionfinance-web:12` / digest `9b90e339…` em 05/10/2026) |

Retificação 15/10/2026: produto servido **0.1.1**, task `actionfinance-web:15`, SPA `index-UhuYx_ma.js`. O registro de 09/10 permanece histórico.

## Compatibilidade referenciada (não é a mesma versão)

| Componente | Nesta adoção | Nota |
|---|---|---|
| ActionFinance | produto 0.1.0 | — |
| Spider | próprio | LIST/LOOKUP Pay; sem relatório MP |
| ActionHub | próprio | LIST de cobranças ≠ extrato |
