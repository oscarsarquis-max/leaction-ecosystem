# GESTAO-007D — Ingrediente juntado volta a ter saída

Base: `feat/gestao-007c-trocar` (`8bfb8307`). Branch: `feat/gestao-007d-juntado`. Imagem em produção: `lojadepaes-gestao:007d-20261105` (anterior: `007c-20261105`).

Regra do ciclo cumprida: na Loja de Pães só foram feitos os pontos autorizados (SSH só para o meu IP, fechado só a minha regra; leitura no banco `gestao`; rebuild e restart do `gestao-api`). **Não houve migração** e **nenhum dado de produção foi alterado**. O deploy rodou com `GESTAO_SEM_BANCO=1`. Quem reativa e troca em produção continua sendo o Oscar, pela tela. A reativação e a troca das capturas são só no banco local de demonstração.

## 1. Diagnóstico (só leitura, organização boulangerie)

| Ingrediente | Ativo | Juntado em | Itens | Lotes | Saldo |
|---|---|---|---|---|---|
| Farinha de Trigo sarraceno | sim | — | 1 (Trigo Sarraceno, Leve Croc) | 1 | 500 g |
| Farinha de trigo integral | sim | — | 1 (Nita 100% Integral, Nita) | 1 | 2.000 g |
| Farinha de trigo tipo 0 | sim | — | 4 | 8 | 20.000 g |
| Farinha de trigo tipo 00 | não | Farinha de trigo tipo 0 | 0 | 0 | 0 |
| Farinha de trigo tipo 1 | não | Farinha de trigo tipo 0 | 0 | 0 | 0 |

No tipo 0 estão: Farinha de Trigo Doppio Zero (Caputo, 2 lotes, 4.000 g), Farinha de Trigo Nita 00 (Nita, 1 lote, 4.000 g), Farinha de Trigo Superiore (Globo, 4 lotes, 8.000 g) e Farinha de Trigo Tipo Nuvola (Caputo, 1 lote, 4.000 g).

Junções, todas por Loja de Pães (`admin@lojadepaes.com.br`), horário de São Paulo:

| Quando | O que saiu | O que ficou | Motivo |
|---|---|---|---|
| 03/11/2026 17:42:45 | Farinha de trigo tipo 00 | Farinha de trigo tipo 0 | Junção: “Farinha de trigo tipo 00” passou para “Farinha de trigo tipo 0” (duas linhas, a da Doppio Zero e a da Nita 00) |
| 03/11/2026 17:42:48 | Farinha de trigo tipo 1 | Farinha de trigo tipo 0 | Junção: “Farinha de trigo tipo 1” passou para “Farinha de trigo tipo 0” (Superiore) |

Depois do deploy, a mesma leitura: tipo 00 segue inativo, juntado ao tipo 0, e `atualizado_em` continua 03/11/2026 20:01 UTC. Nada foi reativado nem trocado em produção.

A causa: em 03/11 a junção inativou "Farinha de trigo tipo 00" dentro de "Farinha de trigo tipo 0" (a Nita 00 e a Doppio Zero foram junto), e a busca ainda oferece esse nome pelo catálogo; escolher manda o id inativo para a troca, que só mandava escolher o que ficou, e cadastrar de novo esbarra no nome que já existe.

## 2. O que mudou

A busca e as sugestões não oferecem ingrediente inativo ou juntado. O nome que bate com um juntado volta numa oferta à parte, com o destino e o dia. Vale para a entrada, Trocar ingrediente e Cadastrar novo, que usam a mesma busca. Produtos ainda não tem busca de ingrediente.

Quando o nome escolhido ou digitado é um ingrediente juntado, o diálogo diz **Farinha de trigo tipo 00** foi juntado a *Farinha de trigo tipo 0* em 03/11 e o botão é **Reativar como ingrediente separado**. Reativar não move item nenhum: só deixa o ingrediente disponível de novo, com o motivo e uma linha de histórico (Reativação). A troca dos itens continua com a pessoa.

A mensagem de erro da troca deixa de dizer "Escolha o que ficou". Diz para reativar se quiser usar aquele ingrediente separado, e o botão Reativar aparece quando cabe. Cadastrar o mesmo nome de um inativo devolve o mesmo caminho, em vez de um 409 sem saída.

Juntar respeita os qualificadores do 005A. O aviso de pares parecidos não propõe 00 com 0, nem seco com fresco. A API recusa com `422` e código `qualificadores_diferentes`.

Não houve migração. O histórico da reativação é um movimento do tipo que já existia, com o motivo marcado.

## 3. Testes

| Onde | Resultado |
|---|---|
| `test_reativar.py`, `test_ingrediente_busca.py`, `test_estoque.py`, `test_valor_pago.py` | **92 passed** |
| `trocarIngrediente.test.tsx`, `fluxo.test.tsx`, `buscaLote.test.tsx`, `buscaLista.test.ts` | **43 passed** |
| `ruff` nos arquivos do backend tocados, `eslint --max-warnings 0`, `tsc` e `npm run build` | limpos |

Os testes novos, que descrevem o que travava:

| Pedido | Teste |
|---|---|
| A busca não traz o juntado; reativar não move o saldo; a troca depois grava | `test_busca_nao_traz_o_juntado_reativar_nao_move_e_depois_a_troca_funciona` e "o juntado não aparece na busca: reativar e só então a troca grava" |
| Juntar 00 com 0 (e seco com fresco) dá 422 `qualificadores_diferentes`, e o aviso de pares não propõe esse par | `test_pares_nao_propoem_00_com_0_e_a_api_recusa` |
| Trocar para o inativo diz para reativar, sem "Escolha o que ficou"; cadastrar o mesmo nome aponta o reativar | `test_trocar_para_o_inativo_diz_para_reativar` |

## 4. Capturas locais (1280 e 390 px)

Ambiente **local** (`scripts/capture-gestao-007d.mjs`). Em `docs/evidence/gestao-007d-local/`. Checagem em `capturas.md`: diálogo na área visível, sem rolagem horizontal, controles com 40 px (44 no celular).

A demonstração junta o tipo 00 à farinha genérica "Farinha de trigo", porque a API agora recusa 00 com 0. O dia da junção local é 05/11. Em produção o destino real continua sendo o tipo 0, em 03/11, e ninguém reativou isso daqui.

| O que mostra | 1280 | 390 |
|---|---|---|
| O diálogo "Reativar como ingrediente separado" | `reativar-1280.png` | `reativar-390.png` |
| A lista depois de reativar e mover, com o aviso e os dois saldos | `depois-1280.png` | `depois-390.png` |

Na demonstração local, o item "Farinha de Trigo Nita 00" (1 lote, 1 kg) saiu de Farinha de trigo (que ficou em 0 g) e foi para Farinha de trigo tipo 00 (1 kg). O aviso diz "Movido para Farinha de trigo tipo 00".

## 5. Publicação (procedimento do 002)

- Antes: 871 MB de memória disponíveis, 20 GB livres. Imagem no ar: `007c-20261105`.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.224.96`; não estava entre as 29) e **fechada em seguida**. Conferi que voltou a 29 regras. 80 e 443 seguem em `0.0.0.0/0`. Chave temporária e os tars (local e no host) removidos.
- `remote-deploy.sh` com `GESTAO_SEM_BANCO=1`: "banco: nada a fazer neste deploy". `gestao-api` recriado e saudável com `lojadepaes-gestao:007d-20261105` (anterior: `lojadepaes-gestao:007c-20261105`).
- O JavaScript servido (`index-DNpJZSBv.js`) tem o mesmo SHA-256 do build local e da imagem (`c6702b4a9223129698d3c718cd6f1d92d18e714489b6b644c767b54813759525`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Loja intocada. **Nenhum ingrediente de produção foi reativado nem trocado.**

## 6. Rollback

No host, `GESTAO_IMAGE=lojadepaes-gestao:007c-20261105` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api`. A imagem 007C segue no host. O banco não mudou.
