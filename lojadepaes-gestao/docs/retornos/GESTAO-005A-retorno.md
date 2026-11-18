# GESTAO-005A — A sugestão não pode errar o ingrediente

Base: `feat/gestao-005-ingrediente` (`8eedfe52`). Branch: `feat/gestao-005a-sugestao`. Imagem em produção: `lojadepaes-gestao:005a-20261103`.

Regra do ciclo cumprida: dentro da Loja de Pães só foram feitos os dois pontos autorizados (SSH só para o meu IP, e rebuild/restart do `gestao-api`). **Não houve migração nem carga de catálogo**: este ciclo não muda esquema nem dados; o deploy rodou com `GESTAO_SEM_BANCO=1` (opção nova do `remote-deploy.sh`, que só troca a imagem).

## 1. O defeito e a causa

Item “Fermento biológico seco 500 g”: a 1ª sugestão, já em destaque, era **“Fermento biológico fresco”**, só porque um item parecido da padaria usava esse ingrediente. O certo (“Fermento biológico seco”, do catálogo) vinha em 2º. Um Enter e a pessoa categorizava errado.

Causa: a sugestão ordenava por **de onde veio** (item parecido primeiro), sem olhar o que **diferencia** os ingredientes, e a interface destacava sempre a 1ª.

## 2. Regras novas

**Qualificadores decidem** (`app/domain/busca.py`, `qualificadores()` / `contradiz()`). Dentro de cada grupo os termos se excluem:

| Grupo | Termos |
|---|---|
| frescor | seco · fresco |
| tipo | 00 · 0 · 1 · integral · especial (os números só valem em texto de farinha; “1 kg” é peso e já sai antes) |
| sal | com sal · sem sal |
| cor | branco · preto · ao leite · meio amargo · amargo |
| forma | em pó · em flocos · em grão |
| açúcar | refinado · cristal · mascavo · demerara |

Se o item traz um qualificador que **contradiz** o do candidato (nome do ingrediente, ou o item parecido que o usa), o candidato **sai das sugestões**. Item sem qualificador não exclui ninguém. O candidato excluído **continua na busca**, em “Na sua padaria”.

**Ordem de confiança** (campo `nivel` na resposta; o motivo segue a ordem):

1. o item já existe (ingrediente travado);
2. o nome ou um apelido do ingrediente — **da padaria ou do catálogo** — está contido no nome do item, com os **mesmos qualificadores** (“O nome do item traz “…””); entre os de nível 2, o mais específico (mais palavras) vem antes, e a padaria antes do catálogo;
3. um item parecido da padaria (““…” usa este”);
4. semelhança geral (“Parecido com o nome do item” / “Sugerido pelo catálogo”).

**Destaque só com certeza** (campo `destaque`, só na 1ª): nível 1, ou nível 2 **claramente à frente** da 2ª (mais específico, ou a única, ou a padaria contra o catálogo). Nível 3 e 4 **nunca** vêm em destaque. Sem certeza, o campo mostra **“Escolha o ingrediente”**, nenhuma opção fica marcada na lista (o Enter não escolhe ninguém; a seta ▾ do campo, ou a seta para baixo, abre as sugestões) e a linha segue como “a decidir”.

**Diálogo “Cadastrar novo”**:
- “Estes já existem e parecem” agora inclui os do **catálogo** (“Fermento biológico seco · Fermentos · do catálogo · Usar”). “Usar” num do catálogo **preenche** nome, categoria, unidade e apelidos (nada é criado até “Confirmo que não existe, cadastrar”).
- Nome e categoria vêm do **melhor candidato do catálogo** (o do item; senão o do texto digitado), só quando há certeza. Sem candidato: o nome vem com a inicial maiúscula (nunca o texto cru em minúsculas) e a categoria **vem em branco** (“Escolha a categoria”), com o botão de cadastrar desligado até a pessoa escolher — não mais “Outros” por padrão.

API: `GET /ingredientes/sugestao` ganhou `nivel` e `destaque` em cada sugestão e o parâmetro `so_catalogo=true` (usado pelo diálogo).

## 3. Testes (só os da área)

| Suíte | Resultado |
|---|---|
| `backend/tests/test_sugestao_qualificadores.py` (**novo**) | **34 passed** |
| `backend/tests/test_ingrediente_busca.py` + `test_estoque.py` (dois testes da 005 ajustados à nova ordem/motivo) | **70 passed** — somando os três arquivos: **104 passed** |
| Frontend (`vitest`, 7 arquivos) | **57 passed** (2 novos em `fluxo.test.tsx`; 3 da 005 atualizados) |
| `ruff check`, `tsc --noEmit`, `eslint --max-warnings 0`, `npm run build` | limpos |

Os novos, pelos casos pedidos:
- “Fermento biológico seco 500 g” sugere **seco** em 1º, com destaque, e **não** sugere fresco, mesmo com um item “fresco” (e o ingrediente dele) na padaria; o fresco segue na busca. E o inverso (item fresco, seco na padaria).
- “Farinha Caputo 00 1 kg” sugere “Farinha de trigo tipo 00” (pelo apelido “caputo 00”), e **não** “tipo 1” nem “integral”, mesmo cadastrados na padaria.
- “Manteiga com sal 200 g” não sugere “Manteiga sem sal” — nem a que a padaria já tem com o apelido “manteiga”.
- **Dois candidatos próximos: nada fica em destaque** (padaria com dois “Leite…” de apelido “leite”; padaria com “seco” e “fresco” para o item “Fermento 500 g”, que não exclui nenhum). Na interface: “Escolha o ingrediente”, nada marcado, Enter não escolhe.
- Item que já existe: sempre travado e em destaque. Nível 3 (só item parecido) vem sem destaque. “Sal grosso” ganha de “sal” pela especificidade.
- 14 pares de **contradição** e 7 de **não contradição** (parametrizados) para a lista de qualificadores.
- Diálogo: lista o candidato do catálogo com “Usar” e vem com o nome e a categoria dele; sem candidato, categoria em branco e botão desligado.

## 4. Capturas locais (`docs/evidence/gestao-005a-local/`)

Ambiente **local**, banco de demonstração (a padaria tem “Fermento biológico fresco”, “Farinha de trigo”, “Farinha integral”, etc.). Script: `scripts/capture-gestao-005a.mjs`; cada checagem está em `capturas.md`. Em **1280 e 390 px** (a pedida era 1280): sem rolagem horizontal e com controles de 40 px (44 no celular).

| Caso | 1280 px | 390 px |
|---|---|---|
| **Fermento**: seco em destaque no campo (do catálogo); fresco fora das sugestões | `fermento-seco-em-destaque-1280.png` | `…-390.png` |
| Fermento, lista aberta: Sugeridos só com o seco; “Fermento biológico fresco” continua em “Na sua padaria” | `fermento-busca-aberta-1280.png` | `…-390.png` |
| **Dois candidatos próximos** (“Farinha 5 kg”): “Escolha o ingrediente”, nada em destaque | `dois-candidatos-sem-destaque-1280.png` | `…-390.png` |
| Dois candidatos, lista aberta pela seta: três sugestões, **nenhuma marcada**; o Enter não escolhe | `dois-candidatos-lista-aberta-1280.png` | `…-390.png` |
| **Diálogo** com o candidato do catálogo (“do catálogo · Usar”), nome “Fermento biológico seco” e categoria “Fermentos” já preenchidos | `dialogo-cadastrar-novo-catalogo-1280.png` | `…-390.png` |

## 5. Publicação (procedimento do 002)

- Gate: 903 MB disponíveis, 22 GB livres.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.232.246`; a regra não existia antes) e **fechada em seguida**; conferi que não ficou. As 29 regras antigas não foram tocadas. Chaves temporárias removidas.
- `remote-deploy.sh` com `GESTAO_SEM_BANCO=1`: imagem carregada, `gestao-api` recriado, saudável com `005a-20261103` (anterior: `005-20261103`). **Sem migração, sem catálogo.**
- Depois: `gestao-api` `healthy`; `/api/v1/health` **200**, `/api/v1/ready` **200**; o código novo está dentro do contêiner (checado em execução); o JavaScript servido (`index-Dn2AGBSK.js`) é o mesmo do build local; **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Loja intocada.
- **Sem dados de teste em produção.**

## 6. Rollback

No host, `GESTAO_IMAGE=lojadepaes-gestao:005-20261103` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api` (a imagem 005 segue no host; o banco não mudou).

## 7. Para decidir

- **Lista de qualificadores**: é uma tabela no código (`_QUALIFICADORES`). Se a padaria usar outros termos que diferenciam produtos (ex.: “light”, “zero”, “desnatado”), acrescentar uma linha por termo.
- **Sem certeza, a lista não abre sozinha**: abri-la em toda linha cobriria as colunas ao lado. O campo mostra “Escolha o ingrediente” com a seta ▾ e a lista abre ao focar ou ao tocar a seta. Se preferirem a lista aberta sozinha na linha que acabou de ser digitada, é uma linha.
- “Manteiga com sal” e “Manteiga sem sal” **continuam sendo avisados como parecidos** no cadastro (exige o “Confirmo que não existe”): a trava do cadastro segue conservadora; só a **sugestão** passou a distinguir.
