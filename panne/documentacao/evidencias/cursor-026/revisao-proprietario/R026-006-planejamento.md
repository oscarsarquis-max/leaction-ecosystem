# R026-006 — Planejamento compreensível e acessível

## Escopo

Lista `/planejamento` + detalhe do plano (ex.: `PLN-20260824-0004`).

## Decisões

- Links reais no código e ação `Detalhe` (padrão `/ordens`).
- Resumo operacional via `items_summary` / `item_count` na listagem (lote, sem N+1).
- Prioridade como ordem relativa 1–99 (padrão 50), sem faixas inventadas.
- Ordenação: data operacional → turno → código público → id.

## Evidência API (demo reiniciado, 2026-08-27)

Organização Panne Demonstração — `GET …/production/plans`:

- Ordenação determinística por data/turno/código (ex.: 23 manhã → 23 tarde → 24 manhã…).
- `PLN-20260824-0004`: `item_count=1`, `items_summary=Pão francês (Demo)`, id `e90f89ed-64fb-4359-af49-cf88cf44c7ad`.
- Detalhe: produto `Pão francês (Demo)`, `PAO-FR`, `mass`, `3300`, `priority=50`.
- Horizonte: `0` planos; sem vazamento do id/código da Panne.

## Validação Cortex (navegador)

Confirmados: coluna Conteúdo; links Código e Detalhe; navegação sem depender só do clique da linha; ordenação data/turno/código; detalhe de `PLN-20260824-0004` (Pão francês (Demo), PAO-FR, Massa, 3.300 g); Ordem de processamento relativa 1–99 (padrão 50), sem Alta/Média/Baixa; isolamento Panne → Horizonte (`Recurso não encontrado`) → Panne; lista correta no retorno.

## Estado

**Validada integralmente pelo Cortex.**
