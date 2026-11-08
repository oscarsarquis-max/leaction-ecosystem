# GESTAO-012B — Gigio: contas no servidor e salvaguardas de padaria

Base: `feat/gestao-012a-gigio` (`2be7d3ef`). Branch: `feat/gestao-012b-gigio`. Imagem em produção: `lojadepaes-gestao:012b-20261106`. A anterior, `lojadepaes-gestao:012a-20261106`, continua no host.

Não houve migração. O Alembic segue em `0008_gigio`. `carregar-catalogo` não rodou. O ensaio rodou com `--sem-gravar` e não criou linha.

## O que mudou

O modelo devolve o % sobre a farinha. O servidor calcula os gramas quando a farinha já é conhecida (`gramas = % × farinha`) e ignora os gramas que o modelo manda. O % que aparece na tela é sempre recalculado dos gramas. Um % fora da faixa da própria linha vai para o limite mais próximo, com aviso.

Sem massa-base, os gramas das farinhas são a escala. O % exibido é `gramas ÷ farinha`, então 390 g de água em 625 g de farinha (farinha mais sêmola) ficam 62,4 %, e não os 78 % que o modelo tenha afirmado. Se o modelo não manda grama nenhuma, a conta usa 1 kg de farinha e avisa.

A farinha é a soma da categoria Farinhas, também dentro dos componentes. Sêmola entra nessa soma.

As verificações ficam em `app/domain/verificacoes.py` e valem para a sugestão e para a receita, na aba Revisar. Sem agente de fermentação é pendência: o backend faz uma nova chamada pedindo o fermento e, se ainda faltar, mostra "Falta o fermento" e só aplica com confirmação. Sal fora de 1,5–2,5 % avisa. Hidratação fora da faixa da família avisa; as faixas estão em `app/domain/faixas_familia.yaml` (Sovado 55–68 %, Rústico 65–85 %, Focaccia 70–90 %). Ingrediente repetido entre a linha e um componente avisa, por exemplo "Sal já está na Massa sovada. Somar mesmo assim?".

Fermento ou sal que não estão no estoque podem usar o nome do catálogo. A linha fica "a decidir · não está no seu estoque". "Longa maturação" ou "fermentação natural" puxa o levain ou o PFF no % do padrão da casa.

Confiança alta só em linha fixa ou em padrão da casa (o termo do padrão está no nome e o % bate, com folga de 0,5). O que a descrição pede fica no máximo média. O que a descrição não cita fica baixa. Escrever "padrão da casa" no motivo não eleva a confiança.

`substitui_na_base` aparece no bloco "Altera a massa-base". Aplicar troca farinha da base por integral e mantém a farinha total. O passo 3 não repete o texto de contexto. A tela Padrões tem o cabeçalho Padrão, Ingrediente, %, Observação, linhas compactas, o botão Novo padrão e a edição no mesmo painel. A aba Perdas ficou para o 013.

## Testes

| Onde | Resultado |
|---|---|
| `pytest tests/test_verificacoes_012b.py tests/test_gigio.py` | **18 passed** |
| `pytest` no backend | **268 passed** |
| `vitest` no frontend | **83 passed** |
| `ruff` nos arquivos do ciclo | limpo |

O teste da Focaccia passa 390 g de água e 625 g de farinha (500 g de farinha de trigo e 125 g de sêmola) e exige 62,4 %, nunca 78 %. O açúcar sugerido a 10 % sobre 300 g de farinha vira 30 g e permanece na faixa 8–15 %. Receita sem fermento gera a pendência e uma única chamada extra. Sal a 3,3 % avisa, e Sal fixo junto da Massa sovada avisa a repetição. Confiança alta que não é linha fixa nem padrão desce. A substituição mantém a farinha total (500 g viram 425 g mais 75 g).

## Capturas locais

`scripts/capture-gestao-012b.mjs`, com o gateway falso, em `docs/evidence/gestao-012b-local/`. Checagem em `capturas.md`: sem rolagem horizontal e controles de 40 px (44 abaixo de 960), em 1280 e 390.

- O passo 3 mostra o bloco "Altera a massa-base" (15,1 % da farinha da base por integral, 45 g) e os avisos de sal repetido e de fermento faltando. O pé não traz "Descrição do padeiro". O açúcar da sugestão fica em 30 g, cerca de 10 %, dentro de 8–15 %.
- A aba Revisar do Pão de Canela mostra "Falta o fermento.", o sal em 5,4 % e "Sal já está na Massa sovada. Somar mesmo assim?".
- Padrões tem o cabeçalho, as linhas compactas e o botão Novo padrão.

## Ensaio em produção

`python -m app.cli gigio-ensaio --sem-gravar --organizacao boulangerie`, dentro de `gestao-api`, na imagem `012b-20261106`. Modelo `us.anthropic.claude-sonnet-4-6`.

As quatro primeiras quantidades da base do Pão de Canela são as do pedido (Farinha de trigo 500 g, Água 300 g, Água residual do fermento 30 g, Leite em pó 50 g). As outras quatro, que o pedido não numerou, ficaram: Fermento 5 g, Sal 10 g, Açúcar 20 g, Gordura 40 g. A farinha contida é 500 g. A Focaccia não tem massa-base.

Contagem antes e depois: organizacoes 1, produtos 10, receitas 10, receita_linhas 0, gigio_sugestao 0, padrao_padaria 5, ingredientes 10. `gravou=0`.

### Pão de Canela sobre a Massa sovada

Tokens 2176 / 892. Farinha contida 500 g. Rendimento e perda não informados.

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
| Coco queimado | 10 % | 50 g | 8–15 % | média | Inclusão pedida pelo padeiro |
| Canela em pó | 1,6 % | 8 g | 1–2,5 % | média | Calda de canela e aroma no miolo |

Altera a massa-base: Farinha de trigo integral, 20 %, 100 g, confiança média. O motivo diz que substitui 20 % da farinha de trigo da base. Não entrou como linha a mais. Aviso: "Farinha de trigo integral entrou como substituição da farinha da base, não como acréscimo." O açúcar repetido foi descartado.

Os percentuais das inclusões estão dentro das próprias faixas. Alta só nas linhas já incluídas na base. Coco e canela, citados na descrição, ficam em média.

### Focaccia Alta

Tokens 2048 / 1287. Farinha contida 100 g, a escala que o modelo informou em gramas. Rendimento 240 g. Perda 10 %. A descrição pública pede longa maturação, e o levain entrou a 20 %, o padrão da casa.

| Linha | % | Quantidade | Faixa | Confiança | Motivo |
|---|---|---|---|---|---|
| Farinha de trigo tipo 00 | 100 % | 100 g | — | baixa | Base da focaccia |
| Água | 80 % | 80 g | 70–90 % | baixa | 80 g ÷ 100 g de farinha |
| Levain | 20 % | 20 g | — | alta | Longa maturação, padrão da casa |
| Sal marinho | 2 % | 2 g | — | baixa | Referência clássica; não é padrão da casa |
| Azeite de oliva | 5 % | 5 g | — | baixa | Gordura na massa |
| Alho confitado | 8 % | 8 g | 5–12 % | média | Pedido do padeiro |
| Tomate cereja | 20 % | 20 g | 15–30 % | média | Pedido do padeiro |
| Alecrim | 1 % | 1 g | 0,5–2 % | média | Pedido do padeiro |
| Azeite de oliva (finalização) | 4 % | 4 g | 3–6 % | baixa | Acabamento |

A água está em 80 %, que é 80 g sobre 100 g de farinha, dentro de 70–90 %. Não há um 78 % solto em cima de outra farinha. O teste automático cobre o caso em que os gramas e o % do modelo discordam: 390 g em 625 g aparecem como 62,4 %.

## Imagem

`https://lojadepaes.com.br/` respondeu 200. `https://gestao.lojadepaes.com.br/` respondeu 200, com `/api/v1/health` e `/api/v1/ready` em 200. O JavaScript servido é `index-DC2nx5pE.js`, SHA-256 `9f6c9042c3fe4f712864142754dbd5fc3641a54bfda4f15a7dbe9d1b1c5435a9`, o mesmo da imagem local, do contêiner e da página.

O deploy usou `GESTAO_SEM_BANCO=1`. Nenhum dado de teste entrou no banco. A Loja não mudou: media_assets 16/0/0, product_variants 16/6/6, products 16/35/6, showcase_slots 10/16/0, antes e depois.

A regra de SSH aberta para este ciclo foi fechada. A porta 22 voltou às 29 regras que já existiam. As portas 80 e 443 seguem abertas para a internet.

## Checklist

1. **Feito.** Os testes novos passam (18, junto com os do Gigio). A suíte do backend ficou em 268.
2. **Feito.** O ensaio `--sem-gravar` rodou de novo nos dois casos. A Focaccia tem levain a 20 % e a água em 80 % (80 g ÷ 100 g). O Pão de Canela traz o integral como substituição. Os percentuais das inclusões ficam nas faixas. A confiança alta ficou nas linhas fixas e no levain, que é o padrão da casa. Contagem antes igual à depois. `gravou=0`.
3. **Feito.** Capturas em 1280 e 390 do passo 3 (bloco "Altera a massa-base" e aviso), da aba Revisar e da tela Padrões. `docs/evidence/gestao-012b-local/capturas.md`.
4. **Feito.** A imagem `012b-20261106` está no ar. `lojadepaes.com.br` respondeu 200. Este retorno e as capturas entram no mesmo commit, com o push da branch.
