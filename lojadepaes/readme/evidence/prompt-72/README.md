# Prompt 72 — Fila, endereço e fidelidade

Três causas distintas. Sem PII.

## 1. Osvaldo

O pedido existe: `LP2BEEEFEB18`, **finalizado** em setembro, fora da fila vigente. A busca antiga era só por referência; o nome não encontrava. «Todos» não existia. Agora a busca por nome cobre o histórico completo e **Todos** inclui finalizados e cancelados.

Contagens após o publish: vigentes 6 · todos 17 · finalizados 1 · cancelados 8. `LP2BEEEFEB18` aparece em Todos, Finalizados e na busca «osvaldo»; não aparece na fila vigente.

## 2. Endereço de LP42BF063F0C

No pedido operacional todos os campos de entrega estão vazios. Na solicitação vinculada só a **rua** está preenchida; o parse recusa (falta número). Não há endereço completo persistido. Não foi inventado nem copiado. O admin passa a listar os campos faltantes e o rascunho incompleto da solicitação. O link do pedido continua aceitando complemento mesmo pago/em produção.

## 3. Fidelidade

`LP42BF063F0C` está pago e em produção, é focaccia, **sem participação** (`opt_in` falso, sem conta). Não há evento de carimbo. A regra antiga também excluía focaccia da acumulação; a correção separa carimbo (focaccia conta) de prêmio (focaccia não). Este pedido **não** recebe carimbo retroativo. Ajuste manual do proprietário, se existir em outro cadastro, permanece. Não houve reprocessamento em produção.
