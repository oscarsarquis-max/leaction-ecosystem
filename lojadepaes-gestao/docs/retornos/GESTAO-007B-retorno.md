# GESTAO-007B — Lista de Ingredientes no mesmo padrão da de Entradas

Base: `feat/gestao-007a-lista` (`2b435d47`). Branch: `feat/gestao-007b-ingredientes`. Só frontend. Imagem em produção: `lojadepaes-gestao:007b-20261105` (anterior: `007a-20261104`).

Regra do ciclo cumprida: na Loja de Pães só foram feitos os dois pontos autorizados (SSH só para o meu IP, fechado só a minha regra; rebuild e restart do `gestao-api`). **Não houve migração.** O deploy rodou com `GESTAO_SEM_BANCO=1`. Nenhum dado de produção foi alterado. A pasta `C:\Projetos\lojadepaes-gestao` não foi movida, apagada nem renomeada.

## 1. O que mudou

A lista de ingredientes era uma faixa sem cabeçalho: a seta ficava numa coluna com borda, o selo "Em dia" aparecia em todas as linhas e, ao expandir, o código, a quantidade, a validade e o custo ficavam soltos. O selo "custo corrigido" era alto, com o texto colado no topo.

A lista agora é uma tabela com cabeçalho **Ingrediente · Saldo · Vence primeiro · Situação**. O saldo fica à direita, com algarismos tabulares. A categoria e "N itens · N lotes" vão na segunda linha, em cinza. A seta fica dentro da célula do nome, sem coluna e sem borda própria. O nome continua abrindo o painel.

A situação só aparece na exceção: **Sem saldo**, **Vence em 7 dias** e **Parecidos**. O dia comum fica com um travessão.

A área expandida é uma tabela no mesmo desenho da linha de Entradas: **Item / Lote · Quantidade · Validade · Custo · Ações**. Cada item é uma sub-linha em negrito, com os lotes embaixo. O menu ⋯ traz Corrigir custo e Trocar ingrediente.

"custo corrigido" é uma etiqueta pequena, numa linha só, ao lado do custo, no mesmo estilo dos outros selos. O antes e o depois aparecem ao passar o mouse ou ao tocar.

No celular o cartão mostra o nome e o saldo, a categoria e o selo, se houver. Ao expandir, os lotes viram uma lista: código · quantidade · validade · custo.

## 2. Testes (só os da área)

| Onde | Resultado |
|---|---|
| Frontend `buscaLista.test.ts`, `buscaLote.test.tsx` e `fluxo.test.tsx` | **40 passed** |
| `eslint --max-warnings 0` nos arquivos tocados, `tsc --noEmit`, `npm run build` | limpos |

| Pedido | Teste |
|---|---|
| O normal leva travessão e não o selo "Em dia"; a exceção leva o selo | `fluxo.test.tsx`: Açúcar tem "—" e não tem "Em dia"; Farinha tem "Vence em 7 dias" e "Parecidos"; Sal tem "Sem saldo" |
| A linha expandida tem cabeçalho, o lote e o selo "custo corrigido" | `fluxo.test.tsx`: região "Lotes de Farinha de trigo", colunas "Item / Lote" e "Quantidade", texto "custo corrigido" |
| O menu ⋯ traz Corrigir custo e Trocar ingrediente | o mesmo teste, itens "Corrigir custo" e "Trocar ingrediente" |
| A busca por "fuba" ainda abre os lotes | `buscaLote.test.tsx`: região "Lotes de Fubá Orgânico" com `E20261103-12` |

## 3. Capturas locais (1280 e 390 px)

Ambiente **local**, banco de demonstração já semeado nos ciclos 007 e 007A (`scripts/capture-gestao-007b.mjs`). Em `docs/evidence/gestao-007b-local/`. Checagem em `capturas.md`: sem rolagem horizontal da página; controles com 40 px (44 no celular). A etiqueta "custo corrigido" é um selo pequeno, de propósito, e fica fora dessa medida.

| O que mostra | 1280 | 390 |
|---|---|---|
| A lista, com cabeçalho e sem selo nas linhas normais | `lista-1280.png` | `lista-390.png` |
| Uma linha expandida, com o cabeçalho da tabela (no computador) e o lote com "custo corrigido" | `expandida-1280.png` | `expandida-390.png` |

No celular a lista vira cartão (nome e saldo, categoria) e os lotes viram a lista simples, com a mesma etiqueta ao lado do custo.

## 4. Publicação (procedimento do 002)

- Antes: 895 MB de memória disponíveis, 21 GB livres. Imagem no ar: `007a-20261104`.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.224.96`; não estava entre as 29) e **fechada em seguida**. Conferi que voltou a 29 regras. Chave temporária e o tar local removidos. O tar no host também foi apagado depois do `docker load`.
- `remote-deploy.sh` com `GESTAO_SEM_BANCO=1`: "banco: nada a fazer neste deploy". `gestao-api` recriado e `healthy` com `lojadepaes-gestao:007b-20261105` (anterior: `lojadepaes-gestao:007a-20261104`).
- Dentro do contêiner: `/api/v1/health` **200**, `/api/v1/ready` **200**. O JavaScript servido (`index-0RdsAzNi.js`) tem o mesmo SHA-256 do build local (`0db3ac03a57ca663c27617b6a470919057b55dad9712e40e9bc4299f416ec670`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Loja intocada. **Sem dados de teste em produção.**

## 5. Rollback

No host, `GESTAO_IMAGE=lojadepaes-gestao:007a-20261104` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api`. A imagem 007A segue no host. O banco não mudou.

## 6. Pasta antiga (só leitura)

`C:\Projetos\lojadepaes-gestao` não é um checkout. Nada foi movido, apagado ou renomeado.

Só nela (9), cache e metadado de instalação:

- `backend/.ruff_cache/0.17.3/11291311054574184913`
- `backend/.ruff_cache/0.17.3/11977808701469560981`
- `backend/.ruff_cache/0.17.3/1291622354866290394`
- `backend/.ruff_cache/0.17.3/4005513091308367242`
- `backend/lojadepaes_gestao.egg-info/PKG-INFO`
- `backend/lojadepaes_gestao.egg-info/SOURCES.txt`
- `backend/lojadepaes_gestao.egg-info/dependency_links.txt`
- `backend/lojadepaes_gestao.egg-info/requires.txt`
- `backend/lojadepaes_gestao.egg-info/top_level.txt`

O mesmo caminho com bytes diferentes (52): `.gitattributes`; `backend/app/api/v1/auth.py`, `estoque.py`, `hoje.py`, `router.py`; `backend/app/catalogo/catalogo-ingredientes.yaml`; `backend/app/domain/auth.py`, `custos.py`, `entradas.py`, `ingredientes.py`; `backend/app/main.py`; `backend/pyproject.toml`; `backend/tests/conftest.py`; `backend/tests/fixtures/catalogo-ingredientes-v1.yaml`; `backend/tests/fixtures/loja_schema_e7b3c9a41d06.sql`; `backend/tests/test_organizacoes.py`; `backend/tests/test_sugestao_qualificadores.py`; `deploy/remote-deploy.sh`; `deploy/s3_put.py`; `docs/PROJETO-INTERFACE.md`; capturas de `gestao-002`, `gestao-003`, `gestao-003-local`, `gestao-004-local`, `gestao-005-local`, `gestao-005a-local`, `gestao-006-local` (`capturas-1280.md` e `capturas-390.md`); `frontend/index.html`; `frontend/src/App.test.tsx`; `frontend/src/lib/api.ts`, `entradaForm.ts`, `format.ts`; `frontend/src/pages/EntradaSemNota.tsx`, `Entradas.tsx`, `Hoje.test.tsx`, `Hoje.tsx`, `Ingredientes.tsx`, `Login.test.tsx`, `Login.tsx`, `fluxo.css`, `fluxo.test.tsx`, `pages.css`; `frontend/src/shell/Shell.tsx`, `Sidebar.tsx`, `Topbar.tsx`, `shell.css`, `tokens.css`; `frontend/src/test-setup.ts`; `scripts/capture-evidence.mjs`, `capture-gestao-006.mjs`, `seed-demo-gestao-006.py`.
