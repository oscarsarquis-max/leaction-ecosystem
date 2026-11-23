# GESTAO-022 — Lote vencido não aparece como “vence em 7 dias”

Base: `feat/gestao-020-painel` (`49497e83`). Branch: `feat/gestao-022-vencido`. Sem migração (`GESTAO_SEM_BANCO=1`). Sem merge na `main`.

## Checklist

1. **Feito.** `git apply --check` do `GESTAO-022-lote-vencido.patch` limpo; `git apply` ok. Front: `npx vitest run src/pages/Hoje.test.tsx src/pages/custos021.test.tsx` — **24 passando**. Backend: `pytest tests/test_vencido_022.py` — **1 passando**.

2. **Feito.** Captura local em `docs/evidence/gestao-022-local/hoje-lote-vencido-1280.png`: grupo **Vencido**, selo “há 7 dias”, número **Lotes vencidos**, barra “1 lote vencido”.

3. **Feito.** Imagem `lojadepaes-gestao:022-20261123`. Deploy com `GESTAO_SEM_BANCO=1` (“banco: nada a fazer neste deploy”). Só o `gestao-api` recriado e healthy (anterior em produção: `020-20261120`). `https://gestao.lojadepaes.com.br/` 200, health/ready 200, serve `index-CtNJnu_9.js`. `https://lojadepaes.com.br` 200. SSH deste ciclo fechado (`regras_22` vazias). Continuam no ar: `gestao-api`, `infra-api-1`, `lepain`, `infra-caddy-1`, `infra-db-1`.

## O que mudou

- **Front:** estoque na Hoje separa **Vencido** (`dias < 0`) de **Vence em 7 dias** (`dias ≥ 0`); número **Lotes vencidos**; números do dia numa linha em tela larga; demanda sem pedidos vira aviso sem barras vazias.
- **Backend:** `calcular_fluxo` separa vencidos e a vencer; etapa Ingredientes usa `falta` + “N lote(s) vencido(s)” (e, se houver, “· N vencem em 7 dias”); `GET /hoje` mantém vencidos em `vence_em_7_dias` com `dias` negativo.

## Como voltar

No host, `GESTAO_IMAGE=lojadepaes-gestao:020-20261120` e recriar só o `gestao-api`. Sem mudança de banco.
