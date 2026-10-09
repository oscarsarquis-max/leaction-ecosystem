# Índice de versões — ActionFinance

Atualizado em 09/10/2026 na adoção de AF-BL-023 1.0. Conferências novas substituem linhas; não apagar histórico de implantação encerrada — acrescentar retificação.

## Relações (não misturar)

```text
Prompt 023  →  AF-BL-023 rev 1.0     (requisitos)
Prompt 024  →  controle de versionamento (este índice)
Produto     →  0.1.0 atual           (código + system/info)
Banco       →  Flyway Vn             (última inspect pública: V19 em 05/10/2026)
Implantação →  task / digest / SPA   (ver manifesto de adoção)
```

## Baseline

| ID | Revisão | Data | SHA-256 | Estado |
|---|---|---|---|---|
| AF-BL-023 | 1.0 | 09/10/2026 | `775B9CBD467B5F073FD73A3B01943D5A02E3BF0589B9EE2553B1D0662E20D073` | Vigente |

## Produto

| Versão | Estado | Base | Código | Schema alvo | Implantação | Aceite |
|---|---|---|---|---|---|---|
| 0.1.0 | **Publicada** (identificação já existente no artefato) | Anterior à AF-BL-023; requisitos 023 **não** implementados | Sem tag de release imutável (limite histórico) | V19 no origin na inspect 05/10/2026 | [manifesto de adoção](manifests/AF-0.1.0-published-at-bl023-adoption.md) | Cadastros/Pay: aceite de produto **não** atribuído (REV_017) |
| *(próxima)* | Não atribuída | AF-BL-023 1.0 | — | — | — | — |

Não existe versão 1.0 de produto. `0.1.0` é a convenção desde a fundação (`pom.xml`, `package.json`, `actionfinance.app.version`).

## Banco (repositório)

Sequência intacta: `V1` … `V20`. `V20` é migration de 019 (identidade comercial do recibo), **não** versão 20 do produto. Checksums: não reiniciar, não renomear aplicadas.

Última inspect pública do origin: Flyway **1–19** (05/10/2026, REV_017). Este ciclo **não** relê o RDS.

## Implantação vigente conferida em 09/10/2026

| Peça | Valor conferido |
|---|---|
| Host | `https://actionfinance.actionhub.com.br/` HTML 200 |
| SPA | `index-BYEiixeg.js` |
| `GET /api/v1/system/info` | `version=0.1.0`, `stage=FOUNDATION`, `accessMode=OIDC`, `receiptSyncEnabled=true`, `spiderIntegrationStatus=RECEIPT_SYNC` |
| Task definition / digest ECS | **Não reinspecionados** neste ciclo (último relato: `actionfinance-web:12` / digest `9b90e339…` em 05/10/2026) |

## Compatibilidade referenciada (não é a mesma versão)

| Componente | Nesta adoção | Nota |
|---|---|---|
| ActionFinance | produto 0.1.0 | — |
| Spider | próprio | LIST/LOOKUP Pay; sem relatório MP |
| ActionHub | próprio | LIST de cobranças ≠ extrato |
