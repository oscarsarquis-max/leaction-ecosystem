# Manifesto final — cenário 026.1

- Versão: `026.1`
- Data-âncora: `2026-08-24`
- Alembic: `0020_inventory_procurement`
- Alvo: `panne_demo`
- Verificação: ok
- Hash das contagens: `e75fffbc3c5ceef384a181a893428231564fc853f6782834ad94c0e4e70407d2`

## Compras completas

Fornecedor Moinho Demo (`SKU-FAR-25`) e cotação comparável do Laticínio Demo. Requisições em rascunho, enviada, aprovada e convertida. Duas cotações com `chosen=false`. Pedido parcial (`partially_received`) e pedido recebido (`received`). Recebimento parcial com lote interno, recebimento completo, devolução com motivo, preço observado por comando humano.

## Seis jornadas

Todas `ok` no `panne_demo` (ver `documentacao/evidencias/cursor-026/smoke-journeys.txt`).

## Rotas e perfis

Router real auditado no teste automatizado; 22 superfícies principais abertas no servidor; 7 perfis `panne-demo:<subject>` com HTTP 200.

## Tabelas vazias (intencionais)

`bedrock_invocation`, `cms_remote_cache` e demais zeros do recorte: sem rede, sem editorial remoto, sem histórico extra de preço. Lista completa em `evidencias/cursor-026/seed-coverage.md`.

## Limitações restantes

Ver [LIMITACOES-026.md](LIMITACOES-026.md).
