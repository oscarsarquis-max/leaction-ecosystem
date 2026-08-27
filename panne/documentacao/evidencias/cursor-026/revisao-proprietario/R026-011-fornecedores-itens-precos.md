# R026-011 — Fornecedores, itens comerciais e histórico de preços

## Estado

**Validada integralmente pelo Cortex** (após reinício completo da demo).

## Passagens

| Passagem | Resultado |
|---|---|
| 1ª | Código entregue; falha Cortex **exclusivamente** por API antiga em `:5080` |
| 2ª | Reinício → validação integral no processo novo |

## Validação integral (Cortex)

- Links semânticos + Detalhe; estados humanos; contagem real.
- Moinho Demo · 1 item ativo; GET detalhe ok.
- FOR-MOINHO · SKU-FAR-25 · Farinha de trigo tipo 1 (Demo) · FAR-TRIGO · 25 kg.
- Último preço R$ 13,00 · **24/08/2026, 20:03**.
- Histórico (mais recente primeiro): R$ 13,00 · Recebimento; R$ 13,10 · Cadastro de demonstração; R$ 12,50 · Cadastro de demonstração.
- Distinção custo operacional ≠ valor contábil.
- Nenhuma criação/alteração na validação.
- Isolamento: Panne → Horizonte limpa detalhe/histórico; Horizonte «recurso não encontrado»; sem financeiro Panne residual.

## 1ª falha (registro)

API antiga PID 6616 (14:16:07): lista sem `active_item_count`; detalhe **405**. Validação final no processo reiniciado (API 42328 · 15:04:42; FE 53712 · 15:04:43).

## Restrições

CURSOR-027 não iniciado. Sem commit/push/merge/deploy. R026-001…010 intactas.
