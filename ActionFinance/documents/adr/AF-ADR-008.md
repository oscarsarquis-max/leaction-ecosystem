# AF-ADR-008 — Panne e Hub preservam seus domínios

## Controle

| Campo | Valor |
|---|---|
| Identificador | AF-ADR-008 |
| Versão | 0.1 |
| Status | PROPOSED |
| Data | 25/09/2026 |
| Dependências | ACTIONFINANCE_ARQ_001 §1.1–1.3 e §5 |

Decisões de negócio correlatas (CONFIRMED_BY_OWNER): Hub recebe assinaturas, não executa o financeiro geral; Panne governa estoque físico; ActionFinance não replica movimento físico.

## Contexto

Uma compra gera entrada física e obrigação financeira. Uma venda, um recebível e um depósito são fatos distintos. Documentos de transição chegaram a atribuir execução financeira ampla ao Hub.

## Decisão

- Panne: fonte de fatos operacionais. Esses fatos poderão originar obrigações no ActionFinance quando houver contrato. ActionFinance não replica entrada, saída, lote, validade ou movimento físico e não presume API de títulos no Panne.
- ActionHub: fonte do recebimento de subscrições. Reimportar resultado não cria receita/recebimento em duplicidade.
- ActionFinance: fonte dos títulos e decisões gerenciais.
- Provider/banco futuro: execução/liquidação externa.
- Cobrança avulsa no working tree do Hub é divergência legada; sem remoção ou reaproveitamento automático.

Vínculo entre fatos: `businessReference + sourceSystem + sourceRecordId` com unicidade por empresa e tipo, quando a importação existir.

## Alternativas rejeitadas

1. ActionFinance como segundo estoque.
2. Hub como ledger do grupo.
3. Uma tabela única “documento” compartilhada entre produtos.

## Consequências

- Integrações Panne/Hub só via Spider e contratos posteriores.
- A relação operacional→obrigação fica autorizada no futuro contrato; não é proibida por este ADR.
- Não assumir que APIs de compra/custo ou de títulos do Panne existem hoje.

## Atualização de precedência — 28/09/2026

As novas diretrizes do proprietário substituem os limites anteriores conflitantes de ActionHub/assinaturas e endereço de publicação. Consultar ACTIONFINANCE_ARQ_002_DIRETRIZES_INTEGRACAO e a fonte ACTIONFINANCE_DIR_INT_001_2026-09-28, vinculadas no índice. Preservar domínio financeiro local, estoque Panne e histórico. Não iniciar integração nem publicar domínios. PRM_002_COR_001 permanece pendente de retorno.
