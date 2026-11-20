# GESTAO-020 — Painel da página inicial e preço informado no Gestão

Base: `feat/gestao-021-custos` (`ee67c0cf`). Branch: `feat/gestao-020-painel`. Sem merge na `main`. Sem login em produção.

## Checklist

1. **Feito.** `git apply --check` do `GESTAO-020-painel.patch` limpo; `git apply` ok. Front: `npx vitest run src/pages/Hoje.test.tsx src/pages/custos021.test.tsx src/pages/situacao019.test.tsx` — **27 passando**. Backend: `pytest tests/test_painel_020.py tests/test_custos_021.py` — **23 passando**.

2. **Feito.** Migração `0014_preco_manual` no local (`gestao_test` `:55540`): `alembic current` → **`0014_preco_manual` (head)**. Em produção: backup do `gestao` antes do upgrade; mesma revisão.

3. **Feito.** Capturas locais em `docs/evidence/gestao-020-local/`: Hoje com demanda (1280/390), Hoje vazia (1280/390), painel com preço informado (1280). Demanda só em `lojadepaes_test`.

4. **Feito.** Backup `gestao-20261120T161121Z.dump`. Imagem `lojadepaes-gestao:020-20261120` (anterior `021-20261120b`). Upgrade `0013_custos → 0014_preco_manual`; `alembic current` = **`0014_preco_manual` (head)**. Health/ready 200. `lojadepaes.com.br` 200. SSH fechado. Commit e push da branch, **sem merge na `main`**.

5. **Feito** no sentido pedido: não entrei na conta de produção.

## O que mudou

- **Hoje:** números com atalho, gráficos, fornadas com selo de vínculo, necessidade de ingredientes, pendências, estoque (acabaram sem água/preparos), áreas.
- **Quem controla estoque:** exclui água (`e_agua`) e preparos da casa (`produto_id`).
- **Preço informado:** `produtos.preco_manual` + `PUT /custos/produtos/{id}/preco`; `preco_proprio` quando não há variante da Loja.
- **Próximo passo de receitas:** “Monte a primeira receita” só sem nenhuma publicada; senão “N produtos sem receita publicada”.
- **Aviso de versão da Loja:** só para `admin_plataforma` (front).

## Como voltar

No host, `GESTAO_IMAGE` da imagem anterior (`021-20261120b`) e recriar só o `gestao-api`. `0014` é aditiva (`preco_manual` nulo).
