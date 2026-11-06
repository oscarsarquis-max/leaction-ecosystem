# GESTAO-012A — Gigio: correções antes do uso real

Base: `feat/gestao-012-gigio` (`b0daac50`). Branch: `feat/gestao-012a-gigio`. Imagem em produção: `lojadepaes-gestao:012a-20261106` (anterior, ainda no host: `012-20261106`).

A quantidade da massa-base é o peso da massa. O Gigio sugere só o que vai além dela. O ensaio real não grava. A organização de teste saiu de produção.

Não houve migração. O Alembic continua em `0008_gigio`. `carregar-catalogo` não rodou.

## 1. Massa-base

A massa-base é um componente com receita publicada. O backend expande essa receita e calcula a farinha contida. Para o Gigio, essas linhas vão como fixas e já incluídas. O % do que ele sugere usa essa farinha. Linha sugerida que repete um ingrediente da base é descartada, com aviso.

No editor, o % do padeiro usa a farinha recursiva dos componentes. A linha do componente mostra "—". Sem receita publicada, o passo 1 diz "Monte primeiro a receita da {nome}" e oferece abrir essa receita.

O caso numérico do teste: 800 g de massa sovada, com 500 g de farinha em 830 g de massa, dão farinha contida de 482 g.

## 2. Passo 1 e passo 3

O passo 1 traz as linhas atuais da receita numa mini tabela: ingrediente, quantidade e unidade, com "+ linha".

O passo 3 abre num painel de até 960 px (no celular, a tela inteira). Colunas: Usar, Ingrediente, %, Quantidade, Faixa, Confiança. O motivo fica embaixo do nome, na linha inteira. Faixa igual no mínimo e no máximo não aparece. No celular, cada sugestão é um cartão.

## 3. Categorias

Aplicar não cria ingrediente. A ligação usa o ingrediente que já existe. No diálogo de cadastro, a categoria continua sendo a do catálogo. O "Outros" da auditoria veio da captura anterior, que tinha cadastrado Açúcar, Canela e Manteiga assim no ambiente de demonstração. A captura deste ciclo corrige esses três no banco local: Açúcares e mel, Sal e temperos, Gorduras. Nenhum ingrediente da `boulangerie` foi alterado.

## 4. Testes

| Onde | Resultado |
|---|---|
| `pytest` no backend, antes do último teste | **260 passed** |
| `pytest tests/test_gigio.py`, depois | **11 passed** |
| `vitest` no frontend | **83 passed** |
| `ruff` nos arquivos do ciclo | limpo |

O arquivo do Gigio cobre o pedido que o gateway falso recebe (padrões ativos, linha fixa e massa-base expandida), o descarte da linha que repete a base, o % recursivo de 482 g, a massa sem receita publicada, e o ensaio que não troca "Farinha de trigo" por um ingrediente só parecido.

## 5. Capturas locais

`scripts/capture-gestao-012a.mjs`, com o gateway falso, em `docs/evidence/gestao-012a-local/`. Controles de 40 px (44 abaixo de 960). O Pão de Canela fica com Massa sovada 500 g e "—" no %, Sal 10 g a 3,3 %, e sem farinha nem água em dobro. Açúcar, Canela e Manteiga aparecem nas categorias do catálogo. O rodapé diz "Parcial: R$ 0,10 · 4 linhas sem custo".

| O que mostra | Arquivo |
|---|---|
| Passo 1, 390 e 1280 | `gigio-passo1-390.png`, `gigio-passo1-1280.png` |
| Passo 3, cartão, 960 e tabela larga | `gigio-passo3-390.png`, `gigio-passo3-960.png`, `gigio-passo3-1280.png` |
| Receita sem duplicar a base | `receita-sem-duplicar-390.png`, `receita-sem-duplicar-1280.png` |
| Rendimento, custo parcial alinhado | `rendimento-parcial-1280.png` |
| Lista, "R$ 0,01 parcial" e "R$ 0,00 parcial" | `lista-parcial-1280.png` |
| Gestão › Padrões | `padroes-390.png`, `padroes-1280.png` |

## 6. Ensaio real, sem gravar

`python -m app.cli gigio-ensaio --sem-gravar --organizacao boulangerie`, dentro do `gestao-api` de produção. A descrição de cada caso veio de `GET https://lojadepaes.com.br/api/v1/catalog/products` (só nome e texto; preço não entra).

As quatro primeiras quantidades da base são as do pedido. As outras quatro, que o pedido não numerou, ficaram: Fermento 5 g, Sal 10 g, Açúcar 20 g, Gordura 40 g. A farinha contida desse caso é 500 g.

A linha da base só liga um ingrediente da casa quando o nome é o mesmo. "Farinha de trigo" não vira a farinha parecida que a padaria tem.

Contagem antes e depois, as duas iguais. `gravou=0`.

| Tabela | Antes | Depois |
|---|---|---|
| organizacoes | 1 | 1 |
| produtos | 10 | 10 |
| receitas | 10 | 10 |
| receita_linhas | 0 | 0 |
| gigio_sugestao | 0 | 0 |
| padrao_padaria | 5 | 5 |
| ingredientes | 10 | 10 |

### Pão de Canela sobre a Massa sovada

Modelo `us.anthropic.claude-sonnet-4-6`. Tokens 1863 de entrada e 1044 de saída. Farinha contida 500 g. Rendimento 600 g. Perda 10 %.

Descrição: "Pão meio integral, levemente adocicado no miolo, com coco queimado. Casca crocante e coberta por uma calda de canela doce. Pão para alegrar os lanches da manhã. Adorável com chocolate quente ou café. Sirva com acompanhamento de queijo fresco."

| Linha | % | Quantidade | Faixa | Confiança | Motivo |
|---|---|---|---|---|---|
| Farinha de trigo | 100 % | 500 g | — | alta | Já incluída na massa-base. |
| Água | 60 % | 300 g | — | alta | Já incluída na massa-base. |
| Água residual do fermento | 6 % | 30 g | — | alta | Já incluída na massa-base. |
| Leite em pó | 10 % | 50 g | — | alta | Já incluída na massa-base. |
| Fermento | 1 % | 5 g | — | alta | Já incluída na massa-base. |
| Sal | 2 % | 10 g | — | alta | Já incluída na massa-base. |
| Açúcar | 4 % | 20 g | — | alta | Já incluída na massa-base. |
| Gordura | 8 % | 40 g | — | alta | Já incluída na massa-base. |
| Farinha de trigo integral | 15 % | 75 g | 10–20 % | media | Toque integral leve, sem pesar a massa sovada. Faixa típica para pão meio integral. |
| Coco queimado | 10 % | 50 g | 8–15 % | media | Inclusão no miolo. Faixa típica para coco ralado tostado em pão enriquecido. |
| Canela em pó (calda) | 1 % | 5 g | 0,5–2 % | media | Para a calda de cobertura. Faixa típica; ajuste ao gosto do padeiro. |
| Açúcar (calda) | 10 % | 50 g | 8–15 % | media | Base da calda doce de canela para a casca. Faixa típica para calda de cobertura. |
| Água (calda) | 6 % | 30 g | 4–8 % | media | Para dissolver o açúcar e a canela da calda. Ajuste a consistência desejada. |
| Melhorador de farinha | 1 % | 5 g | — | alta | Recomendado ao incluir farinha integral, para manter estrutura e maciez da massa sovada. |

Modo de fazer:

- Misture a farinha integral à massa sovada já preparada, incorporando aos poucos até homogeneizar.
- Adicione o melhorador junto com a farinha integral.
- Acrescente o coco queimado no final da sova, apenas para distribuir sem quebrar.
- Modele os pães e deixe fermentar até dobrar de volume.
- Asse normalmente conforme o padrão da casa para pão sovado.
- Enquanto os pães ainda estão quentes, prepare a calda: dissolva o açúcar e a canela em pó na água em fogo baixo até encorpar levemente.
- Pincele a calda sobre a casca dos pães assim que saírem do forno, para fixar e dar brilho crocante.

Observação: a farinha integral substitui parte da farinha da base — o padeiro decide se reduz a farinha principal ou soma ao total. O coco deve estar bem tostado antes de entrar na massa. A calda é aplicada depois do forno. O rendimento não foi informado: os pesos da calda foram estimados para 500 g de farinha.

### Focaccia Alta

Modelo `us.anthropic.claude-sonnet-4-6`. Tokens 1669 de entrada e 1366 de saída. Sem massa-base. Rendimento 1277 g. Perda 10 %.

Descrição: "Focaccia alta, longa maturação, com alhos confitados e tomates cereja. O aroma fica por conta do alecrim. Tostadinha por cima e fofa no miolo, é perfeita para um encontro a dois. Um vinho tinto e música completam a experiência."

| Linha | % | Quantidade | Faixa | Confiança | Motivo |
|---|---|---|---|---|---|
| Farinha de trigo tipo 0 | 80 % | 500 g | — | media | Base principal da focaccia alta — boa extensibilidade e estrutura para miolo fofo |
| Farinha de semolina | 20 % | 125 g | — | media | Complementa a tipo 0, dá crocância na base e tostado por cima |
| Água | 78 % | 390 g | — | media | Focaccia alta pede hidratação elevada (78 %) para miolo aberto e fofo — acima do padrão da casa de 60 % |
| Melhorador de farinha | 1 % | 6 g | — | media | Apoia a estrutura na longa maturação |
| Sal | 2 % | 13 g | — | media | Padrão da casa |
| Azeite (massa) | 6 % | 38 g | — | media | Azeite na massa é clássico da focaccia — maciez e sabor |
| Azeite (finalização) | 8 % | 50 g | — | media | Generoso por cima antes de assar — garante o tostado e o brilho característico |
| Alho confitado | 8 % | 50 g | 5–12 % | media | Inclusão não medida — faixa típica para cobertura de focaccia |
| Tomate cereja | 16 % | 100 g | 10–20 % | media | Inclusão não medida — faixa típica para cobertura de focaccia |
| Alecrim | 0,8 % | 5 g | 0,5–1,5 % | media | Inclusão não medida — faixa típica de erva seca/fresca para focaccia |

Modo de fazer:

- Misture as farinhas e o melhorador a seco.
- Adicione a água (reservando 10 % para o final), o azeite da massa e o sal. Misture até incorporar.
- Acrescente a água reservada aos poucos e desenvolva a massa até ponto de véu leve.
- Cubra e leve à geladeira para longa maturação: 12 a 24 horas.
- Retire, deixe aclimatar por 1 hora em temperatura ambiente.
- Unte generosamente a assadeira com azeite e transfira a massa sem degaseificar demais.
- Deixe fermentar na assadeira por mais 1 a 2 horas até crescer bem.
- Afunde os dedos na massa formando os furinhos clássicos.
- Distribua o alho confitado e os tomates cereja pressionando levemente.
- Regue com o azeite de finalização e espalhe o alecrim.
- Asse em forno alto (220–240 °C) até dourar bem por cima e tostar a base.

Observação: o rendimento não foi informado; a referência usada foi 500 g de farinha. A hidratação de 78 % é de propósito, acima dos 60 % da casa, para a massa mole da focaccia alta. O modelo não listou levain: disse que o fermento da casa não estava entre os ingredientes nomeados e que o padeiro inclui o que tiver.

## 7. Limpeza da gigio-teste

Autorizada pelo Oscar em 06/11, às 13:46. Nenhuma linha de outra organização apontava para ela (`cruzadas=0`). O usuário `gigio-teste` não era membro de outra organização. Sessões e tentativas de login desse usuário: 0.

Inventário antes:

| O quê | gigio-teste | boulangerie |
|---|---|---|
| organizacao | 1 (CNPJ 19.900.000/0001-76) | 1 |
| gigio_sugestao | 1 | 0 |
| padrao_padaria | 5 | 5 |
| produtos | 1 | 10 |
| receitas | 1 | 10 |
| receita_linhas | 0 | 0 |
| locais | 1 (Despensa) | 1 |
| membros | 1 | 1 |
| ingredientes | 0 | 10 |
| familias | 0 | 3 |
| correcoes_custo | 0 | 5 |
| entrada_linhas | 0 | 16 |
| entradas | 0 | 6 |
| itens_estoque | 0 | 11 |
| lotes | 0 | 16 |
| movimentos | 0 | 24 |
| parecidos_distintos | 0 | 1 |
| sessoes | 0 | 18 |
| trocas_ingrediente | 0 | 3 |

O produto era "Pão de teste do Gigio", rascunho, receita `b6260851-5def-4126-8930-a07b72fe065c`. A sugestão `9698b10e-50d6-4119-9104-ec5f41aa2f77` não tinha sido aplicada.

`pg_dump -Fc` antes de apagar: `/opt/lojadepaes-gestao/backups/gestao-pre012a.dump` (100.291 bytes, SHA-256 `6b675841fc2d6e31422fe46472801da4bf2a587d36862aeb905286934b80bd08`, modo `600`). `pg_restore --list`: 197 linhas.

Depois: organização, usuário e todas as tabelas com `organizacao_id` da `gigio-teste` em 0. A `boulangerie` ficou com a mesma contagem de cada tabela. Só ela permanece em `organizacoes`.

## 8. Publicação

- Antes da carga: 910 MB de memória disponíveis, 19,7 GB livres. Imagem que estava no ar: `012-20261106`.
- `gestao-api` recriado com `lojadepaes-gestao:012a-20261106`, sem Alembic e sem catálogo. Health e ready 200.
- O JavaScript servido (`index-riA8cnlK.js`) tem o mesmo SHA-256 na imagem, no contêiner e em `https://gestao.lojadepaes.com.br/`: `2ebd9c24ce7bfac35f74dab777f26cec5d75cc33c47b8c893d3d30e1f535c05c`.
- `https://lojadepaes.com.br/` 200. `pg_stat_user_tables` da Loja igual antes e depois: `media_assets` 16/0/0, `product_variants` 16/6/6, `products` 16/35/6, `showcase_slots` 10/16/0.
- SSH na porta 22 ficou aberta só para os IPs desta sessão e essas regras foram fechadas. Voltaram as 29 regras que já existiam. 80 e 443 seguem em `0.0.0.0/0`. Chave temporária e o tar da imagem foram removidos.

## 9. Rollback

A imagem `012-20261106` continua no host. Recolocar `GESTAO_IMAGE=lojadepaes-gestao:012-20261106` e recriar só o `gestao-api`. O banco não mudou de esquema. O dump `gestao-pre012a.dump` está no host. A `gigio-teste` não volta com a imagem anterior: ela foi apagada de propósito.

## Checklist

1. **Feito.** Passo 1 com as linhas, passo 3 no painel largo e a receita do Pão de Canela sem duplicar a base, com "—" no componente.
2. **Feito.** Os dois casos do `gigio-ensaio`, com a contagem igual antes e depois e `gravou=0`.
3. **Feito.** 260 testes do backend, 11 do Gigio depois da correção do nome, 83 do frontend.
4. **Feito.** Inventário, dump e contagem 0 da `gigio-teste`. A `boulangerie` com a mesma contagem antes e depois.
5. **Feito.** Padrões em 390 e 1280. Rendimento e lista com o custo parcial do 011.
6. **Feito.** Imagem no ar. `lojadepaes.com.br` 200. Este retorno e as capturas estão no mesmo commit, com push da branch.
