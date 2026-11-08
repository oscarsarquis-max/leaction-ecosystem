# GESTAO-010 — Receitas (etapa 4)

Base: `feat/gestao-009-produtos` (`d93def86`). Branch: `feat/gestao-010-receitas`. Imagem em produção: `lojadepaes-gestao:010-20261106` (anterior: `009-20261105`).

A receita técnica fica na Gestão. Nada foi lido nem escrito na Loja. O catálogo de ingredientes não foi recarregado. Em produção, produtos, famílias, receitas, linhas e versões ficaram com zero linhas.

## 0. Ajustes do 009

O ingrediente "Preparos da casa" passa a ter unidade base escolhida no Novo/Editar produto, quando Componente está marcado. O padrão é grama. A unidade de venda não é mais copiada. A Cobertura de chocolate da demonstração local foi corrigida pela tela, de unidade para grama. Em produção não havia componente.

No painel do produto, o atalho do preparo diz "Ver em Ingredientes". Na coluna Situação, de Produtos e de Ingredientes, o selo e o travessão ficam no meio da linha.

A palavra "GESTÃO" saiu de junto da logo em todos os lugares em que aparecia: barra lateral, gaveta do celular, login e as telas de conta. A logo fica sozinha, como no arquivo original. O título da aba do navegador continua "Loja de Pães · Gestão". O grupo do menu "Gestão" permanece.

## 1. Migração

`pg_dump -Fc` do banco `gestao` **antes** do Alembic: `/opt/lojadepaes-gestao/backups/gestao-pre010.dump` (81.292 bytes, SHA-256 `b1331e984e33d3ff37dd606e7899cbfc8f54826944ff69f48d77cb38f978d89f`, `chmod 600`). `pg_restore --list`: 167 linhas. Antes do dump: `alembic_version = 0005_produtos`, 0 produtos, 0 famílias, 0 receitas.

Alembic `0005_produtos` → `0006_receitas`. Só acrescenta:

| Objeto | O que entra |
|---|---|
| `receitas.rendimento_quantidade` | numérico, vazio |
| `receitas.rendimento_unidade` | `g` \| `kg` \| `ml` \| `l` \| `un`, vazio |
| `receitas.peso_unidade_g` | numérico, vazio |
| `receitas.perda_percentual` | numérico, padrão 0 |
| `receitas.modo_fazer` | JSON, lista vazia |
| `receitas.versao` | inteiro, padrão 1 |
| `ck_receitas_situacao` | passa a aceitar `publicada` além de `rascunho`. O valor antigo continua válido |
| `receita_linhas` | receita, ingrediente, texto, quantidade, unidade, ordem, observação. Nasce vazia |
| `receita_versoes` | cópia imutável: rendimento, perda, modo de fazer e linhas em JSON. Nasce vazia |

Nenhuma linha existente foi reescrita. `carregar-catalogo` não rodou.

## 2. O que a tela faz

"4 Receitas" saiu do "em breve". A lista, os chips, o painel e a tabela densa reusam Entradas, Ingredientes e o modal do 007C. Selo só na exceção: "Rascunho", "Custo parcial" e "Sem linhas". O dia comum é travessão.

O editor é uma página, com a trilha "Receitas / Bolo de chocolate" e as abas Ingredientes, Modo de fazer, Rendimento e Revisar. O % do padeiro usa a soma das farinhas. Sem farinha, o traço. Colar da planilha deixa "a decidir" o que não bater exatamente. Publicar grava a versão e fica bloqueado enquanto houver linha a decidir ou unidade incompatível. Editar uma publicada abre o rascunho da versão seguinte; a publicada continua valendo até a próxima publicação.

O custo da linha é a média dos lotes com saldo, ou o último lote se o saldo acabou. Sem custo, a linha fica desconhecida. O componente usa o custo da receita publicada dele. O custo da receita é a soma. Por unidade, divide pelo rendimento já com a perda. Se alguma linha não tem custo, o selo é "Custo parcial", com a quantidade de linhas que faltam. Nunca aparece como zero.

Conversão só entre kg e g, e entre l e ml. Unidade só com ingrediente em unidade. Massa com volume responde `422`, com a mensagem na linha. Produto que usa um componente que, direta ou indiretamente, usa o próprio produto responde `422` `ciclo_receita`.

No painel do produto, a Estrutura mostra as linhas reais: ingrediente com borda cheia, componente com borda tracejada, a quantidade, o custo por unidade e "Montar receita". O selo "Sem receita" sai quando existe versão publicada.

No fluxo, falta é produzido sem receita. Atenção é rascunho ou custo parcial. Em dia é o resto. Se uma etapa anterior está em falta, Receitas não fica em dia.

## 3. Testes

| Onde | Resultado |
|---|---|
| `pytest` no backend | **243 passed** |
| `vitest` no frontend | **83 passed** |
| `ruff`, `tsc` | limpos |

Os testes novos: 500 g de farinha, 350 g de água e 10 g de sal dão 100 %, 70 % e 2 %; linha em kg com ingrediente em g; mililitro com ingrediente em grama dá 422; componente com custo recursivo e ciclo A→B→A dá 422; linha sem custo deixa a receita parcial, e o total não vira zero; publicar grava versão imutável e editar abre o rascunho seguinte; outra organização recebe 404. O componente nasce em grama, não na unidade de venda.

## 4. Capturas locais

`scripts/capture-gestao-010.mjs`, em `docs/evidence/gestao-010-local/`. Checagem em `capturas.md`: sem rolagem horizontal, controles de 40 px (44 no celular). A demonstração (Bolo de chocolate usando a Cobertura de chocolate como componente) existe só no banco local.

A logo, antes e depois:

| Onde | Antes | Depois |
|---|---|---|
| Login, 1280 | `login-antes-1280.png` | `login-depois-1280.png` |
| Barra lateral, 1280 | `menu-antes-1280.png` | `menu-depois-1280.png` |
| Gaveta do celular, 390 | `menu-celular-antes-390.png` | `menu-celular-depois-390.png` |

| O que mostra | 320 | 390 | 768 | 960 | 1280 | 1440 |
|---|---|---|---|---|---|---|
| Lista de Receitas | `receitas-lista-320.png` | `receitas-lista-390.png` | `receitas-lista-768.png` | `receitas-lista-960.png` | `receitas-lista-1280.png` | `receitas-lista-1440.png` |
| Ingredientes | `receita-ingredientes-320.png` | `receita-ingredientes-390.png` | `receita-ingredientes-768.png` | `receita-ingredientes-960.png` | `receita-ingredientes-1280.png` | `receita-ingredientes-1440.png` |
| Modo de fazer | `receita-modo-320.png` | `receita-modo-390.png` | `receita-modo-768.png` | `receita-modo-960.png` | `receita-modo-1280.png` | `receita-modo-1440.png` |
| Rendimento | `receita-rendimento-320.png` | `receita-rendimento-390.png` | `receita-rendimento-768.png` | `receita-rendimento-960.png` | `receita-rendimento-1280.png` | `receita-rendimento-1440.png` |
| Revisar | `receita-revisar-320.png` | `receita-revisar-390.png` | `receita-revisar-768.png` | `receita-revisar-960.png` | `receita-revisar-1280.png` | `receita-revisar-1440.png` |

Estrutura no painel do produto: `produto-estrutura-1280.png`. Entrada sem nota: `entrada-sem-nota-1280.png`. As duas lado a lado em 1280: `lado-a-lado-1280.png`.

## 5. Publicação

- Antes: 954 MB de memória disponíveis, 20 GB livres. Imagem no ar: `009-20261105`.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.244.103`; não estava entre as 29) e **fechada em seguida**. Voltou a 29 regras. A conexão na porta 22 passa a expirar. 80 e 443 seguem em `0.0.0.0/0`. Chave temporária e os tars (local e no host) removidos.
- Dump acima, depois `alembic upgrade head` **somente**. `carregar-catalogo` não rodou.
- `gestao-api` recriado e saudável com `lojadepaes-gestao:010-20261106`. Health e ready 200.
- O JavaScript servido (`index-BXFiaR-p.js`) tem o mesmo SHA-256 do build local, da imagem e do ar (`0d73e2fd54d95105f51c3d00a83905be98e604beb13ef71cae6ec78182567eba`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Depois da migração: 0 produtos, 0 famílias, 0 receitas, 0 linhas, 0 versões.

## 6. Rollback

A imagem `009-20261105` continua no host. Recolocar `GESTAO_IMAGE=lojadepaes-gestao:009-20261105` e recriar só o `gestao-api`. As colunas e tabelas novas podem ficar: a imagem anterior não as usa. O dump `gestao-pre010.dump` está no host se for preciso voltar o banco.

## Checklist

1. **Feito.** Dump `gestao-pre010.dump` antes da migração. Tabelas e colunas na seção 1. Nenhum dado antigo foi reescrito.
2. **Feito.** 243 testes de backend e 83 de frontend passando.
3. **Feito.** Seis larguras da lista e das quatro abas, a Estrutura, o lado a lado com a Entrada sem nota, e a logo antes e depois.
4. **Feito.** Imagem `010-20261106` no ar. Loja 200. Zero receitas em produção.
5. **Feito.** Este retorno e as capturas estão no mesmo commit, com push da branch.
