# GESTAO-021 — Custos e preço (rateio por kg, margem/markup, Loja só lida)

Base: `main` (`fb8b11e1`). Branch: `feat/gestao-021-custos`. Sem merge na `main`. Sem login em produção. Oscar informa os custos reais.

## Checklist

1. **Feito.** `git apply --check` do patch `GESTAO-021-custos-e-preco.patch` saiu limpo; `git apply` aplicou. Front: `npx vitest run src/pages/custos021.test.tsx src/pages/Hoje.test.tsx src/pages/situacao019.test.tsx` — **19 passando**. Backend: `pytest tests/test_custos_021.py` — **6 passando** (4 do contrato Oscar + 2 do adendo multicliente).

2. **Feito.** Migração `0013_custos` no ambiente local (`gestao_test` em `127.0.0.1:55540`): `alembic current` → **`0013_custos` (head)**. Em produção: backup do banco `gestao` antes do upgrade; mesma revisão `0013_custos`.

3. **Feito.** Capturas locais com backend real (`8090`) e Vite (`5185`) em `docs/evidence/gestao-021-local/`: `custos-1280.png`, `custos-390.png`, `painel-produto-1280.png`. Exemplo Oscar: Aluguel R$ 3.000 / 600 kg → R$ 5/kg; pão 1.000 g, variável R$ 12 → rateio R$ 5, total R$ 17; margem 60 % → sugerido R$ 30.

4. **Feito.** Backup pré-migrate `gestao-20261120T150421Z.dump` (S3). Imagem `lojadepaes-gestao:021-20261120b` (adendo multicliente). Upgrade `0012_cultura_viva → 0013_custos`; `alembic current` = **`0013_custos` (head)**. `gestao-api` healthy (anterior `019-20261119`); `/api/v1/health` e `/ready` 200. `https://lojadepaes.com.br` 200; `gestao.lojadepaes.com.br/api/v1/health` 200. Porta 22 deste ciclo fechada (`regras_22` vazia). Commit e push da branch, **sem merge na `main`**.

5. **Feito** no sentido pedido: não entrei na conta de produção. Custos reais ficam com o Oscar.

## Adendo multicliente

- `GET /custos` (e as escritas que devolvem a visão) só passam a sessão `gestao_reader` para `_precos_loja` quando `organizacao.fonte_loja` é verdadeiro. Sem Loja integrada: `loja: []`, sem consulta.
- Custos fixos, massa do mês e regras continuam só da organização da sessão (`OrgScoped` + `parametros_custo` por `organizacao_id`).
- Testes: `test_sem_fonte_loja_nao_consulta_gestao_reader` (mock/`spy` em `_precos_loja`, sessão sempre `None`) e `test_custos_isolados_por_organizacao` (fixos/regras de A ausentes em B).

## Campo de unidades da Loja

Por variante: `physical_units` se > 0; senão `units_per_pack` se > 0; senão `1`. O retorno traz `campo_unidades` (`physical_units` | `units_per_pack` | `default_1`).

## Domínio

O módulo de “corrigir custo” do lote permanece em `app.domain.custos`. O ciclo 021 vive em `app.domain.custos_preco` (API em `/api/v1/custos`).

## Como voltar

No host, apontar `GESTAO_IMAGE` para a imagem anterior (`019-20261119` ou a que estiver no `.env` antes deste deploy) e recriar só o `gestao-api`. O schema `0013_custos` é só aditivo; o downgrade Alembic existe se precisar reverter colunas/tabelas.
