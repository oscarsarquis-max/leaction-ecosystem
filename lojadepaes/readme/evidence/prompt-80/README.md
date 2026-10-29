# Prompt 80 — Curadoria da refeição, título e foto

07/10/2026. Correção pontual. Sem redesign, pedido, e-mail, cobrança ou compra externa.

## Publicado

| Peça | Estado |
|---|---|
| Loja | `lojadepaes:prod-20261007d` (rollback de app: `prod-20261007c`; bundle `/assets/index-BuTqGpTP.js`) |
| Hub marketplace | plugin Flask; rollback `rollback-prompt80-20261007T150020Z` |
| Alembic Loja | `b8e4c1d93f50` (inalterado) |
| Flags | vitrine pública on; complementos do Gigio on |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

## Três causas distintas

### 1. Contexto

O CTA só surgia depois de “vinho” no texto. A inferência lia a última palavra, não a mesa. “Leitão com saladas, que pão e acompanhamentos” não abria seleção.

Agora a conversa inteira entra no critério: prato (`mesa=leitao,salada`), categorias desta resposta, exclusões. Ordem do Gigio: responder a pergunta; depois “Para completar a mesa…”; o botão fica abaixo. Pedido/pagamento não ganham CTA.

### 2. Título / agrupamento

O cabeçalho da história usava o nome do primeiro produto. Daí “Vinho Tinto Vinho Tinto…” no H2 e de novo no cartão. Chips “vinho tinto” + “Vinhos” se repetiam. Preço dizia “na Mercado Livre”.

Cabeçalho único: **Sugestões para sua mesa**. Cartões só com o título do item. Repetição exata acidental some na exibição; o título bruto fica na fonte. Artigo: “no Mercado Livre” / “na Amazon”.

### 3. Imagem

`contain` sozinho não bastava: o quadro era 4:3 com `width/height: 100%`, e a foto oficial do Hub às vezes vinha pela menor variante. O quadro passou a 3:4, altura estável, `max-width/max-height`, contain e centro. No Hub, a foto oficial escolhida é a de maior `max_size`/`size` declarado. Sem sufixo inventado fora do contrato já usado (`-I` → `-O`).

Captura `garrafas-1440.png` e `garrafas-390.png`: rolha, rótulo e base visíveis nas três garrafas servidas.

## Jornada (perguntas genéricas)

| Pergunta | Resultado |
|---|---|
| Leitão com saladas, pão e acompanhamentos | Pães primeiro; “Para completar a mesa…”; CTA sem pedir vinho. `cats=vinhos,azeites,queijos&mesa=leitao,salada` |
| E um vinho? | Resposta sobre vinho na mesa anterior; CTA só de vinhos; link da primeira resposta intacto |
| Um queijo também faria sentido? | Queijo como tábua/entrada, não sobre o porco; seleção real de queijos |
| Só vinho, sem queijo | CTA só `vinhos` |
| sem álcool | CTA sem vinhos (azeites da mesa) |
| Pedido e pagamento | Sem CTA comercial |

JSON em `prod/chat-api-*.json`. A captura headless do chat estourou o tempo; a prova da conversa é a API ao vivo (Bedrock, 6–7 s). A vitrine foi aberta no navegador pelos hrefs reais.

## Vitrine depois

| Superfície | Itens | Título |
|---|---|---|
| Mesa (CTA) | 8 (3 vinhos, 3 queijos, 2 azeites) | Sugestões para sua mesa |
| Só vinhos + mesa | 3 | Sugestões para sua mesa |
| Catálogo geral | 29, grade 3/2/1, 12/página | Para acompanhar seu pão |

Sem gravata/livro/chaveiro/Mikasa. Sem H2 com nome de produto. Sem “na Mercado Livre”. Hub sem preço nesta carga → “Consulte o preço no Mercado Livre”, sem valor inventado.

## Limitações dos dados

- Harmonização é sugestão do Gigio, não degustação certificada.
- Preço e foto vêm do Hub/marketplace; ausência de preço não é preenchida.
- A prateleira genérica do Hub ainda sorteia termos; o CTA do Gigio trava `ids`.
- Foto incompleta do vendedor continua incompleta — o CSS não inventa recorte.

## Rollback

- Loja: `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007c`.
- Hub: restaurar `$RB/backend/app/services` e `pm2 restart marketplace-api`.
- Só o complemento do Gigio: `LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=false`.
