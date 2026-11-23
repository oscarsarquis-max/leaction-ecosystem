# GESTAO-023 — Entrada só manual e lote vencido em Ingredientes

Base: `feat/gestao-022-vencido` (`3857ad62`). Branch: `feat/gestao-023-entrada`. Sem migração (`GESTAO_SEM_BANCO=1`). Sem merge na `main`.

## Checklist

1. **Feito.** `git apply --check` do `GESTAO-023-entrada-manual.patch` limpo; `git apply` ok. Front: `npx vitest run src/pages/fluxo.test.tsx` — **34 passando**.

2. **Feito.** Capturas locais em `docs/evidence/gestao-023-local/`: `entradas-1280.png`, `nova-entrada-1280.png`, `ingredientes-vencido-1280.png`.

3. **Feito.** Imagem `lojadepaes-gestao:023-20261123`. Deploy com `GESTAO_SEM_BANCO=1`. Só o `gestao-api` recriado e healthy (anterior: `022-20261123`). `gestao.lojadepaes.com.br` 200 (health/ready 200), serve `index-CgiByl07.js`. `lojadepaes.com.br` 200. SSH deste ciclo fechado (`regras_22` vazias).

## O que mudou

- **Entrada:** “Nova entrada” abre `/entradas/nova` direto; painel “Como chegou?” removido; aliases `/entradas/sem-nota` e `?nova=1` seguem; filtros Com/Sem nota saem; motivo exibido como **Compra** (valor `compra_sem_nota` intacto).
- **Ingredientes:** selo **Vencido** quando o primeiro lote já passou; filtro **Vencidos e a vencer**.
- **Servidor:** única frase de usuário com “com nota” era o erro `tipo_indisponivel` → “Entrada por nota fiscal ainda não está disponível.”. Nenhuma label de motivo no backend; o valor `compra_sem_nota` não mudou.

## Como voltar

No host, `GESTAO_IMAGE=lojadepaes-gestao:022-20261123` e recriar só o `gestao-api`. Sem mudança de banco.
