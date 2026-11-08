# GESTAO-011 — Importar os produtos da vitrine

Base: `feat/gestao-010-receitas` (`c29586d1`). Branch: `feat/gestao-011-importar`. Imagem em produção: `lojadepaes-gestao:011-20261106` (anterior: `010-20261106`).

O Oscar confirmou que os 10 produtos publicados são a vitrine. Não houve GRANT. `showcase_slots` e `media_assets` não foram lidos nem alterados. A foto é a URL pública `https://lojadepaes.com.br/api/v1/catalog/media/{featured_image_id}`. Os nomes ficaram iguais aos da Loja, inclusive "Sicicilano". A importação é única: o produto passa a ser da Gestão.

## 0. Acabamentos do 010

Na tabela da receita, as colunas Quantidade, % do padeiro e Custo passaram a caber o título inteiro. A tabela da Entrada sem nota permanece com as larguras de antes.

Custo incompleto não aparece como total. Na lista de Receitas e no painel do produto, o valor fica "R$ 0,01 parcial" em cinza, ou "—". No rodapé: "Parcial: R$ 0,10 · 2 linhas sem custo".

Na aba Rendimento, a frase do custo usa o mesmo recuo do cartão (`entrada-dica`).

## 1. Famílias

O mapa aprovado está em `backend/app/importacao/familias-vitrine.yaml`.

| Produto | Família |
|---|---|
| Focaccia Alta (Italian Focaccia) | Focaccia |
| Pão Fermentação Natural de Trigo | Pão Rústico |
| Pain Noir Malté au Café (Pão preto maltado de café) | Pão Sovado |
| Pão de Frutas (Arabian Bread) | Pão Sovado |
| Pão Nuvem de Leite (Ninho) | Pão Sovado |
| Pão de Café (Marroquinus) | Pão Sovado |
| Pão de Canela (Cinnamon Bread) | Pão Sovado |
| Pão de Erva Doce (Anise Bread) | Pão Sovado |
| Pão de Limão Sicicilano (Lemon Bread) | Pão Sovado |
| Rolled Bread de Pepperoni com Muçarela e Manteiga de Alho | Pão Sovado |

## 2. Migração

`pg_dump -Fc` do banco `gestao` **antes** do Alembic: `/opt/lojadepaes-gestao/backups/gestao-pre011.dump` (89.235 bytes, SHA-256 `62b7c30b7f1dc9fb2ec092810aa64130fa240ef51e13393ee2eee279790202eb`, `chmod 600`). `pg_restore --list`: 183 linhas. Antes do dump: `alembic_version = 0006_receitas`, 0 produtos, 0 famílias, 0 receitas.

Alembic `0006_receitas` → `0007_importacao_loja`. Só acrescenta:

| Objeto | O que entra |
|---|---|
| `produtos.foto_url` | texto, vazio. URL pública da foto, sem copiar o arquivo |
| `produtos.origem_loja_id` | identificador da Loja, vazio. Único por organização quando preenchido |
| `uq_produtos_org_origem_loja` | índice único parcial, só quando a origem está preenchida |

Nenhuma linha existente foi reescrita. `carregar-catalogo` não rodou.

## 3. Execução em produção

Comando: `importar-produtos-loja --organizacao boulangerie --executar --confirm boulangerie`.

Primeira vez:

```
3 famílias criadas, 10 produtos criados, 0 já importados, 0 não criados
```

Os 10 nasceram Produzido · Venda, unidade `un`, com foto e receita em rascunho, sem linhas. Famílias: Focaccia (1), Pão Rústico (1), Pão Sovado (8).

Segunda vez, no mesmo comando:

```
0 famílias criadas, 0 produtos criados, 10 já importados, 0 não criados
```

A segunda passagem não duplicou e não reescreveu o que já estava gravado.

No banco da Loja, `pg_stat_user_tables` ficou igual antes e depois (inserções, atualizações e exclusões) em `products`, `product_variants`, `showcase_slots` e `media_assets`. Os publicados continuam 10. A leitura usou `SET LOCAL ROLE gestao_reader` e `ROLLBACK`.

## 4. Tela

A lista de Produtos mostra a miniatura de 40 px à esquerda do nome. Sem foto, a inicial no fundo neutro. No painel, a foto ocupa a largura do conteúdo, em 4:3, com a linha "Importado da Loja em 06/11". Se a imagem falhar, entra a mesma inicial. O navegador passou a aceitar a foto da Loja em `img-src` (`https://lojadepaes.com.br`). O resto da política de conteúdo permanece.

## 5. Testes

| Onde | Resultado |
|---|---|
| `pytest` no backend | **250 passed** |
| `vitest` no frontend | **83 passed** |
| `ruff` | limpo |

A importação de teste cria as 3 famílias e os 10 produtos, não duplica na segunda vez, não sobrescreve um nome que o Oscar tenha mudado, não cria um nome que já exista na Gestão e não escreve na Loja.

## 6. Capturas locais

`scripts/capture-gestao-011.mjs`, em `docs/evidence/gestao-011-local/`. Checagem em `capturas.md`: sem rolagem horizontal, controles de 40 px (44 no celular), 10 miniaturas carregadas e a foto do painel visível.

| O que mostra | 390 | 1280 |
|---|---|---|
| Lista de Produtos | `produtos-lista-390.png` | `produtos-lista-1280.png` |
| Painel da Focaccia | `produto-painel-390.png` | `produto-painel-1280.png` |

A demonstração local também tem os produtos do ciclo 010 (Bolo, Cobertura, Chocolate em barra, Pão de queijo). Os 10 da vitrine estão nas mesmas telas, com as fotos públicas.

## 7. Publicação

- Antes: 911 MB de memória disponíveis, 20 GB livres. Imagem no ar: `010-20261106`.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.244.103`; não estava entre as 29) e **fechada em seguida**. Voltou a 29 regras. A conexão na porta 22 passa a expirar. 80 e 443 seguem em `0.0.0.0/0`. Chave temporária e o tar (local e no host) removidos.
- Dump acima, depois `alembic upgrade head` **somente**. `carregar-catalogo` não rodou.
- `gestao-api` recriado e saudável com `lojadepaes-gestao:011-20261106`. Health e ready 200.
- O JavaScript servido (`index-BGgMiVMx.js`) tem o mesmo SHA-256 do build local, da imagem e do ar (`331cd62c7a0d076c4b7dafaf63047a48230965782bcb9e3cf8eead3cce2c259a`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200.

## 8. Rollback

A imagem `010-20261106` continua no host. Recolocar `GESTAO_IMAGE=lojadepaes-gestao:010-20261106` e recriar só o `gestao-api`. As colunas novas podem ficar: a imagem anterior não as usa. O dump `gestao-pre011.dump` está no host se for preciso voltar o banco. Os 10 produtos importados estão só na organização `boulangerie`.

## Checklist

1. **Feito.** A primeira execução criou 3 famílias e 10 produtos, Produzido · Venda, receita em rascunho.
2. **Feito.** A segunda execução criou 0.
3. **Feito.** Lista e painel em 1280 e 390, com as 10 miniaturas e a foto da Focaccia.
4. **Feito.** `lojadepaes.com.br` 200. Nenhuma escrita na Loja. SSH fechado.
5. **Feito.** Este retorno e as capturas estão no mesmo commit, com push da branch.
