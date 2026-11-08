# GESTAO-007A — Lista de Entradas de volta ao padrão

Base: `feat/gestao-007-lote` (`8357a132`). Branch: `feat/gestao-007a-lista`. Só frontend. Imagem em produção: `lojadepaes-gestao:007a-20261104` (anterior: `007-20261104`).

Regra do ciclo cumprida: na Loja de Pães só foram feitos os dois pontos autorizados (SSH só para o meu IP, fechado só a minha regra; rebuild e restart do `gestao-api`). **Não houve migração.** O deploy rodou com `GESTAO_SEM_BANCO=1`. Nenhum dado de produção foi alterado.

## 1. O que mudou

A linha da entrada tinha voltado a ficar misturada: título de tamanho variável, lotes e valor sem coluna, sem cabeçalho, e o selo "Completa" em todas as linhas.

A lista agora é uma tabela com cabeçalho **Data · Entrada · Itens · Valor · Situação**. Itens e Valor ficam à direita, com algarismos tabulares. Na coluna Entrada, o motivo (e o fornecedor, se houver) vem em destaque; os itens ficam numa segunda linha cinza, numa linha só, cortada com reticências, e o nome inteiro aparece ao passar o mouse.

Os lotes saíram da linha. Continuam na linha expandida e na busca, como no 007. A situação só aparece quando há exceção: selo âmbar **Pendente**. A entrada completa fica com um travessão, sem selo.

A linha expandida mantém a tabela item · ingrediente · quantidade · lote · validade · custo · ações, com os cabeçalhos na largura das colunas. As ações ficam no menu ⋯ (Corrigir custo, Trocar ingrediente e, quando falta, Informar validade).

No celular cada entrada é um cartão: data e valor, o motivo, os itens em cinza. Sem faixa de lotes. O selo Pendente fica na primeira linha, só quando há pendência.

`docs/PROJETO-INTERFACE.md` ganhou a regra: toda lista tem cabeçalho e colunas fixas, números à direita; selo só para exceção; código de lote ou ID no detalhe e na busca, não na linha principal.

## 2. Testes (só os da área)

| Onde | Resultado |
|---|---|
| Frontend `buscaLista.test.ts`, `buscaLote.test.tsx` e `fluxo.test.tsx` | **39 passed** |
| `eslint --max-warnings 0` nos arquivos tocados, `tsc --noEmit`, `npm run build` | limpos |

| Pedido | Teste |
|---|---|
| A linha mostra o motivo e os itens, sem o código do lote, e a completa não leva selo | `buscaLote.test.tsx`: "a linha mostra o motivo e os itens, sem o lote…" (título no mouse, travessão, sem "Completa" e sem `E20261103`) |
| A pendente leva o selo e a completa não | `fluxo.test.tsx`: a linha "Compra sem nota · Atacadão" tem "Pendente" e não tem "Completa"; cabeçalho "Entrada" |
| A busca por "-12" ainda abre a linha com o lote em destaque | o mesmo teste do 007, na região expandida |
| "Corrigir custo" no menu ⋯ grava com histórico, como o 006 | `buscaLote.test.tsx` e os dois testes de "Corrigir custo" em `fluxo.test.tsx`: o menu traz "Corrigir custo" e "Trocar ingrediente"; o envio segue `{ valor_pago, motivo }` |

## 3. Capturas locais (1280 e 390 px)

Ambiente **local**, banco de demonstração (`scripts/seed-demo-gestao-007.py` e `scripts/seed-demo-gestao-007a.py`, `scripts/capture-gestao-007a.mjs`). Em `docs/evidence/gestao-007a-local/`. Checagem em `capturas.md`: sem rolagem horizontal da página; controles com 40 px (44 no celular).

| O que mostra | 1280 | 390 |
|---|---|---|
| A lista, com cabeçalho, itens alinhados e a completa sem selo | `lista-1280.png` | `lista-390.png` |
| Uma linha expandida (lote, validade, custo e o menu ⋯) | `entrada-expandida-1280.png` | `entrada-expandida-390.png` |
| Uma pendente, com o selo âmbar | `pendente-1280.png` | `pendente-390.png` |

## 4. Publicação (procedimento do 002)

- Antes: 989 MB de memória disponíveis, 21 GB livres. Imagem no ar: `007-20261104`.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.224.51`; não estava entre as 29) e **fechada em seguida**. Conferi que voltou a 29 regras. Chave temporária e o tar local removidos. O tar no host também foi apagado depois do `docker load`.
- `remote-deploy.sh` com `GESTAO_SEM_BANCO=1`: "banco: nada a fazer neste deploy". `gestao-api` recriado e `healthy` com `lojadepaes-gestao:007a-20261104` (anterior: `lojadepaes-gestao:007-20261104`).
- Dentro do contêiner: `/api/v1/health` **200**, `/api/v1/ready` **200**. O JavaScript servido (`index-Bx7dZiPg.js`) tem o mesmo SHA-256 do build local (`8f306df6f06b676f4a9dc7b9a5817ad4a1bfbd02e5f76c2973e4db0db2bf00a8`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Loja intocada. **Sem dados de teste em produção.**

## 5. Rollback

No host, `GESTAO_IMAGE=lojadepaes-gestao:007-20261104` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api`. A imagem 007 segue no host. O banco não mudou.
