# GESTAO-009 — Produtos (etapa 3)

Base: `feat/gestao-007d-juntado` (`6b9ee69b`). Branch: `feat/gestao-009-produtos`. Imagem em produção: `lojadepaes-gestao:009-20261105` (anterior: `007d-20261105`).

O produto nasce na Gestão. Nada foi lido nem escrito na Loja. O catálogo de ingredientes não foi recarregado. Em produção, `produtos`, `familias` e `receitas` ficaram com zero linhas.

## 0. Trocar ingrediente (007C)

O campo de destino vinha preenchido com a origem porque a primeira sugestão em destaque vira o placeholder do campo, e o nome do item batia com o próprio ingrediente. O destino agora começa vazio, com "Buscar ingrediente de destino". A origem sai das sugestões (`exceto` na API e no campo). Destino igual à origem continua `422` `mesmo_ingrediente`. Em 390 px o campo cabe na largura do diálogo (`trocar-destino-390.png`).

## 1. Migração

`pg_dump -Fc` do banco `gestao` **antes** do Alembic: `/opt/lojadepaes-gestao/backups/gestao-pre009.dump` (70.988 bytes, SHA-256 `0f7e1284af89277e7f5ff81c4ce68dac1a6208e557ae6f0d5516e713bb3699a6`, `chmod 600`). `pg_restore --list`: 142 linhas.

Alembic `0004_valor_pago_correcoes` → `0005_produtos`. Só acrescenta:

| Objeto | O que entra |
|---|---|
| `organizacoes.familias_sugestoes_dispensadas` | boolean, falso |
| `familias` | id, organizacao_id, nome, nome_normalizado, criado_em |
| `produtos` | id, organizacao_id, nome, nome_normalizado, codigo, modalidade, uso_venda, uso_componente, familia_id, unidade_venda, peso_unidade_g, ativo, observacao, item_estoque_id, criado_em, atualizado_em |
| `receitas` | id, organizacao_id, produto_id (único), situacao `rascunho`, criado_em. Sem linhas |
| `ingredientes.produto_id` | uuid, vazio nos ingredientes que já existiam, único |
| `ck_ingredientes_categoria` | a lista só ganha "Preparos da casa". Os valores antigos continuam válidos |

As seis famílias (Pães, Bolos, Doces, Coberturas e recheios, Massas, Revenda) não são gravadas sozinhas: aparecem como sugestão até o Oscar aceitar ou dispensar.

## 2. O que a tela faz

"3 Produtos" saiu do "em breve". A lista, os chips, o filtro de família, o painel e o diálogo reusam Entradas, Ingredientes e o modal do 007C. Selo só na exceção: "Sem receita" (produzido; as linhas ficam para o GESTAO-010) e "Sem item" (comprado sem item de estoque). O dia comum é travessão.

Com `uso_componente` ligado, nasce (ou volta) um ingrediente "Preparos da casa" com o mesmo nome. Desligar o uso não apaga esse ingrediente: ele fica inativo se não tiver saldo. A receita técnica é só o lugar, em rascunho, sem linhas. O diagrama mostra isso: "Receita ainda vazia · Montar receita (em breve)".

Enquanto existir um produzido, a etapa fica em atenção, porque a receita ainda não tem linhas. Em dia só quando todo produto ativo é comprado e tem item de estoque, e a etapa anterior não está em falta.

## 3. Testes

| Onde | Resultado |
|---|---|
| `pytest` no backend | **235 passed** |
| `vitest` no frontend | **83 passed** |
| `ruff`, `eslint`, `tsc` | limpos |

Os testes novos: produzido, comprado e componente na busca como Preparos da casa; comprado sem item é pendente; nome igual 409 e nome parecido pede confirmação; desligar o componente não apaga o ingrediente; a troca não sugere a origem e o mesmo destino dá 422; produto de outra organização não aparece.

## 4. Capturas locais

`scripts/capture-gestao-009.mjs`, em `docs/evidence/gestao-009-local/`. Checagem em `capturas.md`: sem rolagem horizontal, controles de 40 px (44 no celular), diálogo dentro da largura. A demonstração (Cobertura de chocolate, Bolo de chocolate, Chocolate em barra, Pão de queijo congelado) existe só no banco local.

| O que mostra | 320 | 390 | 768 | 960 | 1280 | 1440 |
|---|---|---|---|---|---|---|
| Lista com filtros | `produtos-lista-320.png` | `produtos-lista-390.png` | `produtos-lista-768.png` | `produtos-lista-960.png` | `produtos-lista-1280.png` | `produtos-lista-1440.png` |
| Painel, estrutura da cobertura | `produtos-painel-320.png` | `produtos-painel-390.png` | `produtos-painel-768.png` | `produtos-painel-960.png` | `produtos-painel-1280.png` | `produtos-painel-1440.png` |
| Novo produto, comprado | `produtos-novo-320.png` | `produtos-novo-390.png` | `produtos-novo-768.png` | `produtos-novo-960.png` | `produtos-novo-1280.png` | `produtos-novo-1440.png` |

Lado a lado em 1280: `lado-a-lado-1280.png` (Ingredientes e Produtos). A busca de ingredientes com o componente: `ingredientes-busca-1280.png` (Preparos da casa · Cobertura de chocolate). O destino da troca em 390: `trocar-destino-390.png`.

## 5. Publicação

- Antes: 876 MB de memória disponíveis, 20 GB livres. Imagem no ar: `007d-20261105`.
- SSH: porta 22 aberta **só para o meu IP /32** (`189.14.176.74`; não estava entre as 29) e **fechada em seguida**. Voltou a 29 regras. 80 e 443 seguem em `0.0.0.0/0`. Chave temporária e os tars (local e no host) removidos.
- Dump acima, depois `alembic upgrade head` **somente**. `carregar-catalogo` não rodou.
- `gestao-api` recriado e saudável com `lojadepaes-gestao:009-20261105`. Health e ready 200.
- O JavaScript servido (`index-uPJGg9pu.js`) tem o mesmo SHA-256 do build local, da imagem e do ar (`ca8d6d9220ca6a48b3e6070116524944a046a946dd4e467308095c5b38fd0601`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Depois da migração: 0 produtos, 0 famílias, 0 receitas.

## 6. Rollback

A imagem `007d-20261105` continua no host. Recolocar `GESTAO_IMAGE=lojadepaes-gestao:007d-20261105` e recriar só o `gestao-api`. As tabelas novas podem ficar: a imagem anterior não as usa. O dump `gestao-pre009.dump` está no host se for preciso voltar o banco.

## Checklist

1. **Feito.** Dump `gestao-pre009.dump` antes da migração. Tabelas e colunas na seção 1. Nenhum dado antigo foi reescrito.
2. **Feito.** 235 testes de backend e 83 de frontend passando.
3. **Feito.** Seis larguras, 1280 e 390 no quadro acima, lado a lado, painel da cobertura, diálogo comprado e a busca mostrando Preparos da casa.
4. **Feito.** Imagem `009-20261105` no ar. Loja 200. Zero produtos em produção.
5. **Feito.** Este retorno e as capturas estão no mesmo commit, com push da branch.
