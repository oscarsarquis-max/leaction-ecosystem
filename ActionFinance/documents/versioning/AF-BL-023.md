# AF-BL-023 — Baseline de requisitos

| Campo | Valor |
|---|---|
| Identificador | AF-BL-023 |
| Revisão | **1.0** |
| Data da decisão | 09/10/2026 |
| Autoria da decisão | Proprietário do produto |
| Prompt de origem | ACTIONFINANCE_PROMPT_TESOURARIA_MP_023 |
| Arquivo canônico (não reescrito) | [prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md](../prompts/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md) |
| Cópia imutável desta revisão | [baselines/AF-BL-023/1.0/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md](baselines/AF-BL-023/1.0/ACTIONFINANCE_PROMPT_TESOURARIA_MP_023.md) |
| SHA-256 (SHA256, arquivo UTF-8) | `775B9CBD467B5F073FD73A3B01943D5A02E3BF0589B9EE2553B1D0662E20D073` |
| Tamanho do arquivo na adoção | 8653 bytes |
| Projeto executivo associado | [ACTIONFINANCE_PROJETO_TESOURARIA_MP_023](../architecture/ACTIONFINANCE_PROJETO_TESOURARIA_MP_023.md) — **não** faz parte do texto aprovado do prompt; não altera o hash |

Esta revisão **identifica requisitos**. Não afirma que tesouraria, conciliação ou posição de caixa estejam implementadas.

Mudança futura da baseline: novo prompt, nova revisão (1.1+), hash próprio, diferença explícita em relação a 1.0. Não editar o arquivo da 1.0.

## Pendências vinculadas (abertas)

Não encerradas por esta baseline.

| Pendência | Prompt / evidência | Vínculo |
|---|---|---|
| Integridade dos recebimentos (pagador, pago, método; prova pública do ID `b6cf9b7a…`) | 019 — [REV_INTEGRIDADE_RECEBIMENTOS_019](../reviews/ACTIONFINANCE_REV_INTEGRIDADE_RECEBIMENTOS_019.md) | Continua; V20 local não publicada |
| Dados recuperados / contratos de captura de recebimentos | 021 (autorização vigente) | Continua |
| Rastreabilidade / Monitor (persistência RAM 24h/2000; prova pública da execução) | 020 | Continua |
| Aplicação analítica 022 além deste recorte | 022 | Direção; não implementada |

## O que a 1.0 não inclui como implementado

Pagamento pelo Finance; conector MP automático; extrato persistido; três bases de saldo no produto; projeção; alteração de OPENING produtivo.
