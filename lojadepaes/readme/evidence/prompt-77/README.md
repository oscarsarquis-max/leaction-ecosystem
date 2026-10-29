# Prompt 77 — Jornada contextual do Gigio

07/10/2026. Sem seed, migração, pedido, e-mail, cobrança ou compra externa.

## Publicado

| Peça | Estado |
|---|---|
| Código Loja | `lojadepaes:prod-20261007b` |
| Rollback de app | `prod-20261006k` (não usar `h`; `a` é a primeira carga desta jornada, sem o reforço do CTA) |
| Bundle | `/assets/index-zwbhWtVP.js` |
| Alembic | `b8e4c1d93f50` (inalterado) |
| Hub marketplace | `https://actionhub.com.br/marketplace-api` — perfil `lojadepaes` inalterado |
| Hub FE build | `70XS4IOjG8YxGNHbm3l8H` (o mesmo do Prompt 75) |

## Flags efetivas

| Flag | Valor |
|---|---|
| `LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED` | **true** |
| `LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED` | **true** |
| `LOJADEPAES_ACCOMPANIMENTS_PREVIEW` | **false** |
| Gigio comum | **true** (Bedrock / Claude, atendimento comum intacto) |
| Pedidos / Pix / fidelidade | **true** |

A flag de complementos do Gigio desliga só o CTA e a consulta `lookup_accompaniments`. A vitrine genérica `/acompanhar` e o chat comum continuam.

## Exemplo concreto (produção, clique no botão renderizado)

Pergunta: «Como servir um pão de fermentação natural? Sugira vinho e queijo para acompanhar.»

- Resposta culinária + botão **Ver acompanhamentos sugeridos**.
- Destino: `/acompanhar?cats=vinhos,queijos&tipo=tinto&ids=…` — título «Acompanhamentos para vinho tinto e queijos», filtros visíveis, «Ver todos os acompanhamentos».
- 12 cartões de vinhos e queijos; nenhum azeite ou embalagem.
- Botões dos produtos: `https://www.mercadolivre.com.br/p/MLB…` (oficiais). Sem busca genérica externa.

Continuação: «Prefiro queijo, sem vinho.»

- Novo botão: `/acompanhar?cats=queijos&…`
- O botão da resposta anterior permanece com vinhos+queijos.

Acesso genérico `https://lojadepaes.com.br/acompanhar` continua a seleção completa do perfil (32 itens). IDs inválidos devolvem vazio + «Ver todos»; categoria desconhecida não finge contexto.

## Fotos e texto de entrega

Fotos da integração com `object-fit: contain`, centro e 12 px de respiro. Garrafas inteiras no cartão 4/3; queijos e azeites sem esticar. Grade 3/2/1 e 12 por página preservadas.

Rótulo público: **Data informada de entrega**. Ajuda: «Confira a previsão de entrega no Mercado Livre ou na Amazon e informe a data abaixo para planejar sua fornada. As compras e entregas são separadas.» A data é informada pelo cliente.

## Prova no navegador

Chrome headless contra produção. Capturas em `readme/evidence/prompt-77/prod/`.

| Arquivo | O quê |
|---|---|
| `chat-cta-1440.png` | Resposta + botão real |
| `vitrine-contextual-1440.png` / `390` | Clique no CTA → seleção filtrada |
| `chat-continuation-1440.png` | Continuação (dois hrefs no JSON) |
| `garrafas-{1440,1024,768,390,320}.png` | Garrafa inteira, contain |
| `queijos-1440.png` / `azeites-1440.png` | Outros formatos |
| `vitrine-geral-1440.png` | Catálogo sem filtro |

## Preservado

Pedidos, pagamentos, fidelidade, endereço, agenda e e-mails. Modelo e credenciais do Gigio. Limite de duas rodadas de ferramenta + síntese do Prompt 57. Sem reset de banco.

## Limitações

- A prateleira de vinhos do Hub ainda traz ruído da busca do Mercado Livre (gravata, livro «Roses are red»). O filtro da Loja não inventa esses itens e não os troca por azeite; o ajuste fino continua no painel do Hub.
- Claude às vezes sugere vinho/queijo sem chamar a ferramenta. O backend valida o critério da pergunta/resposta e monta o CTA; o modelo não inventa URL, preço nem ID.
- Azeite citado só como fio na fatia não entra no link. Restrição alimentar não vai na URL.
- Primeira leitura do Hub após restart do API pode vir fria (timeout 2 s); a seguinte serve o perfil.

## Rollback

- App: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006k` e `docker compose up -d --force-recreate api`.
- Só a jornada do Gigio: `LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=false` e recreate do API. A vitrine genérica permanece.
