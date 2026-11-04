# GESTAO-007 — Achar o lote sem procurar

Base: `feat/gestao-006-valor-pago` (`463f71e2`). Branch: `feat/gestao-007-lote`. Imagem em produção: `lojadepaes-gestao:007-20261104` (anterior: `006-20261103`).

Regra do ciclo cumprida: na Loja de Pães só foram feitos os dois pontos autorizados (SSH só para o meu IP, fechado só a minha regra; rebuild e restart do `gestao-api`). **Não houve migração nem carga de catálogo.** O deploy rodou com `GESTAO_SEM_BANCO=1`. Nenhum dado de produção foi alterado.

## 1. O que mudou

A lista de Entradas deixava seis linhas iguais (“Contagem de estoque · Sem nota · 3 itens”) e a de Ingredientes só dizia “1 item · 1 lote”. O código do lote não aparecia.

- **Entradas.** O texto principal são os itens (“Fubá Orgânico, Trigo Sarraceno e mais 1”). Motivo e “Sem nota” ficam na segunda linha. À direita, os lotes (“E20261103-12 a -14”, ou o código único). Abrir a linha expande no lugar uma tabela: item, ingrediente, quantidade, lote, validade, custo por kg, L ou un, e as ações **Corrigir custo** e **Trocar ingrediente**. “Ver detalhes” continua abrindo o painel.
- **Ingredientes.** A seta da linha expande no lugar: cada item e, embaixo, os lotes (código, quantidade, validade, custo, **Corrigir custo**). O painel lateral segue como estava; cada lote nele também tem **Corrigir custo** e o selo.
- **Busca.** “Buscar item, ingrediente ou lote” no topo das duas telas. Aceita parte do código (“-12” ou “E20261103-12”), ignora acento e maiúsculas, e mantém o hífen (um “-12” não casa com o 12 da data). A linha encontrada já abre expandida, com o lote destacado.
- **Depois de corrigir.** O lote ganha o selo “custo corrigido”. Ao passar o mouse ou tocar, mostra o antes e o depois. O histórico é o mesmo da 006 (`correcoes_custo`); nada de coluna nova.

## 2. Testes (só os da área)

| Onde | Resultado |
|---|---|
| Backend `tests/test_lote_na_lista.py` (novo) + `test_estoque.py` + `test_valor_pago.py` | **47 passed** |
| Frontend `buscaLista.test.ts`, `buscaLote.test.tsx` (novos) e `fluxo.test.tsx` | **39 passed** |
| `ruff check` nos arquivos novos, `tsc --noEmit`, `eslint --max-warnings 0` nos arquivos tocados, `npm run build` | limpos |

| Pedido | Teste |
|---|---|
| A busca por “-12” acha `E20261103-12` e não um 12 no meio da data | `buscaLista.test.ts`: “'-12' acha o lote E20261103-12…”; na tela, `buscaLote.test.tsx`: “a linha lista os itens e os lotes, e '-12' abre essa linha com o lote em destaque” |
| A busca por “fuba” acha “Fubá Orgânico” | `buscaLista.test.ts`: “'fuba' acha Fubá Orgânico…”; na tela, “'fuba' acha Fubá Orgânico e abre os lotes” |
| A linha da entrada lista os itens e os lotes | `test_lista_da_entrada_traz_os_itens_e_os_lotes`; `buscaLista.test.ts`: “a linha resume os itens e o intervalo de lotes” (“Fubá Orgânico, Trigo Sarraceno e mais 1”, “E20261103-12 a -14”) |
| “Corrigir custo” na linha expandida grava com histórico, como o 006 | `test_corrigir_custo_na_entrada_grava_historico_e_o_selo`; na tela, “'Corrigir custo' na linha expandida grava o valor pago e o motivo…” (`valor_pago` 20, motivo “Achei a nota”, selo “custo corrigido”) |

## 3. Capturas locais (1280 e 390 px)

Ambiente **local**, banco de demonstração (`scripts/seed-demo-gestao-007.py`, `scripts/capture-gestao-007.mjs`). Em `docs/evidence/gestao-007-local/`. Checagem em `capturas.md`: sem rolagem horizontal da página; controles com 40 px (44 no celular). No celular a tabela vira um cartão por item, para validade, custo e ações caberem na tela.

| O que mostra | 1280 | 390 |
|---|---|---|
| Entradas com a linha expandida (itens, lotes, custo, Corrigir custo, Trocar ingrediente, selo) | `entradas-expandida-1280.png` | `entradas-expandida-390.png` |
| Busca por “-12”: a linha aberta e o lote `E20261103-12` destacado | `busca-lote-1280.png` | `busca-lote-390.png` |
| Ingredientes com os lotes expandidos e o selo “custo corrigido” | `ingredientes-lotes-1280.png` | `ingredientes-lotes-390.png` |

## 4. Publicação (procedimento do 002)

- Antes: 989 MB de memória disponíveis, 21 GB livres. Imagem no ar: `006-20261103`.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.224.51`; não estava entre as 29) e **fechada em seguida**. Conferi que não ficou e que as 29 regras antigas continuam. Chave temporária e o tar local removidos. O tar no host também foi apagado depois do `docker load`.
- `remote-deploy.sh` com `GESTAO_SEM_BANCO=1`: “banco: nada a fazer neste deploy”. `gestao-api` recriado e `healthy` com `lojadepaes-gestao:007-20261104` (anterior: `lojadepaes-gestao:006-20261103`).
- Dentro do contêiner: `/api/v1/health` **200**, `/api/v1/ready` **200** (`gestao_db`, `sessao` e `loja_leitura`). O JavaScript servido (`index-XSLvPAfv.js`) tem o mesmo SHA-256 do build local (`5a3b149968920ecbe611a848bbce956c4e799711485d3e6fbfd640c391856406`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Loja intocada. **Sem dados de teste em produção.**

## 5. Rollback

No host, `GESTAO_IMAGE=lojadepaes-gestao:006-20261103` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api`. A imagem 006 segue no host. O banco não mudou.
