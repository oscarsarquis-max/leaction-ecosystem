# GESTAO-005 — Ingrediente: buscar antes de cadastrar e sugerir pela entrada

Base: `feat/gestao-004-ajustes` (`447f551f`). Branch: `feat/gestao-005-ingrediente`. Imagem em produção: `lojadepaes-gestao:005-20261103`.

Regra do ciclo cumprida: dentro da Loja de Pães só foram feitos os três pontos autorizados (SSH só para o meu IP, rebuild/restart do `gestao-api`, migração no banco `gestao` sem `CREATE EXTENSION`). Nada mais foi tocado.

## 1. O que mudou

**Ninguém cadastra ingrediente sem antes ter certeza de que ele não existe.** A entrada deixou de criar ingredientes: ela só **aponta** para um que já existe.

| Peça | Como ficou |
|---|---|
| Modelo | `ingrediente` ganhou `categoria` (as 13 do pedido; padrão “Outros”), `apelidos` (lista de textos) e, quando alguém confirma “não existe” diante de um parecido, **quem** confirmou e **quando**. |
| Comparação | Em Python (`rapidfuzz`), **sem extensão no Postgres**. Não contam: acento, maiúscula, plural, ordem das palavras, palavras vazias (de, da, tipo) e o peso no nome (“1 kg”, “500 g”). O número do produto **conta** (“tipo 00” ≠ “tipo 0”). Enquanto digita, vale palavra incompleta. |
| Catálogo | Tabela global `catalogo_ingrediente` (sem organização), 70 ingredientes / 12 categorias, do `catalogo-ingredientes.yaml` (versão 1) copiado **sem alterar** (hash conferido). Só **sugere**: escolher um do catálogo cria o ingrediente da organização (mesmo nome, categoria, unidade, apelidos) **depois** do diálogo de confirmação. Edição só por YAML/nova versão. |
| `carregar-catalogo` | `python -m app.cli carregar-catalogo`: upsert pelo nome normalizado, idempotente, nunca apaga, registra a versão. Valida categoria fora da lista, unidade fora de g/ml/un, nome repetido e apelido que aponta para dois nomes: **falha com a linha do erro** e não grava nada. Roda no deploy, logo depois da migração (`deploy/remote-deploy.sh`). |

### API

- `GET /ingredientes/busca?q=` — padaria (com categoria, saldo, itens, achado por nome ou apelido) e catálogo (só o que ainda não existe na padaria). `q` vazio lista a padaria inteira.
- `GET /ingredientes/sugestao?item=` — até 3 sugestões, cada uma com o motivo, nesta ordem: (1) o item já existe → ingrediente **travado**; (2) item parecido da organização; (3) ingrediente da organização por nome/apelido; (4) catálogo.
- `POST /ingredientes` — nome igual (normalizado) → **`409 ja_existe`** devolvendo o existente. Nome parecido → **`409 ingrediente_parecido`** até vir `confirmado_inexistente: true`; aí grava quem confirmou e quando.
- **O colar da planilha nunca cria ingrediente**: liga só com nome/apelido exatos; senão a linha fica “a decidir”; coluna vazia vira sugestão pelo item.
- Tudo isolado por organização; o catálogo é o único dado global.

### Interface

- **Campo Ingrediente = busca** (linha da tabela, lista do celular, “Novo ingrediente” da tela Ingredientes): “Sugeridos para “<item>””, “Na sua padaria” (por categoria, com saldo), “Do catálogo”, “Não encontrei, cadastrar novo”.
- **Sugestão pendente** aparece em destaque (borda tracejada, nome em itálico, botão “Usar”); confirma com clique ou **Enter**. Enquanto não confirmar, a linha conta **“a decidir”** no rodapé e a entrada não grava. Escolhido vira chip (nome + categoria) com ×; ingrediente que vem do item existente fica travado.
- **Diálogo “Cadastrar novo ingrediente”**: primeiro os existentes parecidos (cada um com “Usar”), depois nome genérico, categoria e unidade base, e o botão **“Confirmo que não existe, cadastrar”**.
- **Ingredientes**: filtro por categoria (com contagem), categoria embaixo do nome, “Novo ingrediente” começa pela busca, “Editar” muda nome, categoria e apelidos.

## 2. Testes (só os da área)

| Suíte | Resultado |
|---|---|
| `backend/tests/test_ingrediente_busca.py` (novo) | **44 passed** — comparação (acento, caixa, plural, ordem, palavra vazia, peso, número do produto, digitando); catálogo (70 itens em 12 categorias, idempotente rodando 2×, YAML inválido com a linha do erro, comando e saída); API (`409 ja_existe`, `confirmado_inexistente` com quem/quando, apelido parecido, colar nunca cria, busca, sugestão por item parecido / item existente travado / nome ou apelido / catálogo, máximo de 3, **isolamento entre organizações**, editar categoria e apelidos). |
| `backend/tests/test_estoque.py` (adaptado: a entrada agora liga por `ingrediente_id`) | **26 passed**. Os dois conjuntos juntos: **70 passed**. |
| Frontend (`vitest`, 7 arquivos) | **55 passed**, entre eles `fluxo.test.tsx` (21) com: sugestão pendente = “a decidir” até confirmar; Enter confirma e o × volta a “a decidir”; item existente trava o ingrediente; busca mostra padaria + catálogo e o diálogo mostra os **existentes antes dos campos**; “Não encontrei” leva o texto digitado e “Usar” escolhe o existente; categoria embaixo do nome e filtro; Novo ingrediente começa pela busca; Editar muda nome, categoria e apelidos. `entradaForm.test.ts` atualizado (a linha leva `ingrediente_id`, nunca cria). |
| `ruff`, `tsc --noEmit`, `eslint --max-warnings 0`, `npm run build` | limpos |

Nenhum teste rodou contra a produção. Postgres de teste e demonstração: descartável, local.

## 3. Capturas locais (`docs/evidence/gestao-005-local/`)

Ambiente **local** com banco de demonstração (organização “Padaria de demonstração”, 7 ingredientes, 5 itens com saldo). Script: `scripts/capture-gestao-005.mjs`; o resultado de cada checagem está em `capturas.md`. Em **1280 e 390 px**, todas sem rolagem horizontal e com controles de 40 px (44 no celular).

| O que mostra | 1280 px | 390 px |
|---|---|---|
| Linha com a **sugestão pendente** (item “Fermento fresco 500 g” → “Fermento biológico fresco”; rodapé “1 a decidir”) | `linha-com-sugestao-pendente-1280.png` | `linha-com-sugestao-pendente-390.png` |
| **Busca aberta**: Sugeridos para o item, Na sua padaria (por categoria, com saldo) | `busca-aberta-1280.png` | `busca-aberta-390.png` |
| Busca digitando “fermento”: Sugeridos + Na sua padaria + **Do catálogo** + “Não encontrei, cadastrar novo” | `busca-aberta-digitando-1280.png` | `busca-aberta-digitando-390.png` |
| **Diálogo “Cadastrar novo ingrediente”** com o existente parecido (“Usar”) antes dos campos | `dialogo-cadastrar-novo-1280.png` | `dialogo-cadastrar-novo-390.png` |
| **Ingredientes** com o filtro de categoria (Farinhas) | `ingredientes-filtro-categoria-1280.png` | `ingredientes-filtro-categoria-390.png` |
| Ingredientes sem filtro | `ingredientes-todos-1280.png` | `ingredientes-todos-390.png` |

A revisão visual achou e corrigiu um defeito: a lista de busca e o diálogo saem da tabela por portal para o `<body>` e perdiam as variáveis e a fonte do tema (lista “crua”, controles abaixo de 40 px). Agora o portal leva o tema junto (`.gestao-portal`).

## 4. Publicação (procedimento do 002)

- Gate de recursos: 916 MB disponíveis, 22 GB livres.
- SSH: porta 22 aberta **só para o meu IP /32**. O IP mudou no meio do ciclo (`191.57.225.3` → `191.57.232.246`); abri o segundo e **fechei os dois**, conferindo em seguida que nenhum dos dois ficou. Nenhuma das 29 regras antigas foi tocada. Chaves temporárias removidas do meu computador.
- `remote-deploy.sh` (atualizado: roda o `carregar-catalogo` logo após a migração): imagem carregada; migração **`0003_ingrediente_catalogo`** aplicada (só adiciona colunas e a tabela do catálogo; sem `CREATE EXTENSION`); catálogo carregado; `gestao-api` recriado. O deploy confirmou `saudável com lojadepaes-gestao:005-20261103 (anterior: 004-20261102)`.
- Depois: `gestao-api` `healthy`; `/api/v1/health` **200** e `/api/v1/ready` **200**; o JavaScript servido em produção (`index-BqEqFXJG.js`) é o mesmo do build local; **`https://lojadepaes.com.br/` 200** e `https://gestao.lojadepaes.com.br/` 200. Loja (`infra-api-1`, `infra-db-1`, `infra-caddy-1`) intocada.
- **Sem dados de teste em produção**: nenhum ingrediente, item, entrada ou usuário foi criado; só a migração e o catálogo de referência.

### Saída do `carregar-catalogo` em produção

1ª execução (no deploy):

```
catálogo de ingredientes - versão 1
70 inseridos, 0 alterados, 0 iguais
```

2ª execução (contêiner efêmero, mesma imagem):

```
catálogo de ingredientes - versão 1
0 inseridos, 0 alterados, 70 iguais
```

## 5. Rollback

1. **Imagem:** no host, `GESTAO_IMAGE=lojadepaes-gestao:004-20261102` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api` (a imagem 004 segue no host). A migração 0003 é **só aditiva** (colunas com padrão e uma tabela nova): a imagem antiga convive com ela, não precisa de `downgrade`.
2. **Só o banco:** `alembic downgrade 0002_organizacoes_estoque` remove as colunas e o catálogo (só se também voltar a imagem).
3. **Parar só o Gestão:** `deploy/rollback.sh`.

## 6. Para decidir

- **Novo catálogo**: para incluir ou corrigir ingredientes, edita-se o YAML (nova versão) e o deploy roda o `carregar-catalogo`; ele não apaga nada do que já existe. Se quiserem uma tela para isso, é outro ciclo.
- **“Cadastrar novo” sem parecido** exige o mesmo botão “Confirmo que não existe, cadastrar”: a confirmação é gravada com quem e quando só quando havia um parecido; se preferirem registrar sempre, é uma linha.
