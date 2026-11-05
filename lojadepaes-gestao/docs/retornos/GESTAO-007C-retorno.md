# GESTAO-007C — Trocar ingrediente abre na tela

Base: `feat/gestao-007b-ingredientes` (`b9a0d0c6`). Branch: `feat/gestao-007c-trocar`. Imagem em produção: `lojadepaes-gestao:007c-20261105` (anterior: `007b-20261105`).

Regra do ciclo cumprida: na Loja de Pães só foram feitos os dois pontos autorizados (SSH só para o meu IP, fechado só a minha regra; rebuild e restart do `gestao-api`). **Não houve migração.** O deploy rodou com `GESTAO_SEM_BANCO=1`. Nenhum ingrediente de produção foi trocado. A troca da captura é só no banco local de demonstração.

## 1. A causa

O formulário "Trocar ingrediente" (e o "Corrigir custo" do mesmo menu) era desenhado dentro da linha expandida, no fluxo da página, e o cartão cortava o que passava da área visível: no Fubá local o formulário ia de y=644 a y=913 numa tela de 900 px, sem erro de console nem de rede.

O mesmo desenho valia para a linha expandida de Entradas. No painel lateral o formulário ficava dentro do painel fixo, então aparecia; agora os quatro diálogos (Corrigir custo, Trocar ingrediente, Cadastrar novo, Juntar) usam o mesmo modal.

## 2. O que mudou

"Trocar ingrediente" é ação do item. O ⋯ da sub-linha do item (o nome em negrito) tem Trocar ingrediente. O ⋯ da linha do lote tem Corrigir custo (e Informar validade, quando a entrada ainda está pendente). Vale na lista de Ingredientes, na de Entradas e nos dois painéis.

O diálogo diz o que vai mudar: "Mover **item** (N lote(s), quantidade) de *origem* para:", com a mesma busca da entrada (sugestões, padaria, catálogo e cadastrar com confirmação), motivo obrigatório e o botão "Mover".

Depois de gravar, a lista recarrega sem recarregar a página, os dois saldos mudam e aparece "Movido para …".

## 3. Testes (só os da área)

| Onde | Resultado |
|---|---|
| `buscaLista.test.ts`, `buscaLote.test.tsx`, `fluxo.test.tsx`, `trocarIngrediente.test.tsx` | **42 passed** |
| `eslint --max-warnings 0` nos arquivos tocados, `tsc --noEmit`, `npm run build` | limpos |

O teste novo, `trocarIngrediente.test.tsx`, falha no formulário antigo: o diálogo precisa estar fora de `.linha-expandida` e de `.fluxo-lista-card`, com `position: fixed` e `top: 0px`. No diagnóstico o formulário estava `static`, dentro do cartão. Agora o teste passa nos dois lugares:

| Pedido | Teste |
|---|---|
| Em Ingredientes, o ⋯ do lote não tem Trocar; o ⋯ do item abre o diálogo na área visível, grava e os dois saldos mudam | "na lista de ingredientes o ⋯ do item abre o diálogo na área visível, grava e os dois saldos mudam" |
| Em Entradas, o mesmo clique abre o diálogo na área visível e grava | "na lista de entradas o ⋯ do item abre o diálogo na área visível e grava" |
| Corrigir custo no lote, na linha e no painel | `buscaLote.test.tsx` e `fluxo.test.tsx`: o menu do lote abre "Corrigir custo"; o diálogo do painel fica fora de `.gestao-painel` |

## 4. Capturas locais (1280 e 390 px)

Ambiente **local** (`scripts/capture-gestao-007c.mjs`). Em `docs/evidence/gestao-007c-local/`. Checagem em `capturas.md`: diálogo na área visível, sem rolagem horizontal, controles com 40 px (44 no celular). O botão "Usar" da sugestão pendente é o chip já existente da busca e fica fora dessa medida.

| O que mostra | 1280 | 390 |
|---|---|---|
| O ⋯ do item, com "Trocar ingrediente" | `menu-item-1280.png` | `menu-item-390.png` |
| O diálogo centralizado (no celular, em tela cheia) | `dialogo-1280.png` | `dialogo-390.png` |
| A lista depois de mover, com o aviso e os dois saldos | `depois-1280.png` | `depois-390.png` |

Na demonstração local, o item "Fubá Orgânico" (1 lote, 1 kg) saiu de Fubá Orgânico e foi para Trigo Sarraceno. O aviso diz "Movido para Trigo Sarraceno". Fubá ficou em 0 g, sem saldo. Trigo Sarraceno ficou em 2 kg.

## 5. Publicação (procedimento do 002)

- Antes: 878 MB de memória disponíveis, 20 GB livres. Imagem no ar: `007b-20261105`, contêiner `healthy`.
- SSH: porta 22 aberta **só para o meu IP /32** (`191.57.224.96`; não estava entre as 29) e **fechada em seguida**. Conferi que voltou a 29 regras, as mesmas de antes. Chave temporária e o tar local removidos. O tar no host foi apagado depois do `docker load`.
- `remote-deploy.sh` com `GESTAO_SEM_BANCO=1`: "banco: nada a fazer neste deploy". `gestao-api` recriado e saudável com `lojadepaes-gestao:007c-20261105` (anterior: `lojadepaes-gestao:007b-20261105`).
- Dentro do contêiner: `/api/v1/health` **200**, `/api/v1/ready` **200**. O JavaScript servido (`index-DKfX-U3m.js`) tem o mesmo SHA-256 do build local e da imagem (`6d64141b0add35c8e3ec702031d340291d470f0c67d00cc9a1debfacca74da36`).
- **`https://lojadepaes.com.br/` 200**, `https://gestao.lojadepaes.com.br/` 200. Loja intocada. **Nenhum ingrediente de produção foi trocado.**

## 6. Rollback

No host, `GESTAO_IMAGE=lojadepaes-gestao:007b-20261105` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api`. A imagem 007B segue no host. O banco não mudou.
